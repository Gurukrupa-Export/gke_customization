// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt


frappe.query_reports["New Master Record Entries"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1
        },
		{
            fieldname: "selected_doctypes",
            label: __("Doctypes"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                const doctypes = [
                    "Item", "BOM", "Customer", "Supplier", "Warehouse", "Territory", "Company", "Supplier Group",
					"Contact", "Address", "Department", "Branch", "Designation", "Employee", "Employee Grade",
					"Employee Group", "Employee Onboarding Template", "Employee Skill", "Shift Type",
					"Interview Type", "Interview Round", "Holiday List", "Leave Type",
					"Leave Policy", "Item Group", "Asset", "Asset Category", "Loan Product", "Item Attribute",
					"Attribute Value", "UOM", "HD Ticket Type", "HD Agent", "HD Team", "Cost Center", "Bank Account",
					"Price List", "Item Price", "Grievance Type", "Leave Allocation", "Sales Person", "Sales Partner",
					"Location", "Salary Component", "Salary Structure", "Project","Issue Type"
                ];
                return doctypes
                    .filter(d => d.toLowerCase().includes(txt.toLowerCase()))
                    .map(d => ({ value: d, label: d, description: "" }));
            }
        }
    ]
};
