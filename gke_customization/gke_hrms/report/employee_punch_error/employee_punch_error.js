// Copyright (c) 2024, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Employee Punch Error"] = {
	"filters": [
		{
			"label": __("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": 'Company'
		},
		{
			"label": __("From Date"),
			"fieldname": "from_date",
			"fieldtype": "Date",
		},
		{
			"label": __("To Date"),
			"fieldname": "to_date",
			"fieldtype": "Date",
		},
		{
			"label": __("Department"),
			"fieldname": "department",
			"fieldtype": "Link",
			"options": 'Department',
			"get_query": function() {
				var company = frappe.query_report.get_filter_value('company')
				return {
					"doctype": "Department",
					"filters": {"company": company}
				}
			},
		},
		{
			"label": __("Employee"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": 'Employee'
		},	
		

	],
	onload: (report) => {
		
		report.page.add_button("Clear Filters", function() {
			window.open("/app/query-report/Employee%20Punch%20Error", "_self")
		}).addClass("btn-info");

		report.page.add_button("Generate", function() {
			var date = frappe.query_report.get_filter_value('date');
			var employeeId = frappe.query_report.get_filter_value('employee');
			frappe.query_report.set_filter_value({
				"date": date,
				"employee": employeeId
			});
		}).addClass("btn-primary");

		report.page.add_inner_button(__("Mark as Attendance"), function() {
			// var filters = report.get_values();
			// console.log(filters);
			
			var selected_rows = [];
			var checkedRow = 0;
			// $('.dt-scrollable').find(":input[type=checkbox]").each((idx, row) => {
			// 	if(row.checked){					
			// 		checkedRow++;
			// 		if(checkedRow == 1){
			// 			let employeeId = frappe.query_report.data[idx]['employee']
			// 			let date = frappe.query_report.data[idx]['date']
			// 			// frappe.set_route('Form', 'Manual Punch');
			// 			frappe.new_doc("Manual Punch", {
			// 					doctype: "Manual Punch",
			// 					date: date,
			// 					employee: employeeId
			// 				});
			// 			selected_rows.push(frappe.query_report.data[idx]);
			// 			console.log(selected_rows);
			// 		} 
			// 	}
			// });
			$('.dt-scrollable').find(":input[type=checkbox]").each((idx, row) => {
				if(row.checked){                    
					checkedRow++;
					if(checkedRow == 1){
						let employeeId = frappe.query_report.data[idx]['employee']
						let date = frappe.query_report.data[idx]['date']

						selected_rows.push({
							employeeId: employeeId,
							date: date
						});
					} 
				}
			});
		
			if(checkedRow === 0){
				frappe.msgprint(__("Please select at least one row."));
				return false; 
			} else if(checkedRow > 1){
				frappe.msgprint(__("You can select only one row."));
				return false;
			}
		
			let selectedRow = selected_rows[0];
			frappe.new_doc("Manual Punch", {
				doctype: "Manual Punch",
				error_date: selectedRow.date,
				employee: selectedRow.employeeId
			});
		}).addClass("btn-second");		
	},
	get_datatable_options(options) {
        return Object.assign(options, {
            checkboxColumn: true
        });
    }
};