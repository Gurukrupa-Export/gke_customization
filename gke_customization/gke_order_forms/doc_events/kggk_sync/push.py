"""The single push pipeline. Every trigger - hooks, the manual button, Manufacturing Plan
submit - comes through here, so there is one behaviour to reason about and one to fix.
"""

import frappe

from . import client, files, payload as payload_builder
from .config import get_sync_config, in_reentrant_context
from .log import SyncRun, log_skip

# Fields that identify a record and cannot be changed on an existing one.
IMMUTABLE_ON_UPDATE = {"Item": {"variant_of", "item_code"}, "BOM": {"item"}}

def _link_exists(config, doctype, value, cache):
	key = (doctype, value)
	if key not in cache:
		cache[key] = client.exists(config, doctype, value)
	return cache[key]


def _strip_missing_links(config, doc, data, run, cache):
	"""Drop optional Link values the target does not have; refuse on essential ones.

	Dropping an optional link - one Item Category, one Sizer Type - keeps the record
	syncing instead of failing whole on a single absent master. Dropping a mandatory one
	would create a broken record on the target, so that blocks the push instead.

	Returns a list of blocking problems; empty means it is safe to send.
	"""
	blocking = []
	for fieldname, (link_doctype, essential) in payload_builder.link_fields(doc.doctype).items():
		value = data.get(fieldname)
		if not value:
			continue
		found = _link_exists(config, link_doctype, value, cache)
		if found is None:
			# The check itself failed - a timeout, a 500, a 403. Treating that as "it is
			# there" sends the value anyway and the target rejects the whole record with a
			# message that blames something else entirely.
			run.mismatch(
				doc.doctype,
				doc.name,
				f"{fieldname}: could not check whether {link_doctype} '{value}' exists on "
				"target, sending it anyway",
				kind="LINK-UNKNOWN",
				once_key=f"linkcheck::{link_doctype}",
			)
			continue
		if found:
			continue
		if essential:
			blocking.append(f"{fieldname}: {link_doctype} '{value}' does not exist on target")
			continue
		data.pop(fieldname, None)
		run.mismatch(
			doc.doctype,
			doc.name,
			f"{fieldname}: {link_doctype} '{value}' does not exist on target, field dropped",
			kind="LINK-MISSING",
		)
	return blocking


def _send(config, doctype, name, data):
	"""PUT the existing record, POST a new one if the target has never seen it."""
	path = f"/api/resource/{client.segment(doctype)}/{client.segment(name)}"
	update_data = {
		k: v for k, v in data.items() if k not in IMMUTABLE_ON_UPDATE.get(doctype, set())
	}
	response = client.put(config, path, json=update_data)
	if response.not_found:
		response = client.post(config, f"/api/resource/{client.segment(doctype)}", json=data)
		return response, "created"
	return response, "updated"


def push_item(item_code, config, run, seen=None):
	"""Create or update one Item on the target, attachments included."""
	seen = seen if seen is not None else set()
	if item_code in seen:
		return True
	seen.add(item_code)

	if not frappe.db.exists("Item", item_code):
		run.item_failed(item_code, "item does not exist on this site")
		return False

	doc = frappe.get_doc("Item", item_code)

	# A variant cannot be created before its template exists on the target.
	if doc.get("variant_of"):
		template = doc.variant_of
		if client.exists(config, "Item", template) is False:
			run.line("INFO", "Item", item_code, f"template {template} missing on target, pushing it first")
			run.items_total += 1
			push_item(template, config, run, seen=seen)

	allowed = payload_builder.get_target_fields(config, "Item", run=run)
	data, attachments = payload_builder.build_payload(doc, allowed, run=run)
	blocking = _strip_missing_links(config, doc, data, run, run.link_cache)
	if blocking:
		message = "required master(s) missing on target - " + "; ".join(blocking)
		run.item_failed(item_code, message)
		return False

	response, action = _send(config, "Item", item_code, data)
	if not response.ok:
		message = response.message()
		run.item_failed(item_code, message)
		return False

	note = action
	if attachments:
		resolved = files.upload_all(config, attachments, "Item", item_code, run=run)
		if resolved:
			follow_up = client.put(
				config, f"/api/resource/Item/{client.segment(item_code)}", json=resolved
			)
			if follow_up.ok:
				note = f"{action}, {len(resolved)} attachment(s)"
			else:
				run.mismatch(
					"Item", item_code, f"attachment urls could not be set - {follow_up.message()}"
				)
				note = f"{action}, attachments uploaded but not linked"

	run.item_ok(item_code, note)
	return True


def push_bom(bom_name, config, run):
	"""Create or update one BOM on the target, attachments included."""
	if not frappe.db.exists("BOM", bom_name):
		run.bom_failed(bom_name, "BOM does not exist on this site")
		return False

	doc = frappe.get_doc("BOM", bom_name)

	# A BOM cannot validate on the target without its finished-goods item. Batches are
	# assembled from Items and BOMs independently - "Sync Now" takes the oldest unsynced of
	# each - so the item a given BOM needs is very often not in the same batch. Pull it in
	# rather than failing the BOM for a reason the operator cannot act on.
	if doc.get("item") and client.exists(config, "Item", doc.item) is False:
		run.line("INFO", "BOM", bom_name, f"item {doc.item} missing on target, pushing it first")
		run.items_total += 1
		push_item(doc.item, config, run)

	allowed = payload_builder.get_target_fields(config, "BOM", run=run)
	data, attachments = payload_builder.build_payload(doc, allowed, run=run)
	blocking = _strip_missing_links(config, doc, data, run, run.link_cache)
	if blocking:
		message = "required master(s) missing on target - " + "; ".join(blocking)
		run.bom_failed(bom_name, message)
		return False

	response, action = _send(config, "BOM", bom_name, data)
	if not response.ok:
		message = response.message()
		run.bom_failed(bom_name, message)
		return False

	note = action
	if attachments:
		resolved = files.upload_all(config, attachments, "BOM", bom_name, run=run)
		if resolved:
			follow_up = client.put(config, f"/api/resource/BOM/{client.segment(bom_name)}", json=resolved)
			if follow_up.ok:
				note = f"{action}, {len(resolved)} attachment(s)"
			else:
				run.mismatch("BOM", bom_name, f"attachment urls could not be set - {follow_up.message()}")

	run.bom_ok(bom_name, note)
	return True


# One Manufacturing Plan can carry hundreds of distinct items - a real plan on this site
# selects 490 items and 490 BOMs. Pushing 980 records in a single job would run for the
# better part of an hour, exceed the job timeout, and lose the whole run's progress. Work
# is processed a chunk at a time and the remainder re-queued, so a run makes durable
# progress and a timeout costs one chunk instead of everything.
CHUNK_SIZE = 50
JOB_TIMEOUT = 3600


def sync_records(
	items=None,
	boms=None,
	trigger="Manual",
	reference=None,
	totals=None,
	counters=None,
	chunk_index=0,
	run_id=None,
):
	"""Push a batch of Items and BOMs. The one entry point every trigger calls.

	Items go first, across chunks as well as within one: a BOM whose finished-goods item
	does not exist on the target cannot validate there. Each record is wrapped in a
	savepoint so one bad row cannot take the rest of the chunk down with it.
	"""
	items = list(dict.fromkeys(items or []))
	boms = list(dict.fromkeys(boms or []))

	if in_reentrant_context():
		log_skip("push suppressed: already inside a sync or a bulk operation")
		return None

	config, reason = get_sync_config()
	if not config:
		log_skip(reason)
		return None

	if not items and not boms:
		return None

	if totals is None:
		totals = {"items": len(items), "boms": len(boms)}

	# Items first, then BOMs, filling one chunk.
	batch_items = items[:CHUNK_SIZE]
	rest_items = items[len(batch_items) :]
	bom_budget = max(CHUNK_SIZE - len(batch_items), 0)
	batch_boms = boms[:bom_budget]
	rest_boms = boms[len(batch_boms) :]

	run = SyncRun(
		trigger=trigger,
		reference=reference,
		config=config,
		counters=counters,
		chunk_index=chunk_index,
	)
	run.items_total = int(totals.get("items") or 0)
	run.boms_total = int(totals.get("boms") or 0)
	if rest_items or rest_boms:
		run.line(
			"INFO",
			None,
			None,
			f"chunk {chunk_index + 1}: {len(batch_items)} item(s), {len(batch_boms)} BOM(s); "
			f"{len(rest_items)} item(s) and {len(rest_boms)} BOM(s) still queued",
		)

	items, boms = batch_items, batch_boms

	frappe.flags.in_kggk_sync = True
	reported = False
	try:
		seen = set()
		for item_code in items:
			frappe.db.savepoint("kggk_item")
			try:
				push_item(item_code, config, run, seen=seen)
			except Exception as exc:
				frappe.db.rollback(save_point="kggk_item")
				run.item_failed(item_code, f"unexpected error: {exc}")
				frappe.log_error(frappe.get_traceback(), f"KGGK sync: Item {item_code}"[:140])

		for bom_name in boms:
			frappe.db.savepoint("kggk_bom")
			try:
				push_bom(bom_name, config, run)
			except Exception as exc:
				frappe.db.rollback(save_point="kggk_bom")
				run.bom_failed(bom_name, f"unexpected error: {exc}")
				frappe.log_error(frappe.get_traceback(), f"KGGK sync: BOM {bom_name}"[:140])

		# Reached only if the loops ran to completion; the reporting below then owns it.
		reported = True
	finally:
		frappe.flags.in_kggk_sync = False
		if not reported:
			# A chunk killed by the job timeout, or one that raised on its way out, still
			# reports what it learned. Silence here would look exactly like a clean run.
			run.report()

	if rest_items or rest_boms:
		frappe.db.commit()
		# Hand the remainder to a fresh job. A distinct job_id per chunk is required:
		# deduplicate=True would otherwise reject the continuation, because the job queueing
		# it is itself still running under the base id. `run_id` is in the id too, so
		# re-pushing the same plan cannot collide with a chunk still pending from the
		# previous run and be silently dropped.
		frappe.enqueue(
			"gke_customization.gke_order_forms.doc_events.kggk_sync.push.sync_records",
			queue="long",
			timeout=JOB_TIMEOUT,
			job_id=f"kggk_sync::{run_id or reference or trigger}::chunk{chunk_index + 1}",
			deduplicate=True,
			items=rest_items,
			boms=rest_boms,
			trigger=trigger,
			reference=reference,
			totals=totals,
			counters=run.counters(),
			chunk_index=chunk_index + 1,
			run_id=run_id,
		)
		return {
			"status": "Running",
			**run.counters(),
			"remaining": len(rest_items) + len(rest_boms),
		}

	status = run.finish()
	return {"status": status, **run.counters()}


def enqueue_sync(items=None, boms=None, trigger="Manual", reference=None, job_id=None):
	"""Queue a batch. Never blocks the save or submit that asked for it."""
	items = list(dict.fromkeys(items or []))
	boms = list(dict.fromkeys(boms or []))
	if not items and not boms:
		return False

	if in_reentrant_context():
		return False

	config, reason = get_sync_config()
	if not config:
		log_skip(reason)
		return False

	frappe.enqueue(
		"gke_customization.gke_order_forms.doc_events.kggk_sync.push.sync_records",
		queue="long",
		timeout=JOB_TIMEOUT,
		enqueue_after_commit=True,
		job_id=job_id or f"kggk_sync::{trigger}::{reference or ''}",
		deduplicate=True,
		items=items,
		boms=boms,
		trigger=trigger,
		reference=reference,
		run_id=frappe.generate_hash(length=8),
	)
	return True
