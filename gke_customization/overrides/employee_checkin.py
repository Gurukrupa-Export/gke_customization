import frappe
from frappe import _
from frappe.utils import get_datetime
from hrms.hr.doctype.employee_checkin.employee_checkin import EmployeeCheckin
from hrms.hr.doctype.shift_assignment.shift_assignment import (
    get_actual_start_end_datetime_of_shift,
)
from hrms.hr.doctype.shift_type.shift_type import get_employee_shift


class CustomEmployeeCheckin(EmployeeCheckin):
    # validate() is intentionally NOT overridden: the core EmployeeCheckin
    # validations (incl. validate_time_change) run as-is and dispatch to the
    # fetch_shift() override below, which keeps the upgrade path clean.

    @frappe.whitelist()
    def fetch_shift(self):
        """Session-based punch pairing (default) with legacy window-containment
        fallback controlled by HR Settings switches."""
        if self.flags.get("pp_result"):
            # Already classified upstream by sync_checkin._determine_log_type() —
            # avoid a second classify_punch() call for the same punch.
            from gke_customization.gke_hrms.punch_pairing import bind_checkin

            bind_checkin(self, self.flags.pp_result)
            return

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
                result = classify_punch(self.employee, get_datetime(self.time))
                bind_checkin(self, result)
                return
            except Exception:
                # never block punch creation on an engine failure:
                # log it and fall back to legacy window behaviour
                frappe.logger("punch_pairing").error(
                    {
                        "msg": "classify_punch failed, using legacy fetch_shift",
                        "employee": self.employee,
                        "time": str(self.time),
                        "traceback": frappe.get_traceback(),
                    }
                )
                return _legacy_fetch_shift(self)

        if mode == "log":
            # parallel-run: keep legacy behaviour, log the engine decision only
            try:
                result = classify_punch(self.employee, get_datetime(self.time))
                frappe.logger("punch_pairing").info(
                    {
                        "doctype": "Employee Checkin",
                        "employee": self.employee,
                        "time": str(self.time),
                        "engine": {
                            "rule": result.get("rule"),
                            "log_type": result.get("log_type"),
                            "shift": (result.get("instance") or {}).get("shift_type"),
                        },
                    }
                )
            except Exception:
                frappe.logger("punch_pairing").error(frappe.get_traceback())
            return _legacy_fetch_shift(self)

        return _legacy_fetch_shift(self)


def _legacy_fetch_shift(doc):
    """Previous behaviour (window containment + shift-assignment preference).
    Retained for the 'off' and parallel-run modes."""
    if not (
        shift_actual_timings := get_actual_start_end_datetime_of_shift(
            doc.employee, get_datetime(doc.time), True
        )
    ):
        doc.shift = None
        doc.offshift = 1
        return

    if (
        shift_actual_timings.shift_type.determine_check_in_and_check_out
        == "Strictly based on Log Type in Employee Checkin"
        and not doc.log_type
        and not doc.skip_auto_attendance
    ):
        frappe.throw(
            _("Log Type is required for check-ins falling in the shift: {0}.").format(
                shift_actual_timings.shift_type.name
            )
        )
    assignment = frappe.get_all(
        "Shift Assignment",
        filters={
            "employee": doc.employee,
            "start_date": ["<=", doc.time],
            "docstatus": 1,
            "status": "Active",
        },
        or_filters=[["end_date", ">=", doc.time], ["end_date", "is", "not set"]],
        pluck="shift_type",
    )
    if assignment:
        shift_assigment = get_employee_shift(
            doc.employee, get_datetime(doc.time), True, "forward"
        )
        if shift_actual_timings.shift_type.name != shift_assigment.shift_type.name:
            doc.offshift = 0
            doc.shift = shift_assigment.shift_type.name
            doc.shift_actual_start = shift_assigment.actual_start
            doc.shift_actual_end = shift_assigment.actual_end
            doc.shift_start = shift_assigment.start_datetime
            doc.shift_end = shift_assigment.end_datetime
        else:
            doc.offshift = 0
            doc.shift = shift_actual_timings.shift_type.name
            doc.shift_actual_start = shift_actual_timings.actual_start
            doc.shift_actual_end = shift_actual_timings.actual_end
            doc.shift_start = shift_actual_timings.start_datetime
            doc.shift_end = shift_actual_timings.end_datetime
    elif not doc.attendance:
        doc.offshift = 0
        doc.shift = shift_actual_timings.shift_type.name
        doc.shift_actual_start = shift_actual_timings.actual_start
        doc.shift_actual_end = shift_actual_timings.actual_end
        doc.shift_start = shift_actual_timings.start_datetime
        doc.shift_end = shift_actual_timings.end_datetime
