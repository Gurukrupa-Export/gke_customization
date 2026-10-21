# Accounts Payable Aging Summary Report
# Logic: same as Accounts Payable / AP Summary (Payment Ledger based).
# Every open voucher (Purchase Invoice, Journal Entry, unallocated Payment Entry,
# Debit Note) is taken with its outstanding and bucketed by Due Date vs Aging date.

import frappe
from frappe import _
from frappe.utils import date_diff, flt, getdate, nowdate

from erpnext.accounts.report.accounts_receivable.accounts_receivable import (
	ReceivablePayableReport,
)

# Select option in filter -> Supplier Group name in master
SUPPLIER_TYPE_MAP = {
	"All Suppliers": None,
	"Diamond": "Diamond",
}

OVERDUE_BUCKETS = ["1-30", "31-60", "61-90", "91-120", "120+"]
UPCOMING_BUCKETS = ["Due Today", "1-30", "31-60", "61-90", "91+"]


def execute(filters=None):
	filters = frappe._dict(filters or {})
	# Only Supplier filter is shown; company = default company, aging as on today
	filters.company = (
		frappe.defaults.get_user_default("Company")
		or frappe.db.get_single_value("Global Defaults", "default_company")
		or frappe.db.get_value("Company", {}, "name")
	)
	if not filters.company:
		frappe.throw(_("Please set a default Company"))

	report_date = getdate(nowdate())
	rows = get_ap_rows(filters, report_date)
	data = build_data(rows, report_date)
	for d in data:
		d["company"] = filters.company
	return get_columns(), data


def get_ap_rows(filters, report_date):
	"""Run the standard Accounts Payable logic (same source as AP Summary)."""
	ap_filters = frappe._dict(
		{
			"company": filters.company,
			"report_date": report_date,
			"ageing_based_on": "Due Date",
			"calculate_ageing_with": "Report Date",
			"range": "30, 60, 90, 120",
			"range1": 30,
			"range2": 60,
			"range3": 90,
			"range4": 120,
			"based_on_payment_terms": 0,
			"party_type": "Supplier",
		}
	)

	supplier_group = SUPPLIER_TYPE_MAP.get(filters.supplier_type or "All Suppliers")
	if supplier_group:
		# Filters on Supplier master's current group (same as AP Summary)
		ap_filters.supplier_group = supplier_group

	args = {
		"account_type": "Payable",
		"naming_by": ["Buying Settings", "supp_master_name"],
	}
	result = ReceivablePayableReport(ap_filters).run(args)
	return (result[1] if result and len(result) > 1 else []) or []


def build_data(rows, report_date):
	rows = [r for r in rows if r.get("voucher_no") and flt(r.get("outstanding"), 2)]
	if not rows:
		return []

	suppliers = list({r.get("party") for r in rows if r.get("party")})
	supplier_info = {
		s.name: s
		for s in frappe.get_all(
			"Supplier",
			filters={"name": ["in", suppliers]},
			fields=["name", "supplier_name", "supplier_group"],
		)
	}

	data = []
	for r in rows:
		due_date = getdate(r.get("due_date") or r.get("posting_date"))
		age = date_diff(report_date, due_date)  # +ve = overdue, -ve = not yet due
		status, bucket = get_bucket(age)
		info = supplier_info.get(r.get("party")) or frappe._dict()

		data.append(
			{
				"supplier": r.get("party"),
				"supplier_name": info.get("supplier_name") or r.get("party_name"),
				"supplier_group": info.get("supplier_group"),
				"voucher_type": r.get("voucher_type"),
				"voucher_no": r.get("voucher_no"),
				"posting_date": r.get("posting_date"),
				"due_date": due_date,
				"outstanding": flt(r.get("outstanding"), 2),
				"age": age,
				"status": status,
				"bucket": bucket,
				"due_month": due_date.strftime("%B %Y"),
				"due_month_key": due_date.strftime("%Y-%m"),
			}
		)

	data.sort(key=lambda d: (d["due_date"], d["supplier"] or ""))
	return data


def get_bucket(age):
	if age > 0:
		if age <= 30:
			return "Overdue", "1-30"
		if age <= 60:
			return "Overdue", "31-60"
		if age <= 90:
			return "Overdue", "61-90"
		if age <= 120:
			return "Overdue", "91-120"
		return "Overdue", "120+"

	days_left = -age
	if days_left == 0:
		return "Not Yet Due", "Due Today"
	if days_left <= 30:
		return "Not Yet Due", "1-30"
	if days_left <= 60:
		return "Not Yet Due", "31-60"
	if days_left <= 90:
		return "Not Yet Due", "61-90"
	return "Not Yet Due", "91+"


def get_columns():
	return [
		{"label": _("Supplier"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 110},
		{"label": _("Supplier Name"), "fieldname": "supplier_name", "fieldtype": "Data", "width": 180},
		{"label": _("Supplier Group"), "fieldname": "supplier_group", "fieldtype": "Link", "options": "Supplier Group", "width": 120},
		{"label": _("Voucher Type"), "fieldname": "voucher_type", "fieldtype": "Data", "width": 130},
		{"label": _("Voucher No"), "fieldname": "voucher_no", "fieldtype": "Dynamic Link", "options": "voucher_type", "width": 170},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 100},
		{"label": _("Outstanding Amount"), "fieldname": "outstanding", "fieldtype": "Currency", "width": 150},
		{"label": _("Age (Days)"), "fieldname": "age", "fieldtype": "Data", "width": 90},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
		{"label": _("Bucket"), "fieldname": "bucket", "fieldtype": "Data", "width": 90},
		{"label": _("Due Month"), "fieldname": "due_month", "fieldtype": "Data", "width": 120},
		{"label": _("Due Month Key"), "fieldname": "due_month_key", "fieldtype": "Data", "hidden": 1},
	]