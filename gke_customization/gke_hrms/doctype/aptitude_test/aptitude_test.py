# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AptitudeTest(Document):
	pass


	def validate(self, method=None):
		# Reset obtained marks to 0 at the start of validation
		self.obtained_marks = 0
		if self.paper_set == "Set - C1":
			self.min_marks = 15
		else:
			self.min_marks = 36
		
		# if self.part_type == "Set - A1":
		if self.a1_q1_options == "240":
			self.obtained_marks += 3  # Add 3 marks

		if self.a1_q2_options == "External Assistance":
			self.obtained_marks += 3  # Add 3 marks
		
		if self.a1_q3_options == "OTPR":
			self.obtained_marks += 3  # Add 3 marks

		if self.a1_q4_options == "None of these":
			self.obtained_marks += 3  # Add 3 marks

		if self.a1_q5_options == "96":
			self.obtained_marks += 3  # Add 3 marks

		if self.a1_q6_options == "Both I and II follow":
			self.obtained_marks += 3  # Add 3 marks

		if self.a1_q7_options == "Gold":
			self.obtained_marks += 3  # Add 3 marks

		if self.a1_q8_options == "The diameter of the inside of the ring":
			self.obtained_marks += 3  # Add 3 marks

		if self.a1_q9_options == "Designing":
			self.obtained_marks += 3  # Add 3 marks

		if self.a1_q10_options == "To specify the main topic of the email":
			self.obtained_marks += 3  # Add 3 marks

		if self.a1_q11_options == "Carbon Copy":
			self.obtained_marks += 3  # Add 3 marks

		if self.a1_q12_options == ".exe":
			self.obtained_marks += 3  # Add 3 marks

		if self.a1_q13_options == "Rabindranath Tagore":
			self.obtained_marks += 3  # Add 3 marks

		if self.a1_q14_options == "Nile":
			self.obtained_marks += 3  # Add 3 marks

		if self.a1_q15_options == "Jupiter":
			self.obtained_marks += 3  # Add 3 marks

		if self.a1_q16_options == "Copy format style":
			self.obtained_marks += 3  # Add 3 marks

		if self.a1_q17_options == "Average()":
			self.obtained_marks += 3  # Add 3 marks

		if self.a1_q18_options == "Now()":
			self.obtained_marks += 3  # Add 3 marks

		# if self.part_type == "Set - A2":
		if self.a2_q1_options == "1996 & 1995":
			self.obtained_marks += 3  # Add 3 marks

		if self.a2_q2_options == "10000":
			self.obtained_marks += 3  # Add 3 marks

		if self.a2_q3_options == "Hockey and Tennis":
			self.obtained_marks += 3  # Add 3 marks

		if self.a2_q4_options == "45 m East":
			self.obtained_marks += 3  # Add 3 marks

		if self.a2_q5_options == "Patients: Doctors":
			self.obtained_marks += 3  # Add 3 marks

		if self.a2_q6_options == "Neither Conclusion I nor II is true":
			self.obtained_marks += 3  # Add 3 marks

		if self.a2_q7_options == "The purity of the gold":
			self.obtained_marks += 3  # Add 3 marks

		if self.a2_q8_options == "Pouring molten metal into a mold to form a shape":
			self.obtained_marks += 3  # Add 3 marks

		if self.a2_q9_options == "Wear protective gloves and goggles":
			self.obtained_marks += 3  # Add 3 marks

		if self.a2_q10_options == "Sends a response to the sender of the email":
			self.obtained_marks += 3  # Add 3 marks

		if self.a2_q11_options == "Sends a reply to the sender and all recipients of the email":
			self.obtained_marks += 3  # Add 3 marks

		if self.a2_q12_options == "To send a blind copy to multiple recipients without others knowing":
			self.obtained_marks += 3  # Add 3 marks

		if self.a2_q13_options == "Rabindranath Tagore":
			self.obtained_marks += 3  # Add 3 marks

		if self.a2_q14_options == "Nile":
			self.obtained_marks += 3  # Add 3 marks

		if self.a2_q15_options == "Jupiter":
			self.obtained_marks += 3  # Add 3 marks

		if self.a2_q16_options == "Max()":
			self.obtained_marks += 3  # Add 3 marks

		if self.a2_q17_options == "View > Freeze Panes > Freeze Top Row":
			self.obtained_marks += 3  # Add 3 marks

		if self.a2_q18_options == "It returns a value from a vertical lookup in a table.":
			self.obtained_marks += 3  # Add 3 marks

		if self.c1_q1_options == "The Nile River":
			self.obtained_marks += 3  # Add 3 marks

		if self.c1_q2_options == "New Delhi":
			self.obtained_marks += 3  # Add 3 marks

		if self.c1_q3_options == "Jwaharlal Nehru":
			self.obtained_marks += 3  # Add 3 marks

		if self.c1_q4_options == "Bengal tiger":
			self.obtained_marks += 3  # Add 3 marks

		if self.c1_q5_options == "Cricket":
			self.obtained_marks += 3  # Add 3 marks

		if self.c1_q6_options == "Mahatma Gandhi":
			self.obtained_marks += 3  # Add 3 marks

		if self.c1_q7_options == "47":
			self.obtained_marks += 3  # Add 3 marks

		if self.c1_q8_options == "43":
			self.obtained_marks += 3  # Add 3 marks

		if self.c1_q9_options == "16":
			self.obtained_marks += 3  # Add 3 marks

		if self.c1_q10_options == "30":
			self.obtained_marks += 3  # Add 3 marks


		min_marks = int(self.min_marks)
		if self.obtained_marks >= min_marks:
			self.test_status = "Pass"
		else:
			self.test_status = "Fail"
