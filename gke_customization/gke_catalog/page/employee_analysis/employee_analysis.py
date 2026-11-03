import frappe
from frappe import _
import datetime

@frappe.whitelist()
def get_employee_details(employee):
    """
    Whitelisted route endpoint. Pulls employee profile metrics, computes 
    real-time corporate tenure, and returns a unified career timeline, 
    performance appraisals, leave utilization, and attendance trends dataset.
    """
    if not employee:
        return None

    # --- PART 1: Query Primary Snapshot Fields ---
    fields = [
        "name",
        "employee_name", 
        "designation", 
        "department", 
        "custom_city", 
        "custom_state", 
        "status", 
        "date_of_joining",
        "reporting_employee_name_",  
        "reports_to",                
        "payroll_cost_center",      
        "branch", 
        "grade",                     
        "ctc"                   
    ]
    
    emp_doc = frappe.db.get_value("Employee", employee, fields, as_dict=True)

    if not emp_doc:
        return None
    
    lang_records = frappe.db.get_all(
        "Employee Languages", 
        filters={"parent": employee, "parenttype": "Employee"}, 
        fields=["language"]
    )
    
    # Process the list carefully using standard dictionary get() method
    languages_list = []
    for row in lang_records:
        if row.get("language"):
            languages_list.append(str(row.get("language")))

    # Combine them with commas, or fall back to '-' if empty
    emp_doc["language"] = ", ".join(languages_list) if languages_list else "-"

    # Handle SQL location string consolidation maps cleanly
    city = emp_doc.get("custom_city")
    state = emp_doc.get("custom_state")
    if city and state:
        emp_doc["location"] = f"{city}, {state}"
    else:
        emp_doc["location"] = city or state or "-"

    # --- PART 2: Robust Tenure Calculation Block ---
    tenure_str = "0 Mos"
    date_of_joining = emp_doc.get("date_of_joining")
    
    if date_of_joining:
        try:
            doj = frappe.utils.getdate(date_of_joining)
            today_date = frappe.utils.getdate()
            diff = frappe.utils.date_diff(today_date, doj)
            
            if diff >= 0:
                years = diff // 365
                months = (diff % 365) // 30
                
                if years > 0:
                    tenure_str = f"{years}y {months}m"
                else:
                    tenure_str = f"{months}m"
            else:
                tenure_str = "0 Mos"
        except Exception:
            tenure_str = "Calculation Error"
    else:
        tenure_str = "DOJ Not Configured"

    emp_doc["tenure"] = tenure_str

    # --- PART 3: Section 5 Performance Overview Query ---
    perf_query = """
        SELECT 
            a.name AS appraisal_id,
            IFNULL(a.start_date, a.creation) AS evaluation_date,
            IFNULL(a.total_score, 0) AS performance_score,
            IFNULL(a.final_score, 0) AS performance_rating,
            CASE 
                WHEN a.final_score >= 4.5 OR a.total_score >= 90 THEN 1 
                ELSE 0 
            END AS high_potential_indicator,
            IFNULL(a.remarks, 'No remarks provided.') AS feedback
        FROM 
            `tabAppraisal` a
        WHERE 
            a.employee = %(employee)s OR a.employee_name = %(employee)s
        ORDER BY 
            evaluation_date ASC;
    """
    performance_overview = frappe.db.sql(perf_query, {"employee": employee}, as_dict=True)

    # --- PART 4: Parameterized SQL Career Timeline Query ---
    timeline_query = """
        SELECT 
            e.name AS employee_id, 
            e.employee_name, 
            'Hired / Profile Setup' AS event_type,
            e.date_of_joining AS event_date, 
            e.company, 
            e.department, 
            e.branch,
            e.designation, 
            e.grade,
            IFNULL(e.ctc, 0.00) AS salary, 
            (SELECT GROUP_CONCAT(lang.language SEPARATOR ', ') 
             FROM `tabEmployee Languages` lang 
             WHERE lang.parent = e.name AND lang.parenttype = 'Employee') AS language,
            e.date_of_joining AS revision_date
        FROM `tabEmployee` e 
        WHERE e.name = %(employee)s
        UNION ALL
        SELECT 
            p.employee AS employee_id, 
            p.employee_name, 'Promotion' AS event_type,
            p.promotion_date AS event_date, 
            p.company, 
            p.department, 
            emp.branch,
            NULL AS designation, 
            NULL AS grade,
            IFNULL(p.revised_ctc, 0.00) AS salary, 
            NULL as language,
            p.promotion_date AS revision_date
        FROM `tabEmployee Promotion` p 
        INNER JOIN `tabEmployee` emp ON p.employee = emp.employee
        WHERE p.docstatus = 1 AND p.employee = %(employee)s
        
        UNION ALL
          SELECT 
            t.employee AS employee_id, 
            t.employee_name, 
            CASE 
                WHEN t.company IS NOT NULL AND t.company != '' AND t.company != emp.company THEN 'Company Transfer'
                WHEN emp.branch IS NOT NULL AND emp.branch != '' AND emp.branch != emp.branch THEN 'Branch Transfer'
                ELSE 'Department Transfer'
            END AS event_type,
            t.transfer_date AS event_date, 
            -- CORRECTED: If transfer company is empty, fallback to the main Employee master company
            IFNULL(NULLIF(t.company, ''), emp.company) AS company, 
            IFNULL(NULLIF(t.department, ''), t.department) AS department, 
            IFNULL(NULLIF(emp.branch, ''), emp.branch) AS branch,
            NULL AS designation, 
            NULL AS grade,
            NULL AS salary, 
            NULL AS language,
            t.transfer_date AS revision_date
        FROM `tabEmployee Transfer` t
        INNER JOIN `tabEmployee` emp ON t.employee = emp.employee
        WHERE t.docstatus = 1 AND t.employee = %(employee)s
    """
    timeline_events = frappe.db.sql(timeline_query, {"employee": employee}, as_dict=True)
    
    current_year = datetime.datetime.now().year
    start_year = current_year - 2  # Includes current year and previous 2 years
    
   # --- PART 5: Leave Utilization Query (Fixed Balance Pulling) ---
    leave_query = """ 
        SELECT 
            la.leave_type, 
            IFNULL(SUM(la.total_leave_days), 0.00) AS total_utilized 
        FROM `tabLeave Application` la 
        WHERE la.status = 'Approved' 
        AND la.employee = %(employee)s
        AND YEAR(la.from_date) >= %(start_year)s
        GROUP BY la.leave_type; 
    """
    leave_summary = frappe.db.sql(leave_query, {"employee": employee, "start_year": start_year}, as_dict=True)

# --- PART 6: Monthly Attendance Query (Filtered for 3 Years) ---
    attendance_query = """ 
        SELECT 
            YEAR(att.attendance_date) AS att_year,
            DATE_FORMAT(att.attendance_date, '%%b') AS att_month_name,
            MONTH(att.attendance_date) AS att_month_num,
            SUM(CASE WHEN att.status = 'Present' THEN 1 ELSE 0 END) AS total_present,
            SUM(CASE WHEN att.status = 'Absent' THEN 1 ELSE 0 END) AS total_absent,
            COUNT(att.name) AS total_working_days 
        FROM `tabAttendance` att 
        WHERE att.employee = %(employee)s 
        AND YEAR(att.attendance_date) >= %(start_year)s
        GROUP BY YEAR(att.attendance_date), MONTH(att.attendance_date) 
        ORDER BY YEAR(att.attendance_date) ASC, MONTH(att.attendance_date) ASC; 
    """
    attendance_trends = frappe.db.sql(attendance_query, {"employee": employee, "start_year": start_year}, as_dict=True)

# --- PART 7: Absenteeism Rate Calculation ---
    total_absences = sum([row.get('total_absent', 0) for row in attendance_trends])
    total_periods = sum([row.get('total_working_days', 0) for row in attendance_trends])
    absenteeism_pct = 0.00
    if total_periods > 0:
        absenteeism_pct = round((total_absences / total_periods) * 100, 2)

    exit_query = """
        SELECT 
            date_resignation, 
            reason_for_resignation, 
            status 
        FROM 
            `tabEmployee Resignation` 
        WHERE 
            employee = %(employee)s 
            and reporting_manager_approval = 'Approved'
        ORDER BY 
            date_resignation ASC 
        LIMIT 100;
    """
    exit_information = frappe.db.sql(exit_query, {"employee": employee}, as_dict=True)
    
    # --- PART 8: Unified Combined Return ---
    return {
        "profile": emp_doc,
        "timeline": timeline_events,
        "compensation": timeline_events,  
        "performance_overview": performance_overview,
        "leave_summary": leave_summary,
        "attendance_trends": attendance_trends,
        "absenteeism_percentage": absenteeism_pct,
        "exit_information": exit_information
    }
