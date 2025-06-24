import frappe

def validate(self, method=None):
    if not self.to_shareholder:
        return

    # Get folio number from Shareholder
    shareholder_folio = frappe.db.get_value('Shareholder', self.to_shareholder, 'custom_folio_number')

    # If transfer type is 'Issue'
    if self.transfer_type == "Issue":
        if shareholder_folio:
            self.custom_folio_number = shareholder_folio
        else:
            # Try to fetch existing folio from previous transfers for same shareholder
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

            # Update Shareholder folio number
            frappe.db.set_value('Shareholder', self.to_shareholder, 'custom_folio_number', self.custom_folio_number)

    # If transfer type is 'Transfer'
    elif self.transfer_type == "Transfer":
        issue_folio = frappe.db.get_value('Shareholder', {
            'name': self.to_shareholder,
            'docstatus': ["in", [0, 1]]
        }, 'custom_folio_number')

        from_issue_folio = frappe.db.get_value('Shareholder', {
            'name': self.from_shareholder,
            'docstatus': ["in", [0, 1]]
        }, 'custom_folio_number')

        if issue_folio:
            self.custom_folio_number = issue_folio
        else:
            max_folio = frappe.db.sql("""
                SELECT MAX(CAST(custom_folio_number AS UNSIGNED)) FROM `tabShare Transfer`
                WHERE custom_folio_number IS NOT NULL AND docstatus IN (0, 1)
            """)[0][0]
            new_folio = (max_folio or 0) + 1
            self.custom_folio_number = new_folio

            # Update Shareholder folio number
            frappe.db.set_value('Shareholder', self.to_shareholder, 'custom_folio_number', new_folio)

        if from_issue_folio:
            self.custom_from_folio_number = from_issue_folio


def _clear_folio_if_last_transfer(self):
    """Clear folio number from Shareholder if this is the last active/cancelled transfer."""
    if self.to_shareholder:
        other_transfers = frappe.db.exists('Share Transfer', {
            'to_shareholder': self.to_shareholder,
            'name': ['!=', self.name],
            'docstatus': ['in', [0, 1]]
        })
        if not other_transfers:
            frappe.db.set_value('Shareholder', self.to_shareholder, 'custom_folio_number', None)

    # Also clear from_shareholder folio if this is a Transfer and last one
    if self.transfer_type == "Transfer" and self.from_shareholder:
        other_transfers_from = frappe.db.exists('Share Transfer', {
            'from_shareholder': self.from_shareholder,
            'name': ['!=', self.name],
            'docstatus': ['in', [0, 1]]
        })
        if not other_transfers_from:
            frappe.db.set_value('Shareholder', self.from_shareholder, 'custom_folio_number', None)


def on_trash(self, method=None):
    _clear_folio_if_last_transfer(self)


def on_cancel(self, method=None):
    _clear_folio_if_last_transfer(self)