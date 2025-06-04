import frappe 
import json

@frappe.whitelist()
def get_delivery_challan(source_name, target_doc=None):
    frappe.throw(f"{source_name} {target_doc}")
    if isinstance(target_doc, str):
        target_doc = json.loads(target_doc)
    if not target_doc:
        target_doc = frappe.new_doc("Delivery Challan")
    else:
        target_doc = frappe.get_doc(target_doc)

    purchase_receipt_items = frappe.db.sql(f"""select * from `tabPurchase Receipt Item` tsed where parent = '{source_name}' """,as_dict=1)
    purchase_receipt = frappe.db.sql(f"""select * from `tabPurchase Receipt` tse where name = '{source_name}' """,as_dict=1)
    frappe.throw(str(purchase_receipt))
    #  and is_return = 1
    for i in purchase_receipt:
        for j in purchase_receipt_items:
            item_code = j.get("item_code")

            item_description = frappe.db.sql(f"""select ti.name, tghc.description, ti.item_group from `tabItem` as ti  
                        join `tabGST HSN Code` as tghc on tghc.hsn_code = ti.gst_hsn_code
                        where ti.name = '{item_code}' """)
                        
            # frappe.throw(str(item_description))
            if(item_description):
                for k in item_description: 
                    if k[2] in ['Diamond - V','Metal - V','Gemstone - V','Finding - V','Other - V','Diamond - T','Metal - T','Gemstone - T','Finding - T','Other - T'] :					
                        # frappe.throw('m')
                        target_doc.append("delivery_challan_detail", {
                                "purchase_receipt": i.get("name"), 
                                "amount": j.get("amount"),
                                "qty": j.get("qty"),
                                "uom": j.get("uom"),
                                "description": "SEMI FINISHED PRODUCT",
                            })
                    else: 
                        # frappe.throw('h')
                        if "JEWELLERY STUDDED WITH GEMS" in k[1]:
                            target_doc.append("delivery_challan_detail", {
                                "purchase_receipt": i.get("name"), 
                                "amount": j.get("amount"),
                                "qty": j.get("qty"),
                                "uom": j.get("uom"),
                                "description": "JEWELLERY STUDDED WITH GEMS",
                            })
                        else:
                            target_doc.append("delivery_challan_detail", {
                                "purchase_receipt": i.get("name"), 
                                "amount": j.get("amount"),
                                "qty": j.get("qty"),
                                "uom": j.get("uom"),
                                "description": k[1],
                            })
            else:
                target_doc.append("delivery_challan_detail", {
                            "purchase_receipt": i.get("name"), 
                            "amount": j.get("amount"),
                            "qty": j.get("qty"),
                            "uom": j.get("uom"),
                            "description": ' ',
                        })

    return target_doc
	

@frappe.whitelist()
def get_delivery_challan1(source_name, target_doc=None,args=None):
    if isinstance(target_doc, str):
        target_doc = json.loads(target_doc)
    if not target_doc:
        target_doc = frappe.new_doc("Delivery Challan")
    else:
        target_doc = frappe.get_doc(target_doc)
 
    purchase_receipt_items = frappe.db.sql(f"""select * from `tabPurchase Receipt Item` tsed where parent = '{source_name}' """,as_dict=1)
    purchase_receipt = frappe.db.sql(f"""select * from `tabPurchase Receipt` tse where name = '{source_name}' """,as_dict=1)
     
    for i in purchase_receipt:
        for j in purchase_receipt_items:
            item_code = j.get("item_code")

            item_description = frappe.db.sql(f"""select ti.name, tghc.description, ti.item_group from `tabItem` as ti  
                        join `tabGST HSN Code` as tghc on tghc.hsn_code = ti.gst_hsn_code
                        where ti.name = '{item_code}' """)
                        
            # frappe.throw(str(item_description))
            if(item_description):
                for k in item_description: 
                    if k[2] in ['Diamond - V','Metal - V','Gemstone - V','Finding - V','Other - V','Diamond - T','Metal - T','Gemstone - T','Finding - T','Other - T'] :					
                        # frappe.throw('m')
                        target_doc.append("delivery_challan_detail", {
                                "reference_document_type" : "Purchase Receipt",
                                "reference_document": i.get("name"), 
                                # "purchase_receipt": i.get("name"), 
                                "amount": j.get("amount"),
                                "qty": j.get("qty"),
                                "uom": j.get("uom"),
                                "description": "SEMI FINISHED PRODUCT",
                            })
                    else: 
                        # frappe.throw('h')
                        if "JEWELLERY STUDDED WITH GEMS" in k[1]:
                            target_doc.append("delivery_challan_detail", {
                                "reference_document_type" : "Purchase Receipt",
                                "reference_document": i.get("name"), 
                                # "purchase_receipt": i.get("name"), 
                                "amount": j.get("amount"),
                                "qty": j.get("qty"),
                                "uom": j.get("uom"),
                                "description": "JEWELLERY STUDDED WITH GEMS",
                            })
                        else:
                            target_doc.append("delivery_challan_detail", {
                                "reference_document_type" : "Purchase Receipt",
                                "reference_document": i.get("name"), 
                                # "purchase_receipt": i.get("name"), 
                                "amount": j.get("amount"),
                                "qty": j.get("qty"),
                                "uom": j.get("uom"),
                                "description": k[1],
                            })
            else:
                target_doc.append("delivery_challan_detail", {
                            "reference_document_type" : "Purchase Receipt",
                            "reference_document": i.get("name"), 
                            # "purchase_receipt": i.get("name"), 
                            "amount": j.get("amount"),
                            "qty": j.get("qty"),
                            "uom": j.get("uom"),
                            "description": ' ',
                        })

    return target_doc
	