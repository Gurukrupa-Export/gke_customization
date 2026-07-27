// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt


frappe.query_reports["Repair Tag Weight Difference Report"] = {

	"filters": [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1
		},
		{
			fieldname: "tag_no",
			label: __("Tag No"),
			fieldtype: "Data"
		},
		{
			fieldname: "party",
			label: __("Party"),
			fieldtype: "Data"
		}
	],

	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data, default_formatter);
		if (!data) return value;

		// Diff button (overview gross-wt diff) coloring
		if (column.fieldname === "diff") {
			const v = flt(data.diff);
			if (v < 0) value = `<span style="color:#e74c3c;font-weight:700;">${value}</span>`;
			else if (v > 0) value = `<span style="color:#27ae60;font-weight:700;">${value}</span>`;
		}

		if (column.fieldname === "status") {
			const colours = { "Sale": "#2980b9", "STOCK": "#e67e22" };
			const c = colours[data.status];
			if (c) value = `<span style="color:${c};font-weight:600;">${value}</span>`;
		}

		if (column.fieldname === "repair_type") {
			if (data.repair_type === "Cust Repair")
				value = `<span style="color:#8e44ad;">${value}</span>`;
			else if (data.repair_type === "GK Repair")
				value = `<span style="color:#16a085;">${value}</span>`;
		}

		const weight_cols = ["gross_wt", "dia_wt", "stone_wt", "other_wt", "gold_wt", "chain_wt"];
		if (weight_cols.includes(column.fieldname) && flt(data[column.fieldname]) < 0) {
			value = `<span style="color:#e74c3c;">${value}</span>`;
		}

		// Render Detail / Diff as clickable icon buttons
		if (column.fieldname === "btn_detail") {
			value = `<button class="btn btn-xs btn-default btn-finish-detail" data-tag="${data.docname}" title="${__("View Item Detail")}">
						<i class="fa fa-search"></i></button>`;
		}
		if (column.fieldname === "btn_diff") {
			value = `<button class="btn btn-xs btn-default btn-diff-detail" data-tag="${data.docname}" title="${__("View Difference Detail")}">
						<i class="fa fa-search"></i></button>`;
		}

		return value;
	},

	"onload": function (report) {
		// Use document-level delegation since the DataTable re-renders rows
		// dynamically (virtual scroll) — report.wrapper binding can miss clicks
		// on rows rendered after the initial load.
		$(document).off("click", ".btn-finish-detail").on("click", ".btn-finish-detail", function (e) {
			e.preventDefault();
			e.stopPropagation();
			const tag = $(this).attr("data-tag");
			if (tag) show_finish_good_detail(tag);
		});

		$(document).off("click", ".btn-diff-detail").on("click", ".btn-diff-detail", function (e) {
			e.preventDefault();
			e.stopPropagation();
			const tag = $(this).attr("data-tag");
			if (tag) show_difference_detail(tag);
		});
	}
};

// ── Popup 1: Item Finish Good Detail — pulled from Repair Order + new BOM ──────
function show_finish_good_detail(tag_no) {
	frappe.call({
		method: "frappe.client.get",
		args: { doctype: "Repair Order", name: tag_no },
		callback: function (r) {
			if (!r.message) { frappe.msgprint(__("Repair Order not found")); return; }
			const ro = r.message;

			frappe.call({
				method: "frappe.client.get",
				args: { doctype: "BOM", name: ro.new_bom },
				callback: function (r2) {
					const bom = r2.message || {};

					const dialog = new frappe.ui.Dialog({
						title: __("Item Finish Good Detail — {0}", [tag_no]),
						size: "large",
						fields: [{ fieldtype: "HTML", fieldname: "html_content" }]
					});

					dialog.fields_dict.html_content.$wrapper.html(`
						<style>
							.fgd-grid { display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px 20px; margin-bottom:14px; }
							.fgd-field label { font-size:11px; color:#888; margin:0; display:block; }
							.fgd-field span  { font-weight:600; font-size:13px; }
							.fgd-wt-row { display:flex; gap:14px; flex-wrap:wrap; background:#f9f9f9;
							              padding:10px 14px; border-radius:4px; }
							.fgd-wt-item label { font-size:11px; color:#888; display:block; margin:0; }
							.fgd-wt-item span  { font-size:14px; font-weight:700; color:#2c3e50; }
						</style>
						<div class="fgd-grid">
							<div class="fgd-field"><label>Repair Order No</label><span>${ro.name}</span></div>
							<div class="fgd-field"><label>Batch No</label><span>${ro.serial_and_design_code_order_form || "-"}</span></div>
							<div class="fgd-field"><label>Customer</label><span>${ro.customer_code || "-"}</span></div>
							<div class="fgd-field"><label>Style-Bio (Item)</label><span>${ro.item || "-"}</span></div>
							<div class="fgd-field"><label>Repair Type</label><span>${ro.product_type || "-"}</span></div>
							<div class="fgd-field"><label>Status</label><span>${ro.workflow_state || "-"}</span></div>
							<div class="fgd-field"><label>Old BOM</label><span>${ro.bom || "-"}</span></div>
							<div class="fgd-field"><label>New BOM</label><span>${ro.new_bom || "-"}</span></div>
						</div>
						<div class="fgd-wt-row">
							<div class="fgd-wt-item"><label>Touch</label><span>${bom.metal_touch || "-"}</span></div>
							<div class="fgd-wt-item"><label>Gross Wt</label><span>${flt(bom.gross_weight,3)}</span></div>
							<div class="fgd-wt-item"><label>Gold Wt</label><span>${flt(bom.metal_weight,3)}</span></div>
							<div class="fgd-wt-item"><label>Dia Wt</label><span>${flt(bom.total_diamond_weight_in_gms,3)}</span></div>
							<div class="fgd-wt-item"><label>Stone Wt</label><span>${flt(bom.total_gemstone_weight_in_gms,3)}</span></div>
							<div class="fgd-wt-item"><label>Other Wt</label><span>${flt(bom.other_weight,3)}</span></div>
							<div class="fgd-wt-item"><label>Finding Wt</label><span>${flt(bom.finding_weight_,3)}</span></div>
						</div>
					`);
					dialog.show();
				}
			});
		}
	});
}

// ── Popup 2: Repair Item Difference Detail — old_bom vs new_bom, row per weight type
function show_difference_detail(tag_no) {
	frappe.call({
		method: "frappe.client.get",
		args: { doctype: "Repair Order", name: tag_no },
		callback: function (r) {
			if (!r.message) { frappe.msgprint(__("Repair Order not found")); return; }
			const ro = r.message;

			// fetch both BOMs in parallel
			frappe.run_serially([
				() => frappe.call({ method: "frappe.client.get", args: { doctype: "BOM", name: ro.bom } }),
				() => frappe.call({ method: "frappe.client.get", args: { doctype: "BOM", name: ro.new_bom } })
			]).then(results => {
				const old_bom = (results[0] && results[0].message) || {};
				const new_bom = (results[1] && results[1].message) || {};

				const rows = [
					{ label: "Metal",   field: "metal_weight" },
					{ label: "Diamond", field: "total_diamond_weight_in_gms" },
					{ label: "Stone",   field: "total_gemstone_weight_in_gms" },
					{ label: "Other",   field: "other_weight" },
					{ label: "Chain",   field: "finding_weight_" }
				];

				let rows_html = "";
				let tot_prv = 0, tot_diff = 0, tot_wt = 0;

				rows.forEach(rw => {
					const prv  = flt(old_bom[rw.field], 3);
					const wt   = flt(new_bom[rw.field], 3);
					const diff = flt(wt - prv, 3);
					tot_prv += prv; tot_wt += wt; tot_diff += diff;
					const diff_color = diff < 0 ? "color:#e74c3c;" : diff > 0 ? "color:#27ae60;" : "";
					rows_html += `
						<tr>
							<td>${rw.label}</td>
							<td style="text-align:right;">${prv}</td>
							<td style="text-align:right;${diff_color}font-weight:600;">${diff}</td>
							<td style="text-align:right;">${wt}</td>
						</tr>`;
				});

				const dialog = new frappe.ui.Dialog({
					title: __("Repair Item Difference Detail — {0}", [tag_no]),
					size: "large",
					fields: [{ fieldtype: "HTML", fieldname: "html_content" }]
				});

				dialog.fields_dict.html_content.$wrapper.html(`
					<style>
						.dd-table { width:100%; border-collapse:collapse; font-size:12px; }
						.dd-table th { background:#f0f0f0; padding:6px 10px; border:1px solid #ddd;
						               text-align:center; font-size:11px; }
						.dd-table td { padding:6px 10px; border:1px solid #eee; }
						.dd-table tfoot td { background:#f9f9f9; font-weight:700; border-top:2px solid #bbb; }
					</style>
					<table class="dd-table">
						<thead>
							<tr><th>Material</th><th>Prv Wt (Old BOM)</th><th>Diff Wt</th><th>Weight (New BOM)</th></tr>
						</thead>
						<tbody>${rows_html}</tbody>
						<tfoot>
							<tr>
								<td style="text-align:right;">Total</td>
								<td style="text-align:right;">${flt(tot_prv,3)}</td>
								<td style="text-align:right;color:#e74c3c;">${flt(tot_diff,3)}</td>
								<td style="text-align:right;">${flt(tot_wt,3)}</td>
							</tr>
						</tfoot>
					</table>
				`);
				dialog.show();
			});
		}
	});
}