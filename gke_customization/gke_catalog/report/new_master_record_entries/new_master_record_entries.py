# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt
# File: your_app/your_module/report/daily_master_changes_report/daily_master_changes_report.py

import frappe
from frappe import _
from datetime import datetime

def execute(filters=None):
    columns = get_columns()
    data = []


#    remaining doctypes to add- Territory, Supplier Group, Employee On Boarding Template, 
# Job Offer Template, Ticket Type, Agent, Team, Metal Type, Metal Colour, SLA

    doctypes = [
        "Item", "BOM", "Customer", "Supplier", "Warehouse", "Territory", "Company", "Supplier Group",
        "Contact", "Address", "Department", "Branch", "Designation", "Employee", "Employee Grade",
        "Employee Group", "Employee Onboarding Template", "Employee Skill", "Shift Type",
        "Interview Type", "Interview Round", "Holiday List", "Leave Type",
        "Leave Policy", "Item Group", "Asset", "Asset Category", "Loan Product", "Item Attribute",
        "Attribute Value", "UOM", "HD Ticket Type", "HD Agent", "HD Team", "Cost Center", "Bank Account",
        "Price List", "Item Price", "Grievance Type", "Leave Allocation", "Sales Person", "Sales Partner",
        "Location", "Salary Component", "Salary Structure", "Project",
        "Issue Type"
    ]

    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    selected_doctypes = filters.get("selected_doctypes") or doctypes

    for dt in doctypes:
        if dt not in selected_doctypes:

            continue
        entries = frappe.get_all(dt,
            filters={"creation": ["between", [from_date, to_date]]},
            fields=["name", "creation", "owner", "modified_by"]
        )
        for row in entries:
            key_info = get_key_field_value(dt, row.name)
            data.append({
                "doctype": dt,
                "name": f'<a href="/app/{dt.lower().replace(" ", "-")}/{row.name}" target="_blank">{row.name}</a>',
                "key_field": key_info,
                "creation": row.creation,
                "owner": row.owner,
                "modified_by": row.modified_by or ""
            })

    return columns, data

def get_columns():
    return [
        {"label": _("Doctype"), "fieldname": "doctype", "fieldtype": "Data", "width": 120},
        # {"label": _("Document Name"), "fieldname": "name", "fieldtype": "Link", "options": "doctype", "width": 150},
        {"label": _("Document Name"), "fieldname": "name", "fieldtype": "Data", "width": 180},
        {"label": _("Key Info"), "fieldname": "key_field", "fieldtype": "Data", "width": 200},
        {"label": _("Created On"), "fieldname": "creation", "fieldtype": "Datetime", "width": 180},
        {"label": _("Created By"), "fieldname": "owner", "fieldtype": "Data", "width": 180},
        # {"label": _("Modified By"), "fieldname": "modified_by", "fieldtype": "Data", "width": 180},
    ]

def get_key_field_value(doctype, name):
    key_fields = {
        "Item": "item_name",
        "Customer": "customer_name",
        "Supplier": "supplier_name",
        "Employee": "employee_name",
        "Department": "department_name",
        "Designation": "designation_name",
        "Branch": "branch",
        "Warehouse": "warehouse_name",
        "Item Group": "item_group_name",
        "BOM": "item",
        "Company": "company_name",
        "Contact": "first_name",
        "Address": "address_title",
        "Employee Grade": "name",
        "Employee Group": "name",
        "Employee Onboarding Template": "name",
        "Employee Skill": "skill_name",
        "Shift Type": "name",
        "Interview Type": "name",
        "Interview Round": "name",
        "Holiday List": "name",
        "Leave Type": "name",
        "Leave Policy": "name",
        "Asset": "asset_name",
        "Asset Category": "name",
        "Loan Product": "loan_name",
        "Item Attribute": "attribute_name",
        "Attribute Value": "name",
        "UOM": "uom_name",
        "HD Ticket Type": "name",
        "HD Agent": "name",
        "HD Team": "name",
        "Cost Center": "cost_center_name",
        "Bank Account": "account_name",
        "Price List": "price_list_name",
        "Item Price": "name",
        "Grievance Type": "name",
        "Leave Allocation": "name",
        "Sales Person": "sales_person_name",
        "Sales Partner": "partner_name",
        "Location": "location_name",
        "Salary Component": "salary_component",
        "Salary Structure": "name",
        "Project": "project_name",
        "Issue Type": "issue_type",
        "Territory": "territory_name",
        "Supplier Group": "supplier_group_name"
    }
    field = key_fields.get(doctype)
    if field:
        return frappe.db.get_value(doctype, name, field)
    return ""

