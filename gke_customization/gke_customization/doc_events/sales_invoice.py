import frappe
import json

@frappe.whitelist()
def get_dispatch_slip(source_name, target_doc=None):
	if isinstance(target_doc, str):
		target_doc = json.loads(target_doc)
	if not target_doc:
		target_doc = frappe.new_doc("Delivery Challan")
	else:
		target_doc = frappe.get_doc(target_doc)

	# sales_invoice_items = frappe.db.get_list("Sales Invoice Item",filters={"parent":source_name},fields=["*"])
	sales_invoice_items = frappe.db.sql(f"""select * from `tabSales Invoice Item` tsed where parent = '{source_name}' """,as_dict=1)
	sales_invoice = frappe.db.sql(f"""select * from `tabSales Invoice` tse where name = '{source_name}'""",as_dict=1)
		
	# frappe.throw(str(item_description))
	for i in sales_invoice:
		for j in sales_invoice_items:
			item_code = j.get("item_code")

			item_description = frappe.db.sql(f"""select ti.name, tghc.description from `tabItem` as ti  
						join `tabGST HSN Code` as tghc on tghc.hsn_code = ti.gst_hsn_code
						where ti.name = '{item_code}' """)
			
			if(item_description):
				for k in item_description:
					if "JEWELLERY STUDDED WITH GEMS" in k[1]:
						target_doc.append("delivery_challan_detail", {
							"sales_invoice": i.get("name"),
							"amount": i.get("total"),
							"description": "JEWELLERY STUDDED WITH GEMS",
						})
					else:
						target_doc.append("delivery_challan_detail", {
							"sales_invoice": i.get("name"),
							"amount": i.get("total"),
							"description": k[1],
						})
			else: 
				target_doc.append("delivery_challan_detail", {
							"sales_invoice": i.get("name"),
							"amount": i.get("total"),
							"description": ' ',
						})

	return target_doc