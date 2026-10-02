import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}

    if not filters.get("mwo"):
        frappe.throw(_("Please select MWO"))

    columns = get_columns()
    data = get_data(filters)
    data = blank_repeated_values(data)

    return columns, data


def get_columns():
    return [
        {
            "fieldname": "mwo",
            "label": _("MWO"),
            "fieldtype": "Link",
            "options": "Manufacturing Work Order",
            "width": 220,
        },
        {
            "fieldname": "item",
            "label": _("Item"),
            "fieldtype": "Link",
            "options": "Item",
            "width": 160,
        },
        {
            "fieldname": "mould_id",
            "label": _("Mould ID"),
            "fieldtype": "Link",
            "options": "Mould",
            "width": 180,
        },
        {
            "fieldname": "mould_no",
            "label": _("Mould No."),
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "fieldname": "rake",
            "label": _("Rake"),
            "fieldtype": "Data",
            "width": 90,
        },
        {
            "fieldname": "tray_no",
            "label": _("Tray no"),
            "fieldtype": "Data",
            "width": 90,
        },
        {
            "fieldname": "box_no",
            "label": _("Box no."),
            "fieldtype": "Data",
            "width": 90,
        },
        {
            "fieldname": "mould_wt_in_gram",
            "label": _("Mould wt in gram"),
            "fieldtype": "Data",
            "width": 140,
        },
        {
            "fieldname": "no_of_mould",
            "label": _("No. of mould"),
            "fieldtype": "Data",
            "width": 110,
        },
        {
            "fieldname": "mould_item",
            "label": _("Mould Item"),
            "fieldtype": "Link",
            "options": "Item",
            "width": 180,
        },
        {
            "fieldname": "type",
            "label": _("Type"),
            "fieldtype": "Data",
            "width": 120,
        },
    ]


def get_data(filters):
    values = {
        "mwo": filters.get("mwo")
    }

    data = frappe.db.sql("""
        SELECT
            mwo.name AS mwo,
            mwo.item_code AS item,
            mould.name AS mould_id,
            mould.mould_no AS mould_no,
            mould.rake AS rake,
            mould.tray_no AS tray_no,
            mould.box_no AS box_no,
            CAST(mould.mould_wtin_gram AS CHAR) AS mould_wt_in_gram,
            CAST(mould.no_of_moulds AS CHAR) AS no_of_mould,
            mdr.item_code AS mould_item,
            mdr.type AS type
        FROM `tabManufacturing Work Order` mwo
        INNER JOIN `tabMould Design Reference` mdr_match
            ON mdr_match.item_code = mwo.item_code
            AND mdr_match.parenttype = 'Mould'
        INNER JOIN `tabMould` mould
            ON mould.name = mdr_match.parent
        INNER JOIN `tabMould Design Reference` mdr
            ON mdr.parent = mould.name
            AND mdr.parenttype = 'Mould'
        WHERE mwo.name = %(mwo)s
        ORDER BY
            mwo.name,
            mould.name,
            mdr.idx
    """, values, as_dict=True)

    for row in data:
        if row.get("mould_wt_in_gram") not in (None, ""):
            row["mould_wt_in_gram"] = "{:.3f}".format(float(row["mould_wt_in_gram"]))
        if row.get("no_of_mould") not in (None, ""):
            row["no_of_mould"] = str(int(float(row["no_of_mould"])))

    return data


def blank_repeated_values(data):
    if not data:
        return data

    parent_fields = [
        "mwo",
        "item",
        "mould_id",
        "mould_no",
        "rake",
        "tray_no",
        "box_no",
        "mould_wt_in_gram",
        "no_of_mould",
    ]

    previous_key = None

    for row in data:
        current_key = tuple(row.get(field) for field in parent_fields)

        if previous_key == current_key:
            for field in parent_fields:
                row[field] = ""

        previous_key = current_key

    return data
