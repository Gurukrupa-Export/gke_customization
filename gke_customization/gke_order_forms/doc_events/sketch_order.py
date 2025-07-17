import frappe, json 
from collections import defaultdict
from frappe.utils import (
	get_datetime,get_first_day,get_last_day,nowdate,add_days,getdate,today
)

@frappe.whitelist()
def get_sketch_order_detail(from_date=None, to_date=None,sof_docstatus=None, branch=None, sketch_order_form=None, customer=None, 
                    workflow_state=None, docstatus=None, is_initial_load=None,offset=None,limit=None):
    from_date = frappe.utils.getdate(from_date) if from_date else None
    to_date = frappe.utils.getdate(to_date) if to_date else None
     
    if from_date and to_date and from_date > to_date:
        from_date, to_date = to_date, from_date
    
    limit = int(frappe.form_dict.get("limit", limit)) if limit else int(frappe.form_dict.get("limit", 20))
    offset = int(frappe.form_dict.get("offset", offset)) if offset else int(frappe.form_dict.get("offset", 0))

    filters = {}
    if from_date:
        filters['order_date'] = ["between", [from_date, to_date]]
    else:
        filters['order_date'] = ["<=", to_date]

    if sof_docstatus:
        filters['docstatus'] = int(sof_docstatus) or 0
    if branch:
        filters['branch'] = branch
    if sketch_order_form:
        filters['name'] = sketch_order_form  # Assuming this is the primary key of Sketch Order Form
    if customer:
        filters['customer_code'] = customer
    # if company and company.strip():
    #     filters['company'] = company

    # if to_date and from_date:
    sketch_order_forms = frappe.db.get_list("Sketch Order Form",
        filters = filters,
        fields=["name", "docstatus", "company", "branch","workflow_state","order_date","customer_code"]
    )
    # frappe.throw(f"{sketch_order_forms}")

    valid_sketch_order_forms = []
    for form in sketch_order_forms:
        order_filters = {'sketch_order_form': form.name , 'docstatus': int(docstatus)}
        
        if is_initial_load != "true" and is_initial_load != True:
            # if docstatus:
            #    order_filters['docstatus'] = int(docstatus)
            if workflow_state:
                order_filters['workflow_state'] = workflow_state

        orders = frappe.db.get_list(
            "Sketch Order",
            filters=order_filters,
            fields=["name", "docstatus", "company", "branch","customer_code","sketch_order_form","workflow_state","sketch_image",
                    "order_type","flow_type","order_date","delivery_date",
                    "creation","owner","modified","_assign"
                    ]
        )

        for order in orders:
            final_items = frappe.db.get_all("Final Sketch Approval CMO",
                filters={
                    'parent': order["name"]
                },
                fields=["sketch_image", "designer", "item", "category", "sub_category","setting_type","gold_wt_approx",
                        "diamond_wt_approx", ]
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
        
            order["sketch_order_id"] = order.pop("name")
            order["workflow_state"] = order.pop("workflow_state")
            order["items"] = final_items
        
        if form["docstatus"] == 0 or orders:
            form["sof_docstatus"] = form.pop("docstatus")
            form["sketch_orderform_id"] = form.pop("name")
            form["sof_workflow_state"] = form.pop("workflow_state")
            if orders:
                form["sketch_order"] = orders 
            
            valid_sketch_order_forms.append(form) 
            
    total_count = len(valid_sketch_order_forms)
    return {
        "data": valid_sketch_order_forms[offset:offset + limit],
        "total_count": total_count
    }

@frappe.whitelist()
def get_sketch_order(from_date=None, to_date=None, sof_docstatus=None, branch=None,sketch_order_form=None, customer=None, 
                        workflow_state=None,docstatus=None, is_initial_load=None, offset=None, limit=None):
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

    if sof_docstatus:
        filters['docstatus'] = int(sof_docstatus)
    if branch:
        filters['branch'] = branch
    if sketch_order_form:
        filters['name'] = ["like", f"%{sketch_order_form}%"]
    if customer:
        filters['customer_code'] = customer

    #Sketch Order Forms
    sketch_order_forms = frappe.db.get_list(
        "Sketch Order Form",
        filters=filters,
        fields=["name", "docstatus", "company", "branch", "workflow_state", "order_date", "customer_code"],
        order_by="modified desc"
    )

    form_names = [form["name"] for form in sketch_order_forms]
    if not form_names:
        return {"data": [], "total_count": 0}

    order_filters = {
        "sketch_order_form": ["in", form_names],
        "docstatus": int(docstatus) if docstatus else 0
    }
    if is_initial_load not in ["true", True] and workflow_state:
        order_filters["workflow_state"] = workflow_state

    sketch_orders = frappe.db.get_all(
        "Sketch Order",
        filters=order_filters,
        fields=["name", "docstatus", "company", "branch", "customer_code", "sketch_order_form", "workflow_state",
                "sketch_image", "order_type", "flow_type", "order_date", "delivery_date", "creation",
                "owner", "modified", "_assign"]
    )

    order_names = [order["name"] for order in sketch_orders]
    item_details = frappe.db.get_all(
        "Final Sketch Approval CMO",
        filters={"parent": ["in", order_names]},
        fields=["parent", "sketch_image", "designer", "item", "category", "sub_category", "setting_type",
                "gold_wt_approx", "diamond_wt_approx"]
    )

    # Group items by order
    items_by_order = defaultdict(list)
    for item in item_details:
        items_by_order[item["parent"]].append(item)

    # Cache employee details
    employee_cache = {}
    def get_employee_details(user_id):
        if not user_id:
            return {"owner_id": None, "owner_dept": None, "owner_desig": None}
        if user_id not in employee_cache:
            emp = frappe.db.get_value("Employee", {"user_id": user_id},
                                     ["name", "department", "designation"], as_dict=True)
            employee_cache[user_id] = emp or {}
        return employee_cache[user_id]

    # Assign items to orders
    orders_by_form = defaultdict(list)
    for order in sketch_orders:
        order_id = order.pop("name")
        order["sketch_order_id"] = order_id
        order["items"] = items_by_order.get(order_id, [])

        assign_raw = order.get("_assign")
        try:
            assign_list = json.loads(assign_raw) if assign_raw else []
            order["_assign"] = assign_list[0] if assign_list else None
            assigned = get_employee_details(order["_assign"])
            order["assigned_depart"] = assigned.get("department")
        except Exception:
            order["_assign"] = None
            order["assigned_depart"] = None

        owner_details = get_employee_details(order.get("owner"))
        order["owner_id"] = owner_details.get("name")
        order["owner_dept"] = owner_details.get("department")
        order["owner_desig"] = owner_details.get("designation")

        orders_by_form[order["sketch_order_form"]].append(order)

    # Final result construction
    valid_sketch_order_forms = []
    for form in sketch_order_forms:
        form_id = form.pop("name")
        form["sketch_orderform_id"] = form_id
        form["sof_docstatus"] = form.pop("docstatus")
        form["sof_workflow_state"] = form.pop("workflow_state")
        form_orders = orders_by_form.get(form_id, [])
        if form["sof_docstatus"] == 0 or form_orders:
            form["sketch_order"] = form_orders
            valid_sketch_order_forms.append(form)

    total_count = len(valid_sketch_order_forms)

    return {
        "data": valid_sketch_order_forms[offset:offset + limit],
        "total_count": total_count
    }
