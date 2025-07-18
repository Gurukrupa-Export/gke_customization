frappe.query_reports["Sketch Order Docstatus"] = {

    formatter: function (value, row, column, data, default_formatter) {

        value = default_formatter(value, row, column, data);

        const docstatus_map = {
            "Pending": 0,
            "Submitted": 1,
            "Cancelled": 2
        };

        if (column.fieldname === "count" && value > 0) {

            const label = data["docstatus"]; 

            if (!label || !(label in docstatus_map)) return value;

            const docstatus = docstatus_map[label];
            const from_date = frappe.query_report.get_filter_value("from_date");
            const to_date = frappe.query_report.get_filter_value("to_date");
            const branch = frappe.query_report.get_filter_value("branch");

            let url = `/app/sketch-order?view=list`;

            if (branch) url += `&branch=${encodeURIComponent(branch)}`;
            if (from_date && to_date) url += `&modified=${encodeURIComponent(JSON.stringify(["between", [from_date, to_date]]))}`;
            if (docstatus !== undefined) url += `&docstatus=${encodeURIComponent(docstatus)}`;

            return `<a href="${url}" target="_blank">${value}</a>`;
        }

        return value;
    }
};
