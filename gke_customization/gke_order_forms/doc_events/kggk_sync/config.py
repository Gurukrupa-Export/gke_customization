"""Settings, URL handling and the site guards for the Manufacturing Plan testing push.

Every outbound push funnels through :func:`get_sync_config`. It is the single place that
decides whether this site may push at all, and to where.

This is the *testing* target and it is deliberately separate from the live Item/BOM sync in
``doc_events/item.py``, which keeps reading ``to_site``/``api_key``/``api_secret`` on the same
settings screen and is not touched by anything here. Two flows, two targets, two sets of
credentials, one settings doctype.
"""

import frappe
from frappe.utils import cint

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
