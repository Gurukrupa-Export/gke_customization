frappe.ui.form.on("Holiday Punch", {

  refresh(frm) {
    let has_error = frm.doc.error_details && frm.doc.error_details.length > 0;

    frm.set_df_property("error_details", "hidden", has_error ? 0 : 1);
  },

  company(frm) {
    // Department filter
    frm.set_query("department", function () {
      return {
        filters: {
          company: frm.doc.company,
        },
      };
    });

    // Shift filter
    frm.set_query("shift_name", function () {
      return {
        filters: {
          custom_company: frm.doc.company,
        },
      };
    });
  },    

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

  add_emp: function (frm, data) {
    $.each(data || [], function (i, d) {
      frm.add_child("employees", {
        employee: d.name,
        employee_name: d.employee_name,
      });
    });

    frm.refresh_field("employees");
  },

  get_employees: function (frm) {
    frappe.call({
      method:
        "gke_customization.gke_hrms.doctype.holiday_punch.holiday_punch.get_employees",
      args: {
        doc: frm.doc,
      },
      callback: function (r) {
        if (r.message) {
          frm.clear_table("employees");

          r.message.forEach(function (row) {
            let child = frm.add_child("employees");

            child.employee = row.name;
            // child.employee_name = row.employee_name;
          });

          frm.refresh_field("employees");

          frappe.msgprint("Employees Fetched Successfully");
        }
      },
    });
  },

  add_new_punch(frm) {
    frappe.call({
      method:
        "gke_customization.gke_hrms.doctype.holiday_punch.holiday_punch.add_checkins",
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

  refresh: function (frm) {
    if (
      frm.doc.workflow_state === "Checkin In Queue" ||
      frm.doc.workflow_state === "Attendance In Queue"
    ) {
      setTimeout(() => {
        frm.reload_doc();
      }, 1000); // 3 sec baad reload
    }
  },

  after_workflow_action: function (frm) {
    // Start Checkin Job
    if (frm.doc.workflow_state === "Checkin In Queue") {
      frappe.call({
        method:
          "gke_customization.gke_hrms.doctype.holiday_punch.holiday_punch.enqueue_modify_checkin",
        args: { docname: frm.doc.name },
        freeze: true,
        freeze_message: "Checkin job started...",
      });
    }

    // Start Attendance Job
    if (frm.doc.workflow_state === "Attendance In Queue") {
      frappe.call({
        method:
          "gke_customization.gke_hrms.doctype.holiday_punch.holiday_punch.enqueue_modify_attendance",
        args: { docname: frm.doc.name },
        freeze: true,
        freeze_message: "Attendance job started...",
      });
    }
  },
});
