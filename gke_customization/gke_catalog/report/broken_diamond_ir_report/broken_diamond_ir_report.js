frappe.query_reports["Broken Diamond IR Report"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_start()
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_end()
        },
        {
            fieldname: "jangad_no",
            label: __("Jangad No"),
            fieldtype: "Link",
            options: "Employee IR"
        },
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 1
        },
        {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "Link",
            options: "Branch"
        },
        {
            fieldname: "from_manager",
            label: __("From Manager"),
            fieldtype: "Link",
            options: "Employee"
        },
        {
            fieldname: "to_manager",
            label: __("To Manager"),
            fieldtype: "Link",
            options: "Employee"
        },
        {
            fieldname: "from_department",
            label: __("From Department"),
            fieldtype: "Link",
            options: "Department"
        },
        {
            fieldname: "to_department",
            label: __("To Department"),
            fieldtype: "Link",
            options: "Department"
        },
        {
            fieldname: "manufacturer",
            label: __("Manufacturer"),
            fieldtype: "Link",
            options: "Manufacturer"
        }
    ]
};