from frappe.model.document import Document
import frappe
from frappe.model.mapper import get_mapped_doc


class CustomerMasterUpdate(Document):
    def on_submit(self):        
        fields_mapping = {
            "sequence": "custom_sequence",
            "salutation": "salutation",
            "customer_codes": "custom_customer_code",
            "customer_group": "customer_group",
            "customer_type": "customer_type",
            "gst_category": "gst_category",
            "export_type": "export_type",
            "old_customer_code": "old_customer_code",
            "customer_grade": "custom_customer_grade",
            "territory": "territory",
            "territory_code": "custom_territory_code",
            "gender": "gender",
            "vendor_code": "vendor_code",
            "from_lead": "lead_name",
            "from_opportunity": "opportunity_name",
            "from_prospect": "prospect_name",
            "account_manager": "account_manager",
            "image": "image",
            "certification_charges": "custom_certification_charges",
            "ignore_po_creation_for_certification": "custom_ignore_po_creation_for_certification",
            "default_price_list": "default_price_list",
            "default_company_bank_account": "default_bank_account",
            "default_payment_terms_template": "payment_terms",
            "is_internal_customer": "is_internal_customer",
            "represents_company": "represents_company",
            "is_customer_exempted_from_sales_tax": "exempt_from_sales_tax",
            "market_segment": "market_segment",
            "industry": "industry",
            "customer_pos_id": "customer_pos_id",
            "website": "website",
            "print_language": "language",
            "customer_details": "customer_details",
            "gemstone_price_multiplier": "custom_gemstone_price_multiplier",
            "customer_primary_contact": "customer_primary_contact",
            "customer_primary_address": "customer_primary_address",
            "mobile_no": "mobile_no",
            "email_id": "email_id",
            "tax_id": "tax_id",
            "tax_withholding_category": "tax_withholding_category",
            "gstin__uin": "gstin",
            "pan": "pan",
            "loyalty_program": "loyalty_program",
            "loyalty_program_tier": "loyalty_program_tier",
            "sales_partner": "default_sales_partner",
            "commission_rate": "default_commission_rate",
            "allow_sales_invoice_creation_without_sales_order": "so_required",
            "allow_sales_invoice_creation_without_delivery_note": "dn_required",
            "is_frozen": "is_frozen",
            "disabled": "disabled",
            "tax_category": "tax_category",
            "is_internal_customer": "is_internal_customer",
            "represents_company": "represents_company",
        }

       
        credit_limit_data = self.get("credit_limit")
        sales_team_data = self.get("sales_team")
        allowed_to_transact_with = self.get("allowed_to_transact_with")

        accounts_data = self.get("accounts")

      
        if frappe.db.exists("Customer", self.customer_data):
            try:
                customer_doc = frappe.get_doc("Customer", self.customer_data)

                for source_field, target_field in fields_mapping.items():
                    new_value = self.get(source_field)
                    if new_value is not None:
                        customer_doc.set(target_field, new_value)

               
                if credit_limit_data:
                    # Clear existing child table entries
                    customer_doc.credit_limits = []

                    # Append new child table data
                    for row in credit_limit_data:
                        customer_doc.append("credit_limits", {
                            "company": row.get("company"),
                            "credit_limit": row.get("credit_limit"),
                            "bypass_credit_limit_check": row.get("bypass_credit_limit_check"),
                        })

                
                if sales_team_data:
                    customer_doc.sales_team = []

                    
                    for row in sales_team_data:
                        customer_doc.append("sales_team", {
                            "sales_person": row.get("sales_person"),
                            "contact_no": row.get("contact_no"),
                            "allocated_percentage": row.get("allocated_percentage"),
                            "allocated_amount": row.get("allocated_amount"),
                            "commission_rate": row.get("commission_rate"),
                            "incentives": row.get("incentives"),
                        })

                # Update child table: accounts
                if accounts_data:
                    # Clear existing accounts entries
                    customer_doc.accounts = []

                    # Append new accounts data
                    for row in accounts_data:
                        customer_doc.append("accounts", {
                            "company": row.get("company"),
                            "account": row.get("account"),
                            "advance_account": row.get("advance_account"),
                        })

                # Save the updated Customer document
                customer_doc.save(ignore_permissions=True)
                frappe.db.commit()
                frappe.msgprint("Customer has been updated successfully with updated credit limits, sales team details, and accounts.")

            except Exception as e:
                frappe.log_error(frappe.get_traceback(), "Customer Update Error")
                frappe.throw(f"An error occurred while updating the customer: {str(e)}")
        else:
                # Prepare data for the new Customer record
                customer_data = {
                    target_field: self.get(source_field)
                    for source_field, target_field in fields_mapping.items()
                    if self.get(source_field) is not None
                }

                # Add mandatory fields
                customer_data["doctype"] = "Customer"
                customer_data["customer_name"] = self.get("customer_name")
                customer_data["customer_group"] = customer_data.get("customer_group") or "Default Customer Group"
                customer_data["territory"] = customer_data.get("territory") or "All Territories"
                customer_data["customer_type"] = customer_data.get("customer_type") or "Company"

                # Add child table data for credit limits
                if credit_limit_data:
                    customer_data["credit_limits"] = [
                        {
                            "company": row.get("company"),
                            "credit_limit": row.get("credit_limit"),
                            "bypass_credit_limit_check": row.get("bypass_credit_limit_check"),
                        }
                        for row in credit_limit_data
                    ]

                # Add child table data for sales team
                if sales_team_data:
                    customer_data["sales_team"] = [
                        {
                            "sales_person": row.get("sales_person"),
                            "contact_no": row.get("contact_no"),
                            "allocated_percentage": row.get("allocated_percentage"),
                            "allocated_amount": row.get("allocated_amount"),
                            "commission_rate": row.get("commission_rate"),
                            "incentives": row.get("incentives"),
                        }
                        for row in sales_team_data
                    ]

                if allowed_to_transact_with:
                    if customer_data["is_internal_customer"]:
                        customer_data["companies"] = [
                            {
                                "company": row.get("company"),
                            }
                            for row in allowed_to_transact_with
                        ]

                # Add child table data for accounts
                if accounts_data:
                    customer_data["accounts"] = [
                        {
                            "company": row.get("company"),
                            "account": row.get("account"),
                            "advance_account": row.get("advance_account"),
                        }
                        for row in accounts_data
                    ]

                # Create the new Customer record
                new_customer = frappe.get_doc(customer_data)
                new_customer.insert(ignore_permissions=True)
                
                frappe.db.set_value("Customer Master Update", self.name, "new_customer", new_customer.name)
                frappe.db.set_value("Customer Master Update", self.name, "customer_primary_contact", '')
                self.reload()
                
                frappe.msgprint(f"New Customer '{new_customer.name}' has been successfully created.")
    
    def on_update_after_submit(self):
        create_supplier_address_contact(self)

def create_supplier_address_contact(self):
    if self.workflow_state == "Create Address":
        address_doc = frappe.new_doc("Address")
        address_doc.address_title = self.address_title
        address_doc.address_type = self.address_type
        address_doc.address_line1 = self.address_line_1
        address_doc.address_line2 = self.address_line_2
        address_doc.city = self.city
        address_doc.state = self.state
        address_doc.country = self.add_country
        address_doc.pincode = self.pincode
        address_doc.email_address = self.email_address
        address_doc.phone = self.phone
            
        if self.new_customer:
            address_links = address_doc.append("links", {})
            address_links.link_doctype = "Customer",
            address_links.link_name = self.new_customer 
        
        address_doc.insert(ignore_permissions=True)
        address_doc.save()

        frappe.db.set_value("Customer", self.new_customer,"customer_primary_address",address_doc.name)
        
        frappe.db.set_value("Customer Master Update", self.name,"customer_primary_address",address_doc.name)
        self.reload()

        frappe.msgprint("Customer Address Created ")
        
    if self.workflow_state == "Create Contact":
        contact_doc = frappe.new_doc("Contact")
        contact_doc.company_name = self.customer_name
        # contact_doc.email_id = self.email_address
        # contact_doc.mobile_no = self.phone
        # contact_doc.gstin
    
        if self.email_address:
            contact_email = contact_doc.append("email_ids", {})
            contact_email.email_id = self.email_address
            contact_email.is_primary = 1 
            
        if self.phone:
            contact_phone = contact_doc.append("phone_nos", {})
            contact_phone.phone = self.phone
            contact_phone.is_primary_mobile_no = 1 
        
        if self.new_customer:
            contact_links = contact_doc.append("links", {})
            contact_links.link_doctype = "Customer",
            contact_links.link_name = self.new_customer 
        
        contact_doc.insert(ignore_permissions=True)
        contact_doc.save()

        frappe.db.set_value("Customer", self.new_customer,"customer_primary_contact",contact_doc.name)
        
        frappe.db.set_value("Customer Master Update", self.name,"customer_primary_contact",contact_doc.name)
        self.reload()

        frappe.msgprint("Customer Contact Created ")
