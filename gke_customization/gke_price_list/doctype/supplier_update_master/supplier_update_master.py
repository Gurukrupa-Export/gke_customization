# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class SupplierUpdateMaster(Document):
    pass


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
            # Create a new Supplier record if it doesn't exist
            try:
                # Prepare data for the new Supplier record
                supplier_data = {
                    target_field: self.get(source_field)
                    for source_field, target_field in fields_mapping.items()
                    if self.get(source_field) is not None
                }

                # Add mandatory fields
                supplier_data["doctype"] = "Supplier"
                supplier_data["supplier_name"] = self.get("supplier_name") or "Unnamed Supplier"
                supplier_data["supplier_group"] = supplier_data.get("supplier_group") or "Default Supplier Group"
                supplier_data["territory"] = supplier_data.get("territory") or "All Territories"
                supplier_data["supplier_type"] = supplier_data.get("supplier_type") or "Company"

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
                    supplier_data["allowed_to_transact_with"] = [
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
                new_supplier = frappe.get_doc(supplier_data)
                new_supplier.insert(ignore_permissions=True)
                frappe.db.commit()

            except Exception as e:
                frappe.log_error(frappe.get_traceback(), "Supplier Creation Error")
                frappe.throw(f"An error occurred while creating the supplier: {str(e)}")

