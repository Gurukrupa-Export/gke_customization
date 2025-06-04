import frappe
from frappe import _
from datetime import datetime

def execute(filters=None):
    columns = get_columns(filters)
    data, total, left, stayed, attrition_rate, retention_rate = get_data(filters)
    # message = get_message(total, left, stayed, attrition_rate, retention_rate)
    message = None
    report_summary = get_report_summary(total, left, stayed, attrition_rate, retention_rate)
    return columns, data,message,None,report_summary

def get_columns(filters=None):
    return [
        {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Data", "options": "Employee", "width": 190},
        {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 220},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Data", "width": 250},
        {"label": _("Date of Joining"), "fieldname": "date_of_joining", "fieldtype": "Date", "width": 160},
        {"label": _("Relieving Date"), "fieldname": "last_working_day", "fieldtype": "HTML", "width": 170},
        # {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
        {"label": _("Tenure"), "fieldname": "tenure_years", "fieldtype": "Data", "width": 120},
    ]

def get_data(filters):
    from_date = datetime.strptime(filters.get("from_date"), "%Y-%m-%d").date() if filters.get("from_date") else None
    to_date = datetime.strptime(filters.get("to_date"), "%Y-%m-%d").date() if filters.get("to_date") else None
    department = filters.get("department")
    status_filter = filters.get("status")

    emp_filters = {"date_of_joining": ("<=", to_date)}
    if status_filter:
        emp_filters["status"] = status_filter

    employees = frappe.get_all("Employee",
        fields=["name", "employee_name", "date_of_joining", "relieving_date", "department", "status", "modified"],
        filters=emp_filters
    )

    employees = [e for e in employees if not e["relieving_date"] or e["relieving_date"] >= from_date]
    
    if department:
        employees = [e for e in employees if e["department"] in department]

    data = []
    total = left = stayed = 0
    employees.sort(key=lambda e: e["date_of_joining"])

    for emp in employees:
        doj = emp["date_of_joining"]
        rd = emp["relieving_date"]
        total += 1

        if rd and from_date <= rd <= to_date:
            left += 1
        elif not rd or rd > to_date:
            stayed += 1

        status_value = emp["status"].lower()
        if rd:
            end_date = rd
        elif status_value in ["inactive", "left", "suspended"]:
            end_date = emp["modified"].date()
        else:
            end_date = datetime.today().date()

        tenure = round((end_date - doj).days / 365.25, 1)
        tenure_display = f"{int(round(tenure * 12))} months" if tenure < 1 else f"{tenure:.1f} yrs"
        resign_display = f"<span style='color: red;'>{rd}</span>" if rd and from_date <= rd <= to_date else ""

        status_display = f"<span style='color: red;'>{emp['status']}</span>" if status_value in ["inactive", "left", "suspended"] else emp["status"]
        emp_link = f'<a href="http://192.168.200.207:8001/app/employee/{emp["name"]}" target="_blank">{emp["name"]}</a>'

        data.append({
            "employee": emp_link,
            "employee_name": emp["employee_name"],
            "date_of_joining": doj,
            "last_working_day": resign_display,
            "department": emp["department"],
            "status": status_display,
            "tenure_years": tenure_display
        })

    attrition_rate = (left / total * 100) if total else 0
    retention_rate = (stayed / total * 100) if total else 0

    
    data.append({
        "employee": f"<b><span style='color: blue;'>Total Employees: {total}</span></b>",
        "status": f"<b><span style='color: green;'>Retention Rate:</span></b>",
        "tenure_years": f"<b><span style='color: green;'>{retention_rate:.2f} % </span></b>",
        "last_working_day": f"<b><span style='color: green;'>Total Stayed: {stayed}</span></b>",
    })
    data.append({
        "status": f"<b><span style='color: red;'>Attrition Rate:</span></b>",
        "tenure_years": f"<b><span style='color: red;'>{attrition_rate:.2f} % </span></b>",
        "last_working_day": f"<b><span style='color: red;'>Total Left: {left}</span></b>",
    })

    return data, total, left, stayed, attrition_rate, retention_rate

def get_message(total, left, stayed, attrition_rate, retention_rate):
    return f"""
    <div style="font-size: 14px; font-weight: bold; margin-bottom: 10px;">
        <span class="indicator blue">Total Employees: {total}</span>&nbsp;&nbsp;&nbsp;
        <span class="indicator green">Retention Rate: {retention_rate:.2f}%</span>&nbsp;&nbsp;&nbsp;
         <span class="indicator red">Attrition Rate: {attrition_rate:.2f}%</span>&nbsp;&nbsp;&nbsp;
        <span class="indicator green">Total Stayed: {stayed}</span>&nbsp;
         <span class="indicator red">Total Left: {left}</span>&nbsp;&nbsp;&nbsp;
    </div>
    """
def get_report_summary(total, left, stayed, attrition_rate, retention_rate):
	return [
		{
			"value": total,
			"indicator": "Blue",
			"label": "Total Employees",
			"datatype": "Int",
		},
		{
			"value": retention_rate,
			"indicator": "Green" if retention_rate >= 70 else "Orange",
			"label": "Retention Rate",
			"datatype": "Percent",
		},
		{
			"value": attrition_rate,
			"indicator": "Red",
			"label": "Attrition Rate",
			"datatype": "Percent",
		},
		{
			"value": stayed,
			"indicator": "Green",
			"label": "Stayed",
			"datatype": "Int",
		},
		{
			"value": left,
			"indicator": "Red" if left > 0 else "Green",
			"label": "Left",
			"datatype": "Int",
		},
	]

