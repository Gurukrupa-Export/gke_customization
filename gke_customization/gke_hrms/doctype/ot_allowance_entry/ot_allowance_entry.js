// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("OT Allowance Entry", {
	setup(frm) {
		frm.set_query("department", function() {
			return {
				filters: {
					company: frm.doc.company
				}
			}
		})
	},
	// onload(frm) {
	// 	let start = frappe.datetime.month_start(frappe.datetime.get_today())
	// 	let end = frappe.datetime.month_end(frappe.datetime.get_today())
	// 	frm.set_value({
	// 		from_date: start,
	// 		to_date: end,
	// 		// employee: null
	// 	});
	// },
    // from_date(frm) {
	// 	if (frm.doc.from_date) {
	// 		let end_of_month = frappe.datetime.month_end(frm.doc.from_date);
	// 		frm.set_value("to_date", end_of_month);
	// 	}
	// },
	// after_save: function(frm) {
	// 	frm.call("get_ot_details",{"from_log":true})
	// },
	search(frm) {
		const method = "gke_customization.gke_hrms.doctype.ot_allowance_entry.ot_allowance_entry";
		const search_button = frm.fields_dict.search.$input;
		const skip_fields = ["name", "owner", "creation", "modified", "modified_by", "docstatus", "idx", "parent", "parentfield", "parenttype", "doctype"];

		const fill_ot_details = (ot_details) => {
			frm.clear_table("ot_details");
			(ot_details || []).forEach((row) => {
				skip_fields.forEach((fieldname) => delete row[fieldname]);
				frm.add_child("ot_details", row);
			});
			frm.refresh_field("ot_details");
			frm.dirty();
		};

		const show_messages = (messages) => {
			(messages || []).forEach((m) => {
				const message = typeof m === "string" ? JSON.parse(m) : m;
				frappe.msgprint(message.message || message);
			});
		};

		const stop_waiting = () => {
			clearTimeout(frm.search_wait_timer);
			frappe.realtime.off("ot_allowance_entry_search_done");
			search_button.prop("disabled", false);
		};

		// Registered before the server call so that a job which fails fast is not missed
		const listen_for_background_search = () => {
			const docname = frm.docname;
			frappe.realtime.off("ot_allowance_entry_search_done");
			frappe.realtime.on("ot_allowance_entry_search_done", (data) => {
				if (data.docname !== docname) return;
				stop_waiting();
				if (!data.success) {
					frappe.msgprint({ title: __("Search Failed"), message: data.error, indicator: "red" });
					return;
				}
				if (data.saved) {
					if (cur_frm && cur_frm.doctype === frm.doctype && cur_frm.docname === data.docname) {
						cur_frm.reload_doc().then(() => show_messages(data.messages));
					}
					return;
				}
				if (cur_frm !== frm || frm.docname !== docname) return;
				frappe.call({
					method: `${method}.get_ot_details_result`,
					args: { docname: docname },
					callback: (r) => {
						if (!r.message) return;
						const result = JSON.parse(r.message);
						fill_ot_details(result.ot_details);
						show_messages(result.messages);
					},
				});
			});
			frappe.show_alert({ message: __("Fetching OT details..."), indicator: "blue" });
			// Fallback so the button cannot stay disabled if the realtime event is lost
			frm.search_wait_timer = setTimeout(stop_waiting, 20 * 60 * 1000);
		};

		search_button.prop("disabled", true);
		listen_for_background_search();
		frappe.call({
			method: `${method}.start_get_ot_details`,
			args: { doc: frm.doc },
			callback: (r) => {
				if (r.message && r.message.background) return;
				stop_waiting();
				if (r.message) fill_ot_details(r.message.ot_details);
			},
			error: () => stop_waiting(),
		});
	},
	employee(frm) {
		if (frm.doc.employee) {
			frappe.db.get_value("Employee", frm.doc.employee, 
                ["company", "designation", "department", "attendance_device_id as punch_id"], 
                (r)=>{
				frm.set_value(r)
			})
		}
		else {
			frm.set_value({
				"company": null,
				"designation": null,
				"department": null,
				"punch_id": null
			})
		}
	},
    allow: function(frm){
		update_fields_in_child_table(frm, "allow");
	}
});

frappe.ui.form.on("OT Details", {
	employee(frm, cdt, cdn) {
		let d = locals[cdt][cdn]
		frappe.call({
			method: "gke_customization.gke_hrms.doctype.ot_allowance_entry.ot_allowance_entry.get_ot_details",
			args: {
				employee: frm.doc.employee,
				for_date: d.attendance_date
			},
			callback: function(r) {
				if (r.message) {
					frappe.model.set_value(cdt,cdn,"shift", r.message)
				}
			}
		})	
	},
	allow(frm, cdt, cdn) {
		let d = locals[cdt][cdn]
		if (!d.allow) {
			frappe.model.set_value(cdt,cdn,"allowed_ot", d.attn_ot_hrs)
		}
	},
	allowed_ot(frm, cdt, cdn) {
		let d = locals[cdt][cdn]
		if (d.allowed_ot > d.attn_ot_hrs || !d.allow || !d.allowed_ot) {
			frappe.model.set_value(cdt,cdn,"allowed_ot", d.attn_ot_hrs)
		}
		frm.refresh_field('ot_details')
	}
})

function update_fields_in_child_table(frm, fieldname) {
	$.each(frm.doc.ot_details || [], function (i, d) {
		d[fieldname] = frm.doc[fieldname];
	});
	refresh_field("ot_details");
}