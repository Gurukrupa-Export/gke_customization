# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, nowdate

# Base Department names (without the " - <company abbr>" suffix) to report on,
# in the order they should appear in the manufacturing flow.
DEPARTMENT_SEQUENCE = [
	"Manufacturing Plan & Management",
	"Computer Aided Designing",
	"Waxing",
	"Model Making",
	"Pre Polish",
	"Diamond Setting",
	"Final Polish",
	"Tagging",
	"Sales",
]

# Shared CTEs:
# - so_base: Sales Order Item rows (with qty = no. of pieces on that line) for Sales Orders that are
#   active - i.e. not Completed/Closed, and not On Hold (those are reported separately).
# - main_mwo: for every Parent Manufacturing Order, the single "main" Manufacturing Work Order
#   (excludes Serial No generation MWOs (for_fg=1) and Finding MWOs (is_finding_mwo=1)); when the
#   main MWO has been split into multiple pieces, the most recently modified one is taken as current.
# - pmo_main: one row per Parent Manufacturing Order (= one row per manufactured piece), linked back
#   to its originating Sales Order Item, carrying the main MWO's current department and weights.
COMMON_CTE = """
WITH so_base AS (
	SELECT soi.name AS soi_name, soi.qty AS qty
	FROM `tabSales Order Item` soi
	INNER JOIN `tabSales Order` so ON so.name = soi.parent
	WHERE so.docstatus = 1
		AND so.status NOT IN ('Completed', 'Closed', 'On Hold')
		AND so.company = %(company)s
),
main_mwo AS (
	SELECT
		mwo.name,
		mwo.manufacturing_order,
		mwo.department,
		mwo.net_wt,
		mwo.diamond_wt,
		ROW_NUMBER() OVER (
			PARTITION BY mwo.manufacturing_order
			ORDER BY mwo.modified DESC
		) AS rn
	FROM `tabManufacturing Work Order` mwo
	WHERE mwo.for_fg = 0
		AND mwo.is_finding_mwo = 0
		AND mwo.manufacturing_order IS NOT NULL
),
pmo_main AS (
	SELECT
		pmo.sales_order_item AS soi_name,
		pmo.name AS pmo_name,
		mm.department AS mwo_department,
		mm.net_wt AS gold_wt,
		mm.diamond_wt AS diamond_wt
	FROM `tabParent Manufacturing Order` pmo
	LEFT JOIN main_mwo mm ON mm.manufacturing_order = pmo.name AND mm.rn = 1
	WHERE pmo.sales_order_item IS NOT NULL
)
"""

SUMMARY_QUERY = (
	COMMON_CTE
	+ """
SELECT
	(SELECT COALESCE(SUM(qty), 0) FROM so_base) AS total_items,
	(
		SELECT COUNT(*)
		FROM pmo_main p
		INNER JOIN so_base b ON b.soi_name = p.soi_name
	) AS generated_order,
	(
		SELECT COUNT(*)
		FROM pmo_main p
		INNER JOIN so_base b ON b.soi_name = p.soi_name
		INNER JOIN `tabDepartment` d ON d.name = p.mwo_department
		WHERE d.company = %(company)s
			AND d.department_name NOT LIKE '%%Manufacturing Plan%%'
	) AS in_progress_order
"""
)

# Sales Orders that are On Hold (status, still submitted) or Cancelled (docstatus=2) are kept out of
# so_base entirely and counted here instead, so they never double up with the "active" figures above.
HOLD_CANCEL_QUERY = """
SELECT COALESCE(SUM(soi.qty), 0) AS qty
FROM `tabSales Order Item` soi
INNER JOIN `tabSales Order` so ON so.name = soi.parent
WHERE so.company = %(company)s
	AND (
		(so.docstatus = 1 AND so.status = 'On Hold')
		OR so.docstatus = 2
	)
"""

DEPARTMENT_QUERY = (
	COMMON_CTE
	+ """
SELECT
	d.department_name AS department_name,
	COUNT(*) AS mwo_count,
	SUM(COALESCE(pm.gold_wt, 0)) AS gold_wt,
	SUM(COALESCE(pm.diamond_wt, 0)) AS diamond_wt
FROM pmo_main pm
INNER JOIN so_base b ON b.soi_name = pm.soi_name
INNER JOIN `tabDepartment` d ON d.name = pm.mwo_department
WHERE d.company = %(company)s
GROUP BY d.department_name
"""
)


def execute(filters=None):
	filters = filters or {}
	company = filters.get("company")
	if not company:
		frappe.throw(_("Please select a Company"))

	summary = frappe.db.sql(SUMMARY_QUERY, {"company": company}, as_dict=True)[0]
	hold_cancel = frappe.db.sql(HOLD_CANCEL_QUERY, {"company": company}, as_dict=True)[0]
	dept_rows = frappe.db.sql(DEPARTMENT_QUERY, {"company": company}, as_dict=True)
	dept_map = {row.department_name: row for row in dept_rows}

	total_items = int(summary.total_items)
	data = [
		{"group": _("Order"), "metric": _("Total Items"), "count": total_items},
		{"group": _("Order"), "metric": _("Generated Order"), "count": summary.generated_order},
		{"group": _("Order"), "metric": _("Pending Order"), "count": total_items - summary.generated_order},
		{"group": _("Order"), "metric": _("In Progress"), "count": summary.in_progress_order},
		{"group": _("Order"), "metric": _("On Hold/Cancelled"), "count": int(hold_cancel.qty)},
	]

	for department in DEPARTMENT_SEQUENCE:
		row = dept_map.get(department)
		data.append(
			{
				"group": _("Department"),
				"metric": department,
				"count": row.mwo_count if row else 0,
				"gold_wt": row.gold_wt if row else 0,
				"diamond_wt": row.diamond_wt if row else 0,
			}
		)

	other_rows = [row for name, row in dept_map.items() if name not in DEPARTMENT_SEQUENCE]
	if other_rows:
		data.append(
			{
				"group": _("Department"),
				"metric": _("Other"),
				"count": sum(row.mwo_count for row in other_rows),
				"gold_wt": sum(row.gold_wt for row in other_rows),
				"diamond_wt": sum(row.diamond_wt for row in other_rows),
			}
		)

	return get_columns(), data


def get_columns():
	return [
		{"label": _("Group"), "fieldname": "group", "fieldtype": "Data", "width": 110},
		{"label": _("Metric"), "fieldname": "metric", "fieldtype": "Data", "width": 260},
		{"label": _("Count"), "fieldname": "count", "fieldtype": "Int", "width": 100},
		{
			"label": _("Gold Wt (gm)"),
			"fieldname": "gold_wt",
			"fieldtype": "Float",
			"precision": 2,
			"width": 120,
		},
		{
			"label": _("Diamond Wt (ct)"),
			"fieldname": "diamond_wt",
			"fieldtype": "Float",
			"precision": 2,
			"width": 130,
		},
	]


# ---------------------------------------------------------------------------
# Manufacturing Dashboard (page) data API
#
# The tabular report above stays untouched. Everything below feeds the
# "Manufacturing Dashboard" desk page instead, which needs richer, nested
# data than a flat report table can carry: a pending/in-progress/completed
# split per department, and due-date alert counters.
#
# Manufacturing Work Order's own `department`/`status` fields are NOT a
# reliable source of truth for where a piece currently is: they can lag
# behind reality by a whole department (confirmed against real data - e.g.
# pieces whose MWO.department still says "Model Making" while the piece has
# already moved on to "Pre Polish"), and MWO.status is often just never
# updated at all (e.g. MWO.status = 'Not Started' while the piece has
# actually finished that department's work).
#
# The real per-department state lives on `Manufacturing Operation` (one row
# per piece per department visit), reached via MWO.manufacturing_operation,
# which always points at the piece's current/latest operation:
#   - Manufacturing Operation.department          -> the piece's real current department
#   - Manufacturing Operation.status               -> Not Started/WIP/QC .../Finished/Revert
#   - Manufacturing Operation.department_ir_status -> In-Transit (issued, not yet received
#     at this department) / Received (department has it and is working on it)
#
# Classification used below (business-confirmed):
#   - docstatus = 0 (MWO never submitted/issued at all), OR the operation is
#     still In-Transit to this department       -> Pending
#   - operation status = 'Finished'              -> Completed for THIS department
#     (this counts a piece as Completed as soon as this department's work is
#     done, even if it hasn't been issued to the next department yet - that's
#     the intended, business-confirmed behaviour, not a bug)
#   - everything else (submitted, received, still being worked on)
#                                                 -> In Progress
#
# Diamond weight is only tracked once a piece has an actual Manufacturing
# Work Order (via pmo_main); Sales Order Item carries a gross (gold) weight
# estimate but no diamond weight, so diamond_wt is reported as None for
# stages that include not-yet-generated pieces (Total / Pending / Hold).
# ---------------------------------------------------------------------------

# Customer / Order Date filters are optional, so the extra SQL fragment (built by
# _build_so_extra_filter) is spliced into every Sales-Order-touching query below rather than
# baked into a fixed WHERE clause - when no customer/date range is chosen the fragment is just
# an empty string, so no branching is needed at the query-string level.


def _build_so_extra_filter(customer=None, from_date=None, to_date=None):
	conditions = []
	params = {}
	if customer:
		conditions.append("so.customer = %(customer)s")
		params["customer"] = customer
	if from_date:
		conditions.append("so.transaction_date >= %(from_date)s")
		params["from_date"] = from_date
	if to_date:
		conditions.append("so.transaction_date <= %(to_date)s")
		params["to_date"] = to_date
	extra_sql = ("\n\t\tAND " + "\n\t\tAND ".join(conditions)) if conditions else ""
	return extra_sql, params


def _dashboard_cte(extra_so_filter=""):
	return f"""
WITH so_base AS (
	SELECT soi.name AS soi_name, soi.qty AS qty
	FROM `tabSales Order Item` soi
	INNER JOIN `tabSales Order` so ON so.name = soi.parent
	WHERE so.docstatus = 1
		AND so.status NOT IN ('Completed', 'Closed', 'On Hold')
		AND so.company = %(company)s
		{extra_so_filter}
),
main_mwo AS (
	SELECT
		mwo.name,
		mwo.manufacturing_order,
		COALESCE(mo.department, mwo.department) AS department,
		mwo.net_wt,
		mwo.diamond_wt,
		mwo.diamond_pcs,
		mwo.docstatus,
		mwo.delivery_date,
		mo.status AS mop_status,
		mo.department_ir_status AS mop_transfer_status,
		ROW_NUMBER() OVER (
			PARTITION BY mwo.manufacturing_order
			ORDER BY mwo.modified DESC
		) AS rn
	FROM `tabManufacturing Work Order` mwo
	LEFT JOIN `tabManufacturing Operation` mo ON mo.name = mwo.manufacturing_operation
	WHERE mwo.for_fg = 0
		AND mwo.is_finding_mwo = 0
		AND mwo.manufacturing_order IS NOT NULL
),
pmo_main AS (
	SELECT
		pmo.sales_order_item AS soi_name,
		pmo.name AS pmo_name,
		mm.department AS mwo_department,
		mm.net_wt AS gold_wt,
		mm.diamond_wt AS diamond_wt,
		mm.diamond_pcs AS diamond_pcs,
		mm.docstatus AS mwo_docstatus,
		mm.mop_status AS mop_status,
		mm.mop_transfer_status AS mop_transfer_status,
		mm.delivery_date AS due_date
	FROM `tabParent Manufacturing Order` pmo
	LEFT JOIN main_mwo mm ON mm.manufacturing_order = pmo.name AND mm.rn = 1
	WHERE pmo.sales_order_item IS NOT NULL
)
"""

# Cheap, CTE-free: just so_base, used for the "Total Orders" count only.
def _dashboard_total_items_query(extra_so_filter=""):
	return f"""
SELECT COALESCE(SUM(soi.qty), 0) AS total_items
FROM `tabSales Order Item` soi
INNER JOIN `tabSales Order` so ON so.name = soi.parent
WHERE so.docstatus = 1
	AND so.status NOT IN ('Completed', 'Closed', 'On Hold')
	AND so.company = %(company)s
	{extra_so_filter}
"""


# Sales Orders that are On Hold or Cancelled are kept out of so_base entirely (see
# _dashboard_cte) and counted here instead, so they never double up with the "active" figures.
# Cheap, CTE-free, standalone.
def _dashboard_hold_cancel_query(extra_so_filter=""):
	return f"""
SELECT
	COALESCE(SUM(soi.qty), 0) AS qty
FROM `tabSales Order Item` soi
INNER JOIN `tabSales Order` so ON so.name = soi.parent
WHERE so.company = %(company)s
	AND (
		(so.docstatus = 1 AND so.status = 'On Hold')
		OR so.docstatus = 2
	)
	{extra_so_filter}
"""

# Single pass over every generated piece (pmo_main), grouped by department. This is the one
# query that pays for the ROW_NUMBER() window function over Manufacturing Work Order, so
# everything derivable from a per-piece row - department breakdown, due-date alerts, and even
# the "generated"/"in progress" order-level totals - is folded into this one query and then
# summed up in Python, instead of re-running the same CTE chain many times over (which is what
# made the first cut of this dashboard painfully slow compared to the plain tabular report).
#
# Department is a LEFT JOIN (not INNER, unlike the tabular report's DEPARTMENT_QUERY above) so
# pieces whose main MWO has no department set yet still show up in the overall totals - they
# just land in the NULL group, which Python excludes from the per-department breakdown exactly
# like the INNER JOIN version would.
def _dashboard_pieces_query(extra_so_filter=""):
	return (
		_dashboard_cte(extra_so_filter)
		+ """
SELECT
	d.department_name AS department_name,
	d.name AS department_id,
	COUNT(*) AS mwo_count,
	SUM(COALESCE(pm.gold_wt, 0)) AS gold_wt,
	SUM(COALESCE(pm.diamond_wt, 0)) AS diamond_wt,
	SUM(COALESCE(pm.diamond_pcs, 0)) AS diamond_pcs,
	SUM(CASE WHEN COALESCE(pm.mop_status, '') != 'Finished'
			AND (pm.mwo_docstatus = 0 OR COALESCE(pm.mop_transfer_status, '') = 'In-Transit')
		THEN 1 ELSE 0 END) AS pending,
	SUM(CASE WHEN COALESCE(pm.mop_status, '') != 'Finished'
			AND pm.mwo_docstatus = 1
			AND COALESCE(pm.mop_transfer_status, '') != 'In-Transit'
		THEN 1 ELSE 0 END) AS in_progress,
	SUM(CASE WHEN COALESCE(pm.mop_status, '') = 'Finished' THEN 1 ELSE 0 END) AS completed,
	SUM(CASE WHEN pm.due_date IS NOT NULL
			AND COALESCE(pm.mop_status, '') != 'Finished'
			AND pm.due_date BETWEEN CURDATE() AND %(due_soon_upper)s
		THEN 1 ELSE 0 END) AS due_soon_count,
	SUM(CASE WHEN pm.due_date IS NOT NULL
			AND COALESCE(pm.mop_status, '') != 'Finished'
			AND pm.due_date BETWEEN CURDATE() AND %(due_soon_upper)s
		THEN COALESCE(pm.gold_wt, 0) ELSE 0 END) AS due_soon_gold_wt,
	SUM(CASE WHEN pm.due_date IS NOT NULL
			AND COALESCE(pm.mop_status, '') != 'Finished'
			AND pm.due_date BETWEEN CURDATE() AND %(due_soon_upper)s
		THEN COALESCE(pm.diamond_wt, 0) ELSE 0 END) AS due_soon_diamond_wt,
	SUM(CASE WHEN pm.due_date IS NOT NULL
			AND COALESCE(pm.mop_status, '') != 'Finished'
			AND pm.due_date < CURDATE()
		THEN 1 ELSE 0 END) AS overdue_count,
	SUM(CASE WHEN pm.due_date IS NOT NULL
			AND COALESCE(pm.mop_status, '') != 'Finished'
			AND pm.due_date < CURDATE()
		THEN COALESCE(pm.gold_wt, 0) ELSE 0 END) AS overdue_gold_wt,
	SUM(CASE WHEN pm.due_date IS NOT NULL
			AND COALESCE(pm.mop_status, '') != 'Finished'
			AND pm.due_date < CURDATE()
		THEN COALESCE(pm.diamond_wt, 0) ELSE 0 END) AS overdue_diamond_wt
FROM pmo_main pm
INNER JOIN so_base b ON b.soi_name = pm.soi_name
LEFT JOIN `tabDepartment` d ON d.name = pm.mwo_department AND d.company = %(company)s
GROUP BY d.department_name, d.name
"""
	)


@frappe.whitelist()
def get_dashboard_data(company=None, due_soon_days=2, customer=None, from_date=None, to_date=None):
	if not company:
		frappe.throw(_("Please select a Company"))

	due_soon_days = cint(due_soon_days)
	if due_soon_days < 0:
		due_soon_days = 0
	due_soon_upper = add_days(nowdate(), due_soon_days)

	extra_so_filter, extra_params = _build_so_extra_filter(customer, from_date, to_date)
	params = {"company": company, "due_soon_upper": due_soon_upper, **extra_params}

	total_items = int(
		frappe.db.sql(_dashboard_total_items_query(extra_so_filter), params, as_dict=True)[0].total_items
	)
	hold_cancel = frappe.db.sql(_dashboard_hold_cancel_query(extra_so_filter), params, as_dict=True)[0]
	piece_rows = frappe.db.sql(_dashboard_pieces_query(extra_so_filter), params, as_dict=True)

	# Rows with no matching department (main MWO has no department set, or it doesn't belong to
	# this company) still count towards order-level totals but are excluded from the department
	# breakdown - mirroring the tabular report's INNER JOIN semantics for "in progress".
	dept_map = {row.department_name: row for row in piece_rows if row.department_name}
	matched_rows = list(dept_map.values())
	in_progress_rows = [row for row in matched_rows if "Manufacturing Plan" not in row.department_name]

	generated_order = sum(row.mwo_count for row in piece_rows)
	generated_gold_wt = sum(row.gold_wt for row in piece_rows)
	generated_diamond_wt = sum(row.diamond_wt for row in piece_rows)
	in_progress_order = sum(row.mwo_count for row in in_progress_rows)
	in_progress_gold_wt = sum(row.gold_wt for row in in_progress_rows)
	in_progress_diamond_wt = sum(row.diamond_wt for row in in_progress_rows)

	pending_order = total_items - generated_order

	# Sales Order Item's gross-weight field is rarely populated before a piece reaches
	# manufacturing in practice, so it is not a trustworthy weight for not-yet-generated
	# pieces. Only stages backed by an actual Manufacturing Work Order (Generated /
	# In Progress) get a real weight; the rest report count only.
	order_summary = [
		{
			"key": "total",
			"label": _("Total Orders"),
			"count": total_items,
			"gold_wt": None,
			"diamond_wt": None,
		},
		{
			"key": "generated",
			"label": _("Generated Orders"),
			"count": generated_order,
			"gold_wt": flt(generated_gold_wt),
			"diamond_wt": flt(generated_diamond_wt),
		},
		{
			"key": "pending",
			"label": _("Pending to Generate"),
			"count": pending_order,
			"gold_wt": None,
			"diamond_wt": None,
		},
		{
			"key": "in_progress",
			"label": _("In Progress"),
			"count": in_progress_order,
			"gold_wt": flt(in_progress_gold_wt),
			"diamond_wt": flt(in_progress_diamond_wt),
		},
		{
			"key": "on_hold",
			"label": _("On Hold / Cancelled"),
			"count": int(hold_cancel.qty),
			"gold_wt": None,
			"diamond_wt": None,
		},
	]

	def dept_row(name, row):
		return {
			"name": name,
			"department_id": row.department_id if row else None,
			"count": row.mwo_count if row else 0,
			"pending": row.pending if row else 0,
			"in_progress": row.in_progress if row else 0,
			"completed": row.completed if row else 0,
			"gold_wt": flt(row.gold_wt) if row else 0,
			"diamond_wt": flt(row.diamond_wt) if row else 0,
			"diamond_pcs": flt(row.diamond_pcs) if row else 0,
		}

	departments = [dept_row(department, dept_map.get(department)) for department in DEPARTMENT_SEQUENCE]

	other_rows = [row for name, row in dept_map.items() if name not in DEPARTMENT_SEQUENCE]
	if other_rows:
		departments.append(
			{
				"name": _("Other"),
				# "Other" is a grouping of several distinct departments, not one Department
				# record, so there's no single filter value to send a "View Detail" link to.
				"department_id": None,
				"count": sum(row.mwo_count for row in other_rows),
				"pending": sum(row.pending for row in other_rows),
				"in_progress": sum(row.in_progress for row in other_rows),
				"completed": sum(row.completed for row in other_rows),
				"gold_wt": flt(sum(row.gold_wt for row in other_rows)),
				"diamond_wt": flt(sum(row.diamond_wt for row in other_rows)),
				"diamond_pcs": flt(sum(row.diamond_pcs for row in other_rows)),
			}
		)

	return {
		"order_summary": order_summary,
		"departments": departments,
		"alerts": {
			"due_soon": {
				"days": due_soon_days,
				"count": sum(row.due_soon_count for row in piece_rows),
				"gold_wt": flt(sum(row.due_soon_gold_wt for row in piece_rows)),
				"diamond_wt": flt(sum(row.due_soon_diamond_wt for row in piece_rows)),
			},
			"overdue": {
				"count": sum(row.overdue_count for row in piece_rows),
				"gold_wt": flt(sum(row.overdue_gold_wt for row in piece_rows)),
				"diamond_wt": flt(sum(row.overdue_diamond_wt for row in piece_rows)),
			},
		},
		"generated_at": frappe.utils.now(),
	}
