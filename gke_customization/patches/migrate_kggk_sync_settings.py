"""Carry the Is Migrate flag onto Data Migration in KGGK.

The Manufacturing Plan sync read `Item Migration in KGGK`, while every message it printed
named `Data Migration in KGGK`. One feature, two settings screens. The value moves to the
screen that holds the site URLs and credentials; the other is left in place, untouched, so
nothing that still reads it breaks.
"""

import frappe
from frappe.utils import cint

SOURCE = "Item Migration in KGGK"
SOURCE_FIELD = "enable_item_bom_sync_on_manufacturing_plan_submit"
TARGET = "Data Migration in KGGK"


def execute():
	if not frappe.db.exists("DocType", TARGET):
		return

	# Default is off. Turning the sync on is a deliberate act, never a side effect of a patch.
	value = 0
	if frappe.db.exists("DocType", SOURCE):
		try:
			value = cint(frappe.db.get_single_value(SOURCE, SOURCE_FIELD))
		except Exception:
			value = 0

	frappe.db.set_value(TARGET, TARGET, "is_migrate", value, update_modified=False)
	frappe.db.set_value(TARGET, TARGET, "sync_status", "Idle", update_modified=False)
