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
            select at.employee,
                at.employee_name, at.company, at.department,
                emp.allowed_personal_hours, emp.designation, emp.old_punch_id,
                emp.middle_name, emp.gender, emp.date_of_birth, emp.date_of_joining, emp.holiday_list,
                at.attendance_date,
                concat(TIME_FORMAT(st.start_time,"%H:%i:%s"), " TO ", TIME_FORMAT(st.end_time,"%H:%i:%s")) as shift,
                time(at.in_time) as in_time, 
                time(at.out_time) as out_time, 
                TIMEDIFF(at.out_time, at.in_time) as spent_hours, 
                at.late_entry, 
                if(at.late_entry, timediff(time(at.in_time), st.start_time), Null) as late_hrs,
                if(at.early_exit, timediff(st.end_time, time(at.out_time)), Null) as early_hrs, 
                pol.hrs as p_out_hrs, 
                sec_to_time(
                    if((at.attendance_request is not null or (at.status = "On Leave" and at.leave_type in (select name from `tabLeave Type` where is_lwp = 0))),
                        st.shift_hours,
                    IF(at.out_time, time_to_sec(TIMEDIFF(at.out_time, at.in_time)), at.working_hours * 3600))
                    + if(at.late_entry=0 and time(at.in_time) > time(st.start_time),
                        time_to_sec(timediff(time(at.in_time), st.start_time)), 0)
                    - if(time(at.in_time) < time(st.start_time),
                        time_to_sec(timediff(st.start_time, time(at.in_time))), 0)
                    - if(at.out_time > timestamp(date(at.in_time), st.end_time),
                        time_to_sec(timediff(at.out_time, timestamp(date(at.in_time), st.end_time))), 0)
                    - ifnull(time_to_sec(pol.hrs),0)
                    + (select ifnull(sum(time_to_sec(pl.total_hours)),0) from `tabPersonal Out Log` pl 
                        where pl.is_cancelled = 0 and pl.employee = at.employee and pl.date = at.attendance_date and pl.out_time >= st.end_time)
                    ) as net_wrk_hrs,
                st.shift_hours, 
                if(st.working_hours_threshold_for_half_day > at.working_hours and at.working_hours > 0, 1, 0) as lh,
                ot.allowed_ot as ot_hours,
                ifnull(at.leave_type, at.status) as status, at.attendance_request
            from 
                `tabAttendance` at 
            left join `tabEmployee` emp on at.employee = emp.name 
            left join `tabShift Type` st on emp.default_shift = st.name 
            left join (select employee, date, sec_to_time(sum(time_to_sec(total_hours))) as hrs 
                        from `tabPersonal Out Log` where is_cancelled = 0 group by employee, date) pol 
                        on at.attendance_date = pol.date and at.employee = pol.employee 
            left join (select * from `tabOT Log` where is_cancelled = 0) ot 
                        on at.attendance_date = ot.attendance_date and at.employee = ot.employee
            where 
                at.docstatus = 1 {conditions}                 
            order by 
                at.employee,
                at.attendance_date asc
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
		["default_shift","holiday_list","date_of_joining","employee_name","company","department",
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
            "attendance_date": date
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