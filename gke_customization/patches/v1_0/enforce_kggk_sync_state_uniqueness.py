"""Collapse duplicate KGGK Sync State rows so the unique constraint can be added.

`mark_state` used to read-then-write with nothing stopping two workers doing it at once, and
the index it created was neither unique nor did it include the target site. Any duplicates
that race produced are still in the table, and `add_unique` will refuse while they are.

Where a record has more than one row for a target, the most recently synced one is the
truth - it is the one whose `target_name` and `local_modified` describe the last push that
actually happened. The rest are discarded.
"""

import frappe

STATE = "KGGK Sync State"


def execute():
	if not frappe.db.table_exists(STATE):
		return

	duplicates = frappe.db.sql(
		"""
		select   record_doctype, record_name, target_site, count(*) as rows_found
		from     `tabKGGK Sync State`
		group by record_doctype, record_name, target_site
		having   rows_found > 1
		""",
		as_dict=True,
	)

	removed = 0
	for group in duplicates:
		names = frappe.db.sql(
			"""
			select   name
			from     `tabKGGK Sync State`
			where    record_doctype = %(record_doctype)s
			and      record_name = %(record_name)s
			and      target_site = %(target_site)s
			-- The row that knows the most: synced most recently, and failing that touched
			-- most recently. `synced_on` is null on rows that never got across.
			order by synced_on desc, modified desc
			""",
			group,
			pluck=True,
		)
		for stale in names[1:]:
			frappe.db.delete(STATE, {"name": stale})
			removed += 1

	if removed:
		frappe.db.commit()
		print(f"KGGK Sync State: removed {removed} duplicate row(s)")

	# `on_doctype_update` adds the constraint, and it can only succeed now the table is clean.
	frappe.reload_doc("gke_order_forms", "doctype", "kggk_sync_state")
