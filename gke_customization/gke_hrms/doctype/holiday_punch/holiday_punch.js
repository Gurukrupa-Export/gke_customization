frappe.ui.form.on("Holiday Punch", {
  shift_name(frm) {
    frappe.db.get_value(
      "Shift Type",
      frm.doc.shift_name,
      ["start_time", "end_time"],
      (r) => {
        frm.set_value("start_time", r.start_time);
        frm.set_value("end_time", r.end_time);
      },
    );
  },
  search: function (frm) {
    frm.call({
      method: "search_checkin",
      doc: frm.doc,
      callback: function (r) {
        for (let i = 0; i < r.message.length; i++) {
          var checkins = r.message[i];
          $.each(checkins || [], function (i, d) {
            if (!d.source) {
              d.source = "Employee Checkin";
            }
            d.type = i % 2 == 0 ? "IN" : "OUT";
            frm.add_child("details", d);
          });
        }
        frm.refresh_field("details");
      },
    });
  },
  add_new_punch(frm) {
    frappe.call({
      method: "gke_customization.gke_hrms.doctype.holiday_punch.holiday_punch.add_checkins",
      args: {
        details: frm.doc.details,
        date: frm.doc.date,
        shift_name: frm.doc.shift_name,
      },
      callback: function (r) {
        if (!r.exc) {
          frm.clear_table("details");
          var arrayLength = r.message.length;
          for (var i = 0; i < arrayLength; i++) {
            frm.add_child("details", {
              date: r.message[i].date,
              type: r.message[i].type,
              employee: r.message[i].employee,
              custom_employee_name: r.message[i]?.custom_employee_name || "",
              time: r.message[i].time,
              employee_checkin: r.message[i].employee_checkin,
              source: r.message[i].source,
            });
          }
          frm.refresh_field("details");
        }
      },
    });
  },
});
