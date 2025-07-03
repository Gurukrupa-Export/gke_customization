frappe.query_reports["Allocated vs Unallocated Asset count"] = {
    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "y") {
            // Get MultiSelect values
            let companies = frappe.query_report.get_filter_value("company") || [];
            let locations = frappe.query_report.get_filter_value("location") || [];

            if (typeof companies === "string") companies = [companies];
            if (typeof locations === "string") locations = [locations];

            let company_param = companies.length > 0 ? encodeURIComponent(JSON.stringify(["in", companies])) : "";
            let location_param = locations.length > 0 ? encodeURIComponent(JSON.stringify(["in", locations])) : "";

            let url = `/app/asset?view=list&docstatus=1`;

            if (company_param) {
                url += `&company=${company_param}`;
            }
            if (location_param) {
                url += `&location=${location_param}`;
            }

            // Add custodian filter based on type
            if (data.x === "Allocated") {
                url += "&custodian=%5B%22is%22%2C%22set%22%5D";
            } else if (data.x === "Unallocated") {
                url += "&custodian=%5B%22is%22%2C%22not+set%22%5D";
            }

            return `<a href="${url}" target="_blank">${value}</a>`;
        }

        return value;
    }
};
