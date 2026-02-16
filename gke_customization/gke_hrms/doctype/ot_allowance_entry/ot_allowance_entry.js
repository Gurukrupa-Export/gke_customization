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