# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):

    columns = get_columns()
    data = []

    if not filters:
        filters = {}

    order_filters = {}

    
    if filters.get("from_date") and filters.get("to_date"):
        order_filters["order_date"] = ["between", [filters["from_date"], filters["to_date"]]]

   
    if filters.get("order_id"):
        order_filters["name"] = ["in", filters["order_id"]]
    if filters.get("company"):
        order_filters["company"] = ["in", filters["company"]]
    if filters.get("branch"):
        branch_names = filters["branch"]
        branch_ids = frappe.get_all("Branch", filters={"branch_name": ["in", branch_names]}, pluck="name")
        order_filters["branch"] = ["in", branch_ids]

    if filters.get("customer"):
        order_filters["customer_code"] = ["in", filters["customer"]]
        # customer_names = filters["customer"]
        # customer_codes = frappe.get_all("Customer", filters={"customer_name": ["in", customer_names]}, pluck="name")
        # order_filters["customer_code"] = ["in", customer_codes]
   
    if filters.get("employee"):
        employee_names = filters["employee"]
        if isinstance(employee_names, str):
           employee_names = [employee_names]

        employee_ids = frappe.get_all("Employee",
        filters={"employee_name": ["in", employee_names]},
        fields=["name", "user_id"]
    )

        user_ids = [e["user_id"] for e in employee_ids if e.get("user_id")]
        if user_ids:
            order_filters["owner"] = ["in", user_ids]
        else:
            order_filters["owner"] = "__invalid_user__"


    if filters.get("setting_type"):
        if isinstance(filters["setting_type"], str):
            filters["setting_type"] = [filters["setting_type"]]
        order_filters["setting_type"] = ["in", filters["setting_type"]]

    if filters.get("status"):
        order_filters["workflow_state"] = filters["status"]
    

   
    orders = frappe.get_all("Order", 
        fields=["name", "company", "branch", "order_type", "order_date", 
                "workflow_state", "delivery_date", "updated_delivery_date","owner"],
        filters=order_filters
    )
    


    # total_orders = len(orders)
    total_orders = len([o for o in orders if o["workflow_state"] != "Approved"])
    unassigned_orders = 0
    other_orders = 0
    approved_orders = 0

    for order in orders:
        state = order["workflow_state"]
        if state == "Draft":
            unassigned_orders += 1
        elif state == "Approved":
            approved_orders += 1
        else:
            other_orders += 1
             

    # message = get_message(total_orders, unassigned_orders, other_orders,approved_orders)
    message = None
    report_summary = get_report_summary(total_orders, unassigned_orders, other_orders, approved_orders, orders, filters)


    chart = get_chart_data(orders)


    order_names = [o["name"] for o in orders]

  
    designer_map = {}
    designer_dept_map = {}
    if order_names:
        assignments = frappe.get_all(
            "Designer Assignment - CAD",
            filters={"parent": ["in", order_names]},
            fields=["parent", "designer_name","designer"]
        )

        # for a in assignments:
        #     if a["parent"] not in designer_map:
        #         designer_map[a["parent"]] = a["designer_name"]
        for a in assignments:
            order_id = a["parent"]
            designer_id = a.get("designer")  
            if designer_id:  
                designer_name = frappe.db.get_value("Employee", designer_id, "employee_name") or designer_id

                if order_id not in designer_map:
                    designer_map[order_id] = designer_name

         
            dept = frappe.db.get_value("Employee", {"name": designer_id}, "department")
            designer_dept_map[order_id] = dept or "" 
    


   
    for order in orders:
        updated_delivery_date = order.get("updated_delivery_date")
        delivery_date = order.get("delivery_date")

        if updated_delivery_date:
            updated_delivery_date_html = f'<span style="color: green;">{updated_delivery_date}</span>'
        else:
            updated_delivery_date_html = "-"

        if delivery_date:
            if updated_delivery_date:
                delivery_date_html = f'<span style="color: red;">{delivery_date}</span>'
            else:
                delivery_date_html = f"{delivery_date}"
        else:
           delivery_date_html = "-"

        data.append({
        "name": order["name"],
        "company": order["company"],
        "branch": frappe.db.get_value("Branch", order["branch"], "branch_name"),
        "order_type": order["order_type"],
        "order_date": order["order_date"],
        "designer_name": designer_map.get(order["name"], ""),
        "workflow_state": order["workflow_state"],
       "delivery_date": delivery_date_html,
    "updated_delivery_date": updated_delivery_date_html,
        "assigned_to_dept": designer_dept_map.get(order["name"], "")
    })

    return columns, data,message,chart,report_summary

def get_columns():
    return [
        {"label": "Order ID", "fieldname": "name", "fieldtype": "Link", "options": "Order", "width": 160},
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 190},
        {"label": "Branch", "fieldname": "branch", "fieldtype": "Data", "width": 170},
        {"label": "Order Type", "fieldname": "order_type", "fieldtype": "Data", "width": 100},
        {"label": "Order Date", "fieldname": "order_date", "fieldtype": "Date", "width": 130},
        {"label": "Designer", "fieldname": "designer_name", "fieldtype": "Data", "width": 200},
        {"label": "Assigned to Deptartment", "fieldname": "assigned_to_dept", "fieldtype": "Data", "width": 200},
        {"label": "Workflow State", "fieldname": "workflow_state", "fieldtype": "Data", "width": 200},
        {"label": "Delivery Date", "fieldname": "delivery_date", "fieldtype": "HTML", "width": 160},
        {"label": "Updated Delivery Date", "fieldname": "updated_delivery_date", "fieldtype": "HTML", "width": 200},
    ]




def get_chart_data(orders):
    workflow_order = [
        "Draft", "Assigned", "Assigned-On-Hold",
        "Designing", "Update Designer", "Designing- On-Hold",
        "Sent to QC", "Sent to QC-On-Hold", "Update Item",
        "Update BOM","BOM QC","BOM QC- On- Hold",
        "Approved", "On-Hold",  "Cancelled",  "Rejected",
    ]

   
    state_counts = {}
    for order in orders:
        state = order.get("workflow_state", "Unknown")
        state_counts[state] = state_counts.get(state, 0) + 1

   
    labels = []
    values = []
    for state in workflow_order:
        count = state_counts.get(state, 0)
        if count > 0:
            labels.append(state)
            values.append(count)

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Order Count", "values": values},
            ],
        },
        "type": "bar",
        "barOptions": {"stacked": False},
    }



def get_report_summary(total, unassigned, assigned, approved, orders=None, filters=None):
    summary = [
        {
            "value": total,
            "indicator": "Blue",
            "label": "Total CAD",
            "datatype": "Int",
        },
        {
            "value": unassigned,
            "indicator": "Red" if unassigned > 0 else "Green",
            "label": "Unassigned CAD",
            "datatype": "Int",
        },
        {
            "value": assigned,
            "indicator": "Green",
            "label": "Assigned CAD",
            "datatype": "Int",
        },
    ]

 
    target_employee_ids = [
        "HR-EMP-00968", "HR-EMP-00222", "HR-EMP-00957",
         "HR-EMP-00254", "HR-EMP-00935", "HR-EMP-02452"
    ]

    employee_records = frappe.get_all("Employee",
        filters={"name": ["in", target_employee_ids]},
        fields=["name", "employee_name", "user_id"]
    )

    user_id_to_name = {
        emp["user_id"]: emp["employee_name"]
        for emp in employee_records if emp.get("user_id")
    }

    user_order_counts = {
        user_id_to_name.get(user_id, user_id): 0 for user_id in user_id_to_name
    }

   
    base_order_filters = {}

    if filters:
        if filters.get("from_date") and filters.get("to_date"):
            base_order_filters["order_date"] = ["between", [filters["from_date"], filters["to_date"]]]
        if filters.get("order_id"):
            base_order_filters["name"] = ["in", filters["order_id"]]
        if filters.get("company"):
            base_order_filters["company"] = ["in", filters["company"]]
        if filters.get("branch"):
            branch_names = filters["branch"]
            branch_ids = frappe.get_all("Branch", filters={"branch_name": ["in", branch_names]}, pluck="name")
            base_order_filters["branch"] = ["in", branch_ids]
        if filters.get("customer"):
            base_order_filters["customer_code"] = ["in", filters["customer"]]
        if filters.get("setting_type"):
            base_order_filters["setting_type"] = ["in", filters["setting_type"]]
        if filters.get("status"):
            base_order_filters["workflow_state"] = filters["status"]

   
    employee_order_filters = base_order_filters.copy()

    if filters and filters.get("employee"):
        selected = filters["employee"]
        if isinstance(selected, str):
            selected = [selected]
        employee_ids = frappe.get_all("Employee",
            filters={"employee_name": ["in", selected]},
            pluck="user_id"
        )
        employee_order_filters["owner"] = ["in", employee_ids]

  
    employee_orders = frappe.get_all("Order",
        fields=["name", "owner", "workflow_state"],
        filters=employee_order_filters
    )

    for order in employee_orders:
        if order.get("workflow_state") == "Approved":
            continue
        uid = order.get("owner")
        if uid in user_id_to_name:
            name = user_id_to_name[uid]
            user_order_counts[name] += 1

    
    for name in user_order_counts:
        count = user_order_counts[name]
        summary.append({
            "value": count,
            "indicator": "Blue" if count > 0 else "Grey",
            "label": name or "Unknown User",
            "datatype": "Int",
        })

    return summary




def get_message(total, unassigned, others,approved):
    return f"""
    <div style="font-size: 14px; font-weight: bold; margin-bottom: 10px;">
        <span class="indicator blue">Total Orders: {total}</span>&nbsp;&nbsp;&nbsp;
        <span class="indicator red">Unassigned: {unassigned}</span>&nbsp;&nbsp;&nbsp;
        <span class="indicator orange">Assigned: {others}</span>&nbsp;&nbsp;&nbsp;
         <span class="indicator green">Approved: {approved}</span>&nbsp;&nbsp;&nbsp;
    </div>
    """