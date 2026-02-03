# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

# import frappe
# from frappe.model.document import Document
# from frappe.utils import getdate, add_to_date, get_datetime, get_datetime_str, time_diff, getdate, get_timedelta, get_time
# from frappe import _
# from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift_timings
# from datetime import timedelta, datetime
# from frappe.query_builder import DocType
# from frappe.query_builder.functions import IfNull, Sum, Timestamp, Date
# from frappe.query_builder import CustomFunction
# from collections import defaultdict

# class OTAllowanceEntry(Document):
# 	def autoname(self):
# 		company_abbr = frappe.db.get_value("Company", self.company, "abbr")
# 		if company_abbr:
# 			if self.branch:
# 				branch_short = self.branch.split('-')[-2] 
# 				series = f"{company_abbr}-{branch_short}-OTA-.#####"
# 			else:
# 				series = f"{company_abbr}-OTA-.#####"

# 			self.name = frappe.model.naming.make_autoname(series)
		
# 	def validate(self):
# 		self.locked_by = frappe.session.user
# 		if self.workflow_state == "Create OT": 
# 			self.make_ot_logs()
# 		if self.employee:
# 			existing= frappe.db.get_all(
# 				"OT Allowance Entry",
# 				filters={
# 					"from_date": self.from_date,
# 					"to_date": self.to_date,
# 					"employee": self.employee,
# 					"name": ["!=", self.name]
# 				},
# 				fields=["name", "locked_by"]
# 			)

# 			for entry in existing:
# 				if entry.locked_by and entry.locked_by != self.locked_by or entry.locked_by == self.locked_by:
# 					form_link = f"/app/ot-allowance-entry/{entry.name}"
# 					frappe.throw(
# 						f"This entry for {self.employee} from  {self.from_date} to {self.to_date} locked by another user: <b>{entry.locked_by}</b><br>"
# 						f"<a href='{form_link}' target='_blank'>View entry</a>"
# 					)

# 	def make_ot_logs(self):
# 		for log in self.ot_details:
# 			if get_timedelta(log.allowed_ot) > get_timedelta(log.attn_ot_hrs):
# 				frappe.throw(_("Allowed OT cannot be greater than Attendance OT Hours"))
# 			# if log.attendance_date and log.employee and log.allow:
# 			# 	exit_ot = frappe.db.get_value("OT Log",{'employee': log.employee, 'attendance_date': log.attendance_date},['name'])
# 			# 	if exit_ot:
# 			# 		continue
# 			# 	else:
# 			create_ot_log(log)
# 		# self.ot_details=[]
# 		frappe.msgprint(_("Records Updated"))

# 	@frappe.whitelist()
# 	def get_ot_details(self, from_log=False):
# 		Attendance = frappe.qb.DocType("Attendance")
# 		ShiftType = frappe.qb.DocType("Shift Type")
# 		OTLog = frappe.qb.DocType("OT Log")
# 		Employee = frappe.qb.DocType("Employee")
# 		PersonalOutLog = frappe.qb.DocType("Personal Out Log")

# 		conditions = self.get_conditions(Attendance, Employee, OTLog, from_log)
		
# 		To_Seconds = CustomFunction("TIME_TO_SEC", ["date"])
# 		ifelse = CustomFunction("IF", ["condition", "then", "else"])
# 		Time_Diff = CustomFunction("TIMEDIFF", ["cur_date", "due_date"])
# 		Time = CustomFunction("Time", ["time"])
# 		Sec_To_Time = CustomFunction("SEC_TO_TIME", ["date"])

# 		sub_query_personal_out_log = (
# 			frappe.qb.from_(PersonalOutLog)
# 			.select(IfNull(Sum(To_Seconds(PersonalOutLog.total_hours)), 0))
# 			.where(
# 				(PersonalOutLog.is_cancelled == 0) &
# 				(PersonalOutLog.employee == Attendance.employee) &
# 				(PersonalOutLog.date == Attendance.attendance_date) &
# 				(PersonalOutLog.out_time >= ShiftType.end_time)
# 			)
# 		)

# 		ot_hours = (
# 			To_Seconds(
# 				Time_Diff(
# 					Attendance.out_time,
# 					Timestamp(Date(Attendance.in_time), ShiftType.end_time)
# 				)
# 			)
# 			+ ifelse(
# 				Timestamp(Date(Attendance.in_time), ShiftType.start_time) > Attendance.in_time,
# 				To_Seconds(
# 					Time_Diff(
# 						Timestamp(Date(Attendance.in_time), ShiftType.start_time), Attendance.in_time
# 					)
# 				), 
# 				0
# 			)
# 			- sub_query_personal_out_log
# 		).as_("attn_ot_hrs")
		
# 		query = (
# 			frappe.qb.from_(Attendance)
# 			.left_join(ShiftType).on(Attendance.shift == ShiftType.name)
# 			.left_join(OTLog).on((OTLog.attendance == Attendance.name) & (OTLog.is_cancelled == 0))
# 			.left_join(Employee).on(Attendance.employee == Employee.name)
# 			.select(
# 				Attendance.name.as_("attendance"),
# 				Attendance.employee,
# 				Attendance.employee_name,
# 				Employee.company,
# 				Employee.designation,
# 				Employee.department,
# 				Employee.branch,
# 				Sec_To_Time(ot_hours).as_("attn_ot_hrs"),
# 				Attendance.shift,
# 				Attendance.attendance_date,
# 				Time(Attendance.in_time).as_("first_in"),
# 				Time(Attendance.out_time).as_("last_out"),
# 				OTLog.name.as_("ot_log"),
# 				OTLog.allow,
# 				OTLog.allowed_ot,
# 				OTLog.remarks
# 			)
# 			.where(
# 				(Attendance.docstatus == 1) &
# 				(To_Seconds(Time_Diff(Attendance.out_time, Timestamp(Date(Attendance.in_time), ShiftType.end_time))) > 0)
# 			)
# 		)

# 		for condition in conditions:
# 			query = query.where(condition)
		
# 		data = query.run(as_dict=True)

# 		self.ot_details = []
		
# 		data =  data + self.get_weekoffs_ot(from_log)
		
# 		if not data:
# 			frappe.msgprint(_("No Records were found for the current filters"))
# 			return
# 		data = sorted(data, key=lambda x:x.get("attendance_date")) 

# 		for row in data:
# 			if self.branch:
# 				if row.get("branch") != self.branch:
# 					continue
				
# 			if not row.get("allowed_ot"):
# 				row["allowed_ot"] = row.get("attn_ot_hrs") 
# 			if row.get("allowed_ot") < timedelta(minutes=30):	# for excluding OT that are less than 30 min
# 				continue
# 			if row["allowed_ot"].total_seconds() > 86399:  # OT > 23:59:59 it shows invalid date in ui 
# 				continue

# 			self.append("ot_details", row)

# 	def get_weekoffs_ot(self, from_log=False):
# 		holidays = self.get_emp_list()
# 		res = []

# 		for holiday_list, emp_list in holidays.items():
# 			holidays_list = frappe.get_all("Holiday", {"parent": holiday_list,
# 					"holiday_date":["between",[self.from_date, self.to_date]]}, ["holiday_date","weekly_off"])
# 			for emp in emp_list:
# 				res += self.get_weekoffs_ot_per_employee(from_log, emp, holidays_list)
# 		return res

# 	def get_weekoffs_ot_per_employee(self, from_log=False, emp = None, holidays = []):
# 		res = []
# 		final_result = []
# 		for holiday in holidays:
# 			shift_ass = frappe.db.get_value("Shift Assignment",
# 					{"employee": self.employee,
# 	  					"start_date": ["<=", holiday.holiday_date],
# 						"end_date": [">=", holiday.holiday_date],
# 						"docstatus": 1
# 	  				},
# 					['name','shift_type'], as_dict=1)
# 			default_shift = ''
# 			holiday_date = getdate(holiday.holiday_date)
			
# 			if shift_ass:
# 				default_shift = shift_ass.shift_type
# 				shift_start_date = holiday_date - timedelta(days=1)
# 			else:
# 				default_shift = emp.default_shift
# 				shift_start_date = holiday_date
# 			shift = get_shift(emp.name, holiday.holiday_date, default_shift) 
			
# 			start_time = get_time(shift.start_time)

# 			# date_time = datetime.combine(shift_start_date, start_time)	
# 			date_time = datetime.combine(getdate(holiday.holiday_date), get_time(shift.start_time))

# 			shift_timings = get_employee_shift_timings(emp.name, get_datetime(date_time), True)[1]
# 			filters = {
# 					"time":["between",[get_datetime_str(shift_timings.actual_start), get_datetime_str(shift_timings.actual_end)]],
# 					"employee": emp.name
# 			}
# 			fields = ["date(time) as date", "log_type as type", "time(time) as time", "time as date_time", "source","name as employee_checkin", 
# 						f"date('{holiday.holiday_date}') as holiday", "employee", "employee_name","shift"]

# 			data = frappe.get_list("Employee Checkin", filters= filters, fields=fields, order_by='date_time')
# 			checkin = {}
# 			for row in data:
# 				if not checkin and row.type == "IN":
# 					checkin = {
# 						"attendance_date": row.holiday,
# 						"date_time": row.date_time,
# 						"first_in": row.time,
# 						"employee": row.employee,
# 						"employee_name": row.employee_name,
# 						"shift": row.shift,
# 						"weekly_off": holiday.weekly_off,
# 						"company": emp.company,
# 						"department": emp.department,
# 						"designation": emp.designation,
# 						"branch": emp.branch
# 					}
# 				elif checkin and row.type == "OUT":
# 					ot_log = {}
# 					ot_log = frappe.db.get_value("OT Log",{"attendance_date": row.holiday, "employee": row.employee, "is_cancelled":0, "first_in": checkin.get("first_in")},
# 												["name as ot_log", "allow", "allowed_ot", "remarks","attendance_date"], as_dict=1) or {}
# 					checkin.update(ot_log)
# 					checkin["last_out"] = row.time
# 					checkin["attn_ot_hrs"] = time_diff(row.date_time, checkin.get("date_time"))
# 					if not checkin.get("allowed_ot"):
# 						checkin["allowed_ot"] = time_diff(row.date_time, checkin.get("date_time"))
# 					if from_log:
# 						if checkin.get("ot_log"):
# 							res.append(checkin)
# 						checkin = {}
# 						continue
# 					res.append(checkin)
# 					checkin = {}
# 		# Group by attendance_date logic of two parts ot in weekof
# 		grouped = defaultdict(list)
# 		for entry in res:
# 			grouped[entry['attendance_date']].append(entry)
# 		for date, entries in grouped.items():
# 			if len(entries) > 1:
# 				base = dict(entries[0])

# 				total_ot = sum((e.get("attn_ot_hrs", timedelta()) for e in entries), timedelta())
# 				total_allowed_ot = sum((e.get("allowed_ot", timedelta()) for e in entries), timedelta())
				
# 				base["first_in"] = min(e.get("first_in") for e in entries)
# 				base["last_out"] = max(e.get("last_out") for e in entries)
# 				base["date_time"] = min(e.get("date_time") for e in entries)
# 				base["attn_ot_hrs"] = total_ot
# 				base["allowed_ot"] = total_ot
# 				base["attendance_date"] = base["attendance_date"]
# 				base["ot_log"] = base.get("ot_log")
# 				base["allow"] = base.get("allow")
# 				base["remarks"] = base.get("remarks")

# 				final_result.append(base)
# 			else:
# 				final_result.extend(entries)

# 		return final_result
	
# 	def get_emp_list(self):
# 		emp_list = []
# 		filters = {}
# 		if self.employee:
# 			filters["employee"] = self.employee
# 		if self.designation:
# 			filters["designation"] = self.designation
# 		if self.department:
# 			filters["department"] = self.department
# 		if self.company:
# 			filters["company"] = self.company

# 		emp_list = frappe.get_list("Employee", filters = filters, fields = ["default_shift","holiday_list","name","company", "designation", "department", "branch"])
# 		holidays = {}
# 		for emp in emp_list:
# 			if shift:=emp.get("default_shift") and not emp.get("holiday_list"):
# 				emp.holiday_list = frappe.db.get_value("Shift Type",shift,"holiday_list")

# 			if emp.holiday_list not in holidays:
# 				holidays[emp.holiday_list] = [emp]
# 			else:
# 				holidays[emp.holiday_list].append(emp)
# 		return holidays

# 	def get_conditions(self, Attendance, Employee, OTLog, from_log):
# 		from frappe.utils import getdate
# 		if not (self.from_date and self.to_date):
# 			frappe.throw(_("Invalid Date Range"))
# 		conditions = [
# 			(Attendance.attendance_date.between(getdate(self.from_date), getdate(self.to_date)))
# 		]
# 		if from_log:
# 			conditions.append((OTLog.name.isnotnull()))

# 		if self.punch_id or self.employee:
# 			if not self.employee:
# 				self.employee = frappe.db.get_value("Employee",{"attendance_device_id":self.punch_id},'name')
# 			conditions.append((Attendance.employee == self.employee))

# 		if self.employee_name:
# 			conditions.append((Attendance.employee_name.like(f"%{self.employee_name}%")))
		
# 		sub_query_filter = [
# 			(Employee.product_incentive_applicable == 1)
# 		]

# 		if self.company:
# 			sub_query_filter.append((Employee.company == self.company))
# 		else:
# 			frappe.throw(_("Company is mandatory"))
		
# 		if self.branch:
# 			sub_query_filter.append((Employee.branch == self.branch))

# 		if self.department:
# 			sub_query_filter.append((Employee.department == self.department))
		
# 		if self.designation:
# 			sub_query_filter.append((Employee.designation == self.designation))

# 		sub_query = (
# 			frappe.qb.from_(Employee)
# 			.select(Employee.name)
# 		)
# 		for filter in sub_query_filter:
# 			sub_query = sub_query.where(filter)
		
# 		conditions.append((Attendance.employee.isin(sub_query)))

# 		return conditions

# def create_ot_log(ref_doc):
# 	if ref_doc.ot_log:
# 		doc = frappe.get_doc("OT Log",ref_doc.ot_log)
# 		if doc.allow and not ref_doc.allow:
# 			doc.delete()
# 			return
# 		# if ref_doc.attendance_date == doc.attendance_date:
# 	else:
# 		if not ref_doc.allow:
# 			return
# 		doc = frappe.new_doc("OT Log")
# 	fields = ["employee","employee_name","attendance_date","attn_ot_hrs","allow","allowed_ot","first_in","last_out","attendance","remarks", "weekly_off","ot_allowance_entry"]
# 	data = {}
# 	for field in fields:
# 		# field == 'ot_allowance_entry'
# 		data[field] = ref_doc.get(field)

# 	doc.update(data)
# 	doc.save()
# 	return doc.name


# def get_shift(employee, date, default_shift):
# 	shift = frappe.db.get_value("Shift Assignment", 
# 				{
# 					"employee": employee, 
# 	 				"start_date": ["<=", date], 
# 					"end_date": [">=",date], 
# 					"status": "Active", 
# 					"docstatus": 1
# 				}, 
# 			['shift_type'] )
	
# 	if not shift:
# 		shift = default_shift
# 	det = frappe.db.get_value("Shift Type", shift, ["name", "start_time", "end_time", "shift_hours", "begin_check_in_before_shift_start_time", "allow_check_out_after_shift_end_time"], as_dict=1)
# 	return det

# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

# 22-01-2026
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, add_to_date, get_datetime, get_datetime_str, time_diff, getdate, get_timedelta, get_time
from frappe import _
from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift_timings
from datetime import timedelta, datetime
from frappe.query_builder import DocType
from frappe.query_builder.functions import IfNull, Sum, Timestamp, Date
from frappe.query_builder import CustomFunction
from collections import defaultdict

class OTAllowanceEntry(Document):
	def autoname(self):
		company_abbr = frappe.db.get_value("Company", self.company, "abbr")
		if company_abbr:
			if self.branch:
				branch_short = self.branch.split('-')[-2] 
				series = f"{company_abbr}-{branch_short}-OTA-.#####"
			else:
				series = f"{company_abbr}-OTA-.#####"

			self.name = frappe.model.naming.make_autoname(series)
		
	def validate(self):
		self.locked_by = frappe.session.user
		if self.workflow_state == "Create OT": 
			self.make_ot_logs()
		if self.employee:
			existing= frappe.db.get_all(
				"OT Allowance Entry",
				filters={
					"from_date": self.from_date,
					"to_date": self.to_date,
					"employee": self.employee,
					"name": ["!=", self.name]
				},
				fields=["name", "locked_by"]
			)

			for entry in existing:
				if entry.locked_by and entry.locked_by != self.locked_by or entry.locked_by == self.locked_by:
					form_link = f"/app/ot-allowance-entry/{entry.name}"
					frappe.throw(
						f"This entry for {self.employee} from  {self.from_date} to {self.to_date} locked by another user: <b>{entry.locked_by}</b><br>"
						f"<a href='{form_link}' target='_blank'>View entry</a>"
					)

	def make_ot_logs(self):
		for log in self.ot_details:
			if not log.allow_excess_ot and get_timedelta(log.allowed_ot) > get_timedelta(log.attn_ot_hrs):
				frappe.throw(_("Allowed OT cannot be greater than Attendance OT Hours"))

			create_ot_log(ref_doc=log)
		frappe.msgprint(_("Records Updated"))

	@frappe.whitelist()
	def get_ot_details(self, from_log=False):
		Attendance = frappe.qb.DocType("Attendance")
		ShiftType = frappe.qb.DocType("Shift Type")
		OTLog = frappe.qb.DocType("OT Log")
		Employee = frappe.qb.DocType("Employee")
		PersonalOutLog = frappe.qb.DocType("Personal Out Log")

		conditions = self.get_conditions(Attendance, Employee, OTLog, from_log)
		
		To_Seconds = CustomFunction("TIME_TO_SEC", ["date"])
		ifelse = CustomFunction("IF", ["condition", "then", "else"])
		Time_Diff = CustomFunction("TIMEDIFF", ["cur_date", "due_date"])
		Time = CustomFunction("Time", ["time"])
		Sec_To_Time = CustomFunction("SEC_TO_TIME", ["date"])

		sub_query_personal_out_log = (
			frappe.qb.from_(PersonalOutLog)
			.select(IfNull(Sum(To_Seconds(PersonalOutLog.total_hours)), 0))
			.where(
				(PersonalOutLog.is_cancelled == 0) &
				(PersonalOutLog.employee == Attendance.employee) &
				(PersonalOutLog.date == Attendance.attendance_date) &
				(PersonalOutLog.out_time >= ShiftType.end_time)
			)
		)

		ot_hours = (
			# Late OT (ONLY if OUT > Shift End)
			ifelse(
				Attendance.out_time > Timestamp(Date(Attendance.in_time), ShiftType.end_time),
				To_Seconds(
					Time_Diff(
						Attendance.out_time,
						Timestamp(Date(Attendance.in_time), ShiftType.end_time)
					)
				),
				0
			)

			+

			# Early OT (ONLY if IN < Shift Start)
			ifelse(
				Timestamp(Date(Attendance.in_time), ShiftType.start_time) > Attendance.in_time,
				To_Seconds(
					Time_Diff(
						Timestamp(Date(Attendance.in_time), ShiftType.start_time),
						Attendance.in_time
					)
				),
				0
			)
			# Personal Out deduction 
			- sub_query_personal_out_log
		).as_("attn_ot_hrs")
		
		query = (
			frappe.qb.from_(Attendance)
			.left_join(ShiftType).on(Attendance.shift == ShiftType.name)
			.left_join(OTLog).on((OTLog.attendance == Attendance.name) & (OTLog.is_cancelled == 0))
			.left_join(Employee).on(Attendance.employee == Employee.name)
			.select(
				Attendance.name.as_("attendance"),
				Attendance.employee,
				# Attendance.employee_name,
				Employee.company,
				Employee.designation,
				Employee.department,
				Employee.branch,
				Sec_To_Time(ot_hours).as_("attn_ot_hrs"),
				Attendance.shift,
				Attendance.attendance_date,
				Time(Attendance.in_time).as_("first_in"),
				Time(Attendance.out_time).as_("last_out"),
				OTLog.name.as_("ot_log"),
				OTLog.allow,
				OTLog.allowed_ot,
				OTLog.remarks
			)
			# .where(
			# 	(Attendance.docstatus == 1) 
			# 	&
			# 	(To_Seconds(Time_Diff(Attendance.out_time, Timestamp(Date(Attendance.in_time), ShiftType.end_time))) > 0)
			# )
			.where(
				(Attendance.docstatus == 1)
				&
				(
					(Timestamp(Date(Attendance.in_time), ShiftType.start_time) > Attendance.in_time)
					|
					(
						To_Seconds(
							Time_Diff(
								Attendance.out_time,
								Timestamp(Date(Attendance.in_time), ShiftType.end_time)
							)
						) > 0
					)
				)
			)
		)

		for condition in conditions:
			query = query.where(condition)
		
		data = query.run(as_dict=True)

		self.ot_details = []
		
		data =  data + self.get_weekoffs_ot(from_log)
		
		if not data:
			frappe.msgprint(_("No Records were found for the current filters"))
			return
		data = sorted(data, key=lambda x:x.get("attendance_date")) 

		for row in data:
			if self.branch:
				if row.get("branch") != self.branch:
					continue

			shift_start = frappe.db.get_value("Shift Type", row["shift"], "start_time")
			
			# If employee came early → FULL early OT must be allowed
			if row.get("first_in") and shift_start and row["first_in"] < shift_start:
				row["allowed_ot"] = row["attn_ot_hrs"]

			# Fallback: if allowed_ot still empty
			if not row.get("allowed_ot"):
				row["allowed_ot"] = row["attn_ot_hrs"]
			if row.get("allowed_ot") < timedelta(minutes=30):	# for excluding OT that are less than 30 min
				continue
			if row["allowed_ot"].total_seconds() > 86399:  # OT > 23:59:59 it shows invalid date in ui 
				continue

			if row.get("attendance"):
				row.update({"employee_name": frappe.db.get_value("Attendance", row["attendance"], "employee_name")})

			self.append("ot_details", row)

	def get_weekoffs_ot(self, from_log=False):
		holidays = self.get_emp_list()
		res = []

		for holiday_list, emp_list in holidays.items():
			holidays_list = frappe.get_all("Holiday", {"parent": holiday_list,
					"holiday_date":["between",[self.from_date, self.to_date]]}, ["holiday_date","weekly_off"])
			for emp in emp_list:
				res += self.get_weekoffs_ot_per_employee(from_log, emp, holidays_list)
		return res

	def get_weekoffs_ot_per_employee(self, from_log=False, emp = None, holidays = []):
		res = []
		final_result = []
		for holiday in holidays:
			shift_ass = frappe.db.get_value("Shift Assignment",
					{"employee": self.employee,
	  					"start_date": ["<=", holiday.holiday_date],
						"end_date": [">=", holiday.holiday_date],
						"docstatus": 1
	  				},
					['name','shift_type'], as_dict=1)
			default_shift = ''
			holiday_date = getdate(holiday.holiday_date)
			
			if shift_ass:
				default_shift = shift_ass.shift_type
				shift_start_date = holiday_date - timedelta(days=1)
			else:
				default_shift = emp.default_shift
				shift_start_date = holiday_date
			shift = get_shift(emp.name, holiday.holiday_date, default_shift) 
			
			# date_time = datetime.combine(shift_start_date, start_time)	
			date_time = datetime.combine(getdate(holiday.holiday_date), get_time(shift.start_time))

			shift_timings = get_employee_shift_timings(emp.name, get_datetime(date_time), True)[1]
			filters = {
					"time":["between",[get_datetime_str(shift_timings.actual_start), get_datetime_str(shift_timings.actual_end)]],
					"employee": emp.name
			}
			fields = ["date(time) as date", "log_type as type", "time(time) as time", "time as date_time", "source","name as employee_checkin", 
						f"date('{holiday.holiday_date}') as holiday", "employee", "shift"]

			data = frappe.get_list("Employee Checkin", filters= filters, fields=fields, order_by='date_time')
			checkin = {}
			for row in data:
				if not checkin and row.type == "IN":
					checkin = {
						"attendance_date": row.holiday,
						"date_time": row.date_time,
						"first_in": row.time,
						"employee": row.employee,
						"employee_name": row.employee_name,
						"shift": row.shift,
						"weekly_off": holiday.weekly_off,
						"company": emp.company,
						"department": emp.department,
						"designation": emp.designation,
						"branch": emp.branch
					}
				elif checkin and row.type == "OUT":
					ot_log = {}
					ot_log = frappe.db.get_value("OT Log",{"attendance_date": row.holiday, "employee": row.employee, "is_cancelled":0, "first_in": checkin.get("first_in")},
												["name as ot_log", "allow", "allowed_ot", "remarks","attendance_date"], as_dict=1) or {}
					checkin.update(ot_log)
					checkin["last_out"] = row.time
					checkin["attn_ot_hrs"] = time_diff(row.date_time, checkin.get("date_time"))
					if not checkin.get("allowed_ot"):
						checkin["allowed_ot"] = time_diff(row.date_time, checkin.get("date_time"))
					if from_log:
						if checkin.get("ot_log"):
							res.append(checkin)
						checkin = {}
						continue
					res.append(checkin)
					checkin = {}
		# Group by attendance_date logic of two parts ot in weekof
		grouped = defaultdict(list)
		for entry in res:
			grouped[entry['attendance_date']].append(entry)
		for date, entries in grouped.items():
			if len(entries) > 1:
				base = dict(entries[0])

				total_ot = sum((e.get("attn_ot_hrs", timedelta()) for e in entries), timedelta())
				total_allowed_ot = sum((e.get("allowed_ot", timedelta()) for e in entries), timedelta())
				
				base["first_in"] = min(e.get("first_in") for e in entries)
				base["last_out"] = max(e.get("last_out") for e in entries)
				base["date_time"] = min(e.get("date_time") for e in entries)
				base["attn_ot_hrs"] = total_ot
				base["allowed_ot"] = total_ot
				base["attendance_date"] = base["attendance_date"]
				base["ot_log"] = base.get("ot_log")
				base["allow"] = base.get("allow")
				base["remarks"] = base.get("remarks")

				final_result.append(base)
			else:
				final_result.extend(entries)

		return final_result
	
	def get_emp_list(self):
		emp_list = []
		filters = {}
		if self.employee:
			filters["employee"] = self.employee
		if self.designation:
			filters["designation"] = self.designation
		if self.department:
			filters["department"] = self.department
		if self.company:
			filters["company"] = self.company

		emp_list = frappe.get_list("Employee", filters = filters, fields = ["default_shift","holiday_list","name","company", "designation", "department", "branch"])
		holidays = {}
		for emp in emp_list:
			if shift:=emp.get("default_shift") and not emp.get("holiday_list"):
				emp.holiday_list = frappe.db.get_value("Shift Type",shift,"holiday_list")

			if emp.holiday_list not in holidays:
				holidays[emp.holiday_list] = [emp]
			else:
				holidays[emp.holiday_list].append(emp)
		return holidays

	def get_conditions(self, Attendance, Employee, OTLog, from_log):
		from frappe.utils import getdate
		if not (self.from_date and self.to_date):
			frappe.throw(_("Invalid Date Range"))
		conditions = [
			(Attendance.attendance_date.between(getdate(self.from_date), getdate(self.to_date)))
		]
		if from_log:
			conditions.append((OTLog.name.isnotnull()))

		if self.punch_id or self.employee:
			if not self.employee:
				self.employee = frappe.db.get_value("Employee",{"attendance_device_id":self.punch_id},'name')
			conditions.append((Attendance.employee == self.employee))

		# if self.employee_name:
		# 	conditions.append((Attendance.employee_name.like(f"%{self.employee_name}%")))
		
		sub_query_filter = [
			(Employee.product_incentive_applicable == 1)
		]

		if self.company:
			sub_query_filter.append((Employee.company == self.company))
		else:
			frappe.throw(_("Company is mandatory"))
		
		if self.branch:
			sub_query_filter.append((Employee.branch == self.branch))
			
		if self.department:
			sub_query_filter.append((Employee.department == self.department))
		
		if self.designation:
			sub_query_filter.append((Employee.designation == self.designation))

		sub_query = (
			frappe.qb.from_(Employee)
			.select(Employee.name)
		)
		for filter in sub_query_filter:
			sub_query = sub_query.where(filter)
		
		conditions.append((Attendance.employee.isin(sub_query)))

		return conditions

def create_ot_log(ref_doc):
	if ref_doc.ot_log:
		doc = frappe.get_doc("OT Log",ref_doc.ot_log)
		if doc.allow and not ref_doc.allow:
			ref_doc.ot_log = None
			doc.delete()
			frappe.msgprint(f"OT Log {doc.name} deleted")
			return
	else:
		if not ref_doc.allow:
			return
		
		# check if ot log already exists
		if frappe.db.exists("OT Log", {"attendance_date": ref_doc.attendance_date, "employee": ref_doc.employee}):
			frappe.throw(_("OT Log already exists for this employee on this date"))
			return

		doc = frappe.new_doc("OT Log")
	fields = ["employee","employee_name","attendance_date","attn_ot_hrs","allow","allowed_ot","first_in","last_out","attendance","remarks", "weekly_off","ot_allowance_entry"]
	data = {}
	for field in fields:
		# field == 'ot_allowance_entry'
		data[field] = ref_doc.get(field)
	
	################## Edited By Aditya at 27-01-2026 ##################
	# update employe name as per attendance log
	data["employee_name"] = frappe.db.get_value("Attendance", ref_doc.attendance, "employee_name")
	data['ot_allowance_entry'] = ref_doc.get("parent", "")

	doc.update(data)
	doc.save()
	ref_doc.ot_log = doc.name
	return doc.name

def get_shift(employee, date, default_shift):
	shift = frappe.db.get_value("Shift Assignment", 
				{
					"employee": employee, 
	 				"start_date": ["<=", date], 
					"end_date": [">=",date], 
					"status": "Active", 
					"docstatus": 1
				}, 
			['shift_type'] )
	
	if not shift:
		shift = default_shift
	det = frappe.db.get_value("Shift Type", shift, ["name", "start_time", "end_time", "shift_hours", "begin_check_in_before_shift_start_time", "allow_check_out_after_shift_end_time"], as_dict=1)
	return det