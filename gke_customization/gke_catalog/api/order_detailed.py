import frappe, json
from frappe.utils import today
from frappe.utils import (
	get_datetime,get_first_day,get_last_day,nowdate,
    add_days,getdate
)
from collections import defaultdict
#/home/frappe/frappe-bench/apps/gke_customization/gke_customization/gke_catalog/api/order_detailed.py

# initial call
# http://192.168.200.207:8001/api/method/gke_customization.gke_order_forms.doc_events.sketch_order.get_sketch_order?

# http://192.168.200.207:8001/api/method/gke_customization.gke_catalog.api.order_detailed.get_order?from_date=2025-06-03&to_date=2025-06-05&company=Gurukrupa%20Export%20Private%20Limited&of_docstatus=1

# for initial loading check: http://192.168.200.207:8001/api/method/gke_customization.gke_catalog.api.order_detailed.get_order?is_initial_load=true

@frappe.whitelist()
def get_order_detail(from_date=None, to_date=None, of_docstatus=None, branch=None, order_form=None, customer=None, workflow_state=None, docstatus=None, is_initial_load=None):
    from_date = frappe.utils.getdate(from_date)
    to_date = frappe.utils.getdate(to_date)
    
    if is_initial_load == "true" or is_initial_load == True:
        filters = {
            'docstatus': 0  # Only Draft Order Forms
        }
    else:
        filters = {
            'order_date': ["between", [from_date, to_date]],
            'docstatus': int(of_docstatus) if of_docstatus is not None else 0
        }

    if branch:
        filters['branch'] = branch
    if order_form:
        filters['name'] = order_form
    if customer:
        filters['customer_code'] = customer

    if to_date and from_date:
        order_forms = frappe.db.get_list("Order Form",
            filters = filters,
            fields=["name", "docstatus", "company", "branch","workflow_state","order_date","customer_code"]
        )

        valid_sketch_order_forms = []
        for form in order_forms:
            order_filters = {'cad_order_form': form.name}
            
            if is_initial_load != "true" and is_initial_load != True:
                if docstatus:
                   order_filters['docstatus'] = int(docstatus)
                if workflow_state:
                   order_filters['workflow_state'] = workflow_state

            orders = frappe.db.get_list(
                "Order",
                filters=order_filters,
                fields=["name", "docstatus", "company", "branch","customer_code","cad_order_form","workflow_state",
                        "order_type","flow_type","order_date","delivery_date","cad_file",
                        "creation","owner","modified","_assign","item","new_bom","category"
                    ]
                )

            for order in orders:
                final_items = []
                item_code = order.get("item")

                if item_code:
                   item_data = frappe.db.get_value("Item", item_code, 
                            ["name", "item_group", "image", "stock_uom"], as_dict=True
                            )
                   if item_data:
                        final_items.append(item_data)

                bom_detail = frappe.db.get_list("BOM",
                    filters={
                        'name': order["new_bom"],
                        'bom_type': 'Template'
                    },
                    fields = [
                            "item",
                            "image",
                            "metal_weight",
                            "total_diamond_weight_in_gms",
                            "total_finding_weight_per_gram",
                            "total_gemstone_weight_in_gms",
                            "other_weight",
                            "finding_weight_",
                            "diamond_weight",
                            "gemstone_weight",
                            "front_view_finish"
                        ]
                ) 
                
                assign_raw = order.get("_assign")
                if assign_raw:
                    try:
                        assign_list = json.loads(assign_raw)
                        first_user = assign_list[0] if assign_list else None
                        order["_assign"] = first_user
                        order["assigned_depart"] = None
                        if first_user:
                            employee_dept = frappe.db.get_value("Employee",{'user_id': order["_assign"]},['department'])
                            order["assigned_depart"] = employee_dept
                    except Exception:
                        order["_assign"] = None
                        order["assigned_depart"] = None
                else:
                    order["_assign"] = None
                
                owner_raw = order.get("owner")
                if owner_raw:
                    try: 
                        order["owner_id"] = None
                        order["owner_dept"] = None
                        order["owner_desig"] = None
                        employee = frappe.db.get_value("Employee", {'user_id': owner_raw}, ['name', 'department', 'designation'], as_dict=True)
                        if employee:
                            order["owner_id"] = employee.name
                            order["owner_dept"] = employee.department
                            order["owner_desig"] = employee.designation

                    except Exception:
                        order["owner_id"] = None
                        order["owner_dept"] = None
                        order["owner_desig"] = None 
            
                order["order_id"] = order.pop("name")
                order["workflow_state"] = order.pop("workflow_state")
                order["items"] = final_items  
                order["bom_detail"] = bom_detail
            
            if form["docstatus"] == 0 or orders:
                form["of_docstatus"] = form.pop("docstatus")
                form["orderform_id"] = form.pop("name")
                form["of_workflow_state"] = form.pop("workflow_state")
                if orders:
                    form["order"] = orders
                
                valid_sketch_order_forms.append(form)

    return valid_sketch_order_forms

# main
@frappe.whitelist()
def get_order1(from_date=None, to_date=None, of_docstatus=None, branch=None, order_form=None, customer=None, workflow_state=None, docstatus=None, is_initial_load=None):
    from_date = frappe.utils.getdate(from_date) if from_date else None
    to_date = frappe.utils.getdate(to_date) if to_date else None

    if from_date and to_date and from_date > to_date:
        from_date, to_date = to_date, from_date

    filters = {}
    if from_date:
        filters['order_date'] = ["between", [from_date, to_date]]
    else:
        filters['order_date'] = ["<=", to_date]

    if of_docstatus:
        filters['docstatus'] = int(of_docstatus)
    if branch:
        filters['branch'] = branch
    if order_form:
        filters['name'] = order_form
    if customer:
        filters['customer_code'] = customer

    order_forms = frappe.db.get_list("Order Form",
        filters = filters,
        fields=["name", "docstatus", "company", "branch","workflow_state","order_date","customer_code"]
    )

    valid_sketch_order_forms = []
    for form in order_forms:
        order_filters = {'cad_order_form': form.name, 'docstatus': int(docstatus)}
        
        if is_initial_load != "true" and is_initial_load != True:
            if workflow_state:
                order_filters['workflow_state'] = workflow_state

        orders = frappe.db.get_list(
            "Order",
            filters=order_filters,
            fields=["name", "docstatus", "company", "branch","customer_code","cad_order_form","workflow_state",
                    "order_type","flow_type","order_date","delivery_date","cad_file",
                    "creation","owner","modified","_assign","item","new_bom","category"
                ]
            )

        for order in orders:
            final_items = []
            item_code = order.get("item")

            if item_code:
                item_data = frappe.db.get_value("Item", item_code, 
                        ["name", "item_group", "image", "stock_uom"], as_dict=True
                        )
                if item_data:
                    final_items.append(item_data)

            bom_detail = frappe.db.get_list("BOM",
                filters={
                    'name': order["new_bom"],
                    'bom_type': 'Template'
                },
                fields = [
                        "item",
                        "image",
                        "metal_weight",
                        "total_diamond_weight_in_gms",
                        "total_finding_weight_per_gram",
                        "total_gemstone_weight_in_gms",
                        "other_weight",
                        "finding_weight_",
                        "diamond_weight",
                        "gemstone_weight",
                        "front_view_finish"
                    ]
            ) 
            
            assign_raw = order.get("_assign")
            if assign_raw:
                try:
                    assign_list = json.loads(assign_raw)
                    first_user = assign_list[0] if assign_list else None
                    order["_assign"] = first_user
                    order["assigned_depart"] = None
                    if first_user:
                        employee_dept = frappe.db.get_value("Employee",{'user_id': order["_assign"]},['department'])
                        order["assigned_depart"] = employee_dept
                except Exception:
                    order["_assign"] = None
                    order["assigned_depart"] = None
            else:
                order["_assign"] = None
            
            owner_raw = order.get("owner")
            if owner_raw:
                try: 
                    order["owner_id"] = None
                    order["owner_dept"] = None
                    order["owner_desig"] = None
                    employee = frappe.db.get_value("Employee", {'user_id': owner_raw}, ['name', 'department', 'designation'], as_dict=True)
                    if employee:
                        order["owner_id"] = employee.name
                        order["owner_dept"] = employee.department
                        order["owner_desig"] = employee.designation

                except Exception:
                    order["owner_id"] = None
                    order["owner_dept"] = None
                    order["owner_desig"] = None 
        
            order["order_id"] = order.pop("name")
            order["workflow_state"] = order.pop("workflow_state")
            order["items"] = final_items  
            order["bom_detail"] = bom_detail
        
        if form["docstatus"] == 0 or orders:
            form["of_docstatus"] = form.pop("docstatus")
            form["orderform_id"] = form.pop("name")
            form["of_workflow_state"] = form.pop("workflow_state")
            if orders:
                form["order"] = orders
            
            valid_sketch_order_forms.append(form)

    # return valid_sketch_order_forms
    total_count = len(valid_sketch_order_forms)

    return {
        "data": valid_sketch_order_forms,
        "total_count": total_count
    }

@frappe.whitelist()
def get_order12(from_date=None, to_date=None, of_docstatus=None, branch=None, order_form=None,
            customer=None, workflow_state=None, docstatus=None,is_initial_load=None,offset=None, limit=None):

    from_date = frappe.utils.getdate(from_date) if from_date else None
    to_date = frappe.utils.getdate(to_date) if to_date else None

    if from_date and to_date and from_date > to_date:
        from_date, to_date = to_date, from_date

    limit = int(frappe.form_dict.get("limit", limit)) if limit else 20
    offset = int(frappe.form_dict.get("offset", offset)) if offset else 0

    filters = {}
    if from_date:
        filters['order_date'] = ["between", [from_date, to_date]]
    else:
        filters['order_date'] = ["<=", to_date]

    if of_docstatus is not None:
        filters['docstatus'] = int(of_docstatus)
    if branch:
        filters['branch'] = branch
    if order_form:
        filters['name'] = ["like", f"%{order_form}%"]
    if customer:
        filters['customer_code'] = customer
 
    order_forms = frappe.get_list(
        "Order Form",
        filters=filters,
        fields=["name", "docstatus", "company", "branch", "workflow_state", "order_date", "customer_code"],
        order_by="creation desc",
         
    )
 
    form_names = [form.name for form in order_forms]
    orders = frappe.get_list(
        "Order",
        filters={
            "cad_order_form": ["in", form_names],
            "docstatus": int(docstatus) if docstatus is not None else ["!=", 2],
            **({"workflow_state": workflow_state} if is_initial_load != "true" and workflow_state else {})
        },
        fields=[
            "name", "docstatus", "company", "branch", "customer_code", "cad_order_form", "workflow_state",
            "order_type", "flow_type", "order_date", "delivery_date", "cad_file", "creation",
            "owner", "modified", "_assign", "item", "new_bom", "category"
        ]
    )

    # Group orders by Order Form
    orders_by_form = {}
    for order in orders:
        orders_by_form.setdefault(order.cad_order_form, []).append(order)

    # Get all item codes and bom names
    item_codes = list({o.item for o in orders if o.item})
    bom_names = list({o.new_bom for o in orders if o.new_bom})

    # Bulk fetch item details
    items_data = {}
    if item_codes:
        items = frappe.get_list("Item", filters={"name": ["in", item_codes]}, fields=["name", "item_group", "image", "stock_uom"])
        items_data = {item.name: item for item in items}

    # Bulk fetch BOM details
    bom_details = {}
    if bom_names:
        boms = frappe.get_list("BOM",
            filters={"name": ["in", bom_names], "bom_type": "Template"},
            fields=["name", "item", "image", "metal_weight", "total_diamond_weight_in_gms", "total_finding_weight_per_gram",
                    "total_gemstone_weight_in_gms", "other_weight", "finding_weight_", "diamond_weight", "gemstone_weight",
                    "front_view_finish"]
        )
        bom_details = {bom.name: bom for bom in boms}

    # Get all users from assign and owner fields
    user_ids = list({o.owner for o in orders if o.owner} | {json.loads(o._assign)[0] for o in orders if o._assign})
    employees = {}
    if user_ids:
        emp_list = frappe.get_list("Employee", filters={"user_id": ["in", user_ids]}, fields=["user_id", "name", "department", "designation"])
        employees = {emp.user_id: emp for emp in emp_list}

    valid_sketch_order_forms = []
    for form in order_forms:
        form_orders = orders_by_form.get(form.name, [])

        for order in form_orders:
            order["items"] = [items_data.get(order.item)] if order.item in items_data else []
            order["bom_detail"] = [bom_details.get(order.new_bom)] if order.new_bom in bom_details else []

            # Handle assigned user
            assign_raw = order.get("_assign")
            assign_user = None
            if assign_raw:
                try:
                    assign_user = json.loads(assign_raw)[0]
                    emp = employees.get(assign_user)
                    order["_assign"] = assign_user
                    order["assigned_depart"] = emp.department if emp else None
                except:
                    order["_assign"] = None
                    order["assigned_depart"] = None
            else:
                order["_assign"] = None
                order["assigned_depart"] = None

            # Handle owner
            owner_user = order.get("owner")
            if owner_user:
                emp = employees.get(owner_user)
                order["owner_id"] = emp.name if emp else None
                order["owner_dept"] = emp.department if emp else None
                order["owner_desig"] = emp.designation if emp else None

            order["order_id"] = order.pop("name")

        if form.docstatus == 0 or form_orders:
            form["of_docstatus"] = form.pop("docstatus")
            form["orderform_id"] = form.pop("name")
            form["of_workflow_state"] = form.pop("workflow_state")
            form["order"] = form_orders
            valid_sketch_order_forms.append(form)

    total_count = len(valid_sketch_order_forms)
    return {
        "total_count": total_count,
        "data": valid_sketch_order_forms[offset:offset + limit]
    }


@frappe.whitelist()
def get_order(from_date=None, to_date=None, of_docstatus=None, branch=None, order_form=None, 
            customer=None, workflow_state=None, docstatus=None, workflow_type=None, design_type=None,
            is_initial_load=None,offset=None, limit=None):
    from_date = frappe.utils.getdate(from_date) if from_date else None
    to_date = frappe.utils.getdate(to_date) if to_date else None

    if from_date and to_date and from_date > to_date:
        from_date, to_date = to_date, from_date

    limit = int(frappe.form_dict.get("limit", limit)) if limit else 20
    offset = int(frappe.form_dict.get("offset", offset)) if offset else 0

    filters = {}
    if from_date:
        filters["order_date"] = ["between", [from_date, to_date]]
    else:
        filters["order_date"] = ["<=", to_date]

    if of_docstatus is not None:
        filters["docstatus"] = int(of_docstatus)
    if branch:
        filters["branch"] = branch
    if order_form:
        filters['name'] = ["like", f"%{order_form}%"]
    if customer:
        filters["customer_code"] = customer

    order_forms = frappe.get_all("Order Form",
        filters=filters,
        fields=["name", "docstatus", "company", "branch", "workflow_state", "order_date", "customer_code"],
        # start=offset,
        # page_length=limit
    
    )

    if not order_forms:
        return {"data": [], "total_count": 0}

    form_names = [of["name"] for of in order_forms]
    order_filters = {
        "cad_order_form": ["in", form_names],
        "docstatus": int(docstatus)
    }

    if is_initial_load != "true" and is_initial_load != True and workflow_state:
        order_filters["workflow_state"] = workflow_state
    
    if workflow_type:
        order_filters["workflow_type"] = workflow_type
    if design_type:
        order_filters["design_type"] = design_type

    orders = frappe.get_all("Order",
        filters=order_filters,
        fields=[
            "name", "docstatus", "company", "branch", "customer_code", "cad_order_form",
            "workflow_state", "order_type", "flow_type", "order_date", "delivery_date", "cad_file",
            "creation", "owner", "modified", "_assign", "item", "new_bom", "category",
            "design_type","workflow_type","design_image_1"
        ],
        # start=offset,
        # page_length=limit
    )
    
    # Group orders by cad_order_form
    order_map = defaultdict(list)
    item_codes = set()
    bom_names = set()
    users_to_fetch = set()

    for order in orders:
        order_map[order["cad_order_form"]].append(order)
        if order.get("item"):
            item_codes.add(order["item"])
        if order.get("new_bom"):
            bom_names.add(order["new_bom"])
        if order.get("owner"):
            users_to_fetch.add(order["owner"])
        if order.get("_assign"):
            try:
                assign_list = json.loads(order["_assign"])
                if assign_list:
                    users_to_fetch.add(assign_list[0])
            except:
                pass

    # Fetch Item Details
    item_details = {}
    if item_codes:
        items = frappe.get_all("Item", filters={"name": ["in", list(item_codes)]},
                               fields=["name", "item_group", "image", "stock_uom"])
        item_details = {item["name"]: item for item in items}

    # Fetch BOM Details
    bom_details = {}
    if bom_names:
        boms = frappe.get_all("BOM",
            filters={"name": ["in", list(bom_names)], "bom_type": "Template"},
            fields=[
                "name", "item", "image", "metal_weight", "total_diamond_weight_in_gms",
                "total_finding_weight_per_gram", "total_gemstone_weight_in_gms", "other_weight",
                "finding_weight_", "diamond_weight", "gemstone_weight", "front_view_finish"
            ]
        )
        bom_details = {bom["name"]: bom for bom in boms}

    # Fetch User Employee Data
    employee_data = {}
    if users_to_fetch:
        employees = frappe.get_all("Employee", filters={"user_id": ["in", list(users_to_fetch)]},
                                   fields=["user_id", "name", "department", "designation"])
        employee_data = {emp["user_id"]: emp for emp in employees}

    # Assemble Orders
    final_forms = []
    for form in order_forms:
        related_orders = order_map.get(form["name"], [])
        for order in related_orders:
            order["order_id"] = order.pop("name")
            order["items"] = [item_details.get(order["item"])] if order.get("item") in item_details else []
            order["bom_detail"] = [bom_details.get(order["new_bom"])] if order.get("new_bom") in bom_details else []

            assign = None
            assigned_user = None
            assigned_dept = None
            try:
                assign_list = json.loads(order.get("_assign", "[]"))
                assign = assign_list[0] if assign_list else None
                assigned_user = employee_data.get(assign, {}).get("user_id") if assign else None
                assigned_dept = employee_data.get(assign, {}).get("department") if assign else None
            except:
                pass

            order["_assign"] = assign
            order["assigned_depart"] = assigned_dept
            order["assigned_user"] = assigned_user

            owner = order.get("owner")
            emp_info = employee_data.get(owner, {}) if owner else {}
            order["owner_id"] = emp_info.get("name")
            order["owner_dept"] = emp_info.get("department")
            order["owner_desig"] = emp_info.get("designation")

        if form["docstatus"] == 0 or related_orders:
            form["orderform_id"] = form.pop("name")
            form["of_docstatus"] = form.pop("docstatus")
            form["of_workflow_state"] = form.pop("workflow_state")
            form["order"] = related_orders
            final_forms.append(form)

    return {
        "total_count": len(final_forms),
        "data": final_forms[offset:offset + limit]
    }
