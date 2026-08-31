// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Department Wise Daily Present Report"] = {
	"filters": [
       {"fieldname": "date", "label": "Date", "fieldtype": "Date", "default": "Today", "reqd": 1},
       {"fieldname": "company", "label": "Company", "fieldtype": "Link", "options": "Company","reqd": 1},
    //    {"fieldname": "department", "label": "Department", "fieldtype": "Link", "options": "Department","reqd": 1},
    //    {"fieldname": "manager", "label": "Manager", "fieldtype": "Link", "options": "Employee"}
		{
			"label": __("Department"),
			"fieldtype": "Link",
			"fieldname": "department",
			"options": "Department",
			"reqd": 1,
			"get_query": function () {
				let company = frappe.query_report.get_filter_value("company");
				return {
					filters: {
						company: company
					}
				};
			},
			"on_change": fetch_employees
		},
		{
			"label": __("Employee"),
			"fieldtype": "Link",
			"fieldname": "manager",
			"options": "Employee",
			"get_query": function () {
				let company = frappe.query_report.get_filter_value("company");
				let department = frappe.query_report.get_filter_value("department");
				let filters = {};
				if (company) filters.company = company;
				if (department) filters.department = department;

				return {
					filters: filters
				};
			},
		}, 
     ],
	onload: (report) => {
		report.page.add_button("Clear Filters", function() {
			window.open("/app/query-report/Department%20Wise%20Daily%20Present%20Report", "_self")
		}).addClass("btn-info")
		
		const user = frappe.user.has_role("System Manager") || frappe.user.has_role("GK HR")
		// console.log('has role',user, 'user', frappe.session.user);	
		if (user) {
			report.page.add_button("Send Mail", function() {
				frappe.call({
					method: "gke_customization.gke_hrms.report.department_wise_daily_present_report.department_wise_daily_present_report.send_morning_present_report",
					args: {
						date: report.get_values().date,
						department: report.get_values().department
					},
					freeze: true,
					freeze_message: __("Sending..."),
					callback: function(r) {
						if (r.message) {
							const sent = r.message.sent || [];
							const skipped = r.message.skipped || [];
 
							let msg;
							if (sent.length) {
								const lines = sent.map(
									s => `${s.department} — ${(s.managers || []).join(", ")}`
								);
								msg = `Mail sent:<br>${lines.join("<br>")}`;
							} else {
								msg = "No mail was sent.";
							}
							if (skipped.length) {
								msg += `<br><br>Skipped (no manager or no data): ${skipped.join(", ")}`;
							}
							frappe.msgprint(msg);
						}
					}
				});
			}).addClass("btn-info")	
		}
	},
	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
 
		// Summary rows are the only ones where late_entry is a number
		// (normal employee rows carry "Yes"/"No"/"" there instead).
		const is_summary_row = data && typeof data.late_entry === "number";
 
		if (is_summary_row && ["status", "late_entry"].includes(column.id)) {
			const color = data.status === "Total" ? "red" : "blue";
			value = $(`<span>${value}</span>`).css({"font-weight": "bold", "color": color});
			value = value.wrap("<p></p>").parent().html();
		}
 
		return value;
	},
};

function fetch_employees(report) {
	// Fetch employee linked to logged-in user
	frappe.db.get_value("Employee", { user_id: frappe.session.user }, "name")
		.then(r => {
			if (r && r.message && r.message.name) {
				frappe.query_report.set_filter_value("manager", r.message.name);
 
				let emp_filter = frappe.query_report.get_filter("manager");
				if (emp_filter) {
					emp_filter.df.read_only = 1;
					emp_filter.refresh();
				}
			}
		});
} 