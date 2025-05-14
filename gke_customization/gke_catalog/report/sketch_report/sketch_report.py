# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart_data = get_chart_data(data)
	summary = get_report_summary(data)

	return columns, data, None, chart_data,summary

def get_columns():
	return [
        {"label": "Sketch Order Form ID", "fieldname": "sketch_order_form", "fieldtype": "Link", "options": "Sketch Order Form", "width": 170},
		{"label": "Sketch Order ID", "fieldname": "name", "fieldtype": "Link", "options": "Sketch Order", "width": 170},
		# {"label": "Workflow State", "fieldname": "workflow_state", "fieldtype": "Data", "width": 150},
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 190},
		{"label": "Created Branch", "fieldname": "branch", "fieldtype": "Data", "width": 170},
        {"label": "Created By", "fieldname": "owner", "fieldtype": "Data", "width": 190},
		{"label": "Working Branch", "fieldname": "working_branch", "fieldtype": "Data", "width": 170},
		{"label": "Department", "fieldname": "department", "fieldtype": "Data", "width": 170},
		{"label": "Creation Date", "fieldname": "creation", "fieldtype": "Date", "width": 170},
		{"label": "Design Type", "fieldname": "design_type", "fieldtype": "Data", "width": 170},
		{"label": "Order Type", "fieldname": "order_type", "fieldtype": "Data", "width": 100},
		{"label": "Category", "fieldname": "category", "fieldtype": "Data", "width": 170},
		{"label": "Sub Category", "fieldname": "subcategory", "fieldtype": "Data", "width": 170},
		{"label": "Metal Target", "fieldname": "metal_target", "fieldtype": "Data", "width": 170},
		{"label": "Diamond Target", "fieldname": "diamond_target", "fieldtype": "Data", "width": 170},
		{"label": "Is Metal Target Range", "fieldname": "is_metal_target_range", "fieldtype": "Data", "width": 170},
		{"label": "Is Diamond Target Range", "fieldname": "is_diamond_target_range", "fieldtype": "Data", "width": 190},
		{"label": "Designer", "fieldname": "designer_name", "fieldtype": "Data", "width": 200},
		{"label": "Assigned Sketch Qty", "fieldname": "assigned_qty", "fieldtype": "Data", "width": 180},
		{"label": "Approved Rough Sketch", "fieldname": "aproved_rough", "fieldtype": "Data", "width": 200},
		{"label": "Rejected Rough Sketch", "fieldname": "rejected_rough", "fieldtype": "Data", "width": 200},
		{"label": "Approved Final Sketch", "fieldname": "aproved_final", "fieldtype": "Data", "width": 200},
		{"label": "Rejected Final Sketch", "fieldname": "reject_final", "fieldtype": "Data", "width": 200},
		{"label": "Approx Gold Wt", "fieldname": "gold_wt_approx", "fieldtype": "Float", "width": 200},
		{"label": "Approx Diamond Wt", "fieldname": "diamond_wt_approx", "fieldtype": "Float", "width": 200},
	]

def build_designer_map(child_table, parent_field, fields):
	records = frappe.get_all(child_table, filters={parent_field: ["!=", ""]}, fields=[parent_field, "designer_name"] + fields)
	result = {}
	for rec in records:
		key = (rec[parent_field], rec["designer_name"])
		result[key] = {field: rec.get(field, 0) for field in fields}
	return result

def get_data(filters=None):
    filters = filters or {}
    order_filters = {}

    user = frappe.session.user
    user_details = frappe.get_value("Employee", {"user_id": user}, ["status", "designation", "department"])

    if user_details and user_details[0] == "Active" and user_details[1] in ["Manager", "Data Analyst L1"] and user_details[2] in ["Product Development - GEPL", "Sketch - GEPL"]:

        employee = frappe.get_value("Employee", {"user_id": user}, "name")
        reportees = frappe.get_all("Employee", filters={"reports_to": employee}, pluck="name")
        reportees.append(employee)

        order_filters["owner"] = ["in", reportees]
    else:
        pass

    if filters.get("start_date") and filters.get("end_date"):
        order_filters["creation"] = ["between", [filters["start_date"], filters["end_date"]]]

    if filters.get("company"):
        order_filters["company"] = filters["company"] if isinstance(filters["company"], str) else ["in", filters["company"]]

    if filters.get("status"):
        order_filters["workflow_state"] = filters["status"] if isinstance(filters["status"], str) else ["in", filters["status"]]

    if filters.get("setting_type"):
        order_filters["setting_type"] = filters["setting_type"] if isinstance(filters["setting_type"], str) else ["in", filters["setting_type"]]
     
    if filters.get("customer"):
        order_filters["customer_code"] = filters["customer"] if isinstance(filters["customer"], str) else ["in", filters["customer"]]

    if filters.get("designer_branch"):
        designers_in_branch = frappe.get_all("Employee", filters={"branch": filters["designer_branch"]}, pluck="name")
        if not designers_in_branch:
            return []

        matching_orders = frappe.get_all("Designer Assignment", filters={"designer": ["in", designers_in_branch]}, pluck="parent")
        if not matching_orders:
            return []

        order_filters["name"] = ["in", matching_orders]
    
    
    if filters.get("user"):
        selected_users = filters.get("user")
        # if isinstance(selected_users, str):
        #     selected_users = [selected_users]

        created_orders = frappe.get_all("Sketch Order", filters={
        "owner": ["in", selected_users]
    }, pluck="name")
        
        reportee_orders = []
        user_employee_map = frappe.get_all(
    "Employee",
    filters={"user_id": ["in", selected_users]},
    fields=["name", "user_id"]
)
        user_id_to_emp_id = {row.user_id: row.name for row in user_employee_map}
        for emp_id in user_id_to_emp_id.values():
            reportees = frappe.get_all("Employee", filters={"reports_to": emp_id}, pluck="user_id")
            if reportees:
                    reportee_orders += frappe.get_all("Sketch Order", filters={"owner": ["in", reportees]}, pluck="name")

    #     allocated_orders = frappe.get_all("ToDo", filters={
    #     "allocated_to": ["in", selected_users],
    #     "reference_type": "Sketch Order"
    # }, pluck="reference_name")

        combined_order_names = list(set(created_orders + reportee_orders))

        if not combined_order_names:
            return []

        order_filters["name"] = ["in", combined_order_names]
    
    
    # Fetch all Sketch Orders with the applied filters (no Designer Assignment required)
    sketch_orders = frappe.get_all("Sketch Order", filters=order_filters, fields=[
        "name", "sketch_order_form", "company", "branch", "department", "creation", "design_type", "workflow_state",
        "order_type", "category", "subcategory", "metal_target", "diamond_target",
        "is_metal_target_range", "is_diamond_target_range", "owner"
    ])

    # Fetch Designer Assignments that correspond to the fetched Sketch Orders
    so_map = {so["name"]: so for so in sketch_orders}
    so_names = list(so_map.keys())

    designer_assignments = frappe.get_all("Designer Assignment", filters={"parent": ["in", so_names]}, fields=[
        "parent", "designer_name", "count_1", "designer"
    ])

    # Build maps for approvals and targets
    rough_sketch_map = build_designer_map("Rough Sketch Approval", "parent", ["approved", "reject"])
    final_sketch_map = build_designer_map("Final Sketch Approval HOD", "parent", ["approved", "reject"])
    final_cmo_map = build_designer_map("Final Sketch Approval CMO", "parent", ["gold_wt_approx", "diamond_wt_approx"])
    
    # Map designer to their branch
    designer_ids = list(set(da["designer"] for da in designer_assignments))
    designer_branch_map = {}
    if designer_ids:
        employees = frappe.get_all(
            "Employee", filters={"name": ["in", designer_ids]},
            fields=["name", "employee_name", "branch", "department", "designation"]
        )
        designer_branch_map = {emp.name: emp.branch for emp in employees}
    
    # Fetch branches of owners (creator of Sketch Orders)
    owners = list(set(so["owner"] for so in sketch_orders))
    owner_branch_map = {}
    if owners:
        owner_employees = frappe.get_all("Employee", filters={"user_id": ["in", owners]}, fields=["user_id", "branch"])
        owner_branch_map = {emp.user_id: emp.branch for emp in owner_employees}

    # Prepare the final data to return, including all orders, even without Designer Assignments
    data = []
    for so in sketch_orders:
        so_name = so["name"]

        for da in designer_assignments:
            if da["parent"] == so_name:
                key = (so_name, da["designer_name"])
                data.append({
                    **so,
                    "branch": owner_branch_map.get(so.get("owner")),
                    "working_branch": designer_branch_map.get(da["designer"]),
                    "designer_name": da["designer_name"],
                    "assigned_qty": da["count_1"],
                    "aproved_rough": rough_sketch_map.get(key, {}).get("approved", 0),
                    "rejected_rough": rough_sketch_map.get(key, {}).get("reject", 0),
                    "aproved_final": final_sketch_map.get(key, {}).get("approved", 0),
                    "reject_final": final_sketch_map.get(key, {}).get("reject", 0),
                    "gold_wt_approx": final_cmo_map.get(key, {}).get("gold_wt_approx", 0),
                    "diamond_wt_approx": final_cmo_map.get(key, {}).get("diamond_wt_approx", 0),
                    "is_metal_target_range": '<span style="color:green;font-weight:bold; font-size:16px;">&#10004;</span>' if so.get("is_metal_target_range") == 1 else "",
                    "is_diamond_target_range": '<span style="color:green;font-weight:bold; font-size:16px;">&#10004;</span>' if so.get("is_diamond_target_range") == 1 else "",
                })

        if not any(da["parent"] == so_name for da in designer_assignments):
            data.append({
                **so,
                "branch": owner_branch_map.get(so.get("owner")),
                "working_branch": "",
                "designer_name": "",
                "assigned_qty": 0,
                "aproved_rough": 0,
                "rejected_rough": 0,
                "aproved_final": 0,
                "reject_final": 0,
                "gold_wt_approx": 0,
                "diamond_wt_approx": 0,
                "is_metal_target_range": "",
                "is_diamond_target_range": "",
            })

    return data



# 

def get_chart_data(orders):
    workflow_order = [
        "Draft", "Unassigned", "Assigned", "Rough Sketch Approval (HOD)",
        "Final Sketch Approval (HOD)", "Requires Update", "Items Updated",
        "Attach Image", "Image QC", "Approved", "Customer Approval", "Cancelled"
    ]

    state_counts = {}
    for order in orders:
        state = order.get("workflow_state")
        if state:
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
            "datasets": [{"name": "Order Count", "values": values}],
        },
        "type": "bar",
        "barOptions": {"stacked": False},
    }



def get_report_summary(data):
    total_orders = len(set(order.get("name") for order in data if order.get("name")))

    summary = [
        {"label": "Total Sketch Orders", "value": total_orders, "indicator": "Orange"},
        {"label": "Assigned Quantity", "value": sum(order.get("assigned_qty", 0) or 0 for order in data), "indicator": "Blue"},
        {"label": "Approved Rough Sketches", "value": sum(order.get("aproved_rough", 0) or 0 for order in data), "indicator": "Green"},
        {"label": "Rejected Rough Sketches", "value": sum(order.get("rejected_rough", 0) or 0 for order in data), "indicator": "Red"},
        {"label": "Approved Final Sketches", "value": sum(order.get("aproved_final", 0) or 0 for order in data), "indicator": "Green"},
        {"label": "Rejected Final Sketches", "value": sum(order.get("reject_final", 0) or 0 for order in data), "indicator": "Red"},
    ]
    
    return summary


