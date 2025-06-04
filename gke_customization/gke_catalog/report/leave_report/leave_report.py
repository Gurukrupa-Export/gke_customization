import frappe
from frappe import _
from datetime import datetime, timedelta

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    chart = get_chart_data(filters)
    return columns, data, None, chart

def get_columns(filters=None):
    columns = [
        {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 350},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 220},
        {"label": _("Leave Type"), "fieldname": "leave_type", "fieldtype": "Data", "width": 160},
        {"label": _("From Date"), "fieldname": "from_date", "fieldtype": "Date", "width": 130},
        {"label": _("To Date"), "fieldname": "to_date", "fieldtype": "Date", "width": 130},
        {"label": _("Total Days"), "fieldname": "total_leave_days", "fieldtype": "Data", "width": 130},
        {"label": _("Leave Balance"), "fieldname": "leave_balance", "fieldtype": "Data", "width": 130},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": _("Reason"), "fieldname": "remark", "fieldtype": "Data", "width": 260},
        {"label": _("Approver ID"), "fieldname": "leave_approver", "fieldtype": "Data", "width": 200},
        {"label": _("Approver Name"), "fieldname": "leave_approver_name", "fieldtype": "Data", "width": 160},
        {"label": _("Application Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 160}
        
        # {"label": _("EMP Code"), "fieldname": "old_employee_code", "fieldtype": "Data", "width": 100},
        # {"label": _("Punch Id"), "fieldname": "old_punch_id", "fieldtype": "Data", "width": 80},
        # {"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 130},
        # {"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 220},
        # {"label": _("Designation"), "fieldname": "designation", "fieldtype": "Link", "options": "Designation", "width": 170},
        # {"label": _("Grade"), "fieldname": "grade", "fieldtype": "Data", "width": 80},  
        
    ]
    return columns

def get_data(filters):
    conditions = get_conditions(filters)

    query = f"""
    SELECT 
        e.name AS employee,
        e.employee_name,
        e.department,
        la.leave_type,
        la.from_date,
        la.to_date,
        la.leave_balance,
        la.leave_approver,
        la.leave_approver_name,
        la.status,
        la.posting_date,
        la.description AS remark
    FROM `tabLeave Application` la
    LEFT JOIN `tabEmployee` e ON e.name = la.employee
    {conditions}
    ORDER BY la.from_date DESC
    """

    leave_data = frappe.db.sql(query, as_dict=1)
    processed_data = []

    for record in leave_data:
        from_date = frappe.utils.getdate(record.get('from_date'))
        to_date = frappe.utils.getdate(record.get('to_date'))
        total_days = (to_date - from_date).days + 1

        holiday_query = f"""
        SELECT h.holiday_date, h.weekly_off
        FROM `tabHoliday` h
        JOIN `tabHoliday List` hl ON hl.name = h.parent
        WHERE h.holiday_date BETWEEN '{from_date}' AND '{to_date}'
        """
        holidays = frappe.db.sql(holiday_query, as_dict=1)

        sundays_in_range = sum(1 for day in get_date_range(from_date, to_date) if day.weekday() == 6)
        holidays_before_start = sum(1 for holiday in holidays if frappe.utils.getdate(holiday.get('holiday_date')) < from_date and not holiday.get('weekly_off'))

        total_days -= sundays_in_range + holidays_before_start
        total_days = max(total_days, 0)

        record['total_leave_days'] = total_days
        processed_data.append(record)

    return processed_data


def get_date_range(start_date, end_date):
    delta = timedelta(days=1)
    current_date = start_date
    date_list = []

    while current_date <= end_date:
        date_list.append(current_date)
        current_date += delta

    return date_list


def get_chart_data(filters):
    conditions = get_conditions(filters)

    chart_query = f"""
    SELECT 
        e.department AS department,
        COUNT(*) AS leave_count
    FROM `tabLeave Application` la
    LEFT JOIN `tabEmployee` e ON e.name = la.employee
    {conditions}
    GROUP BY e.department
    ORDER BY leave_count DESC
    """
    results = frappe.db.sql(chart_query, as_dict=True)

    if not results:
        return {}

    labels = [row['department'] or 'Unknown' for row in results]
    values = [row['leave_count'] for row in results]

    chart = {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": "Leave Applications",
                    "values": values
                }
            ]
        },
        "type": "bar"
    }

    return chart



def get_conditions(filters):
    filter_list = []

    if filters.get("from_date"):
        filter_list.append(f"""la.from_date >= "{filters.get("from_date")}" """)

    if filters.get("to_date"):
        filter_list.append(f"""la.to_date <= "{filters.get("to_date")}" """)

    if filters.get("employee"):
        employees = ', '.join([f'"{employee}"' for employee in filters.get("employee")])
        filter_list.append(f"""e.employee IN ({employees})""")
        
    if filters.get("status"):
        filter_list.append(f'la.status = "{filters.get("status")}"')
        
    if filters.get("leave_type"):
        filter_list.append(f'la.leave_type = "{filters.get("leave_type")}"')
   
    if filters.get("department"):
        departments = ', '.join([f'"{department}"' for department in filters.get("department")])
        filter_list.append(f"""e.department IN ({departments})""")

    conditions = ""
    if filter_list:
        conditions = "WHERE " + " AND ".join(filter_list)

    return conditions
