# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class KGGKSyncLog(Document):
	def on_trash(self):
		# A run that is still going will keep writing to this document from a background
		# worker; deleting it underneath the worker turns a clean run into a stack trace.
		if self.status in ("Queued", "Running"):
			frappe.throw(_("This run is still {0}. Wait for it to finish before deleting it.").format(self.status))
