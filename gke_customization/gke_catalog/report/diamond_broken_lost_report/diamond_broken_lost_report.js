frappe.query_reports["Diamond Broken-Lost Report"] = {
    onload(report) {
        init_user_dept_permissions(report);
    },

    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.add_months(
                frappe.datetime.get_today(),
                -6
            )
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.get_today()
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department",
            on_change: function(report) {
                report.set_filter_value("employee", "");
                report.refresh();
            }
        },
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee",
            get_query: function() {
                let department = frappe.query_report.get_filter_value("department");

                let filters = {};
                if (department) {
                    filters.department = department;
                }

                return {
                    filters: filters
                };
            }
        },
        {
            fieldname: "manufacturer",
            label: __("Manufacturer"),
            fieldtype: "Link",
            options: "Manufacturer"
        }
    ]
};
function init_user_dept_permissions(report) {
    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: "Employee",
            filters: { user_id: frappe.session.user },
            fieldname: ["department"]
        },
        callback(r) {
            if (!r.message) return;

            if (r.message.department && report.get_filter("department")) {
                report.get_filter("department").set_value(r.message.department);
            }

            setTimeout(() => report.refresh(), 500);
        }
    });
}