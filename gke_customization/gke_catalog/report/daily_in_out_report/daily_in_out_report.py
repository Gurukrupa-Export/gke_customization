# Copyright (c) 2026
# Daily In-Out Report (Script Report, Purchase Receipt / Delivery Note)

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
		{"label": _("Closing Stock (Crt)"), "fieldname": "closing_stock", "fieldtype": "Float", "width": 150},
	]


def get_data(company, from_date, to_date):
	opening_stock = get_opening_balance(company, from_date)

	pr_daily = get_daily_purchase_receipt_data(company, from_date, to_date)
	dn_daily = get_daily_delivery_note_data(company, from_date, to_date)

	data = []
	current_date = from_date
	balance = opening_stock

	while current_date <= to_date:
		pr = pr_daily.get(current_date, {"inward": 0.0, "return": 0.0})
		supply = dn_daily.get(current_date, 0.0)

		opening = balance
		inward = pr["inward"]
		return_qty = pr["return"]
		total_stock = opening + inward - return_qty
		closing = total_stock - supply

		data.append(
			{
				"date": current_date,
				"opening_stock": opening,
				"inward_qty": inward,
				"return_qty": return_qty,
				"total_stock": total_stock,
				"supply_qty": supply,
				"closing_stock": closing,
			}
		)

		balance = closing
		current_date = add_days(current_date, 1)

	return data


def get_opening_balance(company, from_date):
	company_condition = ""
	params = {"from_date": from_date}
	if company:
		company_condition = "AND pr.company = %(company)s"
		params["company"] = company

	pr_result = frappe.db.sql(
		f"""
		SELECT
			SUM(CASE WHEN pr.is_return = 0 THEN pri.qty ELSE 0 END) AS inward,
			SUM(CASE WHEN pr.is_return = 1 THEN ABS(pri.qty) ELSE 0 END) AS return_qty
		FROM `tabPurchase Receipt Item` pri
		INNER JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
		WHERE pr.docstatus = 1
			AND pr.posting_date < %(from_date)s
			AND {ITEM_LIKE_CONDITIONS.replace("item_code", "pri.item_code")}
			{company_condition}
		""",
		params,
		as_dict=True,
	)

	dn_company_condition = ""
	dn_params = {"from_date": from_date}
	if company:
		dn_company_condition = "AND dn.company = %(company)s"
		dn_params["company"] = company

	dn_result = frappe.db.sql(
		f"""
		SELECT
			SUM(CASE WHEN dn.is_return = 0 THEN dni.qty ELSE -dni.qty END) AS net_supply
		FROM `tabDelivery Note Item` dni
		INNER JOIN `tabDelivery Note` dn ON dn.name = dni.parent
		WHERE dn.docstatus = 1
			AND dn.posting_date < %(from_date)s
			AND {ITEM_LIKE_CONDITIONS.replace("item_code", "dni.item_code")}
			{dn_company_condition}
		""",
		dn_params,
		as_dict=True,
	)

	inward = flt(pr_result[0].inward) if pr_result else 0.0
	return_qty = flt(pr_result[0].return_qty) if pr_result else 0.0
	net_supply = flt(dn_result[0].net_supply) if dn_result else 0.0

	return inward - return_qty - net_supply


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
			SUM(CASE WHEN pr.is_return = 0 THEN pri.qty ELSE 0 END) AS inward,
			SUM(CASE WHEN pr.is_return = 1 THEN ABS(pri.qty) ELSE 0 END) AS return_qty
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
			SUM(CASE WHEN dn.is_return = 0 THEN dni.qty ELSE -dni.qty END) AS net_supply
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
