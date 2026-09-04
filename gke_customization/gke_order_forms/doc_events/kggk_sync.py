"""Item / BOM / Manufacturing Plan -> KGGK: one module, one target, one flow.

Everything that leaves this site for KGGK goes through here. There are four ways in:

* an Item or BOM is saved                  -> ``item_on_update`` / ``bom_on_update``
* a Manufacturing Plan is submitted        -> ``on_submit`` (its subcontracting rows)
* the hourly reconciler finds drift        -> ``reconcile_changes``
* somebody presses a button                -> ``start_prefill`` / ``retry_log``

All four funnel into ``enqueue_sync`` and then ``sync_records``, so there is exactly one
place where a record is turned into a payload and pushed.

The target is ``to_site`` in Data Migration in KGGK, with ``api_key``/``api_secret``.
There is no second "testing" target: whether a site is test or production is decided by
what those fields point at, and by the master switch, which is off until somebody turns
it on.

This replaces the older ``doc_events/item.py`` push, which ran on ``before_validate`` with
blocking HTTP calls and could abort a local save when KGGK was unreachable. Those
functions are still in that file but are no longer hooked.

Everything lives in this single file on purpose so the whole feature can be read, reviewed
and reverted in one place.
"""

import os
import time
from urllib.parse import quote

import frappe
import requests
from frappe import _
from frappe.utils import cint, flt, now_datetime, time_diff_in_seconds


# ============================================================================
# SETTINGS, GUARDS AND URL HANDLING
# ============================================================================

SETTINGS = "Data Migration in KGGK"

# Reasons a push is refused. Surfaced verbatim wherever the skip is reported.
SKIP_DISABLED = "'Enable KGGK Sync' is off in Data Migration in KGGK"
SKIP_NO_TARGET = "To Site is not set in Data Migration in KGGK"
SKIP_NO_CREDS = "API Key / API Secret are not set in Data Migration in KGGK"
SKIP_SAME_SITE = "To Site is this site ({0}) - refusing to sync a site to itself"
SKIP_INSECURE = (
	"To Site ({0}) is not https. The API secret is sent on every request, so plain HTTP is "
	"refused; use https, or localhost for a development bench."
)
# The target this run was bound to is not the target configured now. Someone repointed To
# Site while the run was in flight.
SKIP_RETARGETED = (
	"this run was queued for {0} but To Site is now {1} - refusing to send records to a "
	"target the run was not checked against"
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


# Hosts allowed to speak plain HTTP. A development bench has no certificate; anything else
# would be putting the API secret on the wire in clear text.
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def is_secure(url):
	"""Is this URL safe to put a credential on?"""
	value = str(url or "").strip().lower()
	host = host_of(value)
	if host in LOCAL_HOSTS or host.endswith(".localhost"):
		return True
	return not value.startswith("http://")


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


def _api_secret():
	"""The API secret, whichever way the field is stored.

	``api_secret`` is a Data field today, so ``get_single_value`` returns it directly. A
	Password field on a Single instead leaves ``*****`` in ``tabSingles`` and keeps the real
	value in ``__Auth`` - and that placeholder authenticates as nothing, producing a 401 that
	looks exactly like a mistyped key and gets debugged in the wrong place. So a value that is
	nothing but asterisks is re-read from ``__Auth``, and converting the field later becomes a
	one-line change to the doctype and nothing else.
	"""
	value = frappe.db.get_single_value(SETTINGS, "api_secret")
	if value and set(str(value)) != {"*"}:
		return value

	from frappe.utils.password import get_decrypted_password

	try:
		return get_decrypted_password(SETTINGS, SETTINGS, "api_secret", raise_exception=False)
	except Exception:
		return None


def is_sync_enabled():
	"""The master switch. An absent or unticked field is OFF, deliberately."""
	return bool(cint(frappe.db.get_single_value(SETTINGS, "enable_sync")))


def get_sync_config():
	"""Resolve the push configuration, or return ``None`` with the reason it was refused.

	Returns ``(config, reason)``. ``config`` carries ``to_site`` plus ready-to-use
	``headers``. ``reason`` is ``None`` on success and a human-readable sentence otherwise.
	Callers report the reason; they never guess at it.
	"""
	settings = frappe.db.get_value(
		SETTINGS,
		SETTINGS,
		["from_site", "to_site", "enable_sync", "api_key"],
		as_dict=True,
	) or frappe._dict()

	if not cint(settings.get("enable_sync")):
		return None, SKIP_DISABLED

	target = settings.get("to_site")
	if not target:
		return None, SKIP_NO_TARGET

	api_key = settings.get("api_key")
	api_secret = _api_secret()
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

	if not is_secure(target):
		return None, SKIP_INSECURE.format(target_host)

	return (
		frappe._dict(
			from_site=base_url(from_site),
			to_site=base_url(target),
			# What this configuration *is*, so a job queued against it can tell that the
			# settings changed underneath it. The secret is included because rotating the
			# key is also a change worth noticing; it is hashed, never carried in the clear.
			fingerprint=config_fingerprint(from_site, target, api_key, api_secret),
			headers={
				"Authorization": f"token {api_key}:{api_secret}",
				"Accept": "application/json",
			},
		),
		None,
	)


def config_fingerprint(from_site, to_site, api_key, api_secret):
	"""A short, stable digest of the settings a run was queued against.

	Job arguments are readable by anyone who can open the queue, so this is a hash rather
	than the values themselves.
	"""
	import hashlib

	raw = "|".join(
		[host_of(from_site), host_of(to_site), str(api_key or ""), str(api_secret or "")]
	)
	return hashlib.sha256(raw.encode()).hexdigest()[:16]


def target_site():
	"""The configured target host, whether or not the sync is switched on.

	Sync State rows are keyed by target, so they must still be readable - to be counted, or
	cleared - while the switch is off.
	"""
	return host_of(frappe.db.get_single_value(SETTINGS, "to_site"))


def setting(fieldname, default=None):
	value = frappe.db.get_single_value(SETTINGS, fieldname)
	return default if value is None else value


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

# Statuses worth trying again. A 5xx is the target having a bad moment; a 429 is it asking us
# to slow down, which is the one 4xx that is not "your payload is wrong". frappe.cloud rate
# limits, and treating its 429 as fatal drops the record for a reason that would have cleared
# itself in a few seconds.
TOO_MANY_REQUESTS = 429
# A target that asks us to wait longer than this is having a bigger problem than one record.
MAX_RETRY_AFTER = 30


class Response:
	"""Uniform result. ``ok`` means the target accepted it; ``error`` is display-ready."""

	def __init__(self, status_code=None, data=None, text="", url="", error=None, headers=None):
		self.status_code = status_code
		self.data = data or {}
		self.text = text or ""
		self.url = url
		self.error = error
		self.headers = headers or {}

	@property
	def exc_type(self):
		"""The Frappe exception class the target raised, when it named one.

		Far more reliable than matching on the message, which is translated.
		"""
		return (self.data or {}).get("exc_type") or ""

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


def api_request(
	config,
	method,
	path,
	json=None,
	params=None,
	files=None,
	data=None,
	timeout=None,
	attempts=None,
	retry_connection=True,
):
	"""Call the target site, retrying only what is worth retrying.

	A connection error or a 5xx is transient and retried. A 4xx is the target telling us
	the payload is wrong; retrying that just sends the same wrong payload again.

	``attempts=1`` opts out of the retries entirely. Three attempts on a 30 s timeout with
	2 s and 4 s of backoff is up to 96 seconds for one call - fine inside a background job,
	far too long for anything that has to answer a web request.

	``retry_connection=False`` is for a call that creates something. A connection error says
	the *answer* was lost, not that the request was: the record may well have been created,
	and sending it again is how one BOM becomes two. Those callers re-ask what happened
	instead of guessing.
	"""
	url = _url(config, path)
	timeout = timeout or (UPLOAD_TIMEOUT if files else DEFAULT_TIMEOUT)
	max_attempts = max(int(attempts or MAX_ATTEMPTS), 1)
	headers = dict(config.headers)
	if json is not None:
		headers["Content-Type"] = "application/json"

	last = None
	for attempt in range(1, max_attempts + 1):
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
			if attempt < max_attempts and retry_connection:
				time.sleep(BACKOFF_SECONDS * attempt)
				continue
			return last

		payload = {}
		try:
			payload = raw.json() or {}
		except ValueError:
			payload = {}

		response = Response(
			status_code=raw.status_code,
			data=payload,
			text=raw.text,
			url=url,
			headers=dict(raw.headers or {}),
		)

		retryable = raw.status_code >= 500 or raw.status_code == TOO_MANY_REQUESTS
		if retryable and attempt < max_attempts:
			last = response
			time.sleep(_retry_delay(response, attempt))
			continue

		return response

	return last or Response(url=url, error="no attempt was made")


def _retry_delay(response, attempt):
	"""How long to wait before trying again.

	A 429 usually carries ``Retry-After``; obeying it is both politer and faster than our own
	backoff guess. Anything absurd is clamped - we are retrying one record, not waiting out
	an outage.
	"""
	after = (response.headers or {}).get("Retry-After")
	if after:
		try:
			return max(1, min(int(float(after)), MAX_RETRY_AFTER))
		except (TypeError, ValueError):
			pass
	return BACKOFF_SECONDS * attempt


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


# One GET can ask about many names at once. The ceiling is the URL, not the API: gunicorn
# refuses a request line over 4094 bytes, and jewellery item codes are long, so a chunk is
# closed on whichever comes first - the count or the encoded length.
EXISTS_BATCH = 50
MAX_FILTER_CHARS = 3000


def _name_chunks(names):
	"""Split names into batches small enough to survive as a query string."""
	chunk, size = [], 0
	for name in names:
		# +6 covers the quotes, comma and percent-encoding overhead of one more entry.
		cost = len(quote(str(name), safe="")) + 6
		if chunk and (len(chunk) >= EXISTS_BATCH or size + cost > MAX_FILTER_CHARS):
			yield chunk
			chunk, size = [], 0
		chunk.append(name)
		size += cost
	if chunk:
		yield chunk


def api_exists_many(config, doctype, names, run=None):
	"""Which of these records exist on the target? Returns ``{name: True/False}``.

	The single-record ``api_exists`` costs one round trip per name. Checking the items and
	BOMs of a real Manufacturing Plan that way is ~980 sequential requests, which is minutes
	of wall clock and the reason the prefill button used to time out. This asks in batches of
	fifty instead.

	A name is **absent from the returned mapping** when its batch could not be asked at all -
	the same distinction ``api_exists`` draws by returning ``None``. Callers must not read a
	missing key as "not there".
	"""
	found = {}
	names = [n for n in dict.fromkeys(names or []) if n]
	if not names:
		return found

	for chunk in _name_chunks(names):
		response = api_get(
			config,
			f"/api/resource/{segment(doctype)}",
			params={
				"filters": frappe.as_json([["name", "in", chunk]]),
				"fields": frappe.as_json(["name"]),
				# Without this the REST layer quietly caps the answer at 20 rows, and a
				# chunk of fifty would report thirty records as missing that are not.
				"limit_page_length": 0,
			},
		)
		if not response.ok:
			if run:
				run.mismatch(
					doctype,
					None,
					f"could not check whether {len(chunk)} {doctype}(s) exist on target - "
					f"{response.message()}",
					kind="LINK-UNKNOWN",
					once_key=f"existsmany::{doctype}",
				)
			continue

		present = {row.get("name") for row in (response.data.get("data") or [])}
		for name in chunk:
			found[name] = name in present

	return found


# A preflight is allowed one short attempt and no retries. Its whole job is to answer
# quickly, including - especially - when the answer is bad.
PREFLIGHT_TIMEOUT = 8


def check_connectivity(config):
	"""Can we reach the target and are the credentials good? Returns ``(ok, message)``.

	Three outcomes look identical from inside a failed sync and are completely different to
	act on: the host is wrong, the key is wrong, or everything is fine. Asking once, cheaply,
	up front turns a two-minute gateway timeout into an immediate sentence.
	"""
	response = api_get(
		config,
		"/api/method/frappe.auth.get_logged_user",
		timeout=PREFLIGHT_TIMEOUT,
		attempts=1,
	)

	if response.error:
		return False, _("{0} could not be reached: {1}").format(config.to_site, response.error)

	if response.status_code in (401, 403):
		return False, _(
			"{0} rejected the API Key / API Secret. Check the credentials in Data Migration in KGGK."
		).format(config.to_site)

	if not response.ok:
		return False, _("{0} answered with {1}").format(config.to_site, response.message())

	user = response.data.get("message") or "?"
	return True, _("Connected to {0} as {1}").format(config.to_site, user)

# ============================================================================
# RUN STATE AND THE REPORT WRITTEN ON THE TARGET
# ============================================================================

STATUS_QUEUED = "Queued"
STATUS_RUNNING = "Running"
STATUS_COMPLETED = "Completed"
STATUS_PARTIAL = "Partially Completed"
STATUS_FAILED = "Failed"

LOG_DOCTYPE = "KGGK Sync Log"
STATE_DOCTYPE = "KGGK Sync State"

# A run of several hundred records must not produce a document nobody can open. Past this
# the counters keep counting and the rows stop; the summary says so.
MAX_LOG_ROWS = 2000

# Dropped links waiting to be re-applied travel in the enqueue kwargs between chunks, so the
# list has to stay small enough to be a job argument rather than a payload.
MAX_DEFERRED = 500

# Whether a run keeps a KGGK Sync Log, and when it opens one.
#
# ON_PROBLEM exists for the single-record pushes. On a busy site every Item save queues one,
# and an eagerly-created log per save would be a document per save forever, nearly all of
# them empty. Those get a log only if something goes wrong; when they succeed, the Sync
# State row is the record that they happened.
LOG_ALWAYS = "always"
LOG_ON_PROBLEM = "on-problem"
LOG_NEVER = "never"

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


# Every way a push can start. Kept in step with the Trigger Select on KGGK Sync Log - an
# unknown value would make the log unsaveable, so `_open_log` falls back to "Manual".
TRIGGERS = (
	"Manual",
	"Manufacturing Plan",
	"Item Update",
	"BOM Update",
	"Prefill",
	"Reconcile",
	"Retry",
)


# The two doctypes this engine pushes, and therefore the only ones whose name on the target
# it can know. Anything else is assumed to be called the same on both sites.
MAPPED_DOCTYPES = ("Item", "BOM")


def mark_state(doctype, name, status, target, error=None, local_modified=None, target_name=None):
	"""Record what this site knows about one record on one target.

	This is the memory that makes "transfer later changes" and the hourly reconciler
	possible: without a row saying when a record last went across successfully, there is
	nothing to compare ``tabItem.modified`` against, and every run would either re-push
	everything or nothing.

	Never raises - a bookkeeping failure must not fail the push it is describing.
	"""
	if not name or not target:
		return

	def write():
		existing = frappe.db.get_value(
			STATE_DOCTYPE,
			{"record_doctype": doctype, "record_name": name, "target_site": target},
			"name",
		)
		doc = (
			frappe.get_doc(STATE_DOCTYPE, existing)
			if existing
			else frappe.get_doc(
				{
					"doctype": STATE_DOCTYPE,
					"record_doctype": doctype,
					"record_name": name,
					"target_site": target,
				}
			)
		)

		doc.status = status
		doc.last_error = str(error or "")[:500]
		if target_name:
			doc.target_name = target_name
		if status == "Synced":
			doc.synced_on = now_datetime()
			# The source document's own timestamp, not "now": the reconciler asks whether the
			# record changed *after* the version we sent, and only this answers that.
			doc.local_modified = local_modified or frappe.db.get_value(doctype, name, "modified")
			doc.attempts = 0
		elif status in ("Failed", "Partial"):
			# Partial counts too, or a link that will never resolve is retried by the
			# reconciler every hour until the end of time.
			doc.attempts = cint(doc.attempts) + 1

		doc.flags.ignore_version = True
		doc.save(ignore_permissions=True)

	# Read-then-write is not atomic, and a plan job, an item save and a prefill can all reach
	# the same record at once. The unique constraint on (type, record, target) is what stops
	# two rows existing; this turns the resulting error into the update it should have been.
	try:
		frappe.db.savepoint("kggk_state")
		write()
	except frappe.exceptions.DuplicateEntryError:
		frappe.db.rollback(save_point="kggk_state")
		try:
			write()
		except Exception:
			frappe.logger("kggk_sync").exception(
				f"could not record sync state for {doctype} {name} after a concurrent insert"
			)
	except Exception:
		frappe.logger("kggk_sync").exception(f"could not record sync state for {doctype} {name}")


def set_state_status(doctype, name, target, status):
	"""Change only the status of a Sync State row.

	Deliberately not `mark_state`: that one stamps ``local_modified`` from the record as it
	is *now* whenever the status is Synced. Promoting a record out of Partial after its link
	was repaired would therefore adopt any edit made since the push, and the reconciler would
	never send it. The version stamp belongs to the push that set it.
	"""
	if not name or not target:
		return
	try:
		row = frappe.db.get_value(
			STATE_DOCTYPE,
			{"record_doctype": doctype, "record_name": name, "target_site": target},
			"name",
		)
		if row:
			frappe.db.set_value(STATE_DOCTYPE, row, "status", status, update_modified=False)
	except Exception:
		frappe.logger("kggk_sync").exception(f"could not set sync status for {doctype} {name}")


def target_names(doctype, names, target):
	"""``{our name: its name on the target}`` for records we have pushed before.

	The name a record has on the target is not always the name we know it by. ERPNext names a
	BOM ``BOM-{item}-{index}``, and the index counts how many BOMs *that* site already holds
	for the item - so a BOM that is ``-002`` here can quite normally land as ``-001`` there.
	An item here carries Template, Quotation, Sales Order and Manufacturing Process BOMs while
	KGGK receives only the Template one, so the two numberings almost never agree.

	Addressing a record by our name after that point 404s, pushes it again, and leaves another
	duplicate behind on every run. Names we have never recorded map to themselves, which is
	the right guess for a first push.
	"""
	names = [n for n in dict.fromkeys(names or []) if n]
	mapping = {n: n for n in names}
	if not names or not target or doctype not in MAPPED_DOCTYPES:
		return mapping

	try:
		for row in frappe.get_all(
			STATE_DOCTYPE,
			filters={
				"record_doctype": doctype,
				"record_name": ("in", names),
				"target_site": target,
			},
			fields=["record_name", "target_name"],
		):
			if row.target_name:
				mapping[row.record_name] = row.target_name
	except Exception:
		frappe.logger("kggk_sync").exception(f"could not read target names for {doctype}")

	return mapping


def target_name_for(doctype, name, target):
	"""What one record is called on the target, falling back to our own name.

	The fallback is a *guess*, and it is only ever safe where the value is checked before
	use - resolving a Link, where `api_exists` decides. Never use it to address a record we
	are about to overwrite: see `target_name_if_known`.
	"""
	return target_names(doctype, [name], target).get(name, name)


def target_name_if_known(doctype, name, target):
	"""What the target calls this record, or ``None`` if we have never recorded it.

	The distinction `target_name_for` cannot make, and the one that matters before a write.
	Assuming an unrecorded BOM is called the same thing over there is how a PUT lands on a
	completely unrelated BOM: names are `BOM-{item}-{nnn}`, the index counts that site's own
	BOMs for the item, and KGGK creates BOMs of its own. `BOM-RING-001` exists on both sites
	and means two different things.
	"""
	if not name or not target or doctype not in MAPPED_DOCTYPES:
		return None
	try:
		return (
			frappe.db.get_value(
				STATE_DOCTYPE,
				{"record_doctype": doctype, "record_name": name, "target_site": target},
				"target_name",
			)
			or None
		)
	except Exception:
		frappe.logger("kggk_sync").exception(f"could not read the target name for {doctype} {name}")
		return None


def is_synced(doctype, name, target):
	"""Has this record ever gone across to this target successfully?"""
	if not name or not target:
		return False
	return bool(
		frappe.db.exists(
			STATE_DOCTYPE,
			{
				"record_doctype": doctype,
				"record_name": name,
				"target_site": target,
				"status": "Synced",
			},
		)
	)


def is_on_target(doctype, name, target):
	"""Does the target hold this record at all - complete or not?

	A Partial record is on the target just as much as a Synced one; it is only waiting for a
	link. Deciding "has KGGK got this?" on Synced alone would treat it as new, and the
	"Send Later Changes" switch would not apply to it.
	"""
	if not name or not target:
		return False
	return bool(
		frappe.db.exists(
			STATE_DOCTYPE,
			{
				"record_doctype": doctype,
				"record_name": name,
				"target_site": target,
				"status": ("in", ["Synced", "Partial"]),
			},
		)
	)


class SyncRun:
	"""One chunk of one run: counters, a problem list, and the report they turn into."""

	def __init__(
		self,
		trigger="Manual",
		reference=None,
		config=None,
		counters=None,
		chunk_index=0,
		log_name=None,
		deferred=None,
		log=LOG_ALWAYS,
	):
		self.trigger = trigger
		self.reference = reference or ""
		self.config = config
		self.chunk_index = chunk_index

		# The KGGK Sync Log this run writes to. Like the counters, the *name* rides in the
		# enqueue kwargs, so every continuation chunk appends to the same document instead of
		# leaving one orphaned log per fifty records.
		self.log_mode = log
		self.log_name = log_name or (self._open_log() if log == LOG_ALWAYS else None)
		self.rows = []
		self.rows_dropped = 0

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

		# Links dropped because the record they point at was not on the target *yet*. These
		# ride between chunks, because the BOM an Item wants is very often pushed later than
		# the Item itself. See `_apply_deferred_links`.
		self.deferred = [tuple(d) for d in (deferred or [])][:MAX_DEFERRED]

		# Records that reached the target with a link still missing. They are on the target
		# and they are not finished, and calling that "Synced" is what used to lose the link
		# for good: the reconciler compares timestamps, the record looks current, and nothing
		# ever goes back for it. Held as Partial instead, which the reconciler does pick up.
		self.incomplete = set()

	# -- counters carried to the next chunk ------------------------------------------

	def counters(self):
		return {
			"items_synced": self.items_synced,
			"items_failed": self.items_failed,
			"boms_synced": self.boms_synced,
			"boms_failed": self.boms_failed,
			"mismatches": self.mismatches,
		}

	@property
	def done(self):
		return self.items_synced + self.items_failed + self.boms_synced + self.boms_failed

	# -- the local log ----------------------------------------------------------------
	#
	# Nothing in this block may raise. A run's job is to push records; failing to write its
	# own diary is not a reason to lose the push, so every entry point is wrapped and the
	# failure goes to the logger.

	def _open_log(self):
		"""Create the KGGK Sync Log for this run and return its name."""
		if self.log_mode == LOG_NEVER:
			return None
		try:
			doc = frappe.get_doc(
				{
					"doctype": LOG_DOCTYPE,
					"trigger": self.trigger if self.trigger in TRIGGERS else "Manual",
					"reference": str(self.reference or "")[:140],
					"target_site": (self.config or {}).get("to_site") or "",
					"status": STATUS_RUNNING,
					"started_on": now_datetime(),
				}
			)
			doc.insert(ignore_permissions=True)
			return doc.name
		except Exception:
			frappe.logger("kggk_sync").exception("could not open a KGGK Sync Log")
			return None

	def _ensure_log(self):
		"""Open the log now, for a run that was only going to log if it went wrong."""
		if self.log_name or self.log_mode != LOG_ON_PROBLEM:
			return
		self.log_mode = LOG_ALWAYS
		self.log_name = self._open_log()

	def row(self, doctype, name, status, message="", action=""):
		"""Buffer one record's outcome. Written to the log once per chunk, not per record."""
		if status in ("Failed", "Skipped"):
			self._ensure_log()
		if len(self.rows) + self.rows_dropped >= MAX_LOG_ROWS:
			self.rows_dropped += 1
			return
		self.rows.append(
			{
				"record_doctype": doctype,
				"record_name": str(name)[:140],
				"status": status,
				"action": action[:140],
				"message": str(message or "")[:MAX_LINE_CHARS],
				"synced_on": now_datetime(),
			}
		)

	def flush(self, status=None):
		"""Write this chunk's rows, counters and progress onto the log document."""
		if not self.log_name or self.log_mode == LOG_NEVER:
			return
		try:
			doc = frappe.get_doc(LOG_DOCTYPE, self.log_name)
		except frappe.DoesNotExistError:
			# Somebody deleted it mid-run. Stop trying rather than raising every chunk.
			self.log_name = None
			return
		except Exception:
			frappe.logger("kggk_sync").exception(f"could not load {self.log_name}")
			return

		try:
			for row in self.rows:
				doc.append("records", row)
			self.rows = []

			for field, value in self.counters().items():
				doc.set(field, value)
			doc.items_total = self.items_total
			doc.boms_total = self.boms_total

			total = self.items_total + self.boms_total
			doc.progress = min(100.0, (self.done / total) * 100) if total else 100.0

			if status:
				doc.status = status
				doc.summary = self.summary(status)
				if status == STATUS_RUNNING and not doc.started_on:
					# The log was created Queued by whoever asked for the run; this is the
					# moment a worker actually picked it up.
					doc.started_on = now_datetime()
				if status != STATUS_RUNNING:
					doc.ended_on = now_datetime()
					doc.progress = 100.0

			if self.problems:
				existing = doc.problems or ""
				doc.problems = (existing + "\n" + "\n".join(self.problems))[-MAX_REPORT_CHARS:]

			if self.rows_dropped:
				doc.summary = (
					(doc.summary or "")
					+ f" | {self.rows_dropped} more record(s) not listed - the run exceeded "
					f"{MAX_LOG_ROWS} rows"
				)

			doc.flags.ignore_version = True
			doc.save(ignore_permissions=True)
			frappe.db.commit()
		except Exception:
			frappe.logger("kggk_sync").exception(f"could not update {self.log_name}")

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
		self._ensure_log()
		self.problem(kind, doctype, name, message, once_key=once_key)

	def defer_link(self, doctype, name, fieldname, value, link_doctype):
		"""Remember a link that was dropped only because its target had not arrived yet.

		``Item.master_bom`` is the case this exists for: items are pushed before BOMs, so the
		BOM an item points at is never on the target at the moment the item is sent, the link
		is dropped, and until now nothing ever put it back - the item landed on KGGK with no
		BOM attached. Rather than special-casing that one field, every dropped link is
		remembered and retried once its target exists.
		"""
		if len(self.deferred) >= MAX_DEFERRED:
			# Past the ceiling the link is not merely deferred, it is dropped - so the record
			# must not be allowed to look finished either.
			self.incomplete.add((doctype, name))
			return
		self.deferred.append((doctype, name, fieldname, value, link_doctype))
		self.incomplete.add((doctype, name))

	# -- outcomes --------------------------------------------------------------------

	def _target_host(self):
		return host_of((self.config or {}).get("to_site"))

	def item_ok(self, name, note="", local_modified=None, target_name=None):
		self.items_synced += 1
		status = "Partial" if ("Item", name) in self.incomplete else "Synced"
		self.line("OK", "Item", name, note or "synced")
		self.row("Item", name, status, note or "synced", action=note)
		mark_state(
			"Item",
			name,
			status,
			self._target_host(),
			local_modified=local_modified,
			target_name=target_name,
		)

	def item_failed(self, name, message):
		self.items_failed += 1
		self.last_error = f"Item {name}: {message}"[:1000]
		self.problem("FAILED", "Item", name, message)
		self.row("Item", name, "Failed", message)
		mark_state("Item", name, "Failed", self._target_host(), error=message)

	def bom_ok(self, name, note="", local_modified=None, target_name=None):
		self.boms_synced += 1
		status = "Partial" if ("BOM", name) in self.incomplete else "Synced"
		self.line("OK", "BOM", name, note or "synced")
		self.row("BOM", name, status, note or "synced", action=note)
		mark_state(
			"BOM",
			name,
			status,
			self._target_host(),
			local_modified=local_modified,
			target_name=target_name,
		)

	def bom_failed(self, name, message):
		self.boms_failed += 1
		self.last_error = f"BOM {name}: {message}"[:1000]
		self.problem("FAILED", "BOM", name, message)
		self.row("BOM", name, "Failed", message)
		mark_state("BOM", name, "Failed", self._target_host(), error=message)

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
			elif self.incomplete or self.mismatches:
				# Everything was accepted, and something is still not right over there - a
				# link never resolved, a field could not be written. "Completed" would put
				# that behind a green tick and nobody would look again.
				status = STATUS_PARTIAL
			else:
				status = STATUS_COMPLETED
		self.line("INFO", None, None, f"=== sync finished: {self.summary(status)} ===")
		self.flush(status)
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


# How long the "this local file is already that file on the target" answer is trusted.
FILE_MAP_TTL = 24 * 60 * 60


def _file_map_key(config):
	return f"kggk_file_map::{host_of(config.to_site)}"


def _remember_upload(config, file_url, target_url):
	"""Note that a public file has already been uploaded, for the rest of the day.

	This used to live on ``frappe.local``, which lasts one request - and a run is a chain of
	background jobs, one per chunk. A catalogue image shared by 490 items was therefore
	re-uploaded once per chunk, twenty times over a full run. Redis outlives the chunk.
	"""
	try:
		frappe.cache().hset(_file_map_key(config), file_url, target_url)
		frappe.cache().expire(_file_map_key(config), FILE_MAP_TTL)
	except Exception:
		pass


def _recall_upload(config, file_url):
	try:
		return frappe.cache().hget(_file_map_key(config), file_url)
	except Exception:
		return None


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

	already = _recall_upload(config, file_url)
	if already:
		return already

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
		# Private files are deliberately not remembered: the target serves them only to users
		# with permission on the document they hang off, so each document needs its own copy.
		_remember_upload(config, file_url, new_url)
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


def _child_rows(doc, df, allowed=None):
	"""Rows of one child table, restricted to fields the target's child doctype has.

	``allowed=None`` means we could not learn the target's child schema, so everything is
	sent and the target decides - the same fallback the parent uses.
	"""
	rows = []
	for row in doc.get(df.fieldname) or []:
		data = {}
		meta = frappe.get_meta(df.options)
		for child_df in meta.fields:
			if child_df.fieldtype in LAYOUT_TYPES or child_df.fieldtype in TABLE_TYPES:
				continue
			if child_df.fieldname in CHILD_EXCLUDE:
				continue
			if allowed is not None and child_df.fieldname not in allowed:
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


def _child_gap(doc, df, allowed):
	"""Child fieldnames that carry a value here and do not exist on the target."""
	missing = set()
	meta = frappe.get_meta(df.options)
	for row in doc.get(df.fieldname) or []:
		for child_df in meta.fields:
			name = child_df.fieldname
			if not name or name in allowed or name in CHILD_EXCLUDE:
				continue
			if child_df.fieldtype in LAYOUT_TYPES or child_df.fieldtype in TABLE_TYPES:
				continue
			if row.get(name) not in (None, "", 0, []):
				missing.add(name)
	return missing


def build_payload(doc, allowed_fields=None, run=None, config=None):
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
			# A jewellery BOM carries several big child tables. One custom field the target
			# is missing on one of them rejects the whole BOM, with a message that names the
			# child row rather than the field - so compare these too, not just the parent's.
			child_allowed = None
			if config is not None and df.options:
				child_allowed = get_target_fields(config, df.options, run=run)
				if child_allowed is not None:
					missing = _child_gap(doc, df, child_allowed)
					if missing:
						run and run.mismatch(
							doc.doctype,
							doc.name,
							f"{name}: {len(missing)} field(s) do not exist on the target's "
							f"{df.options}, dropped: " + ", ".join(sorted(missing)[:15]),
							kind="FIELD-MISSING",
							once_key=f"childgap::{df.options}",
						)
			rows = _child_rows(doc, df, allowed=child_allowed)
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

	# The target host is part of the key. Without it, repointing To Site serves the previous
	# target's field list for the next ten minutes, and every field the new target does have
	# gets dropped as "missing".
	cache_key = f"kggk_target_fields::{host_of(config.to_site)}::{doctype}"
	# `expires=True` is load-bearing, not decoration. On a miss, frappe's `get_value` stores
	# the None it just failed to find in `frappe.local.cache`, while `set_value` with a TTL
	# writes only to redis - so every later read in the same worker hits that cached None and
	# re-fetches. Since `push_item` asks once per record, the schema was being pulled from
	# the target twice for every single record: ~2000 wasted round trips on a 980-record run.
	cached = frappe.cache().get_value(cache_key, expires=True)
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

	on_submit = set()
	for row in rows:
		if row.get("fieldname"):
			fields.add(row["fieldname"])
			if cint(row.get("allow_on_submit")):
				on_submit.add(row["fieldname"])

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
	frappe.cache().set_value(
		_submit_fields_key(config, doctype), sorted(on_submit), expires_in_sec=_TARGET_FIELD_TTL
	)
	return fields


def _submit_fields_key(config, doctype):
	return f"kggk_target_submit_fields::{host_of(config.to_site)}::{doctype}"


def get_target_submit_fields(config, doctype, run=None):
	"""Fields the target still allows to change after a document is submitted.

	Populated as a side effect of ``get_target_fields``; this only reads it back, and asks
	for the schema first if nobody has yet.
	"""
	cached = frappe.cache().get_value(_submit_fields_key(config, doctype), expires=True)
	if cached is None:
		get_target_fields(config, doctype, run=run)
		cached = frappe.cache().get_value(_submit_fields_key(config, doctype), expires=True)
	return set(cached or [])

# ============================================================================
# THE PUSH PIPELINE
# ============================================================================

# Fields that identify a record and cannot be changed on an existing one.
IMMUTABLE_ON_UPDATE = {"Item": {"variant_of", "item_code"}, "BOM": {"item"}}

# ---------------------------------------------------------------------------------
# RECORD IDENTITY ON THE TARGET
# ---------------------------------------------------------------------------------
#
# A record's *name* is not its identity across two sites. ERPNext names a BOM
# `BOM-{item}-{nnn}` where the index counts how many BOMs that site already holds for the
# item, so the same design is `-002` here and `-001` there, and `BOM-RING-001` exists on
# both sites meaning different things. Addressing a record by name alone therefore either
# overwrites something unrelated or creates a duplicate.
#
# So every record we push carries where it came from, and that triple - source site, source
# doctype, source name - is what we look it up by. It is stable across renames on either
# side, it survives our Sync State table being lost, and it makes the push an upsert rather
# than a guess.

IDENTITY_SOURCE_SITE = "custom_kggk_source_site"
IDENTITY_SOURCE_DOCTYPE = "custom_kggk_source_doctype"
IDENTITY_SOURCE_NAME = "custom_kggk_source_name"

# Created on the target for each doctype we push. `read_only` because they are bookkeeping,
# not data anybody there should edit; `no_copy` so an amended document does not inherit an
# identity belonging to another record.
IDENTITY_FIELDS = (
	{
		"fieldname": IDENTITY_SOURCE_SITE,
		"label": "Source Site",
		"fieldtype": "Data",
		"read_only": 1,
		"no_copy": 1,
		"description": "Set by the Gurukrupa sync. The site this record was pushed from.",
	},
	{
		"fieldname": IDENTITY_SOURCE_DOCTYPE,
		"label": "Source DocType",
		"fieldtype": "Data",
		"read_only": 1,
		"no_copy": 1,
		"description": "Set by the Gurukrupa sync.",
	},
	{
		"fieldname": IDENTITY_SOURCE_NAME,
		"label": "Source Name",
		"fieldtype": "Data",
		"read_only": 1,
		"no_copy": 1,
		# The lookup runs on this for every record in a run; without the index it is a full
		# table scan of the target's Item table each time.
		"search_index": 1,
		"description": "Set by the Gurukrupa sync. The name this record has on the source site.",
	},
)


def source_host():
	"""The host this site is known by, for stamping onto records we push."""
	try:
		host = host_of(frappe.utils.get_url())
		if host:
			return host
	except Exception:
		pass
	return host_of(getattr(frappe.local, "site", "") or "")


def _identity_values(doctype, name):
	return {
		IDENTITY_SOURCE_SITE: source_host(),
		IDENTITY_SOURCE_DOCTYPE: doctype,
		IDENTITY_SOURCE_NAME: str(name),
	}


def _identity_key(config, doctype):
	return f"kggk_identity_ready::{host_of(config.to_site)}::{doctype}"


def ensure_identity_fields(config, doctype, run=None):
	"""Make sure the target can hold - and be searched by - a record's origin.

	Returns True when the target has all three fields. Without them the upsert has nothing
	to look a record up by and has to fall back to matching on name, which is the behaviour
	this exists to replace, so a failure here is reported rather than passed over.
	"""
	cached = frappe.cache().get_value(_identity_key(config, doctype), expires=True)
	if cached:
		return True

	existing = get_target_fields(config, doctype, run=run)
	if existing is None:
		# We could not read the schema at all. Nothing is safe to conclude.
		return False

	missing = [f for f in IDENTITY_FIELDS if f["fieldname"] not in existing]
	for field in missing:
		row = dict(field)
		row["dt"] = doctype
		ok, message = _create_custom_field(config, row)
		if not ok:
			run and run.mismatch(
				doctype,
				None,
				f"could not create {row['fieldname']} on the target - {message}. Records will "
				"be matched by name instead, which cannot tell two sites' BOMs apart.",
				kind="IDENTITY-UNAVAILABLE",
				once_key=f"identity::{doctype}",
			)
			return False

	if missing:
		# The schema just changed; whatever we cached about it is a field list short.
		frappe.cache().delete_value(f"kggk_target_fields::{host_of(config.to_site)}::{doctype}")

	frappe.cache().set_value(_identity_key(config, doctype), 1, expires_in_sec=_TARGET_FIELD_TTL)
	return True


def lookup_by_identity(config, doctype, name, run=None):
	"""What the target calls the record that came from our ``name``, or ``None``.

	``None`` means "not there" only when the question was actually answered; a lookup that
	failed returns ``_LOOKUP_FAILED`` so the caller refuses to create rather than creating a
	duplicate on the strength of a timeout.
	"""
	identity = _identity_values(doctype, name)
	response = api_get(
		config,
		f"/api/resource/{segment(doctype)}",
		params={
			"filters": frappe.as_json(
				[
					[IDENTITY_SOURCE_SITE, "=", identity[IDENTITY_SOURCE_SITE]],
					[IDENTITY_SOURCE_DOCTYPE, "=", doctype],
					[IDENTITY_SOURCE_NAME, "=", str(name)],
				]
			),
			"fields": frappe.as_json(["name"]),
			"limit_page_length": 0,
			"order_by": "creation asc",
		},
	)
	if not response.ok:
		run and run.mismatch(
			doctype,
			name,
			f"could not ask the target which record came from this one - {response.message()}",
			kind="IDENTITY-LOOKUP-FAILED",
			once_key=f"idlookup::{doctype}",
		)
		return _LOOKUP_FAILED

	rows = response.data.get("data") or []
	if not rows:
		return None
	if len(rows) > 1:
		# The target already holds duplicates of this record. Say so - it is a data problem
		# over there that no amount of syncing will fix - and keep using the oldest, so that
		# every later run addresses the same one instead of alternating between them.
		run and run.mismatch(
			doctype,
			name,
			f"the target holds {len(rows)} records that all claim to come from this one "
			f"({', '.join(r.get('name') for r in rows[:5])}); using the oldest",
			kind="TARGET-DUPLICATE",
		)
	return rows[0].get("name")


# Distinct from None, which means "asked, and it is not there".
_LOOKUP_FAILED = object()


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
	target_host = host_of(config.to_site)
	for fieldname, (link_doctype, essential) in link_fields(doc.doctype).items():
		value = data.get(fieldname)
		if not value:
			continue

		# A link to an Item or a BOM has to carry the name the *target* uses, which is not
		# always ours. Sending our name would point the link at nothing, or worse at the
		# wrong record.
		remote_value = target_name_for(link_doctype, value, target_host)
		if remote_value != value:
			data[fieldname] = remote_value

		found = _link_exists(config, link_doctype, remote_value, cache)
		if found is None:
			# The check itself failed - a timeout, a 500, a 403. Treating that as "it is
			# there" sends the value anyway and the target rejects the whole record with a
			# message that blames something else entirely.
			run.mismatch(
				doc.doctype,
				doc.name,
				f"{fieldname}: could not check whether {link_doctype} '{remote_value}' exists "
				"on target, sending it anyway",
				kind="LINK-UNKNOWN",
				once_key=f"linkcheck::{link_doctype}",
			)
			continue
		if found:
			continue
		if essential:
			blocking.append(
				f"{fieldname}: {link_doctype} '{remote_value}' does not exist on target"
			)
			continue
		data.pop(fieldname, None)
		# Deferred with OUR name. The target may not have named it yet - that happens when
		# it is pushed, later in this same run - so the translation has to wait until the
		# relink pass rather than being frozen in now.
		run.defer_link(doc.doctype, doc.name, fieldname, value, link_doctype)
		run.mismatch(
			doc.doctype,
			doc.name,
			f"{fieldname}: {link_doctype} '{remote_value}' does not exist on target, field "
			"dropped for now - will be re-applied if it arrives later in this run",
			kind="LINK-MISSING",
		)
	return blocking


def _apply_deferred_links(config, run):
	"""Put back the links that were dropped only because their target arrived later.

	Items are pushed before BOMs, so ``Item.master_bom`` is always dropped on the way out and
	the item lands on KGGK unlinked. This runs after the BOMs, re-checks the whole backlog in
	batched calls rather than one per link, and PUTs back the ones that now resolve.

	What is still missing keeps the LINK-MISSING line it already has - it is a genuine gap,
	not an ordering artefact.
	"""
	if not run.deferred:
		return

	target_host = host_of(config.to_site)

	# Now, not when the link was dropped: the record it points at may have been pushed since,
	# and only now do we know what the target decided to call it.
	remote = {}
	for _dt, _name, _field, value, link_doctype in run.deferred:
		remote.setdefault(link_doctype, set()).add(value)
	remote = {
		link_doctype: target_names(link_doctype, sorted(values), target_host)
		for link_doctype, values in remote.items()
	}

	exists = {}
	for link_doctype, mapping in remote.items():
		exists[link_doctype] = api_exists_many(
			config, link_doctype, sorted(set(mapping.values())), run=run
		)

	# One PUT per record, not per field, so an item with two recovered links costs one call.
	updates = {}
	still_missing = []
	for doctype, name, fieldname, value, link_doctype in run.deferred:
		remote_value = remote.get(link_doctype, {}).get(value, value)
		if exists.get(link_doctype, {}).get(remote_value):
			updates.setdefault((doctype, name), {})[fieldname] = remote_value
		else:
			still_missing.append((doctype, name, fieldname, link_doctype, remote_value))

	# Records that will still be waiting on something after this pass, whatever happens to
	# the PUTs below. Only a record on neither list has actually been completed.
	unfinished = {(doctype, name) for doctype, name, _f, _ld, _v in still_missing}

	for (doctype, name), fields in updates.items():
		# The record being patched may itself be under a different name over there.
		known = target_name_if_known(doctype, name, target_host)
		if not known:
			# The state row is missing - `mark_state` swallows its own failures, so this can
			# happen after a push that otherwise worked. Ask the target directly rather than
			# either guessing our own name, which is what lands a PUT on an unrelated record,
			# or giving up on a link we can still repair.
			found = lookup_by_identity(config, doctype, name, run=run)
			known = None if found is _LOOKUP_FAILED else found

		if not known:
			run.mismatch(
				doctype,
				name,
				f"{', '.join(sorted(fields))}: cannot be re-linked - the target has no record "
				"that came from this one, and its name there was never recorded",
				kind="RELINK-FAILED",
			)
			unfinished.add((doctype, name))
			continue

		response = api_put(
			config, f"/api/resource/{segment(doctype)}/{segment(known)}", json=fields
		)
		if response.ok:
			run.line("RELINKED", doctype, name, ", ".join(sorted(fields)))
		else:
			run.mismatch(
				doctype,
				name,
				f"{', '.join(sorted(fields))}: could not be re-linked on target - "
				f"{response.message()}",
				kind="RELINK-FAILED",
			)
			# A failed relink is not a lost one. Put it back in the backlog so the next chunk,
			# and failing that the hourly reconciler, tries again.
			for fieldname, value in fields.items():
				link_doctype = next(
					(ld for dt, nm, fn, _v, ld in run.deferred
					 if (dt, nm, fn) == (doctype, name, fieldname)),
					None,
				)
				still_missing.append((doctype, name, fieldname, link_doctype, value))
			unfinished.add((doctype, name))

	# Whatever is finished is finished: promote it out of Partial so the reconciler stops
	# carrying it. Anything still waiting keeps its Partial row and will be picked up again.
	for doctype, name in {k for k in updates} - unfinished:
		run.incomplete.discard((doctype, name))
		set_state_status(doctype, name, target_host, "Synced")

	for doctype, name, fieldname, link_doctype, value in still_missing:
		run.incomplete.add((doctype, name))
		set_state_status(doctype, name, target_host, "Partial")
		run.line(
			"LINK-PENDING", doctype, name, f"{fieldname}: {link_doctype} '{value}' still absent"
		)

	# Only what could not be resolved is worth carrying into the next chunk.
	run.deferred = [
		(doctype, name, fieldname, value, link_doctype)
		for doctype, name, fieldname, link_doctype, value in still_missing
	]


def _send(config, doctype, name, data, lookup=None, run=None):
	"""Upsert one record on the target, addressed by where it came from.

	Returns ``(response, action, target_name, blocked_fields)``.

	The record is looked up by its identity - the source site, doctype and name stamped on
	it - and *not* by its name, which means two different things on two sites. Three answers
	are possible and all three matter:

	* a name comes back  -> PUT that record, whatever it is called over there
	* nothing comes back -> POST, and remember what the target decides to call it
	* the question could not be answered -> refuse. Creating on the strength of a failed
	  lookup is how a duplicate is made, and a duplicate BOM is not something the next run
	  can tidy up.

	``blocked_fields`` is non-empty only when the target has already submitted the record and
	would not let those fields change.
	"""
	data = dict(data)
	data.update(_identity_values(doctype, name))

	identified = ensure_identity_fields(config, doctype, run=run)

	target_id = lookup
	if not target_id and identified:
		found = lookup_by_identity(config, doctype, name, run=run)
		if found is _LOOKUP_FAILED:
			return (
				Response(error="could not determine whether this record already exists on the target"),
				"skipped",
				name,
				[],
			)
		target_id = found

	if not target_id and not identified:
		# No identity on the target and no recorded name. Matching on our own name is exactly
		# the guess that overwrites an unrelated record, so this refuses instead - the
		# prefill button creates the identity fields and then it will go through.
		return (
			Response(
				error="the target has no source-identity fields, so this record cannot be "
				"matched safely - run Check / Prefill Target Site first"
			),
			"skipped",
			name,
			[],
		)

	if target_id:
		update_data = {
			k: v for k, v in data.items() if k not in IMMUTABLE_ON_UPDATE.get(doctype, set())
		}
		path = f"/api/resource/{segment(doctype)}/{segment(target_id)}"
		response = api_put(config, path, json=update_data)

		if response.ok:
			return response, "updated", target_id, []

		# The target has submitted this record, so most of it is frozen over there. Sending
		# the whole payload would keep failing on the first frozen field forever. ERPNext
		# still lets a handful of fields change after submit - is_active and is_default on a
		# BOM among them - so send those and say plainly which ones could not move.
		#
		# This engine never submits anything itself: submitting is irreversible on someone
		# else's production site, and the REST route for it needs a full read-modify-write
		# that would overwrite the record if it went wrong. Records land as drafts and KGGK
		# submits them.
		if response.exc_type == "UpdateAfterSubmitError":
			allowed = get_target_submit_fields(config, doctype, run=run)
			reduced = {k: v for k, v in update_data.items() if k in allowed}
			blocked = sorted(set(update_data) - set(reduced))
			if not reduced:
				return response, "updated", target_id, blocked
			retry = api_put(config, path, json=reduced)
			action = "updated (submitted on target)" if retry.ok else "updated"
			return retry, action, target_id, blocked

		if not response.not_found:
			return response, "updated", target_id, []

		# It was there when we asked and is not there now - deleted mid-run. Fall through and
		# create it again rather than failing the record.
		run and run.line("INFO", doctype, name, f"{target_id} vanished from the target, recreating")

	# Create. Deliberately not retried on a connection error: the record may have been
	# created and only the answer lost, so we ask the target what happened rather than
	# sending it a second time.
	response = api_post(
		config, f"/api/resource/{segment(doctype)}", json=data, retry_connection=False
	)

	if response.error and identified:
		settled = lookup_by_identity(config, doctype, name, run=run)
		if settled is not _LOOKUP_FAILED and settled:
			run and run.line(
				"RECOVERED", doctype, name, f"the create did land, as {settled}, despite the error"
			)
			return Response(status_code=200, data={"data": {"name": settled}}), "created", settled, []

	assigned = ((response.data or {}).get("data") or {}).get("name") or name
	return response, "created", assigned, []


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
	# Captured before the push, not after. If somebody saves this item while it is in flight,
	# storing the later timestamp would swallow their edit permanently; storing the version
	# we actually sent leaves the reconciler able to spot the difference next time round.
	sent_version = doc.modified

	target_host = host_of(config.to_site)

	# A variant cannot be created before its template exists on the target.
	if doc.get("variant_of"):
		template = doc.variant_of
		if api_exists(config, "Item", target_name_for("Item", template, target_host)) is False:
			run.line("INFO", "Item", item_code, f"template {template} missing on target, pushing it first")
			run.items_total += 1
			push_item(template, config, run, seen=seen)

	allowed = get_target_fields(config, "Item", run=run)
	data, attachments = build_payload(doc, allowed, run=run, config=config)
	blocking = _strip_missing_links(config, doc, data, run, run.link_cache)
	if blocking:
		message = "required master(s) missing on target - " + "; ".join(blocking)
		run.item_failed(item_code, message)
		return False

	response, action, target_id, blocked = _send(
		config,
		"Item",
		item_code,
		data,
		lookup=target_name_if_known("Item", item_code, target_host),
		run=run,
	)
	if blocked:
		run.mismatch(
			"Item",
			item_code,
			f"the target has submitted this record, so {len(blocked)} field(s) could not be "
			"updated: " + ", ".join(blocked[:20]) + (f" (+{len(blocked) - 20} more)" if len(blocked) > 20 else ""),
			kind="SUBMITTED-ON-TARGET",
		)
	if not response.ok:
		message = response.message()
		run.item_failed(item_code, message)
		return False

	note = action
	if target_id != item_code:
		# Worth saying out loud: from here on the two sites know this record by different
		# names, and every later link to it has to use theirs.
		note = f"{action} as {target_id}"
		run.line("RENAMED", "Item", item_code, f"the target calls it {target_id}")

	if attachments:
		resolved = upload_all(config, attachments, "Item", target_id, run=run)
		if resolved:
			follow_up = api_put(
				config, f"/api/resource/Item/{segment(target_id)}", json=resolved
			)
			if follow_up.ok:
				note = f"{note}, {len(resolved)} attachment(s)"
			else:
				run.mismatch(
					"Item", item_code, f"attachment urls could not be set - {follow_up.message()}"
				)
				note = f"{note}, attachments uploaded but not linked"

	run.item_ok(item_code, note, local_modified=sent_version, target_name=target_id)
	return True


def push_bom(bom_name, config, run):
	"""Create or update one BOM on the target, attachments included."""
	if not frappe.db.exists("BOM", bom_name):
		run.bom_failed(bom_name, "BOM does not exist on this site")
		return False

	doc = frappe.get_doc("BOM", bom_name)
	sent_version = doc.modified

	# A BOM cannot validate on the target without its finished-goods item. Batches are
	# assembled from Items and BOMs independently - "Sync Now" takes the oldest unsynced of
	# each - so the item a given BOM needs is very often not in the same batch. Pull it in
	# rather than failing the BOM for a reason the operator cannot act on.
	target_host = host_of(config.to_site)

	if (
		doc.get("item")
		and api_exists(config, "Item", target_name_for("Item", doc.item, target_host)) is False
	):
		run.line("INFO", "BOM", bom_name, f"item {doc.item} missing on target, pushing it first")
		run.items_total += 1
		push_item(doc.item, config, run)

	allowed = get_target_fields(config, "BOM", run=run)
	data, attachments = build_payload(doc, allowed, run=run, config=config)
	blocking = _strip_missing_links(config, doc, data, run, run.link_cache)
	if blocking:
		message = "required master(s) missing on target - " + "; ".join(blocking)
		run.bom_failed(bom_name, message)
		return False

	response, action, target_id, blocked = _send(
		config,
		"BOM",
		bom_name,
		data,
		lookup=target_name_if_known("BOM", bom_name, target_host),
		run=run,
	)
	if blocked:
		run.mismatch(
			"BOM",
			bom_name,
			f"the target has submitted this BOM, so {len(blocked)} field(s) could not be "
			"updated: " + ", ".join(blocked[:20]) + (f" (+{len(blocked) - 20} more)" if len(blocked) > 20 else ""),
			kind="SUBMITTED-ON-TARGET",
		)
	if not response.ok:
		message = response.message()
		run.bom_failed(bom_name, message)
		return False

	note = action
	if target_id != bom_name:
		# The common case for BOMs, not the exception. An item here carries Template,
		# Quotation, Sales Order and Manufacturing Process BOMs while KGGK receives only the
		# Template one, so the two sites' numbering almost never lines up.
		note = f"{action} as {target_id}"
		run.line("RENAMED", "BOM", bom_name, f"the target calls it {target_id}")

	if attachments:
		resolved = upload_all(config, attachments, "BOM", target_id, run=run)
		if resolved:
			follow_up = api_put(config, f"/api/resource/BOM/{segment(target_id)}", json=resolved)
			if follow_up.ok:
				note = f"{note}, {len(resolved)} attachment(s)"
			else:
				run.mismatch("BOM", bom_name, f"attachment urls could not be set - {follow_up.message()}")

	run.bom_ok(bom_name, note, local_modified=sent_version, target_name=target_id)
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
	log_name=None,
	deferred=None,
	expect_target=None,
	expect_fingerprint=None,
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

	# The settings are a Single, so they can be edited while this run is in flight - and a
	# run is a chain of jobs, each of which reads them afresh. Without this a twenty-chunk
	# run can be repointed halfway through and post the rest of a Manufacturing Plan into a
	# different company's site, recording Sync State rows that say it went somewhere it did
	# not. The run travels with the target it was queued for and refuses anything else.
	blocked = _wrong_target(config, expect_target, expect_fingerprint)
	if blocked:
		log_skip(blocked)
		if log_name:
			_abandon_run(log_name, blocked)
		return {"status": STATUS_FAILED, "error": blocked}

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
		log_name=log_name,
		deferred=deferred,
		log=LOG_ON_PROBLEM if trigger in ("Item Update", "BOM Update") else LOG_ALWAYS,
	)
	run.items_total = int(totals.get("items") or 0)
	run.boms_total = int(totals.get("boms") or 0)
	if chunk_index == 0:
		run.flush(STATUS_RUNNING)
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
	loops_completed = False
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

		# The BOMs of this chunk now exist on the target, so the links that were dropped
		# because they did not - `Item.master_bom` above all - can be put back.
		frappe.db.savepoint("kggk_relink")
		try:
			_apply_deferred_links(config, run)
		except Exception as exc:
			frappe.db.rollback(save_point="kggk_relink")
			run.mismatch(None, None, f"the relink pass failed: {exc}", kind="RELINK-FAILED")

		loops_completed = True
	finally:
		frappe.flags.in_kggk_sync = False
		if not loops_completed:
			# A chunk killed by the job timeout, or one that raised on its way out, still
			# reports what it learned. Silence here would look exactly like a clean run.
			run.flush()
			run.report()

	if rest_items or rest_boms:
		# Every chunk reports its own problems. Only the last one used to, because `finish()`
		# is the only other caller of `report()` - so on a twenty-chunk run, nineteen chunks
		# of mismatches went nowhere but the log file.
		run.flush()
		run.report()
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
			log_name=run.log_name,
			deferred=run.deferred,
			expect_target=expect_target,
			expect_fingerprint=expect_fingerprint,
		)
		return {
			"status": "Running",
			**run.counters(),
			"remaining": len(rest_items) + len(rest_boms),
		}

	status = run.finish()
	return {"status": status, **run.counters()}


def _wrong_target(config, expect_target, expect_fingerprint):
	"""The reason this run must not proceed against the current settings, or ``None``."""
	if expect_target and host_of(config.to_site) != expect_target:
		return SKIP_RETARGETED.format(expect_target, host_of(config.to_site))
	if expect_fingerprint and config.get("fingerprint") != expect_fingerprint:
		# Same host, different credentials. Worth stopping for on its own: a key that changed
		# mid-run usually means the target was repointed and back, or rotated under us.
		return (
			f"the KGGK settings changed after this run was queued (target {host_of(config.to_site)} "
			"is the same, but the credentials are not) - refusing to continue"
		)
	return None


def _abandon_run(log_name, reason):
	"""Close a log for a run that refused to proceed, so it does not sit at Running."""
	try:
		doc = frappe.get_doc(LOG_DOCTYPE, log_name)
		doc.status = STATUS_FAILED
		doc.summary = reason
		doc.ended_on = now_datetime()
		doc.problems = ((doc.problems or "") + f"\nABORTED       | - | - | {reason}")[
			-MAX_REPORT_CHARS:
		]
		doc.flags.ignore_version = True
		doc.save(ignore_permissions=True)
		frappe.db.commit()
	except Exception:
		frappe.logger("kggk_sync").exception(f"could not close abandoned run {log_name}")


def enqueue_sync(items=None, boms=None, trigger="Manual", reference=None, job_id=None, log_name=None):
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
		log_name=log_name,
		# Bound here, where the target is known to be the one the caller decided on.
		expect_target=host_of(config.to_site),
		expect_fingerprint=config.get("fingerprint"),
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
# ITEM AND BOM ENTRY POINTS
# ============================================================================
#
# These replace the `before_validate` hooks in `doc_events/item.py`, which pushed to KGGK
# synchronously with `requests` and called `frappe.throw` on any API error - so an
# unreachable KGGK site aborted the local save. Nothing below can do that: the whole body
# is inside a try, and the push itself happens in a background job.

# The rule that first sends a record to KGGK, carried over verbatim from the hooks this
# replaces so nothing that used to cross stops crossing.
def is_eligible(doc):
	"""Should this record go to KGGK on its own merit, before any sync history?"""
	if doc.doctype == "Item":
		return doc.get("setting_type") == "Close"
	if doc.doctype == "BOM":
		return doc.get("setting_type") == "Close" and doc.get("bom_type") == "Template"
	return False


def _on_master_update(doc):
	"""Queue a push for one Item or BOM. Never blocks, slows or fails the save.

	Two ways to qualify:

	* the record meets `is_eligible` - a closed design, a template BOM - which is exactly
	  what the old hooks pushed, so this is not a behaviour change; or
	* KGGK already has it, in which case a later edit here has to reach it there. That is
	  the whole of "transfer later changes", and it is why Sync State exists.

	Anything else is left alone: a live jewellery site holds tens of thousands of items that
	KGGK has never asked for and does not want.
	"""
	try:
		if in_reentrant_context():
			return

		# The cheapest gate first. On a site with the switch off this is one cached read on
		# every Item and BOM save, instead of five field reads and a password decrypt.
		if not is_sync_enabled():
			return

		config, reason = get_sync_config()
		if not config:
			log_skip(reason, doc.doctype, doc.name)
			return

		target_host = host_of(config.to_site)
		already = is_on_target(doc.doctype, doc.name, target_host)

		# "Send Later Changes" means exactly that: changes to a record KGGK already holds.
		# Testing eligibility here instead was the bug - a Close Item is eligible forever, so
		# every later save of one still went across with the switch off, which is precisely
		# the case the switch exists to stop.
		if already and not cint(setting("sync_updates", 1)):
			return

		if not is_eligible(doc) and not already:
			return

		# Durable intent, written before the queue is touched. `frappe.enqueue` can refuse -
		# redis unreachable, or `deduplicate` declining because a job with this id is already
		# running, in which case the *current* edit is simply dropped - and an exception here
		# is swallowed so the save cannot fail. Without this row nothing would remember that a
		# push was ever wanted: the reconciler joins on Sync State, so a record with no row is
		# invisible to it forever.
		mark_state(doc.doctype, doc.name, "Pending", target_host)

		key = "items" if doc.doctype == "Item" else "boms"
		enqueue_sync(
			**{key: [doc.name]},
			trigger=f"{doc.doctype} Update",
			reference=doc.name,
			# Ten rapid saves of the same item collapse into at most two jobs: the one
			# running and the one queued behind it.
			job_id=f"kggk_{doc.doctype.lower()}::{doc.name}",
		)
	except Exception:
		# `enqueue_after_commit` defers the handoff, but `frappe.enqueue` still opens redis
		# and runs its queue-size check synchronously. An unreachable redis would otherwise
		# raise straight through `doc.save()` - the exact failure this rewrite exists to end.
		frappe.logger("kggk_sync").exception(
			f"could not queue the KGGK push for {doc.doctype} {doc.name}"
		)


def item_on_update(doc, method=None):
	_on_master_update(doc)


def bom_on_update(doc, method=None):
	"""Also hooked on ``on_update_after_submit``.

	BOMs here are submitted, and Frappe runs ``on_update`` for a save and a submit but a
	*different* hook for an edit after submit. Registering only the first would mean
	post-submit BOM edits never reach KGGK - which is most BOM edits.
	"""
	_on_master_update(doc)

# ============================================================================
# THE HOURLY RECONCILER
# ============================================================================

# What one scheduled pass is allowed to queue. At CHUNK_SIZE=50 this is four chunks, which
# finishes long before the next hour, so passes cannot overlap into a pile-up.
RECONCILE_LIMIT = 200

# A record that has failed this many times running is left alone. Without a ceiling, one
# permanently broken record - a mandatory master the target will never have - consumes the
# whole hourly budget forever and the genuinely stale records behind it never move.
MAX_RECONCILE_ATTEMPTS = 5


def _drifted(doctype, target, limit):
	"""Records whose local version is newer than what KGGK last received.

	This single comparison is what the whole Sync State table exists for: `local_modified`
	is the source document's timestamp at the moment of the last successful push, so
	anything edited since sorts out here and nothing else does.
	"""
	if limit <= 0:
		return []
	rows = frappe.db.sql(
		f"""
		select   state.record_name
		from     `tabKGGK Sync State` state
		join     `tab{doctype}` source on source.name = state.record_name
		where    state.record_doctype = %(doctype)s
		and      state.target_site = %(target)s
		and      (
		             (state.status = 'Synced' and (
		                 state.local_modified is null or source.modified > state.local_modified
		             ))
		             -- Pending is a push that was asked for and may never have been queued:
		             -- redis was down, the worker died, or the deduplicated job id was
		             -- refused because one was already running. It is the only record of
		             -- that intent, so it has to be visible here.
		             or (state.status in ('Pending', 'Partial')
		                 and state.attempts < %(max_attempts)s)
		             or (state.status = 'Failed' and state.attempts < %(max_attempts)s)
		         )
		order by source.modified asc
		limit    %(limit)s
		""",
		{
			"doctype": doctype,
			"target": target,
			"limit": cint(limit),
			"max_attempts": MAX_RECONCILE_ATTEMPTS,
		},
		pluck=True,
	)
	return rows or []


def reconcile_changes():
	"""Hourly: find what drifted out of step and push it. The safety net, not the main path.

	`item_on_update` already queues the ordinary case. This catches what it could not: a
	save made while KGGK was down, a job lost to a worker restart, a record edited by a
	patch or a bulk import that never fired the hook.

	Reads and enqueues only - no HTTP - so it finishes in milliseconds whatever the target
	is doing.
	"""
	if in_reentrant_context():
		return

	if not cint(setting("auto_reconcile", 0)):
		return

	config, reason = get_sync_config()
	if not config:
		log_skip(reason, None, "hourly reconcile")
		return

	target = host_of(config.to_site)
	budget = cint(setting("reconcile_batch_size", 0)) or RECONCILE_LIMIT

	items = _drifted("Item", target, budget)
	boms = _drifted("BOM", target, budget - len(items))

	if not items and not boms:
		return

	frappe.logger("kggk_sync").info(
		f"{_stamp()} | RECONCILE     | - | - | {len(items)} item(s), {len(boms)} BOM(s) out of step"
	)
	enqueue_sync(
		items=items,
		boms=boms,
		trigger="Reconcile",
		reference=f"hourly {now_datetime():%Y-%m-%d %H:%M}",
		job_id="kggk_reconcile",
	)

# ============================================================================
# RETRY
# ============================================================================


@frappe.whitelist()
def retry_log(log_name):
	"""Re-queue whatever failed in an earlier run, into a new log.

	A new document rather than a rewrite of the old one: the failed attempt stays readable
	exactly as it was, which is the thing you go back to when the retry fails too.
	"""
	frappe.only_for("System Manager")

	log = frappe.get_doc(LOG_DOCTYPE, log_name)
	if log.status in (STATUS_QUEUED, STATUS_RUNNING):
		frappe.throw(_("This run is still {0}.").format(log.status))

	items = [r.record_name for r in log.records if r.status in ("Failed", "Pending") and r.record_doctype == "Item"]
	boms = [r.record_name for r in log.records if r.status in ("Failed", "Pending") and r.record_doctype == "BOM"]

	if not items and not boms:
		frappe.throw(_("Nothing in this run failed, so there is nothing to retry."))

	config, reason = get_sync_config()
	if not config:
		frappe.throw(_(reason), title=_("Sync Not Available"))

	retry = frappe.get_doc(
		{
			"doctype": LOG_DOCTYPE,
			"trigger": "Retry",
			"reference": log_name,
			"target_site": config.to_site,
			"status": STATUS_QUEUED,
			"items_total": len(items),
			"boms_total": len(boms),
		}
	)
	retry.insert(ignore_permissions=True)

	enqueue_sync(
		items=items,
		boms=boms,
		trigger="Retry",
		reference=log_name,
		job_id=f"kggk_retry::{retry.name}",
		log_name=retry.name,
	)
	return retry.name

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
	if not plans:
		return [], [], []

	# One query for every plan, not one query per plan. Child rows carry their parent's
	# docstatus, so submitted plans are selected without a join.
	filters = {
		"parenttype": "Manufacturing Plan",
		"subcontracting": 1,
		"docstatus": 1,
	}
	if limit_plans:
		filters["parent"] = ("in", plans)

	rows = frappe.get_all(
		"Manufacturing Plan Table",
		filters=filters,
		fields=["item_code", "manufacturing_bom"],
		order_by="parent asc, idx asc",
	)

	items, boms = [], []
	for row in rows:
		if row.item_code and row.item_code not in items:
			items.append(row.item_code)
		if row.manufacturing_bom and row.manufacturing_bom not in boms:
			boms.append(row.manufacturing_bom)

	return plans, items, boms


def _prefill_doctypes():
	"""The doctypes the button reconciles: Item, BOM, Manufacturing Plan and their children.

	The child tables matter as much as the parents here. A jewellery BOM's metal, diamond and
	finding rows carry their own custom fields, and one of those missing on the target rejects
	the entire BOM - so the button has to be able to see and create them too.
	"""
	doctypes = []
	for parent in PREFILL_DOCTYPES:
		if not frappe.db.exists("DocType", parent):
			continue
		doctypes.append(parent)
		for df in frappe.get_meta(parent).fields:
			if df.fieldtype in TABLE_TYPES and df.options and df.options not in doctypes:
				doctypes.append(df.options)
	return doctypes


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
	seen_fields = {}

	for doctype in _prefill_doctypes():
		target_fields = get_target_fields(config, doctype, run=run)
		if target_fields is None:
			unreadable.append(doctype)
			continue
		seen_fields[doctype] = target_fields

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

	# The three fields that let a record be found by where it came from. They exist only on
	# the target - there is nothing to mirror them from here - so the gap logic above cannot
	# see them, and without them every push falls back to matching on name.
	for doctype in MAPPED_DOCTYPES:
		target_fields = seen_fields.get(doctype)
		if target_fields is None:
			continue
		for field in IDENTITY_FIELDS:
			if field["fieldname"] not in target_fields:
				row = dict(field)
				row["dt"] = doctype
				creatable.append(row)

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


# A run older than this that still says Running is almost certainly a worker that died, not
# a run still going. It stops one stuck run from blocking the button forever.
STALE_RUN_MINUTES = 120


def _prefill_in_flight():
	"""The name of a prefill that is genuinely still running, if there is one."""
	for row in frappe.get_all(
		LOG_DOCTYPE,
		filters={"trigger": "Prefill", "status": ("in", [STATUS_QUEUED, STATUS_RUNNING])},
		fields=["name", "modified"],
		order_by="modified desc",
		limit=5,
	):
		age = time_diff_in_seconds(now_datetime(), row.modified)
		if age < STALE_RUN_MINUTES * 60:
			return row.name
	return None


def _stored_result(log_name):
	"""The findings a prefill check wrote onto its log, or ``None``."""
	problems = frappe.db.get_value(LOG_DOCTYPE, log_name, "problems") or ""
	start = problems.rfind("{")
	if start == -1:
		return None
	try:
		return frappe.parse_json(problems[start:])
	except Exception:
		return None


def _check_is_actionable(result):
	"""Why the findings of this check must not be acted on, or ``None``.

	A check that could not see everything is not a check. Applying on the back of one creates
	custom fields and pushes records on the strength of a question that was never answered -
	and the gaps it could not see are exactly the records that will fail.
	"""
	if not result:
		return _("The check did not record its findings, so there is nothing to apply.")
	if result.get("applied"):
		return _("That log is an Apply, not a check.")
	if cint(result.get("unchecked")):
		return _(
			"{0} record(s) could not be checked against the target, so this run does not know "
			"what is missing. Run the check again."
		).format(cint(result.get("unchecked")))
	if result.get("schema_unreadable"):
		return _("The target's field list could not be read for: {0}.").format(
			", ".join(result["schema_unreadable"])
		)
	if result.get("standard_field_gaps"):
		return _(
			"The target is missing {0} standard field(s), so the two sites are running "
			"different app versions. That has to be resolved by deploying, not by this button."
		).format(len(result["standard_field_gaps"]))
	return None


@frappe.whitelist()
def start_prefill(apply=0, limit_plans=None, check_log=None):
	"""Hand the prefill to a worker and return the log to watch. Answers in milliseconds.

	This used to do the whole job inside the web request: one existence check per item and
	per BOM across every submitted plan, each retried three times on a 30 second timeout,
	and on apply a POST per custom field - of which Item alone has nearly two hundred. Well
	past the 120 second gateway limit, so the browser got "Request Timed Out" while the work
	carried on invisibly in a worker that had already been killed.

	What is still done here is only what has to be: refusing, with a reason, before anything
	is queued. A configuration problem or an unreachable target should be a sentence on
	screen, not a log entry you have to go and find.
	"""
	frappe.only_for("System Manager")
	apply = cint(apply)

	config, reason = get_sync_config()
	if not config:
		frappe.throw(_(reason), title=_("KGGK Sync Not Available"))

	# One short call, no retries. Eight seconds to learn the target is unreachable beats two
	# minutes of gateway timeout followed by a guess.
	reachable, message = check_connectivity(config)
	if not reachable:
		frappe.throw(message, title=_("Cannot Reach the Target Site"))

	if apply:
		# Apply acts on the findings of one specific check. Without naming it, "the second
		# press" is only a second call to the same endpoint - and between the two presses the
		# To Site can have been changed, which would create fields and push records into a
		# site nobody ever checked.
		if not check_log:
			frappe.throw(
				_("Run the check first, then apply its result."), title=_("Nothing to Apply")
			)
		log = frappe.db.get_value(
			LOG_DOCTYPE, check_log, ["trigger", "status", "target_site"], as_dict=True
		)
		if not log or log.trigger != "Prefill":
			frappe.throw(_("{0} is not a prefill check.").format(check_log))
		if log.status != STATUS_COMPLETED:
			frappe.throw(
				_("That check finished as {0}, so its findings are incomplete.").format(log.status),
				title=_("Check Not Usable"),
			)
		if host_of(log.target_site) != host_of(config.to_site):
			frappe.throw(
				_("That check was run against {0}, but To Site is now {1}.").format(
					host_of(log.target_site), host_of(config.to_site)
				),
				title=_("Target Changed"),
			)
		refusal = _check_is_actionable(_stored_result(check_log))
		if refusal:
			frappe.throw(refusal, title=_("Check Not Usable"))

	running = _prefill_in_flight()
	if running:
		frappe.throw(
			_("A prefill is already running: {0}").format(running), title=_("Already Running")
		)

	log = frappe.get_doc(
		{
			"doctype": LOG_DOCTYPE,
			"trigger": "Prefill",
			"reference": _("Apply") if apply else _("Check only"),
			"target_site": config.to_site,
			"status": STATUS_QUEUED,
		}
	)
	log.insert(ignore_permissions=True)

	frappe.enqueue(
		"gke_customization.gke_order_forms.doc_events.kggk_sync.run_prefill",
		queue="long",
		timeout=JOB_TIMEOUT,
		enqueue_after_commit=True,
		job_id=f"kggk_prefill::{log.name}",
		deduplicate=True,
		log_name=log.name,
		apply=apply,
		limit_plans=limit_plans,
		expect_target=host_of(config.to_site),
		expect_fingerprint=config.get("fingerprint"),
	)

	return {"log": log.name, "target": config.to_site, "connection": message}


def run_prefill(log_name, apply=0, limit_plans=None, expect_target=None, expect_fingerprint=None):
	"""Work out what the target is missing and, on apply, fill it in.

	Two presses on purpose: the first writes nothing, the second creates Custom Fields on
	another site and queues records at it. If To Site has been pointed somewhere unintended,
	the check is the last chance to notice.

	Never throws for a *sync* problem. A target that rejects one field is reported and the
	rest continues; the log says what happened either way.
	"""
	apply = cint(apply)

	config, reason = get_sync_config()
	if not config:
		_close_prefill(log_name, STATUS_FAILED, reason)
		return

	blocked = _wrong_target(config, expect_target, expect_fingerprint)
	if blocked:
		_close_prefill(log_name, STATUS_FAILED, blocked)
		return

	run = SyncRun(
		trigger="Prefill",
		reference=config.to_site,
		config=config,
		log_name=log_name,
	)
	run.flush(STATUS_RUNNING)

	creatable, standard_gaps, unreadable = _field_gaps(config, run=run)
	plans, items, boms = _plan_records(limit_plans)

	run.items_total = len(items)
	run.boms_total = len(boms)

	# Ask about the names the target uses, not ours - otherwise every record it renamed
	# reads as missing and gets pushed again, which is how duplicates breed.
	target_host = host_of(config.to_site)
	item_map = target_names("Item", items, target_host)
	bom_map = target_names("BOM", boms, target_host)

	# Batched: one request per fifty names instead of one per name. This is the difference
	# between twenty requests and a thousand for a real plan.
	item_presence = api_exists_many(config, "Item", sorted(set(item_map.values())), run=run)
	bom_presence = api_exists_many(config, "BOM", sorted(set(bom_map.values())), run=run)

	missing_items = [n for n in items if item_presence.get(item_map[n]) is False]
	missing_boms = [n for n in boms if bom_presence.get(bom_map[n]) is False]
	# A name whose batch could not be asked about is unknown, never assumed present.
	unchecked = [n for n in items if item_map[n] not in item_presence] + [
		n for n in boms if bom_map[n] not in bom_presence
	]

	for line in standard_gaps:
		run.mismatch(None, None, f"standard field absent on target: {line}", kind="VERSION-GAP")

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
		# A check that could not see everything must not close green. Its whole output is a
		# list of what the target is missing, and an unanswered question is not an empty one -
		# `Completed` here is what let an incomplete check be applied.
		incomplete = bool(unchecked) or bool(unreadable) or bool(standard_gaps)
		if incomplete:
			result["message"] += _(
				" Incomplete: {0} record(s) could not be checked, {1} doctype(s) unreadable, "
				"{2} standard field gap(s). Run it again before applying."
			).format(len(unchecked), len(unreadable), len(standard_gaps))
		_close_prefill(
			log_name,
			STATUS_PARTIAL if incomplete else STATUS_COMPLETED,
			result["message"],
			result=result,
			run=run,
		)
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
			run.mismatch(
				row["dt"],
				row["fieldname"],
				f"could not create on target - {message}",
				kind="FIELD-CREATE-FAILED",
			)

	# The target's schema is now different, so anything cached about it is stale.
	for doctype in _prefill_doctypes():
		frappe.cache().delete_value(f"kggk_target_fields::{host_of(config.to_site)}::{doctype}")
		frappe.cache().delete_value(_submit_fields_key(config, doctype))

	queued = enqueue_sync(
		items=missing_items,
		boms=missing_boms,
		trigger="Prefill",
		reference=f"prefill {log_name}",
	)

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
	_close_prefill(
		log_name,
		STATUS_PARTIAL if failed else STATUS_COMPLETED,
		result["message"],
		result=result,
		run=run,
	)
	return result


def _close_prefill(log_name, status, message, result=None, run=None):
	"""Write the prefill's answer onto its log. The only place the button's result lives."""
	if run:
		run.report(status)
	try:
		doc = frappe.get_doc(LOG_DOCTYPE, log_name)
		doc.status = status
		doc.summary = message
		doc.ended_on = now_datetime()
		doc.progress = 100.0
		if result:
			doc.items_total = result.get("items_total") or 0
			doc.boms_total = result.get("boms_total") or 0
			# The check's findings, for the button that acts on them.
			doc.problems = (
				(doc.problems or "")
				+ "\n\n"
				+ frappe.as_json(result, indent=1)
			)[-MAX_REPORT_CHARS:]
		if run and run.rows:
			for row in run.rows:
				doc.append("records", row)
			run.rows = []
		doc.flags.ignore_version = True
		doc.save(ignore_permissions=True)
		frappe.db.commit()
	except Exception:
		frappe.logger("kggk_sync").exception(f"could not close prefill log {log_name}")


@frappe.whitelist()
def prefill_result(log_name):
	"""The stored findings of a prefill check, for the form that offers to act on them."""
	frappe.only_for("System Manager")
	result = _stored_result(log_name)
	if result:
		# The form needs to know whether it may offer Apply at all, and the reason has to be
		# the same one the server will enforce - two implementations of "is this usable"
		# would eventually disagree, and the disagreement would be a button that throws.
		result["blocked_reason"] = _check_is_actionable(result)
	return result


@frappe.whitelist()
def prefill_testing_site(apply=0, limit_plans=None):
	"""Deprecated. Kept so an older client calling the previous name still works."""
	return start_prefill(apply=apply, limit_plans=limit_plans)
