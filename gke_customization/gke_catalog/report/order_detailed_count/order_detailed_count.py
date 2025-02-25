# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
import urllib.parse
import json
from datetime import datetime,timedelta

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    message = get_message()
    return columns, data,message



def get_columns():
    return [
        {"label": "Order ID", "fieldname": "orderform_id", "fieldtype": "Data", "width": 180},
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 220},
        {"label": "Branch", "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 180},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "HTML", "width": 180},
        {"label": "Customer PO", "fieldname": "po_no", "fieldtype": "Data", "width": 180},
        {"label": "Order Type", "fieldname": "order_type", "fieldtype": "Data", "width": 150},    
        {"label": "No.of Pcs", "fieldname": "qty", "fieldtype": "Data", "width": 110},
        {"label": "Diamond Quality", "fieldname": "diamond_quality", "fieldtype": "Data", "width": 180},
        {"label": "Order Date", "fieldname": "order_date", "fieldtype": "Date", "width": 120},
        {"label": "Created Date/Time", "fieldname": "created_datetime", "fieldtype": "Data", "width": 180},
        {"fieldname": "order_form_creator", "label": "Order Creator", "fieldtype": "Data", "width": 200},
        {"fieldname": "employee", "label": "Employee", "fieldtype": "Data", "width": 200},
        {"fieldname": "department", "label": "Department", "fieldtype": "Data", "width": 200},
        {"fieldname": "designation", "label": "Designation", "fieldtype": "Data", "width": 200},      
        # {"label": "Assigned To", "fieldname": "assigned_users", "fieldtype": "Data", "width": 200},
        {"fieldname": "assigned_to_dept", "label": "Assigned To Dept", "fieldtype": "Data", "width": 200},
        {"label": "Status", "fieldname": "status", "fieldtype": "HTML", "width": 190},
        {"label": "Workflow State", "fieldname": "workflow_state1", "fieldtype": "Data", "width": 120},
        {"label": "Status Date-Time", "fieldname": "status_datetime", "fieldtype": "Data", "width": 180}, 
        {"label": "Time Difference", "fieldname": "time_difference", "fieldtype": "Data", "width": 230},
        {"label": "Status Duration", "fieldname": "status_duration", "fieldtype": "Data", "width": 250},
        {"label": "Target Days", "fieldname": "target_days", "fieldtype": "Data", "width": 110},     
        {"fieldname": "total_metal_weight", "label": "Metal Wt (g)", "fieldtype": "Data", "width": 120},
        {"fieldname": "total_diamond_weight_in_grams", "label": "Total Diamond (ct)", "fieldtype": "Data", "width": 170},
        {"fieldname": "total_gemstone_weight_in_grams", "label": "Total Gemstone (ct)", "fieldtype": "Data", "width": 180},
        {"fieldname": "total_finding_weight_per_grams", "label": "Total Finding Weight (g)", "fieldtype": "Data", "width": 200},
        {"fieldname": "other_weight_grams", "label": "Other Wt", "fieldtype": "Data", "width": 120},
        {"label": "Delivery Date", "fieldname": "delivery_date", "fieldtype": "HTML", "width": 120},
        {"label": "Updated Delivery Date", "fieldname": "updated_delivery_date", "fieldtype": "HTML", "width": 120},
    ]

def get_data(filters):
    conditions = []

    # if filters.get("from_date") and filters.get("to_date"):
    #     conditions.append(f"DATE(od.creation) BETWEEN '{filters['from_date']}' AND '{filters['to_date']}'")
    
    if filters.get("from_date"):
        conditions.append(f"""od.order_date >= "{filters['from_date']}" """)
    if filters.get("to_date"):
        conditions.append(f"""od.order_date <= "{filters['to_date']}" """)

    if filters.get("order_id"):
        order_ids = "', '".join(filters["order_id"])
        conditions.append(f"odf.name IN ('{order_ids}')")

    if filters.get("company"):
        companies = ', '.join([f'"{company}"' for company in filters.get("company")])
        conditions.append(f"od.company IN ({companies})")
    
    if filters.get("branch"):
        branches = ', '.join([f'"{branch}"' for branch in filters.get("branch")])
        conditions.append(f"od.branch IN ({branches})")
    
    if filters.get("customer"):
        customers = ', '.join([f'"{customer}"' for customer in filters.get("customer")])
        conditions.append(f"od.customer_code IN ({customers})")

    if filters.get("customer_po"):
        customerspo = ', '.join([f'"{customer_po}"' for customer_po in filters.get("customer_po")])
        conditions.append(f"od.po_no IN ({customerspo})")
    
    if filters.get("diamond_quality"):
        conditions.append(f'od.diamond_quality = "{filters.get("diamond_quality")}"')

    if filters.get("status"):
        conditions.append(f"od.workflow_state = '{filters['status']}'")

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    query = f"""
        SELECT
            od.name AS orderform_id,
            od.company AS company,
            od.branch AS branch, 
            od.customer_code AS customer,
            od.po_no AS po_no,
            od.order_type,
            od.qty AS qty,
            od.diamond_quality AS diamond_quality,
            od.design_type,
            od.order_date, 
            od.creation AS created_datetime,      
            od.owner AS order_form_creator,
            e.employee AS employee,
            e.department AS department,
            e.designation AS designation,
            od._assign AS assigned_users,  
            od.workflow_state AS status,
            CASE 
    WHEN od.workflow_state = 'Draft' THEN 1
    WHEN od.workflow_state = 'Update Item' THEN 2
    WHEN od.workflow_state = 'Assigned' THEN 3
    WHEN od.workflow_state = 'Assigned - On-Hold' THEN 4
    WHEN od.workflow_state = 'Designing' THEN 5
    WHEN od.workflow_state = 'Update Designer' THEN 6
    WHEN od.workflow_state = 'Designing - On-Hold' THEN 7
    WHEN od.workflow_state = 'Sent to QC' THEN 8
    WHEN od.workflow_state = 'Sent to QC-On-Hold' THEN 9
    WHEN od.workflow_state = 'Customer Approval' THEN 10
    WHEN od.workflow_state = 'Reupdate BOM' THEN 11
    WHEN od.workflow_state = 'Update BOM' THEN 12
    WHEN od.workflow_state = 'BOM QC - On-Hold' THEN 13
    WHEN od.workflow_state = 'Customer Approval' THEN 14
    WHEN od.workflow_state = 'Reupdate BOM' THEN 15
    WHEN od.workflow_state = 'Approved' THEN 16
    WHEN od.workflow_state = 'On-Hold' THEN 17
    WHEN od.workflow_state = 'Rejected' THEN 18
    WHEN od.workflow_state = 'Cancelled' THEN 0
    ELSE NULL
END AS workflow_state1,

            
            od.modified AS status_datetime,
            "2 Days" AS target_days,
            CAST(bm.metal_weight AS DECIMAL(10,4)) AS total_metal_weight,
            CAST(bm.finding_weight_ AS DECIMAL(10,4)) AS total_finding_weight_per_grams,
            bm.diamond_weight AS total_diamond_weight_in_grams,
            bm.gemstone_weight AS total_gemstone_weight_in_grams,
            CAST(bm.other_weight AS DECIMAL(10,4)) AS other_weight_grams,
            odf.delivery_date AS delivery_date,
            odf.updated_delivery_date
        FROM `tabOrder` AS od
        LEFT JOIN `tabOrder Form` AS odf on od.cad_order_form = odf.name
        LEFT JOIN `tabEmployee` e ON od.owner = e.user_id
        LEFT JOIN `tabBOM` bm on bm.name = COALESCE(od.new_bom, od.bom)
        {where_clause}
        GROUP BY od.name 
        ORDER BY created_datetime DESC, od.name ASC    
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
        row["orderform_id"] = f'<a href="https://gkexport.frappe.cloud/app/order/{encoded_form_name}" target="_blank">{row["orderform_id"]}</a>'
        
        row["status"] = format_status(row["status"])
        created_dt = datetime.strptime(str(row["created_datetime"]), "%Y-%m-%d %H:%M:%S.%f")
        status_dt = datetime.strptime(str(row["status_datetime"]), "%Y-%m-%d %H:%M:%S.%f")
        row["created_datetime"] = created_dt.strftime("%Y-%m-%d %H:%M:%S")
        row["status_datetime"] = status_dt.strftime("%Y-%m-%d %H:%M:%S")
        

        # metal_wt = row["metal_weight"]
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
        "status_duration": f"<b><span style='color: green;'>Avg / Order: {convert_seconds_to_time(total_status_duration // total_orders) if total_orders and has_valid_status else '0'}</span></b>",  
    }
    data.append(avg_row)

    return data


def calculate_status_duration(modified_dt, status):
    if status in ["<span style='color:green; font-weight:bold;'>Approved</span>", 
                  "<span style='color:inherit; font-weight:bold;'>Cancelled</span>"]:
        return "-", False
    current_dt = datetime.now()
    days_count = 0
    temp_dt = modified_dt
    
    while temp_dt < current_dt:
        temp_dt += timedelta(days=1)
        if temp_dt.weekday() != 6:  
            days_count += 1
    
    time_difference = current_dt - modified_dt
    time_str = convert_seconds_to_time(time_difference.total_seconds())
    
    
    # exceeded = days_count > 2 and status not in ["Approved", "Cancelled"]
    exceeded = days_count > 2 and status not in ["<span style='color:green; font-weight:bold;'>Approved</span>", "<span style='color:inherit; font-weight:bold;'>Cancelled</span>"]

    
    
    if exceeded:
        return f"<span style='color: red;'>{time_str}</span>", True
    return time_str, False



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
        <span class="indicator yellow" style="font-size: 15px; margin-left: 73px;">
        No. of Pcs: Quantity of items in Order</span>
        <br>
      <span style="color: green; font-size: 27px; margin-right: 5px; line-height: 0;">•</span>
        <span style="font-size: 15px;">Total Number of Workflow State in this process is 19 (1-Draft, 2-Update Item, 3-Assigned, 
        4-Assigned-On-Hold, 5-Designing, 6-Update Designer, 
        7-Designing- On-Hold, 8-Sent to QC, 9-Sent to QC-On-Hold, 
        10-Customer Approval, 11-Reupdate BOM, 12-Update BOM, 13-BOM QC- On- Hold, 14-Customer Approval, 15 - Reupdate BOM, 16-Approved,17-On-Hold, 18-Rejected   0-Cancelled)
       </span>
        

"""


def format_status(status):
    status_colors = {
        "Draft": "red",
        "Approved": "green"
    }
    return f"<span style='color:{status_colors.get(status, 'inherit')}; font-weight:bold;'>{status}</span>"
