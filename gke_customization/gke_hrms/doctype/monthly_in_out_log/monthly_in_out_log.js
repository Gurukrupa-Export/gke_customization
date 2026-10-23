// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

const MIL_RESOLVED_STATUSES = [
	"Auto-Resolved (Approved OT)",
	"Auto-Closed (Shift End)",
	"HR-Approved",
	"Rejected",
];

const FULL_DAY_ACTION = "adjust_punch_full_day";
const ADD_PUNCHES_ACTION = "add_missing_punches";
const MODE_AUTO = "Auto-fill from shift";
const MODE_MANUAL = "Enter manually";

frappe.ui.form.on("Monthly In-Out Log", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.docstatus === 2) return;

		frm.add_custom_button(__("Fetch Latest Data"), () => {
			frm.call({
				method: "populate_from_attendance",
				doc: frm.doc,
				freeze: true,
			}).then(() => {
				frappe.show_alert({
					message: __("Monthly In-Out Log refreshed"),
					indicator: "green",
				});
				frm.reload_doc();
			});
		});

		if (frm.doc.punch_error && !MIL_RESOLVED_STATUSES.includes(frm.doc.resolution_status)) {
			frm.add_custom_button(__("Resolve Error Punch"), () => open_resolve_dialog(frm)).addClass(
				"btn-primary"
			);
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
			freeze: true,
		})
		.then((r) => show_resolve_dialog(frm, r.message || {}));
}

// ---------------------------------------------------------------------------
// Dialog
// ---------------------------------------------------------------------------

function get_action_options(options) {
	const list = [{ label: "", value: "" }];

	// one action for every Missing OUT: prefilled with approved OT when it
	// exists, else the shift end; HR can override with the actual time
	if (options.missing_out) {
		list.push({ label: __("Set Check-out"), value: "set_out" });
	}

	if (options.add_punches_allowed) {
		list.push({
			label: __("Add Missing Punches (Manual Punch Entry)"),
			value: ADD_PUNCHES_ACTION,
		});
	}

	list.push(
		{ label: __("Adjust Punches & Mark Full Day"), value: FULL_DAY_ACTION },
		{ label: __("Reject"), value: "reject" }
	);
	return list;
}

function show_resolve_dialog(frm, options) {
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
				options: get_action_options(options),
				onchange: () => sync_dialog(dialog, options),
			},
			{
				fieldname: "inout_mode",
				label: __("IN/OUT Times"),
				fieldtype: "Select",
				options: `${MODE_AUTO}\n${MODE_MANUAL}`,
				default: MODE_AUTO,
				hidden: 1,
				onchange: () => sync_dialog(dialog, options),
			},
			{
				fieldname: "in_time",
				label: __("Check-in Time (date & time)"),
				fieldtype: "Datetime",
				hidden: 1,
				onchange: () => render_preview(dialog, options),
			},
			{
				fieldname: "out_time",
				label: __("Check-out Time (date & time)"),
				fieldtype: "Datetime",
				hidden: 1,
				onchange: () => render_preview(dialog, options),
			},
			{
				fieldname: "remarks",
				label: __("Remarks"),
				fieldtype: "Small Text",
			},
		],
		primary_action_label: __("Continue"),
		primary_action(values) {
			const args = build_resolve_args(values, options);
			if (!args) return;

			const submit = () => submit_resolution(frm, dialog, args);

			if (args.action === FULL_DAY_ACTION) {
				frappe.confirm(
					__(
						"This will replace the current attendance with a new Present attendance using the selected IN and OUT times. Continue?"
					),
					submit
				);
			} else if (args.action === ADD_PUNCHES_ACTION) {
				frappe.confirm(
					__(
						"A draft entry will be created with the existing punches. You can add the missing punches and create the attendance from there. Continue?"
					),
					() => submit_manual_punch_resolution(frm, dialog, args)
				);
			} else {
				submit();
			}
		},
	});

	dialog.show();
}

// Validates the form and returns only the args the chosen action needs.
// Returns null (after showing a message) when the request must not be sent.
function build_resolve_args(values, options) {
	const action = values.action;
	const args = { action, remarks: values.remarks };
	const stop = (message) => {
		frappe.msgprint({
			title: __("Cannot proceed"),
			message,
			indicator: "red",
		});
		return null;
	};

	if (action === "set_out") {
		if (!values.out_time) return stop(__("Check-out time is required."));
		args.out_time = values.out_time;
	}

	if (action === FULL_DAY_ACTION) {
		if (options.day_fix_blocker) return stop(options.day_fix_blocker);

		const manual = values.inout_mode === MODE_MANUAL;
		// auto-fill falls back to the shift window if set_value has not landed
		const in_time = manual ? values.in_time : values.in_time || options.shift_start;
		const out_time = manual ? values.out_time : values.out_time || options.shift_end;

		if (!in_time || !out_time) {
			return stop(__("IN and OUT times are required."));
		}
		if (!moment(out_time).isAfter(moment(in_time))) {
			return stop(__("OUT time must be after IN time."));
		}
		if (manual && options.shift_start && options.shift_end) {
			const start = moment(options.shift_start);
			const end = moment(options.shift_end);
			if (
				moment(in_time).isBefore(start) ||
				moment(in_time).isAfter(end) ||
				moment(out_time).isBefore(start) ||
				moment(out_time).isAfter(end)
			) {
				return stop(
					__("IN and OUT must be inside the shift window {0} to {1}.", [
						fmt_dt(options.shift_start),
						fmt_dt(options.shift_end),
					])
				);
			}
		}
		args.in_time = in_time;
		args.out_time = out_time;
	}

	if (action === ADD_PUNCHES_ACTION && options.day_fix_blocker) {
		return stop(options.day_fix_blocker);
	}

	return args;
}

function submit_resolution(frm, dialog, args) {
	frm.call({
		method: "resolve_error",
		doc: frm.doc,
		args,
		freeze: true,
	}).then((r) => {
		const new_attendance = r.message && r.message.new_attendance;
		frappe.show_alert({
			message: new_attendance
				? __("Punches excluded and Full Day granted. New attendance: {0}", [new_attendance])
				: __("Error punch resolved and attendance updated"),
			indicator: "green",
		});
		dialog.hide();
		frm.reload_doc();
	});
}

function submit_manual_punch_resolution(frm, dialog, args) {
	frappe
		.call({
			method: "gke_customization.gke_hrms.ot_resolver.create_manual_punch_entry_for_resolution",
			args: {
				employee: frm.doc.employee,
				attendance_date: frm.doc.attendance_date,
				remarks: args.remarks,
			},
			freeze: true,
		})
		.then((r) => {
			const result = r.message || {};
			dialog.hide();
			frappe.set_route("Form", "Manual Punch Entry", result.manual_punch_entry);
		});
}

// ---------------------------------------------------------------------------
// Field visibility / values (runs when Action or IN/OUT mode changes)
// ---------------------------------------------------------------------------

function sync_dialog(dialog, options) {
	const action = dialog.get_value("action") || "";
	const action_changed = dialog.last_action !== action;
	dialog.last_action = action;

	const is_set_out = action === "set_out";
	const is_full_day = action === FULL_DAY_ACTION;
	const f = dialog.fields_dict;

	// silent writes: set_input does not fire onchange, so no re-entry
	if (action_changed) {
		f.inout_mode.set_input(MODE_AUTO);
		f.in_time.set_input("");
		// smart prefill: approved OT when present, else the shift end; HR can
		// overwrite with the actual time before submitting
		f.out_time.set_input(
			is_set_out ? options.expected_out || options.shift_end || "" : ""
		);
	}

	const mode = is_full_day
		? action_changed
			? MODE_AUTO
			: dialog.get_value("inout_mode") || MODE_AUTO
		: "";
	const is_manual = mode === MODE_MANUAL;

	f.inout_mode.last_options = null;

	dialog.set_df_property("inout_mode", "hidden", is_full_day ? 0 : 1);
	dialog.set_df_property("in_time", "hidden", is_manual ? 0 : 1);
	dialog.set_df_property("in_time", "reqd", is_manual ? 1 : 0);
	dialog.set_df_property("out_time", "hidden", is_set_out || is_manual ? 0 : 1);
	dialog.set_df_property("out_time", "reqd", is_set_out || is_manual ? 1 : 0);

	// auto mode: fill the shift window silently
	if (is_full_day && !is_manual) {
		f.in_time.set_input(options.shift_start || "");
		f.out_time.set_input(options.shift_end || "");
	}

	["inout_mode", "in_time", "out_time"].forEach((name) => f[name].refresh());

	// the select input only exists after refresh; make sure a mode is selected
	if (is_full_day && !dialog.get_value("inout_mode")) {
		f.inout_mode.set_input(mode);
	}

	render_preview(dialog, options, mode);
}

function render_preview(dialog, options, mode) {
	const action = dialog.get_value("action") || "";
	const current_mode = mode !== undefined ? mode : dialog.get_value("inout_mode");

	dialog.fields_dict.ot_preview.$wrapper.html(
		ot_preview_html(options, action, {
			manual: current_mode === MODE_MANUAL,
			in_time: dialog.get_value("in_time"),
			out_time: dialog.get_value("out_time"),
		})
	);
}

// ---------------------------------------------------------------------------
// Preview
// ---------------------------------------------------------------------------

const b = (v) => `<b>${frappe.utils.escape_html(String(v ?? ""))}</b>`;
const fmt_dt = (v) => (v ? frappe.datetime.str_to_user(v) : "");
const alert_html = (cls, msg) => `<div class="alert ${cls}" style="margin-bottom:10px">${msg}</div>`;

// Same conditions the backend returns in day_fix_blocker
function ot_preview_html(options, action, ctx = {}) {
	if (action === "set_out") {
		const out_time = ctx.out_time;
		if (!out_time) {
			return alert_html("alert-info", __("Enter the check-out date & time below."));
		}
		let source;
		if (options.approved_ot && options.expected_out && out_time === options.expected_out) {
			source = __("shift end + approved overtime {0}", [b(options.approved_ot_hours)]);
		} else if (options.shift_end && out_time === options.shift_end) {
			source = __("shift end, no overtime");
		} else {
			source = __("your entered time");
		}
		return alert_html(
			"alert-success",
			__("Check-out will be set to {0} ({1}).", [b(fmt_dt(out_time)), source])
		);
	}

	if (action === FULL_DAY_ACTION) {
		const blocker = options.day_fix_blocker;
		if (blocker) return alert_html("alert-danger", blocker);

		const in_time = ctx.manual ? ctx.in_time : options.shift_start;
		const out_time = ctx.manual ? ctx.out_time : options.shift_end;

		if (!in_time || !out_time) {
			return alert_html("alert-info", __("Enter both the IN and OUT date & time."));
		}

		const hrs = moment(out_time).diff(moment(in_time), "hours", true);
		if (hrs <= 0) {
			return alert_html("alert-danger", __("OUT time must be after IN time."));
		}

		if (ctx.manual && options.shift_start && options.shift_end) {
			const start = moment(options.shift_start);
			const end = moment(options.shift_end);
			if (
				moment(in_time).isBefore(start) ||
				moment(in_time).isAfter(end) ||
				moment(out_time).isBefore(start) ||
				moment(out_time).isAfter(end)
			) {
				return alert_html(
					"alert-danger",
					__("IN and OUT must be inside the shift window {0} to {1}.", [
						b(fmt_dt(options.shift_start)),
						b(fmt_dt(options.shift_end)),
					])
				);
			}
		}

		return alert_html(
			"alert-warning",
			__(
				"Attendance will be marked Present from {0} to {1} ({2} hrs). Existing punches in this time range will be excluded and recorded in the audit trail.",
				[b(fmt_dt(in_time)), b(fmt_dt(out_time)), hrs.toFixed(2)]
			)
		);
	}

	if (action === ADD_PUNCHES_ACTION) {
		if (options.day_fix_blocker) return alert_html("alert-danger", options.day_fix_blocker);
		return alert_html(
			"alert-info",
			__(
				"A draft entry will be created with the existing punches. Add the missing punches and click 'Create Attendance' to rebuild attendance."
			)
		);
	}

	if (action === "reject") {
		return alert_html(
			"alert-danger",
			__("No changes will be made to attendance. The punch error will be marked as resolved.")
		);
	}

	// no action chosen yet: neutral summary of what is available
	const lines = [];

	if (options.missing_out) {
		if (options.approved_ot) {
			lines.push(
				__("Approved overtime of {0} is available. 'Set Check-out' will use {1} by default.", [
					b(options.approved_ot_hours),
					b(fmt_dt(options.expected_out)),
				])
			);
		} else if (options.shift_end) {
			lines.push(
				__("No approved overtime was found. 'Set Check-out' will use the shift end ({0}) by default.", [
					b(fmt_dt(options.shift_end)),
				])
			);
		}
	} else {
		lines.push(__("The recorded punches need to be corrected. Use 'Add Missing Punches' to update them."));
	}

	lines.push(__("Select an action below to see exactly what will change."));

	return alert_html("alert-info", lines.join("<br>"));
}
