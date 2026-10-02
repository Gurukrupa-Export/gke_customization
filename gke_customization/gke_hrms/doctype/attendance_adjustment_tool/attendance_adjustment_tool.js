// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Attendance Adjustment Tool", {
// 	refresh(frm) {

// 	},
// });
// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("Attendance Adjustment Tool", {
    from_date(frm) {
      set_shift_details(frm);
    },
  
    to_date(frm) {
      set_shift_details(frm);
    },
  
    // onload: function (frm) {
    //   if (frm.is_new()) return;
    //   frappe.call({
    //     method:
    //       "gke_customization.gke_hrms.api.generate_attendence_adjusment.process_salary_adjustment",
    //     args: {
    //       docname: frm.doc.name,
    //     },
    //     callback: function (r) {
    //       if (r.message) {
    //         //  yaha data pass kar diya
    //         render_preview(frm, r.message);
    //       }
    //     },
    //   });
    //   // frm.set_df_property("adjustment_details", "hidden", 1);
    // },
  
    onload: function (frm) {
      if (frm.is_new()) return;
  
      frappe.call({
        method:
          "gke_customization.gke_hrms.api.generate_attendence_adjusment.process_salary_adjustment",
        args: {
          docname: frm.doc.name,
        },
        callback: function (r) {
          if (!r.message) return;
  
          // employees collect karo
          let employees = [];
  
          (r.message || []).forEach((row) => {
            if (row.employee) {
              employees.push(row.employee);
            }
          });
  
          // duplicate remove
          employees = [...new Set(employees)];
          console.log(employees)
  
          frappe.call({
            method:
              "gke_customization.gke_hrms.api.generate_attendence_adjusment.check_employee_active_validation_based_on_doj",
            args: {
              employees: employees,
            },
            callback: function () {
              // validation pass hui to preview render karo
              render_preview(frm, r.message);
            },
          });
        },
      });
    },
  
    generate_btn: function (frm) {
      frappe.call({
        method:
          "gke_customization.gke_hrms.api.generate_attendence_adjusment.process_salary_adjustment",
        args: {
          docname: frm.doc.name,
        },
        callback: function (r) {
          if (r.message) {
            console.log("child", r.message);
  
            frm.clear_table("adjustment_details");
  
            r.message.forEach(function (row) {
              let child = frm.add_child("adjustment_details");
              child.employee = row.employee;
              child.employee_name = row.employee_name;
              child.full_days = row.full_days;
              child.calendar_days = row.calendar_days;
              child.difference_days = row.remove_days;
              child.shift_hours = row.shift_hours;
              child.payable_days = row.full_days;
              child.monthly_salary = row.monthly_salary;
              child.actual_salary = row.actual_salary;
              child.fractional_hours = row.fractional_hours;
              child.action = row.action;
            });
            // frm.set_df_property("adjustment_details", "hidden", 0);
            frm.refresh_field("adjustment_details");
            // frm.fields_dict.adjustment_details.grid.refresh();
          }
        },
      });
    },
  
    refresh: function (frm) {
      if (
        frm.doc.workflow_state === "Modify CheckIn In Queue" ||
        frm.doc.workflow_state === "Update Attendance In Queue"
      ) {
        setTimeout(() => {
          frm.reload_doc();
        }, 1000); // 3 sec baad reload
      }
    },
  
    refresh(frm) {
      // child table name change kar lena agar alag hai
      let has_error = frm.doc.error_details && frm.doc.error_details.length > 0;
  
      // Error Details tab show/hide
      frm.toggle_display("error_details", has_error);
  
      // ya agar tab break field hai to uska fieldname use karo
      frm.set_df_property("error_details", "hidden", has_error ? 0 : 1);
    },
  
    preview_btn: function (frm) {
      frappe.call({
        method:
          "gke_customization.gke_hrms.api.generate_attendence_adjusment.process_salary_adjustment",
        args: {
          docname: frm.doc.name,
        },
        callback: function (r) {
          if (r.message) {
            // 🔥 yaha data pass kar diya
            render_preview(frm, r.message);
          }
        },
      });
    },
  
    processed: function (frm) {
      let value = frm.doc.processed ? 1 : 0;
  
      (frm.doc.adjustment_details || []).forEach((row) => {
        row.processed = value;
      });
  
      frm.refresh_field("adjustment_details");
    },
  
    after_workflow_action: function (frm) {
      if (frm.doc.workflow_state === "Modify CheckIn In Queue") {
        frappe.call({
          method:
            "gke_customization.gke_hrms.api.generate_attendence_adjusment.enqueue_modify_checkin",
          args: {
            docname: frm.doc.name,
          },
          callback: function () {
            frappe.msgprint("Modify CheckIn Process In Working");
          },
        });
      }
  
      if (frm.doc.workflow_state === "Update Attendance In Queue") {
        frappe.call({
          method:
            "gke_customization.gke_hrms.api.generate_attendence_adjusment.enqueue_modify_attendance",
          args: {
            docname: frm.doc.name,
          },
          callback: function () {
            frappe.msgprint("Modify Attendance Process In Working");
          },
        });
      }
    },
  });
  
  // function render_preview(frm) {
  //   let data = frm.doc.adjustment_details || [];
  
  //   let html = `
  //         <h4>Adjustment Preview</h4>
  //         <table class="table table-bordered table-striped">
  //             <thead>
  //                 <tr>
  //                     <th>No</th>
  //                     <th>Employee</th>
  //                     <th>Name</th>
  //                     <th>Calendar Days</th>
  //                     <th>Difference Days</th>
  //                     <th>Shift Hours</th>
  //                     <th>Full Days</th>
  //                     <th>Remove Days</th>
  //                     <th>Monthly Salary</th>
  //                     <th>Actual Salary</th>
  //                     <th>Fractional Hours</th>
  //                     <th>Action</th>
  //                 </tr>
  //             </thead>
  //             <tbody>
  //     `;
  
  //   data.forEach((row, i) => {
  //     html += `
  //             <tr>
  //                 <td>${i + 1}</td>
  //                 <td>${row.employee || ""}</td>
  //                 <td>${row.employee_name || ""}</td>
  //                 <td>${row.calendar_days || 0}</td>
  //                 <td>${row.difference_days || 0}</td>
  //                 <td>${row.shift_hours || 0}</td>
  //                 <td>${row.payable_days || 0}</td>
  //                 <td>${row.difference_days || 0}</td>
  //                 <td>${row.monthly_salary || 0}</td>
  //                 <td>${row.actual_salary || 0}</td>
  //                 <td>${row.fractional_hours || 0}</td>
  //                 <td>${row.action || 0}</td>
  //             </tr>
  //         `;
  //   });
  
  //   html += `</tbody></table>`;
  
  //   frm.fields_dict.preview_html.$wrapper.html(html);
  // }
  
  function render_preview(frm, data) {
    let rows = data || frm.doc.adjustment_details || [];
  
    let html = `
      <details class="adjustment-preview-box" open>
  
        <summary
          style="
            cursor:pointer;
            font-size:16px;
            font-weight:600;
            margin-bottom:15px;
          "
        >
          Adjustment Preview
        </summary>
  
        <div class="table-responsive">
          <table class="table table-bordered table-striped">
  
            <thead>
              <tr>
                <th>No</th>
                <th>Employee</th>
                <th>Name</th>
                <th>Actual Salary</th>
                <th>Monthly Salary</th>
                <th>Calendar Days</th>
                <th>Payable Days</th>
                <th>Difference Days</th>
                <th>Remove Days</th>
                <th>Fractional Hours</th>
                <th>Action</th>
              </tr>
            </thead>
  
            <tbody>
    `;
  
    rows.forEach((row, i) => {
      html += `
        <tr>
          <td>${i + 1}</td>
          <td>${row.employee || ""}</td>
          <td>${row.employee_name || ""}</td>
          <td>${row.actual_salary || 0}</td>
          <td>${row.monthly_salary || 0}</td>
          <td>${row.calendar_days || 0}</td>
          <td>${row.full_days || 0}</td>
          <td>${row.remove_days || row.difference_days || 0}</td>
          <td>${row.remove_days || 0}</td>
          <td>${row.fractional_hours || 0}</td>
          <td>${row.action || ""}</td>
        </tr>
      `;
    });
  
    html += `
            </tbody>
          </table>
        </div>
  
      </details>
    `;
  
    frm.fields_dict.preview_html.$wrapper.html(html);
  
    // optional styling
    // frm.fields_dict.preview_html.$wrapper.find(".adjustment-preview-box").css({
    //   border: "1px solid var(--border-color)",
    //   borderRadius: "10px",
    //   padding: "12px",
    //   marginTop: "10px"
    // });
  }
  
  function set_shift_details(frm) {
    if (!frm.doc.from_date) return;
  
    frappe.db
      .get_list("Shift Assignment", {
        filters: {
          employee: frm.doc.employee,
          docstatus: 1,
          status: "Active",
        },
        fields: ["shift_type", "start_date", "end_date"],
        order_by: "start_date desc",
      })
      .then((res) => {
        let from_date = frm.doc.from_date;
        let matched_shift = null;
  
        //  Case 1: Shift Assignment available
        if (res.length) {
          for (let i = 0; i < res.length; i++) {
            let shift = res[i];
  
            if (shift.end_date) {
              if (from_date >= shift.start_date && from_date <= shift.end_date) {
                matched_shift = shift;
                break;
              }
            } else {
              if (from_date >= shift.start_date) {
                matched_shift = shift;
                break;
              }
            }
          }
  
          if (matched_shift) {
            return apply_shift_time(frm, matched_shift.shift_type);
          }
        }
  
        //  Case 2: No Shift Assignment → fallback to Employee default_shift
        frappe.db
          .get_value("Employee", frm.doc.employee, "default_shift")
          .then((emp) => {
            if (emp.message && emp.message.default_shift) {
              return apply_shift_time(frm, emp.message.default_shift);
            } else {
              frappe.throw("No Shift Assignment or Default Shift found");
            }
          });
      });
  }
  
  function apply_shift_time(frm, shift_type) {
    frappe.db
      .get_value("Shift Type", shift_type, ["start_time", "end_time"])
      .then((r) => {
        if (r.message) {
          let in_time = r.message.start_time;
          let out_time = r.message.end_time;
  
          frm.set_value("shift", shift_type);
          frm.set_value("custom_in_time", in_time);
          frm.set_value("custom_out_time", out_time);
        }
      });
}
  