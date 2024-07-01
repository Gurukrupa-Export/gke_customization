// Copyright (c) 2024, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Employee Variable Payment"] = {
	"filters": [
		{
			"label": __("Department"),
			"fieldtype": "MultiSelectList",
			"fieldname": "department",
			get_data: function(txt) {
				var filters = {}
				return frappe.db.get_link_options('Department', txt, filters);
			},
			"on_change": fetch_employees
		},
		{
			"label": __("Employees"),
			"fieldname": "employees",
			"fieldtype": "MultiSelectList",
			get_data: function(txt) {
				var filters = get_filter_dict(frappe.query_report);
				if (!filters) filters = {}
				return frappe.db.get_link_options('Employee', txt, filters);
			},
			"on_change": function(query_report){
				var emp_list = query_report.get_filter_value('employees')
				query_report.current_emp = 0
				query_report.emp_count = emp_list.length
				set_employee(query_report, query_report.current_emp)
			},
		},
		{
			"label": __("Selected Employee"),
			"fieldtype": "Link",
			"fieldname": "cur_employee",
			"options": "Employee",
			"get_query": function() {
				var emp_list = frappe.query_report.get_filter_value('employees')
				return {
					"doctype": "Employee",
					"filters": {"employee":["in",emp_list]}
				}
			},
			"on_change": function(query_report){
				let emp =  frappe.query_report.get_filter_value('cur_employee');
				let employees = query_report.get_filter_value('employees')
				var idx = employees.indexOf(emp)
				if (idx>0) {
					query_report.current_emp = idx
				}
				set_employee_details(query_report)
			},
		},
		{
			"label": __("Employee"),
			"fieldtype": "Link",
			"fieldname": "employee",
			"options": "Employee",
			"reqd": 1,
			"hidden": 1,
			"get_query": function() {
				var filters = get_filter_dict(frappe.query_report)
				if (!filters) return
				return {
					"doctype": "Employee",
					"filters": filters
				}
			}
		},
		{
			"label":"Employee Name",
			"fieldtype": "Data",
			"fieldname": "emp_name",
			"read_only": 1
		},
		{
			"label":"Employee Designation",
			"fieldtype": "Data",
			"fieldname": "designation",
			"read_only": 1
		},
		{
			"label":"Department Name",
			"fieldtype": "Data",
			"fieldname": "emp_department",
			"read_only": 1
		},
		{
			"label":"Variable Start Date",
			"fieldtype": "Date",
			"fieldname": "contract_start_date",
			"read_only": 1
		},
		{
			"label":"Variable End Date",
			"fieldtype": "Date",
			"fieldname": "contract_end_date",
			"read_only": 1
		},
		{
			"label": __("Prev"),
			"fieldtype": "Button",
			"fieldname": "prev",
			"depends_on": "eval:(frappe.query_report.emp_count>1 && frappe.query_report.current_emp != 0)",
			"onclick": function() {
				var prev_emp = (frappe.query_report.current_emp - 1)
				set_employee(frappe.query_report, prev_emp, true)
				if (prev_emp < 0) prev_emp = 0
				frappe.query_report.current_emp = prev_emp
			}
		},
		{
			"label": __("Next"),
			"fieldtype": "Button",
			"fieldname": "next",
			"width": "80",
			"depends_on": "eval:(frappe.query_report.emp_count>1 && frappe.query_report.emp_count - 1 > frappe.query_report.current_emp)",
			"onclick": function() {
				var next_emp = (frappe.query_report.current_emp + 1)
				set_employee(frappe.query_report, next_emp, true)
				if (next_emp > frappe.query_report.emp_count) next_emp = frappe.query_report.emp_count - 1
				frappe.query_report.current_emp = next_emp
			}
		},

	],
	onload: (report) => {
		
		report.page.add_button("Clear Filters", function() {
			window.open("/app/query-report/Employee%20Variable%20Payment", "_self")
		}).addClass("btn-info");

		report.page.add_button("Generate", function() {
			var emp = frappe.query_report.get_filter_value('cur_employee');
			if (!emp) {
				frappe.msgprint("No Employee Selected")
			}
			else {
				frappe.query_report.set_filter_value({
					"employee": emp
				});
			}
		}).addClass("btn-primary");
	}
};

function set_employee(query_report, index, preset = false) {
	var employees = query_report.get_filter_value('employees')
	query_report.set_filter_value({
		"cur_employee": employees[index] || null,
		"employee": preset ? employees[index] : null
	});
}

function set_employee_details(query_report) {
	var employee = query_report.get_filter_value('cur_employee');
	frappe.db.get_value("Employee", employee, ["employee_name", "department", "designation", "custom_contract_start_date", "custom_contract_end_date"], (r)=> {
		query_report.set_filter_value({
			"emp_name": r.employee_name,
			"designation": r.designation,
			"emp_department": r.department,
			"contract_start_date": r.custom_contract_start_date, 
			"contract_end_date": r.custom_contract_end_date, 
		}); 
	})
}

function fetch_employees(query_report) {
	var filters = get_filter_dict(query_report)
	if (filters){
		frappe.db.get_list("Employee",{"filters" : filters, "pluck":"name", "order_by":"name"}).then((r)=>{
			query_report.set_filter_value("employees",r)
			if (r.length != 0) {
				query_report.current_emp = 0
				query_report.emp_count = r.length
				set_employee(query_report, query_report.current_emp)
			}
			else {
				query_report.set_filter_value({
					"employee": null
				});		
			}
		})
	}
	else {
		query_report.emp_count = 0
		query_report.set_filter_value({
			"employee": null,
			"employees":[],
			"cur_employee": null,
			"emp_name": null,
			"designation": null,
			"emp_department": null, 
			"contract_start_date": null, 
			"contract_end_date": null, 
		});
	}
}

function get_filter_dict(query_report) {
	var company = query_report.get_filter_value('company');
	var department = query_report.get_filter_value('department');
	var filters = {}
	if (department.length > 0) { 
		filters['department'] = ['in',department]
	} 
	else if (department.length > 0) {
		filters['department'] = ['in',department]
	}
	else {
		return null
	}
	return filters
}