# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "name", "label": _("Product Certification"), "fieldtype": "Link", "options": "Product Certification", "width": 150, "hidden": 1},
		{"fieldname": "issue_id", "label": _("Issue ID"), "fieldtype": "Link", "options": "Product Certification", "width": 130},
		{"fieldname": "receive_id", "label": _("Receive ID"), "fieldtype": "Link", "options": "Product Certification", "width": 130},
		{"fieldname": "serial_no", "label": _("Serial No"), "fieldtype": "Link", "options": "Serial No", "width": 130},
		{"fieldname": "huid", "label": _("HUID No"), "fieldtype": "Data", "width": 110},
		{"fieldname": "amount", "label": _("Amount"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "item_code", "label": _("Item Code"), "fieldtype": "Link", "options": "Item", "width": 150},
		{"fieldname": "metal_touch", "label": _("Metal Touch"), "fieldtype": "Data", "width": 110},
		{"fieldname": "category", "label": _("Category"), "fieldtype": "Data", "width": 110},
		{"fieldname": "sub_category", "label": _("Sub Category"), "fieldtype": "Data", "width": 110},
		
		{"fieldname": "setting", "label": _("Setting"), "fieldtype": "Data", "width": 110},
		# {"fieldname": "reference_customer", "label": _("Reference Customer"), "fieldtype": "Link", "options": "Customer", "width": 150},
		{"fieldname": "dia_wt", "label": _("Dia Wt"), "fieldtype": "Float", "width": 90},
		{"fieldname": "pcs", "label": _("Dia. Pcs"), "fieldtype": "Int", "width": 80},
		{"fieldname": "gold_wt", "label": _("Gold Wt"), "fieldtype": "Float", "width": 90},
		{"fieldname": "gross_wt", "label": _("Gross Wt"), "fieldtype": "Float", "width": 90},
		{"fieldname": "chain_wt", "label": _("Chain Wt"), "fieldtype": "Float", "width": 90},
	]


def get_conditions(filters):
	filters = filters or {}
	conditions = ""
	values = {}

	if filters.get("company"):
		conditions += " AND issue.company = %(company)s"
		values["company"] = filters.get("company")

	if filters.get("from_date"):
		conditions += " AND issue.date >= %(from_date)s"
		values["from_date"] = filters.get("from_date")

	if filters.get("to_date"):
		conditions += " AND issue.date <= %(to_date)s"
		values["to_date"] = filters.get("to_date")

	if filters.get("receive_status"):
		conditions += " AND issue.receive_status = %(receive_status)s"
		values["receive_status"] = filters.get("receive_status")

	if filters.get("service_type"):
		conditions += " AND issue.service_type = %(service_type)s"
		values["service_type"] = filters.get("service_type")

	if filters.get("customer"):
		conditions += " AND COALESCE(recv.customer, issue.customer) = %(customer)s"
		values["customer"] = filters.get("customer")

	if filters.get("item_code"):
		conditions += " AND iepd.item_code = %(item_code)s"
		values["item_code"] = filters.get("item_code")

	if filters.get("serial_no"):
		conditions += " AND iepd.serial_no = %(serial_no)s"
		values["serial_no"] = filters.get("serial_no")

	return conditions, values


def get_data(filters):
	conditions, values = get_conditions(filters)

	query = """
		SELECT
			issue.name AS name,
			issue.name AS issue_id,
			recv.name AS receive_id,
			iepd.serial_no AS serial_no,
			COALESCE(repd.huid, iepd.huid) AS huid,
			COALESCE(repd.amount, iepd.amount) AS amount,
			iepd.item_code AS item_code,
			COALESCE(repd.metal_touch, iepd.metal_touch) AS metal_touch,
			COALESCE(repd.category, iepd.category) AS category,
			COALESCE(repd.sub_category, iepd.sub_category) AS sub_category,
			IFNULL(COALESCE(repd.diamond_pcs, iepd.diamond_pcs), 0) AS pcs,
			COALESCE(repd.setting_type, iepd.setting_type) AS setting,
			COALESCE(recv.customer, issue.customer) AS reference_customer,
			COALESCE(repd.diamond_weight, iepd.diamond_weight) AS dia_wt,
			COALESCE(repd.gold_weight, iepd.gold_weight) AS gold_wt,
			COALESCE(repd.gross_weight, iepd.gross_weight) AS gross_wt,
			(SELECT SUM(bfd.quantity) FROM `tabBOM Finding Detail` bfd
				WHERE bfd.parent = COALESCE(repd.bom, iepd.bom) AND bfd.finding_category = 'Chains'
			) AS chain_wt
		FROM `tabProduct Certification` issue
		INNER JOIN (
			SELECT e.*, ROW_NUMBER() OVER (PARTITION BY e.parent, e.serial_no ORDER BY e.idx) AS rn
			FROM `tabExploded Product Details` e
		) iepd ON iepd.parent = issue.name
		LEFT JOIN `tabProduct Certification` recv
			ON recv.type = 'Receive' AND recv.receive_against = issue.name AND recv.docstatus < 2
		LEFT JOIN (
			SELECT e.*, ROW_NUMBER() OVER (PARTITION BY e.parent, e.serial_no ORDER BY e.idx) AS rn
			FROM `tabExploded Product Details` e
		) repd ON repd.parent = recv.name AND repd.serial_no <=> iepd.serial_no AND repd.rn = iepd.rn
		WHERE issue.type = 'Issue' AND issue.docstatus < 2 {conditions}
		ORDER BY issue.date DESC, issue.name, iepd.idx
	""".format(conditions=conditions)

	return frappe.db.sql(query, values, as_dict=1)
