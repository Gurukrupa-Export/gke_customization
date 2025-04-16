import frappe
from frappe import _
from datetime import datetime

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart_data(filters)
    return columns, data, None, chart

def get_columns():
    return [
        {"label": _("Job Applicant"), "fieldname": "job_applicant", "fieldtype": "Link", "options": "Job Applicant", "width": 220},
        {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 190},
        {"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 250},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 180},
        {"label": _("Designation"), "fieldname": "designation", "fieldtype": "Link", "options": "Designation", "width": 160},
        {"label": _("Branch"), "fieldname": "location", "fieldtype": "Link", "options": "Branch", "width": 160},
        {"label": _("Joining Date"), "fieldname": "date_of_joining", "fieldtype": "Date", "width": 130},
        {"label": _("Onboarding Start Date"), "fieldname": "boarding_begins_on", "fieldtype": "Date", "width": 180},
        {"label": _("Probation Period"), "fieldname": "probation_period", "fieldtype": "Data", "width": 150},
        {"label": _("Onboarding Status"), "fieldname": "boarding_status", "fieldtype": "Data", "width": 160},
        {"label": _("Time Duration"), "fieldname": "time_duration", "fieldtype": "Data", "width": 160},
        {"label": _("Activities"), "fieldname": "activities_button", "fieldtype": "Data", "width": 130},
    ]

def get_data(filters):
    conditions = get_conditions(filters)

    query = f"""
    SELECT 
        eo.name as onboarding_id,
        eo.job_applicant,
        eo.employee_name,
        eo.company AS company,
        COALESCE(eo.department, ja.custom_department) AS department,
        COALESCE(eo.designation, ja.designation) AS designation,
        jop.location,
        eo.date_of_joining,
        eo.boarding_begins_on,
        (CASE 
            WHEN eo.boarding_begins_on IS NULL THEN '-'
            WHEN eo.boarding_status = 'Completed' THEN 
                CONCAT(DATEDIFF(IFNULL(eo.modified, CURDATE()), eo.boarding_begins_on), ' days taken')
            ELSE CONCAT('Started ',DATEDIFF(CURDATE(), eo.boarding_begins_on), ' days ago')
        END) AS time_duration,
        MAX(CASE WHEN jot.offer_term = 'Probationary Period' THEN jot.value END) AS probation_period,
        eo.boarding_status,
        eo.project
    FROM `tabEmployee Onboarding` eo
    LEFT JOIN `tabJob Applicant` ja ON eo.job_applicant = ja.name
    LEFT JOIN `tabJob Offer` jo ON eo.job_applicant = jo.job_applicant
    LEFT JOIN `tabJob Offer Term` jot ON jo.name = jot.parent
    LEFT JOIN `tabJob Opening` jop ON ja.job_title = jop.name
    {conditions}
    GROUP BY eo.job_applicant
    ORDER BY eo.date_of_joining DESC
    """

    records = frappe.db.sql(query, as_dict=1)

    for row in records:
        row["activities_button"] = f'<button class="btn btn-sm btn-primary view-activities-btn" data-onboarding-id="{row["onboarding_id"]}">View</button>'

    return records


# Chart: Onboardings Per Month
def get_chart_data(filters):
    conditions = []
    
    if filters.get("from_date"):
        conditions.append(f"eo.date_of_joining >= '{filters.get('from_date')}'")
    if filters.get("to_date"):
        conditions.append(f"eo.date_of_joining <= '{filters.get('to_date')}'")
    if filters.get("company"):
        companies = ', '.join([f'"{d}"' for d in filters.get("company")])
        conditions.append(f"""eo.company IN ({companies})""")
    if filters.get("department"):
        departments = ', '.join([f'"{d}"' for d in filters.get("department")])
        conditions.append(f"""COALESCE(eo.department, ja.custom_department) IN ({departments})""")
    if filters.get("branch"):
        branches = ', '.join([f'"{d}"' for d in filters.get("branch")])
        conditions.append(f"""jop.location IN ({branches})""")    
    if filters.get("status"):
        conditions.append(f"eo.boarding_status = '{filters.get('status')}'")    

    condition_str = "WHERE eo.date_of_joining IS NOT NULL"
    if conditions:
        condition_str += " AND " + " AND ".join(conditions)

    monthly_data = frappe.db.sql(f"""
        SELECT 
            DATE_FORMAT(eo.date_of_joining, '%Y-%m') AS month,
            COUNT(*) AS onboardings
        FROM `tabEmployee Onboarding` eo
        LEFT JOIN `tabJob Applicant` ja ON eo.job_applicant = ja.name
        LEFT JOIN `tabJob Opening` jop ON ja.job_title = jop.name                         
        {condition_str}
        GROUP BY month
        ORDER BY month ASC
    """, as_dict=True)

    labels = [row["month"] for row in monthly_data]
    values = [row["onboardings"] for row in monthly_data]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": "Onboardings",
                    "values": values
                }
            ]
        },
        "type": "line",
        "colors": ["#4CD7C6"],
        "title": "Monthly Employee Onboardings"
    }



def get_conditions(filters):
    conds = []

    if filters.get("from_date"):
        conds.append(f"eo.date_of_joining >= '{filters.get('from_date')}'")
    if filters.get("to_date"):
        conds.append(f"eo.date_of_joining <= '{filters.get('to_date')}'")
    if filters.get("company"):
        companies = ', '.join([f'"{d}"' for d in filters.get("company")])
        conds.append(f"""eo.company IN ({companies})""")
    
    if filters.get("department"):
        departments = ', '.join([f'"{d}"' for d in filters.get("department")])
        conds.append(f"""COALESCE(eo.department, ja.custom_department) IN ({departments})""")

    if filters.get("branch"):
        branches = ', '.join([f'"{d}"' for d in filters.get("branch")])
        conds.append(f"""jop.location IN ({branches})""")    

    if filters.get("status"):
        conds.append(f"eo.boarding_status = '{filters.get('status')}'")

    return "WHERE " + " AND ".join(conds) if conds else ""



@frappe.whitelist()
def get_onboarding_activities(onboarding_id):
    onboarding = frappe.db.get_all(
        "Employee Onboarding",
        filters={"name": onboarding_id},
        fields=["project", "job_applicant", "employee_name"]
    )

    if not onboarding:
        return {"onboarding_details": {}, "activities": []}

    project = onboarding[0]["project"]

    tasks = frappe.db.get_all(
        "Task", 
        filters={"project": project},
        fields=["project", "subject", "status","_assign","exp_start_date","exp_end_date"]
    )

    activities_with_task = []
    for task in tasks:
        clean_subject = task["subject"].split(":")[0].strip() if task["subject"] else ""
        activities_with_task.append({
            "project": task["project"],
            "subject": clean_subject,
            "task_status": task["status"],
            "assigned_to": task["_assign"],
            "exp_start_date": task["exp_start_date"],
            "exp_end_date": task["exp_end_date"]
        })

    return {
        "onboarding_details": {
            "job_applicant": onboarding[0]["job_applicant"],
            "employee_name": onboarding[0]["employee_name"]
        },
        "activities": activities_with_task
    }


