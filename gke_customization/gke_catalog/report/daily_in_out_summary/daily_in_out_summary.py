# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import add_days, flt, get_first_day, getdate, nowdate

ITEM_LIKE_CONDITIONS = "(item_code LIKE 'D-Polished%%' OR item_code LIKE 'D-LGD%%')"


def execute(filters=None):
	filters = frappe._dict(filters or {})

	today = getdate(nowdate())
	from_date = getdate(filters.from_date) if filters.from_date else get_first_day(today)
	to_date = getdate(filters.to_date) if filters.to_date else today
	company = filters.company

	columns = get_columns()
	data = get_data(company, from_date, to_date)

	return columns, data


def get_columns():
	return [
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 100},
		{"label": _("Opening Stock (Crt)"), "fieldname": "opening_stock", "fieldtype": "Float", "width": 150},
		{"label": _("Inward Qty (Crt)"), "fieldname": "inward_qty", "fieldtype": "Float", "width": 140},
		{"label": _("Return Qty (Crt)"), "fieldname": "return_qty", "fieldtype": "Float", "width": 140},
		{"label": _("Total Stock (Crt)"), "fieldname": "total_stock", "fieldtype": "Float", "width": 140},
		{"label": _("Supply Crt (Sold Qty)"), "fieldname": "supply_qty", "fieldtype": "Float", "width": 160},
		{"label": _("Sales return Qty (Crt)"), "fieldname": "sales_return_qty", "fieldtype": "Float", "width": 140},
		{"label": _("Closing Stock (Crt)"), "fieldname": "closing_stock", "fieldtype": "Float", "width": 150},
	]


def get_data(company, from_date, to_date):
	opening_stock = get_opening_balance(company, from_date)

	pr_daily = get_daily_purchase_receipt_data(company, from_date, to_date)
	dn_daily = get_daily_delivery_note_data(company, from_date, to_date)
	si_return_daily = get_daily_sales_invoice_return_data(company, from_date, to_date)

	data = []
	current_date = from_date
	balance = opening_stock

	while current_date <= to_date:
		pr = pr_daily.get(current_date, {"inward": 0.0, "return": 0.0})
		supply = dn_daily.get(current_date, 0.0)
		sales_return_qty = si_return_daily.get(current_date, 0.0)

		opening = balance
		inward = pr["inward"]
		return_qty = pr["return"]
		total_stock = opening + inward - return_qty
		closing = total_stock - supply + sales_return_qty

		data.append(
			{
				"date": current_date,
				"opening_stock": opening,
				"inward_qty": inward,
				"return_qty": return_qty,
				"total_stock": total_stock,
				"supply_qty": supply,
				"sales_return_qty": sales_return_qty,
				"closing_stock": closing,
			}
		)

		balance = closing
		current_date = add_days(current_date, 1)

	return data


@frappe.whitelist()
def get_summary(company=None):
	today = getdate(nowdate())

	current_month_start = get_first_day(today)

	previous_month_end = add_days(current_month_start, -1)
	previous_month_start = get_first_day(previous_month_end)

	fiscal_year = frappe.db.get_value(
		"Fiscal Year",
		{"year_start_date": ["<=", today], "year_end_date": [">=", today]},
		["year_start_date"],
	)
	fy_start = getdate(fiscal_year) if fiscal_year else get_first_day(today, 0)

	periods = {
		"today": (today, today),
		"current_month": (current_month_start, today),
		"previous_month": (previous_month_start, previous_month_end),
		"current_fy": (fy_start, today),
	}

	summary = {}
	for key, (from_date, to_date) in periods.items():
		summary[key] = get_period_summary(company, from_date, to_date)
		summary[key]["from_date"] = from_date
		summary[key]["to_date"] = to_date

	return summary


def get_period_summary(company, from_date, to_date):
	opening = get_opening_balance(company, from_date)

	pr_daily = get_daily_purchase_receipt_data(company, from_date, to_date)
	dn_daily = get_daily_delivery_note_data(company, from_date, to_date)
	si_return_daily = get_daily_sales_invoice_return_data(company, from_date, to_date)

	inward = sum(row["inward"] for row in pr_daily.values())
	return_qty = sum(row["return"] for row in pr_daily.values())
	supply_qty = sum(dn_daily.values())
	sales_return_qty = sum(si_return_daily.values())

	total_stock = opening + inward - return_qty
	closing = total_stock - supply_qty + sales_return_qty

	return {
		"opening_stock": opening,
		"inward_qty": inward,
		"return_qty": return_qty,
		"total_stock": total_stock,
		"supply_qty": supply_qty,
		"sales_return_qty": sales_return_qty,
		"closing_stock": closing,
	}


@frappe.whitelist()
def get_detail_vouchers(company=None, from_date=None, to_date=None, key=None):
	from_date = getdate(from_date)
	to_date = getdate(to_date)

	params = {"from_date": from_date, "to_date": to_date, "company": company}

	if key in ("inward_qty", "return_qty"):
		doctype = "Purchase Receipt"
		company_condition = "AND pr.company = %(company)s" if company else ""
		qty_condition = "pri.qty > 0" if key == "inward_qty" else "pri.qty < 0"
		rows = frappe.db.sql(
			f"""
			SELECT DISTINCT pr.name
			FROM `tabPurchase Receipt Item` pri
			INNER JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
			WHERE pr.docstatus = 1
				AND pr.posting_date BETWEEN %(from_date)s AND %(to_date)s
				AND {qty_condition}
				AND {ITEM_LIKE_CONDITIONS.replace("item_code", "pri.item_code")}
				{company_condition}
			""",
			params,
			as_list=True,
		)
	elif key == "supply_qty":
		doctype = "Delivery Note"
		company_condition = "AND dn.company = %(company)s" if company else ""
		rows = frappe.db.sql(
			f"""
			SELECT DISTINCT dn.name
			FROM `tabDelivery Note Item` dni
			INNER JOIN `tabDelivery Note` dn ON dn.name = dni.parent
			WHERE dn.docstatus = 1
				AND dn.posting_date BETWEEN %(from_date)s AND %(to_date)s
				AND {ITEM_LIKE_CONDITIONS.replace("item_code", "dni.item_code")}
				{company_condition}
			""",
			params,
			as_list=True,
		)
	elif key == "sales_return_qty":
		doctype = "Sales Invoice"
		company_condition = "AND si.company = %(company)s" if company else ""
		rows = frappe.db.sql(
			f"""
			SELECT DISTINCT si.name
			FROM `tabSales Invoice Item` sii
			INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
			WHERE si.docstatus = 1
				AND si.is_return = 1
				AND si.update_stock = 1
				AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
				AND {ITEM_LIKE_CONDITIONS.replace("item_code", "sii.item_code")}
				{company_condition}
			""",
			params,
			as_list=True,
		)
	else:
		frappe.throw(_("Invalid detail key: {0}").format(key))

	return {"doctype": doctype, "names": [row[0] for row in rows]}


def get_opening_balance(company, from_date):
	company_condition = ""
	params = {"from_date": from_date}
	if company:
		company_condition = "AND sle.company = %(company)s"
		params["company"] = company

	result = frappe.db.sql(
		f"""
		SELECT SUM(t.qty_after_transaction) AS opening_stock
		FROM (
			SELECT
				sle.item_code,
				sle.warehouse,
				sle.qty_after_transaction,
				ROW_NUMBER() OVER (
					PARTITION BY sle.item_code, sle.warehouse
					ORDER BY sle.posting_datetime DESC, sle.creation DESC
				) AS rn
			FROM `tabStock Ledger Entry` sle
			WHERE sle.is_cancelled = 0
				AND sle.posting_date < %(from_date)s
				AND {ITEM_LIKE_CONDITIONS.replace("item_code", "sle.item_code")}
				{company_condition}
		) t
		WHERE t.rn = 1
		""",
		params,
		as_dict=True,
	)

	return flt(result[0].opening_stock) if result else 0.0


def get_daily_purchase_receipt_data(company, from_date, to_date):
	company_condition = ""
	params = {"from_date": from_date, "to_date": to_date}
	if company:
		company_condition = "AND pr.company = %(company)s"
		params["company"] = company

	rows = frappe.db.sql(
		f"""
		SELECT
			pr.posting_date AS posting_date,
			SUM(CASE WHEN pri.qty > 0 THEN pri.qty ELSE 0 END) AS inward,
			SUM(CASE WHEN pri.qty < 0 THEN ABS(pri.qty) ELSE 0 END) AS return_qty
		FROM `tabPurchase Receipt Item` pri
		INNER JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
		WHERE pr.docstatus = 1
			AND pr.posting_date BETWEEN %(from_date)s AND %(to_date)s
			AND {ITEM_LIKE_CONDITIONS.replace("item_code", "pri.item_code")}
			{company_condition}
		GROUP BY pr.posting_date
		""",
		params,
		as_dict=True,
	)

	result = defaultdict(lambda: {"inward": 0.0, "return": 0.0})
	for row in rows:
		result[getdate(row.posting_date)] = {
			"inward": flt(row.inward),
			"return": flt(row.return_qty),
		}

	return result


def get_daily_delivery_note_data(company, from_date, to_date):
	company_condition = ""
	params = {"from_date": from_date, "to_date": to_date}
	if company:
		company_condition = "AND dn.company = %(company)s"
		params["company"] = company

	rows = frappe.db.sql(
		f"""
		SELECT
			dn.posting_date AS posting_date,
			SUM(dni.qty) AS net_supply
		FROM `tabDelivery Note Item` dni
		INNER JOIN `tabDelivery Note` dn ON dn.name = dni.parent
		WHERE dn.docstatus = 1
			AND dn.posting_date BETWEEN %(from_date)s AND %(to_date)s
			AND {ITEM_LIKE_CONDITIONS.replace("item_code", "dni.item_code")}
			{company_condition}
		GROUP BY dn.posting_date
		""",
		params,
		as_dict=True,
	)

	return {getdate(row.posting_date): flt(row.net_supply) for row in rows}


def get_daily_sales_invoice_return_data(company, from_date, to_date):
	company_condition = ""
	params = {"from_date": from_date, "to_date": to_date}
	if company:
		company_condition = "AND si.company = %(company)s"
		params["company"] = company

	rows = frappe.db.sql(
		f"""
		SELECT
			si.posting_date AS posting_date,
			SUM(ABS(sii.qty)) AS return_qty
		FROM `tabSales Invoice Item` sii
		INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
		WHERE si.docstatus = 1
			AND si.is_return = 1
			AND si.update_stock = 1
			AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
			AND {ITEM_LIKE_CONDITIONS.replace("item_code", "sii.item_code")}
			{company_condition}
		GROUP BY si.posting_date
		""",
		params,
		as_dict=True,
	)

	return {getdate(row.posting_date): flt(row.return_qty) for row in rows}
