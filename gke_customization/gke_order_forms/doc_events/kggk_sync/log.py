"""Run state and logging for the KGGK sync.

Everything the operator sees lives on the existing **Data Migration in KGGK** Single -
status, counters, and a plain-text log. No log doctype is created.
"""

import json

import frappe
from frappe.utils import cint, now_datetime

from .config import SETTINGS

# Keep the tail of the log. Old lines are dropped from the front so the field cannot grow
# without bound on a site that syncs thousands of items a day.
MAX_LOG_CHARS = 200_000

STATUS_IDLE = "Idle"
STATUS_QUEUED = "Queued"
STATUS_RUNNING = "Running"
STATUS_COMPLETED = "Completed"
STATUS_PARTIAL = "Partially Completed"
STATUS_FAILED = "Failed"


def _stamp():
	return now_datetime().strftime("%Y-%m-%d %H:%M:%S")


def _set(values, allow_commit=False):
	"""Write settings fields without touching `modified`, so a run never looks like an edit."""
	try:
		# set_single_value, not set_value: the latter is deprecated for Single doctypes.
		frappe.db.set_single_value(SETTINGS, values, update_modified=False)
		if allow_commit:
			frappe.db.commit()
	except Exception:
		frappe.logger("kggk_sync").exception("failed writing sync state")


def append_log(lines, allow_commit=False):
	"""Append lines to the settings log field, trimmed to the newest MAX_LOG_CHARS."""
	if not lines:
		return
	try:
		existing = frappe.db.get_single_value(SETTINGS, "sync_log") or ""
		text = existing + ("\n" if existing else "") + "\n".join(lines)
		if len(text) > MAX_LOG_CHARS:
			text = text[-MAX_LOG_CHARS:]
			# Do not leave a half line at the top.
			cut = text.find("\n")
			if cut != -1:
				text = text[cut + 1 :]
			text = "... earlier lines trimmed ...\n" + text
		_set({"sync_log": text}, allow_commit=allow_commit)
	except Exception:
		frappe.logger("kggk_sync").exception("failed appending to sync log")


def log_skip(reason, doctype=None, name=None):
	"""Record a refused push. Used by the guards, which run outside a SyncRun."""
	line = f"{_stamp()} | SKIP     | {doctype or '-'} | {name or '-'} | {reason}"
	frappe.logger("kggk_sync").info(line)
	append_log([line])


class SyncRun:
	"""One sync run: counters, a log buffer, and the status the operator sees.

	Flushes every ``flush_every`` records rather than only at the end, so the progress
	panel actually moves during a long run instead of jumping from 0 to done.
	"""

	def __init__(self, trigger="Manual", reference=None, allow_commit=None, flush_every=5, resume=False):
		self.trigger = trigger
		self.reference = reference or ""
		# A large batch is processed in chunks across several jobs. A resuming chunk must
		# carry the running totals forward instead of restarting them at zero.
		self.resume = resume
		self.flush_every = flush_every
		# Committing mid-request would commit whatever else the request has touched. Only
		# the background worker, which owns its transaction, is allowed to.
		self.allow_commit = (
			bool(frappe.flags.get("in_background_job"))
			if allow_commit is None
			else allow_commit
		)
		self.buffer = []
		self._since_flush = 0
		self.items_total = self.items_synced = self.items_failed = self.items_skipped = 0
		self.boms_total = self.boms_synced = self.boms_failed = 0
		self.mismatches = 0
		self.failed_records = []
		self.last_error = ""
		# "does this master exist on the target" answers, reused across the whole run so a
		# batch of 200 items does not re-ask about the same Item Group 200 times.
		self.link_cache = {}

	# -- lifecycle ---------------------------------------------------------------

	def start(self):
		if self.resume:
			self._load_counters()
			_set({"sync_status": STATUS_RUNNING}, allow_commit=self.allow_commit)
			return self

		self.line("INFO", None, None, f"=== sync started ({self.trigger} {self.reference}) ===".strip())
		_set(
			{
				"sync_status": STATUS_RUNNING,
				"last_run_started_on": now_datetime(),
				"last_run_completed_on": None,
				"last_trigger": self.trigger,
				"last_reference": self.reference,
				"last_error": "",
				"total_items": 0,
				"items_synced": 0,
				"items_failed": 0,
				"items_skipped": 0,
				"total_boms": 0,
				"boms_synced": 0,
				"boms_failed": 0,
				"field_mismatches": 0,
			},
			allow_commit=self.allow_commit,
		)
		return self

	def _load_counters(self):
		row = frappe.db.get_value(
			SETTINGS,
			SETTINGS,
			[
				"items_synced",
				"items_failed",
				"items_skipped",
				"boms_synced",
				"boms_failed",
				"field_mismatches",
				"last_error",
			],
			as_dict=True,
		) or frappe._dict()
		self.items_synced = cint(row.get("items_synced"))
		self.items_failed = cint(row.get("items_failed"))
		self.items_skipped = cint(row.get("items_skipped"))
		self.boms_synced = cint(row.get("boms_synced"))
		self.boms_failed = cint(row.get("boms_failed"))
		self.mismatches = cint(row.get("field_mismatches"))
		self.last_error = row.get("last_error") or ""
		self.failed_records = get_failed_records()

	def finish(self, status=None):
		if status is None:
			if self.items_failed or self.boms_failed:
				status = STATUS_PARTIAL if (self.items_synced or self.boms_synced) else STATUS_FAILED
			else:
				status = STATUS_COMPLETED
		self.line(
			"INFO",
			None,
			None,
			f"=== sync finished: {status} | items {self.items_synced}/{self.items_total} "
			f"synced, {self.items_failed} failed, {self.items_skipped} already synced | "
			f"BOMs {self.boms_synced}/{self.boms_total} synced, {self.boms_failed} failed | "
			f"{self.mismatches} field mismatches ===",
		)
		self.flush(force=True, extra={
			"sync_status": status,
			"last_run_completed_on": now_datetime(),
			"failed_records": json.dumps(self.failed_records[:500]),
		})
		return status

	# -- logging -----------------------------------------------------------------

	def line(self, level, doctype, name, message):
		text = f"{_stamp()} | {level:<8} | {doctype or '-'} | {name or '-'} | {message}"
		self.buffer.append(text)
		frappe.logger("kggk_sync").info(text)

	def mismatch(self, doctype, name, message):
		"""A field that could not be written to the target. The reason the log exists."""
		self.mismatches += 1
		self.line("MISMATCH", doctype, name, message)

	# -- outcomes ----------------------------------------------------------------

	def item_ok(self, name, note=""):
		self.items_synced += 1
		self.line("OK", "Item", name, note or "synced")
		self._tick()

	def item_failed(self, name, message):
		self.items_failed += 1
		self.last_error = f"Item {name}: {message}"[:1000]
		self.failed_records.append({"doctype": "Item", "name": name, "error": str(message)[:500]})
		self.line("FAILED", "Item", name, message)
		self._tick()

	def item_skipped(self, name, message):
		self.items_skipped += 1
		self.line("SKIP", "Item", name, message)
		self._tick()

	def bom_ok(self, name, note=""):
		self.boms_synced += 1
		self.line("OK", "BOM", name, note or "synced")
		self._tick()

	def bom_failed(self, name, message):
		self.boms_failed += 1
		self.last_error = f"BOM {name}: {message}"[:1000]
		self.failed_records.append({"doctype": "BOM", "name": name, "error": str(message)[:500]})
		self.line("FAILED", "BOM", name, message)
		self._tick()

	# -- flushing ----------------------------------------------------------------

	def _tick(self):
		self._since_flush += 1
		if self._since_flush >= self.flush_every:
			self.flush()

	def flush(self, force=False, extra=None):
		if not force and not self.buffer and not self._since_flush:
			return
		self._since_flush = 0
		values = {
			"total_items": self.items_total,
			"items_synced": self.items_synced,
			"items_failed": self.items_failed,
			"items_skipped": self.items_skipped,
			"total_boms": self.boms_total,
			"boms_synced": self.boms_synced,
			"boms_failed": self.boms_failed,
			"field_mismatches": self.mismatches,
			"last_error": self.last_error,
		}
		if extra:
			values.update(extra)
		_set(values, allow_commit=self.allow_commit)
		if self.buffer:
			append_log(self.buffer, allow_commit=self.allow_commit)
			self.buffer = []


def get_failed_records():
	raw = frappe.db.get_single_value(SETTINGS, "failed_records")
	if not raw:
		return []
	try:
		return json.loads(raw)
	except Exception:
		return []


def get_progress():
	"""Counters for the form's progress panel."""
	row = frappe.db.get_value(
		SETTINGS,
		SETTINGS,
		[
			"sync_status",
			"last_run_started_on",
			"last_run_completed_on",
			"last_trigger",
			"last_reference",
			"total_items",
			"items_synced",
			"items_failed",
			"items_skipped",
			"total_boms",
			"boms_synced",
			"boms_failed",
			"field_mismatches",
			"last_error",
		],
		as_dict=True,
	) or frappe._dict()

	# Single doctypes store every value as text, so counters come back as strings. Cast
	# once here rather than leaving every consumer to remember.
	for field in (
		"total_items",
		"items_synced",
		"items_failed",
		"items_skipped",
		"total_boms",
		"boms_synced",
		"boms_failed",
		"field_mismatches",
	):
		row[field] = cint(row.get(field))

	done = row["items_synced"] + row["items_failed"] + row["items_skipped"]
	done += row["boms_synced"] + row["boms_failed"]
	total = row["total_items"] + row["total_boms"]
	row["progress_percent"] = round(done * 100.0 / total, 1) if total else 0.0
	row["failed_count"] = len(get_failed_records())
	return row
