
import frappe
def validate(self, method=None):
    if self.transfer_type == "Issue" and self.to_shareholder:
        shareholder_folio = frappe.db.get_value('Shareholder', self.to_shareholder, 'custom_folio_number')

        if shareholder_folio:
            self.custom_folio_number = shareholder_folio
        else:
            existing = frappe.db.get_value('Share Transfer', {
                'to_shareholder': self.to_shareholder,
                'custom_folio_number': ['!=', None],
                'docstatus': ["in", [0, 1]],
                'name': ['!=', self.name]
            }, 'custom_folio_number')

            if existing:
                self.custom_folio_number = existing
            else:
                max_folio = frappe.db.sql("""
                    SELECT MAX(CAST(custom_folio_number AS UNSIGNED)) FROM `tabShare Transfer`
                    WHERE custom_folio_number IS NOT NULL AND docstatus IN (0, 1)
                """)[0][0]

                self.custom_folio_number = (max_folio or 0) + 1

            frappe.db.set_value('Shareholder', self.to_shareholder, 'custom_folio_number', self.custom_folio_number)

    elif self.transfer_type == "Transfer" and self.to_shareholder:
        issue_folio = frappe.db.get_value('Shareholder',{ 'name': self.to_shareholder,'docstatus': ["in", [0, 1]] },'custom_folio_number')
        from_issue_folio = frappe.db.get_value('Shareholder',{ 'name': self.from_shareholder,'docstatus': ["in", [0, 1]] },'custom_folio_number')
        if issue_folio:
            self.custom_folio_number = issue_folio
        if from_issue_folio:
            self.custom_from_folio_number = from_issue_folio