# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime, timedelta, time
from frappe.utils import get_datetime, getdate, get_time
from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift_timings


class OTRequest(Document):
	def autoname(self):
		# Get company abbreviation
		company_abbr = frappe.db.get_value("Company", self.company, "abbr")
		if company_abbr:
			if self.branch:
				branch_short = self.branch.split('-')[-2] 
				series = f"{company_abbr}-{branch_short}-OT-.#####"
			else:
				series = f"{company_abbr}-OT-.#####"

			self.name = frappe.model.naming.make_autoname(series)
		
	

	def validate(self):

		for child in self.order_request:

			# Validate OT Hours
			if child.ot_hours:
				try:
					ot_value = child.ot_hours

					# Convert string to time
					if isinstance(ot_value, str):
						try:
							ot_time = datetime.strptime(ot_value, "%H:%M:%S").time()
						except ValueError:
							frappe.throw(
								f"Row {child.idx}: Invalid OT Hours format '{ot_value}'. "
								"Please use HH:MM:SS format."
							)

					# If timedelta
					elif isinstance(ot_value, timedelta):
						total_hours = ot_value.total_seconds() / 3600
						ot_time = None

					# If time object
					elif isinstance(ot_value, time):
						ot_time = ot_value

					else:
						frappe.throw(
							f"Row {child.idx}: Unsupported OT Hours type."
						)

					# Convert time → total hours
					if isinstance(ot_value, timedelta):
						pass  # already calculated
					else:
						total_hours = (
							ot_time.hour
							+ (ot_time.minute / 60)
							+ (ot_time.second / 3600)
						)

					# Eligibility rule (1 hour or more)
					child.food_eligibility = (
						"Eligible" if total_hours >= 1 else "Not Eligible"
					)

				except Exception as e:
					frappe.throw(f"Row {child.idx}: Error processing OT Hours. {str(e)}")

			# Validate Work Date & Checkin
			if child.work_start_date and child.employee_id:

				work_date = getdate(child.work_start_date)

				shift_timings = get_employee_shift_timings(child.employee_id, get_datetime(child.work_start_date), True)[1]

				# frappe.throw(f"Shift timings for Employee {child.employee_id} on {child.work_start_date}: {shift_timings}")

				start_datetime = shift_timings.get("actual_start") or get_datetime(f"{work_date} 00:00:00")
				end_datetime = shift_timings.get("actual_end") or get_datetime(f"{work_date} 23:59:59")

				checkins = frappe.get_all(
					"Employee Checkin",
					filters={
						"employee": child.employee_id,
						"time": ["between", [start_datetime, end_datetime]],
					},
					fields=["name", "time"],
					order_by="time desc",
					limit=1
				)

				if checkins:
					last_checkin_time = checkins[0].time
					frappe.msgprint(
						f"Row {child.idx}: Last Checkin for Employee "
						f"{child.employee_id} on {work_date} was at {last_checkin_time}."
					)

		# self.check_attendance_request_exists()
		self.set_max_ot_hrs()
	
	def set_max_ot_hrs(self):
		if self.order_request:
			max_ot = max(
				(get_time(i.ot_hours) for i in self.order_request if i.ot_hours),
				default=None
			)

			if max_ot:
				self.ot_hours = max_ot

	# Added by Aditya at 29-01-2026
	def on_update_after_submit(self):
		if self.get("workflow_state") == "Create Checkin":
			self.check_attendance_request_exists(throw_error=True)
			self.create_checkin()

	def create_checkin(self):
		if not self.order_request:
			frappe.throw("Please add order request")
		
		save_point = "ot_attendance"
		frappe.db.savepoint(save_point)

		try:
			# frappe.msgprint("Create Checkins............")
			for child in self.order_request:
				if child.employee_id and child.ot_hours and child.enable_ot_duration:
					out_time = get_datetime(child.work_end_date)
					in_time = get_datetime(child.work_start_date)
					attendance_date = getdate(child.work_start_date)

					# Create Check-in Entries
					checkin_in_id = self._create_employee_checkin(child.employee_id, in_time, "IN")
					checkin_out_id = self._create_employee_checkin(child.employee_id, out_time, "OUT")
					
					checkin_ids = [checkin_in_id, checkin_out_id]
					# frappe.msgprint(f"Checkin IDs: {checkin_ids}")
					
					# Handle Attendance
					self._handle_attendance(child.employee_id, attendance_date, in_time, out_time, checkin_ids, get_time(child.ot_hours))

			frappe.db.commit()
		except Exception as e:
			frappe.db.rollback(save_point=save_point)
			frappe.log_error(message=f"Error in creating checkin/attendance: {frappe.get_traceback()}", title="Error in creating checkin/attendance", reference_doctype=self.doctype, reference_name=self.name)
			frappe.throw(str(e))


	def check_attendance_request_exists(self, throw_error=False):
		"""
		Check if Attendance Request exists for an employee on a given date.

		:param employee: Employee ID
		:param work_date: date or datetime
		:param throw_error: bool (raise exception if found)
		:return: Attendance Request name or None
		"""
		messages = []
		for child in self.order_request:
			work_date = getdate(child.work_start_date)

			# Check if Attendance already exists
			attendance = frappe.db.exists(
				"Attendance",
				{
					"employee": child.employee_id,
					"attendance_date": work_date,
					"docstatus": 1,
				},
			)

			# If attendance exists → bypass
			if attendance:
				continue
			
			# Check Attendance Request
			attendance_request = frappe.get_all(
				"Attendance Request",
				filters={
					"employee": child.employee_id,
					"from_date": ["<=", work_date],
					"to_date": [">=", work_date],
					"docstatus": 1,
				},
				fields=["name"],
				limit=1,
			)

			if not attendance_request:
				messages.append(
                f"Row {child.idx}: No Attendance Request for "
                f"Employee <b>{child.employee_id}</b> on "
                f"<b>{work_date}</b>"
            )

		if messages:
			msg = "<br>".join(messages)

			if throw_error:
				frappe.throw(msg)
			else:
				frappe.msgprint(msg)			


	def _create_employee_checkin(self, employee, time, log_type):
		"""Creates an Employee Checkin record."""
		checkin = frappe.new_doc("Employee Checkin")
		checkin.employee = employee
		checkin.time = time
		checkin.log_type = log_type
		checkin.source = "Manual Punch"
		checkin.save(ignore_permissions=True)
		return checkin.name

	def _handle_attendance(self, employee, attendance_date, in_time, out_time, checkin_ids, ot_hours):
		"""Handles creation or update of Attendance record."""
		# Check for existing attendance
		attendance_name = frappe.db.exists("Attendance", {
			"employee": employee,
			"attendance_date": attendance_date,
			"docstatus": 1
		})

		if attendance_name:
			self._update_existing_attendance(attendance_name, in_time, out_time, checkin_ids, ot_hours)
		# else:
		# 	self._create_new_attendance(employee, attendance_date, in_time, out_time, checkin_ids)

	def _update_existing_attendance(self, attendance_name, in_time, out_time, checkin_ids, ot_hours):
		"""Updates existing submitted attendance directly using db_set."""

		attendance_doc = frappe.get_doc("Attendance", attendance_name)

		existing_status = attendance_doc.status
		existing_shift = attendance_doc.shift
		existing_working_hours = attendance_doc.get("working_hours") or 0
		existing_in_time = attendance_doc.get("in_time")
		existing_out_time = attendance_doc.get("out_time")
		
		if existing_in_time:
			final_in_time = min(existing_in_time, in_time)
		else:
			final_in_time = in_time
		
		if existing_out_time:
			final_out_time = max(existing_out_time, out_time)
		else:
			final_out_time = out_time

		# Get existing checkins linked to this attendance
		existing_checkins = frappe.get_all(
			"Employee Checkin",
			filters={"attendance": attendance_name},
			pluck="name"
		)

		ot_hrs = get_time(ot_hours)
		total_seconds = ot_hrs.hour * 3600 + ot_hrs.minute * 60 + ot_hrs.second
		float_hours = total_seconds / 3600

		# Calculate new working hours
		total_working_hours = existing_working_hours + float_hours

		# Direct DB Update (No Cancel / No Submit)
		frappe.db.set_value("Attendance", attendance_name, {
			"status": existing_status,
			"shift": existing_shift,
			"in_time": final_in_time,
			"out_time": final_out_time,
			"working_hours": total_working_hours
		})

		# Link checkins
		all_checkins = list(set((checkin_ids or []) + existing_checkins))
		self._link_checkins_to_attendance(all_checkins, attendance_name)

		frappe.db.commit()
	
	def _create_new_attendance(self, employee, attendance_date, in_time, out_time, checkin_ids):
		"""Creates a new attendance record."""
		new_attendance = frappe.new_doc("Attendance")
		new_attendance.employee = employee
		new_attendance.attendance_date = attendance_date
		new_attendance.status = "Present"
		new_attendance.in_time = in_time
		new_attendance.out_time = out_time
		
		if out_time > in_time:
			new_attendance.working_hours = (out_time - in_time).total_seconds() / 3600
			
		new_attendance.insert(ignore_permissions=True)
		new_attendance.submit()
		
		# Link checkins
		self._link_checkins_to_attendance(checkin_ids, new_attendance.name)
		
		frappe.msgprint(f"Attendance created for {employee} on {attendance_date}")
		
	def _link_checkins_to_attendance(self, checkin_ids, attendance_name):
		"""Links the checkin records to the attendance."""
		if checkin_ids and attendance_name:
			for checkin_id in checkin_ids:
				frappe.db.set_value("Employee Checkin", checkin_id, "attendance", attendance_name)

					


@frappe.whitelist()
def fill_employee_details(department_head,branch=None, gender=None):
	filters = {
		# 'department': department,
		'reports_to': department_head,
		'status': 'Active'
	}
	if branch:
		filters.update({ 'branch': branch })
	
	if gender:
		filters.update({ 'gender': gender })
		
	employees = frappe.db.get_all("Employee",
			filters = filters,
			fields = ['name','employee_name']
		)

	if employees:
		return employees
	else:
		frappe.msgprint(f"There is no Employees for Selected Department Head.")
