# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CustomerScorecardScoringCriteria(Document):
	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		criteria_name: DF.Link
		formula: DF.SmallText | None
		max_score: DF.Float
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		score: DF.Percent
		weight: DF.Percent
	pass
