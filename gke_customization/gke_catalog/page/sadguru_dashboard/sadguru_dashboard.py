import frappe
from frappe.utils import flt

DEFAULT_COMPANY = "Sadguru Diamond"


def _sort_rows(rows, sort_by, sort_order):
	if sort_by not in ("qty", "rate", "amount"):
		sort_by = "amount"
	reverse = (sort_order or "desc").lower() != "asc"
	rows.sort(key=lambda r: flt(r.get(sort_by)), reverse=reverse)
	return rows


@frappe.whitelist()
def get_purchase_kpis(from_date=None, to_date=None, company=None, supplier=None):
	company = company or DEFAULT_COMPANY

	conditions = ""
	params = {"company": company, "from_date": from_date, "to_date": to_date}
	if supplier:
		conditions = "and pi.supplier = %(supplier)s"
		params["supplier"] = supplier

	totals = frappe.db.sql(
		f"""
		select coalesce(sum(pii.qty), 0) as qty,
			coalesce(sum(pii.amount), 0) as amount,
			count(distinct pi.supplier) as supplier_count,
			count(distinct date_format(pi.posting_date, '%%Y-%%m')) as month_count
		from `tabPurchase Invoice Item` pii
		join `tabPurchase Invoice` pi on pi.name = pii.parent
		where pi.docstatus = 1 and pi.company = %(company)s
			and pi.posting_date between %(from_date)s and %(to_date)s
			{conditions}
		""",
		params,
		as_dict=True,
	)[0]

	total_amount = flt(totals.amount)
	total_qty = flt(totals.qty)
	return {
		"total_purchase": total_amount,
		"total_qty_purchased": total_qty,
		"avg_per_supplier": total_amount / totals.supplier_count if totals.supplier_count else 0,
		"avg_per_supplier_qty": total_qty / totals.supplier_count if totals.supplier_count else 0,
		"avg_monthly_purchase": total_amount / totals.month_count if totals.month_count else 0,
		"avg_monthly_purchase_qty": total_qty / totals.month_count if totals.month_count else 0,
	}


@frappe.whitelist()
def get_sales_kpis(from_date=None, to_date=None, company=None, customer=None, grade=None):
	company = company or DEFAULT_COMPANY

	conditions = ""
	params = {"company": company, "from_date": from_date, "to_date": to_date}
	if customer:
		conditions += " and si.customer = %(customer)s"
		params["customer"] = customer
	if grade:
		conditions += " and sii.diamond_grade = %(grade)s"
		params["grade"] = grade

	totals = frappe.db.sql(
		f"""
		select coalesce(sum(sii.qty), 0) as qty,
			coalesce(sum(sii.amount), 0) as amount,
			count(distinct sii.diamond_grade) as grade_count,
			count(distinct date_format(si.posting_date, '%%Y-%%m')) as month_count
		from `tabSales Invoice Item` sii
		join `tabSales Invoice` si on si.name = sii.parent
		where si.docstatus = 1 and si.company = %(company)s
			and si.posting_date between %(from_date)s and %(to_date)s
			{conditions}
		""",
		params,
		as_dict=True,
	)[0]

	# Company-wide benchmark, independent of the customer filter, so "Avg Per
	# Customer" stays meaningful (not trivially 1) when a customer is selected.
	company_wide = frappe.db.sql(
		"""
		select coalesce(sum(sii.amount), 0) as amount,
			coalesce(sum(sii.qty), 0) as qty,
			count(distinct si.customer) as customer_count
		from `tabSales Invoice Item` sii
		join `tabSales Invoice` si on si.name = sii.parent
		where si.docstatus = 1 and si.company = %(company)s
			and si.posting_date between %(from_date)s and %(to_date)s
		""",
		{"company": company, "from_date": from_date, "to_date": to_date},
		as_dict=True,
	)[0]

	total_amount = flt(totals.amount)
	total_qty = flt(totals.qty)
	company_total = flt(company_wide.amount)
	company_qty = flt(company_wide.qty)
	return {
		"total_sales": total_amount,
		"total_qty_sold": total_qty,
		"avg_per_customer": company_total / company_wide.customer_count if company_wide.customer_count else 0,
		"avg_per_customer_qty": company_qty / company_wide.customer_count if company_wide.customer_count else 0,
		"avg_per_grade": total_amount / totals.grade_count if totals.grade_count else 0,
		"avg_per_grade_qty": total_qty / totals.grade_count if totals.grade_count else 0,
		"avg_monthly_sales": total_amount / totals.month_count if totals.month_count else 0,
		"avg_monthly_sales_qty": total_qty / totals.month_count if totals.month_count else 0,
	}


@frappe.whitelist()
def get_purchase_breakdown(
	from_date=None, to_date=None, company=None, supplier=None, sort_by="amount", sort_order="desc"
):
	company = company or DEFAULT_COMPANY

	conditions = ""
	params = {"company": company, "from_date": from_date, "to_date": to_date}
	if supplier:
		conditions = "and pi.supplier = %(supplier)s"
		params["supplier"] = supplier

	rows = frappe.db.sql(
		f"""
		select pi.supplier, pi.supplier_name,
			sum(pii.qty) as qty,
			sum(pii.amount) as amount
		from `tabPurchase Invoice Item` pii
		join `tabPurchase Invoice` pi on pi.name = pii.parent
		where pi.docstatus = 1 and pi.company = %(company)s
			and pi.posting_date between %(from_date)s and %(to_date)s
			{conditions}
		group by pi.supplier, pi.supplier_name
		""",
		params,
		as_dict=True,
	)

	for row in rows:
		row["qty"] = flt(row["qty"])
		row["amount"] = flt(row["amount"])
		row["rate"] = row["amount"] / row["qty"] if row["qty"] else 0

	return _sort_rows(rows, sort_by, sort_order)


@frappe.whitelist()
def get_sales_breakdown(
	from_date=None, to_date=None, company=None, customer=None, grade=None, sort_by="amount", sort_order="desc"
):
	company = company or DEFAULT_COMPANY

	conditions = ""
	params = {"company": company, "from_date": from_date, "to_date": to_date}
	if customer:
		conditions += " and si.customer = %(customer)s"
		params["customer"] = customer
	if grade:
		conditions += " and sii.diamond_grade = %(grade)s"
		params["grade"] = grade

	rows = frappe.db.sql(
		f"""
		select si.customer as label_id, si.customer_name as label,
			sum(sii.qty) as qty,
			sum(sii.amount) as amount
		from `tabSales Invoice Item` sii
		join `tabSales Invoice` si on si.name = sii.parent
		where si.docstatus = 1 and si.company = %(company)s
			and si.posting_date between %(from_date)s and %(to_date)s
			{conditions}
		group by si.customer, si.customer_name
		""",
		params,
		as_dict=True,
	)

	for row in rows:
		row["qty"] = flt(row["qty"])
		row["amount"] = flt(row["amount"])
		row["rate"] = row["amount"] / row["qty"] if row["qty"] else 0

	return _sort_rows(rows, sort_by, sort_order)


@frappe.whitelist()
def get_sales_grade_breakdown(
	from_date=None, to_date=None, company=None, customer=None, sort_by="amount", sort_order="desc"
):
	company = company or DEFAULT_COMPANY

	conditions = ""
	params = {"company": company, "from_date": from_date, "to_date": to_date}
	if customer:
		conditions = "and si.customer = %(customer)s"
		params["customer"] = customer

	rows = frappe.db.sql(
		f"""
		select coalesce(sii.diamond_grade, 'Not Set') as label,
			sum(sii.qty) as qty,
			sum(sii.amount) as amount
		from `tabSales Invoice Item` sii
		join `tabSales Invoice` si on si.name = sii.parent
		where si.docstatus = 1 and si.company = %(company)s
			and si.posting_date between %(from_date)s and %(to_date)s
			{conditions}
		group by sii.diamond_grade
		""",
		params,
		as_dict=True,
	)

	for row in rows:
		row["qty"] = flt(row["qty"])
		row["amount"] = flt(row["amount"])
		row["rate"] = row["amount"] / row["qty"] if row["qty"] else 0

	return _sort_rows(rows, sort_by, sort_order)


@frappe.whitelist()
def get_sales_matrix(from_date=None, to_date=None, company=None, customer=None, month=None):
	company = company or DEFAULT_COMPANY

	conditions = ""
	params = {"company": company, "from_date": from_date, "to_date": to_date}
	if customer:
		conditions += " and si.customer = %(customer)s"
		params["customer"] = customer
	if month:
		conditions += " and date_format(si.posting_date, '%%Y-%%m') = %(month)s"
		params["month"] = month

	rows = frappe.db.sql(
		f"""
		select si.customer as customer_id, si.customer_name as customer,
			coalesce(sii.diamond_grade, 'Not Set') as grade,
			sum(sii.qty) as qty,
			sum(sii.amount) as amount
		from `tabSales Invoice Item` sii
		join `tabSales Invoice` si on si.name = sii.parent
		where si.docstatus = 1 and si.company = %(company)s
			and si.posting_date between %(from_date)s and %(to_date)s
			{conditions}
		group by si.customer, si.customer_name, sii.diamond_grade
		""",
		params,
		as_dict=True,
	)

	grades = sorted({row.grade for row in rows})
	customers = {}
	for row in rows:
		qty = flt(row.qty)
		amount = flt(row.amount)
		entry = customers.setdefault(
			row.customer_id,
			{"customer": row.customer, "cells": {}, "total_qty": 0, "total_amount": 0},
		)
		entry["cells"][row.grade] = {"qty": qty, "amount": amount}
		entry["total_qty"] += qty
		entry["total_amount"] += amount

	customer_rows = sorted(customers.values(), key=lambda r: r["total_amount"], reverse=True)
	return {"grades": grades, "rows": customer_rows}


@frappe.whitelist()
def get_purchase_monthly(from_date=None, to_date=None, company=None, supplier=None):
	company = company or DEFAULT_COMPANY

	conditions = ""
	params = {"company": company, "from_date": from_date, "to_date": to_date}
	if supplier:
		conditions = "and pi.supplier = %(supplier)s"
		params["supplier"] = supplier

	rows = frappe.db.sql(
		f"""
		select date_format(pi.posting_date, '%%Y-%%m') as month,
			sum(pii.qty) as qty,
			sum(pii.amount) as amount
		from `tabPurchase Invoice Item` pii
		join `tabPurchase Invoice` pi on pi.name = pii.parent
		where pi.docstatus = 1 and pi.company = %(company)s
			and pi.posting_date between %(from_date)s and %(to_date)s
			{conditions}
		group by month
		order by month
		""",
		params,
		as_dict=True,
	)

	for row in rows:
		row["qty"] = flt(row["qty"])
		row["amount"] = flt(row["amount"])
		row["rate"] = row["amount"] / row["qty"] if row["qty"] else 0

	return rows


@frappe.whitelist()
def get_sales_monthly(from_date=None, to_date=None, company=None, customer=None, grade=None):
	company = company or DEFAULT_COMPANY

	conditions = ""
	params = {"company": company, "from_date": from_date, "to_date": to_date}
	if customer:
		conditions += " and si.customer = %(customer)s"
		params["customer"] = customer
	if grade:
		conditions += " and sii.diamond_grade = %(grade)s"
		params["grade"] = grade

	rows = frappe.db.sql(
		f"""
		select date_format(si.posting_date, '%%Y-%%m') as month,
			sum(sii.qty) as qty,
			sum(sii.amount) as amount
		from `tabSales Invoice Item` sii
		join `tabSales Invoice` si on si.name = sii.parent
		where si.docstatus = 1 and si.company = %(company)s
			and si.posting_date between %(from_date)s and %(to_date)s
			{conditions}
		group by month
		order by month
		""",
		params,
		as_dict=True,
	)

	for row in rows:
		row["qty"] = flt(row["qty"])
		row["amount"] = flt(row["amount"])
		row["rate"] = row["amount"] / row["qty"] if row["qty"] else 0

	return rows


@frappe.whitelist()
def get_monthly_trend(from_date=None, to_date=None, company=None):
	company = company or DEFAULT_COMPANY

	purchase_rows = frappe.db.sql(
		"""
		select date_format(pi.posting_date, '%%Y-%%m') as month,
			sum(pii.qty) as qty,
			sum(pii.amount) as amount
		from `tabPurchase Invoice Item` pii
		join `tabPurchase Invoice` pi on pi.name = pii.parent
		where pi.docstatus = 1 and pi.company = %(company)s
			and pi.posting_date between %(from_date)s and %(to_date)s
		group by month
		""",
		{"company": company, "from_date": from_date, "to_date": to_date},
		as_dict=True,
	)

	sales_rows = frappe.db.sql(
		"""
		select date_format(si.posting_date, '%%Y-%%m') as month,
			sum(sii.qty) as qty,
			sum(sii.amount) as amount
		from `tabSales Invoice Item` sii
		join `tabSales Invoice` si on si.name = sii.parent
		where si.docstatus = 1 and si.company = %(company)s
			and si.posting_date between %(from_date)s and %(to_date)s
		group by month
		""",
		{"company": company, "from_date": from_date, "to_date": to_date},
		as_dict=True,
	)

	by_month = {}
	for row in purchase_rows:
		by_month.setdefault(row.month, {}).update(
			{"purchase_qty": flt(row.qty), "purchase_amount": flt(row.amount)}
		)
	for row in sales_rows:
		by_month.setdefault(row.month, {}).update(
			{"sales_qty": flt(row.qty), "sales_amount": flt(row.amount)}
		)

	result = []
	for month in sorted(by_month.keys()):
		data = by_month[month]
		purchase_qty = data.get("purchase_qty", 0)
		purchase_amount = data.get("purchase_amount", 0)
		sales_qty = data.get("sales_qty", 0)
		sales_amount = data.get("sales_amount", 0)
		result.append(
			{
				"month": month,
				"purchase_qty": purchase_qty,
				"purchase_rate": purchase_amount / purchase_qty if purchase_qty else 0,
				"purchase_amount": purchase_amount,
				"sales_qty": sales_qty,
				"sales_rate": sales_amount / sales_qty if sales_qty else 0,
				"sales_amount": sales_amount,
			}
		)

	return result
