# Copyright (c) 2026, Your Company
# For license information, please see license.txt

import frappe
from frappe.utils import flt, cint

STATUS_ORDER = ("WIP", "Not Issued", "Received")


def execute(filters=None):
    filters = filters or {}
    return get_columns(), get_data(filters)


def get_columns():
    return [
        {"label": "Department", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 140},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 130},
        {"label": "Current Process", "fieldname": "current_process", "fieldtype": "Data", "width": 130},
        {"label": "Worker Code", "fieldname": "worker_code", "fieldtype": "Link", "options": "Employee", "width": 110},
        {"label": "Worker", "fieldname": "worker", "fieldtype": "Data", "width": 140},
        {"label": "Issue Date", "fieldname": "issue_date", "fieldtype": "Date", "width": 100},
        {"label": "MWO", "fieldname": "batch_no", "fieldtype": "Link", "options": "Manufacturing Work Order", "width": 140},
        {"label": "Design ID", "fieldname": "design_id", "fieldtype": "Data", "width": 120},
        {"label": "Category", "fieldname": "category", "fieldtype": "Data", "width": 110},
        {"label": "PMO", "fieldname": "g_order_no", "fieldtype": "Data", "width": 120},
        {"label": "Customer Code", "fieldname": "old_customer_code", "fieldtype": "Data", "width": 130},
        {"label": "Gold wt", "fieldname": "gold_wt", "fieldtype": "Float", "width": 90, "precision": 3},
        {"label": "Diamond pcs", "fieldname": "diamond_pcs", "fieldtype": "Int", "width": 100},
        {"label": "Diamond Wt", "fieldname": "diamond_wt", "fieldtype": "Float", "width": 100, "precision": 3},
        {"label": "Day Pending", "fieldname": "day_pending", "fieldtype": "Int", "width": 100},
        {"label": "Metal Touch", "fieldname": "metal_touch", "fieldtype": "Data", "width": 100},
        {"label": "Metal Ratio", "fieldname": "metal_purity", "fieldtype": "Data", "width": 130},
        {"label": "Due date", "fieldname": "due_date", "fieldtype": "Date", "width": 100},
        {"label": "Order type", "fieldname": "order_type", "fieldtype": "Data", "width": 100},
    ]


def get_data(filters):
    values = {}

    wanted_status = set(as_list(filters["status"])) if filters.get("status") else None
    dept_filter = set(as_list(filters["department"])) if filters.get("department") else None
    emp_filter = set(as_list(filters["employee"])) if filters.get("employee") else None
    op_filter = set(as_list(filters["operation"])) if filters.get("operation") else None
    has_worker_filter = bool(emp_filter or op_filter)

    # Which parts of the report are needed for these filters?
    need_a = wanted_status is None or bool(wanted_status & {"WIP", "Received"})
    need_b = (
        (wanted_status is None or "Not Issued" in wanted_status)
        and not has_worker_filter  # Not Issued rows have no worker / process
    )
    if not (need_a or need_b):
        return []

    # ---- MWO level conditions (only things that live on the MWO) ----
    conds = []
    if filters.get("from_date"):
        conds.append("mwo.posting_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]
    if filters.get("to_date"):
        conds.append("mwo.posting_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]
    if filters.get("manufacturing_work_order"):
        conds.append("mwo.name in %(manufacturing_work_order)s")
        values["manufacturing_work_order"] = as_list(filters["manufacturing_work_order"])
    if filters.get("order_type"):
        conds.append("mwo.order_type = %(order_type)s")
        values["order_type"] = filters["order_type"]
    where = "".join(f" AND {c}" for c in conds)

    # ---- Query 1: MWO list (one row per MWO, no GROUP BY) ----
    mwo_rows = frappe.db.sql(
        f"""
        SELECT
            mwo.name                        AS batch_no,
            mwo.department                  AS mwo_department,
            mwo.status                      AS mwo_status,
            mwo.posting_date                AS issue_date,
            mwo.item_code                   AS design_id,
            COALESCE(NULLIF(itm.custom_catalogue_image, ''), itm.image)
                                            AS item_image,
            mwo.item_category               AS category,
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
        WHERE mwo.docstatus < 2
          {where}
        """,
        values,
        as_dict=1,
    )
    if not mwo_rows:
        return []

    # ---- Query 2: all Employee IR rows for those MWOs (one flat query) ----
    ir_rows = frappe.db.sql(
        f"""
        SELECT
            eiro.manufacturing_work_order   AS mwo,
            eiro.manufacturing_operation    AS mop,
            ir.name                         AS ir_name,
            ir.type                         AS ir_type,
            ir.employee                     AS employee,
            ir.operation                    AS operation,
            ir.department                   AS department,
            ir.creation                     AS creation
        FROM `tabManufacturing Work Order` mwo
        JOIN `tabEmployee IR Operation` eiro
            ON eiro.manufacturing_work_order = mwo.name
        JOIN `tabEmployee IR` ir
            ON ir.name = eiro.parent
        WHERE mwo.docstatus < 2
          AND ir.docstatus < 2
          {where}
        """,
        values,
        as_dict=1,
    )

    # ---- Build lookups in Python ----
    has_ir = set()          # MWOs having any Employee IR row
    issues = {}             # mwo -> {ir_name: {...}}
    rcv_by_mop = {}         # (employee, operation, mop) -> last receive creation
    rcv_by_mwo = {}         # (employee, operation, mwo) -> last receive creation

    for o in ir_rows:
        has_ir.add(o.mwo)

        if o.ir_type == "Issue":
            doc = issues.setdefault(o.mwo, {}).setdefault(o.ir_name, {
                "employee": o.employee,
                "operation": o.operation,
                "department": o.department,
                "creation": o.creation,
                "mops": [],
            })
            doc["mops"].append(o.mop or "")

        elif o.ir_type == "Receive":
            if o.mop:
                k = (o.employee, o.operation, o.mop)
                if k not in rcv_by_mop or o.creation > rcv_by_mop[k]:
                    rcv_by_mop[k] = o.creation
            k = (o.employee, o.operation, o.mwo)
            if k not in rcv_by_mwo or o.creation > rcv_by_mwo[k]:
                rcv_by_mwo[k] = o.creation

    def is_received(mwo_name, issue):
        for mop in issue["mops"]:
            if mop:
                last = rcv_by_mop.get((issue["employee"], issue["operation"], mop))
            else:
                last = rcv_by_mwo.get((issue["employee"], issue["operation"], mwo_name))
            if last and last >= issue["creation"]:
                return True
        return False

    # ---- Build report rows ----
    rows = []
    for base in mwo_rows:
        mwo_name = base.batch_no
        mwo_dept = base.pop("mwo_department")
        mwo_status = base.pop("mwo_status")

        if mwo_name in issues:
            # Part A: MWO has been issued at least once
            if not need_a:
                continue

            mwo_issues = issues[mwo_name]
            latest = max(i["creation"] for i in mwo_issues.values())

            for issue in mwo_issues.values():
                if issue["creation"] != latest:
                    continue  # only latest Issue per MWO
                if dept_filter and issue["department"] not in dept_filter:
                    continue
                if emp_filter and issue["employee"] not in emp_filter:
                    continue
                if op_filter and issue["operation"] not in op_filter:
                    continue

                row = dict(base)
                row["department"] = issue["department"]
                row["current_process"] = issue["operation"]
                if is_received(mwo_name, issue):
                    row["status"] = "Received"
                    row["worker_code"] = None
                    row["worker"] = None
                else:
                    row["status"] = "WIP"
                    row["worker_code"] = issue["employee"]
                    row["worker"] = None  # filled below
                rows.append(row)

        elif mwo_name not in has_ir:
            # Part B: never issued
            if not need_b or (mwo_status or "") == "Cancelled":
                continue
            if dept_filter and mwo_dept not in dept_filter:
                continue

            row = dict(base)
            row["department"] = mwo_dept
            row["current_process"] = None
            row["worker_code"] = None
            row["worker"] = None
            row["status"] = "Not Issued"
            rows.append(row)

    if wanted_status:
        rows = [r for r in rows if r["status"] in wanted_status]

    if not rows:
        return []

    # ---- Worker names: single query only for WIP workers ----
    emp_ids = list({r["worker_code"] for r in rows if r.get("worker_code")})
    if emp_ids:
        names = dict(frappe.get_all(
            "Employee",
            filters={"name": ["in", emp_ids]},
            fields=["name", "employee_name"],
            as_list=True,
            limit_page_length=0,
        ))
        for r in rows:
            if r.get("worker_code"):
                r["worker"] = names.get(r["worker_code"])

    # sort: latest issue date first, then (stable) by department and status order
    rows.sort(key=lambda r: str(r.get("issue_date") or ""), reverse=True)
    rows.sort(key=lambda r: (
        r.get("department") or "",
        STATUS_ORDER.index(r["status"]),
    ))

    rows.append(get_total_row(rows))
    return rows


def get_total_row(rows):
    """Grand total row: MWO count + sum of Gold wt, Diamond pcs, Diamond wt."""
    return {
        "is_total_row": 1,
        "department": "Total",
        "batch_no": len(rows),
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