# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

#  mr.name IN ('GE-MR-MF-25-27220', 'GE-MR-MF-25-27091', 'GE-MR-MF-24-00004')
#  http://192.168.200.207:8001/app/query-report/Advance%20Bagging%20Report%20From%20MR?prepared_report_name=28c359a0im

import frappe
from frappe.utils import format_datetime

def execute(filters=None):
    columns = [
        {"label": "Company", "fieldname": "company", "fieldtype": "Data","width": 220},
        {"label": "Material Req Id", "fieldname": "name", "fieldtype": "Link", "options": "Material Request", "width": 180},
        {"label": "Status", "fieldname": "workflow_state", "fieldtype": "Data","width": 220},
        {"label": "Material Req Creation", "fieldname": "creation", "fieldtype": "Data","width": 220},
        {"label": "Purpose", "fieldname": "material_request_type", "fieldtype": "Data", "width": 130},
        {"label": "Material Type", "fieldname": "material_type", "fieldtype": "Data", "width": 130},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 210},
        {"label": "Item Attributes", "fieldname": "item_attributes", "fieldtype": "Data", "width": 700},
        {"label": "Alternative Item", "fieldname": "custom_alternative_item", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": "Quantity", "fieldname": "qty", "fieldtype": "Float", "width": 100},
        {"label": "Pcs", "fieldname": "pcs", "fieldtype": "Int", "width": 80},
        {"label": "Customer PO", "fieldname": "custom_customer_po_no", "fieldtype": "Data", "width": 150},
        {"label": "Jewelex Order No", "fieldname": "custom_jewelex_order_no", "fieldtype": "Data", "width": 150},
        {"label": "Order Type", "fieldname": "custom_order_type", "fieldtype": "Data", "width": 120},
        {"label": "Ref Customer", "fieldname": "custom_ref_customer", "fieldtype": "Data", "width": 150},        
		{"label": "Manufacturing Order", "fieldname": "manufacturing_order", "fieldtype": "Link", "options": "Parent Manufacturing Order", "width": 220},
        {"label": "Manufacturer", "fieldname": "custom_manufacturer", "fieldtype": "Data", "width": 150},
        {"label": "Customer Code", "fieldname": "customer", "fieldtype": "Data", "width": 150},
        {"label": "Design Code", "fieldname": "order_item_code", "fieldtype": "Data", "width": 190},
        {"label": "MOP Status", "fieldname": "department", "fieldtype": "Data", "width": 150},
        {"label": "Item Category", "fieldname": "item_category", "fieldtype": "Data", "width": 150},
        {"label": "Item Sub Category", "fieldname": "item_sub_category", "fieldtype": "Data", "width": 150},
        {"label": "Setting Type", "fieldname": "setting_type", "fieldtype": "Data", "width": 150},
    ]

    filters_dict = {"material_request_type": "Manufacture"}

#     filters_dict = {
#     "material_request_type": "Manufacture",
#     "name": "GE-MR-MF-24-00004"  # test
# }

    if filters.get("from_date") and filters.get("to_date"):
        filters_dict["creation"] = ["between", [filters["from_date"], filters["to_date"]]]
    elif filters.get("from_date"):
        filters_dict["creation"] = [">=", filters["from_date"]]
    elif filters.get("to_date"):
        filters_dict["creation"] = ["<=", filters["to_date"]]

    if filters.get("workflow_state"):
        filters_dict["workflow_state"] = ["in", filters["workflow_state"]]

    # PMO Filter
    if filters.get("manufacturing_order"):
        filters_dict["manufacturing_order"] = ["in", filters["manufacturing_order"]]

    if filters.get("company"):
        filters_dict["company"] = filters["company"]

    data = []

    material_requests = frappe.get_all("Material Request", 
        fields=[
            "name", "material_request_type", "title", "custom_customer_po_no",
            "custom_jewelex_order_no", "custom_order_type", "manufacturing_order",
            "custom_manufacturer", "custom_ref_customer","docstatus","workflow_state","creation"
        ],
        filters=filters_dict,
       # limit=10
    )

    for mr in material_requests:
        material_type = get_material_type_from_title(mr.title)

        if filters.get("material_type") and filters["material_type"] != material_type:
            continue

        mr_items = frappe.get_all("Material Request Item",
            fields=["item_code", "qty", "custom_alternative_item", "pcs"],
            filters={"parent": mr.name}
        )

        pmo = frappe.get_value("Parent Manufacturing Order", mr.manufacturing_order,
            ["customer", "item_code", "item_category", "item_sub_category", "setting_type","ref_customer","company"], as_dict=True
        ) if mr.manufacturing_order else {}

        
        if filters.get("item_category") and pmo and pmo.get("item_category") not in filters["item_category"]:
            continue

        if filters.get("setting_type") and pmo and pmo.get("setting_type") not in filters["setting_type"]:
            continue

        department = get_department(mr.manufacturing_order)

        for item in mr_items:
            attributes = get_item_attributes(item.item_code)

            row = {
                "company":pmo.company,
                "name": mr.name,
                "workflow_state":mr.workflow_state,
                "creation":format_datetime(mr.creation, "dd-MM-yyyy HH:mm:ss"),
                "material_request_type": mr.material_request_type,
                "material_type": material_type,
                "item_code": item.item_code,
                "qty": item.qty,
                "custom_alternative_item": item.custom_alternative_item,
                "pcs": item.pcs,
                "custom_customer_po_no": mr.custom_customer_po_no,
                "custom_jewelex_order_no": mr.custom_jewelex_order_no,
                "custom_order_type": mr.custom_order_type,
                "manufacturing_order": mr.manufacturing_order,
                "custom_manufacturer": mr.custom_manufacturer,
                "custom_ref_customer": pmo.ref_customer,
                "customer": pmo.get("customer"),
                "order_item_code": pmo.get("item_code"),
                "item_category": pmo.get("item_category"),
                "item_sub_category": pmo.get("item_sub_category"),
                "setting_type": pmo.get("setting_type"),
                "department": department,
                "item_attributes": attributes
            }
            data.append(row)

    data.sort(key=lambda x: (0 if x["workflow_state"] == "Draft" else 1))

    return columns, data


def get_material_type_from_title(title):
    if not title or len(title) < 3:
        return "Unknown"

    code = title[2]  # 3rd character :MRD-SH-(BR00159-001)-2
    return {
        "D": "Diamond",
        "M": "Metal",
        "G": "Gemstone",
        "F": "Finding",
        "O": "Others"
    }.get(code, "Unknown")


def get_item_attributes(item_code):
    attributes = frappe.get_all("Item Variant Attribute",
        filters={"parent": item_code},
        fields=["attribute", "attribute_value"],
        order_by="creation asc"
    )
    return ",  ".join(f"•  {attr.attribute}: {attr.attribute_value}" for attr in attributes) if attributes else ""


def get_department(manufacturing_order):
    if not manufacturing_order:
        return ""

    mwo = frappe.get_all("Manufacturing Work Order",
        filters={
            "manufacturing_order": manufacturing_order,
            "is_finding_mwo": ["!=", 1],
            "for_fg": ["!=", 1]
        },
        pluck="name"
    )
    if not mwo:
        return ""

    mop = frappe.get_all("Manufacturing Operation",
        filters={
            "manufacturing_work_order": ["in", mwo],
            "status": ["!=", "Finished"]
        },
        fields=["department"],
        limit=1
    )
    return mop[0].department if mop else ""
