frappe.query_reports["Lender Loan Repayment Summary"] = {
    "filters": [
		{
            "fieldname": "name",
            "label": "Unsecured Loan ID",
            "fieldtype": "Link",
            "options": "Unsecured Loan",
            "default": "",
        },
        {
            "fieldname": "lender",
            "label": "Lender",
            "fieldtype": "Link",
            "options": "Business Partner",  // or "Lender" if custom Doctype
            "reqd": 1
        },
		{
            "fieldname": "from_date",
            "label": "From Date",
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)
        },
        {
            "fieldname": "to_date",
            "label": "To Date",
            "fieldtype": "Date",
            "default": frappe.datetime.get_today()
        }
    ]
};
