# Copyright (c) 2026, Your Company
# For license information, please see license.txt

import re
import time

import frappe
from frappe.utils import flt, cint, getdate

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
        {"label": "Is Finding MWO", "fieldname": "is_finding_mwo", "fieldtype": "Data", "width": 140},
        {"label": "Jewelex Batch No", "fieldname": "jewelex_batch_no", "fieldtype": "Data", "width": 150},
        {"label": "Item Code", "fieldname": "design_id", "fieldtype": "Data", "width": 120},
        {"label": "Category", "fieldname": "category", "fieldtype": "Data", "width": 110},
        {"label": "Sub Category", "fieldname": "sub_category", "fieldtype": "Data", "width": 170},
        {"label": "PMO", "fieldname": "g_order_no", "fieldtype": "Data", "width": 210},
        {"label": "Customer Code", "fieldname": "old_customer_code", "fieldtype": "Data", "width": 140},
        {"label": "Gold wt", "fieldname": "gold_wt", "fieldtype": "Float", "width": 100, "precision": 3},
        {"label": "Gross Wt", "fieldname": "gross_wt", "fieldtype": "Float", "width": 100, "precision": 3},
        {"label": "Diamond pcs", "fieldname": "diamond_pcs", "fieldtype": "Int", "width": 125},
        {"label": "Diamond Wt", "fieldname": "diamond_wt", "fieldtype": "Float", "width": 120, "precision": 3},
        {"label": "Day Pending", "fieldname": "day_pending", "fieldtype": "Int", "width": 125},
        {"label": "Metal Touch", "fieldname": "metal_touch", "fieldtype": "Data", "width": 120},
        {"label": "Metal Purity", "fieldname": "metal_purity", "fieldtype": "Data", "width": 120},
        {"label": "Due date", "fieldname": "due_date", "fieldtype": "Date", "width": 110},
        {"label": "Order type", "fieldname": "order_type", "fieldtype": "Data", "width": 120},
    ]


def chunks(items, n=1000):
    items = list(items)
    for i in range(0, len(items), n):
        yield items[i:i + n]


# "Make Receive Entry" dialog jis server function se bharta hai
MRE_METHOD = (
    "jewellery_erpnext.jewellery_erpnext.doctype.manufacturing_operation."
    "manufacturing_operation.get_make_receive_entry_rows"
)
MRE_CACHE_SECONDS = 60
_mre_cache = {}        # mop -> (time, rows)   (har worker process ka apna, 60 sec)


def _make_receive_rows(fn, mop):
    """Dialog wali function se ek MOP ki rows (kuch bhi galat ho to khali list)."""
    now = time.time()
    hit = _mre_cache.get(mop)
    if hit and now - hit[0] < MRE_CACHE_SECONDS:
        return hit[1]

    rows = []
    try:
        res = fn(manufacturing_operation=mop)
        data = res.get("message", res) if isinstance(res, dict) else {}
        rows = (data or {}).get("rows") or []
    except Exception:
        rows = []
    finally:
        # Function msgprint karta hai ("No active Stock Reservation Entries...");
        # report me popup nahi chahiye.
        frappe.clear_messages()

    if len(_mre_cache) > 5000:
        _mre_cache.clear()
    _mre_cache[mop] = (now, rows)
    return rows


def get_balances_from_dialog(mwo_mop):
    """MWO-wise Gold wt, Diamond wt, Diamond pcs: "Make Receive Entry" dialog ke
    "Available to Receive" ke barabar (usi function se, MWO ki current MOP par).

        Gold wt     = Metal + Finding rows ki available_to_receive_qty
        Diamond wt  = Diamond rows ki available_to_receive_qty
        Diamond pcs = Diamond rows ki available_to_receive_pcs
    Gemstone ginte nahi.

    mwo_mop: {mwo name: uski current MOP}
    """
    fn = frappe.get_attr(MRE_METHOD)        # nahi mila to exception -> caller fallback use karega

    # Function sirf unhi MWO par chalate hain jinki active Stock Reservation Entry hai
    # (baaki ke liye dialog "No active ... found" deta hai, yani 0).
    with_mop = [m for m, mop in mwo_mop.items() if mop]
    active = set()
    for part in chunks(with_mop):
        active.update(frappe.db.sql(
            """
            SELECT DISTINCT manufacturing_work_order
            FROM `tabStock Reservation Entry`
            WHERE docstatus = 1
              AND status NOT IN %(inactive)s
              AND manufacturing_work_order IN %(m)s
            """,
            {"m": tuple(part), "inactive": INACTIVE_SRE_STATUS},
            pluck="manufacturing_work_order",
        ))

    raw = {}
    for mwo in active:
        raw[mwo] = _make_receive_rows(fn, mwo_mop[mwo])

    item_codes = list({r.get("item_code") for rows in raw.values() for r in rows if r.get("item_code")})
    groups = {}
    for part in chunks(item_codes):
        for name, group in frappe.db.sql(
            "SELECT name, item_group FROM `tabItem` WHERE name IN %(i)s",
            {"i": tuple(part)},
        ):
            groups[name] = group

    out = {}
    for mwo, rows in raw.items():
        d = {"gold_wt": 0.0, "diamond_wt": 0.0, "diamond_pcs": 0.0}
        for r in rows:
            g = (groups.get(r.get("item_code")) or "").lower()
            qty = flt(r.get("available_to_receive_qty"))
            pcs = flt(r.get("available_to_receive_pcs"))
            if g.startswith("metal") or g.startswith("finding"):
                d["gold_wt"] += max(qty, 0)
            elif g.startswith("diamond"):
                d["diamond_wt"] += max(qty, 0)
                d["diamond_pcs"] += max(pcs, 0)
        out[mwo] = d
    return out


# Reservation jo ab "active" nahi hain
INACTIVE_SRE_STATUS = ("Cancelled", "Closed", "Delivered", "Draft")


def get_balances_from_reservations(mwo_names):
    """MWO-wise Gold wt, Diamond wt, Diamond pcs.

    "Make Receive Entry" dialog ke "Available to Receive" jaisa: MWO ki ACTIVE
    Stock Reservation Entries (submitted, cancelled/closed/delivered nahi).
        available     = reserved_qty - delivered_qty
        Gold wt       = Metal + Finding item groups
        Diamond wt    = Diamond item groups
        Diamond pcs   = unhi diamond items + warehouse ke stock entry lines ka net pcs
    Gemstone ginte nahi. Active reservation na ho to sab 0.
    """
    out = {}
    names = list(mwo_names)
    if not names:
        return out
    name_set = set(names)

    # 1) Active Stock Reservation Entries -> weights
    diamond_keys = {}      # mwo -> {(item_code, warehouse)}
    for part in chunks(names):
        sres = frappe.db.sql(
            """
            SELECT sre.manufacturing_work_order AS mwo,
                   sre.item_code                AS item_code,
                   sre.warehouse                AS warehouse,
                   sre.reserved_qty             AS reserved_qty,
                   sre.delivered_qty            AS delivered_qty,
                   i.item_group                 AS item_group
            FROM `tabStock Reservation Entry` sre
            JOIN `tabItem` i ON i.name = sre.item_code
            WHERE sre.docstatus = 1
              AND sre.status NOT IN %(inactive)s
              AND sre.manufacturing_work_order IN %(m)s
            """,
            {"m": tuple(part), "inactive": INACTIVE_SRE_STATUS},
            as_dict=1,
        )
        for r in sres:
            qty = flt(r.reserved_qty) - flt(r.delivered_qty)
            if round(qty, 3) <= 0:
                continue
            g = (r.item_group or "").lower()
            d = out.setdefault(r.mwo, {"gold_wt": 0.0, "diamond_wt": 0.0, "diamond_pcs": 0.0})
            if g.startswith("metal") or g.startswith("finding"):
                d["gold_wt"] += qty
            elif g.startswith("diamond"):
                d["diamond_wt"] += qty
                diamond_keys.setdefault(r.mwo, set()).add((r.item_code, r.warehouse))

    # 2) Diamond pcs: sirf un MWOs ke liye jinke active diamond reservations hain
    if diamond_keys:
        net_pcs = {}       # (mwo, item, warehouse) -> net pcs
        for part in chunks(list(diamond_keys.keys())):
            lines = frappe.db.sql(
                """
                SELECT
                    se.manufacturing_work_order AS mwo,
                    TRIM(IFNULL(sed.custom_manufacturing_work_order, '')) AS line_mwo,
                    sed.item_code               AS item_code,
                    sed.s_warehouse             AS s_warehouse,
                    sed.t_warehouse             AS t_warehouse,
                    CAST(IFNULL(NULLIF(sed.pcs, ''), 0) AS DECIMAL(20, 3)) AS pcs
                FROM `tabStock Entry Detail` sed
                JOIN `tabStock Entry` se ON se.name = sed.parent
                JOIN `tabItem` i ON i.name = sed.item_code
                WHERE se.docstatus = 1
                  AND se.manufacturing_work_order IN %(m)s
                  AND i.item_group LIKE 'Diamond%%'
                """,
                {"m": tuple(part)},
                as_dict=1,
            )
            for r in lines:
                pcs = flt(r.pcs)

                # Line par apna MWO ho to wahi malik, nahi to entry ke header ka MWO
                owner = r.mwo
                if r.line_mwo and r.line_mwo != r.mwo:
                    parts = [x.strip() for x in re.split(r"[,;\n]+", r.line_mwo) if x.strip()]
                    if not parts or r.mwo in parts:
                        owner = r.mwo
                    elif len(parts) == 1:
                        owner = parts[0]
                    else:
                        continue
                if owner not in name_set:
                    continue

                if r.t_warehouse:
                    k = (owner, r.item_code, r.t_warehouse)
                    net_pcs[k] = net_pcs.get(k, 0.0) + pcs
                if r.s_warehouse:
                    k = (owner, r.item_code, r.s_warehouse)
                    net_pcs[k] = net_pcs.get(k, 0.0) - pcs

        for mwo, keys in diamond_keys.items():
            total = 0.0
            for (item, wh) in keys:
                total += max(net_pcs.get((mwo, item, wh), 0.0), 0.0)
            out[mwo]["diamond_pcs"] = total
    return out


def get_data(filters):
    values = {"excluded_status": tuple(EXCLUDE_MWO_STATUS)}

    wanted_status = set(as_list(filters["status"])) if filters.get("status") else None
    dept_filter = as_list(filters["department"]) if filters.get("department") else None
    emp_filter = set(as_list(filters["employee"])) if filters.get("employee") else None
    op_filter = set(as_list(filters["operation"])) if filters.get("operation") else None
    has_worker_filter = bool(emp_filter or op_filter)
    finding_filter = set(as_list(filters["is_finding_mwo"])) if filters.get("is_finding_mwo") else set()

    # ---- MWO level conditions ----
    conds = ["mwo.status NOT IN %(excluded_status)s"]

    # ---- Date filter: "Issue Date" column par ----
    # Issue Date = latest Employee IR (Issue) ki date (WIP / Received).
    # Jinko Issue nahi hua unki dikhne wali date MWO ki posting date hai.
    # Pehle candidate MWOs nikalte hain: (range me Employee IR Issue) YA (range me posting date).
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    if from_date:
        values["from_date"] = from_date
    if to_date:
        values["to_date"] = to_date

    if from_date or to_date:
        issue_conds = [
            "ir.docstatus = 1",
            "ir.type = 'Issue'",
            "IFNULL(eiro.manufacturing_work_order, '') != ''",
        ]
        if from_date:
            issue_conds.append("COALESCE(ir.date_time, ir.creation) >= %(from_date)s")
        if to_date:
            issue_conds.append("COALESCE(ir.date_time, ir.creation) < DATE_ADD(%(to_date)s, INTERVAL 1 DAY)")
        issued_mwos = frappe.db.sql(
            f"""
            SELECT DISTINCT eiro.manufacturing_work_order
            FROM `tabEmployee IR Operation` eiro
            JOIN `tabEmployee IR` ir ON ir.name = eiro.parent
            WHERE {' AND '.join(issue_conds)}
            """,
            values,
            pluck="manufacturing_work_order",
        )

        posted_conds = []
        if from_date:
            posted_conds.append("mwo.posting_date >= %(from_date)s")
        if to_date:
            posted_conds.append("mwo.posting_date <= %(to_date)s")
        date_cond = "(" + " AND ".join(posted_conds) + ")"
        if issued_mwos:
            date_cond = f"({date_cond} OR mwo.name IN %(issued_mwos)s)"
            values["issued_mwos"] = tuple(issued_mwos)
        conds.append(date_cond)

    if dept_filter:
        conds.append("mwo.department IN %(department)s")
        values["department"] = tuple(dept_filter)
    if filters.get("manufacturing_work_order"):
        conds.append("mwo.name IN %(manufacturing_work_order)s")
        values["manufacturing_work_order"] = tuple(as_list(filters["manufacturing_work_order"]))
    if filters.get("order_type"):
        conds.append("mwo.order_type = %(order_type)s")
        values["order_type"] = filters["order_type"]
    # Is Finding MWO: sirf "Yes" ya sirf "No" select ho to filter lagta hai (dono ya khali = sab)
    if finding_filter == {"Yes"}:
        conds.append("IFNULL(mwo.is_finding_mwo, 0) = 1")
    elif finding_filter == {"No"}:
        conds.append("IFNULL(mwo.is_finding_mwo, 0) = 0")
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
            cmop.gross_wt                   AS cur_gross_wt,
            pmop.gross_wt                   AS prev_gross_wt,
            mwo.posting_date                AS issue_date,
            mwo.tree_number                 AS tree_number,
            IF(mwo.is_finding_mwo = 1, 'Yes', 'No')
                                            AS is_finding_mwo,
            mwo.jewelex_batch_no            AS jewelex_batch_no,
            mwo.item_code                   AS design_id,
            COALESCE(NULLIF(itm.custom_catalogue_image, ''), itm.image)
                                            AS item_image,
            mwo.item_category               AS category,
            mwo.item_sub_category           AS sub_category,
            mwo.manufacturing_order         AS g_order_no,
            cust.old_customer_code          AS old_customer_code,
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

    # Gold wt / Diamond wt / Diamond pcs (Make Receive Entry ke "Available to Receive" jaise)
    mwo_mop = {r.batch_no: r.cur_mop for r in mwo_rows}
    try:
        balances = get_balances_from_dialog(mwo_mop)
    except Exception:
        # Dialog wali function na mile / chale to reservation + stock entry wala tareeka
        frappe.log_error(title="Everyday Work Report: Make Receive Entry function use nahi ho payi")
        balances = get_balances_from_reservations(list(mwo_mop.keys()))

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
        cur_gross_wt = base.pop("cur_gross_wt")
        prev_gross_wt = base.pop("prev_gross_wt")

        row = dict(base)
        bal = balances.get(base.batch_no, {})
        row["gold_wt"] = round(bal.get("gold_wt", 0.0), 3)
        row["diamond_wt"] = round(bal.get("diamond_wt", 0.0), 3)
        row["diamond_pcs"] = int(round(bal.get("diamond_pcs", 0.0)))
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

        # Gross Wt: usi MOP ka jiske Employee IR se status nikla hai (nahi to current MOP ka)
        if src_mop and src_mop == prev_mop and src_mop != cur_mop:
            row["gross_wt"] = prev_gross_wt
        else:
            row["gross_wt"] = cur_gross_wt
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

        # Dikhne wali Issue Date range ke andar honi chahiye
        if from_date or to_date:
            shown = getdate(row["issue_date"]) if row.get("issue_date") else None
            if (
                shown is None
                or (from_date and shown < getdate(from_date))
                or (to_date and shown > getdate(to_date))
            ):
                continue

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

    # Total row Frappe ka built-in frozen row dikhata hai (JS ke get_datatable_options me
    # PMO ka distinct count aur sums set hote hain), isliye yahan total row nahi jodte.
    return rows


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