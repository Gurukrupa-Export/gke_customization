# Copyright (c) 2026, Gurukrupa Export
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def execute():
    """Index Employee Checkin.attendance for the Attendance to Employee Checkin joins in reports and the monthly log.

    The Property Setter keeps the index from being dropped when the Employee Checkin doctype syncs on migrate.
    """
    make_property_setter(
        "Employee Checkin", "attendance", "search_index", "1", "Check", for_doctype=False
    )

    if not frappe.db.get_column_index("tabEmployee Checkin", "attendance", unique=False):
        frappe.db.add_index("Employee Checkin", ["attendance"])
