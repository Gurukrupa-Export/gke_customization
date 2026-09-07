// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("Data Migration in KGGK", {
	refresh(frm) {
		// "Why isn't it syncing" should be answered on the screen, not in a log file.
		if (frm.doc.enable_sync) return;
		frm.dashboard.set_headline(
			__("KGGK Sync is off. Nothing is pushed to the To Site until it is switched on."),
			"orange"
		);
	},

	// Two buttons, because they are two different decisions. Reading the target is free and
	// reversible; creating fields on it is neither. Rolling them into one press meant nobody
	// could create the missing fields without also committing to pushing ten thousand
	// records at the other site.
	check_target_site(frm) {
		if (unsaved(frm)) return;
		start(frm, "check");
	},

	prefill_target_site(frm) {
		if (unsaved(frm)) return;
		frappe.confirm(
			__(
				"Create every custom field that {0} is missing?<br><br>" +
					"This writes to the other site. No Items or BOMs are pushed.",
				[frappe.utils.escape_html(frm.doc.to_site || "the target")]
			),
			() => start(frm, "fields")
		);
	},

	view_sync_logs() {
		frappe.set_route("List", "KGGK Sync Log");
	},
});

function unsaved(frm) {
	if (!frm.is_dirty()) return false;
	// The server reads these from the database, so an unsaved To Site would produce a
	// refusal that contradicts what is on screen.
	frappe.msgprint({
		title: __("Unsaved Changes"),
		indicator: "orange",
		message: __("Save the settings first, then press the button."),
	});
	return true;
}

// Both actions are background jobs, and the answer lands on a KGGK Sync Log. Rather than
// hold the user in front of a dialog for something that can take minutes, send them to that
// document: it updates itself, survives a page reload, and is still there tomorrow.
//
// Only the refusals are answered inline - a missing setting or an unreachable target comes
// back from the server as a thrown message, which is what you want when you just pressed a
// button.
function start(frm, action) {
	frappe.call({
		method: "gke_customization.gke_order_forms.doc_events.kggk_sync.start_prefill",
		args: { action: action },
		freeze: true,
		freeze_message:
			action === "check" ? __("Checking the connection...") : __("Queueing the field creation..."),
		callback(r) {
			if (r.exc || !r.message) return;
			frappe.show_alert({
				message: r.message.connection || __("Started"),
				indicator: "green",
			});
			frappe.set_route("Form", "KGGK Sync Log", r.message.log);
		},
	});
}
