frappe.query_reports["Company wise Assets"] = {
    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (["total_asset"].includes(column.fieldname)) {
            let company = data.company || "";
            let company_param = company ? `&company=${encodeURIComponent(company)}` : "";

            let url = `/app/asset?view=list&docstatus=1${company_param}`;

            return `<a href="${url}" target="_blank">${value}</a>`;
        }

        return value;
    }
};
