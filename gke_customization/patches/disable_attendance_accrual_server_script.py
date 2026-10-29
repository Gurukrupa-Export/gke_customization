# Copyright (c) 2026, Gurukrupa Export
# License: GNU General Public License v3. See license.txt

import frappe

# replaced by gke_customization.gke_hrms.doc_events.leave_allocation.apply_attendance_based_allocation
SERVER_SCRIPT = "Leave accural attendance wise"


def execute():
    if frappe.db.exists("Server Script", SERVER_SCRIPT):
        frappe.db.set_value("Server Script", SERVER_SCRIPT, "disabled", 1)
