import json
import re

import frappe
from frappe.utils import add_months, cint, date_diff, get_first_day, getdate

from gke_customization.gke_catalog.report.product_development_to_production.product_development_to_production import (
	get_data as get_report_data,
)
from gke_customization.gke_catalog.report.cad_dashboard_script.cad_dashboard_script import (
	BUCKET_LABELS,
	REJECTED_STATES,
	_bucket_of,
)

CACHE_TTL = 600

# A CAD order's current workflow_state bucket implies how far along the
# (mostly) linear design pipeline it has travelled - used to build a
# cumulative "reached this stage or further" funnel from current state alone,
# since no stage-history is tracked. on_hold/rework variants are folded into
# the stage they're blocking/revisiting rather than getting their own rank.
CAD_STAGE_RANK = {
	"pending": 0,
	"assigned": 1,
	"assigned_on_hold": 1,
	"designing": 2,
	"designing_on_hold": 2,
	"rework": 2,
	"qc": 3,
	"approved": 4,
}


# Sketch Order workflow states shown in the Sketch Funnel: (stage key, label, state).
SKETCH_FUNNEL_STAGES = [
	("sketch_status_draft", "Draft", "Draft"),
	("sketch_status_assigned", "Assigned", "Assigned"),
	("sketch_status_customer_approval", "Customer Approval", "Customer Approval"),
	("sketch_status_update_item", "Update Item", "Update Item"),
]


def _sketch_orders_by_status(filters, state=None):
	"""Sketch Orders (not cancelled) in the date window, straight from
	`tabSketch Order` - the report rows only contain sketch orders that already
	have a final approval, so Draft/Assigned ones would never appear there."""
	conditions = ["so.docstatus != 2"]
	params = {}
	if state is None:
		conditions.append("so.workflow_state IN %(states)s")
		params["states"] = [st for _, _, st in SKETCH_FUNNEL_STAGES]
	else:
		conditions.append("so.workflow_state = %(state)s")
		params["state"] = state
	if filters.get("from_date"):
		conditions.append("so.order_date >= %(from_date)s")
		params["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("so.order_date <= %(to_date)s")
		params["to_date"] = filters["to_date"]
	likes = []
	for i, v in enumerate(_split_bulk_values(filters.get("sketch_order_no"))):
		params[f"sn{i}"] = f"%{v}%"
		likes.append(f"so.name LIKE %(sn{i})s")
	if likes:
		conditions.append("(" + " OR ".join(likes) + ")")
	return frappe.db.sql(
		f"""
		SELECT so.name AS sketch_order_no, so.workflow_state AS sketch_workflow_state,
			so.order_date AS sketch_order_date, so.customer_code AS customer,
			so.item_code AS item_code
		FROM `tabSketch Order` so
		WHERE {" AND ".join(conditions)}
		ORDER BY so.order_date DESC
		""",
		params,
		as_dict=True,
	)


def _parse_filters(filters):
	if isinstance(filters, str):
		return json.loads(filters) if filters else {}
	return filters or {}


def _date_filters(filters):
	"""Just the from_date/to_date - the only thing the (slow, external-API-
	backed) report query itself is filtered by. Keeping the cache key scoped
	to just these means the extra text filters (item code, sketch order no,
	...) never force a re-fetch - they're applied in-memory afterwards."""
	return {"from_date": filters.get("from_date"), "to_date": filters.get("to_date")}


def _cached_rows(filters):
	date_filters = _date_filters(filters)
	key = f"pdtp_dashboard_rows:{frappe.as_json(date_filters, indent=None)}"
	rows = frappe.cache().get_value(key, expires=True)
	if rows is None:
		rows = get_report_data(date_filters)
		frappe.cache().set_value(key, rows, expires_in_sec=CACHE_TTL)
	return rows


def _cad_orders_without_sketch(filters):
	"""CAD Orders (`tabOrder`, bom_or_cad='CAD') that have no Sketch Order behind
	them at all - these can never show up in `_cached_rows`/the Product
	Development To Production report, since that report's query always starts
	FROM Sketch Order and only ever reaches a CAD Order by joining onto one
	that already exists. So this is a separate, direct query over `tabOrder`
	instead of a filter over the report's own rows."""
	date_filters = _date_filters(filters)
	key = f"pdtp_dashboard_cad_without_sketch:{frappe.as_json(date_filters, indent=None)}"
	rows = frappe.cache().get_value(key, expires=True)
	if rows is not None:
		return rows

	conditions = ["o.bom_or_cad = 'CAD'", "o.docstatus != 2", "o.workflow_state != 'Cancelled'"]
	params = {}
	if date_filters.get("from_date"):
		conditions.append("o.order_date >= %(from_date)s")
		params["from_date"] = date_filters["from_date"]
	if date_filters.get("to_date"):
		conditions.append("o.order_date <= %(to_date)s")
		params["to_date"] = date_filters["to_date"]
	where = " AND ".join(conditions)

	rows = frappe.db.sql(
		f"""
		SELECT
			o.name AS cad_order_no,
			o.design_id AS item_code,
			o.order_date AS cad_order_date,
			o.workflow_state AS cad_workflow_state,
			o.customer_code AS customer
		FROM `tabOrder` o
		WHERE {where}
		ORDER BY o.order_date DESC
		""",
		params,
		as_dict=True,
	)

	# "Has a Sketch Order behind it" used to be a correlated NOT EXISTS with an
	# OR across a join - un-indexable (`design_id`/`item_code` have no index), so
	# it re-scanned for every CAD order (~75s). The set of designs that do have a
	# Sketch Order is small, so it is loaded once and checked in Python instead.
	# Lower-cased to match MariaDB's case-insensitive collation; NULL design_id
	# never matches (as in SQL), but '' does, exactly like the old query.
	sketch_designs = {
		(code or "").lower()
		for (code,) in frappe.db.sql(
			"SELECT item_code FROM `tabSketch Order` WHERE item_code IS NOT NULL"
		)
	}
	sketch_designs.update(
		(code or "").lower()
		for (code,) in frappe.db.sql(
			"""
			SELECT fsac.item
			FROM `tabFinal Sketch Approval CMO` fsac
			INNER JOIN `tabSketch Order` so ON so.name = fsac.parent
			WHERE fsac.parenttype = 'Sketch Order'
				AND fsac.parentfield = 'final_sketch_approval_cmo'
				AND fsac.item IS NOT NULL
			"""
		)
	)
	rows = [
		r for r in rows
		if r.get("item_code") is None or r["item_code"].lower() not in sketch_designs
	]
	for row in rows:
		row["cad_bucket"] = _bucket_of(row["cad_workflow_state"]) if row.get("cad_workflow_state") else None

	frappe.cache().set_value(key, rows, expires_in_sec=CACHE_TTL)
	return rows


def _sketch_order_completion_dates(sketch_order_nos):
	"""The month a Sketch Order is considered "completed" for the monthly
	chart is the month it got its item_code - but item_code is written via
	`frappe.db.set_value(...)` in `make_items()` (see Sketch Order's
	on_submit), which bypasses Frappe's change-tracking entirely, so there is
	no Version diff for the item_code field itself to look up (confirmed: zero
	such diffs exist in this instance's data).

	`make_items()` runs inside `on_submit()` though, so item_code is always
	generated in the same request that flips the Sketch Order's docstatus
	0 -> 1. That transition *is* a normal tracked save, so it shows up in
	Version history - this uses the earliest such transition as a stand-in
	for "item_code was generated". Falls back to the Sketch Order's own
	`creation` timestamp for the rare doc with no such Version entry (e.g.
	submitted before Version tracking was turned on, or version log purged)."""
	if not sketch_order_nos:
		return {}

	completion = {}
	version_rows = frappe.db.get_all(
		"Version",
		filters={"ref_doctype": "Sketch Order", "docname": ["in", sketch_order_nos]},
		fields=["docname", "creation", "data"],
		order_by="creation asc",
	)
	for v in version_rows:
		if v.docname in completion:
			continue
		try:
			data = json.loads(v.data) if v.data else {}
		except (TypeError, ValueError):
			continue
		for change in data.get("changed") or []:
			if len(change) >= 3 and change[0] == "docstatus" and change[1] in (0, "0") and change[2] in (1, "1"):
				completion[v.docname] = v.creation
				break

	missing = [name for name in sketch_order_nos if name not in completion]
	if missing:
		for d in frappe.db.get_all("Sketch Order", filters={"name": ["in", missing]}, fields=["name", "creation"]):
			completion[d.name] = d.creation

	return completion


def _split_bulk_values(value):
	"""Split a filter box's raw text into individual values - comma,
	semicolon, newline, or plain whitespace separated - so pasting a bulk
	list of codes (one per line, or comma-separated) works the same as
	typing a single value."""
	if not value:
		return []
	tokens = re.split(r"[,;\r\n]+|\s+", value.strip())
	return [t.strip().lower() for t in tokens if t.strip()]


def _apply_extra_filters(rows, filters):
	"""Cheap in-memory narrowing on top of the cached, date-filtered rows.
	Each bulk field matches a row if ANY of its pasted values is found
	(substring) in that row's field; different fields are AND-ed together."""
	bulk_filters = [
		(_split_bulk_values(filters.get("item_code")), "item_code"),
		(_split_bulk_values(filters.get("sketch_order_no")), "sketch_order_no"),
		(_split_bulk_values(filters.get("cad_order_no")), "cad_order_no"),
		(_split_bulk_values(filters.get("stylebio")), "stylebio"),
	]
	bulk_filters = [(values, field) for values, field in bulk_filters if values]

	tag_values = _split_bulk_values(filters.get("tag"))
	setting_type = (filters.get("setting_type") or "").strip().lower()

	if not bulk_filters and not tag_values and not setting_type:
		return rows

	def matches(row):
		for values, field in bulk_filters:
			field_value = (row.get(field) or "").lower()
			if not any(value in field_value for value in values):
				return False
		if tag_values:
			tag_value = (row.get("tag_nos") or "").lower()
			if not any(value in tag_value for value in tag_values):
				return False
		if setting_type and setting_type not in (row.get("setting_type") or "").lower():
			return False
		return True

	return [r for r in rows if matches(r)]


def _rows_with_cad_status(filters, include_cancelled=False):
	"""Report rows enriched with the linked CAD Order's workflow_state/bucket,
	reusing the exact bucketing used by the CAD Order Dashboard so "received"
	means the same thing across both pages.

	Cancelled CAD Orders are ignored unless `include_cancelled` is set - only
	the CAD Order funnel (and its drill-downs) counts them."""
	rows = _cached_rows(filters)
	rows = _apply_extra_filters(rows, filters)

	cad_names = list({row.get("cad_order_no") for row in rows if row.get("cad_order_no")})
	status_map = {}
	cancelled_cads = set()
	if cad_names:
		for d in frappe.db.get_all(
			"Order", filters={"name": ["in", cad_names]}, fields=["name", "workflow_state", "docstatus"]
		):
			status_map[d.name] = d.workflow_state
			if d.workflow_state == "Cancelled" or d.docstatus == 2:
				cancelled_cads.add(d.name)

	if cancelled_cads and not include_cancelled:
		# Cancelled CAD Orders are ignored entirely. Rows are (sketch order,
		# CAD order) pairs, so a design whose only CAD order was cancelled must
		# stay (as a design with no CAD yet) rather than vanish; if the design
		# also has another, live CAD order, the cancelled pair is just dropped.
		def design_key(r):
			return (r.get("sketch_order_no"), r.get("item_code"))

		live_designs = {
			design_key(r)
			for r in rows
			if not r.get("cad_order_no") or r["cad_order_no"] not in cancelled_cads
		}
		kept, seen_unlinked = [], set()
		for r in rows:
			if r.get("cad_order_no") not in cancelled_cads:
				kept.append(r)
				continue
			key = design_key(r)
			if key in live_designs or key in seen_unlinked:
				continue
			seen_unlinked.add(key)
			r["cad_order_no"] = None
			r["cad_order_date"] = None
			# CAD *was* placed (then cancelled), so this isn't a "CAD not placed" blocker.
			r["cad_cancelled_only"] = True
			kept.append(r)
		rows = kept

	for row in rows:
		cad_no = row.get("cad_order_no")
		state = status_map.get(cad_no) if cad_no else None
		row["cad_workflow_state"] = state
		row["cad_bucket"] = _bucket_of(state) if state else None

	sketch_names = list({row.get("sketch_order_no") for row in rows if row.get("sketch_order_no")})
	sketch_state_map = {}
	if sketch_names:
		sketch_state_map = {
			d.name: d.workflow_state
			for d in frappe.db.get_all(
				"Sketch Order", filters={"name": ["in", sketch_names]}, fields=["name", "workflow_state"]
			)
		}

	for row in rows:
		sketch_no = row.get("sketch_order_no")
		row["sketch_workflow_state"] = sketch_state_map.get(sketch_no) if sketch_no else None

	return rows


def _matches_stage(row, stage):
	if stage == "cad_raised":
		return bool(row.get("cad_order_no"))
	if stage == "cad_pending":
		# Sketch approved but no CAD order placed against it yet, and no
		# StyleBio either (both must be blank).
		return not row.get("cad_order_no") and not row.get("stylebio") and not row.get("cad_cancelled_only")
	if stage == "cad_not_received":
		# CAD order placed, but the design hasn't come back approved yet.
		return bool(row.get("cad_order_no")) and row.get("cad_bucket") not in ("approved", None) and row.get(
			"cad_workflow_state"
		) not in REJECTED_STATES
	if stage == "cataloged":
		return bool(row.get("entry_date"))
	if stage == "tagged":
		return bool(row.get("first_tag_date"))
	if stage == "sold":
		return cint(row.get("total_sold")) > 0
	if stage == "has_stylebio":
		return bool(row.get("stylebio"))
	if stage == "no_stylebio":
		return not row.get("stylebio")
	if stage == "no_tag":
		return not row.get("first_tag_date")
	if stage == "cad_order_raised":
		return bool(row.get("cad_order_no"))
	if stage == "cad_order_rejected":
		return row.get("cad_bucket") == "rejected"
	if stage == "sketch_order_designing":
		# Running Sketch Orders = Sketch Orders whose workflow state is "Assigned".
		return row.get("sketch_workflow_state") == "Assigned"
	if stage == "cad_order_running_designing":
		# Currently sitting in the design stage itself - not just "reached
		# designing or beyond" like the cumulative cad_order_designing funnel
		# stage, but still there right now.
		return row.get("cad_bucket") in ("designing", "designing_on_hold", "rework")
	cad_rank = {
		"cad_order_assigned": 1,
		"cad_order_designing": 2,
		"cad_order_qc": 3,
		"cad_order_completed": 4,
	}.get(stage)
	if cad_rank is not None:
		return CAD_STAGE_RANK.get(row.get("cad_bucket"), -1) >= cad_rank
	return True  # sketch_approved - every row already passed the CMO-approval join


def _month_keys_in_range(from_date, to_date):
	"""Every YYYY-MM between from_date and to_date (inclusive), so the monthly
	chart only ever spans the filter's own window - not whatever stray months
	first_tag_date happens to fall in outside that range."""
	if not from_date or not to_date:
		return []

	cur = get_first_day(getdate(from_date))
	end = get_first_day(getdate(to_date))
	months = []
	while cur <= end:
		months.append(cur.strftime("%Y-%m"))
		cur = add_months(cur, 1)
	return months


def _cad_order_buckets(rows):
	"""One cad_bucket per distinct cad_order_no - rows share a CAD order's
	workflow_state, so dedup by order number rather than counting every
	design row against it."""
	buckets = {}
	for row in rows:
		cad_no = row.get("cad_order_no")
		if cad_no:
			buckets[cad_no] = row.get("cad_bucket")
	return buckets


def _avg_days(rows, start_field, end_field):
	diffs = []
	for row in rows:
		start, end = row.get(start_field), row.get(end_field)
		if start and end:
			diffs.append(date_diff(end, start))
	return round(sum(diffs) / len(diffs), 1) if diffs else None


@frappe.whitelist()
def get_dashboard_data(filters=None):
	filters = _parse_filters(filters)
	rows = _rows_with_cad_status(filters)
	total = len(rows)

	unique_sketch_orders = len({r["sketch_order_no"] for r in rows if r.get("sketch_order_no")})
	# Includes cancelled CAD orders, to match the CAD Order funnel's "Raised" count.
	rows_incl_cancelled = _rows_with_cad_status(filters, include_cancelled=True)
	unique_cad_orders = len({r["cad_order_no"] for r in rows_incl_cancelled if r.get("cad_order_no")})
	unique_stylebio = len({r["stylebio"] for r in rows if r.get("stylebio")})
	tagged_designs = sum(1 for r in rows if _matches_stage(r, "tagged"))
	total_pcs_sold = sum(cint(r.get("total_sold")) for r in rows)

	running_sketch_orders = len(
		{
			r["sketch_order_no"]
			for r in rows
			if r.get("sketch_order_no") and _matches_stage(r, "sketch_order_designing")
		}
	)
	running_cad_orders = len(
		{
			r["cad_order_no"]
			for r in rows
			if r.get("cad_order_no") and _matches_stage(r, "cad_order_running_designing")
		}
	)

	summary_kpis = [
		{
			"key": "total_sketch_orders",
			"stage": "sketch_approved",
			"label": "Total Sketch Orders",
			"count": unique_sketch_orders,
		},
		{"key": "total_designs", "stage": "sketch_approved", "label": "Total Designs", "count": total},
		{"key": "total_cad_orders", "stage": "cad_order_raised", "label": "Total CAD Orders", "count": unique_cad_orders},
		{"key": "total_stylebio", "stage": "has_stylebio", "label": "Unique StyleBio", "count": unique_stylebio},
		{"key": "total_tags", "stage": "tagged", "label": "Total Tags", "count": tagged_designs},
		{"key": "total_pcs_sold", "stage": "sold", "label": "Total Pcs Sold", "count": total_pcs_sold},
		{
			"key": "running_sketch_orders",
			"stage": "sketch_order_designing",
			"label": "Running Sketch Orders (Designing)",
			"count": running_sketch_orders,
		},
		{
			"key": "running_cad_orders",
			"stage": "cad_order_running_designing",
			"label": "Running CAD Orders (Designing)",
			"count": running_cad_orders,
		},
	]

	sketch_status_counts = {}
	for r in _sketch_orders_by_status(filters):
		state = r["sketch_workflow_state"]
		sketch_status_counts[state] = sketch_status_counts.get(state, 0) + 1
	sketch_funnel = [
		{"stage": stage, "label": label, "count": sketch_status_counts.get(state, 0)}
		for stage, label, state in SKETCH_FUNNEL_STAGES
	]

	funnel = [
		{"stage": "sketch_approved", "label": "Sketch Approved", "count": total},
		{
			"stage": "cad_raised",
			"label": "CAD Orders",
			"count": sum(1 for r in rows if _matches_stage(r, "cad_raised")),
		},
		{
			"stage": "has_stylebio",
			"label": "StyleBio (Designs)",
			"count": sum(1 for r in rows if _matches_stage(r, "has_stylebio")),
		},
		{
			"stage": "tagged",
			"label": "First Tag",
			"count": sum(1 for r in rows if _matches_stage(r, "tagged")),
		},
	]

	# Third row of KPI cards: the former "Pipeline Funnel" values.
	summary_kpis += [
		{"key": f"pipeline_{f['stage']}", "stage": f["stage"], "label": f["label"], "count": f["count"]}
		for f in funnel
		if f["stage"] != "tagged"  # "First Tag" is intentionally not shown as a card
	]

	cad_buckets = _cad_order_buckets(rows_incl_cancelled)
	total_cad = len(cad_buckets)
	non_rejected_ranks = [
		CAD_STAGE_RANK[b] for b in cad_buckets.values() if b in CAD_STAGE_RANK
	]
	rejected_cad = sum(1 for b in cad_buckets.values() if b == "rejected")

	def _reached(rank):
		return sum(1 for r in non_rejected_ranks if r >= rank)

	# Stage labels for everything past "raised" are pulled straight from the
	# CAD Order Dashboard's own BUCKET_LABELS (and its "Completed" wording for
	# the folded "approved" bucket - see PAGE_BUCKET_LABELS there) so this
	# funnel's terminology for a given status always matches that dashboard.
	cad_funnel = [
		{"stage": "cad_order_raised", "label": "CAD Orders Raised", "count": total_cad},
		{"stage": "cad_order_assigned", "label": BUCKET_LABELS["assigned"], "count": _reached(1)},
		{"stage": "cad_order_designing", "label": BUCKET_LABELS["designing"], "count": _reached(2)},
		{"stage": "cad_order_qc", "label": BUCKET_LABELS["qc"], "count": _reached(3)},
		{"stage": "cad_order_completed", "label": "Completed", "count": _reached(4)},
		{"stage": "cad_order_rejected", "label": BUCKET_LABELS["rejected"], "count": rejected_cad},
	]

	no_sketch_cad = _cad_orders_without_sketch(filters)
	no_sketch_completed = sum(1 for r in no_sketch_cad if r.get("cad_bucket") == "approved")

	blockers = [
		{
			"stage": "cad_pending",
			"label": "Sketch Approved – CAD Not Placed",
			"count": sum(1 for r in rows if _matches_stage(r, "cad_pending")),
		},
		{
			"stage": "cad_not_received",
			"label": "CAD Order Placed – Design Not Received",
			"count": sum(1 for r in rows if _matches_stage(r, "cad_not_received")),
		},
		{
			"stage": "cad_without_sketch",
			"label": "CAD Without Sketch Order",
			"count": len(no_sketch_cad),
			"completed_count": no_sketch_completed,
			"completed_pct": round(no_sketch_completed / len(no_sketch_cad) * 100, 1) if no_sketch_cad else 0,
		},
		{
			"stage": "no_stylebio",
			"label": "No StyleBio Designs",
			"count": sum(1 for r in rows if _matches_stage(r, "no_stylebio")),
		},
		{
			"stage": "no_tag",
			"label": "No Tag Designs",
			"count": sum(1 for r in rows if _matches_stage(r, "no_tag")),
		},
	]

	with_stylebio = sum(1 for r in rows if _matches_stage(r, "has_stylebio"))
	tagged = funnel[3]["count"]
	stylebio_tag_ratio = {
		"total_designs": total,
		"with_stylebio": with_stylebio,
		"tagged": tagged,
		"stylebio_coverage_pct": round(with_stylebio / total * 100, 1) if total else 0,
		"tag_ratio_pct": round(tagged / total * 100, 1) if total else 0,
		"tag_vs_stylebio_pct": round(tagged / with_stylebio * 100, 1) if with_stylebio else 0,
	}

	lead_times = {
		"sketch_to_cad": _avg_days(rows, "sketch_order_date", "cad_order_date"),
		"cad_to_tag": _avg_days(rows, "cad_order_date", "first_tag_date"),
		"sketch_to_tag": _avg_days(rows, "sketch_order_date", "first_tag_date"),
	}

	_attach_erp_category(rows)
	category_map = {}
	for row in rows:
		key = row.get("erp_category") or "Uncategorized"
		bucket = category_map.setdefault(
			key, {"category": key, "total": 0, "stylebio": 0, "tagged": 0, "sold_qty": 0}
		)
		bucket["total"] += 1
		if row.get("stylebio"):
			bucket["stylebio"] += 1
		if row.get("first_tag_date"):
			bucket["tagged"] += 1
		bucket["sold_qty"] += cint(row.get("total_sold"))
	category_breakdown = sorted(category_map.values(), key=lambda b: -b["total"])

	customer_map = {}
	for row in rows:
		key = row.get("customer") or "Unknown"
		bucket = customer_map.setdefault(key, {"customer": key, "total": 0, "tagged": 0, "sold_qty": 0})
		bucket["total"] += 1
		if row.get("first_tag_date"):
			bucket["tagged"] += 1
		bucket["sold_qty"] += cint(row.get("total_sold"))
	customer_breakdown = sorted(customer_map.values(), key=lambda b: -b["total"])[:20]
	customer_names = {
		c.name: c.customer_name
		for c in frappe.db.get_all(
			"Customer",
			filters={"name": ["in", [b["customer"] for b in customer_breakdown]]},
			fields=["name", "customer_name"],
		)
	}
	for b in customer_breakdown:
		b["customer_name"] = customer_names.get(b["customer"]) or b["customer"]

	month_keys = _month_keys_in_range(filters.get("from_date"), filters.get("to_date"))

	# "Completed" here = the Sketch Order behind the design got its item_code -
	# see `_sketch_order_completion_dates` for why that's resolved via the
	# order's submit (docstatus 0->1) event rather than first_tag_date.
	sketch_order_nos = list({r["sketch_order_no"] for r in rows if r.get("sketch_order_no")})
	completion_dates = _sketch_order_completion_dates(sketch_order_nos)

	# Each unique item code is counted exactly once overall, in the month of
	# its earliest completion date.
	first_completion = {}
	for row in rows:
		item_code = row.get("item_code")
		completion_date = completion_dates.get(row.get("sketch_order_no"))
		if not item_code or not completion_date:
			continue
		if item_code not in first_completion or completion_date < first_completion[item_code]:
			first_completion[item_code] = completion_date

	monthly_items = {}
	for item_code, completion_date in first_completion.items():
		month_key = getdate(completion_date).strftime("%Y-%m")
		if month_keys and month_key not in month_keys:
			continue  # outside the selected filter window
		monthly_items.setdefault(month_key, set()).add(item_code)

	monthly_map = {k: len(v) for k, v in monthly_items.items()}

	if not month_keys:
		month_keys = sorted(monthly_map.keys())

	monthly_completed = [
		{
			"month": key,
			"month_label": getdate(f"{key}-01").strftime("%b-%Y"),
			"completed_count": monthly_map.get(key, 0),
		}
		for key in month_keys
	]

	return {
		"summary_kpis": summary_kpis,
		"funnel": funnel,
		"sketch_funnel": sketch_funnel,
		"cad_funnel": cad_funnel,
		"blockers": blockers,
		"stylebio_tag_ratio": stylebio_tag_ratio,
		"lead_times": lead_times,
		"category_breakdown": category_breakdown,
		"customer_breakdown": customer_breakdown,
		"monthly_completed": monthly_completed,
		"total_sold_qty": sum(cint(r.get("total_sold")) for r in rows),
		"generated_at": frappe.utils.now(),
	}


@frappe.whitelist()
def get_setting_type_options():
	rows = frappe.db.sql(
		"SELECT DISTINCT setting_type FROM `tabItem` WHERE setting_type IS NOT NULL AND setting_type != '' ORDER BY setting_type",
		as_dict=False,
	)
	return [r[0] for r in rows]


@frappe.whitelist()
def get_dashboard_payload(filters=None):
	"""Single round trip for the whole page: computed off one shared
	row-fetch so the (slow, external-API-backed) report data is only
	ever fetched once per load."""
	filters = _parse_filters(filters)
	return get_dashboard_data(filters)


def _attach_images(rows):
	item_codes = list({r["item_code"] for r in rows if r.get("item_code")})
	if not item_codes:
		return rows

	image_rows = frappe.db.sql(
		"""
		SELECT fsac.item AS item_code, fsac.final_image AS final_image, fsac.sketch_image AS sketch_image
		FROM `tabFinal Sketch Approval CMO` fsac
		WHERE fsac.item IN %(items)s
			AND (fsac.final_image IS NOT NULL OR fsac.sketch_image IS NOT NULL)
		""",
		{"items": item_codes},
		as_dict=True,
	)
	image_by_item = {}
	for image_row in image_rows:
		if image_row.item_code not in image_by_item:
			image_by_item[image_row.item_code] = image_row.final_image or image_row.sketch_image

	for row in rows:
		row["image"] = image_by_item.get(row.get("item_code"))

	return rows


def _attach_erp_category(rows):
	"""Set row["erp_category"] from the ERP Item's item_category (not Jwelex)."""
	item_codes = list({r["item_code"] for r in rows if r.get("item_code")})
	category_by_item = {}
	if item_codes:
		category_by_item = {
			it.name: it.item_category
			for it in frappe.db.get_all(
				"Item", filters={"name": ["in", item_codes]}, fields=["name", "item_category"]
			)
		}
	for row in rows:
		row["erp_category"] = category_by_item.get(row.get("item_code"))
	return rows


def _attach_erp_details(rows):
	"""Category, Setting, Dia Wt and Metal Wt for the detail list - all from
	ERP (Item + the item's default BOM, else its latest BOM), never from
	Jwelex."""
	item_codes = list({r["item_code"] for r in rows if r.get("item_code")})
	item_map = {}
	bom_map = {}
	if item_codes:
		for it in frappe.db.get_all(
			"Item",
			filters={"name": ["in", item_codes]},
			fields=["name", "item_category", "setting_type"],
		):
			item_map[it.name] = it

		for b in frappe.db.get_all(
			"BOM",
			filters={"item": ["in", item_codes], "docstatus": ["<", 2]},
			fields=["item", "total_diamond_weight", "total_metal_weight"],
			order_by="is_default asc, modified asc",
		):
			bom_map[b.item] = b  # later rows (default, most recent) win

	for row in rows:
		it = item_map.get(row.get("item_code")) or {}
		bom = bom_map.get(row.get("item_code")) or {}
		row["erp_category"] = it.get("item_category")
		row["erp_setting"] = it.get("setting_type")
		row["dia_wt"] = bom.get("total_diamond_weight")
		row["metal_wt"] = bom.get("total_metal_weight")

	return rows


@frappe.whitelist()
def get_segment_rows(filters=None, stage=None, category=None, customer=None, month=None):
	filters = _parse_filters(filters)

	if stage == "cad_without_sketch":
		# These orders never appear in the Sketch-Order-anchored report rows
		# (see `_cad_orders_without_sketch`), so they're fetched separately
		# rather than filtered out of `_rows_with_cad_status`.
		rows = _cad_orders_without_sketch(filters)
		if customer:
			rows = [r for r in rows if (r.get("customer") or "Unknown") == customer]
		return _attach_erp_details(_attach_images(rows))

	sketch_state = {k: st for k, _, st in SKETCH_FUNNEL_STAGES}.get(stage)
	if sketch_state:
		rows = _sketch_orders_by_status(filters, state=sketch_state)
		if customer:
			rows = [r for r in rows if (r.get("customer") or "Unknown") == customer]
		return _attach_erp_details(_attach_images(rows))

	# The CAD Order funnel counts cancelled CAD orders, so its drill-downs must too.
	rows = _rows_with_cad_status(filters, include_cancelled=(stage or "").startswith("cad_order_"))

	rows = [r for r in rows if _matches_stage(r, stage)]
	if category:
		_attach_erp_category(rows)
		rows = [r for r in rows if (r.get("erp_category") or "Uncategorized") == category]
	if customer:
		rows = [r for r in rows if (r.get("customer") or "Unknown") == customer]
	if month:
		# Same "completed" definition as the monthly chart itself - see
		# `_sketch_order_completion_dates`.
		sketch_order_nos = list({r["sketch_order_no"] for r in rows if r.get("sketch_order_no")})
		completion_dates = _sketch_order_completion_dates(sketch_order_nos)
		# Same rule as the chart: one row per unique item code, in the month
		# of its earliest completion date.
		first = {}
		for r in rows:
			d = completion_dates.get(r.get("sketch_order_no"))
			if r.get("item_code") and d and (r["item_code"] not in first or d < first[r["item_code"]][0]):
				first[r["item_code"]] = (d, r)
		rows = [
			r for d, r in first.values()
			if getdate(d).strftime("%Y-%m") == month
		]

	return _attach_erp_details(_attach_images(rows))
