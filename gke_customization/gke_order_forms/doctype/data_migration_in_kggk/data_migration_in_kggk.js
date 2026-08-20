// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt
//
// Follows the MOP Settings pattern: a deduplicated background job, a status headline, and
// a progress panel that polls only while a run is actually active.

frappe.ui.form.on("Data Migration in KGGK", {
	refresh(frm) {
		_render_status_headline(frm);
		_setup_sync_button(frm);
		_setup_custom_buttons(frm);
		_poll_progress(frm);
	},

	from_site(frm) {
		_warn_same_site(frm);
	},

	to_site(frm) {
		_warn_same_site(frm);
	},
});

const ACTIVE = ["Queued", "Running"];

function _host(url) {
	if (!url) return "";
	return String(url)
		.trim()
		.toLowerCase()
		.replace(/^https?:\/\//, "")
		.replace(/\/.*$/, "")
		.replace(/:\d+$/, "");
}

function _is_system_manager() {
	return frappe.user_roles && frappe.user_roles.includes("System Manager");
}

function _is_active(frm) {
	return ACTIVE.includes(frm.doc.sync_status);
}

// Say it while they are typing, not after a run silently does nothing.
function _warn_same_site(frm) {
	const from = _host(frm.doc.from_site);
	const to = _host(frm.doc.to_site);
	if (from && to && from === to) {
		frappe.msgprint({
			title: __("Same Site Configured"),
			message: __(
				"From Site and To Site both point at <b>{0}</b>. Nothing will sync while this is the case — a site is never allowed to push into itself.",
				[frappe.utils.escape_html(to)]
			),
			indicator: "red",
		});
	}
}

function _render_status_headline(frm) {
	frm.dashboard.clear_headline();
	const status = frm.doc.sync_status;

	if (!frm.doc.is_migrate) {
		frm.dashboard.set_headline_alert(
			__("Sync is off — tick Is Migrate to enable pushing to the To Site"),
			"gray"
		);
		return;
	}
	if (_host(frm.doc.from_site) && _host(frm.doc.from_site) === _host(frm.doc.to_site)) {
		frm.dashboard.set_headline_alert(
			__("From Site and To Site are the same — every push will be refused"),
			"red"
		);
		return;
	}

	const map = {
		Running: [__("Sync running"), "orange"],
		Queued: [__("Sync queued — waiting for a background worker"), "blue"],
		Failed: [__("Last sync failed — see the Migration Log below"), "red"],
		"Partially Completed": [
			__("Last sync partly failed — see the Migration Log below"),
			"yellow",
		],
		Completed: [__("Last sync completed"), "green"],
	};
	const entry = map[status];
	if (entry) frm.dashboard.set_headline_alert(entry[0], entry[1]);
}

function _setup_sync_button(frm) {
	const field = frm.fields_dict.sync_now;
	const $btn = field && field.$input;
	if (!$btn) return;

	const blocked = !_is_system_manager() || _is_active(frm) || !frm.doc.is_migrate;
	$btn.prop("disabled", blocked);
	if (blocked) {
		$btn.attr(
			"title",
			!_is_system_manager()
				? __("Only System Manager can start a sync.")
				: !frm.doc.is_migrate
				? __("Tick Is Migrate first.")
				: __("A sync is already running.")
		);
	} else {
		$btn.removeAttr("title");
	}

	// Re-bound on every refresh, so namespace the handler to avoid stacking duplicates.
	$btn.off("click.kggk").on("click.kggk", function () {
		if (blocked) return;
		frappe.prompt(
			[
				{
					fieldname: "limit",
					fieldtype: "Int",
					label: __("Maximum records to sync"),
					default: 200,
					reqd: 1,
					description: __(
						"Oldest unsynced first, for Items and BOMs separately. Large batches hold a background worker for a long time — run those off-hours."
					),
				},
			],
			(values) => {
				frappe.call({
					method: "sync_now",
					doc: frm.doc,
					args: { limit: values.limit },
					freeze: true,
					freeze_message: __("Queueing sync..."),
					callback: () => frm.reload_doc(),
				});
			},
			__("Sync to KGGK"),
			__("Queue")
		);
	});
}

function _setup_custom_buttons(frm) {
	if (!_is_system_manager()) return;

	if (cint(frm.doc.items_failed) + cint(frm.doc.boms_failed) > 0) {
		frm.add_custom_button(__("Retry Failed"), () => {
			frappe.call({
				method: "retry_failed",
				doc: frm.doc,
				freeze: true,
				callback: () => frm.reload_doc(),
			});
		});
	}

	frm.add_custom_button(__("Re-sync Since"), () => {
		if (!frm.doc.resync_since) {
			frappe.msgprint({
				title: __("Pick a Date"),
				message: __("Set <b>Re-sync From Date</b> first — it decides how far back to go."),
				indicator: "orange",
			});
			return;
		}
		frappe.confirm(
			__(
				"Re-push everything in scope modified on or after {0}? This includes records already marked synced.",
				[frappe.format(frm.doc.resync_since, { fieldtype: "Date" })]
			),
			() => {
				frappe.call({
					method: "start_resync",
					doc: frm.doc,
					args: { since: frm.doc.resync_since },
					freeze: true,
					callback: () => frm.reload_doc(),
				});
			}
		);
	});

	if (frm.doc.sync_log) {
		frm.add_custom_button(__("Clear Log"), () => {
			frappe.confirm(__("Clear the migration log?"), () => {
				frappe.call({
					method: "clear_log",
					doc: frm.doc,
					callback: () => frm.reload_doc(),
				});
			});
		});
	}
}

function cint(v) {
	return parseInt(v, 10) || 0;
}

let _poll_timer = null;

function _poll_progress(frm) {
	if (_poll_timer) {
		clearTimeout(_poll_timer);
		_poll_timer = null;
	}

	frappe.call({
		method:
			"gke_customization.gke_order_forms.doctype.data_migration_in_kggk.data_migration_in_kggk.get_sync_progress",
		callback(r) {
			if (r.exc || !r.message) return;
			_render_progress(frm, r.message);
			if (ACTIVE.includes(r.message.sync_status)) {
				_poll_timer = setTimeout(() => _poll_progress(frm), 5000);
			}
		},
	});
}

function _render_progress(frm, d) {
	const field = frm.fields_dict.sync_progress_html;
	if (!field || !field.$wrapper) return;

	const status = d.sync_status || "Idle";
	const pct = d.progress_percent || 0;
	const colour =
		status === "Completed"
			? "success"
			: status === "Failed"
			? "danger"
			: status === "Partially Completed"
			? "warning"
			: ACTIVE.includes(status)
			? "primary"
			: "secondary";

	const n = (v) => cint(v);
	const esc = (v) => frappe.utils.escape_html(String(v || ""));

	const html = `
<div style="border:1px solid var(--border-color);border-radius:6px;padding:12px 16px;margin:4px 0;">
  <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:8px;">
    <b>${esc(d.last_trigger || "No run yet")}${
		d.last_reference ? " · " + esc(d.last_reference) : ""
	}</b>
    <span class="badge badge-${colour}">${esc(status)}</span>
  </div>
  <div class="progress" style="height:12px;margin-bottom:8px;">
    <div class="progress-bar bg-${colour}" role="progressbar"
         style="width:${Math.min(pct, 100)}%;transition:width .4s ease;"
         aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"></div>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:6px 16px;font-size:12px;">
    <span><b>Items:</b> ${n(d.items_synced)}/${n(d.total_items)}</span>
    <span style="color:var(--red-500);"><b>Failed:</b> ${n(d.items_failed)}</span>
    <span style="color:var(--text-muted);"><b>Already synced:</b> ${n(d.items_skipped)}</span>
    <span><b>BOMs:</b> ${n(d.boms_synced)}/${n(d.total_boms)}</span>
    <span style="color:var(--red-500);"><b>Failed:</b> ${n(d.boms_failed)}</span>
    <span style="color:var(--orange-500);"><b>Field mismatches:</b> ${n(d.field_mismatches)}</span>
    <span><b>${pct.toFixed(1)}%</b></span>
  </div>
  ${
		d.last_error
			? `<div style="margin-top:8px;font-size:11px;color:var(--red-500);">${esc(
					d.last_error
			  )}</div>`
			: ""
  }
</div>`;

	let $box = field.$wrapper.find(".kggk-progress");
	if (!$box.length) {
		$box = $("<div class='kggk-progress'></div>").appendTo(field.$wrapper);
	}
	$box.html(html);
}
