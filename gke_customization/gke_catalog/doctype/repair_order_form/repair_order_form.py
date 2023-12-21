# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import get_link_to_form
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document

class RepairOrderForm(Document):
	def on_submit(self):
		create_serial_and_design_order(self)

	def on_cancel(self):
		delete_auto_created_serial_and_design_order(self)

def create_serial_and_design_order(self):
	doclist = []
	for row in self.order_details:
		docname = make_serial_and_design_order(row.name, parent_doc = self)
		doclist.append(get_link_to_form("Repair Order", docname))
		
	if doclist:
		msg = _("The following {0} were created: {1}").format(
				frappe.bold(_("Repair Order")), "<br>" + ", ".join(doclist)
			)
		frappe.msgprint(msg)

def delete_auto_created_serial_and_design_order(self):
	for row in frappe.get_all("Repair Order", filters={"serial_and_design_id_order_form": self.name}):
		frappe.delete_doc("Repair Order", row.name)

def make_serial_and_design_order(source_name, target_doc=None, parent_doc = None):
	def set_missing_values(source, target):
		target.serial_and_design_id_order_form_detail = source.name
		target.serial_and_design_code_order_form = source.parent
		target.index = source.idx

	doc = get_mapped_doc(
		"Repair Order Form Detail",
		source_name,
		{
			"Repair Order Form Detail": {
				"doctype": "Repair Order" 
			}
		},target_doc, set_missing_values
	)

	for entity in parent_doc.get("service_type", []):
		doc.append("service_type", {"service_type1": entity.service_type1})
	# doc.company = parent_doc.company
	# doc.salesman_name = parent_doc.salesman_name
	# doc.parcel_place = parent_doc.parcel_place
	# doc.branch = parent_doc.branch
	doc.customer_code = parent_doc.customer_code
	doc.po_no = parent_doc.po_no
	doc.parcel_place = parent_doc.parcel_place
	doc.due_days = parent_doc.due_days
	# doc.po_no = parent_doc.po_no
	# doc.po_no = parent_doc.po_no
	# doc.po_no = parent_doc.po_no
	# doc.po_no = parent_doc.po_no
	doc.form_remarks = parent_doc.remarks
	doc.save()
	return doc.name
