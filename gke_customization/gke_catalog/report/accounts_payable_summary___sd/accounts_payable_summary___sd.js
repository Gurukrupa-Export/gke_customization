// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Accounts Payable Summary - SD"] = {
	filters: [
		{
			fieldname: "summary_type",
			label: __("Summary Type"),
			fieldtype: "Select",
			options: "Customer Summary\nMonthly Summary",
			default: "Customer Summary",
			on_change: function () {
				let is_monthly = frappe.query_report.get_filter_value("summary_type") === "Monthly Summary";
				frappe.query_report.toggle_filter_display("calculate_ageing_with", is_monthly);
				frappe.query_report.toggle_filter_display("from_date", is_monthly);
				frappe.query_report.toggle_filter_display("to_date", is_monthly);
			},
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "report_date",
			label: __("Posting Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "ageing_based_on",
			label: __("Ageing Based On"),
			fieldtype: "Select",
			options: "Posting Date\nDue Date",
			default: "Due Date",
		},
		{
			fieldname: "calculate_ageing_with",
			label: __("Calculate Ageing With"),
			fieldtype: "Select",
			options: "Report Date\nToday Date",
			default: "Report Date",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -30),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "finance_book",
			label: __("Finance Book"),
			fieldtype: "Link",
			options: "Finance Book",
		},
		{
			fieldname: "cost_center",
			label: __("Cost Center"),
			fieldtype: "Link",
			options: "Cost Center",
			get_query: () => {
				var company = frappe.query_report.get_filter_value("company");
				return {
					filters: {
						company: company,
					},
				};
			},
		},
		{
			fieldname: "party_type",
			label: __("Party Type"),
			fieldtype: "Autocomplete",
			options: get_party_type_options(),
			on_change: function () {
				frappe.query_report.set_filter_value("party", "");
				frappe.query_report.toggle_filter_display(
					"supplier_group",
					frappe.query_report.get_filter_value("party_type") !== "Supplier"
				);
			},
		},
		{
			fieldname: "party",
			label: __("Party"),
			fieldtype: "MultiSelectList",
			options: "party_type",
			get_data: function (txt) {
				if (!frappe.query_report.filters) return;

				let party_type = frappe.query_report.get_filter_value("party_type");
				if (!party_type) return;

				return frappe.db.get_link_options(party_type, txt);
			},
		},
		{
			fieldname: "payment_terms_template",
			label: __("Payment Terms Template"),
			fieldtype: "Link",
			options: "Payment Terms Template",
		},
		{
			fieldname: "supplier_group",
			label: __("Supplier Group"),
			fieldtype: "Link",
			options: "Supplier Group",
		},
		{
			fieldname: "based_on_payment_terms",
			label: __("Based On Payment Terms"),
			fieldtype: "Check",
		},
		{
			fieldname: "for_revaluation_journals",
			label: __("Revaluation Journals"),
			fieldtype: "Check",
		},
	],

	onload: function (report) {
		report.page.add_inner_button(__("Accounts Payable"), function () {
			var filters = report.get_values();
			frappe.set_route("query-report", "Accounts Payable - SD", { company: filters.company });
		});
		let is_monthly = frappe.query_report.get_filter_value("summary_type") === "Monthly Summary";
		frappe.query_report.toggle_filter_display("calculate_ageing_with", is_monthly);
		frappe.query_report.toggle_filter_display("from_date", is_monthly);
		frappe.query_report.toggle_filter_display("to_date", is_monthly);
	},

	// Freeze Party Type and Party columns in Monthly Summary
	after_datatable_render: function (datatable) {
		apply_frozen_columns(datatable);
	},
};

erpnext.utils.add_dimensions("Accounts Payable Summary - SD", 9);

function get_party_type_options() {
	let options = [];
	frappe.db
		.get_list("Party Type", { filters: { account_type: "Payable" }, fields: ["name"] })
		.then((res) => {
			res.forEach((party_type) => {
				options.push(party_type.name);
			});
		});
	return options;
}

function apply_frozen_columns(datatable) {
	const STYLE_ID = "ap-summary-frozen-cols";
	document.getElementById(STYLE_ID)?.remove();

	// restore rows hidden by a previous render (e.g. after switching back to Customer Summary)
	datatable?.wrapper?.querySelectorAll("[data-ap-hidden]").forEach((r) => {
		r.style.display = "";
		r.removeAttribute("data-ap-hidden");
	});

	// remove scroll listener from a previous render
	if (datatable && datatable.__frozen_sync) {
		datatable.__frozen_scroller?.removeEventListener("scroll", datatable.__frozen_sync);
		datatable.__frozen_sync = null;
	}

	const is_monthly = frappe.query_report.get_filter_value("summary_type") === "Monthly Summary";
	if (!is_monthly || !datatable) return;

	// Find the two columns by fieldname (falls back to label)
	const cols = datatable.datamanager.getColumns();
	const find = (fieldname, label) =>
		cols.find((c) => c.id === fieldname) ||
		cols.find((c) => (c.name || "").toString().trim() === label);

	// Outstanding Amount: starts in its normal position and sticks once it
	// scrolls up to the 3rd column slot (right after Party Type and Party)
	const outstanding =
		cols.find((c) => c.id === "outstanding") ||
		cols.find((c) => (c.name || "").toString().trim().toLowerCase().startsWith("outstanding"));

	const frozen = [find("party_type", "Party Type"), find("party", "Party"), outstanding].filter(
		(c, i, arr) => c && arr.indexOf(c) === i
	);

	const wrapper = datatable.wrapper;
	let left = 0;

	// Header row stays visible on vertical scroll
	let css = `
		.datatable .dt-header {
			position: sticky;
			top: 0;
			z-index: 4;
		}
		.datatable .dt-header .dt-cell {
			background: var(--subtle-fg, #f3f3f3);
		}
		/* hide the blank inline filter row under the header */
		.datatable .dt-row-filter {
			display: none !important;
		}
		.datatable .dt-cell--header {
			position: sticky;
			top: 0;
			z-index: 3;
		}`;

	frozen.forEach((col, i) => {
		const idx = col.colIndex;
		const header = wrapper.querySelector(`.dt-cell--header.dt-cell--col-${idx}`);
		const width = header ? header.offsetWidth : col.width || 120;

		// body cells: sticky left
		css += `
		.datatable .dt-scrollable .dt-cell--col-${idx} {
			position: sticky !important;
			left: ${left}px;
			z-index: 2;
			background: var(--card-bg, #fff);
		}`;

		// header + filter row cells: positioned by JS (see sync below)
		css += `
		.datatable .dt-header .dt-cell--col-${idx} {
			position: sticky !important;
			top: 0;
			left: auto !important;
			z-index: 5;
			background: var(--subtle-fg, #f3f3f3);
		}`;

		if (i === frozen.length - 1) {
			css += `
		.datatable .dt-cell--col-${idx} {
			box-shadow: 2px 0 3px -1px rgba(0, 0, 0, 0.15);
		}`;
		}

		left += width;
	});

	const style = document.createElement("style");
	style.id = STYLE_ID;
	style.textContent = css;
	document.head.appendChild(style);

	hide_filter_row(wrapper);

	if (!frozen.length) return;

	// The header scrolls horizontally separately from the body, so CSS sticky
	// can't hold it. Move the frozen header cells to line up with the body cells.
	const scroller = wrapper.querySelector(".dt-scrollable");
	if (!scroller) return;

	const sync = () => {
		requestAnimationFrame(() => {
			hide_filter_row(wrapper);
			frozen.forEach((col) => {
				const idx = col.colIndex;
				const head_cells = wrapper.querySelectorAll(`.dt-header .dt-cell--col-${idx}`);
				const body_cell = wrapper.querySelector(`.dt-scrollable .dt-cell--col-${idx}`);
				if (!body_cell) return;

				head_cells.forEach((cell) => {
					cell.style.transform = "";
					const delta = body_cell.getBoundingClientRect().left - cell.getBoundingClientRect().left;
					if (Math.abs(delta) > 0.5) cell.style.transform = `translateX(${delta}px)`;
				});
			});
		});
	};

	datatable.__frozen_sync = sync;
	datatable.__frozen_scroller = scroller;
	scroller.addEventListener("scroll", sync, { passive: true });
	sync();
}

// Hide the blank inline filter row that sits under the column headers
function hide_filter_row(wrapper) {
	const rows = new Set(wrapper.querySelectorAll(".dt-row-filter"));
	// anything in the header block after the first row is the filter row
	wrapper.querySelectorAll(".dt-header .dt-row").forEach((row, i) => {
		if (i > 0) rows.add(row);
	});
	rows.forEach((row) => {
		row.style.setProperty("display", "none", "important");
		row.setAttribute("data-ap-hidden", "1");
	});
}