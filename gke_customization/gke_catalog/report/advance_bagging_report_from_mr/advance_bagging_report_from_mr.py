# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

#  mr.name IN ('GE-MR-MF-25-27220', 'GE-MR-MF-25-27091', 'GE-MR-MF-24-00004')
#  http://192.168.200.207:8001/app/query-report/Advance%20Bagging%20Report%20From%20MR?prepared_report_name=28c359a0im

import frappe
import json

def execute(filters=None):
    # Always show department received date column now
    show_department_date = True

    # Base columns (always shown)
    columns = [
        {"label": "Material Req Id", "fieldname": "name", "fieldtype": "Link", "options": "Material Request", "width": 180},
        {"label": "Status", "fieldname": "workflow_state", "fieldtype": "Data","width": 220},
    ]
    
    # Always add Department Received Date column with Datetime
    if show_department_date:
        columns.append({"label": "Reserved / Transfered Date", "fieldname": "department_received_date", "fieldtype": "Datetime", "width": 210})
    
    # Continue with remaining columns
    columns.extend([
        {"label": "Department", "fieldname": "final_department", "fieldtype": "Data", "width": 150, "align": "left"},
        {"label": "Warehouse", "fieldname": "warehouse", "fieldtype": "Data", "width": 180, "align": "left"},
        {"label": "Purpose", "fieldname": "material_request_type", "fieldtype": "Data", "width": 130},
        {"label": "Material Type", "fieldname": "material_type", "fieldtype": "Data", "width": 130},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 210},
        {"label": "Item Attributes", "fieldname": "item_attributes", "fieldtype": "Data", "width": 700},
        {"label": "Alternative Item", "fieldname": "custom_alternative_item", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": "Quantity", "fieldname": "qty", "fieldtype": "Float", "width": 100},
        {"label": "Pcs", "fieldname": "pcs", "fieldtype": "Int", "width": 80},
        {"label": "Customer PO", "fieldname": "custom_customer_po_no", "fieldtype": "Data", "width": 150},
        {"label": "Jewelex Order No", "fieldname": "custom_jewelex_order_no", "fieldtype": "Data", "width": 150},
        {"label": "Order Type", "fieldname": "custom_order_type", "fieldtype": "Data", "width": 120},
        {"label": "Ref Customer", "fieldname": "custom_ref_customer", "fieldtype": "Data", "width": 150},        
        {"label": "Manufacturing Order", "fieldname": "manufacturing_order", "fieldtype": "Link", "options": "Parent Manufacturing Order", "width": 220},
        {"label": "Manufacturer", "fieldname": "custom_manufacturer", "fieldtype": "Data", "width": 150},
        {"label": "Customer Code", "fieldname": "customer", "fieldtype": "Data", "width": 150},
        {"label": "Design Code", "fieldname": "order_item_code", "fieldtype": "Data", "width": 190},
        {"label": "MOP Status", "fieldname": "department", "fieldtype": "Data", "width": 150},
        {"label": "Item Category", "fieldname": "item_category", "fieldtype": "Data", "width": 150},
        {"label": "Item Sub Category", "fieldname": "item_sub_category", "fieldtype": "Data", "width": 150},
        {"label": "Setting Type", "fieldname": "setting_type", "fieldtype": "Data", "width": 150},
    ])

    filters_dict = {
        "material_request_type": "Manufacture",
        "workflow_state": ["!=", "Material Transferred to MOP"]
    }

    if filters.get("from_date") and filters.get("to_date"):
        filters_dict["creation"] = ["between", [filters["from_date"], filters["to_date"]]]
    elif filters.get("from_date"):
        filters_dict["creation"] = [">=", filters["from_date"]]
    elif filters.get("to_date"):
        filters_dict["creation"] = ["<=", filters["to_date"]]

    if filters.get("manufacturing_order") and filters["manufacturing_order"]:
        filters_dict["manufacturing_order"] = ["in", filters["manufacturing_order"]]

    if filters.get("workflow_state") and filters["workflow_state"]:
        filters_dict["workflow_state"] = ["in", filters["workflow_state"]]

    warehouse_name_map = get_warehouse_display_names()
    department_transfer_map = get_department_transfer_map()
    
    # Always get department received dates
    department_received_map = get_department_received_date_map()

    data = []

    material_requests = frappe.get_all("Material Request", 
        fields=[
            "name", "material_request_type", "title", "custom_customer_po_no",
            "custom_jewelex_order_no", "custom_order_type", "manufacturing_order",
            "custom_manufacturer", "custom_ref_customer","docstatus","workflow_state",
            "set_from_warehouse", "set_warehouse", "custom_department"
        ],
        filters=filters_dict,
    )

    if filters.get("warehouse") and filters["warehouse"]:
        filtered_mrs = []
        for mr in material_requests:
            should_include = False
            
            # For Material Reserved - check both old logic and new reservation warehouse
            if mr["workflow_state"] == "Material Reserved":
                # Check original from_warehouse logic
                if mr.get("set_from_warehouse") in filters["warehouse"]:
                    should_include = True
                else:
                    # Check if any items have target reservation warehouse in filter
                    mr_items = frappe.get_all("Material Request Item",
                        fields=["item_code"],
                        filters={"parent": mr.name}
                    )
                    for item in mr_items:
                        target_warehouse = get_reserved_target_warehouse(mr.name, item.item_code)
                        if not target_warehouse:
                            # If no reservation found, try getting RSV warehouse based on material type
                            target_warehouse = get_rsv_warehouse_by_material_type(mr.title)
                        if target_warehouse and target_warehouse in filters["warehouse"]:
                            should_include = True
                            break
            
            # For other statuses - keep existing logic
            elif mr["workflow_state"] == "Reservation Pending" and mr.get("set_from_warehouse") in filters["warehouse"]:
                should_include = True
            elif mr["workflow_state"] in ("Material Transferred", "Submitted", "Material Transferred to Department") and mr.get("set_warehouse") in filters["warehouse"]:
                should_include = True
                
            if should_include:
                filtered_mrs.append(mr)
        
        material_requests = filtered_mrs

    for mr in material_requests:
        material_type = get_material_type_from_title(mr.title)

        if filters.get("material_type") and filters["material_type"] != material_type:
            continue

        mr_items = frappe.get_all("Material Request Item",
            fields=[
                "item_code", 
                "qty", 
                "pcs",
                "custom_alternative_item",
                "warehouse",
                "from_warehouse"
            ],
            filters={"parent": mr.name}
        )

        pmo = frappe.get_value("Parent Manufacturing Order", mr.manufacturing_order,
            ["customer", "item_code", "item_category", "item_sub_category", "setting_type", "department"], as_dict=True
        ) if mr.manufacturing_order else {}

        if filters.get("item_category") and pmo and pmo.get("item_category") not in filters["item_category"]:
            continue

        if filters.get("setting_type") and pmo and pmo.get("setting_type") not in filters["setting_type"]:
            continue

        department = get_department(mr.manufacturing_order)

        for item in mr_items:
            warehouse = ""
            final_department = ""
            warehouse_id = ""
            
            if mr.workflow_state == "Cancelled":
                warehouse = ""
                final_department = ""
            elif mr.workflow_state == "Draft":
                warehouse = ""
                final_department = ""
            elif mr.workflow_state == "Material Reserved":
                # First try to get target warehouse from Stock Entry
                warehouse_id = get_reserved_target_warehouse(mr.name, item.item_code)
                # If not found, determine RSV warehouse based on material type
                if not warehouse_id:
                    warehouse_id = get_rsv_warehouse_by_material_type(mr.title)
                # Fallback to original logic
                if not warehouse_id:
                    warehouse_id = item.from_warehouse or mr.set_from_warehouse or ""
                
                warehouse = warehouse_name_map.get(warehouse_id, warehouse_id) if warehouse_id else ""
                final_department = get_warehouse_department(warehouse_id) if warehouse_id else ""
            elif mr.workflow_state == "Material Transferred":
                warehouse_id = item.warehouse or mr.set_warehouse or ""
                warehouse = warehouse_name_map.get(warehouse_id, warehouse_id) if warehouse_id else ""
                final_department = get_warehouse_department(warehouse_id) if warehouse_id else ""
            elif mr.workflow_state == "Material Transferred to Department":
                warehouse_id = item.warehouse or mr.set_warehouse or ""
                warehouse = warehouse_name_map.get(warehouse_id, warehouse_id) if warehouse_id else ""
                final_department = (department_transfer_map.get(mr.name) or 
                                  mr.custom_department or 
                                  (pmo.get("department") if pmo else ""))
            elif mr.workflow_state == "Reservation Pending":
                warehouse_id = item.from_warehouse or mr.set_from_warehouse or ""
                warehouse = warehouse_name_map.get(warehouse_id, warehouse_id) if warehouse_id else ""
                final_department = get_warehouse_department(warehouse_id) if warehouse_id else ""
            elif mr.workflow_state == "Submitted":
                warehouse_id = item.warehouse or mr.set_warehouse or ""
                warehouse = warehouse_name_map.get(warehouse_id, warehouse_id) if warehouse_id else ""
                final_department = (department_transfer_map.get(mr.name) or 
                                  mr.custom_department or 
                                  (pmo.get("department") if pmo else ""))
            else:
                warehouse = ""
                final_department = ""

            if filters.get("department") and filters["department"]:
                transfer_dept = department_transfer_map.get(mr.name, "")
                if (final_department not in filters["department"] and 
                    (not pmo or pmo.get("department") not in filters["department"]) and
                    transfer_dept not in filters["department"]):
                    continue

            attributes = get_item_attributes(item.item_code)

            row = {
                "name": mr.name,
                "workflow_state": mr.workflow_state,
                "final_department": final_department,
                "warehouse": warehouse,
                "material_request_type": mr.material_request_type,
                "material_type": material_type,
                "item_code": item.item_code,
                "qty": item.qty,
                "custom_alternative_item": item.custom_alternative_item,
                "pcs": item.pcs,
                "custom_customer_po_no": mr.custom_customer_po_no,
                "custom_jewelex_order_no": mr.custom_jewelex_order_no,
                "custom_order_type": mr.custom_order_type,
                "manufacturing_order": mr.manufacturing_order,
                "custom_manufacturer": mr.custom_manufacturer,
                "custom_ref_customer": mr.custom_ref_customer,
                "customer": pmo.get("customer"),
                "order_item_code": pmo.get("item_code"),
                "item_category": pmo.get("item_category"),
                "item_sub_category": pmo.get("item_sub_category"),
                "setting_type": pmo.get("setting_type"),
                "department": department,
                "item_attributes": attributes
            }
            
            # Always add department received date
            if show_department_date:
                row["department_received_date"] = department_received_map.get(mr.name, "")
            
            data.append(row)

    return columns, data

def get_department_received_date_map():
    """Get dates with time for all Material Requests based on their workflow state"""
    try:
        # Get all Material Requests with their workflow states
        mrs = frappe.get_all("Material Request", 
            fields=["name", "workflow_state", "creation", "modified"],
            filters={"material_request_type": "Manufacture"}
        )
        
        department_date_map = {}
        
        for mr in mrs:
            date_to_show = None
            
            if mr.workflow_state == 'Draft':
                # Show creation datetime for Draft
                date_to_show = mr.creation
                
            elif mr.workflow_state == 'Cancelled':
                # Show when it was cancelled (modified datetime)
                date_to_show = mr.modified
                
            elif mr.workflow_state == 'Material Reserved':
                # Show Reserve transfer datetime
                reserve_date = frappe.db.sql("""
                    SELECT MIN(se.posting_date) as date
                    FROM `tabStock Entry` se
                    LEFT JOIN `tabStock Entry Detail` sde ON sde.parent = se.name
                    WHERE sde.material_request = %s
                    AND se.docstatus = 1
                    AND se.purpose = 'Material transfer to Reserve'
                """, mr.name)
                if reserve_date and reserve_date[0][0]:
                    date_to_show = reserve_date[0][0]
                else:
                    date_to_show = mr.modified
                    
            elif mr.workflow_state == 'Material Transferred to Department':
                # Show department transfer datetime
                dept_date = frappe.db.sql("""
                    SELECT MIN(se.posting_date) as date
                    FROM `tabStock Entry` se
                    LEFT JOIN `tabStock Entry Detail` sde ON sde.parent = se.name
                    WHERE sde.material_request = %s
                    AND se.docstatus = 1
                    AND se.purpose = 'Material Transfered to Department'
                """, mr.name)
                if dept_date and dept_date[0][0]:
                    date_to_show = dept_date[0][0]
                else:
                    date_to_show = mr.modified
                    
            elif mr.workflow_state == 'Material Transferred':
                # Show any transfer datetime
                transfer_date = frappe.db.sql("""
                    SELECT MIN(se.posting_date) as date
                    FROM `tabStock Entry` se
                    LEFT JOIN `tabStock Entry Detail` sde ON sde.parent = se.name
                    WHERE sde.material_request = %s
                    AND se.docstatus = 1
                    AND se.stock_entry_type = 'Material Transfer'
                """, mr.name)
                if transfer_date and transfer_date[0][0]:
                    date_to_show = transfer_date[0][0]
                else:
                    date_to_show = mr.modified
                    
            else:
                # For other statuses, show modified datetime
                date_to_show = mr.modified
            
            if date_to_show:
                department_date_map[mr.name] = date_to_show
        
        return department_date_map
    except Exception as e:
        frappe.log_error(f"Error in get_department_received_date_map: {str(e)}")
        return {}

def get_reserved_target_warehouse(mr_name, item_code):
    """Get target warehouse from Stock Entry with type 'Material transfer to Reserve'"""
    try:
        result = frappe.db.sql("""
            SELECT sde.t_warehouse
            FROM `tabStock Entry Detail` sde
            LEFT JOIN `tabStock Entry` se ON se.name = sde.parent
            WHERE 
                sde.material_request = %s
                AND sde.item_code = %s
                AND se.stock_entry_type = 'Material transfer to Reserve'
                AND se.docstatus = 1
            ORDER BY se.creation DESC
            LIMIT 1
        """, (mr_name, item_code), as_dict=True)
        
        if result and result[0].get('t_warehouse'):
            return result[0]['t_warehouse']
        return ""
    except:
        return ""

def get_rsv_warehouse_by_material_type(title):
    """Get RSV warehouse based on material type from MR title"""
    material_type = get_material_type_from_title(title)
    
    # Map material types to their respective RSV warehouses
    rsv_warehouse_map = {
        "Diamond": "Diamond Bagging RSV - GEPL",
        "Gemstone": "Gemstone Bagging RSV - GEPL", 
        "Metal": "Metal Bagging RSV - GEPL",
        "Finding": "Finding Bagging RSV - GEPL"
    }
    
    return rsv_warehouse_map.get(material_type, "")

# **NEW FUNCTION: Get Summary Data for Modal**
@frappe.whitelist()
def get_summary_data(filters=None):
    """Get summary data for the modal display"""
    
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    # Get the same base data as main report
    columns, data = execute(filters)
    
    # Group by item_code for summary
    item_summary = {}
    total_qty = 0
    total_pcs = 0
    
    for row in data:
        item_code = row.get("item_code")
        if not item_code:
            continue
            
        qty = frappe.utils.flt(row.get("qty", 0))
        pcs = frappe.utils.flt(row.get("pcs", 0))
        
        if item_code not in item_summary:
            item_summary[item_code] = {
                "item_code": item_code,
                "sum_of_quantity": 0,
                "count_of_pcs": 0
            }
        
        item_summary[item_code]["sum_of_quantity"] += qty
        item_summary[item_code]["count_of_pcs"] += pcs
        
        total_qty += qty
        total_pcs += pcs
    
    # Convert to list and sort by item_code
    result = list(item_summary.values())
    result.sort(key=lambda x: x["item_code"])
    
    # Add Grand Total row
    result.append({
        "item_code": "Grand Total",
        "sum_of_quantity": total_qty,
        "count_of_pcs": total_pcs
    })
    
    return result

def get_warehouse_display_names():
    warehouses = frappe.get_all("Warehouse", fields=["name", "warehouse_name"])
    return {w.name: w.warehouse_name or w.name for w in warehouses}

def get_department_transfer_map():
    try:
        transfers = frappe.get_all("Material Request Department Transfer",
            fields=["parent", "department"],
            filters={"docstatus": ["!=", 2]}
        )
        transfer_map = {}
        for transfer in transfers:
            transfer_map[transfer.parent] = transfer.department
        return transfer_map
    except:
        return {}

def get_material_type_from_title(title):
    if not title or len(title) < 3:
        return "Unknown"

    code = title[2]  # 3rd character :MRD-SH-(BR00159-001)-2
    return {
        "D": "Diamond",
        "M": "Metal",
        "G": "Gemstone",
        "F": "Finding",
        "O": "Others"
    }.get(code, "Unknown")

def get_item_attributes(item_code):
    attributes = frappe.get_all("Item Variant Attribute",
        filters={"parent": item_code},
        fields=["attribute", "attribute_value"],
        order_by="creation asc"
    )
    return ",  ".join(f"•  {attr.attribute}: {attr.attribute_value}" for attr in attributes) if attributes else ""

def get_department(manufacturing_order):
    if not manufacturing_order:
        return ""

    mwo = frappe.get_all("Manufacturing Work Order",
        filters={
            "manufacturing_order": manufacturing_order,
            "is_finding_mwo": ["!=", 1],
            "for_fg": ["!=", 1]
        },
        pluck="name"
    )
    if not mwo:
        return ""

    mop = frappe.get_all("Manufacturing Operation",
        filters={
            "manufacturing_work_order": ["in", mwo],
            "status": ["!=", "Finished"]
        },
        fields=["department"],
        limit=1
    )
    return mop[0].department if mop else ""

def get_warehouse_department(warehouse_id):
    if not warehouse_id:
        return ""
    
    warehouse_doc = frappe.get_value("Warehouse", warehouse_id, "department", as_dict=False)
    return warehouse_doc or ""
