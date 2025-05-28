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

	# sales_invoice_items = frappe.db.get_list("Sales Invoice Item",filters={"parent":source_name},fields=["*"])
	sales_invoice_items = frappe.db.sql(f"""select * from `tabSales Invoice Item` tsed where parent = '{source_name}' """,as_dict=1)
	sales_invoice = frappe.db.sql(f"""select * from `tabSales Invoice` tse where name = '{source_name}'""",as_dict=1)
		
	# frappe.throw(str(item_description))
	for i in sales_invoice:
		for j in sales_invoice_items:
			item_code = j.get("item_code")

			item_description = frappe.db.sql(f"""select ti.name, tghc.description, ti.item_group from `tabItem` as ti  
						join `tabGST HSN Code` as tghc on tghc.hsn_code = ti.gst_hsn_code
						where ti.name = '{item_code}' """)
			
			if(item_description):
				for k in item_description:
					if k[2] in ['Diamond - V','Metal - V','Gemstone - V','Finding - V','Other - V','Diamond - T','Metal - T','Gemstone - T','Finding - T','Other - T'] :					
						# frappe.throw('m')
						target_doc.append("delivery_challan_detail", {
								"reference_document_type" : "Sales Invoice",
                                "reference_document": i.get("name"), 
								# "sales_invoice": i.get("name"),
								"amount": j.get("amount"),
								"qty": j.get("qty"),
								"uom": j.get("uom"),
								"description": "SEMI FINISHED PRODUCT",
							})
					else: 
						if "JEWELLERY STUDDED WITH GEMS" in k[1]:
							target_doc.append("delivery_challan_detail", {
								"reference_document_type" : "Sales Invoice",
                                "reference_document": i.get("name"),
								# "sales_invoice": i.get("name"),
								"amount": j.get("amount"),
								"qty": j.get("qty"),
								"uom": j.get("uom"),
								"description": "JEWELLERY STUDDED WITH GEMS",
							})
						else:
							target_doc.append("delivery_challan_detail", {
								"reference_document_type" : "Sales Invoice",
                                "reference_document": i.get("name"),
								# "sales_invoice": i.get("name"),
								"amount": j.get("amount"),
								"qty": j.get("qty"),
								"uom": j.get("uom"),
								"description": k[1],
							})
			else: 
				target_doc.append("delivery_challan_detail", {
							"reference_document_type" : "Sales Invoice",
                            "reference_document": i.get("name"),
							# "sales_invoice": i.get("name"),
							"amount": j.get("amount"),
							"qty": j.get("qty"),
							"uom": j.get("uom"),
							"description": j.get("description"),
						})

	return target_doc


def validate(self,method=None):
	if self.company=='Sadguru Diamond' and not self.is_return:
		for r in self.items :
			# if r.sales_order:
			# 	Diamond_grade=frappe.db.get_value('Sales Order',r.sales_order,'items.diamond_grade')
			# 	Batch_no=frappe.db.get_value('Sales Order',r.sales_order,'items.batch_no')
			# 	self.diamond_grade=Diamond_grade
			# 	self.batch_no = Batch_no
			
			if not r.batch_no and not r.diamond_grade:
				frappe.throw("Batch no and Diamond grade are mandatory")
			elif not r.batch_no:
				frappe.throw("Batch no is mandatory")
			elif not r.diamond_grade:
				frappe.throw("Diamond grade is mandatory")

