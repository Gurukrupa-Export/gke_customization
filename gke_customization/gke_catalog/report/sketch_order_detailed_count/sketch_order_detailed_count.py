import frappe
from frappe import _
from datetime import datetime, timedelta
import urllib.parse
import re

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    message = get_message()
   
    filtered_data = [row for row in data if row['status_duration'] != "-"]

    total_time_diff = calculate_total_time_diff(data)
    total_status_duration = calculate_total_status_duration(filtered_data)
    

    unique_order_count = len(set([row['form_name'] for row in data]))
    unique_customer_count = len(set([row['customer_code'] for row in data]))
    
    total_weights = calculate_total_weights(data)
    avg_weights = calculate_avg_weights(data,unique_order_count)


    total_row = get_total_row(data, total_time_diff, total_status_duration, total_weights, avg_weights, unique_order_count, unique_customer_count)
    avg_row = get_avg_row(data, total_time_diff, total_status_duration, avg_weights, unique_order_count, unique_customer_count)
    
    if total_row:
        data.append(total_row)
    if avg_row:
        data.append(avg_row)
    
    return columns, data, message

def get_columns():
    columns = [
        {"fieldname": "form_name", "label": _("ID"), "fieldtype": "Data", "width": 170},
        {"fieldname": "company", "label": _("Company"), "fieldtype": "Link", "options": "Company", "width": 250},
        {"fieldname": "branch", "label": _("Branch"), "fieldtype": "Link", "options": "Branch", "width": 150},
        {"fieldname": "customer_code", "label": _("Customer"), "fieldtype": "Data", "width": 150},
        {"fieldname": "order_type", "label": _("Order Type"), "fieldtype": "Data", "width": 150},
        # {"fieldname": "category", "label": _("Category"), "fieldtype": "Data", "width": 120},
        # {"fieldname": "subcategory", "label": _("Sub Category"), "fieldtype": "Data", "width": 180},
        {"fieldname": "order_date", "label": _("Order Date"), "fieldtype": "Date", "width": 150},
        {"fieldname": "document_created", "label": _("Created Date/Time"), "fieldtype": "Datetime", "width": 190},
        {"fieldname": "owner", "label": _("Order Creator"), "fieldtype": "Data", "width": 200},
        {"fieldname": "employee", "label": _("Creator Emp ID"), "fieldtype": "Link","options":"Employee", "width": 150},
        {"fieldname": "creator_department", "label": _("Creator Department"), "fieldtype": "Data","align":"left", "width": 200},
        {"fieldname": "creator_designation", "label": _("Creator Designation"), "fieldtype": "Data", "width": 200},
        # {"fieldname": "_assign", "label": _("Assigned to"), "fieldtype": "Data", "width": 150},
        {"fieldname": "assigned_department", "label": _("Assigned to Department"), "fieldtype": "Data","align":"left", "width": 190},
        {"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 150},
        {"fieldname": "workflow_count", "label": _("Workflow State"), "fieldtype": "Data", "width": 130},
        {"fieldname": "status_change_time", "label": _("Status Date/Time"), "fieldtype": "Datetime", "width": 180},
        {"fieldname": "time_to_status", "label": _("Time Difference"), "fieldtype": "Data", "width": 200},
        {"fieldname": "status_duration", "label": _("Status Duration"), "fieldtype": "Data", "width": 200},
        {"fieldname": "item", "label": _("Item Code"), "fieldtype": "Link","options":"Item","align":"left", "width": 150},
        {"fieldname": "bom", "label": _("Template BOM"), "fieldtype": "Link","options":"BOM", "align":"left" ,"width": 200},
        {"fieldname": "metal_weight", "label": "Total Metal Wt(g)", "fieldtype": "Data", "width": 180},
        # {"fieldname": "finding_pcs", "label": "Finding Pcs", "fieldtype": "Int", "width": 120},
        # {"fieldname": "total_diamond_pcs", "label": "Total Diamond Pcs", "fieldtype": "Int", "width": 120},
        {"fieldname": "total_diamond_weight_in_gms", "label": "Total Diamond Wt (g)", "fieldtype": "Data", "width": 180},
        {"fieldname": "total_finding_weight_per_gram", "label": "Total Finding Wt (g)", "fieldtype": "Data", "width": 180},
        # {"fieldname": "total_gemstone_pcs", "label": "Total Gemstone Pcs", "fieldtype": "Int", "width": 120},
        {"fieldname": "total_gemstone_weight_in_gms", "label": "Total Gemstone Wt (g)", "fieldtype": "Data", "width": 180},
        {"fieldname": "other_weight", "label": "Other Wt", "fieldtype": "Data", "width": 180},
        # {"fieldname": "total_other_pcs", "label": "Total Other Pcs", "fieldtype": "Int", "width": 120},
        {"fieldname": "delivery_date", "label": _("Delivery Date"), "fieldtype": "Date", "width": 150}
    ]
    return columns

def get_data(filters):
    conditions = get_conditions(filters)
    query = f"""
    SELECT
        sko.name AS form_name,
        sko.company AS company,
        sko.branch AS branch,
        sko.owner,
        e.employee,
        i.name as item,
        bom.name as bom,
        bom.metal_weight,
        bom.finding_pcs,
        bom.total_finding_weight_per_gram,
        bom.total_diamond_pcs,
        bom.total_diamond_weight_in_gms,
        bom.total_gemstone_pcs,
        bom.total_gemstone_weight_in_gms,
        bom.other_weight,
        bom.total_other_pcs,
        e.department AS creator_department,
        e.designation AS creator_designation,
        latest_assignments._assign as _assign,
        emp.department as assigned_department,
        sko.category AS category,
        sko.subcategory AS subcategory,
        sko.delivery_date AS delivery_date,
        sko.order_type AS order_type,
        sko.customer_code AS customer_code,
        sko.order_date AS order_date,
        sko.creation as document_created,
        (SELECT MIN(modified) 
         FROM `tabSketch Order` 
         WHERE name = sko.name) AS status_change_time,
        sko.workflow_state AS status,
        (CASE
          WHEN sko.workflow_state = 'Cancelled' THEN 0
          WHEN sko.workflow_state = 'Unassigned' THEN 1
          WHEN sko.workflow_state = 'On Hold' THEN 2
		  WHEN sko.workflow_state = 'Assigned' THEN 3
		  WHEN sko.workflow_state = 'On Hold - Assigned' THEN 4
		  WHEN sko.workflow_state = 'Rough Sketch Approval (HOD)' THEN 5
		  WHEN sko.workflow_state = 'On Hold - Rough Sketch Approval' THEN 6
		  WHEN sko.workflow_state = 'Final Sketch Approval (HOD)' THEN 7
          WHEN sko.workflow_state = 'ON Hold - Final Sketch Approved (HOD)' THEN 8
          WHEN sko.workflow_state = 'Customer Approval' THEN 9
          WHEN sko.workflow_state = 'Requires Update' THEN 10
		  ELSE 11
        END ) as workflow_count,
        latest_assignments._assign AS latest_assigned_user,
        emp.department AS latest_assigned_user_department
    FROM `tabSketch Order` sko
    LEFT JOIN tabEmployee e
        ON sko.owner = e.user_id
    LEFT JOIN (
        SELECT _assign, MAX(modified) AS latest_assignment
        FROM `tabSketch Order`
        GROUP BY _assign
    ) latest_assignments
        ON sko._assign = latest_assignments._assign
        AND sko.modified = latest_assignments.latest_assignment
    LEFT JOIN tabEmployee emp
        ON JSON_CONTAINS(sko._assign, JSON_QUOTE(emp.user_id))
    LEFT JOIN tabItem i
        ON sko.name = i.custom_sketch_order_id and i.has_variants = 0
    LEFT JOIN tabBOM bom
        ON i.name = bom.item and bom.bom_type = 'Template'    
    {f"WHERE {conditions}" if conditions else ""}   
    GROUP BY 
        sko.name, i.name, bom.name
    ORDER BY sko.name DESC, sko.order_date DESC
    """
    
    data = frappe.db.sql(query, as_dict=1)
    
    for row in data:
        if row["status_change_time"] and row["document_created"]:
            time_diff = datetime.strptime(str(row["status_change_time"]), "%Y-%m-%d %H:%M:%S.%f") - datetime.strptime(str(row["document_created"]), "%Y-%m-%d %H:%M:%S.%f")
            days, seconds = time_diff.days, time_diff.seconds
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            row["time_to_status"] = f"{days}d {hours}h {minutes}m {seconds}s"
        else:
            row["time_to_status"] = "N/A"
        
        
        if row["status_change_time"]:
            status_duration = datetime.now() - datetime.strptime(str(row["status_change_time"]), "%Y-%m-%d %H:%M:%S.%f")
            status_days, status_seconds = status_duration.days, status_duration.seconds
            status_hours, status_remainder = divmod(status_seconds, 3600)
            status_minutes, status_seconds = divmod(status_remainder, 60)
            row["status_duration"] = f"{status_days}d {status_hours}h {status_minutes}m {status_seconds}s"
        else:
            row["status_duration"] = "N/A"

        # created_dt = datetime.strptime(str(row["document_created"]), "%Y-%m-%d %H:%M:%S.%f")
        # status_dt = datetime.strptime(str(row["status_change_time"]), "%Y-%m-%d %H:%M:%S.%f")
        # row["document_created"] = created_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
        # row["status_change_time"] = status_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
        # row["status_duration"] = calculate_status_duration(status_dt, row["status"])   

        row["status"] = f'<span style="color:red;font-weight:bold;">Draft</span>' if row["status"] == 'Draft' else f'<span style="color:green;font-weight:bold;">Items Updated</span>' if row["status"] == 'Items Updated' else row["status"]
        
        if "Items Updated" in row["status"] or "Cancelled" in row["status"]:
            row["status_duration"] = "-"

        encoded_form_name = urllib.parse.quote(row["form_name"])
        encoded_customer_name = urllib.parse.quote(row["customer_code"])
        row["form_name"] = f'<a href="https://gkexport.frappe.cloud/app/sketch-order/{encoded_form_name}" target="_blank">{row["form_name"]}</a>'
        row["customer_code"] = f'<a href="https://gkexport.frappe.cloud/app/customer/{encoded_customer_name}" target="_blank">{row["customer_code"]}</a>'
    
    return data


def calculate_total_time_diff(data):
    total_time = timedelta()
    counted_sketch_order_ids = set()
    
    for row in data:
        if row["form_name"] in counted_sketch_order_ids:
            continue
        
        counted_sketch_order_ids.add(row["form_name"])
        
        if row["status_change_time"] and row["document_created"]:
            time_diff = datetime.strptime(str(row["status_change_time"]), "%Y-%m-%d %H:%M:%S.%f") - datetime.strptime(str(row["document_created"]), "%Y-%m-%d %H:%M:%S.%f")
            total_time += time_diff
    
    return total_time


def calculate_total_status_duration(data):
    total_status_duration = timedelta()
    counted_sketch_order_ids = set()
    
    for row in data:
        if row["form_name"] in counted_sketch_order_ids:
            continue
        
        counted_sketch_order_ids.add(row["form_name"])
        
        if row["status_change_time"]:
            status_duration = datetime.now() - datetime.strptime(str(row["status_change_time"]), "%Y-%m-%d %H:%M:%S.%f")
            total_status_duration += status_duration
    
    return total_status_duration


def calculate_total_weights(data):
    total_metal_weight = 0
    total_diamond_weight = 0
    total_finding_weight = 0
    total_gemstone_weight = 0
    total_other_weight = 0
    
    for row in data:
        total_metal_weight += float(row.get("metal_weight") or 0)
        total_diamond_weight += float(row.get("total_diamond_weight_in_gms") or 0)
        total_finding_weight += float(row.get("total_finding_weight_per_gram") or 0)
        total_gemstone_weight += float(row.get("total_gemstone_weight_in_gms") or 0)
        total_other_weight += float(row.get("other_weight") or 0)
    
    return {
        "metal_weight": total_metal_weight,
        "diamond_weight": total_diamond_weight,
        "finding_weight": total_finding_weight,
        "gemstone_weight": total_gemstone_weight,
        "other_weight": total_other_weight
    }



def calculate_avg_weights(data,unique_order_count):
    total_weights = calculate_total_weights(data)
    
    num_rows = unique_order_count
    avg_metal_weight = total_weights["metal_weight"] / num_rows if num_rows else 0
    avg_diamond_weight = total_weights["diamond_weight"] / num_rows if num_rows else 0
    avg_finding_weight = total_weights["finding_weight"] / num_rows if num_rows else 0
    avg_gemstone_weight = total_weights["gemstone_weight"] / num_rows if num_rows else 0
    avg_other_weight = total_weights["other_weight"] / num_rows if num_rows else 0
    
    return {
        "metal_weight": avg_metal_weight,
        "diamond_weight": avg_diamond_weight,
        "finding_weight": avg_finding_weight,
        "gemstone_weight": avg_gemstone_weight,
        "other_weight": avg_other_weight
    }

def format_timedelta(td):
    days = td.days
    seconds = td.seconds
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"

def get_total_row(data, total_time_diff, total_status_duration, total_weights, avg_weights, unique_order_count, unique_customer_count):
    if not data:
        return None
    
    # total_orders = unique_order_count / len(data) if data else 0
    # total_time_diff_str = str(total_time_diff)
    # total_status_duration_str = str(total_status_duration)

    days, remainder = divmod(total_time_diff.seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    total_time_str = f"{total_time_diff.days + days}d {hours}h {minutes}m {seconds}s"

    status_days, remainder = divmod(total_status_duration.seconds, 86400)
    status_hours, remainder = divmod(remainder, 3600)
    status_minutes, status_seconds = divmod(remainder, 60)
    total_status_str = f"{total_status_duration.days + status_days}d {status_hours}h {status_minutes}m {status_seconds}s"
    
    return {
        "form_name": f"<b><span style='color: rgb(23,175,23); font-size: 15px; font-weight: bold;'>Total Orders: {unique_order_count}</span></b>",
        "company": "",
        "branch": "",
        "category": "",
        "subcategory": "",
        "order_date": "",
        "document_created": "",
        "status": "",
        "status_change_time": "",
        "time_to_status": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;'>{total_time_str}</span></b>",
        "status_duration": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;'>{total_status_str}</span></b>",
        "customer_code": f"<b><span style='color: rgb(23,175,23); font-size: 15px; font-weight: bold;'>Customers: {unique_customer_count}</span></b>",
        "metal_weight": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;'>{total_weights['metal_weight']:.2f}</span></b><br><b><span style='color:rgb(23,175,23); font-size: 15px;'>Avg: {avg_weights['metal_weight']:.2f}</span></b>",
        "total_diamond_weight_in_gms": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;'>{total_weights['diamond_weight']:.2f}</span></b><br><b><span style='color:rgb(23,175,23); font-size: 15px;'>Avg: {avg_weights['diamond_weight']:.2f}</span></b>",
        "total_finding_weight_per_gram": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;'>{total_weights['finding_weight']:.2f}</span></b><br><b><span style='color:rgb(23,175,23); font-size: 15px;'>Avg: {avg_weights['finding_weight']:.2f}</span></b>",
        "total_gemstone_weight_in_gms": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;'>{total_weights['gemstone_weight']:.2f}</span></b><br><b><span style='color:rgb(23,175,23); font-size: 15px;'>Avg: {avg_weights['gemstone_weight']:.2f}</span></b>",
        "other_weight": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;'>{total_weights['other_weight']:.2f}</span></b><br><b><span style='color:rgb(23,175,23); font-size: 15px;'>Avg: {avg_weights['other_weight']:.2f}</span></b>"
    }


def format_timedelta(td):
    days = td.days
    seconds = td.seconds
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"


def get_avg_row(data, total_time_diff, total_status_duration, avg_weights, unique_order_count, unique_customer_count):
    if not data:
        return None
    
    avg_orders = unique_order_count / unique_customer_count if data else 0
    # avg_time_diff = total_time_diff.total_seconds() / len(data) if data else 0
    # avg_time_diff_str = str(timedelta(seconds=avg_time_diff))
    # avg_status_duration = total_status_duration.total_seconds() / len(data) if data else 0
    # avg_status_duration_str = str(timedelta(seconds=avg_status_duration))
    
    avg_time_diff_str = timedelta(seconds=(total_time_diff.total_seconds() / unique_order_count)) if data else timedelta()
    avg_status_duration_str = timedelta(seconds=(total_status_duration.total_seconds() / unique_order_count)) if data else timedelta()

    return {
        "form_name": f"<b><span style='color: rgb(23,175,23); font-size: 15px; font-weight: bold;'>Avg/Customer: {avg_orders:.2f}</span></b>",
        "company": "",
        "branch": "",
        "category": "",
        "subcategory": "",
        "order_date": "",
        "document_created": "",
        "status": "",
        "status_change_time": "",
        "time_to_status": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;'>Avg: {format_timedelta(avg_time_diff_str)}</span></b>",
        "status_duration": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;'>Avg: {format_timedelta(avg_status_duration_str)}</span></b>",
        "customer_code": "",
        "metal_weight": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;'>Avg/Order: {avg_weights['metal_weight']:.2f}</span></b>",
        "total_diamond_weight_in_gms": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;'>Avg/Order: {avg_weights['diamond_weight']:.4f}</span></b>",
        "total_finding_weight_per_gram": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;'>Avg/Order: {avg_weights['finding_weight']:.2f}</span></b>",
        "total_gemstone_weight_in_gms": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;'>Avg/Order: {avg_weights['gemstone_weight']:.2f}</span></b>",
        "other_weight": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;'>Avg/Order: {avg_weights['other_weight']:.2f}</span></b>"
    }


# def get_avg_row(data, total_time_diff, total_status_duration, unique_order_count, unique_customer_count):
#     if not data:
#         return None
    
#     avg_orders_per_customer = unique_order_count / unique_customer_count if unique_customer_count else 0
#     avg_time_diff = timedelta(seconds=(total_time_diff.total_seconds() / len(data))) if data else timedelta()
#     avg_status_duration = timedelta(seconds=(total_status_duration.total_seconds() / len(data))) if data else timedelta()
    
#     return {
#         "form_name": f"<b><span style='color: rgb(23,175,23); font-size: 15px; font-weight: bold;'>Avg/Customer: {avg_orders_per_customer:.2f}</span></b>",
#         "company": "",
#         "branch": "",
#         "category": "",
#         "subcategory": "",
#         "order_date": "",
#         "document_created": "",
#         "status": "",
#         "status_change_time": "",
#         "time_to_status": f"<b><span style='color:rgb(23,175,23); font-size: 15px;'>Avg: {format_timedelta(avg_time_diff)}</span></b>",
#         "status_duration": f"<b><span style='color:rgb(23,175,23); font-size: 15px;'>Avg: {format_timedelta(avg_status_duration)}</span></b>",
#         "customer_code": ""
#     }


def get_message():
    
	return """<span class="indicator" style="font-weight: bold; font-size: 15px;">
        Note : &nbsp;&nbsp;
        </span>
        <span class="indicator blue" style="font-size: 15px;">
        Time difference = Created date-time - Status date-time.
        </span>
        &nbsp;&nbsp;&nbsp;
        <span class="indicator yellow" style="font-size: 15px; margin-left: 126px;">
        Sketch Order Count: Total Number of Sketch orders.
        </span>
        <br>
        &nbsp;
        <span class="indicator blue" style="font-size: 15px;margin-left: 67px;">
        Status Duration = Status date-time - Current date-time.
        </span>
        <span class="indicator yellow" style="font-size: 15px; margin-left: 144px;">
        Items Count = Total Number of Items in Sketch Orders.
        </span>
        <br>
        </span>
      <span style="display: inline-flex; align-items: baseline; font-size: 15px; margin-left: 20px;">
      <span style="color: green; font-size: 27px; margin-right: 5px; line-height: 0;">•</span>
       <span>
        Total Number of Workflow State in this process is 12 (1-Unassigned, 2-On Hold, 3-Assigned, 
        4-On Hold-Assigned, 5-Rough Sketch Approval (HOD), 6-On Hold - Rough Sketch Approval, 
        7-Final Sketch Approval (HOD), 8-On Hold - Final Sketch Approved (HOD), 9-Customer Approval, 
        10-Requires Update, 11-Items Updated, 0-Cancelled)
       </span>
    </span>

"""

def get_conditions(filters):
    conditions = []
    if filters.get("from_date"):
        conditions.append(f"""sko.order_date >= "{filters['from_date']}" """)
    if filters.get("to_date"):
        conditions.append(f"""sko.order_date <= "{filters['to_date']}" """)
    # if filters.get("category"):
    #     conditions.append(f"""sko.category = "{filters['category']}" """)
    if filters.get("company"):
        companies = ', '.join([f'"{company}"' for company in filters.get("company")])
        conditions.append(f"""sko.company IN ({companies})""")
    if filters.get("branch"):
        branches = ', '.join([f'"{branch}"' for branch in filters.get("branch")])
        conditions.append(f"""sko.branch IN ({branches})""")
    if filters.get("order_id"):
        order_ids = "', '".join(filters["order_id"])
        conditions.append(f"sko.name IN ('{order_ids}')")  
    if filters.get("customer_code"):
        customer_codes = "', '".join(filters["customer_code"])
        conditions.append(f"sko.customer_code IN ('{customer_codes}')")           
    if filters.get("status"):
        conditions.append(f"""sko.workflow_state = "{filters['status']}" """)  
    return " AND ".join(conditions) if conditions else ""
