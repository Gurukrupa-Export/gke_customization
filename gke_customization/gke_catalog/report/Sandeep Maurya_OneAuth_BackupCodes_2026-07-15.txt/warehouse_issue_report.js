// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Warehouse Issue Report"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
			get_query: () => {
				const company = frappe.query_report.get_filter_value("company");
				return { filters: company ? { company: company } : {} };
			},
		},
		{
			fieldname: "manager",
			label: __("Manager"),
			fieldtype: "Link",
			options: "Employee",
			get_query: () => {
				const company = frappe.query_report.get_filter_value("company");
				return { filters: company ? { company: company } : {} };
			},
		},
		{ fieldname: "operation", label: __("Operation"), fieldtype: "Link", options: "Department Operation" },
		{
			fieldname: "warehouse",
			label: __("Employee Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
			get_query: () => {
				const filters = {
					employee: ["is", "set"],
					is_group: 0,
					disabled: 0,
				};
				const company = frappe.query_report.get_filter_value("company");
				if (company) filters.company = company;
				if (!frappe.query_report.get_filter_value("include_wip")) {
					filters.name = ["not like", "%WIP%"];
				}
				return { filters: filters };
			},
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: ["", "Running", "Close"].join("\n"),
		},
		{ fieldname: "include_wip", label: __("Include WIP Warehouses"), fieldtype: "Check", default: 0 },
		{ fieldname: "show_zero_rows", label: __("Show Rows With No Activity"), fieldtype: "Check", default: 0 },
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) return value;

		if (column.fieldname === "detail" && data.warehouse) {
			const wh = encodeURIComponent(data.warehouse);
			const touch = encodeURIComponent(data.slip_touch || "");
			return `<button class="btn btn-xs btn-default" data-wh="${wh}" data-touch="${touch}"
				onclick="frappe.query_reports['Warehouse Issue Report'].show_detail(decodeURIComponent(this.dataset.wh), decodeURIComponent(this.dataset.touch))">
				${__("View")}</button>`;
		}
		if (column.fieldname === "status" && data.status) {
			const color = data.status === "Running" ? "orange" : "green";
			return `<span class="indicator-pill ${color}">${value}</span>`;
		}
		if (column.fieldname === "loss" && data.loss > 0) {
			return `<span style="color: var(--red-600, #c0392b)">${value}</span>`;
		}
		if (column.fieldname === "balance") {
			return `<b>${value}</b>`;
		}
		return value;
	},

	show_detail(warehouse, touch) {
		const filters = Object.assign({}, frappe.query_report.get_filter_values(), {
			detail_warehouse: warehouse,
			detail_touch: touch || "",
		});
		const main =
			(frappe.query_report.data || []).find(
				(r) => r.warehouse === warehouse && (r.slip_touch || "") === (touch || "")
			) || {};
		const unit = "g";
		const n = (v) => (v === undefined || v === null || v === "" ? "" : Number(v).toFixed(3));
		const esc = (v) => frappe.utils.escape_html(v == null ? "" : String(v));

		const dialog = new frappe.ui.Dialog({
			title: touch
				? __("Warehouse History: {0} ({1})", [warehouse, touch])
				: __("Warehouse History: {0}", [warehouse]),
			size: "extra-large",
			fields: [{ fieldtype: "HTML", fieldname: "body" }],
		});
		const $body = dialog.fields_dict.body.$wrapper;
		$body.html(`<div class="text-muted" style="padding:16px">${__("Loading…")}</div>`);
		dialog.show();

		frappe
			.call({
				method: "frappe.desk.query_report.run",
				args: {
					report_name: "Warehouse Issue Report",
					filters: filters,
					ignore_prepared_report: 1,
				},
			})
			.then((r) => {
				const rows = ((r.message && r.message.result) || []).filter((d) => d && !Array.isArray(d));
				if (!rows.length) {
					$body.html(`<div class="text-muted" style="padding:16px">${__("Could not load entries. Please refresh the report and try again.")}</div>`);
					return;
				}
				const summary = `
					<div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px 16px;margin-bottom:12px;font-size:13px">
						<div><span class="text-muted">${__("Worker")}:</span> <b>${esc(main.employee_name)}</b></div>
						<div><span class="text-muted">${__("Manager")}:</span> ${esc(main.manager_name)}</div>
						<div><span class="text-muted">${__("Period")}:</span> ${frappe.datetime.str_to_user(filters.from_date)} – ${frappe.datetime.str_to_user(filters.to_date)}</div>
						<div><span class="text-muted">${__("Slip Touch")}:</span> ${esc(touch)}</div>
						<div><span class="text-muted">${__("Batch Issue")}:</span> ${n(main.batch_issue)} ${unit}</div>
						<div><span class="text-muted">${__("Extra Issue")}:</span> ${n(main.extra_issue)} ${unit}</div>
						<div><span class="text-muted">${__("Batch Receive")}:</span> ${n(main.batch_return)} ${unit}</div>
						<div><span class="text-muted">${__("Extra Receive")}:</span> ${n(main.extra_return)} ${unit}</div>
						<div><span class="text-muted">${__("Opening")}:</span> ${n(main.opening)} ${unit}</div>
						<div><span class="text-muted">${__("Loss")}:</span> ${n(main.loss)} ${unit}</div>
						<div><span class="text-muted">${__("Balance")}:</span> <b>${n(main.balance)} ${unit}</b></div>
					</div>`;

				const body = rows
					.map((d) => {
						const opening = d.entry_type === __("Opening");
						const se = d.voucher_no
							? `<a href="/app/stock-entry/${encodeURIComponent(d.voucher_no)}" target="_blank">${esc(d.voucher_no)}</a>`
							: "";
						return `<tr style="${opening ? "font-weight:600;background:var(--subtle-fg)" : ""}">
							<td>${d.posting_date ? frappe.datetime.str_to_user(d.posting_date) : ""}</td>
							<td>${esc(d.entry_type)}</td>
							<td>${esc(d.batch_no)}</td>
							<td>${esc(d.sub_category)}</td>
							<td>${esc(d.item_code)}</td>
							<td class="text-right">${n(d.issue_wt)}</td>
							<td class="text-right">${n(d.receive_wt)}</td>
							<td class="text-right" style="color:var(--red-600,#c0392b)">${n(d.loss)}</td>
							<td class="text-right"><b>${n(d.balance)}</b></td>
							<td>${se}</td>
						</tr>`;
					})
					.join("");

				$body.html(`
					${summary}
					<div style="max-height:60vh;overflow:auto;border:1px solid var(--border-color);border-radius:8px">
						<table class="table table-sm" style="margin:0;font-size:12.5px">
							<thead style="position:sticky;top:0;background:var(--card-bg);z-index:1">
								<tr>
									<th>${__("Entry Date")}</th><th>${__("Type")}</th><th>${__("Batch No (MWO)")}</th>
									<th>${__("Sub Category")}</th><th>${__("Item")}</th>
									<th class="text-right">${__("Issue Wt")}</th><th class="text-right">${__("Receive Wt")}</th>
									<th class="text-right">${__("Loss")}</th><th class="text-right">${__("Balance")}</th>
									<th>${__("Stock Entry")}</th>
								</tr>
							</thead>
							<tbody>${body}</tbody>
						</table>
					</div>
					<div class="text-muted" style="font-size:12px;margin-top:6px">
						${__("{0} entries. Balance after each entry = previous balance + issue − receive − loss.", [Math.max(rows.length - 1, 0)])}
					</div>`);
			});
	},
};
