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
      "depends_on": "eval:doc.company"
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
      "fieldname": "work_order_status",
      "label": __("Work Order Status"),
      "fieldtype": "Select",
      "options": "\nDraft\nSubmitted\nCancelled",
      "reqd": 0
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
    report.page.add_inner_button(__("Clear Filters"), function () {
      // Reset all filters to their default values or empty
      report.get_filter("company").set_value("");
      report.get_filter("branch").set_value("");
      report.get_filter("from_date").set_value(frappe.datetime.add_months(frappe.datetime.get_today(), -1));
      report.get_filter("to_date").set_value(frappe.datetime.get_today());
      report.get_filter("work_order_status").set_value("");
      report.get_filter("goods_type").set_value("");
      report.get_filter("department").set_value("");
      
      // Refresh the report
      report.refresh();
    });
  }
};
