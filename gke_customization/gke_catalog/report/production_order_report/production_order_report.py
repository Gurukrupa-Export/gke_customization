import frappe

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": "Order Form", "fieldname": "order_form_id", "fieldtype": "Link", "options": "Order Form", "width": 150},
        {"label": "Order", "fieldname": "order", "fieldtype": "Link", "options": "Order", "width": 150},
        {"label": "Item Code", "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 200},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Data", "width": 200},
        {"label": "Order Date", "fieldname": "order_date", "fieldtype": "Date", "width": 120},
        {"label": "Progress Stage", "fieldname": "progress", "fieldtype": "Data", "width": 180},
        {"label": "Workflow State", "fieldname": "workflow_state", "fieldtype": "Data", "width": 180},
        {"label": "Current Department", "fieldname": "current_department", "fieldtype": "Data", "width": 180},
    ]

def get_data(filters):
    conditions = []
    if filters.get("from_date"):
        conditions.append(f"""o.order_date >= "{filters['from_date']}" """)
    if filters.get("to_date"):
        conditions.append(f"""o.order_date <= "{filters['to_date']}" """)

    if filters.get("order"):
        order_ids = "', '".join(filters["order"])
        conditions.append(f"o.name IN ('{order_ids}')")
    if filters.get("order_form"):
        order_ids = "', '".join(filters["order_form"])
        conditions.append(f"o.cad_order_form IN ('{order_ids}')")    

    if filters.get("company"):
        companies = ', '.join([f'"{company}"' for company in filters.get("company")])
        conditions.append(f"o.company IN ({companies})")
    
    if filters.get("branch"):
        branches = ', '.join([f'"{branch}"' for branch in filters.get("branch")])
        conditions.append(f"o.branch IN ({branches})")
    
    if filters.get("customer"):
        customers = ', '.join([f'"{customer}"' for customer in filters.get("customer")])
        conditions.append(f"o.customer_code IN ({customers})")

    conditions_sql = " AND ".join(conditions) if conditions else "1=1"

    orders = frappe.db.sql(f"""
        SELECT 
            o.name AS order_name, o.cad_order_form AS order_form_id, o.design_id AS item, o.customer_code AS customer, o.order_date AS order_date
        FROM 
            `tabOrder` o
        WHERE 
            o.docstatus < 2 AND {conditions_sql}
        ORDER BY 
            o.order_date DESC
    """, as_dict=True)

    data = []
    for order in orders:
        sales_orders = frappe.db.sql("""
            SELECT 
                so.name AS sales_order, soi.item_code AS item, soi.order_form_id AS order_form
            FROM 
                `tabSales Order` so
            LEFT JOIN
                `tabSales Order Item` soi 
                ON so.name = soi.parent                        
            WHERE 
                soi.order_form_id = %s
        """, (order['order_name'],), as_dict=True)

        stages = []
        for so in sales_orders:
            stage = get_order_progress(order['order_name'], so['sales_order'])
            stages.append(stage)

        stage_order = [
            "Sales Invoice", "PMO-Manufacturing Process",
            "Manufacturing Plan", "Sales Order", "Quotation", "Order", "Order Form"
        ]

        progress = next((stage for stage in stage_order if stage in stages), "Order Form")
        if not sales_orders:
            progress = get_order_progress(order['order_name'], None)

        workflow_state = get_workflow_state(order['order_name'], sales_orders, progress)

        current_department = "-"
        for so in sales_orders:
            department_ir = frappe.db.sql("""
                SELECT di.current_department 
                FROM `tabDepartment IR` di
                JOIN `tabDepartment IR Operation` dio ON di.name = dio.parent
                WHERE dio.parent_manufacturing_order IN (
                    SELECT pmo.name 
                    FROM `tabParent Manufacturing Order` pmo 
                    WHERE pmo.sales_order = %s
                )
                ORDER BY di.modified DESC 
                LIMIT 1
            """, so['sales_order'], as_dict=True)

            if department_ir:
                current_department = department_ir[0]['current_department']
                break

        data.append({
            "order": order['order_name'],
            "order_form_id": order['order_form_id'],
            "item": order['item'],
            "customer": order['customer'],
            "order_date": order['order_date'],
            "progress": progress,
            "workflow_state": workflow_state or "",
            "current_department": current_department
        })

    return data

def get_order_progress(order_id, sale_id):
    if sale_id and frappe.db.exists("Sales Invoice Item", {"sales_order": sale_id}):
        return "Sales Invoice"
    # elif sale_id and frappe.db.exists("Serial No Creator", {"sales_order": sale_id}):
    #     return "Serial No Creator"
    elif frappe.db.exists("Parent Manufacturing Order", {"sales_order": sale_id}):
        return "PMO-Manufacturing Process"
    elif frappe.db.exists("Manufacturing Plan Table", {"sales_order": sale_id}):
        return "Manufacturing Plan"
    elif frappe.db.exists("Sales Order Item", {"order_form_id": order_id}):
        return "Sales Order"
    elif frappe.db.exists("Quotation", {"order_form_id": order_id}):
        return "Quotation"
    elif frappe.db.exists("Order", {"name": order_id}):
        return "Order"
    else:
        return "Order Form"

def get_workflow_state(order_id, sales_orders, progress_stage):
    doctypes_list = [
        {
            "doctype": "Sales Invoice",
            "fieldname": "sales_order",
            "child_table": "Sales Invoice Item",
            "child_field": "sales_order",
            "ids": [so['sales_order'] for so in sales_orders if so.get('sales_order')]
        },
        # {
        #     "doctype": "Serial No Creator",
        #     "fieldname": "sales_order",
        #     "ids": [so['sales_order'] for so in sales_orders if so.get('sales_order')]
        # },
        {
            "doctype": "Parent Manufacturing Order",
            "fieldname": "sales_order",
            "ids": [so['sales_order'] for so in sales_orders if so.get('sales_order')]
        },
        {
            "doctype": "Manufacturing Plan",
            "fieldname": "sales_order",
            "child_table": "Manufacturing Plan Table",
            "child_field": "sales_order",
            "ids": [so['sales_order'] for so in sales_orders if so.get('sales_order')]
        },
        {
            "doctype": "Sales Order",
            "fieldname": "name",
            "ids": [so['sales_order'] for so in sales_orders if so.get('sales_order')]
        },
        {
            "doctype": "Quotation",
            "fieldname": "order_form_id",
            "child_table": "Quotation Item",
            "child_field": "order_form_id",
            "ids": [order_id]
        },
        {
            "doctype": "Order",
            "fieldname": "name",
            "ids": [order_id]
        },
        {
            "doctype": "Order Form",
            "fieldname": "name",
            "ids": [so['order_form'] for so in sales_orders if so.get('order_form')]
        },
    ]

    docstatus_map = {0: 'Draft', 1: 'Submitted', 2: 'Cancelled'}

    for entry in doctypes_list:
        ids = entry['ids']
        if not ids:
            continue

        id_list = "', '".join(ids)
        doctype = entry['doctype']
        fieldname = entry['fieldname']

        has_wf = frappe.db.has_column(doctype, 'workflow_state')

        if entry.get('child_table'):
            child_table = entry['child_table']
            child_field = entry['child_field']
            result = frappe.db.sql(f"""
                SELECT p.{ 'workflow_state' if has_wf else 'docstatus' } 
                FROM `tab{doctype}` p
                JOIN `tab{child_table}` c ON p.name = c.parent
                WHERE c.{child_field} IN ('{id_list}')
                ORDER BY p.modified DESC
                LIMIT 1
            """, as_dict=True)
        else:
            result = frappe.db.sql(f"""
                SELECT { 'workflow_state' if has_wf else 'docstatus' }
                FROM `tab{doctype}`
                WHERE {fieldname} IN ('{id_list}')
                ORDER BY modified DESC
                LIMIT 1
            """, as_dict=True)

        if result:
            value = result[0]['workflow_state'] if has_wf else docstatus_map.get(result[0]['docstatus'], 'Unknown')
            if value:
                return value

    return None
