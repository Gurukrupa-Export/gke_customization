// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["Waxset and gold set diamond issue report"] = {
	filters: [
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date",
            reqd: 0,
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1)
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            reqd: 0,
            default: frappe.datetime.get_today()
        },
        {
            fieldname: "manufacturing_work_order",
            label: "Manufacturing Work Order",
            fieldtype: "Link",
            options: "Manufacturing Work Order",
            reqd: 0
        },
        {
            fieldname: "serial_no",
            label: "Serial No",
            fieldtype: "Link",
            options: "Serial No",
            reqd: 0
        },
        {
            fieldname: "item_category",
            label: "Item Category",
            fieldtype: "Data",
            reqd: 0
        }
    ]
};