# Copyright (c) 2026, [Your Company] and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"label": "Creation Pattern",
			"fieldname": "creation_pattern",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": "Code Status",
			"fieldname": "code_status",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": "Item Category",
			"fieldname": "item_category",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": "Item Subcategory",
			"fieldname": "item_subcategory",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": "Setting Style",
			"fieldname": "setting_style",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": "Subsetting Style",
			"fieldname": "subsetting_style",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": "Sketch Design Code",
			"fieldname": "sketch_design_code",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": "CAD Design Code",
			"fieldname": "cad_design_code",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": "Template BOM",
			"fieldname": "template_bom",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": "Stylebio",
			"fieldname": "stylebio",
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"label": "Tag No",
			"fieldname": "tag_no",
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"label": "Master Serial Number: Gold",
			"fieldname": "master_serial_gold",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": "Master Finished Good BOM : Gold",
			"fieldname": "master_fg_bom_gold",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": "Master Serial Number : Silver",
			"fieldname": "master_serial_silver",
			"fieldtype": "Data",
			"width": 190,
		},
		{
			"label": "Master FG BOM : Silver",
			"fieldname": "master_fg_bom_silver",
			"fieldtype": "Data",
			"width": 170,
		},
		{
			"label": "GC: G to D / D to G",
			"fieldname": "gc_ratio",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": "GC Remark",
			"fieldname": "gc_remark",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": "Template wise: deactive code count",
			"fieldname": "template_deactive_count",
			"fieldtype": "Int",
			"width": 200,
		},
		{
			"label": "Suffix/Set/Similar remarks",
			"fieldname": "similar_remarks",
			"fieldtype": "Data",
			"width": 220,
		},
		{
			"label": "Suffix/Set/Similar Design Code",
			"fieldname": "similar_design_code",
			"fieldtype": "Data",
			"width": 220,
		},
		{
			"label": "Sketch Image",
			"fieldname": "sketch_image",
			"fieldtype": "Attach Image",
			"width": 100,
		},
		{
			"label": "Cad Front Image",
			"fieldname": "cad_front_image",
			"fieldtype": "Attach Image",
			"width": 100,
		},
		{
			"label": "Product image",
			"fieldname": "product_image",
			"fieldtype": "Attach Image",
			"width": 100,
		},
		{
			"label": "Additional Available Images Count",
			"fieldname": "additional_images_count",
			"fieldtype": "Int",
			"width": 220,
		},
		{
			"label": "ERP Creation Date",
			"fieldname": "erp_creation_date",
			"fieldtype": "Date",
			"width": 140,
		},
		{
			"label": "Created by: Customer Name",
			"fieldname": "customer_name",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": "Developed by: Designer/Supplier Name",
			"fieldname": "designer_name",
			"fieldtype": "Data",
			"width": 220,
		},
	]


def get_conditions(filters):
	conditions = ""

	if filters.get("item_category"):
		conditions += " AND it.item_category = %(item_category)s"

	if filters.get("item_subcategory"):
		conditions += " AND it.item_subcategory = %(item_subcategory)s"

	if filters.get("setting_type"):
		conditions += " AND it.setting_type = %(setting_type)s"

	if filters.get("sub_setting_type"):
		conditions += " AND it.sub_setting_type = %(sub_setting_type)s"

	if filters.get("code_status"):
		if filters.get("code_status") == "Active":
			conditions += " AND it.disabled = 0"
		elif filters.get("code_status") == "Deactive":
			conditions += " AND it.disabled = 1"

	if filters.get("tag_no"):
		conditions += " AND it.tag_no = %(tag_no)s"

	if filters.get("customer_code"):
		conditions += " AND ord.customer_code = %(customer_code)s"

	if filters.get("from_date"):
		conditions += " AND ord.order_date >= %(from_date)s"

	if filters.get("to_date"):
		conditions += " AND ord.order_date <= %(to_date)s"

	return conditions


def get_data(filters):
	conditions = get_conditions(filters)

	query = """
		SELECT
			it.custom_reason_for_design_code_                              AS creation_pattern,
			IF(it.disabled = 1, 'Deactive', 'Active')                      AS code_status,
			it.item_category                                               AS item_category,
			it.item_subcategory                                            AS item_subcategory,
			it.setting_type                                                AS setting_style,
			it.sub_setting_type                                            AS subsetting_style,
			it.maching_design_id                                           AS sketch_design_code,
			NULL                                                            AS cad_design_code,
			NULL                                                            AS template_bom,
			it.stylebio                                                    AS stylebio,
			it.tag_no                                                      AS tag_no,
			it.tag_no                                                      AS master_serial_gold,
			it.master_bom                                                  AS master_fg_bom_gold,
			NULL                                                            AS master_serial_silver,
			NULL                                                            AS master_fg_bom_silver,
			bom.metal_to_diamond_ratio_excl_of_finding                     AS gc_ratio,
			NULL                                                            AS gc_remark,
			NULL                                                            AS template_deactive_count,
			(
				SELECT GROUP_CONCAT(cst.reason SEPARATOR '; ')
				FROM `tabSimilar Item Table` cst
				WHERE cst.parent = it.name
			)                                                               AS similar_remarks,
			(
				SELECT GROUP_CONCAT(cst.item_code SEPARATOR '; ')
				FROM `tabSimilar Item Table` cst
				WHERE cst.parent = it.name
			)                                                               AS similar_design_code,
			it.sketch_image                                                AS sketch_image,
			it.front_view                                                  AS cad_front_image,
			it.custom_catalogue_image                                      AS product_image,
			(
				(it.sketch_image        IS NOT NULL) + (it.front_view          IS NOT NULL) +
				(it.back_view            IS NOT NULL) + (it.left_view           IS NOT NULL) +
				(it.right_view           IS NOT NULL) + (it.top_view            IS NOT NULL) +
				(it.bottom_view          IS NOT NULL) + (it.rendered_image_1    IS NOT NULL) +
				(it.rendered_image_2     IS NOT NULL) + (it.rendered_image_3    IS NOT NULL) +
				(it.rendered_image_4     IS NOT NULL) + (it.rendered_image_5    IS NOT NULL)
			)                                                               AS additional_images_count,
			ord.order_date                                                 AS erp_creation_date,
			ord.customer_code                                              AS customer_name,
			(
				SELECT GROUP_CONCAT(da.designer_name SEPARATOR '; ')
				FROM `tabDesigner Assignment` da
				WHERE da.parent = sko.name
				  AND da.parenttype = 'Sketch Order'
			)                                                               AS designer_name

		FROM `tabItem` it
		LEFT JOIN `tabBOM` bom          ON bom.name = it.default_bom
		LEFT JOIN `tabOrder` ord        ON ord.name = it.custom_cad_order_id
		LEFT JOIN `tabSketch Order` sko ON sko.name = it.custom_sketch_order_id
		WHERE 1=1 {conditions}
		ORDER BY it.creation DESC
	""".format(conditions=conditions)

	return frappe.db.sql(query, filters, as_dict=1)