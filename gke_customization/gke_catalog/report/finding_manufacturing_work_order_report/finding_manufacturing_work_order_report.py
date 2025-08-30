import frappe

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    if data:
        total_row = get_total_row(data)
        data.append(total_row)
    return columns, data

def get_columns():
    return [
        {"label": "Manufacturing Work Order", "fieldname": "manufacturing_work_order", "fieldtype": "Link", "options": "Manufacturing Work Order", "width": 350},
        {"label": "PMO", "fieldname": "pmo_no", "fieldtype": "Data", "width": 120},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": "Finding WT ", "fieldname": "wt_quantity", "fieldtype": "Float", "width": 150},
        {"label": "Customer Code", "fieldname": "customer_id", "fieldtype": "Link", "options": "Customer", "width": 140},
        {"label": "Customer Name", "fieldname": "customer_name", "fieldtype": "Data", "width": 300},
        {"label": "Customer Goods Used", "fieldname": "customer_goods_used", "fieldtype": "Data", "width": 180},
        {"label": "Design Code", "fieldname": "design_code", "fieldtype": "Data", "width": 150},
        {"label": "BOM", "fieldname": "bom_no", "fieldtype": "Link", "options": "BOM", "width": 140},
        {"label": "Department", "fieldname": "department", "fieldtype": "Data", "width": 120},
        {"label": "Department Status", "fieldname": "department_status", "fieldtype": "Data", "width": 160},
        {"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
        {"label": "Quantity", "fieldname": "quantity", "fieldtype": "Float", "width": 100},
    ]

def get_data(filters):
    conditions = ["mwo.is_finding_mwo = 1"]
    values = {}


    if filters:
        if filters.get("company"):
            conditions.append("mwo.company = %(company)s")
            values["company"] = filters["company"]
            
        if filters.get("branch"):
            conditions.append("mwo.branch = %(branch)s")
            values["branch"] = filters["branch"]
            
        if filters.get("from_date"):
            conditions.append("mwo.posting_date >= %(from_date)s")
            values["from_date"] = filters["from_date"]
            
        if filters.get("to_date"):
            conditions.append("mwo.posting_date <= %(to_date)s")
            values["to_date"] = filters["to_date"]
            
        if filters.get("department"):
            conditions.append("mwo.department = %(department)s")
            values["department"] = filters["department"]
            
        if filters.get("work_order_status"):
            if filters["work_order_status"] == "Draft":
                conditions.append("mwo.docstatus = 0")
            elif filters["work_order_status"] == "Submitted":
                conditions.append("mwo.docstatus = 1")
            elif filters["work_order_status"] == "Cancelled":
                conditions.append("mwo.docstatus = 2")
        else:
            conditions.append("mwo.docstatus IN (0, 1)")
            
        if filters.get("goods_type"):
            if filters["goods_type"] == "Yes":
                conditions.append("COALESCE(pmo.is_customer_material, 0) = 1")
            elif filters["goods_type"] == "No":
                conditions.append("COALESCE(pmo.is_customer_material, 0) = 0")
    else:
        conditions.append("mwo.docstatus IN (0, 1)")

    where_condition = " AND ".join(conditions)

    query = f"""
        SELECT
            mwo.name AS manufacturing_work_order,
            mwo.manufacturing_order AS pmo_no,
            CASE 
                WHEN mwo.docstatus = 0 THEN 'Draft'
                WHEN mwo.docstatus = 1 THEN 'Submitted'
                WHEN mwo.docstatus = 2 THEN 'Cancelled'
                ELSE 'Unknown'
            END AS status,
            COALESCE(mwo.finding_wt, 0) AS wt_quantity,
            mwo.customer AS customer_id,
            COALESCE(c.customer_name, '') AS customer_name,
            CASE
                WHEN COALESCE(pmo.is_customer_material, 0) = 1 THEN 'Yes'
                ELSE 'No'
            END AS customer_goods_used,
            COALESCE(mwo.item_code, '') AS design_code,
            COALESCE(mwo.master_bom, '') AS bom_no,
            COALESCE(mwo.department, '') AS department,
            COALESCE((
                SELECT mop2.status
                FROM `tabManufacturing Operation` mop2
                WHERE mop2.manufacturing_work_order = mwo.name
                  AND mop2.department = mwo.department
                ORDER BY mop2.finish_time DESC, mop2.modified DESC
                LIMIT 1
            ), '') AS department_status,
            mwo.posting_date,
            COALESCE(mwo.qty, 0) AS quantity
        FROM `tabManufacturing Work Order` mwo
        LEFT JOIN `tabParent Manufacturing Order` pmo ON pmo.name = mwo.manufacturing_order
        LEFT JOIN `tabCustomer` c ON c.name = mwo.customer
        WHERE {where_condition}
        ORDER BY mwo.posting_date DESC, mwo.name DESC
    """

    data = frappe.db.sql(query, values, as_dict=1)
    return data

def get_total_row(data):
    """Generate total row with count of manufacturing orders and sum of quantities"""
    total_count = len(data)
    
    return {
        "manufacturing_work_order": f"Total Orders = {total_count}",
    }
