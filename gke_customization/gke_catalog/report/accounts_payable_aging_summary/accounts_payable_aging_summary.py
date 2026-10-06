# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import escape_html, flt, fmt_money, formatdate, nowdate

from gke_customization.gke_catalog.report.accounts_receivable___sd.accounts_receivable___sd import (
	ReceivablePayableReport,
)

# True = Journal Entries with a payable balance are counted as invoices too.
# False = only Purchase Invoices (matches the Purchase Invoice list).
INCLUDE_JOURNAL_ENTRIES = False
INVOICE_VOUCHER_TYPES = (
	("Purchase Invoice", "Journal Entry") if INCLUDE_JOURNAL_ENTRIES else ("Purchase Invoice",)
)
# Not-yet-due invoices are shown only for this many days after the report date
UPCOMING_DAYS = 30

# True = hide invoices whose status is "Partly Paid".
# False = show them with the balance left.
EXCLUDE_PARTLY_PAID = True

# True = amount of a Purchase Invoice is its full Grand Total, even if a part is already paid
# (same as "Sum of Grand Total" in the Purchase Invoice list).
# False = Grand Total minus what is already paid (balance still owed).
SHOW_FULL_GRAND_TOTAL = True

# Month-wise table: show only months of overdue invoices (due date before the report date)
ONLY_OVERDUE_MONTHS = True

OVERDUE_BUCKETS = ["d1_30", "d31_60", "d61_90", "d91_120", "d120_plus"]


class PayableOutstandingBase(ReceivablePayableReport):
	"""Re-uses the Accounts Receivable - SD engine for Payable and exposes the outstanding
	invoice rows (with due date and age) so that summaries can be built on top of them."""

	def assign_date_columns(self):
		# date-wise columns are not needed for the summary report
		pass

	def load(self):
		self.filters.update(
			{
				"account_type": "Payable",
				"naming_by": ["Buying Settings", "supp_master_name"],
				"ageing_based_on": "Due Date",
			}
		)
		self.set_defaults()
		self.party_naming_by = frappe.db.get_value("Buying Settings", None, "supp_master_name")
		self.get_data()

	def get_invoice_rows(self):
		"""Outstanding (> 0) invoice rows with a due date. Each voucher is counted once.
		Amounts are on Grand Total basis (paise kept, rounding adjustment of the invoice removed)."""
		seen = set()
		rows = []
		for row in self.data:
			if not row or row.get("bold"):
				continue
			if row.get("voucher_type") not in INVOICE_VOUCHER_TYPES:
				continue
			if flt(row.get("outstanding")) <= 0 or not row.get("entry_date"):
				continue

			key = (row.voucher_type, row.voucher_no, row.get("payment_term"))
			if key in seen:
				continue
			seen.add(key)
			rows.append(row)

		return self.apply_invoice_details(rows)

	def apply_invoice_details(self, rows):
		"""Use the Purchase Invoice itself to
		- drop partly paid invoices (status "Partly Paid", the same status the Purchase Invoice list uses)
		- show the Grand Total (paise kept) instead of the rounded ledger amount."""
		names = list({r.voucher_no for r in rows if r.voucher_type == "Purchase Invoice"})
		if not names:
			return rows

		invoices = {
			d.name: d
			for d in frappe.get_all(
				"Purchase Invoice",
				filters={"name": ["in", names]},
				fields=[
					"name",
					"status",
					"base_grand_total",
					"base_rounding_adjustment",
				],
			)
		}

		result = []
		for r in rows:
			inv = invoices.get(r.voucher_no) if r.voucher_type == "Purchase Invoice" else None
			if inv:
				if EXCLUDE_PARTLY_PAID and inv.status == "Partly Paid":
					continue

				if SHOW_FULL_GRAND_TOTAL:
					r["outstanding"] = flt(inv.base_grand_total)
				else:
					# rounding_adjustment = rounded_total - grand_total; payments stay deducted
					r["outstanding"] = flt(r.outstanding) - flt(inv.base_rounding_adjustment)
			result.append(r)
		return result


def prepare_filters(filters):
	filters = frappe._dict(filters or {})
	# no filters on the report: use default company and today's date
	if not filters.get("company"):
		filters.company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
			"Global Defaults", "default_company"
		)
	if not filters.get("report_date"):
		filters.report_date = nowdate()
	# age is always calculated as on the report date
	filters.calculate_ageing_with = "Report Date"
	filters.ageing_based_on = "Due Date"
	return filters


def get_bucket(age):
	"""age = report date - due date (in days). > 0 means overdue."""
	if age > 0:
		if age <= 30:
			return "d1_30"
		if age <= 60:
			return "d31_60"
		if age <= 90:
			return "d61_90"
		if age <= 120:
			return "d91_120"
		return "d120_plus"

	if age >= -UPCOMING_DAYS:
		return "upcoming"

	return None  # due after the upcoming window


def get_upcoming_bucket(age):
	"""age = report date - due date (in days). <= 0 means not yet due.
	Buckets count the days AHEAD of the report date; an invoice due today falls in the first bucket."""
	days_ahead = -age
	if days_ahead < 0:
		return None  # already overdue
	if days_ahead <= 30:
		return "d1_30"
	if days_ahead <= 60:
		return "d31_60"
	if days_ahead <= 90:
		return "d61_90"
	if days_ahead <= 120:
		return "d91_120"
	return "d120_plus"


def execute(filters=None):
	report = PayableOutstandingBase(prepare_filters(filters))
	report.load()
	currency = report.company_currency
	invoice_rows = list(report.get_invoice_rows())

	# Tables 1 and 2 (overdue by due date / upcoming = next days from the report date) are shown as HTML above;
	# Table 3 (month-wise) is the report table below them
	message = get_aging_html(
		invoice_rows,
		currency,
		_("Accounts Payable Aging Summary (By Due Date)"),
		lambda row: get_bucket(row.age),
		_("Overdue"),
	)
	message += get_aging_html(
		invoice_rows,
		currency,
		_("Accounts Payable Aging Summary (Post Date - Upcoming)"),
		lambda row: get_upcoming_bucket(row.age),
		_("Upcoming"),
	)
	message += (
		f'<div style="font-size:15px;font-weight:bold;margin:5px 0 0;">'
		f'{escape_html(_("Month-wise Overdue Payable (By Due Date)") if ONLY_OVERDUE_MONTHS else _("Month-wise Payable (By Due Date)"))}</div>'
	)
	data = get_month_rows(invoice_rows, currency)

	return get_month_columns(), data, message, None, None, 1


def get_aging_html(invoice_rows, currency, title, bucket_getter, suffix):
	count = {k: 0 for k in OVERDUE_BUCKETS}
	amount = {k: 0.0 for k in OVERDUE_BUCKETS}

	for row in invoice_rows:
		bucket = bucket_getter(row)
		if bucket not in OVERDUE_BUCKETS:
			continue
		count[bucket] += 1
		amount[bucket] += flt(row.outstanding)

	total_count = sum(count[k] for k in OVERDUE_BUCKETS)
	total_amount = sum(amount[k] for k in OVERDUE_BUCKETS)

	headers = [
		_("Metric"),
		_("Total Payable"),
		_("1 - 30 Days"),
		_("31 - 60 Days"),
		_("61 - 90 Days"),
		_("91 - 120 Days"),
		_("120+ Days"),
		_("Total"),
	]

	count_cells = [total_count] + [count[k] for k in OVERDUE_BUCKETS] + [total_count]
	amount_cells = [total_amount] + [amount[k] for k in OVERDUE_BUCKETS] + [total_amount]

	th_style = "background:#1f3864;color:#fff;text-align:center;vertical-align:middle;"
	td_style = "text-align:right;white-space:nowrap;"

	head_html = "".join(f'<th style="{th_style}">{escape_html(h)}</th>' for h in headers)

	def body_row(label, cells, formatter):
		tds = "".join(f'<td style="{td_style}">{formatter(c)}</td>' for c in cells)
		return f'<tr><td style="font-weight:bold;">{escape_html(label)}</td>{tds}</tr>'

	rows_html = body_row(_("Headcount (Invoices)"), count_cells, lambda c: str(int(c)))
	rows_html += body_row(
		_("Total Amount"), amount_cells, lambda c: fmt_money(c, currency=currency)
	)

	return (
		f'<div style="font-size:15px;font-weight:bold;margin:5px 0 8px;">{escape_html(title)}</div>'
		'<div style="overflow-x:auto;">'
		'<table class="table table-bordered" style="min-width:1000px;margin-bottom:20px;">'
		f"<thead><tr>{head_html}</tr></thead><tbody>{rows_html}</tbody></table></div>"
	)


def get_month_rows(invoice_rows, currency):
	"""Month-on-month (by due date) invoice count and amount."""
	months = defaultdict(lambda: {"count": 0, "amount": 0.0})
	for row in invoice_rows:
		if ONLY_OVERDUE_MONTHS and flt(row.age) <= 0:
			continue  # not yet due
		key = (row.entry_date.year, row.entry_date.month)
		months[key]["count"] += 1
		months[key]["amount"] += flt(row.outstanding)

	if not months:
		return []

	rows = []
	total_count, total_amount = 0, 0.0
	for year, month in sorted(months):
		values = months[(year, month)]
		rows.append(
			{
				"month": formatdate(f"{year}-{month:02d}-01", "MMMM yyyy"),
				"invoice_count": values["count"],
				"total_amount": values["amount"],
				"currency": currency,
			}
		)
		total_count += values["count"]
		total_amount += values["amount"]

	rows.append(
		{
			"month": _("Total Payable"),
			"invoice_count": total_count,
			"total_amount": total_amount,
			"currency": currency,
			"bold": 1,
		}
	)
	return rows


def get_month_columns():
	return [
		{"label": _("Metric"), "fieldname": "month", "fieldtype": "Data", "width": 200},
		{"label": _("Headcount (Invoices)"), "fieldname": "invoice_count", "fieldtype": "Int", "width": 180},
		{"label": _("Total Amount Payable"), "fieldname": "total_amount", "fieldtype": "Float", "width": 240},
	]