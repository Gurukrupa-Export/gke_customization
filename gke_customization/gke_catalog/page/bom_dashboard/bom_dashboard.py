# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

"""API for the BOM Dashboard page (`bom-dashboard`). Open to every logged-in user.

Pipeline data comes from `Order` (workflow_state, due date, assignees); the
BOM documents linked via Order's own `bom` / `new_bom` fields feed a small
BOM-document panel. Only counts/sums are returned by `get_dashboard_data`;
order/BOM names are resolved on demand by `get_segment_orders`.
"""

import json

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, nowdate

# ---------------------------------------------------------------------------
# CONFIG - everything BOM-specific / assumed lives here. Verify these first.
# ---------------------------------------------------------------------------

SOURCE_SQL = "o.bom_or_cad = 'New BOM'"  # which Orders belong to the BOM flow
DUE_DATE_SQL = "o.delivery_date"  # e.g. "COALESCE(o.bom_delivery_date, o.delivery_date)"
# Order already carries a direct link to its BOM: no join field on tabBOM
# needed. Verified via System Console: 'bom' is populated on 34,741/34,833
# New BOM orders (99.7%), 'new_bom' on 31,806, and where both are set they
# match. 'bom' is used first, 'new_bom' as a fallback; only ~10 orders have
# neither. (custom_order_id on tabBOM was tried first but is always blank -
# real BOMs link out to Manufacturing Plan / Quotation, never back to Order.)
GK_PREFIX = "Gurukrupa Export"  # customer_name prefix that means "in-house"

# (key, label, workflow states) in pipeline order, built from the real
# "Order with Customer Approval Final3" workflow (33 states, verified via
# System Console). Every state is mapped so nothing falls into "other"
# silently; states with 0 current New BOM orders will just show 0.
BUCKETS = [
	("pending", "Not Started", ["Draft", "Un-assigned", "Assigned", "Order BOM"]),
	("on_hold", "On Hold", [
		"On Hold", "Assigned - On-Hold", "Designing - On-Hold", "Sent to QC - On-Hold",
		"BOM QC - On-Hold", "Creating BOM - On-Hold", "Updating BOM - On-Hold",
		"Update Item - On-Hold", "Design Rework in Progress - On Hold",
	]),
	("update_item", "Update Item", ["Update Item", "Update Designer"]),
	("update_bom", "Update BOM", ["Update BOM", "Reupdate BOM", "Updating BOM"]),
	("creating_bom", "Creating BOM", [
		"Creating BOM", "CAD or BOM", "Create CAD", "Create BOM",
	]),
	("designing", "Designing / Rework", [
		"Designing", "Design Rework in Progress", "Update Requested",
	]),
	("bom_qc", "BOM QC", ["BOM QC", "Sent to QC"]),
	("customer_approval", "Customer Approval", ["Customer Approval", "Customer Approved"]),
	("approved", "Approved", ["Approved"]),
	("rejected", "Rejected / Cancelled", ["Rejected", "Cancelled", "Customer Design Rejected"]),
	("other", "Other Stage", None),
]
DONE = {"approved", "rejected"}  # excluded from alerts and "in progress"

FILTER_KEYS = (
	"company",  # optional: no company filter in the UI, kept for API callers
	"from_date",
	"to_date",
	"setting_type",
	"sub_setting_type1",
	"category",
	"customer",
	"branch",
	"assigned_to",
)

LABELS = {key: label for key, label, _states in BUCKETS}
STATE_BUCKET = {s: key for key, _label, states in BUCKETS if states for s in states}
ORDER = [b[0] for b in BUCKETS]
UNASSIGNED = "__unassigned__"


# ---------------------------------------------------------------------------
# data helpers
# ---------------------------------------------------------------------------


def _bucket(state):
	return STATE_BUCKET.get(state, "other")


def _assignees(row):
	try:
		return [u for u in json.loads(row.get("_assign") or "[]") if u]
	except ValueError:
		return []


def _fetch_rows(f):
	cond, params = [], {}
	for key, col in (
		("company", "o.company"),
		("customer", "o.customer_code"),
		("branch", "o.branch"),
		("setting_type", "o.setting_type"),
		("sub_setting_type1", "o.sub_setting_type1"),
		("category", "o.category"),
	):
		if f.get(key):
			cond.append(f"{col} = %({key})s")
			params[key] = f[key]
	if f.get("from_date"):
		cond.append("o.order_date >= %(from_date)s")
		params["from_date"] = getdate(f["from_date"])
	if f.get("to_date"):
		# order_date is a Datetime: exclusive next-day bound keeps the whole to_date
		cond.append("o.order_date < %(to_date)s")
		params["to_date"] = add_days(getdate(f["to_date"]), 1)
	extra = "".join(f" AND {c}" for c in cond)

	rows = frappe.db.sql(
		f"""
		SELECT o.name, o.workflow_state, o.category, o.qty, o.order_type, o._assign,
			o.bom, o.new_bom, cust.customer_name, {DUE_DATE_SQL} AS due_date
		FROM `tabOrder` o
		LEFT JOIN `tabCustomer` cust ON cust.name = o.customer_code
		WHERE {SOURCE_SQL} AND o.docstatus != 2{extra}
		""",
		params,
		as_dict=True,
	)
	# exact match here (a SQL LIKE on `_assign` would treat "_" in emails as a wildcard)
	if f.get("assigned_to"):
		rows = [r for r in rows if f["assigned_to"] in _assignees(r)]
	return rows


def _context(kw):
	f = {k: kw.get(k) or None for k in FILTER_KEYS}
	rows = _fetch_rows(f)
	emails = list({u for r in rows for u in _assignees(r)})
	names = (
		{u.name: u.full_name for u in frappe.get_all("User", {"name": ["in", emails]}, ["name", "full_name"])}
		if emails
		else {}
	)
	return f, rows, names


def _risk_fn(days):
	today = getdate(nowdate())
	soon = getdate(add_days(nowdate(), max(cint(days), 0)))

	def risk_of(row):
		if _bucket(row.workflow_state) in DONE or not row.due_date:
			return None
		due = getdate(row.due_date)
		if due < today:
			return "overdue"
		if due <= soon:
			return "due_soon"
		return None

	return risk_of


def _stock_key(row):
	# Verified against real data (System Console, 34,832 New BOM orders):
	#   Stock Order | Customer: 15975   Sales | Customer: 9061
	#   (blank)     | Customer: 9533    Sales | GK: 148
	#   Stock Order | GK: 63            (blank) | GK: 53
	# Every combination is mapped; "blank_order_type" replaces the old
	# catch-all "other" so it's visible instead of hidden.
	is_gk = (row.customer_name or "").startswith(GK_PREFIX)
	if row.order_type == "Stock Order":
		return "gk_stock" if is_gk else "customer_stock"
	if row.order_type == "Sales":
		return "gk_order" if is_gk else "customer_order"
	return "gk_blank" if is_gk else "blank_order_type"


def _row_keys_fn(view, names, only):
	def assignee(row):
		users = [u for u in _assignees(row) if not only or u == only]
		if not users:
			return [(UNASSIGNED, _("Unassigned"))]
		return [(u, names.get(u) or u) for u in users]

	def status(row):
		b = _bucket(row.workflow_state)
		return [(b, _(LABELS[b]))]

	def customer(row):
		c = row.customer_name or _("Unknown Customer")
		return [(c, c)]

	return {"status": status, "customer": customer}.get(view, assignee)


def _metric():
	return {"qty": 0, "overdue": 0, "due_soon": 0}


def _add(target, qty, risk):
	target["qty"] += qty
	if risk:
		target[risk] += 1


def _build_matrix(rows, row_keys_fn, risk_of, fixed_rows=None):
	# Matrix counts ORDERS (1 per order), not piece qty. Column totals and the
	# grand total count each order once, so they match the KPI strip even in the
	# assignee view (an order with 2 assignees appears in 2 rows, but once in totals).
	m, cols, grand = {}, {}, _metric()
	for row in rows:
		qty, risk = 1, risk_of(row)
		cat = row.category or _("Uncategorized")
		for key, label in row_keys_fn(row):
			r = m.setdefault(key, {"key": key, "name": label, "cells": {}, "total": _metric()})
			_add(r["cells"].setdefault(cat, _metric()), qty, risk)
			_add(r["total"], qty, risk)
		_add(cols.setdefault(cat, _metric()), qty, risk)
		_add(grand, qty, risk)

	if fixed_rows:
		for k in fixed_rows:
			m.setdefault(k, {"key": k, "name": _(LABELS[k]), "cells": {}, "total": _metric()})
		out_rows = [m[k] for k in fixed_rows]
	else:
		out_rows = sorted(m.values(), key=lambda r: r["total"]["qty"], reverse=True)

	categories = sorted(cols, key=lambda c: cols[c]["qty"], reverse=True)
	return {
		"categories": categories,
		"rows": out_rows,
		"category_totals": cols,
		"grand_total": grand,
	}


def _matrix_filtered(rows, stock_filter=None, status_filter=None):
	"""Subset of `rows` for the matrix only - the KPI strip, workload and
	alerts panels always use the full, unfiltered `rows`."""
	out = rows
	if stock_filter:
		out = [r for r in out if _stock_key(r) == stock_filter]
	if status_filter:
		out = [r for r in out if _bucket(r.workflow_state) == status_filter]
	return out


def _chunks(seq, n=5000):
	seq = list(seq)
	for i in range(0, len(seq), n):
		yield seq[i : i + n]


def _order_bom_name(row):
	"""The BOM linked to an order, straight from Order's own fields."""
	return row.bom or row.new_bom or None


def _bom_docs_by_name(bom_names):
	out = {}
	for chunk in _chunks(bom_names):
		for b in frappe.db.sql(
			"""
			SELECT name, docstatus, is_active, total_bom_amount
			FROM `tabBOM`
			WHERE name IN %(names)s AND docstatus != 2
			""",
			{"names": chunk},
			as_dict=True,
		):
			out[b.name] = b
	return out


def _bom_state(b):
	if b.docstatus == 0:
		return "draft"
	return "active" if b.is_active else "inactive"


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_dashboard_data(**kw):
	f, rows, names = _context(kw)
	only = f.get("assigned_to")
	risk_of = _risk_fn(kw.get("due_soon_days", 2))
	total = len(rows)

	counts = dict.fromkeys(ORDER, 0)
	stock = dict.fromkeys(
		("customer_order", "customer_stock", "gk_order", "gk_stock", "blank_order_type", "gk_blank"), 0
	)
	workload = {}
	due_soon = overdue = 0
	for row in rows:
		b = _bucket(row.workflow_state)
		counts[b] += 1
		stock[_stock_key(row)] += 1
		risk = risk_of(row)
		due_soon += risk == "due_soon"
		overdue += risk == "overdue"
		for key, label in _row_keys_fn("assignee", names, only)(row):
			w = workload.setdefault(
				key, {"key": key, "name": label, "count": 0, "in_progress": 0, "completed": 0}
			)
			w["count"] += 1
			if b == "approved":
				w["completed"] += 1
			elif b not in DONE:
				w["in_progress"] += 1

	view = kw.get("matrix_view") or "assignee"
	matrix_rows = _matrix_filtered(rows, kw.get("matrix_stock_filter"), kw.get("matrix_status_filter"))
	matrix = _build_matrix(
		matrix_rows,
		_row_keys_fn(view, names, only),
		risk_of,
		fixed_rows=ORDER if view == "status" else None,
	)

	bom_names = list({_order_bom_name(r) for r in rows if _order_bom_name(r)})
	bom_docs = _bom_docs_by_name(bom_names)
	bom_counts = dict.fromkeys(("draft", "active", "inactive"), 0)
	no_bom = 0
	total_amount = 0
	for r in rows:
		name = _order_bom_name(r)
		doc = bom_docs.get(name) if name else None
		if not doc:
			no_bom += 1
			continue
		bom_counts[_bom_state(doc)] += 1
		total_amount += flt(doc.total_bom_amount)

	return {
		"total_orders": total,
		"status_summary": [{"key": k, "label": _(LABELS[k]), "count": counts[k]} for k in ORDER],
		"stock": stock,
		"workload": sorted(workload.values(), key=lambda w: w["count"], reverse=True),
		"matrix": matrix,
		"alerts": {
			"due_soon": {"days": max(cint(kw.get("due_soon_days", 2)), 0), "count": due_soon},
			"overdue": {"count": overdue},
		},
		"bom_docs": {
			**bom_counts,
			"no_bom": no_bom,
			"total_amount": total_amount,
		},
		"generated_at": frappe.utils.now(),
	}


@frappe.whitelist()
def get_segment_orders(segment=None, **kw):
	"""Names behind one displayed number: {"doctype": "Order"|"BOM", "names": [...]}."""
	f, rows, names = _context(kw)
	only = f.get("assigned_to")
	risk_of = _risk_fn(kw.get("due_soon_days", 2))
	seg = frappe.parse_json(segment) if isinstance(segment, str) else (segment or {})
	t = seg.get("type")

	def orders(it):
		return {"doctype": "Order", "names": sorted({r.name for r in it})}

	if t == "total":
		return orders(rows)
	if t == "status_bucket":
		return orders(r for r in rows if _bucket(r.workflow_state) == seg.get("bucket"))
	if t == "stock_split":
		return orders(r for r in rows if _stock_key(r) == seg.get("key"))
	if t == "alert":
		return orders(r for r in rows if risk_of(r) == seg.get("which"))

	if t == "assignee":
		metric, key = seg.get("metric", "total"), seg.get("key")
		keys_fn = _row_keys_fn("assignee", names, only)

		def match(r):
			if key not in [k for k, _label in keys_fn(r)]:
				return False
			b = _bucket(r.workflow_state)
			return metric == "total" or (metric == "completed" and b == "approved") or (
				metric == "in_progress" and b not in DONE
			)

		return orders(r for r in rows if match(r))

	if t == "matrix_cell":
		view, row_key, cat = seg.get("view", "assignee"), seg.get("row_key"), seg.get("category")
		keys_fn = _row_keys_fn(view, names, only)
		matrix_rows = _matrix_filtered(rows, kw.get("matrix_stock_filter"), kw.get("matrix_status_filter"))
		return orders(
			r
			for r in matrix_rows
			if (cat is None or (r.category or _("Uncategorized")) == cat)
			and (row_key is None or row_key in [k for k, _label in keys_fn(r)])
		)

	if t in ("bom_doc", "no_bom"):
		bom_names = list({_order_bom_name(r) for r in rows if _order_bom_name(r)})
		bom_docs = _bom_docs_by_name(bom_names)
		if t == "bom_doc":
			return {
				"doctype": "BOM",
				"names": sorted(n for n, d in bom_docs.items() if _bom_state(d) == seg.get("which")),
			}
		return orders(r for r in rows if not bom_docs.get(_order_bom_name(r)))

	return {"doctype": "Order", "names": []}