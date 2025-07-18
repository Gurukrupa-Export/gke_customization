# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt
# check push
from __future__ import unicode_literals
from frappe.utils import flt
import frappe
from frappe.utils.data import now_datetime
from frappe import _
from frappe.model.document import Document,json
from frappe.model.mapper import get_mapped_doc
from frappe.utils import get_link_to_form
from erpnext.setup.utils import get_exchange_rate
from erpnext.controllers.item_variant import create_variant, get_variant

class Order(Document):
	def on_submit(self):
		item_variant = create_line_items(self)
		if self.bom_or_cad == 'Duplicate BOM' or (self.design_type == 'Mod - Old Stylebio & Tag No' and self.bom_type == 'Duplicate BOM'):
			if (self.mod_reason == 'Change in Metal Touch'):
				new_bom = create_bom_for_touch(self,item_variant)
				frappe.db.set_value("Order",self.name,"new_bom",new_bom)
				frappe.msgprint(_("New BOM Created: {0}".format(get_link_to_form("BOM",new_bom))))
				self.reload()
			else:
				new_bom = create_bom(self,item_variant)
				frappe.db.set_value("Order",self.name,"new_bom",new_bom)
				frappe.msgprint(_("New BOM Created: {0}".format(get_link_to_form("BOM",new_bom))))
				self.reload()

	def validate(self):
		if self.order_type != 'Purchase':
			cerate_timesheet(self)
		calculate_metal_weights(self)
		calculate_finding_weights(self)
		calculate_diamond_weights(self)
		calculate_gemstone_weights(self)
		calculate_other_weights(self)
		calculate_total(self)
		if self.is_finding_order and self.workflow_state == 'Update Item':
			check_finding_code(self)
		
	def on_update_after_submit(self):
		if self.is_repairing == 0 and (self.design_type == 'Mod - Old Stylebio & Tag No' and self.bom_type != 'Duplicate BOM'):
			cerate_bom_timesheet(self)
		calculate_metal_weights(self)
		calculate_finding_weights(self)
		calculate_diamond_weights(self)
		calculate_gemstone_weights(self)
		calculate_other_weights(self)
		calculate_total(self)
		if (self.workflow_state == 'Approved' and self.mod_reason not in ['Change in Metal Touch','Change in Metal Colour']) and (self.is_finding_order==0) and (self.is_repairing==0) and self.bom_type != 'Duplicate BOM':
			timesheet = frappe.get_doc("Timesheet",{"order":self.name},"name")
			timesheet.run_method('submit')
		if self.workflow_state == 'Update BOM' and self.design_type == 'Sketch Design':
			update_variant_attributes(self)
	
	def on_cancel(self):
		if frappe.db.get_list("Timesheet",filters={"order":self.name},fields="name"):
			for timesheet in frappe.db.get_list("Timesheet",filters={"order",self.name},fields="name"):
				frappe.db.set_value("Timesheet",timesheet["name"],"docstatus","2")

		frappe.db.set_value("Order",self.name,"workflow_state","Cancelled")
		self.reload()

def calculate_metal_weights(self):
	total_metal_weight = 0
	for i in self.metal_detail:
		total_metal_weight += i.finish_product_weight
	self.total_metal_weight = total_metal_weight

def calculate_finding_weights(self):
	# total_finding_weightin_gms = 0
	total_finding_weight = 0
	total_finding_pcs = 0
	for i in self.finding_detail:
		total_finding_weight += i.quantity
		total_finding_pcs += i.qty
	self.total_finding_pcs = total_finding_pcs
	self.total_finding_weightin_gms = total_finding_weight

def calculate_diamond_weights(self):
	total_diamond_weight = 0
	total_diamond_pcs = 0
	for i in self.diamond_detail:
		total_diamond_weight += i.quantity
		total_diamond_pcs += i.pcs
		i.weight_in_gms = i.quantity/5
	self.total_diamond_weight = total_diamond_weight
	self.total_diamond_pcs = total_diamond_pcs
	self.total_diamond_weightin_gms = total_diamond_weight/5

def calculate_gemstone_weights(self):
	total_gemstone_weight = 0
	total_gemstone_pcs = 0
	for i in self.gemstone_detail:
		total_gemstone_weight += i.quantity
		total_gemstone_pcs += i.pcs
		i.weight_in_gms = i.quantity/5
	self.total_gemstone_weight = total_gemstone_weight
	self.total_gemstone_pcs = total_gemstone_pcs
	self.total_gemstone_weightin_gms = total_gemstone_weight/5

def calculate_other_weights(self):
	total_other_pcs = 0
	total_other_weight = 0
	for i in self.other_detail:
		total_other_weight += i.quantity
		total_other_pcs += i.qty
	self.total_other_weight = total_other_weight
	self.total_other_pcs = total_other_pcs

def calculate_total(self):
	"""Calculate the total weight of metal, diamond, gemstone, and finding.
	Also calculate the gold to diamond ratio, and the diamond ratio.
	"""
	self.metal_weight = self.total_metal_weight
	self.diamond_weight = sum(row.quantity for row in self.diamond_detail)
	self.gemstone_weight = sum(row.quantity for row in self.gemstone_detail)
	self.other_weight = sum(row.quantity for row in self.other_detail)
	self.finding_weight = sum(row.quantity for row in self.finding_detail)
	self.metal_and_finding_weight = flt(self.metal_weight) + flt(self.finding_weight)

	self.total_diamond_weight_in_gms = self.total_diamond_weightin_gms
	self.total_gemstone_weight_in_gms = self.total_gemstone_weightin_gms
	
	self.gross_weight = (
		flt(self.metal_and_finding_weight)
		+ flt(self.total_diamond_weight_in_gms)
		+ flt(self.total_gemstone_weight_in_gms)
		+ flt(self.total_other_weight)
	)

	self.gold_to_diamond_ratio = (
		flt(self.metal_and_finding_weight) / flt(self.diamond_weight) if self.diamond_weight else 0
	)
	self.diamond_ratio = (
		flt(self.diamond_weight) / flt(self.total_diamond_pcs) if self.total_diamond_pcs else 0
	)

	self.metal_to_diamond_ratio_excl_of_finding = (
		flt(self.metal_weight) / flt(self.diamond_weight) if self.diamond_weight else 0
	)
	if self.gold_to_diamond_ratio:
		ratio_value = float(self.gold_to_diamond_ratio)

		# Fetch the single GC Ratio Master document
		gc_ratio_master = frappe.get_single("GC Ratio Master")
		for row in gc_ratio_master.gc_ratio:
			range_text = row.metal_to_gold_ratio_group.strip()

			try:
				if '-' in range_text:
					lower, upper = [float(x.strip()) for x in range_text.split('-')]
					if lower <= ratio_value <= upper:
						self.rating = row.rating
						# frappe.msgprint(f"Found rating: {row.rating} for ratio {ratio_value} in range {lower}-{upper}")
						break

				elif 'Above' in range_text:
					threshold = float(range_text.replace('Above', '').strip())
					if ratio_value > threshold:
						self.rating = row.rating
						# frappe.msgprint(f"Found rating: {row.rating} for ratio {ratio_value} above {threshold}")
						break

				elif 'Below' in range_text:
					threshold = float(range_text.replace('Below', '').strip())
					if ratio_value < threshold:
						self.rating = row.rating
						# frappe.msgprint(f"Found rating: {row.rating} for ratio {ratio_value} below {threshold}")
						break

			except ValueError:
				frappe.msgprint(f"Skipping invalid range value: {range_text}")
	# net_wt_add_on

def cerate_timesheet(self):
	if not self.customer_order_form:
		if self.workflow_state == "Designing":
			# for assignment in self.designer_assignment:
			
			if len(self.designer_assignment)>1:
				for i in self.designer_assignment[:-1]:
					timesheet,docstatus = frappe.db.get_value("Timesheet", {"employee": i.designer,"order":self.name}, ["name","docstatus"])
					if docstatus == 0:
					# frappe.db.set_value("Timesheet",timesheet,"docstatus","1")
						timesheet_doc = frappe.get_doc("Timesheet", timesheet)
						if (timesheet_doc.time_logs):
							timesheet_doc.time_logs[-1].to_time = now_datetime()
							timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600
							timesheet_doc.save()
						timesheet_doc.run_method('submit')
				# frappe.throw(f"{time_sheet_list}")

			designer_value = self.designer_assignment[-1].designer
		

			# # Check if a timesheet document already exists for the employee
			timesheet = frappe.get_all(
				"Timesheet", filters={"employee": designer_value,"order":self.name}, fields=["name"],
			)
			if timesheet:
				timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])
			else:
				timesheet_doc = frappe.new_doc("Timesheet")
				timesheet_doc.employee = designer_value
			
			if (timesheet_doc.time_logs and 
				timesheet_doc.time_logs[-1].activity_type in ['CAD Designing','CAD Designing - On-Hold','QC Activity - On-Hold']) :
				timesheet_doc.time_logs[-1].to_time = now_datetime()
				timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600

			time_log = timesheet_doc.append("time_logs", {})
			time_log.activity_type = "CAD Designing"
			time_log.from_time = now_datetime()
			timesheet_doc.order = self.name			
			timesheet_doc.save()			

			frappe.msgprint("Timesheets created for CAD for each designer assignment") 

		elif self.workflow_state == "Sent to QC":
			# for assignment in self.designer_assignment:
			if len(self.designer_assignment)>1:
				for i in self.designer_assignment[:-1]:
					timesheet,docstatus = frappe.db.get_value("Timesheet", {"employee": i.designer,"order":self.name}, ["name","docstatus"])
					if docstatus == 0:
						timesheet_doc = frappe.get_doc("Timesheet", timesheet)
						if (timesheet_doc.time_logs):
							timesheet_doc.time_logs[-1].to_time = now_datetime()
							timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600
							timesheet_doc.save()
						timesheet_doc.run_method('submit')

			designer_value = self.designer_assignment[-1].designer
					# designer_value = assignment.designer

					# Check if a timesheet document already exists for the employee
			timesheet = frappe.get_all(
				"Timesheet", filters={"employee": designer_value,"order":self.name}, fields=["name"],
			)
			if timesheet:
				timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])

				if timesheet_doc.time_logs:	
					time_log = timesheet_doc.time_logs[-1]					
					time_log.to_time = now_datetime()
					time_log.completed = 1
					time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600

				qc_time_log = timesheet_doc.append("time_logs", {})
				qc_time_log.activity_type = "QC Activity"
				qc_time_log.from_time = now_datetime()
				qc_time_log.custom_cad_order_id = self.name				
				timesheet_doc.save()
			else:
				frappe.throw("Timesheets is not created for each designer assignment")		
			
			frappe.msgprint("Timesheets created for QC for each designer assignment")
		
		elif self.workflow_state == "Designing - On-Hold":
			# for assignment in self.designer_assignment:
					# designer_value = assignment.designer
			if len(self.designer_assignment)>1:
				for i in self.designer_assignment[:-1]:
					timesheet,docstatus = frappe.db.get_value("Timesheet", {"employee": i.designer,"order":self.name}, ["name","docstatus"])
					if docstatus == 0:
					# frappe.db.set_value("Timesheet",timesheet,"docstatus","1")
						timesheet_doc = frappe.get_doc("Timesheet", timesheet)
						if (timesheet_doc.time_logs):
							timesheet_doc.time_logs[-1].to_time = now_datetime()
							timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600
							timesheet_doc.save()
						timesheet_doc.run_method('submit')


			designer_value = self.designer_assignment[-1].designer
					# Check if a timesheet document already exists for the employee
					# timesheet = frappe.db.get_list("Timesheet",filters={"employee":designer_value,"order":self.name},fields=["name"])
			timesheet = frappe.get_all(
				"Timesheet", filters={"employee": designer_value,"order":self.name}, fields=["name"],
			)
			if timesheet:
				timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])

				if (timesheet_doc.time_logs):	
					time_log = timesheet_doc.time_logs[-1]					
					time_log.to_time = now_datetime()
					time_log.completed = 1
					time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600

				if not timesheet_doc.time_logs or timesheet_doc.time_logs[-1].activity_type != "CAD Designing - On-Hold":
					qc_time_log = timesheet_doc.append("time_logs", {})
					qc_time_log.activity_type = "CAD Designing - On-Hold"
					qc_time_log.from_time = now_datetime()
					qc_time_log.custom_cad_order_id = self.name				
					timesheet_doc.save()
			else:
				frappe.throw("Timesheets is not created for each designer assignment")		
			
			# frappe.msgprint("Timesheets created for Designing - On-Hold for each designer assignment")
		
		elif self.workflow_state == "Assigned":
			# for assignment in self.designer_assignment:
			# 		designer_value = assignment.designer
			if len(self.designer_assignment)>1:
				for i in self.designer_assignment[:-1]:
					timesheet,docstatus = frappe.db.get_value("Timesheet", {"employee": i.designer,"order":self.name}, ["name","docstatus"])
					if docstatus == 0:
						timesheet_doc = frappe.get_doc("Timesheet", timesheet)
						if (timesheet_doc.time_logs):
							timesheet_doc.time_logs[-1].to_time = now_datetime()
							timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600
							timesheet_doc.save()
						timesheet_doc.run_method('submit')

			designer_value = self.designer_assignment[-1].designer
					# Check if a timesheet document already exists for the employee
					# timesheet = frappe.db.get_list("Timesheet",filters={"employee":designer_value,"order":self.name},fields=["name"])
			timesheet = frappe.get_all(
				"Timesheet", filters={"employee": designer_value,"order":self.name}, fields=["name"],
			)
			if timesheet:
				timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])
				activity_type = timesheet_doc.time_logs[-1].activity_type
				if activity_type == 'QC Activity':
					timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])

					if timesheet_doc.time_logs:	
						time_log = timesheet_doc.time_logs[-1]					
						time_log.to_time = now_datetime()
						time_log.completed = 1
						time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600

					# qc_time_log = timesheet_doc.append("time_logs", {})
					# qc_time_log.activity_type = "CAD Designing - On-Hold"
					# qc_time_log.from_time = now_datetime()
					# qc_time_log.custom_cad_order_id = self.name
									
					timesheet_doc.save()
			# else:
						# frappe.throw("Timesheets is not created for each designer assignment")		
			
			frappe.msgprint("Timesheets Assigned for each designer assignment")
		
		elif self.workflow_state == "Sent to QC - On-Hold":
			# for assignment in self.designer_assignment:
			# 		designer_value = assignment.designer
			if len(self.designer_assignment)>1:
				for i in self.designer_assignment[:-1]:
					timesheet,docstatus = frappe.db.get_value("Timesheet", {"employee": i.designer,"order":self.name}, ["name","docstatus"])
					if docstatus == 0:
						timesheet_doc = frappe.get_doc("Timesheet", timesheet)
						if (timesheet_doc.time_logs):
							timesheet_doc.time_logs[-1].to_time = now_datetime()
							timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600
							timesheet_doc.save()
						timesheet_doc.run_method('submit')

			designer_value = self.designer_assignment[-1].designer
					# Check if a timesheet document already exists for the employee
					# timesheet = frappe.db.get_list("Timesheet",filters={"employee":designer_value,"order":self.name},fields=["name"])
			timesheet = frappe.get_all(
				"Timesheet", filters={"employee": designer_value,"order":self.name}, fields=["name"],
			)
			if timesheet:
				timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])

				if timesheet_doc.time_logs:	
					time_log = timesheet_doc.time_logs[-1]					
					time_log.to_time = now_datetime()
					time_log.completed = 1
					time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600
				
				if not timesheet_doc.time_logs or timesheet_doc.time_logs[-1].activity_type != "QC Activity - On-Hold":			
					qc_time_log = timesheet_doc.append("time_logs", {})
					qc_time_log.activity_type = "QC Activity - On-Hold"
					qc_time_log.from_time = now_datetime()
					qc_time_log.custom_cad_order_id = self.name
					timesheet_doc.save()
			else:
				frappe.throw("Timesheets is not created for each designer assignment")		
			
			# frappe.msgprint("Timesheets created for QC - On-Hold for each designer assignment")
		
		elif self.workflow_state == "Update Item":
			if self.bom_or_cad == 'CAD':
				# for assignment in self.designer_assignment:
				# 		designer_value = assignment.designer
				if len(self.designer_assignment)>1:
					for i in self.designer_assignment[:-1]:
						timesheet,docstatus = frappe.db.get_value("Timesheet", {"employee": i.designer,"order":self.name}, ["name","docstatus"])
						if docstatus == 0:
							timesheet_doc = frappe.get_doc("Timesheet", timesheet)
							if (timesheet_doc.time_logs):
								timesheet_doc.time_logs[-1].to_time = now_datetime()
								timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600
								timesheet_doc.save()
							timesheet_doc.run_method('submit')

				designer_value = self.designer_assignment[-1].designer
						# Check if a timesheet document already exists for the employee
				timesheet = frappe.get_all(
					"Timesheet", filters={"employee": designer_value,"order":self.name}, fields=["name"],
				)
				if timesheet:
					timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])

					if timesheet_doc.time_logs:	
						time_log = timesheet_doc.time_logs[-1]					
						time_log.to_time = now_datetime()
						time_log.completed = 1
						time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600

					update_time_log = timesheet_doc.append("time_logs", {})
					update_time_log.activity_type = "Update Item"
					update_time_log.from_time = now_datetime()
					update_time_log.custom_cad_order_id = self.name				
					timesheet_doc.save()
					
				else:
					frappe.throw("Timesheets is not created for each designer assignment")
				frappe.msgprint("Timesheets created for Update Item for each designer assignment")		
		
		elif self.workflow_state == "Update BOM":
			# frappe.throw(str(self.workflow_state))
			if self.bom_or_cad == 'CAD':
				# for assignment in self.designer_assignment:
				# 		designer_value = assignment.designer
				if len(self.designer_assignment)>1:
					for i in self.designer_assignment[:-1]:
						timesheet,docstatus = frappe.db.get_value("Timesheet", {"employee": i.designer,"order":self.name}, ["name","docstatus"])
						if docstatus == 0:
							timesheet_doc = frappe.get_doc("Timesheet", timesheet)
							if (timesheet_doc.time_logs):
								timesheet_doc.time_logs[-1].to_time = now_datetime()
								timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600
								timesheet_doc.save()
							timesheet_doc.run_method('submit')

				designer_value = self.designer_assignment[-1].designer
						# Check if a timesheet document already exists for the employee
				timesheet = frappe.get_all(
					"Timesheet", filters={"employee": designer_value,"order":self.name}, fields=["name"],)
				if timesheet:
					timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])
					
					time_log = timesheet_doc.time_logs[-1]					
					time_log.to_time = now_datetime()
					time_log.completed = 1
					time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600
					timesheet_doc.save()
					timesheet_doc.run_method('submit')
					
					frappe.msgprint("Timesheets Completed for each designer assignment")
				
				else:
					frappe.throw("Timesheets is not created for each designer assignment")

		elif self.workflow_state == "Update Designer":
			if self.bom_or_cad == 'CAD':
				# for assignment in self.designer_assignment:
				# 		designer_value = assignment.designer
				if len(self.designer_assignment)>1:
					for i in self.designer_assignment[:-1]:
						timesheet,docstatus = frappe.db.get_value("Timesheet", {"employee": i.designer,"order":self.name}, ["name","docstatus"])
						if docstatus == 0:
							timesheet_doc = frappe.get_doc("Timesheet", timesheet)
							if (timesheet_doc.time_logs):
								timesheet_doc.time_logs[-1].to_time = now_datetime()
								timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600
								timesheet_doc.save()
							timesheet_doc.run_method('submit')

				designer_value = self.designer_assignment[-1].designer
						# Check if a timesheet document already exists for the employee
				timesheet = frappe.get_all(
					"Timesheet", filters={"employee": designer_value,"order":self.name}, fields=["name"],
				)
				if timesheet:
					timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])

					time_log = timesheet_doc.time_logs[-1]					
					time_log.to_time = now_datetime()
					time_log.completed = 1
					time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600
					timesheet_doc.save()				
				else:
					frappe.throw("Timesheets is not created for each designer assignment")
				frappe.msgprint("Timesheets Update for each designer assignment")

		elif self.workflow_state == "Cancelled": 
		# for assignment in self.designer_assignment:
		# 		designer_value = assignment.designer
			if len(self.designer_assignment)>1:
				for i in self.designer_assignment[:-1]:
					timesheet,docstatus = frappe.db.get_value("Timesheet", {"employee": i.designer,"order":self.name}, ["name","docstatus"])
					if docstatus == 0:
						timesheet_doc = frappe.get_doc("Timesheet", timesheet)
						if (timesheet_doc.time_logs):
							timesheet_doc.time_logs[-1].to_time = now_datetime()
							timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600
							timesheet_doc.save()
						timesheet_doc.run_method('submit')
			if self.designer_assignment:
				designer_value = self.designer_assignment[-1].designer
						# Check if a timesheet document already exists for the employee
				timesheet = frappe.get_all(
					"Timesheet", filters={"employee": designer_value,}, fields=["name"],
				)
				if timesheet:
					timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])
	
					time_log = timesheet_doc.time_logs[-1]					
					time_log.to_time = now_datetime()
					time_log.completed = 1
					time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600
									
					timesheet_doc.save()
					timesheet_doc.run_method('submit')
				# else:
				# 	frappe.throw("Timesheets is cancelled for each designer assignment")		
			
			frappe.msgprint("Timesheets Cancelled for each designer assignment")

def cerate_bom_timesheet(self):
	if not self.customer_order_form:
		if self.workflow_state == "Creating BOM":
			if self.bom_or_cad in ['CAD','Check']:

				if len(self.bom_assignment)>1:
					for i in self.bom_assignment[:-1]:
						timesheet,docstatus = frappe.db.get_value("Timesheet", {"employee": i.designer,"order":self.name}, ["name","docstatus"])
						if docstatus == 0:
						# frappe.db.set_value("Timesheet",timesheet,"docstatus","1")
							timesheet_doc = frappe.get_doc("Timesheet", timesheet)
							if (timesheet_doc.time_logs):
								timesheet_doc.time_logs[-1].to_time = now_datetime()
								timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600
								timesheet_doc.save()
							timesheet_doc.run_method('submit')

				designer_value = self.bom_assignment[-1].designer		
				
				# # Check if a timesheet document already exists for the employee
				timesheet = frappe.get_all(
					"Timesheet", filters={"employee": designer_value,"order":self.name}, fields=["name"],
				)
				if timesheet:
					timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])
				else:
					timesheet_doc = frappe.new_doc("Timesheet")
					timesheet_doc.employee = designer_value
				
				if (timesheet_doc.time_logs and 
					timesheet_doc.time_logs[-1].activity_type in ['BOM QC','BOM QC - On-Hold']) :
					timesheet_doc.time_logs[-1].to_time = now_datetime()
					timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600

				time_log = timesheet_doc.append("time_logs", {})
				time_log.activity_type = "Create BOM"
				time_log.from_time = now_datetime()
				timesheet_doc.order = self.name	
				if self.new_bom:
					timesheet_doc.save()
					frappe.msgprint("Timesheets Created for BOM each designer assignment")
		
		elif self.workflow_state == "Creating BOM - On-Hold":
			if self.bom_or_cad in ['CAD','Check']:
				# for assignment in self.designer_assignment:
						# designer_value = assignment.designer
				if len(self.bom_assignment)>1:
					for i in self.bom_assignment[:-1]:
						timesheet,docstatus = frappe.db.get_value("Timesheet", {"employee": i.designer,"order":self.name}, ["name","docstatus"])
						if docstatus == 0:
						# frappe.db.set_value("Timesheet",timesheet,"docstatus","1")
							timesheet_doc = frappe.get_doc("Timesheet", timesheet)
							if (timesheet_doc.time_logs):
								timesheet_doc.time_logs[-1].to_time = now_datetime()
								timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600
								timesheet_doc.save()
							timesheet_doc.run_method('submit')


				designer_value = self.bom_assignment[-1].designer
						# Check if a timesheet document already exists for the employee
						# timesheet = frappe.db.get_list("Timesheet",filters={"employee":designer_value,"order":self.name},fields=["name"])
				timesheet = frappe.get_all(
					"Timesheet", filters={"employee": designer_value,"order":self.name}, fields=["name"],
				)
				if timesheet:
					timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])

					if timesheet_doc.time_logs:	
						time_log = timesheet_doc.time_logs[-1]					
						time_log.to_time = now_datetime()
						time_log.completed = 1
						time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600

					if not timesheet_doc.time_logs or timesheet_doc.time_logs[-1].activity_type != "Create BOM - On Hold":
						qc_time_log = timesheet_doc.append("time_logs", {})
						qc_time_log.activity_type = "Create BOM - On Hold"
						qc_time_log.from_time = now_datetime()
						qc_time_log.custom_cad_order_id = self.name
						timesheet_doc.save()

				else:
					frappe.throw("Timesheets is not created for each designer assignment")		
				
				# frappe.msgprint("Timesheets created for Creating BOM - On-Hold for each designer assignment")

		elif self.workflow_state == "BOM QC":
			if self.bom_or_cad in ['CAD','Check']:
				# for assignment in self.designer_assignment:
				if len(self.bom_assignment)>1:
					for i in self.bom_assignment[:-1]:
						timesheet,docstatus = frappe.db.get_value("Timesheet", {"employee": i.designer,"order":self.name}, ["name","docstatus"])
						if docstatus == 0:
							timesheet_doc = frappe.get_doc("Timesheet", timesheet)
							if (timesheet_doc.time_logs):
								timesheet_doc.time_logs[-1].to_time = now_datetime()
								timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600
								timesheet_doc.save()
							timesheet_doc.run_method('submit')

				designer_value = self.bom_assignment[-1].designer
						# designer_value = assignment.designer

						# Check if a timesheet document already exists for the employee
				timesheet = frappe.get_all(
					"Timesheet", filters={"employee": designer_value,"order":self.name}, fields=["name"],
				)
				if timesheet:
					timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])

					if timesheet_doc.time_logs:	
						time_log = timesheet_doc.time_logs[-1]					
						time_log.to_time = now_datetime()
						time_log.completed = 1
						time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600

					qc_time_log = timesheet_doc.append("time_logs", {})
					qc_time_log.activity_type = "BOM QC"
					qc_time_log.from_time = now_datetime()
					qc_time_log.custom_cad_order_id = self.name				
					timesheet_doc.save()
				else:
					frappe.throw("Timesheets is not created for each designer assignment")		
			
			frappe.msgprint("Timesheets created for BOM QC for each designer assignment")
		
		elif self.workflow_state == "BOM QC - On-Hold":
			if self.bom_or_cad in ['CAD','Check']:
				if len(self.bom_assignment)>1:
					for i in self.bom_assignment[:-1]:
						timesheet,docstatus = frappe.db.get_value("Timesheet", {"employee": i.designer,"order":self.name}, ["name","docstatus"])
						if docstatus == 0:
							timesheet_doc = frappe.get_doc("Timesheet", timesheet)
							if (timesheet_doc.time_logs):
								timesheet_doc.time_logs[-1].to_time = now_datetime()
								timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600
								timesheet_doc.save()
							timesheet_doc.run_method('submit')

				designer_value = self.bom_assignment[-1].designer
						# Check if a timesheet document already exists for the employee
						# timesheet = frappe.db.get_list("Timesheet",filters={"employee":designer_value,"order":self.name},fields=["name"])
				timesheet = frappe.get_all(
					"Timesheet", filters={"employee": designer_value,"order":self.name}, fields=["name"],
				)
				if timesheet:
					timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])

					if timesheet_doc.time_logs:	
						time_log = timesheet_doc.time_logs[-1]					
						time_log.to_time = now_datetime()
						time_log.completed = 1
						time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600

					if not timesheet_doc.time_logs or timesheet_doc.time_logs[-1].activity_type != "BOM QC - On Hold":
						qc_time_log = timesheet_doc.append("time_logs", {})
						qc_time_log.activity_type = "BOM QC - On Hold"
						qc_time_log.from_time = now_datetime()
						qc_time_log.custom_cad_order_id = self.name
						timesheet_doc.save()
				else:
					frappe.throw("Timesheets is not created for each designer assignment")		
				
			# frappe.msgprint("Timesheets created for BOM QC - On-Hold for each designer assignment")
		
		elif self.workflow_state == "Updating BOM":
			if self.bom_or_cad in ['CAD','Check']:
				# for assignment in self.designer_assignment:
				# 		designer_value = assignment.designer
				if len(self.bom_assignment)>1:
					for i in self.bom_assignment[:-1]:
						timesheet,docstatus = frappe.db.get_value("Timesheet", {"employee": i.designer,"order":self.name}, ["name","docstatus"])
						if docstatus == 0:
							timesheet_doc = frappe.get_doc("Timesheet", timesheet)
							if (timesheet_doc.time_logs):
								timesheet_doc.time_logs[-1].to_time = now_datetime()
								timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600
								timesheet_doc.save()
							timesheet_doc.run_method('submit')

				designer_value = self.bom_assignment[-1].designer
						# Check if a timesheet document already exists for the employee
				timesheet = frappe.get_all(
					"Timesheet", filters={"employee": designer_value,"order":self.name}, fields=["name"],
				)
				if timesheet:
					timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])

					if timesheet_doc.time_logs:	
						time_log = timesheet_doc.time_logs[-1]					
						time_log.to_time = now_datetime()
						time_log.completed = 1
						time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600
					
					update_time_log = timesheet_doc.append("time_logs", {})
					update_time_log.activity_type = "Updating BOM"
					update_time_log.from_time = now_datetime()
					update_time_log.custom_cad_order_id = self.name	
					timesheet_doc.save()
					# timesheet_doc.run_method('submit')
				else:
					frappe.throw("Timesheets is not created for each designer assignment")
				
			frappe.msgprint("Timesheets Updating BOM for each designer assignment")
		
		elif self.workflow_state == "Updating BOM - On-Hold":
			if self.bom_or_cad in ['CAD','Check']:
				# for assignment in self.designer_assignment:
						# designer_value = assignment.designer
				if len(self.bom_assignment)>1:
					for i in self.bom_assignment[:-1]:
						timesheet,docstatus = frappe.db.get_value("Timesheet", {"employee": i.designer,"order":self.name}, ["name","docstatus"])
						if docstatus == 0:
						# frappe.db.set_value("Timesheet",timesheet,"docstatus","1")
							timesheet_doc = frappe.get_doc("Timesheet", timesheet)
							if (timesheet_doc.time_logs):
								timesheet_doc.time_logs[-1].to_time = now_datetime()
								timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600
								timesheet_doc.save()
							timesheet_doc.run_method('submit')


				designer_value = self.bom_assignment[-1].designer
						# Check if a timesheet document already exists for the employee
						# timesheet = frappe.db.get_list("Timesheet",filters={"employee":designer_value,"order":self.name},fields=["name"])
				timesheet = frappe.get_all(
					"Timesheet", filters={"employee": designer_value,"order":self.name}, fields=["name"],
				)
				if timesheet:
					timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])

					if timesheet_doc.time_logs:	
						time_log = timesheet_doc.time_logs[-1]					
						time_log.to_time = now_datetime()
						time_log.completed = 1
						time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600

					if not timesheet_doc.time_logs or timesheet_doc.time_logs[-1].activity_type != "Updating BOM - On Hold":
						qc_time_log = timesheet_doc.append("time_logs", {})
						qc_time_log.activity_type = "Updating BOM - On Hold"
						qc_time_log.from_time = now_datetime()
						qc_time_log.custom_cad_order_id = self.name
						timesheet_doc.save()
				else:
					frappe.throw("Timesheets is not created for each designer assignment")		
				
			# frappe.msgprint("Timesheets created for Updating BOM - On-Hold for each designer assignment")
		
		elif self.workflow_state == "Approved":		
			if self.bom_or_cad in ['CAD','Check']:
				if len(self.bom_assignment)>1:				
					for i in self.bom_assignment[:-1]:
						timesheet,docstatus = frappe.db.get_value("Timesheet", {"employee": i.designer,"order":self.name}, ["name","docstatus"])
						if docstatus == 0:
							timesheet_doc = frappe.get_doc("Timesheet", timesheet)
							if (timesheet_doc.time_logs):
								timesheet_doc.time_logs[-1].to_time = now_datetime()
								timesheet_doc.time_logs[-1].hours = (now_datetime() - timesheet_doc.time_logs[-1].from_time).total_seconds()/3600
								timesheet_doc.save()
							timesheet_doc.run_method('submit')

				
				designer_value = self.bom_assignment[-1].designer
						# Check if a timesheet document already exists for the employee
				timesheet = frappe.get_all(
					"Timesheet", filters={"employee": designer_value,"order":self.name}, fields=["name"],
				)
				if timesheet:
					timesheet_doc = frappe.get_doc("Timesheet", timesheet[0]["name"])

					time_log = timesheet_doc.time_logs[-1]					
					time_log.to_time = now_datetime()
					time_log.completed = 1
					time_log.hours = (now_datetime() - time_log.from_time).total_seconds()/3600				
					timesheet_doc.save()
					timesheet_doc.run_method('submit')				
				else:
					frappe.throw("Timesheets is not created for each designer assignment")
			# frappe.msgprint("Timesheets Created for each bom designer assignment")

# def create_line_items(self):
# 	# if not self.customer_order_form: 
# 	item_variant = ''
# 	if self.item_type == 'Template and Variant':
# 		# if self.design_type != 'Sketch Design':
# 		if self.subcategory != frappe.db.get_value("Item",self.design_id,"item_subcategory"):
# 			if self.design_type != 'New Design':
# 				design_id = frappe.db.get_value('Order',self.name,'design_id')
# 				variant_of = frappe.db.get_value("Item",design_id,"variant_of")
# 				attribute_list = make_atribute_list(self.name)
# 				validate_variant_attributes(variant_of,attribute_list)

# 			item_template = create_item_template_from_order(self)
# 			updatet_item_template(item_template)
# 			item_variant = create_variant_of_template_from_order(item_template,self.name)
# 			update_item_variant(item_variant,item_template)
# 			frappe.msgprint(_("New Item Created: {0}".format(get_link_to_form("Item",item_variant))))
# 			frappe.db.set_value(self.doctype, self.name, "item", item_variant)
# 			self.reload()
# 		# else:
# 		# 	frappe.db.set_value(self.doctype, self.name, "item", self.design_id)
# 		# 	self.reload()

# 	elif self.item_type == 'Only Variant':
# 		# if self.subcategory != frappe.db.get_value("Item","design_id","item_subcategory"):

# 		design_id = frappe.db.get_value('Order',self.name,'design_id')
# 		# variant_of = frappe.db.get_value("Item",design_id,"variant_of")
# 		# attribute_list = make_atribute_list(self.name)
# 		# validate_variant_attributes(variant_of,attribute_list)

# 		item_variant = create_only_variant_from_order(self,self.name)
# 		frappe.db.set_value('Item',item_variant[0],{
# 			"is_design_code":1,
# 			"variant_of" : item_variant[1]
# 		})
# 		frappe.msgprint(_("New Item Created: {0}".format(get_link_to_form("Item",item_variant[0]))))
# 		frappe.db.set_value(self.doctype, self.name, "item", item_variant[0])
# 		self.reload()
# 		# else:
# 		# 	frappe.db.set_value(self.doctype, self.name, "item", self.design_id)
# 		# 	self.reload()
		
# 	elif self.item_type == 'No Variant No Suffix':
# 		if not self.is_finding_order:
# 			item_variant = self.design_id
# 			frappe.db.set_value(self.doctype, self.name, "item", self.design_id)
# 			frappe.db.set_value(self.doctype, self.name, "new_bom", self.bom)
# 			self.reload()
# 			if self.bom_or_cad in ['New BOM','CAD'] and self.is_repairing == 1 :
# 				new_bom = create_bom(self,item_variant)
# 				frappe.db.set_value("Order",self.name,"new_bom",new_bom)
# 			elif self.design_type == 'Sketch Design':
# 				update_variant_attributes(self)
# 				frappe.db.set_value("Item",self.design_id,"custom_cad_order_id",self.name)
# 				frappe.db.set_value("Item",self.design_id,"custom_cad_order_form_id",self.cad_order_form)
# 			# else:
# 			# 	frappe.db.set_value(self.doctype, self.name, "new_bom", self.bom)
# 		else:
# 			item_variant = self.item

# 	return	item_variant


def create_line_items(self):
	
	sketch_order_form_id = frappe.db.get_value("Item", self.design_id, "custom_sketch_order_id")
	custom_sketch_order_form_id = frappe.db.get_value("Item", self.design_id, "custom_sketch_order_form_id")

	item_variant = ''
	new_item_created = False  # Flag to track if a new item is created

	if self.item_type == 'Template and Variant':
		item_template = create_item_template_from_order(self)
		updatet_item_template(item_template)
		item_variant = create_variant_of_template_from_order(item_template, self.name)
		update_item_variant(item_variant, item_template)

		# Set custom_sketch_order_id to the new variant
		frappe.db.set_value("Item", item_variant, "custom_sketch_order_id", sketch_order_form_id)
		frappe.db.set_value("Item", item_variant, "custom_sketch_order_form_id", custom_sketch_order_form_id)

		frappe.db.set_value(self.doctype, self.name, "item", item_variant)
		self.reload()
		new_item_created = True
		frappe.msgprint(_("New Item Created: {0}".format(get_link_to_form("Item", item_variant))))
		
	elif self.item_type == 'Only Variant':
		design_id = frappe.db.get_value('Order', self.name, 'design_id')
		template = frappe.db.get_value("Item",design_id,"variant_of")
		args = make_atribute_list(self.name)
		variant_item_code = None
		possible_variants = [i for i in get_item_codes_by_attributes(args, template) if i != variant_item_code]
		for variant in possible_variants:
			variant = frappe.get_doc("Item", variant)
			if variant:
				final_variant = str(variant).replace("Item(","").replace(")","")
				frappe.throw(f"Already available {final_variant}")

		
		item_variant = create_only_variant_from_order(self, self.name)

		frappe.db.set_value('Item', item_variant[0], {
			"is_design_code": 1,
			"variant_of": item_variant[1],
			"custom_sketch_order_id": sketch_order_form_id,
			"custom_sketch_order_form_id": custom_sketch_order_form_id
		})

		frappe.db.set_value(self.doctype, self.name, "item", item_variant[0])
		self.reload()
		new_item_created = True
		frappe.msgprint(_("New Item Created: {0}".format(get_link_to_form("Item", item_variant[0]))))

	elif self.item_type == 'No Variant No Suffix':
		if not self.is_finding_order:
			item_variant = self.design_id
			frappe.db.set_value(self.doctype, self.name, "item", self.design_id)
			frappe.db.set_value(self.doctype, self.name, "new_bom", self.bom)
			self.reload()

			if self.bom_or_cad in ['New BOM', 'CAD'] and self.is_repairing == 1:
				new_bom = create_bom(self, item_variant)
				frappe.db.set_value("Order", self.name, "new_bom", new_bom)

			elif self.design_type == 'Sketch Design':
				update_variant_attributes(self)
				frappe.db.set_value("Item", self.design_id, "custom_cad_order_id", self.name)
				frappe.db.set_value("Item", self.design_id, "custom_cad_order_form_id", self.cad_order_form)

			# Set sketch order IDs
			frappe.db.set_value("Item", self.design_id, "custom_sketch_order_id", sketch_order_form_id)
			frappe.db.set_value("Item", item_variant, "custom_sketch_order_form_id", custom_sketch_order_form_id)
		else:
			item_variant = self.item

	# Set item_remark based on whether a new item was created
	frappe.db.set_value(self.doctype, self.name, "item_remark", "New Item" if new_item_created else "Copy Paste Item")

	return item_variant

def get_item_codes_by_attributes(attribute_filters, template_item_code=None):
	items = []

	for attribute, values in attribute_filters.items():
		attribute_values = values

		if not isinstance(attribute_values, list):
			attribute_values = [attribute_values]

		if not attribute_values:
			continue

		wheres = []
		query_values = []
		for attribute_value in attribute_values:
			wheres.append("( attribute = %s and attribute_value = %s )")
			query_values += [attribute, attribute_value]

		attribute_query = " or ".join(wheres)

		if template_item_code:
			variant_of_query = "AND t2.variant_of = %s"
			query_values.append(template_item_code)
		else:
			variant_of_query = ""

		query = f"""
			SELECT
				t1.parent
			FROM
				`tabItem Variant Attribute` t1
			WHERE
				1 = 1
				AND (
					{attribute_query}
				)
				AND EXISTS (
					SELECT
						1
					FROM
						`tabItem` t2
					WHERE
						t2.name = t1.parent
						{variant_of_query}
				)
			GROUP BY
				t1.parent
			ORDER BY
				NULL
		"""

		item_codes = set([r[0] for r in frappe.db.sql(query, query_values)])
		items.append(item_codes)

	res = list(set.intersection(*items))

	return res




def create_item_template_from_order(source_name, target_doc=None):
	def post_process(source, target):
		target.is_design_code = 1
		target.has_variants = 1

		if source.designer_assignment:
			target.designer = source.designer_assignment[0].designer
		else:
			if frappe.db.get_value('Employee',{'user_id':frappe.session.user},'name'):
				target.designer = frappe.db.get_value('Employee',{'user_id':frappe.session.user},'name')
			else:
				target.designer = frappe.db.get_value('User',frappe.session.user,'full_name')

		target.item_group = source.subcategory + " - T",
		
	doc = get_mapped_doc(
		"Order",
		source_name.name,
		{
			"Order": {
				"doctype": "Item",
				"field_map": {
					"category": "item_category",
					"subcategory": "item_subcategory",
					"setting_type": "setting_type",
					"india":"india",
					"india_states":"india_states",
					"usa":"usa",
					"usa_states":"usa_states",
				} 
			}
		},target_doc, post_process
	)

	
	doc.save()

	return doc.name

def create_variant_of_template_from_order(item_template,source_name, target_doc=None):
	def post_process(source, target):
		target.order_form_type = 'Order'
		target.item_group = frappe.db.get_value('Order',source_name,'subcategory') + " - V",
		target.custom_cad_order_id = source_name
		target.custom_cad_order_form_id = frappe.db.get_value('Order',source_name,'cad_order_form')
		target.item_code = f'{item_template}-001'
		target.sequence = item_template[2:7]
		subcateogy = frappe.db.get_value('Item',item_template,'item_subcategory')
		for i in frappe.get_all("Attribute Value Item Attribute Detail",{'parent': subcateogy,'in_item_variant':1},'item_attribute',order_by='idx asc'):
			attribute_with = i.item_attribute.lower().replace(' ', '_').replace('/', '')
			if i.item_attribute == 'Rhodium':
				attribute_with = 'rhodium_'
			if attribute_with == 'cap/ganthan':
				attribute_with = 'capganthan'
			try:
				attribute_value = frappe.db.get_value('Order',source_name,attribute_with)
			except:
				attribute_value = ' '
			
			target.append('attributes',{
				'attribute':i.item_attribute,
				'variant_of':item_template,
				'attribute_value':attribute_value
			})

		if source.designer_assignment:
			target.designer = source.designer_assignment[0].designer
		else:
			if frappe.db.get_value('Employee',{'user_id':frappe.session.user},'name'):
				target.designer = frappe.db.get_value('Employee',{'user_id':frappe.session.user},'name')
			else:
				target.designer = frappe.db.get_value('User',frappe.session.user,'full_name')

	doc = get_mapped_doc(
		"Order",
		source_name,
		{
			"Order": {
				"doctype": "Item",
				"field_map": {
					"category": "item_category",
					"subcategory": "item_subcategory",
					"setting_type": "setting_type",
					"metal_target":"approx_gold",
					"diamond_target":"approx_diamond",
					"sub_setting_type1":"sub_setting_type",
					"sub_setting_type2":"sub_setting_type2",
					"india":"india",
					"india_states":"india_states",
					"usa":"usa",
					"usa_states":"usa_states",
					"has_serial_no":1
				} 
			}
		},target_doc, post_process
	)
	
	doc.save()
	return doc.name

def create_only_variant_from_order(self,source_name, target_doc=None):
	def post_process(source, target):
		# if db_data['item_group'] == 'Design DNU':
		# 	index = int(self.design_id.split('-')[1]) + 1
		# 	suffix = "%.3i" % index
		# 	item_code = self.design_id.split('-')[0] + '-' + suffix
		# 	# frappe.throw(f"{item_code}")
		# else:
		db_data = frappe.db.get_list('Item',filters={'name':self.design_id},fields=['variant_of','item_group'],order_by='creation desc')[0]
		if db_data['variant_of']:
			db_data1 = frappe.db.get_list('Item',filters={'variant_of':db_data['variant_of']},fields=['name'],order_by='creation desc')[0]
			index = int(db_data1['name'].split('-')[1]) + 1
			variant_of = db_data['variant_of']
		else:
			# variant_of = db_data['variant_of']
			index =  1
			variant_of = self.design_id
		suffix = "%.3i" % index
		# item_code = db_data['variant_of'] + '-' + suffix
		item_code = variant_of + '-' + suffix
		# frappe.throw(f"{item_code}")
		
		target.order_form_type = 'Order'
		if db_data['item_group'] == 'Design DNU':
			target.item_group = "Design DNU",
			target.sequence = suffix
		else:
			target.item_group = frappe.db.get_value('Order',source_name,'subcategory') + " - V",		
			target.sequence = item_code[2:7]
		target.item_code = item_code
		target.custom_cad_order_id = source_name
		target.custom_cad_order_form_id = frappe.db.get_value('Order',source_name,'cad_order_form')
		target.has_serial_no = 1
		target.variant_of = variant_of

		for i in frappe.get_all("Attribute Value Item Attribute Detail",{'parent': self.subcategory,'in_item_variant':1},'item_attribute',order_by='idx asc'):
			attribute_with = i.item_attribute.lower().replace(' ', '_').replace('/', '')
			if i.item_attribute == 'Rhodium':
				attribute_with = 'rhodium_'
			if attribute_with == 'cap/ganthan':
				attribute_with = 'capganthan'
			try:
				attribute_value = frappe.db.get_value('Order',source_name,attribute_with)
			except:
				attribute_value = ' '
			
			# target.append('attributes',{
			# 	'attribute':i.item_attribute,
			# 	'variant_of':item_template,
			# 	'attribute_value':attribute_value
			# })
			target.append('attributes',{
				'attribute':i.item_attribute,
				'variant_of':variant_of,
				'attribute_value':attribute_value
			})

		if source.designer_assignment:
			target.designer = source.designer_assignment[0].designer
		else:
			if frappe.db.get_value('Employee',{'user_id':frappe.session.user},'name'):
				target.designer = frappe.db.get_value('Employee',{'user_id':frappe.session.user},'name')
			else:
				target.designer = frappe.db.get_value('User',frappe.session.user,'full_name')
		
	doc = get_mapped_doc(
		"Order",
		source_name,
		{
			"Order": {
				"doctype": "Item",
				"field_map": {
					"category": "item_category",
					"subcategory": "item_subcategory",
					"metal_target":"approx_gold",
					"diamond_target":"approx_diamond",
					"setting_type": "setting_type",
					"sub_setting_type1":"sub_setting_type",
					"sub_setting_type2":"sub_setting_type2",
					"india":"india",
					"india_states":"india_states",
					"usa":"usa",
					"usa_states":"usa_states",
					"age_group":"custom_age_group",
					"alphabetnumber":"custom_alphabetnumber",
					"animalbirds":"custom_animalbirds",
					"collection":"custom_collection",
					"design_style":"custom_design_style",
					"gender":"custom_gender",
					"lines_rows":"custom_lines__rows",
					"language":"custom_language",
					"occasion":"custom_occasion",
					"rhodium":"custom_rhodium",
					"shapes":"custom_religious",
					"religious":"custom_shapes",
					"zodiac":"custom_zodiac",
					"has_serial_no":1
				} 
			}
		},target_doc, post_process
	)
	doc.save()
	return doc.name,doc.variant_of

def create_sufix_of_variant_template_from_order(source_name, target_doc=None):
	variant_of = frappe.db.get_value("Item",source_name.design_id,'variant_of')
	if variant_of == None:
		frappe.throw(f'Template of {variant_of} is not available')

	def post_process(source, target):
		target.is_design_code = 1
		target.has_variants = 1
		target.item_group = source.subcategory + " - T",
		# query = """
		# SELECT name, modified_sequence, `sequence`
		# FROM `tabItem` ti
		# WHERE name LIKE %s AND has_variants = 1
		# ORDER BY creation DESC
		# """

		# results = frappe.db.sql(query, (f"%{variant_of}/%",), as_dict=True)
		# if results:
		# 	modified_sequence = int(results[0]['modified_sequence']) + 1
		# 	modified_sequence = f"{modified_sequence:02}"
		# else:
		# 	modified_sequence = '01'
		
		# target.item_code = variant_of + '/' + modified_sequence
		# # frappe.throw(target.item_code)
		# target.modified_sequence = modified_sequence
		# target.order_form_type = 'Order'
		# target.custom_cad_order_id = source_name
		# target.custom_cad_order_form_id = frappe.db.get_value('Order',source_name,'cad_order_form')

		if source.designer_assignment:
			target.designer = source.designer_assignment[0].designer
		else:
			if frappe.db.get_value('Employee',{'user_id':frappe.session.user},'name'):
				target.designer = frappe.db.get_value('Employee',{'user_id':frappe.session.user},'name')
			else:
				target.designer = frappe.db.get_value('User',frappe.session.user,'full_name')
	
	doc = get_mapped_doc(
		"Order",
		source_name.name,
		{
			"Order": {
				"doctype": "Item",
				"field_map": {
					"category": "item_category",
					"subcategory": "item_subcategory",
					"setting_type": "setting_type",
					"india":"india",
					"india_states":"india_states",
					"usa":"usa",
					"usa_states":"usa_states",
				} 
			}
		},target_doc, post_process
	)
	doc.save()
	return doc.name

def create_variant_of_sufix_of_variant_from_order(self,item_template,source_name, target_doc=None):
	def post_process(source, target):
		target.order_form_type = 'Order'
		target.item_group = frappe.db.get_value('Order',source_name,'subcategory') + " - V",
		target.custom_cad_order_id = source_name
		target.custom_cad_order_form_id = frappe.db.get_value('Order',source_name,'cad_order_form')
		target.item_code = f'{item_template}-001'
		target.sequence = item_template[2:7]
		subcateogy = frappe.db.get_value('Item',item_template,'item_subcategory')
		for i in frappe.get_all("Attribute Value Item Attribute Detail",{'parent': subcateogy,'in_item_variant':1},'item_attribute',order_by='idx asc'):
			attribute_with = i.item_attribute.lower().replace(' ', '_').replace('/', '')	
			if attribute_with == 'rhodium':
				attribute_with = 'rhodium_'
			if attribute_with == 'cap/ganthan':
				attribute_with = 'capganthan'
			try:
				attribute_value = frappe.db.get_value('Order',source_name,attribute_with)
			except:
				attribute_value = ' '

			target.append('attributes',{
				'attribute':i.item_attribute,
				'variant_of':item_template,
				'attribute_value':frappe.db.get_value('Order',source_name,attribute_with)
			})

		if source.designer_assignment:
			target.designer = source.designer_assignment[0].designer
		else:
			if frappe.db.get_value('Employee',{'user_id':frappe.session.user},'name'):
				target.designer = frappe.db.get_value('Employee',{'user_id':frappe.session.user},'name')
			else:
				target.designer = frappe.db.get_value('User',frappe.session.user,'full_name')
	
	doc = get_mapped_doc(
		"Order",
		source_name,
		{
			"Order": {
				"doctype": "Item",
				"field_map": {
					"category": "item_category",
					"subcategory": "item_subcategory",
					"setting_type": "setting_type",
					"metal_target":"approx_gold",
					"diamond_target":"approx_diamond",
					"sub_setting_type1":"sub_setting_type",
					"sub_setting_type2":"sub_setting_type2",
					"india":"india",
					"india_states":"india_states",
					"usa":"usa",
					"usa_states":"usa_states",
					"has_serial_no":1
				} 
			}
		},target_doc, post_process
	)
	doc.save()
	return doc.name

def updatet_item_template(item_template):
	frappe.db.set_value('Item',item_template,{
		"is_design_code":0,
		"item_code":item_template,
		"custom_cad_order_id":"",
		"custom_cad_order_form_id":"",
	})

def update_item_variant(item_variant,item_template):
	frappe.db.set_value('Item',item_variant,{
		"is_design_code":1,
		"variant_of" : item_template
	})



def create_bom(self, item_variant):
	bom_doc = frappe.get_doc("BOM", self.bom)

	# Create a copy of the BOM
	new_bom_doc = frappe.copy_doc(bom_doc)
	new_bom_doc.docstatus = 0
	new_bom_doc.name = ''
	new_bom_doc.is_active = 1
	new_bom_doc.is_default = 1
	new_bom_doc.bom_type = 'Template'
	new_bom_doc.item = item_variant
	new_bom_doc.custom_order_form_type = 'Order'
	new_bom_doc.custom_cad_order_form_id = self.cad_order_form
	new_bom_doc.custom_order_id = self.name

	# If metal_type is Silver, update metal details and convert quantities
	if self.metal_type and  self.mod_reason == "Change In Metal Type" and self.metal_type.strip().lower() == "silver":
		# Fetch Jewellery Settings
		settings = frappe.get_single("Jewellery Settings")
		wax_to_gold_10 = settings.wax_to_gold_10
		wax_to_gold_14 = settings.wax_to_gold_14
		wax_to_gold_18 = settings.wax_to_gold_18
		wax_to_gold_22 = settings.wax_to_gold_22
		wax_to_silver_ratio = settings.wax_to_silver

		# Update each row in new BOM's metal_detail
		for new_row, original_row in zip(new_bom_doc.metal_detail, bom_doc.metal_detail):
			new_row.metal_type = "Silver"
			new_row.metal_touch = self.metal_touch
			new_row.metal_colour = self.metal_colour
			new_row.metal_purity = "85.0"

			# Perform conversion based on original metal_touch
			if original_row.metal_touch == "10KT":
				converted_qty = (original_row.quantity / wax_to_gold_10) * wax_to_silver_ratio
			elif original_row.metal_touch == "14KT":
				converted_qty = (original_row.quantity / wax_to_gold_14) * wax_to_silver_ratio
			elif original_row.metal_touch == "18KT":
				converted_qty = (original_row.quantity / wax_to_gold_18) * wax_to_silver_ratio
			elif original_row.metal_touch == "22KT":
				converted_qty = (original_row.quantity / wax_to_gold_22) * wax_to_silver_ratio
			else:
				# If not matched, keep original quantity
				converted_qty = original_row.quantity

			new_row.quantity = converted_qty

		# Update BOM-level fields
		new_bom_doc.metal_type = self.metal_type
		new_bom_doc.metal_touch = self.metal_touch
		new_bom_doc.metal_colour = self.metal_colour
		new_bom_doc.metal_purity = "85.0"

		total_metal_weight = sum(row.quantity for row in new_bom_doc.metal_detail)
		new_bom_doc.metal_weight = total_metal_weight
		new_bom_doc.metal_target = total_metal_weight
		new_bom_doc.total_metal_weight = total_metal_weight

	
	new_bom_doc.save()
	return new_bom_doc.name


def create_bom_for_touch(self,item_variant=None):
	bom_doc = frappe.get_doc("BOM",self.bom)
	new_bom_doc =  frappe.copy_doc(bom_doc)
	qty = 0
	for i in new_bom_doc.metal_detail:
		i.quantity = flt(i.quantity)*(flt(self.metal_touch.replace("KT",""))/flt(i.metal_touch.replace("KT","")))
		qty = i.quantity
		i.metal_touch = self.metal_touch
		if i.metal_touch == '22KT':
			i.metal_purity = '91.9'
		if i.metal_touch == '18KT':
			i.metal_purity = '75.4'
	new_bom_doc.metal_touch = self.metal_touch
	if new_bom_doc.metal_touch == '22KT':
			new_bom_doc.metal_purity = 91.9
	if new_bom_doc.metal_touch == '18KT':
		new_bom_doc.metal_purity = 75.4
	new_bom_doc.metal_target = qty
	new_bom_doc.custom_order_form_type = 'Order'
	new_bom_doc.custom_cad_order_form_id = self.cad_order_form
	new_bom_doc.custom_order_id = self.name
	new_bom_doc.insert()
	# Commit the changes to the database
	frappe.db.commit()
	return new_bom_doc.name


@frappe.whitelist()
def make_quotation(source_name, target_doc=None):
	
	import json
	from erpnext.setup.utils import get_exchange_rate

	def set_missing_values(source, target):
		from erpnext.controllers.accounts_controller import get_default_taxes_and_charges
		quotation = frappe.get_doc(target)
		company_currency = frappe.get_cached_value("Company", quotation.company, "default_currency")
		if company_currency == quotation.currency:
			exchange_rate = 1
		else:
			exchange_rate = get_exchange_rate(
				quotation.currency, company_currency, quotation.transaction_date, args="for_selling"
			)
		quotation.conversion_rate = exchange_rate

		# get default taxes
		taxes = get_default_taxes_and_charges(
			"Sales Taxes and Charges Template", company=quotation.company
		)
		if taxes.get("taxes"):
			quotation.update(taxes)

		quotation.run_method("set_missing_values")
		quotation.run_method("calculate_taxes_and_totals")

		quotation.quotation_to = "Customer"
		field_map = {
			"company": "company",
			"party_name": "customer_code",
			"order_type": "order_type",
			"diamond_quality": "diamond_quality"
		}
		for target_field, source_field in field_map.items():
			quotation.set(target_field, source.get(source_field))

		service_types = frappe.db.get_values("Service Type 2", {"parent": source.name}, "service_type1")
		for service_type in service_types:
			quotation.append("service_type", {"service_type1": service_type[0]})

	if isinstance(target_doc, str):
		target_doc = json.loads(target_doc)
	if not target_doc:
		target_doc = frappe.new_doc("Quotation")
	else:
		target_doc = frappe.get_doc(target_doc)

	order = frappe.db.get_value("Order", source_name, "*", as_dict=True)

	item_data = {
		"order_form_type": "Order",
		"order_form_id": order.get("name"),
		"qty": order.get("qty") or 1,
		"copy_bom": order.get("new_bom")
	}

	# If new_bom is present, get fields from BOM
	if order.get("new_bom"):
		bom = frappe.get_doc("BOM", order.get("new_bom"))
		item_data.update({
			"branch": bom.get("branch"),
			"project": bom.get("project"),
			"item_code": bom.get("item"),
			"serial_no": bom.get("serial_no"),
			"metal_type": bom.get("metal_type"),
			"metal_colour": bom.get("metal_colour"),
			"metal_purity": bom.get("metal_purity"),
			"metal_touch": bom.get("metal_touch"),
			"gemstone_quality": bom.get("gemstone_quality"),
			"item_category": bom.get("item_category"),
			"diamond_quality": bom.get("diamond_quality"),
			"item_subcategory": bom.get("item_subcategory"),
			"setting_type": bom.get("setting_type"),
			"delivery_date": bom.get("delivery_date"),
			"salesman_name": bom.get("salesman_name"),
			"order_form_date": bom.get("order_form_date"),
			"custom_customer_sample": bom.get("custom_customer_sample"),
			"custom_customer_voucher_no": bom.get("custom_customer_voucher_no"),
			"custom_customer_gold": bom.get("custom_customer_gold"),
			"custom_customer_diamond": bom.get("custom_customer_diamond"),
			"custom_customer_stone": bom.get("custom_customer_stone"),
			"custom_customer_good": bom.get("custom_customer_good"),
			"po_no": bom.get("po_no"),
			"custom_jewelex_batch_no": bom.get("custom_jewelex_batch_no"),
			"custom_product_size": bom.get("custom_product_size")
		})
	else:
		# Fallback to Order fields
		item_data.update({
			"branch": order.get("branch"),
			"project": order.get("project"),
			"item_code": order.get("item"),
			"serial_no": order.get("tag_no"),
			"metal_type": order.get("metal_type"),
			"metal_colour": order.get("metal_colour"),
			"metal_purity": order.get("metal_purity"),
			"metal_touch": order.get("metal_touch"),
			"gemstone_quality": order.get("gemstone_quality"),
			"item_category": order.get("category"),
			"diamond_quality": order.get("diamond_quality"),
			"item_subcategory": order.get("subcategory"),
			"setting_type": order.get("setting_type"),
			"delivery_date": order.get("delivery_date"),
			"salesman_name": order.get("salesman_name"),
			"order_form_date": order.get("order_date"),
			"custom_customer_sample": order.get("customer_sample"),
			"custom_customer_voucher_no": order.get("customer_voucher_no"),
			"custom_customer_gold": order.get("customer_gold"),
			"custom_customer_diamond": order.get("customer_diamond"),
			"custom_customer_stone": order.get("customer_stone"),
			"custom_customer_good": order.get("customer_good"),
			"po_no": order.get("po_no"),
			"custom_jewelex_batch_no": order.get("jewelex_batch_no"),
			"custom_product_size": order.get("product_size")
		})

	target_doc.append("items", item_data)

	set_missing_values(order, target_doc)
	return target_doc

def update_variant_attributes(self):
	variant_attributes = frappe.db.sql(f"""select name,attribute,attribute_value from `tabItem Variant Attribute` where parent = '{self.design_id}'""",as_dict=1)
	for attribute in variant_attributes:
		# if attribute['attribute'] == 'Cap/Ganthan':
		# 	frappe.throw(f"{attribute['attribute'].replace(' ','_').lower()}")

		attribute_lower = attribute['attribute'].replace(' ','_').lower()
		if attribute_lower == 'rhodium':
			attribute_lower = 'rhodium_'
		if attribute_lower == 'cap/ganthan':
			attribute_lower = 'capganthan'

		# attribute_value = getattr(self, attribute_lower)
		if self.get(attribute_lower) != attribute['attribute_value']:
			frappe.db.set_value('Item Variant Attribute',attribute['name'],'attribute_value',self.get(attribute_lower))

def check_finding_code(self):
	if self.metal_touch == '22KT':
		metal_purity = 91.9
	if self.metal_touch == '18KT':
		metal_purity = 75.4
	args = {
		"Metal Type":self.metal_type,
		"Metal Touch":self.metal_touch,
		"Metal Purity":metal_purity,
		"Metal Colour":self.metal_colour,
		"Finding Category":self.finding_category,
		"Finding Sub-Category":self.finding_subcategory,
		"Finding Size":self.finding_size,

	}
	# frappe.throw(f"{args}")
	variant = get_variant(
					"F", args
				)
	if variant:
		self.item = variant
	else:
		# Create a new variant
		variant = create_variant("F", args)
		variant_item_group = frappe.db.get_value(
			"Variant Item Group", {"parent": self.company, "item_variant": "F"}, "item_group"
		)
		if variant_item_group:
			variant.item_group = variant_item_group
		variant.flags.ignore_permissions = True
		variant.save()
		self.item = variant.name
	# frappe.throw(f"{variant}")
	return

@frappe.whitelist()
def calculate_item_wt_details(doc, bom=None, item=None):
	if isinstance(doc, str):
		doc = json.loads(doc)
	settings = frappe.get_doc("Jewellery Settings")
	doc["cam_weight"] = flt(doc["cad_weight"]) / flt(settings.cad_to_rpt)
	doc["wax_weight"] = flt(doc["cam_weight"]) / flt(settings.rpt_to_wax)
	ratio_dict = {
		"22KT":"18",
		"18KT":"16",
		"14KT":"14.23",
		"10KT":"12.73",
		"20KT":"10"
	}

	doc["casting_weight"] = flt(doc["wax_weight"])*flt(ratio_dict[doc["metal_touch"]])
	doc["cad_finish_ratio"] = flt(ratio_dict[doc["metal_touch"]])
	return doc

def make_atribute_list(source_name):
	order_details = frappe.get_doc('Order',source_name)
	all_variant_attribute = frappe.db.sql(
		f"""select item_attribute from `tabAttribute Value Item Attribute Detail` 
		where parent = '{order_details.subcategory}' and in_item_variant=1""",as_list=1
	)

	final_list = {}
	for i in all_variant_attribute:
		new_i = i[0].replace(' ','_').replace('/','').lower()
		if new_i == 'rhodium':
			new_i = 'rhodium_'
		final_list[i[0]] = order_details.get_value(new_i)
	return final_list

def validate_variant_attributes(variant_of,attribute_list):
	args = attribute_list
	variant = get_variant(variant_of, args)
	if variant:
		frappe.throw(
			_("Item variant <b>{0}</b> exists with same attributes").format(get_link_to_form("Item",variant)), ItemVariantExistsError
		)



@frappe.whitelist()
def make_quotation_batch(order_names, target_doc=None):
	if isinstance(order_names, str):
		order_names = json.loads(order_names)
	if isinstance(target_doc, str):
		target_doc = json.loads(target_doc)
	if not target_doc:
		target_doc = frappe.new_doc("Quotation")
	else:
		target_doc = frappe.get_doc(target_doc)

	target_doc.items = []
	for name in order_names:
		order = frappe.db.get_value("Order", name, "*", as_dict=True)
		if not order:
			continue

		target_doc.append("items", {
			"branch": order.branch,
			"project": order.project,
			"item_code": order.item,
			"serial_no": order.tag_no,
			"metal_colour": order.metal_colour,
			"metal_purity": order.metal_purity,
			"metal_touch": order.metal_touch,
			"gemstone_quality": order.gemstone_quality,
			"item_category": order.category,
			"diamond_quality": order.diamond_quality,
			"item_subcategory": order.subcategory,
			"setting_type": order.setting_type,
			"delivery_date": order.delivery_date,
			"order_form_type": "Order",
			"order_form_id": order.name,
			"salesman_name": order.salesman_name,
			"order_form_date": order.order_date,
			"custom_customer_sample": order.customer_sample,
			"custom_customer_voucher_no": order.customer_voucher_no,
			"custom_customer_gold": order.customer_gold,
			"custom_customer_diamond": order.customer_diamond,
			"custom_customer_stone": order.customer_stone,
			"custom_customer_good": order.customer_good,
			"po_no": order.po_no,
			"custom_jewelex_batch_no": order.jewelex_batch_no,
			"qty": order.qty
		})

	# Only run set_missing_values once
	first_order = frappe.db.get_value("Order", order_names[0], "*", as_dict=True)
	make_quotation_fill_defaults(target_doc, first_order)

	return target_doc


def make_quotation_fill_defaults(quotation, order):
	from erpnext.controllers.accounts_controller import get_default_taxes_and_charges
	company_currency = frappe.get_cached_value("Company", quotation.company, "default_currency")
	if company_currency == quotation.currency:
		exchange_rate = 1
	else:
		exchange_rate = get_exchange_rate(
			quotation.currency, company_currency, quotation.transaction_date, args="for_selling"
		)
	quotation.conversion_rate = exchange_rate

	taxes = get_default_taxes_and_charges(
		"Sales Taxes and Charges Template", company=quotation.company
	)
	if taxes.get("taxes"):
		quotation.update(taxes)

	quotation.quotation_to = "Customer"
	quotation.company = order.company
	quotation.party_name = order.customer_code
	quotation.order_type = order.order_type
	quotation.diamond_quality = order.diamond_quality

	service_types = frappe.db.get_values("Service Type 2", {"parent": order.name}, "service_type1")
	for service_type in service_types:
		quotation.append("service_type", {"service_type1": service_type[0]})

	quotation.run_method("set_missing_values")
	quotation.run_method("calculate_taxes_and_totals")
