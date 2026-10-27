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
	},

	onload: function (report) {
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
				.text(".apsd-report .datatable { display: none !important; } .apsd-drill, .apsd-drill:hover, .apsd-drill:focus { text-decoration: none !important; border-bottom: 0 !important; } .apsd-drill:hover { color: #0b5ed7 !important; } .apsd-pdf:hover { filter: brightness(1.12); }")
				.appendTo("head");
		}

		$(document)
			.off("click.apsd")
			.on("click.apsd", ".apsd-drill", function () {
				const bucket = $(this).data("bucket");
				const label = $(this).data("label") || bucket;
				frappe.call({
					method: `${APSD_METHOD}.get_bucket_invoices`,
					args: {
						filters: frappe.query_report.get_filter_values(),
						bucket: bucket,
					},
					freeze: true,
					callback: (r) => apsd_show_invoices(label, r.message || []),
				});
			});

		$(document)
			.off("click.apsdpdf")
			.on("click.apsdpdf", ".apsd-pdf", function () {
				// send exactly what is on screen (minus the button) so the PDF always matches
				const $copy = $("#apsd-container").clone();
				$copy.find(".apsd-pdf").parent().remove();
				open_url_post(`/api/method/${APSD_METHOD}.download_pdf`, { html: $copy.html() });
			});
	},
};

function apsd_show_invoices(label, rows) {
	const body = rows
		.map(
			(d) => `<tr>
				<td><a href="${frappe.utils.get_form_link(d.voucher_type, d.voucher_no)}" target="_blank">${frappe.utils.escape_html(d.voucher_no)}</a></td>
				<td>${frappe.utils.escape_html(d.party || "")}</td>
				<td>${frappe.datetime.str_to_user(d.posting_date) || ""}</td>
				<td>${frappe.datetime.str_to_user(d.due_date) || ""}</td>
				<td>${frappe.utils.escape_html(d.bill_no || "")}</td>
				<td style="text-align:right">${d.age}</td>
				<td style="text-align:right">${format_currency(d.outstanding)}</td>
			</tr>`
		)
		.join("");

	const dialog = new frappe.ui.Dialog({
		title: `${label} (${rows.length})`,
		size: "extra-large",
		fields: [{ fieldtype: "HTML", fieldname: "list" }],
	});
	dialog.fields_dict.list.$wrapper.html(`
		<div style="max-height:60vh;overflow:auto">
		<table class="table table-bordered table-sm">
			<thead><tr>
				<th>${__("Voucher")}</th><th>${__("Supplier")}</th><th>${__("Posting Date")}</th>
				<th>${__("Due Date")}</th><th>${__("Bill No")}</th>
				<th style="text-align:right">${__("Age (Days)")}</th>
				<th style="text-align:right">${__("Outstanding")}</th>
			</tr></thead>
			<tbody>${body || `<tr><td colspan="7">${__("No records")}</td></tr>`}</tbody>
		</table></div>`);
	dialog.show();
}