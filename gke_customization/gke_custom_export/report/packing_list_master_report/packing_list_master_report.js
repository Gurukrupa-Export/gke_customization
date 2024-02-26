// Copyright (c) 2023, gurukrupa_export] and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Packing List Master Report"] = {
	"filters": [		
		{
			"label": __("Sales Order"),
			"fieldname": "salesOrder",
			"fieldtype": "MultiSelectList",
			get_data: function(txt) {
				var filters = get_filter_dict(frappe.query_report)
				if (!filters) filters = {}
				return frappe.db.get_link_options('Sales Order', txt, filters);
			},
			"on_change": function(query_report){
				var emp_list = query_report.get_filter_value('salesOrder')
				query_report.current_emp = 0
				query_report.emp_count = emp_list.length
				set_salesOrder(query_report, query_report.current_emp)
			},
		},
		{
			"label": __("Selected Sales Order"),
			"fieldtype": "Link",
			"fieldname": "cur_sales_order",
			"options": "Sales Order",
			"get_query": function() {
				var salesOrder_list = frappe.query_report.get_filter_value('salesOrder')
				return {
					"doctype": "Sales Order",
					"filters": {"name":["in",salesOrder_list]}
				}
			},
			"on_change": function(query_report){
				let emp =  frappe.query_report.get_filter_value('cur_sales_order');
				let employees = query_report.get_filter_value('salesOrder')
				var idx = employees.indexOf(emp)
				if (idx>0) {
					query_report.current_emp = idx
				}
				set_salesOrder_details(query_report)
			},

		},
		{
			"label": __("Sales Order"),
			"fieldtype": "Link",
			"fieldname": "sales_order",
			"options": "Sales Order",
			"hidden": 1,
			"get_query": function() {
				var filters = get_filter_dict(frappe.query_report)
				if (!filters) return
				return {
					"doctype": "Sales Order",
					"filters": filters
				}
			}
		},
		{
			"label": __("Customer Name"),
			"fieldtype": "Data",
			"fieldname": "customer_name",
			"read_only": 1
		},
		{
			"label": __("Customer Address"),
			"fieldtype": "Data",
			"fieldname": "customer_address",
			"read_only": 1
		},
		{
			"label": __("Customer"),
			"fieldtype": "Link",
			"fieldname": "customer",
			"options":"Customer",
			"on_change": fetch_salesOrder
		},
		{
			"label": __("Date"),
			"fieldtype": "Date",
			"fieldname": "date",
			// "default": frappe.datetime.get_today(),
		},
		{
			"label": __("Prev"),
			"fieldtype": "Button",
			"fieldname": "prev",
			"depends_on": "eval:(frappe.query_report.emp_count>1 && frappe.query_report.current_emp != 0)",
			"onclick": function() {
				var prev_emp = (frappe.query_report.current_emp - 1)
				set_salesOrder(frappe.query_report, prev_emp, true)
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
				set_salesOrder(frappe.query_report, next_emp, true)
				if (next_emp > frappe.query_report.emp_count) next_emp = frappe.query_report.emp_count - 1
				frappe.query_report.current_emp = next_emp
			}
		},

		
	],
	onload: (report) => {
		report.page.add_button("Clear Filters", function() {
			window.open("/app/query-report/Packing%20List%20Master%20Report", "_self")
		}).addClass("btn-info")
		report.page.add_button("Generate", function() {
			var emp = frappe.query_report.get_filter_value('cur_sales_order');
			var date = frappe.query_report.get_filter_value('date');
			// var customer_name = frappe.query_report.get_filter_value('customer_name');
			frappe.query_report.set_filter_value({
				"sales_order": emp,
				"date":date,
				// "customer_name":customer_name
			});
			// else {
			// }
		}).addClass("btn-primary")
		fetch_salesOrder(report)
	}
};

function set_salesOrder(query_report, index, preset = false) {
	var salesOrder = query_report.get_filter_value('salesOrder')
	query_report.set_filter_value({
		"cur_sales_order": salesOrder[index] || null,
		"sales_order": preset ? salesOrder[index] : null
	});
	console.log(salesOrder)
}

function set_salesOrder_details(query_report) {
	var sales_order_detail = query_report.get_filter_value('cur_sales_order');
	frappe.db.get_value("Sales Order", sales_order_detail, ["customer_name", "customer_address", ], (r)=> {
		query_report.set_filter_value({
			"customer_name": r.customer_name,
			"customer_address": r.customer_address,
		});
	})
	console.log(sales_order_detail);
}

function fetch_salesOrder(query_report){
	var filters = get_filter_dict(query_report)
	console.log(filters)
	if (filters){
		frappe.db.get_list("Sales Order",{"filters" : filters, "pluck":"name", "order_by":"creation DESC"}).then((r)=>{
			query_report.set_filter_value("salesOrder",r)
			if (r.length != 0) {
				query_report.current_emp = 0
				query_report.emp_count = r.length
				set_salesOrder(query_report, query_report.current_emp)
			}
			else {
				query_report.set_filter_value({
					"sales_order": null
				});		
			}
		})
	}
	else {
		query_report.emp_count = 0
		query_report.set_filter_value({
			"sales_order": null,
			"salesOrder":[],
			"cur_sales_order": null,
			"customer_name": null,
			"customer_address": null
		});
	}
}

function get_filter_dict(query_report) {
	var customerName = query_report.get_filter_value('customer');
	
	var filters = {}
	console.log(customerName);

	if (customerName) {
		filters['customer'] = customerName
	}
	// else if (customerName) {
	// 	filters['customer'] = customerName
	// }
	else {
		return null
	}
	console.log(filters);
	return filters
}

// function fetch_sales_order(query_report) {
// 	var filters = get_filter_dict(query_report)
// 	if (filters){
// 		frappe.db.get_list("Sales Order",{"filters" : filters, "pluck":"name", "order_by":"creation DESC"}).then((r)=>{
// 			query_report.set_filter_value("salesOrder",r)
// 			if (r.length != 0) {
// 				query_report.cur_sales_order = 0
// 				query_report.emp_count = r.length
// 				set_employee(query_report, query_report.cur_sales_order)
// 			}
// 			else {
// 				query_report.set_filter_value({
// 					"sales_order": null
// 				});		
// 			}
// 		})
// 	}
// 	else {
// 		query_report.emp_count = 0
// 		query_report.set_filter_value({
// 			"sales_order": null,
// 			"salesOrder":[],
// 			"cur_sales_order": null,
// 		});
// 	}
// }