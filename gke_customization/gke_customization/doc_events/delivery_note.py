import frappe
import json 

def validate(self,method=None):
	for r in self.items :
		if r.sales_order:
			Diamond_grade=frappe.db.get_value('Sales Order',r.sales_order,'items.diamond_grade')
			Batch_no=frappe.db.get_value('Sales Order',r.sales_order,'items.batch_no')
			r.diamond_grade=Diamond_grade
			r.batch_no = Batch_no
			

        
		if not r.batch_no and not r.diamond_grade:
			frappe.throw("Batch no and Diamond grade are mandatory")
		elif not r.batch_no:
			frappe.throw("Batch no is mandatory")
		elif not r.diamond_grade:
			frappe.throw("Diamond grade is mandatory")