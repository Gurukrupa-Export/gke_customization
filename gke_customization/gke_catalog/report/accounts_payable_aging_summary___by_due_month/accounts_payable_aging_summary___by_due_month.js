// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

// APSDM v3 - By Due Month (Download PDF left of Actions)
const APSDM_METHOD =
	"gke_customization.gke_catalog.report.accounts_payable_aging_summary___by_due_month.accounts_payable_aging_summary___by_due_month";

frappe.query_reports["Accounts Payable Aging Summary - By Due Month"] = {
	// Only one filter, exactly like the reference screenshot.
	// Company = user default, As-On Date = today (report is a prepared report).
	filters: [
		{
			fieldname: "supplier_group",
			label: __("Supplier Group"),
			fieldtype: "Select",
			options: "All Suppliers\nDiamond",
			default: "All Suppliers",
		},
	],

	after_datatable_render: function () {
		const report = frappe.query_report;
		const first = ((report.raw_data || {}).result || [])[0];
		const html = first && (Array.isArray(first) ? first[0] : first.html);
		if (!html) return;

		$("#apsdm-container").remove();
		$('<div id="apsdm-container" style="padding: 8px 0;"></div>').html(html).insertBefore(report.$report);

		apsdm_place_pdf_button(report);
	},

	onload: function (report) {
		// "Download PDF" on the LEFT side of the Actions button (placed again after the toolbar is built)
		apsdm_place_pdf_button(report);
		setTimeout(() => apsdm_place_pdf_button(report), 600);
		setTimeout(() => apsdm_place_pdf_button(report), 1500);

		// Always open with "All Suppliers" (Frappe otherwise restores the last used filter),
		// unless the URL explicitly asks for a supplier group.
		const from_url = new URLSearchParams(window.location.search).get("supplier_group");
		if (!from_url) {
			setTimeout(() => {
				if (report.get_filter_value("supplier_group") !== "All Suppliers") {
					report.set_filter_value("supplier_group", "All Suppliers");
				}
			}, 400);
		}

		// The report is rendered as HTML (data row); hide the empty datatable.
		report.page.wrapper.addClass("apsdm-report");
		if (!$("#apsdm-style").length) {
			$("<style id='apsdm-style'>")
				.text(".apsdm-report .datatable { display: none !important; } .apsdm-drill, .apsdm-drill:hover, .apsdm-drill:focus { text-decoration: none !important; border-bottom: 0 !important; } .apsdm-drill:hover { color: #0b5ed7 !important; } .apsdm-pdf-btn { background: #c0392b !important; border: 0 !important; border-radius: 0 !important; color: #fff !important; font-weight: 600; margin-right: 8px; } .apsdm-pdf-btn:hover, .apsdm-dl-pdf:hover, .apsdm-dl-excel:hover { filter: brightness(1.12); }")
				.appendTo("head");
		}

		$(document)
			.off("click.apsdm")
			.on("click.apsdm", ".apsdm-drill", function () {
				const bucket = $(this).data("bucket");
				const label = $(this).data("label") || bucket;
				const filters = frappe.query_report.get_filter_values();
				frappe.call({
					method: `${APSDM_METHOD}.get_bucket_invoices`,
					args: { filters: filters, bucket: bucket },
					freeze: true,
					callback: (r) => apsdm_show_invoices(label, r.message || [], bucket, filters),
				});
			});
	},
};

function apsdm_place_pdf_button(report) {
	const $wrap = report.page.wrapper;
	$wrap.find(".apsdm-pdf-btn").remove();
	// make sure no old "primary action" copy of the button is left at the far right
	if (report.page.clear_primary_action) report.page.clear_primary_action();

	const $btn = $(`<button class="btn btn-sm apsdm-pdf-btn">${__("Download PDF")}</button>`).on("click", () =>
		apsdm_download_pdf()
	);

	// find the "Actions" button: by class first, then by its visible text anywhere in the page header
	let $target = $wrap.find(".page-actions .actions-btn-group").first();
	if (!$target.length) {
		const label = __("Actions");
		const $actions_btn = $wrap
			.find(".page-head button, .page-actions button, .standard-actions button")
			.filter((i, el) => $(el).text().trim().indexOf(label) === 0)
			.first();
		if ($actions_btn.length) {
			const $group = $actions_btn.closest(".btn-group, .actions-btn-group");
			$target = $group.length ? $group : $actions_btn;
		}
	}
	if (!$target.length) {
		console.warn("APSDM v3: Actions button not found - Download PDF placed at the start of the toolbar");
		$wrap.find(".page-actions").first().prepend($btn);
		return;
	}

	// Put [Download PDF] and Actions together in our own small row, so the order is always
	// [Download PDF] [Actions] whatever order Frappe lays out its own toolbar in.
	let $holder = $target.parent(".apsdm-actions-wrap");
	if (!$holder.length) {
		$holder = $('<div class="apsdm-actions-wrap" style="display:flex;align-items:center;gap:8px;"></div>');
		$holder.insertBefore($target);
		$holder.append($target);
	}
	$holder.prepend($btn);
	console.log("APSDM v3: Download PDF placed left of Actions");
}

function apsdm_download_pdf() {
	// send exactly what is on screen so the PDF always matches
	const html = $("#apsdm-container").html();
	if (!html) {
		frappe.msgprint(__("The report is not loaded yet."));
		return;
	}
	open_url_post(`/api/method/${APSDM_METHOD}.download_pdf`, { html: html });
}

function apsdm_show_invoices(label, rows, bucket, filters) {
	const esc = (v) => frappe.utils.escape_html(v || "");
	const date = (v) => frappe.datetime.str_to_user(v) || "";

	const body = rows
		.map(
			(d) => `<tr>
				<td class="nw"><a href="${frappe.utils.get_form_link(d.voucher_type, d.voucher_no)}" target="_blank">${esc(d.voucher_no)}</a></td>
				<td class="nw">${esc(d.party)}</td>
				<td class="name">${esc(d.supplier_name)}</td>
				<td class="nw">${date(d.posting_date)}</td>
				<td class="nw">${date(d.due_date)}</td>
				<td class="nw">${esc(d.bill_no)}</td>
				<td class="nw num">${d.age}</td>
				<td class="nw num amt">${format_currency(d.outstanding)}</td>
			</tr>`
		)
		.join("");

	const dialog = new frappe.ui.Dialog({
		title: `${label} (${rows.length})`,
		size: "extra-large",
		fields: [{ fieldtype: "HTML", fieldname: "list" }],
	});

	// use the screen width instead of the narrow default modal
	dialog.$wrapper.find(".modal-dialog").css({ "max-width": "min(1500px, 96vw)", width: "96vw" });

	dialog.fields_dict.list.$wrapper.html(`
		<style>
			.apsdm-list { max-height: 65vh; overflow: auto; }
			.apsdm-list table { width: 100%; border-collapse: collapse; font-size: 13px; }
			.apsdm-list th, .apsdm-list td { padding: 8px 12px; border: 1px solid #e3e8ee; vertical-align: middle; }
			.apsdm-list th { position: sticky; top: 0; z-index: 1; background: #eef3f9; font-weight: 700; white-space: nowrap; }
			.apsdm-list tbody tr:nth-child(even) td { background: #fafcfe; }
			.apsdm-list .nw { white-space: nowrap; }
			.apsdm-list .name { min-width: 260px; width: 100%; white-space: normal; }
			.apsdm-list .num { text-align: right; font-variant-numeric: tabular-nums; }
			.apsdm-list .amt { font-weight: 600; }
		</style>
		<div class="apsdm-list">
		<table>
			<thead><tr>
				<th>${__("Voucher")}</th>
				<th>${__("Supplier")}</th>
				<th>${__("Supplier Name")}</th>
				<th>${__("Posting Date")}</th>
				<th>${__("Due Date")}</th>
				<th>${__("Bill No")}</th>
				<th class="num">${__("Age (Days)")}</th>
				<th class="num">${__("Outstanding")}</th>
			</tr></thead>
			<tbody>${body || `<tr><td colspan="8">${__("No records")}</td></tr>`}</tbody>
		</table></div>`);
	dialog.show();

	// Download PDF / Download Excel in the dialog header
	const post = (method) =>
		open_url_post(`/api/method/${APSDM_METHOD}.${method}`, {
			// the exact rows shown in this dialog
			rows: JSON.stringify(rows),
			label: label,
			filters: JSON.stringify(filters),
		});

	const btn = "border:0;border-radius:0;color:#ffffff;font-weight:600;padding:6px 14px;box-shadow:none;";
	const $buttons = $(`
		<span class="apsdm-export" style="display:inline-flex;gap:8px;margin-right:12px;">
			<button type="button" class="btn btn-sm apsdm-dl-pdf" style="${btn}background:#c0392b;">${__("Download PDF")}</button>
			<button type="button" class="btn btn-sm apsdm-dl-excel" style="${btn}background:#1e8449;">${__("Download Excel")}</button>
		</span>`);
	$buttons.find(".apsdm-dl-pdf").on("click", () => post("download_bucket_pdf"));
	$buttons.find(".apsdm-dl-excel").on("click", () => post("download_bucket_excel"));

	const $actions = dialog.$wrapper.find(".modal-header .modal-actions");
	if ($actions.length) {
		$actions.prepend($buttons);
	} else {
		dialog.$wrapper.find(".modal-header").append($buttons);
	}
}