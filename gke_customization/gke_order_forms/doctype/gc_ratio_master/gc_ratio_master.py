# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class GCRatioMaster(Document):
    def validate(self):
        for row in self.gc_ratio:
            if row.type == "Range":
                if row.range_1 >= row.range_2:
                    frappe.throw("Range 1 should be less than Range 2 for Range type.")
            row.metal_to_gold_ratio_group = f"{row.range_1}-{row.range_2}"
            if row.type in ["Above", "Below"]:
                if row.range_1 is None:
                    frappe.throw("Range 1 should be set for Above and Below types.")
                row.metal_to_gold_ratio_group = f"{row.type} {row.range_1}"
