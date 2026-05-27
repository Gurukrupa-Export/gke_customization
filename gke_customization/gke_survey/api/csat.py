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
