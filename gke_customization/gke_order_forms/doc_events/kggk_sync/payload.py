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
	# Sync markers are local bookkeeping about the push itself.
	"Item": {"custom_is_sync", "custom_last_synced_on", "custom_sync_error"},
}
DOCTYPE_EXCLUDE["BOM"] |= {"custom_is_sync", "custom_last_synced_on", "custom_sync_error"}

CHILD_EXCLUDE = ALWAYS_EXCLUDE - {"idx"}

_TARGET_FIELD_TTL = 600


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
	"""Return ``(payload, attachments, dropped)`` for one document.

	``attachments`` maps fieldname -> source file url; those are uploaded separately,
	because an Attach field holds a path and the target has no such file. ``dropped``
	lists fields the target does not have, which the caller records in the log.
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
		run.mismatch(
			doc.doctype,
			doc.name,
			f"{len(dropped)} field(s) not present on target, dropped: {', '.join(sorted(dropped)[:25])}"
			+ (" ..." if len(dropped) > 25 else ""),
		)

	return payload, attachments, dropped


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


def get_target_fields(config, doctype):
	"""Fieldnames the target site has for ``doctype``.

	``None`` means the lookup failed - the caller then sends everything and lets the target
	decide, which is the old behaviour and strictly better than refusing to sync.
	"""
	from . import client

	cache_key = f"kggk_target_fields::{doctype}"
	cached = frappe.cache().get_value(cache_key)
	if cached is not None:
		return set(cached) if cached else None

	fields = set(ALWAYS_EXCLUDE)

	response = client.get(config, f"/api/resource/DocType/{client.segment(doctype)}")
	if not response.ok:
		frappe.cache().set_value(cache_key, [], expires_in_sec=60)
		return None
	for row in (response.data.get("data") or {}).get("fields") or []:
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
	if custom.ok:
		for row in custom.data.get("data") or []:
			if row.get("fieldname"):
				fields.add(row["fieldname"])

	frappe.cache().set_value(cache_key, list(fields), expires_in_sec=_TARGET_FIELD_TTL)
	return fields
