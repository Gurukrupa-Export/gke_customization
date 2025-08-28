import frappe
from frappe.utils import format_datetime

def fetch_material_type(item_code):
    # Adjust the field below to match your schema: 'item_group', 'item_type', or your custom field.
    # Example shown with item_group.
    material_type = frappe.db.get_value("Item", item_code, "item_group")
    return material_type or ""

def execute(filters=None):
    columns = [
        {"label": "Company", "fieldname": "company", "fieldtype": "Data", "width": 220},
        {"label": "BOM ID", "fieldname": "bom_id", "fieldtype": "Link", "options": "BOM", "width": 180},
        {"label": "BOM Type", "fieldname": "bom_type", "fieldtype": "Data", "width": 130},
        {"label": "BOM Creation", "fieldname": "bom_creation", "fieldtype": "Data", "width": 150},
        {"label": "Material Type", "fieldname": "material_type", "fieldtype": "Data", "width": 130},
        {"label": "Item Attributes", "fieldname": "item_attributes", "fieldtype": "Data", "width": 350},
        {"label": "Quantity", "fieldname": "qty", "fieldtype": "Float", "width": 100},
        {"label": "Pcs", "fieldname": "pcs", "fieldtype": "Int", "width": 80},
        {"label": "Design Code", "fieldname": "design_code", "fieldtype": "Data", "width": 180},
        {"label": "Item Category", "fieldname": "item_category", "fieldtype": "Data", "width": 150},
        {"label": "Item Sub Category", "fieldname": "item_sub_category", "fieldtype": "Data", "width": 150}
    ]

    filters = filters or {}
    filters_dict = {"material_request_type": "Manufacture"}

    if filters.get("from_date") and filters.get("to_date"):
        filters_dict["creation"] = ["between", [filters["from_date"], filters["to_date"]]]
    elif filters.get("from_date"):
        filters_dict["creation"] = [">=", filters["from_date"]]
    elif filters.get("to_date"):
        filters_dict["creation"] = ["<=", filters["to_date"]]

    if filters.get("bom_id"):
        mwo_names = frappe.get_list("Parent Manufacturing Order",
                                    filters={"master_bom": filters["bom_id"]},
                                    pluck="name")
        if mwo_names:
            filters_dict["manufacturing_order"] = ["in", mwo_names]
        else:
            return columns, []

    if filters.get("design_code"):
        filters_dict["item_code"] = filters["design_code"]

    material_requests = frappe.get_all(
        "Material Request",
        fields=["name", "company", "creation", "material_request_type",
                "workflow_state", "manufacturing_order"],
        filters=filters_dict
    )

    data = []

    for mr in material_requests:
        mr_items = frappe.get_all(
            "Material Request Item",
            fields=["item_code", "qty", "pcs"],
            filters={"parent": mr.name}
        )

        mwo = frappe.get_doc("Parent Manufacturing Order", mr.manufacturing_order) if mr.manufacturing_order else None

        if filters.get("item_category") and mwo and mwo.item_category not in filters["item_category"]:
            continue
        if filters.get("item_sub_category") and mwo and mwo.item_sub_category not in filters["item_sub_category"]:
            continue

        bom_type = ""
        bom_creation = ""
        bom_id = ""
        if mwo and mwo.master_bom:
            bom_doc = frappe.get_value("BOM", mwo.master_bom, ["bom_type", "creation"], as_dict=True)
            if bom_doc:
                bom_type = bom_doc.get("bom_type", "")
                bom_creation = format_datetime(bom_doc.get("creation"), "dd-MM-yyyy HH:mm:ss")
                bom_id = mwo.master_bom

        for item in mr_items:
            # Get material type directly from Item table
            material_type = fetch_material_type(item.item_code)

            attributes_list = frappe.get_all(
                "Item Variant Attribute",
                filters={"parent": item.item_code},
                fields=["attribute", "attribute_value"],
                order_by="creation asc"
            )
            item_attributes = ", ".join(f"• {attr['attribute']}: {attr['attribute_value']}" for attr in attributes_list) if attributes_list else ""

            row = {
                "company": mr.company,
                "bom_id": bom_id,
                "bom_type": bom_type,
                "bom_creation": bom_creation,
                "material_type": material_type,
                "item_attributes": item_attributes,
                "qty": item.qty,
                "pcs": item.pcs or 0,
                "design_code": mwo.item_code if mwo else "",
                "item_category": mwo.item_category if mwo else "",
                "item_sub_category": mwo.item_sub_category if mwo else ""
            }
            data.append(row)

    return columns, data
