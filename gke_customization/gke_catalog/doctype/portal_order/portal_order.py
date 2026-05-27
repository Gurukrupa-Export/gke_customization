# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import re
import frappe
from frappe.model import workflow
from frappe.model.document import Document
from frappe.model.workflow import apply_workflow

class PortalOrder(Document):
    def before_save(self):
        if self.status == "Ordered" and self.workflow_state == "Draft": 
            apply_workflow(self, "Send to Order")
            self.status = "Ordered"
            self.apply_status_to_child(status="Ordered")
        
        if self.status == "Cancel Order" and self.workflow_state == "Draft":
            apply_workflow(self, "Cancel")
            self.status = "Cancel Order"
            self.apply_status_to_child(status="Cancel Order")
            
        if self.status == "Cancel Order" and self.workflow_state == "Ordered":
            apply_workflow(self, "Cancel")
            self.status = "Cancel Order"
            self.apply_status_to_child(status="Cancel Order")


    def apply_status_to_child(self, status):
        for item in self.items:
            if item.status == "Cancel Order":
                continue  # skip only this item

            # frappe.throw(f"Applying Cancel Workflow  {self.name} with status {status}")
            frappe.msgprint(f"Updating item {item.name} status to {status}")
            item.status = status

            
            
            
            
            
            
            
            
            

    # def after_save(self):
    #     if self.flags.get("workflow_applied"):
    #         frappe.db.set_value("Portal Order", self.name, "status", self.status)

    #         # Persist child table item status to DB if order is cancelled
    #         if self.status == "Cancelled":
    #             for item in self.items:  # replace 'items' with your actual child table field name
    #                 frappe.db.set_value(
    #                     "Portal Order Item",  # replace with your actual child DocType name
    #                     item.name,
    #                     "status",
    #                     "Cancelled"
    #                 )

    #         frappe.db.commit()
            
    #     if self.flags.get("workflow_applied"):
    #         return

    #     if self.status == "Ordered":
    #         self.flags.workflow_applied = True
    #         apply_workflow(self, "Approve")
    #         self.status = "Ordered"

    #     elif self.status == "Cancelled":
    #         self.flags.workflow_applied = True
    #         apply_workflow(self, "Cancel")
    #         self.status = "Cancelled"
    #         # Cancel all child table items
    #         self.cancel_all_items()

    # def cancel_all_items(self):
    #     """Set status of all items in child table to Cancelled"""
    #     for item in self.items:  # replace 'items' with your actual child table field name
    #         item.status = "Cancelled"

    # def after_save(self):
    #     if self.flags.get("workflow_applied"):
    #         frappe.db.set_value("Portal Order", self.name, "status", self.status)

    #         # Persist child table item status to DB if order is cancelled
    #         if self.status == "Cancelled":
    #             for item in self.items:  # replace 'items' with your actual child table field name
    #                 frappe.db.set_value(
    #                     "Portal Order Item",  # replace with your actual child DocType name
    #                     item.name,
    #                     "status",
    #                     "Cancelled"
    #                 )

    #         frappe.db.commit()


