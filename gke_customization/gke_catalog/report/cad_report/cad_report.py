import frappe
from datetime import datetime
from frappe.utils import now_datetime, get_datetime
import json

def execute(filters=None):
    current_user = frappe.session.user
    restricted_users = ["khushal_r@gkexport.com","ashish_m@gkexport.com","rahul_d@gkexport.com","kaushik_g@gkexport.com","chandan_d@gkexport.com","soumaya_d@gkexport.com"]

    apply_restrictions = current_user in restricted_users

    relevant_order_names = []
    assigned_by_map = {}

    if apply_restrictions:
        created_order_names = frappe.get_all(
            "Order",
            filters={"owner": current_user, "docstatus": ["<", 2]},
            pluck="name"
        )

        assigned_to_me = frappe.get_all(
            "ToDo",
            filters={"reference_type": "Order", "status": ["!=", "Cancelled"], "allocated_to": current_user},
            fields=["reference_name", "owner"]
        )
        assigned_by_me = frappe.get_all(
            "ToDo",
            filters={"reference_type": "Order", "status": ["!=", "Cancelled"], "owner": current_user},
            fields=["reference_name", "owner"]
        )

        todo_order_names = set()
        for row in assigned_to_me + assigned_by_me:
            todo_order_names.add(row.reference_name)
            if row.reference_name not in assigned_by_map:
                assigned_by_map[row.reference_name] = set()
            assigned_by_map[row.reference_name].add(row.owner)

        relevant_order_names = list(set(created_order_names).union(todo_order_names))

        if not relevant_order_names:
            return [], [], None, {}, []

    # Build order filters
    order_filters = {}
    if apply_restrictions:
        order_filters["name"] = ["in", relevant_order_names]

    # Apply incoming filters
    if filters.get("order_id"):
        user_selected_orders = filters["order_id"]
        if apply_restrictions:
            filtered_order_ids = list(set(user_selected_orders) & set(relevant_order_names))
            if not filtered_order_ids:
                return [], [], None, {}, []
            order_filters["name"] = ["in", filtered_order_ids]
        else:
            order_filters["name"] = ["in", user_selected_orders]

    if filters.get("start_date") and filters.get("end_date"):
        order_filters["order_date"] = ["between", [filters["start_date"], filters["end_date"]]]

    if filters.get("company"):
        order_filters["company"] = filters["company"] if isinstance(filters["company"], str) else ["in", filters["company"]]

    if filters.get("customer"):
        order_filters["customer_code"] = filters["customer"] if isinstance(filters["customer"], str) else ["in", filters["customer"]]

    if filters.get("setting_type"):
        order_filters["setting_type"] = filters["setting_type"] if isinstance(filters["setting_type"], str) else ["in", filters["setting_type"]]

    if filters.get("status"):
        order_filters["workflow_state"] = filters["status"] if isinstance(filters["status"], str) else ["in", filters["status"]]

    if filters.get("workflow_type"):
        order_filters["workflow_type"] = filters["workflow_type"] if isinstance(filters["workflow_type"], str) else ["in", filters["workflow_type"]]

    if filters.get("designer_branch"):
        designers_in_branch = frappe.get_all(
            "Employee",
            filters={"branch": filters["designer_branch"]},
            pluck="name"
        )
        if designers_in_branch:
            orders_with_matching_designers = frappe.get_all(
                "Designer Assignment - CAD",
                filters={"designer": ["in", designers_in_branch]},
                pluck="parent"
            )
            if orders_with_matching_designers:
                if "name" in order_filters:
                    order_filters["name"] = ["in", list(set(order_filters["name"][1]) & set(orders_with_matching_designers))]
                else:
                    order_filters["name"] = ["in", orders_with_matching_designers]
            else:
                return [], [], None, {}, []
        else:
            return [], [], None, {}, []
    # Fetch order data
    data = frappe.get_all(
        "Order",
        filters=order_filters,
        fields=["name", "owner", "_assign", "workflow_state", "company", "branch", "order_type",
                "order_date", "delivery_date", "updated_delivery_date", "modified"]
    )

    now = now_datetime()
    for row in data:
        row["assigned_by"] = ", ".join(assigned_by_map.get(row.name, [])) if apply_restrictions else ""
        row["_assign"] = row.get("_assign") or ""
        row["view_details"] = f"""<button class='btn btn-sm btn-primary view-assignment-btn' data-order="{row['name']}">View Details</button>"""
        row["workflow_duration_button"] = f"""<button class='btn btn-sm btn-primary view-workflow-btn' data-order="{row['name']}">Workflow Duration</button>"""

        if row.get("modified"):
            modified_dt = get_datetime(row["modified"])
            duration = now - modified_dt
            row["status_duration"] = f"{duration.days}d {duration.seconds // 3600}h {(duration.seconds % 3600) // 60}m"
        else:
            row["status_duration"] = ""

        designer_ids = frappe.get_all(
            "Designer Assignment - CAD",
            filters={"parent": row["name"], "parentfield": "designer_assignment"},
            pluck="designer"
        )
        if designer_ids:
            employee_names = frappe.get_all(
                "Employee",
                filters={"name": ["in", designer_ids]},
                fields=["employee_name"]
            )
            row["designer_name"] = ", ".join(emp["employee_name"] for emp in employee_names)
            row["assigned_to_dept"] = frappe.db.get_value("Employee", designer_ids[0], "department") or ""
        else:
            row["designer_name"] = ""
            row["assigned_to_dept"] = ""

        bom_ids = frappe.get_all(
            "Designer Assignment - CAD",
            filters={"parent": row["name"], "parentfield": "bom_assignment"},
            pluck="designer"
        )
        if bom_ids:
            employee_names = frappe.get_all(
                "Employee",
                filters={"name": ["in", bom_ids]},
                fields=["employee_name"]
            )
            row["bom_name"] = ", ".join(emp["employee_name"] for emp in employee_names)
        else:
            row["bom_name"] = ""

        result_rows = []

        todos = frappe.get_all(
        "ToDo",
        filters={"reference_type": "Order", "reference_name": row.name, "status": ["!=", "Cancelled"]},
        fields=["owner", "allocated_to", "creation"],
        order_by="creation asc"
    )


        if todos:
           row["assigned_to"] = ", ".join(set(todo["allocated_to"] for todo in todos if todo.get("allocated_to")))
           row["assigned_by"] = ", ".join(set(todo["owner"] for todo in todos if todo.get("owner")))
           row["assigned_on"] = ", ".join(set(todo["creation"].strftime("%Y-%m-%d %H:%M") for todo in todos if todo.get("creation")))
        else:
           row["assigned_to"] = ""
           row["assigned_by"] = ""
           row["assigned_on"] = ""

    # total_orders = sum(1 for o in data if o["workflow_state"] != "Approved")
    total_orders = len(data)
    unassigned_orders = sum(1 for o in data if o["workflow_state"] == "Draft")
    assigned_orders = sum(1 for o in data if o["workflow_state"] == "Assigned")
    other_orders = total_orders - unassigned_orders - assigned_orders


    # report_summary = get_report_summary(total_orders, unassigned_orders, other_orders, approved_orders)
    report_summary = get_report_summary(
    total_orders, unassigned_orders, assigned_orders, orders=data, filters=filters
)

    chart = get_chart_data(data)

    # Define report columns
    columns = [
        {"label": "Order ID", "fieldname": "name", "fieldtype": "Link", "options": "Order"},
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 190},
        # {"label": "Branch", "fieldname": "branch", "fieldtype": "Data", "width": 170},
        {"label": "Order Type", "fieldname": "order_type", "fieldtype": "Data", "width": 100},
        {"label": "Order Date", "fieldname": "order_date", "fieldtype": "Date", "width": 130},
        # {"label": "Assigned Details", "fieldname": "view_details", "fieldtype": "HTML"},
        {"label": "Assigned By", "fieldname": "assigned_by", "fieldtype": "Data","width":190},
        {"label": "Assigned To", "fieldname": "assigned_to", "fieldtype": "Data","width":190},
        {"label": "Assigned On", "fieldname": "assigned_on", "fieldtype": "Data","width":190},
        {"label": "Assigned to Deptartment", "fieldname": "assigned_to_dept", "fieldtype": "Data", "width": 240},
        {"label": "Designer Assignment", "fieldname": "designer_name", "fieldtype": "Data", "width": 250},
        {"label": "Workflow State", "fieldname": "workflow_state", "fieldtype": "Data", "width": 200},
        {"label": "Status Date Time", "fieldname": "modified", "fieldtype": "Datetime", "width": 180},
        {"label": "Status Duration", "fieldname": "status_duration", "fieldtype": "Data", "width": 150},
        {"label": "Delivery Date", "fieldname": "delivery_date", "fieldtype": "HTML", "width": 160},
        # {"label": "Updated Delivery Date", "fieldname": "updated_delivery_date", "fieldtype": "HTML", "width": 200},
    ]

    return columns, data, None, chart, report_summary




def get_chart_data(orders):
    workflow_order = [
        "Draft", "Assigned", "Assigned-On-Hold", "Designing", "Update Designer",
        "Designing- On-Hold", "Sent to QC", "Sent to QC-On-Hold", "Update Item",
        "Update BOM", "BOM QC", "BOM QC- On- Hold", "Approved",
        "On-Hold", "Cancelled", "Rejected",
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
            "datasets": [{"name": "Order Count", "values": values}],
        },
        "type": "bar",
        "barOptions": {"stacked": False},
    }



def get_report_summary(total, unassigned, assigned, orders=None, filters=None):
    from frappe import session

    restricted_users = [
         "khushal_r@gkexport.com", "ashish_m@gkexport.com",
        "rahul_d@gkexport.com", "kaushik_g@gkexport.com", "chandan_d@gkexport.com",
        "soumaya_d@gkexport.com"
    ]

    summary = [
        {"value": total, "indicator": "Blue", "label": "Total CAD", "datatype": "Int"},
        {"value": unassigned, "indicator": "Red" if unassigned > 0 else "Green", "label": "Unassigned CAD", "datatype": "Int"},
        {"value": assigned, "indicator": "Green", "label": "Assigned CAD", "datatype": "Int"},
    ]

    if session.user not in restricted_users and orders:
        user_summary = get_fixed_employee_summary(orders)
        summary.extend(user_summary)

    return summary


def get_fixed_employee_summary(orders):
    import json

    target_employees = {
        "rahul_d@gkexport.com": "Rahul D",
        "soumaya_d@gkexport.com": "Soumaya D",
        "chandan_d@gkexport.com": "Chandan D",
        # "poonam_n@gkexport.com": "Poonam N",
        "kaushik_g@gkexport.com": "Kaushik G",
        "khushal_r@gkexport.com": "Khushal R",
        "ashish_m@gkexport.com": "Ashish M"
    }

    counts = {label: 0 for label in target_employees.values()}

    user_order_map = {user: set() for user in target_employees.keys()}

    for order in orders:
        order_name = order["name"]
        
        # 1. Created by user
        owner = order.get("owner")
        if owner in target_employees:
            user_order_map[owner].add(order_name)

        # 2. Assigned in _assign field
        _assign = order.get("_assign")
        if _assign:
            try:
                assigned_users = json.loads(_assign)
                for user in assigned_users:
                    if user in target_employees:
                        user_order_map[user].add(order_name)
            except Exception:
                pass

        # 3 & 4. ToDos related to this order
        todos = frappe.get_all(
            "ToDo",
            filters={"reference_type": "Order", "reference_name": order_name, "status": ["!=", "Cancelled"]},
            fields=["allocated_to", "owner"]
        )
        for todo in todos:
            allocated_to = todo.get("allocated_to")
            owner = todo.get("owner")

            if allocated_to in target_employees:
                user_order_map[allocated_to].add(order_name)
            if owner in target_employees:
                user_order_map[owner].add(order_name)

    for user, orders_set in user_order_map.items():
        label = target_employees[user]
        counts[label] = len(orders_set)

    summary = []
    for label, count in counts.items():
        summary.append({
            "value": count,
            "indicator": "Blue",
            "label": label,
            "datatype": "Int"
        })

    return summary
