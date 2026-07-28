// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["ESIC Challan Report"] = {
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
			"label": __("Company"),
			"fieldtype": "Link",
			"fieldname": "company",
			"options": "Company",
			"reqd": 1,
		},
		{
			"label": __("Branch"),
			"fieldtype": "Link",
			"fieldname": "branch",
			"options": "Branch" 
		}, 
	],
	onload: (report) => {
		set_dates();
		report.page.add_button("Clear Filters", function() {
			window.open("/app/query-report/ESIC%20Challan%20Report", "_self")
		}).addClass("btn-info")
		
		report.page.add_inner_button(__("ESIC File"), function () {
			frappe.call({
				method: "gke_customization.gke_hrms.report.esic_challan_report.esic_challan_report.export_txt", 
				args: {
					filters: report.get_values()
				},
				callback: function (r) {
				if (r.message) {
					// 🔽 Auto download
					const link = document.createElement("a");
					link.href = r.message;
					link.download = "esic_export.xlsx";
					document.body.appendChild(link);
					link.click();
					document.body.removeChild(link);
				}
			}
			});
		}).addClass("btn-secondary");
		
	},
	"formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
		if (data && ["gross_pay","employee_id"].includes(column.id) && value) {
			value = $(`<span>${value}</span>`);
			var $value = $(value).css("font-weight", "bold");
			value = $value.wrap("<p></p>").parent().html();
		}
		var total_field = ["Total Employees", "Total Gross","Excepted Employees","Excepted Gross","ESIC Members","ESIC Wages","Employee Contribution","Employer Contribution","Total Contribution"];
		if (["branch", "employee_name"].includes(column.id) && total_field.includes(data.employee_name)) {
			value = $(`<span>${value}</span>`);
			var $value = $(value).css("font-weight", "bold");
			var $value = $(value).css("color", "blue");
			value = $value.wrap("<p></p>").parent().html();
		}

        return value;
    }
};

function fetch_month_list() {
	frappe.call({
		method: "gurukrupa_customizations.gurukrupa_customizations.report.monthly_in_out.monthly_in_out.get_month_range",
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