# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

"""Add the synthetic resolver sources to the Employee Checkin 'source' Select.

The Monthly In-Out Log error resolver writes OUT checkins with
source = "OT Resolver" / "Auto Close". Existing sites already have the custom
field, so the updated options from punch_pairing_fields (which only runs once)
never reach them; this patch appends the two options in place.
"""

import frappe

SOURCE_OPTIONS = (
    "\nEmployee Checkin\nManual Punch\nBiometric\nOutdoor Duty\n"
    "Work From Home\nOT Resolver\nAuto Close"
)


def execute():
    name = frappe.db.exists(
        "Custom Field", {"dt": "Employee Checkin", "fieldname": "source"}
    )
    if not name:
        return  # fresh installs get the full list from punch_pairing_fields

    current = frappe.db.get_value("Custom Field", name, "options") or ""
    if "Auto Close" not in current:
        frappe.db.set_value("Custom Field", name, "options", SOURCE_OPTIONS)
