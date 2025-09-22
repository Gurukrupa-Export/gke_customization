import frappe
from frappe import _

def gke_custom_validate_account_party_type(self):
        if self.is_cancelled:
            return

        if self.party_type and self.party:
            account_type = frappe.get_cached_value("Account", self.account, "account_type")
            if account_type and (account_type not in ["Receivable", "Payable", "Equity", "Liability"]):
                frappe.throw(
                    _("Party Type and Party can only be set for Receivable / Payable account<br><br>{0}")
                    .format(self.account)
                )
