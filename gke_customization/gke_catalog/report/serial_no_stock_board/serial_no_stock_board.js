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
	},
};

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
	let grand_total = { count: 0, gross_wt: 0, gold_wt: 0, chain_wt: 0, dia_wt: 0, stone_wt: 0 };

	STATUS_SUMMARY_ORDER.forEach((status) => {
		groups[status] = { count: 0, gross_wt: 0, gold_wt: 0, chain_wt: 0, dia_wt: 0, stone_wt: 0 };
	});

	data.forEach((row) => {
		let status = row.status || "Stock";
		if (!groups[status]) {
			groups[status] = { count: 0, gross_wt: 0, gold_wt: 0, chain_wt: 0, dia_wt: 0, stone_wt: 0 };
		}
		groups[status].count += 1;
		groups[status].gross_wt += flt(row.gross_wt);
		groups[status].gold_wt += flt(row.gold_wt);
		groups[status].chain_wt += flt(row.chain_wt);
		groups[status].dia_wt += flt(row.dia_wt);
		groups[status].stone_wt += flt(row.stone_wt);

		grand_total.count += 1;
		grand_total.gross_wt += flt(row.gross_wt);
		grand_total.gold_wt += flt(row.gold_wt);
		grand_total.chain_wt += flt(row.chain_wt);
		grand_total.dia_wt += flt(row.dia_wt);
		grand_total.stone_wt += flt(row.stone_wt);
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
				</tr>`;
		})
		.join("");

	let table_html = `
		<div class="status-summary-table-wrapper" style="margin: 10px 0;">
			<table class="table table-bordered" style="margin-bottom: 0;">
				<thead>
					<tr>
						<th>${__("Status")}</th>
						<th class="text-right">${__("Total Tag")}</th>
						<th class="text-right">${__("Gross Wt.")}</th>
						<th class="text-right">${__("Gold Wt")}</th>
						<th class="text-right">${__("Chain Wt.")}</th>
						<th class="text-right">${__("Dia Wt")}</th>
						<th class="text-right">${__("Stone Wt")}</th>
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
					</tr>
				</tbody>
			</table>
		</div>`;

	let $table = $(table_html).insertBefore(report.$report);

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

		$table.find(".status-summary-row").removeClass("table-active status-summary-row-active");
		if (next_status) {
			$(this).addClass("table-active status-summary-row-active");
		}
	});
}
