# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}

    columns = get_columns()
    data = get_data(filters)
    data = apply_grouping(data)

    return columns, data


def get_columns():
    return [
        {"label": _("Trans Date"), "fieldname": "trans_date", "fieldtype": "Date", "width": 100},
        {"label": _("Trans Time"), "fieldname": "trans_time", "fieldtype": "Data", "width": 90},
        {"label": _("Jangad No"), "fieldname": "jangad_no", "fieldtype": "Data", "width": 100},
        {"label": _("Manufacturing Work Order"), "fieldname": "manufacturing_work_order", "fieldtype": "Link", "options": "Manufacturing Work Order", "width": 180},
        {"label": _("From Dept"), "fieldname": "from_department", "fieldtype": "Link", "options": "Department", "width": 130},
        {"label": _("From Mgr"), "fieldname": "from_manager", "fieldtype": "Data", "width": 110},
        {"label": _("To Dept"), "fieldname": "to_department", "fieldtype": "Link", "options": "Department", "width": 130},
        {"label": _("To Mgr"), "fieldname": "to_manager", "fieldtype": "Data", "width": 110},
        {"label": _("Transporter"), "fieldname": "transporter", "fieldtype": "Data", "width": 100},
        {"label": _("Issue Confirm"), "fieldname": "issue_confirm", "fieldtype": "Data", "width": 100},
        {"label": _("Receive Confirm"), "fieldname": "receive_confirm", "fieldtype": "Data", "width": 110},
        {"label": _("Jangad Lock Date"), "fieldname": "jangad_lock_date", "fieldtype": "Data", "width": 130},
        {"label": _("Jangad Lock Time"), "fieldname": "jangad_lock_time", "fieldtype": "Data", "width": 130},
        {"label": _("Jangad Lock"), "fieldname": "jangad_lock", "fieldtype": "Data", "width": 100},
        {"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 130},
        {"label": _("Sample No"), "fieldname": "sample_no", "fieldtype": "Data", "width": 120},
        {"label": _("Category"), "fieldname": "category", "fieldtype": "Data", "width": 120},
        {"label": _("Gross Wt"), "fieldname": "gross_wt", "fieldtype": "Float", "width": 100},
        {"label": _("Pcs"), "fieldname": "pcs", "fieldtype": "Int", "width": 80},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
        {"label": _("Issue Employee"), "fieldname": "issue_employee", "fieldtype": "Data", "width": 130},
        {"label": _("Receive Employee"), "fieldname": "receive_employee", "fieldtype": "Data", "width": 130},
        {"label": _("Issue Date"), "fieldname": "issue_date", "fieldtype": "Date", "width": 100},
        {"label": _("Receive Date"), "fieldname": "receive_date", "fieldtype": "Date", "width": 100},
        {"label": _("Type"), "fieldname": "type", "fieldtype": "Data", "width": 90},
    ]


def get_data(filters):
    conditions = []
    query_filters = {}

    if filters.get("company"):
        conditions.append("dir.company = %(company)s")
        query_filters["company"] = filters.get("company")

    if filters.get("branch"):
        conditions.append("dir.branch = %(branch)s")
        query_filters["branch"] = filters.get("branch")

    if filters.get("jangad_no"):
        conditions.append("dir.name LIKE %(jangad_no)s")
        query_filters["jangad_no"] = f"%{filters.get('jangad_no')}%"

    if filters.get("from_dept"):
        conditions.append("""
            CASE
                WHEN dir.type = 'Issue' THEN dir.current_department
                WHEN dir.type = 'Receive' THEN dir.previous_department
            END = %(from_dept)s
        """)
        query_filters["from_dept"] = filters.get("from_dept")

    if filters.get("to_dept"):
        conditions.append("""
            CASE
                WHEN dir.type = 'Issue' THEN dir.next_department
                WHEN dir.type = 'Receive' THEN dir.current_department
            END = %(to_dept)s
        """)
        query_filters["to_dept"] = filters.get("to_dept")

    if filters.get("from_manager"):
        conditions.append("""
            EXISTS (
                SELECT 1 FROM `tabEmployee` e
                WHERE e.department = CASE
                        WHEN dir.type = 'Issue' THEN dir.current_department
                        WHEN dir.type = 'Receive' THEN dir.previous_department
                    END
                AND e.designation IN ('Manager', 'Senior Manager')
                AND e.name = %(from_manager)s
            )
        """)
        query_filters["from_manager"] = filters.get("from_manager")

    if filters.get("to_manager"):
        conditions.append("""
            EXISTS (
                SELECT 1 FROM `tabEmployee` e
                WHERE e.department = CASE
                        WHEN dir.type = 'Issue' THEN dir.next_department
                        WHEN dir.type = 'Receive' THEN dir.current_department
                    END
                AND e.designation IN ('Manager', 'Senior Manager')
                AND e.name = %(to_manager)s
            )
        """)
        query_filters["to_manager"] = filters.get("to_manager")

    if filters.get("item_code"):
        conditions.append("mwo.item_code = %(item_code)s")
        query_filters["item_code"] = filters.get("item_code")

    if filters.get("sample_no"):
        conditions.append("item.variant_of = %(sample_no)s")
        query_filters["sample_no"] = filters.get("sample_no")

    if filters.get("category"):
        conditions.append("mwo.item_category = %(category)s")
        query_filters["category"] = filters.get("category")

    if filters.get("status"):
        conditions.append("dir.type = %(status)s")
        query_filters["status"] = filters.get("status")

    if filters.get("from_date"):
        conditions.append("DATE(dir.date_time) >= %(from_date)s")
        query_filters["from_date"] = filters.get("from_date")

    if filters.get("to_date"):
        conditions.append("DATE(dir.date_time) <= %(to_date)s")
        query_filters["to_date"] = filters.get("to_date")

    condition_sql = ""
    if conditions:
        condition_sql = " AND " + " AND ".join(conditions)

    data = frappe.db.sql("""
        SELECT
            DATE(dir.date_time) AS trans_date,
            DATE_FORMAT(dir.date_time, '%%h:%%i %%p') AS trans_time,
            REPLACE(dir.name, 'Department-IR-', '') AS jangad_no,
            /* From Department */
            CASE
                WHEN dir.type = 'Issue' THEN dir.current_department
                WHEN dir.type = 'Receive' THEN dir.previous_department
            END AS from_department,
            /* From Manager */
            (
                SELECT e.employee_name
                FROM `tabEmployee` e
                WHERE e.department =
                    CASE
                        WHEN dir.type = 'Issue' THEN dir.current_department
                        WHEN dir.type = 'Receive' THEN dir.previous_department
                    END
                AND e.designation IN ('Manager', 'Senior Manager')
                ORDER BY
                    CASE
                        WHEN e.designation = 'Manager' THEN 1
                        WHEN e.designation = 'Senior Manager' THEN 2
                    END
                LIMIT 1
            ) AS from_manager,
            /* To Department */
            CASE
                WHEN dir.type = 'Issue' THEN dir.next_department
                WHEN dir.type = 'Receive' THEN dir.current_department
            END AS to_department,
            /* To Manager */
            (
                SELECT e.employee_name
                FROM `tabEmployee` e
                WHERE e.department =
                    CASE
                        WHEN dir.type = 'Issue' THEN dir.next_department
                        WHEN dir.type = 'Receive' THEN dir.current_department
                    END
                AND e.designation IN ('Manager', 'Senior Manager')
                ORDER BY
                    CASE
                        WHEN e.designation = 'Manager' THEN 1
                        WHEN e.designation = 'Senior Manager' THEN 2
                    END
                LIMIT 1
            ) AS to_manager,
            '' AS transporter,
            CASE
                WHEN dir.type = 'Issue' THEN 'Yes'
                ELSE ''
            END AS issue_confirm,
            CASE
                WHEN dir.type = 'Receive' THEN 'Yes'
                ELSE ''
            END AS receive_confirm,
            '' AS jangad_lock_date,
            '' AS jangad_lock_time,
            '' AS jangad_lock,
            mwo.item_code AS item_code,
            item.variant_of AS sample_no,
            mwo.item_category AS category,
            diro.gross_wt,
            diro.diamond_pcs AS pcs,
            dir.workflow_state AS status,
            /* Issue Employee */
            CASE
                WHEN dir.type = 'Issue' THEN issue_user.full_name
                ELSE ''
            END AS issue_employee,
            /* Receive Employee */
            CASE
                WHEN dir.type = 'Receive' THEN receive_user.full_name
                ELSE ''
            END AS receive_employee,
            /* Issue Date */
            CASE
                WHEN dir.type = 'Issue' THEN DATE(dir.date_time)
                ELSE NULL
            END AS issue_date,
            /* Receive Date */
            CASE
                WHEN dir.type = 'Receive' THEN DATE(dir.date_time)
                ELSE NULL
            END AS receive_date,
            dir.type,
            diro.manufacturing_work_order
        FROM `tabDepartment IR` dir
        LEFT JOIN `tabDepartment IR Operation` diro
            ON diro.parent = dir.name
        LEFT JOIN `tabManufacturing Work Order` mwo
            ON mwo.name = diro.manufacturing_work_order
        LEFT JOIN `tabItem` item
            ON item.name = mwo.item_code
        LEFT JOIN `tabUser` issue_user
            ON issue_user.name = CASE
                                    WHEN dir.type = 'Issue' THEN dir.owner
                                 END
        LEFT JOIN `tabUser` receive_user
            ON receive_user.name = CASE
                                      WHEN dir.type = 'Receive' THEN dir.owner
                                   END
        WHERE dir.docstatus < 2
        {condition_sql}
        ORDER BY dir.date_time DESC, dir.name
    """.format(condition_sql=condition_sql), query_filters, as_dict=True)

    return data


def apply_grouping(data):
    """
    Blank out Jangad-level fields on repeated rows belonging to the same
    Jangad No, so each Jangad No group displays its parent-level info
    only once (on the first row), while item/operation-level fields
    (Manufacturing Work Order, Item Code, Gross Wt, Pcs, etc.) still
    display on every row.
    """
    # Fields to blank out on repeat rows within the same Jangad No group
    group_fields = [
        "trans_date",
        "trans_time",
        "jangad_no",
        "from_department",
        "from_manager",
        "to_department",
        "to_manager",
        "issue_confirm",
        "receive_confirm",
    ]

    last_jangad_no = None

    for row in data:
        current_jangad_no = row.get("jangad_no")

        if current_jangad_no == last_jangad_no:
            # Same Jangad No as previous row -> blank the group-level fields
            for field in group_fields:
                row[field] = ""
        else:
            # New Jangad No group starts here
            last_jangad_no = current_jangad_no

    return data