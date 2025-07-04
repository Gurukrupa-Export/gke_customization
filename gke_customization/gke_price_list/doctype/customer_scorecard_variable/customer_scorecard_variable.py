# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import sys

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import getdate


class VariablePathNotFound(frappe.ValidationError):
	pass

class CustomerScorecardVariable(Document):
	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.SmallText | None
		is_custom: DF.Check
		param_name: DF.Data
		path: DF.Data
		variable_label: DF.Data

	def validate(self):
		self.validate_path_exists()

	def validate_path_exists(self):
		if "." in self.path:
			try:
				from gke_customization.gke_price_list.doctype.customer_scorecard_period.customer_scorecard_period import (
					import_string_path,
				)

				import_string_path(self.path)
			except AttributeError:
				frappe.throw(_("Could not find path for " + self.path), VariablePathNotFound)

		else:
			if not hasattr(sys.modules[__name__], self.path):
				frappe.throw(_("Could not find path for " + self.path), VariablePathNotFound)


def get_ordered_qty(scorecard):
	"""Returns the total number of ordered quantity (based on Sales Orders made by the customer)"""

	so = frappe.qb.DocType("Sales Order")

	return (
		frappe.qb.from_(so)
		.select(Sum(so.total_qty))
		.where(
			(so.customer == scorecard.customer)
			& (so.docstatus == 1)
			& (so.transaction_date >= scorecard.start_date)
			& (so.transaction_date <= scorecard.end_date)
		)
	).run(as_list=True)[0][0] or 0