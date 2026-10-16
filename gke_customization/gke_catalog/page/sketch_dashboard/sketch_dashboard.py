# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, flt, get_first_day, get_last_day, getdate, nowdate


# Workflow states grouped into dashboard stages
BUCKETS = [
	("draft", "Draft", ["Draft"]),
	("assigned", "Assigned", ["Assigned"]),
	("rough_hod", "Rough sketch (HOD)", ["Rough Sketch Approval (HOD)"]),
	("final_hod", "Final sketch (HOD)", ["Final Sketch Approval (HOD)"]),
	("customer_approval", "Customer approval", ["Customer Approval"]),
	("item_update", "Item update", ["Requires Update", "Update Item", "Items Updated"]),
	("approved", "Approved", ["Approved"]),
	(
		"on_hold",
		"On hold",
		[
			"On Hold",
			"On Hold - Assigned",
			"On Hold - Rough Sketch Approval",
			"ON Hold - Final Sketch Approved (HOD)",
			"On Hold - Requires Update",
		],
	),
	("cancelled", "Cancelled", ["Cancelled"]),
	("old_workflow", "Old workflow", ["Attach Image", "Image QC"]),
]

STATE_TO_BUCKET = {state: key for key, _label, states in BUCKETS for state in states}
BUCKET_LABELS = {key: label for key, label, _states in BUCKETS}
BUCKET_LABELS["other"] = "Other"
BUCKET_ORDER = [b[0] for b in BUCKETS] + ["other"]

DESIGNER_ACTIVE_STATES = {
	"Assigned",
	"Rough Sketch Approval (HOD)",
	"Final Sketch Approval (HOD)",
	"On Hold - Assigned",
	"On Hold - Rough Sketch Approval",
	"ON Hold - Final Sketch Approved (HOD)",
}

DESIGNER_DONE_STATES = {
	"Customer Approval",
	"Requires Update",
	"Update Item",
	"Items Updated",
	"Approved",
	"On Hold - Requires Update",
	"Attach Image",
	"Image QC",
}

ALERT_STATES = {"Draft", "On Hold"} | DESIGNER_ACTIVE_STATES

MADE_BY_LABELS = {
	"designer": "In-house designer",
	"supplier": "Supplier",
	"not_assigned": "Not assigned",
}

NOT_SET = "Not set"

# Supplier groups that are valid for sketch work; anything else is flagged
DESIGN_SUPPLIER_GROUPS = {"Designs", "Services", "Subcontracting"}

UNUSUAL_APPROVAL_ROW = 100


def _parse_filters(filters):
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)
	f = frappe._dict(filters or {})
	# Company filter is not shown on the page; use the user's default company
	if not f.get("company"):
		f.company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
			"Global Defaults", "default_company"
		)
	if not f.company:
		frappe.throw(_("Please set a default Company"))
	if not frappe.has_permission("Sketch Order", "read"):
		frappe.throw(_("You are not permitted to view Sketch Orders."), frappe.PermissionError)
	return f


def _conditions(f, with_dates=True, with_designer=True):
	cond = ["so.company = %(company)s"]
	params = {"company": f.company}

	mapping = [
		("branch", "so.branch"),
		("customer", "so.customer_code"),
		("sales_person", "so.salesman_name"),
		("category", "so.category"),
		("order_type", "so.order_type"),
	]
	for key, column in mapping:
		if f.get(key):
			cond.append(f"{column} = %({key})s")
			params[key] = f.get(key)
	# Sketch number: an exact Sketch Order (S/ORD/00110-1), or a form number (S/ORD/00110)
	# which matches all orders of that form (S/ORD/00110-1, -2, ...)
	if f.get("sketch_no"):
		sketch_no = f.get("sketch_no").strip()
		if frappe.db.exists("Sketch Order", sketch_no):
			cond.append("so.name = %(sketch_no)s")
			params["sketch_no"] = sketch_no
		else:
			cond.append("so.name like %(sketch_no)s")
			params["sketch_no"] = sketch_no + "-%"

	if with_designer and f.get("designer"):
		cond.append(
			"exists (select 1 from `tabDesigner Assignment` dax "
			"where dax.parent = so.name and dax.parenttype = 'Sketch Order' "
			"and dax.designer = %(designer)s)"
		)
		params["designer"] = f.designer

	tab = f.get("tab") or "all"
	if tab == "open_setting":
		cond.append("so.setting_type = 'Open'")
	elif tab == "nova_glow":
		cond.append("so.setting_type = 'Nova Glow'")
	elif tab == "close_open_setting":
		cond.append("so.sub_setting_type1 = 'Close-Open Setting'")

	if with_dates:
		if f.get("from_date"):
			cond.append("date(so.order_date) >= %(from_date)s")
			params["from_date"] = f.from_date
		if f.get("to_date"):
			cond.append("date(so.order_date) <= %(to_date)s")
			params["to_date"] = f.to_date

	return " and ".join(cond), params


def _fetch_rows(f):
	where, params = _conditions(f)
	return frappe.db.sql(
		f"""
		select
			so.name, so.workflow_state, so.docstatus, so.qty,
			so.order_type, so.category, so.design_type, so.flow_type,
			so.customer_code, cust.customer_name,
			so.supplier, so.supplier_name, sup.supplier_group,
			date(so.delivery_date) as due_date
		from `tabSketch Order` so
		left join `tabCustomer` cust on cust.name = so.customer_code
		left join `tabSupplier` sup on sup.name = so.supplier
		where {where}
		""",
		params,
		as_dict=True,
	)


def _fetch_assignments(order_names):
	if not order_names:
		return {}
	rows = frappe.db.sql(
		"""
		select parent, designer, designer_name, count_1
		from `tabDesigner Assignment`
		where parenttype = 'Sketch Order' and parent in %(names)s
		""",
		{"names": tuple(order_names)},
		as_dict=True,
	)
	amap = {}
	for r in rows:
		amap.setdefault(r.parent, []).append(r)
	return amap


def _bucket(row):
	if cint(row.docstatus) == 2:
		return "cancelled"
	return STATE_TO_BUCKET.get(row.workflow_state, "other")


# In-house designer if assigned, else supplier, else not assigned
def _not_assigned_kind(row):
	"""For orders with no designer and no supplier: why they are not assigned."""
	b = _bucket(row)
	if b in ("draft", "on_hold"):
		return "waiting"
	if b == "cancelled":
		return "cancelled"
	return "to_check"


def _made_by(row, amap):
	if amap.get(row.name):
		return "designer"
	if row.supplier:
		return "supplier"
	return "not_assigned"


def _designer_key(a):
	return a.designer or a.designer_name or "__unknown__"


def _designer_stage(row):
	if cint(row.docstatus) == 2 or row.workflow_state == "Cancelled":
		return "cancelled"
	if row.workflow_state in DESIGNER_ACTIVE_STATES:
		return "in_progress"
	if row.workflow_state in DESIGNER_DONE_STATES:
		return "completed"
	return "other"


# Due-date alert only while the order is still with the designer / HOD
def _risk(row, today, due_soon_upper):
	if cint(row.docstatus) == 2 or row.workflow_state not in ALERT_STATES or not row.due_date:
		return None
	due = getdate(row.due_date)
	if due < today:
		return "overdue"
	if due <= due_soon_upper:
		return "due_soon"
	return None


def _wrong_supplier(row):
	return bool(row.supplier) and (row.supplier_group or "") not in DESIGN_SUPPLIER_GROUPS


def _health_kind(row):
	if cint(row.docstatus) == 1 and row.workflow_state == "Cancelled":
		return "cancelled_not_closed"
	if cint(row.docstatus) == 2 and row.workflow_state == "Approved":
		return "approved_but_cancelled"
	return None


def _overdue_age(row, today):
	days = (today - getdate(row.due_date)).days
	if days <= 7:
		return "overdue_7"
	if days <= 30:
		return "overdue_30"
	return "overdue_old"


def _is_stuck(row, today):
	if _designer_stage(row) != "in_progress" or not row.due_date:
		return False
	return (today - getdate(row.due_date)).days > 30


def _own_prefix(company):
	return " ".join((company or "").split()[:2]).lower()


def _customer_label(row):
	if row.customer_name and row.customer_name != row.customer_code:
		return f"{row.customer_code} - {row.customer_name}"
	return row.customer_code or NOT_SET


def _supplier_label(row):
	return row.supplier_name or row.supplier or NOT_SET


def _breakdown(rows, key_fn, limit=None):
	out = {}
	for row in rows:
		key = key_fn(row) or NOT_SET
		entry = out.setdefault(key, {"key": key, "label": key, "orders": 0, "designs": 0})
		entry["orders"] += 1
		entry["designs"] += cint(row.qty)
	result = sorted(out.values(), key=lambda d: d["orders"], reverse=True)
	return result[:limit] if limit else result


def _pct(part, whole):
	return round(flt(part) * 100.0 / flt(whole), 1) if whole else 0


def _approval_conditions(f, from_date=None, to_date=None):
	where, params = _conditions(f, with_dates=False, with_designer=False)
	extra = ""
	if f.get("designer"):
		extra += " and t.designer = %(designer)s"
		params["designer"] = f.designer
	if from_date:
		extra += " and date(t.creation) >= %(appr_from)s"
		params["appr_from"] = from_date
	if to_date:
		extra += " and date(t.creation) <= %(appr_to)s"
		params["appr_to"] = to_date
	return where, extra, params


def _designer_performance(f):
	where, extra, params = _approval_conditions(f, f.get("from_date"), f.get("to_date"))
	perf = {}

	def entry(designer, name):
		key = designer or name or "__unknown__"
		return perf.setdefault(
			key,
			{
				"designer": designer,
				"name": name or designer or _("Designer not recorded"),
				"rough_approved": 0,
				"rough_rejected": 0,
				"final_approved": 0,
				"final_rejected": 0,
				"final_hold": 0,
				"cmo_approved": 0,
			},
		)

	for r in frappe.db.sql(
		f"""
		select t.designer, t.designer_name, sum(t.approved) as a, sum(t.reject) as rj
		from `tabRough Sketch Approval` t
		join `tabSketch Order` so on so.name = t.parent
		where t.parenttype = 'Sketch Order' and {where} {extra}
		group by t.designer, t.designer_name
		""",
		params,
		as_dict=True,
	):
		e = entry(r.designer, r.designer_name)
		e["rough_approved"] += cint(r.a)
		e["rough_rejected"] += cint(r.rj)

	for r in frappe.db.sql(
		f"""
		select t.designer, t.designer_name, sum(t.approved) as a, sum(t.reject) as rj, sum(t.hold) as h
		from `tabFinal Sketch Approval HOD` t
		join `tabSketch Order` so on so.name = t.parent
		where t.parenttype = 'Sketch Order' and {where} {extra}
		group by t.designer, t.designer_name
		""",
		params,
		as_dict=True,
	):
		e = entry(r.designer, r.designer_name)
		e["final_approved"] += cint(r.a)
		e["final_rejected"] += cint(r.rj)
		e["final_hold"] += cint(r.h)

	for r in frappe.db.sql(
		f"""
		select t.designer, t.designer_name, count(*) as c
		from `tabFinal Sketch Approval CMO` t
		join `tabSketch Order` so on so.name = t.parent
		where t.parenttype = 'Sketch Order' and {where} {extra}
		group by t.designer, t.designer_name
		""",
		params,
		as_dict=True,
	):
		e = entry(r.designer, r.designer_name)
		e["cmo_approved"] += cint(r.c)

	# Why "rough sketch approved" and "final sketch reviewed" differ: per order and
	# designer, rough sketches passed minus final sketches reviewed, grouped by the
	# order's current stage.
	gap_rows = frappe.db.sql(
		f"""
		select x.parent, x.dkey, max(x.dname) as dname, sum(x.rough_pass) as rough_pass,
			sum(x.final_seen) as final_seen, max(so.workflow_state) as workflow_state,
			max(so.docstatus) as docstatus
		from (
			select t.parent, ifnull(t.designer, t.designer_name) as dkey, t.designer_name as dname,
				ifnull(t.approved, 0) as rough_pass, 0 as final_seen
			from `tabRough Sketch Approval` t
			join `tabSketch Order` so on so.name = t.parent
			where t.parenttype = 'Sketch Order' and {where} {extra}
			union all
			select t.parent, ifnull(t.designer, t.designer_name), t.designer_name, 0,
				ifnull(t.approved, 0) + ifnull(t.reject, 0) + ifnull(t.hold, 0)
			from `tabFinal Sketch Approval HOD` t
			join `tabSketch Order` so on so.name = t.parent
			where t.parenttype = 'Sketch Order' and {where} {extra}
		) x
		join `tabSketch Order` so on so.name = x.parent
		group by x.parent, x.dkey
		""",
		params,
		as_dict=True,
	)
	for g in gap_rows:
		missing = cint(g.rough_pass) - cint(g.final_seen)
		if missing <= 0:
			continue
		e = entry(g.dkey if g.dkey != g.dname else None, g.dname)
		b = _bucket(g)
		if b == "cancelled":
			kind = "gap_cancelled"
		elif b in ("draft", "assigned", "rough_hod", "final_hod", "customer_approval", "on_hold"):
			kind = "gap_waiting"
		else:
			kind = "gap_not_taken"
		e[kind] = e.get(kind, 0) + missing

	result = []
	for e in perf.values():
		for k in ("gap_waiting", "gap_cancelled", "gap_not_taken"):
			e.setdefault(k, 0)
		rough_total = e["rough_approved"] + e["rough_rejected"]
		final_total = e["final_approved"] + e["final_rejected"] + e["final_hold"]
		e["rough_total"] = rough_total
		e["final_total"] = final_total
		e["rough_rate"] = _pct(e["rough_approved"], rough_total)
		e["final_rate"] = _pct(e["final_approved"], final_total)
		result.append(e)

	result.sort(key=lambda d: d["rough_total"] + d["final_total"], reverse=True)

	totals = {
		k: sum(e[k] for e in result)
		for k in (
			"rough_approved",
			"rough_rejected",
			"final_approved",
			"final_rejected",
			"final_hold",
			"cmo_approved",
			"gap_waiting",
			"gap_cancelled",
			"gap_not_taken",
		)
	}
	totals["rough_total"] = totals["rough_approved"] + totals["rough_rejected"]
	totals["final_total"] = totals["final_approved"] + totals["final_rejected"] + totals["final_hold"]
	totals["rough_rate"] = _pct(totals["rough_approved"], totals["rough_total"])
	totals["final_rate"] = _pct(totals["final_approved"], totals["final_total"])

	return result, totals


def _monthly_trend(f):
	end = getdate(f.get("to_date") or nowdate())
	start = get_first_day(add_months(end, -11))
	end = get_last_day(end)
	where, extra, params = _approval_conditions(f, start, end)

	months = []
	cursor = start
	while cursor <= end:
		months.append((cursor.year, cursor.month))
		cursor = add_months(cursor, 1)

	def monthly(table, hold=False):
		hold_sql = ", sum(t.hold) as h" if hold else ""
		data = {}
		for r in frappe.db.sql(
			f"""
			select year(t.creation) as y, month(t.creation) as m,
				sum(t.approved) as a, sum(t.reject) as rj {hold_sql}
			from `{table}` t
			join `tabSketch Order` so on so.name = t.parent
			where t.parenttype = 'Sketch Order' and {where} {extra}
			group by year(t.creation), month(t.creation)
			""",
			params,
			as_dict=True,
		):
			data[(cint(r.y), cint(r.m))] = (cint(r.a), cint(r.rj) + (cint(r.h) if hold else 0))
		return data

	rough = monthly("tabRough Sketch Approval")
	final = monthly("tabFinal Sketch Approval HOD", hold=True)

	labels, rough_rate, final_rate, rough_total, final_total = [], [], [], [], []
	for y, m in months:
		labels.append(getdate(f"{y}-{m:02d}-01").strftime("%b %y"))
		ra, rr = rough.get((y, m), (0, 0))
		fa, fr = final.get((y, m), (0, 0))
		rough_rate.append(_pct(ra, ra + rr))
		final_rate.append(_pct(fa, fa + fr))
		rough_total.append(ra + rr)
		final_total.append(fa + fr)

	return {
		"labels": labels,
		"rough_rate": rough_rate,
		"final_rate": final_rate,
		"rough_total": rough_total,
		"final_total": final_total,
	}


def _unusual_approval_rows(f):
	where, extra, params = _approval_conditions(f, f.get("from_date"), f.get("to_date"))
	params["limit_qty"] = UNUSUAL_APPROVAL_ROW
	out = []
	for stage, table, hold_sql in (
		("Rough sketch", "tabRough Sketch Approval", "0"),
		("Final sketch", "tabFinal Sketch Approval HOD", "ifnull(t.hold, 0)"),
	):
		out += frappe.db.sql(
			f"""
			select %(stage)s as stage, t.parent as sketch_order, t.designer, t.designer_name,
				ifnull(t.approved, 0) as approved, ifnull(t.reject, 0) as reject,
				{hold_sql} as hold, date(t.creation) as recorded_on
			from `{table}` t
			join `tabSketch Order` so on so.name = t.parent
			where t.parenttype = 'Sketch Order' and {where} {extra}
				and (ifnull(t.approved, 0) + ifnull(t.reject, 0) + {hold_sql}) >= %(limit_qty)s
			""",
			dict(params, stage=stage),
			as_dict=True,
		)
	out.sort(key=lambda r: cint(r.approved) + cint(r.reject) + cint(r.hold), reverse=True)
	return out[:20]


# Main dashboard data
@frappe.whitelist()
def get_dashboard_data(filters=None, due_soon_days=2):
	f = _parse_filters(filters)

	due_soon_days = max(cint(due_soon_days), 0)
	today = getdate(nowdate())
	due_soon_upper = getdate(add_days(today, due_soon_days))

	rows = _fetch_rows(f)
	amap = _fetch_assignments([r.name for r in rows])

	total_orders = len(rows)
	total_designs = sum(cint(r.qty) for r in rows)

	bucket_orders = {k: 0 for k in BUCKET_ORDER}
	bucket_designs = {k: 0 for k in BUCKET_ORDER}
	for r in rows:
		b = _bucket(r)
		bucket_orders[b] += 1
		bucket_designs[b] += cint(r.qty)
	bucket_states = {key: states for key, _label, states in BUCKETS}
	bucket_states["cancelled"] = bucket_states["cancelled"] + ["any order cancelled after submit"]
	status_summary = [
		{
			"key": k,
			"label": _(BUCKET_LABELS[k]),
			"states": bucket_states.get(k, ["states outside the active workflow"]),
			"orders": bucket_orders[k],
			"designs": bucket_designs[k],
			"pct": _pct(bucket_orders[k], total_orders),
		}
		for k in BUCKET_ORDER
		if k != "other" or bucket_orders[k]
	]

	made_by = {k: {"key": k, "label": _(v), "orders": 0, "designs": 0} for k, v in MADE_BY_LABELS.items()}
	not_assigned_breakdown = {"waiting": 0, "cancelled": 0, "to_check": 0}
	# How Purchase orders split by who made them (explains Purchase vs Supplier counts)
	purchase_split = {"supplier": 0, "designer": 0, "not_assigned": 0}
	for r in rows:
		kind = _made_by(r, amap)
		if r.order_type == "Purchase":
			purchase_split[kind] += 1
		if kind == "not_assigned":
			not_assigned_breakdown[_not_assigned_kind(r)] += 1
		m = made_by[kind]
		m["orders"] += 1
		m["designs"] += cint(r.qty)

	workload = {}
	for r in rows:
		stage = _designer_stage(r)
		seen = set()
		for a in amap.get(r.name, []):
			key = _designer_key(a)
			e = workload.setdefault(
				key,
				{
					"key": key,
					"designer": a.designer,
					"name": a.designer_name or a.designer or _("Unknown"),
					"orders": 0,
					"designs": 0,
					"in_progress": 0,
					"completed": 0,
					"cancelled": 0,
					"stuck": 0,
				},
			)
			e["designs"] += cint(a.count_1)
			if key in seen:
				continue
			seen.add(key)
			e["orders"] += 1
			if stage in ("in_progress", "completed", "cancelled"):
				e[stage] += 1
			if _is_stuck(r, today):
				e["stuck"] += 1
	designer_workload = sorted(workload.values(), key=lambda d: (d["in_progress"], d["orders"]), reverse=True)

	alerts = {
		"due_soon_days": due_soon_days,
		"due_soon": 0,
		"overdue": 0,
		"overdue_7": 0,
		"overdue_30": 0,
		"overdue_old": 0,
	}
	for r in rows:
		risk = _risk(r, today, due_soon_upper)
		if risk == "overdue":
			alerts["overdue"] += 1
			alerts[_overdue_age(r, today)] += 1
		elif risk == "due_soon":
			alerts["due_soon"] += 1

	matrix = {}
	for r in rows:
		cat = r.category or NOT_SET
		b = _bucket(r)
		m = matrix.setdefault(cat, {"category": cat, "cells": {}, "total": 0})
		m["cells"][b] = m["cells"].get(b, 0) + 1
		m["total"] += 1
	matrix_columns = [k for k in BUCKET_ORDER if bucket_orders[k]]
	category_status_matrix = {
		"columns": [{"key": k, "label": _(BUCKET_LABELS[k])} for k in matrix_columns],
		"rows": sorted(matrix.values(), key=lambda d: d["total"], reverse=True),
		"column_totals": {k: bucket_orders[k] for k in matrix_columns},
		"grand_total": total_orders,
	}

	performance, performance_totals = _designer_performance(f)
	unusual = _unusual_approval_rows(f)
	unusual_designers = {u.designer or u.designer_name for u in unusual}
	for p in performance:
		p["unusual"] = (p["designer"] or p["name"]) in unusual_designers

	own_prefix = _own_prefix(f.company)
	own_labels = {
		_customer_label(r)
		for r in rows
		if own_prefix and (r.customer_name or "").lower().startswith(own_prefix)
	}
	top_customers = _breakdown(rows, _customer_label, limit=10)
	for c in top_customers:
		c["own"] = c["key"] in own_labels

	no_maker = sum(
		1
		for r in rows
		if _made_by(r, amap) == "not_assigned" and _bucket(r) not in ("draft", "cancelled", "on_hold")
	)
	top_suppliers = _breakdown([r for r in rows if _made_by(r, amap) == "supplier"], _supplier_label, limit=10)
	wrong_labels = {_supplier_label(r) for r in rows if _wrong_supplier(r)}
	for sp in top_suppliers:
		sp["warn"] = sp["key"] in wrong_labels

	data_health = {
		"cancelled_not_closed": sum(1 for r in rows if _health_kind(r) == "cancelled_not_closed"),
		"approved_but_cancelled": sum(1 for r in rows if _health_kind(r) == "approved_but_cancelled"),
		"wrong_supplier": sum(1 for r in rows if _wrong_supplier(r)),
		"wrong_supplier_groups": sorted({r.supplier_group or "No group" for r in rows if _wrong_supplier(r)}),
		"old_workflow": bucket_orders["old_workflow"],
		"no_maker": no_maker,
		"other_state": bucket_orders["other"],
		"unusual_approvals": unusual,
	}

	categories = frappe.db.sql_list(
		"""
		select distinct category from `tabSketch Order`
		where company = %(company)s and ifnull(category, '') != ''
		order by category
		""",
		{"company": f.company},
	)

	return {
		"total_orders": total_orders,
		"total_designs": total_designs,
		"status_summary": status_summary,
		"made_by": list(made_by.values()),
		"not_assigned_breakdown": not_assigned_breakdown,
		"purchase_split": purchase_split,
		"order_types": _breakdown(rows, lambda r: r.order_type),
		"designer_workload": designer_workload,
		"alerts": alerts,
		"category_status_matrix": category_status_matrix,
		"design_types": _breakdown(rows, lambda r: r.design_type),
		"flow_types": _breakdown(rows, lambda r: r.flow_type),
		"top_suppliers": top_suppliers,
		"top_customers": top_customers,
		"performance": performance,
		"performance_totals": performance_totals,
		"trend": _monthly_trend(f),
		"data_health": data_health,
		"categories": categories,
		"generated_at": frappe.utils.now(),
	}


# Orders behind a clicked number (drill-down)
@frappe.whitelist()
def get_segment_orders(filters=None, segment=None, due_soon_days=2):
	f = _parse_filters(filters)
	segment = frappe._dict(frappe.parse_json(segment) if isinstance(segment, str) else (segment or {}))
	seg_type = segment.get("type")

	due_soon_days = max(cint(due_soon_days), 0)
	today = getdate(nowdate())
	due_soon_upper = getdate(add_days(today, due_soon_days))

	rows = _fetch_rows(f)
	amap = _fetch_assignments([r.name for r in rows])

	def keep(r):
		if seg_type == "total":
			return True
		if seg_type == "bucket":
			return _bucket(r) == segment.key
		if seg_type == "made_by":
			return _made_by(r, amap) == segment.key
		if seg_type == "not_assigned":
			return _made_by(r, amap) == "not_assigned" and _not_assigned_kind(r) == segment.key
		if seg_type == "order_type":
			return (r.order_type or NOT_SET) == segment.key
		if seg_type == "design_type":
			return (r.design_type or NOT_SET) == segment.key
		if seg_type == "flow_type":
			return (r.flow_type or NOT_SET) == segment.key
		if seg_type == "supplier":
			return _made_by(r, amap) == "supplier" and _supplier_label(r) == segment.key
		if seg_type == "customer":
			return _customer_label(r) == segment.key
		if seg_type == "alert":
			risk = _risk(r, today, due_soon_upper)
			if segment.key in ("overdue_7", "overdue_30", "overdue_old"):
				return risk == "overdue" and _overdue_age(r, today) == segment.key
			return risk == segment.key
		if seg_type == "matrix":
			if segment.get("category") and (r.category or NOT_SET) != segment.category:
				return False
			if segment.get("bucket") and _bucket(r) != segment.bucket:
				return False
			return True
		if seg_type == "designer":
			keys = {_designer_key(a) for a in amap.get(r.name, [])}
			if segment.key not in keys:
				return False
			metric = segment.get("metric") or "orders"
			if metric == "stuck":
				return _is_stuck(r, today)
			return metric == "orders" or _designer_stage(r) == metric
		if seg_type == "health":
			if segment.key == "wrong_supplier":
				return _wrong_supplier(r)
			if segment.key in ("cancelled_not_closed", "approved_but_cancelled"):
				return _health_kind(r) == segment.key
			if segment.key == "old_workflow":
				return _bucket(r) == "old_workflow"
			if segment.key == "no_maker":
				return _made_by(r, amap) == "not_assigned" and _bucket(r) not in (
					"draft",
					"cancelled",
					"on_hold",
				)
			if segment.key == "other_state":
				return _bucket(r) == "other"
		return False

	selected = [r for r in rows if keep(r)]
	selected.sort(key=lambda r: (r.due_date or getdate("1900-01-01"), r.name), reverse=True)

	out = []
	for r in selected[:1000]:
		designers = ", ".join(
			sorted({a.designer_name or a.designer for a in amap.get(r.name, []) if (a.designer_name or a.designer)})
		)
		out.append(
			{
				"name": r.name,
				"status": (
					f"{r.workflow_state} (document cancelled)"
					if cint(r.docstatus) == 2 and r.workflow_state != "Cancelled"
					else r.workflow_state
				),
				"customer": _customer_label(r),
				"category": r.category,
				"designs": cint(r.qty),
				"made_by": designers or (_supplier_label(r) if r.supplier else ""),
				"due_date": r.due_date,
			}
		)

	return {"total": len(selected), "orders": out}