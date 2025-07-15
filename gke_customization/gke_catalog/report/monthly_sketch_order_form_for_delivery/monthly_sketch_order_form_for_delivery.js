frappe.query_reports["Monthly Sketch Order Form for Delivery"] = {

    filters: [
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            reqd: 1
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1
        },
        {
            fieldname: "branch",
            label: "Branch",
            fieldtype: "Link",
            options: "Branch",
            default: "GEPL-MU-0009"
        }
    ],

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        const clickable_states = ["submitted", "pending", "cancelled"];

        if (clickable_states.includes(column.fieldname) && value > 0) {
            let branch = frappe.query_report.get_filter_value("branch") || "";
            let delivery_date = data["delivery_date"] || data["Delivery Date"];

            let url = `/app/sketch-order-form?view=list`;

            if (branch) {
                url += `&branch=${encodeURIComponent(branch)}`;
            }

            if (delivery_date) {
                url += `&delivery_date=${encodeURIComponent(JSON.stringify(["=", delivery_date]))}`;
            }

            if (column.fieldname === "submitted") {
                url += `&docstatus=1`;
            }

            if (column.fieldname === "pending") {
                url += `&docstatus=0`;
            }

            if (column.fieldname === "cancelled") {
                url += `&workflow_state=${encodeURIComponent("Cancelled")}`;
            }

            return `<a href="${url}" target="_blank">${value}</a>`;
        }

        return value;
    }
};
