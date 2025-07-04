frappe.query_reports["Total Asset Value and NBV"] = {
    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (["total_asset_cost", "net_book_value"].includes(column.fieldname)) {
            let company = data.company || "";
            let company_param = company ? `&company=${encodeURIComponent(company)}` : "";

            let url = `/app/asset?view=list&docstatus=1${company_param}`;

            if (column.fieldname === "net_book_value") {
                url += `&status=%5B%22not+in%22%2C%5B%22Scrapped%22%2C%22Sold%22%5D%5D`;
            }

            return `<a href="${url}" target="_blank">${value}</a>`;
        }

        return value;
    }
};
