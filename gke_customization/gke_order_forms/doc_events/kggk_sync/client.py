"""Authenticated HTTP access to the target site.

One helper, used by every caller, so timeouts, retries and error shape are decided in a
single place instead of being re-typed at each request.
"""

import time
from urllib.parse import quote

import frappe
import requests

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


def request(config, method, path, json=None, params=None, files=None, data=None, timeout=None):
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


def get(config, path, **kwargs):
	return request(config, "GET", path, **kwargs)


def put(config, path, **kwargs):
	return request(config, "PUT", path, **kwargs)


def post(config, path, **kwargs):
	return request(config, "POST", path, **kwargs)


def exists(config, doctype, name):
	"""Does this record exist on the target? ``None`` when the check itself failed."""
	if not name:
		return False
	response = get(
		config,
		f"/api/resource/{segment(doctype)}/{segment(name)}",
		params={"fields": '["name"]'},
	)
	if response.ok:
		return True
	if response.not_found:
		return False
	return None
