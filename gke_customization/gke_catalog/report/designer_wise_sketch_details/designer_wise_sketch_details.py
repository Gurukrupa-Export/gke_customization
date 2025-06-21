
import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data



def get_columns(filters=None):
	columns = [
		{"label": "Designer Name", "fieldname": "designer_name", "fieldtype": "Data", "width": 200},
		{"label": "Category", "fieldname": "category", "fieldtype": "Data", "width": 100},
		{"label": "Sub Category", "fieldname": "subcategory", "fieldtype": "Data", "width": 170},
		{"label": "Assign Qty ", "fieldname": "assign_qty", "fieldtype": "Data", "width": 100},
        {"label": "Rough Sketch Approved", "fieldname": "ra", "fieldtype": "Int", "width": 200},
        {"label": "RSA %", "fieldname": "ra_percent", "fieldtype": "Data", "width": 80},
        {"label": "Rough Sketch Rejected", "fieldname": "rr", "fieldtype": "Int", "width": 180},
		{"label": "RSR %", "fieldname": "rr_percent", "fieldtype": "Data", "width": 80},
        {"label": "Final Sketch Approved", "fieldname": "fa", "fieldtype": "Int", "width": 180},
		{"label": "FSA %", "fieldname": "fa_percent", "fieldtype": "Data", "width": 80},
        {"label": "Final Sketch Rejected", "fieldname": "fr", "fieldtype": "Int", "width": 180},
		{"label": "FSR %", "fieldname": "fr_percent", "fieldtype": "Data", "width": 80},
		# {"label": "Total", "fieldname": "total", "fieldtype": "Int", "width": 160},
	]
	return columns

def get_data(filters=None):
	conditions = get_conditions(filters)

	query =  f"""
        SELECT 
            ds.designer_name AS designer_name,
			o.category AS category,
			o.subcategory as subcategory,
			SUM(ds.count_1) AS assign_qty,
            COALESCE(rsa_summary.ra, 0) AS ra,
            COALESCE(rsa_summary.rr, 0) AS rr,
            COALESCE(fsa_summary.fa, 0) AS fa,
            COALESCE(fsa_summary.fr, 0) AS fr,
			CONCAT(ROUND((COALESCE(rsa_summary.ra, 0) / NULLIF(SUM(ds.count_1), 0)) * 100, 2), ' %') AS ra_percent,
            CONCAT(ROUND((COALESCE(rsa_summary.rr, 0) / NULLIF(SUM(ds.count_1), 0)) * 100, 2), ' %') AS rr_percent,
            CONCAT(ROUND((COALESCE(fsa_summary.fa, 0) / NULLIF(COALESCE(rsa_summary.ra, 0), 0)) * 100, 2), ' %') AS fa_percent,
            CONCAT(ROUND((COALESCE(fsa_summary.fr, 0) / NULLIF(COALESCE(rsa_summary.ra, 0), 0)) * 100, 2), ' %') AS fr_percent
        FROM 
            `tabDesigner Assignment` ds
        LEFT JOIN `tabSketch Order` o ON o.name = ds.parent
		LEFT JOIN `tabEmployee` e ON e.name = ds.designer
        LEFT JOIN (
    SELECT 
        r.designer, 
        o.category,
		o.subcategory,
        SUM(r.approved) AS ra, 
        SUM(r.reject) AS rr
    FROM `tabRough Sketch Approval` r
    LEFT JOIN `tabSketch Order` o ON o.name = r.parent
    GROUP BY r.designer, o.category,o.subcategory
) rsa_summary ON rsa_summary.designer = ds.designer AND rsa_summary.category = o.category AND rsa_summary.subcategory = o.subcategory
        LEFT JOIN (
    SELECT 
        f.designer, 
        o.category,
		o.subcategory,
        SUM(f.approved) AS fa, 
        SUM(f.reject) AS fr
    FROM `tabFinal Sketch Approval HOD` f
    LEFT JOIN `tabSketch Order` o ON o.name = f.parent
    GROUP BY f.designer, o.category,o.subcategory
) fsa_summary ON fsa_summary.designer = ds.designer AND fsa_summary.category = o.category AND fsa_summary.subcategory = o.subcategory
		WHERE {conditions}
        GROUP BY ds.designer_name,o.category,o.subcategory
        ORDER BY ds.designer_name,o.category,o.subcategory

"""  

	data = frappe.db.sql(query, as_dict=1)
	for row in data:
		row["total"] = (row.get("ra", 0) or 0) + (row.get("rr", 0) or 0) + (row.get("fa", 0) or 0) + (row.get("fr", 0) or 0)

	return data

def get_conditions(filters):
	conditions =[]

	if filters.get("company"):
		conditions.append(f'''o.company = "{filters.get("company")}" ''')
		
	if filters.get("branch"):
		# conditions.append(f'''e.branch = "{filters.get("branch")}" ''')		
		branch = ', '.join([f'"{branch}"' for branch in filters.get("branch")])
		conditions.append(f"e.branch IN ({branch})")	
			
	if filters.get("year"):
		conditions.append(f"""Year(o.order_date) = "{filters['year']}" """)	
	if filters.get("from_date"):
		conditions.append(f"""Date(o.order_date) >= "{filters['from_date']}" """)
	if filters.get("to_date"):
		conditions.append(f"""Date(o.order_date) <= "{filters['to_date']}" """)	
	# if filters.get("category"):
	# 	conditions.append(f'''o.category = "{filters.get("category")}" ''')
	if filters.get("designer"):
		conditions.append(f'''ds.designer = "{filters.get("designer")}" ''')   
	if filters.get("category"):
		category = ', '.join([f'"{category}"' for category in filters.get("category")])
		conditions.append(f"o.category IN ({category})")
	if conditions:
		conditions = " AND ".join(conditions)
	else:
		conditions = " "

	return conditions
