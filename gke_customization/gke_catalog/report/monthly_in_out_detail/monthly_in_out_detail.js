// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Monthly In-Out Detail"] = {
    "filters": [
        {
            "label": __("Month"),
            "fieldtype": "Select",
            "fieldname": "month",
            "reqd": 1,
            "options": [],
            "default": function() {
                const dateObject = new Date();
                const options = { month: "short", year: "numeric" };
                return dateObject.toLocaleDateString("en-US", options); // "Jan 2026"
            },
            "on_change": function(query_report) {
                var _month = query_report.get_filter_value('month');
                console.log("Selected month:", _month);
                if (!_month) return;
                
                let monthMoment = moment(_month, "MMM YYYY");
                if (!monthMoment.isValid()) {
                    console.error("Invalid month format:", _month);
                    return;
                }
                
                let firstDayOfMonth = monthMoment.clone().startOf('month').format(frappe.datetime.DEFAULT_DATE_FORMAT);
                let lastDayOfMonth = monthMoment.clone().endOf('month').format(frappe.datetime.DEFAULT_DATE_FORMAT);
                
                console.log("Setting dates:", firstDayOfMonth, "to", lastDayOfMonth);
                
                query_report.set_filter_value({
                    "from_date": firstDayOfMonth,
                    "to_date": lastDayOfMonth
                });
            }
        },
        {
            "label": __("From Date"),
            "fieldtype": "Date",
            "fieldname": "from_date",
            "read_only": 1,
            "default": frappe.datetime.month_start(),
            "width": "120px"
        },
        {
            "label": __("To Date"),
            "fieldtype": "Date",
            "fieldname": "to_date",
            "reqd": 1,
            "read_only": 1,
            "default": frappe.datetime.month_end(),
            "width": "120px"
        },
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1,
            "width": "200px"
        },
        {
            "fieldname": "department",
            "label": __("Department"),
            "fieldtype": "Link",
            "options": "Department",
            "reqd": 1,
            "get_query": function() {
                var company = frappe.query_report.get_filter_value('company');
                return {
                    "filters": { "company": company || undefined }
                };
            },
            "width": "200px"
        },
        {
            "fieldname": "branch",
            "label": __("Branch"),
            "fieldtype": "Link",
            "options": "Branch",
            "get_query": function() {
                var company = frappe.query_report.get_filter_value('company');
                return {
                    "filters": { "company": company || undefined }
                };
            },
            "width": "200px"
        },
        {
            "fieldname": "employee",
            "label": __("Employee"),
            "fieldtype": "Link",
            "options": "Employee",
            "get_query": function() {
                var company = frappe.query_report.get_filter_value('company');
                var department = frappe.query_report.get_filter_value('department');
                var filters = { "status": "Active" };
                if (company) filters.company = company;
                if (department) filters.department = department;
                return { "filters": filters };
            },
            "width": "200px"
        }
    ],
    
    "onload": function(report) {
        fetch_month_list();
    }
};

// ✅ COMPLETE 24 MONTHS ACROSS 3 YEARS (2024, 2025, 2026)
function fetch_month_list() {
    var options = [];
    
    // 2024 - All 12 months
    for (var month = 0; month < 12; month++) {
        var date = new Date(2024, month, 1);
        options.push(date.toLocaleDateString("en-US", { month: "short", year: "numeric" }));
    }
    
    // 2025 - All 12 months  
    for (var month = 0; month < 12; month++) {
        var date = new Date(2025, month, 1);
        options.push(date.toLocaleDateString("en-US", { month: "short", year: "numeric" }));
    }
    
    // 2026 - All 12 months (ADDED!)
    for (var month = 0; month < 12; month++) {
        var date = new Date(2026, month, 1);
        options.push(date.toLocaleDateString("en-US", { month: "short", year: "numeric" }));
    }
    
    var monthFilter = frappe.query_report.get_filter('month');
    monthFilter.df.options = options;
    monthFilter.refresh();
}
