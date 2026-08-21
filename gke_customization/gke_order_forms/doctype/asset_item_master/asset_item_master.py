# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
import json
from frappe import _
from frappe.model.document import Document
from frappe.model.workflow import apply_workflow

class AssetItemMaster(Document):
	def autoname(self):
			# Get company abbreviation
			company_abbr = frappe.db.get_value("Company", self.company, "abbr")
			if company_abbr:
				if self.branch:
					branch_short = self.branch.split('-')[-2] 
					series = f"{company_abbr}-{branch_short}-ASM-.#####"
				else:
					series = f"{company_abbr}-ASM-.#####"
	
				self.name = frappe.model.naming.make_autoname(series)
	def before_save(self):
			if self.consumable_items:
				for row in self.consumable_items:
					if row.item_code:
						item = frappe.db.get_value("Item",{'name': row.item_code},['item_name','variant_of'],as_dict=True)
						if item.variant_of:
							attribute_value = frappe.db.get_value(
								"Item Variant Attribute",
								{'parent': row.item_code,'attribute': 'Asset Type'},
								['attribute_value'])
							row.item_name = attribute_value
						else:
							row.item_name = item.item_name

@frappe.whitelist()
def create_asset_material_req(items, user, branch):
	if isinstance(items, str):
		items = json.loads(items)

	if not items:
		frappe.throw(_("No items provided."))

	required_by = items[0].get("required_by")

	if not required_by:
		frappe.throw(_("Required By date is missing."))

	employee_detail = frappe.db.get_value("Employee", {'user_id': user}, ['company','name','branch','department'], as_dict=True)
	if not employee_detail:
		frappe.throw(_("User Id is not linked to Employee."))

	warehouse_filters = {
		"custom_branch": branch,
		"company": employee_detail.company,
		"warehouse_type": "Consumables"
	}

	warehouse = None

	# First preference: Department-specific warehouse
	if employee_detail.department:
		warehouse = frappe.db.get_value("Warehouse", {**warehouse_filters, "department": employee_detail.department}, "name" )

	# Fallback: Warehouse with no department assigned
	if not warehouse:
		warehouse = frappe.db.get_value("Warehouse",{**warehouse_filters},"name" )

	if not warehouse:
		frappe.throw(_("No Warehouse found for the selected branch."))
		
	# frappe.throw(f"{items} {required_by} {employee_detail} {warehouse}")
	material_req = frappe.new_doc('Material Request')
	material_req.material_request_type = 'Purchase'
	material_req.schedule_date = required_by
	material_req.set_warehouse = warehouse
	material_req.company = employee_detail.company

	for item in items:
		item_code = item.get("item_code")
		quantity = item.get("quantity")

		material_req.append('items', {
			'item_code': item_code,
			'qty': quantity, 
			'warehouse': warehouse
		})
	
	material_req.insert()
	if material_req.workflow_state == 'Draft':
		apply_workflow(material_req, "Send For Approval")

	# frappe.db.set_value("Material Request", material_req.name, "workflow_state", "Send For Approval")

	return material_req.name