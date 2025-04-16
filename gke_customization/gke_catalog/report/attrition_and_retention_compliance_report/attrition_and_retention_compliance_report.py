import frappe
from frappe import _
from datetime import datetime

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    # chart = get_chart_data(filters)
    return columns, data

def get_columns():
    return [
        # Employee Identity & Position
        {"label": _("Employee ID"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "sticky": True, "width": 300},
        {"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 200},
        {"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 150},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 190},
        {"label": _("Designation"), "fieldname": "designation", "fieldtype": "Link", "options": "Designation", "width": 150},

        # Employment Details
        {"label": _("Employee Status"), "fieldname": "employee_status", "fieldtype": "Data", "width": 140},
        {"label": _("On Probation?"), "fieldname": "is_employee_on_probation", "fieldtype": "Data", "align": "center", "width": 130},
        {"label": _("Tenure"), "fieldname": "tenure", "fieldtype": "Data", "width": 140},

        # Resignation & Exit Process
        {"label": _("Date of Resignation"), "fieldname": "date_resignation", "fieldtype": "Date", "width": 140},
        {"label": _("Last Working Day"), "fieldname": "last_working_day", "fieldtype": "Date", "width": 140},
        {"label": _("Requested Relieving Date"), "fieldname": "requested_relieving_date", "fieldtype": "Date", "width": 190},
        {"label": _("Notice Period"), "fieldname": "notice_period", "fieldtype": "Data", "width": 160},
        {"label": _("Served Notice Period"), "fieldname": "served_notice", "fieldtype": "Data", "width": 180},
        {"label": _("Reason for Resignation"), "fieldname": "reason_for_resignation", "fieldtype": "Data", "width": 220},
        {"label": _("Resignation Status"), "fieldname": "resign_status", "fieldtype": "Data", "width": 160},
        {"label": _("Waive Off Notice Period"), "fieldname": "waive_off_notice_period", "fieldtype": "Data", "align": "center", "width": 190},
        {"label": _("Reduced Notice Days"), "fieldname": "reduce_notice_days", "fieldtype": "Int", "width": 190},

        # Reporting & HR Approvals
        {"label": _("Reporting Manager"), "fieldname": "reporting_manager", "fieldtype": "Link", "options": "Employee", "width": 180},
        {"label": _("Reporting Manager Approval"), "fieldname": "reporting_manager_approval", "fieldtype": "Data", "width": 225},
        {"label": _("HR Manager"), "fieldname": "hr_manager", "fieldtype": "Link", "options": "Employee", "width": 180},
        {"label": _("HR Manager Approval"), "fieldname": "hr_manager_approval", "fieldtype": "Data", "width": 200},

        # Exit Interview
        {"label": _("Exit Interview Scheduled?"), "fieldname": "exit_interview_done", "fieldtype": "Data", "align": "center", "width": 210},
        {"label": _("Interview Status"), "fieldname": "exit_interview_status", "fieldtype": "Data", "width": 160},
        {"label": _("Interview Date"), "fieldname": "interview_date", "fieldtype": "Data", "width": 160},
        {"label": _("Final decision"), "fieldname": "exit_emp_status", "fieldtype": "Data", "width": 160},
        {"label": _("Relieving Date"), "fieldname": "final_rel_date", "fieldtype": "Date", "width": 140},

        # Full & Final and Status Checks
        {"label": _("FnF Initiated?"), "fieldname": "fnf_initiated", "fieldtype": "Data", "align": "center", "width": 130},
        {"label": _("FnF Status"), "fieldname": "fnf_status", "fieldtype": "Data", "width": 160},
        {"label": _("FnF Date"), "fieldname": "fnf_date", "fieldtype": "Data", "width": 160},
        {"label": _("Final Settlement Overdue?"), "fieldname": "final_settlement_overdue", "fieldtype": "Data", "align": "center", "width": 210},

        # Access/User Status
        {"label": _("User Disabled?"), "fieldname": "user_status", "fieldtype": "Data", "align": "center", "width": 130},
        {"label": _("Last Salary Processed Date"), "fieldname": "posting_date", "fieldtype": "Data", "width": 220},
        {"label": _("Still Active After Final Day?"), "fieldname": "still_active_after_last_day", "fieldtype": "Data", "align": "center", "width": 230},
    ]


def get_data(filters):
    conditions = get_conditions(filters)

    query = f"""
    SELECT  
    er.employee,
    er.employee_name,
    er.company,
    er.branch,
    er.department,
    er.designation,
    er.date_resignation,
    er.last_working_day,
    er.requested_relieving_date,
    er.reason_for_resignation,
    er.reporting_manager,
    er.reporting_manager_approval,
    er.hr_manager,
    er.notice_period,
   (CASE 
  WHEN ei.relieving_date IS NOT NULL
  THEN DATEDIFF(ei.relieving_date, er.date_resignation)
  ELSE "Serving Notice"
END) AS served_notice,
    er.hr_manager_approval,
    CASE WHEN er.waive_off_notice_period = 'Yes' THEN '✅' ELSE '❌' END as waive_off_notice_period,
    er.reduce_notice_days,
    er.status as resign_status,
    CASE WHEN er.is_employee_on_probation = 'No' THEN '❌' WHEN er.is_employee_on_probation = 'Yes' THEN '✅' END as is_employee_on_probation,
    e.status as employee_status,
    (CASE WHEN ei.employee is not null THEN '✅' ELSE '❌' END) AS exit_interview_done,
    ei.date AS interview_date,
    ei.employee_status as exit_emp_status,
    ei.relieving_date as final_rel_date,
    fnf.transaction_date,
    CASE WHEN fnf.employee is not null THEN '✅' ELSE '❌' END AS fnf_initiated,
    -- Final Settlement Overdue
(CASE 
    WHEN er.last_working_day < CURDATE() AND fnf.transaction_date IS NULL THEN '✅'
    ELSE '❌'
END) AS final_settlement_overdue,

-- Still Active After Final Day
(CASE 
    WHEN er.last_working_day < CURDATE() AND e.status = 'Active' THEN '✅'
    ELSE '❌'
END) AS still_active_after_last_day,

-- Tenure (in years and months)
CONCAT(
    TIMESTAMPDIFF(YEAR, e.date_of_joining, er.last_working_day), ' Years ', 
    MOD(TIMESTAMPDIFF(MONTH, e.date_of_joining, er.last_working_day), 12), ' Months'
) AS tenure,

    fnf.status as fnf_status,
    ss.posting_date,
    u.name,
    CASE WHEN u.enabled = 0 THEN '✅' ELSE '❌' END AS user_status,
    ei.status as exit_interview_status
FROM `tabEmployee Resignation` er
LEFT JOIN `tabEmployee` e 
    ON er.employee = e.name
LEFT JOIN tabUser u
   ON e.user_id = u.name    
LEFT JOIN `tabExit Interview` ei
    ON er.employee = ei.employee
LEFT JOIN `tabFull and Final Statement` fnf
    ON er.employee = fnf.employee
LEFT JOIN (
    SELECT employee, max(posting_date) as posting_date 
      FROM `tabSalary Slip` GROUP BY employee
   ) AS ss ON er.employee = ss.employee
{conditions}
    """

    records = frappe.db.sql(query, as_dict=1)

    # for row in records:
    #     row["activities_button"] = f'<button class="btn btn-sm btn-primary view-activities-btn" data-onboarding-id="{row["onboarding_id"]}">View</button>'

    return records


def get_conditions(filters):
    conds = []

    if filters.get("from_date"):
        conds.append(f"er.date_resignation is null or er.date_resignation >= '{filters.get('from_date')}'")
    if filters.get("to_date"):
        conds.append(f"er.date_resignation <= '{filters.get('to_date')}'")
    if filters.get("company"):
        companies = ', '.join([f'"{d}"' for d in filters.get("company")])
        conds.append(f"""er.company IN ({companies})""")
    
    if filters.get("department"):
        departments = ', '.join([f'"{d}"' for d in filters.get("department")])
        conds.append(f"""er.department IN ({departments})""")

    if filters.get("branch"):
        branches = ', '.join([f'"{d}"' for d in filters.get("branch")])
        conds.append(f"""er.branch IN ({branches})""")    

    # if filters.get("boarding_status"):
    #     conds.append(f"eo.boarding_status = '{filters.get('boarding_status')}'")

    return "WHERE " + " AND ".join(conds) if conds else ""


