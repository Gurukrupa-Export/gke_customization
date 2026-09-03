# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class KGGKSyncState(Document):
	pass


def on_doctype_update():
	"""One row per (type, record, target), and the reconciler looks it up by that.

	Without the index the hourly reconciler full-scans this table once per doctype, and it
	grows to one row per synced Item and BOM - tens of thousands on a live jewellery site.
	"""
	frappe.db.add_index("KGGK Sync State", ["record_doctype", "record_name"])
