import frappe, json
from frappe.utils import today
from frappe.utils import (
    time_diff,get_datetime_str,time_diff_in_hours,time_diff_in_seconds,format_time,format_duration
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
        if form["workflow_state"] == 'Cancelled':
            continue
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


import frappe
import json
from collections import defaultdict
from frappe.utils import (
    getdate,
    get_datetime_str,
    time_diff,
    time_diff_in_hours,
    time_diff_in_seconds,
    format_duration,
)

@frappe.whitelist()
def get_order(
    from_date=None,
    to_date=None,
    of_docstatus=None,
    branch=None,
    order_form=None,
    customer=None,
    workflow_state=None,
    docstatus=None,
    workflow_type=None,
    design_type=None,
    is_initial_load=None,
    offset=0,
    limit=20,
):

    # ---------------- Date Handling ---------------- #
    from_date = getdate(from_date) if from_date else None
    to_date = getdate(to_date) if to_date else None

    if from_date and to_date and from_date > to_date:
        from_date, to_date = to_date, from_date

    limit = int(limit or frappe.form_dict.get("limit", 20))
    offset = int(offset or frappe.form_dict.get("offset", 0))

    # ---------------- Order Form Filters ---------------- #
    filters = {}

    if from_date and to_date:
        filters["order_date"] = ["between", [from_date, to_date]]
    elif from_date:
        filters["order_date"] = [">=", from_date]
    elif to_date:
        filters["order_date"] = ["<=", to_date]

    if of_docstatus is not None:
        filters["docstatus"] = int(of_docstatus)

    if branch:
        filters["branch"] = branch

    if order_form:
        filters["name"] = ["like", f"%{order_form}%"]

    if customer:
        filters["customer_code"] = customer

    order_forms = frappe.get_all(
        "Order Form",
        filters=filters,
        fields=[
            "name",
            "docstatus",
            "company",
            "branch",
            "workflow_state",
            "order_date",
            "customer_code",
            "delivery_date",
        ],
    )

    if not order_forms:
        return {"total_count": 0, "data": []}

    form_names = [d.name if hasattr(d, "name") else d["name"] for d in order_forms]

    # ---------------- Order Filters ---------------- #
    order_filters = {
        "cad_order_form": ["in", form_names],
    }

    if docstatus is not None:
        order_filters["docstatus"] = int(docstatus)

    if is_initial_load not in ("true", True) and workflow_state:
        order_filters["workflow_state"] = workflow_state

    if workflow_type:
        order_filters["workflow_type"] = workflow_type

    if design_type:
        order_filters["design_type"] = design_type

    orders = frappe.get_all(
    "Order",
    filters=order_filters,
    fields=[
        "name",
        "docstatus",
        "company",
        "branch",
        "customer_code",
        "cad_order_form",
        "workflow_state",
        "order_type",
        "flow_type",
        "order_date",
        "cad_delivery_date",
        "delivery_date",
        "cad_file",
        "creation",
        "owner",
        "modified",
        "_assign",
        "item",
        "new_bom",
        "category",
        "setting_type",
        "design_type",
        "workflow_type",
        "design_image_1",

        # Product Ratio Fields
        "gold_to_diamond_ratio",
        "metal_to_diamond_ratio_excl_of_finding",
        "diamond_ratio",
        "rating",
        ],
    )

    # ---------------- Collect Related Data ---------------- #
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

        try:
            assign_list = json.loads(order.get("_assign") or "[]")
            if assign_list:
                users_to_fetch.add(assign_list[0])
        except Exception:
            pass

    # ---------------- Item Details ---------------- #
    item_details = {
        d["name"]: d
        for d in frappe.get_all(
            "Item",
            filters={"name": ["in", list(item_codes)]},
            fields=["name", "item_group", "image", "stock_uom"],
        )
    } if item_codes else {}

    # ---------------- BOM Details ---------------- #
    bom_details = {
        d["name"]: d
        for d in frappe.get_all(
            "BOM",
            filters={
                "name": ["in", list(bom_names)],
                "bom_type": "Template",
            },
            fields=[
                "name",
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
                "front_view_finish",
            ],
        )
    } if bom_names else {}

    # ---------------- Employee Details ---------------- #
    employee_data = {
        d["user_id"]: d
        for d in frappe.get_all(
            "Employee",
            filters={"user_id": ["in", list(users_to_fetch)]},
            fields=["user_id", "name", "department", "designation"],
        )
    } if users_to_fetch else {}

    # ---------------- Designer Assignment Details ---------------- #
    order_ids = [order["name"] for order in orders]
    designer_names_by_order = defaultdict(list)
    if order_ids:
        designer_rows = frappe.get_all(
            "Designer Assignment - CAD",
            filters={"parent": ["in", order_ids], "parenttype": "Order"},
            fields=["parent", "designer_name", "idx"],
            order_by="parent, idx",
        )
        for row in designer_rows:
            if row.designer_name:
                designer_names_by_order[row.parent].append(row.designer_name)

    # ---------------- Time Taken (Approval) & Approver ---------------- #
    time_taken_by_order = {}
    approver_by_order = {}
    if order_ids:
        timesheets = frappe.get_all(
            "Timesheet",
            filters={"order": ["in", order_ids], "docstatus": ["!=", 2]},
            fields=["name", "order"],
        )
        timesheet_order_map = {ts.name: ts.order for ts in timesheets}

        if timesheet_order_map:
            workflow_comments = frappe.get_all(
                "Comment",
                filters={
                    "reference_doctype": "Timesheet",
                    "reference_name": ["in", list(timesheet_order_map.keys())],
                    "comment_type": "Workflow",
                    "content": ["in", ["Sent to QC", "Approved"]],
                },
                fields=["reference_name", "content", "creation", "owner"],
            )

            comments_by_timesheet = defaultdict(list)
            for c in workflow_comments:
                comments_by_timesheet[c.reference_name].append(c)

            latest_pair_by_order = {}
            latest_approved_by_order = {}
            for ts_name, order_name in timesheet_order_map.items():
                rows = comments_by_timesheet.get(ts_name, [])
                approved_rows = [c for c in rows if c.content == "Approved"]
                sent_to_qc_times = [c.creation for c in rows if c.content == "Sent to QC"]

                if not approved_rows:
                    continue

                latest_approved_row = max(approved_rows, key=lambda c: c.creation)
                approved_time = latest_approved_row.creation

                existing_approved = latest_approved_by_order.get(order_name)
                if not existing_approved or approved_time > existing_approved[0]:
                    latest_approved_by_order[order_name] = (approved_time, latest_approved_row.owner)

                prior_sent_to_qc_times = [t for t in sent_to_qc_times if t < approved_time]

                if not prior_sent_to_qc_times:
                    continue

                sent_to_qc_time = max(prior_sent_to_qc_times)

                existing_pair = latest_pair_by_order.get(order_name)
                if not existing_pair or approved_time > existing_pair[0]:
                    latest_pair_by_order[order_name] = (approved_time, sent_to_qc_time)

            for order_name, (approved_time, sent_to_qc_time) in latest_pair_by_order.items():
                seconds = time_diff_in_seconds(approved_time, sent_to_qc_time)
                time_taken_by_order[order_name] = format_duration(seconds)

            for order_name, (_, owner) in latest_approved_by_order.items():
                approver_by_order[order_name] = owner

    # ---------------- Final Response ---------------- #
    final_forms = []

    for form in order_forms:

        if form["workflow_state"] == "Cancelled":
            continue

        related_orders = order_map.get(form["name"], [])

        for order in related_orders:

            order["designer_name"] = ", ".join(designer_names_by_order.get(order["name"], []))
            order["time_taken_approval"] = time_taken_by_order.get(order["name"])
            order["approver"] = approver_by_order.get(order["name"])
            order["order_id"] = order.pop("name")
            order["items"] = (
                [item_details[order["item"]]]
                if order.get("item") in item_details
                else []
            )

            order["bom_detail"] = (
                [bom_details[order["new_bom"]]]
                if order.get("new_bom") in bom_details
                else []
            )

            # Assigned User
            assign = None
            try:
                assign_list = json.loads(order.get("_assign") or "[]")
                assign = assign_list[0] if assign_list else None
            except Exception:
                pass

            order["_assign"] = assign
            order["assigned_user"] = employee_data.get(assign, {}).get("user_id")
            order["assigned_depart"] = employee_data.get(assign, {}).get("department")

            # Owner Details
            owner_info = employee_data.get(order.get("owner"), {})
            order["owner_id"] = owner_info.get("name")
            order["owner_dept"] = owner_info.get("department")
            order["owner_desig"] = owner_info.get("designation")

            # Time Difference
            if form.get("order_date") and order.get("order_date"):
                of_date = get_datetime_str(form["order_date"])
                ord_date = get_datetime_str(order["order_date"])

                order["total_time_diff"] = time_diff(of_date, ord_date)
                order["total_time_diff_hours"] = round(
                    time_diff_in_hours(of_date, ord_date), 2
                )
                order["total_time_diff_days"] = format_duration(
                    time_diff_in_seconds(of_date, ord_date)
                )

        if form["docstatus"] == 0 or related_orders:
            form["orderform_id"] = form.pop("name")
            form["of_docstatus"] = form.pop("docstatus")
            form["of_workflow_state"] = form.pop("workflow_state")
            form["order"] = related_orders
            final_forms.append(form)

    return {
        "total_count": len(final_forms),
        "data": final_forms[offset: offset + limit],
    }