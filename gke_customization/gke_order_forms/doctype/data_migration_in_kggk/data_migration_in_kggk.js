// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

// Prefill the KGGK testing site.
//
// Two presses on purpose. The first only looks and reports; the second creates Custom
// Fields on another site and queues records at it. If the Testing Site field has been
// pointed somewhere unintended, the dry run is the last chance to notice — so the dialog
// names the target and never pre-selects the destructive option.

frappe.ui.form.on("Data Migration in KGGK", {
	// The trigger is the Button field in the Manufacturing Plan Testing Sync section, not a
	// toolbar button - it belongs beside the settings it acts on, where it can be found.
	prefill_testing_site(frm) {
		if (frm.is_dirty()) {
			// The server reads these from the database, so an unsaved Testing Site would
			// produce a refusal that contradicts what is on screen.
			frappe.msgprint({
				title: __("Unsaved Changes"),
				indicator: "orange",
				message: __("Save the settings first, then press the button."),
			});
			return;
		}
		check_testing_site(frm);
	},
});

function check_testing_site(frm) {
	frappe.call({
		method: "gke_customization.gke_order_forms.doc_events.kggk_sync.prefill_testing_site",
		args: { apply: 0 },
		freeze: true,
		freeze_message: __("Checking the testing site..."),
		callback(r) {
			if (r.exc || !r.message) return;
			show_prefill_summary(frm, r.message);
		},
	});
}

function show_prefill_summary(frm, out) {
	const rows = [
		[__("Target"), frappe.utils.escape_html(out.target)],
		[__("Manufacturing Plans scanned"), out.plans_scanned],
		[__("Custom fields to create"), (out.fields_to_create || []).length],
		[__("Items missing on target"), `${out.items_missing} / ${out.items_total}`],
		[__("BOMs missing on target"), `${out.boms_missing} / ${out.boms_total}`],
	];

	let html = `<table class="table table-bordered" style="margin:0">
		${rows.map(([k, v]) => `<tr><td style="width:60%">${k}</td><td>${v}</td></tr>`).join("")}
	</table>`;

	if ((out.fields_to_create || []).length) {
		html += `<p style="margin-top:12px"><b>${__("Will be created on the target")}</b></p>
			<div style="max-height:160px;overflow:auto"><code>${out.fields_to_create
				.map(frappe.utils.escape_html)
				.join("<br>")}</code></div>`;
	}

	// A standard field missing on the target means the two sites run different app
	// versions. Creating a same-named custom field would hide that behind something that
	// only looks right, so these are shown and never created.
	if ((out.standard_field_gaps || []).length) {
		html += `<p style="margin-top:12px"><b>${__("Standard fields absent on the target")}</b><br>
			<span class="text-muted">${__(
				"These are not custom fields, so they are not created — the two sites are running different app versions."
			)}</span></p>
			<div style="max-height:120px;overflow:auto"><code>${out.standard_field_gaps
				.map(frappe.utils.escape_html)
				.join("<br>")}</code></div>`;
	}

	if ((out.schema_unreadable || []).length) {
		html += `<p style="margin-top:12px" class="text-danger">${__(
			"Could not read the target's field list for: {0}. Nothing can be reconciled for those.",
			[out.schema_unreadable.join(", ")]
		)}</p>`;
	}

	const nothing_to_do =
		!(out.fields_to_create || []).length && !out.items_missing && !out.boms_missing;

	const d = new frappe.ui.Dialog({
		title: __("Testing Site Check"),
		fields: [{ fieldtype: "HTML", fieldname: "summary", options: html }],
		primary_action_label: nothing_to_do ? __("Close") : __("Create and Push"),
		primary_action() {
			d.hide();
			if (nothing_to_do) return;
			apply_prefill(frm, out);
		},
	});
	d.show();
}

function apply_prefill(frm, out) {
	frappe.confirm(
		__(
			"Create {0} custom field(s) on {1} and push {2} item(s) and {3} BOM(s)?<br><br>This writes to the other site.",
			[
				(out.fields_to_create || []).length,
				frappe.utils.escape_html(out.target),
				out.items_missing,
				out.boms_missing,
			]
		),
		() => {
			frappe.call({
				method: "gke_customization.gke_order_forms.doc_events.kggk_sync.prefill_testing_site",
				args: { apply: 1 },
				freeze: true,
				freeze_message: __("Prefilling the testing site..."),
				callback(r) {
					if (r.exc || !r.message) return;
					const res = r.message;
					frappe.msgprint({
						title: __("Prefill Complete"),
						indicator: (res.fields_failed || []).length ? "orange" : "green",
						message: res.message,
					});
				},
			});
		}
	);
}
