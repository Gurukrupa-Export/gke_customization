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