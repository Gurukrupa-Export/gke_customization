// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Finding Manufacturing Work Order Report"] = {
  "filters": [
    {
      "fieldname": "company",
      "label": __("Company"),
      "fieldtype": "Link",
      "options": "Company",
      "reqd": 0,
    },
    {
      "fieldname": "branch",
      "label": __("Branch"),
      "fieldtype": "Link",
      "options": "Branch",
      "reqd": 0,
    },
    {
      "fieldname": "from_date",
      "label": __("From Posting Date"),
      "fieldtype": "Date",
      "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
      "reqd": 0
    },
    {
      "fieldname": "to_date",
      "label": __("To Posting Date"),
      "fieldtype": "Date",
      "default": frappe.datetime.get_today(),
      "reqd": 0
    },
    {
      "fieldname": "department_status",
      "label": __("Department Status"),
      "fieldtype": "Select",
      "options": "\nCancelled\nFinished\nNot Started\nOn Hold\nWIP",
    },
    {
      "fieldname": "goods_type",
      "label": __("Customer Goods"),
      "fieldtype": "Select",
      "options": "\nYes\nNo",
      "reqd": 0
    },
    {
      "fieldname": "department",
      "label": __("Department"),
      "fieldtype": "Link",
      "options": "Department",
      "reqd": 0
    }
  ],

  onload: function(report) {
    // Add "Clear Filter" button
    report.page.add_inner_button(__("Clear Filter"), function () {
      report.filters.forEach(function (filter) {
        let field = report.get_filter(filter.fieldname);
        if (field.df.fieldtype === "MultiSelectList") {
          field.set_value([]);
        } else if (field.df.default) {
          field.set_value(field.df.default);
        } else {
          field.set_value("");
        }
      });
      report.refresh();
    });
  }
};
