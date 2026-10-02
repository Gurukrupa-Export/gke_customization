// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Serial No Stock Board"] = {
	filters: [
		{
			"fieldname": "tag_no",
			"label": __("Serial No"),
			"fieldtype": "Link",
			"options": "Serial No",
			"reqd": 0,
			"on_change": function(report) {
				gke_handle_tag_no_change(report);
			},
		},
		{
			"fieldname": "tag_no_list",
			"label": __("Bulk Serial No"),
			"fieldtype": "Small Text",
			"hidden": 1,
			"reqd": 0,
		},
		{
			"fieldname": "customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"reqd": 0,
		},
		{
			"fieldname": "category",
			"label": __("Category"),
			"fieldtype": "Link",
			"options": "Attribute Value",
			"get_query": function() {
				return {
					filters: { "is_category": 1 }
				};
			},
			"reqd": 0,
		},
		{
			"fieldname": "sub_category",
			"label": __("Sub Category"),
			"fieldtype": "Link",
			"options": "Attribute Value",
			"get_query": function() {
				let category = frappe.query_report.get_filter_value("category");
				let filters = { "is_subcategory": 1 };
				if (category) {
					filters["parent_attribute_value"] = category;
				}
				return { filters: filters };
			},
			"reqd": 0,
		},
		{
			"fieldname": "setting_type",
			"label": __("Setting Type"),
			"fieldtype": "Data",
			"reqd": 0,
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "\nStock\nApprove\nTransfer\nSalesman\nLocker\nRepair\nIssue to Lab\nSale",
			"reqd": 0,
		},
		{
			"fieldname": "branch",
			"label": __("Branch"),
			"fieldtype": "Link",
			"options": "Branch",
			"reqd": 0,
		},
		{
			"fieldname": "warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"reqd": 0,
		},
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 0,
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"reqd": 0,
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"reqd": 0,
		},
	],

	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "status" && data && data.status) {
			let color_map = {
				"Stock": "green",
				"Approve": "blue",
				"Transfer": "purple",
				"Salesman": "orange",
				"Locker": "yellow",
				"Repair": "red",
				"Issue to Lab": "cyan",
				"Sale": "pink",
			};
			let color = color_map[data.status] || "grey";
			return `<span class="indicator-pill ${color}">${data.status}</span>`;
		}

		return value;
	},

	after_datatable_render: function(datatable_obj) {
		gke_render_status_summary(frappe.query_report);
		gke_setup_inline_filter_totals(frappe.query_report, datatable_obj);
	},

	onload: function(report) {
		gke_setup_bulk_serial_filter(report);
	},
};

function gke_setup_bulk_serial_filter(report) {
	let filter = report.get_filter("tag_no");
	if (!filter || !filter.$wrapper) return;

	// Page filters are rendered with only_input:true, so $wrapper is just a
	// flat ".form-group" div directly containing the input — there is no
	// nested ".control-input-wrapper" like on regular doctype forms.
	let $input_area = filter.$wrapper;
	if (!$input_area.length || $input_area.find(".gke-bulk-serial-icon").length) return;

	$input_area.css("position", "relative");
	filter.$input && filter.$input.css("padding-right", "26px");

	let $icon = $(`
		<span class="gke-bulk-serial-icon" title="${__("Bulk Paste Serial Nos")}"
			style="position:absolute; right:6px; top:50%; transform:translateY(-50%);
			       cursor:pointer; z-index:5; color: var(--text-muted);">
			${frappe.utils.icon("small-file", "sm")}
		</span>
	`);
	$input_area.append($icon);

	report._gke_bulk_serial_icon = $icon;
	gke_refresh_bulk_serial_icon(report, $icon);

	$icon.on("click", function(e) {
		e.stopPropagation();
		gke_open_bulk_serial_dialog(report, $icon);
	});
}

// Defining "on_change" on the tag_no filter (below) makes the report
// framework skip its default auto-refresh for this field, so this handler
// is responsible for triggering the refresh itself in every case, not just
// when it clears the stale bulk filter.
function gke_handle_tag_no_change(report) {
	let tag_no = report.get_filter_value("tag_no");
	if (tag_no && report.get_filter_value("tag_no_list")) {
		report.set_filter_value("tag_no_list", "");
		if (report._gke_bulk_serial_icon) {
			gke_refresh_bulk_serial_icon(report, report._gke_bulk_serial_icon);
		}
	}
	report.refresh();
}

function gke_refresh_bulk_serial_icon(report, $icon) {
	let raw = report.get_filter_value("tag_no_list") || "";
	let count = raw
		.split(/[\n,;|\t ]+/)
		.map((v) => v.trim())
		.filter(Boolean).length;

	if (count) {
		$icon.css("color", "var(--primary-color)");
		$icon.attr("title", __("{0} Serial No(s) selected — click to edit", [count]));
	} else {
		$icon.css("color", "var(--text-muted)");
		$icon.attr("title", __("Bulk Paste Serial Nos"));
	}
}

function gke_open_bulk_serial_dialog(report, $icon) {
	let existing = report.get_filter_value("tag_no_list") || "";

	let d = new frappe.ui.Dialog({
		title: __("Bulk Serial No"),
		fields: [
			{
				fieldname: "serial_no_text",
				fieldtype: "Small Text",
				label: __("Paste Serial Numbers"),
				description: __("Separate by new line, comma, space, or semicolon"),
				default: existing,
			},
		],
		primary_action_label: __("Apply"),
		primary_action: function(values) {
			let raw = (values.serial_no_text || "").trim();
			report.set_filter_value("tag_no_list", raw);
			if (raw) {
				report.set_filter_value("tag_no", "");
			}
			d.hide();
			gke_refresh_bulk_serial_icon(report, $icon);
			report.refresh();
		},
		secondary_action_label: __("Clear"),
		secondary_action: function() {
			report.set_filter_value("tag_no_list", "");
			d.hide();
			gke_refresh_bulk_serial_icon(report, $icon);
			report.refresh();
		},
	});

	d.show();
}

function gke_compute_detail_totals(rows) {
	let totals = { count: 0, gross_wt: 0, gold_wt: 0, chain_wt: 0, dia_wt: 0, stone_wt: 0, finding_wt: 0, other_wt: 0 };

	(rows || []).forEach((row) => {
		totals.count += 1;
		totals.gross_wt += flt(row.gross_wt);
		totals.gold_wt += flt(row.gold_wt);
		totals.chain_wt += flt(row.chain_wt);
		totals.dia_wt += flt(row.dia_wt);
		totals.stone_wt += flt(row.stone_wt);
		totals.finding_wt += flt(row.finding_wt);
		totals.other_wt += flt(row.other_wt);
	});

	return totals;
}

// Renders our own "Total" footer under the serial-no-wise detail table.
// Kept fully independent from report.data / add_total_row so it can never
// leak a synthetic row back into gke_render_status_summary's counts — it
// just re-renders from whatever rows are currently on screen.
function gke_render_detail_total(report, totals) {
	if (!report || !report.$report) return;

	report.page.main.find(".detail-total-table-wrapper").remove();

	let table_html = `
		<div class="detail-total-table-wrapper" style="margin: 10px 0;">
			<table class="table table-bordered" style="margin-bottom: 0;">
				<thead>
					<tr>
						<th>${__("Total Serial No.")}</th>
						<th class="text-right">${__("Gross Wt.")}</th>
						<th class="text-right">${__("Gold Wt")}</th>
						<th class="text-right">${__("Chain Wt.")}</th>
						<th class="text-right">${__("Dia Wt")}</th>
						<th class="text-right">${__("Stone Wt")}</th>
						<th class="text-right">${__("Finding Wt.")}</th>
						<th class="text-right">${__("Other Wt.")}</th>
					</tr>
				</thead>
				<tbody>
					<tr style="font-weight: bold;">
						<td>${totals.count}</td>
						<td class="text-right">${format_number(totals.gross_wt, null, 3)}</td>
						<td class="text-right">${format_number(totals.gold_wt, null, 3)}</td>
						<td class="text-right">${format_number(totals.chain_wt, null, 3)}</td>
						<td class="text-right">${format_number(totals.dia_wt, null, 3)}</td>
						<td class="text-right">${format_number(totals.stone_wt, null, 3)}</td>
						<td class="text-right">${format_number(totals.finding_wt, null, 3)}</td>
						<td class="text-right">${format_number(totals.other_wt, null, 3)}</td>
					</tr>
				</tbody>
			</table>
		</div>`;

	$(table_html).insertAfter(report.$report);
}

// The datatable's own per-column "in-table" filter row (typing a value under
// a column header) filters visible rows purely inside frappe-datatable and
// never calls report.datatable.refresh() or fires any report-level event, so
// our totals row/summary would otherwise stay frozen at the last full
// dataset. We patch columnmanager.applyFilter (the internal handler that
// runs on every filter keystroke) so we can recompute totals from whatever
// rows are actually visible once the built-in filtering finishes.
function gke_get_visible_rows(report, datatable) {
	if (!datatable || !datatable.datamanager || !datatable.bodyRenderer) return [];

	// datamanager.getData(index) reads from whatever dataset is currently
	// loaded in the datatable (the full dataset, or the subset loaded by
	// report.datatable.refresh() on a status-summary click) — unlike
	// report.data, which always stays the original, unfiltered dataset and
	// would go out of sync with visibleRowIndices after a status click.
	let visible_idx = datatable.bodyRenderer.visibleRowIndices || [];
	return datatable.datamanager.rowViewOrder
		.filter((index) => visible_idx.includes(index))
		.map((index) => datatable.datamanager.getData(index))
		.filter(Boolean);
}

function gke_setup_inline_filter_totals(report, datatable) {
	if (!datatable || !datatable.columnmanager) return;

	let columnmanager = datatable.columnmanager;
	let original_apply_filter = columnmanager.applyFilter.bind(columnmanager);

	columnmanager.applyFilter = function(filters) {
		let result = original_apply_filter(filters);
		Promise.resolve(result).then(() => {
			let visible_rows = gke_get_visible_rows(report, datatable);
			gke_render_detail_total(report, gke_compute_detail_totals(visible_rows));
		});
		return result;
	};
}

function gke_render_status_summary(report) {
	if (!report || !report.$report || !report.page) return;

	const STATUS_SUMMARY_ORDER = ["Stock", "Approve", "Transfer", "Salesman", "Locker", "Repair", "Issue to Lab", "Sale"];

	const STATUS_SUMMARY_COLOR = {
		"Stock": "green",
		"Approve": "blue",
		"Transfer": "purple",
		"Salesman": "orange",
		"Locker": "yellow",
		"Repair": "red",
		"Issue to Lab": "cyan",
		"Sale": "pink",
	};

	report.page.main.find(".status-summary-table-wrapper").remove();

	// This hook only fires after a real server fetch (never after our own
	// client-side datatable.refresh() below), so it's safe to snapshot the
	// full, unfiltered dataset here and reuse it for status filtering
	// without re-running the (expensive) report query on every click.
	report._gke_full_data = report.data || [];
	report._gke_active_status = null;

	let data = report._gke_full_data;
	let groups = {};
	let grand_total = { count: 0, gross_wt: 0, gold_wt: 0, chain_wt: 0, dia_wt: 0, stone_wt: 0, finding_wt: 0, other_wt: 0 };

	STATUS_SUMMARY_ORDER.forEach((status) => {
		groups[status] = { count: 0, gross_wt: 0, gold_wt: 0, chain_wt: 0, dia_wt: 0, stone_wt: 0, finding_wt: 0, other_wt: 0 };
	});

	data.forEach((row) => {
		let status = row.status || "Stock";
		if (!groups[status]) {
			groups[status] = { count: 0, gross_wt: 0, gold_wt: 0, chain_wt: 0, dia_wt: 0, stone_wt: 0, finding_wt: 0, other_wt: 0 };
		}
		groups[status].count += 1;
		groups[status].gross_wt += flt(row.gross_wt);
		groups[status].gold_wt += flt(row.gold_wt);
		groups[status].chain_wt += flt(row.chain_wt);
		groups[status].dia_wt += flt(row.dia_wt);
		groups[status].stone_wt += flt(row.stone_wt);
		groups[status].finding_wt += flt(row.finding_wt);
		groups[status].other_wt += flt(row.other_wt);

		grand_total.count += 1;
		grand_total.gross_wt += flt(row.gross_wt);
		grand_total.gold_wt += flt(row.gold_wt);
		grand_total.chain_wt += flt(row.chain_wt);
		grand_total.dia_wt += flt(row.dia_wt);
		grand_total.stone_wt += flt(row.stone_wt);
		grand_total.finding_wt += flt(row.finding_wt);
		grand_total.other_wt += flt(row.other_wt);
	});

	let current_status = report._gke_active_status;

	let rows_html = Object.keys(groups)
		.map((status) => {
			let g = groups[status];
			let color = STATUS_SUMMARY_COLOR[status] || "grey";
			let active = current_status === status ? "table-active status-summary-row-active" : "";
			return `
				<tr class="status-summary-row ${active}" data-status="${frappe.utils.escape_html(status)}" style="cursor:pointer;">
					<td><span class="indicator-pill ${color}">${frappe.utils.escape_html(status)}</span></td>
					<td class="text-right">${g.count}</td>
					<td class="text-right">${format_number(g.gross_wt, null, 3)}</td>
					<td class="text-right">${format_number(g.gold_wt, null, 3)}</td>
					<td class="text-right">${format_number(g.chain_wt, null, 3)}</td>
					<td class="text-right">${format_number(g.dia_wt, null, 3)}</td>
					<td class="text-right">${format_number(g.stone_wt, null, 3)}</td>
					<td class="text-right">${format_number(g.finding_wt, null, 3)}</td>
					<td class="text-right">${format_number(g.other_wt, null, 3)}</td>
				</tr>`;
		})
		.join("");

	let table_html = `
		<div class="status-summary-table-wrapper" style="margin: 10px 0;">
			<table class="table table-bordered" style="margin-bottom: 0;">
				<thead>
					<tr>
						<th>${__("Status")}</th>
						<th class="text-right">${__("Total Serial No.")}</th>
						<th class="text-right">${__("Gross Wt.")}</th>
						<th class="text-right">${__("Gold Wt")}</th>
						<th class="text-right">${__("Chain Wt.")}</th>
						<th class="text-right">${__("Dia Wt")}</th>
						<th class="text-right">${__("Stone Wt")}</th>
						<th class="text-right">${__("Finding Wt.")}</th>
						<th class="text-right">${__("Other Wt.")}</th>
					</tr>
				</thead>
				<tbody>
					${rows_html}
					<tr class="status-summary-row status-summary-total-row" data-status="" style="cursor:pointer; font-weight: bold;">
						<td>${__("Total")}</td>
						<td class="text-right">${grand_total.count}</td>
						<td class="text-right">${format_number(grand_total.gross_wt, null, 3)}</td>
						<td class="text-right">${format_number(grand_total.gold_wt, null, 3)}</td>
						<td class="text-right">${format_number(grand_total.chain_wt, null, 3)}</td>
						<td class="text-right">${format_number(grand_total.dia_wt, null, 3)}</td>
						<td class="text-right">${format_number(grand_total.stone_wt, null, 3)}</td>
						<td class="text-right">${format_number(grand_total.finding_wt, null, 3)}</td>
						<td class="text-right">${format_number(grand_total.other_wt, null, 3)}</td>
					</tr>
				</tbody>
			</table>
		</div>`;

	let $table = $(table_html).insertBefore(report.$report);

	gke_render_detail_total(report, grand_total);

	$table.find(".status-summary-row").on("click", function() {
		let status = $(this).attr("data-status") || "";
		let next_status = report._gke_active_status === status ? null : status;

		report._gke_active_status = next_status;

		let filtered = next_status
			? report._gke_full_data.filter((row) => (row.status || "Stock") === next_status)
			: report._gke_full_data;

		// Filter the already-fetched dataset directly in the datatable —
		// no server round-trip, so it's instant even on a large report.
		report.datatable.refresh(filtered);
		gke_render_detail_total(report, gke_compute_detail_totals(filtered));

		$table.find(".status-summary-row").removeClass("table-active status-summary-row-active");
		if (next_status) {
			$(this).addClass("table-active status-summary-row-active");
		}
	});
}
