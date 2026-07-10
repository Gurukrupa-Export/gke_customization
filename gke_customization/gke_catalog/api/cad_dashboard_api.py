# # ye h new sketch api

import frappe


import calendar
from datetime import date


import json
import calendar
from datetime import date
import json

from frappe.utils import getdate, get_first_day, get_last_day, add_months



def get_month_date_range(year, month):
    from_date = date(int(year), int(month), 1)
    last_day = calendar.monthrange(int(year), int(month))[1]
    to_date = date(int(year), int(month), last_day)
    return from_date, to_date


# ============================================================
# COMMON FILTER BUILDER (shared by all endpoints)
# ============================================================
def _build_filters(company=None, branch=None, department=None, design_by=None,
                    merchandiser=None, setting_type=None, year=None, month=None):
    """
    Builds the SQL filter string + param list safely (using %s placeholders
    instead of f-string interpolation, to avoid SQL injection).
    Returns: (filter_sql, params_list, designer_filters_dict)
    """

    filters = ""
    params = []

    if company:
        filters += " AND so.company=%s"
        params.append(company)

    if branch:
        filters += " AND so.branch=%s"
        params.append(branch)

    if department:
        filters += " AND so.department=%s"
        params.append(department)

    if merchandiser:
        filters += " AND so.merchandiser=%s"
        params.append(merchandiser)

    if setting_type:
        filters += " AND so.setting_type=%s"
        params.append(setting_type)

    if year and month:
        from_date, to_date = get_month_date_range(year, month)
        filters += " AND DATE(so.creation) BETWEEN %s AND %s"
        params.extend([from_date, to_date])

    if design_by:
        designer_filters = {
            "r":      (" AND r.designer=%s", [design_by]),
            "h":      (" AND h.designer=%s", [design_by]),
            "hod":    (" AND hod.designer=%s", [design_by]),
            "design": (" AND design.designer=%s", [design_by]),
            "emp":    (" AND emp.name=%s", [design_by]),
        }
    else:
        designer_filters = {
            "r": ("", []),
            "h": ("", []),
            "hod": ("", []),
            "design": ("", []),
            "emp": ("", []),
        }

    return filters, params, designer_filters


# ============================================================
# 1. TOTAL / APPROVED / REJECTED / RATES  (fastest -> load first)
# ============================================================
@frappe.whitelist()
def get_sketch_summary(company=None, branch=None, department=None, design_by=None,
                        merchandiser=None, setting_type=None, year=None, month=None):

    filters, params, designer_filters = _build_filters(
        company, branch, department, design_by, merchandiser, setting_type, year, month
    )

    filter_hod_sql, filter_hod_params = designer_filters["hod"]
    filter_r_sql, filter_r_params = designer_filters["r"]
    filter_h_sql, filter_h_params = designer_filters["h"]

    approved = frappe.db.sql(f"""
        SELECT SUM(IFNULL(hod.approved,0))
        FROM `tabSketch Order` so
        INNER JOIN `tabFinal Sketch Approval HOD` hod ON hod.parent = so.name
        WHERE hod.approved > 0
        {filters}{filter_hod_sql}
    """, params + filter_hod_params)[0][0] or 0

    rejected = frappe.db.sql(f"""
        SELECT SUM(
            COALESCE(r.approved,0) + COALESCE(r.reject,0) - COALESCE(h.approved,0)
        )
        FROM `tabSketch Order` so
        LEFT JOIN `tabRough Sketch Approval` r ON r.parent = so.name
        LEFT JOIN `tabFinal Sketch Approval HOD` h ON h.parent = so.name
        WHERE 1=1
        {filters}{filter_r_sql}{filter_h_sql}
    """, params + filter_r_params + filter_h_params)[0][0] or 0

    total = approved + rejected

    return {
        "total_sketch": total,
        "approved_sketch": approved,
        "rejected_sketch": rejected,
        "approval_rate": round((approved * 100) / (approved + rejected), 2) if approved + rejected else 0,
        "rejection_rate": round((rejected * 100) / (approved + rejected), 2) if approved + rejected else 0,
    }


# ============================================================
# 2. GOLD / DIAMOND WEIGHTS
# ============================================================
@frappe.whitelist()
def get_sketch_weights(company=None, branch=None, department=None, design_by=None,
                        merchandiser=None, setting_type=None, year=None, month=None):

    filters, params, designer_filters = _build_filters(
        company, branch, department, design_by, merchandiser, setting_type, year, month
    )

    filter_hod_sql, filter_hod_params = designer_filters["hod"]

    weights = frappe.db.sql(f"""
        SELECT
            SUM(IFNULL(cmo.gold_wt_approx,0)) AS gold_weight,
            SUM(IFNULL(cmo.diamond_wt_approx,0)) AS diamond_weight
        FROM `tabSketch Order` so
        INNER JOIN `tabFinal Sketch Approval CMO` cmo ON cmo.parent = so.name
        INNER JOIN `tabFinal Sketch Approval HOD` hod ON hod.parent = so.name
        WHERE hod.approved > 0
        {filters}{filter_hod_sql}
    """, params + filter_hod_params, as_dict=True)[0]

    return {
        "gold_weight": weights.gold_weight or 0,
        "diamond_weight": weights.diamond_weight or 0,
    }


# ============================================================
# 3. DAILY TREND
# ============================================================
@frappe.whitelist()
def get_daily_trend(company=None, branch=None, department=None, design_by=None,
                     merchandiser=None, setting_type=None, year=None, month=None):

    filters, params, designer_filters = _build_filters(
        company, branch, department, design_by, merchandiser, setting_type, year, month
    )

    filter_r_sql, filter_r_params = designer_filters["r"]
    filter_h_sql, filter_h_params = designer_filters["h"]

    trend = frappe.db.sql(f"""
        SELECT
            DATE(so.creation) date,
            SUM(IFNULL(h.approved,0)) approved,
            SUM(
                COALESCE(r.approved,0) + COALESCE(r.reject,0) - COALESCE(h.approved,0)
            ) rejected
        FROM `tabSketch Order` so
        LEFT JOIN `tabRough Sketch Approval` r ON r.parent = so.name
        LEFT JOIN `tabFinal Sketch Approval HOD` h ON h.parent = so.name
        WHERE 1=1
        {filters}{filter_r_sql}{filter_h_sql}
        GROUP BY DATE(so.creation)
        ORDER BY DATE(so.creation)
    """, params + filter_r_params + filter_h_params, as_dict=True)

    return trend


# ============================================================
# 4. CATEGORY WISE
# ============================================================
@frappe.whitelist()
def get_category_wise(company=None, branch=None, department=None, design_by=None,
                       merchandiser=None, setting_type=None, year=None, month=None):

    filters, params, designer_filters = _build_filters(
        company, branch, department, design_by, merchandiser, setting_type, year, month
    )

    filter_r_sql, filter_r_params = designer_filters["r"]
    filter_h_sql, filter_h_params = designer_filters["h"]
    
    category = frappe.db.sql(f"""
        SELECT
            so.category,
            so.setting_type,
            SUM(IFNULL(h.approved,0)) approved,
            SUM(
                COALESCE(r.approved,0) + COALESCE(r.reject,0) - COALESCE(h.approved,0)
            ) rejected
        FROM `tabSketch Order` so
        LEFT JOIN `tabRough Sketch Approval` r ON r.parent = so.name
        LEFT JOIN `tabFinal Sketch Approval HOD` h ON h.parent = so.name
        WHERE 1=1
        {filters}{filter_r_sql}{filter_h_sql}
        GROUP BY so.category, so.setting_type
    """, params + filter_r_params + filter_h_params, as_dict=True)


    return category


# ============================================================
# 5. AVERAGE COST PER SKETCH  (heavy nested query -> load later)
#    NOTE: doesn't use design_by filter (department-level cost, not
#    sliced per designer — same as original logic)
# ============================================================
@frappe.whitelist()
def get_average_cost(company=None, branch=None, department=None, design_by=None,
                      merchandiser=None, setting_type=None, year=None, month=None):

    filters, params, designer_filters = _build_filters(
        company, branch, department, design_by, merchandiser, setting_type, year, month
    )

    average_cost = frappe.db.sql(f"""
        SELECT
            ROUND(
                SUM(
                    CASE
                        WHEN main.department_gold_weight = 0 THEN 0
                        ELSE (main.department_salary_cost * main.total_gold_weight) / main.department_gold_weight
                    END
                ) / NULLIF(SUM(main.sketch_count),0),
                2
            )
        FROM
        (
            SELECT
                so.department,
                COUNT(DISTINCT so.name) AS sketch_count,
                SUM(COALESCE(cmo.gold_wt_approx,0)) AS total_gold_weight,
                (
                    SELECT SUM(COALESCE(emp.ctc,0))
                    FROM `tabEmployee` emp
                    WHERE emp.department = so.department
                    AND COALESCE(emp.status,'')='Active'
                ) AS department_salary_cost,
                (
                    SELECT SUM(COALESCE(cmo2.gold_wt_approx,0))
                    FROM `tabSketch Order` so2
                    LEFT JOIN `tabFinal Sketch Approval CMO` cmo2 ON cmo2.parent = so2.name
                    WHERE so2.department = so.department
                ) AS department_gold_weight
            FROM `tabSketch Order` so
            LEFT JOIN `tabFinal Sketch Approval CMO` cmo ON cmo.parent = so.name
            WHERE 1=1
            {filters}
            GROUP BY so.department
        ) main
    """, params)[0][0] or 0

    return {"average_cost_incurred_per_sketch": average_cost}


# ============================================================
# 6. MONTH WISE EMPLOYEE GOLD
# ============================================================
@frappe.whitelist()
def get_month_employee_gold(company=None, branch=None, department=None, design_by=None,
                             merchandiser=None, setting_type=None, year=None, month=None):

    cache_key = "month_employee_gold:" + json.dumps({
        "company": company,
        "branch": branch,
        "department": department,
        "design_by": design_by,
        "merchandiser": merchandiser,
        "setting_type": setting_type,
        "year": year,
        "month": month
    }, sort_keys=True)

    cache = frappe.cache()

    cached_data = cache.get_value(cache_key)
    if cached_data:
        return cached_data

    filters, params, designer_filters = _build_filters(
        company, branch, department, design_by, merchandiser, setting_type, year, month
    )

    filter_emp_sql, filter_emp_params = designer_filters["emp"]
    # frappe.throw("lkjhgvhbj")
    month_employee_gold = frappe.db.sql(f"""
        SELECT
            DATE_FORMAT(so.creation, '%%M %%Y') AS month,
            COALESCE(emp.employee_name, emp.name) AS employee_name,
            hod.designer_name,
            SUM(IFNULL(cmo.gold_wt_approx,0)) AS approved_gold_weight
        FROM `tabSketch Order` so
        LEFT JOIN `tabEmployee` emp ON so.owner = emp.user_id
        INNER JOIN `tabFinal Sketch Approval HOD` hod ON hod.parent = so.name
        INNER JOIN `tabFinal Sketch Approval CMO` cmo ON cmo.parent = so.name
        WHERE hod.approved > 0
        AND cmo.gold_wt_approx > 0
        {filters}{filter_emp_sql}
        GROUP BY DATE_FORMAT(so.creation,'%%Y-%%m'),
                 COALESCE(emp.employee_name, emp.name)
        ORDER BY DATE_FORMAT(so.creation,'%%Y-%%m'),
                 employee_name
    """, params + filter_emp_params, as_dict=True)

    # Cache for 5 minutes
    cache.set_value(cache_key, month_employee_gold, expires_in_sec=300)

    return month_employee_gold


# ============================================================
# 7. DESIGNER DAILY SUMMARY  (heaviest -> load last)
# ============================================================
@frappe.whitelist()
def get_designer_daily_summary(company=None, branch=None, department=None, design_by=None,
                                merchandiser=None, setting_type=None, year=None, month=None):

    filters, params, designer_filters = _build_filters(
        company, branch, department, design_by, merchandiser, setting_type, year, month
    )

    filter_design_sql, filter_design_params = designer_filters["design"]

    designer_daily_summary = frappe.db.sql(f"""
        SELECT
            DATE(so.creation) AS sketch_date,
            emp.employee_name AS designer,
            SUM(COALESCE(design.total_design,0)) AS total_design,
            SUM(COALESCE(hod.approved,0)) AS approved,
            SUM(COALESCE(rough.rejected,0) + COALESCE(hod.rejected,0)) AS rejected
        FROM `tabSketch Order` so
        LEFT JOIN (
            SELECT parent, designer, SUM(COALESCE(count_1,0)) total_design
            FROM `tabDesigner Assignment`
            GROUP BY parent, designer
        ) design ON design.parent = so.name
        LEFT JOIN (
            SELECT parent, designer, SUM(COALESCE(reject,0)) rejected
            FROM `tabRough Sketch Approval`
            GROUP BY parent, designer
        ) rough ON rough.parent = so.name AND rough.designer = design.designer
        LEFT JOIN (
            SELECT parent, designer,
                SUM(COALESCE(approved,0)) approved,
                SUM(COALESCE(reject,0)) rejected
            FROM `tabFinal Sketch Approval HOD`
            GROUP BY parent, designer
        ) hod ON hod.parent = so.name AND hod.designer = design.designer
        LEFT JOIN `tabEmployee` emp ON design.designer = emp.name
        WHERE 1=1
        AND emp.employee_name IS NOT NULL
        {filters}{filter_design_sql}
        GROUP BY DATE(so.creation), emp.employee_name
        ORDER BY DATE(so.creation) DESC
    """, params + filter_design_params, as_dict=True)

    return designer_daily_summary



# new cad api (single method for each query)


# ─────────────────────────────────────────────────────────────────────────
# SHARED HELPERS (common logic — reused by every whitelisted endpoint below)
# ─────────────────────────────────────────────────────────────────────────

def _get_filters(filters):
    """Normalize the `filters` param — accepts dict, JSON string, or None."""
    if not filters:
        return {}
    if isinstance(filters, str):
        try:
            return json.loads(filters)
        except ValueError:
            return {}
    return filters


BASE_CONDITION = """
    `tabOrder`.bom_or_cad = 'CAD'
    AND `tabOrder`.workflow_type = 'CAD'
    AND `tabOrder`.workflow_state IN ('Approved', 'Update Item')
    AND `tabTimesheet`.workflow_state = 'Approved'
"""

# used by the 4 "active designer" style queries (design_by_employee, design_by_category,
# gold_weight_by_employee, design_by_branch, staff_salary, designer_salary/get_designer_count)
STAFF_BASE_CONDITION = """
    `tabEmployee`.status = 'Active'
    AND `tabEmployee`.department LIKE 'Computer Aided Designing%%'
    AND `tabEmployee`.department NOT LIKE '%%Sketch%%'
    AND `tabOrder`.bom_or_cad = 'CAD'
    AND `tabOrder`.workflow_type = 'CAD'
    AND `tabOrder`.workflow_state IN ('Approved', 'Update Item')
    AND `tabTimesheet`.workflow_state = 'Approved'
"""


def _build_conditions(filters):
    """Builds the common WHERE-clause fragment + bind values from filters dict."""
    
    fields_map = {
        "tabOrder.company":       filters.get("company"),
        "tabOrder.category":      filters.get("category"),
        "tabEmployee.branch":     filters.get("branch"),
        "tabEmployee.department": filters.get("department"),
        "tabTimesheet.employee_name": filters.get("design_by"),
        "tabEmployee.reporting_employee_name_": filters.get("manager"),
        "tabOrder.setting_type":  filters.get("setting_type"),
    }

    conditions = []
    values = []

    for field, value in fields_map.items():
        if value:
            table, col = field.split(".", 1)

            if isinstance(value, list):
                placeholders = ", ".join(["%s"] * len(value))
                conditions.append(
                    f"AND `{table}`.`{col}` IN ({placeholders})"
                )
                values.extend(value)

            else:
                conditions.append(
                    f"AND `{table}`.`{col}` = %s"
                )
                values.append(value)

    return " ".join(conditions), values
# def _get_date_filter(filters, date_column="`tabTimesheet`.start_date"):
#     """date = {"from": "...", "to": "..."} -> WHERE fragment + bind values."""
#     date = filters.get("date")
#     if date and date.get("from") and date.get("to"):
#         return f"AND {date_column} BETWEEN %s AND %s", [date["from"], date["to"]]
#     return "", []

import calendar
from datetime import date


def _get_date_filter(filters, date_column="`tabTimesheet`.start_date"):
    """
    filters = {
        "year": 2026,
        "month": 7
    }
    """

    year = filters.get("year")
    month = filters.get("month")

    if year and month:
        # First date of month
        from_date = date(int(year), int(month), 1)

        # Last date of month
        last_day = calendar.monthrange(int(year), int(month))[1]
        to_date = date(int(year), int(month), last_day)

        return (
            f"AND {date_column} BETWEEN %s AND %s",
            [from_date, to_date]
        )

    return "", []

def _run(sql, values):
    return frappe.db.sql(sql, tuple(values), as_dict=True)


def _calculate_prorated_salary(ctc, from_date, to_date):
    """Month-by-month proration of ctc between from_date and to_date (inclusive)."""
    total = 0
    cursor = from_date

    while cursor <= to_date:
        month_start = get_first_day(cursor)
        month_end = get_last_day(cursor)

        segment_start = cursor
        segment_end = month_end if month_end < to_date else to_date

        days_in_month = (month_end - month_start).days + 1
        days_in_segment = (segment_end - segment_start).days + 1

        per_day_salary = ctc / days_in_month
        total += per_day_salary * days_in_segment

        cursor = add_months(month_start, 1)

    return total


def _get_designer_salary_rows(filters):
    """Shared query used by both get_designer_salary() and get_per_gram_cost()."""
    extra, vals = _build_conditions(filters)
    dc, dv = _get_date_filter(filters)
    sql = f"""
        SELECT DISTINCT
            `tabEmployee`.name,
            COALESCE(`tabEmployee`.ctc, 0) AS ctc
        FROM `tabEmployee`
        INNER JOIN `tabTimesheet` ON `tabTimesheet`.employee = `tabEmployee`.name
        INNER JOIN `tabOrder`     ON `tabTimesheet`.`order` = `tabOrder`.name
        WHERE `tabEmployee`.status = 'Active'
          AND `tabEmployee`.designation = 'Computer Aided Designer'
          AND `tabEmployee`.department LIKE 'Computer Aided Designing%%'
          AND `tabEmployee`.department NOT LIKE '%%Sketch%%'
          AND `tabOrder`.bom_or_cad = 'CAD'
          AND `tabOrder`.workflow_type = 'CAD'
          AND `tabOrder`.workflow_state IN ('Approved', 'Update Item')
          AND `tabTimesheet`.workflow_state = 'Approved'
          {extra} {dc}
    """
    return _run(sql, vals + dv)


def _compute_designer_salary(filters):
    """Pure computation (no HTTP) — reused by get_designer_salary and get_per_gram_cost."""
    employees = _get_designer_salary_rows(filters)
    date = filters.get("date")

    if not employees:
        return {"total_salary": 0.00, "designer_salary": 0.00}

    if not (date and date.get("from") and date.get("to")):
        total = sum(emp.get("ctc") or 0 for emp in employees)
        return {"designer_salary": round(total, 2), "total_salary": round(total, 2)}

    from_date = getdate(date["from"])
    to_date = getdate(date["to"])

    total_salary = 0
    for emp in employees:
        ctc = emp.get("ctc") or 0
        total_salary += _calculate_prorated_salary(ctc, from_date, to_date)

    return {"total_salary": round(total_salary, 2), "designer_salary": employees[0].ctc}


def _compute_staff_salary(filters):
    """Pure computation (no HTTP) — reused by get_staff_salary and get_per_gram_cost."""
    extra, vals = _build_conditions(filters)
    dc, dv = _get_date_filter(filters)
    sql = f"""
        SELECT COALESCE(ROUND(SUM(x.ctc), 2), 0) AS staff_salary
        FROM (
            SELECT DISTINCT
                `tabEmployee`.name,
                COALESCE(`tabEmployee`.ctc, 0) AS ctc
            FROM `tabEmployee`
            INNER JOIN `tabTimesheet` ON `tabTimesheet`.employee = `tabEmployee`.name
            INNER JOIN `tabOrder`     ON `tabTimesheet`.`order` = `tabOrder`.name
            WHERE `tabEmployee`.status = 'Active'
              AND `tabEmployee`.department LIKE 'Computer Aided Designing%%'
              AND `tabEmployee`.designation <> 'Computer Aided Designer'
              AND `tabOrder`.bom_or_cad = 'CAD'
              AND `tabOrder`.workflow_type = 'CAD'
              AND `tabOrder`.workflow_state IN ('Approved', 'Update Item')
              AND `tabTimesheet`.workflow_state = 'Approved'
              {extra} {dc}
        ) x
    """
    rows = _run(sql, vals + dv)
    return rows[0].get("staff_salary") if rows else 0


def _compute_gold_weight(filters):
    """Pure computation (no HTTP) — reused by get_gold_weight and get_per_gram_cost."""
    extra, vals = _build_conditions(filters)
    dc, dv = _get_date_filter(filters)
    sql = f"""
        SELECT ROUND(SUM(x.total_metal_weight), 2) AS gold_weight
        FROM (
            SELECT DISTINCT
                `tabOrder`.name,
                COALESCE(`tabOrder`.total_metal_weight, 0) AS total_metal_weight
            FROM `tabOrder`
            INNER JOIN `tabTimesheet` ON `tabTimesheet`.`order` = `tabOrder`.name
            INNER JOIN `tabEmployee`  ON `tabEmployee`.name = `tabTimesheet`.employee
            WHERE {BASE_CONDITION} {extra} {dc}
        ) x
    """
    rows = _run(sql, vals + dv)
    return rows[0].get("gold_weight") if rows else 0


# ─────────────────────────────────────────────────────────────────────────
# 1. TOTAL UPDATED  →  GET /api/method/<app>.<path>.get_total_updated
# ─────────────────────────────────────────────────────────────────────────
@frappe.whitelist()
def get_total_updated(filters=None):
    filters = _get_filters(filters)
    extra, vals = _build_conditions(filters)
    dc, dv = _get_date_filter(filters)
    sql = f"""
        SELECT COUNT(DISTINCT `tabOrder`.name) AS total_updated
        FROM `tabOrder`
        LEFT JOIN `tabTimesheet` ON `tabTimesheet`.`order` = `tabOrder`.name
        LEFT JOIN `tabEmployee`  ON `tabEmployee`.name = `tabTimesheet`.employee
        WHERE {BASE_CONDITION} {extra} {dc}
    """
    return _run(sql, vals + dv)



@frappe.whitelist()
def get_designer_count(filters=None):
    filters = _get_filters(filters)
    extra, vals = _build_conditions(filters)
    dc, dv = _get_date_filter(filters)

    sql = f"""
        SELECT COUNT(DISTINCT `tabEmployee`.name) AS designer_count
        FROM `tabEmployee`
        INNER JOIN `tabTimesheet`
            ON `tabTimesheet`.employee = `tabEmployee`.name
        INNER JOIN `tabOrder`
            ON `tabTimesheet`.`order` = `tabOrder`.name
        WHERE `tabEmployee`.status = 'Active'
          AND `tabEmployee`.designation = 'Computer Aided Designer'
          AND `tabEmployee`.department LIKE 'Computer Aided Designing%%'
          AND `tabEmployee`.department NOT LIKE '%%Sketch%%'
          AND `tabOrder`.bom_or_cad = 'CAD'
          AND `tabOrder`.workflow_type = 'CAD'
          AND `tabOrder`.workflow_state IN ('Approved', 'Update Item')
          AND `tabTimesheet`.workflow_state = 'Approved'
          {extra} {dc}
    """

    return _run(sql, vals + dv)
# ─────────────────────────────────────────────────────────────────────────
# 2. TOTAL DESIGN
# ─────────────────────────────────────────────────────────────────────────
@frappe.whitelist()
def get_total_design(filters=None):
    filters = _get_filters(filters)
    extra, vals = _build_conditions(filters)
    dc, dv = _get_date_filter(filters)
    sql = f"""
        SELECT SUM(DISTINCT `tabOrder Form`.total_rows) AS total_design
        FROM `tabOrder`
        LEFT JOIN `tabTimesheet`  ON `tabTimesheet`.`order` = `tabOrder`.name
        LEFT JOIN `tabEmployee`   ON `tabEmployee`.name = `tabTimesheet`.employee
        LEFT JOIN `tabOrder Form` ON `tabOrder`.cad_order_form = `tabOrder Form`.name
        WHERE {BASE_CONDITION} {extra} {dc}
    """
    return _run(sql, vals + dv)


# ─────────────────────────────────────────────────────────────────────────
# 3. DIAMOND PCS
# ─────────────────────────────────────────────────────────────────────────
@frappe.whitelist()
def get_diamond_pcs(filters=None):
    filters = _get_filters(filters)
    extra, vals = _build_conditions(filters)
    dc, dv = _get_date_filter(filters)
    sql = f"""
        SELECT SUM(COALESCE(x.total_diamond_pcs, 0)) AS diamond_pcs
        FROM (
            SELECT DISTINCT
                `tabOrder`.name,
                `tabOrder`.total_diamond_pcs
            FROM `tabOrder`
            INNER JOIN `tabTimesheet` ON `tabTimesheet`.`order` = `tabOrder`.name
            INNER JOIN `tabEmployee`  ON `tabEmployee`.name = `tabTimesheet`.employee
            WHERE {BASE_CONDITION} {extra} {dc}
        ) x
    """
    return _run(sql, vals + dv)


# ─────────────────────────────────────────────────────────────────────────
# 4. DIAMOND WEIGHT
# ─────────────────────────────────────────────────────────────────────────
@frappe.whitelist()
def get_diamond_weight(filters=None):
    filters = _get_filters(filters)
    extra, vals = _build_conditions(filters)
    dc, dv = _get_date_filter(filters)
    sql = f"""
        SELECT ROUND(SUM(x.total_diamond_weight), 2) AS diamond_weight
        FROM (
            SELECT DISTINCT
                `tabOrder`.name,
                COALESCE(`tabOrder`.total_diamond_weight, 0) AS total_diamond_weight
            FROM `tabOrder`
            INNER JOIN `tabTimesheet` ON `tabTimesheet`.`order` = `tabOrder`.name
            INNER JOIN `tabEmployee`  ON `tabEmployee`.name = `tabTimesheet`.employee
            WHERE {BASE_CONDITION} {extra} {dc}
        ) x
    """
    return _run(sql, vals + dv)


# ─────────────────────────────────────────────────────────────────────────
# 5. GOLD WEIGHT
# ─────────────────────────────────────────────────────────────────────────
@frappe.whitelist()
def get_gold_weight(filters=None):
    filters = _get_filters(filters)
    return [{"gold_weight": _compute_gold_weight(filters)}]


# ─────────────────────────────────────────────────────────────────────────
# 6. AVG DAYS
# ─────────────────────────────────────────────────────────────────────────
@frappe.whitelist()
def get_avg_days(filters=None):
    filters = _get_filters(filters)
    extra, vals = _build_conditions(filters)
    dc, dv = _get_date_filter(filters)
    sql = f"""
        SELECT ROUND(AVG(DATEDIFF(`tabTimesheet`.end_date, `tabTimesheet`.start_date)), 2) AS avg_days
        FROM `tabTimesheet`
        INNER JOIN `tabOrder`    ON `tabOrder`.name = `tabTimesheet`.`order`
        INNER JOIN `tabEmployee` ON `tabEmployee`.name = `tabTimesheet`.employee
        WHERE `tabTimesheet`.workflow_state = 'Approved'
          AND `tabTimesheet`.start_date IS NOT NULL
          AND `tabTimesheet`.end_date IS NOT NULL
          AND `tabOrder`.bom_or_cad = 'CAD'
          AND `tabOrder`.workflow_type = 'CAD'
          AND `tabOrder`.workflow_state IN ('Approved', 'Update Item')
          {extra} {dc}
    """
    return _run(sql, vals + dv)


# ─────────────────────────────────────────────────────────────────────────
# 7. DESIGNER COUNT
# ─────────────────────────────────────────────────────────────────────────
@frappe.whitelist()
def get_designer_count(filters=None):
    filters = _get_filters(filters)
    extra, vals = _build_conditions(filters)
    dc, dv = _get_date_filter(filters)
    sql = f"""
        SELECT COUNT(DISTINCT `tabEmployee`.name) AS designer_count
        FROM `tabEmployee`
        INNER JOIN `tabTimesheet` ON `tabTimesheet`.employee = `tabEmployee`.name
        INNER JOIN `tabOrder`     ON `tabTimesheet`.`order` = `tabOrder`.name
        WHERE `tabEmployee`.status = 'Active'
          AND `tabEmployee`.designation = 'Computer Aided Designer'
          AND `tabEmployee`.department LIKE 'Computer Aided Designing%%'
          AND `tabEmployee`.department NOT LIKE '%%Sketch%%'
          AND `tabOrder`.bom_or_cad = 'CAD'
          AND `tabOrder`.workflow_type = 'CAD'
          AND `tabOrder`.workflow_state IN ('Approved', 'Update Item')
          AND `tabTimesheet`.workflow_state = 'Approved'
          {extra} {dc}
    """
    return _run(sql, vals + dv)


# ─────────────────────────────────────────────────────────────────────────
# 8. DESIGNER SALARY (with prorated calc when a date range is given)
# ─────────────────────────────────────────────────────────────────────────
@frappe.whitelist()
def get_designer_salary(filters=None):
    filters = _get_filters(filters)
    return [_compute_designer_salary(filters)]


# ─────────────────────────────────────────────────────────────────────────
# 9. STAFF SALARY
# ─────────────────────────────────────────────────────────────────────────
@frappe.whitelist()
def get_staff_salary(filters=None):
    filters = _get_filters(filters)
    return [{"staff_salary": _compute_staff_salary(filters)}]


# ─────────────────────────────────────────────────────────────────────────
# 10. PER GRAM COST (depends on designer_salary + staff_salary + gold_weight
#     computed in-process, not via separate HTTP round-trips)
# ─────────────────────────────────────────────────────────────────────────
@frappe.whitelist()
def get_per_gram_cost(filters=None):
    filters = _get_filters(filters)

    designer_data = _compute_designer_salary(filters)
    designer = designer_data.get("designer_salary") or 0
    staff = _compute_staff_salary(filters) or 0
    gold = _compute_gold_weight(filters) or 0

    total_salary = (designer_data.get("total_salary") or 0) + staff
    per_gram = round(total_salary / gold, 2) if gold else 0

    return {
        "designer_salary": designer,
        "staff_salary":    staff,
        "total_salary":    total_salary,
        "per_gram_cost":   per_gram,
    }


# ─────────────────────────────────────────────────────────────────────────
# 11. DESIGN BY EMPLOYEE (top 10)
# ─────────────────────────────────────────────────────────────────────────
@frappe.whitelist()
def get_design_by_employee(filters=None):
    filters = _get_filters(filters)
    extra, vals = _build_conditions(filters)
    dc, dv = _get_date_filter(filters)
    sql = f"""
        SELECT
            `tabEmployee`.employee_name AS employee,
            COUNT(DISTINCT `tabOrder`.name) AS total_design
        FROM `tabEmployee`
        INNER JOIN `tabTimesheet` ON `tabTimesheet`.employee = `tabEmployee`.name
        INNER JOIN `tabOrder`     ON `tabTimesheet`.`order` = `tabOrder`.name
        WHERE {STAFF_BASE_CONDITION} {extra} {dc}
        GROUP BY `tabEmployee`.name, `tabEmployee`.employee_name
        ORDER BY total_design DESC
        LIMIT 10
    """
    return _run(sql, vals + dv)


# ─────────────────────────────────────────────────────────────────────────
# 12. DESIGN BY CATEGORY
# ─────────────────────────────────────────────────────────────────────────
@frappe.whitelist()
def get_design_by_category(filters=None):
    filters = _get_filters(filters)
    # frappe.throw(f"{filters, STAFF_BASE_CONDITION}")
    extra, vals = _build_conditions(filters)
    dc, dv = _get_date_filter(filters)
    sql = f"""
        SELECT
            `tabOrder`.category AS category,
            COUNT(DISTINCT `tabOrder`.name) AS total_design
        FROM `tabEmployee`
        INNER JOIN `tabTimesheet` ON `tabTimesheet`.employee = `tabEmployee`.name
        INNER JOIN `tabOrder`  ON `tabTimesheet`.`order` = `tabOrder`.name
        WHERE {STAFF_BASE_CONDITION} {extra} {dc}
        GROUP BY `tabOrder`.category
        ORDER BY total_design DESC
    """
    return _run(sql, vals + dv)


# ─────────────────────────────────────────────────────────────────────────
# 13. GOLD WEIGHT BY EMPLOYEE (top 10)
# ─────────────────────────────────────────────────────────────────────────
@frappe.whitelist()
def get_gold_weight_by_employee(filters=None):
    filters = _get_filters(filters)
    extra, vals = _build_conditions(filters)
    dc, dv = _get_date_filter(filters)
    sql = f"""
        SELECT
            x.employee_name AS employee,
            ROUND(SUM(COALESCE(x.total_metal_weight, 0)), 3) AS gold_weight
        FROM (
            SELECT DISTINCT
                `tabEmployee`.name AS employee_id,
                `tabEmployee`.employee_name,
                `tabOrder`.name AS order_id,
                COALESCE(`tabOrder`.total_metal_weight, 0) AS total_metal_weight
            FROM `tabEmployee`
            INNER JOIN `tabTimesheet` ON `tabTimesheet`.employee = `tabEmployee`.name
            INNER JOIN `tabOrder`     ON `tabTimesheet`.`order` = `tabOrder`.name
            WHERE {STAFF_BASE_CONDITION} {extra} {dc}
        ) x
        GROUP BY x.employee_id, x.employee_name
        ORDER BY gold_weight DESC
        LIMIT 10
    """
    return _run(sql, vals + dv)


# ─────────────────────────────────────────────────────────────────────────
# 14. DESIGN BY BRANCH
# ─────────────────────────────────────────────────────────────────────────
@frappe.whitelist()
def get_design_by_branch(filters=None):
    filters = _get_filters(filters)
    extra, vals = _build_conditions(filters)
    dc, dv = _get_date_filter(filters)
    sql = f"""
        SELECT
            `tabBranch`.branch_name AS branch,
            `tabBranch`.name AS branch_id,
            COUNT(DISTINCT `tabOrder`.name) AS total_design
        FROM `tabEmployee`
        INNER JOIN `tabBranch`    ON `tabBranch`.name = `tabEmployee`.branch
        INNER JOIN `tabTimesheet` ON `tabTimesheet`.employee = `tabEmployee`.name
        INNER JOIN `tabOrder`     ON `tabTimesheet`.`order` = `tabOrder`.name
        WHERE {STAFF_BASE_CONDITION} {extra} {dc}
        GROUP BY `tabBranch`.name, `tabBranch`.branch_name
        ORDER BY total_design DESC
    """
    return _run(sql, vals + dv)


# ─────────────────────────────────────────────────────────────────────────
# OPTIONAL: combined endpoint kept for backward compatibility (old callers
# that still expect one big payload). New UI code should call the
# individual methods above in parallel instead of this one.
# ─────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_cad_dashboard_data(filters=None):
    filters = _get_filters(filters)
    return {
        "total_updated":           get_total_updated(filters),
        "total_design":            get_total_design(filters),
        "diamond_pcs":             get_diamond_pcs(filters),
        "diamond_weight":          get_diamond_weight(filters),
        "gold_weight":             get_gold_weight(filters),
        "avg_days":                get_avg_days(filters),
        "per_gram_cost":           get_per_gram_cost(filters),
        "designer_salary":         get_designer_salary(filters),
        "staff_salary":            get_staff_salary(filters),
        "design_by_employee":      get_design_by_employee(filters),
        "design_by_category":      get_design_by_category(filters),
        "gold_weight_by_employee": get_gold_weight_by_employee(filters),
        "design_by_branch":        get_design_by_branch(filters),
        "employee_count":          get_designer_count(filters),
    }
    
    
# customer wise data of cad
@frappe.whitelist()
def get_customer_wise_cad_catgory_count(filters=None):
    sql = """
        SELECT
            category,
            SUM(qty) AS total_psc
        FROM
            `tabOrder`
        WHERE
            workflow_type = 'CAD'
            AND bom_or_cad = 'CAD'
        GROUP BY
            category
        ORDER BY
            total_psc DESC
        LIMIT 10
    """

    return frappe.db.sql(sql, as_dict=True)

    
@frappe.whitelist()
def get_customer_wise_cad_grade(filters=None):
    sql = """
        SELECT
            c.custom_customer_grade
        FROM
            `tabOrder` o
        LEFT JOIN
            `tabCustomer` c
            ON o.customer_code = c.name
        WHERE
            o.workflow_type = 'CAD'
            AND o.bom_or_cad = 'CAD'
        GROUP BY
            c.custom_customer_grade
        LIMIT 10
    """

    return frappe.db.sql(sql, as_dict=True)


@frappe.whitelist()
def get_customer_wise_cad_setting_type(filters=None):
    sql = """
        SELECT
            o.setting_type,
            COUNT(*) AS total_count
        FROM
            `tabOrder` o
        WHERE
            o.workflow_type = 'CAD'
            AND o.bom_or_cad = 'CAD'
        GROUP BY
            o.setting_type
        ORDER BY
            total_count DESC
    """

    return frappe.db.sql(sql, as_dict=True)

