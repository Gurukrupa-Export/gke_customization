import copy
import itertools
import json
from datetime import datetime

import frappe
from erpnext.stock.doctype.batch.batch import get_batch_qty
from frappe import _, scrub
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder import CustomFunction
from frappe.query_builder.custom import ConstantColumn
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import cint, flt
from six import itervalues

from jewellery_erpnext.jewellery_erpnext.customization.stock_entry.doc_events.se_utils import (
	create_repack_for_subcontracting,
)
from jewellery_erpnext.jewellery_erpnext.customization.stock_entry.doc_events.update_utils import (
	update_main_slip_se_details,
)
from jewellery_erpnext.jewellery_erpnext.customization.utils.metal_utils import (
	get_purity_percentage,
)
from jewellery_erpnext.utils import get_item_from_attribute, get_variant_of_item, update_existing





def before_validate(self, method):
	if (
		not self.get("__islocal") and frappe.db.exists("Stock Entry", self.name) and self.docstatus == 0
	) or self.flags.throw_batch_error:
		self.update_batches()

	pure_item_purity = None

	dir_staus_data = frappe._dict()

	for row in self.items:

		if not row.batch_no and not row.serial_no and row.s_warehouse:
			frappe.throw(_("Please click Get FIFO Batch Button"))

		if not self.auto_created and row.manufacturing_operation:

			if not dir_staus_data.get(row.manufacturing_operation):
				dir_staus_data[row.manufacturing_operation] = frappe.db.get_value(
					"Manufacturing Operation", row.manufacturing_operation, "department_ir_status"
				)
			if dir_staus_data[row.manufacturing_operation] == "In-Transit":
				frappe.throw(
					_("Stock Entry not allowed for {0} in between transit").format(row.manufacturing_operation)
				)
		if row.custom_variant_of in ["M", "F"]:
			if not pure_item_purity:
				# pure_item = frappe.db.get_value("Manufacturing Setting", self.company, "pure_gold_item")
				if self.stock_entry_type == 'Material Transfer (MAIN SLIP)':
					manufacturer = frappe.db.get_value("Main Slip",self.to_main_slip,"manufacturer")
				elif self.manufacturing_order:
					manufacturer = frappe.db.get_value("Parent Manufacturing Order",self.manufacturing_order,"manufacturer")
				else:
					manufacturer = frappe.defaults.get_user_default("manufacturer")

				pure_item = frappe.db.get_value("Manufacturing Setting", {"manufacturer":manufacturer}, "pure_gold_item")

				if not pure_item and self.stock_entry_type not in ['Customer Goods Transfer','Customer Goods Issue','Customer Goods Received']:
					
					frappe.throw(_("Pure Item not mentioned in Manufacturing Setting"))

				pure_item_purity = get_purity_percentage(pure_item)

			item_purity = get_purity_percentage(row.item_code)

			if not item_purity:
				continue

			if pure_item_purity == item_purity:
				row.custom_pure_qty = row.qty

			# else:
			# 	row.custom_pure_qty = flt((item_purity * row.qty) / pure_item_purity, 3)

	validate_pcs(self)
	# if self.stock_entry_type == "Material Receive (WORK ORDER)":
	# 	get_receive_work_order_batch(self)
	# changes pending

	# if self.purpose in ["Repack", "Manufacturing"]:
	# 	amount = 0
	# 	source_qty = 1
	# 	metal_data = {}
	# 	for row in self.items:
	# 		if row.s_warehouse:
	# 			if row.custom_variant_of in ["M", "F"]:
	# 				batch_data = frappe.db.get_value("Batch", row.batch_no, ["custom_metal_rate", "custom_alloy_rate"], as_dict = 1)
	# 				is_alloy = False
	# 				if batch_data.get("custom_alloy_rate") and not batch_data.get("custom_metal_rate"):
	# 					is_alloy = True
	# 				metal_data.setdefault((row.item_code, row.batch_no), frappe._dict({"metal_rate": batch_data.get("custom_metal_rate"), "alloy_rate": batch_data.get("custom_alloy_rate"), "qty": row.qty, "is_alloy": is_alloy}))
	# 			else:
	# 				if row.inventory_type not in ["Customer Goods", "Customer Stock"]:
	# 					source_qty += row.qty
	# 					amount += row.amount if row.get("amount") else 0

	# 	avg_amount = 1

	# for row in self.items:
	# 	if row.t_warehouse:
	# 		if row.inventory_type in ["Customer Goods", "Customer Stock"]:
	# 			row.allow_zero_valuation_rate = 1
	# 			row.basic_rate = 0
	# 		else:
	# 			row.set_basic_rate_manually = 1
	# 			if row.custom_variant_of in ["M", "F"]:
	# 				finish_purity_attribute = frappe.db.get_value("Item Variant Attribute", {"parent": row.item_code, "attribute": "Metal Purity"}, "attribute_value")
	# 				finish_purity = 0
	# 				if finish_purity_attribute:
	# 					finish_purity = frappe.db.get_value("Attribute Value", finish_purity_attribute, "purity_percentage")
	# 				rate = 0
	# 				test = 0
	# 				alloy_rate = 0
	# 				test1 = 0
	# 				lst = []
	# 				for i in metal_data:
	# 					purity_attribute = frappe.db.get_value("Item Variant Attribute", {"parent": i[0], "attribute": "Metal Purity"}, "attribute_value")

	# 					if purity_attribute:
	# 						purity = frappe.db.get_value("Attribute Value", purity_attribute, "purity_percentage")
	# 						if metal_data[i].get("metal_rate"):
	# 							rate += flt(metal_data[i].qty * metal_data[i].metal_rate * purity, 3)
	# 							test += flt(metal_data[i].qty * purity, 3)
	# 						if metal_data[i].get("alloy_rate") and metal_data[i].get("metal_rate"):
	# 							alloy_rate += flt((metal_data[i].qty * metal_data[i].alloy_rate * (100 - purity)) / 100, 3)
	# 							test1 += flt((metal_data[i].qty * (100 - purity)) / 100, 3)
	# 				if finish_purity > 0:
	# 					row.custom_metal_rate = flt(flt(rate, 3) / test, 3)
	# 				else:
	# 					row.custom_metal_rate = 0
	# 				if test1:
	# 					row.custom_alloy_rate = flt(alloy_rate / test1, 3)
	# 				else:
	# 					row.custom_alloy_rate = 0

	# 				row.basic_rate = flt((flt(row.custom_metal_rate * (finish_purity / 100), 3) + flt(row.custom_alloy_rate * ((flt(100 - finish_purity, 3)) / 100), 3)), 3)
	# 			else:
	# 				row.basic_rate = flt(avg_amount, 3)

	# 			row.amount = row.qty * row.basic_rate
	# 			row.basic_amount = row.qty * row.basic_rate


def validate_pcs(self):
	pcs_data = {}
	for row in self.items:
		if row.material_request_item:
			if pcs_data.get(row.material_request_item):
				row.pcs = 0
			else:
				pcs_data[row.material_request_item] = row.pcs
	self.flags.ignore_mandatory = True


