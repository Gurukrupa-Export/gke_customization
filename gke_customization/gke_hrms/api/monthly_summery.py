import frappe
from frappe import _
from datetime import timedelta, datetime
from frappe.utils import flt, getdate, add_days, format_time, today, add_to_date, get_time, get_datetime
import frappe.utils
from gurukrupa_customizations.gurukrupa_customizations.doctype.manual_punch.manual_punch import get_checkins
from frappe.query_builder.functions import Count, Date, Concat, IfNull, Sum
from frappe.query_builder import CustomFunction

STATUS = {
	"Absent" : "A",
	"Present" : "P",
	"Half Day" : "HD",
	"Privilege Leave" : "PL",
	"Casual Leave" : "CL",
	"Sick Leave" : "SL",
	"Leave Without Pay" : "LWP",
	"Outdoor Duty" : "OD",
	"Work From Home" : "WFH",
	# "Maternity Leave" : "ML",
	"Marriage leave" : "ML",
}

@frappe.whitelist(allow_guest=True)
def attendance1(from_date = None,to_date = None,employee = None):
	conditions = get_conditions(from_date,to_date,employee) 

	Attendance = frappe.qb.DocType("Attendance")
	Employee = frappe.qb.DocType("Employee")
	ShiftType = frappe.qb.DocType("Shift Type")
	PersonalOutLog = frappe.qb.DocType("Personal Out Log")
	OTLog = frappe.qb.DocType("OT Log")

	TIME_FORMAT = CustomFunction('TIME_FORMAT', ['time', 'format'])
	TIMEDIFF = CustomFunction('TIMEDIFF', ['time1', 'time2'])
	SEC_TO_TIME = CustomFunction('SEC_TO_TIME', ['seconds'])
	TIME_TO_SEC = CustomFunction('TIME_TO_SEC', ['time'])
	IF = CustomFunction('IF', ['condition', 'true_expr', 'false_expr'])
	TIMESTAMP = CustomFunction('TIMESTAMP', ['date', 'time'])
	TIME = CustomFunction('TIME', ['time'])
	ADDDATE = CustomFunction('ADDDATE', ['date', 'days'])
	ADDTIME = CustomFunction("ADDTIME", ["date", "time"])

	# Personal Out Log subquery
	pol_subquery = (
		frappe.qb.from_(PersonalOutLog)
		.select(
			PersonalOutLog.employee, 
			PersonalOutLog.date, 
			SEC_TO_TIME(IfNull(Sum(TIME_TO_SEC(PersonalOutLog.total_hours)), 0)).as_('hrs')
			)
		.where(PersonalOutLog.is_cancelled == 0)
		.groupby(PersonalOutLog.employee, PersonalOutLog.date)
	).as_('pol')

	# OT Log subquery
	ot_subquery = (
		frappe.qb.from_(OTLog)
		.select('*')
		.where(OTLog.is_cancelled == 0)
	).as_('ot')

	# -----------------------------
	# SHIFT WINDOW -- New Added 
	# -----------------------------
	shift_start = TIMESTAMP(Attendance.attendance_date, ShiftType.start_time)

	shift_end = IF(
		ShiftType.start_time < ShiftType.end_time,
		TIMESTAMP(Attendance.attendance_date, ShiftType.end_time),
		TIMESTAMP(ADDDATE(Attendance.attendance_date, 1), ShiftType.end_time)
	)

	shift_start_with_grace = ADDTIME(
		shift_start,
		SEC_TO_TIME(ShiftType.late_entry_grace_period * 60)
	)

	effective_in = IF(
		Attendance.in_time <= shift_start_with_grace,
		shift_start,
		Attendance.in_time
	)

	effective_out = IF(
		Attendance.out_time > shift_end,
		shift_end,
		Attendance.out_time
	)
	
	query = (
		frappe.qb.from_(Attendance)
		.left_join(Employee).on(Attendance.employee == Employee.name)
		.left_join(ShiftType).on(Attendance.shift == ShiftType.name)
		.left_join(pol_subquery).on(
			(Attendance.attendance_date == pol_subquery.date) &
			(Attendance.employee == pol_subquery.employee)
		)
		.left_join(ot_subquery).on(
			(Attendance.attendance_date == ot_subquery.attendance_date) &
			(Attendance.employee == ot_subquery.employee)
		)
		.select(
			Attendance.attendance_date, 
			(Attendance.shift).as_('shift_name'),

			Concat(TIME_FORMAT(ShiftType.start_time, "%H:%i:%s"), " TO ", TIME_FORMAT(ShiftType.end_time, "%H:%i:%s")).as_('shift'),
			
			TIME(Attendance.in_time).as_('in_time'),
			TIME(Attendance.out_time).as_('out_time'),


			Attendance.late_entry,
			# IF(Attendance.late_entry, TIMEDIFF(TIME(Attendance.in_time), ShiftType.start_time), None).as_('late_hrs'),
			IF(Attendance.late_entry, TIMEDIFF(Attendance.in_time, TIMESTAMP(Attendance.attendance_date, ShiftType.start_time)), None).as_('late_hrs'),
			IF(Attendance.early_exit, TIMEDIFF(ShiftType.end_time, TIME(Attendance.out_time)), None).as_('early_hrs'),
			
			# TIMEDIFF(Attendance.out_time, Attendance.in_time).as_('spent_hours'),
			
			################################################
			# ✅ FIXED SPENT HOURS (date aware)
			SEC_TO_TIME(
				IF(
					Attendance.out_time.isnull(),
					0,
					TIME_TO_SEC(
						TIMEDIFF(
							IF(
								Attendance.out_time < Attendance.in_time,
								TIMESTAMP(
									ADDDATE(Date(Attendance.in_time), 1),
									TIME(Attendance.out_time),
								),
								Attendance.out_time,
							),
							Attendance.in_time,
						)
					),
				)
			).as_("spent_hours"),
			################################################

			
			pol_subquery.hrs.as_('p_out_hrs'),
			################################################
			# ✅ FIXED NET WORKING HOURS -- Negative hours Issue solved
			SEC_TO_TIME(
				IfNull(
					IF(
						Attendance.status.isin(["A", "ERR"]),
						0,
						TIME_TO_SEC(
							TIMEDIFF(effective_out, effective_in)
						)
						- IfNull(TIME_TO_SEC(pol_subquery.hrs), 0)
					),
					0
				)
			).as_("net_wrk_hrs"),
			################################################

			ShiftType.shift_hours,
			IF((ShiftType.working_hours_threshold_for_half_day > Attendance.working_hours) & (Attendance.working_hours > 0), 1, 0).as_('lh'),
			ot_subquery.allowed_ot.as_('ot_hours'),
			IfNull(Attendance.leave_type, Attendance.status).as_('status'),
			Attendance.attendance_request
		)
		.where((Attendance.docstatus == 1))
		.orderby(Attendance.attendance_date, order=frappe.qb.asc)
	)

	for condition in conditions:
		query = query.where(condition)

	data = query.run(as_dict=1)
	
	if not data:
		return

	data = process_data(data,from_date,to_date,employee)
	totals = get_totals(data, employee)
	data += totals 

	return totals   


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
                    if((
					#    at.attendance_request is not null or 
					   (at.status = "On Leave" and at.leave_type in (select name from `tabLeave Type` where is_lwp = 0))
					   ),
                        st.shift_hours * 3600,
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
		# frappe.throw(f"{data}")
		data = process_data(data,from_date,to_date,employee)
		totals = get_totals(data, employee)
		data += totals 
	return totals
    
  
def get_conditions(from_date,to_date,employee):	
	from_date = frappe.form_dict["from_date"]
	to_date = frappe.form_dict["to_date"]
	employee = frappe.form_dict["employee"]		

	Attendance = frappe.qb.DocType("Attendance")

	if from_date and to_date:
		conditions = [
			(Attendance.attendance_date.between(from_date, to_date))
		]
	
	if employee:
		conditions.append(Attendance.employee == employee)

	return conditions
   
def process_data(data,from_date,to_date, employee):
	processed = {}
	result = []
	holidays = []
	wo = []
	emp_det = frappe.db.get_value("Employee", employee, 
		["default_shift","holiday_list","date_of_joining","employee_name","company","department",
    "designation","old_punch_id","middle_name","gender","date_of_birth"], as_dict=1)
	
	shift = ''
	for row in data:
		shift = row.shift_name

	if not shift:
		shift = emp_det.get("default_shift")

	shift_det = frappe.db.get_value("Shift Type", shift, ['shift_hours','holiday_list','start_time', 'end_time','early_exit_grace_period'], as_dict=1)
	shift_hours = flt(shift_det.get("shift_hours"))
	shift_name = f"{format_time(shift_det.get('start_time'))} To {format_time(shift_det.get('end_time'))}"
	grace_period = shift_det.get("early_exit_grace_period")
	
	EmployeeCheckin = frappe.qb.DocType("Employee Checkin")
	addition_day = add_days(to_date,1)

	# checkins = (
	# 	frappe.qb.from_(EmployeeCheckin)
	# 	.select(
	# 		Date(EmployeeCheckin.time).as_("login_date"),
	# 		EmployeeCheckin.attendance,
	# 		Count(EmployeeCheckin.name).as_("cnt")
	# 	)
	# 	.where(
	# 		(EmployeeCheckin.time.between(from_date, addition_day)) &
	# 		(EmployeeCheckin.employee == employee)
	# 		&
	# 		(EmployeeCheckin.attendance.isnotnull()) & 
	# 		(EmployeeCheckin.attendance != "")
	# 	)
	# 	.groupby(EmployeeCheckin.attendance)
	# ).run(as_dict=True)

	from_date_time = get_datetime(from_date)
	to_date_time = get_datetime(f"{addition_day} 23:59:59")

	#########################################################
	is_night_shift = get_time(shift_det.get('start_time')) > get_time(shift_det.get('end_time'))

	TIME = CustomFunction("TIME", ["time"])
	IF = CustomFunction("IF", ["condition", "true_expr", "false_expr"])

	# Modify the checkins query to handle night shifts:
	if is_night_shift:
		# For night shifts, group check-ins by the shift start date
		# If time is before shift start (meaning it's from next day), use previous date
		shift_start_time = shift_det.get('start_time')
		checkins = (
			frappe.qb.from_(EmployeeCheckin)
			.select(
				IF(
					TIME(EmployeeCheckin.time) < shift_start_time, # shift_start_time = 23:00:00 and time =  22:00:00
					Date(EmployeeCheckin.time - timedelta(days=1)), #
					Date(EmployeeCheckin.time)
				).as_("login_date"),
				EmployeeCheckin.attendance,
				Count(EmployeeCheckin.name).as_("cnt")
			)
			.where(
				(EmployeeCheckin.time.between(from_date_time, to_date_time)) &
				(EmployeeCheckin.employee == employee) &
				(EmployeeCheckin.attendance.isnotnull()) &
				(EmployeeCheckin.attendance != "")
			)
			.groupby(EmployeeCheckin.attendance)
		).run(as_dict=True)
	else:
		# Keep existing logic for day shifts
		checkins = (
			frappe.qb.from_(EmployeeCheckin)
			.select(
				Date(EmployeeCheckin.time).as_("login_date"),
				EmployeeCheckin.attendance,
				Count(EmployeeCheckin.name).as_("cnt")
			)
			.where(
				(EmployeeCheckin.time.between(from_date_time, to_date_time)) &
				(EmployeeCheckin.employee == employee) &
				(EmployeeCheckin.attendance.isnotnull()) &
				(EmployeeCheckin.attendance != "")
			)
			.groupby(EmployeeCheckin.attendance)
		).run(as_dict=True)
	#########################################################
	
	
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
		# for security grace period 45 min
		if grace_period != 0:
			if not (row.early_hrs): 
				if row.status == 'Absent':
					row.net_wrk_hrs = timedelta(0)
					row.total_pay_hrs = timedelta(0)
				elif row.status == 'Leave Without Pay':
					# FIXED: Force LWP to 0 hours
					row.net_wrk_hrs = timedelta(0)
					row.total_pay_hrs = timedelta(0)
				elif row.late_hrs or row.p_out_hrs:
					late = row.late_hrs or timedelta(0)
					p_out = row.p_out_hrs or timedelta(0)
					total = late + p_out
					
					row.net_wrk_hrs = timedelta(hours=shift_hours) - total
					row.total_pay_hrs = row.net_wrk_hrs + (row.ot_hours or timedelta(0))
				else:
					row.net_wrk_hrs = timedelta(hours=shift_hours)
					row.total_pay_hrs = row.net_wrk_hrs + (row.ot_hours or timedelta(0))

		if row.lh:
			row.status = 'LH'
		shift_hours_in_sec = 0
		if row.shift_hours:
			shift_hours_in_sec = row.shift_hours * 3600
			if row.status not in ['Leave Without Pay', 'Absent']:
				if row.net_wrk_hrs.total_seconds() > shift_hours_in_sec or (shift_hours_in_sec - row.net_wrk_hrs.total_seconds()) < 60:
					row.net_wrk_hrs = timedelta(hours=row.shift_hours)
		else:
			shift = emp_det.get("default_shift")
			shift_det = frappe.db.get_value("Shift Type", shift, ['shift_hours','start_time', 'end_time'], as_dict=1)
			shift_hours = flt(shift_det.get("shift_hours"))
			shift_name = f"{format_time(shift_det.get('start_time'))} To {format_time(shift_det.get('end_time'))}"
			row.shift = shift_name
			
			leave_status = frappe.db.get_value('Leave Type',{'name': row.status,'is_earned_leave': 0}, ['name'])
			e_leave_status = frappe.db.get_value('Leave Type', {'name': row.status,'max_continuous_days_allowed': ['>',0]}, ['name'])
			
			# FIXED: Check if LWP specifically
			is_lwp = frappe.db.get_value('Leave Type', {'name': row.status, 'is_lwp': 1}, ['name'])
			
			if is_lwp:
				# Force LWP to 0 hours
				row.status = STATUS.get(row.status) or row.status
				row.net_wrk_hrs = timedelta(0)
			elif leave_status or e_leave_status:
				row.status = STATUS.get(row.status) or row.status
				row.net_wrk_hrs = timedelta(hours=shift_hours)
			else:
				row.net_wrk_hrs = timedelta(0)
				
		row["total_pay_hrs"] = row.net_wrk_hrs + (row.get("ot_hours") or timedelta(0))
		row.status = STATUS.get(row.status) or row.status
		processed[row.attendance_date] = row

	ot_for_wo = frappe.get_all("OT Log", {"employee":employee,"attendance_date": ["between",[from_date,to_date]], "is_cancelled":0}, ["attendance_date","allowed_ot as ot_hours", "first_in as in_time", "last_out as out_time"])
	ot_for_wo = {row.attendance_date: row for row in ot_for_wo}
	date_range = get_date_range(from_date, to_date)
	
	for date in date_range:
		row = processed.get(date,ot_for_wo.get(date,{}))
		status = row.get("status") or "XX"

		if date in od:
			status = "OD"
			if row.get("ot_hours"):
				if ot_hours:=row.get("ot_hours"):
					row['total_pay_hrs'] = ot_hours
			else:
				row['total_pay_hrs'] = row.get("total_pay_hrs")
		elif date in wo and (date >= getdate(emp_det.get("date_of_joining"))):
			status = "WO"			
			date_time = datetime.combine(getdate(date), get_time(shift_det.start_time))
			if first_in_last_out := get_checkins(employee,date_time):		
				row["in_time"] = get_time(first_in_last_out[0].get("time"))
				row["out_time"] = get_time(first_in_last_out[-1].get("time"))
			if ot_hours:=row.get("ot_hours"):
				row['total_pay_hrs'] = ot_hours
		elif (date in holidays) and (date >= getdate(emp_det.get("date_of_joining"))):
			if row.get("status") in ["LWP", "PL", "CL", "SL", "ML","WFH"]:
				pass
			else:
				status = 'H'
				row['net_wrk_hrs'] = timedelta(hours=shift_hours)
				row['total_pay_hrs'] = timedelta(hours=shift_hours)
		else:
			status = "XX"	
		if count:=checkins.get(date):
			if count %2 != 0:
				row["status"] = "ERR"
				row['net_wrk_hrs'] = timedelta(0)
				row['total_pay_hrs'] = timedelta(0)
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

def get_totals(data, employee):	 
	totals = { 
		"employee": data[0].get("employee") if data else "Unknown",
		"employee_name": data[0].get("employee_name") if data else "Unknown",
		"company": data[0].get("company") if data else "Unknown",
		"department": data[0].get("department") if data else "Unknown",
		"designation": data[0].get("designation") if data else "Unknown",
		"old_punch_id": data[0].get("old_punch_id") if data else "Unknown",
		"net_wrk_hrs": timedelta(0),
		"spent_hours": timedelta(0),
		"late_hrs": timedelta(0),
		"early_hrs": timedelta(0),
		"p_out_hrs": timedelta(0),
		"ot_hours": timedelta(0),
		"total_pay_hrs": timedelta(0),
		"late_count": 0   
	}

	late_count = 0
	penalty_days = 0 
	totals["shift_hours"] = 0.0

	for row in data:
		totals["net_wrk_hrs"] += (row.get("net_wrk_hrs") or timedelta(0))
		totals["total_pay_hrs"] += (row.get("total_pay_hrs") or timedelta(0))
		totals["ot_hours"] += (row.get("ot_hours") or timedelta(0))
		totals["early_hrs"] += (row.get("early_hrs") or timedelta(0))
		totals["late_hrs"] += (row.get("late_hrs") or timedelta(0))
		totals["p_out_hrs"] += (row.get("p_out_hrs") or timedelta(0))
		totals["spent_hours"] += (row.get("spent_hours") or timedelta(0))

		if row.get("late_entry"):
			late_count += 1
		if not totals["shift_hours"] and row.get("shift_hours"):		
			totals["shift_hours"] = flt(row.get("shift_hours"))

	totals["late_count"] = late_count

	if late_count > 4 and late_count < 10:
		penalty_days = 0.5
	if late_count >= 10 and late_count < 15:
		penalty_days = 1
	if late_count >= 15:
		penalty_days = 1.5
    
	conversion_factor = 3600 * flt(totals.get("shift_hours", 1))  
	conversion_factor = 0
	con_factor = 3600 * flt(totals["shift_hours"])
	if con_factor > 0:
		conversion_factor = con_factor
	else:
		conversion_factor = 1

	shift_hour_value = frappe.db.get_value("Shift Type", {'name': frappe.db.get_value("Employee", employee, 'default_shift')}, 'shift_hours') or timedelta(0)
	if totals["shift_hours"]:
		penalty_hrs = timedelta(hours=flt(totals["shift_hours"]) * penalty_days) or timedelta(0)
	else:
		penalty_hrs = timedelta(hours=flt(shift_hour_value) * penalty_days) or timedelta(0)

	for key in ["net_wrk_hrs", "spent_hours", "late_hrs", "early_hrs", "p_out_hrs", "ot_hours", "total_pay_hrs"]:
		totals[f"total_days_{key}"] = flt(totals[key].total_seconds() / conversion_factor, 2) if conversion_factor else 0

	allowed_personal_hours = frappe.db.get_value("Employee", employee, 'allowed_personal_hours') or timedelta(0)
	totals["refund"] = min(allowed_personal_hours, (totals["early_hrs"] + totals["late_hrs"] + totals["p_out_hrs"]))
	totals["refund_days"] = flt(totals["refund"].total_seconds() / conversion_factor ,2) if conversion_factor else 0

	totals["penalty_days"] = penalty_days

	totals["net_pay_hrs"] = totals["net_wrk_hrs"] + totals["ot_hours"]  + totals["refund"] - penalty_hrs
	totals["net_pay_days"] = flt(totals["net_pay_hrs"].total_seconds() / conversion_factor, 2) if conversion_factor else 0

	totals["net_pay_hrs_wo_ot"] = totals["net_wrk_hrs"] + totals["refund"] - penalty_hrs
	totals["net_pay_days_wo_ot"] = flt(totals["net_pay_hrs_wo_ot"].total_seconds() / conversion_factor, 2) if conversion_factor else 0

	return totals


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