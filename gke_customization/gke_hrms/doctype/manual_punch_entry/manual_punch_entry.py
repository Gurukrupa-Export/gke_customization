# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cint, add_to_date, get_datetime, get_datetime_str, getdate, get_time
from datetime import datetime
import itertools
from hrms.hr.doctype.employee_checkin.employee_checkin import mark_attendance_and_link_log
from gurukrupa_customizations.gurukrupa_customizations.doctype.personal_out_gate_pass.personal_out_gate_pass import create_prsnl_out_logs
from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift_timings

class ManualPunchEntry(Document):
	def on_update(self):
		if self.workflow_state == "Create Attendance":
			if self.employee:
				if not self.shift_name:
					frappe.throw(_('Shift type missing for Employee: {0}').format(self.employee))
				process_attendance(self.employee, self.shift_name, self.date)
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
		if self.employee:				
			existing = frappe.db.get_all(
				"Manual Punch Entry",
				filters={
					"employee": self.employee,
					"date": self.date,
					"name": ["!=", self.name],
				},
				fields=["name", "locked_by"]
			)

			for entry in existing:
				if entry.locked_by and entry.locked_by != self.locked_by:
					form_link = f"/app/manual-punch-entry/{entry.name}"
					frappe.throw(
						f"This entry for {self.employee} at  {self.date} locked by another user: <b>{entry.locked_by}</b><br>"
						f"<a href='{form_link}' target='_blank'>View entry</a>"
					)


	@frappe.whitelist()
	def validate_punch(self):
		shift_datetime = datetime.combine(getdate(self.date), get_time(self.start_time))
		shift_det = get_employee_shift_timings(self.employee, shift_datetime, True)[1]
		if not (get_datetime(self.new_punch) > shift_det.actual_start and get_datetime(self.new_punch) < shift_det.actual_end):
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
		return get_checkins(self.employee, shift_datetime)

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
			shift_ass = frappe.db.get_value("Shift Assignment",
					{"employee": self.employee,
	  					"start_date": ["<=", self.date],
						"end_date": [">=", self.date],
						"docstatus": 1
	  				},
					['name','shift_type'], as_dict=1)
			shift_type = ''
			if shift_ass:
				shift_type = shift_ass.shift_type
			else: 
				if emp:
					shift_type = emp.get("default_shift")
			if emp:
				self.employee = emp.get('name')
				self.employee_name = emp.get("employee_name")
				self.shift_name = shift_type
				if self.shift_name:
					self.start_time, self.end_time = frappe.db.get_value("Shift Type", self.shift_name,['start_time', 'end_time'])
		if not self.employee:
			frappe.msgprint(_("Employee is Mandatory"))


def process_attendance(employee, shift_type, date):
	if attnd:=frappe.db.exists("Attendance",{"employee":employee, "attendance_date":date, "docstatus": 1}):
		attendance = frappe.get_doc("Attendance",attnd)
		attendance.cancel()
	doc = frappe.get_doc("Shift Type", shift_type)
	if (
		not cint(doc.enable_auto_attendance)
		or not doc.process_attendance_after
		or not doc.last_sync_of_checkin
	):
		return

	filters = {
		"skip_auto_attendance": 0,
		"attendance": ("is", "not set"),
		"time": (">=", doc.process_attendance_after),
		"shift_actual_end": ("<", doc.last_sync_of_checkin),
		"shift": doc.name,
		"employee": employee
	}
	logs = frappe.db.get_list(
		"Employee Checkin", fields="*", filters=filters, order_by="employee,time"
	)

	for key, group in itertools.groupby(
		logs, key=lambda x: (x["employee"], x["shift_actual_start"])
	):
		if not doc.should_mark_attendance(employee, date):
				continue

		single_shift_logs = list(group)
		(
			attendance_status,
			working_hours,
			late_entry,
			early_exit,
			in_time,
			out_time,
		) = doc.get_attendance(single_shift_logs)
		

		mark_attendance_and_link_log(
			single_shift_logs,
			attendance_status,
			key[1].date(),
			working_hours,
			late_entry,
			early_exit,
			in_time,
			out_time,
			doc.name,
		)

	for employee in doc.get_assigned_employees(doc.process_attendance_after, True):
		doc.mark_absent_for_dates_with_no_attendance(employee)

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
