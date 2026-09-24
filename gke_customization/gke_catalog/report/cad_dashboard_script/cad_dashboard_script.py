# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, nowdate

# ---------------------------------------------------------------------------
# Per-user tab access for the CAD Dashboard's setting-type tabs (All / Open
# Setting / Nova Glow / Close-Open Setting). Hardcoded on purpose - no
# doctype/UI for this; update TAB_ACCESS_MAP / ROLE_TAB_ACCESS below and
# redeploy to change who sees what. A user with no matching email and no
# matching role gets none of the tabs.
# ---------------------------------------------------------------------------

ALL_TABS = {"all", "open_setting", "nova_glow", "close_open_setting"}

TAB_ACCESS_MAP = {
	"chirag_t@gkexport.com": set(ALL_TABS),
	"kaushik_g@gkexport.com": set(ALL_TABS),
	"sandeep_m@gkexport.com": set(ALL_TABS),
	"gr@gkexport.com": set(ALL_TABS),
	"arun_l@gkexport.com": {"nova_glow"},
	"ashish_m@gkexport.com": {"open_setting"},
}

ROLE_TAB_ACCESS = {
	"System Manager": set(ALL_TABS),
	"Computer Aided Designer - ST - GE": set(ALL_TABS),
	"Designer": set(ALL_TABS),
	"CAD Hod": set(ALL_TABS),
	"Coordinator - ST - GE": set(ALL_TABS),
}


def _allowed_tabs(user):
	"""Priority order:
	1. Administrator / System Manager -> every tab, always.
	2. A user listed in TAB_ACCESS_MAP -> exactly the tabs listed there
	   (this overrides role-based access, so e.g. a CAD Hod listed with only
	   "nova_glow" does NOT also inherit the CAD Hod role's all-tabs access).
	3. Everyone else -> union of the tabs granted by their roles.
	"""
	if user == "Administrator":
		return set(ALL_TABS)

	roles = set(frappe.get_roles(user))
	if "System Manager" in roles:
		return set(ALL_TABS)

	if user in TAB_ACCESS_MAP:
		return set(TAB_ACCESS_MAP[user])

	allowed = set()
	for role in roles:
		allowed |= ROLE_TAB_ACCESS.get(role, set())
	return allowed


# ---------------------------------------------------------------------------
# Per-user designer scoping. A regular designer must only ever see their own
# row(s) in the dashboard/matrix - never every designer's data. Users holding
# any role in DESIGNER_SCOPE_EXEMPT_ROLES (and Administrator) are exempt and
# may view/filter across all designers as before. This is enforced here,
# server-side, by overriding whatever `designer` value the client sent -
# never trusting the client-supplied filter for non-exempt users.
# ---------------------------------------------------------------------------

DESIGNER_SCOPE_EXEMPT_ROLES = {
	"System Manager",
	"Director",
	"CEO",
	"Branch Manager",
	"Department Manager",
	"CAD Hod",
	"Coordinator - ST - GE",
}


def _designer_scope_for_session():
	"""Employee ID to restrict designer-keyed views to, or None if the
	current session is exempt (Administrator / management role) and should
	see every designer's data unrestricted.
	"""
	user = frappe.session.user
	if user == "Administrator" or (DESIGNER_SCOPE_EXEMPT_ROLES & set(frappe.get_roles(user))):
		return None

	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	return employee or "__no_designer_match__"


def _scope_assignments(assignments_by_order, designer_scope):
	"""Drop co-assignees from each order's assignment list when a designer
	scope is active.

	`_fetch_filtered_rows` only guarantees the scoped designer is *one of*
	an order's assignees (via EXISTS) - an order can carry more than one
	designer row. Without this step, any designer-keyed view built from
	`assignments_by_order` (workload table, designer matrices, drill-downs)
	would still show every co-assignee on a shared order, leaking other
	designers' names/counts to a restricted session. When no scope is
	active (exempt users), the assignments are returned unchanged.
	"""
	if designer_scope is None:
		return assignments_by_order
	scoped = {}
	for order_name, assignments in assignments_by_order.items():
		matched = [a for a in assignments if a.designer == designer_scope]
		if matched:
			scoped[order_name] = matched
	return scoped


def _tab_key_for_filters(setting_type, sub_setting_type1):
	if sub_setting_type1 == "Close-Open Setting":
		return "close_open_setting"
	if setting_type == "Open":
		return "open_setting"
	if setting_type == "Nova Glow":
		return "nova_glow"
	return "all"


def _enforce_tab_access(setting_type, sub_setting_type1):
	tab_key = _tab_key_for_filters(setting_type, sub_setting_type1)
	if tab_key not in _allowed_tabs(frappe.session.user):
		frappe.throw(_("You are not permitted to view this tab."), frappe.PermissionError)


@frappe.whitelist()
def get_my_tab_access():
	allowed = _allowed_tabs(frappe.session.user)
	return {
		"allow_all": "all" in allowed,
		"allow_open_setting": "open_setting" in allowed,
		"allow_nova_glow": "nova_glow" in allowed,
		"allow_close_open_setting": "close_open_setting" in allowed,
	}


@frappe.whitelist()
def get_my_matrix_view_access():
	"""Whether the current session should be locked to the Status x Category
	matrix view only.

	`get_dashboard_data` already scopes the designer/customer-keyed matrices
	to the session's own data for a restricted user (see
	`_designer_scope_for_session` / `_scope_assignments`), so there is no
	data leak in what those matrices contain. This is a separate, UI-level
	policy on top of that: a plain Designer-role user should never even be
	offered the option to switch into the Designer/Customer-keyed views -
	only the aggregate Status x Category view. Management (anyone exempt
	from designer scoping) may freely switch between all views.
	"""
	return {"restrict_to_status": _designer_scope_for_session() is not None}


# ---------------------------------------------------------------------------
# CAD Dashboard (page) data API.
#
# Source doctype: `Order` (module "GKE Order Forms"), filtered to
# bom_or_cad = 'CAD' - the flag actually used in production data to mark a
# row as a CAD design order (workflow_type = 'CAD' is a newer/parallel field
# that is only populated on a small subset of rows, so bom_or_cad is the
# reliable filter).
#
# `Order.workflow_state` drives the CAD design workflow. States are grouped
# into buckets for the KPI strip:
#   - pending          : Draft, Un-assigned              (not yet picked up)
#   - assigned         : Assigned
#   - assigned_on_hold : Assigned - On-Hold
#   - designing        : Designing
#   - designing_on_hold: Designing - On-Hold
#   - rework           : Design Rework in Progress
#   - qc               : Sent to QC, Sent to QC - On-Hold
#   - approved         : Approved                        (CAD design signed off)
#   - rejected         : Rejected, Cancelled, Customer Design Rejected
#   - bom_stage        : everything else (Update BOM, Update Item, Creating BOM,
#                        BOM QC, Customer Approval, ...) - the order has moved on
#                        past the CAD design stage into BOM creation/QC, but is
#                        still tagged bom_or_cad = 'CAD' since that field is not
#                        revised once set.
#
# Designer is read from the `designer_assignment` child table
# (Designer Assignment - CAD: designer [Employee], designer_name). An order
# can have zero or more designer rows (e.g. still Un-assigned); each row is
# counted once per order for workload purposes, keyed by designer_name.
#
# Due date for alerts is COALESCE(cad_delivery_date, delivery_date) - the
# CAD-specific delivery date field is only populated for a subset of orders,
# so the general delivery_date is used as a fallback. Orders already in a
# terminal state (Approved / Rejected / Cancelled) are excluded from alerts.
#
# `get_dashboard_data` returns only counts/sums - never the underlying order
# names - so the payload stays small regardless of how many orders match a
# given segment. When the UI needs the actual order list for one number
# (a KPI tile, a designer stat, an alert, a matrix cell/row/column/total),
# it calls `get_segment_orders` with a `segment` descriptor identifying that
# one number; the same row-fetch + classification helpers below are reused
# to resolve just that segment on demand, so results always match exactly
# what's displayed without ever materializing every segment's order list.
# ---------------------------------------------------------------------------

PENDING_STATES = ["Draft", "Un-assigned"]
ASSIGNED_STATES = ["Assigned"]
ASSIGNED_ON_HOLD_STATES = ["Assigned - On-Hold"]
DESIGNING_STATES = ["Designing"]
DESIGNING_ON_HOLD_STATES = ["Designing - On-Hold"]
REWORK_STATES = ["Design Rework in Progress"]
QC_STATES = ["Sent to QC", "Sent to QC - On-Hold"]
APPROVED_STATES = ["Approved"]
REJECTED_STATES = ["Rejected", "Cancelled", "Customer Design Rejected"]
TERMINAL_STATES = APPROVED_STATES + REJECTED_STATES

BUCKET_STATES = {
	"pending": PENDING_STATES,
	"assigned": ASSIGNED_STATES,
	"assigned_on_hold": ASSIGNED_ON_HOLD_STATES,
	"designing": DESIGNING_STATES,
	"designing_on_hold": DESIGNING_ON_HOLD_STATES,
	"rework": REWORK_STATES,
	"qc": QC_STATES,
	"approved": APPROVED_STATES,
	"rejected": REJECTED_STATES,
}

BUCKET_LABELS = {
	"pending": "Draft",
	"assigned": "Assigned",
	"assigned_on_hold": "Assigned - On Hold",
	"designing": "Designing",
	"designing_on_hold": "Designing - On Hold",
	"rework": "Rework",
	"qc": "Sent to QC",
	"approved": "Approved",
	"rejected": "Rejected / Cancelled",
	"bom_stage": "Moved to BOM Stage",
}

STATUS_ROW_ORDER = [
	"pending",
	"assigned",
	"assigned_on_hold",
	"designing",
	"designing_on_hold",
	"rework",
	"qc",
	"approved",
	"rejected",
	"bom_stage",
]

UNCATEGORIZED = _("Uncategorized")


def execute(filters=None):
	filters = filters or {}
	company = filters.get("company")
	conditions = ["o.bom_or_cad = 'CAD'", "o.docstatus != 2"]
	params = {}
	if company:
		conditions.append("o.company = %(company)s")
		params["company"] = company
	where = " AND ".join(conditions)

	rows = frappe.db.sql(
		f"""
		SELECT o.workflow_state AS workflow_state, COUNT(*) AS count
		FROM `tabOrder` o
		WHERE {where}
		GROUP BY o.workflow_state
		""",
		params,
		as_dict=True,
	)

	state_counts = {row.workflow_state: row.count for row in rows}
	data = []
	accounted_states = set()
	for bucket, states in BUCKET_STATES.items():
		count = sum(state_counts.get(state, 0) for state in states)
		accounted_states.update(states)
		data.append({"bucket": BUCKET_LABELS[bucket], "count": count})

	other_count = sum(count for state, count in state_counts.items() if state not in accounted_states)
	data.append({"bucket": BUCKET_LABELS["bom_stage"], "count": other_count})

	return get_columns(), data


def get_columns():
	return [
		{"label": _("Status"), "fieldname": "bucket", "fieldtype": "Data", "width": 220},
		{"label": _("Count"), "fieldname": "count", "fieldtype": "Int", "width": 100},
	]


def _build_extra_filter(
	designer=None,
	from_date=None,
	to_date=None,
	setting_type=None,
	category=None,
	sub_setting_type1=None,
	customer=None,
	branch=None,
	department=None,
	assigned_to=None,
):
	conditions = []
	params = {}
	if designer:
		conditions.append(
			"EXISTS (SELECT 1 FROM `tabDesigner Assignment - CAD` da "
			"WHERE da.parent = o.name AND da.designer = %(designer)s)"
		)
		params["designer"] = designer
	if assigned_to:
		# Standard Frappe "Assigned To" - `_assign` stores a JSON array of user
		# emails, so this mirrors the same LIKE match the list view/report view
		# use for their built-in Assigned To filter.
		conditions.append("o._assign LIKE %(assigned_to)s")
		params["assigned_to"] = f'%"{assigned_to}"%'
	if customer:
		conditions.append("o.customer_code = %(customer)s")
		params["customer"] = customer
	if branch:
		conditions.append("o.branch = %(branch)s")
		params["branch"] = branch
	if department:
		conditions.append("o.department = %(department)s")
		params["department"] = department
	if from_date:
		conditions.append("o.order_date >= %(from_date)s")
		params["from_date"] = getdate(from_date)
	if to_date:
		# order_date is a Datetime field - a plain "<= to_date" only matches
		# midnight of to_date and silently drops every later timestamp that
		# same day, so use an exclusive bound on the following day instead.
		conditions.append("o.order_date < %(to_date)s")
		params["to_date"] = add_days(getdate(to_date), 1)
	if setting_type:
		conditions.append("o.setting_type = %(setting_type)s")
		params["setting_type"] = setting_type
	if category:
		conditions.append("o.category = %(category)s")
		params["category"] = category
	if sub_setting_type1:
		conditions.append("o.sub_setting_type1 = %(sub_setting_type1)s")
		params["sub_setting_type1"] = sub_setting_type1
	extra_sql = ("\n\t\tAND " + "\n\t\tAND ".join(conditions)) if conditions else ""
	return extra_sql, params


def _fetch_filtered_rows(
	company,
	designer=None,
	from_date=None,
	to_date=None,
	setting_type=None,
	category=None,
	sub_setting_type1=None,
	customer=None,
	branch=None,
	department=None,
	assigned_to=None,
):
	extra_filter, extra_params = _build_extra_filter(
		designer=designer,
		from_date=from_date,
		to_date=to_date,
		setting_type=setting_type,
		category=category,
		sub_setting_type1=sub_setting_type1,
		customer=customer,
		branch=branch,
		department=department,
		assigned_to=assigned_to,
	)
	params = {"company": company, **extra_params}
	return frappe.db.sql(
		f"""
		SELECT
			o.name AS name,
			o.workflow_state AS workflow_state,
			o.category AS category,
			o.qty AS qty,
			o.order_type AS order_type,
			o.design_type AS design_type,
			cust.customer_name AS customer_name,
			COALESCE(o.cad_delivery_date, o.delivery_date) AS due_date
		FROM `tabOrder` o
		LEFT JOIN `tabCustomer` cust ON cust.name = o.customer_code
		WHERE o.bom_or_cad = 'CAD'
			AND o.docstatus != 2
			AND o.company = %(company)s
			{extra_filter}
		""",
		params,
		as_dict=True,
	)


def _fetch_assignments_by_order(order_names):
	if not order_names:
		return {}
	assignment_rows = frappe.db.sql(
		"""
		SELECT parent, designer, designer_name
		FROM `tabDesigner Assignment - CAD`
		WHERE parent IN %(order_names)s
		""",
		{"order_names": order_names},
		as_dict=True,
	)
	assignments_by_order = {}
	for a in assignment_rows:
		assignments_by_order.setdefault(a.parent, []).append(a)
	return assignments_by_order


def _bucket_of(state):
	for bucket, states in BUCKET_STATES.items():
		if state in states:
			return bucket
	return "bom_stage"


def _classify_stock(row):
	"""Which row-3 KPI segment (if any) this order's Stock/Sales split falls under."""
	is_gk = (row.customer_name or "").startswith("Gurukrupa Export")
	if row.order_type == "Stock Order":
		return "gk_stock" if is_gk else "customer_stock"
	if row.order_type == "Sales" and not is_gk:
		return "customer_order"
	return None


def _designer_row_keys(row, assignments_by_order):
	designers = assignments_by_order.get(row.name)
	if designers:
		return [(a.designer or "__unassigned__", a.designer_name or a.designer) for a in designers]
	return [("__unassigned__", _("Unassigned"))]


def _status_row_keys(row):
	bucket = _bucket_of(row.workflow_state)
	return [(bucket, _(BUCKET_LABELS[bucket]))]


def _customer_row_keys(row):
	customer = row.customer_name or _("Unknown Customer")
	return [(customer, customer)]


def _apply_matrix_filter(rows, matrix_filter, status_filter=None):
	"""Narrow the matrix (only) to one Stock/Sales split and/or one status bucket.

	Independent of the Designer/Status view toggle - either can be combined
	with either view. Neither touches the KPI strip, designer workload, or
	alerts sections, which always reflect the full filtered order set.
	"""
	if matrix_filter in ("gk_stock", "customer_stock", "customer_order"):
		rows = [row for row in rows if _classify_stock(row) == matrix_filter]
	if status_filter:
		rows = [row for row in rows if _bucket_of(row.workflow_state) == status_filter]
	return rows


def _new_matrix_metric():
	return {"qty": 0, "overdue": 0, "due_soon": 0}


def _add_matrix_metric(target, qty, risk):
	target["qty"] += qty
	if risk:
		target[risk] += 1


def _category_columns(row):
	category = row.category or UNCATEGORIZED
	return [(category, category)]


def _status_columns(row):
	bucket = _bucket_of(row.workflow_state)
	return [(bucket, _(BUCKET_LABELS[bucket]))]


def _build_matrix(source_rows, row_keys_fn, column_keys_fn, risk_of):
	"""Generic "matrix row x column" qty builder (counts/sums only - no order
	names; those are resolved on demand by `get_segment_orders`).

	`row_keys_fn(row)` / `column_keys_fn(row)` each return a list of (key,
	label) pairs identifying which matrix row(s)/column(s) this order
	contributes to - a list since one order can map to more than one
	designer (multi-designer orders are counted once per designer), but
	exactly one category and exactly one status. The row/column/grand
	totals are summed straight from the same cells built below, so the
	displayed totals always foot exactly against the rows and columns shown
	- even where an order is counted more than once.

	`risk_of(row)` returns "overdue" / "due_soon" / None, tallied alongside
	qty on every cell so the matrix can flag risk (a small dot) without ever
	shipping the underlying order names - just two extra counts per cell.
	"""
	matrix_rows = {}
	column_labels = {}
	for row in source_rows:
		qty = flt(row.qty)
		risk = risk_of(row)
		col_keys = column_keys_fn(row)
		for col_key, col_label in col_keys:
			column_labels[col_key] = col_label
		for key, label in row_keys_fn(row):
			m_row = matrix_rows.setdefault(key, {"key": key, "name": label, "cells": {}, "total": _new_matrix_metric()})
			for col_key, _col_label in col_keys:
				cell = m_row["cells"].setdefault(col_key, _new_matrix_metric())
				_add_matrix_metric(cell, qty, risk)
			_add_matrix_metric(m_row["total"], qty, risk)

	column_totals = {}
	grand_total = _new_matrix_metric()
	for m_row in matrix_rows.values():
		for col_key, cell in m_row["cells"].items():
			col_total = column_totals.setdefault(col_key, _new_matrix_metric())
			col_total["qty"] += cell["qty"]
			col_total["overdue"] += cell["overdue"]
			col_total["due_soon"] += cell["due_soon"]
		grand_total["qty"] += m_row["total"]["qty"]
		grand_total["overdue"] += m_row["total"]["overdue"]
		grand_total["due_soon"] += m_row["total"]["due_soon"]

	return matrix_rows, column_totals, grand_total, column_labels


@frappe.whitelist()
def get_dashboard_data(
	company=None,
	due_soon_days=2,
	designer=None,
	from_date=None,
	to_date=None,
	setting_type=None,
	category=None,
	matrix_filter=None,
	sub_setting_type1=None,
	status_filter=None,
	customer=None,
	branch=None,
	department=None,
	assigned_to=None,
):
	if not company:
		frappe.throw(_("Please select a Company"))

	_enforce_tab_access(setting_type, sub_setting_type1)
	designer_scope = _designer_scope_for_session()
	if designer_scope is not None:
		designer = designer_scope

	due_soon_days = cint(due_soon_days)
	if due_soon_days < 0:
		due_soon_days = 0
	due_soon_upper = add_days(nowdate(), due_soon_days)

	rows = _fetch_filtered_rows(
		company,
		designer,
		from_date,
		to_date,
		setting_type,
		category,
		sub_setting_type1,
		customer=customer,
		branch=branch,
		department=department,
		assigned_to=assigned_to,
	)
	assignments_by_order = _fetch_assignments_by_order([row.name for row in rows])
	assignments_by_order = _scope_assignments(assignments_by_order, designer_scope)

	# ---- status summary ----
	status_counts = {key: 0 for key in list(BUCKET_STATES.keys()) + ["bom_stage"]}
	for row in rows:
		status_counts[_bucket_of(row.workflow_state)] += 1

	status_summary = [
		{"key": bucket, "label": _(BUCKET_LABELS[bucket]), "count": status_counts[bucket]}
		for bucket in STATUS_ROW_ORDER
	]
	total_orders = len(rows)

	# ---- Assigned to Designer ----
	# `workflow_state = 'Assigned'` is just a status label an order can carry
	# without ever having an actual row in the Designer Assignment - CAD child
	# table (e.g. moved to "Assigned" manually before a designer was picked).
	# This KPI instead counts orders that genuinely have >= 1 designer row
	# with a non-blank `designer`, independent of workflow_state.
	assigned_to_designer_count = sum(
		1 for row in rows if any(a.designer for a in assignments_by_order.get(row.name, []))
	)

	# ---- GK Stock / Customer Stock / Customer Order ----
	stock_counts = {"gk_stock": 0, "customer_stock": 0, "customer_order": 0}
	for row in rows:
		key = _classify_stock(row)
		if key:
			stock_counts[key] += 1

	# ---- designer workload ----
	designer_map = {}
	for row in rows:
		bucket = _bucket_of(row.workflow_state)
		is_active = bucket not in ("approved", "rejected", "bom_stage")
		is_completed = bucket == "approved"
		for designer_id, designer_name in _designer_row_keys(row, assignments_by_order):
			entry = designer_map.setdefault(
				designer_id,
				{"designer": designer_id if designer_id != "__unassigned__" else None, "name": designer_name, "count": 0, "in_progress": 0, "completed": 0},
			)
			entry["count"] += 1
			if is_completed:
				entry["completed"] += 1
			elif is_active:
				entry["in_progress"] += 1

	designers_workload = sorted(designer_map.values(), key=lambda d: d["count"], reverse=True)

	# ---- shared risk classification (used by both the matrices' dots below
	# and the due-date alerts) ----
	def risk_of(row):
		bucket = _bucket_of(row.workflow_state)
		if bucket in ("approved", "rejected") or not row.due_date:
			return None
		due_date = getdate(row.due_date)
		if due_date < getdate(nowdate()):
			return "overdue"
		if due_date <= getdate(due_soon_upper):
			return "due_soon"
		return None

	# ---- designer x category / status x category qty matrices ----
	# `matrix_filter` and `status_filter` narrow just these tables - to one of
	# the row-3 KPI segments (GK Stock / Customer Stock / Customer Order)
	# and/or one status bucket - without touching any of the other sections
	# above, which always reflect the full filtered order set.
	matrix_source_rows = _apply_matrix_filter(rows, matrix_filter, status_filter)

	d_rows, d_category_totals, d_grand_total, _d_labels = _build_matrix(
		matrix_source_rows, lambda row: _designer_row_keys(row, assignments_by_order), _category_columns, risk_of
	)
	d_categories = sorted(d_category_totals.keys(), key=lambda c: d_category_totals[c]["qty"], reverse=True)
	designer_category_matrix = {
		"categories": d_categories,
		"category_labels": {c: c for c in d_categories},
		"rows": sorted(d_rows.values(), key=lambda r: r["total"]["qty"], reverse=True),
		"category_totals": d_category_totals,
		"grand_total": d_grand_total,
	}

	# Every order has exactly one status (unlike designers, never double-counted).
	# Rows are always shown in the same pipeline order as the KPI strip -
	# including zero-count buckets - so the table shape stays stable regardless
	# of what's currently filtered.
	s_rows, s_category_totals, s_grand_total, _s_labels = _build_matrix(
		matrix_source_rows, _status_row_keys, _category_columns, risk_of
	)
	s_categories = sorted(s_category_totals.keys(), key=lambda c: s_category_totals[c]["qty"], reverse=True)
	for bucket in STATUS_ROW_ORDER:
		s_rows.setdefault(
			bucket, {"key": bucket, "name": _(BUCKET_LABELS[bucket]), "cells": {}, "total": _new_matrix_metric()}
		)
	status_category_matrix = {
		"categories": s_categories,
		"category_labels": {c: c for c in s_categories},
		"rows": [s_rows[bucket] for bucket in STATUS_ROW_ORDER],
		"category_totals": s_category_totals,
		"grand_total": s_grand_total,
	}

	# Designer x Status (Qty) - rows are designers, columns are the same
	# fixed status-bucket pipeline order as the KPI strip (not sorted by
	# qty), so the table shape stays stable regardless of what's filtered.
	ds_rows, ds_column_totals, ds_grand_total, _ds_labels = _build_matrix(
		matrix_source_rows, lambda row: _designer_row_keys(row, assignments_by_order), _status_columns, risk_of
	)
	designer_status_matrix = {
		"categories": STATUS_ROW_ORDER,
		"category_labels": {bucket: _(BUCKET_LABELS[bucket]) for bucket in STATUS_ROW_ORDER},
		"rows": sorted(ds_rows.values(), key=lambda r: r["total"]["qty"], reverse=True),
		"category_totals": ds_column_totals,
		"grand_total": ds_grand_total,
	}

	c_rows, c_category_totals, c_grand_total, _c_labels = _build_matrix(
		matrix_source_rows, _customer_row_keys, _category_columns, risk_of
	)
	c_categories = sorted(c_category_totals.keys(), key=lambda c: c_category_totals[c]["qty"], reverse=True)
	customer_category_matrix = {
		"categories": c_categories,
		"category_labels": {c: c for c in c_categories},
		"rows": sorted(c_rows.values(), key=lambda r: r["total"]["qty"], reverse=True),
		"category_totals": c_category_totals,
		"grand_total": c_grand_total,
	}

	# Customer x Status (Qty) - rows are customers, columns are the same
	# fixed status-bucket pipeline order as the KPI strip (not sorted by
	# qty), so the table shape stays stable regardless of what's filtered.
	cs_rows, cs_column_totals, cs_grand_total, _cs_labels = _build_matrix(
		matrix_source_rows, _customer_row_keys, _status_columns, risk_of
	)
	customer_status_matrix = {
		"categories": STATUS_ROW_ORDER,
		"category_labels": {bucket: _(BUCKET_LABELS[bucket]) for bucket in STATUS_ROW_ORDER},
		"rows": sorted(cs_rows.values(), key=lambda r: r["total"]["qty"], reverse=True),
		"category_totals": cs_column_totals,
		"grand_total": cs_grand_total,
	}

	# ---- due-date alerts ----
	due_soon_count = 0
	overdue_count = 0
	for row in rows:
		risk = risk_of(row)
		if risk == "overdue":
			overdue_count += 1
		elif risk == "due_soon":
			due_soon_count += 1

	# ---- design type breakdown ----
	design_type_map = {}
	for row in rows:
		key = row.design_type or None
		label = row.design_type or _("Unspecified")
		entry = design_type_map.setdefault(key, {"design_type": key, "label": label, "count": 0})
		entry["count"] += 1
	design_types = sorted(design_type_map.values(), key=lambda d: d["count"], reverse=True)

	return {
		"total_orders": total_orders,
		"gk_stock": {"count": stock_counts["gk_stock"]},
		"customer_stock": {"count": stock_counts["customer_stock"]},
		"customer_order": {"count": stock_counts["customer_order"]},
		"assigned_to_designer": {"count": assigned_to_designer_count},
		"status_summary": status_summary,
		"designers": designers_workload,
		"designer_category_matrix": designer_category_matrix,
		"status_category_matrix": status_category_matrix,
		"designer_status_matrix": designer_status_matrix,
		"customer_category_matrix": customer_category_matrix,
		"customer_status_matrix": customer_status_matrix,
		"alerts": {
			"due_soon": {"days": due_soon_days, "count": due_soon_count},
			"overdue": {"count": overdue_count},
		},
		"design_types": design_types,
		"generated_at": frappe.utils.now(),
	}


@frappe.whitelist()
def get_segment_orders(
	company=None,
	due_soon_days=2,
	designer=None,
	from_date=None,
	to_date=None,
	setting_type=None,
	category=None,
	matrix_filter=None,
	sub_setting_type1=None,
	status_filter=None,
	segment=None,
	customer=None,
	branch=None,
	department=None,
	assigned_to=None,
):
	"""Resolve the order names behind exactly one displayed number.

	Re-runs the same filtered row fetch as `get_dashboard_data` (never cached
	between the two calls, so this is always consistent with what's on screen)
	and applies just the one classification needed for `segment`, instead of
	every dashboard section's order list being computed and shipped upfront.
	"""
	if not company:
		frappe.throw(_("Please select a Company"))

	_enforce_tab_access(setting_type, sub_setting_type1)
	designer_scope = _designer_scope_for_session()
	if designer_scope is not None:
		designer = designer_scope

	segment = frappe.parse_json(segment) if isinstance(segment, str) else (segment or {})
	seg_type = segment.get("type")

	due_soon_days = cint(due_soon_days)
	if due_soon_days < 0:
		due_soon_days = 0
	due_soon_upper = add_days(nowdate(), due_soon_days)

	rows = _fetch_filtered_rows(
		company,
		designer,
		from_date,
		to_date,
		setting_type,
		category,
		sub_setting_type1,
		customer=customer,
		branch=branch,
		department=department,
		assigned_to=assigned_to,
	)

	if seg_type == "total":
		return sorted(row.name for row in rows)

	if seg_type == "status_bucket":
		bucket = segment.get("bucket")
		return sorted(row.name for row in rows if _bucket_of(row.workflow_state) == bucket)

	if seg_type == "stock_split":
		key = segment.get("key")
		return sorted(row.name for row in rows if _classify_stock(row) == key)

	if seg_type == "assigned_to_designer":
		assignments_by_order = _fetch_assignments_by_order([row.name for row in rows])
		assignments_by_order = _scope_assignments(assignments_by_order, designer_scope)
		return sorted(
			row.name for row in rows if any(a.designer for a in assignments_by_order.get(row.name, []))
		)

	if seg_type == "designer":
		assignments_by_order = _fetch_assignments_by_order([row.name for row in rows])
		assignments_by_order = _scope_assignments(assignments_by_order, designer_scope)
		designer_key = segment.get("designer_key")
		metric = segment.get("metric", "total")
		names = []
		for row in rows:
			keys = [key for key, _label in _designer_row_keys(row, assignments_by_order)]
			if designer_key not in keys:
				continue
			bucket = _bucket_of(row.workflow_state)
			is_active = bucket not in ("approved", "rejected", "bom_stage")
			is_completed = bucket == "approved"
			if metric == "total" or (metric == "completed" and is_completed) or (metric == "in_progress" and is_active):
				names.append(row.name)
		return sorted(names)

	if seg_type == "designer_status":
		assignments_by_order = _fetch_assignments_by_order([row.name for row in rows])
		assignments_by_order = _scope_assignments(assignments_by_order, designer_scope)
		designer_key = segment.get("designer_key")
		bucket = segment.get("bucket")
		names = []
		for row in rows:
			keys = [key for key, _label in _designer_row_keys(row, assignments_by_order)]
			if designer_key not in keys:
				continue
			if _bucket_of(row.workflow_state) != bucket:
				continue
			names.append(row.name)
		return sorted(names)

	if seg_type == "matrix_cell":
		view = segment.get("view", "designer")
		row_key = segment.get("row_key")  # None -> every row (column total / grand total)
		cell_category = segment.get("category")  # None -> every category (row total / grand total)
		filtered_rows = _apply_matrix_filter(rows, matrix_filter, status_filter)

		assignments_by_order = {}
		if view in ("designer", "designer_status") and row_key is not None:
			assignments_by_order = _fetch_assignments_by_order([row.name for row in filtered_rows])
			assignments_by_order = _scope_assignments(assignments_by_order, designer_scope)

		names = []
		for row in filtered_rows:
			if cell_category is not None:
				if view in ("designer_status", "customer_status"):
					if _bucket_of(row.workflow_state) != cell_category:
						continue
				elif (row.category or UNCATEGORIZED) != cell_category:
					continue
			if row_key is not None:
				if view == "status":
					keys = [key for key, _label in _status_row_keys(row)]
				elif view in ("customer", "customer_status"):
					keys = [key for key, _label in _customer_row_keys(row)]
				else:
					keys = [key for key, _label in _designer_row_keys(row, assignments_by_order)]
				if row_key not in keys:
					continue
			names.append(row.name)
		return sorted(names)

	if seg_type == "alert":
		which = segment.get("which")
		names = []
		for row in rows:
			bucket = _bucket_of(row.workflow_state)
			if bucket in ("approved", "rejected") or not row.due_date:
				continue
			due_date = getdate(row.due_date)
			if due_date < getdate(nowdate()):
				row_which = "overdue"
			elif due_date <= getdate(due_soon_upper):
				row_which = "due_soon"
			else:
				continue
			if row_which == which:
				names.append(row.name)
		return sorted(names)

	if seg_type == "design_type":
		design_type = segment.get("design_type")
		return sorted(row.name for row in rows if (row.design_type or None) == design_type)

	return []


@frappe.whitelist()
def get_designer_status_breakdown(
	company=None,
	due_soon_days=2,
	designer=None,
	from_date=None,
	to_date=None,
	setting_type=None,
	category=None,
	matrix_filter=None,
	sub_setting_type1=None,
	designer_key=None,
	customer=None,
	branch=None,
	department=None,
	assigned_to=None,
):
	"""Status-bucket counts behind one designer's "in progress" number.

	Used by the Designer Workload popup: clicking "in progress" for a
	designer shows this breakdown instead of jumping straight to the order
	list, so the user can pick one status before drilling in.
	"""
	if not company:
		frappe.throw(_("Please select a Company"))

	_enforce_tab_access(setting_type, sub_setting_type1)
	designer_scope = _designer_scope_for_session()
	if designer_scope is not None:
		designer = designer_scope

	rows = _fetch_filtered_rows(
		company,
		designer,
		from_date,
		to_date,
		setting_type,
		category,
		sub_setting_type1,
		customer=customer,
		branch=branch,
		department=department,
		assigned_to=assigned_to,
	)
	assignments_by_order = _fetch_assignments_by_order([row.name for row in rows])
	assignments_by_order = _scope_assignments(assignments_by_order, designer_scope)

	counts = {}
	for row in rows:
		keys = [key for key, _label in _designer_row_keys(row, assignments_by_order)]
		if designer_key not in keys:
			continue
		bucket = _bucket_of(row.workflow_state)
		if bucket in ("approved", "rejected", "bom_stage"):
			continue
		counts[bucket] = counts.get(bucket, 0) + 1

	return [
		{"bucket": bucket, "label": _(BUCKET_LABELS[bucket]), "count": counts[bucket]}
		for bucket in STATUS_ROW_ORDER
		if bucket in counts
	]


@frappe.whitelist()
def get_order_thumbnails(order_names):
	"""Design Image 1 (+ name) for the Designer x Category matrix's image popup.

	Kept as a separate call (not bundled into get_dashboard_data) since the
	image field is only needed on demand, for whichever cell the user clicks.
	"""
	order_names = frappe.parse_json(order_names) if isinstance(order_names, str) else order_names
	order_names = list(order_names or [])
	if not order_names:
		return []

	rows = frappe.get_list(
		"Order",
		filters={"name": ["in", order_names]},
		fields=["name", "design_image_1"],
		limit_page_length=0,
	)
	image_by_name = {row.name: row.design_image_1 for row in rows}

	# preserve the caller's order (already sorted/sliced for the popup)
	return [
		{"name": name, "design_image_1": image_by_name.get(name)}
		for name in order_names
		if name in image_by_name
	]