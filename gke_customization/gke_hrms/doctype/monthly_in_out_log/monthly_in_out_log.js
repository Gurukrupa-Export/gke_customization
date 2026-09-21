// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

const MIL_RESOLVED_STATUSES = [
	"Auto-Resolved (Approved OT)",
	"Auto-Closed (Shift End)",
	"HR-Approved",
	"Rejected",
];

frappe.ui.form.on("Monthly In-Out Log", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.docstatus === 2) return;

		frm.add_custom_button(__("Fetch Latest Data"), () => {
			frm.call({
				method: "populate_from_attendance",
				doc: frm.doc,
				freeze: true,
			}).then((r) => {
				// populate_from_attendance swallows its own exceptions and
				// returns False; never claim success when it failed
				if (r.message) {
					frappe.show_alert({
						message: __("Monthly In-Out Log refreshed"),
						indicator: "green",
					});
				} else {
					frappe.show_alert({
						message: __(
							"Refresh failed. Please check the Error Log."
						),
						indicator: "red",
					});
				}
				frm.reload_doc();
			});
		});

		if (
			frm.doc.punch_error &&
			!MIL_RESOLVED_STATUSES.includes(frm.doc.resolution_status)
		) {
			frm.add_custom_button(
				__("Resolve Error Punch"),
				() => open_resolve_dialog(frm)
			).addClass("btn-primary");
		}
	},
});

function open_resolve_dialog(frm) {
	frappe
		.call({
			method: "gke_customization.gke_hrms.ot_resolver.get_resolution_options",
			args: {
				employee: frm.doc.employee,
				attendance_date: frm.doc.attendance_date,
			},
		})
		.then((r) => show_resolve_dialog(frm, r.message || {}));
}

function show_resolve_dialog(frm, options) {
	const action_options = [{ label: "", value: "" }];

	if (options.approved_ot) {
		action_options.push({
			label: __("Use approved OT"),
			value: "approve_ot",
		});
	}

	if (options.missing_out) {
		action_options.push({
			label: __("Close at shift end (no OT)"),
			value: "auto_close",
		});
	}

	// 'Set OUT' only fixes a Missing OUT; the server rejects it for any
	// other punch error, so do not offer it
	if (options.punch_error === "Missing OUT") {
		action_options.push({
			label: __("Enter actual check-out time"),
			value: "set_out",
		});
	}

	action_options.push({
		label: __("Reject"),
		value: "reject",
	});

	const dialog = new frappe.ui.Dialog({
		title: __("Resolve Error Punch: {0}", [frm.doc.punch_error]),
		fields: [
			{
				fieldtype: "HTML",
				options: `<div style="margin-bottom:10px; word-break:break-word">
					<b>${__("Punch ledger")}:</b>
					${frappe.utils.escape_html(frm.doc.punch_ledger || "-")}
				</div>`,
			},
			{
				fieldname: "ot_preview",
				fieldtype: "HTML",
				options: ot_preview_html(options, ""),
			},
			{
				fieldname: "action",
				label: __("Action"),
				fieldtype: "Select",
				reqd: 1,
				options: action_options,
				onchange() {
					const is_set_out =
						dialog.get_value("action") === "set_out";

					dialog.set_df_property(
						"out_time",
						"hidden",
						is_set_out ? 0 : 1
					);

					dialog.set_df_property(
						"out_time",
						"reqd",
						is_set_out ? 1 : 0
					);

					if (!is_set_out) {
						dialog.set_value("out_time", "");
					}

					dialog.fields_dict.ot_preview.$wrapper.html(
						ot_preview_html(
							options,
							dialog.get_value("action")
						)
					);
				},
			},
			{
				fieldname: "out_time",
				label: __("Actual Check-out (date & time)"),
				fieldtype: "Datetime",
				hidden: 1,
			},
			{
				fieldname: "remarks",
				label: __("Remarks"),
				fieldtype: "Small Text",
			},
		],
		primary_action_label: __("Resolve"),
		primary_action(values) {
			frm.call({
				method: "resolve_error",
				doc: frm.doc,
				args: {
					action: values.action,
					out_time: values.out_time,
					remarks: values.remarks,
				},
				freeze: true,
			}).then(() => {
				frappe.show_alert({
					message: __(
						"Error punch resolved and attendance updated"
					),
					indicator: "green",
				});
				dialog.hide();
				frm.reload_doc();
			});
		},
	});

	dialog.show();
}

function ot_preview_html(options, action) {
	const alert = (cls, msg) =>
		`<div class="alert ${cls}" style="margin-bottom:10px">${msg}</div>`;

	if (action === "approve_ot" && options.expected_out) {
		return alert(
			"alert-success",
			__(
				"Check-out will be set to <b>{0}</b> (shift end + approved OT {1}).",
				[
					options.expected_out,
					options.approved_ot_hours || "",
				]
			)
		);
	}

	if (action === "auto_close" && options.shift_end) {
		return alert(
			"alert-warning",
			__(
				"Check-out will be set to <b>{0}</b> (shift end, no OT).",
				[options.shift_end]
			)
		);
	}

	if (action === "set_out") {
		return alert(
			"alert-info",
			__("Check-out will be the time you enter below.")
		);
	}

	if (action === "reject") {
		return alert(
			"alert-danger",
			__(
				"Attendance will be left as-is and the error stays closed."
			)
		);
	}

	let hint;

	if (options.approved_ot) {
		hint = __(
			"Approved OT Log found ({0}). Resolving with it sets check-out to <b>{1}</b>.",
			[
				options.approved_ot_hours || "",
				options.expected_out || "",
			]
		);
	} else {
		hint = __("No approved OT Log for this day.");
	}

	if (options.shift_end) {
		hint +=
			" " +
			__(
				"Closing at shift end sets check-out to <b>{0}</b>.",
				[options.shift_end]
			);
	}

	return alert("alert-info", hint);
}
