"""Dry-run the sync against a throwaway target on localhost.

    bench --site <site> execute gke_customization.gke_order_forms.doc_events.kggk_sync.dry_run.run
    bench --site <site> execute ...dry_run.run --kwargs "{'plan': 'MP-GEPL-2025-00405', 'limit': 5}"

Stands up a mock Frappe REST endpoint in-process, points the settings at it for the
duration, pushes a handful of records and prints what crossed the wire. Everything is
rolled back at the end: no markers are set, and the real To Site and credentials are
restored even if the run raises.

**This is not a substitute for testing against the real KGGK site.** It proves our side of
the wire - payload shape, ordering, attachments, the guards - but the mock accepts what
real KGGK might reject. Use it to catch regressions cheaply, then do one real run.
"""

import json
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

import frappe

from .config import SETTINGS, current_site_hosts

_RESTORE_FIELDS = (
	"from_site",
	"to_site",
	"api_key",
	"api_secret",
	"is_migrate",
	"ignore_site_check",
	"sync_status",
	"sync_log",
)


class _Recorder:
	def __init__(self):
		self.exists = set()
		self.created = []
		self.updated = []
		self.uploads = []
		self.rejected_keys = []


def _handler_for(recorder, known_fields):
	class Handler(BaseHTTPRequestHandler):
		def log_message(self, *args):
			pass

		def _reply(self, code, body):
			raw = json.dumps(body).encode()
			self.send_response(code)
			self.send_header("Content-Type", "application/json")
			self.send_header("Content-Length", str(len(raw)))
			self.end_headers()
			self.wfile.write(raw)

		def _path(self):
			return urllib.parse.unquote(self.path.split("?")[0])

		def _segments(self):
			"""Split first, unquote after.

			Item codes legitimately contain "/" (BA00026/01-001), which the client escapes
			to %2F. Unquoting before splitting would turn one segment into two and route
			the request to the wrong place - a mock bug that looks exactly like a product
			failure in the log.
			"""
			raw = self.path.split("?")[0]
			return [urllib.parse.unquote(part) for part in raw.split("/")]

		def _body(self):
			length = int(self.headers.get("Content-Length") or 0)
			return json.loads(self.rfile.read(length) or b"{}")

		def do_GET(self):
			path = self._path()
			parts = self._segments()
			if path.startswith("/api/resource/DocType/"):
				doctype = parts[-1]
				fields = known_fields.get(doctype, set())
				return self._reply(200, {"data": {"fields": [{"fieldname": f} for f in fields]}})
			if path == "/api/resource/Custom Field":
				return self._reply(200, {"data": []})
			if len(parts) >= 5:
				name = parts[4]
				if name in recorder.exists:
					return self._reply(200, {"data": {"name": name}})
				# Masters are assumed present; Items and BOMs only exist once pushed.
				if parts[3] in ("Item", "BOM"):
					return self._reply(404, {"exception": "DoesNotExistError"})
				return self._reply(200, {"data": {"name": name}})
			return self._reply(404, {})

		def do_PUT(self):
			body = self._body()
			name = self._segments()[4]
			if name not in recorder.exists:
				return self._reply(404, {"exception": "DoesNotExistError"})
			recorder.updated.append((name, len(body)))
			return self._reply(200, {"data": {"name": name}})

		def do_POST(self):
			path = self._path()
			if path == "/api/method/upload_file":
				length = int(self.headers.get("Content-Length") or 0)
				recorder.uploads.append(length)
				self.rfile.read(length)
				return self._reply(
					200, {"message": {"file_url": f"/files/dryrun_{len(recorder.uploads)}.bin"}}
				)
			body = self._body()
			doctype = self._segments()[3]
			name = body.get("item_code") or body.get("name") or f"{doctype}-{len(recorder.created)}"
			unknown = [k for k in body if k not in known_fields.get(doctype, set())]
			if unknown:
				recorder.rejected_keys.extend(unknown)
			recorder.exists.add(name)
			recorder.created.append((name, len(body)))
			return self._reply(200, {"data": {"name": name}})

	return Handler


def run(plan=None, limit=3, item=None):
	"""Push a few records at a mock target and report. Changes nothing permanently."""
	from . import push, selectors

	saved = frappe.db.get_value(SETTINGS, SETTINGS, list(_RESTORE_FIELDS), as_dict=True) or frappe._dict()

	known_fields = {
		doctype: {f.fieldname for f in frappe.get_meta(doctype).fields if f.fieldname}
		for doctype in ("Item", "BOM")
	}
	recorder = _Recorder()
	server = HTTPServer(("127.0.0.1", 0), _handler_for(recorder, known_fields))
	port = server.server_address[1]
	threading.Thread(target=server.serve_forever, daemon=True).start()

	try:
		if plan:
			from ..manufacturing_plan import collect_records

			items, boms = collect_records(frappe.get_doc("Manufacturing Plan", plan), only_unsynced=False)
			items, boms = items[:limit], boms[:limit]
			source = f"Manufacturing Plan {plan}"
		elif item:
			items, boms, source = [item], [], f"Item {item}"
		else:
			items = selectors.unsynced_items(limit=limit)
			boms = selectors.unsynced_boms(limit=limit)
			source = "oldest unsynced records"

		if not items and not boms:
			print("Nothing to dry-run.")
			return

		# Stay under one chunk: a continuation would commit and defeat the rollback below.
		if len(items) + len(boms) >= push.CHUNK_SIZE:
			items = items[: push.CHUNK_SIZE // 2]
			boms = boms[: push.CHUNK_SIZE // 2 - 1]

		here = sorted(current_site_hosts())[0]
		frappe.db.set_single_value(
			SETTINGS,
			{
				"from_site": f"http://{here}",
				"to_site": f"http://127.0.0.1:{port}",
				"api_key": "dry-run",
				"api_secret": "dry-run",
				"is_migrate": 1,
				"ignore_site_check": 0,
				"sync_log": "",
			},
			update_modified=False,
		)
		frappe.clear_cache()

		print(f"\nDRY RUN — {source}")
		print(f"  target      : http://127.0.0.1:{port} (in-process mock)")
		print(f"  pushing     : {len(items)} item(s), {len(boms)} BOM(s)\n")

		result = push.sync_records(items=items, boms=boms, trigger="Dry Run", reference=source)

		print("  result      :", json.dumps(result or {}))
		print(f"  created     : {[(n, f'{k} fields') for n, k in recorder.created]}")
		print(f"  updated     : {recorder.updated}")
		print(f"  uploads     : {len(recorder.uploads)} file(s)")
		print(
			f"  unknown keys: {sorted(set(recorder.rejected_keys)) or 'none'}"
			"   <- must be none; anything here would be rejected by real KGGK"
		)
		print("\n--- migration log ---")
		print(frappe.db.get_single_value(SETTINGS, "sync_log") or "(empty)")
		print(
			"\nNothing was changed permanently. This mock accepts what real KGGK may reject —\n"
			"do one real run before switching Is Migrate on."
		)
		return result
	finally:
		server.shutdown()
		# Undo the sync markers and log the push wrote.
		frappe.db.rollback()
		frappe.db.set_single_value(
			SETTINGS, {field: saved.get(field) for field in _RESTORE_FIELDS}, update_modified=False
		)
		frappe.db.commit()
		frappe.clear_cache()
