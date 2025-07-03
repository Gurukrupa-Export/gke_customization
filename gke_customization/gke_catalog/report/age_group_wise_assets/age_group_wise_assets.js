frappe.query_reports["Age Group wise Assets"] = {
    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "asset_count") {
            let companies = frappe.query_report.get_filter_value("company") || [];
            let locations = frappe.query_report.get_filter_value("location") || [];

            if (typeof companies === "string") companies = [companies];
            if (typeof locations === "string") locations = [locations];

            let company_param = companies.length > 0 ? encodeURIComponent(JSON.stringify(["in", companies])) : "";
            let location_param = locations.length > 0 ? encodeURIComponent(JSON.stringify(["in", locations])) : "";

            let age_bracket = data && data.age_bracket ? data.age_bracket.replace(/(<([^>]+)>)/gi, "") : "";
            let today = frappe.datetime.get_today();

            let start_date = "";
            let end_date = "";

            if (age_bracket === "< 1 Year") {
                start_date = frappe.datetime.add_months(today, -12);
                end_date = today;
            } else if (age_bracket === "1–3 Years") {
                start_date = frappe.datetime.add_months(today, -36);
                end_date = frappe.datetime.add_months(today, -12);
            } else if (age_bracket === "> 3 Years") {
                start_date = "";
                end_date = frappe.datetime.add_months(today, -36);
            }

            let url = `/app/asset?view=list&docstatus=1`;
            if (company_param) url += `&company=${company_param}`;
            if (location_param) url += `&location=${location_param}`;

            if (age_bracket === "< 1 Year" || age_bracket === "1–3 Years") {
                url += `&purchase_date=${encodeURIComponent(JSON.stringify([">=", start_date]))}`;
                url += `&purchase_date=${encodeURIComponent(JSON.stringify(["<=", end_date]))}`;
            } else if (age_bracket === "> 3 Years") {
                url += `&purchase_date=${encodeURIComponent(JSON.stringify(["<=", end_date]))}`;
            }

            return `<a href="${url}" target="_blank">${value}</a>`;
        }

        return value;
    }
    };
