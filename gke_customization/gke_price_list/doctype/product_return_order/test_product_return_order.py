# Copyright (c) 2026, Gurukrupa Export and Contributors
# See license.txt

from unittest.mock import patch

import frappe
import requests
from frappe.tests import UnitTestCase

MOD = "gke_customization.gke_price_list.doctype.product_return_order.product_return_order"
SERIAL = "SN-F02-TEST"
URL = "https://kg.example.invalid/api/method/serial_product_return_order"


class TestProductReturnOrder(UnitTestCase):
	pass


class _Settings(frappe._dict):
	"""Data Migration in KGGK as on_submit reads it.

	get_password behaves like BaseDocument.get_password for a Data field with no __Auth row:
	the value when set, otherwise "Password not found" (None with raise_exception=False).
	"""

	def get_password(self, fieldname="password", raise_exception=True):
		self.setdefault("password_reads", []).append(fieldname)
		if self.get(fieldname):
			return self.get(fieldname)
		if raise_exception:
			frappe.throw(f"Password not found for Data Migration in KGGK Data Migration in KGGK {fieldname}")


def _settings(**overrides):
	base = {"prf_to_site": "https://kg.example.invalid/", "api_key": "key", "api_secret": "secret"}
	base.update(overrides)
	return _Settings(base)


class _Serial(frappe._dict):
	def insert(self, ignore_permissions=False):
		self.inserted = True
		return self


class TestJewelexSerialPush(UnitTestCase):
	"""on_submit's push of a Jewelex serial to the KGGK site.

	Boundaries are patched, as in test_kggk_sync: nothing is written and no request leaves
	the process.
	"""

	def setUp(self):
		self.doc = frappe.get_doc(
			{
				"doctype": "Product Return Order",
				"name": "PRO-F02-TEST",
				"customer": "_F02 Customer",
				"company": "_F02 Company",
				"item_code": "_F02 Item",
				"is_jewelex_tag": 1,
				"jewelex_tag": "F02-TAG",
				"new_bom": "BOM-F02-TEST",
			}
		)
		self.serial = _Serial(name=SERIAL)
		self.settings = _settings()
		self.post = self._patch(f"{MOD}.requests.post")
		self.new_doc = self._patch("frappe.new_doc", return_value=self.serial)
		self.get_single = self._patch("frappe.get_single", side_effect=lambda doctype: self.settings)
		# Nothing may reach the database: run-tests commits when it finishes.
		self._patch(f"{MOD}.make_autoname", return_value=SERIAL)
		self._patch(f"{MOD}.ProductReturnOrder.genrate_serial_no", return_value="SNF02.1244")
		self.db_set = self._patch(f"{MOD}.ProductReturnOrder.db_set")
		self._patch("frappe.log_error")

	def _patch(self, target, **kwargs):
		patcher = patch(target, **kwargs)
		self.addCleanup(patcher.stop)
		return patcher.start()

	def test_blank_prf_to_site_keeps_the_serial_local(self):
		"""README step 5: with PRF To Site blank the serial is created and nothing is sent."""
		self.settings = _settings(prf_to_site=None)
		self.doc.on_submit()
		self.assertTrue(self.serial.inserted)
		self.db_set.assert_called_once_with("serial_no", SERIAL, update_modified=False)
		self.post.assert_not_called()
		self.assertNotIn("password_reads", self.settings)

	def test_unconfigured_settings_do_not_block_approval(self):
		"""All blank: reading api_secret before the switch used to raise 'Password not found'."""
		self.settings = _Settings()
		self.doc.on_submit()
		self.assertTrue(self.serial.inserted)
		self.post.assert_not_called()

	def test_configured_site_gets_exactly_one_post(self):
		self.doc.on_submit()
		self.post.assert_called_once_with(
			URL,
			headers={
				"Authorization": "token key:secret",
				"Content-Type": "application/json",
				"Accept": "application/json",
			},
			json={"name": "PRO-F02-TEST", "serial_no": SERIAL, "customer": "_F02 Customer"},
			timeout=30,
		)

	def test_missing_credentials_stop_approval_before_any_request(self):
		for missing in ("api_key", "api_secret"):
			with self.subTest(missing=missing):
				self.settings = _settings(**{missing: None})
				with self.assertRaises(frappe.ValidationError) as ctx:
					self.doc.on_submit()
				# msgprint strips the <b> tags when stdin is a TTY: match plain text only.
				self.assertIn("PRF To Site", str(ctx.exception))
				self.post.assert_not_called()

	def test_remote_error_stops_approval(self):
		self.post.side_effect = requests.exceptions.ConnectionError("refused")
		with self.assertRaises(frappe.ValidationError) as ctx:
			self.doc.on_submit()
		self.assertIn("Remote Serial No synchronization failed", str(ctx.exception))
		self.post.assert_called_once()

	def test_remote_http_error_stops_approval(self):
		self.post.return_value.raise_for_status.side_effect = requests.exceptions.HTTPError("500")
		with self.assertRaises(frappe.ValidationError) as ctx:
			self.doc.on_submit()
		self.assertIn("Remote Serial No synchronization failed", str(ctx.exception))

	def test_remote_timeout_stops_approval(self):
		self.post.side_effect = requests.exceptions.ReadTimeout("read timed out")
		with self.assertRaises(frappe.ValidationError) as ctx:
			self.doc.on_submit()
		self.assertIn("timed out", str(ctx.exception))

	def test_create_item_path_without_bom_is_skipped(self):
		self.doc.new_bom = None
		self.doc.on_submit()
		self.new_doc.assert_not_called()
		self.get_single.assert_not_called()
		self.post.assert_not_called()

	def test_non_jewelex_return_gets_a_local_serial_only(self):
		self.doc.is_jewelex_tag = 0
		self.doc.on_submit()
		self.assertTrue(self.serial.inserted)
		self.get_single.assert_not_called()
		self.post.assert_not_called()
