// Copyright (c) 2026
// For license information, please see license.txt

// Report path: apps/gke_customization/gke_customization/gke_catalog/report/product_lifecycle

frappe.query_reports["Product Lifecycle"] = {
	filters: [
		{
			fieldname: "item_code_bom",
			label: __("Item Code / BOM"),
			fieldtype: "Data",
			on_change: function (report) {
				toggle_filters(report, "item_code_bom", "tag_no");
			},
		},
		{
			fieldname: "tag_no",
			label: __("Serial No"),
			fieldtype: "Data",
			on_change: function (report) {
				toggle_filters(report, "tag_no", "item_code_bom");
			},
		},
	],

	onload: function (report) {
		// This report is fully custom HTML, not the standard datatable grid.
		report.page.main.find(".report-wrapper").hide();

		report.custom_container = $('<div class="finish-tag-history"></div>').insertBefore(
			report.page.main.find(".report-wrapper")
		);

		inject_styles();
		render_history(report);
	},
};

function toggle_filters(report, active_field, other_field) {
	let active_val = frappe.query_report.get_filter_value(active_field);
	let other_filter = frappe.query_report.filters.find(
		(f) => f.df.fieldname === other_field
	);

	if (active_val) {
		frappe.query_report.set_filter_value(other_field, "");
		if (other_filter) other_filter.$input.prop("disabled", true);
	} else {
		if (other_filter) other_filter.$input.prop("disabled", false);
	}

	render_history(report);
}

let fetch_history_debounced = frappe.utils.debounce(fetch_and_render_history, 300);

function render_history(report) {
	let $container = report.custom_container;
	let filters = frappe.query_report.get_filter_values();

	if (!filters.item_code_bom && !filters.tag_no) {
		report._last_history_key = null;
		$container.html(
			`<div class="fth-hint">${__(
				"Enter an Item Code / BOM or a Serial No to view history."
			)}</div>`
		);
		return;
	}

	// A single paste can fire this twice (debounced "input" + trailing "change"
	// on blur) - collapse rapid repeats and skip refetching unchanged filters.
	fetch_history_debounced(report);
}

function fetch_and_render_history(report) {
	let $container = report.custom_container;
	let filters = frappe.query_report.get_filter_values();
	let key = JSON.stringify(filters);

	if (report._last_history_key === key) {
		return;
	}
	report._last_history_key = key;

	$container.html(`<div class="fth-hint">${__("Loading...")}</div>`);

	frappe.call({
		method:
			"gke_customization.gke_catalog.report.product_lifecycle.product_lifecycle.get_finish_tag_history",
		args: { filters: filters },
		callback: function (r) {
			let sections = (r.message && r.message.sections) || [];
			let item = r.message && r.message.item;
			$container.empty();

			if (item) {
				$container.append(build_item_banner_html(item));
			}

			if (!sections.length) {
				$container.append(`<div class="fth-hint">${__("No records found.")}</div>`);
				return;
			}

			sections.forEach((section) => {
				$container.append(build_section_html(section, report));
			});
		},
	});
}

function build_item_banner_html(item) {
	let image_html = item.image
		? `<img src="${frappe.utils.escape_html(item.image)}" alt="${frappe.utils.escape_html(
				item.item_code
		  )}">`
		: `<div class="fth-item-noimage">${__("No Image")}</div>`;

	return $(`
		<div class="fth-item-banner">
			<div class="fth-item-image">${image_html}</div>
			<div class="fth-item-info">
				<div class="fth-item-code">${frappe.utils.escape_html(item.item_code)}</div>
				${item.item_name ? `<div class="fth-item-name">${frappe.utils.escape_html(item.item_name)}</div>` : ""}
			</div>
		</div>
	`);
}

function build_section_html(section, report) {
	let $section = $(`
		<div class="fth-section">
			<div class="fth-section-header">${frappe.utils.escape_html(section.title)}</div>
		</div>
	`);

	let $tableWrapper = $('<div class="fth-table-wrapper"></div>');
	let filter_state = {};

	if (section.inline_filters && section.inline_filters.length) {
		$section.append(build_inline_filters_html(section, report, $tableWrapper, filter_state));
	}

	$section.append($tableWrapper);
	render_section_table($tableWrapper, section, filter_state);

	return $section;
}

function render_section_table($tableWrapper, section, filter_state) {
	$tableWrapper.empty();

	if (!section.rows || !section.rows.length) {
		$tableWrapper.append(`<div class="fth-empty">${__("No records")}</div>`);
		return;
	}

	let $table = $('<table class="fth-table"></table>');
	let $thead = $("<thead></thead>");

	let $headRow = $("<tr></tr>");
	section.columns.forEach((col) => {
		$headRow.append(`<th>${frappe.utils.escape_html(col.label)}</th>`);
	});
	$thead.append($headRow);

	if (section.filterable) {
		let $filterRow = $('<tr class="fth-column-filter-row"></tr>');
		section.columns.forEach((col) => {
			let $td = $("<td></td>");
			let $input = $(
				`<input type="text" class="fth-column-filter-input" data-fieldname="${col.fieldname}" placeholder="${__(
					"Filter"
				)}">`
			);
			if (filter_state[col.fieldname]) $input.val(filter_state[col.fieldname]);
			$td.append($input);
			$filterRow.append($td);
		});
		$thead.append($filterRow);
	}

	$table.append($thead);

	let $tbody = $("<tbody></tbody>");
	section.rows.forEach((row) => {
		let $tr = $("<tr></tr>");
		section.columns.forEach((col) => {
			let val = row[col.fieldname];
			$tr.append(`<td>${val != null && val !== "" ? frappe.utils.escape_html(String(val)) : ""}</td>`);
		});
		$tbody.append($tr);
	});
	$table.append($tbody);

	$tableWrapper.append($table);

	if (section.filterable) {
		wire_column_filters($tableWrapper, filter_state);
		apply_column_filters($tableWrapper, section, filter_state);
	}
}

function wire_column_filters($tableWrapper, filter_state) {
	$tableWrapper.find(".fth-column-filter-input").on("input", function () {
		let fieldname = $(this).data("fieldname");
		let val = $(this).val().trim().toLowerCase();

		if (val) {
			filter_state[fieldname] = val;
		} else {
			delete filter_state[fieldname];
		}

		apply_column_filters($tableWrapper, null, filter_state);
	});
}

function apply_column_filters($tableWrapper, section, filter_state) {
	let active_fieldnames = Object.keys(filter_state);
	let $rows = $tableWrapper.find("tbody tr");

	$tableWrapper.find(".fth-no-matches").remove();

	if (!active_fieldnames.length) {
		$rows.show();
		return;
	}

	let column_index = {};
	$tableWrapper.find(".fth-column-filter-input").each(function (idx) {
		column_index[$(this).data("fieldname")] = idx;
	});

	let visible_count = 0;
	$rows.each(function () {
		let $tds = $(this).find("td");
		let matches = active_fieldnames.every((fieldname) => {
			let idx = column_index[fieldname];
			let text = $tds.eq(idx).text().toLowerCase();
			return text.indexOf(filter_state[fieldname]) !== -1;
		});
		$(this).toggle(matches);
		if (matches) visible_count++;
	});

	if (!visible_count) {
		$tableWrapper.append(`<div class="fth-empty fth-no-matches">${__("No matching records")}</div>`);
	}
}

function build_inline_filters_html(section, report, $tableWrapper, filter_state) {
	let $bar = $('<div class="fth-inline-filters"></div>');

	section.inline_filters.forEach((df) => {
		let $field = $('<div class="fth-inline-field"></div>').appendTo($bar);

		let handle_change = (value) => {
			let filters = frappe.query_report.get_filter_values();
			$tableWrapper.html(`<div class="fth-empty">${__("Loading...")}</div>`);

			frappe.call({
				method:
					"gke_customization.gke_catalog.report.product_lifecycle.product_lifecycle.get_serial_no_section_data",
				args: {
					filters: filters,
					department: value,
				},
				callback: function (r) {
					if (r.message) {
						render_section_table($tableWrapper, r.message, filter_state);
					}
				},
			});
		};

		let control = frappe.ui.form.make_control({
			df: {
				fieldname: df.fieldname,
				label: df.label,
				fieldtype: df.fieldtype,
				options: df.options,
				placeholder: df.label,
				onchange: () => handle_change(control.get_value()),
			},
			parent: $field[0],
			render_input: true,
		});
		control.set_value(df.value || "");
		control.refresh();
	});

	return $bar;
}

function inject_styles() {
	if ($("#fth-style").length) return;
	$(`<style id="fth-style">
		.finish-tag-history { padding: 10px 2px 30px; }
		.fth-hint { padding: 20px 4px; color: #8d99a6; font-style: italic; }
		.fth-item-banner {
			display: flex;
			align-items: center;
			gap: 16px;
			margin-bottom: 20px;
			padding: 12px;
			border: 1px solid #d8d8d8;
			border-radius: 6px;
			background: #fafafa;
		}
		.fth-item-image {
			flex: 0 0 auto;
			width: 90px;
			height: 90px;
			display: flex;
			align-items: center;
			justify-content: center;
			border: 1px solid #e0e0e0;
			border-radius: 4px;
			background: #fff;
			overflow: hidden;
		}
		.fth-item-image img {
			max-width: 100%;
			max-height: 100%;
			object-fit: contain;
		}
		.fth-item-noimage {
			font-size: 11px;
			color: #b0b0b0;
			font-style: italic;
			text-align: center;
		}
		.fth-item-info { display: flex; flex-direction: column; gap: 2px; }
		.fth-item-code { font-size: 15px; font-weight: 600; color: #1f1f1f; }
		.fth-item-name { font-size: 12px; color: #6c7680; }
		.fth-section { margin-bottom: 24px; }
		.fth-section-header {
			background: #d9ead3;
			color: #1c3a13;
			font-weight: 600;
			font-style: italic;
			text-decoration: underline;
			padding: 8px 12px;
			border: 1px solid #b6d7a8;
		}
		.fth-table { width: 100%; border-collapse: collapse; margin-top: 2px; }
		.fth-table th, .fth-table td {
			border: 1px solid #d8d8d8;
			padding: 6px 10px;
			text-align: left;
			font-size: 12px;
			vertical-align: top;
			color: #1f1f1f;
		}
		.fth-table td {
			background: #fff;
		}
		.fth-table th {
			background: #f5f5f5;
			font-style: italic;
			text-decoration: underline;
			white-space: nowrap;
		}
		.fth-inline-filters {
			display: flex;
			flex-wrap: wrap;
			gap: 12px;
			align-items: flex-end;
			padding: 8px 10px;
			background: #f9f9f9;
			border: 1px solid #d8d8d8;
			border-top: none;
		}
		.fth-inline-field { width: 220px; }
		.fth-inline-field .frappe-control { margin-bottom: 0; }
		.fth-table-wrapper .fth-table { margin-top: 0; }
		.fth-column-filter-row td {
			background: #fcfcfc;
			padding: 4px 6px;
		}
		.fth-column-filter-input {
			width: 100%;
			box-sizing: border-box;
			font-size: 11px;
			padding: 3px 6px;
			border: 1px solid #d8d8d8;
			border-radius: 3px;
		}
		.fth-empty {
			padding: 10px 12px;
			color: #8d99a6;
			font-style: italic;
			border: 1px solid #eee;
			border-top: none;
		}
	</style>`).appendTo("head");
}