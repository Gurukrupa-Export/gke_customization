# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SurveyQuestion(Document):
	def validate(self):
		if self.answer_type == "Checkbox" and not self.description:
			frappe.throw("Description is required for Checkbox type questions. Add options in description.")
