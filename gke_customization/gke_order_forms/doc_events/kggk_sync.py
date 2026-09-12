"""Manufacturing Plan -> KGGK testing site: one module, one flow.

On Manufacturing Plan submit, the plan's subcontracting rows' items and their
`manufacturing_bom` BOMs are pushed to a separate testing site, behind an explicit switch
on Data Migration in KGGK that is off by default.

This is deliberately NOT the live Item/BOM sync. That one lives in `doc_events/item.py`,
fires on `before_validate`, and pushes to `to_site` with `api_key`/`api_secret`. This one
fires on submit, pushes to `testing_site` with its own credentials, and adds no fields to
Item or BOM. Two flows, two targets, one settings screen.

Everything lives in this single file on purpose so the whole feature can be read, reviewed
and reverted in one place.
"""

import os
import time
from urllib.parse import quote

import frappe
import requests
from frappe import _
from frappe.utils import cint, flt, now_datetime


# ============================================================================
# SETTINGS, GUARDS AND URL HANDLING
# ============================================================================

SETTINGS = "Data Migration in KGGK"

# Reasons a push is refused. Surfaced verbatim wherever the skip is reported.
SKIP_DISABLED = (
	"'Send Manufacturing Plan Data to Testing Site' is off in Data Migration in KGGK"
)
SKIP_NO_TARGET = "Testing Site is not set in Data Migration in KGGK"
SKIP_NO_CREDS = "Testing API Key / Testing API Secret are not set in Data Migration in KGGK"
SKIP_SAME_SITE = "Testing Site is this site ({0}) - refusing to sync a site to itself"
SKIP_LIVE_TARGET = (
	"Testing Site ({0}) is the live To Site - refusing to push a Manufacturing Plan into the "
	"production KGGK site"
)


def strip_scheme(url):
	"""Host+path of a site URL, lowercased, with scheme and trailing slash removed."""
	if not url:
		return ""
	value = str(url).strip().lower()
	for prefix in ("https://", "http://"):
		if value.startswith(prefix):
			value = value[len(prefix) :]
			break
	return value.rstrip("/")


def host_of(url):
	"""Bare hostname of a site URL - no scheme, no port, no path.

	Comparison happens on the host alone so that ``https://kggk.frappe.cloud/`` and
	``kggk.frappe.cloud:443`` are recognised as the same site.
	"""
	value = strip_scheme(url)
	value = value.split("/")[0]
	return value.split(":")[0]


def base_url(url):
	"""Request-ready base URL: scheme preserved (https assumed), no trailing slash."""
	if not url:
		return ""
	value = str(url).strip().rstrip("/")
	if not value.startswith(("http://", "https://")):
		value = "https://" + value
	return value


def current_site_hosts():
	"""Every host string that legitimately identifies the site this code is running on.

	``get_url()`` follows ``host_name`` in site config, which is not always set on a
	bench; ``frappe.local.site`` is the directory name and is always present. Either
	matching the configured From Site is good enough to treat this as the source site.
	"""
	hosts = set()
	try:
		hosts.add(host_of(frappe.utils.get_url()))
	except Exception:
		pass
	site = getattr(frappe.local, "site", None)
	if site:
		hosts.add(host_of(site))
	return {h for h in hosts if h}


def _testing_api_secret():
	"""Read the secret from ``__Auth``, not from ``tabSingles``.

	A Password field on a Single stores ``*****`` in the Singles table and the real value in
	``__Auth``. ``frappe.db.get_value`` returns the placeholder, which authenticates as
	nothing - and the resulting 401 looks exactly like a mistyped key, so it would be
	debugged in the wrong place.
	"""
	from frappe.utils.password import get_decrypted_password

	try:
		return get_decrypted_password(SETTINGS, SETTINGS, "testing_api_secret", raise_exception=False)
	except Exception:
		return None


def is_sync_enabled():
	"""The master switch. An absent or unticked field is OFF, deliberately."""
	return bool(cint(frappe.db.get_single_value(SETTINGS, "enable_testing_sync")))


def get_sync_config():
	"""Resolve the push configuration, or return ``None`` with the reason it was refused.

	Returns ``(config, reason)``. ``config`` carries ``to_site`` - the *testing* site, named
	``to_site`` because every request helper reads that key - plus ready-to-use ``headers``.
	``reason`` is ``None`` on success and a human-readable sentence otherwise. Callers report
	the reason; they never guess at it.
	"""
	settings = frappe.db.get_value(
		SETTINGS,
		SETTINGS,
		["from_site", "to_site", "enable_testing_sync", "testing_site", "testing_api_key"],
		as_dict=True,
	) or frappe._dict()

	if not cint(settings.get("enable_testing_sync")):
		return None, SKIP_DISABLED

	target = settings.get("testing_site")
	if not target:
		return None, SKIP_NO_TARGET

	api_key = settings.get("testing_api_key")
	api_secret = _testing_api_secret()
	if not api_key or not api_secret:
		return None, SKIP_NO_CREDS

	target_host = host_of(target)

	# --- the same-site guards ------------------------------------------------------
	# Never legitimate, never bypassable. A Single doctype travels with a database restore,
	# so a clone of this site arrives already configured to push; without this it pushes
	# straight back into itself, and the inbound write re-fires the hooks on the way in.
	if target_host in current_site_hosts():
		return None, SKIP_SAME_SITE.format(target_host)

	from_site = settings.get("from_site")
	if from_site and host_of(from_site) == target_host:
		return None, SKIP_SAME_SITE.format(target_host)

	# --- the wrong-target guard ----------------------------------------------------
	# `to_site` is the live KGGK site the Item/BOM before_validate hooks push to. If the
	# Testing Site field has been pointed at it, one plan submit would put several hundred
	# items and BOMs into production. Pasting the wrong URL is a realistic mistake and this
	# is a cheap way to survive it.
	live = settings.get("to_site")
	if live and host_of(live) == target_host:
		return None, SKIP_LIVE_TARGET.format(target_host)

	return (
		frappe._dict(
			from_site=base_url(from_site),
			to_site=base_url(target),
			headers={
				"Authorization": f"token {api_key}:{api_secret}",
				"Accept": "application/json",
			},
		),
		None,
	)


def in_reentrant_context():
	"""True when a push must not run because we are inside one, or inside a bulk operation.

	The inbound leg of a sync is an ordinary document save on the receiving site. Without
	this, a site that is both a source and a target ping-pongs writes between the two.
	"""
	flags = frappe.flags
	if getattr(flags, "in_kggk_sync", False):
		return True
	# Deliberately not `in_test`: the config guard already refuses on a site with no
	# To Site or credentials, so tests are safe without it, and including it would make
	# the push itself impossible to exercise under `bench run-tests`.
	for flag in ("in_migrate", "in_install", "in_patch", "in_import", "in_setup_wizard"):
		if getattr(flags, flag, False):
			return True
	return False

# ============================================================================
# HTTP ACCESS TO THE TARGET SITE
# ============================================================================

DEFAULT_TIMEOUT = 30
UPLOAD_TIMEOUT = 120
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 2


class Response:
	"""Uniform result. ``ok`` means the target accepted it; ``error`` is display-ready."""

	def __init__(self, status_code=None, data=None, text="", url="", error=None):
		self.status_code = status_code
		self.data = data or {}
		self.text = text or ""
		self.url = url
		self.error = error

	@property
	def ok(self):
		return self.error is None and self.status_code is not None and self.status_code < 400

	@property
	def not_found(self):
		return self.status_code == 404

	def message(self):
		"""The most useful line the target gave us, for the migration log."""
		if self.error:
			return self.error
		exc = self.data.get("exception") or self.data.get("_server_messages") or ""
		if exc:
			return f"HTTP {self.status_code}: {str(exc)[:600]}"
		return f"HTTP {self.status_code}: {self.text[:600]}"


def segment(value):
	"""Escape one URL path segment. Item codes legitimately contain '/' and spaces."""
	return quote(str(value), safe="")


def _url(config, path):
	return f"{config.to_site}/{path.lstrip('/')}"


def api_request(config, method, path, json=None, params=None, files=None, data=None, timeout=None):
	"""Call the target site, retrying only what is worth retrying.

	A connection error or a 5xx is transient and retried. A 4xx is the target telling us
	the payload is wrong; retrying that just sends the same wrong payload again.
	"""
	url = _url(config, path)
	timeout = timeout or (UPLOAD_TIMEOUT if files else DEFAULT_TIMEOUT)
	headers = dict(config.headers)
	if json is not None:
		headers["Content-Type"] = "application/json"

	last = None
	for attempt in range(1, MAX_ATTEMPTS + 1):
		try:
			raw = requests.request(
				method,
				url,
				headers=headers,
				json=json,
				params=params,
				files=files,
				data=data,
				timeout=timeout,
			)
		except requests.exceptions.RequestException as exc:
			last = Response(url=url, error=f"connection failed: {exc}")
			if attempt < MAX_ATTEMPTS:
				time.sleep(BACKOFF_SECONDS * attempt)
				continue
			return last

		payload = {}
		try:
			payload = raw.json() or {}
		except ValueError:
			payload = {}

		response = Response(
			status_code=raw.status_code, data=payload, text=raw.text, url=url
		)

		if raw.status_code >= 500 and attempt < MAX_ATTEMPTS:
			last = response
			time.sleep(BACKOFF_SECONDS * attempt)
			continue

		return response

	return last or Response(url=url, error="no attempt was made")


def api_get(config, path, **kwargs):
	return api_request(config, "GET", path, **kwargs)


def api_put(config, path, **kwargs):
	return api_request(config, "PUT", path, **kwargs)


def api_post(config, path, **kwargs):
	return api_request(config, "POST", path, **kwargs)


def api_exists(config, doctype, name):
	"""Does this record exist on the target? ``None`` when the check itself failed."""
	if not name:
		return False
	response = api_get(
		config,
		f"/api/resource/{segment(doctype)}/{segment(name)}",
		params={"fields": '["name"]'},
	)
	if response.ok:
		return True
	if response.not_found:
		return False
	return None

# ============================================================================
# RUN STATE AND THE REPORT WRITTEN ON THE TARGET
# ============================================================================

STATUS_RUNNING = "Running"
STATUS_COMPLETED = "Completed"
STATUS_PARTIAL = "Partially Completed"
STATUS_FAILED = "Failed"

# One POST carries the whole chunk's problems. Bounded so a run that fails wholesale cannot
# push a multi-megabyte document at a site that is already unhappy.
MAX_REPORT_LINES = 200
MAX_LINE_CHARS = 500
MAX_REPORT_CHARS = 60_000

# Diagnostics, not payload - it gets a shorter leash than a data push.
REPORT_TIMEOUT = 20


def _stamp():
	return now_datetime().strftime("%Y-%m-%d %H:%M:%S")


def log_skip(reason, doctype=None, name=None):
	"""Record a refused push.

	Local only, and deliberately so: a skip means there is no reachable target, so there is
	nowhere to write it but here.
	"""
	frappe.logger("kggk_sync").info(
		f"{_stamp()} | SKIP     | {doctype or '-'} | {name or '-'} | {reason}"
	)


class SyncRun:
	"""One chunk of one run: counters, a problem list, and the report they turn into."""

	def __init__(self, trigger="Manual", reference=None, config=None, counters=None, chunk_index=0):
		self.trigger = trigger
		self.reference = reference or ""
		self.config = config
		self.chunk_index = chunk_index

		# Cumulative across chunks. These ride in the enqueue kwargs, not in the database.
		counters = counters or {}
		self.items_synced = int(counters.get("items_synced") or 0)
		self.items_failed = int(counters.get("items_failed") or 0)
		self.boms_synced = int(counters.get("boms_synced") or 0)
		self.boms_failed = int(counters.get("boms_failed") or 0)
		self.mismatches = int(counters.get("mismatches") or 0)

		self.items_total = 0
		self.boms_total = 0

		# Problems from *this* chunk only. Carrying them forward would grow the queued job
		# payload with every continuation.
		self.problems = []
		self.last_error = ""
		self._once = set()

		# "Does this master exist on the target" answers, reused across the chunk so fifty
		# items do not ask about the same Item Group fifty times.
		self.link_cache = {}

	# -- counters carried to the next chunk ------------------------------------------

	def counters(self):
		return {
			"items_synced": self.items_synced,
			"items_failed": self.items_failed,
			"boms_synced": self.boms_synced,
			"boms_failed": self.boms_failed,
			"mismatches": self.mismatches,
		}

	# -- logging ---------------------------------------------------------------------

	def line(self, level, doctype, name, message):
		frappe.logger("kggk_sync").info(
			f"{_stamp()} | {level:<14} | {doctype or '-'} | {name or '-'} | {message}"
		)

	def problem(self, kind, doctype, name, message, once_key=None):
		"""One line for the target's Error Log.

		``once_key`` collapses a problem that would otherwise repeat per record - a target
		schema we could not read is one fact, not five hundred.
		"""
		if once_key is not None:
			if once_key in self._once:
				return
			self._once.add(once_key)
		self.problems.append(
			f"{kind:<14} | {doctype or '-'} | {name or '-'} | {message}"[:MAX_LINE_CHARS]
		)
		self.line(kind, doctype, name, message)

	def mismatch(self, doctype, name, message, kind="FIELD-MISSING", once_key=None):
		"""Something could not be written to the target. This is the report's whole point."""
		self.mismatches += 1
		self.problem(kind, doctype, name, message, once_key=once_key)

	# -- outcomes --------------------------------------------------------------------

	def item_ok(self, name, note=""):
		self.items_synced += 1
		self.line("OK", "Item", name, note or "synced")

	def item_failed(self, name, message):
		self.items_failed += 1
		self.last_error = f"Item {name}: {message}"[:1000]
		self.problem("FAILED", "Item", name, message)

	def bom_ok(self, name, note=""):
		self.boms_synced += 1
		self.line("OK", "BOM", name, note or "synced")

	def bom_failed(self, name, message):
		self.boms_failed += 1
		self.last_error = f"BOM {name}: {message}"[:1000]
		self.problem("FAILED", "BOM", name, message)

	# -- the report ------------------------------------------------------------------

	def summary(self, status):
		return (
			f"{status} | items {self.items_synced}/{self.items_total} synced, "
			f"{self.items_failed} failed | BOMs {self.boms_synced}/{self.boms_total} synced, "
			f"{self.boms_failed} failed | {self.mismatches} field/link problem(s)"
		)

	def finish(self, status=None):
		if status is None:
			if self.items_failed or self.boms_failed:
				status = STATUS_PARTIAL if (self.items_synced or self.boms_synced) else STATUS_FAILED
			else:
				status = STATUS_COMPLETED
		self.line("INFO", None, None, f"=== sync finished: {self.summary(status)} ===")
		self.report(status)
		return status

	def report(self, status=STATUS_RUNNING):
		"""Write this chunk's problems as one Error Log on the target site.

		One document per chunk, not one per record. A real plan carries several hundred
		items; per-record reporting would mean as many POSTs, each with its own retries and
		timeout, at the exact moment the target is least able to answer - the reporter would
		time the job out before the sync did. It would also bury the answer in hundreds of
		rows instead of stating it once.

		Nothing here may raise. This runs at the tail of a background job whose entire
		purpose is not to disturb the Manufacturing Plan that started it.
		"""
		if not self.problems:
			return False

		title = f"KGGK sync: {self.trigger} {self.reference}".strip()
		if self.chunk_index:
			title = f"{title} (chunk {self.chunk_index + 1})"

		body_lines = [
			self.summary(status),
			f"source: {(self.config or {}).get('from_site') or frappe.local.site}",
			f"at: {_stamp()}",
			"",
			*self.problems[:MAX_REPORT_LINES],
		]
		if len(self.problems) > MAX_REPORT_LINES:
			body_lines.append(f"... and {len(self.problems) - MAX_REPORT_LINES} more")
		body = "\n".join(body_lines)[:MAX_REPORT_CHARS]

		try:

			if not self.config:
				raise ValueError("no target configuration")

			# reference_doctype is deliberately left unset: it is a Link to DocType, and if
			# the target has no "Manufacturing Plan" the POST fails validation and the whole
			# report is lost over a decoration.
			response = api_post(
				self.config,
				"/api/resource/Error Log",
				json={"method": title[:140], "error": body},
				timeout=REPORT_TIMEOUT,
			)
			if response.ok:
				return True
			reason = response.message()
		except Exception as exc:
			reason = f"{type(exc).__name__}: {exc}"

		# Last resort only. The target is this report's home; writing locally is here so a
		# report is never silently lost, and it says on its face that it is a fallback.
		try:
			frappe.logger("kggk_sync").error(f"could not write Error Log to target: {reason}")
			frappe.log_error(
				f"FALLBACK - the sync report could not be written to the testing site "
				f"({reason}), so it is here instead.\n\n{body}",
				title[:140],
			)
		except Exception:
			pass
		return False

# ============================================================================
# ATTACHMENTS
# ============================================================================

# A CAD or video attachment can be large. Beyond this we log and move on rather than
# holding a worker open on a 200 MB multipart POST.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


def _cache():
	if getattr(frappe.local, "kggk_file_cache", None) is None:
		frappe.local.kggk_file_cache = {}
	return frappe.local.kggk_file_cache


def _find_file_doc(file_url):
	"""The File record behind a field value, preferring an exact url match."""
	rows = frappe.get_all(
		"File",
		filters={"file_url": file_url},
		fields=["name", "file_name", "is_private"],
		order_by="creation desc",
		limit=1,
	)
	if not rows:
		return None
	return frappe.get_doc("File", rows[0].name)


def upload(config, file_url, target_doctype, target_name, fieldname, run=None):
	"""Upload one attachment and return the target's file url, or ``None``.

	Public files are cached for the run so a catalogue image shared by fifty items is
	uploaded once. Private files are uploaded per document, because the target serves them
	only to users with permission on the document they are attached to.
	"""

	if not file_url:
		return None

	# Already absolute - the target can fetch it directly, nothing to upload.
	if str(file_url).startswith(("http://", "https://")):
		return file_url

	cache = _cache()
	if file_url in cache:
		return cache[file_url]

	file_doc = _find_file_doc(file_url)
	if not file_doc:
		if run:
			run.mismatch(
				target_doctype, target_name, f"{fieldname}: no File record for {file_url}, field skipped"
			)
		return None

	try:
		content = file_doc.get_content()
	except Exception as exc:
		if run:
			run.mismatch(
				target_doctype, target_name, f"{fieldname}: cannot read {file_url} ({exc}), field skipped"
			)
		return None

	if content is None:
		if run:
			run.mismatch(target_doctype, target_name, f"{fieldname}: {file_url} is empty, field skipped")
		return None

	if len(content) > MAX_UPLOAD_BYTES:
		if run:
			run.mismatch(
				target_doctype,
				target_name,
				f"{fieldname}: {file_url} is {len(content) // (1024 * 1024)} MB, over the "
				f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit, field skipped",
			)
		return None

	is_private = cint(file_doc.is_private)
	file_name = file_doc.file_name or os.path.basename(file_url) or "attachment"

	response = api_post(
		config,
		"/api/method/upload_file",
		data={
			"doctype": target_doctype,
			"docname": target_name,
			"fieldname": fieldname,
			"is_private": is_private,
			"file_name": file_name,
		},
		files={"file": (file_name, content)},
	)

	if not response.ok:
		if run:
			run.mismatch(
				target_doctype, target_name, f"{fieldname}: upload of {file_url} failed - {response.message()}"
			)
		return None

	new_url = (response.data.get("message") or {}).get("file_url")
	if not new_url:
		if run:
			run.mismatch(
				target_doctype, target_name, f"{fieldname}: upload of {file_url} returned no file_url"
			)
		return None

	if not is_private:
		cache[file_url] = new_url
	return new_url


def upload_all(config, attachments, target_doctype, target_name, run=None):
	"""Upload every attachment for a document. Returns ``fieldname -> new url``."""
	resolved = {}
	for fieldname, value in (attachments or {}).items():
		new_url = upload(config, value, target_doctype, target_name, fieldname, run=run)
		if new_url:
			resolved[fieldname] = new_url
	return resolved

# ============================================================================
# PAYLOAD BUILT FROM THE DOCTYPE DEFINITION
# ============================================================================

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

	response = api_get(config, f"/api/resource/DocType/{segment(doctype)}")
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

	custom = api_get(
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

# ============================================================================
# THE PUSH PIPELINE
# ============================================================================

# Fields that identify a record and cannot be changed on an existing one.
IMMUTABLE_ON_UPDATE = {"Item": {"variant_of", "item_code"}, "BOM": {"item"}}

def _link_exists(config, doctype, value, cache):
	key = (doctype, value)
	if key not in cache:
		cache[key] = api_exists(config, doctype, value)
	return cache[key]


def _strip_missing_links(config, doc, data, run, cache):
	"""Drop optional Link values the target does not have; refuse on essential ones.

	Dropping an optional link - one Item Category, one Sizer Type - keeps the record
	syncing instead of failing whole on a single absent master. Dropping a mandatory one
	would create a broken record on the target, so that blocks the push instead.

	Returns a list of blocking problems; empty means it is safe to send.
	"""
	blocking = []
	for fieldname, (link_doctype, essential) in link_fields(doc.doctype).items():
		value = data.get(fieldname)
		if not value:
			continue
		found = _link_exists(config, link_doctype, value, cache)
		if found is None:
			# The check itself failed - a timeout, a 500, a 403. Treating that as "it is
			# there" sends the value anyway and the target rejects the whole record with a
			# message that blames something else entirely.
			run.mismatch(
				doc.doctype,
				doc.name,
				f"{fieldname}: could not check whether {link_doctype} '{value}' exists on "
				"target, sending it anyway",
				kind="LINK-UNKNOWN",
				once_key=f"linkcheck::{link_doctype}",
			)
			continue
		if found:
			continue
		if essential:
			blocking.append(f"{fieldname}: {link_doctype} '{value}' does not exist on target")
			continue
		data.pop(fieldname, None)
		run.mismatch(
			doc.doctype,
			doc.name,
			f"{fieldname}: {link_doctype} '{value}' does not exist on target, field dropped",
			kind="LINK-MISSING",
		)
	return blocking


def _send(config, doctype, name, data):
	"""PUT the existing record, POST a new one if the target has never seen it."""
	path = f"/api/resource/{segment(doctype)}/{segment(name)}"
	update_data = {
		k: v for k, v in data.items() if k not in IMMUTABLE_ON_UPDATE.get(doctype, set())
	}
	response = api_put(config, path, json=update_data)
	if response.not_found:
		response = api_post(config, f"/api/resource/{segment(doctype)}", json=data)
		return response, "created"
	return response, "updated"


def push_item(item_code, config, run, seen=None):
	"""Create or update one Item on the target, attachments included."""
	seen = seen if seen is not None else set()
	if item_code in seen:
		return True
	seen.add(item_code)

	if not frappe.db.exists("Item", item_code):
		run.item_failed(item_code, "item does not exist on this site")
		return False

	doc = frappe.get_doc("Item", item_code)

	# A variant cannot be created before its template exists on the target.
	if doc.get("variant_of"):
		template = doc.variant_of
		if api_exists(config, "Item", template) is False:
			run.line("INFO", "Item", item_code, f"template {template} missing on target, pushing it first")
			run.items_total += 1
			push_item(template, config, run, seen=seen)

	allowed = get_target_fields(config, "Item", run=run)
	data, attachments = build_payload(doc, allowed, run=run)
	blocking = _strip_missing_links(config, doc, data, run, run.link_cache)
	if blocking:
		message = "required master(s) missing on target - " + "; ".join(blocking)
		run.item_failed(item_code, message)
		return False

	response, action = _send(config, "Item", item_code, data)
	if not response.ok:
		message = response.message()
		run.item_failed(item_code, message)
		return False

	note = action
	if attachments:
		resolved = upload_all(config, attachments, "Item", item_code, run=run)
		if resolved:
			follow_up = api_put(
				config, f"/api/resource/Item/{segment(item_code)}", json=resolved
			)
			if follow_up.ok:
				note = f"{action}, {len(resolved)} attachment(s)"
			else:
				run.mismatch(
					"Item", item_code, f"attachment urls could not be set - {follow_up.message()}"
				)
				note = f"{action}, attachments uploaded but not linked"

	run.item_ok(item_code, note)
	return True


def push_bom(bom_name, config, run):
	"""Create or update one BOM on the target, attachments included."""
	if not frappe.db.exists("BOM", bom_name):
		run.bom_failed(bom_name, "BOM does not exist on this site")
		return False

	doc = frappe.get_doc("BOM", bom_name)

	# A BOM cannot validate on the target without its finished-goods item. Batches are
	# assembled from Items and BOMs independently - "Sync Now" takes the oldest unsynced of
	# each - so the item a given BOM needs is very often not in the same batch. Pull it in
	# rather than failing the BOM for a reason the operator cannot act on.
	if doc.get("item") and api_exists(config, "Item", doc.item) is False:
		run.line("INFO", "BOM", bom_name, f"item {doc.item} missing on target, pushing it first")
		run.items_total += 1
		push_item(doc.item, config, run)

	allowed = get_target_fields(config, "BOM", run=run)
	data, attachments = build_payload(doc, allowed, run=run)
	blocking = _strip_missing_links(config, doc, data, run, run.link_cache)
	if blocking:
		message = "required master(s) missing on target - " + "; ".join(blocking)
		run.bom_failed(bom_name, message)
		return False

	response, action = _send(config, "BOM", bom_name, data)
	if not response.ok:
		message = response.message()
		run.bom_failed(bom_name, message)
		return False

	note = action
	if attachments:
		resolved = upload_all(config, attachments, "BOM", bom_name, run=run)
		if resolved:
			follow_up = api_put(config, f"/api/resource/BOM/{segment(bom_name)}", json=resolved)
			if follow_up.ok:
				note = f"{action}, {len(resolved)} attachment(s)"
			else:
				run.mismatch("BOM", bom_name, f"attachment urls could not be set - {follow_up.message()}")

	run.bom_ok(bom_name, note)
	return True


# One Manufacturing Plan can carry hundreds of distinct items - a real plan on this site
# selects 490 items and 490 BOMs. Pushing 980 records in a single job would run for the
# better part of an hour, exceed the job timeout, and lose the whole run's progress. Work
# is processed a chunk at a time and the remainder re-queued, so a run makes durable
# progress and a timeout costs one chunk instead of everything.
CHUNK_SIZE = 50
JOB_TIMEOUT = 3600


def sync_records(
	items=None,
	boms=None,
	trigger="Manual",
	reference=None,
	totals=None,
	counters=None,
	chunk_index=0,
	run_id=None,
):
	"""Push a batch of Items and BOMs. The one entry point every trigger calls.

	Items go first, across chunks as well as within one: a BOM whose finished-goods item
	does not exist on the target cannot validate there. Each record is wrapped in a
	savepoint so one bad row cannot take the rest of the chunk down with it.
	"""
	items = list(dict.fromkeys(items or []))
	boms = list(dict.fromkeys(boms or []))

	if in_reentrant_context():
		log_skip("push suppressed: already inside a sync or a bulk operation")
		return None

	config, reason = get_sync_config()
	if not config:
		log_skip(reason)
		return None

	if not items and not boms:
		return None

	if totals is None:
		totals = {"items": len(items), "boms": len(boms)}

	# Items first, then BOMs, filling one chunk.
	batch_items = items[:CHUNK_SIZE]
	rest_items = items[len(batch_items) :]
	bom_budget = max(CHUNK_SIZE - len(batch_items), 0)
	batch_boms = boms[:bom_budget]
	rest_boms = boms[len(batch_boms) :]

	run = SyncRun(
		trigger=trigger,
		reference=reference,
		config=config,
		counters=counters,
		chunk_index=chunk_index,
	)
	run.items_total = int(totals.get("items") or 0)
	run.boms_total = int(totals.get("boms") or 0)
	if rest_items or rest_boms:
		run.line(
			"INFO",
			None,
			None,
			f"chunk {chunk_index + 1}: {len(batch_items)} item(s), {len(batch_boms)} BOM(s); "
			f"{len(rest_items)} item(s) and {len(rest_boms)} BOM(s) still queued",
		)

	items, boms = batch_items, batch_boms

	frappe.flags.in_kggk_sync = True
	reported = False
	try:
		seen = set()
		for item_code in items:
			frappe.db.savepoint("kggk_item")
			try:
				push_item(item_code, config, run, seen=seen)
			except Exception as exc:
				frappe.db.rollback(save_point="kggk_item")
				run.item_failed(item_code, f"unexpected error: {exc}")
				frappe.log_error(frappe.get_traceback(), f"KGGK sync: Item {item_code}"[:140])

		for bom_name in boms:
			frappe.db.savepoint("kggk_bom")
			try:
				push_bom(bom_name, config, run)
			except Exception as exc:
				frappe.db.rollback(save_point="kggk_bom")
				run.bom_failed(bom_name, f"unexpected error: {exc}")
				frappe.log_error(frappe.get_traceback(), f"KGGK sync: BOM {bom_name}"[:140])

		# Reached only if the loops ran to completion; the reporting below then owns it.
		reported = True
	finally:
		frappe.flags.in_kggk_sync = False
		if not reported:
			# A chunk killed by the job timeout, or one that raised on its way out, still
			# reports what it learned. Silence here would look exactly like a clean run.
			run.report()

	if rest_items or rest_boms:
		frappe.db.commit()
		# Hand the remainder to a fresh job. A distinct job_id per chunk is required:
		# deduplicate=True would otherwise reject the continuation, because the job queueing
		# it is itself still running under the base id. `run_id` is in the id too, so
		# re-pushing the same plan cannot collide with a chunk still pending from the
		# previous run and be silently dropped.
		frappe.enqueue(
			"gke_customization.gke_order_forms.doc_events.kggk_sync.sync_records",
			queue="long",
			timeout=JOB_TIMEOUT,
			job_id=f"kggk_sync::{run_id or reference or trigger}::chunk{chunk_index + 1}",
			deduplicate=True,
			items=rest_items,
			boms=rest_boms,
			trigger=trigger,
			reference=reference,
			totals=totals,
			counters=run.counters(),
			chunk_index=chunk_index + 1,
			run_id=run_id,
		)
		return {
			"status": "Running",
			**run.counters(),
			"remaining": len(rest_items) + len(rest_boms),
		}

	status = run.finish()
	return {"status": status, **run.counters()}


def enqueue_sync(items=None, boms=None, trigger="Manual", reference=None, job_id=None):
	"""Queue a batch. Never blocks the save or submit that asked for it."""
	items = list(dict.fromkeys(items or []))
	boms = list(dict.fromkeys(boms or []))
	if not items and not boms:
		return False

	if in_reentrant_context():
		return False

	config, reason = get_sync_config()
	if not config:
		log_skip(reason)
		return False

	frappe.enqueue(
		"gke_customization.gke_order_forms.doc_events.kggk_sync.sync_records",
		queue="long",
		timeout=JOB_TIMEOUT,
		enqueue_after_commit=True,
		job_id=job_id or f"kggk_sync::{trigger}::{reference or ''}",
		deduplicate=True,
		items=items,
		boms=boms,
		trigger=trigger,
		reference=reference,
		run_id=frappe.generate_hash(length=8),
	)
	return True

# ============================================================================
# MANUFACTURING PLAN ENTRY POINTS
# ============================================================================

def collect_records(doc):
	"""Return ``(items, boms)`` for the subcontracting rows of a Manufacturing Plan."""
	items = []
	boms = []

	for row in doc.get("manufacturing_plan_table") or []:
		if not cint(row.get("subcontracting")):
			continue

		item_code = row.get("item_code")
		if item_code and item_code not in items:
			items.append(item_code)

		bom_name = row.get("manufacturing_bom")
		if bom_name:
			if bom_name not in boms:
				boms.append(bom_name)
		else:
			# The plan throws on submit when a row has no manufacturing_bom, so this should
			# be unreachable. Say so rather than quietly pushing an item with no BOM.
			frappe.logger("kggk_sync").warning(
				f"{doc.name}: subcontracting row {row.get('idx')} has no manufacturing_bom"
			)

	return items, boms


def on_submit(doc, method=None):
	"""Queue the push. Submitting must never be slowed, blocked or rolled back by it.

	Everything is inside the try on purpose. ``enqueue_after_commit`` only defers the moment
	the job is handed to a worker - ``frappe.enqueue`` still opens the redis connection and
	runs its queue-size check synchronously, inside the submit transaction. An unreachable
	redis or a full queue would otherwise raise straight through ``doc.submit()`` and lose
	the plan, which is the one outcome this feature must never cause.
	"""
	try:
		items, boms = collect_records(doc)
		if not items and not boms:
			return

		config, reason = get_sync_config()
		if not config:
			log_skip(reason, "Manufacturing Plan", doc.name)
			return

		enqueue_sync(
			items=items,
			boms=boms,
			trigger="Manufacturing Plan",
			reference=doc.name,
			job_id=f"kggk_plan::{doc.name}",
		)
	except Exception:
		frappe.logger("kggk_sync").exception(f"could not queue the KGGK push for {doc.name}")


def sync_plan_now(plan_name):
	"""Run the push inline. For ``bench execute`` and tests, not for a request."""
	doc = frappe.get_doc("Manufacturing Plan", plan_name)
	items, boms = collect_records(doc)
	return sync_records(items=items, boms=boms, trigger="Manufacturing Plan", reference=plan_name)

# ============================================================================
# PREFILL: MAKE THE TESTING SITE READY
# ============================================================================
#
# A testing site is usually a thinner copy of GK: it lacks custom fields that were added
# here later, and it lacks the item and BOM records the plans refer to. Pushing into it
# then fails in ways that look like sync bugs but are really "the target was never set up".
#
# This is the button on Data Migration in KGGK. It works in two presses on purpose: the
# first says what it would do, the second does it. The first press writes nothing, which
# matters because the second one creates Custom Fields on another site - and if the Testing
# Site field has been pointed somewhere unintended, a dry run is the last chance to notice.

# Doctypes reconciled by the button. Manufacturing Plan is checked so the target is ready
# for it, but plan documents themselves are never copied - only the items and BOMs they
# name.
PREFILL_DOCTYPES = ("Item", "BOM", "Manufacturing Plan")

# Custom Field properties worth carrying to the target. Deliberately not everything: `name`,
# `owner` and the timestamps are the target's to own, and `module` is skipped because the
# module that exists here may not exist there.
CUSTOM_FIELD_PROPERTIES = (
	"fieldname",
	"label",
	"fieldtype",
	"options",
	"insert_after",
	"description",
	"default",
	"depends_on",
	"mandatory_depends_on",
	"read_only_depends_on",
	"fetch_from",
	"fetch_if_empty",
	"precision",
	"length",
	"reqd",
	"read_only",
	"hidden",
	"unique",
	"no_copy",
	"allow_on_submit",
	"in_list_view",
	"in_standard_filter",
	"print_hide",
	"report_hide",
	"translatable",
	"non_negative",
	"permlevel",
)


def _local_custom_fields(doctype):
	"""This site's Custom Fields for a doctype, keyed by fieldname."""
	rows = frappe.get_all(
		"Custom Field",
		filters={"dt": doctype},
		fields=list(CUSTOM_FIELD_PROPERTIES) + ["idx"],
		order_by="idx asc",
	)
	return {row["fieldname"]: row for row in rows if row.get("fieldname")}


def _plan_records(limit_plans=None):
	"""Every item and BOM the submitted Manufacturing Plans' subcontracting rows name.

	Scoped to what the sync actually pushes. Copying all of `tabItem` would be tens of
	thousands of records on a live jewellery site and is not what this button is for.
	"""
	plans = frappe.get_all(
		"Manufacturing Plan",
		filters={"docstatus": 1},
		pluck="name",
		order_by="modified desc",
		limit=limit_plans or None,
	)

	items, boms = [], []
	for plan in plans:
		rows = frappe.get_all(
			"Manufacturing Plan Table",
			filters={"parent": plan, "parenttype": "Manufacturing Plan", "subcontracting": 1},
			fields=["item_code", "manufacturing_bom"],
		)
		for row in rows:
			if row.item_code and row.item_code not in items:
				items.append(row.item_code)
			if row.manufacturing_bom and row.manufacturing_bom not in boms:
				boms.append(row.manufacturing_bom)

	return plans, items, boms


def _field_gaps(config, run=None):
	"""What the target is missing, per doctype.

	Splits deliberately. A missing *custom* field is ours to create. A missing *standard*
	field means the two sites are running different app versions, and papering over that
	with a same-named Custom Field would hide a real problem behind a field that only looks
	right - so those are reported and never created.
	"""
	creatable = []
	standard_gaps = []
	unreadable = []

	for doctype in PREFILL_DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue

		target_fields = get_target_fields(config, doctype, run=run)
		if target_fields is None:
			unreadable.append(doctype)
			continue

		local_custom = _local_custom_fields(doctype)
		for df in frappe.get_meta(doctype).fields:
			name = df.fieldname
			if not name or name in target_fields or df.fieldtype in LAYOUT_TYPES:
				continue
			if name in local_custom:
				row = dict(local_custom[name])
				row.pop("idx", None)
				row["dt"] = doctype
				creatable.append(row)
			else:
				standard_gaps.append(f"{doctype}.{name} ({df.fieldtype})")

	return creatable, standard_gaps, unreadable


def _create_custom_field(config, row):
	"""POST one Custom Field to the target. Returns ``(ok, message)``."""
	payload = {k: v for k, v in row.items() if v not in (None, "")}
	payload["dt"] = row["dt"]

	response = api_post(config, "/api/resource/Custom Field", json=payload)
	if response.ok:
		return True, "created"

	# `insert_after` names a field that may not exist on the target - the field itself is
	# still worth creating, it just lands at the end of the form instead.
	if payload.pop("insert_after", None):
		retry = api_post(config, "/api/resource/Custom Field", json=payload)
		if retry.ok:
			return True, "created without insert_after"
		return False, retry.message()

	return False, response.message()


@frappe.whitelist()
def prefill_testing_site(apply=0, limit_plans=None):
	"""Check the testing site and, on the second press, fill in what it is missing.

	``apply=0`` inspects and reports; nothing on the target changes. ``apply=1`` creates the
	missing Custom Fields and queues the missing item and BOM records.

	Never throws for a *sync* problem - a refusal to run is a thrown message, because you
	pressed a button and deserve to be told why, but a target that rejects one field is
	reported and the rest continues.
	"""
	frappe.only_for("System Manager")
	apply = cint(apply)

	config, reason = get_sync_config()
	if not config:
		frappe.throw(_(reason), title=_("Testing Sync Not Available"))

	run = SyncRun(
		trigger="Prefill" if apply else "Prefill (check only)",
		reference=config.to_site,
		config=config,
	)

	creatable, standard_gaps, unreadable = _field_gaps(config, run=run)
	plans, items, boms = _plan_records(limit_plans)

	# Which records the target does not have yet. `api_exists` returns None when the check
	# itself failed; those are counted as unknown rather than assumed present.
	missing_items, missing_boms, unchecked = [], [], []
	for doctype, names, bucket in (("Item", items, missing_items), ("BOM", boms, missing_boms)):
		for name in names:
			found = api_exists(config, doctype, name)
			if found is False:
				bucket.append(name)
			elif found is None:
				unchecked.append(f"{doctype} {name}")

	result = {
		"applied": bool(apply),
		"target": config.to_site,
		"plans_scanned": len(plans),
		"fields_to_create": [f"{r['dt']}.{r['fieldname']}" for r in creatable],
		"standard_field_gaps": standard_gaps,
		"schema_unreadable": unreadable,
		"items_total": len(items),
		"boms_total": len(boms),
		"items_missing": len(missing_items),
		"boms_missing": len(missing_boms),
		"unchecked": len(unchecked),
	}

	if not apply:
		result["message"] = _(
			"Checked {0}. {1} field(s) would be created, {2} item(s) and {3} BOM(s) would be pushed."
		).format(config.to_site, len(creatable), len(missing_items), len(missing_boms))
		# The check itself is worth a record on the target when it found something.
		for line in standard_gaps:
			run.mismatch(None, None, f"standard field absent on target: {line}", kind="VERSION-GAP")
		run.report()
		return result

	created, failed = [], []
	for row in creatable:
		ok, message = _create_custom_field(config, row)
		label = f"{row['dt']}.{row['fieldname']}"
		if ok:
			created.append(label)
			run.line("FIELD-CREATED", row["dt"], row["fieldname"], message)
		else:
			failed.append(label)
			run.mismatch(row["dt"], row["fieldname"], f"could not create on target - {message}",
			             kind="FIELD-CREATE-FAILED")

	for line in standard_gaps:
		run.mismatch(None, None, f"standard field absent on target: {line}", kind="VERSION-GAP")

	# The schema is now different, so anything cached about it is stale.
	for doctype in PREFILL_DOCTYPES:
		frappe.cache().delete_value(f"kggk_target_fields::{doctype}")

	queued = enqueue_sync(
		items=missing_items,
		boms=missing_boms,
		trigger="Prefill",
		reference=f"prefill {frappe.generate_hash(length=6)}",
	)

	run.report()

	result.update(
		{
			"fields_created": created,
			"fields_failed": failed,
			"records_queued": bool(queued),
			"message": _(
				"{0} field(s) created, {1} failed. {2} item(s) and {3} BOM(s) queued for push."
			).format(len(created), len(failed), len(missing_items), len(missing_boms)),
		}
	)
	return result
