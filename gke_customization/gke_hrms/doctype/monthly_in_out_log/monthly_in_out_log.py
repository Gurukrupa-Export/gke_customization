# # Copyright (c) 2026, Gurukrupa Export and contributors
# # For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from datetime import timedelta, datetime
from frappe.utils import (
    flt, getdate, add_days, format_time,
    get_time, get_datetime
)

from gurukrupa_customizations.gurukrupa_customizations.doctype.manual_punch.manual_punch import get_checkins  # pyright: ignore[reportMissingImports]
from gke_customization.gke_hrms.utils import get_employee_shift

from frappe.query_builder.functions import Count, Date, IfNull, Sum, Concat
from frappe.query_builder import CustomFunction


# ============================================================
# CONSTANTS
# ============================================================

STATUS = {
    "Absent": "Absent",
    "Present": "Present",
    "Half Day": "Half Day",
    "On Leave": "On Leave",
    "Leave Without Pay": "On Leave",
    "Sick Leave": "On Leave",
    "Casual Leave": "On Leave",
    "Marriage Leave": "On Leave",
    "Work From Home": "Work From Home",
}

REVERSE_STATUS = {v: k for k, v in STATUS.items()}

TOTAL_STATUS_ROWS = [
    "Total Hours",
    "Total Days",
    "Refund Min(P.Hrs)",
    "Penalty in Days",
    "Net Hrs",
    "Net Days",
    "Net Hrs w/o OT",
    "Net Days w/o OT",
]


# ============================================================
# DOCUMENT CONTROLLER
# ============================================================

class MonthlyInOutLog(Document):

    def validate(self):
        """
        By default populate on validate if employee + attendance_date present.
        Change this behavior if you want manual button-based population instead.
        """
        self.company = frappe.db.get_value("Employee", self.employee, "company")
        self.shit_type = get_employee_shift(self.employee, self.attendance_date)
        self.shift_hours = frappe.db.get_value("Shift Type", self.shit_type, "shift_hours")

        if not self.validate_duplicate_entry():
            self.populate_from_attendance()
    
    def on_submit(self):
        self.populate_from_attendance()

        if not self.attendance:
            atten_doc = frappe.db.get_value("Attendance", {"employee": self.employee, "attendance_date": self.attendance_date, "docstatus": 1 }, "name")
            if atten_doc:
                self.db_set("attendance", atten_doc)
            

    def validate_duplicate_entry(self):
        """
        Prevent duplicate Monthly In-Out Log for same employee & date
        """

        if not self.employee or not self.attendance_date:
            return

        login_date = getdate(self.attendance_date)

        duplicate = frappe.db.exists(
            "Monthly In-Out Log",
            {
                "employee": self.employee,
                "attendance_date": login_date,
                "docstatus": ["in", [0, 1]],
                "name": ["!=", self.name],
            },
        )

        if duplicate:
            return True

    @frappe.whitelist()
    def populate_from_attendance(self):
        """
        Populate document fields using the service function.
        Uses the first record returned for the date.
        """
        try:
            # normalize
            attendance_date = getdate(self.attendance_date)

            if self.attendance:
                attendance_doc = frappe.get_doc("Attendance", self.attendance)
                if not attendance_doc.working_hours:
                    self.net_wrk_hrs = timedelta(0)
                    self.spent_hrs = timedelta(0)
                    self.p_out_hrs = timedelta(0)
                    self.ot_hrs = timedelta(0)
                    self.in_time = timedelta(0)
                    self.out_time = timedelta(0)
                    self.early_hrs = timedelta(0)
                    self.late_hrs = timedelta(0)
                    self.late = 0
                    return

            # frappe.throw(f'{attendance_date}')
            # call the shared service function (module-level)
            res = get_attendance_details_by_date(self.company, self.employee, attendance_date)
            # frappe.throw(f"{res}")
            records = res.get("records") or []

            if not records:
                return

            # use the first (daily) record for the date
            record = records[0]

            # Reset all fields you expect to populate
            for f in ("status", "spent_hrs", "net_wrk_hrs","in_time", "out_time", "p_out_hrs", "late", "late_hrs", "early_hrs", "ot_hrs"):
                if hasattr(self, f):
                    setattr(self, f, None)

            self.status =  record.get("status")

            # time/duration fields as HH:MM:SS
            self.spent_hrs = fmt_td_or_value(record.get("spent_hrs") or record.get("spent_hours"))
            
            # net_wrk_hrs may be timedelta; keep as string
            self.net_wrk_hrs = fmt_td_or_value(record.get("net_wrk_hrs"))

            self.in_time = fmt_td_or_value(record.get("in_time"))
            self.out_time = fmt_td_or_value(record.get("out_time"))

            self.p_out_hrs = fmt_td_or_value(record.get("p_out_hrs"))

            self.late = record.get("late") or record.get("late_entry")
            self.late_hrs = fmt_td_or_value(record.get("late_hrs"))
            self.early_hrs = fmt_td_or_value(record.get("early_hrs"))
            self.ot_hrs= fmt_td_or_value(record.get("ot_hours") or record.get("othrs"))

        except Exception:
            frappe.log_error(title="MonthlyInOutLog.populate_from_attendance_error", message=frappe.get_traceback(with_context=True), reference_doctype=self.doctype)

# ============================================================
# WHITELISTED SERVICE (MODULE-LEVEL, REUSABLE)
# ============================================================

@frappe.whitelist()
def get_attendance_details_by_date(company, employee, attendance_date):
    """
    Whitelisted wrapper for the module-level fetcher.
    Normalizes input date and returns shaped result:
    {
      "employee": <employee id>,
      "attendance_date": <date>,
      "records": [ { daily record dict } ],
      "totals": [ { totals dicts } ]
    }
    """
    if not (company and employee and attendance_date):
        frappe.throw(_("Company, Employee and Attendance Date are required"))

    attendance_date = getdate(attendance_date)

    filters = {
        "company": company,
        "employee": employee,
        "from_date": attendance_date,
        "to_date": attendance_date,
    }


    return fetch_attendance_data(filters)


# ============================================================
# RESPONSE SHAPING (MODULE-LEVEL, REUSABLE)
# ============================================================

def fetch_attendance_data(filters):
    """
    Reusable service that returns shaped attendance data for the given filters.
    This function is intentionally module-level so other controllers / scripts can import it.
    """
    employee = filters.get("employee")

    # fetch basic employee fields once
    emp = frappe.db.get_value(
        "Employee",
        employee,
        ["name", "employee_name", "department", "designation", "company", "attendance_device_id"],
        as_dict=True,
    ) or {}

    raw_data = get_data(filters)

    if not raw_data:
        return {
            "employee": employee,
            "attendance_date": filters.get("from_date"),
            "records": [],
            "totals": [],
        }

    records = []
    totals = []

    # frappe.throw(f'{raw_data}')
    for row in raw_data:
        # totals rows identified by status or by missing login_date + aggregate keys
        if row.get("status") in TOTAL_STATUS_ROWS:
            totals.append(row)
            continue

        if row.get("login_date") is None and any(k in row for k in ("total_pay_hrs", "ot_hours", "net_wrk_hrs")):
            totals.append(row)
            continue

        # daily record shaping
        records.append({
            "employee": emp.get("name"),
            "employee_name": emp.get("employee_name"),
            "department": emp.get("department"),
            "designation": emp.get("designation"),
            "company": emp.get("company"),
            "punch_id": emp.get("attendance_device_id"),

            "login_date": row.get("login_date"),
            "shift_type": row.get("shift"),
            "shift_hours": row.get("shift_hours"),

            "status": row.get("status"),

            "spent_hrs": row.get("spent_hours"),
            "net_wrk_hrs": row.get("net_wrk_hrs"),

            "in_time": row.get("in_time"),
            "out_time": row.get("out_time"),

            "p_out_hrs": row.get("p_out_hrs"),

            "late": row.get("late_entry"),
            "late_hrs": row.get("late_hrs"),
            "early_hrs": row.get("early_hrs"),

            "ot_hours": row.get("ot_hours"),
        })

    return {
        "employee": emp.get("name"),
        "attendance_date": filters.get("from_date"),
        "records": records,
        "totals": totals,
    }


# ============================================================
# CORE REPORT LOGIC (UNCHANGED) - get_data, get_conditions, process_data, get_totals, get_date_range
# ============================================================

def get_data(filters):
    """
    Original report logic lifted into this controller file.
    Business rules preserved exactly.
    """
    Attendance = frappe.qb.DocType("Attendance")
    Employee = frappe.qb.DocType("Employee")
    ShiftType = frappe.qb.DocType("Shift Type")
    PersonalOutLog = frappe.qb.DocType("Personal Out Log")
    OTLog = frappe.qb.DocType("OT Log")

    TIME_FORMAT = CustomFunction('TIME_FORMAT', ['time', 'format'])
    TIMEDIFF = CustomFunction("TIMEDIFF", ["time1", "time2"])
    SEC_TO_TIME = CustomFunction("SEC_TO_TIME", ["seconds"])
    TIME_TO_SEC = CustomFunction("TIME_TO_SEC", ["time"])
    IF = CustomFunction("IF", ["condition", "true_expr", "false_expr"])
    TIMESTAMP = CustomFunction("TIMESTAMP", ["date", "time"])
    TIME = CustomFunction("TIME", ["time"])
    ADDDATE = CustomFunction("ADDDATE", ["date", "days"])
    ADDTIME = CustomFunction("ADDTIME", ["date", "time"])


    conditions = get_conditions(filters)

    # Personal Out Log subquery
    pol_subquery = (
        frappe.qb.from_(PersonalOutLog)
        .select(
            PersonalOutLog.employee,
            PersonalOutLog.date,
            SEC_TO_TIME(IfNull(Sum(TIME_TO_SEC(PersonalOutLog.total_hours)), 0)).as_("hrs"),
        )
        .where(PersonalOutLog.is_cancelled == 0)
        .groupby(PersonalOutLog.employee, PersonalOutLog.date)
    ).as_("pol")

    # OT Log subquery
    ot_subquery = (
        frappe.qb.from_(OTLog)
        .select("*")
        .where(OTLog.is_cancelled == 0)
    ).as_("ot")

    # -----------------------------
    # SHIFT WINDOW (KEY FIX)
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
			Attendance.attendance_date, 
			(Attendance.shift).as_('shift_name'),

			Concat(TIME_FORMAT(ShiftType.start_time, "%H:%i:%s"), " TO ", TIME_FORMAT(ShiftType.end_time, "%H:%i:%s")).as_('shift'),
			
			TIME(Attendance.in_time).as_('in_time'),
			TIME(Attendance.out_time).as_('out_time'),
			
            			
			Attendance.late_entry,
			IF(Attendance.late_entry, TIMEDIFF(Attendance.in_time, TIMESTAMP(Attendance.attendance_date, ShiftType.start_time)), None).as_('late_hrs'),
			IF(Attendance.early_exit, TIMEDIFF(ShiftType.end_time, TIME(Attendance.out_time)), None).as_('early_hrs'),

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

			# SEC_TO_TIME(
			# 	IF(
			# 		# FIXED: Check for LWP first - force 0 hours
			# 		(Attendance.status == "On Leave") & 
			# 		(Attendance.leave_type == "Leave Without Pay"),
			# 		0,
			# 		IF(
			# 			# Check for Absent - force 0 hours
			# 			Attendance.status == "Absent",
			# 			0,
			# 			IF(
			# 				# Check for paid leaves (not LWP) - use shift hours
			# 				( (Attendance.status == "On Leave") & 
			# 				(Attendance.leave_type.isin(frappe.db.get_list('Leave Type', filters={'is_lwp': 0}, pluck='name')) ) ),
			# 				ShiftType.shift_hours * 3600,
			# 				# For Present/WFH - calculate actual hours
			# 				IF(Attendance.out_time, TIME_TO_SEC(TIMEDIFF(Attendance.out_time, Attendance.in_time)), Attendance.working_hours * 3600)
			# 			)
			# 		)
			# 	)
			# 	+ IF((Attendance.late_entry == 0) & (TIME(Attendance.in_time) > ShiftType.start_time),
			# 		TIME_TO_SEC(TIMEDIFF(TIME(Attendance.in_time), ShiftType.start_time)), 0)
			# 	- IF(TIME(Attendance.in_time) < ShiftType.start_time,
			# 		TIME_TO_SEC(TIMEDIFF(ShiftType.start_time, TIME(Attendance.in_time))), 0)
				
			# 	- IF(Attendance.out_time > TIMESTAMP(Date(Attendance.in_time), ShiftType.end_time),
			# 		TIME_TO_SEC(TIMEDIFF(Attendance.out_time, TIMESTAMP(Date(Attendance.in_time), ShiftType.end_time))), 0)
				
			# 	- IfNull(TIME_TO_SEC(pol_subquery.hrs), 0)
			# 	+ (
			# 		frappe.qb.from_(PersonalOutLog)
			# 		.select(IfNull(Sum(TIME_TO_SEC(PersonalOutLog.total_hours)), 0))
			# 		.where(
			# 			(PersonalOutLog.is_cancelled == 0) &
			# 			(PersonalOutLog.employee == Attendance.employee) &
			# 			(PersonalOutLog.date == Attendance.attendance_date) &
			# 			(PersonalOutLog.out_time >= ShiftType.end_time)
			# 		)
			# 	)
			# ).as_('net_wrk_hrs'),

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

    data = query.run(as_dict=True)

    if not data:
        return []

    data = process_data(data, filters)
    data.extend(get_totals(data, filters.get("employee")))

    return data


# ============================================================
# HELPERS (UNCHANGED LOGIC)
# ============================================================

def get_conditions(filters):
    Attendance = frappe.qb.DocType("Attendance")
    if not filters.get("from_date"):
        frappe.throw(_("Attendance Date is required"))

    conditions = [Attendance.attendance_date == filters.get("from_date")]

    if filters.get("employee"):
        conditions.append(Attendance.employee == filters.get("employee"))

    return conditions

# small helper to format timedelta/time-like to HH:MM:SS string
def fmt_td_or_value(val):
    if not val:
        return "00:00:00"
    if isinstance(val, timedelta):
        secs = int(val.total_seconds())
        h = secs // 3600
        m = (secs % 3600) // 60
        s = secs % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
    if isinstance(val, datetime):
        # rarely expected, return date-time string
        return val.strftime("%Y-%m-%d %H:%M:%S")
    return val

def process_data(data, filters):
    employee = filters.get("employee")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    processed = {}
    result = []
    holidays = []
    wo = []
    emp_det = frappe.db.get_value("Employee", employee, ["default_shift", "holiday_list", "date_of_joining"], as_dict=1)

    shift = ''
    for row in data:
        if row.get("shift_name"):
            shift = row.get("shift_name")

    if not shift:
        shift = emp_det.get("default_shift")

    shift_det = frappe.db.get_value("Shift Type", shift, ['shift_hours', 'holiday_list', 'start_time', 'end_time', 'early_exit_grace_period'], as_dict=1)
    shift_hours = flt(shift_det.get("shift_hours") or 0)
    shift_name = f"{format_time(shift_det.get('start_time'))} To {format_time(shift_det.get('end_time'))}"
    grace_period = shift_det.get("early_exit_grace_period") or 0

    EmployeeCheckin = frappe.qb.DocType("Employee Checkin")
    addition_day = add_days(to_date,1)

    ################################################
    from_date_time = get_datetime(from_date)
    to_date_time = get_datetime(f"{addition_day} 23:59:59")
    ################################################

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
    od = frappe.get_list("Employee Checkin", {'employee': employee, 'source': "Outdoor Duty", "time": ['between', [from_date, add_days(to_date, 1)]]}, 'date(time) as login_date', pluck='login_date', group_by='login_date')
    if shift and not emp_det.get('holiday_list'):
        emp_det['holiday_list'] = shift_det.get("holiday_list")

    if hl_name := emp_det.get('holiday_list'):
        holidays = frappe.get_list("Holiday", {"parent": hl_name, "holiday_date": ["between", [from_date, to_date]]}, ["holiday_date", "weekly_off"], ignore_permissions=1)
        wo = [row.holiday_date for row in holidays if row.weekly_off]
        holidays = [row.holiday_date for row in holidays if not row.weekly_off]

    for row in data:
        # security grace period logic
        if grace_period != 0:
            if not (row.get("early_hrs")):
                if row.get("status") == 'Absent':
                    row["net_wrk_hrs"] = timedelta(0)
                    row["total_pay_hrs"] = timedelta(0)
                elif row.status == 'Leave Without Pay':
                    # FIXED: Force LWP to 0 hours
                    row.net_wrk_hrs = timedelta(0)
                    row.total_pay_hrs = timedelta(0)
                elif row.get("late_hrs") or row.get("p_out_hrs"):
                    late = row.get("late_hrs") or timedelta(0)
                    p_out = row.get("p_out_hrs") or timedelta(0)
                    total = late + p_out

                    row["net_wrk_hrs"] = timedelta(hours=shift_hours) - total
                    row["total_pay_hrs"] = timedelta(0)
                else:
                    row["net_wrk_hrs"] = timedelta(hours=shift_hours)
                    row["total_pay_hrs"] = row.get("net_wrk_hrs") + (row.get("ot_hours") or timedelta(0))

        if row.get("lh"):
            row["status"] = 'LH'

        shift_hours_in_sec = ''
        if row.shift_hours:
            shift_hours_in_sec = row.shift_hours * 3600
            # FIXED: Don't override LWP hours
            if row.status not in ['Leave Without Pay', 'Absent']:
                if row.net_wrk_hrs.total_seconds() > shift_hours_in_sec or (shift_hours_in_sec - row.net_wrk_hrs.total_seconds()) < 60:
                    row.net_wrk_hrs = timedelta(hours=row.shift_hours)
        else:
            shift = emp_det.get("default_shift")
            shift_det = frappe.db.get_value("Shift Type", shift, ['shift_hours', 'start_time', 'end_time'], as_dict=1)
            shift_hours = flt(shift_det.get("shift_hours") or 0)
            shift_name = f"{format_time(shift_det.get('start_time'))} To {format_time(shift_det.get('end_time'))}"
            row["shift"] = shift_name

            leave_status = frappe.db.get_value('Leave Type', {'name': row.get("status"), 'is_earned_leave': 1}, ['name'])
            e_leave_status = frappe.db.get_value('Leave Type', {'name': row.status,'max_continuous_days_allowed': ['>',0]}, ['name'])

            # FIXED: Check if LWP specifically
            is_lwp = frappe.db.get_value('Leave Type', {'name': row.status, 'is_lwp': 1}, ['name'])
            
            if is_lwp:
                # Force LWP to 0 hours
                row.status = STATUS.get(row.status) or row.status
                row.net_wrk_hrs = timedelta(0)
            elif leave_status or e_leave_status:
                row["status"] = STATUS.get(row.status) or row.status
                row["net_wrk_hrs"] = timedelta(hours=shift_hours)
            else:
                row["net_wrk_hrs"] = timedelta(0)

        row["total_pay_hrs"] = row.get("net_wrk_hrs") + (row.get("ot_hours") or timedelta(0))
        # row["status"] = STATUS.get(row.get("status")) or row.get("status")
        status = row.get("status")

        # Normalize all leave types to "On Leave"
        if frappe.db.exists("Leave Type", status):
            row["status"] = "On Leave"

        elif status in (
            "Present",
            "Absent",
            "Half Day",
            "Work From Home",
            "OD",
            "WO",
            "H",
        ):
            row["status"] = status

        else:
            # safety fallback
            row["status"] = "Absent"

        processed[row.get("attendance_date")] = row

    ot_for_wo = frappe.get_all("OT Log", {"employee": employee, "attendance_date": ["between", [from_date, to_date]], "is_cancelled": 0}, ["attendance_date", "allowed_ot as ot_hours", "first_in as in_time", "last_out as out_time"])
    ot_for_wo = {row.attendance_date: row for row in ot_for_wo}
    date_range = get_date_range(from_date, to_date)

    for date in date_range:
        row = processed.get(date, ot_for_wo.get(date, {}))
        status = row.get("status") or "XX"

        # Check for odd checkin count first, but don't override WO/Holiday status later
        has_checkin_error = False
        if count:=checkins.get(date):
            # frappe.msgprint(f"{count=}")
            if count %2 != 0:
                has_checkin_error = True

        if date in od:
            status = "OD"
            if row.get("ot_hours"):
                if ot_hours := row.get("ot_hours"):
                    row['total_pay_hrs'] = ot_hours
            else:
                row['total_pay_hrs'] = row.get("total_pay_hrs")

        elif date in wo and (date >= getdate(emp_det.get("date_of_joining"))):
            status = "WO"
            date_time = datetime.combine(getdate(date), get_time(shift_det.start_time))
			
			################## PREVS ##################################
			# if first_in_last_out := get_checkins(employee,date_time):		
			# 	row["in_time"] = get_time(first_in_last_out[0].get("time"))
			# 	row["out_time"] = get_time(first_in_last_out[-1].get("time"))

			
			################## NEW ##################################
			# Get check-ins for this WO date
			# Note: get_checkins() may return check-ins from previous day's night shift
			# that ended on this WO date (e.g., 31-Jan 19:59 IN, 01-Feb 08:00 OUT)
            if first_in_last_out := get_checkins(employee, date_time):
                # Filter check-ins by checking if they have a linked Attendance record
                # Check-ins WITH attendance field: belong to a previous shift (e.g., 31-Jan night shift)
                # Check-ins WITHOUT attendance field: likely incomplete OT work on WO day
                for ci in first_in_last_out:
                    # Check if this check-in is linked to an Attendance record
                    if frappe.db.get_value("Employee Checkin", {"name": ci.get("employee_checkin")}, "attendance"):
                        # This check-in belongs to a previous shift's attendance record
                        # Don't show times to avoid confusion (previous shift's data)
                        has_checkin_error = False  # No error - it's from a valid previous attendance
                        row["in_time"] = ""
                        row["out_time"] = ""
                    else:
                        # This check-in has no attendance record (incomplete OT work on WO)
                        # Show the check-in times for review
                        row["in_time"] = get_time(first_in_last_out[0].get("time"))
                        row["out_time"] = get_time(first_in_last_out[-1].get("time"))
            else:
                # No check-ins found for this WO date - clean WO
                has_checkin_error = False
			
            # Add OT hours if OT Log exists (created 1-2 days after work)
            if ot_hours:=row.get("ot_hours"):
                row['total_pay_hrs'] = ot_hours
            ##########################################################################

        elif (date in holidays) and (date >= getdate(emp_det.get("date_of_joining"))):
            if row.get("status") in ["LWP", "PL", "CL", "SL", "ML","WFH"]:
                pass
            else:
                status = 'H'
                row['net_wrk_hrs'] = timedelta(hours=shift_hours)
                row['total_pay_hrs'] = timedelta(hours=shift_hours)
        else:
            status = "XX"

        if has_checkin_error:
            row["status"] = "ERR" 
            row['net_wrk_hrs'] = timedelta(0)
            row['total_pay_hrs'] = timedelta(0)

        temp = {
            "login_date": date,
            "shift": shift_name,
            "status": status
        }
        if not row.get("spent_hours"):
            row["spent_hours"] = None
        temp.update(row)
        result.append(temp)

    return result


def get_totals(data, employee):
    totals = {
        "status": "Total Hours",
        "net_wrk_hrs": timedelta(0),
        "spent_hours": timedelta(0),
        "late_hrs": timedelta(0),
        "early_hrs": timedelta(0),
        "p_out_hrs": timedelta(0),
        "ot_hours": timedelta(0),
        "total_pay_hrs": timedelta(0),
    }
    late_count = 0
    penalty_days = 0

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
        if row.get("shift_hours"):
            totals["shift_hours"] = row.get("shift_hours")

    if late_count > 4 and late_count < 10:
        penalty_days = 0.5
    if late_count >= 10 and late_count < 15:
        penalty_days = 1
    if late_count >= 15:
        penalty_days = 1.5

    total_days = {"status": "Total Days"}
    conversion_factor = 3600 * flt(totals.get("shift_hours") or 0)

    penalty_hrs = timedelta(hours=flt(totals.get("shift_hours") or 0) * penalty_days)
    for key, value in totals.items():
        if key in ["status", "shift_hours"]:
            continue
        total_days[key] = flt(value.total_seconds() / conversion_factor, 2) if conversion_factor else 0.0

    refund = {
        "ot_hours": "Refund Min(P.Hrs)",
        "total_pay_hrs": min(frappe.db.get_value("Employee", employee, 'allowed_personal_hours') or timedelta(0),
                                (totals["early_hrs"] + totals["late_hrs"] + totals["p_out_hrs"]))
    }

    penalty_for_late_entry = {
        "ot_hours": "Penalty in Days",
        "total_pay_hrs": penalty_days
    }

    net_pay_hrs = {
        "ot_hours": "Net Hrs",
        "total_pay_hrs": totals["net_wrk_hrs"] + totals["ot_hours"] + refund["total_pay_hrs"] - penalty_hrs
    }

    net_pay_days = {
        "ot_hours": "Net Days",
        "total_pay_hrs": flt(net_pay_hrs['total_pay_hrs'].total_seconds() / conversion_factor, 2) if conversion_factor else 0.0
    }

    net_pay_hrs_wo_ot = {
        "ot_hours": "Net Hrs w/o OT",
        "total_pay_hrs": totals["net_wrk_hrs"] + refund["total_pay_hrs"] - penalty_hrs
    }

    net_pay_days_wo_ot = {
        "ot_hours": "Net Days w/o OT",
        "total_pay_hrs": flt(net_pay_hrs_wo_ot['total_pay_hrs'].total_seconds() / conversion_factor, 2) if conversion_factor else 0.0
    }

    return [totals, total_days, refund, penalty_for_late_entry, net_pay_hrs, net_pay_days, net_pay_hrs_wo_ot, net_pay_days_wo_ot]


def get_date_range(start_date, end_date):
    import datetime
    start_date = getdate(start_date)
    end_date = getdate(end_date)

    range_list = []
    delta = datetime.timedelta(days=1)
    current_date = start_date

    while current_date <= end_date:
        range_list.append(current_date)
        current_date += delta

    return range_list


def create_monthly_in_out_log(doc, method=None):
    """
    Create Monthly In-Out Log when Attendance is submitted
    """

    # Safety checks
    if not doc.employee or not doc.attendance_date: return

    attendance_date = getdate(doc.attendance_date)

    # Prevent duplicate Monthly In-Out Log
    if frappe.db.exists(
        "Monthly In-Out Log",
        {
            "attendance": doc.name,
            "attendance_date": attendance_date,
            "docstatus": ["in", [0, 1]],  # only submitted,draft docs
        }
    ):return

    # Create Monthly In-Out Log
    monthly_log = frappe.new_doc("Monthly In-Out Log")
    monthly_log.employee = doc.employee
    monthly_log.attendance_date = attendance_date
    monthly_log.attendance = doc.name
    monthly_log.status = doc.status

    monthly_log.save()
    monthly_log.submit()
    frappe.db.commit()


def cancel_monthly_in_out_log(doc, method=None):
    """
    Cancel Monthly In-Out Log when Attendance is cancelled
    """

    if not doc.employee or not doc.attendance_date: return

    attendance_date = getdate(doc.attendance_date)

    monthly_log_name = frappe.db.get_value(
        "Monthly In-Out Log",
        {
            "attendance": doc.name,
            "attendance_date": attendance_date,
            "docstatus": 1,  # only submitted docs
        },
        "name",
    )
    if not monthly_log_name: return

    monthly_log = frappe.get_doc("Monthly In-Out Log", monthly_log_name)
    monthly_log.cancel()
