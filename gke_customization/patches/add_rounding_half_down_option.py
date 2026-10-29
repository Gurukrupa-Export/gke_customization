# Copyright (c) 2026, Gurukrupa Export
# License: GNU General Public License v3. See license.txt

import frappe

NEW_OPTION = "0.5 Down"


def execute():
    # add "0.5 Down" (floor to nearest half day) to the Leave Type rounding
    # select, keeping whatever options the site already has
    field = frappe.get_meta("Leave Type").get_field("rounding")
    options = field.options or ""

    if NEW_OPTION in options.split("\n"):
        return

    lines = options.split("\n")
    if "0.5" in lines:
        lines.insert(lines.index("0.5") + 1, NEW_OPTION)
    else:
        lines.append(NEW_OPTION)

    frappe.make_property_setter(
        {
            "doctype_or_field": "DocField",
            "doctype": "Leave Type",
            "fieldname": "rounding",
            "property": "options",
            "value": "\n".join(lines),
            "property_type": "Select",
        },
        validate_fields_for_doctype=False,
        # user-generated setters survive future doctype syncs; this patch runs only once per site
        is_system_generated=False,
    )
