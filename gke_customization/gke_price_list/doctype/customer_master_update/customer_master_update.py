from frappe.model.document import Document
import frappe
from frappe.model.mapper import get_mapped_doc


class CustomerMasterUpdate(Document):
    def on_submit(self):
        if self.workflow_state in ['Update Customer', 'Create Customer']:
            if frappe.db.exists("Customer", self.customer_data):
                self.update_customer()
            else:
                self.create_customer()
     ##################################################################           
        if self.workflow_state in ['Update Payment Term', 'Create Payment Term']:
            self.update_customer_payment()

    def update_customer_payment(self):    
        existing_payment_term = frappe.db.get_value("Customer Payment Terms", {"customer": self.cpt_customer}, "name" )

        if existing_payment_term:
            customer_payment_term = frappe.get_doc("Customer Payment Terms", existing_payment_term)
        else:
            customer_payment_term = frappe.new_doc("Customer Payment Terms")
            customer_payment_term.customer = self.customer
    
        existing_rows = {
            row.item_type: row for row in customer_payment_term.customer_payment_details
        }
        incoming_item_types = set()

        for row in self.customer_payment_terms:
            incoming_item_types.add(row.item_type)
            existing_row = existing_rows.get(row.item_type)
            
            if existing_row:
                if (
                    existing_row.payment_term != row.payment_term or existing_row.due_date_based_on != row.due_date_based_on or
                    existing_row.due_days != row.due_days or existing_row.due_months != row.due_months   
                ):
                    existing_row.payment_term = row.payment_term
                existing_row.due_date_based_on = row.due_date_based_on
                existing_row.due_days = row.due_days
                existing_row.due_months = row.due_months
                existing_row.flags.modified = True
            else:
                customer_payment_term.append("customer_payment_details", {
                    "item_type": row.item_type,
                    "payment_term": row.payment_term,
                    "due_date_based_on": row.due_date_based_on,
                    "due_days": row.due_days,
                    "due_months": row.due_months
                })

        customer_payment_term.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.msgprint("Customer payment terms Updated")

    def update_customer(self):
        fields_mapping = self.get_fields_mapping()
        credit_limit_data = self.get("credit_limit")
        sales_team_data = self.get("sales_team")
        allowed_to_transact_with = self.get("allowed_to_transact_with")
        order_type_criteria = self.get("custom_order_type_criteria")
        sales_type = self.get("sales_type")
        metal_criteria = self.get("metal_criteria")
        diamond_grades = self.get("diamond_grades")
        accounts_data = self.get("accounts")
        customer_representatives = self.get("custom_customer_representatives")

        try:
            customer_doc = frappe.get_doc("Customer", self.customer_data)

            for source_field, target_field in fields_mapping.items(): 
                new_value = self.get(source_field) 
                if new_value is not None:
                    customer_doc.set(target_field, new_value)

            gst_category_value = self.get("gst_category")
            if gst_category_value:
                customer_doc.set("gst_category", gst_category_value)
                # frappe.db.set_value("Customer", customer_doc.name, 'gst_category', gst_category_value)
                # self.reload()

            if self.credit_limit:
                customer_doc.credit_limits = []
                for row in self.credit_limit:
                    customer_doc.append("credit_limits", {
                        "company": row.get("company"),
                        "credit_limit": row.get("credit_limit"),
                        "bypass_credit_limit_check": row.get("bypass_credit_limit_check"),
                    })

            if self.sales_team:
                customer_doc.sales_team = []
                for row in self.sales_team:
                    customer_doc.append("sales_team", {
                        "sales_person": row.get("sales_person"),
                        "contact_no": row.get("contact_no"),
                        "allocated_percentage": row.get("allocated_percentage"),
                        "allocated_amount": row.get("allocated_amount"),
                        "commission_rate": row.get("commission_rate"),
                        "incentives": row.get("incentives"),
                    })

            if self.accounts:
                customer_doc.accounts = []
                for row in self.accounts:
                    customer_doc.append("accounts", {
                        "company": row.get("company"),
                        "account": row.get("account"),
                        "advance_account": row.get("advance_account"),
                    })
            
            if self.custom_order_type_criteria:
                customer_doc.custom_order_type_criteria = []
                for row in self.custom_order_type_criteria:
                    customer_doc.append("custom_order_type_criteria", {
                        "order_type": row.get("order_type"),
                        "flow_type": row.get("flow_type")
                    })
            
            if self.sales_type:
                customer_doc.sales_type = []
                for row in self.sales_type:
                    customer_doc.append("sales_type", {
                        "sales_type": row.get("sales_type"),
                        "tax_rate": row.get("tax_rate")
                    })
            
            if self.metal_criteria:
                customer_doc.metal_criteria = []
                for row in self.metal_criteria:
                    customer_doc.append("metal_criteria", {
                        "metal_type": row.get("metal_type"),
                        "metal_touch": row.get("metal_touch"),
                        "metal_purity": row.get("metal_purity")
                    })
            
            if self.diamond_grades:
                customer_doc.diamond_grades = []
                for row in self.diamond_grades:
                    customer_doc.append("diamond_grades", {
                        "diamond_quality": row.get("diamond_quality"),
                        "diamond_grade_1": row.get("diamond_grade_1"),
                        "diamond_grade_2": row.get("diamond_grade_2"),
                        "diamond_grade_3": row.get("diamond_grade_3"),
                        "diamond_grade_4": row.get("diamond_grade_4")
                    })
            
            if self.custom_customer_representatives:
                customer_doc.custom_customer_representatives = []
                for row in self.custom_customer_representatives:
                    customer_doc.append("custom_customer_representatives", {
                        "employee": row.get("employee"),
                        "full_name": row.get("full_name"),
                        "user_id": row.get("user_id") 
                    })
            customer_doc.save(ignore_permissions=True)
            frappe.db.commit()
            
            frappe.msgprint("Customer has been updated successfully.")

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Customer Update Error")
            frappe.throw(f"An error occurred while updating the customer: {str(e)}")
    
    def get_fields_mapping(self):
        return {
            "sequence": "custom_sequence",
            "customer_codes": "custom_customer_code",
            "customer_group": "customer_group",
            "customer_type": "customer_type",
            # "gst_category": "gst_category",
            "export_type": "export_type",
            "old_customer_code": "old_customer_code",
            "customer_grade": "custom_customer_grade",
            "territory": "territory",
            "territory_code": "custom_territory_code",
            "gender": "gender",
            "vendor_code": "vendor_code",
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
            "brand": "brand",
            "cfa": "cfa",
            "custom_sketch_workflow_state": "custom_sketch_workflow_state",
            "custom_order_workflow_state": "custom_order_workflow_state",
            "custom_consider_2_digit_for_bom": "custom_consider_2_digit_for_bom",
            "custom_consider_2_digit_for_diamond": "custom_consider_2_digit_for_diamond",
            "custom_consider_2_digit_for_gemstone": "custom_consider_2_digit_for_gemstone",
            "custom_advanced_manual_bagging_available": "custom_advanced_manual_bagging_available",
            "custom_require_customer_bulk_numbers": "custom_require_customer_bulk_numbers",
            "custom_allowed_item_category_for_invoice": "custom_allowed_item_category_for_invoice",
            "custom_approval_warehouse": "custom_approval_warehouse",
            "compute_making_charges_on": "compute_making_charges_on",
            "diamond_price_list": "diamond_price_list",
            "custom_gemstone_price_list_type": "custom_gemstone_price_list_type",
            "custom_tan_no": "custom_tan_no",
            "custom_msme_no": "custom_msme_no",
            "custom_msme_type": "custom_msme_type",
            "custom_iec_no": "custom_iec_no",
            "aadhar_card": "custom_aadhar_card",
            "pan_card": "custom_pan_card",
            "other_documents": "custom_other_documents",
            "cancel_cheque": "custom_cancel_cheque",
            "authorized_persons_letter": "custom_authorized_persons_letter",
            "kyc": "custom_kyc",
        }

    def create_customer(self):
        fields_mapping = self.get_fields_mapping()
        credit_limit_data = self.get("credit_limit")
        sales_team_data = self.get("sales_team")
        allowed_to_transact_with = self.get("allowed_to_transact_with")
        order_type_criteria = self.get("custom_order_type_criteria")
        sales_type = self.get("sales_type")
        metal_criteria = self.get("metal_criteria")
        diamond_grades = self.get("diamond_grades")
        accounts_data = self.get("accounts")
        customer_representatives = self.get("custom_customer_representatives")

        customer_data = {
            target_field: self.get(source_field)
            for source_field, target_field in fields_mapping.items()
            if self.get(source_field) is not None
        }

        # Mandatory fields
        customer_data["doctype"] = "Customer"
        customer_data["customer_name"] = self.get("customer_name")
        customer_data["customer_group"] = customer_data.get("customer_group") or "Default Customer Group"
        customer_data["territory"] = customer_data.get("territory")
        customer_data["customer_type"] = customer_data.get("customer_type") or "Company" 
 
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
        
        if order_type_criteria:
            customer_data["custom_order_type_criteria"] = [
                {
                    "order_type": row.get("order_type"),
                    "flow_type": row.get("flow_type")
                }
                for row in order_type_criteria
            ]
        
        if sales_type:
            customer_data["sales_type"] = [
                {
                    "sales_type": row.get("sales_type"),
                    "tax_rate": row.get("tax_rate")
                }
                for row in sales_type
            ]
        if metal_criteria:
            customer_data["metal_criteria"] = [
                {
                    "metal_type": row.get("metal_type"),
                    "metal_touch": row.get("metal_touch"),
                    "metal_purity": row.get("metal_purity")
                }
                for row in metal_criteria
            ]
        if diamond_grades:
            customer_data["diamond_grades"] = [
                {
                    "diamond_quality": row.get("diamond_quality"),
                    "diamond_grade_1": row.get("diamond_grade_1"),
                    "diamond_grade_2": row.get("diamond_grade_2"),
                    "diamond_grade_3": row.get("diamond_grade_3"),
                    "diamond_grade_4": row.get("diamond_grade_4")

                }
                for row in diamond_grades
            ]
        
        if customer_representatives:
            customer_data["custom_customer_representatives"] = [
                {
                    "employee": row.get("employee"),
                    "full_name": row.get("full_name"),
                    "user_id": row.get("user_id") 

                }
                for row in customer_representatives
            ]
        # Insert the customer
        new_customer = frappe.get_doc(customer_data)
        new_customer.insert(ignore_permissions=True)

        frappe.db.set_value("Customer Master Update", self.name, "new_customer", new_customer.name)
        frappe.db.set_value("Customer Master Update", self.name, "customer_primary_contact", '')

        if self.other_cust_address:
            frappe.db.set_value("Customer Master Update", self.name, "address_title", new_customer.name)

        self.reload()
        frappe.msgprint(f"New Customer '{new_customer.name}' has been successfully created.")

    def on_update_after_submit(self):
        self.create_supplier_address_contact()
        if self.workflow_state != 'Completed':
            frappe.msgprint(f"Customer address/contact has been successfully created.")
        
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
                address_doc.country = self.add_country
                address_doc.pincode = self.pincode
                address_doc.email_address = self.email_address
                address_doc.phone = self.phone
                if self.gstin__uin:
                    address_doc.gstin = self.gstin__uin
                    
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
            else:
                frappe.throw(f"{self.address_title} Address Title is reqd..") 
        if self.workflow_state == "Create Contact":
            if self.phone:
                contact_doc = frappe.new_doc("Contact")
                contact_doc.company_name = self.customer_name 
            
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
            else:
                frappe.throw(f"{self.phone}Phone is reqd..") 
        if self.workflow_state == "Create Bank Account":
            if self.bank:
                bank_acc = frappe.new_doc("Bank Account")
                bank_acc.account_name = self.customer_name
                bank_acc.bank = self.bank 
                bank_acc.account_type = self.account_type
                bank_acc.party_type = "Customer" 
                bank_acc.party = self.new_customer
                bank_acc.branch_code = self.branch_code
                bank_acc.bank_account_no = self.bank_account_no
                bank_acc.insert(ignore_permissions=True)
                bank_acc.save()

                # frappe.throw(f"{bank_acc.name}")
                frappe.db.set_value("Customer Master Update", self.name,"bank_account",bank_acc.name)
                self.reload()

                frappe.msgprint("Customer Bank Account Created ")
            else:
                frappe.throw(f"{self.bank} Bank is reqd..") 

# if self.workflow_state == 'Update Customer' or self.workflow_state == 'Create Customer':      
#             fields_mapping = {
#                 "sequence": "custom_sequence",
#                 "salutation": "salutation",
#                 "customer_codes": "custom_customer_code",
#                 "customer_group": "customer_group",
#                 "customer_type": "customer_type",
#                 "gst_category": "gst_category",
#                 "export_type": "export_type",
#                 "old_customer_code": "old_customer_code",
#                 "customer_grade": "custom_customer_grade",
#                 "territory": "territory",
#                 "territory_code": "custom_territory_code",
#                 "gender": "gender",
#                 "vendor_code": "vendor_code",
#                 "from_lead": "lead_name",
#                 "from_opportunity": "opportunity_name",
#                 "from_prospect": "prospect_name",
#                 "account_manager": "account_manager",
#                 "image": "image",
#                 "certification_charges": "custom_certification_charges",
#                 "ignore_po_creation_for_certification": "custom_ignore_po_creation_for_certification",
#                 "default_price_list": "default_price_list",
#                 "default_company_bank_account": "default_bank_account",
#                 "default_payment_terms_template": "payment_terms",
#                 "is_internal_customer": "is_internal_customer",
#                 "represents_company": "represents_company",
#                 "is_customer_exempted_from_sales_tax": "exempt_from_sales_tax",
#                 "market_segment": "market_segment",
#                 "industry": "industry",
#                 "customer_pos_id": "customer_pos_id",
#                 "website": "website",
#                 "print_language": "language",
#                 "customer_details": "customer_details",
#                 "gemstone_price_multiplier": "custom_gemstone_price_multiplier",
#                 "customer_primary_contact": "customer_primary_contact",
#                 "customer_primary_address": "customer_primary_address",
#                 "mobile_no": "mobile_no",
#                 "email_id": "email_id",
#                 "tax_id": "tax_id",
#                 "tax_withholding_category": "tax_withholding_category",
#                 "gstin__uin": "gstin",
#                 "pan": "pan",
#                 "loyalty_program": "loyalty_program",
#                 "loyalty_program_tier": "loyalty_program_tier",
#                 "sales_partner": "default_sales_partner",
#                 "commission_rate": "default_commission_rate",
#                 "allow_sales_invoice_creation_without_sales_order": "so_required",
#                 "allow_sales_invoice_creation_without_delivery_note": "dn_required",
#                 "is_frozen": "is_frozen",
#                 "disabled": "disabled",
#                 "tax_category": "tax_category",
#                 "is_internal_customer": "is_internal_customer",
#                 "represents_company": "represents_company",
#                 "brand": "brand",
#                 "cfa": "cfa",
#                 "custom_sketch_workflow_state": "custom_sketch_workflow_state",
#                 "custom_order_workflow_state": "custom_order_workflow_state",
#                 "custom_consider_2_digit_for_bom": "custom_consider_2_digit_for_bom",
#                 "custom_consider_2_digit_for_diamond": "custom_consider_2_digit_for_diamond",
#                 "custom_consider_2_digit_for_gemstone": "custom_consider_2_digit_for_gemstone",
#                 "custom_advanced_manual_bagging_available": "custom_advanced_manual_bagging_available",
#                 "custom_require_customer_bulk_numbers": "custom_require_customer_bulk_numbers",
#                 "custom_allowed_item_category_for_invoice": "custom_allowed_item_category_for_invoice",
#                 "custom_approval_warehouse": "custom_approval_warehouse",
#                 "compute_making_charges_on": "compute_making_charges_on",
#                 "diamond_price_list": "diamond_price_list",
#                 "custom_gemstone_price_list_type": "custom_gemstone_price_list_type"
#             }

#             credit_limit_data = self.get("credit_limit")
#             sales_team_data = self.get("sales_team")
#             allowed_to_transact_with = self.get("allowed_to_transact_with")
#             order_type_criteria = self.get("custom_order_type_criteria")
#             sales_type = self.get("sales_type")
#             metal_criteria = self.get("metal_criteria")
#             diamond_grades = self.get("diamond_grades")

#             accounts_data = self.get("accounts")

#             if frappe.db.exists("Customer", self.customer_data):
#                 try:
#                     customer_doc = frappe.get_doc("Customer", self.customer_data)

#                     for source_field, target_field in fields_mapping.items():
#                         # source_field = 'gst_category'
#                         new_value = self.get(source_field)
#                         if new_value is not None:
#                             # frappe.throw(f"{customer_doc} || {source_field} || {new_value}")
#                             customer_doc.set(target_field, new_value)

                
#                     if credit_limit_data:
#                         customer_doc.credit_limits = []
#                         for row in credit_limit_data:
#                             customer_doc.append("credit_limits", {
#                                 "company": row.get("company"),
#                                 "credit_limit": row.get("credit_limit"),
#                                 "bypass_credit_limit_check": row.get("bypass_credit_limit_check"),
#                             })

#                     if sales_team_data:
#                         customer_doc.sales_team = []
#                         for row in sales_team_data:
#                             customer_doc.append("sales_team", {
#                                 "sales_person": row.get("sales_person"),
#                                 "contact_no": row.get("contact_no"),
#                                 "allocated_percentage": row.get("allocated_percentage"),
#                                 "allocated_amount": row.get("allocated_amount"),
#                                 "commission_rate": row.get("commission_rate"),
#                                 "incentives": row.get("incentives"),
#                             })

#                     if accounts_data:
#                         customer_doc.accounts = []
#                         for row in accounts_data:
#                             customer_doc.append("accounts", {
#                                 "company": row.get("company"),
#                                 "account": row.get("account"),
#                                 "advance_account": row.get("advance_account"),
#                             })
                    
#                     if order_type_criteria:
#                         customer_doc.custom_order_type_criteria = []
#                         for row in order_type_criteria:
#                             customer_doc.append("custom_order_type_criteria", {
#                                 "order_type": row.get("order_type"),
#                                 "flow_type": row.get("flow_type")
#                             })
                    
#                     if sales_type:
#                         customer_doc.sales_type = []
#                         for row in sales_type:
#                             customer_doc.append("sales_type", {
#                                 "sales_type": row.get("sales_type"),
#                                 "tax_rate": row.get("tax_rate")
#                             })
                    
#                     if metal_criteria:
#                         customer_doc.metal_criteria = []
#                         for row in metal_criteria:
#                             customer_doc.append("metal_criteria", {
#                                 "metal_type": row.get("metal_type"),
#                                 "metal_touch": row.get("metal_touch"),
#                                 "metal_purity": row.get("metal_purity")
#                             })
                    
#                     if diamond_grades:
#                         customer_doc.diamond_grades = []
#                         for row in diamond_grades:
#                             customer_doc.append("diamond_grades", {
#                                 "diamond_quality": row.get("diamond_quality"),
#                                 "diamond_grade_1": row.get("diamond_grade_1"),
#                                 "diamond_grade_2": row.get("diamond_grade_2"),
#                                 "diamond_grade_3": row.get("diamond_grade_3"),
#                                 "diamond_grade_4": row.get("diamond_grade_4")
#                             })

#                     # Save the updated Customer document
#                     customer_doc.save(ignore_permissions=True)
#                     frappe.db.commit()
#                     frappe.msgprint("Customer has been updated successfully.")

#                 except Exception as e:
#                     frappe.log_error(frappe.get_traceback(), "Customer Update Error")
#                     frappe.throw(f"An error occurred while updating the customer: {str(e)}")
#             else:
#                     # Prepare data for the new Customer record
#                     customer_data = {
#                         target_field: self.get(source_field)
#                         for source_field, target_field in fields_mapping.items()
#                         if self.get(source_field) is not None
#                     }

#                     # Add mandatory fields
#                     customer_data["doctype"] = "Customer"
#                     customer_data["customer_name"] = self.get("customer_name")
#                     customer_data["customer_group"] = customer_data.get("customer_group") or "Default Customer Group"
#                     customer_data["territory"] = customer_data.get("territory")
#                     customer_data["customer_type"] = customer_data.get("customer_type") or "Company"

#                     # Add child table data for credit limits
#                     if credit_limit_data:
#                         customer_data["credit_limits"] = [
#                             {
#                                 "company": row.get("company"),
#                                 "credit_limit": row.get("credit_limit"),
#                                 "bypass_credit_limit_check": row.get("bypass_credit_limit_check"),
#                             }
#                             for row in credit_limit_data
#                         ]

#                     # Add child table data for sales team
#                     if sales_team_data:
#                         customer_data["sales_team"] = [
#                             {
#                                 "sales_person": row.get("sales_person"),
#                                 "contact_no": row.get("contact_no"),
#                                 "allocated_percentage": row.get("allocated_percentage"),
#                                 "allocated_amount": row.get("allocated_amount"),
#                                 "commission_rate": row.get("commission_rate"),
#                                 "incentives": row.get("incentives"),
#                             }
#                             for row in sales_team_data
#                         ]

#                     if allowed_to_transact_with:
#                         if customer_data["is_internal_customer"]:
#                             customer_data["companies"] = [
#                                 {
#                                     "company": row.get("company"),
#                                 }
#                                 for row in allowed_to_transact_with
#                             ]

#                     # Add child table data for accounts
#                     if accounts_data:
#                         customer_data["accounts"] = [
#                             {
#                                 "company": row.get("company"),
#                                 "account": row.get("account"),
#                                 "advance_account": row.get("advance_account"),
#                             }
#                             for row in accounts_data
#                         ]
                    
#                     if order_type_criteria:
#                         customer_data["custom_order_type_criteria"] = [
#                             {
#                                 "order_type": row.get("order_type"),
#                                 "flow_type": row.get("flow_type")
#                             }
#                             for row in order_type_criteria
#                         ]
                    
#                     if sales_type:
#                         customer_data["sales_type"] = [
#                             {
#                                 "sales_type": row.get("sales_type"),
#                                 "tax_rate": row.get("tax_rate")
#                             }
#                             for row in sales_type
#                         ]
#                     if metal_criteria:
#                         customer_data["metal_criteria"] = [
#                             {
#                                 "metal_type": row.get("metal_type"),
#                                 "metal_touch": row.get("metal_touch"),
#                                 "metal_purity": row.get("metal_purity")
#                             }
#                             for row in metal_criteria
#                         ]
#                     if diamond_grades:
#                         customer_data["diamond_grades"] = [
#                             {
#                                 "diamond_quality": row.get("diamond_quality"),
#                                 "diamond_grade_1": row.get("diamond_grade_1"),
#                                 "diamond_grade_2": row.get("diamond_grade_2"),
#                                 "diamond_grade_3": row.get("diamond_grade_3"),
#                                 "diamond_grade_4": row.get("diamond_grade_4")

#                             }
#                             for row in diamond_grades
#                         ]


#                     # Create the new Customer record
#                     new_customer = frappe.get_doc(customer_data)
#                     new_customer.insert(ignore_permissions=True)
                    
#                     frappe.db.set_value("Customer Master Update", self.name, "new_customer", new_customer.name)
#                     frappe.db.set_value("Customer Master Update", self.name, "customer_primary_contact", '')
#                     if self.other_cust_address:
#                         frappe.db.set_value("Customer Master Update", self.name, "address_title", new_customer.name)          
#                     self.reload()
                    
#                     frappe.msgprint(f"New Customer '{new_customer.name}' has been successfully created.")
    
