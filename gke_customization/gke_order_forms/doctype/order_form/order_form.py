# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe,json
from frappe import _
from frappe.utils import get_link_to_form
from datetime import datetime, timedelta, time
import frappe
from frappe.utils import now_datetime, get_datetime
from frappe.utils import get_link_to_form
from frappe import _

from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from erpnext.controllers.item_variant import (
	ItemVariantExistsError,
	copy_attributes_to_variant,
	get_variant,
	make_variant_item_code,
	validate_item_variant_attributes,
)
from frappe.utils import (
	cint,
	cstr,
	flt,
	formatdate,
	get_link_to_form,
	getdate,
	now_datetime,
	nowtime,
	strip,
	strip_html,
)
import json
from datetime import datetime, date
from frappe.utils.file_manager import save_file
import openpyxl
from io import BytesIO

class OrderForm(Document):
	def on_submit(self):
		if self.workflow_state == 'Approved':
			create_cad_orders(self)
		if self.supplier:
			create_po(self)

	def validate_rows(self):
		seen = {}
		duplicates = {}
		error_logs = []

		try:
			for i, row in enumerate(self.order_details):
				try:
					row_dict = row.as_dict()
					for field in [
						'name', 'idx', 'parent', 'parenttype', 'parentfield',
						'doctype', '__unsaved', 'owner', 'creation',
						'modified', 'modified_by'
					]:
						row_dict.pop(field, None)
					for key, value in row_dict.items():
						if isinstance(value, (datetime, date)):
							row_dict[key] = value.isoformat()
					row_str = json.dumps(row_dict, sort_keys=True)

					# Track all indices where this row pattern appears
					if row_str not in seen:
						seen[row_str] = [i]
					else:
						seen[row_str].append(i)
				except Exception as row_error:
					frappe.log_error(title="Validate Row Error", 
									message=f"Order Form: {self.name} | Row: {i+1} -> {row_error}")
					error_logs.append(f"Row {i+1}: {row_error}")

			# Now, collect all duplicates
			for indices in seen.values():
				if len(indices) > 1:
					duplicates[tuple(idx+1 for idx in indices)] = True

			if duplicates:
				# Build the duplicate message with bold rows inside
				msg = "❌ Duplicate rows found: "
				groups = []
				for dup_rows in duplicates.keys():
					bold_rows = ", ".join([f"<b>{num}</b>" for num in dup_rows])
					groups.append(f"Rows {bold_rows} are identical")
				msg += ". ".join(groups) + "."

				# Save the error message (stripping HTML tags for plain text) into error_log field
				import re
				plain_text_msg = re.sub(r'<[^>]*>', '', msg)
				frappe.db.set_value(self.doctype, self.name, "error_log", plain_text_msg)
				frappe.msgprint(msg)
			
			else:
				frappe.db.set_value(self.doctype, self.name, "error_log", None)
				# frappe.db.set_value(self.doctype, self.name, "workflow_state", "Draft")
				return "No duplicates found"

		except Exception as e:
			# General fallback error (catch for the whole method)
			frappe.log_error(title="Validate Rows (General Error)", 
							message=f"Order Form: {self.name} | Error: {e}")
			raise

	def on_update_after_submit(self):
		if self.updated_delivery_date:
			order_names = frappe.get_all(
				"Order",
				filters={"cad_order_form": self.name},
				pluck="name"
			)

			for order_name in order_names:
				frappe.db.set_value("Order", order_name, "updated_delivery_date", self.updated_delivery_date)

	def on_cancel(self):
		if frappe.db.get_list("Order",filters={"cad_order_form":self.name},fields="name"):
			for order in frappe.db.get_list("Order",filters={"cad_order_form":self.name},fields="name"):
				frappe.db.set_value("Order",order["name"],"workflow_state","Cancelled")
				# frappe.throw(f"{order}")
				if frappe.db.get_list("Timesheet",filters={"order":order["name"]},fields="name"):
					for timesheet in frappe.db.get_list("Timesheet",filters={"order":order["name"]},fields="name"):
						frappe.db.set_value("Timesheet",timesheet["name"],"docstatus","2")

		frappe.db.set_value("Order Form",self.name,"workflow_state","Cancelled")
		self.reload()

	def validate(self):

		# self.validate_category_subcaegory()
		# self.validate_filed_value()
		# validate_item_variant(self)
		# validate_is_mannual(self)
		if self.workflow_state == 'Validate Rows':
			self.validate_rows()

		if self.workflow_state == 'Fetch Data':
			validate_design_id(self)
			set_data(self)

		if self.workflow_state == 'Send For Approval':
			self.validate_filed_value()
		
		for i in self.order_details:	
			if i.metal_type == "Silver":
				i.metal_colour = "White"
				i.metal_touch = "20KT"
				i.setting_type = "Open"
				i.diamond_type = "AD"

	def validate_category_subcaegory(self):
		for row in self.get("order_details"):
			if row.subcategory:
				parent = frappe.db.get_value("Attribute Value", row.subcategory, "parent_attribute_value")
				if row.category != parent:
					frappe.throw(_(f"Category & Sub Category mismatched in row #{row.idx}"))
	
	def validate_filed_value(self):
    # List of attribute names and corresponding row field to validate
		attr_fields = [
			("Design Type", "design_type", "Design Type"),
			("Diamond Quality", "diamond_quality", "Diamond Quality"),
			("Setting Type", "setting_type", "Setting Type"),
			("Sub Setting Type1", "sub_setting_type1", "Setting Type 1"),
			("Sub Setting Type2", "sub_setting_type2", "Setting Type 2"),
			("Metal Type", "metal_type", "Metal Type"),
			("Metal Touch", "metal_touch", "Metal Touch"),
			("Metal Colour", "metal_colour", "Metal Colour"),
			("Diamond Type", "diamond_type", "Diamond Type"),
			("Sizer Type", "sizer_type", "Sizer Type"),
			("Stone Changeable", "stone_changeable", "Stone Changeable"),
			("Feature", "feature", "Feature"),
			("Rhodium", "rhodium", "Rhodium"),
			("Enamal", "enamal", "Enamal"),
			("Gemstone Type", "gemstone_type", "Gemstone Type"),
			("Gemstone Quality", "gemstone_quality", "Gemstone Quality"),
			("Mod Reason", "mod_reason", "Mod Reason"),
			("Finding Category", "finding_category", "Finding Category"),
			("Finding Sub-Category", "finding_subcategory", "Finding Sub-Category"),
			("Finding Size", "finding_size", "Finding Size"),
			("Metal Target Range", "metal_target_from_range", "Metal Target Range"),
			("Diamond Target Range", "diamond_target_from_range", "Diamond Target Range"),
			("Detachable", "detachable", "Detachable"),
			("Lock Type", "lock_type", "Lock Type"),
			("Cap/Ganthan", "capganthan", "Cap/Ganthan"),
			("Charm", "charm", "Charm"),
			("Back Chain", "back_chain", "Back Chain"),
			("Back Belt", "back_belt", "Back Belt"),
			("Black Bead", "black_bead", "Black Bead"),
			("2 in 1", "two_in_one", "2 in 1"),
			("Chain Type", "chain_type", "Chain Type"),
			("Nakshi From", "nakshi_from", "Nakshi From"),
		]

		# Cache all attribute values in a dict: { attribute_name: set_of_values }
		attribute_cache = {}

		for attr_name, _, _ in attr_fields:
			doc = frappe.get_doc("Item Attribute", attr_name)
			# Using set for O(1) contains lookup
			attribute_cache[attr_name] = set(i.attribute_value for i in doc.item_attribute_values)

		# Iterate over rows and validate
		for idx, row in enumerate(self.get("order_details"), start=1):
			for attr_name, field_name, display_name in attr_fields:
				val = getattr(row, field_name, None)
				if val:  # Check only if field value is present
					if val not in attribute_cache[attr_name]:
						frappe.throw(f"{display_name} is not Correct in Row #{idx}")
			
		
# def create_cad_orders(self):
# 	doclist = []
# 	for row in self.order_details:
# 		docname = make_cad_order(row.name, parent_doc = self)
# 		doclist.append(get_link_to_form("Order", docname))

# 	if doclist:
# 		msg = _("The following {0} were created: {1}").format(
# 				frappe.bold(_("Orders")), "<br>" + ", ".join(doclist)
# 			)
# 		frappe.msgprint(msg)



def create_cad_orders(self):
    doclist = []

    # Fetch Order Criteria once
    order_criteria = frappe.get_single("Order Criteria")
    criteria_rows = order_criteria.get("order")
    enabled_criteria = next((row for row in criteria_rows if not row.disable), None)

    if not enabled_criteria:
        frappe.throw("No enabled Order Criteria found.")

    # Parse CAD and IBM times
    cad_days = int(enabled_criteria.cad_approval_day or 0)

    # Parse cad_submission_time
    cad_time_raw = enabled_criteria.cad_submission_time
    if isinstance(cad_time_raw, time):
        cad_time = cad_time_raw
    elif isinstance(cad_time_raw, timedelta):
        cad_time = (datetime.min + cad_time_raw).time()
    elif isinstance(cad_time_raw, str):
        try:
            h, m, s = [int(x) for x in cad_time_raw.strip().split(".")]
            cad_time = time(h, m, s)
        except:
            frappe.throw("Invalid CAD Submission Time format.")
    else:
        cad_time = time(0, 0, 0)

    # Parse IBM approval time
    ibm_time_raw = enabled_criteria.cad_appoval_timefrom_ibm_team
    if isinstance(ibm_time_raw, time):
        ibm_timedelta = timedelta(hours=ibm_time_raw.hour, minutes=ibm_time_raw.minute, seconds=ibm_time_raw.second)
    elif isinstance(ibm_time_raw, timedelta):
        ibm_timedelta = ibm_time_raw
    elif isinstance(ibm_time_raw, str):
        try:
            h, m, s = [int(x) for x in ibm_time_raw.strip().split(".")]
            ibm_timedelta = timedelta(hours=h, minutes=m, seconds=s)
        except:
            frappe.throw("Invalid IBM Approval Time format.")
    else:
        ibm_timedelta = timedelta()

	for row in self.order_details:
		if row.status == 'Pending' and self.is_mannual == 1:
			frappe.throw(f"Status of row{row.idx} should be Done before approvedd")

        # Create Order
        docname = make_cad_order(row.name, parent_doc=self)

        # Link Pre Order Form Details
        if row.pre_order_form_details:
            frappe.db.set_value("Pre Order Form Details", row.pre_order_form_details, "order_form_id", self.name)

        # Set order_date to now
        order_datetime = now_datetime()
        frappe.db.set_value("Order", docname, "order_date", order_datetime)

        # Set delivery_date if available
        if self.delivery_date:
            frappe.db.set_value("Order", docname, "delivery_date", self.delivery_date)

        # Calculate CAD & IBM delivery dates
        cad_delivery_datetime = datetime.combine(order_datetime.date() + timedelta(days=cad_days), cad_time)
        ibm_delivery_datetime = cad_delivery_datetime + ibm_timedelta

        frappe.db.set_value("Order", docname, "cad_delivery_date", cad_delivery_datetime)
        frappe.db.set_value("Order", docname, "ibm_delivery_date", ibm_delivery_datetime)

        # Collect links for message
        doclist.append(get_link_to_form("Order", docname))

    # Final message
    if doclist:
        msg = _("The following {0} were created: {1}").format(
            frappe.bold(_("Orders")), "<br>" + ", ".join(doclist)
        )
        frappe.msgprint(msg)


def delete_auto_created_cad_order(self):
	for row in frappe.get_all("Order", filters={"order_form": self.name}):
		frappe.delete_doc("Order", row.name)

def make_cad_order(source_name, target_doc=None, parent_doc = None):
	def set_missing_values(source, target):
		target.cad_order_form_detail = source.name
		target.cad_order_form = source.parent
		target.index = source.idx
	
	
	design_type = frappe.get_doc('Order Form Detail',source_name).design_type
	item_type = frappe.get_doc('Order Form Detail',source_name).item_type
	# as_per_serial_no = frappe.get_doc('Order Form Detail',source_name).as_per_serial_no
	mod_reason = frappe.get_doc('Order Form Detail',source_name).mod_reason
	design_id = frappe.get_doc('Order Form Detail',source_name).design_id
	is_repairing = frappe.get_doc('Order Form Detail',source_name).is_repairing
	is_finding_order = frappe.get_doc('Order Form Detail',source_name).is_finding_order
	if design_type == 'Mod - Old Stylebio & Tag No':
		if is_repairing == 1:
			bom_or_cad = frappe.get_doc('Order Form Detail',source_name).bom_or_cad
			item_type = frappe.get_doc('Order Form Detail',source_name).item_type
		else:
		# 	variant_of = frappe.db.get_value("Item",design_id,"variant_of")
		# 	bom = frappe.db.get_value('Item',design_id,'master_bom')
		# 	if bom==None:
		# 		frappe.throw(f'BOM is not available for {design_id}')
		# 	attribute_list = make_atribute_list(source_name)
		# 	validate_variant_attributes(variant_of,attribute_list)
		# 	if mod_reason in ['No Design Change','Change in Metal Colour']:
		# 		item_type = "Only Variant"
		# 		# bom_or_cad = workflow_state_maker(source_name)
		# 	elif mod_reason in ['Attribute Change']:
		# 		attribute_list = make_atribute_list(source_name)
		# 		validate_variant_attributes(variant_of,attribute_list)
		# 		item_type = "Only Variant"
		# 		# bom_or_cad = 'Check'
		# 	elif mod_reason == 'Change in Metal Touch':
		# 		item_type = "No Variant No Suffix"
		# 		# bom_or_cad = workflow_state_maker(source_name)
		# 	else:
		# 		attribute_list = make_atribute_list(source_name)
		# 		validate_variant_attributes(variant_of,attribute_list)
		# 		# item_type = "Suffix Of Variant"
		# 		item_type = "Template and Variant"
		# 		# bom_or_cad = 'CAD'

			bom_or_cad = 'Check'
			# if frappe.db.get_value("Item",design_id,"Item_group") == 'Design DNU':
			# 	item_type = "Only Variant"
	elif design_type == 'Sketch Design':
		# variant_of = frappe.db.get_value("Item",design_id,"variant_of")
		# attribute_list = make_atribute_list(source_name)
		# validate_variant_attributes(variant_of,attribute_list)
		# item_type = "No Variant No Suffix"
		item_type = "Only Variant"
		bom_or_cad = 'CAD'
		# bom_or_cad = 'Check'
	elif design_type == 'As Per Design Type':
		item_type = "No Variant No Suffix"
		bom_or_cad = 'New BOM'
	elif is_finding_order:
		item_type = "No Variant No Suffix"
		bom_or_cad = 'New BOM'
	else:
		item_type = 'Template and Variant'
		bom_or_cad = 'CAD'

	doc = get_mapped_doc(
		"Order Form Detail",
		source_name,
		{
			"Order Form Detail": {
				"doctype": "Order" 
			}
		},target_doc, set_missing_values
	)

	for entity in parent_doc.get("service_type",[]):
		doc.append("service_type", {"service_type1": entity.service_type1})
	doc.parcel_place = parent_doc.parcel_place
	doc.company = parent_doc.company
	doc.form_remarks = parent_doc.remarks
	doc.india = parent_doc.india
	doc.usa = parent_doc.usa
	doc.india_states = parent_doc.india_states
	doc.item_type = item_type
	doc.bom_or_cad = bom_or_cad
	if design_type in ['New Design','Sketch Design']:
		doc.workflow_type = 'CAD'
	
	doc.save()
	if design_type == 'As Per Design Type' and item_type == "No Variant No Suffix" and bom_or_cad == 'New BOM':
		doc.submit()
		frappe.db.set_value("Order",doc.name,"workflow_state","Approved")
	return doc.name

def make_atribute_list(source_name):
	order_form_details = frappe.get_doc('Order Form Detail',source_name)
	all_variant_attribute = frappe.db.sql(
		f"""select item_attribute from `tabAttribute Value Item Attribute Detail` 
		where parent = '{order_form_details.subcategory}' and in_item_variant=1""",as_list=1
	)

	final_list = {}
	for i in all_variant_attribute:
		new_i = i[0].replace(' ','_').replace('/','').lower()
		final_list[i[0]] = order_form_details.get_value(new_i)
	return final_list
# def set_item_type(source_name):
# 	doc = frappe.get_doc('Order Form Detail',source_name)
	
# 	# all_variant_attribute = frappe.db.get_list('Attribute Value Item Attribute Detail',filters={'parent':doc.subcategory,'in_item_variant':1},fields=['item_attribute'])
# 	all_variant_attribute = frappe.db.sql(
# 		f"""select item_attribute from `tabAttribute Value Item Attribute Detail` where parent = '{doc.subcategory}' and in_item_variant=1""",as_dict=1
# 	)
# 	# suffix_attribute = frappe.db.get_list('Attribute Value Item Attribute Detail',filters={'parent':doc.subcategory,'suffix':1},fields=['item_attribute'])
# 	suffix_attribute = frappe.db.sql(
# 		f"""select item_attribute from `tabAttribute Value Item Attribute Detail` where parent = '{doc.subcategory}' and suffix=1""",as_dict=1
# 	)
# 	# print(suffix_attribute)

# 	all_attribute_list = []
# 	for variant_attribut in all_variant_attribute:
# 		item_attribute = variant_attribut['item_attribute'].lower().replace(' ','_')
# 		all_attribute_list.append(item_attribute)
	
# 	# bom_detail = frappe.db.get_value('BOM',{'is_active':1,'item':doc.design_id},all_attribute_list,as_dict=1)
# 	bom = frappe.db.get_value('Item',doc.design_id,'master_bom')
# 	if bom==None:
# 		frappe.throw(f'BOM is not available for {doc.design_id}')
# 	bom_detail = frappe.db.get_value('BOM',doc.bom,all_attribute_list,as_dict=1)
	
# 	all_item_type = []
# 	for attribute in suffix_attribute:
# 		item_attribute = attribute['item_attribute'].lower().replace(' ','_')
# 		if bom_detail[item_attribute] != frappe.db.get_value('Order Form Detail',source_name,item_attribute):
# 			item_type = 'Suffix Of Variant'
# 		else:
# 			item_type = 'Only Variant'
# 		all_item_type.append(item_type)
	
# 	if 'Suffix Of Variant' in all_item_type:
# 		item_type = 'Suffix Of Variant'
# 	else:
# 		item_type = 'Only Variant'

# 	return item_type


def workflow_state_maker(source_name):

	doc = frappe.get_doc('Order Form Detail',source_name)
	all_variant_attribute = frappe.db.sql(
		f"""select item_attribute from `tabAttribute Value Item Attribute Detail` where parent = '{doc.subcategory}' and in_item_variant=1""",as_dict=1
	)
	all_attribute_list = []
	for variant_attribut in all_variant_attribute:
		item_attribute = variant_attribut['item_attribute'].lower().replace(' ','_').replace('/','')
		all_attribute_list.append(item_attribute)
	
	bom_detail = frappe.db.get_value('BOM',doc.bom,all_attribute_list,as_dict=1)
	cad_attribute_list = frappe.db.sql(
		f"""select item_attribute from `tabAttribute Value Item Attribute Detail` where parent = '{doc.subcategory}' and in_cad_flow=1""",as_dict=1
	)
	
	all_bom_or_cad = []
	for i in cad_attribute_list:
		item_attribute = i['item_attribute'].lower().replace(' ','_')
		if str(bom_detail[item_attribute]).replace(".0","") != str(frappe.db.get_value('Order Form Detail',source_name,item_attribute)):
			bom_or_cad = 'CAD'
		else:
			bom_or_cad = 'New BOM'
		all_bom_or_cad.append(bom_or_cad)
	
	
	if 'CAD' in all_bom_or_cad:
		bom_or_cad = 'CAD'
	else:
		bom_or_cad = 'New BOM'

	return bom_or_cad


@frappe.whitelist()
def make_order_form(source_name,target_doc=None):
	if isinstance(target_doc, str):
		target_doc = json.loads(target_doc)
	if not target_doc:
		target_doc = frappe.new_doc("Order Form")
	else:
		target_doc = frappe.get_doc(target_doc)

	titan_order_form = frappe.db.get_value("Titan Order Form", source_name, "*")

	target_doc.append("order_details", {
		"category": titan_order_form.get("item_category"),
		"design_by": "Our Design",
		"design_type": "Mod - Old Stylebio & Tag No",
		"design_id": titan_order_form.get("design_code"),
		"titan_code": titan_order_form.get("titan_code"),
		"subcategory": titan_order_form.get("item_subcategory"),
		"bom": titan_order_form.get("bom"),
		"serial_no_bom": titan_order_form.get("serial_no_bom"),
		"tag_no": titan_order_form.get("serial_no"),
		"metal_type": titan_order_form.get("metal_type"),
		"metal_touch": titan_order_form.get("metal_touch"),
		"metal_purity": titan_order_form.get("metal_purity"),
		"metal_colour": titan_order_form.get("metal_colour"),
		"product_size": titan_order_form.get("product_size"),
		"setting_type": titan_order_form.get("setting_type"),
		"delivery_date": titan_order_form.get("delivery_date"),
		"enamal": titan_order_form.get("enamal"),
		"rhodium": titan_order_form.get("rhodium"),
	})


	return target_doc


# @frappe.whitelist()
# def get_metal_color_varinat(metal_colour,design_id):
# 	variant_of = frappe.db.get_value('Item',{'name':design_id},'variant_of')
# 	all_variant = frappe.db.get_all('Item',filters={'variant_of':variant_of},pluck='name')
# 	for i in all_variant:
# 		print(frappe.db.sql(f"""SELECT attribute_value  from `tabItem Variant Attribute` tiva where parent ='{i}' and `attribute`= 'Metal Colour'""",as_dict=1))
# 		if metal_colour == frappe.db.sql(f"""SELECT attribute_value  from `tabItem Variant Attribute` tiva where parent ='{i}' and `attribute`= 'Metal Colour'""",as_dict=1)[0]['attribute_value']:
# 			return i
		
# def check_varinat(source_name):
# 	row = frappe.get_doc('Order Form Detail',source_name)
# 	# variant_of,item_subcategory = frappe.db.get_value('Item',{'name':row.design_id},['variant_of','item_subcategory'])
# 	# all_variant = frappe.db.get_all('Item',filters={'variant_of':variant_of},pluck='name')

# 	item_subcategory = row.subcategory
# 	all_attribute = frappe.db.sql(f"""select item_attribute  from `tabAttribute Value Item Attribute Detail` taviad  where parent = '{item_subcategory}' and in_item_variant =1""",as_dict=1)
# 	a = []
# 	for i in all_variant:
# 		variant_attrbute_value_list = []
# 		for j in all_attribute:
# 			attribute_value = frappe.db.sql(f"""SELECT attribute_value  from `tabItem Variant Attribute` tiva where parent ='{i}' and `attribute`= '{j['item_attribute']}'""",as_dict=1)
# 			if attribute_value:
# 				variant_attrbute_value_list.append(attribute_value[0]['attribute_value'])
# 			else:
# 				variant_attrbute_value_list.append('')
# 		a.append([i,variant_attrbute_value_list])
	
# 	current_data = []
# 	for k in all_attribute:
# 		av = frappe.db.get_value('Order Form Detail',row.name,k['item_attribute'].replace(' ','_').lower())
# 		if type(av) == float:
# 			av = "{:g}".format(av)
# 		current_data.append(av)


# 	is_present = any(current_data == sublist[1] for sublist in a)
	
# 	if is_present:
# 		matching_sublist = next(sublist for sublist in a if current_data == sublist[1])
# 		first_element = matching_sublist[0]
# 		return first_element
	# else:
	# 	return row.design_id

# @frappe.whitelist()
# def get_bom_details(design_id,doc):
# 	doc = json.loads(doc)
# 	if doc['is_finding_order']:
# 		master_bom = frappe.db.get_value("BOM",{"bom_type":"Template","item":design_id},"name",order_by="creation DESC")
# 		frappe.throw(f"{master_bom}//{doc['is_finding_order']}")
	
# 	item_subcategory = frappe.db.get_value("Item",design_id,"item_subcategory")

# 	fg_bom = frappe.db.get_value("BOM",{"bom_type":"Finished Goods","item":design_id},"name",order_by="creation DESC")
# 	master_bom = fg_bom
# 	if not fg_bom:
# 		temp_bom = frappe.db.get_value("Item",design_id,"master_bom")
# 		master_bom = temp_bom
# 	if not master_bom:
# 		frappe.throw(f"Master BOM for Item <b>{get_link_to_form('Item',design_id)}</b> is not set")
# 	all_item_attributes = []

# 	for i in frappe.get_doc("Attribute Value",item_subcategory).item_attributes:
# 		all_item_attributes.append(i.item_attribute.replace(' ','_').replace('/','').lower())
	
# 	with_value = frappe.db.get_value("BOM",master_bom,all_item_attributes,as_dict=1)
# 	with_value['master_bom'] = master_bom
# 	return with_value
@frappe.whitelist()
def get_bom_details(design_id, doc):
	doc = json.loads(doc)

	if doc['is_finding_order']:
		master_bom = frappe.db.get_value("BOM", {"bom_type": "Template", "item": design_id}, "name", order_by="creation DESC")
		frappe.throw(f"{master_bom}//{doc['is_finding_order']}")

	item_subcategory = frappe.db.get_value("Item", design_id, "item_subcategory")
	item_info = frappe.db.get_value("Item", design_id, ["item_category", "item_subcategory"], as_dict=1) or {}
	fg_bom = frappe.db.get_value("BOM", {"bom_type": "Finished Goods", "item": design_id}, "name", order_by="creation DESC")
	master_bom = fg_bom or frappe.db.get_value("Item", design_id, "master_bom")

	if not master_bom:
		frappe.throw(f"Master BOM for Item <b>{get_link_to_form('Item', design_id)}</b> is not set")

	# Prepare attribute keys from subcategory
	attribute_keys = []
	attribute_pairs = []

	for attr in frappe.get_doc("Attribute Value", item_subcategory).item_attributes:
		formatted = attr.item_attribute.replace(' ', '_').replace('/', '').lower()
		attribute_keys.append(formatted)
		attribute_pairs.append((attr.item_attribute, formatted))

	# Get values from Item Variant Attribute table
	variant_attributes = frappe.db.get_all("Item Variant Attribute", filters={"parent": design_id}, fields=["attribute", "attribute_value"])
	variant_map = {d.attribute.replace(' ', '_').replace('/', '').lower(): d.attribute_value for d in variant_attributes}

	# Get fallback values from BOM
	bom_values = frappe.db.get_value("BOM", master_bom, attribute_keys, as_dict=1)

	with_value = {}
	for original_name, formatted_key in attribute_pairs:
		with_value[formatted_key] = variant_map.get(formatted_key) or bom_values.get(formatted_key)

	with_value['bom'] = master_bom
	with_value['category'] = item_info.get("item_category") or ""
	with_value['subcategory'] = item_info.get("item_subcategory") or ""
	return with_value

def validate_variant_attributes(variant_of,attribute_list):
	args = attribute_list
	variant = get_variant(variant_of, args)
	if variant:
		frappe.throw(
			_("Item variant <b>{0}</b> exists with same attributes").format(get_link_to_form("Item",variant)), ItemVariantExistsError
		)

@frappe.whitelist()
def get_metal_purity(metal_type,metal_touch,customer):
	metal_purity = frappe.db.sql(f"""select metal_purity from `tabMetal Criteria` where parent = '{customer}' and metal_type = '{metal_type}' and metal_touch = '{metal_touch}'""",as_dict=1)
	return metal_purity


@frappe.whitelist()
def get_sketh_details(design_id):
	
	db_data = frappe.db.sql(f"select name,attribute, attribute_value from `tabItem Variant Attribute` where parent = '{design_id}'",as_dict=1)
	final_data = {}
	sketch_order_id = frappe.db.get_value("Item",design_id,"custom_sketch_order_id")
	final_data['item_category'] = frappe.db.get_value("Item",design_id,"item_category")
	final_data['item_subcategory'] = frappe.db.get_value("Item",design_id,"item_subcategory")
	final_data['setting_type'] = frappe.db.get_value("Item",design_id,"setting_type")
	final_data['sub_setting_type1'] = frappe.db.get_value("Sketch Order",sketch_order_id,"sub_setting_type1")
	final_data['sub_setting_type2'] = frappe.db.get_value("Sketch Order",sketch_order_id,"sub_setting_type2")
	final_data['qty'] = frappe.db.get_value("Sketch Order",sketch_order_id,"qty")
	final_data['metal_type'] = frappe.db.get_value("Sketch Order",sketch_order_id,"metal_type")
	final_data['metal_touch'] = frappe.db.get_value("Sketch Order",sketch_order_id,"metal_touch")
	final_data['metal_colour'] = frappe.db.get_value("Sketch Order",sketch_order_id,"metal_colour")
	final_data['metal_target'] = frappe.db.get_value("Item",design_id,"approx_gold")
	final_data['diamond_target'] = frappe.db.get_value("Item",design_id,"approx_diamond")
	final_data['product_size'] = frappe.db.get_value("Sketch Order",sketch_order_id,"product_size")
	final_data['sizer_type'] = frappe.db.get_value("Sketch Order",sketch_order_id,"sizer_type")
	final_data['length'] = frappe.db.get_value("Sketch Order",sketch_order_id,"length")
	final_data['width'] = frappe.db.get_value("Sketch Order",sketch_order_id,"width")
	final_data['height'] = frappe.db.get_value("Sketch Order",sketch_order_id,"height")
	for i in db_data:
		if i.attribute_value in [None,'']:
			continue
		final_data[i.attribute.lower().replace(' ','_')]=i.attribute_value
	return final_data

@frappe.whitelist()
def get_item_details(item_code):
	item_code = frappe.db.sql(f"""select attribute,attribute_value from `tabItem Variant Attribute` where parent = '{item_code}'""")
	return item_code

@frappe.whitelist()
def item_attribute_query(doctype, txt, searchfield, start, page_len, filters):
	args = {
		'item_attribute': filters.get("item_attribute"),
		"txt": "%{0}%".format(txt),
	}
	condition = ''
	if filters.get("customer_code"):		
		if filters.get("item_attribute") == "Metal Touch":
			args["customer_code"] = filters.get("customer_code")
			condition += "and attribute_value in (select metal_touch from `tabMetal Criteria`  where parent = %(customer_code)s)"

	item_attribute = frappe.db.sql(f"""select attribute_value
			from `tabItem Attribute Value`
				where parent = %(item_attribute)s 
				and attribute_value like %(txt)s {condition}
			""",args)
	return item_attribute if item_attribute else []

@frappe.whitelist()
def get_customer_orderType(customer_code):
	order_type = frappe.db.sql(
		f""" select order_type from `tabOrder Type` where parent= '{customer_code}' """, as_dict=1
	)

	return order_type

@frappe.whitelist()
def get_customer_order_form(source_name, target_doc=None):
	if isinstance(target_doc, str):
		target_doc = json.loads(target_doc)
	target_doc = frappe.new_doc("Order Form") if not target_doc else frappe.get_doc(target_doc)

	if source_name:
		customer_order_form = frappe.db.sql(f"""SELECT * FROM `tabCustomer Order Form Detail` 
							WHERE parent = '{source_name}' AND docstatus = 1""", as_dict=1)
	if not customer_order_form:
		frappe.msgprint(_("Please submit the Customer Order Form"))
		return target_doc

	for i in customer_order_form:
		item, order_id = i.get("design_code"), i.get("order_id")
		order_data = frappe.db.sql(f"SELECT * FROM `tabOrder` WHERE name = '{order_id}'", as_dict=1)
		customer_design_code = frappe.db.sql(f"SELECT * FROM `tabBOM` WHERE item = '{item}' AND name = '{i.get('design_code_bom')}'", as_dict=1)
		item_serial = frappe.db.get_value("Serial No", {'item_code': item}, 'name')

		data_source = order_data if order_data else customer_design_code
		if data_source:
			for j in data_source:
				target_doc.append("order_details", {
					"delivery_date": target_doc.delivery_date,
					"design_by": j.get('design_by'),
					"design_type": j.get('design_type'),
					"qty": j.get('qty'),
					"design_id": j.get("item", item),
					"bom": j.get("new_bom", i.get('design_code_bom')),
					"tag_no": item_serial or j.get('tag_no'),
					"diamond_quality": i.get("diamond_quality"),
					"customer_order_form": i.get("parent"),
					"category": i.get("category"),
					"subcategory": i.get("subcategory"),
					"setting_type": i.get("setting_type"),
					"theme_code": i.get("theme_code"),
					"metal_type": i.get("metal_type"),
					"metal_touch": i.get("metal_touch"),
					"metal_colour": i.get("metal_colour"),
					"metal_target": i.get("metal_target"),
					"diamond_target": i.get("diamond_target"),
					"feature": i.get("feature"),
					"product_size": i.get("product_size"),
					"rhodium": i.get("rhodium"),
					"enamal": j.get("enamal"),
					"sub_setting_type1": j.get("sub_setting_type1"),
					"sub_setting_type2": j.get("sub_setting_type2"),
					"sizer_type": j.get("sizer_type"),
					"stone_changeable": j.get("stone_changeable"),
					"detachable": j.get("detachable"),
					"lock_type": j.get("lock_type"),
					"capganthan": j.get("capganthan"),
					"charm": j.get("charm"),
					"back_chain": j.get("back_chain"),
					"back_chain_size": j.get("back_chain_size"),
					"back_belt": j.get("back_belt"),
					"back_belt_length": j.get("back_belt_length"),
					"black_beed_line": j.get("black_beed_line"),
					"back_side_size": j.get("back_side_size"),
					"back_belt_patti": j.get("back_belt_patti"),
					"two_in_one": j.get("two_in_one"),
					"number_of_ant": j.get("number_of_ant"),
					"distance_between_kadi_to_mugappu": j.get("distance_between_kadi_to_mugappu"),
					"space_between_mugappu": j.get("space_between_mugappu"),
					"chain_type": j.get("chain_type"),
					"customer_chain": j.get("customer_chain"),
					"nakshi_weght": j.get("nakshi_weght"),
				})
	return target_doc

def validate_item_variant(self):
	for i in self.order_details:
		if i.design_type == "Sketch Design" and i.design_id:
			custom_sketch_order_id = frappe.db.get_value("Item", i.design_id, "custom_sketch_order_id")
			if custom_sketch_order_id:
				# Get all variants where variant_of = i.design_id
				variants = frappe.get_all("Item",
					filters={"variant_of": i.design_id},
					fields=["name"]
				)
				if variants:
					variant_names = ", ".join(item.name for item in variants)
					frappe.throw(f"""
						You already created a variant for this Design ID ({i.design_id}).<br><br>
						Items found: {variant_names}<br><br>
						You cannot create another variant using <b>Sketch Design</b>.<br>
						Please select <b>Design Type = 'Mod - Old Stylebio & Tag No'</b> and select the variant in Design ID.
					""")

def validate_design_id(self):
	for i in self.order_details:
		if i.subcategory:
			parent = frappe.db.get_value("Attribute Value", i.subcategory, "parent_attribute_value")
			if i.category != parent:
				frappe.throw(_(f"Category & Sub Category mismatched in row #{i.idx}"))
		# If tagno exists, find all matching enabled Items by old_tag_no
		if i.tagno and i.design_type != 'Sketch Design':
			matching_item = frappe.db.get_value("Item",{"old_tag_no": i.tagno, "disabled": 0},"name",order_by="creation desc")
			if matching_item:
				matching_bom = frappe.db.get_value("Item",matching_item,"master_bom")
				# Set design_id only if not manually overridden
				if not i.design_id or i.design_id == matching_item:
					i.design_id = matching_item
					if not i.bom:
						i.bom = matching_bom
					
		if i.design_type == "Sketch Design" and i.design_id:
			custom_sketch_order_id = frappe.db.get_value("Item", i.design_id, "custom_sketch_order_id")
			if custom_sketch_order_id:
				# Get all variants where variant_of = i.design_id
				variants = frappe.db.get_list("Item",filters={"variant_of": i.design_id,"disabled":0},pluck="name")
				if variants:
					# variant_names = ", ".join(item.name for item in variants)
					variant_names = ", ".join(variant_names)
					frappe.throw(f"""
						You already created a variant for this Design ID ({i.design_id}).<br><br>
						Items found: {variant_names}<br><br>
						You cannot create another variant using <b>Sketch Design</b>.<br>
						Please select <b>Design Type = 'Mod - Old Stylebio & Tag No'</b> and select the variant in Design ID.
					""")

def set_data(self):
	if self.order_details:
		for i in self.order_details:
			if i.design_type in ['As Per Design Type','Mod - Old Stylebio & Tag No'] and i.design_id:
				try:
					design_id = i.design_id
					item_subcategory = frappe.db.get_value("Item", design_id, "item_subcategory")
					master_bom = i.bom

					# Prepare a list to hold the item attribute names formatted as per your requirements
					all_item_attributes = []
					
					# Retrieve all item attributes for the given item subcategory
					for item_attr in frappe.get_doc("Attribute Value", item_subcategory).item_attributes:
						# Format the item attribute names by replacing spaces with underscores, removing '/', and converting to lower case
						formatted_attr = item_attr.item_attribute.replace(' ', '_').replace('/', '').lower()
						all_item_attributes.append(formatted_attr)
					
					# Retrieve the values for the specified attributes from the BOM
					attribute_values = frappe.db.get_value("BOM", master_bom, all_item_attributes, as_dict=1)
					
					# Dynamically set the attributes on self with the retrieved values
					for key, value in attribute_values.items():
						if str(key) == "item_category":
							key = "category"
						if str(key) == "item_subcategory":
							key = "subcategory"
						a = getattr(i, key, value)
						# frappe.throw(f"{a}")
						if a:
							continue
						else:
							setattr(i, key, value)
				except:
					frappe.throw(f"Row {i.idx} has Issue.Check BOM first.")

def create_po(self):
	qty = 0
	po_doc = frappe.new_doc("Purchase Order")
	po_doc.supplier = self.supplier
	po_doc.transaction_date = self.delivery_date
	po_doc.company = self.company
	po_doc.branch = self.branch
	po_doc.project = self.project
	po_doc.purchase_type = 'Subcontracting'
	# po_doc.custom_form = "Order Form"
	# po_doc.custom_form_id = self.name
	po_doc.schedule_date = self.delivery_date

	po_item_log = po_doc.append("items", {})
	if self.purchase_type == 'Design':
		po_item_log.item_code = "Design Expness"
	elif self.purchase_type == 'RPT':
		po_item_log.item_code = "RPT Expness"
	elif self.purchase_type == 'Model':
		total_weight = 0
		# qty_18 = 0
		# qty_22 = 0
		item_code = ''
		for i in self.order_details:
			# total_weight += i.total_weight
			if i.metal_touch == '18KT':
				item_code = "Semi Finish Goods 18KT"
			if i.metal_touch == '22KT':
				item_code = "Semi Finish Goods 22KT"
		po_item_log.item_code = item_code
		# po_item_log.total_weight = total_weight
		# po_item_log.weight_per_unit = total_weight/qty_22
	elif self.purchase_type == 'Mould':
		po_item_log.item_code = "Mould Expness"
	
	if self.purchase_type in ['Model']:
		qty_18 = 0
		qty_22 = 0
		for i in self.order_details:
			if i.metal_touch == '18KT':
				qty_18 += i.qty
			if i.metal_touch == '22KT':
				qty_22 += i.qty
		if qty_18:
			qty = qty_18
		else:
			qty = qty_22
	else:
		for i in self.order_details:
			qty+=i.qty
	
	po_item_log.qty = qty
	po_item_log.schedule_date = self.delivery_date
	po_item_log.schedule_date = self.delivery_date
	po_item_log.qty = len(self.order_details)

	# po_doc.set("payment_schedule", [])
	# po_trn_log = po_doc.append("payment_schedule", {})
	# po_trn_log.due_date = self.delivery_date
	# po_trn_log.invoice_portion = 100.0

	
	po_doc.save()
	po_name = po_doc.name
	frappe.db.set_value("Purchase Order",po_name,"custom_form","Order Form")
	frappe.db.set_value("Purchase Order",po_name,"custom_form_id",self.name)
	msg = _("The following {0} is created: {1}").format(
			frappe.bold(_("Purchase Order")), "<br>" + get_link_to_form("Purchase Order", po_name)
		)
	
	frappe.msgprint(msg)

@frappe.whitelist()
def make_from_pre_order_form(source_name, target_doc=None):
	if isinstance(target_doc, str):
		target_doc = json.loads(target_doc)
	target_doc = frappe.new_doc("Order Form") if not target_doc else frappe.get_doc(target_doc)

	if source_name:
				customer_order_form = frappe.db.sql(f"""SELECT * FROM `tabPre Order Form Details` 
							WHERE parent = '{source_name}'""", as_dict=1)
		# customer_order_form = frappe.db.sql(f"""SELECT * FROM `tabPre Order Form Details` 
		# 					WHERE parent = '{source_name}' AND docstatus = 1""", as_dict=1)

	# parent = frappe.db.get_value("Pre Order Form Details",source_name)
	target_doc.customer_code = frappe.db.get_value("Pre Order Form",source_name,"customer_code")
	target_doc.order_date = frappe.db.get_value("Pre Order Form",source_name,"order_date")
	target_doc.salesman_name = frappe.db.get_value("Pre Order Form",source_name,"sales_person")
	target_doc.diamond_quality = frappe.db.get_value("Pre Order Form",source_name,"diamond_quality")
	target_doc.branch = frappe.db.get_value("Pre Order Form",source_name,"branch")
	target_doc.order_type = frappe.db.get_value("Pre Order Form",source_name,"order_type")
	target_doc.due_days = frappe.db.get_value("Pre Order Form",source_name,"due_days")
	target_doc.po_no = frappe.db.get_value("Pre Order Form",source_name,"po_no")
	target_doc.delivery_date = frappe.db.get_value("Pre Order Form",source_name,"delivery_date")
	target_doc.pre_order_form = source_name
	# target_doc.branch = frappe.db.get_value("Pre Order Form",source_name,"customer")
	service_types = frappe.db.get_values("Service Type 2", {"parent": source_name},"service_type1")
	for service_type in service_types:
		target_doc.append("service_type",{"service_type1": service_type[0]})
	
	shipping_territories = frappe.db.get_values("Territory Multi Select", {"parent": source_name},"territory")
	for shipping_territory in shipping_territories:
		target_doc.append("parcel_place",{"territory": shipping_territory[0]})

	for i in customer_order_form:
		# frappe.throw(f"{i}")
		# item, order_id = i.get("design_code"), i.get("order_id")
		# order_data = frappe.db.sql(f"SELECT * FROM `tabOrder` WHERE name = '{order_id}'", as_dict=1)
		# customer_design_code = frappe.db.sql(f"SELECT * FROM `tabBOM` WHERE item = '{item}' AND name = '{i.get('design_code_bom')}'", as_dict=1)
		# item_serial = frappe.db.get_value("Serial No", {'item_code': item}, 'name')

		# data_source = order_data if order_data else customer_design_code
		# if data_source:
		# 	for j in data_source:
		if i.status == 'Done':
			design_id = i.item_variant
			item_subcategory = frappe.db.get_value("Item", design_id, "item_subcategory")
			master_bom = i.bom

			extra_fields = {}

			if item_subcategory and master_bom:
				all_item_attributes = []
				for item_attr in frappe.get_doc("Attribute Value", item_subcategory).item_attributes:
					formatted_attr = item_attr.item_attribute.replace(' ', '_').replace('/', '').lower()
					all_item_attributes.append((item_attr.item_attribute, formatted_attr))

				# Build dict from Item Variant Attributes
				variant_attributes = frappe.db.get_all("Item Variant Attribute",
					filters={"parent": design_id},
					fields=["attribute", "attribute_value"]
				)
				variant_attr_map = {d.attribute.replace(' ', '_').replace('/', '').lower(): d.attribute_value for d in variant_attributes}

				# Fetch fallback values from BOM
				attribute_values = frappe.db.get_value("BOM", master_bom, [f[1] for f in all_item_attributes], as_dict=1)

				for original_name, formatted_name in all_item_attributes:
					value = variant_attr_map.get(formatted_name) or attribute_values.get(formatted_name)
					if value:
						fieldname = "category" if formatted_name == "item_category" else \
									"subcategory" if formatted_name == "item_subcategory" else formatted_name
						extra_fields[fieldname] = value

			target_doc.append("order_details", {
				"design_by":i.design_by,
				"design_type":i.design_type,
				"order_type":i.order_type,
				"delivery_date":frappe.db.get_value("Pre Order Form",source_name,"delivery_date"),
				"diamond_quality":frappe.db.get_value("Pre Order Form",source_name,"diamond_quality"),
				"design_id": i.item_variant,
				"mod_reason":i.mod_reason,
				"bom":i.bom,
				"category":i.new_category,
				"subcategory":i.new_sub_category,
				"metal_target":i.gold_target,
				"diamond_target":i.diamond_target,
				"setting_type":i.bom_setting_type,
				"pre_order_form_details":i.name,
				"diamond_type":"Natural",
				"jewelex_batch_no":i.bulk_order_no,
				"design_image_1":i.design_image,
				**({"metal_touch": i.metal_touch} if i.design_type == "New Design" else {}),
				**({"metal_colour": i.metal_color} if i.design_type == "New Design" else {}),
				**extra_fields
			})
			
	return target_doc


@frappe.whitelist()
def validate_rows(docname):
    doc = frappe.get_doc("Order Form", docname)
    return doc.validate_rows()


