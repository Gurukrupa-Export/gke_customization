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

// What a finished prefill run offers next. A check offers both actions; a field-creation
// run offers the push, and offers creation again for whatever was left out or failed - so
// the whole job can be finished from the one document instead of starting over.
function offer_apply(frm) {
	frappe.call({
		method: "gke_customization.gke_order_forms.doc_events.kggk_sync.prefill_result",
		args: { log_name: frm.doc.name },
		callback(r) {
			const out = r.message;
			if (!out) return;

			// A run that queued records has nothing left to offer.
			if (out.action === "records" || out.action === "all") {
				render_summary(frm, out);
				return;
			}

			render_summary(frm, out);

			const outstanding = out.fields_to_create || [];
			if (outstanding.length) {
				frm.add_custom_button(
					__("Create Missing Fields"),
					() => choose_fields(out),
					__("Actions")
				).addClass("btn-primary");
			}

			if (!out.items_missing && !out.boms_missing) return;

			// The push is the one the server can refuse, and it says why. Showing the reason
			// beats offering a button that throws when pressed.
			if (out.blocked_reason) {
				frm.dashboard.add_comment(
					__("Cannot push records: {0}", [out.blocked_reason]),
					"orange",
					true
				);
				return;
			}

			frm.add_custom_button(
				__("Push Missing Records"),
				() => confirm_records(out, frm.doc.name),
				__("Actions")
			);
		},
	});
}

// Not every missing field is wanted. Some belong to a module the target does not run, and
// creating them there is clutter nobody will remove - so the list is presented and the
// operator decides. Everything is ticked by default, because that is the common case.
function choose_fields(out) {
	const outstanding = out.fields_to_create || [];
	// Only the identity fields still outstanding. After a partial run the result still lists
	// every identity field it ever found, and treating an already-created one as "unticked"
	// would warn about a problem that no longer exists.
	const identityLeft = (out.identity_fields || []).filter((f) => outstanding.includes(f));
	const identity = new Set(identityLeft);

	const options = outstanding.map((f) => ({
		label: identity.has(f)
			? `${frappe.utils.escape_html(f)} <span class="text-muted">— ${__(
					"needed to match records"
			  )}</span>`
			: frappe.utils.escape_html(f),
		value: f,
		checked: 1,
	}));

	const dialog = new frappe.ui.Dialog({
		title: __("Create Fields on the Target"),
		size: "large",
		fields: [
			{
				fieldtype: "HTML",
				options: `<p class="text-muted">${__(
					"These are created on {0}. Untick anything you do not want.",
					[frappe.utils.escape_html(out.target)]
				)}</p>`,
			},
			{
				fieldname: "fields",
				fieldtype: "MultiCheck",
				label: __("Fields to create"),
				options: options,
				columns: 1,
			},
		],
		primary_action_label: __("Create Selected"),
		primary_action() {
			const chosen = dialog.get_value("fields") || [];
			if (!chosen.length) {
				frappe.msgprint({
					title: __("Nothing Selected"),
					indicator: "orange",
					message: __("Tick at least one field, or close this dialog."),
				});
				return;
			}

			// Leaving these out is allowed, but it is not a small thing: without them a
			// record cannot be matched on the target and the push refuses it rather than
			// guessing at its name. Better said here than met later as a wall of failures.
			const dropped = identityLeft.filter((f) => !chosen.includes(f));
			const go = () => {
				dialog.hide();
				run_action({ action: "fields", fields: JSON.stringify(chosen) });
			};

			if (dropped.length) {
				frappe.confirm(
					__(
						"{0} is not selected. Without it, records of that type cannot be " +
							"matched on the target and will be refused rather than sent. Continue?",
						[dropped.join(", ")]
					),
					go
				);
				return;
			}
			go();
		},
	});
	dialog.show();
}

function render_summary(frm, out) {
	const rows = [
		[__("Target"), frappe.utils.escape_html(out.target)],
		[__("Manufacturing Plans scanned"), out.plans_scanned],
		[__("Items missing on target"), `${out.items_missing} / ${out.items_total}`],
		[__("BOMs missing on target"), `${out.boms_missing} / ${out.boms_total}`],
	];

	// A run that created fields reports what happened to each one; a check reports how many
	// it would create.
	if (out.fields_created || out.fields_skipped) {
		rows.push([__("Fields created"), (out.fields_created || []).length]);
		if ((out.fields_skipped || []).length) {
			rows.push([__("Fields not selected"), out.fields_skipped.length]);
		}
		if ((out.fields_failed || []).length) {
			rows.push([
				`<span class="text-danger">${__("Fields that failed")}</span>`,
				`<span class="text-danger">${out.fields_failed.length}</span>`,
			]);
		}
	} else {
		rows.push([__("Custom fields to create"), (out.fields_to_create || []).length]);
	}

	// The number the summary used to leave out, and the one that decides whether any of the
	// others can be believed: a record whose batch could not be asked about is unknown, not
	// absent, and a check carrying any is not a check.
	if (out.unchecked) {
		rows.push([
			`<span class="text-danger">${__("Records that could not be checked")}</span>`,
			`<span class="text-danger">${out.unchecked}</span>`,
		]);
	}

	let html = `<table class="table table-bordered" style="margin:0">
		${rows.map(([k, v]) => `<tr><td style="width:60%">${k}</td><td>${v}</td></tr>`).join("")}
	</table>`;

	html += field_list(__("Still to be created"), out.fields_to_create);
	html += field_list(__("Created on the target"), out.fields_created);
	html += field_list(__("Could not be created"), out.fields_failed);

	// Findings, not faults. A standard field missing on the target means the two sites run
	// different app versions; a same-named custom field would hide that behind something
	// that only looks right, so these are shown and never created - and they do not stop
	// anything, because they are a permanent fact about two deployments rather than a
	// transient fault.
	(out.warnings || []).forEach((note) => {
		html += `<p style="margin-top:12px" class="text-muted">${frappe.utils.escape_html(note)}</p>`;
	});

	html += field_list(__("Standard fields absent on the target"), out.standard_field_gaps);

	if ((out.expected_absent || []).length) {
		html += `<p style="margin-top:12px" class="text-muted">${__(
			"Not examined, because the target has no such table: {0}",
			[frappe.utils.escape_html(out.expected_absent.join(", "))]
		)}</p>`;
	}

	frm.dashboard.add_section(html, __("Prefill Result"));
}

function field_list(title, entries) {
	if (!(entries || []).length) return "";
	return `<p style="margin-top:12px"><b>${title}</b></p>
		<div style="max-height:160px;overflow:auto"><code>${entries
			.map(frappe.utils.escape_html)
			.join("<br>")}</code></div>`;
}

function confirm_records(out, check_log) {
	frappe.confirm(
		__(
			"Push {0} item(s) and {1} BOM(s) to {2}?<br><br>" +
				"They are queued and sent in the background.",
			[out.items_missing, out.boms_missing, frappe.utils.escape_html(out.target)]
		),
		// Naming the run binds the push to it: the server re-reads that log and refuses if
		// To Site has moved since it ran.
		() => run_action({ action: "records", check_log: check_log })
	);
}

function run_action(args) {
	frappe.call({
		method: "gke_customization.gke_order_forms.doc_events.kggk_sync.start_prefill",
		args: args,
		freeze: true,
		freeze_message: __("Queueing..."),
		callback(r) {
			if (r.exc || !r.message) return;
			frappe.set_route("Form", "KGGK Sync Log", r.message.log);
		},
	});
}
