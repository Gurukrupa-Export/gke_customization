# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt
import itertools
import frappe
from datetime import datetime
from frappe.model.document import Document
from frappe.utils import cint, add_to_date, get_datetime, get_datetime_str, getdate, get_time
from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift_timings
from gurukrupa_customizations.gurukrupa_customizations.doctype.personal_out_gate_pass.personal_out_gate_pass import create_prsnl_out_logs
from hrms.hr.doctype.employee_checkin.employee_checkin import mark_attendance_and_link_log
import itertools
from operator import itemgetter

class HolidayPunch(Document):
	def on_submit(self):
		
		self.update_emp_checkin()
		self.delete_checkin()
		# self.details = []
  
		emp_list = []
		for i in self.details:
			if i.employee:
				if not self.shift_name:
					frappe.throw((f"Shift type missing for Employee: {self.employee}"))
				emp_list.append(i.employee)

		for j in list(set(emp_list)):
			process_attendance(j, self.shift_name, self.date)
			cancel_linked_records(date=self.date, employee=j)
			create_prsnl_out_logs(from_date=self.date, to_date=self.date, employee=j)
			frappe.msgprint("Attendance Updated")

			
	# def validate(self):
	# 	# self.validate_od_punch()
	# 	self.update_emp_checkin()
	# 	self.delete_checkin()
	# 	self.details = []



	@frappe.whitelist()
	def validate_punch(self):
		shift_datetime = datetime.combine(getdate(self.date), get_time(self.start_time))
		shift_det = get_employee_shift_timings(self.employee, shift_datetime, True)[1]
		if not (get_datetime(self.new_punch) > shift_det.actual_start and get_datetime(self.new_punch) < shift_det.actual_end):
			frappe.throw((f"Punch must be in between {shift_det.actual_start} and {shift_det.actual_end}"))

	def update_emp_checkin(self):
		for punch in self.details:
			if punch.employee_checkin:
				doc = frappe.get_doc("Employee Checkin", punch.employee_checkin)
				# frappe.throw("IF")
			else:
				# frappe.throw("ELSE")
				doc = frappe.new_doc("Employee Checkin")
				doc.time = punch.time
				doc.employee = punch.employee
			doc.skip_auto_attendance = 0
			doc.log_type = punch.type
			doc.source = punch.source
			doc.save()

	@frappe.whitelist()
	def search_checkin(self):
		# self.validate_filters()
		self.details = []
		shift_datetime = datetime.combine(getdate(self.date), get_time(self.start_time))
		return get_checkins(self,shift_datetime)
	
	def delete_checkin(self):
		if self.to_be_deleted:
			to_be_deleted = self.to_be_deleted.split(",")
			to_be_deleted = [name for name in to_be_deleted if name]
			for docname in to_be_deleted:
				frappe.delete_doc("Employee Checkin",docname,ignore_missing=1)
			frappe.msgprint((f"Following Employee Checkins deleted: {', '.join(to_be_deleted)}"))
		self.to_be_deleted = None


def get_checkins(self,shift_datetime):
	employee_list = frappe.db.get_list('Employee',filters={'company': self.company,'default_shift':self.shift_name},fields=['name','employee_name'])
	# frappe.throw(str(employee_list))
	# if not (employee and shift_datetime):
	# 	return []
	data_list = []
	for i in employee_list:
		employee = i['name']
		shift_timings = get_employee_shift_timings(employee, get_datetime(shift_datetime), True)[1] 	#for current shift
		or_filter = {
				"time":["between",[get_datetime_str(shift_timings.actual_start), get_datetime_str(shift_timings.actual_end)]]
		}
		fields = ["date(time) as date", "log_type as type", "time", "source", "name as employee_checkin", "employee"]
		attendance = frappe.db.get_value("Attendance", {"employee": employee, "attendance_date": getdate(shift_datetime), "docstatus":1})
		if attendance:
			or_filter["attendance"] = attendance

		# frappe.throw(str(or_filter))
		data = frappe.get_list("Employee Checkin", filters= {"employee": employee}, or_filters = or_filter, fields=fields, order_by='time')
		if not data:
			continue
			# frappe.msgprint(str(employee))
		data_list.append(data)
		# if not data:
		# 	return []
	
	return data_list


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
		frappe.db.sql(f"""update `tabOT Log` set is_cancelled = 1 where name in ('{"', '".join(ot)}')""")
		frappe.msgprint("Existing OT Records are cancelled")
	if po:
		frappe.db.sql(f"""update `tabPersonal Out Log` set is_cancelled = 1 where name in ('{"', '".join(po)}')""")
# 	return {"ot":ot, "po": po}

@frappe.whitelist()
def add_checkins(details,date,start_time,end_time):

	details = frappe.json.loads(details)
	employee_details = {}

	for entry in details:
		employee_id = entry['employee']
		if employee_id not in employee_details:
			employee_details[employee_id] = []
		employee_details[employee_id].append(entry)
	
	all_data = []
	# frappe.throw(str(employee_details))
	
	for j in employee_details:
		length = len(employee_details[j])
		one_data = check_employee_punch(employee_details[j],date,length,start_time,end_time)
		all_data.append(one_data)

	# length = len(employee_details['HR-EMP-00495'])
	# one_data = check_employee_punch(employee_details['HR-EMP-00495'],date,length,start_time,end_time)
	# all_data.append(one_data)
		# break

	merged_data = []
	for sublist in all_data:
		merged_data.extend(sublist)

	# final_merged_data = []
	for m in merged_data:
		m['idx'] = merged_data.index(m)

	# frappe.throw(str(merged_data))
	return merged_data

def check_employee_punch(employee_details,date,length,start_time,end_time):
	if length == 2:
		last_punch_time = datetime.strptime(employee_details[-1]['time'], "%Y-%m-%d %H:%M:%S").time()
		if last_punch_time < datetime.strptime(end_time, "%H:%M:%S").time():
			employee_details = make_in(employee_details)
			employee_details = make_out(employee_details,start_time,end_time)

	else:
		employee_details = make_out(employee_details,start_time,end_time)
		# frappe.throw("ELSE")
	return employee_details


def make_in(employee_details):
	# new_entry = employee_details[-1].copy()
	employee_details.append(
		{
			'date':employee_details[-1]['date'],
			'type':'IN',
			'employee':employee_details[-1]['employee'],
			'time':employee_details[-1]['time'],
			'source':'Manual Punch',
			'idx':'',
		}
	)
	# new_entry['idx'] += 1
	# new_entry['type'] = 'IN'
	# employee_details.append(new_entry)
	return employee_details

def make_out(employee_details,start_time,end_time):

	employee_details.append(
		{
			'date':employee_details[-1]['date'],
			'type':'OUT',
			'employee':employee_details[-1]['employee'],
			'time':employee_details[-1]['date'] + ' ' + end_time,
			'source':'Manual Punch',
			'idx':'',
		}
	)

	# new_entry = employee_details[-1].copy()

	# # new_entry['idx'] += 1
	# new_entry['type'] = 'OUT'
	# new_entry['time'] = new_entry['date'] + ' ' + end_time
	# employee_details.append(new_entry)
	return employee_details