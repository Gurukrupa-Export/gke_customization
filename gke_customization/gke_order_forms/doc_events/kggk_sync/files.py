"""Move attachments to the target site.

An Attach field holds a path, not an image. Copying the string gives the target a dead
link, because the File record and its bytes only exist here. So the bytes are uploaded and
the field is set to the URL the target gives back.
"""

import os

import frappe
from frappe.utils import cint

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
	from . import client

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

	response = client.post(
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
