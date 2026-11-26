import frappe

from jewellery_erpnext.jewellery_erpnext.doctype.manufacturing_work_order.manufacturing_work_order import (
	create_cad_mwo as _create_cad_mwo,
)


# @frappe.whitelist()
# def create_cad_mwo(data):
# 	return _create_cad_mwo(data)
import json

import frappe
from frappe import _

_STANDARD_KEYS = (
	"name", "owner", "creation", "modified", "modified_by", "docstatus", "idx",
	"parent", "parentfield", "parenttype", "doctype",
)


@frappe.whitelist()
def create_cad_mwo(data):
	"""Create a CAD/CAM Manufacturing Work Order from a payload sent by another site.

	Department is resolved from this site's Manufacturing Setting and falls back
	to the department sent in the payload.
	"""
	if isinstance(data, str):
		data = json.loads(data)

	manufacturing_order = data.get("manufacturing_order")
	existing = frappe.db.get_value(
		"Manufacturing Work Order",
		{"manufacturing_order": manufacturing_order, "for_cad_cam": 1},
	)
	if existing:
		return {"name": existing, "already_exists": 1}

	for key in _STANDARD_KEYS:
		data.pop(key, None)

	doc = frappe.new_doc("Manufacturing Work Order")
	doc.update(data)

	# These link to records that live on the sending site; keep them only if they also exist here,
	# otherwise link validation rejects the whole document.
	for fieldname, link_doctype in (
		("custom_tracking_bom", "Tracking Bom"),
		("master_bom", "BOM"),

		("serial_id_bom", "BOM"),
	):
		value = doc.get(fieldname)
		if value and not frappe.db.exists(link_doctype, value):
			doc.set(fieldname, None)

	# Fetch the plan from this site's Parent Manufacturing Order if the sent one is missing here.
	if not doc.get("manufacturing_plan") and manufacturing_order:
		doc.manufacturing_plan = frappe.db.get_value(
			"Parent Manufacturing Order", manufacturing_order, "manufacturing_plan"
		)

	# The sender may not include the manufacturer; take it from this site's Parent Manufacturing Order.
	if not doc.get("manufacturer") and manufacturing_order:
		doc.manufacturer = frappe.db.get_value(
			"Parent Manufacturing Order", manufacturing_order, "manufacturer"
		)

	department = None
	if doc.get("manufacturer"):
		department = frappe.db.get_value(
			"Manufacturing Setting",
			{"manufacturer": doc.manufacturer},
			"default_cad_department",
		)
	if department:
		doc.department = department
	elif not frappe.db.exists("Department", doc.get("department")):
		frappe.throw(
			_(
				"CAD/CAM Department is not configured on this site (manufacturer: {0}, department sent: {1})"
			).format(doc.get("manufacturer"), doc.get("department"))
		)

	doc.for_cad_cam = 1
	doc.auto_created = 1
	doc.insert()
	return {"name": doc.name, "already_exists": 0}
