"""The receiving end of the Gurukrupa -> KGGK sync. Runs on KGGK.

The sending site (`kggk_sync.py`) used to look a record up by where it came from and then POST
or PUT it with the plain REST API. Those are two requests, so nothing stopped two of them from
racing: a Manufacturing Plan job and a BOM save could both ask "is BOM-X here?", both hear no,
and both create it - two BOMs for one design. A POST whose answer was lost to a 502 had the
same effect when it was sent again.

`upsert` makes it one step on this site. It takes a database lock on the record's source
identity, looks the record up by that identity, creates or updates it, and commits before
letting the lock go - so a second push of the same record waits, then finds the first one's
work and updates it. Sending the same push twice is therefore harmless, which is what lets
the sender retry a 502.

Self-contained on purpose: KGGK's copy of this app does not carry `kggk_sync.py`, only this.
"""

import hashlib

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime

RECEIVER_VERSION = 1

# What the sync sends. Anything else is refused.
PUSHED_DOCTYPES = ("Item", "BOM")

# Where a record came from: stamped on it by the sender, created here by its prefill.
SOURCE_SITE = "custom_kggk_source_site"
SOURCE_DOCTYPE = "custom_kggk_source_doctype"
SOURCE_NAME = "custom_kggk_source_name"
# The sender's `modified` for the version this record holds, when this site has the field.
SOURCE_VERSION = "custom_kggk_source_version"

# How long a push waits for another push of the same record before giving up.
LOCK_TIMEOUT = 30

# Columns that are this site's own and never taken from the sender.
FRAMEWORK_FIELDS = {
	"name", "owner", "creation", "modified", "modified_by", "docstatus", "idx", "doctype",
	"parent", "parentfield", "parenttype", "amended_from",
}


class ReceiverBusy(frappe.ValidationError):
	"""Another push of this record held the lock for too long. The sender retries a 503."""

	http_status_code = 503


class SourceConflict(frappe.ValidationError):
	"""A record here already claims a different origin under the name this one needs."""

	http_status_code = 409


@frappe.whitelist(methods=["GET"])
def capabilities():
	"""Lets the sender find out that this site can take an atomic upsert."""
	return {"version": RECEIVER_VERSION, "doctypes": list(PUSHED_DOCTYPES)}


@frappe.whitelist(methods=["POST"])
def upsert(doctype, source_site, source_name, data, source_version=None, policy=None):
	"""Create or update the record that came from ``source_name`` on ``source_site``.

	``data`` is the full create payload. ``policy`` says what an update must do differently:

	* ``omit``        fields an update must leave alone (immutable, or this site's to own)
	* ``merge_child`` ``{table: key}`` - add the rows ``data`` has for keys this record lacks,
	  never replace the table (Item Defaults: KGGK's own rows stay)
	* ``clear``       ``{field: empty}`` - values emptied on the sender, emptied here too

	Returns ``{"name", "action", "blocked", "applied_version"}``. ``action`` is ``created``,
	``updated``, ``unchanged`` or ``stale`` - the last when this site already holds a newer
	version of the record than the one sent, which is then left exactly as it is.
	"""
	if doctype not in PUSHED_DOCTYPES:
		frappe.throw(_("{0} records are not received by the KGGK sync.").format(doctype))
	frappe.has_permission(doctype, "create", throw=True)
	frappe.has_permission(doctype, "write", throw=True)

	data = _as_dict(data)
	policy = _as_dict(policy)
	if not source_site or not source_name:
		frappe.throw(_("A pushed record must say where it came from."))
	_require_identity_fields(doctype)

	key = _lock_key(doctype, source_site, source_name)
	_lock(key)
	frappe.flags.in_kggk_sync = True
	try:
		existing = _find(doctype, source_site, source_name)
		if existing:
			result = _update(doctype, existing, data, source_version, policy)
		else:
			result = _create(doctype, data, source_site, source_name, source_version, policy)
		# Before the lock goes: the next push of this record must see what this one did.
		frappe.db.commit()
		return result
	finally:
		frappe.flags.in_kggk_sync = False
		_unlock(key)


# ---------------------------------------------------------------------------------
# LOCKING
# ---------------------------------------------------------------------------------


def _lock_key(doctype, source_site, source_name):
	# MariaDB lock names are capped at 64 characters; item codes are not.
	digest = hashlib.sha1(f"{doctype}|{source_site}|{source_name}".encode()).hexdigest()
	return f"kggk:{digest}"


def _lock(key):
	if frappe.db.db_type == "postgres":
		# Held until this transaction ends - which `upsert` makes the commit, so the same rule.
		frappe.db.sql("select pg_advisory_xact_lock(hashtext(%s))", (key,))
		return
	got = frappe.db.sql("select get_lock(%s, %s)", (key, LOCK_TIMEOUT))
	if not got or cint(got[0][0]) != 1:
		raise ReceiverBusy(_("Another push of this record is still being applied. Try again."))


def _unlock(key):
	if frappe.db.db_type == "postgres":
		return
	try:
		frappe.db.sql("select release_lock(%s)", (key,))
	except Exception:
		# The lock dies with the connection anyway; never let tidying up mask the result.
		pass


# ---------------------------------------------------------------------------------
# FIND, CREATE, UPDATE
# ---------------------------------------------------------------------------------


def _require_identity_fields(doctype):
	missing = [f for f in (SOURCE_SITE, SOURCE_DOCTYPE, SOURCE_NAME) if not frappe.get_meta(doctype).has_field(f)]
	if missing:
		frappe.throw(
			_("{0} has no {1} here yet. Run Check / Prefill Target Site on the sending site.").format(
				doctype, ", ".join(missing)
			)
		)


def _find(doctype, source_site, source_name):
	"""This site's record from that origin. The oldest, if a past race left more than one."""
	found = frappe.get_all(
		doctype,
		filters={
			SOURCE_SITE: source_site,
			SOURCE_DOCTYPE: doctype,
			SOURCE_NAME: source_name,
			"docstatus": ("<", 2),
		},
		pluck="name",
		order_by="creation asc",
		limit=1,
	)
	return found[0] if found else None


def _create(doctype, data, source_site, source_name, source_version, policy):
	payload = {k: v for k, v in data.items() if k not in FRAMEWORK_FIELDS}
	payload.update({SOURCE_SITE: source_site, SOURCE_DOCTYPE: doctype, SOURCE_NAME: source_name})
	if source_version and frappe.get_meta(doctype).has_field(SOURCE_VERSION):
		payload[SOURCE_VERSION] = source_version

	# An Item is named by its code, so an Item pushed before identities existed is already here
	# under that name with no origin. Claim it if it is unclaimed; refuse if it is somebody else's.
	if doctype == "Item" and payload.get("item_code") and frappe.db.exists("Item", payload["item_code"]):
		claimed = frappe.db.get_value(
			"Item", payload["item_code"], [SOURCE_SITE, SOURCE_DOCTYPE, SOURCE_NAME], as_dict=True
		)
		ours = {SOURCE_SITE: source_site, SOURCE_DOCTYPE: doctype, SOURCE_NAME: source_name}
		if any(claimed.values()) and dict(claimed) != ours:
			raise SourceConflict(
				_("Item {0} here came from {1} ({2}), not from this push.").format(
					payload["item_code"], claimed.get(SOURCE_SITE) or "?", claimed.get(SOURCE_NAME) or "?"
				)
			)
		frappe.db.set_value("Item", payload["item_code"], ours, update_modified=False)
		result = _update(doctype, payload["item_code"], data, source_version, policy)
		result["action"] = f"adopted, {result['action']}"
		return result

	doc = frappe.get_doc({"doctype": doctype, **payload})
	doc.insert()
	return {"name": doc.name, "action": "created", "blocked": [], "applied_version": source_version}


def _update(doctype, name, data, source_version, policy):
	doc = frappe.get_doc(doctype, name)

	held = doc.get(SOURCE_VERSION) if doc.meta.has_field(SOURCE_VERSION) else None
	if held and source_version and get_datetime(held) > get_datetime(source_version):
		# An older push arriving late - a retry, a slow worker - after a newer one. Applying it
		# would put the record back in time.
		return {"name": doc.name, "action": "stale", "blocked": [], "applied_version": str(held)}

	omit = set(policy.get("omit") or []) | FRAMEWORK_FIELDS
	changes = {k: v for k, v in data.items() if k not in omit}
	for field, empty in (policy.get("clear") or {}).items():
		if field not in changes and field not in omit:
			changes[field] = empty

	merged = []
	for table, key in (policy.get("merge_child") or {}).items():
		have = {row.get(key) for row in doc.get(table) or []}
		for row in data.get(table) or []:
			if row.get(key) and row.get(key) not in have:
				merged.append((table, {k: v for k, v in row.items() if k not in FRAMEWORK_FIELDS}))
				have.add(row.get(key))

	if source_version and doc.meta.has_field(SOURCE_VERSION):
		changes[SOURCE_VERSION] = source_version

	if doc.docstatus == 1:
		return _update_submitted(doc, changes, merged, source_version)

	doc.update(changes)
	for table, row in merged:
		doc.append(table, row)
	doc.save()
	return {"name": doc.name, "action": "updated", "blocked": [], "applied_version": source_version}


def _update_submitted(doc, changes, merged, source_version):
	"""Apply what a submitted record still allows; name, never force, the rest.

	Read from this site's own metadata - its Custom Fields and Property Setters included - which
	is the one thing the sender could only ever guess at.
	"""
	allowed = {df.fieldname for df in doc.meta.fields if cint(df.allow_on_submit)}
	changed = {k: v for k, v in changes.items() if _differs(doc.get(k), v)}
	if merged:
		changed.update({table: None for table, _row in merged})
	apply = {k: v for k, v in changed.items() if k in allowed}
	blocked = sorted(set(changed) - set(apply))
	if not apply:
		action = "unchanged" if not blocked else "blocked"
		return {"name": doc.name, "action": action, "blocked": blocked, "applied_version": None}

	doc.update({k: v for k, v in apply.items() if k not in {t for t, _r in merged}})
	for table, row in merged:
		if table in apply:
			doc.append(table, row)
	doc.save()
	return {
		"name": doc.name,
		"action": "updated (submitted)",
		"blocked": blocked,
		"applied_version": source_version if not blocked else None,
	}


def _differs(current, wanted):
	"""Would ``wanted`` change a value that is ``current`` now? Child rows by content."""
	if isinstance(wanted, list) or isinstance(current, list):
		mine = wanted or []
		theirs = [row.as_dict() if hasattr(row, "as_dict") else row for row in (current or [])]
		if len(mine) != len(theirs):
			return True
		for ours, existing in zip(mine, theirs):
			for key, value in (ours or {}).items():
				if key in FRAMEWORK_FIELDS:
					continue
				if _differs((existing or {}).get(key), value):
					return True
		return False
	if current in (None, "") and wanted in (None, ""):
		return False
	if isinstance(wanted, (int, float)) or isinstance(current, (int, float)):
		try:
			return flt(current) != flt(wanted)
		except Exception:
			pass
	return str(current) != str(wanted)


def _as_dict(value):
	if not value:
		return {}
	if isinstance(value, str):
		value = frappe.parse_json(value)
	return dict(value)
