// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Location wise Asset count"] = {
    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "count") {
            let companies = frappe.query_report.get_filter_value("company") || [];
            if (typeof companies === "string") companies = [companies];

            let company_param = companies.length > 0 ? encodeURIComponent(JSON.stringify(["in", companies])) : "";

            let location = data && data.location ? data.location.replace(/(<([^>]+)>)/gi, "") : "";
            let location_param = location ? `&location=${encodeURIComponent(location)}` : "";

            let url = `/app/asset?view=list&docstatus=1`;
            if (company_param) url += `&company=${company_param}`;
            url += location_param;

            return `<a href="${url}" target="_blank">${value}</a>`;
        }

        return value;
    }
};
