import frappe
from frappe import _
from datetime import datetime, timedelta
import urllib.parse

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    totals_row = calculate_totals(data)
    data.append(totals_row)
    return columns, data

def get_columns():
    return [
        {"label": _("Company"), "fieldname": "company", "fieldtype": "Data", "width": 220},
        {"label": _("Branch"), "fieldname": "branch", "fieldtype": "Data", "width": 220},
        {"label": _("Manufacturer"), "fieldname": "manufacturer", "fieldtype": "Data", "width": 150},
        {"label": _("Manufacturing Work Order ID"), "fieldname": "manufacturing_work_order", "fieldtype": "Link", "options": "Manufacturing Work Order", "width": 340},  
        {"label": _("Issued Date"), "fieldname": "issued_date", "fieldtype": "Datetime", "width": 180},
        {"label": _("Issued By"), "fieldname": "issued_by", "fieldtype": "Data", "width": 180},
        {"label": _("Type"), "fieldname": "type", "fieldtype": "Data", "width": 100},
        {"label": _("Transfer Type"), "fieldname": "transfer_type", "fieldtype": "Data", "width": 150},
        {"label": _("Current Department"), "fieldname": "current_department", "fieldtype": "Data", "width": 180},
        {"label": _("Next Department"), "fieldname": "next_department", "fieldtype": "Data", "width": 180},
        {"label": _("Manufacturing Operation"), "fieldname": "manufacturing_operation", "fieldtype": "Data", "width": 200},
        {"label": _("Gross Weight"), "fieldname": "gross_wt", "fieldtype": "Data", "width": 150},
        {"label": _("Department Received ID"), "fieldname": "department_receive", "fieldtype": "Link","options":"Department IR", "width": 200},
        {"label": _("Department Receive Status"), "fieldname": "department_ir_status", "fieldtype": "Data", "width": 190},
        {"label": _("Design Code"), "fieldname": "item_code", "fieldtype": "Data", "width": 150},
        {"label": _("Received Date and Time"), "fieldname": "received_date", "fieldtype": "Datetime", "width": 180},
        {"label": _("Received By"), "fieldname": "receive_by", "fieldtype": "Data", "width": 180},
        {"label": _("Department Issue ID"), "fieldname": "receive_against", "fieldtype": "Link","options":"Department IR", "width": 190},
        {"label": _("Received From"), "fieldname": "receive_from", "fieldtype": "Data", "width": 180},
        {"label": _("Received Department"), "fieldname": "received_department", "fieldtype": "Data", "width": 200},
        {"label": _("Time Between IR"), "fieldname": "time_diff", "fieldtype": "Data", "width": 180},
        
    ]

def get_data(filters):
    """Fetches data using Frappe ORM and processes it in Python"""
    conditions = build_conditions(filters)


    department_ir_list = frappe.get_all(
        "Department IR",
        filters=conditions,
        fields=["name", "company", "manufacturer", "date_time as issued_date", "owner as issued_by", 
                "current_department", "next_department", "type", "transfer_type"]
    )

    department_ir_names = [d["name"] for d in department_ir_list]

    department_ir_operations = frappe.get_all(
        "Department IR Operation",
        filters={"parent": ["in", department_ir_names]},
        fields=["parent", "manufacturing_work_order", "manufacturing_operation", "gross_wt", "net_wt", 
                "diamond_wt", "gemstone_wt", "other_wt", "finding_wt"]
    )

    received_ir = frappe.get_all(
        "Department IR",
        filters={"receive_against": ["in", department_ir_names]},
        fields=["receive_against", "date_time as received_date", "current_department as received_department", "owner as receive_by"]
    )

    manufacturing_operations = frappe.get_all(
        "Manufacturing Operation",
        filters={"department_issue_id": ["in", department_ir_names]},
        fields=["department_issue_id", "department_ir_status", "item_code","department_receive_id"]
    )

    manufacturing_work_orders = frappe.get_all(
        "Manufacturing Work Order",
        filters={"name": ["in", [op["manufacturing_work_order"] for op in department_ir_operations]]},
        fields=["name", "item_code", "branch"]
    )

    department_receive_records = frappe.get_all(
        "Department IR",
        filters={"name": ["in", [mo["department_receive_id"] for mo in manufacturing_operations if mo.get("department_receive_id")]]},
        fields=["name", "current_department","owner","date_time"]
    )

    operation_dict = {op["parent"]: op for op in department_ir_operations}
    received_dict = {rec["receive_against"]: rec for rec in received_ir}
    mo_dict = {mo["department_issue_id"]: mo for mo in manufacturing_operations}
    mwo_dict = {mwo["name"]: mwo for mwo in manufacturing_work_orders}
    dep_rec_dict = {rec["name"]: rec for rec in department_receive_records}

    data = []
    for dr in department_ir_list:
        op = operation_dict.get(dr["name"], {})
        received = received_dict.get(dr["name"], {})
        mo = mo_dict.get(dr["name"], {})
        mwo = mwo_dict.get(op.get("manufacturing_work_order", ""))

        dep_rec = dep_rec_dict.get(mo.get("department_receive_id"), {})

        received_department = dep_rec.get("current_department", "") if mo.get("department_ir_status") == "Received" else ""
        receive_by = dep_rec.get("owner", "") if mo.get("department_ir_status") == "Received" else ""

        final_received_date = dep_rec.get("date_time") if mo.get("department_ir_status") == "Received" else None
        time_diff = compute_time_diff(dr["issued_date"], final_received_date)


        if filters.get("from_date"):
           from_date = datetime.strptime(filters["from_date"], "%Y-%m-%d")
           if dr["issued_date"] < from_date:
                continue
           
        if filters.get("to_date"):
            to_date = datetime.strptime(filters["to_date"], "%Y-%m-%d")
            if dr["issued_date"] > to_date:
                continue

        if filters.get("manufacturing_work_order_id") and op.get("manufacturing_work_order") not in filters["manufacturing_work_order_id"]:
         continue

        if filters.get("branch") and mwo.get("branch") not in filters["branch"]:
          continue



        issued_date = dr["issued_date"]
        received_date = received.get("received_date", None)
        # time_diff = compute_time_diff(issued_date, received_date)

        data.append({
            "company": dr["company"],
            "branch":mwo.get("branch", ""),
            "manufacturer": dr["manufacturer"],
            "issued_date": issued_date,
            "issued_by": dr["issued_by"],
            "type": dr["type"],
            "transfer_type": dr["transfer_type"],
            "current_department": dr["current_department"],
            "next_department": dr["next_department"],
            "manufacturing_work_order": op.get("manufacturing_work_order", "N/A"),
            "manufacturing_operation": op.get("manufacturing_operation", "N/A"),
            "gross_wt": op.get("gross_wt", 0),
            "net_wt": op.get("net_wt", 0),
            "diamond_wt_ct": op.get("diamond_wt", 0),
            "diamond_wt": op.get("diamond_wt", 0) * 0.2,
            "gemstone_wt_ct": op.get("gemstone_wt", 0),
            "gemstone_wt": op.get("gemstone_wt", 0) * 0.2,
            "other_wt": op.get("other_wt", 0),
            "finding_wt": op.get("finding_wt", 0),
            "received_date": final_received_date,
            "receive_from": dr["current_department"] if mo.get("department_ir_status") == "Received" else "",
            "received_department": received_department ,
            "department_ir_status": "Pending" if mo.get("department_ir_status") == "In-Transit" else mo.get("department_ir_status", ""),
            "item_code": mwo.get("item_code", ""),
            "time_diff": time_diff,
            "receive_by": receive_by,
            "department_receive":mo["department_receive_id"],
            "receive_against":mo["department_issue_id"],
        })

    data.sort(key=lambda x: (x["department_ir_status"] != "Pending", x["manufacturing_work_order"], -x["issued_date"].timestamp()), reverse=False)
    # data.sort(key=lambda x: (x["manufacturing_work_order"], -x["issued_date"].timestamp()), reverse=False)

    return data

def compute_time_diff(issued_date, received_date):
    """Calculates time difference in human-readable format"""
    if not issued_date or not received_date:
        return ""
    
    issued_dt = datetime.strptime(str(issued_date), "%Y-%m-%d %H:%M:%S")
    received_dt = datetime.strptime(str(received_date), "%Y-%m-%d %H:%M:%S")
    diff = received_dt - issued_dt

    days, seconds = diff.days, diff.seconds
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    

    return f"{days}d {hours}h:{minutes}m:{seconds}s" if days > 0 else f"{hours}h:{minutes}m:{seconds}s"


def build_conditions(filters):
    """Builds filters for the report"""
    conditions = {"docstatus": 1, "type": "Issue"}

    if filters.get("from_date") or filters.get("to_date"):
        date_conditions = {}

        if filters.get("from_date"):
            date_conditions["date_time"] = (">=", filters["from_date"])  
        
        if filters.get("to_date"):
            date_conditions["date_time"] = ("<=", filters["to_date"])

        related_department_ir_names = frappe.get_all(
            "Department IR",
            filters=date_conditions,
            pluck="name"
        )

        if related_department_ir_names:
            conditions["name"] = ["in", related_department_ir_names]


    if filters.get("company"):
        conditions["company"] = ["in", filters["company"]]



    if filters.get("branch"):
         related_mwo_names = frappe.get_all(
                "Manufacturing Work Order",
                filters={"branch": ["in", filters["branch"]]},
                pluck="name"
    )
         if related_mwo_names:
            conditions["manufacturing_work_order"] = ["in", related_mwo_names]


    if filters.get("manufacturing_work_order_id"):
        related_department_ir_names = frappe.get_all(
            "Department IR Operation",
            filters={"manufacturing_work_order": ["in", filters["manufacturing_work_order_id"]]},
            pluck="parent"
        )
        if related_department_ir_names:
            conditions["name"] = ["in", related_department_ir_names]

    if filters.get("current_department"):
        conditions["current_department"] = ["in", filters["current_department"]]

    if filters.get("next_department"):
        conditions["next_department"] = ["in", filters["next_department"]]


    return conditions



def calculate_totals(data):
    """Compute totals for numeric fields based on the latest entry for each manufacturing work order."""
    
    latest_entries = {}
    
    for row in data:
        mwo = row["manufacturing_work_order"]
        if mwo not in latest_entries or row["issued_date"] > latest_entries[mwo]["issued_date"]:
            latest_entries[mwo] = row

 
    latest_data = latest_entries.values()

    total_gross_wt = sum(row.get("gross_wt", 0) for row in latest_data)
    total_net_wt = sum(row.get("net_wt", 0) for row in latest_data)
    total_diamond_wt_ct = sum(row.get("diamond_wt_ct", 0) for row in latest_data)
    total_diamond_wt = round(sum(float(row.get("diamond_wt", 0) or 0) for row in latest_data), 3)
    total_gemstone_wt_ct = sum(row.get("gemstone_wt_ct", 0) for row in latest_data)
    total_gemstone_wt = sum(row.get("gemstone_wt", 0) for row in latest_data)
    total_other_wt = sum(row.get("other_wt", 0) for row in latest_data)
    total_finding_wt = sum(row.get("finding_wt", 0) for row in latest_data)

    return {
        "company": "<span style='color:green; font-weight:bold;'>TOTAL</span>",
        "gross_wt": f"<span style='color:green; font-weight:bold;'>{total_gross_wt}</span>",
        "net_wt": f"<span style='color:green; font-weight:bold;'>{total_net_wt}</span>",
        "diamond_wt_ct": f"<span style='color:green; font-weight:bold;'>{total_diamond_wt_ct}</span>",
        "diamond_wt": f"<span style='color:green; font-weight:bold;'>{total_diamond_wt}</span>",
        "gemstone_wt_ct": f"<span style='color:green; font-weight:bold;'>{total_gemstone_wt_ct}</span>",
        "gemstone_wt": f"<span style='color:green; font-weight:bold;'>{total_gemstone_wt}</span>",
        "other_wt": f"<span style='color:green; font-weight:bold;'>{total_other_wt}</span>",
        "finding_wt": f"<span style='color:green; font-weight:bold;'>{total_finding_wt}</span>",
    }

