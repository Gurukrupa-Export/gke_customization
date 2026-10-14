# Copyright (c) 2024, Gurukrupa Export and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from gke_customization.gke_order_forms.doctype.repair_order.repair_order import (
	genrate_serial_no,
)
from gke_customization.gke_price_list.doctype.product_return_order.test_product_return_order import (
	fake_get_value,
	make_bom,
)


class TestRepairOrder(UnitTestCase):
	"""genrate_serial_no names a repaired piece's serial from its BOM (same rule as Product Return Order)."""

	def compose(self, bom):
		with self.freeze_time("2026-06-15 12:00:00", is_utc=True), patch(
			"frappe.get_doc", return_value=bom
		), patch.object(frappe.db, "get_value", side_effect=fake_get_value):
			return genrate_serial_no(frappe._dict(company="_Test Company"), "BOM-TEST")

	def test_metal_only_bom_takes_zero_grade(self):
		self.assertEqual(self.compose(make_bom(metal=["_Test Gold"])), "SLG02F.####")

	def test_diamond_bom_keeps_first_row_grade(self):
		bom = make_bom(metal=["_Test Gold"], diamond=["_Test VS", "_Test Grade No Abbr"])
		self.assertEqual(self.compose(bom), "SLGV2F.####")

	def test_grade_without_abbreviation_is_rejected(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Diamond Grade:(<b>)?_Test Grade No Abbr"):
			self.compose(make_bom(metal=["_Test Gold"], diamond=["_Test Grade No Abbr"]))
