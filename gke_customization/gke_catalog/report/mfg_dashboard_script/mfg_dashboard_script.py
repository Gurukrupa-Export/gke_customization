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
		# customer is matched on the piece's PMO (ref_customer); Sales Order Items with no
		# piece generated yet have no PMO, so those fall back to the Sales Order's ref_customer
		# (so.customer is the internal billing customer, not the actual one)
		# (uncorrelated IN subqueries so MariaDB materializes each once - a correlated EXISTS
		# per Sales Order Item made the dashboard ~15x slower)
		conditions.append(
			"""(soi.name IN (
				SELECT cpmo.sales_order_item FROM `tabParent Manufacturing Order` cpmo
				WHERE cpmo.docstatus != 2 AND cpmo.ref_customer = %(customer)s
			) OR (
				so.ref_customer = %(customer)s
				AND soi.name NOT IN (
					SELECT cpmo.sales_order_item FROM `tabParent Manufacturing Order` cpmo
					WHERE cpmo.docstatus != 2 AND cpmo.sales_order_item IS NOT NULL
				)
			))"""
		)
		params["customer"] = customer
	if from_date:
		conditions.append("so.transaction_date >= %(from_date)s")
		params["from_date"] = from_date
	if to_date:
		conditions.append("so.transaction_date <= %(to_date)s")
		params["to_date"] = to_date
	extra_sql = ("\n\t\tAND " + "\n\t\tAND ".join(conditions)) if conditions else ""
	return extra_sql, params


# Per-piece weights are the design weights from the MWO's master (Design Code) BOM at every stage
# (business-confirmed) - neither the Manufacturing Operation's weighed values nor the stock ledger
# are used, so a piece never shows a missing weight just because it wasn't weighed yet.
# Diamonds use diamond_weight (the sum of the BOM's diamond rows): total_diamond_weight is left at
# 0 on many BOMs that do carry diamonds.


# Every piece's last Manufacturing Operation is Tagging, so on MWO data alone all finished pieces
# pile up in the Tagging card forever. Once tagged, a piece gets a Serial No (via Serial Number
# Creator) and from then on that serial's status/warehouse is the real location of the piece:
# sold/delivered -> Sales, moved to product allocation stock -> Product Allocation, out for
# hallmarking -> Hallmarking. Only pieces whose serial is still in the Tagging FG store (or that
# have no serial yet) stay in Tagging. NULL means "no override - use the MWO department".
_POST_TAGGING_STAGE = """CASE
			WHEN sn.name IS NULL THEN NULL
			WHEN sn.status = 'Delivered' THEN 'Sales'
			WHEN sn.warehouse LIKE '%%Product Allocation%%' THEN 'Product Allocation'
			WHEN sn.warehouse LIKE '%%Hallmarking%%' THEN 'Hallmarking'
			ELSE NULL
		END"""

# Dashboard department order: the real Department records plus the post-tagging stages above.
DASHBOARD_DEPARTMENT_SEQUENCE = [
	"Manufacturing Plan & Management",
	"Computer Aided Designing",
	"Waxing",
	"Model Making",
	"Pre Polish",
	"Diamond Setting",
	"Final Polish",
	"Tagging",
	"Hallmarking",
	"Product Allocation",
	"Sales",
]


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
		COALESCE(bom.total_metal_weight, 0) AS net_wt,
		COALESCE(bom.diamond_weight, 0) AS diamond_wt,
		COALESCE(bom.total_diamond_pcs, 0) AS diamond_pcs,
		COALESCE(bom.gemstone_weight, 0) AS gemstone_wt,
		mwo.docstatus,
		mwo.delivery_date,
		mo.status AS mop_status,
		mo.department_ir_status AS mop_transfer_status,
		mo.operation AS mop_operation,
		mo.name AS mop_name,
		ROW_NUMBER() OVER (
			PARTITION BY mwo.manufacturing_order
			ORDER BY mwo.modified DESC
		) AS rn
	FROM `tabManufacturing Work Order` mwo
	LEFT JOIN `tabManufacturing Operation` mo ON mo.name = mwo.manufacturing_operation
	-- falls back to the item's master BOM when the MWO has none, so the piece isn't 0 weight
	LEFT JOIN `tabItem` item ON item.name = mwo.item_code
	LEFT JOIN `tabBOM` bom ON bom.name = COALESCE(NULLIF(mwo.master_bom, ''), item.master_bom)
	WHERE mwo.for_fg = 0
		AND mwo.is_finding_mwo = 0
		AND mwo.docstatus != 2
		AND mwo.manufacturing_order IS NOT NULL
),
piece_serial AS (
	SELECT
		snc.parent_manufacturing_order AS pmo,
		MAX(COALESCE(NULLIF(snc.fg_serial_no, ''), snc.serial_no)) AS serial_no
	FROM `tabSerial Number Creator` snc
	WHERE snc.docstatus = 1
	GROUP BY snc.parent_manufacturing_order
),
pmo_main AS (
	SELECT
		pmo.sales_order_item AS soi_name,
		pmo.name AS pmo_name,
		mm.department AS mwo_department,
		mm.net_wt AS gold_wt,
		mm.diamond_wt AS diamond_wt,
		mm.diamond_pcs AS diamond_pcs,
		mm.gemstone_wt AS gemstone_wt,
		mm.docstatus AS mwo_docstatus,
		mm.mop_status AS mop_status,
		mm.mop_transfer_status AS mop_transfer_status,
		mm.mop_operation AS mop_operation,
		mm.name AS mwo_name,
		mm.mop_name AS mop_name,
		mm.delivery_date AS due_date,
		{_POST_TAGGING_STAGE} AS post_tagging_stage
	FROM `tabParent Manufacturing Order` pmo
	LEFT JOIN main_mwo mm ON mm.manufacturing_order = pmo.name AND mm.rn = 1
	LEFT JOIN piece_serial ps ON ps.pmo = pmo.name
	LEFT JOIN `tabSerial No` sn ON sn.name = ps.serial_no
	WHERE pmo.sales_order_item IS NOT NULL
		-- a cancelled piece stays linked to its (still active) Sales Order Item, so it must be
		-- dropped explicitly or it keeps counting as a generated / in-progress piece
		AND pmo.docstatus != 2
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


# Not-yet-generated pieces have no Manufacturing Work Order, so their weights come from the
# Sales Order Item's item's master (Design Code) BOM - the same BOM the generated pieces use -
# times the pieces still to generate. Shared by the Pending card and its order list.
_PENDING_GENERATED_JOIN = """LEFT JOIN (
	SELECT pmo.sales_order_item, COUNT(*) AS generated
	FROM `tabParent Manufacturing Order` pmo
	WHERE pmo.docstatus != 2 AND pmo.sales_order_item IS NOT NULL
	GROUP BY pmo.sales_order_item
) g ON g.sales_order_item = soi.name
LEFT JOIN `tabItem` item ON item.name = soi.item_code
LEFT JOIN `tabBOM` bom ON bom.name = item.master_bom"""
_PENDING_QTY = "(soi.qty - COALESCE(g.generated, 0))"


def _dashboard_pending_weight_query(extra_so_filter=""):
	return f"""
SELECT
	COALESCE(SUM({_PENDING_QTY} * COALESCE(bom.total_metal_weight, 0)), 0) AS gold_wt,
	COALESCE(SUM({_PENDING_QTY} * COALESCE(bom.diamond_weight, 0)), 0) AS diamond_wt
FROM `tabSales Order Item` soi
INNER JOIN `tabSales Order` so ON so.name = soi.parent
{_PENDING_GENERATED_JOIN}
WHERE so.docstatus = 1
	AND so.status NOT IN ('Completed', 'Closed', 'On Hold')
	AND so.company = %(company)s
	AND {_PENDING_QTY} > 0
	{extra_so_filter}
"""


# Sales Orders that are On Hold or Cancelled are kept out of so_base entirely (see
# _dashboard_cte) and counted here instead, so they never double up with the "active" figures.
# Weights are the item's master BOM times qty, like the pending pieces. Cheap, CTE-free, standalone.
def _dashboard_hold_cancel_query(extra_so_filter=""):
	return f"""
SELECT
	COALESCE(SUM(soi.qty), 0) AS qty,
	COALESCE(SUM(CASE WHEN so.docstatus = 2 THEN 0 ELSE soi.qty END), 0) AS on_hold_qty,
	COALESCE(SUM(CASE WHEN so.docstatus = 2 THEN soi.qty ELSE 0 END), 0) AS cancelled_qty,
	COALESCE(SUM(soi.qty * COALESCE(bom.total_metal_weight, 0)), 0) AS gold_wt,
	COALESCE(SUM(soi.qty * COALESCE(bom.diamond_weight, 0)), 0) AS diamond_wt
FROM `tabSales Order Item` soi
INNER JOIN `tabSales Order` so ON so.name = soi.parent
LEFT JOIN `tabItem` item ON item.name = soi.item_code
LEFT JOIN `tabBOM` bom ON bom.name = item.master_bom
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
	COALESCE(pm.post_tagging_stage, d.department_name) AS department_name,
	-- post-tagging stages aren't Department records, so they get no "View Detail" drill-down
	MAX(CASE WHEN pm.post_tagging_stage IS NULL THEN d.name END) AS department_id,
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
	-- subset of in_progress: received/submitted but the department hasn't started work on it yet
	SUM(CASE WHEN pm.mwo_docstatus = 1
			AND COALESCE(pm.mop_transfer_status, '') != 'In-Transit'
			AND pm.mop_status = 'Not Started'
		THEN 1 ELSE 0 END) AS not_started,
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
GROUP BY COALESCE(pm.post_tagging_stage, d.department_name)
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
	pending_wt = frappe.db.sql(_dashboard_pending_weight_query(extra_so_filter), params, as_dict=True)[0]
	piece_rows = frappe.db.sql(_dashboard_pieces_query(extra_so_filter), params, as_dict=True)

	# Rows with no matching department (main MWO has no department set, or it doesn't belong to
	# this company) still count towards order-level totals but are excluded from the department
	# breakdown - mirroring the tabular report's INNER JOIN semantics for "in progress".
	dept_map = {row.department_name: row for row in piece_rows if row.department_name}
	matched_rows = list(dept_map.values())
	# Sold / allocated pieces have left manufacturing, so they aren't "in progress" any more.
	in_progress_rows = [
		row
		for row in matched_rows
		if "Manufacturing Plan" not in row.department_name
		and row.department_name not in ("Product Allocation", "Sales")
	]

	generated_order = sum(row.mwo_count for row in piece_rows)
	generated_gold_wt = sum(row.gold_wt for row in piece_rows)
	generated_diamond_wt = sum(row.diamond_wt for row in piece_rows)
	in_progress_order = sum(row.mwo_count for row in in_progress_rows)
	in_progress_gold_wt = sum(row.gold_wt for row in in_progress_rows)
	in_progress_diamond_wt = sum(row.diamond_wt for row in in_progress_rows)

	pending_order = total_items - generated_order

	# Generated / In Progress weights come from each piece's MWO master BOM, Pending from the
	# item's master BOM (see _dashboard_pending_weight_query), and Total is the two added up.
	# On Hold / Cancelled also uses the item's master BOM (see _dashboard_hold_cancel_query).
	order_summary = [
		{
			"key": "total",
			"label": _("Total Orders"),
			"count": total_items,
			"gold_wt": flt(generated_gold_wt) + flt(pending_wt.gold_wt),
			"diamond_wt": flt(generated_diamond_wt) + flt(pending_wt.diamond_wt),
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
			"gold_wt": flt(pending_wt.gold_wt),
			"diamond_wt": flt(pending_wt.diamond_wt),
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
			"on_hold": int(hold_cancel.on_hold_qty),
			"cancelled": int(hold_cancel.cancelled_qty),
			"gold_wt": flt(hold_cancel.gold_wt),
			"diamond_wt": flt(hold_cancel.diamond_wt),
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
			"not_started": cint(row.not_started) if row else 0,
		}

	departments = [
		dept_row(department, dept_map.get(department)) for department in DASHBOARD_DEPARTMENT_SEQUENCE
	]

	other_rows = [row for name, row in dept_map.items() if name not in DASHBOARD_DEPARTMENT_SEQUENCE]
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
				"not_started": cint(sum(row.not_started for row in other_rows)),
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
		"operations": _get_operation_summary(company, extra_so_filter, extra_params),
		"generated_at": frappe.utils.now(),
	}


# Due-date alert drill-down: the pieces behind the andon board's Due Soon / Overdue counts. Same
# piece set and conditions as the due_soon_* / overdue_* sums in _dashboard_pieces_query, so the
# list's total always matches the lamp it was opened from.
ALERT_CONDITIONS = {
	"due_soon": "pm.due_date BETWEEN CURDATE() AND %(due_soon_upper)s",
	"overdue": "pm.due_date < CURDATE()",
}


@frappe.whitelist()
def get_alert_orders(
	company=None,
	alert=None,
	due_soon_days=2,
	customer=None,
	from_date=None,
	to_date=None,
):
	if not company:
		frappe.throw(_("Please select a Company"))
	if alert not in ALERT_CONDITIONS:
		frappe.throw(_("Invalid alert type"))

	due_soon_days = max(cint(due_soon_days), 0)

	extra_so_filter, extra_params = _build_so_extra_filter(customer, from_date, to_date)
	params = {
		"company": company,
		"due_soon_upper": add_days(nowdate(), due_soon_days),
		**extra_params,
	}
	pieces = f"""
SELECT
	pm.pmo_name,
	pm.mop_name,
	pm.gold_wt,
	pm.diamond_wt,
	pm.due_date,
	COALESCE(pm.post_tagging_stage, d.department_name) AS department,
	{_STAGE_STATUS} AS stage_status
FROM pmo_main pm
INNER JOIN so_base b ON b.soi_name = pm.soi_name
LEFT JOIN `tabDepartment` d ON d.name = pm.mwo_department AND d.company = %(company)s
WHERE pm.due_date IS NOT NULL
	AND COALESCE(pm.mop_status, '') != 'Finished'
	AND {ALERT_CONDITIONS[alert]}
"""
	# the whole list is returned in one go - the dialog shows it as a single scrollable table
	cte = _dashboard_cte(extra_so_filter)
	orders = frappe.db.sql(
		cte
		+ f"""
SELECT
	p.pmo_name AS order_no,
	pmo.item_code AS design_no,
	pmo.item_category AS item_category,
	pmo.ref_customer AS customer,
	p.department,
	p.gold_wt,
	p.diamond_wt,
	p.due_date,
	DATEDIFF(p.due_date, CURDATE()) AS days_left,
	p.stage_status
FROM ({pieces}) p
INNER JOIN `tabParent Manufacturing Order` pmo ON pmo.name = p.pmo_name
ORDER BY p.due_date ASC, p.pmo_name ASC
""",
		params,
		as_dict=True,
	)

	_attach_mwo(orders)

	return {
		"alert": alert,
		"orders": orders,
		"order_count": len(orders),
	}


# MWO column of the order lists. A PMO has several MWOs - the Serial No (for_fg) one, Finding
# ones, and the main one, which can be split into -02, -03 ... - so the list shows the main MWO
# ending in "-01". Display only: weights / department still come from pmo_main's current MWO.
# Looked up in one query after the list is built, so the heavy list queries stay unchanged.
def _main_mwo_01(pmos):
	"""{PMO name: its main "-01" MWO} for the given PMOs."""
	pmos = list({p for p in pmos if p})
	if not pmos:
		return {}
	return dict(
		frappe.db.sql(
			"""
SELECT mwo.manufacturing_order, MIN(mwo.name)
FROM `tabManufacturing Work Order` mwo
WHERE mwo.manufacturing_order IN %(pmos)s
	AND mwo.for_fg = 0
	AND mwo.is_finding_mwo = 0
	AND mwo.docstatus != 2
	AND mwo.name LIKE '%%-01'
GROUP BY mwo.manufacturing_order
""",
			{"pmos": tuple(pmos)},
		)
	)


def _attach_mwo(orders):
	mwo_map = _main_mwo_01(o.get("order_no") for o in orders)
	for o in orders:
		o.mwo = mwo_map.get(o.get("order_no"))


# Excel download for every dashboard order list. The dialog sends the table exactly as it is on
# screen - header, the rows left after any column search, and the Total row - so the file always
# matches what the user is looking at, whichever list it came from.
@frappe.whitelist()
def export_order_list(title=None, rows=None):
	import re

	from frappe.utils.xlsxutils import build_xlsx_response

	data = frappe.parse_json(rows) or []
	if not isinstance(data, list) or not all(isinstance(row, list) for row in data):
		frappe.throw(_("Invalid export data"))

	# titles like "On Hold / Cancelled Orders" would otherwise break the file name
	name = " ".join(re.sub(r"[^\w\- ]+", " ", title or _("Orders")).split()) or _("Orders")
	build_xlsx_response(data, f"{name} {nowdate()}")


# Department card drill-down: the pieces behind a card's "Not started" count.
# Same piece set and conditions as the not_started sum in _dashboard_pieces_query,
# and the same department grouping as the cards (post-tagging stage overrides the MWO department),
# so the list's total always matches the number on the card.
DEPARTMENT_PIECE_CONDITIONS = {
	"not_started": """pm.mwo_docstatus = 1
		AND COALESCE(pm.mop_transfer_status, '') != 'In-Transit'
		AND pm.mop_status = 'Not Started'""",
}
# sent instead of a department name for the "Other" card, which groups every department
# outside DASHBOARD_DEPARTMENT_SEQUENCE
OTHER_DEPARTMENTS = "__other__"


@frappe.whitelist()
def get_department_pieces(
	company=None,
	department=None,
	kind=None,
	customer=None,
	from_date=None,
	to_date=None,
):
	if not company or not department:
		frappe.throw(_("Please select a Company and a Department"))
	if kind not in DEPARTMENT_PIECE_CONDITIONS:
		frappe.throw(_("Invalid list type"))

	extra_so_filter, extra_params = _build_so_extra_filter(customer, from_date, to_date)
	params = {
		"company": company,
		"department": department,
		"sequence": tuple(DASHBOARD_DEPARTMENT_SEQUENCE),
		**extra_params,
	}
	stage = "COALESCE(pm.post_tagging_stage, d.department_name)"
	if department == OTHER_DEPARTMENTS:
		department_condition = f"{stage} IS NOT NULL AND {stage} NOT IN %(sequence)s"
	else:
		department_condition = f"{stage} = %(department)s"

	orders = frappe.db.sql(
		_dashboard_cte(extra_so_filter)
		+ f"""
SELECT
	pm.pmo_name AS order_no,
	pmo.ref_customer AS customer,
	pmo.item_code AS design_no,
	pmo.item_category AS item_category,
	{stage} AS department,
	mo.operation AS operation,
	pm.gold_wt,
	pm.diamond_wt,
	mo.start_time AS issue_date,
	pm.due_date,
	emp.employee_name AS employee_name,
	mo.employee AS employee,
	{_STAGE_STATUS} AS stage_status
FROM pmo_main pm
INNER JOIN so_base b ON b.soi_name = pm.soi_name
LEFT JOIN `tabDepartment` d ON d.name = pm.mwo_department AND d.company = %(company)s
INNER JOIN `tabParent Manufacturing Order` pmo ON pmo.name = pm.pmo_name
LEFT JOIN `tabManufacturing Operation` mo ON mo.name = pm.mop_name
LEFT JOIN `tabEmployee` emp ON emp.name = mo.employee
WHERE {department_condition}
	AND {DEPARTMENT_PIECE_CONDITIONS[kind]}
ORDER BY pm.due_date IS NULL, pm.due_date ASC, pm.pmo_name ASC
""",
		params,
		as_dict=True,
	)

	abbr = frappe.get_cached_value("Company", company, "abbr")
	suffix = f" - {abbr}"
	for o in orders:
		if o.operation and abbr and o.operation.endswith(suffix):
			o.operation = o.operation[: -len(suffix)].strip()
	_attach_mwo(orders)

	return {"orders": orders, "order_count": len(orders)}


# KPI card drill-down: the rows behind the Pending to Generate / In Progress / On Hold-Cancelled
# cards, built from the same piece sets as get_dashboard_data so the totals match the cards.
# Pending and On Hold/Cancelled have no Parent Manufacturing Order yet, so those are listed per
# Sales Order Item (qty = pieces); In Progress is listed per piece like the other lists.
SUMMARY_ORDER_KINDS = ("pending", "in_progress", "on_hold")


@frappe.whitelist()
def get_summary_orders(company=None, kind=None, customer=None, from_date=None, to_date=None):
	if not company:
		frappe.throw(_("Please select a Company"))
	if kind not in SUMMARY_ORDER_KINDS:
		frappe.throw(_("Invalid list type"))

	extra_so_filter, extra_params = _build_so_extra_filter(customer, from_date, to_date)
	params = {"company": company, **extra_params}

	if kind == "in_progress":
		# same rows as in_progress_rows in get_dashboard_data
		stage = "COALESCE(pm.post_tagging_stage, d.department_name)"
		orders = frappe.db.sql(
			_dashboard_cte(extra_so_filter)
			+ f"""
SELECT
	pm.pmo_name AS order_no,
	pmo.ref_customer AS customer,
	pmo.item_code AS design_no,
	pmo.item_category AS item_category,
	{stage} AS department,
	mo.operation AS operation,
	pm.gold_wt,
	pm.diamond_wt,
	pm.due_date,
	{_STAGE_STATUS} AS stage_status
FROM pmo_main pm
INNER JOIN so_base b ON b.soi_name = pm.soi_name
LEFT JOIN `tabDepartment` d ON d.name = pm.mwo_department AND d.company = %(company)s
INNER JOIN `tabParent Manufacturing Order` pmo ON pmo.name = pm.pmo_name
LEFT JOIN `tabManufacturing Operation` mo ON mo.name = pm.mop_name
WHERE {stage} IS NOT NULL
	AND {stage} NOT LIKE '%%Manufacturing Plan%%'
	AND {stage} NOT IN ('Product Allocation', 'Sales')
ORDER BY pm.due_date IS NULL, pm.due_date ASC, pm.pmo_name ASC
""",
			params,
			as_dict=True,
		)

		abbr = frappe.get_cached_value("Company", company, "abbr")
		suffix = f" - {abbr}"
		for o in orders:
			if o.operation and abbr and o.operation.endswith(suffix):
				o.operation = o.operation[: -len(suffix)].strip()
		_attach_mwo(orders)

		return {"orders": orders, "order_count": len(orders)}

	if kind == "pending":
		# active Sales Order Items with fewer pieces generated than ordered (see so_base / pmo_main)
		qty = _PENDING_QTY
		condition = f"""so.docstatus = 1
		AND so.status NOT IN ('Completed', 'Closed', 'On Hold')
		AND {qty} > 0"""
		status = "so.status"
	else:
		qty = "soi.qty"
		condition = """((so.docstatus = 1 AND so.status = 'On Hold') OR so.docstatus = 2)"""
		status = "CASE WHEN so.docstatus = 2 THEN 'Cancelled' ELSE 'On Hold' END"

	orders = frappe.db.sql(
		f"""
SELECT
	soi.parent AS sales_order,
	so.ref_customer AS customer,
	soi.item_code AS design_no,
	soi.item_category AS item_category,
	{qty} AS qty,
	{qty} * COALESCE(bom.total_metal_weight, 0) AS gold_wt,
	{qty} * COALESCE(bom.diamond_weight, 0) AS diamond_wt,
	so.transaction_date AS order_date,
	soi.delivery_date AS due_date,
	{status} AS so_status
FROM `tabSales Order Item` soi
INNER JOIN `tabSales Order` so ON so.name = soi.parent
{_PENDING_GENERATED_JOIN}
WHERE so.company = %(company)s
	AND {condition}
	{extra_so_filter}
ORDER BY soi.delivery_date IS NULL, soi.delivery_date ASC, soi.parent ASC, soi.idx ASC
""",
		params,
		as_dict=True,
	)

	return {"orders": orders, "order_count": len(orders)}


# Operation-wise summary (dashboard section 3): every department from Waxing to Final Polish,
# broken down by the Department Operation each piece's current Manufacturing Operation is on.
# Same piece set and weight rules as the department cards, so each department's total matches
# its card. A piece received but not picked up by any operation yet has no operation set (or
# still carries one from another department) - those are reported as "awaiting operation".
OPERATION_SUMMARY_DEPARTMENTS = [
	"Waxing",
	"Model Making",
	"Pre Polish",
	"Diamond Setting",
	"Final Polish",
]


def _dashboard_operations_query(extra_so_filter=""):
	return (
		_dashboard_cte(extra_so_filter)
		+ """
SELECT
	pm.mwo_department AS department,
	dop.name AS operation,
	COUNT(*) AS piece_count,
	SUM(COALESCE(pm.gold_wt, 0)) AS gold_wt,
	SUM(COALESCE(pm.diamond_wt, 0)) AS diamond_wt,
	SUM(COALESCE(pm.diamond_pcs, 0)) AS diamond_pcs
FROM pmo_main pm
INNER JOIN so_base b ON b.soi_name = pm.soi_name
LEFT JOIN `tabDepartment Operation` dop
	ON dop.name = pm.mop_operation AND dop.department = pm.mwo_department
WHERE pm.mwo_department IN %(departments)s
	AND pm.post_tagging_stage IS NULL
GROUP BY pm.mwo_department, dop.name
"""
	)


def _get_operation_summary(company, extra_so_filter, extra_params):
	dept_ids = {
		row.department_name.strip(): row.name
		for row in frappe.get_all(
			"Department", filters={"company": company}, fields=["name", "department_name"]
		)
	}
	departments = [(name, dept_ids[name]) for name in OPERATION_SUMMARY_DEPARTMENTS if name in dept_ids]
	if not departments:
		return []

	params = {"company": company, "departments": tuple(d for _, d in departments), **extra_params}
	rows = frappe.db.sql(_dashboard_operations_query(extra_so_filter), params, as_dict=True)
	row_map = {(row.department, row.operation): row for row in rows}

	operations_by_dept = {}
	for op in frappe.get_all(
		"Department Operation",
		filters={"department": ("in", [d for _, d in departments])},
		fields=["name", "department"],
		order_by="name asc",
	):
		operations_by_dept.setdefault(op.department, []).append(op.name)

	abbr = frappe.get_cached_value("Company", company, "abbr")

	def strip_abbr(name):
		suffix = f" - {abbr}"
		return name[: -len(suffix)].strip() if abbr and name.endswith(suffix) else name.strip()

	def summary(row_list):
		return {
			"count": sum(cint(row.piece_count) for row in row_list),
			"gold_wt": flt(sum(row.gold_wt for row in row_list)),
			"diamond_wt": flt(sum(row.diamond_wt for row in row_list)),
			"diamond_pcs": flt(sum(row.diamond_pcs for row in row_list)),
		}

	result = []
	for name, dept_id in departments:
		dept_rows = [row for row in rows if row.department == dept_id]
		result.append(
			{
				"name": name,
				"department_id": dept_id,
				"operations": [
					{"operation": op, "label": strip_abbr(op), **summary([row_map[(dept_id, op)]] if (dept_id, op) in row_map else [])}
					for op in operations_by_dept.get(dept_id, [])
				],
				"awaiting_operation": summary([row for row in dept_rows if row.operation is None]),
				"total": summary(dept_rows),
			}
		)
	return result


# ---------------------------------------------------------------------------
# Drill-down below the operation-wise summary (dashboard sections 4-6): clicking an operation
# tag shows its stage-wise (status) summary and order list, and clicking an order shows its
# details. "Order" here is one piece = one Parent Manufacturing Order, same as everywhere above.
# ---------------------------------------------------------------------------

ALL_OPERATIONS = "__all__"
AWAITING_OPERATION = "__awaiting__"
STAGE_STATUSES = ["In Progress", "Completed", "Pending", "On Hold"]

# Same split as the department cards' pending / in progress / completed, with operations put
# On Hold carved out of the other buckets.
_STAGE_STATUS = """CASE
		WHEN COALESCE(pm.mop_status, '') = 'Finished' THEN 'Completed'
		WHEN COALESCE(pm.mop_status, '') = 'On Hold' THEN 'On Hold'
		WHEN pm.mwo_docstatus = 0 OR COALESCE(pm.mop_transfer_status, '') = 'In-Transit' THEN 'Pending'
		ELSE 'In Progress'
	END"""


def _stage_pieces_query(extra_so_filter, operation):
	if operation == ALL_OPERATIONS:
		operation_condition = ""
	elif operation == AWAITING_OPERATION:
		operation_condition = "AND dop.name IS NULL"
	else:
		operation_condition = "AND dop.name = %(operation)s"

	return f"""
SELECT
	pm.pmo_name,
	pm.mwo_name,
	pm.mop_name,
	pm.gold_wt,
	pm.diamond_wt,
	pm.diamond_pcs,
	pm.due_date,
	{_STAGE_STATUS} AS stage_status
FROM pmo_main pm
INNER JOIN so_base b ON b.soi_name = pm.soi_name
LEFT JOIN `tabDepartment Operation` dop
	ON dop.name = pm.mop_operation AND dop.department = pm.mwo_department
WHERE pm.mwo_department = %(department)s
	AND pm.post_tagging_stage IS NULL
	{operation_condition}
"""


@frappe.whitelist()
def get_stage_details(
	company=None,
	department=None,
	operation=None,
	status=None,
	page=1,
	page_size=None,
	customer=None,
	from_date=None,
	to_date=None,
):
	if not company or not department:
		frappe.throw(_("Please select a Company and a Department"))

	operation = operation or ALL_OPERATIONS
	page = max(cint(page), 1)
	# no page_size = every order (the dashboard's order list scrolls instead of paging)
	page_size = min(cint(page_size), 100) if cint(page_size) > 0 else None
	if status not in STAGE_STATUSES:
		status = None

	extra_so_filter, extra_params = _build_so_extra_filter(customer, from_date, to_date)
	params = {
		"company": company,
		"department": department,
		"operation": operation,
		"status": status,
		"limit": page_size,
		"offset": (page - 1) * page_size if page_size else 0,
		**extra_params,
	}
	cte = _dashboard_cte(extra_so_filter)
	pieces = _stage_pieces_query(extra_so_filter, operation)
	limit_clause = "LIMIT %(limit)s OFFSET %(offset)s" if page_size else ""

	summary_rows = frappe.db.sql(
		cte
		+ f"""
SELECT
	p.stage_status,
	COUNT(*) AS piece_count,
	SUM(COALESCE(p.gold_wt, 0)) AS gold_wt,
	SUM(COALESCE(p.diamond_wt, 0)) AS diamond_wt
FROM ({pieces}) p
GROUP BY p.stage_status
""",
		params,
		as_dict=True,
	)
	summary_map = {row.stage_status: row for row in summary_rows}

	def summary(row_list):
		return {
			"count": sum(cint(row.piece_count) for row in row_list),
			"gold_wt": flt(sum(row.gold_wt for row in row_list)),
			"diamond_wt": flt(sum(row.diamond_wt for row in row_list)),
		}

	stages = [
		{"status": name, **summary([summary_map[name]] if name in summary_map else [])}
		for name in STAGE_STATUSES
	]
	total = summary(summary_rows)

	orders = frappe.db.sql(
		cte
		+ f"""
SELECT
	p.pmo_name AS order_no,
	pmo.item_code AS design_no,
	pmo.item_category AS item_category,
	p.gold_wt,
	p.diamond_wt,
	p.due_date,
	p.stage_status,
	mo.start_time AS issue_date,
	mo.employee AS employee,
	emp.employee_name AS employee_name
FROM ({pieces}) p
INNER JOIN `tabParent Manufacturing Order` pmo ON pmo.name = p.pmo_name
LEFT JOIN `tabManufacturing Operation` mo ON mo.name = p.mop_name
LEFT JOIN `tabEmployee` emp ON emp.name = mo.employee
WHERE (%(status)s IS NULL OR p.stage_status = %(status)s)
ORDER BY p.due_date IS NULL, p.due_date ASC, p.pmo_name ASC
{limit_clause}
""",
		params,
		as_dict=True,
	)
	_attach_mwo(orders)

	return {
		"stages": stages,
		"total": total,
		"status": status,
		"orders": orders,
		"order_count": summary_map[status].piece_count if status in summary_map else (0 if status else total["count"]),
		"page": page,
		"page_size": page_size,
	}


@frappe.whitelist()
def get_order_details(company=None, order_no=None):
	if not company or not order_no:
		frappe.throw(_("Please select an Order"))
	frappe.has_permission("Parent Manufacturing Order", doc=order_no, throw=True)

	# Reuses the dashboard's per-piece rules (current operation, planned-vs-actual weights), just
	# narrowed to the one piece - no Sales Order filters, so a piece always resolves.
	piece = frappe.db.sql(
		_dashboard_cte()
		+ f"""
SELECT
	pm.pmo_name,
	pm.mwo_name,
	pm.mop_name,
	pm.gold_wt,
	pm.diamond_wt,
	pm.diamond_pcs,
	pm.gemstone_wt,
	pm.due_date,
	COALESCE(pm.post_tagging_stage, d.department_name) AS department,
	{_STAGE_STATUS} AS stage_status
FROM pmo_main pm
LEFT JOIN `tabDepartment` d ON d.name = pm.mwo_department
WHERE pm.pmo_name = %(order_no)s
""",
		{"company": company, "order_no": order_no},
		as_dict=True,
	)
	piece = piece[0] if piece else frappe._dict()

	pmo = frappe.db.get_value(
		"Parent Manufacturing Order",
		order_no,
		[
			"name",
			"sales_order",
			"ref_customer",
			"item_code",
			"item_category",
			"item_sub_category",
			"metal_type",
			"metal_touch",
			"metal_colour",
			"qty",
			"po_no",
		],
		as_dict=True,
	)
	if not pmo:
		frappe.throw(_("Order {0} not found").format(order_no))

	mo = (
		frappe.db.get_value(
			"Manufacturing Operation",
			piece.mop_name,
			["operation", "status", "employee", "start_time", "gross_wt", "net_wt"],
			as_dict=True,
		)
		if piece.mop_name
		else None
	) or frappe._dict()

	abbr = frappe.get_cached_value("Company", company, "abbr")
	suffix = f" - {abbr}"

	def strip_abbr(name):
		return name[: -len(suffix)].strip() if name and abbr and name.endswith(suffix) else name

	return {
		"order_no": pmo.name,
		"sales_order": pmo.sales_order,
		"order_date": frappe.db.get_value("Sales Order", pmo.sales_order, "transaction_date")
		if pmo.sales_order
		else None,
		"customer": pmo.ref_customer,
		"customer_name": frappe.db.get_value("Customer", pmo.ref_customer, "customer_name")
		if pmo.ref_customer
		else None,
		"design_no": pmo.item_code,
		# only a flag - the image itself is streamed by get_catalogue_image so its storage path
		# never reaches the browser
		"has_catalogue_image": bool(
			pmo.item_code and frappe.db.get_value("Item", pmo.item_code, "custom_catalogue_image")
		),
		"item_category": pmo.item_category,
		"item_sub_category": pmo.item_sub_category,
		"qty": pmo.qty,
		"po_no": pmo.po_no,
		"due_date": piece.due_date,
		# the main "-01" MWO, same as the lists' MWO column (see _attach_mwo)
		"work_order": _main_mwo_01([pmo.name]).get(pmo.name),
		"department": piece.department,
		"operation": strip_abbr(mo.operation),
		"status": piece.stage_status,
		"employee": mo.employee,
		"employee_name": frappe.db.get_value("Employee", mo.employee, "employee_name") if mo.employee else None,
		"issue_date": mo.start_time,
		"metal_type": pmo.metal_type,
		"metal_touch": pmo.metal_touch,
		"metal_colour": pmo.metal_colour,
		"gross_wt": flt(mo.gross_wt),
		"net_wt": flt(mo.net_wt),
		"metal_wt": flt(piece.gold_wt),
		"diamond_wt": flt(piece.diamond_wt),
		"diamond_pcs": flt(piece.diamond_pcs),
		"gemstone_wt": flt(piece.gemstone_wt),
	}


# Catalogue image proxy for the dashboard's Order Details panel. The browser only ever gets the
# image bytes from this endpoint (permission-checked per order); the Item's stored image URL /
# S3 path is never sent to the client. Remote fetches are limited to S3 over https so the field
# can't be abused to make the server request arbitrary URLs.
_CATALOGUE_IMAGE_MAX_BYTES = 15 * 1024 * 1024


@frappe.whitelist(methods=["GET"])
def get_catalogue_image(order_no=None):
	from urllib.parse import urlparse

	import requests

	if not order_no:
		frappe.throw(_("Please select an Order"))
	frappe.has_permission("Parent Manufacturing Order", doc=order_no, throw=True)

	item_code = frappe.db.get_value("Parent Manufacturing Order", order_no, "item_code")
	url = item_code and frappe.db.get_value("Item", item_code, "custom_catalogue_image")
	if not url:
		raise frappe.DoesNotExistError(_("No catalogue image"))

	content_type = None
	if url.startswith(("/files/", "/private/files/")):
		file_name = frappe.db.get_value("File", {"file_url": url}, "name")
		if not file_name:
			raise frappe.DoesNotExistError(_("No catalogue image"))
		content = frappe.get_doc("File", file_name).get_content()
	else:
		parsed = urlparse(url)
		if parsed.scheme != "https" or not (parsed.hostname or "").endswith(".amazonaws.com"):
			raise frappe.DoesNotExistError(_("No catalogue image"))
		res = requests.get(url, timeout=15, stream=True)
		if res.status_code != 200:
			raise frappe.DoesNotExistError(_("No catalogue image"))
		content_type = (res.headers.get("Content-Type") or "").split(";")[0].strip()
		content = res.raw.read(_CATALOGUE_IMAGE_MAX_BYTES + 1, decode_content=True)
		if len(content) > _CATALOGUE_IMAGE_MAX_BYTES:
			frappe.throw(_("Catalogue image is too large"))

	if not content_type or not content_type.startswith("image/"):
		import mimetypes

		content_type = mimetypes.guess_type(url)[0] or "image/jpeg"
	if not content_type.startswith("image/"):
		raise frappe.DoesNotExistError(_("No catalogue image"))

	frappe.response.type = "download"
	frappe.response.display_content_as = "inline"
	frappe.response.content_type = content_type
	# neutral name - nothing from the storage path
	frappe.response.filename = f"{item_code}.{content_type.split('/')[-1]}"
	frappe.response.filecontent = content
