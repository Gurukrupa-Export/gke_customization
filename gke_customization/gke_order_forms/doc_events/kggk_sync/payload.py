"""Build the outbound payload from the doctype definition, not from a hand-typed dict.

The old code listed field names by hand, so every field a developer forgot to type was a
field that silently never reached the target. Walking the meta means a custom field added
next month travels without anyone editing this file.
"""

import frappe
from frappe.utils import cint, flt

# Pure layout - never has a value worth sending. "Image" belongs here too: those fields are
# read-only mirrors of an Attach field (item_image_preview mirrors image), and the target
# recomputes them.
LAYOUT_TYPES = {
	"Section Break",
	"Column Break",
	"Tab Break",
	"HTML",
	"HTML Editor",
	"Button",
	"Fold",
	"Heading",
	"Image",
}

ATTACH_TYPES = {"Attach", "Attach Image"}
TABLE_TYPES = {"Table", "Table MultiSelect"}
LINK_TYPES = {"Link"}

# Frappe-owned columns. Sending these either does nothing or actively corrupts the target.
ALWAYS_EXCLUDE = {
	"name",
	"owner",
	"creation",
	"modified",
	"modified_by",
	"docstatus",
	"idx",
	"doctype",
	"parent",
	"parentfield",
	"parenttype",
	"amended_from",
	"naming_series",
	"_user_tags",
	"_comments",
	"_assign",
	"_liked_by",
	"_seen",
}

# Per-doctype exclusions, each for a stated reason.
DOCTYPE_EXCLUDE = {
	# The target rebuilds the explosion from `items` on save; sending ours fights it.
	"BOM": {"exploded_items"},
}

CHILD_EXCLUDE = ALWAYS_EXCLUDE - {"idx"}

_TARGET_FIELD_TTL = 600
# A failed lookup is cached briefly so a dead target is not re-asked once per record, but
# not so long that a target coming back up stays invisible for ten minutes.
_TARGET_FIELD_FAIL_TTL = 60


def _numeric_attributes():
	"""Item Attributes whose value must be sent as a number, cached per request."""
	if getattr(frappe.local, "kggk_numeric_attributes", None) is None:
		frappe.local.kggk_numeric_attributes = set(
			frappe.get_all("Item Attribute", filters={"numeric_values": 1}, pluck="name")
		)
	return frappe.local.kggk_numeric_attributes


def _child_rows(doc, df):
	rows = []
	for row in doc.get(df.fieldname) or []:
		data = {}
		meta = frappe.get_meta(df.options)
		for child_df in meta.fields:
			if child_df.fieldtype in LAYOUT_TYPES or child_df.fieldtype in TABLE_TYPES:
				continue
			if child_df.fieldname in CHILD_EXCLUDE:
				continue
			value = row.get(child_df.fieldname)
			if value is None:
				continue
			data[child_df.fieldname] = value
		if row.get("idx") is not None:
			data["idx"] = row.get("idx")
		# Preserve the historical coercion: a numeric Item Attribute must not arrive as text.
		if df.options == "Item Variant Attribute" and data.get("attribute") in _numeric_attributes():
			data["attribute_value"] = flt(data.get("attribute_value"))
		rows.append(data)
	return rows


def build_payload(doc, allowed_fields=None, run=None):
	"""Return ``(payload, attachments)`` for one document.

	``attachments`` maps fieldname -> source file url; those are uploaded separately,
	because an Attach field holds a path and the target has no such file.

	Fields the target does not have are dropped and reported on ``run`` here rather than
	handed back for a caller to remember - that report is the point of this run.
	"""
	meta = frappe.get_meta(doc.doctype)
	excluded = ALWAYS_EXCLUDE | DOCTYPE_EXCLUDE.get(doc.doctype, set())

	payload = {}
	attachments = {}
	dropped = []

	for df in meta.fields:
		name = df.fieldname
		if not name or df.fieldtype in LAYOUT_TYPES or name in excluded:
			continue

		if allowed_fields is not None and name not in allowed_fields:
			value = doc.get(name)
			# Only worth reporting when we actually had something to send.
			if value not in (None, "", 0, []):
				dropped.append(name)
			continue

		if df.fieldtype in ATTACH_TYPES:
			value = doc.get(name)
			if value:
				attachments[name] = value
			continue

		if df.fieldtype in TABLE_TYPES:
			rows = _child_rows(doc, df)
			if rows:
				payload[name] = rows
			continue

		value = doc.get(name)
		if value is None:
			continue
		if df.fieldtype in ("Check",):
			value = cint(value)
		payload[name] = value

	# Date, Datetime, Time and Decimal values come off the doc as Python objects that the
	# JSON encoder in `requests` cannot serialise. frappe's encoder can, so round-trip the
	# whole payload through it once rather than special-casing field types here.
	payload = frappe.parse_json(frappe.as_json(payload))

	if run and dropped:
		names = sorted(dropped)
		run.mismatch(
			doc.doctype,
			doc.name,
			f"{len(names)} field(s) do not exist on the target, dropped: "
			+ ", ".join(names[:25])
			+ (f" (+{len(names) - 25} more)" if len(names) > 25 else ""),
			kind="FIELD-MISSING",
		)

	return payload, attachments


# Links without which the record is meaningless on the target, beyond those the schema
# already marks mandatory. A BOM whose `item` was dropped is not a lesser BOM, it is a
# broken one - better to fail the record loudly than to create rubbish on the target.
ESSENTIAL_LINKS = {"BOM": {"item"}, "Item": {"item_group", "stock_uom", "variant_of"}}


def link_fields(doctype):
	"""``fieldname -> (target doctype, is_essential)`` for every Link field."""
	essential = ESSENTIAL_LINKS.get(doctype, set())
	out = {}
	for df in frappe.get_meta(doctype).fields:
		if df.fieldtype in LINK_TYPES and df.options:
			out[df.fieldname] = (df.options, bool(df.reqd) or df.fieldname in essential)
	return out


def _schema_unknown(run, doctype, message):
	"""Say that we could not learn the target's schema, once per doctype per chunk.

	Reported, not raised. Sending everything and letting the target reject what it does not
	want still beats refusing to sync - but it must not be silent, because the whole point
	of this run is to find out what the target is missing, and "we never managed to ask" is
	a different answer from "nothing is missing".
	"""
	if run:
		run.mismatch(
			doctype,
			None,
			f"{message}; every field will be sent and the target left to decide, so this run "
			"cannot say which fields are missing",
			kind="SCHEMA-UNKNOWN",
			once_key=f"schema::{doctype}",
		)
	else:
		frappe.logger("kggk_sync").warning(f"kggk target schema for {doctype}: {message}")


def get_target_fields(config, doctype, run=None):
	"""Fieldnames the target site has for ``doctype``.

	``None`` means the lookup failed - the caller then sends everything and lets the target
	decide, which is strictly better than refusing to sync. Every route to ``None`` is
	reported, because a silent one is indistinguishable from a clean run.
	"""
	from . import client

	cache_key = f"kggk_target_fields::{doctype}"
	cached = frappe.cache().get_value(cache_key)
	if cached:
		return set(cached)
	if cached is not None:
		# An empty list is the negative sentinel: a recent lookup failed. Still a failure,
		# so still reported - a cached silence is silence.
		_schema_unknown(run, doctype, "the target's field list could not be read recently")
		return None

	fields = set(ALWAYS_EXCLUDE)

	response = client.get(config, f"/api/resource/DocType/{client.segment(doctype)}")
	if not response.ok:
		frappe.cache().set_value(cache_key, [], expires_in_sec=_TARGET_FIELD_FAIL_TTL)
		_schema_unknown(run, doctype, f"could not read the target's DocType - {response.message()}")
		return None

	rows = (response.data.get("data") or {}).get("fields") or []
	if not rows:
		# A DocType with no fields is not a real answer. Treating it as one would drop every
		# field on every record and report the target as having nothing at all.
		frappe.cache().set_value(cache_key, [], expires_in_sec=_TARGET_FIELD_FAIL_TTL)
		_schema_unknown(run, doctype, "the target returned a DocType definition with no fields")
		return None

	for row in rows:
		if row.get("fieldname"):
			fields.add(row["fieldname"])

	custom = client.get(
		config,
		"/api/resource/Custom Field",
		params={
			"filters": frappe.as_json([["dt", "=", doctype]]),
			"fields": frappe.as_json(["fieldname"]),
			"limit_page_length": 0,
		},
	)
	if not custom.ok:
		# The dangerous branch. Standard fields are known and custom ones are not, so the set
		# looks complete and is not: every custom field on the record would be dropped as
		# "missing on target" and cached that way. A confident wrong answer is worse than no
		# answer, so this counts as a failure rather than a partial success.
		frappe.cache().set_value(cache_key, [], expires_in_sec=_TARGET_FIELD_FAIL_TTL)
		_schema_unknown(
			run, doctype, f"could not read the target's Custom Fields - {custom.message()}"
		)
		return None

	for row in custom.data.get("data") or []:
		if row.get("fieldname"):
			fields.add(row["fieldname"])

	frappe.cache().set_value(cache_key, sorted(fields), expires_in_sec=_TARGET_FIELD_TTL)
	return fields
