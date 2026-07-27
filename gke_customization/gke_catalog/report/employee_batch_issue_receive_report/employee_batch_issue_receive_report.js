// Employee Batch Issue Receive Report - JavaScript File
// File: employee_batch_issue_receive_report.js

frappe.query_reports["Employee Batch Issue Receive Report"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1
        },
        {
            "fieldname": "branch",
            "label": __("Branch"),
            "fieldtype": "Link",
            "options": "Branch",
            "get_query": function() {
                return {
                    "filters": {
                        "company": frappe.query_report.get_filter_value("company")
                    }
                }
            }
        },
        {
            "fieldname": "manufacturer",
            "label": __("Manufacturer"),
            "fieldtype": "Link",
            "options": "Manufacturer"
        },
        {
            "fieldname": "department",
            "label": __("Department"),
            "fieldtype": "Link",
            "options": "Department",
            "get_query": function() {
                return {
                    "filters": {
                        "company": frappe.query_report.get_filter_value("company")
                    }
                }
            },
            "on_change": function() {
                // Clear operation and employee when department changes
                frappe.query_report.set_filter_value("operation", "");
                frappe.query_report.set_filter_value("employee_id", "");
            }
        },
        {
            "fieldname": "operation",
            "label": __("Operation"),
            "fieldtype": "Link",
            "options": "Department Operation",
            "get_query": function() {
                var department = frappe.query_report.get_filter_value("department");
                var company = frappe.query_report.get_filter_value("company");
                
                var filters = {
                    "docstatus": ["!=", 2]
                };
                
                if (department) {
                    filters["department"] = department;
                }
                if (company) {
                    filters["company"] = company;
                }
                
                return {
                    "filters": filters
                }
            },
            "on_change": function() {
                // Clear employee when operation changes
                frappe.query_report.set_filter_value("employee_id", "");
            }
        },
        {
            "fieldname": "employee_id",
            "label": __("Employee"),
            "fieldtype": "Link",
            "options": "Employee",
            "get_query": function() {
                var company = frappe.query_report.get_filter_value("company");
                var department = frappe.query_report.get_filter_value("department");
                var operation = frappe.query_report.get_filter_value("operation");
                
                // If operation is selected, use custom query
                if (operation && operation !== "") {
                    return {
                        "query": "gke_customization.gke_catalog.report.employee_batch_issue_receive_report.employee_batch_issue_receive_report.get_employees_by_operation",
                        "filters": {
                            "department": department,
                            "operation": operation,
                            "company": company
                        }
                    }
                }
                
                // Otherwise, use standard filters
                var filters = {
                    "status": "Active"
                };
                
                if (company) {
                    filters["company"] = company;
                }
                if (department) {
                    filters["department"] = department;
                }
                
                return {
                    "filters": filters
                }
            }
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        }
    ]
};
