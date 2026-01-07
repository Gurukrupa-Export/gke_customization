import frappe
from frappe import _
from datetime import timedelta, datetime
from frappe.utils import flt, getdate, add_days, format_time, today, add_to_date, get_time, get_datetime
from gurukrupa_customizations.gurukrupa_customizations.doctype.manual_punch.manual_punch import get_checkins  # type: ignore
from frappe.query_builder.functions import Count, Date, Concat, IfNull, Sum, Min, Max
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
	"Maternity Leave" : "ML",
}

@frappe.whitelist(allow_guest=True)
def attendance(from_date = None,to_date = None,employee = None):
	Attendance = frappe.qb.DocType("Attendance")
	Employee = frappe.qb.DocType("Employee")
	ShiftType = frappe.qb.DocType("Shift Type")
	PersonalOutLog = frappe.qb.DocType("Personal Out Log")
	OTLog = frappe.qb.DocType("OT Log")

	conditions = get_conditions(from_date,to_date,employee)

	TIME_FORMAT = CustomFunction('TIME_FORMAT', ['time', 'format'])
	TIMEDIFF = CustomFunction('TIMEDIFF', ['time1', 'time2'])
	SEC_TO_TIME = CustomFunction('SEC_TO_TIME', ['seconds'])
	TIME_TO_SEC = CustomFunction('TIME_TO_SEC', ['time'])
	IF = CustomFunction('IF', ['condition', 'true_expr', 'false_expr'])
	TIMESTAMP = CustomFunction('TIMESTAMP', ['date', 'time'])
	TIME = CustomFunction('TIME', ['time'])
	MIN = CustomFunction('MIN', ['expr'])
	MAX = CustomFunction('MAX', ['expr'])
	DATE = CustomFunction('DATE', ['datetime'])
	COALESCE = CustomFunction('COALESCE', ['value1', 'value2'])


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
    

	# Main Query
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
			Attendance.attendance_date, (Attendance.shift).as_('shift_name'),
			Concat(TIME_FORMAT(ShiftType.start_time, "%H:%i:%s"), " TO ", TIME_FORMAT(ShiftType.end_time, "%H:%i:%s")).as_('shift'),
			TIME(Attendance.in_time).as_('in_time'),
			TIME(Attendance.out_time).as_('out_time'),
			TIMEDIFF(Attendance.out_time, Attendance.in_time).as_('spent_hours'),
			Attendance.late_entry,
			IF(Attendance.late_entry, TIMEDIFF(TIME(Attendance.in_time), ShiftType.start_time), None).as_('late_hrs'),
			IF(Attendance.early_exit, TIMEDIFF(ShiftType.end_time, TIME(Attendance.out_time)), None).as_('early_hrs'),
			pol_subquery.hrs.as_('p_out_hrs'),
			SEC_TO_TIME(
				IF(
					( # Attendance.attendance_request.isnotnull() | 
					( (Attendance.status == "On Leave") 
	  					& (Attendance.leave_type.isin(frappe.db.get_list('Leave Type', filters={'is_lwp': 0}, pluck='name')) ) )
					),
					ShiftType.shift_hours * 3600,
					IF(Attendance.out_time, TIME_TO_SEC(TIMEDIFF(Attendance.out_time, Attendance.in_time)), Attendance.working_hours * 3600)
				)
				+ IF((Attendance.late_entry == 0) & (TIME(Attendance.in_time) > ShiftType.start_time),
					TIME_TO_SEC(TIMEDIFF(TIME(Attendance.in_time), ShiftType.start_time)), 0)
				- IF(TIME(Attendance.in_time) < ShiftType.start_time,
					TIME_TO_SEC(TIMEDIFF(ShiftType.start_time, TIME(Attendance.in_time))), 0)
				- IF(Attendance.out_time > TIMESTAMP(Date(Attendance.in_time), ShiftType.end_time),
					TIME_TO_SEC(TIMEDIFF(Attendance.out_time, TIMESTAMP(Date(Attendance.in_time), ShiftType.end_time))), 0)
				- IfNull(TIME_TO_SEC(pol_subquery.hrs), 0)
				+ (
					frappe.qb.from_(PersonalOutLog)
					.select(IfNull(Sum(TIME_TO_SEC(PersonalOutLog.total_hours)), 0))
					.where(
						(PersonalOutLog.is_cancelled == 0) &
						(PersonalOutLog.employee == Attendance.employee) &
						(PersonalOutLog.date == Attendance.attendance_date) &
						(PersonalOutLog.out_time >= ShiftType.end_time)
					)
				)
			).as_('net_wrk_hrs'),
			ShiftType.shift_hours,
			IF((ShiftType.working_hours_threshold_for_half_day > Attendance.working_hours) & (Attendance.working_hours > 0), 1, 0).as_('lh'),
			ot_subquery.allowed_ot.as_('ot_hours'),
			IfNull(Attendance.leave_type, Attendance.status).as_('status'),
			Attendance.attendance_request
		)
		.where(
			(Attendance.docstatus == 1)
		)
		.orderby(Attendance.attendance_date, order=frappe.qb.asc)
	)

	for condition in conditions:
		query = query.where(condition)
	# frappe.throw(f"{query}")
	data = query.run(as_dict=1)
	
	if not data:
		return
	
	data = process_data(data,from_date,to_date,employee)
	
	return data
  
def get_conditions(from_date, to_date, employee):
    """Return a list of QB conditions instead of raw SQL string."""
    Attendance = frappe.qb.DocType("Attendance")

    # fallback to frappe.form_dict if not passed explicitly
    from_date = from_date or frappe.form_dict.get("from_date")
    to_date = to_date or frappe.form_dict.get("to_date")
    employee = employee or frappe.form_dict.get("employee")

    conditions = []

    if from_date and to_date:
        conditions.append(Attendance.attendance_date.between(from_date, to_date))
    if employee:
        conditions.append(Attendance.employee == employee)

    return conditions
   
def process_data(data,from_date,to_date, employee):
	processed = {}
	result = []
	holidays = []
	wo = []
	emp_det = frappe.db.get_value("Employee", employee, 
		["default_shift","holiday_list","date_of_joining","employee_name","company","department","allowed_personal_hours",
    "designation","old_punch_id","middle_name","gender","date_of_birth","branch"], as_dict=1)
	
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
	
	# Checkin query - first IN / last OUT per employee/date, only if no Attendance
	checkins = (
		frappe.qb.from_(EmployeeCheckin)
		.select(
			Date(EmployeeCheckin.time).as_("login_date"),
			Min(EmployeeCheckin.time).as_("first_in"),
			Max(EmployeeCheckin.time).as_("last_out"),
			Count(EmployeeCheckin.name).as_("cnt")
		)
		.where(
			(EmployeeCheckin.time.between(from_date, addition_day)) &
			(EmployeeCheckin.employee == employee)
		)
		.groupby(Date(EmployeeCheckin.time))
	).run(as_dict=True)

	# convert to dict keyed by date
	checkins = {row.login_date: row for row in checkins}
	
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
				elif row.late_hrs or row.p_out_hrs:
					late = row.late_hrs or timedelta(0)
					p_out = row.p_out_hrs or timedelta(0)
					total = late + p_out
					
					row.net_wrk_hrs = timedelta(hours=shift_hours) - total
					row.total_pay_hrs = timedelta(0)
				else:
					row.net_wrk_hrs = timedelta(hours=shift_hours)
					row.total_pay_hrs = row.net_wrk_hrs + (row.ot_hours or timedelta(0))

		if row.lh:
			row.status = 'LH'
		shift_hours_in_sec = ''
		if row.shift_hours:
			shift_hours_in_sec = row.shift_hours * 3600
			if row.net_wrk_hrs.total_seconds() > shift_hours_in_sec or (shift_hours_in_sec - row.net_wrk_hrs.total_seconds()) < 60:
				row.net_wrk_hrs = timedelta(hours=row.shift_hours)
		else:
			shift = emp_det.get("default_shift")
			shift_det = frappe.db.get_value("Shift Type", shift, ['shift_hours','start_time', 'end_time'], as_dict=1)
			shift_hours = flt(shift_det.get("shift_hours"))
			shift_name = f"{format_time(shift_det.get('start_time'))} To {format_time(shift_det.get('end_time'))}"
			row.shift = shift_name
			
			leave_status = frappe.db.get_value('Leave Type',{'name': row.status,'is_earned_leave': 0}, ['name'])
			if leave_status:
				row.status = leave_status
				row.net_wrk_hrs = timedelta(0)
			else:
				row.net_wrk_hrs = timedelta(hours=shift_hours)
				
		row["total_pay_hrs"] = row.net_wrk_hrs + (row.get("ot_hours") or timedelta(0))
		row.status = STATUS.get(row.status) or row.status
		processed[row.attendance_date] = row

	ot_for_wo = frappe.get_all("OT Log", {"employee":employee,"attendance_date": ["between",[from_date,to_date]], "is_cancelled":0}, ["attendance_date","allowed_ot as ot_hours", "first_in as in_time", "last_out as out_time"])
	ot_for_wo = {row.attendance_date: row for row in ot_for_wo}
	date_range = get_date_range(from_date, to_date)

	# Fetch OT approval status from OT Details
	ot_details = frappe.get_all(
		"OT Details",
		{
			"employee": employee,
			"attendance_date": ["between", [from_date, to_date]]
		},
		["attendance_date", "allow", "allowed_ot"]
	)

	# Map by date for quick lookup
	# Example: {date: {"hrs": timedelta, "allow": 0/1}}
	ot_details_map = {
		row.attendance_date: {
			"hrs": row.attn_ot_hrs,
			"allow": row.allow
		}
		for row in ot_details
	}

	for date in date_range:
		# row = processed.get(date,ot_for_wo.get(date,{}))
		row = processed.get(date)

		# 🔹 CASE 1: Attendance NOT available, but Check-in exists
		if not row and date in checkins:
			ci = checkins[date]

			# CHANGE: Preserve existing status for non-attendance days
			row = frappe._dict({
				"attendance_date": date,
				"in_time": get_time(ci.first_in) if ci.first_in else None,
				"out_time": get_time(ci.last_out) if ci.last_out else None,
				"spent_hours": (
					ci.last_out - ci.first_in
					if ci.first_in and ci.last_out else None
				),
				"net_wrk_hrs": timedelta(0),
				"total_pay_hrs": timedelta(0),
				"status": "ERR"   # Check-in only
			})

		# 🔹 CASE 2: No Attendance, no Check-in → fallback to OT
		if not row:
			row = ot_for_wo.get(date, {})

		status = row.get("status") or "XX"
		if date in od:
			status = "OD"
			if row.get("ot_hours"):
				if ot_hours:=row.get("ot_hours"):
					row['total_pay_hrs'] = ot_hours
			else:
				# row["status"] = "OD"
				row['total_pay_hrs'] = row.get("total_pay_hrs")
		elif date in wo and (date >= getdate(emp_det.get("date_of_joining"))):
			status = "WO" # weekly off
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

		count = checkins.get(date)
		count = count.get("cnt") if isinstance(count, dict) else count
		# CHANGE: Extract cnt from check-in row before odd/even validation
		if count:
			if count % 2 != 0:
				status = "ERR"
				row['net_wrk_hrs'] = timedelta(0)
				row['total_pay_hrs'] = timedelta(0)


		# ------------------------------------------------------------------
		# STEP 3: Resolve OT hours for this date
		# ------------------------------------------------------------------

		# Default predefined OT from OT Details (if exists & approved)
		predefined_ot_hrs = None
		ot_detail = ot_details_map.get(date)

		if ot_detail and ot_detail.get("allow") == 1 and row.get("ot_hours"):
			predefined_ot_hrs = row.get("ot_hours")

		# # Call OT resolver
		ot_hours, ot_status = resolve_ot_hours(
			attendance_date=date,
			shift_end_time=get_time(shift_det.end_time),
			out_time=row.get("out_time"),
			threshold_min=30,
			predefined_hrs=predefined_ot_hrs
		)

		# Apply resolved OT to row
		row["ot_hours"] = ot_hours
		row["ot_status"] = ot_status


		temp = {
			"login_date": date,
			"shift": shift_name,
			"status": status,
			"employee": employee,
            "employee_name": emp_det.get("employee_name"),
            "company": emp_det.get("company"),
            "branch": emp_det.get("branch"),
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
def employee_details(branch=None,company = None,department = None):
	company = frappe.form_dict["company"]
	department = frappe.form_dict["department"]
	branch = frappe.form_dict["branch"]

	data = frappe.db.sql(f"""
		select name as employee, employee_name, company, department,
			default_shift as shift, designation, old_punch_id,branch
		from `tabEmployee` 
		where company ='{company}' and department = '{department}' and branch = '{branch}' and status = 'Active'
	""", as_dict=1)

	return data

def resolve_ot_hours(
    attendance_date,
    shift_end_time,
    out_time,
    threshold_min=30,
    predefined_hrs=None
):
	"""
	Resolve OT hours using frappe utilities.

	Priority:
	1. Predefined OT hours (Approved)
	2. Auto-calculated OT (shift end + threshold)
	"""

	# 1️⃣ Approved OT (from OT Details or OT Log)
	if predefined_hrs:
		return predefined_hrs, "Approved"

	# 2️⃣ Missing data → no OT
	if not attendance_date or not shift_end_time or not out_time:
		return None, ""

	# Normalize values using frappe utils
	attendance_date = getdate(attendance_date)
	shift_end_time = get_time(shift_end_time)
	out_time = get_time(out_time)

	# Build datetime safely
	shift_end_dt = get_datetime(f"{attendance_date} {shift_end_time}")
	out_dt = get_datetime(f"{attendance_date} {out_time}")
		
	# 3️⃣ If employee left before or at shift end → NO OT
	if out_dt <= shift_end_dt:
		return None, ""

	diff = out_dt - shift_end_dt

	# 4️⃣ Threshold check
	if diff < timedelta(minutes=threshold_min):
		return None, ""

	# 5️⃣ Valid OT
	return diff, "Pending"