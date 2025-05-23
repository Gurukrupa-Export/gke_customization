// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Attendance Punch Error Report"] = {
	"filters": [
		{
			"label": __("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": 'Company',
			"reqd": 1
		},
		{
			"label": __("From Date"),
			"fieldname": "from_date",
			"fieldtype": "Date",
			"reqd": 1
		},
		{
			"label": __("To Date"),
			"fieldname": "to_date",
			"fieldtype": "Date",
			"reqd": 1
		},
		{
			"label": __("Department"),
			"fieldname": "department",
			"fieldtype": "Link",
			"options": 'Department',
			// "reqd": 1,
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
		{
			"label": __("Branch"),
			"fieldname": "branch",
			"fieldtype": "Link",
			"options": 'Branch'
		},	
	],
	onload: (report) => {
		
		report.page.add_button("Clear Filters", function() {
			window.open("/app/query-report/Attendance%20Punch%20Error%20Report", "_self")
		}).addClass("btn-info");

		report.page.add_button("Generate", function() {
			// var date = frappe.query_report.get_filter_value('attendance_date');
			var employeeId = frappe.query_report.get_filter_value('employee');
			if (employeeId){
				frappe.query_report.set_filter_value({
					// "date": date,
					"employee": employeeId
				});
			}
		}).addClass("btn-primary");

		report.page.add_inner_button(__("Mark as Attendance"), function () {
			// Select the checked checkbox inside the datatable
			let checkedBox = document.querySelector('.dt-cell input[type="checkbox"]:checked');
		
			if (!checkedBox) {
				frappe.msgprint(__("Please select at least one row."));
				return false;
			}
		
			// Get the data-row-index from the closest dt-cell div
			let selectedCell = checkedBox.closest('.dt-cell');
			
			if (!selectedCell) {
				frappe.msgprint(__("Unable to identify the selected row."));
				return false;
			}
		
			// Get the row index from data attribute
			let selectedRowIndex = selectedCell.getAttribute('data-row-index');
		
			if (selectedRowIndex === null) {
				frappe.msgprint(__("Could not fetch the selected row's index."));
				return false;
			}
		
			// Fetch the selected row data using the row index
			let selectedRowData = report.data[selectedRowIndex];
		
			if (!selectedRowData) {
				frappe.msgprint(__("Unable to fetch data for the selected row."));
				return false;
			}
			
			console.log(checkedBox, selectedCell, selectedRowIndex, selectedRowData);
			
			// Open the Manual Punch form with the selected row's data
			frappe.new_doc("Manual Punch", {
				doctype: "Manual Punch",
				error_date: selectedRowData.attendance_date,
				employee: selectedRowData.employee
			});
		}).addClass("btn-second");		
		document.addEventListener("change", function (event) {
            if (event.target.matches('.dt-cell input[type="checkbox"]')) {
                document.querySelectorAll('.dt-cell input[type="checkbox"]').forEach(checkbox => {
                    if (checkbox !== event.target) {
                        checkbox.checked = false;
                    }
                });
            }
        });		
	},
	get_datatable_options(options) {
		console.log(options);
		
        return Object.assign(options, {
            checkboxColumn: true
        });
    }
};	

