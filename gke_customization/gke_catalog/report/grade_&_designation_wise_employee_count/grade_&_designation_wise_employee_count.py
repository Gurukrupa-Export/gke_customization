# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import re

def execute(filters=None):
    filters = filters or {}
    columns = get_columns(filters)
    data = get_data(filters)
    message = get_message()

    total_employees = len(data)
    unique_designations = len(set(row["designation"] for row in data if row.get("designation")))
    
    return columns, data, message



def get_columns(filters=None):
	has_filters = any(filters.get(key) for key in ["company", "branch", "department", "designation", "manufacturer", "operation"])


	# Base columns
	columns = [
		{ "label": _("Grade"), "fieldname": "grade", "fieldtype": "Data", "width": 90 },
	]

	# Show Designation Count only if NO filters are applied
	if not has_filters:
		columns.append({ "label": _("Employees Count"), "fieldname": "emp_count", "fieldtype": "Data", "width": 160 })

	columns.append({
		"label": _("Designation"),
		"fieldname": "designation",
		"fieldtype": "Data",
		"width": 3020 if not has_filters else 320,
	})

	# Add extra detail columns if filters are applied
	if has_filters:
		columns += [
			{ "label": _("Department"), "fieldname": "department", "fieldtype": "Data", "width": 300 },
			{ "label": _("Manufacturer"), "fieldname": "manufacturer", "fieldtype": "Data", "width": 125 },
			{ "label": _("Operation"), "fieldname": "operation", "fieldtype": "Data", "width": 200 },
			{ "label": _("Employee Count"), "fieldname": "count", "fieldtype": "Data", "width": 150 },
		]

	return columns



def natural_key(text):
    """Sort helper to apply natural order like RL-1, RL-2, RL-10"""
    return [int(s) if s.isdigit() else s.lower() for s in re.split(r'(\d+)', text or '')]

def get_data(filters=None):
    conditions = get_conditions(filters)
    has_filters = any(filters.get(key) for key in ["company", "branch", "department", "designation", "manufacturer", "operation"])
    
    if has_filters:
        query = f"""
            SELECT 
                department as department,
                CASE WHEN manufacturer IS NOT NULL THEN manufacturer ELSE '-' END AS manufacturer,
                CASE WHEN custom_operation IS NOT NULL THEN custom_operation ELSE '-' END AS operation,
                grade,
                designation,
                COUNT(name) AS count
            FROM `tabEmployee`
            WHERE status = 'Active' AND relieving_date IS NULL
            {conditions}
            GROUP BY grade, designation, manufacturer, custom_operation
            ORDER BY designation, manufacturer, custom_operation
        """
    else:
        query = f"""
            SELECT 
                grade,
                GROUP_CONCAT(DISTINCT designation ORDER BY designation SEPARATOR ',  ') AS designation,
                COUNT(name) AS emp_count
            FROM `tabEmployee`
            WHERE status = 'Active' AND relieving_date IS NULL
            {conditions}
            GROUP BY grade
            ORDER BY grade
        """
    
    data = frappe.db.sql(query, as_dict=1)
    data.sort(key=lambda d: natural_key(d.get("grade")))
    return data




# ORDER BY company, branch, department, designation

def get_conditions(filters):
    filter_list = []
    
    if filters.get("company"):
       filter_list.append(f'''company = "{filters.get("company")}" ''')
    
    if filters.get("branch"):
        branchs = ', '.join([f'"{branch}"' for branch in filters.get("branch")])
        filter_list.append(f"""branch IN ({branchs})""")

    if filters.get("department"):
        departments = ', '.join([f'"{department}"' for department in filters.get("department")])
        filter_list.append(f"""department IN ({departments})""")
    if filters.get("designation"):
        departments = ', '.join([f'"{designation}"' for designation in filters.get("designation")])
        filter_list.append(f"""designation IN ({departments})""")
    if filters.get("manufacturer"):
       filter_list.append(f'''manufacturer = "{filters.get("manufacturer")}" ''')

    if filters.get("operation"):
        operations = ', '.join([f'"{operation}"' for operation in filters.get("operation")])
        filter_list.append(f"""custom_operation IN ({operations})""")

    # if filters.get("operation"):
    #    filter_list.append(f'''custom_operation = "{filters.get("operation")}" ''')

    conditions = ""
    if filter_list:
        conditions = "AND " + " AND ".join(filter_list)

    return conditions


def get_message():
    return """<span class="indicator" style="font-weight: bold; font-size: 15px;">
        Note : &nbsp;&nbsp;
        </span>
        <span class="indicator red" style="font-size: 15px;">
      Manufacturer and Operation linked only to Designation: Artist (Worker)
        </span>
"""






