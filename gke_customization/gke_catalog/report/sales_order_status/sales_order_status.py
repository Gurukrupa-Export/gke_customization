import frappe
from frappe import _
from datetime import datetime, timedelta
import urllib.parse

def execute(filters=None):
    
    columns = get_columns()
    data = get_data(filters)
    
    total_time_diff = calculate_total_time_diff(data)
    total_status_duration = calculate_total_status_duration(data)
    
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
  

    return columns, data


def get_columns():
    columns = [
        {"fieldname": "form_name", "label": _( "Sales Order ID"), "fieldtype": "Data", "width": 200},
        # {"fieldname": "order_form_id", "label": _( "Order Form ID"), "fieldtype": "Data", "width": 200},
        # {"fieldname": "order_form", "label": _( "Ord_f"), "fieldtype": "Data", "width": 200},
        # {"fieldname": "rep_order_form_id", "label": _( "Repair_f"), "fieldtype": "Data", "width": 200},
        {"fieldname": "quotation", "label": _( "Quotation ID"), "fieldtype": "Link","options":"Quotation", "width": 200},
        {"fieldname": "company", "label": _( "Company"), "fieldtype": "Link", "options": "Company", "width": 250},
        {"fieldname": "branch", "label": _( "Branch"), "fieldtype": "Link", "options": "Branch", "width": 150},
        {"fieldname": "customer_code", "label": _( "Customer"), "fieldtype": "Data", "width": 150},
        {"fieldname": "order_type", "label": _( "Order Type"), "fieldtype": "Data", "width": 150},
        {"fieldname": "sales_type", "label": _( "Sales Type"), "fieldtype": "Data","align":"left", "width": 130},
        {"fieldname": "total_count", "label": _( "Number of Items (Total items in Sales order)"), "fieldtype": "Data", "width": 120},
        {"fieldname": "total_qty", "label": _( "Total Qty (Quantity of item in the Sales Order)"), "fieldtype": "Data", "width": 120},
        {"fieldname": "diamond_quality", "label": _("Diamond Quality"), "fieldtype": "Data", "width": 150},
        # {"fieldname": "category", "label": _( "Category"), "fieldtype": "Data", "width": 120},
        # {"fieldname": "subcategory", "label": _( "Sub Category"), "fieldtype": "Data", "width": 180},
        {"fieldname": "order_date", "label": _( "Order Date"), "fieldtype": "Date", "width": 150},
        {"fieldname": "document_created", "label": _( "Created Date/Time"), "fieldtype": "Datetime", "width": 180},
        {"fieldname": "owner", "label": _( "Sales Order Creator"), "fieldtype": "Data", "width": 200},
        {"fieldname": "employee", "label": _("Creator Emp ID"), "fieldtype": "Link","options":"Employee", "width": 150},
        {"fieldname": "creator_department", "label": _("Creator Department"), "fieldtype": "Data","align":"left", "width": 200},
        {"fieldname": "creator_designation", "label": _("Creator Designation"), "fieldtype": "Data", "width": 200},
        {"fieldname": "latest_assigned_user_department", "label": _("Assigned to Department"), "fieldtype": "Data","align":"left", "width": 190},
        {"fieldname": "status", "label": _( "Status"), "fieldtype": "Data", "width": 150},
        {"fieldname": "status_change_time", "label": _( "Status Date/Time"), "fieldtype": "Datetime", "width": 180},
        {"fieldname": "time_to_status", "label": _( "Time Difference (Difference between created date-time and status date-time)"), "fieldtype": "Data", "width": 200},
        {"fieldname": "status_duration", "label": _("Status Duration (Difference between status date-time and current date-time)"), "fieldtype": "Data", "width": 200},
        {"fieldname": "metal_weight", "label": "Total Metal Wt(g)", "fieldtype": "Data", "width": 150},
        {"fieldname": "custom_customer_gold", "label": "Customer Gold", "fieldtype": "Data","align":"right", "width": 150},
        
        # {"fieldname": "finding_pcs", "label": "Finding Pcs", "fieldtype": "Int", "width": 120},
        # {"fieldname": "total_diamond_pcs", "label": "Total Diamond Pcs", "fieldtype": "Int", "width": 120},
        {"fieldname": "total_diamond_weight_in_gms", "label": "Total Diamond Wt (ct)", "fieldtype": "Data", "width": 180},
        {"fieldname": "custom_customer_diamond", "label": "Customer Diamond", "fieldtype": "Data","align":"right", "width": 150},
        {"fieldname": "total_finding_weight_per_gram", "label": "Total Finding Wt (g)", "fieldtype": "Data", "width": 180},
        # {"fieldname": "total_gemstone_pcs", "label": "Total Gemstone Pcs", "fieldtype": "Int", "width": 120},
        {"fieldname": "total_gemstone_weight_in_gms", "label": "Total Gemstone Wt (ct)", "fieldtype": "Data", "width": 180},
        {"fieldname": "custom_customer_stone", "label": "Customer Stone", "fieldtype": "Data","align":"right", "width": 150},
        {"fieldname": "other_weight", "label": "Other Wt", "fieldtype": "Data", "width": 110},
        {"fieldname": "billing_status", "label": "Billing Status", "fieldtype": "Data", "width": 180},
        {"fieldname": "delivery_status", "label": "Delivery Status", "fieldtype": "Data", "width": 180},
        {"fieldname": "delivery_date", "label": _( "Delivery Date"), "fieldtype": "HTML", "width": 150},
        {"fieldname": "custom_updated_delivery_date", "label": _( "Updated Delivery Date"), "fieldtype": "HTML", "width": 150}

    ]
    return columns

def get_data(filters):
    conditions = get_conditions(filters)
    query = f"""
    SELECT
    so.name AS form_name,
    so.company,
    so.branch,
    so.owner,
    e.employee,
    so.total_qty,
    e.department AS creator_department,
    e.designation AS creator_designation,
    so.delivery_date,
    so.order_type,
    so.sales_type,
    so.customer AS customer_code,
    so.transaction_date AS order_date,
    so.creation AS document_created,
    so._assign AS latest_assigned_user,
    emp.department AS latest_assigned_user_department,
    bom.name AS bom,
    SUM(bom.metal_weight) AS metal_weight,
    SUM(bom.finding_pcs) AS finding_pcs,
    SUM(bom.finding_weight_) AS total_finding_weight_per_gram,
    SUM(bom.total_diamond_pcs) AS total_diamond_pcs,
    SUM(bom.diamond_weight) AS total_diamond_weight_in_gms,
    SUM(bom.total_gemstone_pcs) AS total_gemstone_pcs,
    SUM(bom.gemstone_weight) AS total_gemstone_weight_in_gms,
    SUM(bom.other_weight) AS other_weight,
    SUM(bom.total_other_pcs) AS total_other_pcs,
    MIN(so.modified) AS status_change_time,
    so.custom_updated_delivery_date,
    so.custom_diamond_quality diamond_quality,
    so.billing_status AS billing_status,
    so.delivery_status AS delivery_status,
    CASE WHEN soi.custom_customer_gold IS NULL OR soi.custom_customer_gold = '' THEN 'No'ELSE soi.custom_customer_gold END AS custom_customer_gold,
    CASE WHEN soi.custom_customer_diamond IS NULL OR soi.custom_customer_diamond = '' THEN 'No'ELSE soi.custom_customer_diamond END AS custom_customer_diamond,
    CASE WHEN soi.custom_customer_stone IS NULL OR soi.custom_customer_stone = '' THEN 'No'ELSE soi.custom_customer_stone END AS custom_customer_stone,
    count(soi.name) AS total_count,
    qi.name AS quotation,
    so.status
FROM `tabSales Order` so
LEFT JOIN tabEmployee e ON so.owner = e.user_id
LEFT JOIN `tabSales Order Item` soi ON so.name = soi.parent
LEFT JOIN tabBOM bom
        ON soi.quotation_bom = bom.name and bom.bom_type = 'Quotation'
LEFT JOIN tabQuotation qi ON soi.prevdoc_docname = qi.name
LEFT JOIN tabEmployee emp ON JSON_CONTAINS(so._assign, JSON_QUOTE(emp.user_id))
WHERE {conditions}
GROUP BY
    qi.name, so.name
ORDER BY so.name DESC, so.transaction_date DESC
    """
    
    data = frappe.db.sql(query, as_dict=1)
    # has_valid_status = False


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

        row["status"] = f'<span style="color:red;font-weight:bold;">Draft</span>' if row["status"] == 'Draft' else f'<span style="color:green;font-weight:bold;">Completed</span>' if row["status"] == 'Completed' else f'<span style="color:green;font-weight:bold;">Closed</span>' if row["status"] == 'Closed' else row["status"]

        encoded_form_name = urllib.parse.quote(row["form_name"])
        encoded_customer_name = urllib.parse.quote(row["customer_code"])
        row["form_name"] = f'<a href="http://192.168.64.135:8000/app/sales-order/{encoded_form_name}" target="_blank">{row["form_name"]}</a>'
        row["customer_code"] = f'<a href="http://192.168.64.135:8000/app/customer/{encoded_customer_name}" target="_blank">{row["customer_code"]}</a>'
        

        # if row["status_duration"] != "-":
        #     has_valid_status = True

        # row["status"] = format_status(row["status"])
        created_dt = datetime.strptime(str(row["document_created"]), "%Y-%m-%d %H:%M:%S.%f")
        status_dt = datetime.strptime(str(row["status_change_time"]), "%Y-%m-%d %H:%M:%S.%f")
        row["document_created"] = created_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
        row["status_change_time"] = status_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
        row["status_duration"], exceeded = calculate_status_duration(status_dt, row["status"])
        if exceeded:
            row["status_duration"] = f"<span style='color: red;'>{row['status_duration']}</span>"

        row["status_duration"] = '-' if (row["status"] == '<span style="color:green;font-weight:bold;">Closed</span>' or row["status"] == 'Cancelled' or row["status"] == '<span style="color:green;font-weight:bold;">Completed</span>') else row["status_duration"]
        
        
        if row.get("custom_updated_delivery_date") and row.get("delivery_date"):
            if row["custom_updated_delivery_date"] != row["delivery_date"]:
                row["delivery_date"] = f"<span style='color: red; font-weight: bold;'>{row['delivery_date']}</span>"
                row["custom_updated_delivery_date"] = f"<span style='color: green; font-weight: bold;'>{row['custom_updated_delivery_date']}</span>"
            else:
                row["custom_updated_delivery_date"] = "-"
                row["delivery_date"] = "-"
        else:

            if not row.get("custom_updated_delivery_date"):
                row["custom_updated_delivery_date"] = "-"
            if not row.get("delivery_date"):
                row["delivery_date"] = "-"

        if row.get("custom_customer_gold") == 'Yes':
            row["custom_customer_gold"] = f"<span style='color: #00B8B8; font-weight: bold;'>{row['custom_customer_gold']}</span>"
        
        if row.get("custom_customer_diamond") == 'Yes':
            row["custom_customer_diamond"] = f"<span style='color: #FFE5B4; font-weight: bold;'>{row['custom_customer_gold']}</span>"

        if row.get("custom_customer_stone") == 'Yes':
            row["custom_customer_stone"] = f"<span style='color: #FFE5B4; font-weight: bold;'>{row['custom_customer_gold']}</span>"
        


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
    counted_sales_order_ids = set()
    
    for row in data:
        if row["form_name"] in counted_sales_order_ids:
            continue
        
        counted_sales_order_ids.add(row["form_name"])
        
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
        "order_date": "",
        "document_created": "",
        "status": "",
        "status_change_time": "",
        "time_to_status": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;text-align: left;'>{total_time_str}</span></b>",
        "status_duration": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;'>{total_status_str}</span></b>",
        "customer_code": f"<b><span style='color: rgb(23,175,23); font-size: 15px; font-weight: bold;'>Customers: {unique_customer_count}</span></b>",
        "metal_weight": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;'>{total_weights['metal_weight']:.2f}</span></b><br><b><span style='color:rgb(23,175,23); font-size: 15px;'>Avg: {avg_weights['metal_weight']:.2f}</span></b>",
        "total_diamond_weight_in_gms": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;'>{total_weights['diamond_weight']:.2f}</span></b><br><b><span style='color:rgb(23,175,23); font-size: 15px;'>Avg: {avg_weights['diamond_weight']:.2f}</span></b>",
        "total_finding_weight_per_gram": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;'>{total_weights['finding_weight']:.2f}</span></b><br><b><span style='color:rgb(23,175,23); font-size: 15px;'>Avg: {avg_weights['finding_weight']:.2f}</span></b>",
        "total_gemstone_weight_in_gms": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;'>{total_weights['gemstone_weight']:.2f}</span></b><br><b><span style='color:rgb(23,175,23); font-size: 15px;'>Avg: {avg_weights['gemstone_weight']:.2f}</span></b>",
        "other_weight": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;'>{total_weights['other_weight']:.2f}</span></b><br><b><span style='color:rgb(23,175,23); font-size: 15px;'>Avg: {avg_weights['other_weight']:.2f}</span></b>",
        "delivery_date": "",
        "updated_delivery_date": "",
    }



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
        "form_name": f"<b><span style='color: rgb(23,175,23); font-size: 15px; font-weight: bold; text-align: left;'>Avg/ Customer: {int(avg_orders)}</span></b>",
        "company": "",
        "branch": "",
        "order_date": "",
        "document_created": "",
        "status": "",
        "status_change_time": "",
        "time_to_status": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;text-align: left;'>Avg:{format_timedelta(avg_time_diff_str)}</span></b>",
        "status_duration": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;'>Avg:{format_timedelta(avg_status_duration_str)}</span></b>",
        "customer_code": "",
        "metal_weight": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;'>Avg/Order: {avg_weights['metal_weight']:.2f}</span></b>",
        "total_diamond_weight_in_gms": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;'>Avg/Order: {avg_weights['diamond_weight']:.4f}</span></b>",
        "total_finding_weight_per_gram": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;'>Avg/Order: {avg_weights['finding_weight']:.2f}</span></b>",
        "total_gemstone_weight_in_gms": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;'>Avg/Order: {avg_weights['gemstone_weight']:.2f}</span></b>",
        "other_weight": f"<b><span style='color:rgb(23,175,23); font-size: 15px; font-weight: bold;'>Avg/Order: {avg_weights['other_weight']:.2f}</span></b>"
    }


def calculate_status_duration(modified_dt, status):

    current_dt = datetime.now()
    hours_count = 0
    temp_dt = modified_dt

    while temp_dt < current_dt:
        temp_dt += timedelta(hours=5)
        if temp_dt.weekday() != 6:
            hours_count += 1

    time_difference = current_dt - modified_dt
    time_str = convert_seconds_to_time(time_difference.total_seconds())
    # time_str = convert_seconds_to_time(status_duration.total_seconds())

    exceeded = hours_count > 5 and status not in ["<span style='color:inherit; font-weight:bold;'>Cancelled</span>",f'<span style="color:green;font-weight:bold;">Completed</span>',f'<span style="color:green;font-weight:bold;">Closed</span>']
    

    return time_str, exceeded

def convert_seconds_to_time(seconds):
    days, remainder = divmod(int(seconds), 86400)  
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m {secs}s"

def get_conditions(filters):
    conditions = []
    if filters.get("from_date") and filters.get("to_date"):
        conditions.append(f"""so.transaction_date BETWEEN "{filters['from_date']}" AND "{filters['to_date']}" """)
    if filters.get("company"):
        companies = ', '.join([f'"{company}"' for company in filters.get("company")])
        conditions.append(f"""so.company IN ({companies})""")
    if filters.get("branch"):
        branches = ', '.join([f'"{branch}"' for branch in filters.get("branch")])
        conditions.append(f"""so.branch IN ({branches})""")
    if filters.get("order_id"):
        order_ids = ', '.join([f"'{order}'" for order in filters.get("order_id")])
        conditions.append(f"so.name IN ({order_ids})")
    if filters.get("quotation"):
        quotations = ', '.join([f"'{quotation}'" for quotation in filters.get("quotation")])
        conditions.append(f"qi.name IN ({quotations})")    
    if filters.get("customer_code"):
        customers = ', '.join([f"'{code}'" for code in filters.get("customer_code")])    
        conditions.append(f"so.customer IN ({customers})")
    if filters.get("diamond_quality"):
        conditions.append(f'qi.diamond_quality = "{filters.get("diamond_quality")}"')    
    if filters.get("status"):
        conditions.append(f"so.status = '{filters['status']}'")
    return " AND ".join(conditions) if conditions else ""