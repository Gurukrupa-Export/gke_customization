// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

// A run is a background job, so this form is how anyone watches one. While it is going the
// form refreshes itself; when it is over it offers the two things you actually want -
// retrying what failed, and, after a prefill check, going ahead with it.

const POLL_MS = 5000;
// A run that goes quiet for this long is a dead worker, not a slow one. Stop refreshing and
// let the user decide rather than spinning at them forever.
const POLL_CEILING_MS = 10 * 60 * 1000;

frappe.ui.form.on("KGGK Sync Log", {
	refresh(frm) {
		// refresh() fires many times per form. Clearing first is what stops a stack of
		// intervals all reloading the same document.
		stop_polling(frm);

		const running = ["Queued", "Running"].includes(frm.doc.status);

		if (running) {
			frm.dashboard.add_progress(__("Progress"), [
				{
					title: __("{0}% complete", [Math.round(frm.doc.progress || 0)]),
					width: `${frm.doc.progress || 0}%`,
					progress_class: "progress-bar-success",
				},
			]);
			start_polling(frm);
			frm.add_custom_button(__("Refresh Now"), () => frm.reload_doc());
		}

		if (["Failed", "Partially Completed"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Retry Failed"), () => retry(frm), __("Actions"))
				.addClass("btn-primary");
		}

		// A check that finished Partially Completed still has findings worth reading - it is
		// the incomplete ones you most want to look at - so the summary is rendered either
		// way. Whether Apply is offered is a separate question, answered by the server.
		if (frm.doc.trigger === "Prefill" && ["Completed", "Partially Completed"].includes(frm.doc.status)) {
			offer_apply(frm);
		}
	},

	onload_post_render(frm) {
		frm.page.wrapper.on("remove", () => stop_polling(frm));
	},
});

function start_polling(frm) {
	const started = Date.now();
	frm.__kggk_poll = setInterval(() => {
		if (Date.now() - started > POLL_CEILING_MS) {
			stop_polling(frm);
			return;
		}
		if (!frm.doc || frm.is_dirty()) return;
		frm.reload_doc();
	}, POLL_MS);
}

function stop_polling(frm) {
	if (!frm.__kggk_poll) return;
	clearInterval(frm.__kggk_poll);
	frm.__kggk_poll = null;
}

function retry(frm) {
	frappe.confirm(
		__("Queue another run for the records that failed here?"),
		() => {
			frappe.call({
				method: "gke_customization.gke_order_forms.doc_events.kggk_sync.retry_log",
				args: { log_name: frm.doc.name },
				freeze: true,
				freeze_message: __("Queueing the retry..."),
				callback(r) {
					if (r.exc || !r.message) return;
					frappe.set_route("Form", "KGGK Sync Log", r.message);
				},
			});
		}
	);
}

// The second of the two presses. The first one wrote nothing; this one creates Custom
// Fields on another site and queues records at it, so it names the target and says so.
function offer_apply(frm) {
	frappe.call({
		method: "gke_customization.gke_order_forms.doc_events.kggk_sync.prefill_result",
		args: { log_name: frm.doc.name },
		callback(r) {
			const out = r.message;
			if (!out || out.applied) return;

			render_summary(frm, out);

			// The server refuses an unusable check too; this only avoids offering a button
			// that would throw. Both read the same `blocked_reason`.
			if (out.blocked_reason) {
				frm.dashboard.add_comment(out.blocked_reason, "orange", true);
				return;
			}

			const nothing_to_do =
				!(out.fields_to_create || []).length && !out.items_missing && !out.boms_missing;
			if (nothing_to_do) return;

			frm.add_custom_button(
				__("Create and Push"),
				() => confirm_apply(out, frm.doc.name),
				__("Actions")
			).addClass("btn-primary");
		},
	});
}

function render_summary(frm, out) {
	const rows = [
		[__("Target"), frappe.utils.escape_html(out.target)],
		[__("Manufacturing Plans scanned"), out.plans_scanned],
		[__("Custom fields to create"), (out.fields_to_create || []).length],
		[__("Items missing on target"), `${out.items_missing} / ${out.items_total}`],
		[__("BOMs missing on target"), `${out.boms_missing} / ${out.boms_total}`],
	];

	// The number the summary used to leave out, which is the one that decides whether any of
	// the others can be believed: a record whose batch could not be asked about is unknown,
	// not absent, and a check carrying any is not a check.
	if (out.unchecked) {
		rows.push([
			`<span class="text-danger">${__("Records that could not be checked")}</span>`,
			`<span class="text-danger">${out.unchecked}</span>`,
		]);
	}

	let html = `<table class="table table-bordered" style="margin:0">
		${rows.map(([k, v]) => `<tr><td style="width:60%">${k}</td><td>${v}</td></tr>`).join("")}
	</table>`;

	if ((out.fields_to_create || []).length) {
		html += `<p style="margin-top:12px"><b>${__("Will be created on the target")}</b></p>
			<div style="max-height:160px;overflow:auto"><code>${out.fields_to_create
				.map(frappe.utils.escape_html)
				.join("<br>")}</code></div>`;
	}

	// A standard field missing on the target means the two sites run different app versions.
	// Creating a same-named custom field would hide that behind something that only looks
	// right, so these are shown and never created.
	if ((out.standard_field_gaps || []).length) {
		html += `<p style="margin-top:12px"><b>${__("Standard fields absent on the target")}</b><br>
			<span class="text-muted">${__(
				"These are not custom fields, so they are not created - the two sites are running different app versions."
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

	frm.dashboard.add_section(html, __("Check Result"));
}

function confirm_apply(out, check_log) {
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
				method: "gke_customization.gke_order_forms.doc_events.kggk_sync.start_prefill",
				// Naming the check is what binds the apply to it: the server re-reads that
				// log, and refuses if To Site has moved since it was run.
				args: { apply: 1, check_log: check_log },
				freeze: true,
				freeze_message: __("Queueing the prefill..."),
				callback(r) {
					if (r.exc || !r.message) return;
					frappe.set_route("Form", "KGGK Sync Log", r.message.log);
				},
			});
		}
	);
}
