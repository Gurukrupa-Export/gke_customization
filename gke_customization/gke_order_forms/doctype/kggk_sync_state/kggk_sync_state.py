# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class KGGKSyncState(Document):
	pass


def on_doctype_update():
	"""One row per (type, record, target) - enforced by the database, not by hope.

	`mark_state` reads then writes, which is not atomic: a Manufacturing Plan job, an Item
	save and a prefill can all reach the same record at once and each find no row. Two rows
	for one record mean two different answers to "what is this called on the target" and
	"when did it last go across", and `target_names` would pick whichever the query returned
	first. The constraint is what makes that unrepresentable; `mark_state` catches the
	duplicate-key error and re-reads.

	The target site is part of the key. Two targets legitimately hold the same record under
	different names, so a constraint without it would refuse the second target's row.
	"""
	frappe.db.add_unique(
		"KGGK Sync State",
		["record_doctype", "record_name", "target_site"],
		constraint_name="unique_record_per_target",
	)
