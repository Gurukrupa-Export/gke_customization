import frappe


@frappe.whitelist(allow_guest=False)
def get_csat_details(client_name=None, from_date=None, to_date=None):
    filters = {}

    if client_name:
        filters["client_name"] = client_name

    if from_date and to_date:
        filters["creation"] = ["between", [from_date, to_date]]
    elif from_date:
        filters["creation"] = [">=", from_date]
    elif to_date:
        filters["creation"] = ["<=", to_date]

    fields = [
        "name",
        "creation",
        "client_name",
        "company_name",
        "location",
        "design_accuracy",
        "finishing_setting",
        "diamond_quality",
        "on_time_delivery",
        "repair_service",
        "customization",
        "communication_throughout_sales_process",
        "deadstock_liquidation_recrafting_service",
        "suggestion_for_improvement"
    ]

    data = frappe.get_all(
        "CSAT Questionnaire",
        fields=fields,
        filters=filters,
        order_by="creation desc",
        limit_page_length=1000
    )

    return {
        "total": len(data),
        "data": data
    }


@frappe.whitelist(allow_guest=False)
def get_csat_clients():
    clients = frappe.get_all(
        "CSAT Questionnaire",
        fields=["client_name"],
        filters={"client_name": ["!=", ""]},
        order_by="client_name asc",
        distinct=True
    )

    return [d.client_name for d in clients]


import frappe
import pyodbc

@frappe.whitelist(allow_guest=True)
def get_last_month_customer_invoices(customer_code):
    if not customer_code:
        return {
            "count": 0,
            "invoices": []
        }

    conn = None

    try:
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=27.109.25.76,9880;"
            "DATABASE=JwelexERP;"
            "UID=ra;"
            "PWD=Code@4142;"
            "TrustServerCertificate=yes;"
            "Connection Timeout=15;"
        )

        cursor = conn.cursor()

        sql = """
            SELECT
                SIM.InvoiceNo,
                SIM.SaleDate,
                MC.Cust_Code
            FROM dbo.Sales_Invoice_Master_New SIM WITH (NOLOCK)
            LEFT JOIN dbo.M_Customer MC WITH (NOLOCK)
                ON MC.Cust_ID = SIM.Cust_ID
            WHERE
                SIM.Sale_Type = 'SALE'
                AND MC.Cust_Code = ?
                AND SIM.SaleDate >= DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()) - 1, 0)
                AND SIM.SaleDate < DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()), 0)
            ORDER BY SIM.SaleDate DESC
        """

        cursor.execute(sql, customer_code)

        invoices = []

        for row in cursor.fetchall():
            invoices.append({
                "InvoiceNo": row.InvoiceNo,
                "SaleDate": row.SaleDate.strftime("%Y-%m-%d") if row.SaleDate else "",
                "Cust_Code": row.Cust_Code
            })

        return {
            "count": len(invoices),
            "invoices": invoices
        }

    except Exception:
        frappe.log_error(
            title="Get Last Month Customer Invoices Error",
            message=frappe.get_traceback()
        )
        frappe.throw("Failed to fetch last month invoices")

    finally:
        if conn:
            conn.close()





@frappe.whitelist(allow_guest=False)
def get_order_tracking_customers():
    result = frappe.db.sql("""
        SELECT DISTINCT customer_code, customer_name
        FROM `tabOrder Tracking`
        WHERE customer_code IS NOT NULL AND customer_code != ''
        ORDER BY customer_code ASC
    """, as_dict=True)
    return result





# @frappe.whitelist(allow_guest=False)
# def get_order_tracking_list(customer_code=None, from_date=None, to_date=None):
#     filters = []

#     if customer_code:
#         filters.append(["Order Tracking", "customer_code", "like", f"%{customer_code}%"])

#     if from_date:
#         filters.append(["Order Tracking", "customer_due_date", ">=", from_date])

#     if to_date:
#         filters.append(["Order Tracking", "customer_due_date", "<=", to_date])

#     orders = frappe.get_all(
#         "Order Tracking",
#         filters=filters,
#         fields=[
#             "name", "customer_code", "customer_name", "order_no",
#             "bulk_order_no", "po_no", "main_po_no",
#             "diamond_purity", "customer_due_date"
#         ],
#         order_by="modified desc",
#         limit_page_length=500
#     )

#     for order in orders:
#         order["order_details"] = frappe.get_all(
#             "Bulk Order Detail",
#             filters={"parent": order["name"]},
#             fields=[
#                 "batch_no", "batch_date", "gorder_no",
#                 "current_department", "current_manager", "current_process",
#                 "setting_type", "category", "sub_category",
#                 "gold_weight", "dia_weight", "dia_pcs",
#                 "production_due_date", "finish_date",
#                 "from_branch", "to_branch", "reason"
#             ],
#             order_by="idx asc"
#         )
#     # fetch all version history in one query
#     order_names = [o["name"] for o in orders]

#     if order_names:
#         all_versions = frappe.get_all(
#             "Version",
#             filters={"ref_doctype": "Order Tracking", "docname": ["in", order_names]},
#             fields=["docname", "creation", "owner", "data"],
#             order_by="creation desc",
#             limit_page_length=0
#         )

#         version_map = {}
#         for v in all_versions:
#             version_map.setdefault(v.docname, []).append(v)

#         for order in orders:
#             change_log = []
#             for v in version_map.get(order["name"], []):
#                 try:
#                     data = frappe.parse_json(v.data or "{}")
#                     entries = []

#                     # parent field changes
#                     for item in data.get("changed", []):
#                         if len(item) >= 3:
#                             entries.append({
#                                 "field": item[0],
#                                 "from":  str(item[1]) if item[1] is not None else "",
#                                 "to":    str(item[2]) if item[2] is not None else "",
#                                 "table": None,
#                                 "row":   None
#                             })

#                     # child table row changes
#                     for rc in data.get("row_changed", []):
#                         if len(rc) >= 4:
#                             for item in rc[3]:
#                                 if len(item) >= 3:
#                                     entries.append({
#                                         "field": item[0],
#                                         "from":  str(item[1]) if item[1] is not None else "",
#                                         "to":    str(item[2]) if item[2] is not None else "",
#                                         "table": rc[0],
#                                         "row":   rc[2]
#                                     })

#                     if entries:
#                         change_log.append({
#                             "date":    str(v.creation),
#                             "user":    v.owner,
#                             "changes": entries
#                         })
#                 except Exception:
#                     pass

#             order["change_log"] = change_log


#     return orders



@frappe.whitelist(allow_guest=False)
def get_order_tracking_list(customer_code=None, from_date=None, to_date=None):
    filters = []

    if customer_code:
        filters.append(["Order Tracking", "customer_code", "like", f"%{customer_code}%"])

    if from_date:
        filters.append(["Order Tracking", "customer_due_date", ">=", from_date])

    if to_date:
        filters.append(["Order Tracking", "customer_due_date", "<=", to_date])

    orders = frappe.get_all(
        "Order Tracking",
        filters=filters,
        fields=[
            "name", "customer_code", "customer_name", "order_no","order_date",
            "bulk_order_no", "po_no", "main_po_no",
            "diamond_purity", "customer_due_date"
        ],
        order_by="modified desc",
        limit_page_length=0
    )

    for order in orders:
        order["order_details"] = frappe.get_all(
            "Bulk Order Detail",
            filters={"parent": order["name"]},
            fields=[
                "batch_no", "batch_date", "gorder_no","name",
                "current_department", "current_manager", "current_process",
                "setting_type", "category", "sub_category",
                "gold_weight", "dia_weight", "dia_pcs",
                "production_due_date", "finish_date",
                "from_branch", "to_branch","bulk_order_no"
            ],
            order_by="idx asc"
        )
        order["pdd_change_reasons"] = frappe.get_all(
            "Batch PDD Change Reason",
            filters={"parent": order["name"]},
            fields=["batch_no", "from_date", "reason"]   # ← from_date
        )


    order_names = [o["name"] for o in orders]

    if order_names:
        all_versions = frappe.get_all(
            "Version",
            filters={"ref_doctype": "Order Tracking", "docname": ["in", order_names]},
            fields=["docname", "creation", "owner", "data"],
            order_by="creation desc",
            limit_page_length=0
        )

        version_map = {}
        for v in all_versions:
            version_map.setdefault(v.docname, []).append(v)

        # collect every child-row name referenced in row_changed, resolve batch_no in one query
        changed_row_names = set()
        for v in all_versions:
            try:
                data = frappe.parse_json(v.data or "{}")
                for rc in data.get("row_changed", []):
                    if len(rc) >= 3:
                        changed_row_names.add(rc[2])
            except Exception:
                pass

        batch_no_map = {}
        if changed_row_names:
            rows = frappe.get_all(
                "Bulk Order Detail",
                filters={"name": ["in", list(changed_row_names)]},
                fields=["name", "batch_no"]
            )
            batch_no_map = {r.name: r.batch_no for r in rows}

        for order in orders:
            change_log = []
            for v in version_map.get(order["name"], []):
                try:
                    data = frappe.parse_json(v.data or "{}")
                    entries = []

                    # parent field changes
                    for item in data.get("changed", []):
                        if len(item) >= 3:
                            entries.append({
                                "field":    item[0],
                                "from":     str(item[1]) if item[1] is not None else "",
                                "to":       str(item[2]) if item[2] is not None else "",
                                "table":    None,
                                "row":      None,
                                "batch_no": None
                            })

                    # child table row changes
                    for rc in data.get("row_changed", []):
                        if len(rc) >= 4:
                            row_name = rc[2]
                            for item in rc[3]:
                                if len(item) >= 3:
                                    entries.append({
                                        "field":    item[0],
                                        "from":     str(item[1]) if item[1] is not None else "",
                                        "to":       str(item[2]) if item[2] is not None else "",
                                        "table":    rc[0],
                                        "row":      row_name,
                                        "batch_no": batch_no_map.get(row_name, "")
                                    })

                    if entries:
                        change_log.append({
                            "date":    str(v.creation),
                            "user":    v.owner,
                            "changes": entries
                        })
                except Exception:
                    pass

            order["change_log"] = change_log
    else:
        for order in orders:
            order["change_log"] = []

    return orders


@frappe.whitelist()
def save_pdd_change_reason(order_name, batch_no, from_date, reason):
    from datetime import datetime

    # convert DD-MM-YYYY → YYYY-MM-DD for MySQL Date field
    def to_db_date(d):
        d = str(d).strip()
        try:
            return datetime.strptime(d, "%d-%m-%Y").strftime("%Y-%m-%d")
        except Exception:
            return d  # already YYYY-MM-DD or unknown format

    from_date_db = to_db_date(from_date)

    doc = frappe.get_doc("Order Tracking", order_name)

    existing = next(
        (r for r in doc.batch_pdd_change_reason
         if r.batch_no == batch_no and str(r.from_date) == from_date_db),
        None
    )
    if existing:
        existing.reason = reason
    else:
        doc.append("batch_pdd_change_reason", {
            "batch_no":  batch_no,
            "from_date": from_date_db,   # ← stored as YYYY-MM-DD
            "reason":    reason
        })

    doc.save(ignore_permissions=True)
    return {"success": True}

