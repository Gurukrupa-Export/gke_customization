# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)  
    return columns, data

def get_columns():
    return [
        {"label": "Old Punch ID", "fieldname": "old_punch_id", "fieldtype": "Data"},
        {"label": "Emp ID", "fieldname": "employee", "fieldtype": "Data"},
        {"label": "Emp Name", "fieldname": "employee_name", "fieldtype": "Data"},
        {"label": "Department", "fieldname": "department", "fieldtype": "Data"},
        {"label": "Designation", "fieldname": "designation", "fieldtype": "Data"},
        {"label": "Company", "fieldname": "company", "fieldtype": "Data"},
        {"label": "Branch", "fieldname": "branch", "fieldtype": "Data"},
        {"label": "From Date", "fieldname": "start_date", "fieldtype": "Date"},
        {"label": "To Date", "fieldname": "end_date", "fieldtype": "Date"},
        {"label": "Created On", "fieldname": "posting_date", "fieldtype": "Date"},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data"},
        {"label": "Fix Gross Salary", "fieldname": "ctc", "fieldtype": "Currency"},
        {"label": "Gross Pay", "fieldname": "gross_pay", "fieldtype": "Currency"},
        {"label": "Net Pay", "fieldname": "net_pay", "fieldtype": "Currency"},
        {"label": "Bank Name", "fieldname": "bank_name", "fieldtype": "Data"},
        {"label": "Bank Account No", "fieldname": "bank_account_no", "fieldtype": "Data"},
        {"label": "Shift Work Hours", "fieldname": "shift_hours", "fieldtype": "Float"},
        {"label": "Actual Working Hours", "fieldname": "actual_working_hours", "fieldtype": "Float"},
        {"label": "Extra Working Hours", "fieldname": "extra_working_hours", "fieldtype": "Float"},
        {"label": "Target Working Hours", "fieldname": "target_working_hours", "fieldtype": "Float"},
        {"label": "Extra Payment Days", "fieldname": "custom_extra_payment_days", "fieldtype": "Float"},
        {"label": "Total Payment Days", "fieldname": "total_payment_days", "fieldtype": "Float"},
        {"label": "Product Incentive", "fieldname": "product_incentive", "fieldtype": "Currency"},
        {"label": "Basic", "fieldname": "basic", "fieldtype": "Currency"},
        {"label": "House Rent Allowance", "fieldname": "house_rent_allowance", "fieldtype": "Currency"},
        {"label": "Medical Allowance", "fieldname": "medical_allowance", "fieldtype": "Currency"},
        {"label": "Special Allowance", "fieldname": "special_allowance", "fieldtype": "Currency"},
        {"label": "Conveyance Allowance", "fieldname": "conveyance_allowance", "fieldtype": "Currency"},
        {"label": "Education Allowance", "fieldname": "education_allowance", "fieldtype": "Currency"},
        {"label": "Variable Pay", "fieldname": "variable_pay", "fieldtype": "Currency"},
        {"label": "Washing Allowance", "fieldname": "washing_allowance", "fieldtype": "Currency"},
        {"label": "Attire Allowance", "fieldname": "attire_allowance", "fieldtype": "Currency"},
        {"label": "Professional Tax", "fieldname": "professional_tax", "fieldtype": "Currency"},
        {"label": "Provident Fund", "fieldname": "provident_fund", "fieldtype": "Currency"},
        {"label": "Advance", "fieldname": "advance", "fieldtype": "Currency"},
        {"label": "Arrear", "fieldname": "arrear", "fieldtype": "Currency"},
        {"label": "Arrear Attire Allowance", "fieldname": "arrear_attire_allowance", "fieldtype": "Currency"},
        {"label": "Arrear Basic", "fieldname": "arrear_basic", "fieldtype": "Currency"},
        {"label": "Arrear Conveyance Allowance", "fieldname": "arrear_conveyance_allowance", "fieldtype": "Currency"},
        {"label": "Arrear Education Allowance", "fieldname": "arrear_education_allowance", "fieldtype": "Currency"},
        {"label": "Arrear Employee Loan", "fieldname": "arrear_employee_loan", "fieldtype": "Currency"},
        {"label": "Arrear House Rent Allowance", "fieldname": "arrear_house_rent_allowance", "fieldtype": "Currency"},
        {"label": "Arrear Labor Welfare Fund", "fieldname": "arrear_labor_welfare_fund", "fieldtype": "Currency"},
        {"label": "Arrear Medical Allowance", "fieldname": "arrear_medical_allowance", "fieldtype": "Currency"},
        {"label": "Arrear Product Incentive", "fieldname": "arrear_product_incentive", "fieldtype": "Currency"},
        {"label": "Arrear Professional Tax", "fieldname": "arrear_professional_tax", "fieldtype": "Currency"},
        {"label": "Arrear Special Allowance", "fieldname": "arrear_special_allowance", "fieldtype": "Currency"},
        {"label": "Arrear Variable Pay", "fieldname": "arrear_variable_pay", "fieldtype": "Currency"},
        {"label": "Arrear Washing Allowance", "fieldname": "arrear_washing_allowance", "fieldtype": "Currency"},
        {"label": "Base - Statistical", "fieldname": "base_statistical", "fieldtype": "Currency"},
        {"label": "Employee Loan", "fieldname": "employee_loan", "fieldtype": "Currency"},
        {"label": "Employees State Insurance Corporation", "fieldname": "employees_state_insurance_corporation", "fieldtype": "Currency"},
        {"label": "House Rent Allowance Statistical", "fieldname": "house_rent_allowance_statistical", "fieldtype": "Currency"},
        {"label": "Income Tax", "fieldname": "income_tax", "fieldtype": "Currency"},
        {"label": "Labor Welfare Fund", "fieldname": "labor_welfare_fund", "fieldtype": "Currency"},
        {"label": "Leave Encashment", "fieldname": "leave_encashment", "fieldtype": "Currency"},
        {"label": "Other Allowance", "fieldname": "other_allowance", "fieldtype": "Currency"},
        {"label": "Special Allowance - Statistical", "fieldname": "special_allowance_statistical", "fieldtype": "Currency"},
        {"label": "Washing Allowance New", "fieldname": "washing_allowance_new", "fieldtype": "Currency"}
    ]


def get_data(filters=None):
	conditions = get_conditions(filters)

	query =  f"""
SELECT 
    e.old_punch_id AS old_punch_id,
    ss.employee AS employee, 
    ss.employee_name AS employee_name, 
    ss.department AS department,
    ss.designation AS designation,
    ss.company AS company,
    ss.branch as branch,
    ss.start_date AS start_date, 
    ss.end_date AS end_date,
    ss.posting_date AS posting_date,
    ss.status AS status,
    CONCAT('₹ ', FORMAT(e.ctc, 2)) AS ctc,
    CONCAT('₹ ', FORMAT(ss.gross_pay, 2)) AS gross_pay,
    CONCAT('₹ ', FORMAT(ss.net_pay, 2)) AS net_pay,
    ss.bank_name AS bank_name,
    ss.bank_account_no AS bank_account_no,
    ss.shift_hours as shift_hours,
    ss.actual_working_hours as actual_working_hours,
    ss.extra_working_hours as extra_working_hours,
    ss.target_working_hours as target_working_hours,
    ss.custom_extra_payment_days AS custom_extra_payment_days,
    ROUND((ss.payment_days + (ss.extra_working_hours / ss.shift_hours)), 2) AS total_payment_days,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Product Incentive' THEN sd.amount ELSE 0 END), 2)) AS product_incentive,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Basic' THEN sd.amount ELSE 0 END), 2)) AS basic,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'House Rent Allowance' THEN sd.amount ELSE 0 END), 2)) AS house_rent_allowance,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Medical Allowance' THEN sd.amount ELSE 0 END), 2)) AS medical_allowance,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Special Allowance' THEN sd.amount ELSE 0 END), 2)) AS special_allowance,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Conveyance Allowance' THEN sd.amount ELSE 0 END), 2)) AS conveyance_allowance,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Education Allowance' THEN sd.amount ELSE 0 END), 2)) AS education_allowance,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Variable Pay' THEN sd.amount ELSE 0 END), 2)) AS variable_pay,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Washing Allowance' THEN sd.amount ELSE 0 END), 2)) AS washing_allowance,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Attire Allowance' THEN sd.amount ELSE 0 END), 2)) AS attire_allowance,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Professional Tax' THEN sd.amount ELSE 0 END), 2)) AS professional_tax,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Provident Fund' THEN sd.amount ELSE 0 END), 2)) AS provident_fund,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Advance' THEN sd.amount ELSE 0 END), 2)) AS advance,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Arrear' THEN sd.amount ELSE 0 END), 2)) AS arrear,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Arrear Attire Allowance' THEN sd.amount ELSE 0 END), 2)) AS arrear_attire_allowance,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Arrear Basic' THEN sd.amount ELSE 0 END), 2)) AS arrear_basic,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Arrear Conveyance Allowance' THEN sd.amount ELSE 0 END), 2)) AS arrear_conveyance_allowance,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Arrear Education Allowance' THEN sd.amount ELSE 0 END), 2)) AS arrear_education_allowance,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Arrear Employee Loan' THEN sd.amount ELSE 0 END), 2)) AS arrear_employee_loan,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Arrear House Rent Allowance' THEN sd.amount ELSE 0 END), 2)) AS arrear_house_rent_allowance,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Arrear Labor Welfare Fund' THEN sd.amount ELSE 0 END), 2)) AS arrear_labor_welfare_fund,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Arrear Medical Allowance' THEN sd.amount ELSE 0 END), 2)) AS arrear_medical_allowance,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Arrear Product Incentive' THEN sd.amount ELSE 0 END), 2)) AS arrear_product_incentive,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Arrear Professional Tax' THEN sd.amount ELSE 0 END), 2)) AS arrear_professional_tax,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Arrear Special Allowance' THEN sd.amount ELSE 0 END), 2)) AS arrear_special_allowance,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Arrear Variable Pay' THEN sd.amount ELSE 0 END), 2)) AS arrear_variable_pay,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Arrear Washing Allowance' THEN sd.amount ELSE 0 END), 2)) AS arrear_washing_allowance,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Base - Statistical' THEN sd.amount ELSE 0 END), 2)) AS base_statistical,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Employee Loan' THEN sd.amount ELSE 0 END), 2)) AS employee_loan,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Employees State Insurance Corporation' THEN sd.amount ELSE 0 END), 2)) AS employees_state_insurance_corporation,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'House Rent Allowance Statistical' THEN sd.amount ELSE 0 END), 2)) AS house_rent_allowance_statistical,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Income Tax' THEN sd.amount ELSE 0 END), 2)) AS income_tax,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Labor Welfare Fund' THEN sd.amount ELSE 0 END), 2)) AS labor_welfare_fund,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Leave Encashment' THEN sd.amount ELSE 0 END), 2)) AS leave_encashment,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Other Allowance' THEN sd.amount ELSE 0 END), 2)) AS other_allowance,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Special Allowance - Statistical' THEN sd.amount ELSE 0 END), 2)) AS special_allowance_statistical,
    CONCAT('₹ ', FORMAT(MAX(CASE WHEN sd.salary_component = 'Washing Allowance New' THEN sd.amount ELSE 0 END), 2)) AS washing_allowance_new
FROM 
    `tabSalary Slip` AS ss
JOIN 
    `tabSalary Detail` AS sd ON ss.name = sd.parent
LEFT JOIN 
    `tabEmployee` AS e ON ss.employee = e.employee
{conditions}
GROUP BY 
    e.old_punch_id,
    ss.employee, ss.employee_name, ss.department, ss.designation, 
    ss.company, ss.start_date, ss.end_date, ss.posting_date,
    ss.status, ss.gross_pay, ss.net_pay, ss.bank_name, ss.bank_account_no
ORDER BY 
    ss.posting_date DESC;


"""
	
	data = frappe.db.sql(query, as_dict=1)
	return data

def get_conditions(filters):
    filter_list = []
    if filters.get("from_date"):
        filter_list.append(f"""ss.start_date >= "{filters['from_date']}" """)
        
    if filters.get("to_date"):
        filter_list.append(f"""ss.end_date <= "{filters['to_date']}" """)
    
    if filters.get("company"):
       filter_list.append(f'''ss.company = "{filters.get("company")}" ''')

    if filters.get("branch"):
       filter_list.append(f'''ss.branch = "{filters.get("branch")}" ''')
       
    if filter_list:
        conditions = "WHERE " +  " AND ".join(filter_list)
    else:
        conditions = ""

    return conditions

