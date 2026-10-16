"""Retire eleven BOM fields so ``tabBOM`` fits back inside the MariaDB row-size limit.

``bench migrate`` aborts while syncing fixtures with::

    ALTER TABLE `tabBOM` ADD COLUMN `custom_kggk_source_doctype` varchar(140),
                         ADD COLUMN `custom_kggk_source_name` varchar(140)
    (1118, 'Row size too large. The maximum row size for the used table type,
     not counting BLOBs, is 65535...')

``tabBOM`` carries 281 columns, 112 of them ``varchar(140)``. In utf8mb4 each of those
costs 140*4+2 = 562 bytes, so the declared row is ~64.6 KB of the hard 65,535-byte cap --
about 900 bytes of headroom against the 1,124 the two new columns need. The BOM is simply
out of room.

Removing the eight ``gemstone_type1..8`` Links, ``custom_other_item_1/2`` and ``breadth``
frees ten ``varchar(140)`` plus one ``decimal(21,9)``: ~5.6 KB, or roughly ten more Link
fields of headroom.

WHY THIS PATCH ISSUES DDL
-------------------------
Every other field-removal patch in these apps deletes the Custom Field and leaves the
column alone. That cannot work here: the bytes, not the metadata, are what overflows.
``frappe.db.updatedb`` only ever ADDs columns, so the only way to get the space back is an
explicit ``DROP COLUMN``. The values are destroyed, so they are copied into
``__bom_removed_fields_2026`` first -- ``__``-prefixed to stay out of ``bench
trim-database`` and every ``tab*`` scan. Drop that table once you are confident.

``ALGORITHM=COPY`` is deliberate. MariaDB would otherwise drop the columns instantly and
retain them in the table metadata until the next rebuild, where they keep counting toward
the 65,535-byte limit -- which would leave the migration failing exactly as before.
``bench migrate`` already holds the site in maintenance mode, and rebuilding ~100k rows
takes seconds.

The matching fixture entries are removed from
``gke_customization/fixtures/custom_field.json`` in the same commit. Without that,
``sync_fixtures`` -- which runs immediately after this patch, in ``post_schema_updates`` --
recreates all eleven fields and every column comes straight back.

Idempotent: every step is guarded, so a second run is a no-op. Can also be run ad-hoc::

    bench --site <site> execute gke_customization.patches.remove_bom_row_size_fields.execute
"""

import frappe

from jewellery_erpnext.patches.field_order_utils import (
	drop_layout_fields,
	strip_field_order_entries,
)

DOCTYPE = "BOM"
TABLE = "tabBOM"
ARCHIVE_TABLE = "__bom_removed_fields_2026"

# The retired data fields. Ten are Link -> varchar(140); ``breadth`` is a Float.
FIELDS = (
	"gemstone_type1",
	"gemstone_type2",
	"gemstone_type3",
	"gemstone_type4",
	"gemstone_type5",
	"gemstone_type6",
	"gemstone_type7",
	"gemstone_type8",
	"custom_other_item_1",
	"custom_other_item_2",
	"breadth",
)

# Float, so its "unset" test is 0 rather than an empty string.
NUMERIC_FIELDS = ("breadth",)

# Section/Column Breaks that wrap nothing at all once the eight gemstone fields are gone.
# They hold no data and get no column, so this is cosmetic -- it stops an empty section
# rendering on the BOM form.
LAYOUT_FIELDS = (
	"section_break_s9het",
	"column_break_lur9h",
	"column_break_vodng",
	"column_break_1tdce",
)

# Fields anchored on something being deleted inherit the anchor that field itself used,
# so their position stays defined on the next meta build.
REANCHOR = {
	"section_break_6fswi": "gemstone_type",  # was gemstone_type8
	"product_shape": "length",  # was breadth
	"black_bead": "section_break_olkss",  # was custom_other_item_2
}

# Site-authored Server Scripts that name a dropped column in raw SQL and would 500.
# Matched on the whole stripped line, never a substring: these are user-written scripts
# and a fuzzy rewrite of somebody's SQL is not something a patch should ever risk.
# (name, line to match, replacement line or None to delete the line)
SERVER_SCRIPT_FIXES = (
	("Gk - Catalog Api", "bom.breadth,", None),
	("GK PMO API", "bom.gemstone_type1,bom.gemstone_type,", "bom.gemstone_type,"),
)


def execute():
	_archive_values()
	_fix_server_scripts()
	_warn_about_site_scripts()

	strip_field_order_entries(DOCTYPE, list(FIELDS) + list(LAYOUT_FIELDS))
	_reanchor_dependants()
	_delete_custom_fields()

	dropped = drop_layout_fields(DOCTYPE, LAYOUT_FIELDS)
	if dropped:
		frappe.logger().info(
			"remove_bom_row_size_fields: dropped empty layout fields " + ", ".join(dropped)
		)

	_drop_columns()
	frappe.clear_cache(doctype=DOCTYPE)


def _existing_columns(columns):
	"""Which of ``columns`` are still physically on ``tabBOM``."""
	if not columns:
		return []
	return frappe.db.sql(
		"""SELECT COLUMN_NAME FROM information_schema.COLUMNS
		WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
		AND COLUMN_NAME IN ({placeholders})""".format(
			placeholders=", ".join(["%s"] * len(columns))
		),
		(TABLE, *columns),
		pluck=True,
	)


def _archive_values():
	"""Copy every BOM that has a value in a retired field into ``__bom_removed_fields_2026``.

	DROP COLUMN is irreversible, so this is the only copy of the data outside a database
	backup. Rows where all eleven fields are empty are skipped -- there is nothing to keep.
	"""
	if frappe.db.sql(
		"""SELECT 1 FROM information_schema.TABLES
		WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s""",
		ARCHIVE_TABLE,
	):
		frappe.logger().info(f"remove_bom_row_size_fields: {ARCHIVE_TABLE} already exists, skipping archive")
		return

	columns = _existing_columns(FIELDS)
	if not columns:
		return

	selected = ", ".join(f"`{column}`" for column in columns)
	populated = " OR ".join(
		f"COALESCE(`{column}`, 0) != 0"
		if column in NUMERIC_FIELDS
		else f"COALESCE(`{column}`, '') != ''"
		for column in columns
	)
	frappe.db.sql_ddl(
		f"CREATE TABLE `{ARCHIVE_TABLE}` AS"
		f" SELECT `name`, {selected} FROM `{TABLE}` WHERE {populated}"
	)
	archived = frappe.db.sql(f"SELECT COUNT(*) FROM `{ARCHIVE_TABLE}`")[0][0]
	frappe.logger().info(
		f"remove_bom_row_size_fields: archived {archived} BOM(s) into {ARCHIVE_TABLE}"
		f" ({len(columns)} column(s))"
	)


def _fix_server_scripts():
	"""Take the dropped columns out of the two Server Scripts that select them in SQL.

	Both are enabled whitelisted APIs (``merge_data`` and ``get_pmo_list``); left alone they
	raise *Unknown column* the moment the columns go. Commented-out lines are left as they
	are, and a script that no longer contains the line is skipped rather than rewritten.
	"""
	for name, target, replacement in SERVER_SCRIPT_FIXES:
		script = frappe.db.get_value("Server Script", name, "script")
		if not script:
			continue

		changed = False
		rebuilt = []
		for line in script.split("\n"):
			# A commented-out copy of the line is left alone: its ``strip()`` starts with "#"
			# and so never equals the target.
			if line.strip() == target:
				changed = True
				if replacement is None:
					continue
				# Keep the line's own indentation and trailing whitespace: GK PMO API is
				# stored with CRLF endings, and rebuilding without the \r would leave the
				# script with mixed line endings.
				indent = line[: len(line) - len(line.lstrip())]
				trailing = line[len(line.rstrip()) :]
				rebuilt.append(indent + replacement + trailing)
			else:
				rebuilt.append(line)

		if not changed:
			frappe.logger().info(
				f"remove_bom_row_size_fields: Server Script {name!r} has no {target!r} line, left as is"
			)
			continue

		updated = "\n".join(rebuilt)
		frappe.db.set_value("Server Script", name, "script", updated)
		frappe.logger().info(
			f"remove_bom_row_size_fields: rewrote Server Script {name!r}"
			f" ({len(script)} -> {len(updated)} chars)"
		)


def _warn_about_site_scripts():
	"""Name any other site-authored script still mentioning a retired field.

	``frm.set_query`` on a field that no longer exists is a silent no-op, so these do not
	break -- but somebody should tidy them in the UI, and the patch is the only place that
	knows which ones they are.
	"""
	handled = {name for name, _target, _replacement in SERVER_SCRIPT_FIXES}
	candidates = [
		("Client Script", row)
		for row in frappe.get_all("Client Script", filters={"dt": DOCTYPE}, fields=["name", "script"])
	] + [
		("Server Script", row)
		for row in frappe.get_all("Server Script", fields=["name", "script"])
		# Server Scripts carry no dt, so fall back to naming the table or its usual alias.
		if row.script and ("tabBOM" in row.script or "bom." in row.script)
	]

	for doctype, row in candidates:
		if row.name in handled or not row.script:
			continue
		hits = sorted(field for field in FIELDS if field in row.script)
		if hits:
			frappe.logger().warning(
				f"remove_bom_row_size_fields: {doctype} {row.name!r} still references "
				+ ", ".join(hits)
				+ " -- review it in the UI"
			)


def _reanchor_dependants():
	"""Re-point every Custom Field whose ``insert_after`` names a field being deleted."""
	for fieldname, anchor in REANCHOR.items():
		name = frappe.db.get_value("Custom Field", {"dt": DOCTYPE, "fieldname": fieldname}, "name")
		if not name:
			continue
		if frappe.db.get_value("Custom Field", name, "insert_after") == anchor:
			continue
		frappe.db.set_value("Custom Field", name, "insert_after", anchor)
		frappe.logger().info(
			f"remove_bom_row_size_fields: re-anchored {DOCTYPE}.{fieldname} onto {anchor}"
		)


def _delete_custom_fields():
	"""Delete the eleven Custom Fields.

	``force=True`` for the reason ``remove_serial_no_ownership_tag_field`` uses it -- these
	are Administrator-owned, and ``custom_other_item_1/2`` are ``is_system_generated``, both
	of which ``on_trash`` refuses without it.
	"""
	deleted = []
	for fieldname in FIELDS:
		name = frappe.db.get_value("Custom Field", {"dt": DOCTYPE, "fieldname": fieldname}, "name")
		if not name:
			continue
		frappe.delete_doc("Custom Field", name, force=True, ignore_permissions=True)
		deleted.append(fieldname)

	if deleted:
		frappe.logger().info(
			"remove_bom_row_size_fields: deleted Custom Fields " + ", ".join(deleted)
		)


def _drop_columns():
	"""Drop the retired columns from ``tabBOM`` -- the step that actually frees the bytes."""
	columns = _existing_columns(FIELDS)
	if not columns:
		frappe.logger().info("remove_bom_row_size_fields: no columns left to drop")
		return

	# The Custom Fields are already gone, so nothing will re-add these on the next
	# ``updatedb``. Commit that metadata before the DDL, which auto-commits anyway.
	frappe.db.commit()

	clauses = ", ".join(f"DROP COLUMN `{column}`" for column in columns)
	frappe.db.sql_ddl(f"ALTER TABLE `{TABLE}` {clauses}, ALGORITHM=COPY")
	frappe.logger().info(
		f"remove_bom_row_size_fields: dropped {len(columns)} column(s) from {TABLE}: "
		+ ", ".join(columns)
	)
