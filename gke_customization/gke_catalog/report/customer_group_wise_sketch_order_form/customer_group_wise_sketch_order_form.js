frappe.query_reports["Customer Group wise Sketch Order Form"] = {

    formatter: function (value, row, column, data, default_formatter) {

        value = default_formatter(value, row, column, data);

        const clickable_columns = ["total_orders", "submitted", "pending", "cancelled"];

        if (clickable_columns.includes(column.fieldname) && value > 0) {

            const customer_codes = data.customer_codes ? data.customer_codes.split(",") : [];
            if (customer_codes.length === 0) return value;

            const from_date = frappe.query_report.get_filter_value("from_date");
            const to_date = frappe.query_report.get_filter_value("to_date");
            const branch = frappe.query_report.get_filter_value("branch");

            let url = `/app/sketch-order-form?view=list`;

            url += `&customer_code=${encodeURIComponent(JSON.stringify(["in", customer_codes]))}`;

            if (branch) {
                url += `&branch=${encodeURIComponent(branch)}`;
            }
            if (from_date && to_date) {
                url += `&modified=${encodeURIComponent(JSON.stringify(["between", [from_date, to_date]]))}`;
            }

            if (column.fieldname === "submitted") url += `&docstatus=${encodeURIComponent(1)}`;
            if (column.fieldname === "pending") url += `&docstatus=${encodeURIComponent(0)}`;
            if (column.fieldname === "cancelled") url += `&docstatus=${encodeURIComponent(2)}`;

            return `<a href="${url}" target="_blank">${value}</a>`;
        }

        return value;
    }
};
