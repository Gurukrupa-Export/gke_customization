# Copyright (c) 2026, Gurukrupa Export and Contributors
# See license.txt

import json
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from gke_customization.gke_catalog.report.product_lifecycle import (
	product_lifecycle as pl,
)

MOD = "gke_customization.gke_catalog.report.product_lifecycle.product_lifecycle"
FILTERS = json.dumps({"tag_no": "TAG-1"})


class _Reached(Exception):
	pass


class TestReportAccess(UnitTestCase):
	"""Both whitelisted methods repeat Desk's report access check before reading anything."""

	def test_denied_before_any_read(self):
		with (
			patch(f"{MOD}.get_report_doc", side_effect=frappe.PermissionError) as gate,
			patch.object(pl, "resolve_item_code") as resolve,
		):
			with self.assertRaises(frappe.PermissionError):
				pl.get_finish_tag_history(FILTERS)
			with self.assertRaises(frappe.PermissionError):
				pl.get_serial_no_section_data(FILTERS, "Casting - GEPL")
		resolve.assert_not_called()
		self.assertEqual([call.args for call in gate.call_args_list], [("Product Lifecycle",)] * 2)

	def test_permitted_user_reaches_the_lookups(self):
		with patch(f"{MOD}.get_report_doc"), patch.object(pl, "resolve_item_code", side_effect=_Reached):
			with self.assertRaises(_Reached):
				pl.get_finish_tag_history(FILTERS)
			with self.assertRaises(_Reached):
				pl.get_serial_no_section_data(FILTERS, "Casting - GEPL")


class TestReportAccessOnSite(IntegrationTestCase):
	def test_user_without_report_role_is_denied(self):
		self.addCleanup(frappe.db.rollback)
		email = f"pl-{frappe.generate_hash(length=8)}@example.invalid"
		user = frappe.get_doc({"doctype": "User", "email": email, "first_name": "PL Test", "send_welcome_email": 0})
		user.insert(ignore_permissions=True)
		user.add_roles("Employee")
		with patch.object(pl, "resolve_item_code") as resolve, self.set_user(email):
			with self.assertRaises(frappe.PermissionError):
				pl.get_finish_tag_history(FILTERS)
			with self.assertRaises(frappe.PermissionError):
				pl.get_serial_no_section_data(FILTERS, "Casting - GEPL")
		resolve.assert_not_called()
