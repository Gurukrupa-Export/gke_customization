import frappe
from frappe import _
from datetime import datetime, timedelta
import urllib.parse

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    
    totals_row = calculate_totals(data)
    data.append(totals_row)

    return columns, data

def get_columns(filters=None):
    columns = [
        #Order form
        # {"fieldname": "order_form_id", "label": "Order Form", "fieldtype": "Data", "width": 130},
        {"fieldname": "company", "label": "Company", "fieldtype": "Data", "width": 180},
        {"fieldname": "branch", "label": "Branch", "fieldtype": "Link","options":"Branch", "width": 160},
        {"fieldname": "department", "label": "Department", "fieldtype": "Link","options":"Department", "width": 200},
        {"fieldname": "salesman_name", "label": "Sales Person", "fieldtype": "Data", "width": 170},
        {"fieldname": "customer_code", "label": "Customer", "fieldtype": "Link","options":"Customer", "width": 120},
        {"fieldname": "po_no", "label": "Customer PO No", "fieldtype": "Data", "width": 150},
        {"fieldname": "flow_type", "label": "Flow Type", "fieldtype": "Data", "width": 120},
        {"fieldname": "order_date", "label": "Order Date", "fieldtype": "Date", "width": 120},
        {"fieldname": "delivery_date", "label": "Delivery Date", "fieldtype": "Date", "width": 120},
        {"fieldname": "territory", "label": "Shipping Territory", "fieldtype": "Data", "width": 150},
        {"fieldname": "diamond_quality", "label": "Customer Dia. Quality", "fieldtype": "Data", "width": 170},

        # Order Details
        {"fieldname": "design_by", "label": "Design By", "fieldtype": "Data", "width": 120},
        {"fieldname": "design_type", "label": "Design Type", "fieldtype": "Data", "width": 140},
        # {"fieldname": "design_delivery_date", "label": "Delivery Date", "fieldtype": "Date", "width": 120},
        {"fieldname": "design_code_detail", "label": "Design Code", "fieldtype": "Data", "width": 220},
        {"fieldname": "category", "label": "Item Category", "fieldtype": "Data", "width": 120},
        {"fieldname": "subcategory", "label": "Item Subcategory", "fieldtype": "Data", "width": 140},
        {"fieldname": "setting_type", "label": "Setting Type", "fieldtype": "Data", "width": 120},
        {"fieldname": "sub_setting_type1", "label": "Sub Setting Type1", "fieldtype": "Data", "width": 150},
        {"fieldname": "total_pcs", "label": "No. of Pcs", "fieldtype": "Data", "width": 120},
        {"fieldname": "metal_touch", "label": "Metal Touch", "fieldtype": "Data", "width": 120},
        {"fieldname": "metal_colour", "label": "Metal Colour", "fieldtype": "Data", "width": 120},
        {"fieldname": "metal_target", "label": "Metal Target", "fieldtype": "Data", "width": 120},
        {"fieldname": "diamond_target", "label": "Diamond Target", "fieldtype": "Data", "width": 120},
        {"fieldname": "product_size", "label": "Product Size", "fieldtype": "Data", "width": 120},
        # {"fieldname": "order_form_id", "label": "Order Form", "fieldtype": "Data", "width": 130},
        {"fieldname": "order_form_workflow", "label": "Workflow Status", "fieldtype": "Data", "width": 150},

        # Order
        # {"fieldname": "order_id", "label": "Order", "fieldtype": "Data", "width": 220},
        {"fieldname": "bom_or_cad", "label": "BOM or CAD", "fieldtype": "Data", "width": 120},
        {"fieldname": "order_form_design_id", "label": "Order Form Design ID", "fieldtype": "Link","options":"Item", "width": 180},
        # {"fieldname": "designer_due_date", "label": "Order Design Due Date", "fieldtype": "Date", "width": 150},
        {"fieldname": "order_design_id", "label": "Order Design ID", "fieldtype": "Link","options":"Item", "width": 200},
        {"fieldname": "order_bom", "label": "Order BOM", "fieldtype": "Link","options":"BOM", "width": 220},

        # Item
        # {"fieldname": "item_id", "label": "Item", "fieldtype": "Link", "options": "Item", "width": 220},
        {"fieldname": "designer_name", "label": "Designer Name", "fieldtype": "Data", "width": 150},
        {"fieldname": "order_workflow", "label": "Workflow Status", "fieldtype": "Data", "width": 150},

        {"fieldname": "item_order_form_id", "label": "Item Order Form ID", "fieldtype": "Data", "width": 150},
        {"fieldname": "item_order_id", "label": "Item Order ID", "fieldtype": "Data", "width": 150},
        # {"fieldname": "total_gold_wt", "label": "Item Gold Wt", "fieldtype": "Data", "width": 120},
        # {"fieldname": "total_dia_wt", "label": "Item Dia. Wt", "fieldtype": "Data", "width": 120},
        {"fieldname": "design_category", "label": "Design Category", "fieldtype": "Data", "width": 120},
        {"fieldname": "design_subcategory", "label": "Design Subcategory", "fieldtype": "Data", "width": 150},
        {"fieldname": "design_setting_type", "label": "Design Setting Type", "fieldtype": "Data", "width": 120},

        # BOM
        # {"fieldname": "bom_id", "label": "BOM", "fieldtype": "Link", "options": "BOM", "width": 220},
        {"fieldname": "bom_type", "label": "BOM Type", "fieldtype": "Data", "width": 120},
        {"fieldname": "bom_order_id", "label": "BOM Order ID", "fieldtype": "Link","options":"Order", "width": 180},
        {"fieldname": "bom_category", "label": "BOM Category", "fieldtype": "Data", "width": 140},
        {"fieldname": "bom_subcategory", "label": "BOM Subcategory", "fieldtype": "Data", "width": 150},
        # {"fieldname": "bom_metal_target", "label": "BOM Metal Target", "fieldtype": "Data", "width": 150},
        # {"fieldname": "bom_dia_target", "label": "BOM Dia. Target", "fieldtype": "Data", "width": 150},
        # {"fieldname": "bom_gemstone_type", "label": "BOM Gemstone Type", "fieldtype": "Data", "width": 150},
        
        #BOM Metal Detail
        {"fieldname": "bom_metal_type", "label": "BOM Metal Type", "fieldtype": "Data", "width": 150},
        {"fieldname": "bom_metal_touch", "label": "BOM Metal Touch", "fieldtype": "Data", "width": 150},
        {"fieldname": "bom_metal_purity", "label": "BOM Metal Purity", "fieldtype": "Data", "width": 150},
        {"fieldname": "bom_metal_colour", "label": "BOM Metal Colour", "fieldtype": "Data", "width": 150},
        
        #BOM Finding Details
        {"fieldname": "finding_metal_type", "label": "Finding Metal Type", "fieldtype": "Data", "width": 150},
        {"fieldname": "finding_category", "label": "Finding Category", "fieldtype": "Data", "width": 150},
        {"fieldname": "finding_size", "label": "Finding Size", "fieldtype": "Data", "width": 150},
        {"fieldname": "finding_metal_purity", "label": "Finding Metal Purity", "fieldtype": "Data", "width": 150},
        
        #BOM Diamond Detail
        {"fieldname": "bom_dia_type", "label": "Bom Dia. Type", "fieldtype": "Data", "width": 150},
        {"fieldname": "diamond_shape", "label": "Diamond Shape", "fieldtype": "Data", "width": 150},
        {"fieldname": "diamond_setting", "label": "Diamond Setting", "fieldtype": "Data", "width": 150},
        {"fieldname": "diamond_pcs", "label": "Diamond Pcs", "fieldtype": "Data", "width": 150},
        
        #BOM Gemstone Detail
        {"fieldname": "bom_gemstone_type", "label": "Gemstone Type", "fieldtype": "Data", "width": 150},
        {"fieldname": "gemstone_cut_and_cub", "label": "Gemstone Cut and Cub", "fieldtype": "Data", "width": 150},
        {"fieldname": "gemstone_shape", "label": "Gemstone Shape", "fieldtype": "Data", "width": 150},
        {"fieldname": "gemstone_size", "label": "Gemstone Size", "fieldtype": "Data", "width": 150},
        {"fieldname": "gemstone_pcs", "label": "Gemstone Pcs", "fieldtype": "Data", "width": 150},
        {"fieldname": "gemstone_setting_type", "label": "Gemstone Setting Type", "fieldtype": "Data", "width": 150},
        {"fieldname": "gemstone_quality", "label": "Gemstone Quality", "fieldtype": "Data", "width": 150},
        
        #BOM Other Detail
        # {"fieldname": "other_item_name", "label": "Other Item name", "fieldtype": "Data", "width": 150},
        # {"fieldname": "other_qty", "label": "Other Qty", "fieldtype": "Data", "width": 150},
        # {"fieldname": "other_uom", "label": "Other UOM", "fieldtype": "Data", "width": 150},
        # {"fieldname": "other_wt_in_gms", "label": "Other Wt.", "fieldtype": "Data", "width": 150},

        # Order Form
        #{"fieldname": "order_form_id", "label": "Order Form", "fieldtype": "Link", "options": "Order Form", "width": 150},
        #{"fieldname": "company", "label": "Company", "fieldtype": "Data", "width": 120},
        #{"fieldname": "branch", "label": "Branch", "fieldtype": "Data", "width": 120},
        #{"fieldname": "department", "label": "Department", "fieldtype": "Data", "width": 120},
        #{"fieldname": "salesman_name", "label": "Sales Person", "fieldtype": "Data", "width": 120},
        #{"fieldname": "customer_code", "label": "Customer", "fieldtype": "Data", "width": 120},
        #{"fieldname": "customer_name", "label": "Customer Name", "fieldtype": "Data", "width": 120},


        # Quotation
        # {"fieldname": "quotation_id", "label": "Quotation", "fieldtype": "Link", "options": "Quotation", "width": 230},
        {"fieldname": "quotation_customer_code", "label": "Quotation Customer Code", "fieldtype": "Link","options":"Customer", "width": 150},
        # {"fieldname": "quotation_customer_name", "label": "Quotation Customer Name", "fieldtype": "Data", "width": 150},
        {"fieldname": "quotation_date", "label": "Quotation Date", "fieldtype": "Date", "width": 150},
        # {"fieldname": "valid_till", "label": "Valid Till", "fieldtype": "Date", "width": 150},
        {"fieldname": "quotation_order_type", "label": "Order Type", "fieldtype": "Data", "width": 150},
        {"fieldname": "quotation_branch", "label": "Branch", "fieldtype": "Data", "width": 150},
        {"fieldname": "quotation_diamond_quality", "label": "Diamond Quality", "fieldtype": "Data", "width": 150},
        {"fieldname": "custom_customer_finding", "label": "Customer Finding", "fieldtype": "Data", "width": 200},
        {"fieldname": "custom_customer_gold", "label": "Customer Gold", "fieldtype": "Data","align":"right", "width": 140},
        {"fieldname": "custom_customer_diamond", "label": "Customer Diamond", "fieldtype": "Data","align":"right", "width": 160},
        {"fieldname": "custom_customer_stone", "label": "Customer Stone", "fieldtype": "Data", "align":"right","width": 160},
        
        # Quotation Item
        {"fieldname": "quotation_item_code", "label": "Quotation Item Code", "fieldtype": "Link","options":"Item", "width": 220},
        {"fieldname": "quotation_child_diamond", "label": "Quotation Dia. quality", "fieldtype": "Data", "width": 150},
        {"fieldname": "quotation_bom", "label": "Quotation BOM", "fieldtype": "Link","options":"BOM", "width": 220},
        {"fieldname": "origin_bom", "label": "Origin BOM", "fieldtype": "Link","options":"BOM", "width": 220},
        {"fieldname": "quotation_metal_colour", "label": "Quotation Metal Colour", "fieldtype": "Data", "width": 150},
        {"fieldname": "quotation_metal_touch", "label": "Quotation Metal Touch", "fieldtype": "Data", "width": 150},
        {"fieldname": "quotation_item_category", "label": "Quotation Item Category", "fieldtype": "Data", "width": 150},
        {"fieldname": "quotation_item_subcategory", "label": "Quotation Item Subcategory", "fieldtype": "Data", "width": 150},
        {"fieldname": "quotation_setting_type", "label": "Quotation Setting Type", "fieldtype": "Data", "width": 150},
        {"fieldname": "quotation_stylebio", "label": "Old Stylebio", "fieldtype": "Data", "width": 150},
        # {"fieldname": "quotation_manufacturing_type", "label": "Manufacturing Type", "fieldtype": "Data", "width": 150},
        {"fieldname": "quotation_order_form_id", "label": "Order Form ID", "fieldtype": "Link","options":"Order", "width": 150},
        # {"fieldname": "quotation_order_placed_date", "label": "Order Placed Date", "fieldtype": "Date", "width": 150},
        # {"fieldname": "quotation_delivery_date", "label": "Quotation Delivery Date", "fieldtype": "Date", "width": 150},
        {"fieldname": "quotation_customer_po", "label": "Customer PO", "fieldtype": "Data", "width": 150},
        {"fieldname": "quotation_qty", "label": "Quotation Qty", "fieldtype": "Data", "width": 120},
        
        # Sales Order
        # {"fieldname": "sales_order_id", "label": "Sales Order", "fieldtype": "Link", "options": "Sales Order", "width": 230},
        {"fieldname": "so_customer_code", "label": "SO Customer Code", "fieldtype": "Link","options":"Customer", "width": 150},
        {"fieldname": "sales_order_type", "label": "Sales Order Type", "fieldtype": "Data", "width": 150},
        {"fieldname": "sale_type", "label": "Sale Type", "fieldtype": "Data", "width": 150},
        {"fieldname": "sale_order_date", "label": "Sale Order Date", "fieldtype": "Date", "width": 150},
        {"fieldname": "so_delivery_date", "label": "SO Delivery Date", "fieldtype": "Date", "width": 150},
        {"fieldname": "so_jewelex_order_no", "label": "Jewelex Order No", "fieldtype": "Data", "width": 150},
        
        # Sales Order Item
        {"fieldname": "so_item_name", "label": "SO Item Name", "fieldtype": "Data", "width": 220},
        {"fieldname": "so_quotation_bom", "label": "SO Quotation BOM", "fieldtype": "Link","options":"BOM", "width": 230},
        {"fieldname": "so_origin_bom", "label": "SO Origin BOM", "fieldtype": "Link","options":"BOM", "width": 230},
        {"fieldname": "so_category", "label": "SO Item Category", "fieldtype": "Data", "width": 150},
        {"fieldname": "so_setting_type", "label": "SO Setting Type", "fieldtype": "Data", "width": 150},
        {"fieldname": "so_diamond_quality", "label": "SO Diamond Quality", "fieldtype": "Data", "width": 150},
        {"fieldname": "so_metal_touch", "label": "SO Metal Touch", "fieldtype": "Data", "width": 150},
        {"fieldname": "so_metal_colour", "label": "SO Metal Colour", "fieldtype": "Data", "width": 150},
        {"fieldname": "so_order_form_id", "label": "Order Form ID", "fieldtype": "Link","options":"Order", "width": 150},
        {"fieldname": "so_order_date", "label": "Order Form Date", "fieldtype": "Date", "width": 150},
        {"fieldname": "so_customer_po", "label": "Customer PO no", "fieldtype": "Data", "width": 150},
        {"fieldname": "so_quotation", "label": "Quotation", "fieldtype": "Link","options":"Quotation", "width": 230},

    ]
    return columns

def get_data(filters):
    conditions = get_conditions(filters)
    
    query = f"""
    SELECT 
    of.name AS order_form_id,
    of.company AS company,
    of.branch,
    of.department,
    of.salesman_name,
    of.customer_code,
    of.po_no,
    of.order_type,
    of.flow_type,
    of.order_date,
    of.delivery_date,
    of.due_days,
    t.territory,
    of.diamond_quality,
    of.workflow_state AS order_form_workflow,
    
    od.design_by,
    od.design_type,
    od.delivery_date AS design_delivery_date,
    od.design_id AS design_code_detail,
    od.category,
    od.subcategory,
    od.setting_type,
    od.sub_setting_type1,
    SUM(od.qty) AS total_pcs,
    od.metal_touch,
    od.metal_colour,
    od.metal_target,
    od.diamond_target,
    od.product_size,
    da.designer_name AS designer_name,
    o.workflow_state AS order_workflow,
    o.name AS order_id,
    o.bom_or_cad,
    o.design_id AS order_form_design_id,
    o.est_delivery_date AS designer_due_date,
    o.item AS order_design_id,
    o.bom AS order_bom,

    i.name AS item_id,
    i.order_form_id AS item_order_form_id,
    i.custom_cad_order_id AS item_order_id,
    SUM(i.approx_gold) AS total_gold_wt,
    SUM(i.approx_diamond) AS total_dia_wt,
    i.item_category AS design_category,
    i.item_subcategory AS design_subcategory,
    i.setting_type AS design_setting_type,

    b.name AS bom_id,
    b.bom_type,
    b.custom_order_id AS bom_order_id,
    b.item_category AS bom_category,
    b.item_subcategory AS bom_subcategory,
    b.metal_target AS bom_metal_target,
    b.diamond_target AS bom_dia_target,
    b.gemstone_type1 AS bom_gemstone_type,

    bmd.metal_type AS bom_metal_type,
	bmd.metal_touch AS bom_metal_touch,
	bmd.metal_purity AS bom_metal_purity,
	bmd.metal_colour AS bom_metal_colour,
	
	bfd.metal_type AS finding_metal_type,
	bfd.finding_category AS finding_category,
	bfd.finding_size AS finding_size,
	bfd.metal_purity AS finding_metal_purity,
	
	bdd.diamond_type AS bom_dia_type,
	bdd.stone_shape AS diamond_shape,
	bdd.sub_setting_type AS diamond_setting,
	bdd.pcs AS diamond_pcs,
	
	bgd.gemstone_type AS bom_gemstone_type,
	bgd.cut_or_cab AS gemstone_cut_and_cub,
	bgd.stone_shape AS gemstone_shape,
	bgd.gemstone_size AS gemstone_size,
	bgd.pcs AS gemstone_pcs,
	bgd.sub_setting_type AS gemstone_setting_type,
	bgd.gemstone_quality AS gemstone_quality,
	
	bod.item_code AS other_item_name,
	bod.qty AS other_qty,
	bod.uom AS other_uom,
	bod.quantity AS other_wt_in_gms,

    q.name AS quotation_id,
    q.party_name AS quotation_customer_code,
    q.customer_name AS quotation_customer_name,
    q.transaction_date AS quotation_date,
    q.valid_till,
    q.order_type AS quotation_order_type,
    q.branch AS quotation_branch,
    q.diamond_quality AS quotation_diamond_quality,
    CASE WHEN q.custom_customer_gold IS NULL OR q.custom_customer_gold = '' THEN 'No'ELSE q.custom_customer_gold END AS custom_customer_gold,
    CASE WHEN q.custom_customer_diamond IS NULL OR q.custom_customer_diamond = '' THEN 'No'ELSE q.custom_customer_diamond END AS custom_customer_diamond,
    CASE WHEN q.custom_customer_stone IS NULL OR q.custom_customer_stone = '' THEN 'No'ELSE q.custom_customer_stone END AS custom_customer_stone,
    CASE WHEN q.custom_customer_finding IS NULL OR q.custom_customer_finding = '' THEN 'No'ELSE q.custom_customer_finding END AS custom_customer_finding,
     
	qi.item_code AS quotation_item_code,
	qi.diamond_quality AS quotation_child_diamond,
	qi.quotation_bom AS quotation_bom,
	qi.copy_bom AS origin_bom,
	qi.metal_colour AS quotation_metal_colour,
	qi.metal_touch AS quotation_metal_touch,
	qi.item_category AS quotation_item_category,
	qi.item_subcategory AS quotation_item_subcategory,
	qi.setting_type AS quotation_setting_type,
	qi.old_stylebio AS quotation_stylebio,
	qi.manufacturing_type AS quotation_manufacturing_type,
	qi.order_form_id AS quotation_order_form_id,
	qi.order_form_date AS quotation_order_placed_date,
	qi.delivery_date AS quotation_delivery_date,
	qi.po_no AS quotation_customer_po,
	qi.qty AS quotation_qty,

    so.name AS sales_order_id,
    so.customer AS so_customer_code,
    so.order_type AS sales_order_type,
    so.sales_type AS sale_type,
    so.transaction_date AS sale_order_date,
    so.delivery_date AS so_delivery_date,
	so.custom_jewelex_order_no AS so_jewelex_order_no,
	soi.item_name AS so_item_name,
	soi.quotation_bom AS so_quotation_bom,
	soi.copy_bom AS so_origin_bom,
	soi.item_category AS so_category,
	soi.setting_type AS so_setting_type,
	soi.diamond_quality AS so_diamond_quality,
	soi.metal_touch AS so_metal_touch,
	soi.metal_colour AS so_metal_colour,
	soi.order_form_id AS so_order_form_id,
	soi.order_form_date AS so_order_date,
	soi.po_no AS so_customer_po,
	soi.prevdoc_docname AS so_quotation

FROM `tabOrder Form` of
LEFT JOIN `tabOrder Form Detail` od ON of.name = od.parent
LEFT JOIN `tabOrder` o ON of.name = o.cad_order_form and od.design_id = o.design_id
LEFT JOIN `tabDesigner Assignment` da ON o.name = da.parent
LEFT JOIN `tabItem` i ON of.name = i.order_form_id
LEFT JOIN `tabBOM` b ON o.new_bom = b.name
LEFT JOIN `tabBOM Metal Detail` bmd ON b.name = bmd.parent
LEFT JOIN `tabBOM Finding Detail` bfd ON b.name = bfd.parent
LEFT JOIN `tabBOM Diamond Detail` bdd ON b.name = bdd.parent
LEFT JOIN `tabBOM Gemstone Detail` bgd ON b.name = bgd.parent
LEFT JOIN `tabBOM Other Detail` bod ON b.name = bod.parent
LEFT JOIN `tabQuotation Item` qi ON o.name = qi.order_form_id
LEFT JOIN `tabTerritory Multi Select` t ON t.parent = o.name
LEFT JOIN `tabQuotation` q ON qi.parent = q.name
LEFT JOIN `tabSales Order Item` soi on o.name = soi.order_form_id
LEFT JOIN `tabSales Order` so ON soi.parent = so.name
{conditions}
GROUP by of.name, o.name, i.name, b.name, q.name, so.name   
    """

    data = frappe.db.sql(query, as_dict=1)
    
    for row in data:
        encoded_order_form = urllib.parse.quote(row["order_form_id"])
        encoded_mp_id = urllib.parse.quote(row["design_code_detail"])
        encoded_order_id = urllib.parse.quote(row["order_id"])
        encoded_company = urllib.parse.quote(row["company"])
        row["order_form_id"] = f'<a href="https://gkexport.frappe.cloud/app/order-form/{encoded_order_form}" target="_blank">{row["order_form_id"]}</a>'
        row["design_code_detail"] = f'<a href="https://gkexport.frappe.cloud/app/item/{encoded_mp_id}" target="_blank">{row["design_code_detail"]}</a>'
        row["order_id"] = f'<a href="https://gkexport.frappe.cloud/app/order/{encoded_order_id}" target="_blank">{row["order_id"]}</a>'
        row["company"] = f'<a href="https://gkexport.frappe.cloud/app/company/{encoded_company}" target="_blank">{row["company"]}</a>'
        

    return data


def calculate_totals(data):
    total_no_pcs = 0
    total_gold_wt = 0
    total_dia_wt = 0
    total_gemstone_pcs = 0
    total_other_qty = 0
    total_other_wt = 0
    unique_design_id = set()
    unique_order_id = set()

    for row in data:
        total_no_pcs += int(row.get("total_pcs") or 0)
        total_gold_wt += float(row.get("total_gold_wt") or 0)
        total_dia_wt += float(row.get("total_dia_wt") or 0)
        total_gemstone_pcs += int(row.get("gemstone_pcs") or 0)
        total_other_qty += int(row.get("other_qty") or 0)
        total_other_wt += float(row.get("other_wt_in_gms") or 0)
        unique_design_id.add(row.get("design_code_detail"))
        unique_order_id.add(row.get("order_id"))

    totals_row = {
        "order_form_id": "",
        "company": f'<b><span style="color:rgb(23,175,23); font-size: 15px; font-weight: bold;">Total</span></b>',
        "branch": "",
        "department": "",
        "salesman_name": "",
        "customer_code": "",
        "po_no": "",
        "flow_type": "",
        "order_date": "",
        "delivery_date": "",
        "territory": "",
        "diamond_quality": "",
        "design_by": "",
        "design_type": "",
        "design_delivery_date": "",
        "design_code_detail": f'<b><span style="color:rgb(23,175,23); font-size: 15px; font-weight: bold;">Design Code count:{len(unique_design_id)}</span></b>',
        "category": "",
        "subcategory": "",
        "setting_type": "",
        "sub_setting_type1": "",
        "total_pcs": f'<b><span style="color:rgb(23,175,23); font-size: 15px; font-weight: bold;">{total_no_pcs}</span></b>',
        "metal_touch": "",
        "metal_colour": "",
        "metal_target": "",
        "diamond_target": "",
        "product_size": "",
        "workflow_state": "",
        "order_id": f'<b><span style="color:rgb(23,175,23); font-size: 15px; font-weight: bold;">Count of Orders:{len(unique_order_id)}</span></b>',
        "bom_or_cad": "",
        "order_form_design_id": "",
        "designer_due_date": "",
        "order_design_id": "",
        "order_bom": "",
        "item_id": "",
        "item_order_form_id": "",
        "item_order_id": "",
        "total_gold_wt":f'<b><span style="color:rgb(23,175,23); font-size: 15px; font-weight: bold;">{total_gold_wt:.4f}</span></b>',
        "total_dia_wt": f'<b><span style="color:rgb(23,175,23); font-size: 15px; font-weight: bold;">{total_dia_wt:.4f}</span></b>',
        "design_category": "",
        "design_subcategory": "",
        "design_setting_type": "",
        "bom_id": "",
        "bom_type": "",
        "bom_order_id": "",
        "bom_category": "",
        "bom_subcategory": "",
        "bom_metal_target": "",
        "bom_dia_target": "",
        "bom_gemstone_type": "",
        "bom_metal_type": "",
        "bom_metal_touch": "",
        "bom_metal_purity": "",
        "bom_metal_colour": "",
        "finding_metal_type": "",
        "finding_category": "",
        "finding_size": "",
        "finding_metal_purity": "",
        "bom_dia_type": "",
        "diamond_shape": "",
        "diamond_setting": "",
        "diamond_pcs": "",
        "bom_gemstone_type": "",
        "gemstone_cut_and_cub": "",
        "gemstone_shape": "",
        "gemstone_size": "",
        "gemstone_pcs": f'<b><span style="color:rgb(23,175,23); font-size: 15px; font-weight: bold;">{total_gemstone_pcs}</span></b>',
        "gemstone_setting_type": "",
        "gemstone_quality": "",
        "other_item_name": "",
        "other_qty": f'<b><span style="color:rgb(23,175,23); font-size: 15px; font-weight: bold;">{total_other_qty}</span></b>',
        "other_uom": "",
        "other_wt_in_gms": f'<b><span style="color:rgb(23,175,23); font-size: 15px; font-weight: bold;">{total_other_wt:.3f}</span></b>',
        "quotation_id": "",
        "quotation_customer_code": "",
        "quotation_customer_name": "",
        "quotation_date": "",
        "valid_till": "",
        "quotation_order_type": "",
        "quotation_branch": "",
        "quotation_diamond_quality": "",
        "quotation_item_code": "",
        "quotation_child_diamond": "",
        "quotation_bom": "",
        "origin_bom": "",
        "quotation_metal_colour": "",
        "quotation_metal_touch": "",
        "quotation_item_category": "",
        "quotation_item_subcategory": "",
        "quotation_setting_type": "",
        "quotation_stylebio": "",
        "quotation_manufacturing_type": "",
        "quotation_order_form_id": "",
        "quotation_order_placed_date": "",
        "quotation_delivery_date": "",
        "quotation_customer_po": "",
        "quotation_qty": "",
        "sales_order_id": "",
        "so_customer_code": "",
        "sales_order_type": "",
        "sale_type": "",
        "sale_order_date": "",
        "so_delivery_date": "",
        "so_jewelex_order_no": "",
        "so_item_name": "",
        "so_quotation_bom": "",
        "so_origin_bom": "",
        "so_category": "",
        "so_setting_type": "",
        "so_diamond_quality": "",
        "so_metal_touch": "",
        "so_metal_colour": "",
        "so_order_form_id": "",
        "so_order_date": "",
        "so_customer_po": "",
        "so_quotation": "",
    }
    
    return totals_row


def get_conditions(filters):
    conditions = []
    if filters.get("order"):
        orders = ', '.join([f'"{order}"' for order in filters.get("order")])
        conditions.append(f"""o.name IN ({orders})""")

    if filters.get("order_f"):
        orders_f = ', '.join([f'"{orderf}"' for orderf in filters.get("order_f")])
        conditions.append(f"""of.name IN ({orders_f})""")
    
    if filters.get("company"):
        companies = ', '.join([f'"{company}"' for company in filters["company"]])
        conditions.append(f"of.company IN ({companies})")
    
    if filters.get("branch"):
        Branches = ', '.join([f'"{branch}"' for branch in filters["branch"]])
        conditions.append(f"of.branch IN ({Branches})")

    if filters.get("customer_code"):
        customer_codes = ', '.join([f'"{customer_code}"' for customer_code in filters["customer_code"]])
        conditions.append(f"of.customer_code IN ({customer_codes})")

    if filters.get("bom"):
        boms = ', '.join([f'"{bom}"' for bom in filters.get("bom")])
        conditions.append(f"""b.name IN ({boms})""")

    if filters.get("quotation"):
        quots = ', '.join([f'"{quot}"' for quot in filters.get("quotation")])
        conditions.append(f"""q.name IN ({quots})""")        

    if filters.get("customer_po"):
        customers_po = ', '.join([f"'{po}'" for po in filters.get("customer_po")])    
        conditions.append(f"so.po_no IN ({customers_po})")

    # if filters.get("qt"):
    #     qts = ', '.join([f'"{qt}"' for qt in filters.get("qt")])
    #     conditions.append(f"""pmo.quotation IN ({qts})""")

    if filters.get("so"):
        sos = ', '.join([f'"{so}"' for so in filters.get("so")])
        conditions.append(f"""so.name IN ({sos})""")

    # if filters.get("pmo"):
    #     pmos = ', '.join([f'"{pmo}"' for pmo in filters.get("pmo")])
    #     conditions.append(f"""mwo.manufacturing_order IN ({pmos})""")                
    return f"WHERE {' AND '.join(conditions)}" if conditions else "WHERE 1=1"
