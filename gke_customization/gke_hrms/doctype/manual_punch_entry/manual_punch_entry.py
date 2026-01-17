# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cint, add_to_date, get_datetime, get_datetime_str, getdate, get_time
from datetime import datetime,timedelta
import itertools
from hrms.hr.doctype.employee_checkin.employee_checkin import (mark_attendance_and_link_log,calculate_working_hours)
from gurukrupa_customizations.gurukrupa_customizations.doctype.personal_out_gate_pass.personal_out_gate_pass import create_prsnl_out_logs
from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift_timings
from frappe.model.workflow import apply_workflow
from erpnext.setup.doctype.holiday_list.holiday_list import is_holiday
from gke_customization.gke_hrms.utils import get_employee_shift

class ManualPunchEntry(Document):
	def after_insert(self):
		# if frappe.user.has_role("GK HR"):
		# 	return
		
		if self.miss_punch and self.workflow_state == "Draft":
			# apply_workflow(self, "Send to Manager")
			apply_workflow(self, "Send to HR")

	def on_update(self):
		if self.workflow_state == "Create Attendance":
			if self.employee:
				shift_name = get_employee_shift(self.employee, self.date)
				if self.shift_name != shift_name: 
					frappe.throw(_('Shift type for Employee is {0}').format(shift_name))

				if not self.shift_name:
					frappe.throw(_('Shift type missing for Employee: {0}').format(self.employee))
				# process_attendance(self.employee, self.shift_name, self.date)
				create_attendance_from_manual_punch(self)
				cancel_linked_records(date=self.date, employee=self.employee)
				create_prsnl_out_logs(from_date=self.date, to_date=self.date, employee=self.employee)
				frappe.msgprint(_("Attendance Updated"))

	def validate(self): 
		self.locked_by = frappe.session.user
		if self.workflow_state == "Create Attendance":
			self.validate_od_punch()
			self.update_emp_checkin()
			self.delete_checkin()
			# self.details = [] 

		#shruti
		# if self.employee:				
		# 	existing = frappe.db.get_all(
		# 		"Manual Punch Entry",
		# 		filters={
		# 			"employee": self.employee,
		# 			"date": self.date,
		# 			"name": ["!=", self.name],
		# 			"workflow_state": ["!=", "Rejected"]
		# 		},
		# 		fields=["name", "locked_by"]
		# 	)

		# 	for entry in existing:
		# 		if entry.locked_by and entry.locked_by != self.locked_by:
		# 			form_link = f"/app/manual-punch-entry/{entry.name}"
		# 			frappe.throw(
		# 				f"This entry for {self.employee} at  {self.date} locked by another user: <b>{entry.locked_by}</b><br>"
		# 				f"<a href='{form_link}' target='_blank'>View entry</a>"
		# 			)

		if self.miss_punch:
			self.validate_miss_punch()

	@frappe.whitelist()
	def validate_punch(self):
		shift_datetime = datetime.combine(getdate(self.date), get_time(self.start_time))
		shift_det = get_employee_shift_timings(self.employee, shift_datetime, True)[1]
		if not (get_datetime(self.new_punch) > shift_det.actual_start and get_datetime(self.new_punch) < shift_det.actual_end):
			frappe.throw(_("Punch must be in between {0} and {1}").format(shift_det.actual_start, shift_det.actual_end))
	
	def validate_miss_punch(self):
		shift_datetime = datetime.combine(getdate(self.date), get_time(self.start_time))
		shift_det = get_employee_shift_timings(self.employee, shift_datetime, True)[1]
		if not (get_datetime(self.miss_punch) > shift_det.actual_start and get_datetime(self.miss_punch) < shift_det.actual_end):
			frappe.throw(_("Punch must be in between {0} and {1}").format(shift_det.actual_start, shift_det.actual_end))
		

	def validate_od_punch(self):
		if self.for_od or any([row.source for row in (self.details or []) if row.source == "Outdoor Duty"]):
			if len(self.details) > 2:
				frappe.throw(_("Only single checkin for IN and OUT are allowed for OT"))

	def update_emp_checkin(self):
		for punch in self.details:
			if punch.employee_checkin:
				doc = frappe.get_doc("Employee Checkin", punch.employee_checkin)
			else:
				doc = frappe.new_doc("Employee Checkin")
				doc.time = punch.time
				doc.employee = self.employee
			doc.skip_auto_attendance = 0
			doc.log_type = punch.type
			doc.source = punch.source
			doc.save()

	@frappe.whitelist()
	def search_checkin(self):
		self.validate_filters()
		self.details = []
		shift_datetime = datetime.combine(getdate(self.date), get_time(self.start_time))
		data = get_checkins(self.employee, shift_datetime)
		return data
	
	def delete_checkin(self):
		if self.to_be_deleted:
			to_be_deleted = self.to_be_deleted.split(",")
			to_be_deleted = [name for name in to_be_deleted if name]
			for docname in to_be_deleted:
				frappe.delete_doc("Employee Checkin",docname,ignore_missing=1)
			frappe.msgprint(_("Following Employee Checkins deleted: {0}").format(', '.join(to_be_deleted)))
		self.to_be_deleted = None

	def validate_filters(self):
		if not self.date:
			frappe.throw(_("Date is Mandatory"))
		if self.punch_id:
			emp = frappe.db.get_value("Employee",{"attendance_device_id": self.punch_id},['name','employee_name', 'default_shift'], as_dict=1)
			
			shift_type = get_employee_shift(self.employee, self.date)
			
			if emp:
				self.employee = emp.get('name')
				self.employee_name = emp.get("employee_name")
				self.shift_name = shift_type
				if self.shift_name:
					self.start_time, self.end_time = frappe.db.get_value("Shift Type", self.shift_name,['start_time', 'end_time'])
		if not self.employee:
			frappe.msgprint(_("Employee is Mandatory"))

	def should_mark_attendance(self, employee: str, attendance_date: str) -> bool:
		"""Determines whether attendance should be marked on holidays or not"""
		shift_doc = frappe.get_doc("Shift Type", self.shift_name)
		
		# no need to check if date is a holiday or not since attendance should be marked on all days
		if shift_doc.mark_auto_attendance_on_holidays: 
			return True

		holiday_list = shift_doc.get_holiday_list(employee) 
		
		if is_holiday(holiday_list, attendance_date):
			return False
		return True
	

def create_attendance_from_manual_punch(self):
	employee = self.employee
	shift_type = self.shift_name
	date = self.date
	shift_start_time = frappe.db.get_value("Shift Type",{"name": shift_type}, "start_time")
	shift_datetime = datetime.combine(getdate(date), get_time(shift_start_time))

	attendance_date = shift_datetime.date()
	mark_att = self.should_mark_attendance(employee, attendance_date)
	# mark_att = self.should_mark_attendance(employee, date)

	if mark_att:	
		shift_timings = get_employee_shift_timings(employee, get_datetime(shift_datetime), True)[1] 	#for current shift
		
		# filters = {
		# 	"skip_auto_attendance": 0,
		# 	"attendance": ("is", "not set"),
		# 	"shift": shift_type,
		# 	"employee": employee,
		# 	"time": ["between", [ (shift_timings.actual_start), (shift_timings.actual_end) ]]
		# }

		# checkin_logs = frappe.db.get_list("Employee Checkin", 
		# 	fields=["*"], 
		# 	filters=filters, 
		# 	order_by="time"
		# )

		checkin_logs = frappe.db.sql("""
			SELECT *
			FROM `tabEmployee Checkin`
			WHERE employee = %s
				AND skip_auto_attendance = 0
				AND shift = %s
				AND time BETWEEN %s AND %s
			ORDER BY time ASC
		""", (
			employee,
			shift_type,
			shift_timings.actual_start,
			shift_timings.actual_end
		), as_dict=1)

		if checkin_logs:
			attendance = get_attendance(self, checkin_logs)
			attnd_name = frappe.db.exists("Attendance",{"employee": employee, "attendance_date":date, "docstatus": 1})
			if attnd_name:
				attnd = frappe.get_doc("Attendance",attnd_name)
				attnd.cancel()
				frappe.msgprint(_("Attendance cancelled : {0} ").format(attnd_name))

			# frappe.throw(f"attendance {attendance} || attnd_name{attnd_name} ")
			# attnd = ''
			# if attnd_name:
			# 	attnd = frappe.get_doc("Attendance", attnd_name)
			# 	attnd.db_set({
			# 		"status": attendance.get("status"),
			# 		"working_hours": attendance.get("working_hours"),
			# 		"late_entry": attendance.get("late_entry"),
			# 		"early_exit": attendance.get("early_exit"),
			# 		"in_time": attendance.get("in_time"),
			# 		"out_time": attendance.get("out_time"),
			# 		"shift": self.shift_name,			
			# 	})
			# 	frappe.msgprint(_("Attendance updated : {0} ").format(attnd.name))

			# else:
			new_attnd = frappe.get_doc({
				"doctype": "Attendance",
				"employee": employee,
				"attendance_date": date,
				"status": attendance.get("status"),
				"working_hours": attendance.get("working_hours"),
				"late_entry": attendance.get("late_entry"),
				"early_exit": attendance.get("early_exit"),
				"in_time": attendance.get("in_time"),
				"out_time": attendance.get("out_time"),
				"shift": self.shift_name,
			})
			new_attnd.insert()
			new_attnd.submit()
			frappe.msgprint(_("Attendance created : {0} ").format(new_attnd.name))

			for log in checkin_logs:
				frappe.db.set_value("Employee Checkin", log.name, "attendance", new_attnd.name)
		frappe.msgprint(_("Attendance marked on {0} for {1} ").format(employee, date))
	else:
		frappe.msgprint(_("Attendance not marked as {0} is holiday for {1} on {2}").format(shift_type, employee, date))

def get_attendance(self, logs):
	"""Return attendance_status, working_hours, late_entry, early_exit, in_time, out_time
	for a set of logs belonging to a single shift.	"""

	shift_doc = frappe.get_doc("Shift Type", self.shift_name)

	late_entry = early_exit = False
	total_working_hours, in_time, out_time = calculate_working_hours(
		logs, shift_doc.determine_check_in_and_check_out, shift_doc.working_hours_calculation_based_on
	)
	
	shift_start = logs[0]["shift_start"]
	shift_end = logs[0]["shift_end"]
	
	if (
		cint(shift_doc.enable_late_entry_marking)
		and in_time
		and in_time > shift_start + timedelta(minutes=cint(shift_doc.late_entry_grace_period))
	):
		late_entry = True

	if (
		cint(shift_doc.enable_early_exit_marking)
		and out_time
		and out_time < shift_end - timedelta(minutes=cint(shift_doc.early_exit_grace_period))
	):
		early_exit = True

	if (
		shift_doc.working_hours_threshold_for_absent
		and total_working_hours < shift_doc.working_hours_threshold_for_absent
	):
		# return "Absent", total_working_hours, late_entry, early_exit, in_time, out_time
		return {
			"status": "Absent",
			"working_hours": total_working_hours,
			"late_entry": late_entry,
			"early_exit": early_exit,
			"in_time": in_time,
			"out_time": out_time,
		}

	if (
		shift_doc.working_hours_threshold_for_half_day
		and total_working_hours < shift_doc.working_hours_threshold_for_half_day
	):
		# return "Half Day", total_working_hours, late_entry, early_exit, in_time, out_time
		return {
			"status": "Half Day",
			"working_hours": total_working_hours,
			"late_entry": late_entry,
			"early_exit": early_exit,
			"in_time": in_time,
			"out_time": out_time,
		}

	# return "Present", total_working_hours, late_entry, early_exit, in_time, out_time
	return {
		"status": "Present",
		"working_hours": total_working_hours,
		"late_entry": late_entry,
		"early_exit": early_exit,
		"in_time": in_time,
		"out_time": out_time,
	}


@frappe.whitelist()
def process_attendance(employee, shift_type, date):
	if attnd:=frappe.db.exists("Attendance",{"employee":employee, "attendance_date":date, "docstatus": 1}):
		attendance = frappe.get_doc("Attendance",attnd)
		attendance.cancel()

	doc = frappe.get_doc("Shift Type", shift_type)
	doc.process_auto_attendance()

@frappe.whitelist()
def cancel_linked_records(employee, date):
	ot = frappe.get_list("OT Log",{"employee":employee, "attendance_date":date, "is_cancelled":0},pluck="name")
	po = frappe.get_list("Personal Out Log",{"employee":employee, "date":date, "is_cancelled":0},pluck="name")
	if ot:
		OT_Log = frappe.qb.DocType("OT Log")
		query_ot = (
            frappe.qb.update(OT_Log)
            .set(OT_Log.is_cancelled, 1)
            .where(OT_Log.name.isin(ot))
        )
		query_ot.run()
		frappe.msgprint(_("Existing OT Records are cancelled"))
	if po:
		Personal_Out_Log = frappe.qb.DocType("Personal Out Log")
		query_po = (
            frappe.qb.update(Personal_Out_Log)
            .set(Personal_Out_Log.is_cancelled, 1)
            .where(Personal_Out_Log.name.isin(po))
        )
		query_po.run()
	return {"ot":ot, "po": po}

def get_checkins(employee, shift_datetime):
	if not (employee and shift_datetime):
		return []
	shift_timings = get_employee_shift_timings(employee, get_datetime(shift_datetime), True)[1] 	#for current shift
	or_filter = {
			"time":["between",[get_datetime_str(shift_timings.actual_start), get_datetime_str(shift_timings.actual_end)]]
	}
	fields = ["date(time) as date", "log_type as type", "time", "source", "name as employee_checkin"]
	attendance = frappe.db.get_value("Attendance", {"employee": employee, "attendance_date": getdate(shift_datetime), "docstatus":1})
	if attendance:
		or_filter["attendance"] = attendance
	data = frappe.get_list("Employee Checkin", filters= {"employee": employee}, or_filters = or_filter, fields=fields, order_by='time')
	if not data:
		return []
	return data

@frappe.whitelist()
def get_emp_checkin(date, employee=None,shift_name=None):
	shift_start_time = frappe.db.get_value("Shift Type", shift_name, 'start_time')
	shift_datetime = datetime.combine(getdate(date), get_time(shift_start_time))
	data = get_checkins(employee, shift_datetime)
	return data

###############################################################################################################


# @frappe.whitelist
# def check_employee_lock_on_save(doc, method=None):
#     employee_id = doc.employee
#     current_user = frappe.session.user

#     cache_key = f"employee_lock::{employee_id}"
#     locked_by = frappe.cache().get_value(cache_key)

#     if locked_by and locked_by != current_user:
#         frappe.throw(f"Employee {employee_id} is currently being edited by {locked_by}")
#     frappe.cache().set_value(cache_key, current_user, expires_in_sec=300)
