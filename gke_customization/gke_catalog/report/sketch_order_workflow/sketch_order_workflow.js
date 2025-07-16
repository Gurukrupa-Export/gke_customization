frappe.query_reports["Sketch Order Workflow"] = {
    formatter: function (value, row, column, data, default_formatter) {

        value = default_formatter(value, row, column, data);

        if (column.fieldname === "count" && value > 0) {

            const workflow_state = data.workflow_state;

            let url = `/app/sketch-order?view=list`;

            if (workflow_state) {
                url += `&workflow_state=${encodeURIComponent(JSON.stringify(["=", workflow_state]))}`;
            }

            // filters   
            const from_date = frappe.query_report.get_filter_value("from_date");
            const to_date = frappe.query_report.get_filter_value("to_date");
            const branch = frappe.query_report.get_filter_value("branch");

            if (from_date && to_date) {
                url += `&modified=${encodeURIComponent(JSON.stringify(["between", [from_date, to_date]]))}`;
            }
            if (branch) {
                url += `&branch=${encodeURIComponent(JSON.stringify(["=", branch]))}`;
            }

            return `<a href="${url}" target="_blank">${value}</a>`;
        }

        return value;
    }
};






// http://192.168.200.207:8001/app/sketch-order-form?workflow_state=Draft&from_date=2025-06-06&to_date=2025-06-06

// workflow_state=Draft&modified=%5B"Between"%2C%5B"2025-07-01"%2C"2025-07-31"%5D%5D

