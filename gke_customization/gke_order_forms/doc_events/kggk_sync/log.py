"""Run state for the Manufacturing Plan -> KGGK testing push.

Nothing is persisted on this site. Counters live for the length of one chunk and travel to
the next one in the job's kwargs, so there is no settings field to read back and no row to
go stale. The one durable artefact is a single Error Log written on the *target*, because
the fields and master records it is missing are the target's to fix.

A clean run writes nothing at all. An Error Log per plan submit saying "nothing went wrong"
is exactly the noise that stops people reading Error Logs.
"""

import frappe
from frappe.utils import now_datetime

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
			from . import client

			if not self.config:
				raise ValueError("no target configuration")

			# reference_doctype is deliberately left unset: it is a Link to DocType, and if
			# the target has no "Manufacturing Plan" the POST fails validation and the whole
			# report is lost over a decoration.
			response = client.post(
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
