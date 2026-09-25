# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class SalaryWithholdingRelease(Document):
	def validate(self):
		if flt(self.amount) <= 0:
			frappe.throw(
				_("Release amount must be greater than zero in the release history"),
				title=_("Invalid Release Amount"),
			)
