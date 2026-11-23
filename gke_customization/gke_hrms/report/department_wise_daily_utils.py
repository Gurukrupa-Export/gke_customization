# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe

USER_GROUP_FIELD = "custom_user_group"
ALERT_SENDER = "alerts@gkexport.com"


def get_departments_with_managers(department=None):
    """Return [department] when given, else every Department that has a user in custom_user_group."""
    if department:
        return [department]

    return frappe.get_all(
        "User Group Member",
        filters={"parenttype": "Department", "parentfield": USER_GROUP_FIELD},
        pluck="parent",
        distinct=True,
    )


def get_manager_departments(user_id):
    """Departments where `user_id` is listed in custom_user_group. None means no filter (all departments)."""
    if not user_id:
        return None

    return frappe.get_all(
        "User Group Member",
        filters={
            "parenttype": "Department",
            "parentfield": USER_GROUP_FIELD,
            "user": user_id,
        },
        pluck="parent",
    )


def get_department_manager_emails(department):
    """Users listed in Department.custom_user_group."""
    emails = frappe.get_all(
        "User Group Member",
        filters={
            "parenttype": "Department",
            "parentfield": USER_GROUP_FIELD,
            "parent": department,
        },
        pluck="user",
    )
    return [email for email in emails if email]


def get_branch_hr_emails(department):
    """Users listed in Branch.custom_user_group for every branch that has an active employee in this department."""
    branches = frappe.get_all(
        "Employee",
        filters={"department": department, "status": "Active", "branch": ["is", "set"]},
        pluck="branch",
        distinct=True,
    )
    if not branches:
        return []

    users = frappe.get_all(
        "User Group Member",
        filters={
            "parenttype": "Branch",
            "parentfield": USER_GROUP_FIELD,
            "parent": ["in", branches],
        },
        pluck="user",
    )
    return [user for user in users if user]


def get_active_department_employees(department, fields):
    return frappe.get_all(
        "Employee",
        filters={"department": department, "status": "Active"},
        fields=fields,
    )


def get_employee_checkins_for_date(employee_ids, date):
    """Return {employee: [checkins ordered by time asc]} with log_type, time and shift for one date."""
    checkins_by_employee = {}
    if not employee_ids:
        return checkins_by_employee

    checkins = frappe.get_all(
        "Employee Checkin",
        filters=[
            ["employee", "in", employee_ids],
            ["time", "between", [f"{date} 00:00:00", f"{date} 23:59:59"]],
        ],
        fields=["employee", "log_type", "time", "shift"],
        order_by="time asc",
    )
    for checkin in checkins:
        checkins_by_employee.setdefault(checkin.employee, []).append(checkin)

    return checkins_by_employee


def get_in_out_and_shift(checkins):
    """Return (earliest IN time, latest OUT time, first non-empty shift) from checkins ordered by time asc."""
    if not checkins:
        return None, None, None

    in_times = [checkin.time for checkin in checkins if checkin.log_type == "IN"]
    out_times = [checkin.time for checkin in checkins if checkin.log_type == "OUT"]

    in_time = min(in_times) if in_times else None
    out_time = max(out_times) if out_times else None
    shift = next((checkin.shift for checkin in checkins if checkin.shift), None)

    return in_time, out_time, shift


def get_cc_emails(manager_emails, hr_emails, fixed_cc):
    """Fixed CC followed by branch HR emails, de-duplicated in order, excluding the managers."""
    return [
        email
        for email in dict.fromkeys(fixed_cc + hr_emails)
        if email not in manager_emails
    ]


def send_department_report_emails(
    departments, build_report, render_html, get_subject, log_title, fixed_cc
):
    """Email one report per department to its managers.

    build_report(department) returns the report payload, or a falsy value to skip the department.
    render_html(department, report) returns the email body.
    get_subject(department) returns the email subject.
    Returns {"sent": [...], "skipped": [...]}.
    """
    sent = []
    skipped = []

    for department in departments:
        report = build_report(department)
        if not report:
            skipped.append(department)
            continue

        manager_emails = get_department_manager_emails(department)
        if not manager_emails:
            frappe.log_error(
                title=log_title, message="Department: {0}".format(department)
            )
            skipped.append(department)
            continue

        hr_emails = get_branch_hr_emails(department)
        cc = get_cc_emails(manager_emails, hr_emails, fixed_cc)

        frappe.sendmail(
            recipients=", ".join(manager_emails),
            cc=cc,
            sender=ALERT_SENDER,
            subject=get_subject(department),
            message=render_html(department, report),
            now=True,
            expose_recipients="header",
        )
        sent.append({"department": department, "managers": manager_emails})

    return {"sent": sent, "skipped": skipped}
