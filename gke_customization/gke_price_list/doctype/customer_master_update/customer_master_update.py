from frappe.model.document import Document
import frappe


class CustomerMasterUpdate(Document):
    pass
    def on_submit(self):
        # Mapping of fields between CustomerMasterUpdate and Customer doctype
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
        }

       
        credit_limit_data = self.get("credit_limit")
        sales_team_data = self.get("sales_team")

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

                # Update child table: sales_team
                if sales_team_data:
                    # Clear existing sales team entries
                    customer_doc.sales_team = []

                    # Append new sales team data
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
            # Create a new Customer record if it doesn't exist
            try:
                # Prepare data for the new Customer record
                customer_data = {
                    target_field: self.get(source_field)
                    for source_field, target_field in fields_mapping.items()
                    if self.get(source_field) is not None
                }

                # Add mandatory fields
                customer_data["doctype"] = "Customer"
                customer_data["customer_name"] = self.get("customer_name") or "Unnamed Customer"
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
                frappe.db.commit()
                frappe.msgprint(f"New Customer '{new_customer.customer_name}' has been created successfully with sales team and accounts details.")

            except Exception as e:
                frappe.log_error(frappe.get_traceback(), "Customer Creation Error")
                frappe.throw(f"An error occurred while creating the customer: {str(e)}")

