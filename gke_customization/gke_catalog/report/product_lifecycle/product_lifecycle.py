# Copyright (c) 2026
# For license information, please see license.txt

import json

import frappe
from frappe.desk.query_report import get_report_doc

REPORT_NAME = "Product Lifecycle"


DOCTYPES = {
    "sketch_parent": "Sketch Order",
    "sketch_cmo_child": "Final Sketch Approval CMO",
    "cad_child": "Order Form Detail",
    "order": "Order",
    "repair_child": "Repair Order Form Detail",
    "pr_parent": "Purchase Receipt",
    "pr_child": "Purchase Receipt Item",
    "se_parent": "Stock Entry",
    "se_child": "Stock Entry Detail",
    "re_parent": "Refining Entry",
    "re_child": "Refining Serial No Detail",
    "pc_parent": "Product Certification",
    "pc_child": "Product Details",
    "snc": "Serial Number Creator",
    "serial_no": "Serial No",
    "mop": "Manufacturing Operation",
}

ITEM_JOIN_FIELD = {
    "cad": "design_id",
    "repair": "item",
}


def execute(filters=None):
    """Standard script report entry point.

    This report renders as fully custom HTML on the client
    (see finish_tag_history.js) instead of the default datatable grid,
    so we intentionally return empty columns/data here. All real data is
    fetched via the whitelisted get_finish_tag_history() method below.
    """
    return [], []


def resolve_item_code(filters):
    item_code_bom = (filters.get("item_code_bom") or "").strip()
    tag_no = (filters.get("tag_no") or "").strip()

    if item_code_bom:
        if frappe.db.exists("BOM", item_code_bom):
            return frappe.db.get_value("BOM", item_code_bom, "item")
        return item_code_bom
    elif tag_no:
        return frappe.db.get_value("Serial No", tag_no, "item_code")

    return None


@frappe.whitelist()
def get_finish_tag_history(filters=None):
    # Whitelisted, so any logged-in user can call it directly: repeat Desk's report
    # access check (the report's roles and report permission on Order Form) first.
    get_report_doc(REPORT_NAME)
    if isinstance(filters, str):
        filters = json.loads(filters)
    filters = frappe._dict(filters or {})

    item_code_bom = (filters.get("item_code_bom") or "").strip()
    tag_no = (filters.get("tag_no") or "").strip()
    item_code = resolve_item_code(filters)

    sections = []

    if item_code_bom or tag_no:
        sketch_section, design_codes = get_sketch_section(item_code)
        sections.append(sketch_section)
        sections.append(get_cad_section(design_codes))
        sections.append(get_repair_section(design_codes))
        sections.append(build_serial_no_section(item_code, None))

    if tag_no:
        sections.append(get_purchase_receipt_section(tag_no))
        sections.append(get_stock_entry_section(tag_no))
        sections.append(get_serial_number_creator_section(tag_no))
        sections.append(get_product_certification_section(tag_no))
        sections.append(get_refining_section(tag_no))

    return {"sections": sections, "item": get_item_summary(item_code)}


@frappe.whitelist()
def get_serial_no_section_data(filters=None, department=None):
    """Refreshes just the Serial No section, for its inline Department filter."""
    get_report_doc(REPORT_NAME)
    if isinstance(filters, str):
        filters = json.loads(filters)
    filters = frappe._dict(filters or {})

    item_code = resolve_item_code(filters)
    department = (department or "").strip()

    return build_serial_no_section(item_code, department)


def get_item_summary(item_code):
    if not item_code:
        return None

    item = frappe.db.get_value(
        "Item", item_code, ["item_code", "item_name", "custom_catalogue_image"], as_dict=True
    )
    if not item:
        return None

    return {
        "item_code": item.item_code,
        "item_name": item.item_name,
        "image": item.custom_catalogue_image,
    }


def placeholder_section(title):
    return {
        "title": title,
        "columns": [{"label": "Note", "fieldname": "note"}],
        "rows": [{"note": "Field mapping pending - to be configured"}],
    }


def get_sketch_section(item_code):
    """Returns (section, design_codes).

    Looks up Item.variant_of for item_code, then matches that value against
    Final Sketch Approval CMO.item to find the correct Sketch Order(s) -
    Sketch Order.item_code itself is not used as a join key (unreliable).

    design_codes is {item_code, variant_of} - the values a CAD/Repair row's
    design code field might reference for this product.
    """
    variant_of = frappe.db.get_value("Item", item_code, "variant_of") if item_code else None

    design_codes = set()
    if item_code:
        design_codes.add(item_code)
    if variant_of:
        design_codes.add(variant_of)

    rows = []

    if variant_of:
        cmo_rows = frappe.get_all(
            DOCTYPES["sketch_cmo_child"],
            filters={"item": variant_of},
            fields=["parent", "item"],
        )

        if cmo_rows:
            sketch_orders = frappe.get_all(
                DOCTYPES["sketch_parent"],
                filters={"name": ["in", list({cmo.parent for cmo in cmo_rows})]},
                fields=["name", "design_type", "design_by"],
            )
            so_by_name = {so.name: so for so in sketch_orders}

            for cmo in cmo_rows:
                so = so_by_name.get(cmo.parent)
                rows.append(
                    {
                        "sketch_order": cmo.parent,
                        "design_type": so.design_type if so else None,
                        "design_code": cmo.item,
                        "design_by": so.design_by if so else None,
                    }
                )

    return (
        {
            "title": "Sketch Order/Form",
            "columns": [
                {"label": "Sketch Order", "fieldname": "sketch_order"},
                {"label": "Design Type", "fieldname": "design_type"},
                {"label": "Design Code", "fieldname": "design_code"},
                {"label": "Design By", "fieldname": "design_by"},
            ],
            "rows": rows,
        },
        list(design_codes),
    )


def get_cad_section(design_codes):
    child_rows = (
        frappe.get_all(
            DOCTYPES["cad_child"],
            filters={ITEM_JOIN_FIELD["cad"]: ["in", design_codes]},
            fields=[
                "name",
                "parent",
                "design_type",
                "tag_no",
                "bom",
                "design_id",
                "design_by",
                "mod_reason",
            ],
        )
        if design_codes
        else []
    )

    order_by_cad_row = {}
    if child_rows:
        orders = frappe.get_all(
            DOCTYPES["order"],
            filters={"cad_order_form_detail": ["in", [row.name for row in child_rows]]},
            fields=["name", "cad_order_form_detail"],
        )
        for o in orders:
            order_by_cad_row[o.cad_order_form_detail] = o.name

    rows = []
    for row in child_rows:
        rows.append(
            {
                "order_form": row.parent,
                "order_no": order_by_cad_row.get(row.name),
                "design_type": row.design_type,
                "serial_no": row.tag_no,
                "bom": row.bom,
                "required_design": row.design_id,
                "design_by": row.design_by,
                "reason": row.mod_reason,
            }
        )

    return {
        "title": "CAD Order/Form/Order",
        "columns": [
            {"label": "Order Form", "fieldname": "order_form"},
            {"label": "Order No", "fieldname": "order_no"},
            {"label": "Design Type", "fieldname": "design_type"},
            {"label": "Serial No", "fieldname": "serial_no"},
            {"label": "BOM", "fieldname": "bom"},
            {"label": "Required Design", "fieldname": "required_design"},
            {"label": "Design By", "fieldname": "design_by"},
            {"label": "Reason", "fieldname": "reason"},
        ],
        "rows": rows,
    }


def get_repair_section(design_codes):
    child_rows = (
        frappe.get_all(
            DOCTYPES["repair_child"],
            filters={ITEM_JOIN_FIELD["repair"]: ["in", design_codes]},
            fields=[
                "name",
                "parent",
                "repair_type",
                "tag_no",
                "serial_no_bom",
                "required_design",
                "product_type",
                "mod_reason",
            ],
        )
        if design_codes
        else []
    )

    rows = [
        {
            "design_type": row.repair_type,
            "serial_no": row.tag_no,
            "bom": row.serial_no_bom,
            "required_design": row.required_design,
            "product_type": row.product_type,
            "reason": row.mod_reason,
        }
        for row in child_rows
    ]

    return {
        "title": "Repair Order",
        "columns": [
            {"label": "Design Type", "fieldname": "design_type"},
            {"label": "Serial No", "fieldname": "serial_no"},
            {"label": "BOM", "fieldname": "bom"},
            {"label": "Required Design", "fieldname": "required_design"},
            {"label": "Product Type", "fieldname": "product_type"},
            {"label": "Reason", "fieldname": "reason"},
        ],
        "rows": rows,
    }


def get_purchase_receipt_section(tag_no):
    # serial_no on Purchase Receipt Item is typically a multi-line text
    # field listing several serials, hence the LIKE match.
    child_rows = frappe.get_all(
        DOCTYPES["pr_child"],
        filters={"serial_no": ["like", f"%{tag_no}%"]},
        fields=["name", "parent", "serial_no"],
    )

    parent_cache = {}
    rows = []
    for row in child_rows:
        if row.parent not in parent_cache:
            parent_cache[row.parent] = frappe.db.get_value(
                DOCTYPES["pr_parent"],
                row.parent,
                ["supplier_name", "posting_date"],
                as_dict=True,
            )
        pr = parent_cache[row.parent]
        rows.append(
            {
                "serial_no": row.serial_no,
                "customer": pr.supplier_name if pr else None,
                "date": pr.posting_date if pr else None,
            }
        )

    return {
        "title": "Purchase Receipt",
        "columns": [
            {"label": "Serial No", "fieldname": "serial_no"},
            {"label": "Customer", "fieldname": "customer"},
            {"label": "Date", "fieldname": "date"},
        ],
        "rows": rows,
    }


def get_stock_entry_section(tag_no):
    # serial_no on Stock Entry Detail is typically a multi-line text
    # field listing several serials, hence the LIKE match (same pattern
    # as Purchase Receipt Item above).
    child_rows = frappe.get_all(
        DOCTYPES["se_child"],
        filters={"serial_no": ["like", f"%{tag_no}%"]},
        fields=["parent"],
        distinct=True,
    )

    rows = []
    if child_rows:
        parents = [row.parent for row in child_rows]
        latest = frappe.get_all(
            DOCTYPES["se_parent"],
            filters={"name": ["in", parents]},
            fields=["name", "_customer", "posting_date"],
            order_by="posting_date desc, creation desc",
            limit_page_length=1,
        )
        if latest:
            rows.append(
                {
                    "customer": latest[0]._customer,
                    "date": latest[0].posting_date,
                }
            )

    return {
        "title": "Stock Entry",
        "columns": [
            {"label": "Customer", "fieldname": "customer"},
            {"label": "Date", "fieldname": "date"},
        ],
        "rows": rows,
    }


def get_serial_number_creator_section(tag_no):
    entries = frappe.get_all(
        DOCTYPES["snc"],
        filters={"fg_serial_no": tag_no},
        fields=[
            "parent_manufacturing_order",
            "manufacturing_work_order",
            "manufacturing_operation",
            "creation",
        ],
    )

    rows = [
        {
            "pmo": e.parent_manufacturing_order,
            "mwo": e.manufacturing_work_order,
            "mop": e.manufacturing_operation,
            "date": frappe.utils.getdate(e.creation),
        }
        for e in entries
    ]

    return {
        "title": "Serial Number Creator",
        "columns": [
            {"label": "PMO", "fieldname": "pmo"},
            {"label": "MWO", "fieldname": "mwo"},
            {"label": "MOP", "fieldname": "mop"},
            {"label": "Date", "fieldname": "date"},
        ],
        "rows": rows,
    }


def get_product_certification_section(tag_no):
    child_rows = frappe.get_all(
        DOCTYPES["pc_child"],
        filters={"serial_no": tag_no},
        fields=["parent"],
        distinct=True,
    )

    rows = []
    if child_rows:
        parents = [row.parent for row in child_rows]
        entries = frappe.get_all(
            DOCTYPES["pc_parent"],
            filters={"name": ["in", parents]},
            fields=["name", "supplier", "date"],
        )
        rows = [
            {
                "issue_no": pc.name,
                "supplier_id": pc.supplier,
                "date": pc.date,
            }
            for pc in entries
        ]

    return {
        "title": "Product Certifications",
        "columns": [
            {"label": "Issue No", "fieldname": "issue_no"},
            {"label": "Supplier ID", "fieldname": "supplier_id"},
            {"label": "Date", "fieldname": "date"},
        ],
        "rows": rows,
    }


def build_serial_no_section(item_code, department=None):
    """Serial No section - weight per serial is contextual, not a fixed field.

    With no department filter, weight is the item's gross weight (from the
    serial's own BOM, or the item's active BOM). With a department filter,
    weight is that serial's received_gross_wt from its most recent
    Manufacturing Operation at that department - the department filter here
    is an inline control scoped to this section only and does not affect
    the other sections.
    """
    serials = (
        frappe.get_all(
            DOCTYPES["serial_no"],
            filters={"item_code": item_code},
            fields=["name", "custom_bom_no"],
            order_by="name",
        )
        if item_code
        else []
    )

    if department:
        weight_by_serial = get_department_weight_map([s.name for s in serials], department)
    else:
        weight_by_serial = get_gross_weight_map(item_code, serials)

    rows = [
        {
            "serial_no": s.name,
            "weight": weight_by_serial.get(s.name),
        }
        for s in serials
    ]

    return {
        "key": "serial_no",
        "title": "Serial No",
        "filterable": True,
        "columns": [
            {"label": "Serial No", "fieldname": "serial_no"},
            {"label": "Weight", "fieldname": "weight"},
        ],
        "rows": rows,
        "inline_filters": [
            {
                "fieldname": "department",
                "label": "Department",
                "fieldtype": "Link",
                "options": "Department",
                "value": department or "",
            }
        ],
    }


def get_gross_weight_map(item_code, serials):
    default_bom = None
    bom_gross_wt = {}
    weight_by_serial = {}

    for s in serials:
        bom = s.custom_bom_no
        if not bom:
            if default_bom is None:
                default_bom = (
                    frappe.db.get_value(
                        "BOM",
                        {"item": item_code, "is_active": 1},
                        "name",
                        order_by="creation desc",
                    )
                    or ""
                )
            bom = default_bom

        if not bom:
            continue

        if bom not in bom_gross_wt:
            bom_gross_wt[bom] = frappe.db.get_value("BOM", bom, "gross_weight")

        weight_by_serial[s.name] = bom_gross_wt[bom]

    return weight_by_serial


def get_department_weight_map(serial_names, department):
    if not serial_names:
        return {}

    mop_rows = frappe.db.sql(
        """
        SELECT serial_no, received_gross_wt, creation
        FROM `tabManufacturing Operation`
        WHERE department = %(department)s
          AND serial_no IS NOT NULL
          AND serial_no != ''
        """,
        {"department": department},
        as_dict=True,
    )

    serial_names = set(serial_names)
    latest_by_serial = {}

    for row in mop_rows:
        tokens = row.serial_no.replace("\r", "\n").replace("\n", ",").split(",")
        for token in tokens:
            serial = token.strip()
            if serial not in serial_names:
                continue
            existing = latest_by_serial.get(serial)
            if not existing or row.creation > existing[0]:
                latest_by_serial[serial] = (row.creation, row.received_gross_wt)

    return {serial: data[1] for serial, data in latest_by_serial.items()}


def get_refining_section(tag_no):
    child_rows = frappe.get_all(
        DOCTYPES["re_child"],
        filters={"serial_number": tag_no},
        fields=["parent"],
        distinct=True,
    )

    rows = []
    if child_rows:
        parents = [row.parent for row in child_rows]
        entries = frappe.get_all(
            DOCTYPES["re_parent"],
            filters={"name": ["in", parents], "status": "Received"},
            fields=["name", "creation"],
        )
        rows = [
            {
                "refining_id": re.name,
                "creation_date": frappe.utils.getdate(re.creation),
            }
            for re in entries
        ]

    return {
        "title": "Refining",
        "columns": [
            {"label": "Refining ID", "fieldname": "refining_id"},
            {"label": "Creation Date", "fieldname": "creation_date"},
        ],
        "rows": rows,
    }