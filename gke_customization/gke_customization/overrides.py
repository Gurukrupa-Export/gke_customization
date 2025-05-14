import frappe
from erpnext.controllers import accounts_controller

# Override to skip address validation
def bypass_validate_party_address(self, party_type, party):
    frappe.logger().info("Bypassed validate_party_address for Sales Order")

# Monkey-patch the method
accounts_controller.AccountsController.validate_party_address = bypass_validate_party_address
