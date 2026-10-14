# Chain Issue Receive Report

import frappe
from frappe import _


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    return [
        {"label": _("Request Date"), "fieldname": "request_date", "fieldtype": "Datetime", "width": 150},
        {"label": _("Gorder No"), "fieldname": "gorder_no", "fieldtype": "Link", "options": "Manufacturing Work Order", "width": 200},
        {"label": _("Length"), "fieldname": "length", "fieldtype": "Data", "width": 80},
        {"label": _("Weight"), "fieldname": "weight", "fieldtype": "Float", "width": 90, "precision": 3},
        {"label": _("Due Day"), "fieldname": "due_day", "fieldtype": "Int", "width": 70},
        {"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 100},
        {"label": _("C Status"), "fieldname": "c_status", "fieldtype": "Data", "width": 80},
        {"label": _("Receive Weight"), "fieldname": "receive_weight", "fieldtype": "Float", "width": 110, "precision": 3},
        {"label": _("Issue Date"), "fieldname": "issue_date", "fieldtype": "Datetime", "width": 150},
        {"label": _("Receive Date"), "fieldname": "receive_date", "fieldtype": "Datetime", "width": 150},
        {"label": _("Party"), "fieldname": "party", "fieldtype": "Link", "options": "Customer", "width": 180},
        {"label": _("Job Worker"), "fieldname": "job_worker", "fieldtype": "Data", "width": 150},
        {"label": _("Chain Type"), "fieldname": "chain_type", "fieldtype": "Data", "width": 120},
        {"label": _("Issue Branch"), "fieldname": "issue_branch", "fieldtype": "Link", "options": "Branch", "width": 130},
        {"label": _("Issue By"), "fieldname": "issue_by", "fieldtype": "Data", "width": 130},
        {"label": _("Receive By"), "fieldname": "receive_by", "fieldtype": "Data", "width": 130},
        {"label": _("Req Branch"), "fieldname": "req_branch", "fieldtype": "Link", "options": "Branch", "width": 130},
        {"label": _("Request By"), "fieldname": "request_by", "fieldtype": "Data", "width": 130},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 90},
    ]


def get_data(filters):
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    gorder = filters.get("gorder")
    job_worker = filters.get("job_worker")
    company = filters.get("company")
    branch = filters.get("branch")
    customer = filters.get("customer")

    conditions = ["mwo.is_finding_mwo = 1"]
    values = {}

    if from_date and to_date:
        conditions.append("DATE(mwo.creation) BETWEEN %(from_date)s AND %(to_date)s")
        values["from_date"] = from_date
        values["to_date"] = to_date

    if gorder:
        conditions.append("mwo.name = %(gorder)s")
        values["gorder"] = gorder

    if job_worker:
        conditions.append("em.name = %(job_worker)s")
        values["job_worker"] = job_worker

    if company:
        conditions.append("mwo.company = %(company)s")
        values["company"] = company

    if branch:
        conditions.append("mwo.branch = %(branch)s")
        values["branch"] = branch

    if customer:
        conditions.append("mwo.customer = %(customer)s")
        values["customer"] = customer

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT
            mwo.creation                          AS request_date,
            mwo.name                              AS gorder_no,
            iva.attribute_value                   AS length,
            mwo.gross_wt                          AS weight,
            mwo.due_days                          AS due_day,
            mwo.delivery_date                     AS due_date,
            
            CASE
                WHEN COUNT(CASE WHEN eir.type = 'Receive' THEN 1 END) > 0
                    THEN 'Receive'
                WHEN COUNT(CASE WHEN eir.type = 'Issue' THEN 1 END) > 0
                    THEN 'Issue'
                ELSE 'Requested'
            END                                   AS c_status,
            
            mwo.received_gross_wt                 AS receive_weight,

            MIN(CASE WHEN eir.type = 'Issue'
                     THEN eir.date_time END)      AS issue_date,
            MIN(CASE WHEN eir.type = 'Receive'
                     THEN eir.date_time END)      AS receive_date,

            mwo.customer                          AS party,

            MAX(
                CASE
                    WHEN eir.type = 'Receive' AND eir.subcontracting = 'Yes'
                        THEN sup.supplier_name
                    WHEN eir.type = 'Receive' AND eir.subcontracting = 'No'
                        THEN em.employee_name
                    WHEN eir.type = 'Issue'   AND eir.subcontracting = 'Yes'
                        THEN sup.supplier_name
                    WHEN eir.type = 'Issue'   AND eir.subcontracting = 'No'
                        THEN em.employee_name
                END
            )                                     AS job_worker,

            mwo.item_sub_category                 AS chain_type,

            mwo.branch                            AS issue_branch,
            mwo.branch                            AS req_branch,

            MAX(
                CASE
                    WHEN eir.type = 'Issue' AND eir.subcontracting = 'Yes'
                        THEN sup.supplier_name
                    WHEN eir.type = 'Issue' AND eir.subcontracting = 'No'
                        THEN em.employee_name
                END
            )                                     AS issue_by,

            MAX(
                CASE
                    WHEN eir.type = 'Receive' AND eir.subcontracting = 'Yes'
                        THEN sup.supplier_name
                    WHEN eir.type = 'Receive' AND eir.subcontracting = 'No'
                        THEN em.employee_name
                END
            )                                     AS receive_by,

            req_emp.employee_name                 AS request_by,
            mwo.status                            AS status
        FROM
            `tabManufacturing Work Order` mwo
        LEFT JOIN `tabEmployee IR Operation` eiro
            ON mwo.name = eiro.manufacturing_work_order
        LEFT JOIN `tabEmployee IR` eir
            ON eir.name = eiro.parent
           AND eir.type IN ('Issue', 'Receive')
        LEFT JOIN `tabEmployee` em
            ON eir.employee = em.name
        LEFT JOIN `tabSupplier` sup
            ON eir.subcontractor = sup.name
        LEFT JOIN `tabEmployee` req_emp
            ON req_emp.user_id = mwo.owner
        LEFT JOIN `tabItem` it
            ON it.name = mwo.item_code
        LEFT JOIN `tabItem Variant Attribute` iva
            ON iva.parent = mwo.item_code
           AND iva.attribute = 'Finding Size'
        WHERE
            {where_clause}
        GROUP BY
            mwo.name
        ORDER BY
            mwo.creation
    """

    return frappe.db.sql(query, values=values, as_dict=True)
