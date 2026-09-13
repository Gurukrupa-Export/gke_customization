# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe

from .jewelex_db_config import JEWELEX_DB_CONFIG

JEWELEX_QUERY = """
SELECT  dbo.Batch_Master.Batch_No ,
        dbo.M_Category.Category_Name AS Category ,
        dbo.M_Sub_Category.Sub_Category_Name AS Sub_Category ,
        dbo.M_Design_Setting.DesignSetting_Name AS Setting ,
        dbo.Batch_Master.StyleBio ,
        dbo.M_Customer.Cust_Code AS Party_Code ,
        dbo.Batch_Master.Gold_Wt ,
        dbo.Batch_Master.Dia_Wt ,
        dbo.M_Metal.Metal_Type AS Metal_Type ,
        dbo.Batch_Master.Stone_Wt ,
        dbo.Batch_Master.Other_Wt ,
        dbo.Batch_Master.NetGross_Wt ,
		M_Department.Dept_Name AS Current_Dept ,
        dbo.Process_Master.Process_Name AS Current_Process ,
        dbo.Order_Detail.Bulk_Order_No ,
        dbo.Order_Master.Order_No ,
        dbo.Order_Master.Order_Date ,
        Order_Master.Due_date ,
        Order_Master.Order_Type
FROM    dbo.Batch_Master WITH ( NOLOCK )
        LEFT JOIN dbo.Order_Detail WITH ( NOLOCK ) ON dbo.Batch_Master.Order_Detail_Id = dbo.Order_Detail.Order_Detail_Id
        LEFT JOIN dbo.Order_Master WITH ( NOLOCK ) ON dbo.Order_Detail.Order_Id = dbo.Order_Master.Order_Id
        LEFT JOIN dbo.Gen_Order_Detail WITH ( NOLOCK ) ON dbo.Order_Detail.Order_Detail_Id = Gen_Order_Detail.Order_Detail_Id
        LEFT JOIN dbo.M_Customer WITH ( NOLOCK ) ON dbo.Order_Master.Party_Id = dbo.M_Customer.Cust_ID
        LEFT JOIN dbo.M_Metal WITH ( NOLOCK ) ON dbo.Batch_Master.Metal_ID = dbo.M_Metal.Metal_ID
        LEFT JOIN dbo.M_Purity WITH ( NOLOCK ) ON dbo.Batch_Master.Purity_Id = dbo.M_Purity.Purity_ID
        LEFT JOIN dbo.M_Sub_Category WITH ( NOLOCK ) ON dbo.Batch_Master.Sub_Category_Id = dbo.M_Sub_Category.Sub_Category_ID
        LEFT JOIN dbo.M_Category WITH ( NOLOCK ) ON dbo.Batch_Master.Category_Id = dbo.M_Category.Category_ID
        LEFT JOIN dbo.M_Design_Setting WITH ( NOLOCK ) ON dbo.Batch_Master.Seting_Id = dbo.M_Design_Setting.Design_ID
        LEFT JOIN dbo.Process_Master WITH ( NOLOCK ) ON dbo.Batch_Master.CurrentProcessId = dbo.Process_Master.Process_Id
        LEFT JOIN dbo.M_Department WITH ( NOLOCK ) ON dbo.Batch_Master.CurrentDeptId = dbo.M_Department.Dept_ID
WHERE   Batch_Master.Is_cancel = 0
        AND dbo.Batch_Master.Is_Split = 0
        AND dbo.Batch_Master.Is_Marge = 0
        AND ( ( Batch_Master.Is_Complete = 0 ) OR ( Batch_Master.Is_Complete = 1 AND Batch_Master.Is_Tag = 0 ) )
"""


def execute(filters=None):
	filters = filters or {}
	if frappe.utils.cint(filters.get("compare_mode")):
		return get_compare_columns(), get_compare_data()

	columns = get_columns()
	data = get_jewelex_data(filters)
	return columns, data


def get_columns():
	# ERP-side columns will be added in a later pass.
	return [
		{"label": "Batch No", "fieldname": "Batch_No", "fieldtype": "Data", "width": 110},
		{"label": "Category", "fieldname": "Category", "fieldtype": "Data", "width": 100},
		{"label": "Sub Category", "fieldname": "Sub_Category", "fieldtype": "Data", "width": 110},
		{"label": "Setting", "fieldname": "Setting", "fieldtype": "Data", "width": 100},
		{"label": "Style Bio", "fieldname": "StyleBio", "fieldtype": "Data", "width": 100},
		{"label": "Party Code", "fieldname": "Party_Code", "fieldtype": "Data", "width": 100},
		{"label": "Gold Wt", "fieldname": "Gold_Wt", "fieldtype": "Float", "width": 90},
		{"label": "Dia Wt", "fieldname": "Dia_Wt", "fieldtype": "Float", "width": 90},
		{"label": "Metal Type", "fieldname": "Metal_Type", "fieldtype": "Data", "width": 100},
		{"label": "Stone Wt", "fieldname": "Stone_Wt", "fieldtype": "Float", "width": 90},
		{"label": "Other Wt", "fieldname": "Other_Wt", "fieldtype": "Float", "width": 90},
		{"label": "Net Gross Wt", "fieldname": "NetGross_Wt", "fieldtype": "Float", "width": 100},
		{"label": "Current Dept", "fieldname": "Current_Dept", "fieldtype": "Data", "width": 110},
		{"label": "Current Process", "fieldname": "Current_Process", "fieldtype": "Data", "width": 120},
		{"label": "Bulk Order No", "fieldname": "Bulk_Order_No", "fieldtype": "Data", "width": 110},
		{"label": "Order No", "fieldname": "Order_No", "fieldtype": "Data", "width": 110},
		{"label": "Order Date", "fieldname": "Order_Date", "fieldtype": "Date", "width": 100},
		{"label": "Due Date", "fieldname": "Due_date", "fieldtype": "Date", "width": 100},
		{"label": "Order Type", "fieldname": "Order_Type", "fieldtype": "Data", "width": 100},
	]


def get_jewelex_connection():
	try:
		import pyodbc
	except ImportError:
		frappe.throw(
			"pyodbc is not installed. Run 'bench pip install pyodbc' in the bench environment "
			"(and ensure the ODBC Driver 17 for SQL Server is installed on the OS)."
		)

	conn_str = (
		f"DRIVER={{{JEWELEX_DB_CONFIG['driver']}}};"
		f"SERVER={JEWELEX_DB_CONFIG['server']},{JEWELEX_DB_CONFIG['port']};"
		f"DATABASE={JEWELEX_DB_CONFIG['database']};"
		f"UID={JEWELEX_DB_CONFIG['user']};"
		f"PWD={JEWELEX_DB_CONFIG['password']};"
	)
	return pyodbc.connect(conn_str)


def get_jewelex_data(filters=None):
	# TODO: apply report filters to the query (e.g. WHERE Order_No = ?) once
	# the filters are finalized.
	conn = get_jewelex_connection()
	try:
		cursor = conn.cursor()
		cursor.execute(JEWELEX_QUERY)
		columns = [col[0] for col in cursor.description]
		return [dict(zip(columns, row)) for row in cursor.fetchall()]
	finally:
		conn.close()


JEWELEX_COMPARE_QUERY = f"""
SELECT  Order_No,
        Order_Date,
        COUNT(DISTINCT Batch_No) AS Jewelex_Batch_Count
FROM ( {JEWELEX_QUERY} ) AS jewelex_sub
GROUP BY Order_No, Order_Date
"""

ERP_COMPARE_QUERY = """
SELECT  pmo.jewelex_order_no AS jewelex_order_no,
        COUNT(DISTINCT pmo.name) AS erp_order_count,
        GROUP_CONCAT(DISTINCT pmo.sales_order SEPARATOR ', ') AS erp_order_no
FROM `tabParent Manufacturing Order` pmo
WHERE EXISTS (
    SELECT 1 FROM `tabManufacturing Work Order` mwo
    WHERE mwo.manufacturing_order = pmo.name
      AND mwo.docstatus = 0
)
GROUP BY pmo.jewelex_order_no
"""

ERP_COMPLETE_QUERY = """
SELECT  pmo.jewelex_order_no AS jewelex_order_no,
        COUNT(DISTINCT pmo.name) AS erp_complete_count,
        GROUP_CONCAT(DISTINCT pmo.sales_order SEPARATOR ', ') AS erp_complete_order_no
FROM `tabParent Manufacturing Order` pmo
WHERE EXISTS (
    SELECT 1 FROM `tabManufacturing Work Order` mwo
    WHERE mwo.manufacturing_order = pmo.name
)
AND NOT EXISTS (
    SELECT 1 FROM `tabManufacturing Work Order` mwo
    WHERE mwo.manufacturing_order = pmo.name
      AND mwo.docstatus != 1
)
GROUP BY pmo.jewelex_order_no
"""


def get_compare_columns():
	return [
		{"label": "Order Date", "fieldname": "order_date", "fieldtype": "Date", "width": 100},
		{"label": "Order No", "fieldname": "order_no", "fieldtype": "Data", "width": 110},
		{"label": "Jewelex Batch Count", "fieldname": "jewelex_batch_count", "fieldtype": "Int", "width": 140},
		{"label": "ERP Order No", "fieldname": "erp_order_no", "fieldtype": "Data", "width": 160},
		{"label": "ERP Order Count", "fieldname": "erp_order_count", "fieldtype": "Int", "width": 130},
		{"label": "ERP Order Complete", "fieldname": "erp_order_complete", "fieldtype": "Data", "width": 160},
	]


def get_jewelex_compare_data():
	conn = get_jewelex_connection()
	try:
		cursor = conn.cursor()
		cursor.execute(JEWELEX_COMPARE_QUERY)
		columns = [col[0] for col in cursor.description]
		return [dict(zip(columns, row)) for row in cursor.fetchall()]
	finally:
		conn.close()


NOT_FOUND = "Not Found"


def get_compare_data():
	jewelex_rows = get_jewelex_compare_data()
	erp_rows = frappe.db.sql(ERP_COMPARE_QUERY, as_dict=True)
	erp_complete_rows = frappe.db.sql(ERP_COMPLETE_QUERY, as_dict=True)

	erp_by_order_no = {row.jewelex_order_no: row for row in erp_rows if row.jewelex_order_no}
	erp_complete_by_order_no = {
		row.jewelex_order_no: row for row in erp_complete_rows if row.jewelex_order_no
	}

	combined = []
	for row in jewelex_rows:
		order_no = row.get("Order_No")
		erp_row = erp_by_order_no.get(order_no)
		erp_complete_row = erp_complete_by_order_no.get(order_no)
		combined.append(
			{
				"order_date": row.get("Order_Date"),
				"order_no": order_no,
				"jewelex_batch_count": row.get("Jewelex_Batch_Count"),
				"erp_order_no": erp_row.erp_order_no if erp_row else NOT_FOUND,
				"erp_order_count": erp_row.erp_order_count if erp_row else NOT_FOUND,
				"erp_order_complete": erp_complete_row.erp_complete_order_no if erp_complete_row else NOT_FOUND,
			}
		)

	return sorted(
		combined,
		key=lambda r: (r["order_date"] is None, r["order_date"], r["order_no"] or ""),
	)
