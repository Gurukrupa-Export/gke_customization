import frappe
from frappe import _
from datetime import datetime, timedelta
import urllib.parse

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    
    filtered_data = [row for row in data if row['status_duration'] != "-"]
    total_time_diff = calculate_total_time_diff(data)
    total_status_duration = calculate_total_status_duration(filtered_data)
    

    unique_order_count = len(set([row['form_name'] for row in data]))
    unique_customer_count = len(set([row['customer_code'] for row in data]))
    
    total_row = get_total_row(data, total_time_diff,total_status_duration, unique_order_count, unique_customer_count)
    avg_row = get_avg_row(data, total_time_diff, total_status_duration, unique_order_count, unique_customer_count)
    
    if total_row:
        data.append(total_row)

    if avg_row:
        data.append(avg_row)
        
    message = get_message()
  
    return columns, data, message

def get_columns():
    columns = [
        {"fieldname": "form_name", "label": _( "Sketch Order Form ID"), "fieldtype": "Data", "width": 180},
        {"fieldname": "company", "label": _( "Company"), "fieldtype": "Link", "options": "Company", "width": 250},
        {"fieldname": "branch", "label": _( "Branch"), "fieldtype": "Link", "options": "Branch", "width": 150},
        {"fieldname": "customer_code", "label": _( "Customer"), "fieldtype": "Data", "width": 150},
        {"fieldname": "order_type", "label": _( "Order Type"), "fieldtype": "Data", "width": 130},
        {"fieldname": "order_date", "label": _( "Order Date"), "fieldtype": "Date", "width": 150},
        # {"fieldname": "category", "label": _( "Category"), "fieldtype": "Data", "width": 120},
        {"fieldname": "total_count", "label": _( "Sketch Order Count"), "fieldtype": "Data", "width": 100},
        {"fieldname": "total_item", "label": _( "Items Count"), "fieldtype": "Data", "width": 100},
        {"fieldname": "document_created", "label": _( "Created Date/Time"), "fieldtype": "Datetime", "width": 180},
        {"fieldname": "owner", "label": _( "Order Form Creator"), "fieldtype": "Data", "width": 180},
        {"fieldname": "employee", "label": _("Creator Emp ID"), "fieldtype": "Link","options":"Employee", "width": 150},
        {"fieldname": "creator_department", "label": _("Creator Department"), "fieldtype": "Data","align":"left", "width": 200},
        {"fieldname": "creator_designation", "label": _("Creator Designation"), "fieldtype": "Data", "width": 200},
        {"fieldname": "assigned_department", "label": _("Assigned to Department"), "fieldtype": "Data","align":"left", "width": 190},
        {"fieldname": "docstatus", "label": _("Document Status"), "fieldtype": "Data", "width": 150},
        {"fieldname": "status", "label": _( "Workflow Status"), "fieldtype": "Data", "width": 150},
        {"fieldname": "workflow_count", "label": _("Workflow State"), "fieldtype": "Data", "width": 140},
        {"fieldname": "diamond_target", "label": _( "Diamond Wt."), "fieldtype": "Data", "width": 170},
        {"fieldname": "status_change_time", "label": _( "Status Date/Time"), "fieldtype": "Datetime", "width": 180},
        {"fieldname": "time_to_status", "label": _( "Time Difference"), "fieldtype": "Data", "width": 230},
        {"fieldname": "status_duration", "label": _("Status Duration"), "fieldtype": "Data", "width": 230},
        {"fieldname": "delivery_date", "label": _( "Delivery Date"), "fieldtype": "Date", "width": 150}

    ]
    return columns

def get_data(filters):
    conditions = get_conditions(filters)
    query = f'''
    SELECT 
        skof.name AS form_name,
        skof.company,
        skof.branch,
        skof.owner,
        (CASE WHEN skof.docstatus = 0 THEN "Draft" 
             WHEN skof.docstatus = 1 THEN "Submitted"
             WHEN skof.docstatus = 2 THEN "Cancelled"
        END) AS docstatus, 
        skof._assign,
        skof.delivery_date,
        skof.order_type,
        skof.customer_code,
        skfd.category,
        skfd.subcategory,
        count(distinct sko.name) AS total_count,
        skof.order_date,
        skfd.diamond_target,
        count(distinct i.name) AS total_item,
        e.employee,
        e.department AS creator_department,
        e.designation AS creator_designation,
        skof.creation AS document_created,
        latest_assignments._assign as _assign,
        latest_assignments._assign AS latest_assigned_user,
        emp.department AS latest_assigned_user_department,
        skof.workflow_state AS status,
        (CASE
          WHEN skof.workflow_state = 'Cancelled' THEN 0
          WHEN skof.workflow_state = 'Draft' THEN 1
          WHEN skof.workflow_state = 'Draft - On Hold' THEN 2
          WHEN skof.workflow_state = 'On Hold' THEN 3
          WHEN skof.workflow_state = 'Send For Approval' THEN 4
		  ELSE 5
        END ) as workflow_count,
        (SELECT MIN(modified) FROM `tabSketch Order Form` WHERE name = skof.name) AS status_change_time
    FROM `tabSketch Order Form` skof
    LEFT JOIN `tabSketch Order Form Detail` skfd
        ON skof.name = skfd.parent
    LEFT JOIN `tabSketch Order` sko
         ON skof.name = sko.sketch_order_form
    LEFT JOIN tabEmployee e
        ON skof.owner = e.user_id
    LEFT JOIN (
        SELECT _assign, MAX(modified) AS latest_assignment
        FROM `tabSketch Order Form`
        GROUP BY _assign
    ) latest_assignments
        ON skof._assign = latest_assignments._assign
        AND skof.modified = latest_assignments.latest_assignment 
    LEFT JOIN tabItem i
        ON skof.name = i.custom_sketch_order_form_id and i.has_variants = 0    
    LEFT JOIN tabEmployee emp
        ON JSON_CONTAINS(skof._assign, JSON_QUOTE(emp.user_id))       
    {f"WHERE {conditions}" if conditions else ""}
    GROUP BY skof.name
    ORDER BY  skof.name DESC, skof.order_date DESC
    '''
    
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

        row["status"] = f'<span style="color:red;font-weight:bold;">Draft</span>' if row["status"] == 'Draft' else f'<span style="color:green;font-weight:bold;">Approved</span>' if row["status"] == 'Approved' else row["status"]
        
        if "Approved" in row["status"]:
            row["status_duration"] = "-"

        encoded_form_name = urllib.parse.quote(row["form_name"])
        encoded_customer_name = urllib.parse.quote(row["customer_code"])
        row["form_name"] = f'<a href="https://gkexport.frappe.cloud/app/sketch-order-form/{encoded_form_name}" target="_blank">{row["form_name"]}</a>'
        row["customer_code"] = f'<a href="https://gkexport.frappe.cloud/app/customer/{encoded_customer_name}" target="_blank">{row["customer_code"]}</a>'
    
    return data

def calculate_total_time_diff(data):
    total_time = timedelta()
    
    for row in data:
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


def get_total_row(data, total_time_diff,total_status_duration, unique_order_count, unique_customer_count):
    if not data:
        return None
    
    days, remainder = divmod(total_time_diff.seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    total_time_str = f"{total_time_diff.days + days}d {hours}h {minutes}m {seconds}s"

    status_days, remainder = divmod(total_status_duration.seconds, 86400)
    status_hours, remainder = divmod(remainder, 3600)
    status_minutes, status_seconds = divmod(remainder, 60)
    total_status_str = f"{total_status_duration.days + status_days}d {status_hours}h {status_minutes}m {status_seconds}s"
    
    
    return {
        "form_name": f"<b><span style='color: rgb(23,175,23); font-size: 15px; font-weight: bold; text-align: left;'>Total count: {unique_order_count}</span></b>",
        "company": "",
        "branch": "",
        "category": "",
        "subcategory": "",
        "order_date": "",
        "document_created": "",
        "status": "",
        "status_change_time": "",
        "time_to_status": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;text-align: left;'>{total_time_str}</span></b>",
        "status_duration": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;text-align: left;'>{total_status_str}</span></b>",
        "customer_code": f"<b><span style='color: rgb(23,175,23); font-size: 15px; font-weight: bold; text-align: left;'>Customers: {unique_customer_count}</span></b>"
    }



def format_timedelta(td):
    days = td.days
    seconds = td.seconds
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"


def get_avg_row(data, total_time_diff, total_status_duration, unique_order_count, unique_customer_count):
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
        "form_name": f"<b><span style='color: rgb(23,175,23); font-size: 15px; font-weight: bold; text-align: left;'>Avg/Customer: {avg_orders:.2f}</span></b>",
        "company": "",
        "branch": "",
        "category": "",
        "subcategory": "",
        "order_date": "",
        "document_created": "",
        "status": "",
        "status_change_time": "",
        "time_to_status": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;text-align: left;'>Avg/Order:{format_timedelta(avg_time_diff_str)}</span></b>",
        "status_duration": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;text-align: left;'>Avg/Order:{format_timedelta(avg_status_duration_str)}</span></b>",
        "customer_code": ""
    }
    
    

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
        <span class="indicator yellow" style="font-size: 15px; margin-left: 143px;">
        Items Count = Total Number of Items in Sketch Orders.
        </span>
        <br>
        </span>
        <span class="indicator green" style="font-size: 15px; margin-left: 73px;">
        Total Number of Workflow State in this process is 4 (1-Draft, 2-Draft - On Hold, 3-On Hold, 4-Send For Approval, 5-Approved, 0: Cancelled)
        </span>
"""

def get_conditions(filters):
    conditions = []
    if filters.get("from_date"):
        conditions.append(f"""skof.order_date >= "{filters['from_date']}" """)
    if filters.get("to_date"):
        conditions.append(f"""skof.order_date <= "{filters['to_date']}" """)
    # if filters.get("category"):
    #     conditions.append(f"""skfd.category = "{filters['category']}" """)
    if filters.get("company"):
        conditions.append(f"""skof.company = "{filters['company']}" """)      
    if filters.get("branch"):
        # branches = ', '.join([f'"{branch}"' for branch in filters.get("branch")])
        conditions.append(f"""skof.branch = "{filters['branch']}" """)      
    if filters.get("order_id"):
        order_ids = "', '".join(filters["order_id"])
        conditions.append(f"skof.name IN ('{order_ids}')")  
    if filters.get("customer_code"):
        order_ids = "', '".join(filters["customer_code"])
        conditions.append(f"skof.customer_code IN ('{order_ids}')")
    if filters.get("docstatus"):
        conditions.append(f"""sko.docstatus = "{filters['docstatus']}" """)               
    if filters.get("status"):
        conditions.append(f"""skof.workflow_state = "{filters['status']}" """)
    return " AND ".join(conditions) if conditions else ""
