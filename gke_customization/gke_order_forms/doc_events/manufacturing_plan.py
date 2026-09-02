"""Push a submitted Manufacturing Plan's items and BOMs to the KGGK testing site.

Only subcontracting rows, and the BOM taken is ``manufacturing_bom`` - the one
``ManufacturingPlan.on_submit`` and ``fetch_fg_purchase_rate`` work off for subcontracting,
and the one the plan makes mandatory on a subcontracting row. ``row.bom`` is the Sales Order
BOM and is the wrong one here.

This is a testing flow. It reads the Testing Site settings and never touches the live
Item/BOM sync in ``doc_events/item.py``, which keeps pushing to ``to_site`` on its own hooks.
"""

import frappe
from frappe import _
from frappe.utils import cint

from gke_customization.gke_order_forms.doc_events.kggk_sync.config import get_sync_config
from gke_customization.gke_order_forms.doc_events.kggk_sync.log import log_skip
from gke_customization.gke_order_forms.doc_events.kggk_sync.push import enqueue_sync, sync_records


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


@frappe.whitelist()
def sync_plan(plan_name):
	"""Manual re-push of every subcontracting row, from the button on the plan form.

	Unconditional: there are no sync markers, so there is no such thing as "only the ones
	that have not gone yet", and the target decides what is a create and what is an update.

	The switch is re-read here rather than trusted from the button being visible, so a form
	left open since before someone turned the sync off cannot still push.
	"""
	doc = frappe.get_doc("Manufacturing Plan", plan_name)
	doc.check_permission("read")

	if doc.docstatus != 1:
		frappe.throw(_("Only a submitted Manufacturing Plan can be pushed."))

	config, reason = get_sync_config()
	if not config:
		frappe.throw(_(reason), title=_("Testing Sync Not Available"))

	items, boms = collect_records(doc)
	if not items and not boms:
		return {"queued": False, "message": _("This plan has no subcontracting rows.")}

	# Not the submit job_id: with deduplicate=True, pressing the button while the
	# submit-triggered job is still queued would make enqueue silently drop this one while
	# the user is told it was queued.
	queued = enqueue_sync(
		items=items,
		boms=boms,
		trigger="Manufacturing Plan",
		reference=doc.name,
		job_id=f"kggk_plan::{doc.name}::{frappe.generate_hash(length=6)}",
	)
	if not queued:
		return {
			"queued": False,
			"message": _("Nothing was queued - a push is already running for this plan."),
		}

	return {
		"queued": True,
		"items": len(items),
		"boms": len(boms),
		"message": _("Queued {0} item(s) and {1} BOM(s) for the KGGK testing site.").format(
			len(items), len(boms)
		),
	}


@frappe.whitelist()
def is_testing_sync_enabled():
	"""Whether the form should offer the push button at all."""
	from gke_customization.gke_order_forms.doc_events.kggk_sync.config import is_sync_enabled

	return bool(is_sync_enabled())


def sync_plan_now(plan_name):
	"""Run the push inline. For ``bench execute`` and tests, not for a request."""
	doc = frappe.get_doc("Manufacturing Plan", plan_name)
	items, boms = collect_records(doc)
	return sync_records(items=items, boms=boms, trigger="Manufacturing Plan", reference=plan_name)
