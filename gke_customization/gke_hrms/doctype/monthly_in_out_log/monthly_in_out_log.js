// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

const MIL_RESOLVED_STATUSES = [
	"Auto-Resolved (Approved OT)",
	"Auto-Closed (Shift End)",
	"HR-Approved",
	"Rejected",
];

const FULL_DAY_ACTION = "delete_punch_full_day";
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

		if (
			frm.doc.punch_error &&
			!MIL_RESOLVED_STATUSES.includes(frm.doc.resolution_status)
		) {
			frm.add_custom_button(__("Resolve Error Punch"), () =>
				open_resolve_dialog(frm)
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
			freeze: true,
		})
		.then((r) => show_resolve_dialog(frm, r.message || {}));
}

// ---------------------------------------------------------------------------
// Dialog
// ---------------------------------------------------------------------------

function get_action_options(options) {
	const list = [{ label: "", value: "" }];

	if (options.approved_ot) {
		list.push({ label: __("Use approved OT"), value: "approve_ot" });
	}

	// backend: both actions only work for a "Missing OUT" error
	if (options.missing_out) {
		list.push(
			{ label: __("Close at shift end (no OT)"), value: "auto_close" },
			{ label: __("Enter actual check-out time"), value: "set_out" }
		);
	}

	list.push(
		{ label: __("Delete punch & grant Full Day"), value: FULL_DAY_ACTION },
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
			},			{
				fieldname: "in_time",
				label: __("IN Time (date & time)"),
				fieldtype: "Datetime",
				hidden: 1,
				onchange: () => render_preview(dialog, options),
			},
			{
				fieldname: "out_time",
				label: __("Actual Check-out (date & time)"),
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
		primary_action_label: __("Resolve"),
		primary_action(values) {
			const args = build_resolve_args(values, options);
			if (!args) return;

			const submit = () => submit_resolution(frm, dialog, args);

			if (args.action === FULL_DAY_ACTION) {
				frappe.confirm(
					__(
						"This cancels attendance {0} and creates a new Present attendance. Continue?",
						[frm.doc.attendance || ""]
					),
					submit
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
		if (!values.out_time) return stop(__("Actual check-out time is required."));
		args.out_time = values.out_time;
	}

	if (action === FULL_DAY_ACTION) {
		const blocker = get_full_day_blocker(options);
		if (blocker) return stop(blocker);

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
		args.in_time = in_time;
		args.out_time = out_time;
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
				? __(
					"Punches excluded and Full Day granted. New attendance: {0}",
					[new_attendance]
				)
				: __("Error punch resolved and attendance updated"),
			indicator: "green",
		});
		dialog.hide();
		frm.reload_doc();
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
		f.out_time.set_input("");
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
const alert_html = (cls, msg) =>
	`<div class="alert ${cls}" style="margin-bottom:10px">${msg}</div>`;

// Same conditions the backend enforces in delete_punch_grant_full_day
function get_full_day_blocker(options) {
	if (options.active_ot) {
		return __(
			"An active OT Log exists for this day. Settle the OT Log first; this action cannot proceed."
		);
	}
	if (!options.shift_start || !options.shift_end) {
		return __("This attendance has no shift; Full Day cannot be granted.");
	}
	return "";
}

function ot_preview_html(options, action, ctx = {}) {
	if (action === "approve_ot" && options.expected_out) {
		return alert_html(
			"alert-success",
			__("Check-out will be set to {0} (shift end + approved OT {1}).", [
				b(fmt_dt(options.expected_out)),
				b(options.approved_ot_hours),
			])
		);
	}

	if (action === "auto_close" && options.shift_end) {
		return alert_html(
			"alert-warning",
			__("Check-out will be set to {0} (shift end, no OT).", [
				b(fmt_dt(options.shift_end)),
			])
		);
	}

	if (action === "set_out") {
		return alert_html(
			"alert-info",
			__("Check-out will be the time you enter below.")
		);
	}

	if (action === FULL_DAY_ACTION) {
		const blocker = get_full_day_blocker(options);
		if (blocker) return alert_html("alert-danger", blocker);

		const in_time = ctx.manual ? ctx.in_time : options.shift_start;
		const out_time = ctx.manual ? ctx.out_time : options.shift_end;

		if (!in_time || !out_time) {
			return alert_html(
				"alert-info",
				__("Enter both the IN and OUT date & time.")
			);
		}

		const hrs = moment(out_time).diff(moment(in_time), "hours", true);
		if (hrs <= 0) {
			return alert_html(
				"alert-danger",
				__("OUT time must be after IN time.")
			);
		}

		return alert_html(
			"alert-warning",
			__(
				"Day will be re-marked Present {0} to {1} ({2} hrs). The {3} linked punch(es) and any stray punches inside the window will be excluded with audit comments; a new attendance will be created.",
				[
					b(fmt_dt(in_time)),
					b(fmt_dt(out_time)),
					hrs.toFixed(2),
					options.punch_count || 0,
				]
			)
		);
	}

	if (action === "reject") {
		return alert_html(
			"alert-danger",
			__("Attendance will be left as-is and the error stays closed.")
		);
	}

	// no action chosen yet: neutral summary of what is available
	const lines = [];

	lines.push(
		options.approved_ot
			? __(
				"Approved OT Log found ({0}): available as “Use approved OT”, check-out would be {1}.",
				[b(options.approved_ot_hours), b(fmt_dt(options.expected_out))]
			)
			: __("No approved OT Log for this day.")
	);

	if (options.missing_out && options.shift_end) {
		lines.push(
			__("“Close at shift end” would set check-out to {0}.", [
				b(fmt_dt(options.shift_end)),
			])
		);
	}

	lines.push(__("Select an action below to see exactly what will change."));

	return alert_html("alert-info", lines.join("<br>"));
}