import frappe
from frappe import _
import hrms
from frappe.utils import cint, get_datetime

from hrms.hr.doctype.shift_assignment.shift_assignment import get_actual_start_end_datetime_of_shift
from hrms.hr.doctype.shift_type.shift_type import get_employee_shift

from hrms.hr.utils import (
	get_distance_between_coordinates,
	set_geolocation_from_coordinates,
	validate_active_employee,
)

from hrms.hr.doctype.employee_checkin.employee_checkin import EmployeeCheckin

class CustomEmployeeCheckin(EmployeeCheckin):
    def validate(self):
        validate_active_employee(self.employee)
        self.validate_duplicate_log()
        self.validate_time_change()
        self.fetch_shift()
        self.set_geolocation()
        self.validate_distance_from_shift_location()

    @frappe.whitelist()
    def fetch_shift(self):
        """Session-based punch pairing (default) with legacy fallback,
        controlled by the HR Settings switch (enable_session_pairing)."""
        try:
            from gke_customization.gke_hrms.punch_pairing import (
                bind_checkin,
                classify_punch,
                get_mode,
            )
        except Exception:
            get_mode = None

        mode = get_mode() if get_mode else "off"

        if mode == "live":
            try:
                bind_checkin(self, classify_punch(self.employee, get_datetime(self.time)))
                return
            except Exception:
                # never block punch creation on an engine failure
                frappe.logger("punch_pairing").error(
                    {"msg": "classify_punch failed, using legacy fetch_shift",
                     "employee": self.employee, "time": str(self.time),
                     "traceback": frappe.get_traceback()}
                )
                return self._legacy_fetch_shift()

        return self._legacy_fetch_shift()

    def _legacy_fetch_shift(self):
        """Legacy window-containment behaviour (original fetch_shift body)."""
        if not (
            shift_actual_timings := get_actual_start_end_datetime_of_shift(
                self.employee, get_datetime(self.time), True
            )
        ):
            self.shift = None
            self.offshift = 1
            return

        if (
            shift_actual_timings.shift_type.determine_check_in_and_check_out
            == "Strictly based on Log Type in Employee Checkin"
            and not self.log_type
            and not self.skip_auto_attendance
        ):
            frappe.throw(
                _("Log Type is required for check-ins falling in the shift: {0}.").format(
                    shift_actual_timings.shift_type.name
                )
            )
        assignment = frappe.get_all(
            "Shift Assignment",
            filters={
                "employee": self.employee,
                "start_date": ["<=", self.time],
                "docstatus": 1,
                "status": "Active",
            },
            or_filters=[["end_date", ">=", self.time], ["end_date", "is", "not set"]],
            pluck="shift_type",
        )
        if assignment:
            shift_assigment = get_employee_shift(self.employee, get_datetime(self.time), True, "forward")
            if(shift_actual_timings.shift_type.name != shift_assigment.shift_type.name):
                self.offshift = 0
                self.shift = shift_assigment.shift_type.name
                self.shift_actual_start = shift_assigment.actual_start
                self.shift_actual_end = shift_assigment.actual_end
                self.shift_start = shift_assigment.start_datetime
                self.shift_end = shift_assigment.end_datetime
            else:
                self.offshift = 0
                self.shift = shift_actual_timings.shift_type.name
                self.shift_actual_start = shift_actual_timings.actual_start
                self.shift_actual_end = shift_actual_timings.actual_end
                self.shift_start = shift_actual_timings.start_datetime
                self.shift_end = shift_actual_timings.end_datetime
            # self.offshift = 0
            # self.shift = shift_actual_timings.shift_type.name
            # self.shift_actual_start = shift_actual_timings.actual_start
            # self.shift_actual_end = shift_actual_timings.actual_end
            # self.shift_start = shift_actual_timings.start_datetime
            # self.shift_end = shift_actual_timings.end_datetime
        elif not self.attendance:
            self.offshift = 0
            self.shift = shift_actual_timings.shift_type.name
            self.shift_actual_start = shift_actual_timings.actual_start
            self.shift_actual_end = shift_actual_timings.actual_end
            self.shift_start = shift_actual_timings.start_datetime
            self.shift_end = shift_actual_timings.end_datetime