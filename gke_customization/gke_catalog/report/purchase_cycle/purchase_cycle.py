# Copyright (c) 2026, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	"""Define report columns"""
	return [
		{
			"fieldname": "mr_date_time",
			"label": _("MR Date & Time"),
			"fieldtype": "Datetime",
			"width": 150
		},
		{
			"fieldname": "material_request_id",
			"label": _("Material Request ID"),
			"fieldtype": "Link",
			"options": "Material Request",
			"width": 160
		},
		{
			"fieldname": "department",
			"label": _("Department"),
			"fieldtype": "Link",
			"options": "Department",
			"width": 120
		},
		{
			"fieldname": "item",
			"label": _("Item"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 180
		},
		{
			"fieldname": "qty",
			"label": _("Qty"),
			"fieldtype": "Float",
			"width": 80
		},
		{
			"fieldname": "required_by",
			"label": _("Required By"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "warehouse",
			"label": _("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 150
		},
		{
			"fieldname": "rfq_status",
			"label": _("RFQ Status"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "rfq_ids",
			"label": _("RFQ IDs"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "rfq_date_times",
			"label": _("RFQ Date & Time"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "sq_status",
			"label": _("SQ Status"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "sq_ids",
			"label": _("SQ IDs"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "sq_date_times",
			"label": _("SQ Date & Time"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "po_status",
			"label": _("PO Status"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "po_ids",
			"label": _("PO IDs"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "po_date_times",
			"label": _("PO Date & Time"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "pr_status",
			"label": _("PR Status"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "pr_ids",
			"label": _("PR IDs"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "pr_date_times",
			"label": _("PR Date & Time"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "pi_status",
			"label": _("PI Status"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "pi_ids",
			"label": _("PI IDs"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "pi_date_times",
			"label": _("PI Date & Time"),
			"fieldtype": "Data",
			"width": 200
		}
	]


def get_data(filters):
	"""Fetch report data based on filters"""
	
	conditions = get_conditions(filters)
	
	# Get MR Items first
	mr_items = frappe.db.sql("""
		SELECT
			mr.creation as mr_date_time,
			mr.name as material_request_id,
			wh.department as department,
			mri.name as mri_name,
			mri.item_code as item,
			mri.qty as qty,
			mri.schedule_date as required_by,
			mri.warehouse as warehouse

		FROM `tabMaterial Request` mr
		INNER JOIN `tabMaterial Request Item` mri ON mri.parent = mr.name
		LEFT JOIN `tabWarehouse` wh ON wh.name = mri.warehouse

		WHERE
			mr.docstatus = 1
			AND mr.material_request_type = 'Purchase'
			{conditions}

		ORDER BY mr.creation DESC, mri.idx
	""".format(conditions=conditions), filters, as_dict=1)
	
	final_data = []
	
	for mr_item in mr_items:
		# Get RFQs for this MR Item
		rfqs = frappe.db.sql("""
			SELECT DISTINCT
				rfq.name,
				rfq.status,
				rfq.creation
			FROM `tabRequest for Quotation Item` rfqi
			INNER JOIN `tabRequest for Quotation` rfq ON rfq.name = rfqi.parent
			WHERE rfqi.material_request = %(mr)s
				AND rfqi.material_request_item = %(mri)s
				AND rfq.docstatus = 1
			ORDER BY rfq.creation
		""", {'mr': mr_item['material_request_id'], 'mri': mr_item['mri_name']}, as_dict=1)
		
		# Get SQs - Method 1: Via RFQ
		sq_list = []
		if rfqs:
			rfq_names = [rfq.name for rfq in rfqs]
			sq_list = frappe.db.sql("""
				SELECT DISTINCT
					sq.name,
					sq.status,
					sq.creation
				FROM `tabSupplier Quotation Item` sqi
				INNER JOIN `tabSupplier Quotation` sq ON sq.name = sqi.parent
				WHERE sqi.request_for_quotation IN %(rfq_names)s
					AND sq.docstatus = 1
				ORDER BY sq.creation
			""", {'rfq_names': rfq_names}, as_dict=1)
		
		# Get SQs - Method 2: Directly linked to MR (without RFQ)
		sq_direct = frappe.db.sql("""
			SELECT DISTINCT
				sq.name,
				sq.status,
				sq.creation
			FROM `tabSupplier Quotation Item` sqi
			INNER JOIN `tabSupplier Quotation` sq ON sq.name = sqi.parent
			WHERE sqi.material_request = %(mr)s
				AND sqi.material_request_item = %(mri)s
				AND sq.docstatus = 1
			ORDER BY sq.creation
		""", {'mr': mr_item['material_request_id'], 'mri': mr_item['mri_name']}, as_dict=1)
		
		# Merge SQ lists and remove duplicates
		sq_dict = {}
		for sq in sq_list + sq_direct:
			if sq.name not in sq_dict:
				sq_dict[sq.name] = sq
		sq_list = list(sq_dict.values())
		
		# Get POs for this MR Item
		pos = frappe.db.sql("""
			SELECT DISTINCT
				po.name,
				po.status,
				po.creation
			FROM `tabPurchase Order Item` poi
			INNER JOIN `tabPurchase Order` po ON po.name = poi.parent
			WHERE poi.material_request = %(mr)s
				AND poi.material_request_item = %(mri)s
				AND po.docstatus = 1
			ORDER BY po.creation
		""", {'mr': mr_item['material_request_id'], 'mri': mr_item['mri_name']}, as_dict=1)
		
		# Get SQs - Method 3: From PO Items (additional path)
		if pos:
			po_names = [po.name for po in pos]
			sq_from_po = frappe.db.sql("""
				SELECT DISTINCT
					sq.name,
					sq.status,
					sq.creation
				FROM `tabPurchase Order Item` poi
				INNER JOIN `tabSupplier Quotation` sq ON sq.name = poi.supplier_quotation
				WHERE poi.parent IN %(po_names)s
					AND sq.docstatus = 1
				ORDER BY sq.creation
			""", {'po_names': po_names}, as_dict=1)
			
			# Merge with existing SQs
			for sq in sq_from_po:
				if sq.name not in sq_dict:
					sq_dict[sq.name] = sq
			sq_list = list(sq_dict.values())
		
		# Get PRs for these POs
		pr_list = []
		if pos:
			po_names = [po.name for po in pos]
			pr_list = frappe.db.sql("""
				SELECT DISTINCT
					pr.name,
					pr.status,
					pr.creation
				FROM `tabPurchase Receipt Item` pri
				INNER JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
				WHERE pri.purchase_order IN %(po_names)s
					AND pr.docstatus = 1
					AND pr.is_return = 0
				ORDER BY pr.creation
			""", {'po_names': po_names}, as_dict=1)
		
		# Get PIs for these PRs
		pi_list = []
		if pr_list:
			pr_names = [pr.name for pr in pr_list]
			pi_list = frappe.db.sql("""
				SELECT DISTINCT
					pi.name,
					pi.status,
					pi.creation
				FROM `tabPurchase Invoice Item` pii
				INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
				WHERE pii.purchase_receipt IN %(pr_names)s
					AND pi.docstatus = 1
					AND pi.is_return = 0
				ORDER BY pi.creation
			""", {'pr_names': pr_names}, as_dict=1)
		
		# Build final row
		final_row = {
			'mr_date_time': mr_item['mr_date_time'],
			'material_request_id': mr_item['material_request_id'],
			'department': mr_item['department'],
			'item': mr_item['item'],
			'qty': mr_item['qty'],
			'required_by': mr_item['required_by'],
			'warehouse': mr_item['warehouse'],
			
			# RFQ
			'rfq_status': ', '.join(set([r.status for r in rfqs if r.status])) if rfqs else 'Not Created',
			'rfq_ids': ', '.join([r.name for r in rfqs]) if rfqs else None,
			'rfq_date_times': ', '.join([str(r.creation) for r in rfqs]) if rfqs else None,
			
			# SQ
			'sq_status': ', '.join(set([s.status for s in sq_list if s.status])) if sq_list else None,
			'sq_ids': ', '.join([s.name for s in sq_list]) if sq_list else None,
			'sq_date_times': ', '.join([str(s.creation) for s in sq_list]) if sq_list else None,
			
			# PO
			'po_status': ', '.join(set([p.status for p in pos if p.status])) if pos else None,
			'po_ids': ', '.join([p.name for p in pos]) if pos else None,
			'po_date_times': ', '.join([str(p.creation) for p in pos]) if pos else None,
			
			# PR
			'pr_status': ', '.join(set([p.status for p in pr_list if p.status])) if pr_list else None,
			'pr_ids': ', '.join([p.name for p in pr_list]) if pr_list else None,
			'pr_date_times': ', '.join([str(p.creation) for p in pr_list]) if pr_list else None,
			
			# PI
			'pi_status': ', '.join(set([p.status for p in pi_list if p.status])) if pi_list else None,
			'pi_ids': ', '.join([p.name for p in pi_list]) if pi_list else None,
			'pi_date_times': ', '.join([str(p.creation) for p in pi_list]) if pi_list else None
		}
		
		final_data.append(final_row)
	
	return final_data


def get_conditions(filters):
	"""Build SQL conditions from filters"""
	conditions = []
	
	if filters.get("company"):
		conditions.append("AND mr.company = %(company)s")
	
	if filters.get("branch"):
		conditions.append("AND mri.branch = %(branch)s")
	
	if filters.get("manufacturer"):
		conditions.append("AND mri.manufacturer = %(manufacturer)s")
	 	
	if filters.get("from_date"):
		conditions.append("AND mr.transaction_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("AND mr.transaction_date <= %(to_date)s")
	
	if filters.get("department"):
		conditions.append("AND wh.department = %(department)s")
	
	if filters.get("required_by_from"):
		conditions.append("AND mri.schedule_date >= %(required_by_from)s")
	
	if filters.get("required_by_to"):
		conditions.append("AND mri.schedule_date <= %(required_by_to)s")
	
	return " ".join(conditions)
