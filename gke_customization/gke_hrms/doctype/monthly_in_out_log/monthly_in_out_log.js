// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("Monthly In-Out Log", {
	refresh(frm) {
		if (frm.doc.docstatus == 1) {
			frm.add_custom_button(__("Fetch Latest Data"), function () {
				frm.call({
					method: "populate_from_attendance",
					doc: frm.doc,
					callback: function (r) {
						// TODO: Handle the response
						const response = r.message || r.docs || [];
						console.log(response);
						if (response.length > 0) {
							doc_data = response[0];
							// TODO: Update the form with the response
							let filed_name = [
								"net_wrk_hrs",
								"spent_hrs",
								"p_out_hrs",
								"ot_hrs",
								"in_time",
								"out_time",
								"early_hrs",
								"late_hrs",
								"late",
							];
							filed_name.forEach((field) => {
								frm.set_value(field, doc_data?.[field] || null);
							});
						}
					},
				});
			});
		}

		// ---- Error-punch resolution (ledger flow) ----
		// Error Punch -> Monthly In-Out Log -> check Approved OT:
		//   approved OT exists & matches -> already auto-resolved (status shown)
		//   no approved OT -> HR verifies & resolves here
		if (
			frm.doc.punch_error &&
			!["Auto-Resolved (Approved OT)", "Auto-Closed (Shift End)", "HR-Approved", "Rejected"].includes(
				frm.doc.resolution_status
			)
		) {
			frm.add_custom_button(__("Resolve Error Punch"), function () {
				const dialog = new frappe.ui.Dialog({
					title: __("Resolve Error Punch — {0}", [frm.doc.error_case || frm.doc.punch_error]),
					fields: [
						{
							fieldtype: "HTML",
							options: `<div style="margin-bottom:10px">
                                <b>Punch ledger:</b> ${frappe.utils.escape_html(
									frm.doc.punch_ledger || "-"
								)}<br>
                                <b>Approved OT check:</b> ${frappe.utils.escape_html(
									frm.doc.ot_check_status || "-"
								)}
                            </div>`,
						},
						{
							fieldname: "action",
							label: __("Action"),
							fieldtype: "Select",
							options: [
								{
									label: __("Approve using Approved OT (OUT = shift end + approved OT)"),
									value: "approve_ot",
								},
								{ label: __("Set actual OUT time"), value: "set_out" },
								{ label: __("Auto close at shift end (no OT)"), value: "auto_close" },
								{ label: __("Reject"), value: "reject" },
							],
							default:
								frm.doc.ot_check_status === "Approved OT Matched" ? "approve_ot" : "set_out",
							onchange() {
								const show = dialog.get_value("action") === "set_out";
								dialog.toggle_display("out_time", show);
							},
						},
						{
							fieldname: "out_time",
							label: __("Actual Check-out (date & time)"),
							fieldtype: "Datetime",
							depends_on: 'eval:doc.action=="set_out"',
						},
						{ fieldname: "remarks", label: __("Remarks"), fieldtype: "Small Text" },
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
						}).then(() => {
							frappe.show_alert({
								message: __("Error punch resolved — attendance updated"),
								indicator: "green",
							});
							dialog.hide();
							frm.reload_doc();
						});
					},
				});
				dialog.show();
			}).addClass("btn-primary");
		}
	},
});
