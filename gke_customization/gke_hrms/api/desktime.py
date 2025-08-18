from frappe.utils import cint, add_to_date, get_datetime, get_datetime_str, now
from datetime import datetime, timedelta
import frappe
import requests

@frappe.whitelist()
def get_desktime_detail(date=None):
    today_date = datetime.now().date()
    formatted_date = today_date.strftime("%Y-%m-%d")

    apiKey = "2ebf1bad1d730527759fac0807b29708"
    date = date or formatted_date
    period = frappe.form_dict.get("period") or "day"
    user_id = user_id

    allowed_users = ["bhavika_p@gkexport.com", "hjr@gkexport.com", "vishalrajput@gkexport.com"]

    if user_id not in allowed_users:
        frappe.response["message"] = {"error": "Access denied. Only guest users can fetch DeskTime API."}
        return
    
    url = "https://desktime.com/api/v2/json/employees"
    params = {
        "apiKey": apiKey,
        "date": date,
        "period": period
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        employees_list = list(data.get("employees", {}).get(date, {}).values())

        # Add calculated fields to each employee
        for emp in employees_list:
            productive_time = emp.get("productiveTime", 0)
            expected_work_time = emp.get("expectedWorkTime", 28800)  # default 8h = 28800s
            at_work_time = emp.get("atWorkTime", 0)
            desktime_time = emp.get("desktimeTime", 0)

            emp["effectivenessPercentage"] = calculate_effectiveness(productive_time, expected_work_time)
            emp["lateTime"] = calculate_late_time(emp.get("arrived"), emp.get("work_starts"))
            emp["idleTime"] = calculate_idle_time(at_work_time, desktime_time)

        totals = get_total(employees_list)
        metric_sections = get_metric_sections(employees_list)

        frappe.response["message"] = {
            "totals": totals,
            "metricSections": metric_sections,
            "data": data
        }

    except requests.exceptions.RequestException as e:
        frappe.response["message"] = {"error": str(e)}


def calculate_effectiveness(productive_time, expected_work_time=28800):
    if expected_work_time == 0:
        return 0
    return round((productive_time / expected_work_time) * 100, 1)


def calculate_late_time(arrived, work_starts):
    if not arrived or arrived is False:
        return None
    
    try:
        arrived_time_str = arrived.split(" ")[1] if " " in arrived else arrived
        arrived_time = datetime.strptime(arrived_time_str, "%H:%M:%S")
        expected_time = datetime.strptime(work_starts, "%H:%M:%S")
        
        if arrived_time > expected_time:
            diff_seconds = int((arrived_time - expected_time).total_seconds())
            return seconds_to_hms(diff_seconds)
    except Exception:
        return None
    
    return None


def calculate_idle_time(at_work_time, desktime_time):
    idle_seconds = max(0, at_work_time - desktime_time)
    return seconds_to_hms(idle_seconds)


def seconds_to_hms(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02}:{minutes:02}:{secs:02}"


def get_total(employees_list):
    totalEmployees = len(employees_list)
    onlineEmployees = sum(1 for emp in employees_list if emp.get("isOnline"))
    lateEmployees = sum(1 for emp in employees_list if emp.get("late"))
    absentEmployees = sum(1 for emp in employees_list if not emp.get("arrived"))
    
    productivity_sum = sum(emp.get("productivity", 0) for emp in employees_list)
    avg_productivity = (productivity_sum / totalEmployees) if totalEmployees else 0

    total_hours = sum(emp.get("desktimeTime", 0) for emp in employees_list)

    return {
        "totalEmployees": totalEmployees,
        "onlineEmployees": onlineEmployees,
        "lateEmployees": lateEmployees,
        "absentEmployees": absentEmployees,
        "avg_productivity": round(avg_productivity, 1),
        "total_hours": round(total_hours / 3600)
    }


def get_top_employees(employees, sort_by, limit=5):
    if sort_by == "productive":
        filtered = [e for e in employees if e.get("productivity", 0) > 0]
    elif sort_by == "unproductive":
        filtered = [e for e in employees if e.get("productivity", 0) >= 0 and e.get("desktimeTime", 0) > 0]
    elif sort_by == "effective":
        filtered = [e for e in employees if e.get("effectivenessPercentage", 0) > 0]
    elif sort_by == "desktime":
        filtered = [e for e in employees if e.get("desktimeTime", 0) > 0]
    elif sort_by == "late":
        filtered = [e for e in employees if e.get("late") and e.get("lateTime")]
    elif sort_by == "absent":
        filtered = [e for e in employees if not e.get("arrived")]
    elif sort_by == "idle":
        filtered = [e for e in employees if e.get("atWorkTime", 0) > e.get("desktimeTime", 0)]
    else:
        filtered = employees

    if sort_by == "productive":
        filtered.sort(key=lambda e: e.get("productivity", 0), reverse=True)
    elif sort_by == "unproductive":
        filtered.sort(key=lambda e: e.get("productivity", 0))
    elif sort_by == "effective":
        filtered.sort(key=lambda e: e.get("effectivenessPercentage", 0), reverse=True)
    elif sort_by == "desktime":
        filtered.sort(key=lambda e: e.get("desktimeTime", 0), reverse=True)
    elif sort_by in ["late", "idle"]:
        filtered.sort(key=lambda e: (e.get("atWorkTime", 0) - e.get("desktimeTime", 0)), reverse=True)

    return filtered[:limit]


def get_metric_sections(employees):
    return [
        {"title": "Most Productive", "employees": get_top_employees(employees, "productive"), "metricType": "productivity"},
        {"title": "Most Unproductive", "employees": get_top_employees(employees, "unproductive"), "metricType": "productivity", "emptyMessage": "No unproductive employees found"},
        {"title": "Most Effective", "employees": get_top_employees(employees, "effective"), "metricType": "effectiveness"},
        {"title": "Total DeskTime", "employees": get_top_employees(employees, "desktime"), "metricType": "desktime"},
        {"title": "Late Arrivals", "employees": get_top_employees(employees, "late"), "metricType": "late", "emptyMessage": "No late arrivals today"},
        {"title": "Most Idle Time", "employees": get_top_employees(employees, "idle"), "metricType": "idle", "emptyMessage": "No idle time tracked"}
    ]
