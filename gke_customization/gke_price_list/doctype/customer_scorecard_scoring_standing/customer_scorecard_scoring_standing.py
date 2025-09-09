# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CustomerScorecardScoringStanding(Document):
	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		# employee_link: DF.Link | None
		max_grade: DF.Percent
		min_grade: DF.Percent
		# notify_employee: DF.Check
		# notify_supplier: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		# prevent_pos: DF.Check
		# prevent_rfqs: DF.Check
		standing_color: DF.Literal["Blue", "Purple", "Green", "Yellow", "Orange", "Red"]
		standing_name: DF.Link | None
		# warn_pos: DF.Check
		# warn_rfqs: DF.Check
	# end: auto-generated types

	

	pass
