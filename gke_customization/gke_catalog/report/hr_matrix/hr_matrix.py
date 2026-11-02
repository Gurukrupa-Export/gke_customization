# Copyright (c) 2026, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, today

def execute(filters=None):
    if not filters:
        filters = {}

    # Default date range logic if not provided
    current_year = getdate(today()).year
    start_date = filters.get("from_date") or f"{current_year}-01-01"
    end_date = filters.get("to_date") or f"{current_year}-12-31"
    status_filter = filters.get("status")

    columns = get_columns()
    data = []

    # ----------------------------------------------------
    # SECTION 4: New Hire 90-Day Failure Rate
    # ----------------------------------------------------
    failure_rate_query = """
        SELECT 
            YEAR(date_of_joining) AS hire_year, 
            MONTHNAME(date_of_joining) AS hire_month, 
            COUNT(name) AS total_new_hires, 
            SUM(CASE WHEN relieving_date IS NOT NULL AND DATEDIFF(relieving_date, date_of_joining) <= 90 THEN 1 ELSE 0 END) AS new_hires_left_within_90_days, 
            ROUND((SUM(CASE WHEN relieving_date IS NOT NULL AND DATEDIFF(relieving_date, date_of_joining) <= 90 THEN 1 ELSE 0 END) / COUNT(name)) * 100, 2) AS failure_rate
        FROM `tabEmployee` 
        WHERE date_of_joining BETWEEN %(start_date)s AND %(end_date)s
    """
    if status_filter:
        failure_rate_query += " AND status = %(status)s"
    failure_rate_query += " GROUP BY YEAR(date_of_joining), MONTH(date_of_joining) ORDER BY hire_year DESC, MONTH(date_of_joining) DESC"
    
    failure_data = frappe.db.sql(failure_rate_query, {"start_date": start_date, "end_date": end_date, "status": status_filter}, as_dict=True)

    # ----------------------------------------------------
    # SECTION 5: Average Time to Fill a Job Vacancy
    # ----------------------------------------------------
    time_to_fill_query = """
        SELECT 
            COUNT(DISTINCT ja.name) AS total_positions_filled, 
            ROUND(AVG(DATEDIFF(ja.modified, jr.posting_date)), 2) AS avg_time_to_fill
        FROM `tabJob Applicant` ja 
        INNER JOIN `tabJob Opening` jo ON ja.job_title = jo.name 
        INNER JOIN `tabJob Requisition` jr ON jo.job_requisition = jr.name 
        WHERE ja.status = 'Accepted' 
          AND jr.posting_date IS NOT NULL 
          AND ja.modified IS NOT NULL
          AND ja.modified BETWEEN %(start_date)s AND %(end_date)s
    """
    # Note: Status filter applies optionally if mapable to Job Opening/Applicant context
    fill_data = frappe.db.sql(time_to_fill_query, {"start_date": start_date, "end_date": end_date}, as_dict=True)
    avg_days_to_fill = fill_data[0].avg_time_to_fill if fill_data and fill_data[0].avg_time_to_fill else 0

    # ----------------------------------------------------
    # SECTION 7: Attrition & Retention Rate
    # ----------------------------------------------------
    attrition_query = """
        WITH time_period AS ( 
            SELECT STR_TO_DATE(%(start_date)s, '%%Y-%%m-%%d') AS start_date, STR_TO_DATE(%(end_date)s, '%%Y-%%m-%%d') AS end_date 
        ), 
        emp_counts AS ( 
            SELECT 
                COUNT(CASE WHEN e.date_of_joining <= p.start_date AND (e.relieving_date IS NULL OR e.relieving_date >= p.start_date) THEN 1 END) AS start_count, 
                COUNT(CASE WHEN e.date_of_joining <= p.end_date AND (e.relieving_date IS NULL OR e.relieving_date > p.end_date) THEN 1 END) AS end_count 
            FROM `tabEmployee` e CROSS JOIN time_period p 
            {status_placeholder}
        ), 
        terminations AS ( 
            SELECT COUNT(DISTINCT r.employee) AS leavers_count 
            FROM `tabEmployee Resignation` r CROSS JOIN time_period p 
            WHERE r.last_working_day BETWEEN p.start_date AND p.end_date AND r.docstatus = 1 
        ) 
        SELECT 
            ec.start_count AS active_at_start, 
            ec.end_count AS active_at_end, 
            ((ec.start_count + ec.end_count) / 2.0) AS average_number_of_employees, 
            t.leavers_count AS employees_who_left, 
            ROUND((t.leavers_count / NULLIF((ec.start_count + ec.end_count) / 2.0, 0)) * 100, 2) AS turnover_rate, 
            ROUND(100 - ((t.leavers_count / NULLIF((ec.start_count + ec.end_count) / 2.0, 0)) * 100), 2) AS retention_rate 
        FROM emp_counts ec CROSS JOIN terminations t;
    """
    status_clause = "WHERE e.status = %(status)s" if status_filter else ""
    attrition_data = frappe.db.sql(attrition_query.format(status_placeholder=status_clause), {"start_date": start_date, "end_date": end_date, "status": status_filter}, as_dict=True)
    att_row = attrition_data[0] if attrition_data else {}

	# ----------------------------------------------------
	# SECTION 8: Rate of Internal Referral Hires (%)
	# ----------------------------------------------------
    start_date = filters.get("from_date")
    end_date = filters.get("to_date")

    referral_query = """
        SELECT 
            COUNT(name) AS total_hires, 
            COALESCE(SUM(CASE WHEN reference_employee_code IS NOT NULL OR reference_employee_name IS NOT NULL THEN 1 ELSE 0 END), 0) AS referral_hires, 
            COALESCE(ROUND((SUM(CASE WHEN reference_employee_code IS NOT NULL OR reference_employee_name IS NOT NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(name), 0)) * 100, 2), 0.0) AS referral_rate 
        FROM 
            `tabEmployee` 
        WHERE 
            date_of_joining BETWEEN %(start_date)s AND %(end_date)s
    """

    referral_data = frappe.db.sql(referral_query, {"start_date": start_date, "end_date": end_date}, as_dict=True)
    ref_row = referral_data[0] if referral_data else {"total_hires": 0, "referral_hires": 0, "referral_rate": 0.0}


    # ----------------------------------------------------
    # Consolidating Data into Report Format
    # ----------------------------------------------------
    att_row = attrition_data[0] if attrition_data else {}
    
    for row in failure_data:
        data.append({
            "hire_year": row.hire_year,
            "hire_month": row.hire_month,
            "total_new_hires": row.total_new_hires,
            "new_hires_left_within_90_days": row.new_hires_left_within_90_days,
            "new_hire_90_day_failure_rate_pct": f"{row.failure_rate}%",
            "average_time_to_fill_days": avg_days_to_fill,
            "turnover_rate_percentage": f"{att_row.get('turnover_rate', 0)}%",
            "retention_rate_percentage": f"{att_row.get('retention_rate', 0)}%",
            "internal_referral_hire_rate": f"{ref_row.get('referral_rate', 0)}%"
        })

    return columns, data

def get_columns():
    return [
        {"fieldname": "hire_year", "label": _("Year"), "fieldtype": "Data", "width": 100},
        {"fieldname": "hire_month", "label": _("Month"), "fieldtype": "Data", "width": 120},
        {"fieldname": "total_new_hires", "label": _("Total New Hires"), "fieldtype": "Int", "width": 130},
        {"fieldname": "new_hires_left_within_90_days", "label": _("Left Within 90 Days"), "fieldtype": "Int", "width": 160},
        {"fieldname": "new_hire_90_day_failure_rate_pct", "label": _("90-Day Failure Rate"), "fieldtype": "Data", "width": 160},
        {"fieldname": "average_time_to_fill_days", "label": _("Avg Time to Fill (Days)"), "fieldtype": "Float", "width": 160},
        {"fieldname": "turnover_rate_percentage", "label": _("Turnover Rate"), "fieldtype": "Data", "width": 160},
        {"fieldname": "retention_rate_percentage", "label": _("Retention Rate"), "fieldtype": "Data", "width": 160},
        {"fieldname": "referral_hires", "label": _("Employee Referral"), "fieldtype": "Data", "width": 180},
        {"fieldname": "internal_referral_hire_rate", "label": _("Internal Referral Hire Rate"), "fieldtype": "Data", "width": 180},
    ]