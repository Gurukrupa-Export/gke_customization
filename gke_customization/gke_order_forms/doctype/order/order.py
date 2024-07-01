# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils.data import now_datetime
from frappe import _
from frappe.model.document import Document,json
from frappe.model.mapper import get_mapped_doc
from frappe.utils import get_link_to_form
from erpnext.setup.utils import get_exchange_rate
# import json


class Order(Document):
	def on_submit(self):
		item_variant = create_line_items(self)
		if self.bom_or_cad == 'Duplicate BOM':
			new_bom = create_bom(self,item_variant)
			frappe.db.set_value("Order",self.name,"new_bom",new_bom)
			frappe.msgprint(_("New BOM Created: {0}".format(get_link_to_form("BOM",new_bom))))




	def validate(self):
		cerate_timesheet(self)

def cerate_timesheet(self):
	if self.workflow_state == "Designing":
		for assignment in self.designer_assignment:
			designer_value = assignment.designer

			# # Check if a timesheet document already exists for the employee
			timesheet = frappe.get_all(
				"Timesheet", filters={"employee": designer_value,"order":self.name}, fields=["name"],
			)

			if timesheet:
				timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])
			else:
				timesheet_doc = frappe.new_doc("Timesheet")
				timesheet_doc.employee = designer_value
			
			
			if (timesheet_doc.time_logs and 
	   			timesheet_doc.time_logs[-1].activity_type in ['CAD Designing - On-Hold','QC Activity - On-Hold']) :
				timesheet_doc.time_logs[-1].to_time = now_datetime()
				timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600

			time_log = timesheet_doc.append("time_logs", {})
			time_log.activity_type = "CAD Designing"
			time_log.from_time = now_datetime()
			timesheet_doc.order = self.name			
			timesheet_doc.save()			

		frappe.msgprint("Timesheets created for CAD for each designer assignment") 

	elif self.workflow_state == "Sent to QC":
		for assignment in self.designer_assignment:
				designer_value = assignment.designer

				# Check if a timesheet document already exists for the employee
				timesheet = frappe.get_all(
					"Timesheet", filters={"employee": designer_value,"order":self.name}, fields=["name"],
				)
				if timesheet:
					timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])

					if timesheet_doc.time_logs:	
						time_log = timesheet_doc.time_logs[-1]					
						time_log.to_time = now_datetime()
						time_log.completed = 1
						time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600

					qc_time_log = timesheet_doc.append("time_logs", {})
					qc_time_log.activity_type = "QC Activity"
					qc_time_log.from_time = now_datetime()
					qc_time_log.custom_cad_order_id = self.name				
					timesheet_doc.save()
				else:
					frappe.throw("Timesheets is not created for each designer assignment")		
		
		frappe.msgprint("Timesheets created for QC for each designer assignment")
	
	elif self.workflow_state == "Designing - On-Hold":
		for assignment in self.designer_assignment:
				designer_value = assignment.designer

				# Check if a timesheet document already exists for the employee
				# timesheet = frappe.db.get_list("Timesheet",filters={"employee":designer_value,"order":self.name},fields=["name"])
				timesheet = frappe.get_all(
					"Timesheet", filters={"employee": designer_value,"order":self.name}, fields=["name"],
				)
				if timesheet:
					timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])

					if timesheet_doc.time_logs:	
						time_log = timesheet_doc.time_logs[-1]					
						time_log.to_time = now_datetime()
						time_log.completed = 1
						time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600

					qc_time_log = timesheet_doc.append("time_logs", {})
					qc_time_log.activity_type = "CAD Designing - On-Hold"
					qc_time_log.from_time = now_datetime()
					qc_time_log.custom_cad_order_id = self.name
									
					timesheet_doc.save()
				else:
					frappe.throw("Timesheets is not created for each designer assignment")		
		
		frappe.msgprint("Timesheets created for Designing - On-Hold for each designer assignment")
	
	elif self.workflow_state == "Assigned":
		for assignment in self.designer_assignment:
				designer_value = assignment.designer

				# Check if a timesheet document already exists for the employee
				# timesheet = frappe.db.get_list("Timesheet",filters={"employee":designer_value,"order":self.name},fields=["name"])
				timesheet = frappe.get_all(
					"Timesheet", filters={"employee": designer_value,"order":self.name}, fields=["name"],
				)
				if timesheet:
					timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])
					activity_type = timesheet_doc.time_logs[-1].activity_type
					if activity_type == 'QC Activity':
						timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])

						if timesheet_doc.time_logs:	
							time_log = timesheet_doc.time_logs[-1]					
							time_log.to_time = now_datetime()
							time_log.completed = 1
							time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600

						# qc_time_log = timesheet_doc.append("time_logs", {})
						# qc_time_log.activity_type = "CAD Designing - On-Hold"
						# qc_time_log.from_time = now_datetime()
						# qc_time_log.custom_cad_order_id = self.name
										
						timesheet_doc.save()
				# else:
					# frappe.throw("Timesheets is not created for each designer assignment")		
		
		frappe.msgprint("Timesheets created for Update Design for each designer assignment")
	
	elif self.workflow_state == "Sent to QC - On-Hold":
		for assignment in self.designer_assignment:
				designer_value = assignment.designer

				# Check if a timesheet document already exists for the employee
				# timesheet = frappe.db.get_list("Timesheet",filters={"employee":designer_value,"order":self.name},fields=["name"])
				timesheet = frappe.get_all(
					"Timesheet", filters={"employee": designer_value,"order":self.name}, fields=["name"],
				)
				if timesheet:
					timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])

					if timesheet_doc.time_logs:	
						time_log = timesheet_doc.time_logs[-1]					
						time_log.to_time = now_datetime()
						time_log.completed = 1
						time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600

					qc_time_log = timesheet_doc.append("time_logs", {})
					qc_time_log.activity_type = "QC Activity - On-Hold"
					qc_time_log.from_time = now_datetime()
					qc_time_log.custom_cad_order_id = self.name
									
					timesheet_doc.save()
				else:
					frappe.throw("Timesheets is not created for each designer assignment")		
		
		frappe.msgprint("Timesheets created for QC - On-Hold for each designer assignment")
	
	elif self.workflow_state == "Update Item":
		if self.bom_or_cad == 'CAD':
			for assignment in self.designer_assignment:
					designer_value = assignment.designer

					# Check if a timesheet document already exists for the employee
					timesheet = frappe.get_all(
						"Timesheet", filters={"employee": designer_value,"order":self.name}, fields=["name"],
					)
					if timesheet:
						timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])

						if timesheet_doc.time_logs:	
							time_log = timesheet_doc.time_logs[-1]					
							time_log.to_time = now_datetime()
							time_log.completed = 1
							time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600

						update_time_log = timesheet_doc.append("time_logs", {})
						update_time_log.activity_type = "Update BOM"
						update_time_log.from_time = now_datetime()
						update_time_log.custom_cad_order_id = self.name				
						timesheet_doc.save()

						# time_log = timesheet_doc.time_logs[-1]					
						# time_log.to_time = now_datetime()
						# time_log.completed = 1
						# time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600
						# timesheet_doc.save()
						# timesheet_doc.run_method('submit')
					else:
						frappe.throw("Timesheets is not created for each designer assignment")
			frappe.msgprint("Timesheets created for Update Item for each designer assignment")		
	
	elif self.workflow_state == "Update BOM":
		if self.bom_or_cad == 'CAD':
			for assignment in self.designer_assignment:
					designer_value = assignment.designer

					# Check if a timesheet document already exists for the employee
					timesheet = frappe.get_all(
						"Timesheet", filters={"employee": designer_value,"order":self.name}, fields=["name"],
					)
					if timesheet:
						timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])

						time_log = timesheet_doc.time_logs[-1]					
						time_log.to_time = now_datetime()
						time_log.completed = 1
						time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600
						timesheet_doc.save()
						timesheet_doc.run_method('submit')
					else:
						frappe.throw("Timesheets is not created for each designer assignment")
			frappe.msgprint("Timesheets Completed for each designer assignment")

	elif self.workflow_state == "Cancelled": 
		for assignment in self.designer_assignment:
				designer_value = assignment.designer

				# Check if a timesheet document already exists for the employee
				timesheet = frappe.get_all(
					"Timesheet", filters={"employee": designer_value,}, fields=["name"],
				)
				if timesheet:
					timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])

					time_log = timesheet_doc.time_logs[-1]					
					time_log.to_time = now_datetime()
					time_log.completed = 1
					time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600
									
					timesheet_doc.save()
					timesheet_doc.run_method('submit')
				else:
					frappe.throw("Timesheets is cancelled for each designer assignment")		
		
		frappe.msgprint("Timesheets Completed for each designer assignment")

def create_line_items(self):
	if self.item_type == 'Template and Variant':
		if self.design_type != 'Sketch Design':
			item_template = create_item_template_from_order(self)
			updatet_item_template(item_template)
			item_variant = create_variant_of_template_from_order(item_template,self.name)
			update_item_variant(item_variant,item_template)
			frappe.msgprint(_("New Item Created: {0}".format(get_link_to_form("Item",item_variant))))
			frappe.db.set_value(self.doctype, self.name, "item", item_variant)
		else:
			frappe.db.set_value(self.doctype, self.name, "item", self.design_id)

	elif self.item_type == 'Only Variant':
		# if self.design_type != 'Sketch Design' and self.bom_or_cad == 'CAD':
		if self.design_type != 'Sketch Design':
			item_variant = create_only_variant_from_order(self,self.name)
			frappe.db.set_value('Item',item_variant[0],{
				"is_design_code":1,
				"variant_of" : item_variant[1]
			})
			frappe.msgprint(_("New Item Created: {0}".format(get_link_to_form("Item",item_variant[0]))))
			frappe.db.set_value(self.doctype, self.name, "item", item_variant[0])
		else:
			frappe.db.set_value(self.doctype, self.name, "item", self.design_id)
		
	elif self.item_type == 'Suffix Of Variant':
		# if self.design_type != 'Sketch Design' and self.bom_or_cad == 'CAD':
		if self.design_type != 'Sketch Design':
		# if self.design_type != 'Sketch Design' and self.bom_or_cad == 'CAD'self.item_type != 'No Variant No Suffix':
			item_template = create_sufix_of_variant_template_from_order(self)
			frappe.db.set_value('Item',item_template,'modified_from','')
			updatet_item_template(item_template)
			item_variant = create_variant_of_sufix_of_variant_from_order(self,item_template,self.name)
			update_item_variant(item_variant,item_template)
			frappe.msgprint(_("New Item Created: {0}".format(get_link_to_form("Item",item_variant))))
			frappe.db.set_value(self.doctype, self.name, "item", item_variant)
		else:
			frappe.db.set_value(self.doctype, self.name, "item", self.design_id)
			# frappe.db.set_value(self.doctype, self.name, "new_bom", self.bom)

	elif self.item_type == 'No Variant No Suffix':
		item_variant = self.design_id
		frappe.db.set_value(self.doctype, self.name, "item", self.design_id)
		if self.bom_or_cad in ['New BOM','CAD'] and self.is_repairing == 1 :
			# frappe.throw(f"{self.design_id}")
			new_bom = create_bom(self,item_variant)
			frappe.db.set_value("Order",self.name,"new_bom",new_bom)
		else:
			frappe.db.set_value(self.doctype, self.name, "new_bom", self.bom)

		
	return	item_variant
	# create_reference_doc(self,item)

def create_item_template_from_order(source_name, target_doc=None):
	def post_process(source, target):
		target.is_design_code = 1
		target.has_variants = 1
		if source.designer_assignment:
			target.designer = source.designer_assignment[0].designer
		target.item_group = source.subcategory + " - T",

	doc = get_mapped_doc(
		"Order",
		source_name.name,
		{
			"Order": {
				"doctype": "Item",
				"field_map": {
					"category": "item_category",
					"subcategory": "item_subcategory",
					"setting_type": "setting_type",
					"india":"india",
					"india_states":"india_states",
					"usa":"usa",
					"usa_states":"usa_states",
				} 
			}
		},target_doc, post_process
	)

	
	doc.save()
	return doc.name

def create_variant_of_template_from_order(item_template,source_name, target_doc=None):
	def post_process(source, target):
		target.order_form_type = 'Order'
		target.item_group = frappe.db.get_value('Order',source_name,'subcategory') + " - V",
		target.custom_cad_order_id = source_name
		target.custom_cad_order_form_id = frappe.db.get_value('Order',source_name,'cad_order_form')
		target.item_code = f'{item_template}-001'
		target.sequence = item_template[2:7]
		subcateogy = frappe.db.get_value('Item',item_template,'item_subcategory')
		for i in frappe.get_all("Attribute Value Item Attribute Detail",{'parent': subcateogy,'in_item_variant':1},'item_attribute',order_by='idx asc'):
			attribute_with = i.item_attribute.lower().replace(' ', '_')
			if i.item_attribute == 'Rhodium':
				attribute_with = 'rhodium_'
			try:
				attribute_value = frappe.db.get_value('Order',source_name,attribute_with)
			except:
				attribute_value = ' '
			
			target.append('attributes',{
				'attribute':i.item_attribute,
				'variant_of':item_template,
				'attribute_value':attribute_value
			})

		if source.designer_assignment:
			target.designer = source.designer_assignment[0].designer
		else:
			if frappe.db.get_value('Employee',{'user_id':frappe.session.user},'name'):
				target.designer = frappe.db.get_value('Employee',{'user_id':frappe.session.user},'name')
			else:
				target.designer = frappe.db.get_value('User',frappe.session.user,'full_name')

	doc = get_mapped_doc(
		"Order",
		source_name,
		{
			"Order": {
				"doctype": "Item",
				"field_map": {
					"category": "item_category",
					"subcategory": "item_subcategory",
					"setting_type": "setting_type",
					"metal_target":"approx_gold",
					"diamond_target":"approx_diamond",
					"sub_setting_type1":"sub_setting_type",
					"sub_setting_type2":"sub_setting_type2",
					"india":"india",
					"india_states":"india_states",
					"usa":"usa",
					"usa_states":"usa_states",
					"age_group":"custom_age_group",
					"alphabetnumber":"custom_alphabetnumber",
					"animalbirds":"custom_animalbirds",
					"collection":"custom_collection",
					"design_style":"custom_design_style",
					"gender":"custom_gender",
					"lines_rows":"custom_lines__rows",
					"language":"custom_language",
					"occasion":"custom_occasion",
					"rhodium":"custom_rhodium",
					"shapes":"custom_religious",
					"religious":"custom_shapes",
					"zodiac":"custom_zodiac",
				} 
			}
		},target_doc, post_process
	)
	
	doc.save()
	return doc.name


def create_only_variant_from_order(self,source_name, target_doc=None):
	db_data = frappe.db.get_list('Item',filters={'name':self.design_id},fields=['variant_of'],order_by='creation desc')[0]
	db_data1 = frappe.db.get_list('Item',filters={'variant_of':db_data['variant_of']},fields=['name'],order_by='creation desc')[0]
	def post_process(source, target):
		index = int(db_data1['name'].split('-')[1]) + 1
		suffix = "%.3i" % index
		item_code = db_data['variant_of'] + '-' + suffix
		
		target.order_form_type = 'Order'
		target.item_group = frappe.db.get_value('Order',source_name,'subcategory') + " - V",		
		target.custom_cad_order_id = source_name
		target.custom_cad_order_form_id = frappe.db.get_value('Order',source_name,'cad_order_form')
		target.item_code = item_code
		target.sequence = item_code[2:7]
		target.has_serial_no = 1
		
		for i in frappe.get_all("Attribute Value Item Attribute Detail",{'parent': self.subcategory,'in_item_variant':1},'item_attribute',order_by='idx asc'):
			attribute_with = i.item_attribute.lower().replace(' ', '_')
			if i.item_attribute == 'Rhodium':
				attribute_with = 'rhodium_'
			try:
				attribute_value = frappe.db.get_value('Order',source_name,attribute_with)
			except:
				attribute_value = ' '
			
			# target.append('attributes',{
			# 	'attribute':i.item_attribute,
			# 	'variant_of':item_template,
			# 	'attribute_value':attribute_value
			# })
			target.append('attributes',{
				'attribute':i.item_attribute,
				'variant_of':db_data['variant_of'],
				'attribute_value':attribute_value
			})

		if source.designer_assignment:
			target.designer = source.designer_assignment[0].designer
		else:
			if frappe.db.get_value('Employee',{'user_id':frappe.session.user},'name'):
				target.designer = frappe.db.get_value('Employee',{'user_id':frappe.session.user},'name')
			else:
				target.designer = frappe.db.get_value('User',frappe.session.user,'full_name')
		
	doc = get_mapped_doc(
		"Order",
		source_name,
		{
			"Order": {
				"doctype": "Item",
				"field_map": {
					"category": "item_category",
					"subcategory": "item_subcategory",
					"metal_target":"approx_gold",
					"diamond_target":"approx_diamond",
					"setting_type": "setting_type",
					"sub_setting_type1":"sub_setting_type",
					"sub_setting_type2":"sub_setting_type2",
					"india":"india",
					"india_states":"india_states",
					"usa":"usa",
					"usa_states":"usa_states",
					"age_group":"custom_age_group",
					"alphabetnumber":"custom_alphabetnumber",
					"animalbirds":"custom_animalbirds",
					"collection":"custom_collection",
					"design_style":"custom_design_style",
					"gender":"custom_gender",
					"lines_rows":"custom_lines__rows",
					"language":"custom_language",
					"occasion":"custom_occasion",
					"rhodium":"custom_rhodium",
					"shapes":"custom_religious",
					"religious":"custom_shapes",
					"zodiac":"custom_zodiac",
				} 
			}
		},target_doc, post_process
	)
	# frappe.throw(f"{doc.item_code}")
	doc.save()
	return doc.name,db_data['variant_of']

def create_sufix_of_variant_template_from_order(source_name, target_doc=None):
	variant_of = frappe.db.get_value("Item",source_name.design_id,'variant_of')
	if variant_of == None:
		frappe.throw(f'Template of {variant_of} is not available')

	def post_process(source, target):
		target.is_design_code = 1
		target.has_variants = 1
		target.item_group = source.subcategory + " - T",
		query = """
		SELECT name, modified_sequence, `sequence`
		FROM `tabItem` ti
		WHERE name LIKE %s AND has_variants = 1
		ORDER BY creation DESC
		"""

		results = frappe.db.sql(query, (f"%{variant_of}/%",), as_dict=True)
		if results:
			modified_sequence = int(results[0]['modified_sequence']) + 1
			modified_sequence = f"{modified_sequence:02}"
		else:
			modified_sequence = '01'
		
		target.item_code = variant_of + '/' + modified_sequence
		# frappe.throw(target.item_code)
		target.modified_sequence = modified_sequence
		target.order_form_type = 'Order'
		target.custom_cad_order_id = source_name
		target.custom_cad_order_form_id = frappe.db.get_value('Order',source_name,'cad_order_form')

		if source.designer_assignment:
			target.designer = source.designer_assignment[0].designer
		else:
			if frappe.db.get_value('Employee',{'user_id':frappe.session.user},'name'):
				target.designer = frappe.db.get_value('Employee',{'user_id':frappe.session.user},'name')
			else:
				target.designer = frappe.db.get_value('User',frappe.session.user,'full_name')
		# frappe.throw(f"{target.designer}")
	
	doc = get_mapped_doc(
		"Order",
		source_name.name,
		{
			"Order": {
				"doctype": "Item",
				"field_map": {
					"category": "item_category",
					"subcategory": "item_subcategory",
					"setting_type": "setting_type",
					"india":"india",
					"india_states":"india_states",
					"usa":"usa",
					"usa_states":"usa_states",
				} 
			}
		},target_doc, post_process
	)
	doc.save()
	return doc.name

def create_variant_of_sufix_of_variant_from_order(self,item_template,source_name, target_doc=None):
	def post_process(source, target):
		target.order_form_type = 'Order'
		target.item_group = frappe.db.get_value('Order',source_name,'subcategory') + " - V",
		target.custom_cad_order_id = source_name
		target.custom_cad_order_form_id = frappe.db.get_value('Order',source_name,'cad_order_form')
		target.item_code = item_template[:10] + '-001'
		target.sequence = item_template[2:7]
		

		for i in frappe.get_all("Attribute Value Item Attribute Detail",{'parent': self.subcategory,'in_item_variant':1},'item_attribute',order_by='idx asc'):
			attribute_with = i.item_attribute.lower().replace(' ', '_')	
			target.append('attributes',{
				'attribute':i.item_attribute,
				'variant_of':item_template,
				'attribute_value':frappe.db.get_value('Order',source_name,attribute_with)
			})

		if source.designer_assignment:
			target.designer = source.designer_assignment[0].designer
		else:
			if frappe.db.get_value('Employee',{'user_id':frappe.session.user},'name'):
				target.designer = frappe.db.get_value('Employee',{'user_id':frappe.session.user},'name')
			else:
				target.designer = frappe.db.get_value('User',frappe.session.user,'full_name')
		# frappe.throw(f"{target.designer}")

	doc = get_mapped_doc(
		"Order",
		source_name,
		{
			"Order": {
				"doctype": "Item",
				"field_map": {
					"category": "item_category",
					"subcategory": "item_subcategory",
					"setting_type": "setting_type",
					"metal_target":"approx_gold",
					"diamond_target":"approx_diamond",
					"sub_setting_type1":"sub_setting_type",
					"sub_setting_type2":"sub_setting_type2",
					"india":"india",
					"india_states":"india_states",
					"usa":"usa",
					"usa_states":"usa_states",
					"age_group":"custom_age_group",
					"alphabetnumber":"custom_alphabetnumber",
					"animalbirds":"custom_animalbirds",
					"collection":"custom_collection",
					"design_style":"custom_design_style",
					"gender":"custom_gender",
					"lines_rows":"custom_lines__rows",
					"language":"custom_language",
					"occasion":"custom_occasion",
					"rhodium":"custom_rhodium",
					"shapes":"custom_religious",
					"religious":"custom_shapes",
					"zodiac":"custom_zodiac",
				} 
			}
		},target_doc, post_process
	)
	doc.save()
	return doc.name

def updatet_item_template(item_template):
	frappe.db.set_value('Item',item_template,{
		"is_design_code":0,
		"item_code":item_template,
		"custom_cad_order_id":"",
		"custom_cad_order_form_id":"",
	})

def update_item_variant(item_variant,item_template):
	frappe.db.set_value('Item',item_variant,{
		"is_design_code":1,
		"variant_of" : item_template
	})

def create_bom(self,item_variant):
	bom_doc = frappe.get_doc("BOM",self.bom)
	new_bom_doc = frappe.new_doc("BOM")
	new_bom_doc = bom_doc
	new_bom_doc.docstatus = 0
	new_bom_doc.name = ''
	new_bom_doc.is_active = 1
	new_bom_doc.is_default = 1
	new_bom_doc.bom_type = 'Template'
	new_bom_doc.item = item_variant
	new_bom_doc.custom_order_form_type = 'Order'
	new_bom_doc.custom_cad_order_form_id = self.cad_order_form
	new_bom_doc.custom_order_id = self.name
	new_bom_doc.save()

	return new_bom_doc.name

@frappe.whitelist()
def make_quotation(source_name, target_doc=None):
	
	def set_missing_values(source, target):
		from erpnext.controllers.accounts_controller import get_default_taxes_and_charges
		quotation = frappe.get_doc(target)
		company_currency = frappe.get_cached_value("Company", quotation.company, "default_currency")
		if company_currency == quotation.currency:
			exchange_rate = 1
		else:
			exchange_rate = get_exchange_rate(
				quotation.currency, company_currency, quotation.transaction_date, args="for_selling"
			)
		quotation.conversion_rate = exchange_rate
		# get default taxes
		taxes = get_default_taxes_and_charges(
			"Sales Taxes and Charges Template", company=quotation.company
		)
		if taxes.get("taxes"):
			quotation.update(taxes)
		quotation.run_method("set_missing_values")
		quotation.run_method("calculate_taxes_and_totals")

		quotation.quotation_to = "Customer"
		field_map = {
 			# target : source
			"company": "company",
			"party_name": "customer_code",
			"order_type": "order_type",
			"diamond_quality": "diamond_quality"
		}
		for target_field, source_field in field_map.items():
			quotation.set(target_field,source.get(source_field))
		service_types = frappe.db.get_values("Service Type 2", {"parent": source.name},"service_type1")
		for service_type in service_types:
			quotation.append("service_type",{"service_type1": service_type[0]})

	if isinstance(target_doc, str):
		target_doc = json.loads(target_doc)
	if not target_doc:
		target_doc = frappe.new_doc("Quotation")
	else:
		target_doc = frappe.get_doc(target_doc)

	order = frappe.db.get_value("Order", source_name, "*")

	target_doc.append("items", {
		"branch": order.get("branch"),
		"project": order.get("project"),
		"item_code": order.get("item"),
		"serial_no": order.get("tag_no"),
		"metal_colour": order.get("metal_colour"),
		"metal_purity": order.get("metal_purity"),
		"metal_touch": order.get("metal_touch"),
		"gemstone_quality": order.get("gemstone_quality"),
		"item_category" : order.get("category"),
		"diamond_quality": order.get("diamond_quality"),
		"item_subcategory": order.get("subcategory"),
		"setting_type": order.get("setting_type"),
		"delivery_date": order.get("delivery_date"),
		"order_form_type": "Order",
		"order_form_id": order.get("name"),
		"salesman_name": order.get("salesman_name"),
		"order_form_date": order.get("order_date"),
		"custom_customer_sample": order.get("customer_sample"),
		"custom_customer_voucher_no": order.get("customer_voucher_no"),
		"custom_customer_gold": order.get("customer_gold"),
		"custom_customer_diamond": order.get("customer_diamond"),
		"custom_customer_stone": order.get("customer_stone"),
		"custom_customer_good": order.get("customer_good"),
		"po_no": order.get("po_no"),
	})
	set_missing_values(order, target_doc)

	return target_doc


