# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

from collections import defaultdict

from frappe import _
from frappe.utils import flt, formatdate

from gke_customization.gke_catalog.report.accounts_payable_aging_summary.accounts_payable_aging_summary import (
	PayableOutstandingBase,
	prepare_filters,
)


def execute(filters=None):
	report = PayableOutstandingBase(prepare_filters(filters))
	report.load()

	months = defaultdict(lambda: {"count": 0, "amount": 0.0})
	for row in report.get_invoice_rows():
		key = (row.entry_date.year, row.entry_date.month)  # month of the due date
		months[key]["count"] += 1
		months[key]["amount"] += flt(row.outstanding)

	currency = report.company_currency
	data = []
	total_count, total_amount = 0, 0.0

	for year, month in sorted(months):
		values = months[(year, month)]
		data.append(
			{
				"month": formatdate(f"{year}-{month:02d}-01", "MMMM yyyy"),
				"invoice_count": values["count"],
				"total_amount": values["amount"],
				"currency": currency,
			}
		)
		total_count += values["count"]
		total_amount += values["amount"]

	if data:
		data.append(
			{
				"month": _("Total Payable"),
				"invoice_count": total_count,
				"total_amount": total_amount,
				"currency": currency,
				"bold": 1,
			}
		)

	chart = {
		"data": {
			"labels": [d["month"] for d in data if not d.get("bold")],
			"datasets": [{"values": [d["total_amount"] for d in data if not d.get("bold")]}],
		},
		"type": "bar",
	}

	return get_columns(), data, None, chart, None, 1


def get_columns():
	return [
		{"label": _("Metric"), "fieldname": "month", "fieldtype": "Data", "width": 180},
		{"label": _("Headcount (Invoices)"), "fieldname": "invoice_count", "fieldtype": "Int", "width": 160},
		{
			"label": _("Total Amount Payable"),
			"fieldname": "total_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 200,
		},
		{"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "width": 80},
	]