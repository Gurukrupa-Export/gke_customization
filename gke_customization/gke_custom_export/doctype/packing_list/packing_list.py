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

@frappe.whitelist()
def get_salesInvoice_item(sales_invoice):
	sales_invoice = frappe.db.sql(f"""select * from `tabSales Invoice` tsi join `tabSales Invoice Item` as tsii on tsi.name = tsii.parent join `tabItem` as ti on tsii.item_code = ti.name join `tabBOM` as tb on ti.tag_no = tb.tag_no where tsi.name = '{sales_invoice}' and tb.bom_type ="Finish Goods" """,as_dict=1)

	return sales_invoice


