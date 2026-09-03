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

	// The trigger is the Button field in the KGGK Sync section, not a toolbar button - it
	// belongs beside the settings it acts on, where it can be found.
	prefill_target_site(frm) {
		if (frm.is_dirty()) {
			// The server reads these from the database, so an unsaved To Site would produce
			// a refusal that contradicts what is on screen.
			frappe.msgprint({
				title: __("Unsaved Changes"),
				indicator: "orange",
				message: __("Save the settings first, then press the button."),
			});
			return;
		}
		start_prefill(0);
	},

	view_sync_logs() {
		frappe.set_route("List", "KGGK Sync Log");
	},
});

// The check is a background job, and the answer lands on a KGGK Sync Log. Rather than hold
// the user in front of a dialog for something that can take minutes, send them to that
// document: it updates itself, survives a page reload, and is still there tomorrow.
//
// Only the refusals are answered inline - a missing setting or an unreachable target comes
// back from the server as a thrown message, which is what you want when you just pressed a
// button.
function start_prefill(apply) {
	frappe.call({
		method: "gke_customization.gke_order_forms.doc_events.kggk_sync.start_prefill",
		args: { apply: apply },
		freeze: true,
		freeze_message: apply
			? __("Queueing the prefill...")
			: __("Checking the connection..."),
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
