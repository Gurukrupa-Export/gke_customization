# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate

# Material -> item code prefixes. Gold = metal + finding, so Metal -> Finding
# repack entries cancel out inside the same row.
MATERIAL_PREFIXES = {
	# Gold only: M-G (metal) and F-G (finding). Silver (M-S / F-S) and alloys are excluded.
	"Gold": ["M-G-%", "F-G-%"],
	"Diamond": ["D-%"],
	"Gemstone": ["G-%"],
	"Other": ["O-%"],
}

AMOUNT_FIELDS = [
	"opening",
	"batch_issue",
	"extra_issue",
	"total_issue",
	"batch_return",
	"extra_return",
	"total_return",
	"loss",
	"balance",
]


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)
	if filters.detail_warehouse:
		return get_detail_columns(filters), get_detail_data(filters)
	return get_columns(filters), get_data(filters)


def validate_filters(f):
	if not f.from_date or not f.to_date:
		frappe.throw(_("From Date and To Date are required"))
	if getdate(f.from_date) > getdate(f.to_date):
		frappe.throw(_("From Date cannot be after To Date"))
	# Report is gold only (metal + finding), as confirmed by the user
	f.material = "Gold"


def uom(f):
	return "Carat" if f.material in ("Diamond", "Gemstone") else "Gram"


def amount_col(label, fieldname, f, width=120):
	return {
		"label": _(label) + f" ({uom(f)})",
		"fieldname": fieldname,
		"fieldtype": "Float",
		"precision": 3,
		"width": width,
	}


# ---------------------------------------------------------------------------
# Main report
# ---------------------------------------------------------------------------


def get_columns(f):
	return [
		{"label": _("Detail"), "fieldname": "detail", "fieldtype": "Data", "width": 70},
		{"label": _("Employee Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 250},
		{"label": _("Slip Touch"), "fieldname": "slip_touch", "fieldtype": "Data", "width": 110},
		{"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 150},
		{"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
		{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 190},
		{"label": _("Manager"), "fieldname": "manager_name", "fieldtype": "Data", "width": 180},
		{"label": _("Operation"), "fieldname": "operation", "fieldtype": "Link", "options": "Department Operation", "width": 150},
		amount_col("Opening", "opening", f),
		amount_col("Batch Issue", "batch_issue", f),
		amount_col("Extra Issue", "extra_issue", f),
		amount_col("Total Issue", "total_issue", f),
		amount_col("Batch Return", "batch_return", f),
		amount_col("Extra Return", "extra_return", f),
		amount_col("Total Return", "total_return", f),
		amount_col("Loss", "loss", f),
		amount_col("Balance", "balance", f),
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 90},
	]


def get_conditions(f):
	params = {
		"company": f.company,
		"from_date": f.from_date,
		"to_date": f.to_date,
		"wip": "%WIP%",
	}
	conditions = ["sle.is_cancelled = 0", "sle.posting_date <= %(to_date)s", "ifnull(w.employee, '') != ''"]

	if f.company:
		conditions.append("sle.company = %(company)s")

	prefixes = MATERIAL_PREFIXES.get(f.material, MATERIAL_PREFIXES["Gold"])
	item_conditions = []
	for i, prefix in enumerate(prefixes):
		params[f"item_{i}"] = prefix
		item_conditions.append(f"sle.item_code like %(item_{i})s")
	conditions.append("(" + " or ".join(item_conditions) + ")")

	if not f.include_wip:
		conditions.append("w.name not like %(wip)s")
	if f.warehouse:
		conditions.append("sle.warehouse = %(warehouse)s")
		params["warehouse"] = f.warehouse
	if f.detail_warehouse:
		conditions.append("sle.warehouse = %(detail_warehouse)s")
		params["detail_warehouse"] = f.detail_warehouse
	if f.detail_touch:
		conditions.append(f"{TOUCH} = %(detail_touch)s")
		params["detail_touch"] = f.detail_touch
	if f.employee:
		conditions.append("w.employee = %(employee)s")
		params["employee"] = f.employee
	if f.manager:
		conditions.append("e.reports_to = %(manager)s")
		params["manager"] = f.manager
	if f.operation:
		conditions.append("w.custom_operation = %(operation)s")
		params["operation"] = f.operation

	return " and ".join(conditions), params


IN_PERIOD = "sle.posting_date between %(from_date)s and %(to_date)s"
HAS_MWO = "ifnull(se.manufacturing_work_order, '') != ''"
NO_MWO = "ifnull(se.manufacturing_work_order, '') = ''"
IS_LOSS = "ifnull(se.stock_entry_type, '') = 'Process Loss'"
NOT_LOSS = "ifnull(se.stock_entry_type, '') != 'Process Loss'"
# "M-G-22KT-91.75-Y..." -> "22KT-91.75"
TOUCH = "substring_index(substring_index(sle.item_code, '-', 4), '-', -2)"


def get_data(f):
	where, params = get_conditions(f)

	rows = frappe.db.sql(
		f"""
		select
			sle.warehouse,
			w.employee,
			e.employee_name,
			mgr.employee_name as manager_name,
			w.custom_operation as operation,
			dop.department,
			{TOUCH} as slip_touch,
			sum(case when sle.posting_date < %(from_date)s then sle.actual_qty else 0 end) as opening,
			sum(case when {IN_PERIOD} and sle.actual_qty > 0 and {HAS_MWO}
				then sle.actual_qty else 0 end) as batch_issue,
			sum(case when {IN_PERIOD} and sle.actual_qty > 0 and {NO_MWO}
				then sle.actual_qty else 0 end) as extra_issue,
			sum(case when {IN_PERIOD} and sle.actual_qty < 0 and {NOT_LOSS} and {HAS_MWO}
				then -sle.actual_qty else 0 end) as batch_return,
			sum(case when {IN_PERIOD} and sle.actual_qty < 0 and {NOT_LOSS} and {NO_MWO}
				then -sle.actual_qty else 0 end) as extra_return,
			sum(case when {IN_PERIOD} and sle.actual_qty < 0 and {IS_LOSS}
				then -sle.actual_qty else 0 end) as loss,
			sum(sle.actual_qty) as balance
		from `tabStock Ledger Entry` sle
		inner join `tabWarehouse` w on w.name = sle.warehouse
		left join `tabEmployee` e on e.name = w.employee
		left join `tabEmployee` mgr on mgr.name = e.reports_to
		left join `tabDepartment Operation` dop on dop.name = w.custom_operation
		left join `tabStock Entry` se
			on se.name = sle.voucher_no and sle.voucher_type = 'Stock Entry'
		where {where}
		group by sle.warehouse, {TOUCH}, w.employee, e.employee_name, mgr.employee_name,
			w.custom_operation, dop.department
		order by sle.warehouse, {TOUCH}
		""",
		params,
		as_dict=True,
	)

	data = []
	for r in rows:
		for field in ("opening", "batch_issue", "extra_issue", "batch_return", "extra_return", "loss", "balance"):
			r[field] = flt(r[field], 3)
		r.total_issue = flt(r.batch_issue + r.extra_issue, 3)
		r.total_return = flt(r.batch_return + r.extra_return, 3)
		r.material = f.material
		r.status = "Running" if abs(r.balance) > 0.0005 else "Close"
		r.detail = r.warehouse

		if f.status and r.status != f.status:
			continue
		if not f.show_zero_rows and not any(abs(r[field]) > 0.0005 for field in AMOUNT_FIELDS):
			continue
		data.append(r)

	return data


# ---------------------------------------------------------------------------
# Detail mode (used by the popup): every entry of one warehouse
# ---------------------------------------------------------------------------


def get_detail_columns(f):
	return [
		{"label": _("Entry Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{"label": _("Type"), "fieldname": "entry_type", "fieldtype": "Data", "width": 120},
		{"label": _("Batch No (MWO)"), "fieldname": "batch_no", "fieldtype": "Data", "width": 150},
		{"label": _("Sub Category"), "fieldname": "sub_category", "fieldtype": "Data", "width": 120},
		{"label": _("Item"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 200},
		amount_col("Issue Wt", "issue_wt", f, 100),
		amount_col("Receive Wt", "receive_wt", f, 100),
		amount_col("Loss", "loss", f, 90),
		amount_col("Balance", "balance", f, 100),
		{"label": _("Stock Entry"), "fieldname": "voucher_no", "fieldtype": "Link", "options": "Stock Entry", "width": 140},
	]


def get_detail_data(f):
	where, params = get_conditions(f)

	opening = frappe.db.sql(
		f"""
		select sum(sle.actual_qty)
		from `tabStock Ledger Entry` sle
		inner join `tabWarehouse` w on w.name = sle.warehouse
		left join `tabEmployee` e on e.name = w.employee
		where {where} and sle.posting_date < %(from_date)s
		""",
		params,
	)[0][0]
	balance = flt(opening, 3)

	rows = frappe.db.sql(
		f"""
		select
			sle.posting_date, sle.voucher_no, sle.item_code, sle.actual_qty,
			se.stock_entry_type, se.manufacturing_work_order,
			ifnull(mwo.item_sub_category, mwo.item_category) as sub_category
		from `tabStock Ledger Entry` sle
		inner join `tabWarehouse` w on w.name = sle.warehouse
		left join `tabEmployee` e on e.name = w.employee
		left join `tabStock Entry` se
			on se.name = sle.voucher_no and sle.voucher_type = 'Stock Entry'
		left join `tabManufacturing Work Order` mwo on mwo.name = se.manufacturing_work_order
		where {where} and {IN_PERIOD}
		order by sle.posting_date, sle.posting_time, sle.creation
		""",
		params,
		as_dict=True,
	)

	data = [
		{
			"posting_date": f.from_date,
			"entry_type": _("Opening"),
			"batch_no": "",
			"balance": balance,
		}
	]
	for r in rows:
		qty = flt(r.actual_qty, 3)
		has_mwo = bool(r.manufacturing_work_order)
		is_loss = (r.stock_entry_type or "") == "Process Loss"
		row = {
			"posting_date": r.posting_date,
			"voucher_no": r.voucher_no,
			"item_code": r.item_code,
			"batch_no": r.manufacturing_work_order or "SLIP",
			"sub_category": r.sub_category or "",
		}
		if qty > 0:
			row["entry_type"] = _("Batch Issue") if has_mwo else _("Extra Issue")
			row["issue_wt"] = qty
		elif is_loss:
			row["entry_type"] = _("Loss")
			row["loss"] = -qty
		else:
			row["entry_type"] = _("Batch Receive") if has_mwo else _("Extra Receive")
			row["receive_wt"] = -qty
		balance = flt(balance + qty, 3)
		row["balance"] = balance
		data.append(row)

	return data
