# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

"""BOM Dashboard Script - standalone Script Report (one row per BOM order).

Independent of the dashboard page: it has its own config and SQL, so either
can change without touching the other. Open to all roles.
"""

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, getdate, nowdate

# ---- CONFIG (keep in sync with the page's API if you change the BOM flow) ----
SOURCE_SQL = "o.bom_or_cad = 'New BOM'"
DUE_DATE_SQL = "o.delivery_date"
# Order carries its own direct link to BOM (verified via System Console):
# 'bom' is populated on 99.7% of New BOM orders, 'new_bom' as a fallback
# for the rest. tabBOM.custom_order_id was tried first but is always
# blank - real BOMs there link out to Manufacturing Plan / Quotation, not
# back to Order - so no join on tabBOM's own fields is needed at all.
ORDER_BOM_FIELD_SQL = "COALESCE(o.bom, o.new_bom)"

# Built from the real "Order with Customer Approval Final3" workflow
# (33 states, verified via System Console). Every state is mapped so
# nothing falls into "Other Stage" silently.
STAGES = [
	("Not Started", ["Draft", "Un-assigned", "Assigned", "Order BOM"]),
	("On Hold", [
		"On Hold", "Assigned - On-Hold", "Designing - On-Hold", "Sent to QC - On-Hold",
		"BOM QC - On-Hold", "Creating BOM - On-Hold", "Updating BOM - On-Hold",
		"Update Item - On-Hold", "Design Rework in Progress - On Hold",
	]),
	("Update Item", ["Update Item", "Update Designer"]),
	("Update BOM", ["Update BOM", "Reupdate BOM", "Updating BOM"]),
	("Creating BOM", ["Creating BOM", "CAD or BOM", "Create CAD", "Create BOM"]),
	("Designing / Rework", ["Designing", "Design Rework in Progress", "Update Requested"]),
	("BOM QC", ["BOM QC", "Sent to QC"]),
	("Customer Approval", ["Customer Approval", "Customer Approved"]),
	("Approved", ["Approved"]),
	("Rejected / Cancelled", ["Rejected", "Cancelled", "Customer Design Rejected"]),
]
STATE_STAGE = {s: stage for stage, states in STAGES for s in states}
DONE_STAGES = {"Approved", "Rejected / Cancelled"}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.company:
		frappe.throw(_("Please select a Company"))
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Order"), "fieldname": "name", "fieldtype": "Link", "options": "Order", "width": 150},
		{"label": _("Order Date"), "fieldname": "order_date", "fieldtype": "Date", "width": 100},
		{"label": _("Customer"), "fieldname": "customer_name", "fieldtype": "Data", "width": 180},
		{"label": _("Category"), "fieldname": "category", "fieldtype": "Data", "width": 120},
		{"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 70},
		{"label": _("Workflow State"), "fieldname": "workflow_state", "fieldtype": "Data", "width": 160},
		{"label": _("Stage"), "fieldname": "stage", "fieldtype": "Data", "width": 150},
		{"label": _("Assigned To"), "fieldname": "assigned_to", "fieldtype": "Data", "width": 200},
		{"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 100},
		{"label": _("Days Overdue"), "fieldname": "days_overdue", "fieldtype": "Int", "width": 100},
		{"label": _("BOM"), "fieldname": "bom_name", "fieldtype": "Link", "options": "BOM", "width": 160},
		{"label": _("BOM Status"), "fieldname": "bom_status", "fieldtype": "Data", "width": 100},
		{"label": _("BOM Amount"), "fieldname": "bom_amount", "fieldtype": "Currency", "width": 120},
	]


def get_data(filters):
	cond, params = [], {"company": filters.company}
	for key, col in (
		("customer", "o.customer_code"),
		("category", "o.category"),
		("workflow_state", "o.workflow_state"),
		("setting_type", "o.setting_type"),
	):
		if filters.get(key):
			cond.append(f"{col} = %({key})s")
			params[key] = filters[key]
	if filters.get("from_date"):
		cond.append("o.order_date >= %(from_date)s")
		params["from_date"] = getdate(filters.from_date)
	if filters.get("to_date"):
		cond.append("o.order_date < %(to_date)s")  # Datetime column: include the whole day
		params["to_date"] = add_days(getdate(filters.to_date), 1)
	if filters.get("assigned_to"):
		cond.append("o._assign LIKE %(assigned_to)s")
		params["assigned_to"] = f'%"{filters.assigned_to}"%'
	extra = "".join(f" AND {c}" for c in cond)

	rows = frappe.db.sql(
		f"""
		SELECT o.name, o.order_date, cust.customer_name, o.category, o.qty,
			o.workflow_state, o._assign, {DUE_DATE_SQL} AS due_date,
			b.name AS bom_name, b.docstatus AS bom_docstatus, b.is_active AS bom_is_active,
			COALESCE(b.total_bom_amount, 0) AS bom_amount
		FROM `tabOrder` o
		LEFT JOIN `tabCustomer` cust ON cust.name = o.customer_code
		LEFT JOIN `tabBOM` b ON b.name = {ORDER_BOM_FIELD_SQL} AND b.docstatus != 2
		WHERE {SOURCE_SQL} AND o.docstatus != 2 AND o.company = %(company)s{extra}
		ORDER BY o.order_date DESC, o.name
		""",
		params,
		as_dict=True,
	)

	today = getdate(nowdate())
	for row in rows:
		row.stage = STATE_STAGE.get(row.workflow_state, "Other Stage")
		row.assigned_to = ", ".join(frappe.parse_json(row.pop("_assign") or "[]"))
		overdue = 0
		if row.due_date and row.stage not in DONE_STAGES:
			overdue = max(date_diff(today, getdate(row.due_date)), 0)
		row.days_overdue = overdue
		if row.bom_name:
			row.bom_status = "Draft" if row.bom_docstatus == 0 else ("Active" if row.bom_is_active else "Inactive")
		else:
			row.bom_status = "No BOM"
		row.pop("bom_docstatus", None)
		row.pop("bom_is_active", None)
	return rows