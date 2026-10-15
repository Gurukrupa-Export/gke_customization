# Copyright (c) 2026, Your Company
# For license information, please see license.txt

import frappe
from frappe.utils import flt, cint

STATUS_ORDER = ("WIP", "Not Issued", "Received", "")

# Jin departments me Employee Issue/Receive hota hi nahi, wahan status blank rahega.
# (Department ke naam ki shuruaat se match hota hai, e.g. "Tagging - GEPL")
NO_EMPLOYEE_IR_DEPARTMENTS = ("Tagging",)


def has_no_employee_ir(department):
    return any((department or "").startswith(p) for p in NO_EMPLOYEE_IR_DEPARTMENTS)

# Ye MWO report me nahi aayenge. "Completed" = MWO submitted, isliye wo report me dikhta hai.
EXCLUDE_MWO_STATUS = ("Closed", "Stopped")

# Department-wise concept:
#   Har MWO sirf apne PRESENT department (MWO.department) me dikhta hai.
#   Status MWO ki present MOP (MWO.manufacturing_operation) ke submitted Employee IR se:
#     Issue hua, Receive nahi hua     -> WIP
#     Issue hi nahi hua               -> Not Issued
#     Issue hoke Receive ho gaya      -> Received (MWO abhi isi department me hai)


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    fit_column_widths(columns, data)

    # Text/date columns left align, sirf numbers right align
    for col in columns:
        col["align"] = "right" if col.get("fieldtype") in ("Float", "Int", "Currency") else "left"

    return columns, data


def fit_column_widths(columns, data):
    """Har column ki width header aur data ki sabse lambi value ke hisaab se set karta hai,
    taaki user ko column expand na karna pade."""
    PX_PER_CHAR = 10     # ek character ki approx width (px)
    CELL_PAD = 40        # cell ka padding
    HEADER_PAD = 56      # header ke sort arrow / menu ke liye jagah
    MIN_W, MAX_W = 90, 500

    for col in columns:
        fn = col["fieldname"]
        longest = 0
        for r in data:
            v = r.get(fn)
            if v is None or v == "":
                continue
            if col.get("fieldtype") == "Float":
                text = "{:,.{p}f}".format(flt(v), p=col.get("precision") or 3)
            else:
                text = str(v)
            longest = max(longest, len(text))

        content_w = longest * PX_PER_CHAR + CELL_PAD
        header_w = len(col["label"]) * PX_PER_CHAR + HEADER_PAD
        col["width"] = int(min(max(content_w, header_w, MIN_W), MAX_W))


def get_columns():
    return [
        {"label": "Department", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 270},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 110},
        {"label": "Operation", "fieldname": "current_process", "fieldtype": "Data", "width": 180},
        {"label": "Employee", "fieldname": "worker_code", "fieldtype": "Link", "options": "Employee", "width": 130},
        {"label": "Employee Name", "fieldname": "worker", "fieldtype": "Data", "width": 200},
        {"label": "Issue Date", "fieldname": "issue_date", "fieldtype": "Date", "width": 110},
        {"label": "MWO", "fieldname": "batch_no", "fieldtype": "Link", "options": "Manufacturing Work Order", "width": 300},
        {"label": "Tree Number", "fieldname": "tree_number", "fieldtype": "Data", "width": 130},
        {"label": "Item Code", "fieldname": "design_id", "fieldtype": "Data", "width": 120},
        {"label": "Category", "fieldname": "category", "fieldtype": "Data", "width": 110},
        {"label": "Sub Category", "fieldname": "sub_category", "fieldtype": "Data", "width": 170},
        {"label": "PMO", "fieldname": "g_order_no", "fieldtype": "Data", "width": 210},
        {"label": "Customer Code", "fieldname": "old_customer_code", "fieldtype": "Data", "width": 140},
        {"label": "Gold wt", "fieldname": "gold_wt", "fieldtype": "Float", "width": 100, "precision": 3},
        {"label": "Diamond pcs", "fieldname": "diamond_pcs", "fieldtype": "Int", "width": 125},
        {"label": "Diamond Wt", "fieldname": "diamond_wt", "fieldtype": "Float", "width": 120, "precision": 3},
        {"label": "Day Pending", "fieldname": "day_pending", "fieldtype": "Int", "width": 125},
        {"label": "Metal Touch", "fieldname": "metal_touch", "fieldtype": "Data", "width": 120},
        {"label": "Metal Purity", "fieldname": "metal_purity", "fieldtype": "Data", "width": 120},
        {"label": "Due date", "fieldname": "due_date", "fieldtype": "Date", "width": 110},
        {"label": "Order type", "fieldname": "order_type", "fieldtype": "Data", "width": 120},
    ]


def get_data(filters):
    values = {"excluded_status": tuple(EXCLUDE_MWO_STATUS)}

    wanted_status = set(as_list(filters["status"])) if filters.get("status") else None
    dept_filter = as_list(filters["department"]) if filters.get("department") else None
    emp_filter = set(as_list(filters["employee"])) if filters.get("employee") else None
    op_filter = set(as_list(filters["operation"])) if filters.get("operation") else None
    has_worker_filter = bool(emp_filter or op_filter)

    # ---- MWO level conditions ----
    conds = ["mwo.status NOT IN %(excluded_status)s"]
    if filters.get("from_date"):
        conds.append("mwo.posting_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]
    if filters.get("to_date"):
        conds.append("mwo.posting_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]
    if dept_filter:
        conds.append("mwo.department IN %(department)s")
        values["department"] = tuple(dept_filter)
    if filters.get("manufacturing_work_order"):
        conds.append("mwo.name IN %(manufacturing_work_order)s")
        values["manufacturing_work_order"] = tuple(as_list(filters["manufacturing_work_order"]))
    if filters.get("order_type"):
        conds.append("mwo.order_type = %(order_type)s")
        values["order_type"] = filters["order_type"]
    where = "".join(f" AND {c}" for c in conds)

    # ---- Query 1: MWO list (ek MWO = ek row) ----
    mwo_rows = frappe.db.sql(
        f"""
        SELECT
            mwo.name                        AS batch_no,
            mwo.department                  AS mwo_department,
            mwo.manufacturing_operation     AS cur_mop,
            cmop.status                     AS cur_mop_status,
            cmop.previous_mop               AS prev_mop,
            pmop.department                 AS prev_mop_dept,
            mwo.posting_date                AS issue_date,
            mwo.tree_number                 AS tree_number,
            mwo.item_code                   AS design_id,
            COALESCE(NULLIF(itm.custom_catalogue_image, ''), itm.image)
                                            AS item_image,
            mwo.item_category               AS category,
            mwo.item_sub_category           AS sub_category,
            mwo.manufacturing_order         AS g_order_no,
            cust.old_customer_code          AS old_customer_code,
            mwo.metal_weight                AS gold_wt,
            mwo.diamond_pcs                 AS diamond_pcs,
            mwo.diamond_wt                  AS diamond_wt,
            mwo.due_days                    AS day_pending,
            mwo.metal_touch                 AS metal_touch,
            mwo.metal_purity                AS metal_purity,
            mwo.delivery_date               AS due_date,
            mwo.order_type                  AS order_type
        FROM `tabManufacturing Work Order` mwo
        LEFT JOIN `tabParent Manufacturing Order` pmo
            ON pmo.name = mwo.manufacturing_order
        LEFT JOIN `tabCustomer` cust
            ON cust.name = pmo.ref_customer
        LEFT JOIN `tabItem` itm
            ON itm.name = mwo.item_code
        LEFT JOIN `tabManufacturing Operation` cmop
            ON cmop.name = mwo.manufacturing_operation
        LEFT JOIN `tabManufacturing Operation` pmop
            ON pmop.name = cmop.previous_mop
        WHERE mwo.docstatus < 2
          {where}
        """,
        values,
        as_dict=1,
    )
    if not mwo_rows:
        return []

    # ---- Query 2: present MOP ke submitted Employee IR (Issue / Receive) ----
    # Receive ke baad usi department me nayi khali MOP banti hai, isliye
    # usi department ki previous MOP ke Employee IR bhi dekhte hain.
    mop_set = set()
    for r in mwo_rows:
        if r.cur_mop:
            mop_set.add(r.cur_mop)
        if r.prev_mop and r.prev_mop_dept == r.mwo_department:
            mop_set.add(r.prev_mop)
    cur_mops = list(mop_set)
    last_issue = {}   # mop -> latest submitted Issue
    last_recv = {}    # mop -> latest submitted Receive time

    for i in range(0, len(cur_mops), 1000):
        part = cur_mops[i:i + 1000]
        ir_rows = frappe.db.sql(
            """
            SELECT
                eiro.manufacturing_operation        AS mop,
                ir.type                             AS ir_type,
                ir.employee                         AS employee,
                ir.operation                        AS operation,
                COALESCE(ir.date_time, ir.creation) AS ir_time
            FROM `tabEmployee IR Operation` eiro
            JOIN `tabEmployee IR` ir
                ON ir.name = eiro.parent
            WHERE ir.docstatus = 1
              AND eiro.manufacturing_operation IN %(mops)s
            ORDER BY COALESCE(ir.date_time, ir.creation) ASC
            """,
            {"mops": tuple(part)},
            as_dict=1,
        )
        for o in ir_rows:
            if o.ir_type == "Issue":
                last_issue[o.mop] = o        # ASC order => last wins = latest
            elif o.ir_type == "Receive":
                last_recv[o.mop] = o.ir_time

    # ---- Build report rows ----
    rows = []
    for base in mwo_rows:
        mwo_dept = base.pop("mwo_department")
        cur_mop = base.pop("cur_mop")
        cur_mop_status = base.pop("cur_mop_status")
        prev_mop = base.pop("prev_mop")
        prev_mop_dept = base.pop("prev_mop_dept")

        row = dict(base)
        row["department"] = mwo_dept
        row["worker"] = None  # naam neeche sirf WIP rows ke liye bharta hai

        # Employee IR kis MOP par dekhna hai:
        #   1) current MOP par Issue hai  -> wahi
        #   2) nahi hai, current MOP Finished nahi hai, aur usi department ki previous MOP
        #      par Issue hai (Receive ke baad nayi khali MOP bani)  -> previous MOP
        src_mop = None
        if cur_mop and last_issue.get(cur_mop):
            src_mop = cur_mop
        elif (
            prev_mop
            and cur_mop_status != "Finished"
            and prev_mop_dept == mwo_dept
            and last_issue.get(prev_mop)
        ):
            src_mop = prev_mop

        iss = last_issue.get(src_mop) if src_mop else None
        if iss:
            row["current_process"] = iss.operation
            row["issue_date"] = iss.ir_time.date() if hasattr(iss.ir_time, "date") else iss.ir_time
            recv_time = last_recv.get(src_mop)
            if recv_time and recv_time >= iss.ir_time:
                row["status"] = "Received"
                row["worker_code"] = None
            else:
                row["status"] = "WIP"
                row["worker_code"] = iss.employee

            if emp_filter and iss.employee not in emp_filter:
                continue
            if op_filter and iss.operation not in op_filter:
                continue
        else:
            # Not Issued: process / worker nahi hota
            if has_worker_filter:
                continue
            # Current MOP Finished, ya aisa department jahan Employee IR hota hi nahi
            # (jaise Tagging) => status blank
            if cur_mop_status == "Finished" or has_no_employee_ir(mwo_dept):
                row["status"] = ""
            else:
                row["status"] = "Not Issued"
            row["current_process"] = None
            row["worker_code"] = None

        if wanted_status and row["status"] not in wanted_status:
            continue
        rows.append(row)

    if not rows:
        return []

    # ---- Worker ka naam sirf WIP rows ke liye (single query) ----
    emp_ids = list({r["worker_code"] for r in rows if r.get("status") == "WIP" and r.get("worker_code")})
    if emp_ids:
        names = dict(frappe.get_all(
            "Employee",
            filters={"name": ["in", emp_ids]},
            fields=["name", "employee_name"],
            as_list=True,
            limit_page_length=0,
        ))
        for r in rows:
            if r.get("status") == "WIP" and r.get("worker_code"):
                r["worker"] = names.get(r["worker_code"])

    # sort: department, status order, phir latest issue date pehle
    rows.sort(key=lambda r: str(r.get("issue_date") or ""), reverse=True)
    rows.sort(key=lambda r: (
        r.get("department") or "",
        STATUS_ORDER.index(r["status"]),
    ))

    rows.append(get_total_row(rows))
    return rows


def get_total_row(rows):
    """Grand total row: distinct PMO count + sum of Gold wt, Diamond pcs, Diamond wt."""
    return {
        "is_total_row": 1,
        "department": "Total",
        "g_order_no": len({r.get("g_order_no") for r in rows if r.get("g_order_no")}),
        "gold_wt": flt(sum(flt(r.get("gold_wt")) for r in rows), 3),
        "diamond_pcs": sum(cint(r.get("diamond_pcs")) for r in rows),
        "diamond_wt": flt(sum(flt(r.get("diamond_wt")) for r in rows), 3),
    }


def as_list(value):
    if isinstance(value, list):
        return value

    if isinstance(value, str):
        try:
            parsed = frappe.parse_json(value)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass

        return [value]

    return [value]