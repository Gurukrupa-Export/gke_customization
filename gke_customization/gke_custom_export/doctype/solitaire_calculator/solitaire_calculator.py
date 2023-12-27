# Copyright (c) 2023, vishal@gurukrupaexport.in and contributors
# For license information, please see license.txt

# my_app/my_app/doctype/solitaire_calculator/solitaire_calculator.py

# catalog/solitaire_calculator.py

from __future__ import unicode_literals
import frappe
from frappe.utils import now,getdate
from frappe.model.document import Document
from forex_python.converter import CurrencyRates

class SolitaireCalculator(Document):
      def before_insert(self):
        current_date = getdate()
        current_year = current_date.year
        self.year = current_year
        max_sequence = frappe.db.get_list("Solitaire Calculator", pluck="sequence")
        max_sequence.sort()
        if max_sequence:
            sequence = int(max_sequence[-1]) + 1
            sequence = f"{sequence:04}"
        else:
            sequence = '0001'
        self.sequence = sequence
      


@frappe.whitelist()
def get_usd_inr():
    c = CurrencyRates()
    exchange_rate = c.get_rate('USD', 'INR')
    return round(exchange_rate,2)
    # return 83.20

@frappe.whitelist()
def date_time():
     date = frappe.utils.nowdate()
     return date