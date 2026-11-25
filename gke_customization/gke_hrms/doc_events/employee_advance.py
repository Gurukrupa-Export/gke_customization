import frappe
from frappe import _
from frappe.utils import fmt_money, get_first_day, get_last_day, getdate


def calculate_working_days(doc, method=None):
    draft_advance_filters = {
        "employee": doc.employee,
        "status": "Draft",
        "workflow_state": ["not in", ["Send to Manager", "Send to HR"]],
    }
    if doc.name:
        draft_advance_filters["name"] = ["!=", doc.name]

    unpaid_advance = frappe.db.get_value(
        "Employee Advance", draft_advance_filters, "name"
    )

    if unpaid_advance:
        frappe.throw(
            _(
                "You are not eligible to apply for a new advance because old advance {0} is still Draft."
            ).format(unpaid_advance)
        )

    employee_details = frappe.db.get_value(
        "Employee",
        doc.employee,
        ["ctc", "holiday_list", "default_shift"],
        as_dict=True,
    )
    if not employee_details:
        frappe.throw(_("Employee {0} not found.").format(doc.employee))

    salary = employee_details.ctc
    holiday_list = employee_details.holiday_list
    default_shift = employee_details.default_shift

    if not holiday_list:
        frappe.throw(_("No holiday list linked to the employee."))

    posting_date = getdate(doc.posting_date)
    start_date = get_first_day(posting_date)
    mid_of_month = start_date.replace(day=15)
    end_date = get_last_day(posting_date)

    working_hours_query = """
        SELECT SUM(working_hours)
        FROM `tabAttendance`
        WHERE employee = %s
        AND attendance_date BETWEEN %s AND %s
        AND status IN ('Present', 'Absent', 'On Leave', 'Half Day', 'Work From Home')
        AND docstatus = 1
    """
    working_hours = frappe.db.sql(
        working_hours_query, (doc.employee, start_date, posting_date), as_list=True
    )[0][0]

    working_hours = working_hours or 0
    holiday_count = frappe.db.count(
        "Holiday",
        {"parent": holiday_list, "holiday_date": ["between", [start_date, end_date]]},
    )

    # Calculate total days and working days
    total_days = (end_date - start_date).days + 1  # Inclusive of both dates
    working_days = total_days - holiday_count

    # Get the shift hours from the "Shift Type" linked to the default_shift of the employee
    if default_shift:
        shift_hours = frappe.db.get_value("Shift Type", default_shift, "shift_hours")
        if shift_hours is None:
            frappe.throw(
                _("Shift Type {0} does not have working hours set.").format(
                    default_shift
                )
            )
    else:
        frappe.throw(_("No default shift set for the employee."))

    # Calculate the hourly salary and validate the advance amount
    if salary and shift_hours:
        if working_days <= 0:
            frappe.throw(_("No working days found in the month of the posting date."))

        day_salary = salary / working_days

        hourly_salary = day_salary / shift_hours

        earned_amount = working_hours * hourly_salary

        allowed_amt = earned_amount * 70 / 100

        paid_advance = frappe.db.sql(
            """
            SELECT COALESCE(SUM(advance_amount), 0)
            FROM `tabEmployee Advance`
            WHERE employee = %s
            AND docstatus = 1
            AND posting_date BETWEEN %s AND %s
            AND workflow_state IN ('Send to Account', 'Approved')
        """,
            (doc.employee, start_date, end_date),
        )[0][0]

        remaining_amount = allowed_amt - paid_advance

        if doc.advance_amount > remaining_amount:
            frappe.throw(
                _(
                    "You are not eligible for this advance amount of {0}. The maximum eligible amount based on your working hours is {1}, and the remaining amount is {2}."
                ).format(
                    fmt_money(doc.advance_amount, precision=2),
                    fmt_money(allowed_amt, precision=2),
                    fmt_money(remaining_amount, precision=2),
                )
            )
        if posting_date > mid_of_month and doc.advance_amount > salary:
            frappe.throw(
                _(
                    "Advance amount cannot be greater than the monthly salary. Monthly Salary: {0}, Advance amount: {1}"
                ).format(
                    fmt_money(salary, precision=2),
                    fmt_money(doc.advance_amount, precision=2),
                )
            )
