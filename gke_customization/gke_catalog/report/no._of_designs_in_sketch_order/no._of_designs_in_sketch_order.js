frappe.query_reports["No. of Designs in Sketch Order"] = {
    formatter: function (value, row, column, data, default_formatter) {

        value = default_formatter(value, row, column, data);

        const clickable_columns = ["submitted", "pending", "cancelled"];

        if (clickable_columns.includes(column.fieldname) && value > 0) {

            const branches = frappe.query_report.get_filter_value("branch");
            const branch_param = branches ? `&branch=${encodeURIComponent(branches)}` : "";

            const delivery_date = data["delivery_date"];
            const date_param = delivery_date ? `&delivery_date=${encodeURIComponent(JSON.stringify(["=", delivery_date]))}` : "";

            
            let status_param = "";
            if (column.fieldname === "submitted") {
                status_param = `&docstatus=1`;
            }
            if (column.fieldname === "pending") {
                status_param = `&docstatus=0`;
            }
            if (column.fieldname === "cancelled") {
                status_param = `&docstatus=2`;
            }

           
            const url = `/app/sketch-order?view=list${branch_param}${status_param}${date_param}`;

            return `<a href="${url}" target="_blank">${value}</a>`;
        }

        return value;
    }
};
