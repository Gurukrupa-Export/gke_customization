// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

const APSD_METHOD =
	"gke_customization.gke_catalog.report.accounts_payable_aging_summary_report.accounts_payable_aging_summary_report";

frappe.query_reports["Accounts Payable Aging Summary Report"] = {
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

		$("#apsd-container").remove();
		$('<div id="apsd-container" style="padding: 8px 0;"></div>').html(html).insertBefore(report.$report);

		apsd_place_pdf_button(report);
	},

	onload: function (report) {
		// "Download PDF" on the LEFT side of the Actions button (placed again after the toolbar is built)
		apsd_place_pdf_button(report);
		setTimeout(() => apsd_place_pdf_button(report), 600);
		setTimeout(() => apsd_place_pdf_button(report), 1500);

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
		report.page.wrapper.addClass("apsd-report");
		if (!$("#apsd-style").length) {
			$("<style id='apsd-style'>")
				.text(".apsd-report .datatable { display: none !important; } .apsd-drill, .apsd-drill:hover, .apsd-drill:focus { text-decoration: none !important; border-bottom: 0 !important; } .apsd-drill:hover { color: #0b5ed7 !important; } .apsd-pdf-btn { background: #c0392b !important; border: 0 !important; border-radius: 0 !important; color: #fff !important; font-weight: 600; margin-right: 8px; } .apsd-pdf-btn:hover, .apsd-dl-pdf:hover, .apsd-dl-excel:hover { filter: brightness(1.12); }")
				.appendTo("head");
		}

		$(document)
			.off("click.apsd")
			.on("click.apsd", ".apsd-drill", function () {
				const bucket = $(this).data("bucket");
				const label = $(this).data("label") || bucket;
				const filters = frappe.query_report.get_filter_values();
				frappe.call({
					method: `${APSD_METHOD}.get_bucket_invoices`,
					args: { filters: filters, bucket: bucket },
					freeze: true,
					callback: (r) => apsd_show_invoices(label, r.message || [], bucket, filters),
				});
			});
	},
};

function apsd_place_pdf_button(report) {
	const $wrap = report.page.wrapper;
	$wrap.find(".apsd-pdf-btn").remove();
	// make sure no old "primary action" copy of the button is left at the far right
	if (report.page.clear_primary_action) report.page.clear_primary_action();

	const $btn = $(`<button class="btn btn-sm apsd-pdf-btn">${__("Download PDF")}</button>`).on("click", () =>
		apsd_download_pdf()
	);

	// find the "Actions" button (by class first, then by its visible text anywhere in the page header)
	let $target = $wrap.find(".page-actions .actions-btn-group").first();
	if (!$target.length) {
		const $actions_btn = $wrap
			.find(".page-head button, .page-actions button")
			.filter((i, el) => $(el).text().trim() === __("Actions"))
			.first();
		if ($actions_btn.length) {
			const $group = $actions_btn.closest(".btn-group, .actions-btn-group");
			$target = $group.length ? $group : $actions_btn;
		}
	}
	if (!$target.length) {
		console.warn("APSD: Actions button not found, placing Download PDF at the start of the toolbar");
		$wrap.find(".page-actions").first().prepend($btn);
		return;
	}

	// Put [Download PDF] and Actions together in our own small row, so the order is always
	// [Download PDF] [Actions] whatever order Frappe lays out its own toolbar in.
	let $holder = $target.parent(".apsd-actions-wrap");
	if (!$holder.length) {
		$holder = $('<div class="apsd-actions-wrap" style="display:flex;align-items:center;gap:8px;"></div>');
		$holder.insertBefore($target);
		$holder.append($target);
	}
	$holder.prepend($btn);
}

function apsd_download_pdf() {
	// send exactly what is on screen so the PDF always matches
	const html = $("#apsd-container").html();
	if (!html) {
		frappe.msgprint(__("The report is not loaded yet."));
		return;
	}
	open_url_post(`/api/method/${APSD_METHOD}.download_pdf`, { html: html });
}

function apsd_show_invoices(label, rows, bucket, filters) {
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
			.apsd-list { max-height: 65vh; overflow: auto; }
			.apsd-list table { width: 100%; border-collapse: collapse; font-size: 13px; }
			.apsd-list th, .apsd-list td { padding: 8px 12px; border: 1px solid #e3e8ee; vertical-align: middle; }
			.apsd-list th { position: sticky; top: 0; z-index: 1; background: #eef3f9; font-weight: 700; white-space: nowrap; }
			.apsd-list tbody tr:nth-child(even) td { background: #fafcfe; }
			.apsd-list .nw { white-space: nowrap; }
			.apsd-list .name { min-width: 260px; width: 100%; white-space: normal; }
			.apsd-list .num { text-align: right; font-variant-numeric: tabular-nums; }
			.apsd-list .amt { font-weight: 600; }
		</style>
		<div class="apsd-list">
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
		open_url_post(`/api/method/${APSD_METHOD}.${method}`, {
			// the exact rows shown in this dialog
			rows: JSON.stringify(rows),
			label: label,
			filters: JSON.stringify(filters),
		});

	const btn = "border:0;border-radius:0;color:#ffffff;font-weight:600;padding:6px 14px;box-shadow:none;";
	const $buttons = $(`
		<span class="apsd-export" style="display:inline-flex;gap:8px;margin-right:12px;">
			<button type="button" class="btn btn-sm apsd-dl-pdf" style="${btn}background:#c0392b;">${__("Download PDF")}</button>
			<button type="button" class="btn btn-sm apsd-dl-excel" style="${btn}background:#1e8449;">${__("Download Excel")}</button>
		</span>`);
	$buttons.find(".apsd-dl-pdf").on("click", () => post("download_bucket_pdf"));
	$buttons.find(".apsd-dl-excel").on("click", () => post("download_bucket_excel"));

	const $actions = dialog.$wrapper.find(".modal-header .modal-actions");
	if ($actions.length) {
		$actions.prepend($buttons);
	} else {
		dialog.$wrapper.find(".modal-header").append($buttons);
	}
}