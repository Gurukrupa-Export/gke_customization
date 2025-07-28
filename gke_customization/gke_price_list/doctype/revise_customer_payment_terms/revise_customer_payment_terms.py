# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
import frappe
import json
from frappe.model.document import Document
import copy
import frappe
import json

# @frappe.whitelist()
class ReviseCustomerPaymentTerms(Document):
   def on_submit(self):
        if not frappe.db.exists("Customer Payment Terms", self.customer_payment_terms_name):
            doc = frappe.new_doc("Customer Payment Terms")
            doc.name = self.customer_payment_terms_name 
            doc.customer = self.customer  
            for row in self.customer_payment_details:
                doc.append("customer_payment_details", {
                    "item_type": row.get("item_type"),
                    "payment_term": row.get("payment_term"),
                })
                doc.insert(ignore_permissions=True)
        else:
            frappe.get_doc("Customer Payment Terms", self.customer_payment_terms_name)
            doc.set("customer_payment_details", [])
            for row in self.customer_payment_details:
                doc.append("customer_payment_details", {
                    "item_type": row.get("item_type"),
                    "payment_term": row.get("payment_term"),
                })

            doc.save(ignore_permissions=True)
        return "Updated Successfully"

