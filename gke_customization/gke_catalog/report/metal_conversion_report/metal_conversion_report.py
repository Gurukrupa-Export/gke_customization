from collections import defaultdict

import frappe
from frappe import _
from jewellery_erpnext.jewellery_erpnext.customization.utils.row_ownership import (
    CUSTOMER_INVENTORY_TYPES,
    DEFAULT_INVENTORY_TYPE,
)

#: The Stock Entry a conversion books. Kept local: jewellery ``kggk_prod``'s
#: ``row_ownership`` has no ``METAL_CONVERSION_SE_TYPE``.
CONVERSION_SE_TYPE = "Repack-Metal Conversion"

#: The conversions each "Is Customer Metal" filter keeps. "Yes" keeps Mixed ones too, so
#: no conversion that consumed customer metal is hidden by the filter.
CUSTOMER_METAL_FILTER = {"Yes": ("Yes", "Mixed"), "No": ("No",)}


def execute(filters=None):
    columns, data = [], []

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    return [
        {
            "label": _("Metal Conversion ID"),
            "fieldname": "metal_conversion_id",
            "fieldtype": "Link",
            "options": "Metal Conversions",
            "width": 160,
        },
        {
            "label": _("Stock Entry ID"),
            "fieldname": "stock_entry",
            "fieldtype": "Link",
            "options": "Stock Entry",
            "width": 150,
        },
        {
            "label": _("Creation Date & Time"),
            "fieldname": "creation_datetime",
            "fieldtype": "Datetime",
            "width": 160,
        },
        # {
        #     "label": _("Company"),
        #     "fieldname": "company",
        #     "fieldtype": "Link",
        #     "options": "Company",
        #     "width": 120
        # },
        # {
        #     "label": _("Branch"),
        #     "fieldname": "branch",
        #     "fieldtype": "Link",
        #     "options": "Branch",
        #     "width": 120
        # },
        {
            "label": _("Manufacturer"),
            "fieldname": "manufacturer",
            "fieldtype": "Link",
            "options": "Manufacturer",
            "width": 120,
        },
        {
            "label": _("User"),
            "fieldname": "user_name",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Department"),
            "fieldname": "department",
            "fieldtype": "Link",
            "options": "Department",
            "width": 120,
        },
        {
            "label": _("Source Item"),
            "fieldname": "source_item",
            "fieldtype": "Link",
            "options": "Item",
            "width": 150,
        },
        {
            "label": _("Source Item Qty"),
            "fieldname": "source_qty",
            "fieldtype": "Float",
            "width": 120,
            "precision": 3,
        },
        {
            "label": _("Source Alloy"),
            "fieldname": "source_alloy",
            "fieldtype": "Link",
            "options": "Item",
            "width": 150,
        },
        {
            "label": _("Source Alloy Qty"),
            "fieldname": "source_alloy_qty",
            "fieldtype": "Float",
            "width": 130,
            "precision": 3,
        },
        {
            "label": _("Target Item"),
            "fieldname": "target_item",
            "fieldtype": "Link",
            "options": "Item",
            "width": 150,
        },
        {
            "label": _("Target Item Qty"),
            "fieldname": "target_qty",
            "fieldtype": "Float",
            "width": 130,
            "precision": 3,
        },
        {
            "label": _("Is Customer Metal"),
            "fieldname": "is_customer_metal",
            "fieldtype": "Data",
            "width": 130,
        },
    ]


def get_data(filters):
    filters = frappe._dict(filters or {})
    conditions = get_conditions(filters)

    query = f"""
        SELECT
            mc.creation as creation_datetime,
            mc.name as metal_conversion_id,
            mc.company,
            mc.branch,
            mc.manufacturer,
            COALESCE(u.full_name, u.first_name, mc.owner) as user_name,
            mc.department,
            mc.source_item,
            mc.source_qty,
            mc.source_alloy,
            mc.source_alloy_qty,
            mc.target_item,
            mc.target_qty
        FROM
            `tabMetal Conversions` mc
        LEFT JOIN
            `tabUser` u ON mc.owner = u.name
        WHERE
            mc.docstatus = 1
            AND mc.target_item IS NOT NULL
            AND mc.target_item != ''
            {conditions}
        ORDER BY
            mc.creation DESC
    """

    data = frappe.db.sql(query, filters, as_dict=1)

    ownership = get_conversion_ownership(data)
    for row in data:
        row.update(ownership[row.metal_conversion_id])

    wanted = CUSTOMER_METAL_FILTER.get(filters.is_customer_metal)
    if wanted:
        data = [row for row in data if row.is_customer_metal in wanted]

    return data


def get_conversion_ownership(conversions):
    """Each conversion's Stock Entry and whose metal it consumed, keyed by conversion.

    The header records no owner: FIFO may draw one conversion from several owners, and each
    row of the conversion's Stock Entry carries its own lane's inventory type and customer.
    The entry is found through its ``custom_metal_conversion_reference`` back-reference,
    because ``Metal Conversions.stock_entry`` is empty on historical conversions. Cancelled
    entries and the conversion's Process Loss entry are left out. Two queries, however many
    conversions are listed.
    """
    if not conversions:
        return {}

    entries = frappe.get_all(
        "Stock Entry",
        filters={
            "stock_entry_type": CONVERSION_SE_TYPE,
            "docstatus": 1,
            "custom_metal_conversion_reference": [
                "in",
                [row.metal_conversion_id for row in conversions],
            ],
        },
        fields=["name", "custom_metal_conversion_reference"],
        order_by="name asc",
    )
    stock_entry, conversion_of = {}, {}
    for entry in entries:
        conversion_of[entry.name] = entry.custom_metal_conversion_reference
        stock_entry.setdefault(entry.custom_metal_conversion_reference, entry.name)

    rows_of = defaultdict(list)
    if entries:
        for item in frappe.get_all(
            "Stock Entry Detail",
            filters={
                "parenttype": "Stock Entry",
                "parent": ["in", list(conversion_of)],
            },
            fields=["parent", "item_code", "s_warehouse", "inventory_type"],
            order_by="parent asc, idx asc",
        ):
            rows_of[conversion_of[item.parent]].append(item)

    return {
        row.metal_conversion_id: {
            "stock_entry": stock_entry.get(row.metal_conversion_id),
            **summarise_ownership(row.source_item, rows_of[row.metal_conversion_id]),
        }
        for row in conversions
    }


def summarise_ownership(source_item, rows):
    """Whose metal a conversion consumed: "Yes", "No", "Mixed", or "" when no row says.

    Only the rows that consume ``source_item`` count. The alloy is company stock even in a
    customer's conversion (MCON00333 drew 1.798 g of it), and the produced rows carry the
    lane of the metal they were made from. A row with no inventory type is company stock,
    as in jewellery's ``get_batch_lane_map``.
    """
    consumed = [row for row in rows if row.s_warehouse and row.item_code == source_item]
    customer_rows = [
        row
        for row in consumed
        if (row.inventory_type or DEFAULT_INVENTORY_TYPE) in CUSTOMER_INVENTORY_TYPES
    ]
    if not consumed:
        flag = ""
    elif not customer_rows:
        flag = "No"
    elif len(customer_rows) < len(consumed):
        flag = "Mixed"
    else:
        flag = "Yes"
    return {"is_customer_metal": flag}


def get_conditions(filters):
    conditions = ""

    if filters.get("manufacturer"):
        conditions += " AND mc.manufacturer = %(manufacturer)s"

    if filters.get("department"):
        conditions += " AND mc.department = %(department)s"

    if filters.get("conversion_type"):
        if filters.get("conversion_type") == "Pure to Touch":
            conditions += " AND mc.source_qty < mc.target_qty"
        elif filters.get("conversion_type") == "Touch to Pure":
            conditions += " AND mc.target_qty < mc.source_qty"
        elif filters.get("conversion_type") == "Other Conversions":
            conditions += " AND mc.source_qty = mc.target_qty"

    if filters.get("from_date"):
        conditions += " AND DATE(mc.creation) >= %(from_date)s"

    if filters.get("to_date"):
        conditions += " AND DATE(mc.creation) <= %(to_date)s"

    return conditions
