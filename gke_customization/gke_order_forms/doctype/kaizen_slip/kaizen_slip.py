# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class KaizenSlip(Document):
	pass

import frappe

@frappe.whitelist()
def execute(name, printed_count):
    doc = frappe.get_doc("Kaizen Slip", name)
    printed_count = int(printed_count or 0)

    if printed_count <= 0:
        frappe.throw("Printed count must be greater than 0")

    current_last = int(doc.last_page_no or 0)
    doc.db_set("last_page_no", current_last + printed_count)
    return {
        "last_page_no": current_last + printed_count
    }