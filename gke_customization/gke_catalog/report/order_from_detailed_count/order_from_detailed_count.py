# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
import urllib.parse
import json
from datetime import datetime, timedelta

import frappe.utils

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)

    message = get_message()

    return columns, data,message

def get_columns():
    return [
        {"fieldname": "orderform_id", "label": "Order Form ID", "fieldtype": "Data", "width": 150,"sticky":True},
        {"fieldname": "company", "label": "Company", "fieldtype": "Data", "options": "Company", "width": 250},
        {"fieldname": "branch", "label": "Branch", "fieldtype": "Link", "options": "Branch", "width": 150},
        {"fieldname": "customer", "label": "Customer", "fieldtype": "Data", "width": 150},   
        {"label": "Customer PO", "fieldname": "po_no", "fieldtype": "Data", "width": 180}, 
        {"label": "Order Type", "fieldname": "order_type", "fieldtype": "Data", "width": 150},
        {"label": "Order Count", "fieldname": "order_count", "fieldtype": "Data", "width": 150},
        {"fieldname": "no_of_orders", "label": "No. of Pcs", "fieldtype": "Data", "width": 150},
        {"fieldname": "design_type", "label": "Design Type", "fieldtype": "Data", "width": 150},
        {"label": "Diamond Quality", "fieldname": "diamond_quality", "fieldtype": "Data", "width": 180},
        {"fieldname": "order_date", "label": "Order Date", "fieldtype": "Date", "width": 150},
        {"fieldname": "created_datetime", "label": "Created Date/Time", "fieldtype": "Datetime", "width": 180},
        {"fieldname": "order_form_creator", "label": "Order Form Creator", "fieldtype": "Data", "width": 200},
        {"fieldname": "employee", "label": "Employee", "fieldtype": "Data", "width": 200},
        {"fieldname": "department", "label": "Department", "fieldtype": "Data", "width": 200},
        {"fieldname": "designation", "label": "Designation", "fieldtype": "Data", "width": 200},
        {"fieldname": "assigned_to_dept", "label": "Assigned To Dept", "fieldtype": "Data", "width": 200},
        {"fieldname": "docstatus", "label": "Document Status", "fieldtype": "Data", "width": 150},
        {"fieldname": "status", "label": "Workflow Status", "fieldtype": "Data", "width": 150},
        {"fieldname": "workflow_state", "label": "Workflow State", "fieldtype": "Data", "width": 150},
        {"fieldname": "status_datetime", "label": "Status Date/Time", "fieldtype": "Datetime", "width": 180},
        {"fieldname": "time_difference", "label": "Time Difference", "fieldtype": "Data", "width": 250},
        {"fieldname": "status_duration", "label": "Status Duration", "fieldtype": "Data", "width": 250},
        {"fieldname": "target_days", "label": "Target Days", "fieldtype": "Data", "width": 110},
       {"fieldname": "total_metal_weight", "label": "Metal Wt (g)", "fieldtype": "Data", "width": 120},
        {"fieldname": "total_diamond_weight_in_grams", "label": "Total Diamond (ct)", "fieldtype": "Data", "width": 170},
        {"fieldname": "total_gemstone_weight_in_grams", "label": "Total Gemstone (ct)", "fieldtype": "Data", "width": 180},
        {"fieldname": "total_finding_weight_per_grams", "label": "Total Finding Weight (g)", "fieldtype": "Data", "width": 200},
        {"fieldname": "other_weight_grams", "label": "Other Wt", "fieldtype": "Data", "width": 120},
        {"fieldname": "delivery_date", "label": "Delivery Date", "fieldtype": "HTML", "width": 200},
        {"label": "Updated Delivery Date", "fieldname": "updated_delivery_date", "fieldtype": "HTML", "width": 120},
    ]

def convert_seconds_to_time(seconds):
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{days} days, {hours:02} hrs:{minutes:02} mins:{secs:02} secs"

def get_data(filters):
    conditions = []

    # if filters.get("from_date") and filters.get("to_date"):
    #     conditions.append(f"DATE(ofd.creation) BETWEEN '{filters['from_date']}' AND '{filters['to_date']}'")
    

    if filters.get("from_date"):
        conditions.append(f"""ofd.order_date >= "{filters['from_date']}" """)
    if filters.get("to_date"):
        conditions.append(f"""ofd.order_date <= "{filters['to_date']}" """)

    if filters.get("order_id"):
        order_ids = "', '".join(filters["order_id"])
        conditions.append(f"ofd.name IN ('{order_ids}')")

    if filters.get("company"):
        # companies = ', '.join([f'"{company}"' for company in filters.get("company")])
        conditions.append(f"""ofd.company = "{filters['company']}" """)
    
    if filters.get("branch"):
        # branches = ', '.join([f'"{branch}"' for branch in filters.get("branch")])
        conditions.append(f"""ofd.branch = "{filters['branch']}" """)
    
    if filters.get("customer"):
        customers = ', '.join([f'"{customer}"' for customer in filters.get("customer")])
        conditions.append(f"ofd.customer_code IN ({customers})")

    if filters.get("customer_po"):
        customerspo = ', '.join([f'"{customer_po}"' for customer_po in filters.get("customer_po")])
        conditions.append(f"ofd.po_no IN ({customerspo})")
    
    # if filters.get("category"):
    #     conditions.append(f'od.category = "{filters.get("category")}"')

    if filters.get("diamond_quality"):
        conditions.append(f'ofd.diamond_quality = "{filters.get("diamond_quality")}"')

    if filters.get("status"):
        conditions.append(f"ofd.workflow_state = '{filters['status']}'")

    # if filters.get("status"):
    #     statuses = ', '.join([f'"{status}"' for status in filters.get("status")])
    #     conditions.append(f"ofd.workflow_state IN ({statuses})")

    if filters.get("docstatus"):
        conditions.append(f"""ofd.docstatus = "{filters['docstatus']}" """)
 

    conditions = " AND ".join(conditions) if conditions else ""

    query = f"""
        SELECT
            ofd.company AS company,
            ofd.branch AS branch,
            ofd.customer_code AS customer,
            ofd.po_no AS po_no,
            ofd.name AS orderform_id,
            count(distinct od.name) AS order_count,
            SUM(od.qty) AS no_of_orders,
            ofd.owner AS order_form_creator,
            e.employee AS employee,
            e.department AS department,
            e.designation AS designation,
            ofd._assign AS assigned_users,
            ofd.order_date,
            ofd.delivery_date,
            ofd.order_type,
            ofd.diamond_quality,
            od.design_type,
            ofd.creation AS created_datetime,
              CASE WHEN ofd.docstatus = 0 THEN "Draft"
                 WHEN ofd.docstatus = 1 THEN "Submitted"
                 WHEN ofd.docstatus = 2 THEN "Cancelled" END AS docstatus, 
            ofd.workflow_state AS status,
            CASE WHEN ofd.workflow_state = 'Cancelled' THEN 0
    WHEN ofd.workflow_state = 'Draft' THEN 1
    WHEN ofd.workflow_state = 'Send for Approval' THEN 2
    WHEN ofd.workflow_state = 'On Hold' THEN 3
    WHEN ofd.workflow_state = 'Approved' THEN 4
         END AS workflow_state,
            ofd.modified AS status_datetime,
            "2 Days" AS target_days,
            SUM(bm.metal_weight) AS total_metal_weight,
            SUM(bm.finding_weight_) AS total_finding_weight_per_grams,
            SUM(bm.diamond_weight) AS total_diamond_weight_in_grams,
            SUM(bm.gemstone_weight) AS total_gemstone_weight_in_grams,
            SUM(bm.other_weight) AS other_weight_grams,
            ofd.updated_delivery_date
        FROM `tabOrder Form` AS ofd
        LEFT JOIN `tabOrder Form Detail` AS od ON ofd.name = od.parent
        LEFT JOIN `tabEmployee` e ON ofd.owner = e.user_id
        LEFT JOIN `tabBOM` bm on bm.name = od.bom AND bm.bom_type = 'Template'
        WHERE 
        {conditions}
        GROUP BY ofd.name
        ORDER BY created_datetime DESC, ofd.name ASC    
    """

    data = frappe.db.sql(query, as_dict=True)

    total_seconds = 0
    total_status_seconds = 0  
    unique_customers = set()
    total_orders = len(data)
    total_diam_wt = total_metal_wt = total_gem_wt = total_find_wt = total_other_wt = 0
    total_status_duration = 0
    has_valid_status = False  

    for row in data:
        row["assigned_to_dept"] = ""
        if row.get("assigned_users"):
            assigned_users = json.loads(row["assigned_users"])
            last_assigned_user = assigned_users[-1] if assigned_users else ""
            if last_assigned_user:
                employee = frappe.db.get_value("Employee", {"user_id": last_assigned_user}, "department")
                row["assigned_to_dept"] = employee if employee else ""
                
        if row.get("updated_delivery_date"):
          if row.get("delivery_date") and row["updated_delivery_date"] != row["delivery_date"]:
            row["delivery_date"] = f"<span style='color: red; font-weight: bold;'>{row['delivery_date']}</span>"
            row["updated_delivery_date"] = f"<span style='color: green; font-weight: bold;'>{row['updated_delivery_date']}</span>"
        else:
           row["updated_delivery_date"] = "-" 

        encoded_form_name = urllib.parse.quote(row["orderform_id"])
        row["orderform_id"] = f'<a href="https://gkexport.frappe.cloud/app/order-form/{encoded_form_name}" target="_blank">{row["orderform_id"]}</a>'
        
        row["status"] = format_status(row["status"])
        created_dt = datetime.strptime(str(row["created_datetime"]), "%Y-%m-%d %H:%M:%S.%f")
        status_dt = datetime.strptime(str(row["status_datetime"]), "%Y-%m-%d %H:%M:%S.%f")
        row["created_datetime"] = created_dt.strftime("%Y-%m-%d %H:%M:%S")
        row["status_datetime"] = status_dt.strftime("%Y-%m-%d %H:%M:%S")

        row["status_duration"], exceeded = calculate_status_duration(status_dt, row["status"])
        
        if row["status_duration"] != "-":
            has_valid_status = True
        
        if exceeded:
            row["status_duration"] = f"<span style='color: red;'>{row['status_duration']}</span>"

        time_diff_seconds = int((status_dt - created_dt).total_seconds())
        total_seconds += time_diff_seconds
        row["time_difference"] = convert_seconds_to_time(time_diff_seconds)
        
        
        status_diff_seconds = int((datetime.now() - status_dt).total_seconds())
        total_status_seconds += status_diff_seconds
        row["status_difference"] = convert_seconds_to_time(status_diff_seconds)

        
        # status_duration_seconds = int((datetime.now() - status_dt).total_seconds())
        # total_status_duration += status_duration_seconds if row["status_duration"] != "-" else 0

        status_duration_seconds = int((status_dt - datetime.now()).total_seconds())
        total_status_duration += abs(int(status_duration_seconds)) if row["status_duration"] != "-" else 0

        total_diam_wt += row.get("total_diamond_weight_in_grams", 0) or 0
        total_metal_wt += row.get("total_metal_weight", 0) or 0
        total_gem_wt += row.get("total_gemstone_weight_in_grams", 0) or 0
        total_find_wt += row.get("total_finding_weight_per_grams", 0) or 0
        total_other_wt += row.get("other_weight_grams", 0) or 0

        if row["customer"]:
            unique_customers.add(row["customer"])

    
    total_row = {
        "customer": f"<b><span style='color: green;'>Customer: {len(unique_customers)}</span></b>",
        "orderform_id": f"<b><span style='color: green;'>Total Orders: {total_orders}</span></b>",
        "time_difference": f"<b><span style='color: green;'>{convert_seconds_to_time(total_seconds)}</span></b>",
        "status_difference": f"<b><span style='color: green;'>{convert_seconds_to_time(total_status_seconds)}</span></b>",
        "total_diamond_weight_in_grams": f"<b><span style='color: green;'>Total: {round(total_diam_wt,2)}</span></b>",
        "total_metal_weight": f"<b><span style='color: green;'>Total: {round(total_metal_wt, 2)}</span></b>",
        "total_gemstone_weight_in_grams": f"<b><span style='color: green;'>Total: {round(total_gem_wt,2)}</span></b>",
        "total_finding_weight_per_grams": f"<b><span style='color: green;'>Total: {round(total_find_wt,2)}</span></b>",
        "other_weight_grams": f"<b><span style='color: green;'>Total: {round(total_other_wt,2)}</span></b>",
        "status_duration": f"<b><span style='color: green;'>Total Status Duration: {convert_seconds_to_time(total_status_duration)if has_valid_status else '0'}</span></b>",  
    }
    
    data.append(total_row)

    avg_row = {
        "total_diamond_weight_in_grams": f"<b><span style='color: green;'>Avg / Order: {round(total_diam_wt / total_orders, 2) if total_orders else 0}</span></b>",
        "total_metal_weight": f"<b><span style='color: green;'>Avg / Order: {round(total_metal_wt / total_orders, 2) if total_orders else 0}</span></b>",
        "total_gemstone_weight_in_grams": f"<b><span style='color: green;'>Avg / Order: {round(total_gem_wt / total_orders, 2) if total_orders else 0}</span></b>",
        "total_finding_weight_per_grams": f"<b><span style='color: green;'>Avg / Order: {round(total_find_wt / total_orders, 2) if total_orders else 0}</span></b>",
        "other_weight_grams": f"<b><span style='color: green;'>Avg / Order: {round(total_other_wt / total_orders, 2) if total_orders else 0}</span></b>",
        "time_difference": f"<b><span style='color: green;'>Avg / Order: {convert_seconds_to_time(total_seconds // total_orders) if total_orders else '0'}</span></b>",
        "status_duration": f"<b><span style='color: green;'>Avg / Order: {convert_seconds_to_time(total_status_duration // total_orders) if total_orders and  has_valid_status else '0'}</span></b>",  
    }
    data.append(avg_row)

    return data


def calculate_status_duration(modified_dt, status):
    if status in ["<span style='color:green; font-weight:bold;'>Approved</span>", 
                  "<span style='color:inherit; font-weight:bold;'>Cancelled</span>"]:
        return "-", False
    # current_dt = datetime.now()
    current_dt = frappe.utils.now_datetime()
    days_count = 0
    temp_dt = modified_dt

    while temp_dt < current_dt:
        temp_dt += timedelta(days=1)
        if temp_dt.weekday() != 6:  
            days_count += 1

    time_difference = current_dt - modified_dt
    time_str = convert_seconds_to_time(time_difference.total_seconds())
    # time_str = convert_seconds_to_time(status_duration.total_seconds())

    exceeded = days_count > 2 and status not in ["<span style='color:green; font-weight:bold;'>Approved</span>", "<span style='color:inherit; font-weight:bold;'>Cancelled</span>"]
    

    return time_str, exceeded

def convert_seconds_to_time(seconds):
    days, remainder = divmod(int(seconds), 86400)  
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{days} days, {hours} hrs: {minutes} mins: {secs} secs"

def get_message():

    return """<span class="indicator" style="font-weight: bold; font-size: 15px;">
        Note : &nbsp;&nbsp;
        </span>
        <span class="indicator red" style="font-size: 15px;">
        The standard deadline for this process is 2 days.
        </span>
        &nbsp;&nbsp;&nbsp;
        <span class="indicator blue" style="font-size: 15px;margin-left: 155px;">
        Time difference = Created date-time - Status date-time.
        </span>
        <br>
        &nbsp;
        <span class="indicator red" style="font-size: 15px; margin-left: 65px;">
        Delivery Date turns red if delivery date is updated.
        </span>
        <span class="indicator blue" style="font-size: 15px; margin-left: 160px;">
        Status Duration = Status date-time - Current date-time.
        </span>
        <br>
        <span class="indicator yellow" style="font-size: 15px; margin-left: 72px;">
        Order Count: No. of items in Order
        </span>
        <span class="indicator yellow" style="font-size: 15px; margin-left: 270px;">
        No. of Pcs: Quantity of items in Order
        </span>
        <br>
        <span class="indicator green" style="font-size: 15px; margin-left: 72px;">
        Worklflow State:- Cancelled: 0,  &nbsp;  Draft : 1,  &nbsp; Send For Approval  : 2,   &nbsp; On Hold : 3,  &nbsp;  Approved : 4
        </span>
"""


def format_status(status):
    status_colors = {
        "Draft": "red",
        "Approved": "green"
    }
    return f"<span style='color:{status_colors.get(status, 'inherit')}; font-weight:bold;'>{status}</span>"