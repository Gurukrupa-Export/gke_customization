# Copyright (c) 2025, 8848 Digital LLP and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate
from frappe import _
from frappe.query_builder.functions import IfNull, Sum, Timestamp, Date, Min
from frappe.query_builder import CustomFunction


class PersonalOutEntry(Document):
	def autoname(self):
		company_abbr = frappe.db.get_value("Company", self.company, "abbr")
		if company_abbr:
			if self.branch:
				branch_short = self.branch.split('-')[-2] 
				series = f"{company_abbr}-{branch_short}-POE-.#####"
			else:
				series = f"{company_abbr}-POE-.#####"

			self.name = frappe.model.naming.make_autoname(series)

	def validate(self):
		self.locked_by = frappe.session.user
		#shruti
		if self.employee:
			existing= frappe.db.get_all(
				"Personal Out Entry",
				filters={
					"from_date":self.from_date,
					"to_date":self.to_date,
					"employee":self.employee,
					"name": ["!=", self.name]
				},

				fields=["name", "locked_by"]
			)
			# frappe.throw(f"{existing} ")
			for entry in existing:
				if entry.locked_by and entry.locked_by != self.locked_by or entry.locked_by == self.locked_by:
					form_link = f"/app/personal-out-entry/{entry.name}"
					frappe.throw(
						f"This entry for {self.employee} from  {self.from_date} to {self.to_date} locked by another user: <b>{entry.locked_by}</b><br>"
						f"<a href='{form_link}' target='_blank'>View entry</a>"
					)
		if self.workflow_state == "Create Personal Out":
			self.make_prsnl_out_logs()


	def make_prsnl_out_logs(self):
		if not self.checkin_details:
			return
		for log in self.checkin_details:
			create_prsnl_out_log(log)

		frappe.msgprint(_("Personal Out Records Created/Updated"))
		# self.checkin_details = []

	@frappe.whitelist()
	def get_checkin_details(self, from_log=False):
		EmployeeCheckin = frappe.qb.DocType("Employee Checkin")
		Employee = frappe.qb.DocType("Employee")
		PersonalOutLog = frappe.qb.DocType("Personal Out Log")

		# To_Seconds = CustomFunction("TIME_TO_SEC", ["date"])
		ifelse = CustomFunction("IF", ["condition", "then", "else"])
		Time_Diff = CustomFunction("TIMEDIFF", ["cur_date", "due_date"])
		Time = CustomFunction("Time", ["time"])
		# Sec_To_Time = CustomFunction("SEC_TO_TIME", ["date"])

		emp_det = (
			frappe.qb.from_(EmployeeCheckin)
			.select(
				EmployeeCheckin.employee,
				EmployeeCheckin.employee_name,
				Date(EmployeeCheckin.time).as_('at_date'),
				Sum(ifelse(EmployeeCheckin.log_type == 'OUT', 1, 0)).as_('cnt'),
				EmployeeCheckin.shift_start
				)
			.where(
				(EmployeeCheckin.log_type == 'OUT')
			)
			.groupby(EmployeeCheckin.employee, EmployeeCheckin.shift_start)
			.having(frappe.qb.Field("cnt") > 1)
		).as_('emp_det')

		check_out = (
			frappe.qb.from_(EmployeeCheckin)
			.select(
				EmployeeCheckin.time.as_('checkout'),
				EmployeeCheckin.employee.as_('emp'),
				Date(EmployeeCheckin.time).as_('co_date'),
				EmployeeCheckin.shift_start
			)
			.where(EmployeeCheckin.log_type == 'OUT')
		).as_('check_out')

		check_in = (
			frappe.qb.from_(EmployeeCheckin)
			.select(
				EmployeeCheckin.time,
				EmployeeCheckin.employee,
				Date(EmployeeCheckin.time).as_('ci_date'),
			)
			.where(EmployeeCheckin.log_type == 'IN')
		).as_('check_in')

		pol = (
			frappe.qb.from_(PersonalOutLog)
			.select(
				PersonalOutLog.name,
				PersonalOutLog.approve,
				PersonalOutLog.total_hours,
				PersonalOutLog.employee,
				PersonalOutLog.date,
				PersonalOutLog.out_time
			)
			.where(PersonalOutLog.is_cancelled == 0)
		).as_('pol')

		query = (
			frappe.qb.from_(emp_det)
			.left_join(check_out).on((emp_det.employee == check_out.emp) & (emp_det.at_date == check_out.co_date) & (emp_det.shift_start == check_out.shift_start))
			.left_join(check_in).on((emp_det.employee == check_in.employee) & (emp_det.at_date == check_in.ci_date) & (check_out.checkout < check_in.time))
			.left_join(pol).on((emp_det.employee == pol.employee) & (emp_det.at_date == pol.date) & (Time(check_out.checkout) == pol.out_time))
			.select(
				emp_det.employee,
				emp_det.employee_name,
				emp_det.at_date.as_('date'),
				Time(check_out.checkout).as_('out_time'),
				Time(Min(check_in.time)).as_('in_time'),
				Time(Time_Diff(Min(check_in.time),check_out.checkout)).as_('total_hours'),
				pol.name.as_('po_log'),
				ifelse(pol.name.isnull(), 1, 0).as_('approve'),
				pol.total_hours.as_('approved_hours')
			)
			.groupby(emp_det.employee, emp_det.at_date, check_out.checkout)
			.having(frappe.qb.Field("in_time").isnotnull())
		)
		
		conditions = self.get_conditions(emp_det, pol, Employee, from_log)

		for condition in conditions:
			query = query.where(condition)
	
		data = query.run(as_dict=True)
		# frappe.throw(f"{data}")
		
		self.checkin_details = []
		if not data and not from_log:
			frappe.msgprint(_("No Records were found for the current filters"))
			return
		for row in data:
			if row.po_log:
				row["total_hours"] = row.approved_hours
			self.append("checkin_details", row)


	def get_conditions(self, EmployeeCheckin, PersonalOutLog, Employee, from_log):
		from frappe.utils import getdate
		if not (self.from_date and self.to_date):
			frappe.throw(_("Invalid Date Range"))
		
		conditions = [
			(EmployeeCheckin.at_date.between(getdate(self.from_date), getdate(self.to_date)))
		]

		if from_log:
			conditions.append((PersonalOutLog.name.isnotnull()))
	
		if self.employee:
			conditions.append((EmployeeCheckin.employee == self.employee))
		
		if self.employee_name:
			conditions.append((EmployeeCheckin.employee_name.like(f"%{self.employee_name}%")))
		sub_query_filter = []
		
		if self.company:
			sub_query_filter.append((Employee.company == self.company))
		
		if self.department:
			sub_query_filter.append((Employee.department == self.department))
		
		if self.branch:
			sub_query_filter.append((Employee.branch == self.branch))
		
		if self.designation:
			sub_query_filter.append((Employee.designation == self.designation))
		
		sub_query = (
			frappe.qb.from_(Employee)
			.select(Employee.name)
		)
		for filter in sub_query_filter:
			sub_query = sub_query.where(filter)
		
		conditions.append((EmployeeCheckin.employee.isin(sub_query)))
		
		return conditions

def create_prsnl_out_log(ref_doc):
	if ref_doc.po_log:
		doc = frappe.get_doc("Personal Out Log",ref_doc.po_log)
		if doc.approve and not ref_doc.approve:
			doc.delete()
			return
	else:
		if not ref_doc.approve:
			return
		doc = frappe.new_doc("Personal Out Log")
	fields = ["employee","employee_name","date","out_time","in_time","total_hours","approve"]
	data = {}
	for field in fields:
		data[field] = ref_doc.get(field)

	doc.update(data)
	doc.save()
	return doc.name

@frappe.whitelist()
def create_prsnl_out_logs(from_date=None, to_date = None, employee = None):
	doc = frappe.get_doc("Personal Out Entry")
	doc.from_date = getdate(from_date)
	doc.to_date = getdate(to_date)
	if employee:
		doc.employee = employee
	doc.get_checkin_details()
	doc.save()
