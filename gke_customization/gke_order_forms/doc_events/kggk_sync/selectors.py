"""Which records need pushing.

Shared by the manual button, the scheduler drain and the Manufacturing Plan retry, so
"unsynced" means the same thing everywhere.
"""

import frappe
from frappe.query_builder import DocType

# The scope the Item/BOM doc-event hooks have always used. Kept here so the manual and
# scheduled paths cannot drift from what the hooks push.
ITEM_SCOPE = {"setting_type": "Close"}
BOM_SCOPE = {"setting_type": "Close", "bom_type": "Template"}


def has_markers(doctype):
	return frappe.db.has_column(doctype, "custom_is_sync")


def is_synced(doctype, name):
	"""True only if the record synced *and* has not been edited since."""
	if not has_markers(doctype):
		return False
	row = frappe.db.get_value(
		doctype, name, ["custom_is_sync", "custom_last_synced_on", "modified"], as_dict=True
	)
	if not row or not frappe.utils.cint(row.custom_is_sync):
		return False
	if not row.custom_last_synced_on:
		return False
	return frappe.utils.get_datetime(row.custom_last_synced_on) >= frappe.utils.get_datetime(row.modified)


def unsynced(doctype, scope=None, limit=200, since=None):
	"""Records in scope that still need a push, oldest first.

	"Needs a push" is deliberately not just ``custom_is_sync != 1``. A record that synced
	last week and was edited yesterday is out of date on the target, and a marker-only
	check would skip it forever. Anything whose ``modified`` is newer than its last sync
	counts as unsynced again.
	"""
	table = DocType(doctype)
	query = frappe.qb.from_(table).select(table.name)

	for field, value in (scope or {}).items():
		query = query.where(table[field] == value)

	if since:
		query = query.where(table.modified >= since)

	if has_markers(doctype):
		query = query.where(
			(table.custom_is_sync != 1)
			| table.custom_is_sync.isnull()
			| table.custom_last_synced_on.isnull()
			| (table.custom_last_synced_on < table.modified)
		)

	query = query.orderby(table.modified).limit(limit)
	return [row[0] for row in query.run()]


def unsynced_items(limit=200, since=None):
	return unsynced("Item", ITEM_SCOPE, limit=limit, since=since)


def unsynced_boms(limit=200, since=None):
	return unsynced("BOM", BOM_SCOPE, limit=limit, since=since)


def mark_stale(doctype, name):
	"""Force a record back into the unsynced set, for a deliberate re-push."""
	if has_markers(doctype):
		frappe.db.set_value(doctype, name, "custom_is_sync", 0, update_modified=False)


def has_been_pushed(doctype, name):
	"""Has this record ever reached the target, by any route?"""
	if not frappe.db.has_column(doctype, "custom_last_synced_on"):
		return False
	return bool(frappe.db.get_value(doctype, name, "custom_last_synced_on"))


def in_hook_scope(doc):
	"""The narrow scope the Item/BOM doc-event hooks have always used."""
	scope = ITEM_SCOPE if doc.doctype == "Item" else BOM_SCOPE
	return all(doc.get(field) == value for field, value in scope.items())


def should_push_on_update(doc):
	"""True when a save on this record must be propagated to the target.

	Two ways in, and the second one matters:

	1. The record is in the hook scope - `setting_type = Close`, and for BOM
	   `bom_type = Template`. Unchanged from the original implementation.

	2. The record has been pushed before, by any route. A Manufacturing Plan deliberately
	   ignores the hook scope: every plan BOM is `bom_type = Manufacturing Process`, and
	   plans carry items of any setting type. Gating updates on scope alone would push
	   those records once and then let them drift on the target forever, which is worse
	   than never having sent them - the target would show stale data that looks current.
	"""
	if in_hook_scope(doc):
		return True
	return has_been_pushed(doc.doctype, doc.name)
