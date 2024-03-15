import frappe 
import json

@frappe.whitelist()
def get_delivery_challan(source_name, target_doc=None):
	if isinstance(target_doc, str):
		target_doc = json.loads(target_doc)
	if not target_doc:
		target_doc = frappe.new_doc("Delivery Challan")
	else:
		target_doc = frappe.get_doc(target_doc)

	# sales_invoice_items = frappe.db.get_list("Stock Entry Detail",filters={"parent":f"{source_name}"},fields=["*"])
	stock_entry_items = frappe.db.sql(f"""select * from `tabStock Entry Detail` tsed where parent = '{source_name}' """,as_dict=1)
	stock_entry = frappe.db.sql(f"""select * from `tabStock Entry` tse where name = '{source_name}'""",as_dict=1)
	
	# frappe.throw(str(stock_entry_items))
	
	for i in stock_entry:
		for j in stock_entry_items:
			item_code = j.get("item_code")

			item_description = frappe.db.sql(f"""select ti.name, tghc.description from `tabItem` as ti  
						join `tabGST HSN Code` as tghc on tghc.hsn_code = ti.gst_hsn_code
						where ti.name = '{item_code}' """)
			if(item_description):
				for k in item_description:
					# frappe.throw(k[1]) 
					# target_doc.append("delivery_challan_detail", {
					# 	"stock_entry": i.get("name"),
					# 	"amount": i.get("total_amount"),
					# 	"description": k[1],
					# })
					if "JEWELLERY STUDDED WITH GEMS" in k[1]:
						target_doc.append("delivery_challan_detail", {
							"stock_entry": i.get("name"),
							"amount": i.get("total_amount"),
							"description": "JEWELLERY STUDDED WITH GEMS",
						})
					else:
						target_doc.append("delivery_challan_detail", {
							"stock_entry": i.get("name"),
							"amount": i.get("total_amount"),
							"description": k[1],
						})
			else:
				target_doc.append("delivery_challan_detail", {
							"stock_entry": i.get("name"),
							"amount": i.get("total_amount"),
							"description": ' ',
						})

	return target_doc