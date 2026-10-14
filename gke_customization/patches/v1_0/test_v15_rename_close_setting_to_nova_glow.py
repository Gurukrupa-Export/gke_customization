"""Tests for the Close -> Nova Glow rename patch's guards.

Only the decision to run, skip or refuse is tested, against a patched frappe.db; the
column migration itself is patched out and nothing is written.
"""

from unittest.mock import patch

import frappe
from frappe.modules import patch_handler
from frappe.tests import UnitTestCase

from gke_customization.patches.v1_0 import v15_rename_close_setting_to_nova_glow as n


class TestNovaGlowRenameGuards(UnitTestCase):
	def setUp(self):
		self.attribute_values = set()
		self.sentinel = False
		self._patch(frappe.db, "exists", side_effect=self._exists)
		self._patch(n, "_sentinel_is_set", side_effect=lambda: self.sentinel)
		self.migrate = self._patch(n, "_apply_rename_and_migrate")
		self.set_sentinel = self._patch(n, "_set_sentinel")
		self._patch(frappe, "clear_cache")

	def _patch(self, target, attribute, **kwargs):
		patcher = patch.object(target, attribute, **kwargs)
		self.addCleanup(patcher.stop)
		return patcher.start()

	def _exists(self, doctype, filters=None, *args, **kwargs):
		return doctype == "Attribute Value" and filters["attribute_value"] in self.attribute_values

	def test_sentinel_skips_everything(self):
		self.sentinel = True
		self.attribute_values = {n.OLD_SETTING_TYPE, n.NEW_SETTING_TYPE}
		n.execute()
		self.migrate.assert_not_called()

	def test_renames_when_only_the_old_values_exist(self):
		self.attribute_values = {n.OLD_SETTING_TYPE, n.OLD_SUB_SETTING}
		n.execute()
		self.migrate.assert_called_once_with()
		self.set_sentinel.assert_called_once_with()

	def test_finishes_columns_when_v1_already_renamed_the_masters(self):
		self.attribute_values = {n.NEW_SETTING_TYPE, n.NEW_SUB_SETTING}
		n.execute()
		self.migrate.assert_called_once_with()

	def test_refuses_when_old_and_new_setting_both_exist(self):
		self.attribute_values = {n.OLD_SETTING_TYPE, n.NEW_SETTING_TYPE}
		with self.assertRaises(frappe.ValidationError) as raised:
			n.execute()
		self.migrate.assert_not_called()
		self.set_sentinel.assert_not_called()
		self.assertIn(f"'{n.OLD_SETTING_TYPE}' / '{n.NEW_SETTING_TYPE}'", str(raised.exception))

	def test_refuses_when_old_and_new_sub_setting_both_exist(self):
		self.attribute_values = {n.NEW_SETTING_TYPE, n.OLD_SUB_SETTING, n.NEW_SUB_SETTING}
		with self.assertRaises(frappe.ValidationError) as raised:
			n.execute()
		self.migrate.assert_not_called()
		self.assertIn(f"'{n.OLD_SUB_SETTING}' / '{n.NEW_SUB_SETTING}'", str(raised.exception))

	def test_refusal_leaves_the_patch_pending(self):
		"""No Patch Log row unless execute() returns, so the next migrate runs it again."""
		self.attribute_values = {n.OLD_SETTING_TYPE, n.NEW_SETTING_TYPE}
		update_patch_log = self._patch(patch_handler, "update_patch_log")
		self._patch(frappe.db, "commit")
		rollback = self._patch(frappe.db, "rollback")
		# execute_patch resets in_patch only after a patch succeeds.
		self.addCleanup(setattr, frappe.local.flags, "in_patch", frappe.flags.in_patch)
		with self.assertRaisesRegex(frappe.ValidationError, "Cannot rename the Close setting"):
			patch_handler.execute_patch(n.__name__)
		update_patch_log.assert_not_called()
		rollback.assert_called_once_with()
