"""Settings, URL handling and the site-identity guard for the KGGK sync.

Every outbound push funnels through :func:`get_sync_config`. It is the single place that
decides whether this site is allowed to push at all, which is why the same-site bug is
fixed here rather than at each call site.
"""

import frappe
from frappe.utils import cint

SETTINGS = "Data Migration in KGGK"

# Reasons a push is refused. Surfaced verbatim in the migration log.
SKIP_DISABLED = "Is Migrate is off in Data Migration in KGGK"
SKIP_NO_TARGET = "To Site is not set in Data Migration in KGGK"
SKIP_NO_CREDS = "API Key / API Secret are not set in Data Migration in KGGK"
SKIP_SAME_SITE = "From Site and To Site are the same ({0}) - refusing to sync a site to itself"
SKIP_WRONG_SITE = "This site ({0}) is not the configured From Site ({1}) - refusing to push"


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


def get_settings():
	return frappe.get_cached_doc(SETTINGS)


def is_sync_enabled():
	"""The Is Migrate master switch. Absent field is treated as OFF, deliberately."""
	return bool(cint(frappe.db.get_single_value(SETTINGS, "is_migrate")))


def get_sync_config(check_enabled=True):
	"""Resolve the push configuration, or return ``None`` with the reason it was refused.

	Returns ``(config, reason)``. ``config`` is a dict with ``to_site``, ``from_site`` and
	ready-to-use ``headers``; ``reason`` is ``None`` on success and a human-readable
	sentence otherwise. Callers log the reason - they never guess at it.
	"""
	settings = frappe.db.get_value(
		SETTINGS,
		SETTINGS,
		["from_site", "to_site", "api_key", "api_secret", "is_migrate", "ignore_site_check"],
		as_dict=True,
	) or frappe._dict()

	if check_enabled and not cint(settings.get("is_migrate")):
		return None, SKIP_DISABLED

	from_site = settings.get("from_site")
	to_site = settings.get("to_site")

	if not to_site:
		return None, SKIP_NO_TARGET

	api_key = settings.get("api_key")
	api_secret = settings.get("api_secret")
	if not api_key or not api_secret:
		return None, SKIP_NO_CREDS

	# --- the same-site guard -------------------------------------------------------
	# This is never legitimate and is never bypassable. A Single doctype travels with a
	# database restore, so a clone of the source site arrives already configured to push;
	# without this check it pushes straight back into itself, and the inbound write then
	# re-fires the same hook.
	target_host = host_of(to_site)
	if from_site and host_of(from_site) == target_host:
		return None, SKIP_SAME_SITE.format(target_host)

	here = current_site_hosts()
	if target_host in here:
		return None, SKIP_SAME_SITE.format(target_host)

	# --- the wrong-site guard ------------------------------------------------------
	# Bypassable, because a bench with no host_name configured can report a site identity
	# that never matches From Site. Same-site above is not bypassable; this one is.
	if from_site and not cint(settings.get("ignore_site_check")):
		if here and host_of(from_site) not in here:
			return None, SKIP_WRONG_SITE.format(", ".join(sorted(here)), host_of(from_site))

	return (
		frappe._dict(
			from_site=base_url(from_site),
			to_site=base_url(to_site),
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
