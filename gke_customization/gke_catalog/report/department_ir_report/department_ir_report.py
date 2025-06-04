import frappe
from frappe import _
from frappe import _, cint
from datetime import datetime, timedelta

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
        # {"label": _("Manufacturing Work Order ID"), "fieldname": "manufacturing_work_order", "fieldtype": "Link", "options": "Manufacturing Work Order", "width": 340},
        {"label": _("Issued Date"), "fieldname": "issued_date", "fieldtype": "Datetime", "width": 180},
        {"label": _("Issued By"), "fieldname": "issued_by", "fieldtype": "Data", "width": 180},
        {"label": _("Type"), "fieldname": "type", "fieldtype": "Data", "width": 100},
        {"label": _("Transfer Type"), "fieldname": "transfer_type", "fieldtype": "Data", "width": 150},
        {"label": _("Current Department"), "fieldname": "current_department", "fieldtype": "Data", "width": 180},
        {"label": _("Next Department"), "fieldname": "next_department", "fieldtype": "Data", "width": 180},
        {"label": _("Manufacturing Operation"), "fieldname": "manufacturing_operation", "fieldtype": "Data", "width": 200},
        {"label": _("Gross Weight"), "fieldname": "gross_wt", "fieldtype": "Data", "width": 150},
        {"label": _("Net Weight"), "fieldname": "net_wt", "fieldtype": "Data", "width": 150},
        {"label": _("Finding Weight"), "fieldname": "finding_wt", "fieldtype": "Data", "width": 150},
        {"label": _("Diamond Weight"), "fieldname": "diamond_wt", "fieldtype": "Data", "width": 150},
        {"label": _("Gemstone Weight"), "fieldname": "gemstone_wt", "fieldtype": "Data", "width": 150},
        {"label": _("Diamond Pcs"), "fieldname": "diamond_pcs", "fieldtype": "Data", "width": 150},
        {"label": _("Gemstone Pcs"), "fieldname": "gemstone_pcs", "fieldtype": "Data", "width": 150},
        {"label": _("Department Received ID"), "fieldname": "department_receive", "fieldtype": "Link", "options": "Department IR", "width": 200},
        {"label": _("Department Receive Status"), "fieldname": "department_ir_status", "fieldtype": "Data", "width": 190},
        {"label": _("Design Code"), "fieldname": "item_code", "fieldtype": "Data", "width": 150},
        {"label": _("Received Date and Time"), "fieldname": "received_date", "fieldtype": "Datetime", "width": 180},
        {"label": _("Received By"), "fieldname": "receive_by", "fieldtype": "Data", "width": 180},
        {"label": _("Department Issue ID"), "fieldname": "receive_against", "fieldtype": "Link", "options": "Department IR", "width": 190},
        {"label": _("Received From"), "fieldname": "receive_from", "fieldtype": "Data", "width": 180},
        {"label": _("Received Department"), "fieldname": "received_department", "fieldtype": "Data", "width": 200},
        {"label": _("Time Between IR"), "fieldname": "time_diff", "fieldtype": "Data", "width": 180},
    ]

def get_data(filters):
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
                "diamond_wt", "gemstone_wt", "other_wt", "finding_wt","gemstone_pcs","diamond_pcs"]
    )

    ir_op_map = {}
    for op in department_ir_operations:
        parent = op["parent"]
        if parent not in ir_op_map:
            ir_op_map[parent] = {
                "gross_wt": 0, "net_wt": 0, "diamond_wt": 0, "gemstone_wt": 0, "other_wt": 0, "finding_wt": 0,"diamond_pcs":0,"gemstone_pcs":0,
                "manufacturing_work_order": op["manufacturing_work_order"],
                "manufacturing_operation": op["manufacturing_operation"]
            }
        ir_op_map[parent]["gross_wt"] += op.get("gross_wt", 0)
        ir_op_map[parent]["net_wt"] += op.get("net_wt", 0)
        ir_op_map[parent]["diamond_wt"] += op.get("diamond_wt", 0)
        ir_op_map[parent]["gemstone_wt"] += op.get("gemstone_wt", 0)
        ir_op_map[parent]["other_wt"] += op.get("other_wt", 0)
        ir_op_map[parent]["finding_wt"] += op.get("finding_wt", 0)
        ir_op_map[parent]["diamond_pcs"] += cint(op.get("diamond_pcs", 0))
        ir_op_map[parent]["gemstone_pcs"] += cint(op.get("gemstone_pcs", 0))

    received_ir = frappe.get_all(
        "Department IR",
        filters={"receive_against": ["in", department_ir_names]},
        fields=["receive_against", "date_time as received_date", "current_department as received_department", "owner as receive_by"]
    )

    manufacturing_operations = frappe.get_all(
        "Manufacturing Operation",
        filters={"department_issue_id": ["in", department_ir_names]},
        fields=["department_issue_id", "department_ir_status", "item_code", "department_receive_id"]
    )

    manufacturing_work_orders = frappe.get_all(
        "Manufacturing Work Order",
        filters={"name": ["in", [op["manufacturing_work_order"] for op in department_ir_operations]]},
        fields=["name", "item_code", "branch"]
    )

    department_receive_records = frappe.get_all(
        "Department IR",
        filters={"name": ["in", [mo["department_receive_id"] for mo in manufacturing_operations if mo.get("department_receive_id")]]},
        fields=["name", "current_department", "owner", "date_time"]
    )

    # operation_dict = {op["parent"]: op for op in department_ir_operations}
    received_dict = {rec["receive_against"]: rec for rec in received_ir}
    mo_dict = {mo["department_issue_id"]: mo for mo in manufacturing_operations}
    mwo_dict = {mwo["name"]: mwo for mwo in manufacturing_work_orders}
    dep_rec_dict = {rec["name"]: rec for rec in department_receive_records}

    data = []
    for dr in department_ir_list:
        op = ir_op_map.get(dr["name"], {})
        # op = operation_dict.get(dr["name"], {})
        received = received_dict.get(dr["name"], {})
        mo = mo_dict.get(dr["name"], {})
        mwo = mwo_dict.get(op.get("manufacturing_work_order", ""))
        dep_rec = dep_rec_dict.get(mo.get("department_receive_id"), {})

        received_department = dep_rec.get("current_department", "") if mo.get("department_ir_status") == "Received" else ""
        receive_by = dep_rec.get("owner", "") if mo.get("department_ir_status") == "Received" else ""

        final_received_date = dep_rec.get("date_time") if mo.get("department_ir_status") == "Received" else None
        time_diff = compute_time_diff(dr["issued_date"], final_received_date)

        # if filters.get("to_date") and mo.get("department_ir_status") == "Received":
        #     to_date = datetime.strptime(filters["to_date"], "%Y-%m-%d").date()
        #     if not final_received_date or final_received_date.date() != to_date:
        #         continue

        if filters.get("to_date"):
        # If department_ir_status is NOT 'Received', skip the record
            if mo.get("department_ir_status") != "Received":
                continue
            to_date = datetime.strptime(filters["to_date"], "%Y-%m-%d").date()
            if not final_received_date or final_received_date.date() != to_date:
                continue


        data.append({
            "company": dr["company"],
            "branch": mwo.get("branch", ""),
            "manufacturer": dr["manufacturer"],
            "issued_date": dr["issued_date"],
            "issued_by": dr["issued_by"],
            "type": dr["type"],
            "transfer_type": dr["transfer_type"],
            "current_department": dr["current_department"],
            "next_department": dr["next_department"],
            "manufacturing_work_order": op.get("manufacturing_work_order", "N/A"),
            "manufacturing_operation": op.get("manufacturing_operation", "N/A"),
            "gross_wt": round(op.get("gross_wt", 0), 4),
            "net_wt": round(op.get("net_wt", 0), 4),
            "diamond_pcs": op.get("diamond_pcs", 0),
            "diamond_wt": round(op.get("diamond_wt", 0), 4),
            "gemstone_pcs": op.get("gemstone_pcs", 0),
            "gemstone_wt": round(op.get("gemstone_wt", 0), 4),
            "other_wt": round(op.get("other_wt", 0), 4),
            "finding_wt": round(op.get("finding_wt", 0), 4),
            "received_date": final_received_date,
            "receive_from": dr["current_department"] if mo.get("department_ir_status") == "Received" else "",
            "received_department": received_department,
            "department_ir_status": "Pending" if mo.get("department_ir_status") == "In-Transit" else mo.get("department_ir_status", ""),
            "item_code": mwo.get("item_code", ""),
            "time_diff": time_diff,
            "receive_by": receive_by,
            "department_receive": mo.get("department_receive_id"),
            "receive_against": mo.get("department_issue_id"),
        })

    # data.sort(key=lambda x: (x["department_ir_status"] != "Pending", x["manufacturing_work_order"], -x["issued_date"].timestamp()))
    data.sort(key=lambda x: (x["department_ir_status"] != "Pending", -x["issued_date"].timestamp()))

    return data

def compute_time_diff(issued_date, received_date):
    if not issued_date or not received_date:
        return ""
    diff = received_date - issued_date
    days, seconds = diff.days, diff.seconds
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days}d {hours}h:{minutes}m:{seconds}s" if days > 0 else f"{hours}h:{minutes}m:{seconds}s"

from datetime import datetime, time

def build_conditions(filters):
    conditions = {"docstatus": 1, "type": "Issue"}

    def parse_date(date_str):
        return datetime.strptime(date_str, "%Y-%m-%d").date()

    #  date filter for issued date
    if filters.get("from_date"):
        date = parse_date(filters["from_date"])
        start_date = datetime.combine(date, time.min)
        conditions["date_time"] = ["between", [start_date, datetime.combine(date, time.max)]]

    # Date filter for received_date (to_date)
    # if filters.get("to_date"):
    #     date = parse_date(filters["to_date"])
    #     start_date = datetime.combine(date, time.min)
    #     conditions["received_date"] = ["between", [start_date, datetime.combine(date, time.max)]]

   
    # if filters.get("to_date"):  # Received Date selected
    #     conditions["department_ir_status"] = "Received"

    if filters.get("company"):
        conditions["company"] = ["in", filters["company"]]
    if filters.get("current_department"):
        conditions["current_department"] = ["in", filters["current_department"]]
    if filters.get("next_department"):
        conditions["next_department"] = ["in", filters["next_department"]]

    return conditions




def calculate_totals(data):
   
    total_gross_wt = 0
    total_net_wt = 0
    total_finding_wt = 0
    total_diamond_wt = 0
    total_gemstone_wt = 0
    total_diamond_pcs = 0
    total_gemstone_pcs = 0
    total_other_wt = 0

   
    for row in data:
        total_gross_wt += float(row.get('gross_wt', 0))
        total_net_wt += float(row.get('net_wt', 0))
        total_finding_wt += float(row.get('finding_wt', 0))
        total_diamond_wt += float(row.get('diamond_wt', 0))
        total_gemstone_wt += float(row.get('gemstone_wt', 0))
        total_diamond_pcs += int(row.get('diamond_pcs', 0))
        total_gemstone_pcs += int(row.get('gemstone_pcs', 0))
        total_other_wt += float(row.get('other_wt', 0))

   
    return {
        "company": "<span style='color:green; font-weight:bold;'>TOTAL</span>",
        "gross_wt": f"<span style='color:green; font-weight:bold;'>{round(total_gross_wt, 4)}</span>",
        "net_wt": f"<span style='color:green; font-weight:bold;'>{round(total_net_wt, 4)}</span>",
        "finding_wt": f"<span style='color:green; font-weight:bold;'>{round(total_finding_wt, 4)}</span>",
        "diamond_wt": f"<span style='color:green; font-weight:bold;'>{round(total_diamond_wt, 4)}</span>",
        "gemstone_wt": f"<span style='color:green; font-weight:bold;'>{round(total_gemstone_wt, 4)}</span>",
        "diamond_pcs": f"<span style='color:green; font-weight:bold;'>{total_diamond_pcs}</span>",
        "gemstone_pcs": f"<span style='color:green; font-weight:bold;'>{total_gemstone_pcs}</span>",
        "other_wt": f"<span style='color:green; font-weight:bold;'>{round(total_other_wt, 4)}</span>",
    }
