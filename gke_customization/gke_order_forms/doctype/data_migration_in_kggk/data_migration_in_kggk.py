# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from gke_customization.gke_order_forms.doc_events.kggk_sync import log as sync_log
from gke_customization.gke_order_forms.doc_events.kggk_sync import selectors
from gke_customization.gke_order_forms.doc_events.kggk_sync.config import (
	get_sync_config,
	host_of,
)

ACTIVE_STATUSES = ("Queued", "Running")


class DataMigrationinKGGK(Document):
	def validate(self):
		self._warn_on_same_site()

	def _warn_on_same_site(self):
		"""Say so on screen, at the moment it is configured, rather than silently later."""
		if not (self.from_site and self.to_site):
			return
		if host_of(self.from_site) == host_of(self.to_site):
			frappe.msgprint(
				_(
					"From Site and To Site point at the same site ({0}). Nothing will be synced "
					"while this is the case - a site is never allowed to push into itself."
				).format(frappe.bold(host_of(self.to_site))),
				title=_("Same Site Configured"),
				indicator="red",
			)

	# -- actions -----------------------------------------------------------------

	@frappe.whitelist()
	def sync_now(self, limit=200):
		"""Queue a push of Items and BOMs that have never synced.

		Bounded on purpose. A site with 40,000 unsynced items should drain in deliberate
		batches, not in one job that holds a worker for an hour.
		"""
		_require_system_manager()
		self._require_idle()
		config, reason = get_sync_config()
		if not config:
			frappe.throw(_(reason), title=_("Sync Not Configured"))

		limit = cint(limit) or 200
		items = selectors.unsynced_items(limit=limit)
		boms = selectors.unsynced_boms(limit=limit)

		if not items and not boms:
			frappe.msgprint(_("Nothing to sync - no unsynced Items or BOMs found."), alert=True)
			return {"queued": False}

		return self._queue(items, boms, "Manual", f"Sync Now (limit {limit})")

	@frappe.whitelist()
	def retry_failed(self):
		"""Re-push only what failed in the last run."""
		_require_system_manager()
		self._require_idle()
		config, reason = get_sync_config()
		if not config:
			frappe.throw(_(reason), title=_("Sync Not Configured"))

		records = sync_log.get_failed_records()
		items = [r["name"] for r in records if r.get("doctype") == "Item"]
		boms = [r["name"] for r in records if r.get("doctype") == "BOM"]

		if not items and not boms:
			frappe.msgprint(_("There are no failed records to retry."), alert=True)
			return {"queued": False}

		return self._queue(items, boms, "Manual", "Retry Failed")

	@frappe.whitelist()
	def start_resync(self, since, limit=500):
		"""Re-push everything in scope modified on or after a date.

		Named `start_resync`, not `resync_since`: a Date field of that name already exists
		on this doctype, and a stored field value shadows a method of the same name on the
		Document. (A Button field does not - it stores nothing - which is why the Sync Now
		button can share its name with `sync_now`.)

		The backfill path: after a spell where the sync was off, or after fixing a master
		on the target, this pulls the affected window through again without anyone
		un-ticking Is Synced on hundreds of records by hand.
		"""
		_require_system_manager()
		self._require_idle()
		config, reason = get_sync_config()
		if not config:
			frappe.throw(_(reason), title=_("Sync Not Configured"))

		if not since:
			frappe.throw(_("Pick a date to re-sync from."))

		limit = cint(limit) or 500
		items = selectors.unsynced_items(limit=limit, since=since)
		boms = selectors.unsynced_boms(limit=limit, since=since)

		if not items and not boms:
			frappe.msgprint(
				_("Nothing modified since {0} needs syncing.").format(frappe.format(since, "Date")),
				alert=True,
			)
			return {"queued": False}

		return self._queue(items, boms, "Manual", f"Re-sync since {since}")

	@frappe.whitelist()
	def clear_log(self):
		_require_system_manager()
		frappe.db.set_single_value(
			self.doctype, {"sync_log": "", "last_error": ""}, update_modified=False
		)
		return {"cleared": True}

	# -- helpers -----------------------------------------------------------------

	def _require_idle(self):
		if self.sync_status in ACTIVE_STATUSES:
			frappe.throw(
				_("A sync is already {0}. Wait for it to finish.").format(self.sync_status.lower()),
				title=_("Sync In Progress"),
			)

	def _queue(self, items, boms, trigger, reference):
		from gke_customization.gke_order_forms.doc_events.kggk_sync.push import enqueue_sync

		frappe.db.set_single_value(
			self.doctype,
			{"sync_status": "Queued", "last_trigger": trigger, "last_reference": reference},
			update_modified=False,
		)
		enqueue_sync(
			items=items,
			boms=boms,
			trigger=trigger,
			reference=reference,
			job_id="kggk_manual_sync",
		)
		frappe.msgprint(
			_("Queued {0} item(s) and {1} BOM(s). Progress appears above as the job runs.").format(
				len(items), len(boms)
			),
			alert=True,
		)
		return {"queued": True, "items": len(items), "boms": len(boms)}


def _require_system_manager():
	if "System Manager" not in frappe.get_roles():
		frappe.throw(_("Only System Manager can start a KGGK sync."), frappe.PermissionError)


@frappe.whitelist()
def get_sync_progress():
	"""Polled by the form while a run is active."""
	return sync_log.get_progress()
