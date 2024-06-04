# import frappe
# from datetime import datetime


# def validate(self,method):
#     if len(self.custom_shareholder_table) > 0 and self.custom_activate_interest_calculation == 1:
#         calculate_interest_with_days(self)

# def calculate_interest_with_days(self):
# 	# with calculating days
# 	if len(self.custom_shareholder_table)==1:
# 		self.custom_total_interest_amount = self.custom_shareholder_table[0].interest
# 	else:
# 		for entry in self.custom_shareholder_table:
# 			entry.date = datetime.strptime(str(entry.date), "%Y-%m-%d")

# 		total_interest_amount = 0
# 		for i in range(len(self.custom_shareholder_table) - 1):
# 			current_date = self.custom_shareholder_table[i].date
# 			next_date = self.custom_shareholder_table[i + 1].date
# 			interest = self.custom_shareholder_table[i].interest
# 			days_between = (next_date - current_date).days
# 			total_interest_amount += days_between * interest
# 		self.custom_total_interest_amount = total_interest_amount