frappe.ui.form.on("Holiday Punch", {
	shift_name(frm){
		frappe.db.get_value("Shift Type",frm.doc.shift_name, ["start_time","end_time"], (r) => {
            frm.set_value({"start_time":r.start_time, "end_time":r.end_times})
        })
	},
    // search: function(frm) {
	// 	frm.call({
	// 		method: "search_checkin",
	// 		doc: frm.doc,
	// 		callback: function(r) {
	// 			var checkins = r.message
	// 			$.each(checkins || [], function(i,d) {
	// 				if (!d.source) {
	// 					d.source = "Employee Checkin"
	// 				}
	// 				d.type = i%2==0 ? "IN":"OUT"
	// 				frm.add_child("details", d)
	// 			})
	// 			frm.refresh_field("details")
	// 		}
	// 	})
	// },
});
