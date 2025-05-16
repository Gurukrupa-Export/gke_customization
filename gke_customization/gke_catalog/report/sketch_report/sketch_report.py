# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
import re
from frappe.utils import flt

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart_data = get_chart_data(data)
	summary = get_report_summary(data)

	return columns, data, None, chart_data,summary

def get_columns():
	return [
        {"label": "Sketch Order Form ID", "fieldname": "sketch_order_form", "fieldtype": "Link", "options": "Sketch Order Form", "width": 230},
		{"label": "Sketch Order ID", "fieldname": "name", "fieldtype": "Link", "options": "Sketch Order", "width": 170},
        # {"label": "Workflow State", "fieldname": "workflow_state", "fieldtype": "Data", "width": 150},
		{"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 190},
		{"label": "Created Branch", "fieldname": "branch", "fieldtype": "Data", "width": 170},
        {"label": "Created By", "fieldname": "owner", "fieldtype": "Data", "width": 170},
		{"label": "Working Branch", "fieldname": "working_branch", "fieldtype": "Data", "width": 170},
		{"label": "Department", "fieldname": "department", "fieldtype": "Data", "width": 170},
		{"label": "Creation Date", "fieldname": "creation", "fieldtype": "Date", "width": 170},
		{"label": "Design Type", "fieldname": "design_type", "fieldtype": "Data", "width": 170},
		{"label": "Order Type", "fieldname": "order_type", "fieldtype": "Data", "width": 150},
		{"label": "Category", "fieldname": "category", "fieldtype": "Data", "width": 170},
		{"label": "Sub Category", "fieldname": "subcategory", "fieldtype": "Data", "width": 170},
		{"label": "Metal Target", "fieldname": "metal_target", "fieldtype": "Data", "width": 170},
		{"label": "Diamond Target", "fieldname": "diamond_target", "fieldtype": "Data", "width": 170},
		{"label": "Is Metal Target Range", "fieldname": "is_metal_target_range", "fieldtype": "Data", "width": 170},
		{"label": "Is Diamond Target Range", "fieldname": "is_diamond_target_range", "fieldtype": "Data", "width": 170},
		{"label": "Designer", "fieldname": "designer_name", "fieldtype": "Data", "width": 170},
		{"label": "Assigned Sketch Qty", "fieldname": "assigned_qty", "fieldtype": "Data", "width": 180},
		{"label": "Approved Rough Sketch", "fieldname": "aproved_rough", "fieldtype": "Data", "width": 180},
		{"label": "Rejected Rough Sketch", "fieldname": "rejected_rough", "fieldtype": "Data", "width": 180},
		{"label": "Approved Final Sketch", "fieldname": "aproved_final", "fieldtype": "Data", "width": 180},
		{"label": "Rejected Final Sketch", "fieldname": "reject_final", "fieldtype": "Data", "width": 180},
		{"label": "Approx Gold Wt", "fieldname": "gold_wt_approx", "fieldtype": "Data", "width": 130},
		{"label": "Approx Diamond Wt", "fieldname": "diamond_wt_approx", "fieldtype": "Data", "width": 160},
      
	]

import re
## Cleaning of non-numeric characters (here range values) from a value and safely converts it to float.

def clean_and_convert_to_float(value):
    try:
        cleaned_value = re.sub(r'[^0-9.-]', '', str(value))
        if cleaned_value:
            return flt(cleaned_value)
        else:
            return 0.0
    except ValueError:
        return 0.0
    
## Builds a mapping of (parent, designer) to aggregated field values, handling both numeric and range string data. 

def build_designer_map(child_table, parent_field, fields):
    records = frappe.get_all(child_table, filters={parent_field: ["!=", ""]}, fields=[parent_field, "designer_name"] + fields)
    result = {}

    for rec in records:
        key = (rec[parent_field], rec["designer_name"])

        for field in fields:
            value = rec.get(field, 0)

            if isinstance(value, str) and '-' in value:
                if key not in result:
                    result[key] = {field: [value]}
                else:
                    if field not in result[key] or not isinstance(result[key][field], list):
                        result[key][field] = [value]
                    else:
                        result[key][field].append(value)
            else:
                if key not in result:
                    result[key] = {field: clean_and_convert_to_float(value)}
                else:
                    current_value = result[key].get(field, 0)
                    if isinstance(current_value, list):
                        result[key][field].append(str(value))
                    else:
                        result[key][field] = current_value + clean_and_convert_to_float(value)

    for designer, fields_data in result.items():
        for field, values in fields_data.items():
            if isinstance(values, list):
                result[designer][field] = ', '.join(values)

    return result


def get_data(filters=None):
    filters = filters or {}
    order_filters = {}

## user restriction dept and desgn wise

    user = frappe.session.user
    user_details = frappe.get_value("Employee", {"user_id": user}, ["status", "designation", "department"])

    if user_details and user_details[0] == "Active" and user_details[1] in ["Manager", "Data Analyst"] and user_details[2] in ["Product Development - GEPL", "Sketch - GEPL"]:

        employee = frappe.get_value("Employee", {"user_id": user}, "name")
        reportees = frappe.get_all("Employee", filters={"reports_to": employee}, pluck="name")
        reportees.append(employee)

        order_filters["owner"] = ["in", reportees]
    else:
        pass

## filters:

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

        created_orders = frappe.get_all("Sketch Order", filters={
        "owner": ["in", selected_users]
    }, pluck="name")

 ### Adding the orders of employees who have created orders and have there reporting manager with above dept and desgn    

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



        combined_order_names = list(set(created_orders + reportee_orders))

        if not combined_order_names:
            return []

        order_filters["name"] = ["in", combined_order_names]
    
    
    ### Fetch all Sketch Orders with the applied filters (no Designer Assignment required)
    sketch_orders = frappe.get_all("Sketch Order", filters=order_filters, fields=[
        "name", "sketch_order_form", "company", "branch", "department", "creation", "design_type", "workflow_state",
        "order_type", "category", "subcategory", "metal_target", "diamond_target",
        "is_metal_target_range", "is_diamond_target_range", "owner"
    ])

    ### Fetch Designer Assignments that correspond to the fetched Sketch Orders
    so_map = {so["name"]: so for so in sketch_orders}
    so_names = list(so_map.keys())

    designer_assignments = frappe.get_all("Designer Assignment", filters={"parent": ["in", so_names]}, fields=[
        "parent", "designer_name", "count_1", "designer"
    ])

    ### Build maps for approvals and targets
    rough_sketch_map = build_designer_map("Rough Sketch Approval", "parent", ["approved", "reject"])
    final_sketch_map = build_designer_map("Final Sketch Approval HOD", "parent", ["approved", "reject"])
    final_cmo_map = build_designer_map("Final Sketch Approval CMO", "parent", ["gold_wt_approx", "diamond_wt_approx"])
    
    ### Map designer to their branch
    designer_ids = list(set(da["designer"] for da in designer_assignments))
    designer_branch_map = {}
    if designer_ids:
        employees = frappe.get_all(
            "Employee", filters={"name": ["in", designer_ids]},
            fields=["name", "employee_name", "branch", "department", "designation"]
        )
        designer_branch_map = {emp.name: emp.branch for emp in employees}
    
    ### Fetch branches of owners (creator of Sketch Orders)
    owners = list(set(so["owner"] for so in sketch_orders))
    owner_branch_map = {}
    if owners:
        owner_employees = frappe.get_all("Employee", filters={"user_id": ["in", owners]}, fields=["user_id", "branch"])
        owner_branch_map = {emp.user_id: emp.branch for emp in owner_employees}

    
    total_fields = [
        "metal_target", "diamond_target", "assigned_qty",
        "aproved_rough", "rejected_rough", "aproved_final",
        "reject_final", "gold_wt_approx", "diamond_wt_approx"
    ]

    # Tracking totals and distinct counts
    totals = {field: 0 for field in total_fields}
    distinct_order_forms = set()
    distinct_order_ids = set()
    distinct_sketch_orders = set()
    distinct_sketch_forms = set()
    distinct_order_types = set()
    distinct_designers = set()

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
                    "gold_wt_approx": flt(final_cmo_map.get(key, {}).get("gold_wt_approx") or 0, 3),
                    "diamond_wt_approx": flt(final_cmo_map.get(key, {}).get("diamond_wt_approx") or 0, 3),
                    "is_metal_target_range": '<span style="color:green;font-weight:bold; font-size:16px;">&#10004;</span>' if so.get("is_metal_target_range") == 1 else "",
                    "is_diamond_target_range": '<span style="color:green;font-weight:bold; font-size:16px;">&#10004;</span>' if so.get("is_diamond_target_range") == 1 else "",
                })
# S/ORD/00355-1, S/ORD/00192-1
        if not any(da["parent"] == so_name for da in designer_assignments):
            data.append({
                **so,
                "branch": owner_branch_map.get(so.get("owner")),
                "working_branch": "",
                "designer_name": "",
                "assigned_qty": 0,
                "approved_rough": 0,
                "rejected_rough": 0,
                "aproved_final": 0,
                "reject_final": 0,
                "gold_wt_approx": 0,
                "diamond_wt_approx": 0,
                "is_metal_target_range": "",
                "is_diamond_target_range": "",
            })

        distinct_sketch_orders = set(row["name"] for row in data if row.get("name"))
        distinct_sketch_forms = set(row["sketch_order_form"] for row in data if row.get("sketch_order_form"))
        distinct_designers = set(row["designer_name"] for row in data if row.get("designer_name"))
        distinct_order_types = set(row["order_type"] for row in data if row.get("order_type"))

    # Append final totals row
    totals_row = {
    "assigned_qty": f"<span style='color:green;font-weight:bold; font-size:16px;'>Total: </span> {frappe.cint(sum(clean_and_convert_to_float(row.get('assigned_qty', 0)) for row in data))}",
    "aproved_rough": f"<span style='color:green;font-weight:bold; font-size:16px;'>Total: </span> {frappe.cint(sum(clean_and_convert_to_float(row.get('aproved_rough', 0)) for row in data))}",
    "rejected_rough": f"<span style='color:green;font-weight:bold; font-size:16px;'>Total: </span> {frappe.cint(sum(clean_and_convert_to_float(row.get("rejected_rough", 0)) for row in data))}",
    "aproved_final": f"<span style='color:green;font-weight:bold; font-size:16px;'>Total: </span> {frappe.cint(sum(clean_and_convert_to_float(row.get("aproved_final", 0)) for row in data))}",
    "reject_final": f"<span style='color:green;font-weight:bold; font-size:16px;'>Total: </span> {frappe.cint(sum(clean_and_convert_to_float(row.get("reject_final", 0)) for row in data))}",
    "gold_wt_approx": f"<span style='color:green;font-weight:bold; font-size:16px;'>Total: </span>{round(sum(clean_and_convert_to_float(row.get("gold_wt_approx", 0)) for row in data), 3)}",
    "diamond_wt_approx": f"<span style='color:green;font-weight:bold; font-size:16px;'>Total: </span>{round(sum(clean_and_convert_to_float(row.get("diamond_wt_approx", 0)) for row in data), 3)}",
    "metal_target": f"<span style='color:green;font-weight:bold; font-size:16px;'>Total: </span>{round(sum(clean_and_convert_to_float(row.get("metal_target", 0)) for row in data), 3)}",
    "diamond_target": f"<span style='color:green;font-weight:bold; font-size:16px;'>Total: </span>{round(sum(clean_and_convert_to_float(row.get("diamond_target", 0)) for row in data), 3)}",
    "name": f"🟢 Sketch Orders: {len(distinct_sketch_orders)}",
    "sketch_order_form": f"🟢 Sketch Order Forms: {len(distinct_sketch_forms)}",
    "designer_name": f"🟢 Designers: {len(distinct_designers)}",
    "order_type": f"🟢 Order Types: {len(distinct_order_types)}"
}

    
    data.append(totals_row)

    return data

## Creating Chart Data
def get_chart_data(orders):
    workflow_order = [
        "Draft", "Unassigned", "Assigned", "Rough Sketch Approval (HOD)",
        "Final Sketch Approval (HOD)", "Requires Update", "Items Updated",
        "Attach Image", "Image QC", "Approved", "Customer Approval", "Cancelled"
    ]
    unique_orders = {}
    for order in orders:
        name = order.get("name")
        if name:
            unique_orders[name] = order

    state_counts = {}
    for order in unique_orders.values():
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
        "show_values_on_bar": True
    }

### Summary row for the report for number cards above graph
def get_report_summary(data):
    filtered_data = [
        row for row in data
        if not (isinstance(row.get("name"), str) and "Sketch Orders" in row["name"])
    ]

    total_orders = len(set(order.get("name") for order in filtered_data if order.get("name")))

    summary = [
        {
            "label": "Total Sketch Orders",
            "value": total_orders,
            "indicator": "Orange"
        },
        {
            "label": "Assigned Quantity",
            "value": sum(
                clean_and_convert_to_float(order.get("assigned_qty", 0))
                for order in filtered_data
            ),
            "indicator": "Blue"
        },
        {
            "label": "Approved Rough Sketches",
            "value": sum(
                clean_and_convert_to_float(order.get("aproved_rough", 0))
                for order in filtered_data
            ),
            "indicator": "Green"
        },
        {
            "label": "Rejected Rough Sketches",
            "value": sum(
                clean_and_convert_to_float(order.get("rejected_rough", 0))
                for order in filtered_data
            ),
            "indicator": "Red"
        },
        {
            "label": "Approved Final Sketches",
            "value": sum(
                clean_and_convert_to_float(order.get("aproved_final", 0))
                for order in filtered_data
            ),
            "indicator": "Green"
        },
        {
            "label": "Rejected Final Sketches",
            "value": sum(
                clean_and_convert_to_float(order.get("reject_final", 0))
                for order in filtered_data
            ),
            "indicator": "Red"
        }
    ]

    return summary


