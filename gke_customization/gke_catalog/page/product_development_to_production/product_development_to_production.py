import json
import re

import frappe
from frappe.utils import add_months, cint, date_diff, get_first_day, getdate

from gke_customization.gke_catalog.report.product_development_to_production.product_development_to_production import (
	get_data as get_report_data,
)
from gke_customization.gke_catalog.report.cad_dashboard_script.cad_dashboard_script import (
	REJECTED_STATES,
	_bucket_of,
)

CACHE_TTL = 600


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
	rows = frappe.cache().get_value(key)
	if rows is None:
		rows = get_report_data(date_filters)
		frappe.cache().set_value(key, rows, expires_in_sec=CACHE_TTL)
	return rows


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


def _rows_with_cad_status(filters):
	"""Report rows enriched with the linked CAD Order's workflow_state/bucket,
	reusing the exact bucketing used by the CAD Order Dashboard so "received"
	means the same thing across both pages."""
	rows = _cached_rows(filters)
	rows = _apply_extra_filters(rows, filters)

	cad_names = list({row.get("cad_order_no") for row in rows if row.get("cad_order_no")})
	status_map = {}
	if cad_names:
		status_map = {
			d.name: d.workflow_state
			for d in frappe.db.get_all(
				"Order", filters={"name": ["in", cad_names]}, fields=["name", "workflow_state"]
			)
		}

	for row in rows:
		cad_no = row.get("cad_order_no")
		state = status_map.get(cad_no) if cad_no else None
		row["cad_workflow_state"] = state
		row["cad_bucket"] = _bucket_of(state) if state else None

	return rows


def _matches_stage(row, stage):
	if stage == "cad_raised":
		return bool(row.get("cad_order_no"))
	if stage == "cad_pending":
		# Sketch approved but no CAD order placed against it yet.
		return not row.get("cad_order_no")
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
	unique_cad_orders = len({r["cad_order_no"] for r in rows if r.get("cad_order_no")})
	unique_stylebio = len({r["stylebio"] for r in rows if r.get("stylebio")})
	tagged_designs = sum(1 for r in rows if _matches_stage(r, "tagged"))
	total_pcs_sold = sum(cint(r.get("total_sold")) for r in rows)

	summary_kpis = [
		{
			"key": "total_sketch_orders",
			"stage": "sketch_approved",
			"label": "Total Sketch Orders",
			"count": unique_sketch_orders,
		},
		{"key": "total_designs", "stage": "sketch_approved", "label": "Total Designs", "count": total},
		{"key": "total_cad_orders", "stage": "cad_raised", "label": "Total CAD Orders", "count": unique_cad_orders},
		{"key": "total_stylebio", "stage": "has_stylebio", "label": "Unique StyleBio", "count": unique_stylebio},
		{"key": "total_tags", "stage": "tagged", "label": "Total Tags", "count": tagged_designs},
		{"key": "total_pcs_sold", "stage": "sold", "label": "Total Pcs Sold", "count": total_pcs_sold},
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
		{
			"stage": "sold",
			"label": "Sold",
			"count": sum(1 for r in rows if _matches_stage(r, "sold")),
		},
	]

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

	category_map = {}
	for row in rows:
		key = row.get("category_name") or "Uncategorized"
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

	month_keys = _month_keys_in_range(filters.get("from_date"), filters.get("to_date"))

	monthly_map = {}
	for row in rows:
		if not row.get("first_tag_date"):
			continue
		month_key = getdate(row["first_tag_date"]).strftime("%Y-%m")
		if month_keys and month_key not in month_keys:
			continue  # outside the selected filter window - first_tag_date isn't what from_date/to_date filters on
		monthly_map[month_key] = monthly_map.get(month_key, 0) + 1  # count of designs completed, not pcs

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


@frappe.whitelist()
def get_segment_rows(filters=None, stage=None, category=None, customer=None):
	filters = _parse_filters(filters)
	rows = _rows_with_cad_status(filters)

	rows = [r for r in rows if _matches_stage(r, stage)]
	if category:
		rows = [r for r in rows if (r.get("category_name") or "Uncategorized") == category]
	if customer:
		rows = [r for r in rows if (r.get("customer") or "Unknown") == customer]

	return _attach_images(rows)
