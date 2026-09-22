# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
import pyodbc


def _get_connection():
	return pyodbc.connect(
		"DRIVER={ODBC Driver 17 for SQL Server};"
		"SERVER=27.109.25.76,9880;"
		"DATABASE=JwelexERP;"
		"UID=ra;"
		"PWD=Code@4142;"
		"TrustServerCertificate=yes;"
		"Connection Timeout=15;"
	)


@frappe.whitelist(allow_guest=False)
def get_pd_to_prod_data():
	conn = None

	try:
		conn = _get_connection()

		cursor = conn.cursor()

		sql = """
			SELECT
				Catelog_Info_Ids,
				StyleBio_Ids,
				Entry_Date,
				Category_Name,
				Sub_Category_Name,
				DesignSetting_Name,
				TagNo,
				TagDate
			FROM dbo.Catelog_Information WITH (NOLOCK)
			LEFT JOIN dbo.M_Category WITH (NOLOCK)
				ON M_Category.Category_ID = Catelog_Information.Category_ID
			LEFT JOIN dbo.M_Sub_Category WITH (NOLOCK)
				ON M_Sub_Category.Sub_Category_ID = Catelog_Information.Sub_Category_ID
			LEFT JOIN dbo.M_Design_Setting WITH (NOLOCK)
				ON M_Design_Setting.Design_ID = Catelog_Information.Design_ID
			OUTER APPLY (
				SELECT TOP 1 TagNo, Entry_Date AS TagDate FROM dbo.Item_FinishGood_Master WITH (NOLOCK)
				WHERE StyleBio = StyleBio_Ids
				ORDER BY Finish_Id
			) AS Tag
			ORDER BY Catelog_Info_Ids
		"""

		cursor.execute(sql)

		columns = [column[0] for column in cursor.description]
		data = [dict(zip(columns, row)) for row in cursor.fetchall()]

		for row in data:
			if row.get("Entry_Date"):
				row["Entry_Date"] = row["Entry_Date"].strftime("%Y-%m-%d")
			if row.get("TagDate"):
				row["TagDate"] = row["TagDate"].strftime("%Y-%m-%d")

		return data

	except Exception:
		frappe.log_error(
			title="Get PD to Prod Data Error",
			message=frappe.get_traceback()
		)
		frappe.throw("Failed to fetch PD to Prod data from Jwelex")

	finally:
		if conn:
			conn.close()


@frappe.whitelist(allow_guest=False)
def get_pd_to_prod_tag_summary():
	conn = None

	try:
		conn = _get_connection()

		cursor = conn.cursor()

		sql = """
			SELECT
				S.StyleBio,
				COUNT(DISTINCT S.TagNo) AS TotalTagNo,
				MIN(S.Entry_Date) AS FirstTagDate,
				STRING_AGG(CONVERT(VARCHAR(MAX), S.TagNo), ', ') AS TagNos,
				SUM(S.TotalPcs) AS TotalSold
			FROM Sample_BD..Item_FinishGood_Master AS S WITH (NOLOCK)
			LEFT JOIN JwelexERP..Item_FinishGood_Master AS J WITH (NOLOCK)
				ON S.StyleBio = J.StyleBio
				AND J.Is_Sales = 1
			GROUP BY
				S.StyleBio, S.Entry_Date
		"""

		cursor.execute(sql)

		columns = [column[0] for column in cursor.description]
		data = [dict(zip(columns, row)) for row in cursor.fetchall()]

		for row in data:
			if row.get("FirstTagDate"):
				row["FirstTagDate"] = row["FirstTagDate"].strftime("%Y-%m-%d")

		return data

	except Exception:
		frappe.log_error(
			title="Get PD to Prod Tag Summary Error",
			message=frappe.get_traceback()
		)
		frappe.throw("Failed to fetch PD to Prod tag summary from Jwelex")

	finally:
		if conn:
			conn.close()
