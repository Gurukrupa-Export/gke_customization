# Copyright (c) 2026, Gurukrupa Export and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from gke_customization.gke_price_list.doctype.product_return_order.test_product_return_order import (
	_settings,
)
from gke_customization.gke_price_list.doctype.product_return_order_form import (
	product_return_order_form as prof,
)

MOD = "gke_customization.gke_price_list.doctype.product_return_order_form.product_return_order_form"


class TestProductReturnOrderForm(UnitTestCase):
	pass


class TestKGRefFormPush(UnitTestCase):
	"""on_submit pushes a KG-ref form to the KGGK site only once PRF To Site is set.

	The push itself is patched out; past it, on_submit's own checks run, and a form without
	items stops at the first of them, which shows the local submit carried on.
	"""

	def setUp(self):
		self.doc = frappe.get_doc(
			{"doctype": "Product Return Order Form", "name": "PROF-S1-TEST", "ref_company": "KG"}
		)
		self.settings = _settings()
		self._patch("frappe.get_single", side_effect=lambda doctype: self.settings)
		self.push = self._patch(f"{MOD}.sync_product_return_form_to_remote")

	def _patch(self, target, **kwargs):
		patcher = patch(target, **kwargs)
		self.addCleanup(patcher.stop)
		return patcher.start()

	def submit(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Items are mandatory"):
			self.doc.on_submit()

	def test_blank_prf_to_site_submits_locally(self):
		self.settings = _settings(prf_to_site=None)
		self.submit()
		self.push.assert_not_called()

	def test_configured_site_gets_the_kg_form(self):
		self.submit()
		self.push.assert_called_once_with(self.doc)

	def test_gk_ref_form_is_never_pushed(self):
		self.doc.ref_company = "GK"
		self.submit()
		self.push.assert_not_called()


class TestKGRefFormPushSettings(UnitTestCase):
	def test_missing_credentials_stop_before_any_request(self):
		doc = frappe.get_doc({"doctype": "Product Return Order Form", "name": "PROF-S1-TEST", "ref_company": "KG"})
		with patch(f"{MOD}.requests.post") as post, patch("frappe.log_error"):
			for missing in ("api_key", "api_secret"):
				with self.subTest(missing=missing), patch(
					"frappe.get_single", return_value=_settings(**{missing: None})
				):
					with self.assertRaises(frappe.ValidationError) as ctx:
						prof.sync_product_return_form_to_remote(doc)
					# msgprint strips the <b> tags when stdin is a TTY: match plain text only.
					self.assertIn("PRF To Site", str(ctx.exception))
			post.assert_not_called()
