"""Tests for the pre_model_sync rename of "Revise Diamond Price  List".

The patch's branches depend only on which DocType records and tables exist, so these are
unit tests against a patched frappe.db: no DocType, table or document is created.
"""

from unittest.mock import patch

import frappe
from frappe.modules import patch_handler
from frappe.tests import UnitTestCase

from gke_customization.patches import rename_revise_diamond_price_list_doctype as p

OLD = p.OLD_DOCTYPE
NEW = p.NEW_DOCTYPE


class TestRenameReviseDiamondPriceListDoctype(UnitTestCase):
	def setUp(self):
		self._site(doctypes=(), tables=())
		self._patch(frappe.db, "exists", side_effect=self._exists)
		self._patch(frappe.db, "table_exists", side_effect=self._table_exists)
		self._patch(frappe.db, "count", side_effect=self._count)
		self._patch(frappe, "get_all", return_value=[])
		self.rename_doc = self._patch(frappe, "rename_doc")
		# The steps after the rename run their own queries and are not under test here.
		for helper in ("rekey_workflow_state_field", "rename_in_client_scripts", "report_remaining_references"):
			self._patch(p, helper)

	def _site(self, doctypes, tables, counts=None):
		"""What the site holds: DocType records, tables and their row counts."""
		self.doctypes = set(doctypes)
		self.tables = set(tables)
		self.counts = counts or {}

	def _patch(self, target, attribute, **kwargs):
		patcher = patch.object(target, attribute, **kwargs)
		self.addCleanup(patcher.stop)
		return patcher.start()

	def _exists(self, doctype, name=None, *args, **kwargs):
		return doctype == "DocType" and name in self.doctypes

	def _table_exists(self, doctype, cached=True):
		return doctype in self.tables

	def _count(self, doctype):
		return self.counts[doctype]

	def test_old_doctype_absent_does_nothing(self):
		"""GK live and fresh installs. The old table may survive as a leftover."""
		self._site(doctypes={NEW}, tables={OLD, NEW})
		p.execute()
		self.rename_doc.assert_not_called()

	def test_renames_when_only_the_old_doctype_exists(self):
		self._site(doctypes={OLD}, tables={OLD})
		p.execute()
		self.rename_doc.assert_called_once_with(
			"DocType", OLD, NEW, force=True, show_alert=False, rebuild_search=False
		)

	def test_refuses_when_the_new_doctype_exists(self):
		self._site(doctypes={OLD, NEW}, tables={OLD, NEW}, counts={OLD: 3, NEW: 2})
		with self.assertRaises(frappe.ValidationError) as raised:
			p.execute()
		self.rename_doc.assert_not_called()
		message = str(raised.exception)
		self.assertIn(f"`tab{OLD}` with 3 rows", message)
		self.assertIn(f"`tab{NEW}` with 2 rows", message)
		self.assertIn("--skip-failing", message)

	def test_refuses_on_a_leftover_new_table_even_when_empty(self):
		"""The patch never drops a table, not even an empty one."""
		self._site(doctypes={OLD}, tables={OLD, NEW}, counts={OLD: 3, NEW: 0})
		with self.assertRaises(frappe.ValidationError) as raised:
			p.execute()
		self.rename_doc.assert_not_called()
		self.assertIn(f"{NEW!r}: DocType record absent", str(raised.exception))

	def test_refusal_leaves_the_patch_pending(self):
		"""No Patch Log row unless execute() returns, so the next migrate retries."""
		self._site(doctypes={OLD, NEW}, tables={OLD, NEW}, counts={OLD: 1, NEW: 1})
		update_patch_log = self._patch(patch_handler, "update_patch_log")
		self._patch(frappe.db, "commit")
		rollback = self._patch(frappe.db, "rollback")
		# execute_patch resets in_patch only after a patch succeeds.
		self.addCleanup(setattr, frappe.local.flags, "in_patch", frappe.flags.in_patch)
		# The message, not just the type: AppNotInstalledError is a ValidationError too.
		with self.assertRaisesRegex(frappe.ValidationError, "Cannot rename DocType"):
			patch_handler.execute_patch(p.__name__)
		update_patch_log.assert_not_called()
		rollback.assert_called_once_with()
