import frappe
from frappe import _
from datetime import timedelta, datetime
from frappe.utils import flt, getdate, add_days, format_time, today, add_to_date, get_time
import frappe.utils
from gurukrupa_customizations.gurukrupa_customizations.doctype.manual_punch.manual_punch import get_checkins

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

@frappe.whitelist(allow_guest=True)
def attendance(from_date = None,to_date = None,employee = None):
	conditions = get_conditions(from_date,to_date,employee) 
	if conditions:
		data = frappe.db.sql(f"""
            SELECT 
				at.employee,
                at.employee_name, at.company, at.department,at.working_hours,
                emp.allowed_personal_hours, emp.designation, emp.old_punch_id,
                emp.middle_name, emp.gender, emp.date_of_birth, emp.date_of_joining, emp.holiday_list,
			at.attendance_date,
			CONCAT(TIME_FORMAT(st.start_time, "%H:%i:%s"), " TO ", TIME_FORMAT(st.end_time, "%H:%i:%s")) AS shift, 
			TIME(at.in_time) AS in_time, 
			TIME(at.out_time) AS out_time, 
			TIMEDIFF(at.out_time, at.in_time) AS spent_hours, 
			at.late_entry, 
			IF(at.late_entry, TIMEDIFF(TIME(at.in_time), st.start_time), NULL) AS late_hrs,
			IF(at.early_exit, TIMEDIFF(st.end_time, TIME(at.out_time)), NULL) AS early_hrs, 
			pol.hrs AS p_out_hrs, 
			SEC_TO_TIME(
				IF((at.attendance_request IS NOT NULL OR (at.status = "On Leave" AND at.leave_type IN (SELECT name FROM `tabLeave Type` WHERE is_lwp = 0))),
					st.shift_hours,
					IF(at.out_time, TIME_TO_SEC(TIMEDIFF(at.out_time, at.in_time)), at.working_hours * 3600))
					+ IF(at.late_entry = 0 AND TIME(at.in_time) > TIME(st.start_time),
							TIME_TO_SEC(TIMEDIFF(TIME(at.in_time), st.start_time)), 0)
					- IF(TIME(at.in_time) < TIME(st.start_time),
							TIME_TO_SEC(TIMEDIFF(st.start_time, TIME(at.in_time))), 0)
					- IF(at.out_time > TIMESTAMP(DATE(at.in_time), st.end_time),
							TIME_TO_SEC(TIMEDIFF(at.out_time, TIMESTAMP(DATE(at.in_time), st.end_time))), 0)
					- IFNULL(TIME_TO_SEC(pol.hrs), 0)
					+ (SELECT IFNULL(SUM(TIME_TO_SEC(pl.total_hours)), 0) FROM `tabPersonal Out Log` pl 
						WHERE pl.is_cancelled = 0 AND pl.employee = at.employee AND pl.date = at.attendance_date AND pl.out_time >= st.end_time)
				) AS net_wrk_hrs,
			st.shift_hours, 
			IF(st.working_hours_threshold_for_half_day > at.working_hours AND at.working_hours > 0, 1, 0) AS lh,
			ot.ot_hours AS ot_hours, 
			IFNULL(at.leave_type, at.status) AS status, 
			at.attendance_request
		FROM 
			`tabAttendance` at 
		LEFT JOIN 
			`tabEmployee` emp ON at.employee = emp.name 
		LEFT JOIN 
			`tabShift Type` st ON emp.default_shift = st.name 
		LEFT JOIN 
			(SELECT employee, date, SEC_TO_TIME(SUM(TIME_TO_SEC(total_hours))) AS hrs 
			FROM `tabPersonal Out Log` 
			WHERE is_cancelled = 0 
			GROUP BY employee, date) pol ON at.attendance_date = pol.date AND at.employee = pol.employee 
		LEFT JOIN 
			(SELECT employee, attendance_date, SEC_TO_TIME(SUM(TIME_TO_SEC(allowed_ot))) AS ot_hours 
			FROM `tabOT Log` 
			WHERE is_cancelled = 0 
			GROUP BY employee, attendance_date) ot ON at.attendance_date = ot.attendance_date AND at.employee = ot.employee
		WHERE 
			at.docstatus = 1 
					  {conditions}
		ORDER BY 
			at.attendance_date ASC;
            """, as_dict=True)
		data = process_data(data,from_date,to_date,employee)
	
	return data
    
  
def get_conditions(from_date,to_date,employee):	
	from_date = frappe.form_dict["from_date"]
	to_date = frappe.form_dict["to_date"]
	employee = frappe.form_dict["employee"]		
	if from_date and to_date and employee:
		conditions = f"""and at.attendance_date Between '{from_date}' AND '{to_date}' and at.employee = '{employee}'"""

	return conditions
   
def process_data(data,from_date,to_date, employee):
	processed = {}
	result = []
	holidays = []
	wo = []
	emp_det = frappe.db.get_value("Employee", employee, 
		["default_shift","holiday_list","date_of_joining","employee_name","company","department","allowed_personal_hours",
    "designation","old_punch_id","middle_name","gender","date_of_birth"], as_dict=1)
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
	# frappe.throw(f"{}")

	for row in data:
		if row.lh:
			row.status = 'LH'
		shift_hours_in_sec = row.shift_hours*3600
		if row.net_wrk_hrs.total_seconds() > shift_hours_in_sec or (shift_hours_in_sec - row.net_wrk_hrs.total_seconds()) < 60:
			row.net_wrk_hrs = timedelta(hours=row.shift_hours)
		row["total_pay_hrs"] = row.net_wrk_hrs + (row.get("ot_hours") or timedelta(0))
		row.status = STATUS.get(row.status) or row.status
		processed[row.attendance_date] = row

	ot_for_wo = frappe.get_all("OT Log", {"employee":employee,"attendance_date": ["between",[from_date,to_date]], "is_cancelled":0}, ["attendance_date","allowed_ot as ot_hours", "first_in as in_time", "last_out as out_time"])
	ot_for_wo = {row.attendance_date: row for row in ot_for_wo}
	date_range = get_date_range(from_date, to_date)
	for date in date_range:
		row = processed.get(date,ot_for_wo.get(date,{}))
		if date in od:			
			row["status"] = "OD"
			if ot_hours:=row.get("ot_hours"):
				row['total_pay_hrs'] = ot_hours
		elif date in wo and (date >= getdate(emp_det.get("date_of_joining"))):
			status = "WO"			
			date_time = datetime.combine(getdate(date), get_time(shift_det.start_time))
			if first_in_last_out := get_checkins(employee,date_time):		
				row["in_time"] = get_time(first_in_last_out[0].get("time"))
				row["out_time"] = get_time(first_in_last_out[-1].get("time"))
			if ot_hours:=row.get("ot_hours"):
				row['total_pay_hrs'] = ot_hours
		elif (date in holidays) and (date >= getdate(emp_det.get("date_of_joining"))):
			status = "H"
			row['net_wrk_hrs'] = timedelta(hours=shift_hours)
			row['total_pay_hrs'] = timedelta(hours=shift_hours)
		else:
			status = "XX"	
		if count:=checkins.get(date):
			if count %2 != 0:
				row["status"] = "ERR"
		temp = {
			"login_date": date,
			"shift": shift_name,
			"status": status,
			"employee": employee,
            "employee_name": emp_det.get("employee_name"),
            "company": emp_det.get("company"),
            "department": emp_det.get("department"),
            "designation": emp_det.get("designation"),
            "old_punch_id": emp_det.get("old_punch_id"),
            "middle_name": emp_det.get("middle_name"),
            "gender": emp_det.get("gender"),
            "date_of_birth": emp_det.get("date_of_birth"),
            "date_of_joining": emp_det.get("date_of_joining"),
            "allowed_personal_hours": emp_det.get("allowed_personal_hours"),
            "attendance_date": date,
            "shift_hours": flt(shift_det.get("shift_hours"))
		}
		if not row.get("spent_hours"):
			row["spent_hours"] = None
		temp.update(row)
		result.append(temp)
	return result

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

@frappe.whitelist(allow_guest=True)
def employee_details(company = None,department = None):
	company = frappe.form_dict["company"]
	department = frappe.form_dict["department"]

	data = frappe.db.sql(f"""
		select name as employee, employee_name, company, department,
			default_shift as shift, designation, old_punch_id
		from `tabEmployee` 
		where company ='{company}' and department = '{department}'
	""", as_dict=1)

	return data