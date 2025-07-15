# # Copyright (c) 2025, Gurukrupa Export and contributors
# # For license information, please see license.txt

# # import frappe
# import frappe
# from frappe import _, msgprint
# from frappe.model.document import Document


# class EmployeeAnnexure(Document):

# 	def validate(self):
# 		if not self.salary_structure:
# 			frappe.throw("select a Salary Structure before save")
# 		self.earnings = []
# 		self.deductions = []
# 		base = self.ctc
# 		custom_is_esic_applicable=frappe.db.get_value('Employee',self.employee,'custom_is_esic_applicable')
# 		gross_pay = base if custom_is_esic_applicable else 0
# 		custom_state=frappe.db.get_value('Employee',self.employee,'custom_state')	
# 		component_values = {
# 			"base": base,
# 			"gross_pay": gross_pay,
# 			"custom_state": custom_state
# 			# "custom_month": custom_month
# 		}
# 		# component_values = {"base": base}
# 		salary_structure = frappe.get_doc("Salary Structure", self.salary_structure)

# 		for row in salary_structure.earnings:
# 			salary_component = frappe.get_doc("Salary Component", row.salary_component)
# 			statistical_component=salary_component.statistical_component
# 			abbr = row.abbr
# 			amount=row.amount
# 			amount = self.evaluate_formula(row.formula, component_values)
# 			component_values[abbr] = amount
			
# 			if amount:
# 				if not statistical_component :
# 					self.append("earnings", {
# 						"component": row.salary_component,
# 						"amount": amount,
# 						"abbr": abbr
					
# 			})
# 		for row in salary_structure.deductions:
# 			abbr = row.abbr
# 			amount=row.amount
# 			amount = self.evaluate_formula(row.formula, component_values)
# 			component_values[abbr] = amount

# 			component_values["gross_pay"] = gross_pay
# 			# if amount:
# 			self.append("deductions", {
# 				"component": row.salary_component,
# 				"amount": amount,
# 				"abbr": row.abbr
# 	})    
# 	def evaluate_formula(self, formula, context):
# 		if not formula:
# 			return 0
# 		try:
# 			for key in list(context.keys()):
# 				val = context[key]
# 				if isinstance(val, str):
# 					try:
# 						context[key] = float(val)
# 					except ValueError:
# 						pass
# 			return frappe.safe_eval(formula, context)
# 		except Exception as e:
# 			frappe.msgprint(f"Error evaluating formula '{formula}': {e}")
# 			return 0

# 	# def evaluate_formula(self, formula, context):
# 	# 	if not formula:
# 	# 		return 0
# 	# 	try:
	
# 	# 		for key, value in context.items():
# 	# 			if isinstance(value, str):
# 	# 				try:
# 	# 					context[key] = float(value)
# 	# 				except ValueError:
# 	# 					pass  # Ignore if not convertible
# 	# 	except Exception as e:
# 	# 		print(f"Error evaluating formula: {e}")
# 	# 		return 0			



import frappe
from frappe import _, msgprint
from frappe.model.document import Document
from frappe.utils import getdate

class EmployeeAnnexure(Document):

	def autoname(self):
		company_abbr = frappe.db.get_value("Company", self.company, "abbr")
		if company_abbr:
			if self.branch:
				branch_short = self.branch.split('-')[-2] 
				series = f"{company_abbr}-{branch_short}-EAX-.#####"
			else:
				series = f"{company_abbr}-EAX-.#####"

			self.name = frappe.model.naming.make_autoname(series)

	def validate(self):
		if self.get("__islocal") or not self.name:
			existing = frappe.db.exists(
				"Employee Annexure",
				{
					"employee": self.employee,
					"name": ["!=", self.name]  
				}
			)
			if existing:

				link = frappe.utils.get_link_to_form("Employee Annexure", existing)
				frappe.throw(f"Employee Annexure already exists for this employee , {link}")

		if not self.salary_structure:
			frappe.throw("Select a Salary Structure before saving.")
		# if self.get("__islocal"):
		# 	self.earnings = []
		# 	self.deductions = []

		base = self.ctc
		# custom_is_esic_applicable = frappe.db.get_value('Employee', self.employee, 'custom_is_esic_applicable')
		gross_pay = base #if custom_is_esic_applicable else 0
		# custom_state = frappe.db.get_value('Employee', self.employee, 'custom_state')
		custom_state=frappe.db.get_value('Branch',self.branch,'state')
		custom_month = getdate().month
		component_values = {
			"base": base,
			"gross_pay": gross_pay,
			"custom_state": custom_state,
			"custom_month": custom_month
		}

		salary_structure = frappe.get_doc("Salary Structure", self.salary_structure)

		for row in salary_structure.earnings:
			salary_component = frappe.get_doc("Salary Component", row.salary_component)
			abbr = row.abbr
			amount = self.evaluate_formula(row.formula, component_values)
			component_values[abbr] = amount

			if amount and not salary_component.statistical_component:
				self.append("earnings", {
					"component": row.salary_component,
					"amount": amount,
					"abbr": abbr,
					"formula":row.formula
				})


		for row in salary_structure.deductions:
			abbr = row.abbr
			amount = self.evaluate_formula(row.formula, component_values)
			component_values[abbr] = amount
			if not self.is_esic_applicable:
					if row.abbr=='ESIC':
						amount=0
			if row.abbr=='LWF':
				amount=0
			if  not self.is_pf_applicable:
				if row.abbr=='PF':
					amount=0	
			component_values[abbr] = amount		
			if amount:

				self.append("deductions", {
					"component": row.salary_component,
					"amount": amount,
					"abbr": abbr,
					"formula":row.formula
				})
		# frappe.msgprint(f"{custom_state},{custom_month},{gross_pay}")
	def evaluate_formula(self, formula, context):
		if not formula:
			return 0
		try:
			for key in list(context.keys()):
				val = context[key]
				if isinstance(val, str):
					try:
						context[key] = float(val)
					except ValueError:
						pass  
			return frappe.safe_eval(formula, context)
		except Exception as e:
			# frappe.msgprint(f"Error evaluating formula '{formula}': {e}")
			return 0
