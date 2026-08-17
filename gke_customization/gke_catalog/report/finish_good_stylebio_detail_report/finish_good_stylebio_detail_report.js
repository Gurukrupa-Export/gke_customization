frappe.query_reports["Finish Good Stylebio Detail Report"] = {
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
            options: "Department"
        },
        {
            fieldname: "serial_no",
            label: __("Serial No"),
            fieldtype: "Link",
            options: "Serial No"
        },
        {
            fieldname: "stylebio",
            label: __("Item Code"),
            fieldtype: "Link",
            options: "Item"
        }
    ]
};
function init_user_dept_permissions(report) {
    frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: "User",
            name: frappe.session.user
        },
        callback(user_res) {
            const roles = ((user_res.message && user_res.message.roles) || []).map(r => r.role);
            const management_roles = ["Director", "CEO", "System Manager", "Branch Manager", "Department Manager"];
            const is_management = roles.some(r => management_roles.includes(r));

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
                        if (!is_management) {
                            report.get_filter("department").df.read_only = 1;
                            report.get_filter("department").refresh();
                        }
                    }

                    setTimeout(() => report.refresh(), 500);
                }
            });
        }
    });
}