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
		frappe.throw(_("CAD/CAM Department is not configured on this site"))

	doc.for_cad_cam = 1
	doc.auto_created = 1
	doc.insert()
	return {"name": doc.name, "already_exists": 0}
