// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Department wise Asset Maintenance"] = {
    // filters: [
    //     {
    //         fieldname: "company",
    //         label: __("Company"),
    //         fieldtype: "MultiSelectList",
    //         options: "Company",
    //         reqd: 0,
    //         get_data: function(txt) {
    //             return frappe.db.get_link_options("Company", txt);
    //         }
    //     },
    //     {
    //         fieldname: "location",
    //         label: __("Location"),
    //         fieldtype: "MultiSelectList",
    //         options: "Location",
    //         reqd: 0,
    //         get_data: function(txt) {
    //             return frappe.db.get_link_options("Location", txt);
    //         }
    //     }
    // ],

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "total_assets") {
            let companies = frappe.query_report.get_filter_value("company") || [];
            let locations = frappe.query_report.get_filter_value("location") || [];

            if (typeof companies === "string") companies = [companies];
            if (typeof locations === "string") locations = [locations];

            let company_param = companies.length > 0 ? encodeURIComponent(JSON.stringify(["in", companies])) : "";
            let location_param = locations.length > 0 ? encodeURIComponent(JSON.stringify(["in", locations])) : "";

            let department = data && data.department ? data.department.replace(/(<([^>]+)>)/gi, "") : "";
            let department_param = department ? `&department=${encodeURIComponent(department)}` : "";
            let status_param = `&status=${encodeURIComponent("In Maintenance")}`;

            let url = `/app/asset?view=list&docstatus=1${status_param}`;
            if (company_param) url += `&company=${company_param}`;
            if (location_param) url += `&location=${location_param}`;
            url += department_param;

            return `<a href="${url}" target="_blank">${value}</a>`;
        }

        return value;
    }
};
