"""Push a submitted Manufacturing Plan's items and BOMs to the KGGK site.

Only subcontracting rows are pushed, and the BOM taken is ``manufacturing_bom`` - the one
``ManufacturingPlan.on_submit`` and ``fetch_fg_purchase_rate`` actually work off for
subcontracting. ``row.bom`` is the Sales Order BOM and is the wrong one here.
"""

import frappe
from frappe import _
from frappe.utils import cint

from gke_customization.gke_order_forms.doc_events.kggk_sync.config import get_sync_config
from gke_customization.gke_order_forms.doc_events.kggk_sync.log import log_skip
from gke_customization.gke_order_forms.doc_events.kggk_sync.push import enqueue_sync, sync_records
from gke_customization.gke_order_forms.doc_events.kggk_sync.selectors import is_synced


def collect_records(doc, only_unsynced=True):
	"""Return ``(items, boms)`` for the subcontracting rows of a Manufacturing Plan."""
	items = []
	boms = []

	for row in doc.get("manufacturing_plan_table") or []:
		if not cint(row.get("subcontracting")):
			continue

		item_code = row.get("item_code")
		if item_code and item_code not in items:
			if not (only_unsynced and is_synced("Item", item_code)):
				items.append(item_code)

		bom_name = row.get("manufacturing_bom") or row.get("bom")
		if bom_name and bom_name not in boms:
			if not (only_unsynced and is_synced("BOM", bom_name)):
				boms.append(bom_name)

	return items, boms


def on_submit(doc, method=None):
	"""Queue the push. Submitting must never be slowed or blocked by the sync."""
	config, reason = get_sync_config()
	if not config:
		log_skip(reason, "Manufacturing Plan", doc.name)
		return

	items, boms = collect_records(doc)
	if not items and not boms:
		return

	enqueue_sync(
		items=items,
		boms=boms,
		trigger="Manufacturing Plan",
		reference=doc.name,
		job_id=f"kggk_plan::{doc.name}",
	)


@frappe.whitelist()
def sync_plan(plan_name, only_unsynced=1):
	"""Manual re-push for one plan, from the button on the Manufacturing Plan form."""
	doc = frappe.get_doc("Manufacturing Plan", plan_name)
	doc.check_permission("read")

	config, reason = get_sync_config()
	if not config:
		frappe.throw(_(reason), title=_("Sync Not Configured"))

	items, boms = collect_records(doc, only_unsynced=cint(only_unsynced))
	if not items and not boms:
		return {"queued": False, "message": _("Nothing to sync - every subcontracting row is already synced.")}

	enqueue_sync(
		items=items,
		boms=boms,
		trigger="Manufacturing Plan",
		reference=doc.name,
		job_id=f"kggk_plan::{doc.name}",
	)
	return {
		"queued": True,
		"items": len(items),
		"boms": len(boms),
		"message": _("Queued {0} item(s) and {1} BOM(s) for sync to KGGK.").format(len(items), len(boms)),
	}


@frappe.whitelist()
def get_plan_sync_status(plan_name):
	"""Counts for the indicator on the Manufacturing Plan form."""
	doc = frappe.get_doc("Manufacturing Plan", plan_name)
	doc.check_permission("read")

	all_items, all_boms = collect_records(doc, only_unsynced=False)
	pending_items, pending_boms = collect_records(doc, only_unsynced=True)

	return {
		"total_items": len(all_items),
		"synced_items": len(all_items) - len(pending_items),
		"total_boms": len(all_boms),
		"synced_boms": len(all_boms) - len(pending_boms),
		"has_rows": bool(all_items or all_boms),
	}


def sync_plan_now(plan_name, only_unsynced=True):
	"""Run the push inline. For `bench execute` and tests, not for a request."""
	doc = frappe.get_doc("Manufacturing Plan", plan_name)
	items, boms = collect_records(doc, only_unsynced=only_unsynced)
	return sync_records(items=items, boms=boms, trigger="Manufacturing Plan", reference=plan_name)
