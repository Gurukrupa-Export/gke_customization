import frappe
from erpnext.controllers import accounts_controller

# Custom override function
def custom_validate_party_address(self, party, party_type, billing_address, shipping_address=None):
    
    # Bypass logic: only for Sales Order + condition
    if self.doctype in ["Sales Order","Delivery Note","Sales Invoice"] and getattr(self, "skip_address_check", False):
        if self.company == 'Sadguru Diamond' and self.customer == 'MHCU0022':
            frappe.logger().info("Skipping address validation on Sales Order")
            return

        # Default behavior
        else:
            if billing_address or shipping_address:
                party_address = frappe.get_all(
                    "Dynamic Link",
                    {
                        "link_doctype": party_type,
                        "link_name": party,
                        "parenttype": "Address"
                    },
                    pluck="parent",
                )
                if billing_address and billing_address not in party_address:
                    frappe.throw(("Billing Address does not belong to the {0}").format(party))
                elif shipping_address and shipping_address not in party_address:
                    frappe.throw(("Shipping Address does not belong to the {0}").format(party))

# Perform patch
accounts_controller.AccountsController.validate_party_address = custom_validate_party_address
