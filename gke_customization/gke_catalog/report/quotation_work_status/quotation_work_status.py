# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
import datetime
import urllib.parse
from datetime import datetime,timedelta
import json

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
         {"label": "Quotation ID", "fieldname": "quotation_id", "fieldtype": "Data", "width": 200},
        #  {"label": "Order Form ID", "fieldname": "order_form_id", "fieldtype": "Data", "width": 200},
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 250},
        {"label": "Branch", "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 150},
        # {"label": "Quotation To", "fieldname": "quotation_to", "fieldtype": "Data", "width": 150},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Data", "width": 150},
        {"label": "Order Type", "fieldname": "order_type", "fieldtype": "Data", "width": 150}, 
        {"label": "No. of Items (Total items in the quotation)", "fieldname": "item_count", "fieldtype": "Data", "width": 150}, 
        {"label": "No. of pcs (Quantity of item in the quotation)", "fieldname": "qty", "fieldtype": "Data", "width": 150}, 
        {"label": "Diamond Quality", "fieldname": "diamond_quality", "fieldtype": "Data", "width": 180},
        {"label": "Quotation Date", "fieldname": "transaction_date", "fieldtype": "Date", "width": 150},
        {"label": "Validity Quotation Date", "fieldname": "valid_till", "fieldtype": "Date", "width": 190},
        {"label": "Created Date/Time", "fieldname": "created_datetime", "fieldtype": "Datetime", "width": 180},
        {"label": "Quotation Creator", "fieldname": "quotation_creator", "fieldtype": "Data", "width": 200},
        {"fieldname": "employee", "label": "Creator Employee", "fieldtype": "Data", "width": 200},
        {"fieldname": "department", "label": "Creator Department", "fieldtype": "Data", "width": 200},
        {"fieldname": "designation", "label": "Creator Designation", "fieldtype": "Data", "width": 200},
        {"fieldname": "assigned_to_dept", "label": "Assigned To Dept", "fieldtype": "Data", "width": 200},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 150},
        {"label": "Status Date-Time", "fieldname": "status_datetime", "fieldtype": "Datetime", "width": 180},
        {"label": "Time Difference (Difference between created date-time and status date-time)", "fieldname": "time_difference", "fieldtype": "Data", "width": 250},
        {"fieldname": "status_duration", "label": "Status Duration (Difference between status date-time and current date-time)", "fieldtype": "Data", "width": 280},
        {"fieldname": "target_days", "label": "Target Hrs", "fieldtype": "Data", "width": 110},
        {"fieldname": "total_metal_weight", "label": "Metal Wt", "fieldtype": "Data", "width": 110},
        {"fieldname": "custom_customer_gold", "label": "Customer Gold", "fieldtype": "Data","align":"right", "width": 140},
        {"fieldname": "total_diamond_weight_in_grams", "label": "Total Diamond (ct)", "fieldtype": "Data", "width": 160},
        {"fieldname": "custom_customer_diamond", "label": "Customer Diamond", "fieldtype": "Data","align":"right", "width": 160},
        {"fieldname": "total_gemstone_weight_in_grams", "label": "Total Gemstone (ct)", "fieldtype": "Data", "width": 170},
        {"fieldname": "custom_customer_stone", "label": "Customer Stone", "fieldtype": "Data", "align":"right","width": 160},
        {"fieldname": "total_finding_weight_per_grams", "label": "Total Finding Weight (g)", "fieldtype": "Data", "width": 200},
        # {"fieldname": "custom_customer_finding", "label": "Customer Metal", "fieldtype": "Data", "width": 200},
        {"fieldname": "other_weight_grams", "label": "Other Wt", "fieldtype": "Data", "width": 120},
        # {"fieldname": "custom_customer_other", "label": "Customer Metal", "fieldtype": "Data", "width": 200},    
        # {"fieldname": "ct_total_diamond_weight_in_grams", "label": "Customer Total Diamond (ct)", "fieldtype": "Data", "width": 220},
        # {"fieldname": "ct_total_gemstone_weight_in_grams", "label": "Customer Total Gemstone (ct)", "fieldtype": "Data", "width": 220},
        # {"fieldname": "ct_total_finding_weight_per_grams", "label": "Customer Total Finding Weight (g)", "fieldtype": "Data", "width": 220},
        # {"fieldname": "ct_other_weight_grams", "label": "Customer Other Weight", "fieldtype": "Data", "width": 220},
        {"label": "Delivery Date", "fieldname": "delivery_date", "fieldtype": "HTML", "width": 150},
        {"label": "Updated Delivery Date", "fieldname": "updated_delivery_date", "fieldtype": "HTMl", "width": 180},
    ]

# def convert_seconds_to_time(seconds):
#     days, remainder = divmod(seconds, 86400)
#     hours, remainder = divmod(remainder, 3600)
#     minutes, secs = divmod(remainder, 60)
#     return f"{days} days, {hours:02} hrs:{minutes:02} mins:{secs:02} secs"

def get_data(filters):
    conditions = []

    # if filters.get("from_date") and filters.get("to_date"):
    #     conditions.append(f"DATE(qt.creation) BETWEEN '{filters['from_date']}' AND '{filters['to_date']}'")

    if filters.get("from_date"):
        conditions.append(f"""qt.creation >= "{filters['from_date']}" """)
    if filters.get("to_date"):
        conditions.append(f"""qt.creation <= "{filters['to_date']}" """)

    if filters.get("quotation_id"):
        quotation_ids = "', '".join(filters["quotation_id"])
        conditions.append(f"qt.name IN ('{quotation_ids}')")

    if filters.get("order_id"):
        order_ids = ', '.join([f"'{order}'" for order in filters.get("order_id")])
        conditions.append(f"COALESCE(ord_form.name, rep_form.name) IN ({order_ids})")


    if filters.get("company"):
        companies = ', '.join([f'"{company}"' for company in filters["company"]])
        conditions.append(f"qt.company IN ({companies})")

    if filters.get("branch"):
        branches = ', '.join([f'"{branch}"' for branch in filters["branch"]])
        conditions.append(f"qt.branch IN ({branches})")

    if filters.get("customer"):
        customers = ', '.join([f'"{customer}"' for customer in filters["customer"]])
        conditions.append(f"qt.party_name IN ({customers})")

    if filters.get("category"):
        conditions.append(f"i.item_category = '{filters['category']}'")

    if filters.get("diamond_quality"):
        conditions.append(f'qt.diamond_quality = "{filters.get("diamond_quality")}"')


    if filters.get("status"):
        conditions.append(f"qt.docstatus = {filters['status']}")

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    query = f"""
        SELECT
            qt.company, 
            qt.party_name AS customer,
            qt.name AS quotation_id,
            COALESCE(ord_form.name, rep_form.name) AS order_form_id,
            qti.branch AS branch,
            count(distinct qti.name) as item_count,
            sum(qti.qty) as qty,
            qt.owner AS quotation_creator,
            e.employee AS employee,
            e.department AS department,
            e.designation AS designation,
            qt._assign AS assigned_users,
            qt.transaction_date,
            qt.valid_till,
            qt.order_type,
            qt.diamond_quality,
            qt.creation AS created_datetime, 
            qt.docstatus AS status,
            qt.modified AS status_datetime,
            "5 Hrs" AS target_days,
            qt.modified AS status_datetime,
            SUM(bm.metal_weight) AS total_metal_weight,
            CASE WHEN qti.custom_customer_gold IS NULL OR qti.custom_customer_gold = '' THEN 'No'ELSE qti.custom_customer_gold END AS custom_customer_gold,
            CASE WHEN qti.custom_customer_diamond IS NULL OR qti.custom_customer_diamond = '' THEN 'No'ELSE qti.custom_customer_diamond END AS custom_customer_diamond,
            CASE WHEN qti.custom_customer_stone IS NULL OR qti.custom_customer_stone = '' THEN 'No'ELSE qti.custom_customer_stone END AS custom_customer_stone,

            SUM(bm.finding_weight_) AS total_finding_weight_per_grams,
            SUM(bm.diamond_weight) AS total_diamond_weight_in_grams,
            SUM(bm.gemstone_weight) AS total_gemstone_weight_in_grams,
            SUM(bm.other_weight) AS other_weight_grams,
            COALESCE(ord_form.delivery_date,qti.delivery_date) AS delivery_date,
            ord_form.updated_delivery_date
        FROM `tabQuotation` AS qt
        LEFT JOIN `tabQuotation Item` qti on qt.name = qti.parent
        LEFT JOIN `tabItem` AS i ON i.name = qti.item_code
        LEFT JOIN `tabEmployee` e on qt.owner = e.user_id
        LEFT JOIN `tabBOM` bm on bm.name = qti.quotation_bom
        LEFT JOIN tabOrder ord ON qti.order_form_id = ord.name AND qti.order_form_type = 'Order'
        LEFT JOIN `tabOrder Form` ord_form ON ord.cad_order_form = ord_form.name
        LEFT JOIN `tabRepair Order` rep ON qti.order_form_id = rep.name AND qti.order_form_type = 'Repair Order'
        LEFT JOIN `tabOrder Form` rep_form ON rep.name = rep_form.repair_order


        {where_clause}
        GROUP BY qt.name
        ORDER BY created_datetime DESC, qt.name ASC
    """

    data = frappe.db.sql(query, as_dict=True)

    total_seconds = 0
    total_status_seconds = 0  
    unique_customers = set()
    total_quotation = len(data)
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

        # if row.get("updated_delivery_date") and row.get("delivery_date") and row.get("updated_delivery_date") != row.get("delivery_date"):
        #     row["delivery_date"] = f"<span style='color: red; font-weight: bold;'>{row['delivery_date']}</span>"
        #     row["updated_delivery_date"] = f"<span style='color: green; font-weight: bold;'>{row['updated_delivery_date']}</span>"        
        if row.get("updated_delivery_date"):
          if row.get("delivery_date") and row["updated_delivery_date"] != row["delivery_date"]:
            row["delivery_date"] = f"<span style='color: red; font-weight: bold;'>{row['delivery_date']}</span>"
            row["updated_delivery_date"] = f"<span style='color: green; font-weight: bold;'>{row['updated_delivery_date']}</span>"
        else:
           row["updated_delivery_date"] = "-"

        if row.get("custom_customer_gold") == 'Yes':
            row["custom_customer_gold"] = f"<span style='color: #00B8B8; font-weight: bold;'>{row['custom_customer_gold']}</span>"
        
        if row.get("custom_customer_diamond") == 'Yes':
            row["custom_customer_diamond"] = f"<span style='color: #FFE5B4; font-weight: bold;'>{row['custom_customer_gold']}</span>"

        if row.get("custom_customer_stone") == 'Yes':
            row["custom_customer_stone"] = f"<span style='color: #FFE5B4; font-weight: bold;'>{row['custom_customer_gold']}</span>"

        encoded_form_name = urllib.parse.quote(row["quotation_id"])
        row["quotation_id"] = f'<a href="http://192.168.64.135:8000/app/quotation/{encoded_form_name}" target="_blank">{row["quotation_id"]}</a>'
        
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

        
        status_duration_seconds = int((datetime.now() - status_dt).total_seconds())
        total_status_duration += status_duration_seconds if row["status_duration"] != "-" else 0

        total_diam_wt += row.get("total_diamond_weight_in_grams", 0) or 0
        total_metal_wt += row.get("total_metal_weight", 0) or 0
        total_gem_wt += row.get("total_gemstone_weight_in_grams", 0) or 0
        total_find_wt += row.get("total_finding_weight_per_grams", 0) or 0
        total_other_wt += row.get("other_weight_grams", 0) or 0

        if row["customer"]:
            unique_customers.add(row["customer"])

    
    total_row = {
        "customer": f"<b><span style='color: green;'>Customer: {len(unique_customers)}</span></b>",
        "quotation_id": f"<b><span style='color: green;'>Total Quotations: {total_quotation}</span></b>",
        "time_difference": f"<b><span style='color: green;'>Total: {convert_seconds_to_time(total_seconds)}</span></b>",
        "status_difference": f"<b><span style='color: green;'>{convert_seconds_to_time(total_status_seconds)}</span></b>",
        "total_diamond_weight_in_grams": f"<b><span style='color: green;'>Total: {round(total_diam_wt,2)}</span></b>",
        "total_metal_weight": f"<b><span style='color: green;'>Total: {round(total_metal_wt, 2)}</span></b>",
        "total_gemstone_weight_in_grams": f"<b><span style='color: green;'>Total: {round(total_gem_wt,2)}</span></b>",
        "total_finding_weight_per_grams": f"<b><span style='color: green;'>Total: {round(total_find_wt,2)}</span></b>",
        "other_weight_grams": f"<b><span style='color: green;'>Total: {round(total_other_wt,2)}</span></b>",
        "status_duration": f"<b><span style='color: green;'>Total: {convert_seconds_to_time(total_status_duration)if has_valid_status else '0'}</span></b>",  
    }
    
    data.append(total_row)

    avg_row = {
        "total_diamond_weight_in_grams": f"<b><span style='color: green;'>Avg / Quot: {round(total_diam_wt / total_quotation, 2) if total_quotation else 0}</span></b>",
        "total_metal_weight": f"<b><span style='color: green;'>Avg / Quot: {round(total_metal_wt / total_quotation, 2) if total_quotation else 0}</span></b>",
        "total_gemstone_weight_in_grams": f"<b><span style='color: green;'>Avg / Quot: {round(total_gem_wt / total_quotation, 2) if total_quotation else 0}</span></b>",
        "total_finding_weight_per_grams": f"<b><span style='color: green;'>Avg / Quot: {round(total_find_wt / total_quotation, 2) if total_quotation else 0}</span></b>",
        "other_weight_grams": f"<b><span style='color: green;'>Avg / Quot: {round(total_other_wt / total_quotation, 2) if total_quotation else 0}</span></b>",
        "time_difference": f"<b><span style='color: green;'>Avg / Quot: {convert_seconds_to_time(total_seconds // total_quotation) if total_quotation else '0'}</span></b>",
        "status_duration": f"<b><span style='color: green;'>Avg / Quot: {convert_seconds_to_time(total_status_duration // total_quotation) if total_quotation and has_valid_status else '0'}</span></b>",  
    }
    data.append(avg_row)

    return data


def calculate_status_duration(modified_dt, status):

    if status in ["<span style='color:green; font-weight:bold;'>Submitted</span>", 
                  "<span style='color:inherit; font-weight:bold;'>Cancelled</span>"]:
        return "-", False
    current_dt = datetime.now()
    hrs_count = 0
    temp_dt = modified_dt

    while temp_dt < current_dt:
        temp_dt += timedelta(hours=1)
        if temp_dt.weekday() != 6:  
            hrs_count += 1

    time_difference = current_dt - modified_dt
    time_str = convert_seconds_to_time(time_difference.total_seconds())
    # time_str = convert_seconds_to_time(status_duration.total_seconds())

    exceeded = hrs_count > 5 and status not in ["<span style='color:green; font-weight:bold;'>Submitted</span>", "<span style='color:inherit; font-weight:bold;'>Cancelled</span>"]
    

    return time_str, exceeded

# def convert_seconds_to_time(seconds):
#     days, remainder = divmod(int(seconds), 86400)  
#     hours, remainder = divmod(remainder, 3600)
#     minutes, secs = divmod(remainder, 60)
#     return f"{days} days, {hours} hrs: {minutes} mins: {secs} secs"



def format_status(status):
    status_colors = {
        "Draft": "red",
        "Approved": "green"
    }
    return f"<span style='color:{status_colors.get(status, 'inherit')}; font-weight:bold;'>{status}</span>"

def format_status(status):
    status_mapping = {
        0: "Draft",
        1: "Submitted",
        2: "Cancelled"
    }
    status_colors = {
        0: "red",
        1: "green",
        2: "inherit"
    }
    return f"<span style='color:{status_colors.get(status, 'black')}; font-weight:bold;'>{status_mapping.get(status, 'Unknown')}</span>"

# def convert_seconds_to_time(seconds):
#     hours, remainder = divmod(seconds, 3600)
#     minutes, seconds = divmod(remainder, 60)
#     return f"{hours} hrs {minutes} mins {seconds} secs"


def convert_seconds_to_time(seconds):
    seconds = round(seconds)  
    days, remainder = divmod(seconds, 86400)  
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{days} days, {hours:02} hrs: {minutes:02} mins: {secs:02} secs"

