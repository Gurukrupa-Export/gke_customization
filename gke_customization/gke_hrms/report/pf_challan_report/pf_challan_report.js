// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["PF Challan Report"] = {
	"filters": [
		{
			"label": __("Month"),
			"fieldtype": "Select",
			"fieldname": "month",
			"reqd": 1,
			"options": [],
			"default": ()=>{
				const dateObject = new Date(); // create a new date object with the current date
				const options = { month: "short", year: "numeric" };
				const dateString = dateObject.toLocaleDateString("en-US", options);
				return dateString
			},
			"on_change": function(query_report){
				var _month = query_report.get_filter_value('month');
				if (!_month) return
				let firstDayOfMonth = moment(_month, "MMM YYYY").toDate();
				firstDayOfMonth = frappe.datetime.obj_to_str(firstDayOfMonth)
				let lastDayOfMonth = frappe.datetime.month_end(firstDayOfMonth)
				query_report.set_filter_value({
					"from_date": firstDayOfMonth,
					"to_date": lastDayOfMonth,
					"employee": null
				}); 
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
		fetch_month_list();
		report.page.add_button("Clear Filters", function() {
			window.open("/app/query-report/PF%20Challan%20Report", "_self")
		}).addClass("btn-info")	
		report.page.add_inner_button(__("PF File"), function () {
			frappe.call({
				method: "gke_customization.gke_hrms.report.pf_challan_report.pf_challan_report.export_txt", 
				args: {
					filters: report.get_values()
				},
				callback: function (r) {
				if (r.message) {
					// 🔽 Auto download
					const link = document.createElement("a");
					link.href = r.message;
					link.download = "pf_export.txt";
					document.body.appendChild(link);
					link.click();
					document.body.removeChild(link);
				}
			}
			});
		}).addClass("btn-secondary");
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