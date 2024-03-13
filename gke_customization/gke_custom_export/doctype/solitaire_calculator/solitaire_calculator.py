# Copyright (c) 2023, vishal@gurukrupaexport.in and contributors
# For license information, please see license.txt

# my_app/my_app/doctype/solitaire_calculator/solitaire_calculator.py

# catalog/solitaire_calculator.py

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
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
    
    def before_save(self):
        rate = flt(self.rate) or 0
        rap = flt(self.rap) or 0    

        rate_rap = rate - (rate * rap / 100)
        self.rate_rap = rate_rap

        rate_rap = flt(self.rate_rap) or 0
        carat = flt(self.carat) or 0

        rate_carat = rate_rap * carat
        self.rate_carat = rate_carat

        rate_carat = flt(self.rate_carat) or 0
        usd_to_inr = flt(self.usd_to_inr) or 0

        rate_per_peice_in_inr = rate_carat * usd_to_inr
        self.rate_per_peice_in_inr = rate_per_peice_in_inr

        margin = flt(self.margin) or 0
        rate_per_peice_in_inr = flt(self.rate_per_peice_in_inr) or 0

        selling_rate_per_piecein_inr = rate_per_peice_in_inr + (rate_per_peice_in_inr * margin / 100)
        self.selling_rate_per_piecein_inr = selling_rate_per_piecein_inr

        selling_rate_per_piecein_inr = flt(self.selling_rate_per_piecein_inr) or 0
        carat = flt(self.carat) or 0

        selling_rate_per_caratin_inr = selling_rate_per_piecein_inr / carat
        self.selling_rate_per_caratin_inr = selling_rate_per_caratin_inr
      


@frappe.whitelist()
def get_usd_inr():

    c = CurrencyRates()
    exchange_rate = c.get_rate('USD', 'INR')
    return round(exchange_rate,2)

