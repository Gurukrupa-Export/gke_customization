# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe,json
import requests
from frappe import _
from frappe.utils import get_link_to_form
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document
from frappe.model.workflow import apply_workflow
from frappe.utils import now_datetime
class RepairOrderForm(Document):
	def on_submit(self):
		if not self.order_details:
			frappe.throw("Add atleast One Row in table")
		create_serial_and_design_order(self)

	def on_cancel(self):
		delete_auto_created_serial_and_design_order(self)



def create_serial_and_design_order(self):
	doclist = []
	for row in self.order_details:
		docname = make_serial_and_design_order(row.name, parent_doc = self)
		order_datetime = now_datetime()
		frappe.db.set_value("Repair Order", docname, "order_date", order_datetime)
		if self.delivery_date:
			# Ffrappe.throw(f'{self.delivery_date}')
			frappe.db.set_value("Repair Order", docname, "delivery_date", self.delivery_date)
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

		if source.repair_type == 'Refresh & Replace Defective Material':
			frappe.db.set_value("Repair Order Form Detail",source.name,"required_design","No")
			target.required_design = "No"
			# target.docstatus = 1
			# frappe.db.set_value("Repair Order",target,"workflow_state","Approved")


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
	
	doc.customer_code = parent_doc.customer_code
	doc.po_no = parent_doc.po_no
	doc.parcel_place = parent_doc.parcel_place
	doc.product_type = parent_doc.product_type
	# doc.project = parent_doc.project
	# doc.due_days = parent_doc.due_days
	# doc.form_remarks = parent_doc.remarks
	doc.save()
	if (doc.required_design == "No" and doc.product_return_order and doc.docstatus == 0):
		apply_workflow(doc, "Approve")
	# if doc.
	return doc.name

@frappe.whitelist()
def get_bom_details(design_id,serial_no):
	item_subcategory = frappe.db.get_value("Item",design_id,"item_subcategory")
	if serial_no:
		master_bom = frappe.db.get_value("Serial No",serial_no,"custom_bom_no")
		serial_no_bom = master_bom
		bom = frappe.db.get_value("Item",design_id,"master_bom")
	else:
		master_bom = frappe.db.get_value("Item",design_id,"master_bom")
		bom = master_bom

	if not master_bom:
		frappe.throw(f"Master BOM for Item <b>{get_link_to_form('Item',design_id)}</b> is not set")
	all_item_attributes = []

	for i in frappe.get_doc("Attribute Value",item_subcategory).item_attributes:
		all_item_attributes.append(i.item_attribute.replace(' ','_').replace('/','').lower())
	all_item_attributes.append("diamond_quality")
	# frappe.throw(f"{all_item_attributes}")
	with_value = frappe.db.get_value("BOM",master_bom,all_item_attributes,as_dict=1)
	with_value['master_bom'] = master_bom
	with_value['serial_no_bom'] = serial_no_bom
	with_value['bom'] = bom
	with_value['gross_weight'] = frappe.db.get_value("BOM",master_bom,"gross_weight")
	
	return with_value




@frappe.whitelist()
def get_bom_detail(design_id, bom):

    item_subcategory = frappe.db.get_value(
        "Item",
        design_id,
        "item_subcategory"
    )

    master_bom = bom

    if not master_bom:
        frappe.throw(
            f"Master BOM for Item "
            f"<b>{get_link_to_form('Item', design_id)}</b> is not set"
        )

    def norm(x):
        return str(x).replace(" ", "_").replace("/", "").lower()

    def clean(v):
        if v is None:
            return None

        if isinstance(v, str) and v.strip().lower() in (
            "none",
            "null",
            ""
        ):
            return None

        return v

    def is_empty(v):
        if v is None:
            return True

        if isinstance(v, str) and v.strip().lower() in (
            "none",
            "null",
            ""
        ):
            return True

        return False

    # --------------------------------------------------
    # 1. Expected attributes from Item Subcategory
    # --------------------------------------------------

    expected_keys = []

    if item_subcategory:
        subcategory_doc = frappe.get_doc(
            "Attribute Value",
            item_subcategory
        )

        expected_keys = [
            norm(attr.item_attribute)
            for attr in subcategory_doc.item_attributes
            if attr.item_attribute
        ]

    # --------------------------------------------------
    # 2. Variant attributes
    # --------------------------------------------------

    variant_attributes = frappe.db.get_all(
        "Item Variant Attribute",
        filters={
            "parent": design_id
        },
        fields=[
            "attribute",
            "attribute_value"
        ]
    )

    variant_map = {
        norm(d.attribute): clean(d.attribute_value)
        for d in variant_attributes
        if d.attribute
    }

    # --------------------------------------------------
    # 3. BOM metadata
    # --------------------------------------------------

    bom_meta_fields = {
        f.fieldname
        for f in frappe.get_meta("BOM").fields
    }

    # --------------------------------------------------
    # 4. Fixed fields that should always be fetched
    # --------------------------------------------------

    fixed_bom_fields = [
        "metal_target",
        "qty",
        "metal_type",
        "metal_touch",
        "metal_purity",
        "metal_colour",

        "item_category",
        "item_subcategory",

        "lock_type",
        "setting_type",
        "sub_setting_type1",
        "sub_setting_type2",

        "gemstone_quality",
        "gemstone_type",
        "gemstone_type1",

        "gross_weight",
        "diamond_quality",
        "diamond_target",

        "product_size",
        "sizer_type",

        "length",
        "height",
        "width",

        "stone_changeable",
        "space_between_mugappu",

        "two_in_one",
        "detachable",
        "feature",

        "back_chain",
        "back_chain_size",
        "back_belt",
        "back_belt_length",
        "black_beed",
        "black_beed_line",
        "back_side_size",
        "back_belt_patti",

        "vanki_type",
        "rhodium",

        "chain",
        "chain_type",
        "customer_chain",
        "chain_weight",
        "chain_length",
        "chain_thickness",
        "chain_from",

        "enamal",
        "charm",
        "capganthan",

        "number_of_ant"
    ]

    # Only fetch fields that actually exist
    safe_fields = [
        field
        for field in fixed_bom_fields
        if field in bom_meta_fields
    ]

    # Also fetch expected attribute fields
    for field in expected_keys:
        if field in bom_meta_fields and field not in safe_fields:
            safe_fields.append(field)

    # --------------------------------------------------
    # 5. Fetch BOM
    # --------------------------------------------------

    bom_values = {}

    if safe_fields:
        raw = frappe.db.get_value(
            "BOM",
            master_bom,
            safe_fields,
            as_dict=True
        ) or {}

        bom_values = {
            key: clean(value)
            for key, value in raw.items()
        }

    # --------------------------------------------------
    # 6. Merge
    # Variant value > BOM value
    # --------------------------------------------------

    final_data = {}

    all_keys = set(
        expected_keys
        + list(variant_map.keys())
        + list(bom_values.keys())
    )

    for key in all_keys:

        variant_val = variant_map.get(key)
        bom_val = bom_values.get(key)

        if not is_empty(variant_val):
            final_data[key] = variant_val

        elif not is_empty(bom_val):
            final_data[key] = bom_val

        else:
            final_data[key] = None

    # --------------------------------------------------
    # 7. Return BOM name
    # --------------------------------------------------

    final_data["master_bom"] = master_bom

    return final_data

@frappe.whitelist()
def get_data_from_jwelex(self,tag_no,company):
	url = "http://3.108.219.130:8001/credit-note"

	response = requests.get(
		url,
		params={"tag_no": tag_no,"company":company},
		timeout=30
	)

	response.raise_for_status()
	return response.json()













