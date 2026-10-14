"""Align existing Custom Fields with the names gke_customization's fixture ships, before fixtures import.

``fixtures/custom_field.json`` ships every row under its canonical name ``{dt}-{fieldname}``. Older
gke fixtures shipped some fields under other names (fields renamed in the desk keep their document
name, e.g. ``Warehouse-custom_department`` is the ``department`` field), and a GK-line site may hold
a field under a name the fixture does not use.

The fixture import matches by *name*: ``frappe.modules.import_file.import_doc`` deletes the document
with the row's name, if any, and inserts the row. Two situations therefore break a migrate:

1. The site holds the row's ``(dt, fieldname)`` under another name. The insert then fails with
   "A field with the name ... already exists" (a ValidationError), which stops ``bench migrate``.
2. The row's name is held by a *different* field. The import silently deletes that field's Custom
   Field document (its column stays), so the field disappears from its form.

This patch runs under ``[pre_model_sync]``, before ``sync_fixtures``. For every row in the shipped file
it first moves a different field off the row's name (to that field's own canonical name), then renames
the site's document for the row's ``(dt, fieldname)`` to the row's name. Anything it cannot resolve
safely is collected and raised at the end, so the migrate stops here with a precise list instead of
in the fixture import, and Patch Log does not record the patch as done. Idempotent; a fresh install
marks it done without running it, which is correct because a fresh site holds no old names.

Custom Field does not set ``allow_rename``, and ``frappe.rename_doc(force=True)`` would run doc-event
hooks and server scripts, scan every Dynamic Link table and clear the whole cache per field. So names
move with plain UPDATEs: the Custom Field row plus the framework tables that refer to a document by
``(doctype, name)``. No Link field points at Custom Field. ``Deleted Document`` is left alone: it
records the name a deleted document had.
"""

import json

import frappe

# (doctype, reference doctype column, reference name column): framework tables that point at a document
# by (doctype, name), so a renamed field keeps its versions, comments and attachments.
REFERENCES = (
	("Version", "ref_doctype", "docname"),
	("Comment", "reference_doctype", "reference_name"),
	("File", "attached_to_doctype", "attached_to_name"),
	("Permission Log", "reference_type", "reference"),
	("ToDo", "reference_type", "reference_name"),
	("DocShare", "share_doctype", "share_name"),
	("Tag Link", "document_type", "document_name"),
	("Document Follow", "ref_doctype", "ref_docname"),
	("Activity Log", "reference_doctype", "reference_name"),
	("Communication", "reference_doctype", "reference_name"),
	("Communication Link", "link_doctype", "link_name"),
)


def execute():
	path = frappe.get_app_path("gke_customization", "fixtures", "custom_field.json")
	with open(path) as f:
		rows = [r for r in json.load(f) if r.get("doctype") == "Custom Field"]

	references = [ref for ref in REFERENCES if _has_columns(*ref)]
	site = {
		cf.name: (cf.dt, cf.fieldname)
		for cf in frappe.get_all("Custom Field", fields=["name", "dt", "fieldname"], limit_page_length=0)
	}
	by_pair = {pair: name for name, pair in site.items()}
	wanted = {r["name"]: (r["dt"], r["fieldname"]) for r in rows}
	conflicts, renamed_dts = [], set()

	def move(old, new):
		_rename(old, new, references)
		pair = site.pop(old)
		site[new] = pair
		by_pair[pair] = new
		renamed_dts.add(pair[0])
		print(f"canonicalise_custom_field_names: renamed {old!r} to {new!r}")

	for name, pair in wanted.items():
		occupant = site.get(name)
		if occupant and occupant != pair:
			# A different field holds this row's name: move it to its own canonical name first.
			target = f"{occupant[0]}-{occupant[1]}"
			if target == name or target in site or target in wanted and wanted[target] != occupant:
				conflicts.append(f"{name!r} is held by {occupant[0]}.{occupant[1]}, which cannot move to {target!r}")
				continue
			move(name, target)

		current = by_pair.get(pair)
		if current and current != name:
			if name in site:
				conflicts.append(f"{pair[0]}.{pair[1]} is held as {current!r}, but {name!r} is taken")
				continue
			move(current, name)

	for dt in sorted(renamed_dts):
		frappe.clear_cache(doctype=dt)

	if conflicts:
		frappe.throw(
			"gke_customization fixture names cannot be aligned automatically; resolve these Custom Fields "
			"by hand, then re-run bench migrate:<br>" + "<br>".join(conflicts),
			title="Custom Field name conflicts",
		)


def _rename(old, new, references):
	custom_field = frappe.qb.DocType("Custom Field")
	frappe.qb.update(custom_field).set(custom_field.name, new).where(custom_field.name == old).run()
	for doctype, doctype_column, name_column in references:
		table = frappe.qb.DocType(doctype)
		(
			frappe.qb.update(table)
			.set(table[name_column], new)
			.where((table[doctype_column] == "Custom Field") & (table[name_column] == old))
		).run()


def _has_columns(doctype, *columns):
	return frappe.db.table_exists(doctype) and all(frappe.db.has_column(doctype, c) for c in columns)
