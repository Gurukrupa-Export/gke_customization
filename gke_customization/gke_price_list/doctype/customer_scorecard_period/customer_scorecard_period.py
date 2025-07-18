# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _, throw
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


import gke_customization.gke_price_list.doctype.customer_scorecard_variable.customer_scorecard_variable as variable_functions
from gke_customization.gke_price_list.doctype.customer_scorecard_criteria.customer_scorecard_criteria import (
	get_variables,
)

class CustomerScorecardPeriod(Document):
	

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:	
		from frappe.types import DF

		from gke_customization.gke_price_list.doctype.customer_scorecard_scoring_criteria.customer_scorecard_scoring_criteria import (
			CustomerScorecardScoringCriteria,
		)
		from gke_customization.gke_price_list.doctype.customer_scorecard_scoring_variable.customer_scorecard_scoring_variable import (
			CustomerScorecardScoringVariable,
		)

		amended_from: DF.Link | None
		criteria: DF.Table[CustomerScorecardScoringCriteria]
		end_date: DF.Date
		naming_series: DF.Literal["PU-SSP-.YYYY.-"]
		scorecard: DF.Link
		start_date: DF.Date
		supplier: DF.Link
		total_score: DF.Percent
		variables: DF.Table[CustomerScorecardScoringVariable]


	def validate(self):
		self.validate_criteria_weights()
		self.calculate_variables()
		self.calculate_criteria()
		self.calculate_score()

	def validate_criteria_weights(self):
		weight = 0
		for c in self.criteria:
			weight += c.weight

		if weight != 100:
			throw(_("Criteria weights must add up to 100%"))


	def calculate_variables(self):
		# l = []
		for var in self.variables:
			if "." in var.path:
				method_to_call = import_string_path(var.path)

				var.value = method_to_call(self)
			else:
				method_to_call = getattr(variable_functions, var.path)
				var.value = method_to_call(self)
		# 		l.append([var.param_name, var.value])
		# frappe.throw(f"{l}")

	def calculate_criteria(self):
		for crit in self.criteria:
			try:
				crit.score = min(
					crit.max_score,
					max(
						0,
						frappe.safe_eval(
							self.get_eval_statement(crit.formula), None, {"max": max, "min": min}
						),
					),
				)
			except Exception:
				frappe.throw(
					_(
						"Could not solve criteria score function for {0}. Make sure the formula is valid."
					).format(crit.criteria_name),
					frappe.ValidationError,
				)
				crit.score = 0
		

	def calculate_score(self):
		myscore = 0
		for crit in self.criteria:
			myscore += crit.score * crit.weight / 100.0
		self.total_score = myscore

	def calculate_weighted_score(self, weighing_function):
		try:
			weighed_score = frappe.safe_eval(
				self.get_eval_statement(weighing_function), None, {"max": max, "min": min}
			)
		except Exception:
			frappe.throw(
				_("Could not solve weighted score function. Make sure the formula is valid."),
				frappe.ValidationError,
			)
			weighed_score = 0
		return weighed_score

	def get_eval_statement(self, formula):
		my_eval_statement = formula.replace("\r", "").replace("\n", "")

		for var in self.variables:
			if var.value:
				if var.param_name in my_eval_statement:
					my_eval_statement = my_eval_statement.replace(
						"{" + var.param_name + "}", f"{var.value:.2f}"
					)
			else:
				if var.param_name in my_eval_statement:
					my_eval_statement = my_eval_statement.replace("{" + var.param_name + "}", "0.0")

		return my_eval_statement

def import_string_path(path):
	components = path.split(".")
	mod = __import__(components[0])
	for comp in components[1:]:
		mod = getattr(mod, comp)
	return mod

def make_customer_scorecard(source_name, target_doc=None):
	def update_criteria_fields(obj, target, source_parent):
		target.max_score, target.formula = frappe.db.get_value(
			"Customer Scorecard Criteria", obj.criteria_name, ["max_score", "formula"]
		)

	def post_process(source, target):
		variables = []
		for cr in target.criteria:
			for var in get_variables(cr.criteria_name):
				if var not in variables:
					variables.append(var)
		target.extend("variables", variables)

	doc = get_mapped_doc(
		"Customer Scorecard",
		source_name,
		{
			"Customer Scorecard": {"doctype": "Customer Scorecard Period"},
			"Customer Scorecard Scoring Criteria": {
				"doctype": "Customer Scorecard Scoring Criteria",
				"postprocess": update_criteria_fields,
			},
		},
		target_doc,
		post_process,
		ignore_permissions=True,
	)
	return doc
