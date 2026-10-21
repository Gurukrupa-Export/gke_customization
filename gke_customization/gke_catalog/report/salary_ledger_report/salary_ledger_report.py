# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate

# Users with any of these roles can see every employee; everyone else sees only their own ledger.
HR_ROLES = {"System Manager", "HR Manager", "HR User", "GK HR"}

# Fixed columns as in the Salary Ledger format: (column label, fieldname, salary components)
EARNING_COLUMNS = [
	("Basic", "basic", ["Basic"]),
	("Washing", "washing", ["Washing Allowance", "Washing Allowance New"]),
	("House Rent", "house_rent", ["House Rent Allowance"]),
	("Conveyance", "conveyance", ["Conveyance Allowance"]),
	("Medical", "medical", ["Medical Allowance"]),
	("Attire Allowance", "attire_allowance", ["Attire Allowance"]),
]
DEDUCTION_COLUMNS = [
	("E.S.I.", "esi", ["Employees State Insurance Corporation"]),
	("P.F.", "pf", ["Provident Fund"]),
	("P.T.", "pt", ["Professional Tax"]),
	("LWF", "lwf", ["Labor Welfare Fund"]),
	("TDS", "tds", ["Income Tax"]),
]


def execute(filters=None):
	f = frappe._dict(filters or {})
	validate_filters(f)
	apply_access(f)

	slips = get_slips(f)
	if not slips:
		return get_columns(), []

	details = get_details([s.name for s in slips])

	data = []
	for s in slips:
		row = {
			"employee": s.employee,
			"employee_name": s.employee_name,
			"month": getdate(s.start_date).strftime("%b - %Y"),
			"salary": to_number(s.custom_gross_salary),
			"work_day": flt(s.payment_days) + flt(s.custom_extra_payment_days),
			"gross_pay": flt(s.gross_pay),
			"total_deduction": flt(s.total_deduction),
			"net_pay": flt(s.net_pay),
			"paymode": s.salary_mode,
		}
		slip = details.get(s.name, {"earnings": {}, "deductions": {}})
		for _label, field, comps in EARNING_COLUMNS:
			row[field] = sum(slip["earnings"].get(c, 0) for c in comps)
		for _label, field, comps in DEDUCTION_COLUMNS:
			row[field] = sum(slip["deductions"].get(c, 0) for c in comps)
		data.append(row)

	return get_columns(), data


def validate_filters(f):
	if not f.from_date or not f.to_date:
		frappe.throw(_("From Date and To Date are required"))
	if getdate(f.from_date) > getdate(f.to_date):
		frappe.throw(_("From Date cannot be after To Date"))


def apply_access(f):
	"""Non-HR users can only see their own salary ledger."""
	if set(frappe.get_roles()) & HR_ROLES:
		return
	employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
	if not employee:
		frappe.throw(_("No Employee record is linked to your user."), frappe.PermissionError)
	f.employee = employee


def to_number(value):
	if value in (None, ""):
		return 0
	return flt(str(value).replace(",", ""))


def get_slips(f):
	conditions = ["ss.start_date >= %(from_date)s", "ss.end_date <= %(to_date)s"]
	conditions.append("ss.docstatus in (0, 1)" if f.include_draft else "ss.docstatus = 1")
	params = {"from_date": f.from_date, "to_date": f.to_date}

	for key, column in (
		("company", "ss.company"),
		("branch", "ss.branch"),
		("employee", "ss.employee"),
		("department", "ss.department"),
	):
		if f.get(key):
			conditions.append(f"{column} = %({key})s")
			params[key] = f.get(key)

	return frappe.db.sql(
		f"""
		select
			ss.name, ss.employee, ss.employee_name, ss.department, ss.branch,
			ss.start_date, ss.end_date,
			ss.custom_gross_salary, ss.payment_days, ss.custom_extra_payment_days,
			ss.gross_pay, ss.total_deduction, ss.net_pay,
			emp.salary_mode
		from `tabSalary Slip` ss
		left join `tabEmployee` emp on emp.name = ss.employee
		where {" and ".join(conditions)}
		order by ss.employee_name, ss.start_date
		""",
		params,
		as_dict=True,
	)


def get_details(slip_names):
	"""{slip: {"earnings": {component: amount}, "deductions": {...}}}
	Statistical components are skipped because they are not part of Gross Pay."""
	rows = frappe.db.sql(
		"""
		select parent, parentfield, salary_component, sum(amount) as amount
		from `tabSalary Detail`
		where parenttype = 'Salary Slip'
			and parent in %(names)s
			and parentfield in ('earnings', 'deductions')
			and ifnull(statistical_component, 0) = 0
			and ifnull(do_not_include_in_total, 0) = 0
		group by parent, parentfield, salary_component
		""",
		{"names": tuple(slip_names)},
		as_dict=True,
	)
	details = {}
	for r in rows:
		details.setdefault(r.parent, {"earnings": {}, "deductions": {}})
		details[r.parent][r.parentfield][r.salary_component] = flt(r.amount)
	return details


def currency_col(label, field, width=110):
	return {"label": label, "fieldname": field, "fieldtype": "Currency", "width": width}


def get_columns():
	columns = [
		{"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
		{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
		{"label": _("Month"), "fieldname": "month", "fieldtype": "Data", "width": 100},
		currency_col(_("Salary"), "salary"),
		{"label": _("Work Day"), "fieldname": "work_day", "fieldtype": "Float", "precision": 2, "width": 90},
	]
	for label, field, _comps in EARNING_COLUMNS:
		columns.append(currency_col(_(label), field))
	columns.append(currency_col(_("Gross Salary"), "gross_pay", 120))
	for label, field, _comps in DEDUCTION_COLUMNS:
		columns.append(currency_col(_(label), field, 95))
	columns += [
		currency_col(_("Total Deduct"), "total_deduction", 115),
		currency_col(_("Net Payable"), "net_pay", 120),
		{"label": _("Paymode"), "fieldname": "paymode", "fieldtype": "Data", "width": 90},
	]
	return columns
