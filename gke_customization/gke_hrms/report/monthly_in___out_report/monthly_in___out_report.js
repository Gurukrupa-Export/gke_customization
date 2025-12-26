// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Monthly In - Out Report"] = {
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
			"reqd": 1
		}, 
		{
			"label": __("Branch"),
			"fieldtype": "Link",
			"fieldname": "branch",
			"options": "Branch",
		}, 
		{
			"label": __("Department"),
			"fieldtype": "MultiSelectList",
			"fieldname": "department",
			"reqd": 1,
			get_data: function(txt) {
				var company = frappe.query_report.get_filter_value('company');
				var filters = {}
				if (company) filters['company'] = company
				return frappe.db.get_link_options('Department', txt, filters);
			},
		},
		{
			"label": __("Employee"),
			"fieldtype": "Link",
			"fieldname": "employee",
			"options": "Employee",
			// "depends_on": "eval: frappe.user.has_role('System Manager') || frappe.user.has_role('GK HR')",
			
		}, 

	],
	onload: (report) => {
		fetch_month_list()
		fetch_employees(report)
		
		report.page.add_button("Clear Filters", function() {
			window.open("/app/query-report/Monthly%20In%20-%20Out%20Report", "_self")
		}).addClass("btn-info")

		report.page.add_button("Generate", function() {
			var company = frappe.query_report.get_filter_value('company');
			var department = frappe.query_report.get_filter_value('department');
			if (company){
				frappe.query_report.set_filter_value({
					"company": company,
					"department": department
				});
			}
			report.refresh();
		}).addClass("btn-primary") 
	}
};

function fetch_employees(report) {
	console.log('has role',frappe.user.has_role("System Manager"), frappe.user.has_role("GK HR"));
	console.log('user', frappe.session.user);

	const user = frappe.user.has_role("System Manager") && frappe.user.has_role("GK HR")
	if (!user) {
		// Fetch employee linked to logged-in user
		frappe.db.get_value("Employee", { user_id: frappe.session.user }, "name")
			.then(r => {
				console.log(r.message);
				
				if (r && r.message && r.message.name) {
					report.set_filter_value("employee", r.message.name);

					// Lock the field
					let emp_filter = report.get_filter("employee");
					emp_filter.df.read_only = 1;
					emp_filter.refresh();
				}
			});
	}
}

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