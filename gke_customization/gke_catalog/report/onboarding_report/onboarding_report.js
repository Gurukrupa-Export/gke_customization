// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Onboarding report"] = {
	"filters": [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: '2025-01-01'
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: '2025-05-31'
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "MultiSelectList",
			options: "Company",
			reqd: 0,
			get_data: function (txt) {
				return frappe.db.get_link_options("Company", txt);
			}
		},
        {
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "MultiSelectList",
			options: "Branch",
			reqd: 0,
			get_data: function (txt) {
				return frappe.db.get_link_options("Branch", txt);
			}
		},

		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "MultiSelectList",
			options: "Department",
			reqd: 0,
			get_data: function (txt) {
				return frappe.db.get_link_options("Department", txt);
			}
		},
    

		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			reqd: 0
		}
	],

	onload: function (report) {
		// Clear Filter button setup
		const clearFilterButton = report.page.add_inner_button(__("Clear Filter"), function () {
			report.filters.forEach(function (filter) {
				let field = report.get_filter(filter.fieldname);
				if (field.df.fieldtype === "MultiSelectList") {
					field.set_value([]);
				} else if (field.df.default) {
					field.set_value(field.df.default);
				} else {
					field.set_value("");
				}
			});
		});

		// Fetch distinct options for dropdown filters
		function fetchOptions(doctype, field, filterField, includeBlank = false) {
			frappe.call({
				method: "frappe.client.get_list",
				args: {
					doctype: doctype,
					fields: [`distinct ${field}`],
					order_by: `${field} asc`,
					limit_page_length: 30000,
				},
				callback: function (r) {
					if (r.message) {
						let options = r.message
							.map(row => row[field])
							.filter(value => value && value.trim() !== "");
						if (includeBlank) {
							options.unshift("");
						}
						const filter = report.get_filter(filterField);
						filter.df.options = options;
						filter.refresh();
					}
				},
			});
		}

		// Populate boarding status options
		fetchOptions("Employee Onboarding", "boarding_status", "status", true);

		// Event binding for View Activities button (after report render)
		frappe.after_ajax(() => {
			$(document).on("click", ".view-activities-btn", function () {
				let onboarding_id = $(this).data("onboarding-id");

				frappe.call({
					method: "gke_customization.gke_catalog.report.onboarding_report.onboarding_report.get_onboarding_activities",
					args: { onboarding_id },
					callback: function (r) {
						if (r.message) {
							let details = r.message.onboarding_details;
							let activities = r.message.activities;
					
							let html = `<div style="margin-bottom: 15px;">
								<strong>Applicant ID:</strong> ${details.job_applicant || "N/A"}<br>
								<strong>Employee Name:</strong> ${details.employee_name || "N/A"}
							</div>`;
					
							html += '<table class="table table-bordered">';
							html += '<thead><tr><th>Subject</th><th>Activity Status</th><th>Assigned To</th><th>Exp. Start Date</th><th>Exp. End Date</th></tr></thead>';
							html += '<tbody>';
							activities.forEach(function (act) {
								html += `<tr>
									<td>${act.subject || ""}</td>
									<td>${act.task_status || ""}</td>
									<td>${act.assigned_to || ""}</td>
									<td>${act.exp_start_date || ""}</td>
									<td>${act.exp_end_date || ""}</td>
								</tr>`;
							});
							html += '</tbody></table>';
					
							let dialog = new frappe.ui.Dialog({
								title: 'Onboarding Activities',
								size: 'extra-large',
								fields: [
									{
										fieldtype: 'HTML',
										fieldname: 'activities_html'
									}
								]
							});
					
							dialog.fields_dict.activities_html.$wrapper.html(html);
							dialog.show();
						}
					}
				});
			});
		});
	}
};
