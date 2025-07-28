import frappe
from frappe import _
from datetime import datetime, timedelta

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": "Emp ID", "fieldname": "emp_id", "fieldtype": "Data", "width": 160},
        {"label": "Emp Name", "fieldname": "emp_name", "fieldtype": "Data", "width": 220},
        {"label": "Date", "fieldname": "date", "fieldtype": "Date", "width": 120},
        {"label": "OT/OD", "fieldname": "ot_od", "fieldtype": "Data", "width": 80},
        {"label": "Shift Start", "fieldname": "start_time", "fieldtype": "Time", "width": 100},
        {"label": "Shift End", "fieldname": "end_time", "fieldtype": "Time", "width": 100},
        {"label": "Total OT", "fieldname": "total_ot", "fieldtype": "Data", "width": 100},
        {"label": "OD Start", "fieldname": "od_start_time", "fieldtype": "Time", "width": 100},
        {"label": "OD End", "fieldname": "od_end_time", "fieldtype": "Time", "width": 100},
        {"label": "Total OD", "fieldname": "total_od", "fieldtype": "Data", "width": 100},
    ]

def get_data(filters):
    data_map = {}
    employee_id = filters.get("employee")
    month = filters.get("month")
    year = filters.get("year")
    company = filters.get("company")
    branch = filters.get("branch") or []
    department = filters.get("department") or []

    month_number = datetime.strptime(month, "%B").month if month else None
    year_number = int(year) if year else None

    if month_number and year_number:
        from_date = datetime(year_number, month_number, 1)
        to_date = (from_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    else:
        from_date = to_date = None

    employee_filters = {}
    if company:
        employee_filters["company"] = company
    if branch:
        employee_filters["branch"] = ["in", branch]
    if department:
        employee_filters["department"] = ["in", department]

    employees = frappe.get_all("Employee", fields=["name", "employee_name", "default_shift"], filters=employee_filters)

    for emp in employees:
        if employee_id and emp.name != employee_id:
            continue

        if not emp.default_shift or " TO " not in emp.default_shift:
            continue

        shift_parts = emp.default_shift.split(" TO ")
        shift_end_str = shift_parts[1].split(" ")[0].strip()
        try:
            shift_end = datetime.strptime(shift_end_str, "%H:%M").time()
        except ValueError:
            continue

        checkins = frappe.get_all("Employee Checkin", fields=["time"], filters={
            "employee": emp.name,
            "log_type": "OUT",
            "time": ["between", [from_date, to_date]] if from_date and to_date else ["!=", None]
        }, order_by="time asc")

        for checkin in checkins:
            checkin_time = checkin.time.time()
            total_minutes = (checkin_time.hour * 60 + checkin_time.minute) - (shift_end.hour * 60 + shift_end.minute)
            if total_minutes < 30:
                continue

            key = (emp.name, checkin.time.date())
            data_map[key] = {
                "emp_id": emp.name,
                "emp_name": emp.employee_name,
                "ot_od": "OT",
                "start_time": shift_end.strftime("%H:%M"),
                "end_time": checkin_time.strftime("%H:%M"),
                "total_ot": f"{total_minutes // 60:02}:{total_minutes % 60:02}",
                "od_start_time": None,
                "od_end_time": None,
                "total_od": None,
                "date": checkin.time.date()
            }

    od_filters = {"docstatus": 1}
    if company:
        od_filters["company"] = company
    if from_date and to_date:
        od_filters["from_date"] = ["<=", to_date]
        od_filters["to_date"] = [">=", from_date]

    od_requests = frappe.get_all("Attendance Request", fields=["name", "employee", "from_date", "to_date", "custom_out_time"], filters=od_filters)
    for od in od_requests:
        emp = frappe.get_doc("Employee", od.employee)
        if branch and emp.branch not in branch:
            continue
        if department and emp.department not in department:
            continue
        if employee_id and od.employee != employee_id:
            continue

        if not emp.default_shift or " TO " not in emp.default_shift:
            continue

        shift_parts = emp.default_shift.split(" TO ")
        shift_end_str = shift_parts[1].split(" ")[0].strip()
        try:
            shift_end = datetime.strptime(shift_end_str, "%H:%M")
        except ValueError:
            continue

        try:
            od_end_time = datetime.strptime(str(od.custom_out_time), "%H:%M:%S").time()
        except ValueError:
            continue

        total_minutes = (od_end_time.hour * 60 + od_end_time.minute) - (shift_end.hour * 60 + shift_end.minute)
        if total_minutes < 30:
            continue

        current_date = od.from_date
        while current_date <= od.to_date:
            key = (od.employee, current_date)
            if key not in data_map:
                data_map[key] = {
                    "emp_id": od.employee,
                    "emp_name": emp.employee_name,
                    "ot_od": "OD",
                    "start_time": None,
                    "end_time": None,
                    "total_ot": None,
                    "od_start_time": shift_end.strftime("%H:%M"),
                    "od_end_time": od_end_time.strftime("%H:%M"),
                    "total_od": f"{total_minutes // 60:02}:{total_minutes % 60:02}",
                    "date": current_date
                }
            else:
                data_map[key]["ot_od"] = "OT/OD"
                data_map[key]["od_start_time"] = shift_end.strftime("%H:%M")
                data_map[key]["od_end_time"] = od_end_time.strftime("%H:%M")
                data_map[key]["total_od"] = f"{total_minutes // 60:02}:{total_minutes % 60:02}"
            current_date += timedelta(days=1)

    data = list(data_map.values())
    data.sort(key=lambda x: (x["emp_id"], x["date"]), reverse=False)

    total_employees = len({row["emp_id"] for row in data})
    data.append({
        "emp_id": "",
        "emp_name": f"<span style='color: #c9828f; font-weight: bold;'>Total Employees: {total_employees}</span>",
        "date": "",
        "ot_od": "",
        "start_time": "",
        "end_time": "",
        "total_ot": "",
        "od_start_time": "",
        "od_end_time": "",
        "total_od": ""
    })
    return data
