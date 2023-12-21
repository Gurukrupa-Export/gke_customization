# Copyright (c) 2023, gurukrupa_export] and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class PackingList(Document):
	pass


@frappe.whitelist()
def get_salesOrder_item(sales_order):
	sale_order = frappe.db.sql(f"""select * from `tabSales Order` tso join `tabSales Order Item` as tsoi on  tso.name = tsoi.parent join `tabItem` as ti on tsoi.item_code = ti.name join `tabBOM` as tb on ti.tag_no = tb.tag_no where tso.name = '{sales_order}' and tb.bom_type ="Finish Goods" """,as_dict=1)

	return sale_order