# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import timedelta, datetime
from frappe.utils import flt, getdate, add_days, format_time, today, add_to_date, get_time
import frappe.utils

STATUS = {
	"Absent" : "A",
	"Present" : "P",
	"Half Day" : "HD",
	"Paid Leave" : "PL",
	"Casual Leave" : "CL",
	"Sick Leave" : "SL",
	"Leave Without Pay" : "LWP",
	"Outdoor Duty" : "OD",
	"Maternity Leave" : "ML",
}

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

def get_data(filters=None):
	conditions = get_conditions(filters)
	
	data = frappe.db.sql(f"""SELECT attendance_date,in_time,spent_hours,status,adj_out,adj_spent_hour,rand_int,late_entry,
			TIME_FORMAT(ADDTIME(adj_out,SEC_TO_TIME(rand_int * 60)), "%H:%i" ) AS adj_out_2,
			TIMEDIFF(TIME_FORMAT(ADDTIME(adj_out,SEC_TO_TIME(rand_int * 60) ), "%H:%i" ) , in_time) as total_adj
		FROM (
			SELECT at.attendance_date AS attendance_date, at.late_entry as late_entry,
				TIME_FORMAT(at.in_time, "%H:%i") AS in_time, 
				TIME_FORMAT(SEC_TO_TIME(at.working_hours * 3600), "%H:%i") AS spent_hours,
				IFNULL(at.leave_type, at.status) AS status,
				TIME_FORMAT( 
					IF(TIMESTAMPDIFF(HOUR, at.in_time, at.out_time) >= 9, DATE_ADD(at.in_time, INTERVAL 9 HOUR),at.out_time), "%H:%i"
				) AS adj_out,
				TIME_FORMAT( 
					TIMEDIFF( IF(TIMESTAMPDIFF(HOUR, at.in_time, at.out_time) >= 9, DATE_ADD(at.in_time, INTERVAL 9 HOUR), at.out_time ), at.in_time), "%H:%i"
				) AS adj_spent_hour,
				FLOOR(RAND() * 10) AS rand_int
			FROM 
				`tabAttendance` at 
				LEFT JOIN `tabEmployee` emp ON at.employee = emp.name 
				LEFT JOIN `tabShift Type` st ON emp.default_shift = st.name 
				LEFT JOIN (
					SELECT employee, date, SEC_TO_TIME(SUM(TIME_TO_SEC(total_hours))) AS hrs 
					FROM `tabPersonal Out Log` 
					WHERE is_cancelled = 0 
					GROUP BY employee, date
				) pol ON at.attendance_date = pol.date AND at.employee = pol.employee 
				LEFT JOIN (
					SELECT * FROM `tabOT Log` WHERE is_cancelled = 0
				) ot ON at.attendance_date = ot.attendance_date AND at.employee = ot.employee
			WHERE at.docstatus = 1 {conditions} ) AS subquery
			ORDER BY attendance_date ASC;  
	""",as_dict=1)				  
	
	
	if not data:
		return

	data = process_data(data, filters)
	totals = get_totals(data, filters.get("employee"))
	data += totals

	return data

def process_data(data, filters):
	employee = filters.get("employee")
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	processed = {}
	result = []
	holidays = []
	wo = []
	emp_det = frappe.db.get_value("Employee", employee, ["default_shift","holiday_list","date_of_joining"], as_dict=1)
	shift = emp_det.get("default_shift")
	shift_det = frappe.db.get_value("Shift Type", shift, ['shift_hours','holiday_list','start_time', 'end_time'], as_dict=1)

	shift_hours = flt(shift_det.get("shift_hours"))
	shift_name = f"{format_time(shift_det.get('start_time'))} To {format_time(shift_det.get('end_time'))}"

	checkins = frappe.db.sql(f"""select date(time) as login_date, attendance, count(name) as cnt from `tabEmployee Checkin`
			  where time between '{from_date}' and '{add_days(to_date,1)}' and employee = '{employee}' group by attendance""", as_dict=1)
	
	checkins = {row.login_date: row.cnt for row in checkins}
	od = frappe.get_list("Employee Checkin",{'employee':employee,'source':"Outdoor Duty", "time": ['between',[from_date,add_days(to_date,1)]]},'date(time) as login_date', pluck='login_date',group_by='login_date')

	if shift and not emp_det.get('holiday_list'):
			emp_det['holiday_list'] = shift_det.get("holiday_list")
	
	if hl_name:=emp_det.get('holiday_list'):
		holidays = frappe.get_list("Holiday", {"parent": hl_name,
					"holiday_date":["between",[from_date, to_date]]}, ["holiday_date","weekly_off"], ignore_permissions=1)
		wo = [row.holiday_date for row in holidays if row.weekly_off]
		holidays = [row.holiday_date for row in holidays if not row.weekly_off]
	
	for row in data:
		if row.status in 'Present':
			row.status = 'P'
		if row.status in 'Absent':
			row.status = 'A'
		
		processed[row.attendance_date] = row	
	
	ot_for_wo = frappe.get_all("OT Log", {"employee":employee,"attendance_date": ["between",[from_date,to_date]], "is_cancelled":0}, ["attendance_date","allowed_ot as ot_hours", "first_in as in_time", "last_out as out_time"])
	ot_for_wo = {row.attendance_date: row for row in ot_for_wo}
	date_range = get_date_range(from_date, to_date)


	for date in date_range:
		row = processed.get(date,ot_for_wo.get(date,{}))		

		if date in od:			
			row["status"] = "OD"

		elif date in wo and (date >= getdate(emp_det.get("date_of_joining"))):
			status = "WO"

		elif (date in holidays) and (date >= getdate(emp_det.get("date_of_joining"))):
			status = "H"
			
		else:
			status = "XX"
		temp = { 
			"attendance_date": date,
			"status": status
		}
		temp.update(row)
		result.append(temp)

	# frappe.throw(f"{result}")
	return result

def get_totals(data, employee):    
    totals = {
        "adj_out_2": "Total Hours",
        "total_adj": timedelta(0),
    }
    late_count = 0

    for row in data:
        total_adj_str = row.get("total_adj") or "00:00"
        total_adj_timedelta = str_to_timedelta(total_adj_str)
        totals["total_adj"] += total_adj_timedelta

        if row.get("late_entry"):
            late_count += 1

    # Calculate net days based on 9 hours per day
    total_hours = totals["total_adj"].total_seconds() / 3600
    hours_per_day = 9
    net_days = total_hours / hours_per_day

    # Prepare the total_adj_days dictionary
    total_adj_days = {
        "adj_out_2": "Net Days",
        "total_adj": round(net_days, 2)
    }

    return totals, total_adj_days

def get_columns(filters=None):
	columns = [
		{
			"label": _("Attendance Date"),
			"fieldname": "attendance_date",
			"fieldtype": "Data",
			"width": 250
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("Late Entry"),
			"fieldname": "late_entry",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("In Time"),
			"fieldname": "in_time",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("Out Time"),
			"fieldname": "adj_out_2",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("Total Spent Hours"),
			"fieldname": "total_adj",
			"fieldtype": "Data",
			"width": 250
		},
		# {
		# 	"label": _("rand_int"),
		# 	"fieldname": "rand_int",
		# 	"fieldtype": "Data",
		# 	"width": 120
		# },
		
		# {
		# 	"label": _(""),
		# 	"fieldname": "",
		# 	"fieldtype": ""
		# },
	]
	return columns

def get_conditions(filters):
	if not (filters.get("from_date") and filters.get("to_date")):
		frappe.throw("From & To Dates are mandatory")
	conditions = f"""and (at.attendance_date Between '{filters.get("from_date")}' AND '{filters.get("to_date")}')"""
	
	if filters.get("employee"):
		conditions += f"""and at.employee = '{filters.get("employee")}'"""
		return conditions
	

def get_date_range(start_date, end_date):
	import datetime
	start_date = getdate(start_date)
	end_date = getdate(end_date)

	range = []
	delta = datetime.timedelta(days=1)
	current_date = start_date

	while current_date <= end_date:
		range.append(current_date)
		current_date += delta

	return range

@frappe.whitelist()
def get_month_range():
	from frappe.utils.dateutils import get_dates_from_timegrain, get_period
	end = today()
	start = add_to_date(end, months=-12)
	periodic_range = get_dates_from_timegrain(start, end, "Monthly")
	periods = [get_period(row) for row in periodic_range]
	periods.reverse()
	return periods

def str_to_timedelta(time_str):
	time_str = str(time_str)
	if len(str(time_str).split(':'))==2:
		hours, minutes = map(int, time_str.split(':'))
	elif len(str(time_str).split(':'))==3:
		hours, minutes, seconds = map(int, time_str.split(':'))
	return timedelta(hours=hours, minutes=minutes)