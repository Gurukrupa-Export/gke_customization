from jewellery_erpnext.jewellery_erpnext.customization.batch.doc_events.utils import (
	update_inventory_dimentions,
	update_pure_qty,
)
import frappe
import datetime

def autoname(self,method=None):
	# year_code = get_year_code()
	# month_code = get_month_code()
	# week_code = get_week_code()
	item_group = frappe.db.get_value("Item",{self.item},"item_group")

	if item_group in ["Metal - V", "Diamond - V", "Gemstone - V", "Finding - V", "Other - V"]:
		year_code = get_year_code()
		month_code = get_month_code()
		week_code = get_week_code()
		start_of_week, end_of_week = get_current_week_date_range()

		if item_group == "Diamond - V":
			batch_number = "GE{year_code}{month_code}{week_code}-D".format(
				year_code=year_code, month_code=month_code, week_code=week_code
			)
		elif item_group == "Metal - V":
			batch_number = "GE{year_code}{month_code}{week_code}-M".format(
				year_code=year_code, month_code=month_code, week_code=week_code
			)
		elif item_group == "Gemstone - V":
			batch_number = "GE{year_code}{month_code}{week_code}-G".format(
				year_code=year_code, month_code=month_code, week_code=week_code
			)
		elif item_group == "Finding - V":
			batch_number = "GE{year_code}{month_code}{week_code}-F".format(
				year_code=year_code, month_code=month_code, week_code=week_code
			)
		elif item_group == "Other - V":
			batch_number = "GE{year_code}{month_code}{week_code}-O".format(
				year_code=year_code, month_code=month_code, week_code=week_code
			)
		batch_abbr_code_list = []
		
		for i in frappe.get_doc("Item",self.item).attributes:
			if i.attribute == "Finding Category":
				continue
			batch_abbreviation = frappe.db.get_value(
				"Attribute Value", i.attribute_value, "custom_batch_abbreviation"
			)
			if i.attribute_value:
				if batch_abbreviation:
					batch_abbr_code_list.append(batch_abbreviation)
				else:
					frappe.throw(("Abbrivation is missing for {0}").format(i.attribute_value))
		batch_code = batch_number + "".join(batch_abbr_code_list)
		batch_list = frappe.db.sql(f"""SELECT 
										name
									FROM 
										`tabBatch`
									WHERE 
										manufacturing_date > '{start_of_week}'
										AND manufacturing_date < '{end_of_week}' 
										AND item = '{self.item}'
									ORDER BY 
										CAST(SUBSTRING_INDEX(name, '-', -1) AS UNSIGNED) DESC;
									""",as_dict=1)
		if batch_list:
			batch = batch_list[0]["name"].split('-')[-1]
			sequence = int(batch) + 1
			sequence = f"{sequence:04}"
		else:
			sequence = '0001'
		self.name = batch_code + '-' + sequence


def get_year_code():
	year_dict = {
		"1": "A",
		"2": "B",
		"3": "C",
		"4": "D",
		"5": "E",
		"6": "F",
		"7": "G",
		"8": "H",
		"9": "I",
		"0": "J",
	}
	current_year = datetime.datetime.now().year
	last_two_digits = current_year % 100
	return str(last_two_digits)[0] + year_dict[str(last_two_digits)[1]]


def get_week_code():
	current_date = datetime.date.today()
	week_number = (current_date.day - 1) // 7 + 1
	return str(week_number)


def get_month_code():
	current_date = datetime.datetime.now()
	month_two_digit = current_date.strftime("%m")
	return str(month_two_digit)

def get_current_week_date_range():
	current_date = datetime.date.today()
	first_day_of_month = current_date.replace(day=1)

	# Calculate start of the week
	day_of_week = current_date.weekday()  # Monday is 0, Sunday is 6
	start_of_week = current_date - datetime.timedelta(days=day_of_week)

	# Make sure the week doesn't start before the first of the month
	start_of_week = max(start_of_week, first_day_of_month)

	# Calculate end of the week
	end_of_week = start_of_week + datetime.timedelta(days=6)

	# Make sure the week doesn't extend beyond the month
	last_day_of_month = (
		current_date.replace(day=28) + datetime.timedelta(days=4)
	).replace(day=1) - datetime.timedelta(days=1)
	end_of_week = min(end_of_week, last_day_of_month)

	start_formatted = start_of_week.strftime("%Y-%-m-%-d")
	end_formatted = end_of_week.strftime("%Y-%-m-%-d")

	return start_formatted, end_formatted