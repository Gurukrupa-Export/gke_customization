# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

class SupplierUpdateMaster(Document):
    def on_submit(self):
        # Mapping of fields between SupplierMasterUpdate and Supplier doctype
        fields_mapping = {
            "supplier_group": "supplier_group",
            "supplier_name": "supplier_name",
            "supplier_type": "supplier_type",
            "territory": "territory",
            "country": "country",
            "consider_purchase_receipt_as_customer": "custom_consider_purchase_receipt_as_customergoods",
            "gst_transporter_id": "gst_transporter_id",
            "image": "image",
            "default_company_bank_account": "default_bank_account",
            "price_list": "default_price_list",
            "default_payment_terms_template": "payment_terms",
            "certification_charges": "custom_certification_charges",
            "represents_company": "represents_company",
            "website": "website",
            "print_language": "language",
            "is_irs_1099_reporting_required_for_supplier": "irs_1099",
            "tax_withholding_category": "tax_withholding_category",
            "gstin__uin": "gstin",
            "pan": "pan",
            "supplier_primary_contact": "supplier_primary_contact",
            "mobile_no": "mobile_no",
            "email_id": "email_id",
            "supplier_primary_address": "supplier_primary_address",
            "primary_address": "primary_address",
            "allow_purchase_invoice_creation_without_purchase_order": "allow_purchase_invoice_creation_without_purchase_order",
            "allow_purchase_invoice_creation_without_purchase_receipt": "allow_purchase_invoice_creation_without_purchase_receipt",
            "is_frozen": "is_frozen",
            "disabled": "disabled",
            "warn_rfqs": "warn_rfqs",
            "warn_pos": "warn_pos",
            "prevent_rfqs": "prevent_rfqs",
            "prevent_pos": "prevent_pos",
            "block_supplier": "on_hold",
            "hold_type": "hold_type",
            "release_date": "release_date",
            "is_internal_supplier": "is_internal_supplier",
            "represents_company": "represents_company",
            "reverse_chargeapplicable": "is_reverse_charge_applicable"
        }
        
        # Fetch child table data for accounts and allowed_to_transact_with
        accounts_data = self.get("accounts") or []
        companies_data = self.get("allowed_to_transact_with") or []
        purchase_type_data = self.get("purchase_type") or []

        # Check if the supplier already exists
        if frappe.db.exists("Supplier", self.supplier_data):
            try:
                # Fetch the existing Supplier document
                supplier_doc = frappe.get_doc("Supplier", self.supplier_data)

                # Update parent fields
                for source_field, target_field in fields_mapping.items():
                    new_value = self.get(source_field)
                    if new_value is not None:
                        supplier_doc.set(target_field, new_value)

                # Update child table: accounts
                supplier_doc.accounts = []  # Clear existing accounts
                for row in accounts_data:
                    if row:
                        supplier_doc.append("accounts", {
                            "company": row.get("company"),
                            "account": row.get("account"),
                            "advance_account": row.get("advance_account"),
                        })

                # Update child table: allowed_to_transact_with
                supplier_doc.companies = []  # Clear existing allowed_to_transact_with
                for row in companies_data:
                    if row:
                        supplier_doc.append("companies", {
                            "company": row.get("company"),
                        })

                # Update child table: purchase_type
                supplier_doc.purchase_type = []  # Clear existing purchase_type
                for row in purchase_type_data:
                    if row:
                        supplier_doc.append("purchase_type", {
                            "purchase_type": row.get("purchase_type"),
                        })

                # Save the updated Supplier document
                supplier_doc.save(ignore_permissions=True)
                frappe.db.commit()

            except Exception as e:
                frappe.log_error(frappe.get_traceback(), "Supplier Update Error")
                frappe.throw(f"An error occurred while updating the supplier: {str(e)}")
        else:
            # Prepare data for the new Supplier record
            supplier_data = {
                target_field: self.get(source_field)
                for source_field, target_field in fields_mapping.items()
                if self.get(source_field) is not None
            }

            # Add mandatory fields
            supplier_data["doctype"] = "Supplier"
            supplier_data["supplier_name"] = self.get("supplier_name")
            supplier_data["supplier_group"] = supplier_data.get("supplier_group")
            supplier_data["custom_territory"] = supplier_data.get("territory")
            supplier_data["supplier_type"] = supplier_data.get("supplier_type")
            
            # Add child table data for accounts
            if accounts_data:
                supplier_data["accounts"] = [
                    {
                        "company": row.get("company"),
                        "account": row.get("account"),
                        "advance_account": row.get("advance_account"),
                    }
                    for row in accounts_data
                ]

            # Add child table data for allowed_to_transact_with
            if companies_data:
                if supplier_data["is_internal_supplier"]:
                    supplier_data["companies"] = [
                        {
                            "company": row.get("company"),
                        }
                        for row in companies_data
                    ]

            # Add child table data for purchase_type
            if purchase_type_data:
                supplier_data["purchase_type"] = [
                    {
                        "purchase_type": row.get("purchase_type"),
                    }
                    for row in purchase_type_data
                ]
            
            # Create the new Supplier record
            # frappe.throw(f"{supplier_data}")
            new_supplier = frappe.get_doc(supplier_data)
            new_supplier.insert(ignore_permissions=True)
            
            frappe.db.set_value("Supplier Update Master", self.name, "new_supplier", new_supplier.name)
            frappe.db.set_value("Supplier Update Master", self.name, "supplier_primary_contact", '')
            self.reload()
            
            frappe.msgprint(f"New Supplier '{new_supplier.name}' has been successfully created.")

    def on_update_after_submit(self):
        create_supplier_address_contact(self)
        

def create_supplier_address_contact(self):
    if self.workflow_state == "Create Address":
        if self.address_title:
            address_doc = frappe.new_doc("Address")
            address_doc.address_title = self.address_title
            address_doc.address_type = self.address_type
            address_doc.address_line1 = self.address_line_1
            address_doc.address_line2 = self.address_line_2
            address_doc.city = self.city
            address_doc.state = self.state
            address_doc.country = self.country
            address_doc.pincode = self.pincode
            address_doc.email_address = self.email_address
            address_doc.phone = self.phone
                
            if self.new_supplier:
                address_links = address_doc.append("links", {})
                address_links.link_doctype = "Supplier",
                address_links.link_name = self.new_supplier 
            
            address_doc.insert(ignore_permissions=True)
            address_doc.save()
            
            frappe.db.set_value("Supplier", self.new_supplier,"supplier_primary_address",address_doc.name)
            
            frappe.db.set_value("Supplier Update Master", self.name,"supplier_primary_address",address_doc.name)
            self.reload()
            
            frappe.msgprint("Supplier Address Created ")    
        else:
            frappe.throw(f"{self.address_title} is reqd..")   

    if self.workflow_state == "Create Contact": 
        if self.phone:
            contact_doc = frappe.new_doc("Contact")
            contact_doc.company_name = self.supplier_name 

            if self.email_address:
                contact_email = contact_doc.append("email_ids", {})
                contact_email.email_id = self.email_address
                contact_email.is_primary = 1 
                
            if self.phone:
                contact_phone = contact_doc.append("phone_nos", {})
                contact_phone.phone = self.phone
                contact_phone.is_primary_mobile_no = 1 
            
            if self.new_supplier:
                contact_links = contact_doc.append("links", {})
                contact_links.link_doctype = "Supplier",
                contact_links.link_name = self.new_supplier 
            
            contact_doc.insert(ignore_permissions=True)
            contact_doc.save()
                    
            frappe.db.set_value("Supplier", self.new_supplier,"supplier_primary_contact",contact_doc.name)
            
            frappe.db.set_value("Supplier Update Master", self.name,"supplier_primary_contact",contact_doc.name)
            self.reload()
            
            frappe.msgprint("Supplier Contact Created ")
        else:
            frappe.throw(f"{self.phone} is reqd..") 