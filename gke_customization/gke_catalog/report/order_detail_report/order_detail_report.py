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
        {"label": "Manufacturing Work Order ID", "fieldname": "mwo_id", "fieldtype": "Data"},
        {"label": "Is Finding MWO", "fieldname": "mwo_is_finding", "fieldtype": "Data"},
        {"label": "Customer Code", "fieldname": "mwo_customer", "fieldtype": "Link", "options": "Customer"},
        {"label": "Customer Name", "fieldname": "mwo_customer_name", "fieldtype": "Data"},
        {"label": "Customer PO No.", "fieldname": "customer_po", "fieldtype": "Data"},
        {"label": "Manufacturing Plan ID", "fieldname": "mwo_mp_id", "fieldtype": "Data"},
        {"label": "Design ID", "fieldname": "mwo_design_id", "fieldtype": "Data"},
        {"label": "MFG BOM", "fieldname": "mwo_mfg_bom", "fieldtype": "Link", "options": "BOM"},
        {"label": "Item Category", "fieldname": "mwo_item_category", "fieldtype": "Data"},
        {"label": "Item Sub Category", "fieldname": "mwo_item_subcategory", "fieldtype": "Data"},
        {"label": "MWO Qty", "fieldname": "mwo_qty", "fieldtype": "Data"},
        {"label": "Setting Type", "fieldname": "mwo_setting_type", "fieldtype": "Data"},
        {"label": "Manufacturer", "fieldname": "mwo_manufacturer", "fieldtype": "Data"},
        {"label": "Diamond Grade", "fieldname": "mwo_diam_grade", "fieldtype": "Data"},
        {"label": "Metal Type", "fieldname": "mwo_metal_type", "fieldtype": "Data"},
        {"label": "Metal Touch", "fieldname": "mwo_metal_touch", "fieldtype": "Data"},
        {"label": "Metal Color", "fieldname": "mwo_metal_color", "fieldtype": "Data"},
        {"label": "Metal Purity", "fieldname": "mwo_metal_purity", "fieldtype": "Data"},
        {"label": "Gross Wt", "fieldname": "mwo_gross_wt", "fieldtype": "Data"},
        {"label": "Net Wt", "fieldname": "mwo_net_wt", "fieldtype": "Data"},
        # {"label": "Metal Wt", "fieldname": "mwo_metal_wt", "fieldtype": "Float"},
        {"label": "Finding Wt", "fieldname": "mwo_finding_wt", "fieldtype": "Data"},
        {"label": "Diamond Wt (cts)", "fieldname": "mwo_diam_wt", "fieldtype": "Data"},
        {"label": "Gemstone Wt (cts)", "fieldname": "mwo_gem_wt", "fieldtype": "Data"},
        {"label": "Other Wt", "fieldname": "mwo_other_wt", "fieldtype": "Data"},
        {"label": "Diamond Wt (Gram)", "fieldname": "mwo_diam_wt_gm", "fieldtype": "Data"},
        {"label": "Diamond Pcs", "fieldname": "mwo_diam_pcs", "fieldtype": "Data"},
        {"label": "Gemstone Pcs", "fieldname": "mwo_gem_pcs", "fieldtype": "Data"},
        {"label": "Parent Manufacturing Order ID", "fieldname": "parent_mfg_order", "fieldtype": "Link", "options": "Parent Manufacturing Order"},
        {"label": "Order Type", "fieldname": "mwo_order_type", "fieldtype": "Data"},
        {"label": "Delivery Date", "fieldname": "mwo_delivery_date", "fieldtype": "Date"},
        {"label": "Updated Delivery Date", "fieldname": "mwo_updated_delivery_date", "fieldtype": "Date"},
        {"label": "Manufacturing Operation ID", "fieldname": "mop_id", "fieldtype": "Link", "options": "Manufacturing Operation"},
        {"label": "MOP Status", "fieldname": "mop_status", "fieldtype": "Data"},
        {"label": "Operation", "fieldname": "mop_operation", "fieldtype": "Data"},
        {"label": "Status", "fieldname": "mop_status", "fieldtype": "Data"},
        {"label": "Department", "fieldname": "mop_department", "fieldtype": "Data"},
        {"label": "Employee ID", "fieldname": "mop_employee", "fieldtype": "Link", "options": "Employee"},
        {"label": "Employee Name", "fieldname": "mop_emp_name", "fieldtype": "Data"},
        {"label": "Main Slip No", "fieldname": "mop_main_slip", "fieldtype": "Data"},
        {"label": "Diamond Quality", "fieldname": "pmo_diam_quality", "fieldtype": "Data"},
        {"label": "Customer Gold", "fieldname": "pmo_is_cust_gold", "fieldtype": "Data"},
        {"label": "Customer Diamond", "fieldname": "pmo_is_cust_diam", "fieldtype": "Data"},
        {"label": "Customer Gemstone", "fieldname": "pmo_is_cust_gem", "fieldtype": "Data"},
        {"label": "Customer Chain", "fieldname": "pmo_is_cust_material", "fieldtype": "Data"},
        {"label": "Company Name", "fieldname": "pmo_company", "fieldtype": "Data"},
        {"label": "Due Days", "fieldname": "pmo_due_days", "fieldtype": "Data"},
        {"label": "Est. Delivery Date", "fieldname": "pmo_est_delivery_date", "fieldtype": "Date"},
        {"label": "Est. Delivery Days", "fieldname": "pmo_est_delivery_days", "fieldtype": "Data"},
        {"label": "Manufacturing End Date", "fieldname": "manufacturing_end_date", "fieldtype": "Data"},
        {"label": "Order Form ID", "fieldname": "pmo_order_form_id", "fieldtype": "Link", "options": "Order Form"},
        {"label": "Order Form Date", "fieldname": "pmo_order_form_date", "fieldtype": "Date"},
        {"label": "Quotation ID", "fieldname": "pmo_quotation_id", "fieldtype": "Link", "options": "Quotation"},
        {"label": "Sales Order ID", "fieldname": "pmo_sales_order_id", "fieldtype": "Link", "options": "Sales Order"},
        {"label": "Customer PO", "fieldname": "pmo_customer_po", "fieldtype": "Data"},
        {"label": "Jewelex Order No", "fieldname": "pmo_jewelex_order_no", "fieldtype": "Data"},
        {"label": "Parent Quotation ID", "fieldname": "pmo_parent_quotation_id", "fieldtype": "Link", "options": "Quotation"},
        {"label": "Parent Sales Order ID", "fieldname": "pmo_parent_sales_order_id", "fieldtype": "Link", "options": "Sales Order"},
        {"label": "Parent Plan ID", "fieldname": "pmo_parent_plan_id", "fieldtype": "Link", "options": "Manufacturing Plan"},
        {"label": "Ref Customer ID", "fieldname": "pmo_ref_customer_id", "fieldtype": "Link", "options": "Customer"},
        {"label": "Ref Customer Name", "fieldname": "pmo_ref_customer_name", "fieldtype": "Data"},
        {"label": "Quotation Creation Date", "fieldname": "q_creation_date", "fieldtype": "Date"},
        {"label": "Quotation Quantity", "fieldname": "q_total_qty", "fieldtype": "Data"},
        {"label": "Quotation Branch", "fieldname": "q_branch", "fieldtype": "Data"},
        {"label": "Sales Order Creation Date", "fieldname": "so_creation_date", "fieldtype": "Date"},
        {"label": "Sales Order Delivery Date", "fieldname": "so_delivery_date", "fieldtype": "Date"},
        {"label": "Sales Order Quantity", "fieldname": "so_total_qty", "fieldtype": "Data"},
        {"label": "Serial No Creator", "fieldname": "sn_creator_id", "fieldtype": "Link", "options": "Serial Number Creator"},
        {"label": "Serial No", "fieldname": "sn_serial_no", "fieldtype": "Data"},
        {"label": "Serial No Date", "fieldname": "serial_creation", "fieldtype": "Date"},
        {"label": "FG BOM", "fieldname": "sn_fg_bom", "fieldtype": "Link", "options": "BOM"},
    ]
    return columns

def get_data(filters):
    conditions = get_conditions(filters)
    
    query = f"""
    SELECT 
    mwo.name AS mwo_id,
    (CASE WHEN mwo.is_finding_mwo=1 THEN 'Yes' ELSE 'No' END) AS mwo_is_finding,
    mwo.customer AS mwo_customer,
    c.customer_name AS mwo_customer_name,
    pmo.po_no AS customer_po,
    mwo.manufacturing_plan AS mwo_mp_id,
    mwo.item_code AS mwo_design_id,
    mwo.master_bom AS mwo_mfg_bom,
    mwo.item_category AS mwo_item_category,
    mwo.item_sub_category AS mwo_item_subcategory,
    SUM(mwo.qty) AS mwo_qty,
    mwo.setting_type AS mwo_setting_type,
    mwo.manufacturer AS mwo_manufacturer,
    mwo.diamond_grade AS mwo_diam_grade,
    mwo.metal_type AS mwo_metal_type,
    mwo.metal_touch AS mwo_metal_touch,
    mwo.metal_colour AS mwo_metal_color,
    mwo.metal_purity AS mwo_metal_purity,
    SUM(mwo.gross_wt) AS mwo_gross_wt,
    SUM(mwo.metal_weight) AS mwo_metal_wt,
    SUM(mwo.net_wt) AS mwo_net_wt,
    SUM(mwo.finding_wt) AS mwo_finding_wt,
    SUM(mwo.diamond_wt) AS mwo_diam_wt,
    SUM(mwo.gemstone_wt) AS mwo_gem_wt,
    SUM(mwo.other_wt) AS mwo_other_wt,
    SUM(mwo.diamond_wt_in_gram) AS mwo_diam_wt_gm,
    SUM(mwo.diamond_pcs) AS mwo_diam_pcs,
    SUM(mwo.gemstone_pcs) AS mwo_gem_pcs,
    mwo.manufacturing_order AS parent_mfg_order,
    mwo.order_type AS mwo_order_type,
    mwo.delivery_date AS mwo_delivery_date,
    mwo.custom_updated_delivery_date AS mwo_updated_delivery_date,

    mo.name AS mop_id,
    mo.status AS mop_status,
    mo.operation AS mop_operation,
    mo.status AS mop_status,
    mo.department AS mop_department,
    mo.employee AS mop_employee,
    emp.employee_name AS mop_emp_name,
    mo.main_slip_no AS mop_main_slip,

    pmo.diamond_quality AS pmo_diam_quality,
    (CASE WHEN pmo.is_customer_gold=1 THEN 'Yes' ELSE 'No' END) AS pmo_is_cust_gold,
    (CASE WHEN pmo.is_customer_diamond =1 THEN 'Yes' ELSE 'No' END) AS pmo_is_cust_diam,
    (CASE WHEN pmo.is_customer_gemstone =1 THEN 'Yes' ELSE 'No' END) AS pmo_is_cust_gem,
    (CASE WHEN pmo.is_customer_material =1 THEN 'Yes' ELSE 'No' END) AS pmo_is_cust_material,
    pmo.company AS pmo_company,
    pmo.due_days AS pmo_due_days,
    pmo.estimated_delivery_date AS pmo_est_delivery_date,
    pmo.est_delivery_days AS pmo_est_delivery_days,
    pmo.order_form_id AS pmo_order_form_id,
    pmo.order_form_date AS pmo_order_form_date,
    pmo.quotation AS pmo_quotation_id,
    pmo.sales_order AS pmo_sales_order_id,
    pmo.po_no AS pmo_customer_po,
    pmo.jewelex_order_no AS pmo_jewelex_order_no,
    pmo.parent_quotation AS pmo_parent_quotation_id,
    pmo.parent_sales_order AS pmo_parent_sales_order_id,
    pmo.parent_mp AS pmo_parent_plan_id,
    pmo.ref_customer AS pmo_ref_customer_id,
    pmo.manufacturing_end_date AS manufacturing_end_date,
    cust.customer_name AS pmo_ref_customer_name,

    DATE(q.creation) AS q_creation_date,
    q.total_qty AS q_total_qty,
    q.branch AS q_branch,

    DATE(so.creation) AS so_creation_date,
    so.delivery_date AS so_delivery_date,
    so.total_qty AS so_total_qty,

    sn.name AS sn_creator_id,
    DATE(sn.creation) as serial_creation,
    sn.fg_serial_no AS sn_serial_no,
    sn.fg_bom AS sn_fg_bom

    FROM `tabManufacturing Work Order` mwo
    LEFT JOIN `tabCustomer` c ON mwo.customer = c.name
    LEFT JOIN `tabManufacturing Operation` mo ON mwo.manufacturing_operation = mo.name and mo.status != 'Finished'
    LEFT JOIN `tabEmployee` emp ON mo.employee = emp.name
    LEFT JOIN `tabParent Manufacturing Order` pmo ON mwo.manufacturing_order = pmo.name
    LEFT JOIN `tabCustomer` cust ON pmo.ref_customer = cust.name
    LEFT JOIN `tabQuotation` q ON pmo.quotation = q.name
    LEFT JOIN `tabSales Order` so ON pmo.sales_order = so.name
    LEFT JOIN `tabSerial Number Creator` sn ON mo.name = sn.manufacturing_operation
    WHERE mwo.department != 'Serial Number - GEPL' and mwo.department!= 'Serial Number - KGJPL'
    {conditions}
    GROUP BY 
        mwo.manufacturing_order,mwo.delivery_date,
        mwo.name,mwo.item_code ,mo.name,mwo.manufacturing_plan,
        pmo.quotation,
        pmo.sales_order,DATE(q.creation),DATE(so.creation),
        sn.name
    ORDER BY mwo.manufacturing_order desc  
    """

    data = frappe.db.sql(query, as_dict=1)
    
    for row in data:
        encoded_mwo = urllib.parse.quote(row["mwo_id"])
        encoded_mp_id = urllib.parse.quote(row["mwo_mp_id"])
        row["mwo_id"] = f'<a href="https://gkexport.frappe.cloud/app/manufacturing-work-order/{encoded_mwo}" target="_blank">{row["mwo_id"]}</a>'
        row["mwo_mp_id"] = f'<a href="https://gkexport.frappe.cloud/app/manufacturing-plan/{encoded_mp_id}" target="_blank">{row["mwo_mp_id"]}</a>'
        

    return data


def calculate_totals(data):
    total_qty = 0
    total_gross_wt = 0
    total_net_wt = 0
    total_finding_wt = 0
    total_diam_wt_gm = 0
    total_gem_wt = 0
    total_other_wt = 0
    total_diam_pcs = 0
    total_gem_pcs = 0
    # total_design_id = 0
    total_quotation_qty = 0
    total_serial_no = 0
    total_sales_order_qty = 0
    total_diam_wt = 0
    unique_mwo_count= set()
    unique_mp_count = set()
    unique_serial_no_count = set()
    unique_mp_id = set()
    unique_design_id = set()

    for row in data:
        total_qty += int(row.get("mwo_qty") or 0)
        # total_design_id += int(row.get("mwo_design_id") or 0)
        total_gross_wt += float(row.get("mwo_gross_wt") or 0)
        total_net_wt += float(row.get("mwo_net_wt") or 0)
        total_finding_wt += float(row.get("mwo_finding_wt") or 0)
        total_diam_wt_gm += float(row.get("mwo_diam_wt_gm") or 0)
        total_gem_wt += float(row.get("mwo_gem_wt") or 0)
        total_other_wt += float(row.get("mwo_other_wt") or 0)
        total_diam_pcs += int(row.get("mwo_diam_pcs") or 0)
        total_gem_pcs += int(row.get("mwo_gem_pcs") or 0)
        total_quotation_qty += int(row.get("q_total_qty") or 0)
        total_serial_no += int(row.get("sn_serial_no") or 0)
        total_sales_order_qty += int(row.get("so_total_qty") or 0)
        total_diam_wt += float(row.get("mwo_diam_wt") or 0)
        
        unique_mwo_count.add(row.get("mwo_id"))
        unique_mp_count.add(row.get("mwo_mp_id"))
        unique_serial_no_count.add(row.get("sn_serial_no"))
        unique_mp_id.add(row.get("mwo_mp_id"))
        unique_design_id.add(row.get("mwo_design_id"))
    

    totals_row = {
        "mwo_id": f'<b><span style="color:rgb(23,175,23); font-size: 15px; font-weight: bold;">Total MWO: {len(unique_mwo_count)}</span></b>',
        "mwo_is_finding": "",
        "mwo_customer": "",
        "mwo_customer_name": "",
        "mwo_mp_id": f'<b><span style="color:rgb(23,175,23); font-size: 15px; font-weight: bold;">{len(unique_mp_id)} </span></b>',
        "mwo_design_id": f'<b><span style="color:rgb(23,175,23); font-size: 15px; font-weight: bold;">{len(unique_design_id)}</span></b>',
        "mwo_mfg_bom": "",
        "mwo_item_category": "",
        "mwo_item_subcategory": "",
        "mwo_qty": f'<b><span style="color:rgb(23,175,23); font-size: 15px; font-weight: bold;">{total_qty}</span></b>',
        "mwo_setting_type": "",
        "mwo_manufacturer": "",
        "mwo_diam_grade": "",
        "mwo_metal_type": "",
        "mwo_metal_touch": "",
        "mwo_metal_color": "",
        "mwo_metal_purity": "",
        "mwo_gross_wt": f'<b><span style="color:rgb(23,175,23); font-size: 15px; font-weight: bold;">{total_gross_wt:.4f}</span></b>',
        "mwo_net_wt": f'<b><span style="color:rgb(23,175,23); font-size: 15px; font-weight: bold;">{total_net_wt:.4f}</span></b>',
        "mwo_finding_wt": f'<b><span style="color:rgb(23,175,23); font-size: 15px; font-weight: bold;">{total_finding_wt:.2f}</span></b>',
        "mwo_diam_wt": f'<b><span style="color:rgb(23,175,23); font-size: 15px; font-weight: bold;">{total_diam_wt:.4f}</span></b>',
        "mwo_gem_wt": f'<b><span style="color:rgb(23,175,23); font-size: 15px; font-weight: bold;">{total_gem_wt:.4f}</span></b>',
        "mwo_other_wt": f'<b><span style="color:rgb(23,175,23); font-size: 15px; font-weight: bold;">{total_other_wt:.2f}</span></b>',
        "mwo_diam_wt_gm": f'<b><span style="color:rgb(23,175,23); font-size: 15px; font-weight: bold;">{total_diam_wt_gm:.4f}</span></b>',
        "mwo_diam_pcs": f'<b><span style="color:rgb(23,175,23); font-size: 15px; font-weight: bold;">{total_diam_pcs}</span></b>',
        "mwo_gem_pcs": f'<b><span style="color:rgb(23,175,23); font-size: 15px; font-weight: bold;">{total_gem_pcs}</span></b>',
        "parent_mfg_order": "",
        "mwo_order_type": "",
        "mwo_delivery_date": "",
        "mwo_updated_delivery_date": "",
        "mop_id": "",
        "mop_operation": "",
        "mop_status": "",
        "mop_department": "",
        "mop_employee": "",
        "mop_emp_name": "",
        "mop_main_slip": "",
        "pmo_diam_quality": "",
        "pmo_is_cust_gold": "",
        "pmo_is_cust_diam": "",
        "pmo_is_cust_gem": "",
        "pmo_is_cust_material": "",
        "pmo_company": "",
        "pmo_due_days": "",
        "pmo_est_delivery_date": "",
        "pmo_est_delivery_days": "",
        "manufacturing_end_date":"",
        "pmo_order_form_id": "",
        "pmo_order_form_date": "",
        "pmo_quotation_id": "",
        "pmo_sales_order_id": "",
        "pmo_customer_po": "",
        "pmo_jewelex_order_no": "",
        "pmo_parent_quotation_id": "",
        "pmo_parent_sales_order_id": "",
        "pmo_parent_plan_id": "",
        "pmo_ref_customer_id": "",
        "pmo_ref_customer_name": "",
        "q_creation_date": "",
        "q_total_qty": f'<b><span style="color:rgb(23,175,23); font-size: 15px; font-weight: bold;">{total_quotation_qty}</span></b>',
        "q_branch": "",
        "so_creation_date": "",
        "so_delivery_date": "",
        "so_total_qty": f'<b><span style="color:rgb(23,175,23); font-size: 15px; font-weight: bold;">{total_sales_order_qty}</span></b>',
        "sn_creator_id": "",
        "sn_serial_no": f'<b><span style="color:rgb(23,175,23); font-size: 15px; font-weight: bold;">{total_serial_no}</span></b>',
        "serial_creation": "",
        "sn_fg_bom": ""
    }
    
    return totals_row




def get_conditions(filters):
    conditions = []


    if filters.get("company"):
        companies = ', '.join([f'"{company}"' for company in filters["company"]])
        conditions.append(f"mwo.company IN ({companies})")

    if filters.get("branch"):
        branches = ', '.join([f'"{branch}"' for branch in filters["branch"]])
        conditions.append(f"mwo.branch IN ({branches})")

    if filters.get("mp"):
        mps = ', '.join([f'"{mp}"' for mp in filters.get("mp")])
        conditions.append(f"""mwo.name IN ({mps})""")

    # if filters.get("mop"):
    #     mops = ', '.join([f'"{mop}"' for mop in filters.get("mop")])
    #     conditions.append(f"""mwo.manufacturing_operation IN ({mops})""")

    if filters.get("qt"):
        qts = ', '.join([f'"{qt}"' for qt in filters.get("qt")])
        conditions.append(f"""pmo.quotation IN ({qts})""")

    if filters.get("so"):
        sos = ', '.join([f'"{so}"' for so in filters.get("so")])
        conditions.append(f"""pmo.sales_order IN ({sos})""")

    if filters.get("customer_po"):
        customers_po = ', '.join([f"'{po}'" for po in filters.get("customer_po")])    
        conditions.append(f"pmo.po_no IN ({customers_po})") 

    if filters.get("customer"):
        customers_code = ', '.join([f"'{co}'" for co in filters.get("customer")])    
        conditions.append(f"pmo.customer IN ({customers_code})")   

    if filters.get("category"):
        conditions.append(f"pmo.item_category = '{filters['category']}'")

    if filters.get("department"):
        conditions.append(f"mo.department = '{filters['department']}'")

    if filters.get("delivery_date"):
        conditions.append(f"mwo.delivery_date = '{filters['delivery_date']}'")

    # if filters.get("pmo"):
    #     pmos = ', '.join([f'"{pmo}"' for pmo in filters.get("pmo")])
    #     conditions.append(f"""mwo.manufacturing_order IN ({pmos})""")   
    #              
    return " AND "+"AND ".join(conditions) if conditions else ""
