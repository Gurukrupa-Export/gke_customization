frappe.query_reports["26Q Report"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": "Company",
            "fieldtype": "Link",
            "options": "Company",
            "reqd": 1
        },
        {
            "fieldname": "financial_year",
            "label": "Financial Year",
            "fieldtype": "Link",
            "options": "Fiscal Year",
            "reqd": 1
        },
        {
            "fieldname": "quarter",
            "label": "Quarter",
            "fieldtype": "Select",
            "options": ["", "Q1", "Q2", "Q3", "Q4"],
            "reqd": 0
        },
        {
            "fieldname": "month",
            "label": "Month",
            "fieldtype": "Select",
            "options": [
                "",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December",
                "January",
                "February",
                "March"
            ],
            "reqd": 0
        }
    ]
};