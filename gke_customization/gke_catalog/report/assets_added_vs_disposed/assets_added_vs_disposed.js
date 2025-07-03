// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Assets added vs disposed"] = {
    formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);

    if (["added_count", "disposed_count"].includes(column.fieldname)) {
        let companies = frappe.query_report.get_filter_value("company") || [];
        let locations = frappe.query_report.get_filter_value("location") || [];

        if (typeof companies === "string") companies = [companies];
        if (typeof locations === "string") locations = [locations];

        let company_param = companies.length > 0 ? encodeURIComponent(JSON.stringify(["in", companies])) : "";
        let location_param = locations.length > 0 ? encodeURIComponent(JSON.stringify(["in", locations])) : "";

        let period = data && data.period ? data.period.replace(/(<([^>]+)>)/gi, "") : "";
        let [month_str, year_str] = period.split("-");
        let date = new Date(`${month_str} 1, ${year_str}`);

        // Use ISO format yyyy-mm-dd
        let first_day = frappe.datetime.month_start(date); // yyyy-mm-dd
        let last_day = frappe.datetime.month_end(date);    // yyyy-mm-dd

        let date_field = column.fieldname === "added_count" ? "purchase_date" : "disposal_date";
        let status_param = column.fieldname === "disposed_count"
            ? `&status=${encodeURIComponent(JSON.stringify(["in", ["Sold", "Scrapped"]]))}`
            : "";

        let url = `/app/asset?view=list&docstatus=1`;
        if (company_param) url += `&company=${company_param}`;
        if (location_param) url += `&location=${location_param}`;
        url += `&${date_field}=${encodeURIComponent(JSON.stringify([">=", first_day]))}`;
        url += `&${date_field}=${encodeURIComponent(JSON.stringify(["<=", last_day]))}`;
        url += status_param;

        return `<a href="${url}" target="_blank">${value}</a>`;
    }

    return value;
}

};
