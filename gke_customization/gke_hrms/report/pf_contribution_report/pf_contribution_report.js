// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["PF Contribution Report"] = {
	"filters": [
		{
            "label": __("Month"),
            "fieldtype": "Select",
            "fieldname": "month",
            "reqd": 1,
            "options": [
                "January","February","March","April",
                "May","June","July","August",
                "September","October","November","December"
            ],
            "default": new Date().toLocaleString('en-US', { month: 'long' }),
            "on_change": function() {
                set_dates();
            }
        },
        {
            "label": __("Year"),
            "fieldtype": "Select",
            "fieldname": "year",
            "reqd": 1,
            "options": (() => {
                let years = [];
                let currentYear = new Date().getFullYear();
                for (let i = currentYear - 5; i <= currentYear + 5; i++) {
                    years.push(String(i));
                }
                return years;
            })(),
            "default": String(new Date().getFullYear()),
            "on_change": function() {
                set_dates();
            }
        },
		{
			"label": __("From Date"),
			"fieldtype": "Date",
			"fieldname": "from_date",
			"read_only": 1,
			"default": frappe.datetime.month_start(frappe.datetime.get_today()),
			"on_change": function(query_report) {
				var from_date = query_report.get_values().from_date;
				if (!from_date) {
					return;
				}
				let date = new moment(from_date)
				var to_date = date.endOf('month').format()
				query_report.set_filter_value({
					"to_date": to_date
				});
			}
		},
		{
			"label": __("To Date"),
			"fieldtype": "Date",
			"fieldname": "to_date",
			"reqd": 1,
			"read_only": 1,
			"default": frappe.datetime.month_end(frappe.datetime.get_today())
		},
		{
			"fieldname": "company",
			"label": "Company",
			"fieldtype": "Link",
			"options": "Company",
			// "default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		//{
		//	"fieldname": "report_type",
		//	"label": "Report Type",
		//	"fieldtype": "Select",
		//	"options": "Register Report\nPF File",
		//	"default": "PF File",
		//	"reqd": 1
		//},
		{
			"fieldname": "employee",
			"label": "Employee",
			"fieldtype": "MultiSelectList",
			"get_data": function(txt) {
				var company = frappe.query_report.get_filter_value('company');
				var filters = {}
				if (company) filters['company'] = company
				return frappe.db.get_link_options('Employee', txt, filters);
			}
		}
	],
	
	onload: (report) => {
		set_dates();
		report.page.add_button("Clear Filters", function() {
			window.open("/app/query-report/PF%20Contribution%20Report", "_self")
		}).addClass("btn-info")	
	}
};

function fetch_month_list() {
	frappe.call({
		method: "gke_customization.gke_hrms.report.pf_contribution_report.pf_contribution_report.get_month_range",
		freeze: false,
		callback: function(r) {
			var month = frappe.query_report.get_filter('month');
				month.df.options.push(...r.message);
				month.refresh();
		}
	})
}

function set_dates() {
    let report = frappe.query_report;
    if (!report) return;

    let monthName = report.get_filter_value("month");
    let year = parseInt(report.get_filter_value("year"));

    if (!monthName || !year) return;

    const monthIndex = [
        "January","February","March","April",
        "May","June","July","August",
        "September","October","November","December"
    ].indexOf(monthName);

    let from_date = new Date(year, monthIndex, 1);
    let to_date = new Date(year, monthIndex + 1, 0);

    report.set_filter_value({
        from_date: frappe.datetime.obj_to_str(from_date),
        to_date: frappe.datetime.obj_to_str(to_date)
    });
}