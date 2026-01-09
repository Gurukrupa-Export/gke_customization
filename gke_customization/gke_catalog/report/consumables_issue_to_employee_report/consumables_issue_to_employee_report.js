// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Consumables Issue to Employee Report"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 0
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 0
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "MultiSelectList",
			options: "Department",
			reqd: 0,
			get_data: function(txt) {
				return frappe.db.get_link_options("Department", txt);
			}
		}
	],

	onload: function(report) {
		const clearFilterButton = report.page.add_inner_button(__("Clear Filter"), function() {
			report.filters.forEach(function(filter) {
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
	},

	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		// Make view_details clickable
		if (column.fieldname == "view_details" && data && data.worker_code) {
			return `<a onclick="showEmployeeDetails('${data.worker_code}', '${data.worker}')" style="cursor:pointer; color: #2490ef;">${value}</a>`;
		}
		
		return value;
	}
};

// Global function to show employee details in dialog
window.showEmployeeDetails = function(employee_code, worker_name) {
	let filters = frappe.query_report.get_filter_values();
	
	frappe.call({
		method: 'gke_customization.gke_catalog.report.consumables_issue_to_employee_report.consumables_issue_to_employee_report.get_employee_details',
		args: {
			employee_code: employee_code,
			from_date: filters.from_date,
			to_date: filters.to_date
		},
		callback: function(r) {
			if (r.message) {
				let data = r.message;
				
				// Create HTML table
				let html = `
					<div style="max-height: 500px; overflow-y: auto;">
						<table class="table table-bordered table-hover">
							<thead style="position: sticky; top: 0; background: white;">
								<tr>
									<th>Sr No</th>
									<th>Issue Date</th>
									<th>Dept</th>
									<th>Manager</th>
									<th>Item Code</th>
									<th>Item Group</th>
									<th>Category</th>
									<th>Sub Category</th>
									<th>Qty</th>
									<th>Rate</th>
									<th>Unit</th>
									<th>Total</th>
								</tr>
							</thead>
							<tbody>
				`;
				
				data.forEach(row => {
					html += `
						<tr>
							<td>${row.serial_no}</td>
							<td>${frappe.datetime.str_to_user(row.issue_date)}</td>
							<td>${row.dept || ''}</td>
							<td>${row.manager || ''}</td>
							<td>${row.item_code || ''}</td>
							<td>${row.item_group || ''}</td>
							<td>${row.category || ''}</td>
							<td>${row.sub_category || ''}</td>
							<td>${row.qty}</td>
							<td>${format_currency(row.rate)}</td>
							<td>${row.unit}</td>
							<td>${format_currency(row.total)}</td>
						</tr>
					`;
				});
				
				html += `
							</tbody>
						</table>
					</div>
				`;
				
				// Show dialog
				let d = new frappe.ui.Dialog({
					title: __('Issue Details - {0}', [worker_name]),
					fields: [
						{
							fieldtype: 'HTML',
							fieldname: 'details_html'
						}
					],
					size: 'extra-large'
				});
				
				d.fields_dict.details_html.$wrapper.html(html);
				d.show();
			}
		}
	});
};
