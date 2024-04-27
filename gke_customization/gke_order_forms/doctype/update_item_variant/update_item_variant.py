# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class UpdateItemVariant(Document):
	def on_submit(self):
		db_data = frappe.db.sql(f"select name,attribute, attribute_value from `tabItem Variant Attribute` where parent = '{self.item}'",as_dict=1)
		for i in db_data:
			if self.get(i['attribute'].replace(' ','_').lower()) != i['attribute_value']:
				frappe.db.set_value('Item Variant Attribute',i['name'],'attribute_value',self.get(i['attribute'].replace(' ','_').lower()))

	# @frappe.whitelist
	def before_insert(self):
		# attribute_list = ['metal_colour','product_size','gemstone_type1','enamal','diamond_target','sizer_type','rhodium','stone_changeable','lock_type','chain_type',
   		# 	'chain_length','two_in_one','detachable','feature','chain','number_of_ant','back_chain','back_belt','back_belt_length','back_side_size',
		# 	'chain_thickness','distance_between_kadi_to_mugappu','space_between_mugappu','count_of_spiral_turns','black_bead','black_beed_line']
		db_data = frappe.db.sql(f"select attribute, attribute_value from `tabItem Variant Attribute` where parent = '{self.item}'",as_dict=1)
		for i in db_data:
			setattr(self, i['attribute'].replace(' ','_').lower(), i['attribute_value'])
		


	




@frappe.whitelist()
def get_all_attribute(item):
	db_data = frappe.db.sql(f"select attribute, attribute_value from `tabItem Variant Attribute` where parent = '{item}'",as_dict=1)
	return db_data