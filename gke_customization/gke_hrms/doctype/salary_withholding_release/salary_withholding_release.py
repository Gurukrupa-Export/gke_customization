# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class SalaryWithholdingRelease(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		journal_entry: DF.Link
		payroll_entry: DF.Link | None
		posting_date: DF.Date | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		salary_withholding_cycle: DF.Data | None
		status: DF.Literal["Draft", "Released", "Cancelled"]
	# end: auto-generated types

	def validate(self):
		if flt(self.amount) <= 0:
			frappe.throw(
				_("Release amount must be greater than zero in the release history"),
				title=_("Invalid Release Amount"),
			)
