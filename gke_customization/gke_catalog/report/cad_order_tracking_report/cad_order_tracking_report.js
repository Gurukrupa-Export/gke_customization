frappe.query_reports["CAD Order Tracking Report"] = {
    "filters": [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_days(frappe.datetime.get_today(), -7),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "bom_or_cad",
            "label": __("BOM or CAD"),
            "fieldtype": "Select",
            "options": "\nBOM\nCAD",
            "default": "CAD"
        },
        {
            "fieldname": "order_number",
            "label": __("Order Number"),
            "fieldtype": "Link",
            "options": "Order",
            "get_query": function() {
                let bom_or_cad = frappe.query_report.get_filter_value('bom_or_cad');
                let filters = {"docstatus": ["<", 2]};
                
                if (bom_or_cad) {
                    filters["bom_or_cad"] = bom_or_cad;
                }
                
                return {"filters": filters};
            }
        },
        {
            "fieldname": "branch",
            "label": __("Branch"),
            "fieldtype": "Link",
            "options": "Branch"
        },
        {
            "fieldname": "category",
            "label": __("Category"),
            "fieldtype": "Data"
        },
        {
            "fieldname": "designer",
            "label": __("Designer"),
            "fieldtype": "Link",
            "options": "Employee",
            "get_query": function() {
                return {
                    "filters": {
                        "status": "Active"
                    }
                };
            }
        },
        {
            "fieldname": "workflow_state",
            "label": __("Workflow State"),
            "fieldtype": "Select",
            "options": "\nDraft\nAssigned\nIn Progress\nQC\nApproved\nRejected"
        }
    ],
    
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        // Highlight overdue orders
        if (column.fieldname == "delivery_date" && data.delivery_date) {
            try {
                let due_date = frappe.datetime.str_to_obj(data.delivery_date);
                let today = frappe.datetime.now_date(true);
                
                if (due_date < today && !data.update_item_date_time) {
                    value = `<span style="color: red; font-weight: bold;">${value}</span>`;
                }
            } catch(e) {
                // If date parsing fails, just return value as is
            }
        }
        
        // Highlight pending approvals
        if (column.fieldname == "customer_approval_date_time" && 
            data.send_to_qc_date_time && !data.customer_approval_date_time) {
            value = `<span style="color: orange;">Pending</span>`;
        }
        
        return value;
    },
    
    "onload": function(report) {
        // Show performance message after report loads
        report.page.on("render", function() {
            let data_length = report.data ? report.data.length : 0;
            if (data_length >= 200) {
                frappe.show_alert({
                    message: __("Showing {0} records. Use filters to narrow down results for better performance.", [data_length]),
                    indicator: "orange"
                }, 7);
            }
        });
        
        // Date range validation
        let validate_dates = function() {
            let from_date = report.get_filter_value("from_date");
            let to_date = report.get_filter_value("to_date");
            
            if (from_date && to_date) {
                let diff = frappe.datetime.get_day_diff(to_date, from_date);
                
                if (diff > 90) {
                    frappe.msgprint({
                        title: __("Large Date Range"),
                        message: __("Date range exceeds 90 days. For better performance, please select a shorter date range or use additional filters like Branch, Category, or Designer."),
                        indicator: "orange"
                    });
                }
            }
        };
        
        // Trigger validation on date change
        setTimeout(function() {
            $("[data-fieldname='from_date'], [data-fieldname='to_date']").on("change", validate_dates);
        }, 500);
    }
};
