# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

from datetime import datetime, time, timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, get_time, getdate


class OTRequest(Document):
    def autoname(self):
        company_abbr = frappe.db.get_value("Company", self.company, "abbr")
        if not company_abbr:
            frappe.throw(
                _("Abbreviation is not set for Company {0}").format(self.company)
            )

        if self.branch:
            branch_parts = self.branch.split("-")
            branch_short = (
                branch_parts[-2] if len(branch_parts) > 1 else branch_parts[0]
            )
            series = f"{company_abbr}-{branch_short}-OT-.#####"
        else:
            series = f"{company_abbr}-OT-.#####"

        self.name = frappe.model.naming.make_autoname(series)

    def validate(self):
        for child in self.order_request:
            if child.ot_hours:
                total_hours = get_ot_hours_in_seconds(child.ot_hours, child.idx) / 3600
                child.food_eligibility = (
                    "Eligible" if total_hours >= 1 else "Not Eligible"
                )

        self.set_max_ot_hrs()

    def set_max_ot_hrs(self):
        rows_with_ot = [row for row in self.order_request if row.ot_hours]
        if rows_with_ot:
            max_ot_row = max(
                rows_with_ot,
                key=lambda row: get_ot_hours_in_seconds(row.ot_hours, row.idx),
            )
            self.ot_hours = max_ot_row.ot_hours

    # Added by Aditya at 29-01-2026
    def on_update_after_submit(self):
        if self.get("workflow_state") == "Create Checkin":
            self.check_attendance_request_exists(throw_error=True)
            self.create_checkin()

    def create_checkin(self):
        if not self.order_request:
            frappe.throw(_("Please add order request"))

        save_point = "ot_attendance"
        frappe.db.savepoint(save_point)

        try:
            for child in self.order_request:
                if child.employee_id and child.ot_hours and child.enable_ot_duration:
                    out_time = get_datetime(child.work_end_date)
                    in_time = get_datetime(child.work_start_date)
                    attendance_date = getdate(child.work_start_date)

                    # Create Check-in Entries
                    checkin_in_id = self._create_employee_checkin(
                        child.employee_id, in_time, "IN"
                    )
                    checkin_out_id = self._create_employee_checkin(
                        child.employee_id, out_time, "OUT"
                    )

                    checkin_ids = [checkin_in_id, checkin_out_id]

                    # Handle Attendance
                    self._handle_attendance(
                        child.employee_id,
                        attendance_date,
                        in_time,
                        out_time,
                        checkin_ids,
                        get_time(child.ot_hours),
                    )

            frappe.db.commit()
        except Exception:
            frappe.db.rollback(save_point=save_point)
            frappe.log_error(
                message=frappe.get_traceback(),
                title="Error in creating checkin/attendance",
                reference_doctype=self.doctype,
                reference_name=self.name,
            )
            raise

    def check_attendance_request_exists(self, throw_error=False):
        """
        Check if Attendance Request exists for an employee on a given date.

        :param employee: Employee ID
        :param work_date: date or datetime
        :param throw_error: bool (raise exception if found)
        :return: Attendance Request name or None
        """
        messages = []
        rows = [
            (child, getdate(child.work_start_date))
            for child in self.order_request
            if child.employee_id and child.work_start_date
        ]
        if not rows:
            return

        employees = list({child.employee_id for child, _work_date in rows})
        work_dates = [work_date for _child, work_date in rows]

        existing_attendance = {
            (row.employee, getdate(row.attendance_date))
            for row in frappe.get_all(
                "Attendance",
                filters={
                    "employee": ["in", employees],
                    "attendance_date": ["in", list(set(work_dates))],
                    "docstatus": 1,
                },
                fields=["employee", "attendance_date"],
            )
        }

        attendance_requests = frappe.get_all(
            "Attendance Request",
            filters=[
                ["employee", "in", employees],
                ["from_date", "<=", max(work_dates)],
                ["to_date", ">=", min(work_dates)],
                ["docstatus", "=", 1],
            ],
            fields=["employee", "from_date", "to_date"],
        )

        for child, work_date in rows:
            # If attendance exists → bypass
            if (child.employee_id, work_date) in existing_attendance:
                continue

            has_request = any(
                request.employee == child.employee_id
                and getdate(request.from_date) <= work_date <= getdate(request.to_date)
                for request in attendance_requests
            )

            if not has_request:
                messages.append(
                    _(
                        "Row {0}: No Attendance Request for Employee <b>{1}</b> on <b>{2}</b>"
                    ).format(child.idx, child.employee_id, work_date)
                )

        if messages:
            msg = "<br>".join(messages)

            if throw_error:
                frappe.throw(msg)
            else:
                frappe.msgprint(msg)

    def _create_employee_checkin(self, employee, checkin_time, log_type):
        """Creates an Employee Checkin record."""
        checkin = frappe.new_doc("Employee Checkin")
        checkin.employee = employee
        checkin.time = checkin_time
        checkin.log_type = log_type
        checkin.source = "Manual Punch"
        checkin.save(ignore_permissions=True)
        return checkin.name

    def _handle_attendance(
        self, employee, attendance_date, in_time, out_time, checkin_ids, ot_hours
    ):
        """Handles creation or update of Attendance record."""
        # Check for existing attendance
        attendance_name = frappe.db.exists(
            "Attendance",
            {"employee": employee, "attendance_date": attendance_date, "docstatus": 1},
        )

        if attendance_name:
            self._update_existing_attendance(
                attendance_name, in_time, out_time, checkin_ids, ot_hours
            )

    def _update_existing_attendance(
        self, attendance_name, in_time, out_time, checkin_ids, ot_hours
    ):
        """Updates existing submitted attendance directly using db_set."""

        attendance_doc = frappe.db.get_value(
            "Attendance",
            attendance_name,
            ["status", "shift", "working_hours", "in_time", "out_time"],
            as_dict=True,
        )

        existing_status = attendance_doc.status
        existing_shift = attendance_doc.shift
        existing_working_hours = attendance_doc.get("working_hours") or 0
        existing_in_time = attendance_doc.get("in_time")
        existing_out_time = attendance_doc.get("out_time")

        if existing_in_time:
            final_in_time = min(existing_in_time, in_time)
        else:
            final_in_time = in_time

        if existing_out_time:
            final_out_time = max(existing_out_time, out_time)
        else:
            final_out_time = out_time

        # Get existing checkins linked to this attendance
        existing_checkins = frappe.get_all(
            "Employee Checkin", filters={"attendance": attendance_name}, pluck="name"
        )

        ot_hrs = get_time(ot_hours)
        total_seconds = ot_hrs.hour * 3600 + ot_hrs.minute * 60 + ot_hrs.second
        float_hours = total_seconds / 3600

        # Calculate new working hours
        total_working_hours = existing_working_hours + float_hours

        # Direct DB Update (No Cancel / No Submit)
        frappe.db.set_value(
            "Attendance",
            attendance_name,
            {
                "status": existing_status,
                "shift": existing_shift,
                "in_time": final_in_time,
                "out_time": final_out_time,
                "working_hours": total_working_hours,
            },
        )

        # Link checkins
        all_checkins = list(set((checkin_ids or []) + existing_checkins))
        self._link_checkins_to_attendance(all_checkins, attendance_name)

    def _link_checkins_to_attendance(self, checkin_ids, attendance_name):
        """Links the checkin records to the attendance."""
        if checkin_ids and attendance_name:
            frappe.db.set_value(
                "Employee Checkin",
                {"name": ["in", checkin_ids]},
                "attendance",
                attendance_name,
            )


def get_ot_hours_in_seconds(ot_hours, row_idx):
    if isinstance(ot_hours, timedelta):
        return ot_hours.total_seconds()

    if isinstance(ot_hours, str):
        try:
            ot_hours = datetime.strptime(ot_hours, "%H:%M:%S").time()
        except ValueError:
            frappe.throw(
                _(
                    "Row {0}: Invalid OT Hours format '{1}'. Please use HH:MM:SS format."
                ).format(row_idx, ot_hours)
            )

    if isinstance(ot_hours, time):
        return ot_hours.hour * 3600 + ot_hours.minute * 60 + ot_hours.second

    frappe.throw(_("Row {0}: Unsupported OT Hours type.").format(row_idx))


@frappe.whitelist()
def fill_employee_details(department_head, branch=None, gender=None):
    filters = {
        "reports_to": department_head,
        "status": "Active",
    }
    if branch:
        filters.update({"branch": branch})

    if gender:
        filters.update({"gender": gender})

    employees = frappe.db.get_all(
        "Employee", filters=filters, fields=["name", "employee_name"]
    )

    if employees:
        return employees
    else:
        frappe.msgprint(_("There is no Employees for Selected Department Head."))
