frappe.query_reports["Designer wise Sketch Details"] = {
    filters: [
        {
        fieldname: "year",
        label: __("Year"),
        fieldtype: "Select",
        options: ["", 2023, 2024, 2025, 2026],
        default: new Date().getFullYear(),
        reqd: 0,
        on_change: function () {
            const selected_year = frappe.query_report.get_filter_value("year");
            if (selected_year) {
                frappe.query_report.set_filter_value("from_date", `${selected_year}-01-01`);
                frappe.query_report.set_filter_value("to_date", `${selected_year}-12-31`);
            }
        }
    },
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date",
            // default: frappe.datetime.month_start()
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            // default: frappe.datetime.month_end()
        },
        {
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
            default:"Gurukrupa Export Private Limited",
			reqd: 0,
            on_change: function () {
				let company = frappe.query_report.get_filter_value("company");
				let branch_filter = frappe.query_report.get_filter("branch");
				if (company && company.trim().toLowerCase() === "gurukrupa export private limited") {
					branch_filter.df.hidden = 0;
					branch_filter.toggle(true);
				} else {
					branch_filter.df.hidden = 1;
					branch_filter.toggle(false);
				}
                frappe.query_report.refresh();
			}
		},
    // {
	// 	fieldname: "designer_branch",
	// 	label: __("Branch"),
	// 	fieldtype: "Link",
	// 	options: "Branch",
    //     // default:"GEPL-MU-009",
	// 	reqd: 0,
	// },
    {
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "MultiSelectList",
			options: "Branch",
			reqd: 0,
            hidden:1,
			get_data: function (txt) {
				return frappe.db.get_link_options("Branch", txt);
			},
            on_change: () => frappe.query_report.refresh()
		},
    {
            fieldname: "designer",
            label: "Designer",
            fieldtype: "Link",
            options: "Employee",
             get_query: function () {
                return {
                    filters: {
                        designation: "Sketch Designer"
                    }
                };
            }
        },
        {
            fieldname: "category",
            label: "Category",
            fieldtype: "MultiSelectList",
            options: [],
            get_data: function (txt) {
                return frappe.db.get_list("Sketch Order", {
                    fields: ["category"],
                    distinct: true,
                    filters: [["category", "like", `%${txt}%`]],
                    order_by: "category asc",
                }).then(res => {
                    return (res || [])
                        .map(row => row.category)
                        .filter(v => v)
                        .map(v => ({ value: v, label: v, description: "" }));
                });
            }
        }
    ],

    get_datatable_options(options) {
        return {
            ...options,
            showTotalRow: true
        };
    },
    onload: function (report) {
    // Add Clear Filter Button
    report.page.add_inner_button(__("Clear Filter"), function () {
        report.filters.forEach(function (filter) {
            let field = report.get_filter(filter.fieldname);

            if (field.df.fieldtype === "MultiSelectList") {
                field.set_value([]);
            } else if (field.df.fieldname === "from_date" || field.df.fieldname === "to_date") {
                const year = report.get_filter_value("year") || new Date().getFullYear();
                if (field.df.fieldname === "from_date") {
                    field.set_value(`${year}-01-01`);
                } else {
                    field.set_value(`${year}-12-31`);
                }
            } else if (field.df.default) {
                field.set_value(field.df.default);
            } else {
                field.set_value("");
            }
        });
    });

    // Set default year & dates on first load
    let current_year = new Date().getFullYear();
    report.set_filter_value("year", current_year);
    report.set_filter_value("from_date", `${current_year}-01-01`);
    report.set_filter_value("to_date", `${current_year}-12-31`);

    let company = report.get_filter_value("company");
		let branch_filter = report.get_filter("branch");
		if (company && company.trim().toLowerCase() === "gurukrupa export private limited") {
			branch_filter.df.hidden = 0;
			branch_filter.toggle(true);
		} else {
			branch_filter.df.hidden = 1;
			branch_filter.toggle(false);
		}
}

};


