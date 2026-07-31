// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("Payroll Email", {
  refresh(frm) {

    // Show button only in valid states
    if (!frm.is_new() && frm.doc.status == "Draft") {
      frm.add_custom_button(__("Fetch Employees"), () => {
        frm.trigger("fetch_employees");
      }, __("Actions"));
    }
    if (!frm.is_new() && ["Draft", "Partial Failed", "Failed"].includes(frm.doc.status)) {
      frm.add_custom_button(
        __("Send Email"),
        () => {
          frm.trigger("send_payroll_emails");
        },
        __("Actions"),
      );
    }
  },
  company(frm) {
    const company_filter = {
      filters: {
        company: frm.doc.company,
      },
    };

    frm.set_query("payroll_entry", function () {
      return company_filter;
    });

    frm.set_query("department", function () {
      return company_filter;
    });

    frm.set_query("branch", function () {
      return company_filter;
    });
  },
  from_date(frm) {
    if (frm.doc.from_date) {
      let from_date = frm.doc.from_date;
      console.log("From Date: ", from_date);

      // Step 1: get first day of current month
      let start_of_month = frappe.datetime.month_start(from_date);
      console.log("Start of Month: ", start_of_month);

      // Step 2: jump to first day of next month
      let start_of_next_month = frappe.datetime.add_months(start_of_month, 1);
      console.log("Start of Next Month: ", start_of_next_month);

      // Step 3: subtract 1 day
      let to_date = frappe.datetime.add_days(start_of_next_month, -1);
      console.log("To Date: ", to_date);

      frm.set_value("to_date", to_date);
    }
  },

  fetch_employees(frm) {
    // Basic validations
    if (!frm.doc.company) {
      frappe.msgprint(__("Please select Company"));
      return;
    }

    if (!frm.doc.from_date || !frm.doc.to_date) {
      frappe.msgprint(__("Please select From Date and To Date"));
      return;
    }

    if (frm.doc.from_date > frm.doc.to_date) {
      frappe.msgprint(__("From Date cannot be greater than To Date"));
      return;
    }

    if (frm.doc.status !== "Draft") {
      frappe.msgprint(__("Employees can be fetched only in Draft status"));
      return;
    }

    frappe.confirm(
      __(
        "This will fetch Salary Slips based on the selected filters. Continue?",
      ),
      () => {
        frappe.call({
          method:
            "gke_customization.gke_hrms.doctype.payroll_email.payroll_email.fetch_employees",
          args: {
            filters: {
              company: frm.doc.company,
              payroll_entry: frm.doc.payroll_entry,
              from_date: frm.doc.from_date,
              to_date: frm.doc.to_date,
              department: frm.doc.department,
              designation: frm.doc.designation,
              branch: frm.doc.branch,
            },
          },
          freeze: true,
          freeze_message: __("Fetching employees..."),
          callback: function (r) {
            if (r.message) {
              frm.set_value("payroll_email_details", []);
              if (r.message.length > 0) {
                //    set values in payroll_email_details tabel
                frm.set_value("payroll_email_details", r.message);
                frm.set_value("total_slips", r.message.length);
                frm.refresh_field("payroll_email_details");
                frm.save()
              }
            }
          },
        });
      },
    );
  },

  send_payroll_emails(frm) {
    // Final client-side guard
    if (
      !frm.doc.payroll_email_details ||
      frm.doc.payroll_email_details.length === 0
    ) {
      frappe.msgprint(__("No employees found to send emails"));
      return;
    }

    frappe.confirm(
      __(
        "Are you sure you want to send salary slip emails? This action cannot be undone.",
      ),
      () => {
        frappe
          .call({
            method:
              "gke_customization.gke_hrms.doctype.payroll_email.payroll_email.send_payroll_emails",
            args: {
              batch_name: frm.doc.name,
            },
            freeze: true,
            freeze_message: __("Sending salary slip emails..."),
          })
          .then(() => {
            frm.reload_doc();
          });
      },
    );
  },
});
