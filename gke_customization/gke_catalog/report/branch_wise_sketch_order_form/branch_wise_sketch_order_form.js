frappe.query_reports["Branch Wise Sketch Order Form"] = {


    formatter: function (value, row, column, data, default_formatter) {

        value = default_formatter(value, row, column, data);

        const clickable_columns = ["total_orders", "submitted_orders", "pending_orders", "cancelled_orders"];

        if (clickable_columns.includes(column.fieldname) && value > 0) {

            const branch = data.branch;
            const from_date = frappe.query_report.get_filter_value("from_date");
            const to_date = frappe.query_report.get_filter_value("to_date");

            let url = `/app/sketch-order-form?view=list`;

            if (branch) url += `&branch=${encodeURIComponent(branch)}`;
            if (from_date && to_date) url += `&creation=${encodeURIComponent(JSON.stringify(["between", [from_date, to_date]]))}`;

            if (column.fieldname === "submitted_orders") url += `&docstatus=${encodeURIComponent(1)}`;
            if (column.fieldname === "pending_orders") url += `&docstatus=${encodeURIComponent(0)}`;
            if (column.fieldname === "cancelled_orders") url += `&docstatus=${encodeURIComponent(2)}`;

            return `<a href="${url}" target="_blank">${value}</a>`;
        }

        return value;
    }
};







// http://192.168.200.207:8001/app/sketch-order-form?workflow_state=Draft&from_date=2025-06-06&to_date=2025-06-06

// workflow_state=Draft&modified=%5B"Between"%2C%5B"2025-07-01"%2C"2025-07-31"%5D%5D

