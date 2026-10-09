"""Tests for the receiving end of the KGGK sync - the atomic upsert that runs on KGGK.

Against patched boundaries, like the sender's tests, apart from the lock itself, which is
taken on this site's real database: whether two pushes of one record can overlap is the thing
this module exists to settle.
"""

import unittest
from contextlib import ExitStack
from unittest.mock import patch

import frappe

from . import kggk_receiver as r

IDENTITY = {r.SOURCE_SITE: "gk.example.com", r.SOURCE_DOCTYPE: "BOM", r.SOURCE_NAME: "B-SRC"}


class _Doc(frappe._dict):
	"""Just enough of a document for `_update`."""

	def __init__(self, docstatus=0, fields=(), allow_on_submit=(), **values):
		super().__init__(values)
		self.docstatus = docstatus
		self.saved = 0
		self.appended = []
		self.meta = frappe._dict(
			fields=[frappe._dict(fieldname=f, allow_on_submit=1 if f in allow_on_submit else 0) for f in fields],
			has_field=lambda name: name in fields,
		)

	def update(self, values):
		for key, value in values.items():
			self[key] = value

	def append(self, table, row):
		self.appended.append((table, row))

	def save(self):
		self.saved += 1


def _upsert(existing=None, doc=None, data=None, policy=None, version=None, doctype="BOM"):
	"""Run `upsert` with the database and permissions patched; returns ``(result, mocks)``."""
	with ExitStack() as stack:
		enter = stack.enter_context
		enter(patch.object(frappe, "has_permission", return_value=True))
		enter(patch.object(r, "_require_identity_fields"))
		lock = enter(patch.object(r, "_lock"))
		unlock = enter(patch.object(r, "_unlock"))
		enter(patch.object(r, "_find", return_value=existing))
		enter(patch.object(frappe.db, "commit"))
		get_doc = enter(patch.object(frappe, "get_doc", return_value=doc))
		enter(patch.object(frappe, "get_meta", return_value=frappe._dict(has_field=lambda name: True)))
		result = r.upsert(
			doctype, "gk.example.com", "B-SRC", data or {}, source_version=version, policy=policy or {}
		)
	return result, frappe._dict(lock=lock, unlock=unlock, get_doc=get_doc)


class TestTheUpsertIsOneLockedStep(unittest.TestCase):
	def test_only_items_and_boms_are_received(self):
		with patch.object(frappe, "has_permission", return_value=True):
			with self.assertRaises(frappe.ValidationError):
				r.upsert("Sales Invoice", "gk.example.com", "SI-1", {})

	def test_the_lock_is_held_around_the_lookup_and_the_write(self):
		created = _Doc(name="B-9")
		created.insert = lambda: None
		result, mocks = _upsert(existing=None, doc=created, data={"item": "I-1"})
		self.assertEqual(result["action"], "created")
		mocks.lock.assert_called_once()
		mocks.unlock.assert_called_once()

	def test_a_new_record_is_created_carrying_its_origin_and_version(self):
		captured = {}

		def get_doc(values):
			captured.update(values)
			doc = _Doc(name="B-9")
			doc.insert = lambda: None
			return doc

		with patch.object(frappe, "has_permission", return_value=True), patch.object(
			r, "_require_identity_fields"
		), patch.object(r, "_lock"), patch.object(r, "_unlock"), patch.object(
			r, "_find", return_value=None
		), patch.object(frappe.db, "commit"), patch.object(frappe, "get_doc", side_effect=get_doc), patch.object(
			frappe, "get_meta", return_value=frappe._dict(has_field=lambda name: True)
		):
			result = r.upsert("BOM", "gk.example.com", "B-SRC", {"item": "I-1", "name": "ignored"}, source_version="2026-10-05 10:00:00")
		self.assertEqual(result["name"], "B-9")
		self.assertEqual(captured[r.SOURCE_NAME], "B-SRC")
		self.assertEqual(captured[r.SOURCE_VERSION], "2026-10-05 10:00:00")
		self.assertNotIn("name", captured)

	def test_the_second_push_of_a_record_updates_what_the_first_created(self):
		"""A retried 502, or a second worker: the record is found by its origin, not made again."""
		doc = _Doc(name="B-9", fields=("item", "quantity"), quantity=1)
		result, mocks = _upsert(existing="B-9", doc=doc, data={"quantity": 5})
		self.assertEqual((result["name"], result["action"]), ("B-9", "updated"))
		self.assertEqual(doc.quantity, 5)
		self.assertEqual(doc.saved, 1)


class TestUpdateRules(unittest.TestCase):
	def test_an_older_version_never_overwrites_a_newer_one(self):
		doc = _Doc(name="B-9", fields=("quantity", r.SOURCE_VERSION), quantity=7, **{r.SOURCE_VERSION: "2026-10-05 11:00:00"})
		result, _ = _upsert(existing="B-9", doc=doc, data={"quantity": 5}, version="2026-10-05 10:00:00")
		self.assertEqual(result["action"], "stale")
		self.assertEqual(doc.quantity, 7)
		self.assertEqual(doc.saved, 0)

	def test_omitted_fields_are_left_alone_and_clears_are_applied(self):
		doc = _Doc(name="I-1", fields=("item_name", "variant_of", "brand"), variant_of="T-1", brand="Old")
		_upsert(
			existing="I-1", doc=doc, doctype="Item",
			data={"item_name": "Ring", "variant_of": "T-2"},
			policy={"omit": ["variant_of"], "clear": {"brand": None}},
		)
		self.assertEqual((doc.item_name, doc.variant_of, doc.brand), ("Ring", "T-1", None))

	def test_kggks_own_defaults_stay_and_only_a_missing_company_row_is_added(self):
		doc = _Doc(name="I-1", fields=("item_defaults",), item_defaults=[frappe._dict(company="Other Co")])
		_upsert(
			existing="I-1", doc=doc, doctype="Item",
			data={"item_defaults": [{"company": "KG GK"}]},
			policy={"omit": ["item_defaults"], "merge_child": {"item_defaults": "company"}},
		)
		self.assertEqual(doc.item_defaults, [frappe._dict(company="Other Co")])
		self.assertEqual(doc.appended, [("item_defaults", {"company": "KG GK"})])

	def test_a_submitted_record_takes_what_its_own_metadata_allows(self):
		doc = _Doc(
			docstatus=1, name="B-9", fields=("is_active", "quantity", "custom_note"),
			allow_on_submit=("is_active", "custom_note"), is_active=0, quantity=1, custom_note="",
		)
		result, _ = _upsert(existing="B-9", doc=doc, data={"is_active": 1, "quantity": 5, "custom_note": "x"})
		self.assertEqual(result["blocked"], ["quantity"])
		self.assertEqual((doc.is_active, doc.custom_note, doc.quantity), (1, "x", 1))

	def test_an_unchanged_submitted_record_is_not_a_blocked_one(self):
		doc = _Doc(docstatus=1, name="B-9", fields=("quantity",), quantity=5)
		result, _ = _upsert(existing="B-9", doc=doc, data={"quantity": 5})
		self.assertEqual((result["action"], result["blocked"]), ("unchanged", []))


class TestLegacyItems(unittest.TestCase):
	"""An Item is named by its code, so one pushed before identities existed is already here."""

	def _create(self, claimed):
		with patch.object(frappe.db, "exists", return_value=True), patch.object(
			frappe.db, "get_value", return_value=frappe._dict(claimed)
		), patch.object(frappe.db, "set_value") as stamp, patch.object(
			r, "_update", return_value={"name": "I-1", "action": "updated", "blocked": []}
		), patch.object(frappe, "get_meta", return_value=frappe._dict(has_field=lambda name: True)):
			result = r._create("Item", {"item_code": "I-1"}, "gk.example.com", "I-1", None, {})
		return result, stamp

	def test_an_unclaimed_item_of_the_same_code_is_adopted(self):
		result, stamp = self._create({r.SOURCE_SITE: None, r.SOURCE_DOCTYPE: None, r.SOURCE_NAME: None})
		self.assertTrue(result["action"].startswith("adopted"))
		stamp.assert_called_once()

	def test_an_item_from_another_origin_is_a_conflict_not_an_overwrite(self):
		with self.assertRaises(r.SourceConflict):
			self._create({r.SOURCE_SITE: "other.example.com", r.SOURCE_DOCTYPE: "Item", r.SOURCE_NAME: "I-1"})


class TestTheLockIsReal(unittest.TestCase):
	def test_a_held_lock_is_seen_by_the_database_and_released(self):
		if frappe.db.db_type == "postgres":
			self.skipTest("advisory locks are transaction-scoped on Postgres")
		key = r._lock_key("BOM", "gk.example.com", "B-LOCK")
		r._lock(key)
		try:
			self.assertEqual(int(frappe.db.sql("select is_free_lock(%s)", (key,))[0][0]), 0)
		finally:
			r._unlock(key)
		self.assertEqual(int(frappe.db.sql("select is_free_lock(%s)", (key,))[0][0]), 1)

	def test_a_lock_that_cannot_be_had_asks_the_sender_to_retry(self):
		with patch.object(frappe.db, "sql", return_value=((0,),)):
			with self.assertRaises(r.ReceiverBusy) as raised:
				r._lock("kggk:test")
		self.assertEqual(raised.exception.http_status_code, 503)

	def test_lock_names_fit_the_database_limit(self):
		self.assertLessEqual(len(r._lock_key("Item", "a" * 200, "b" * 500)), 64)


class TestCapabilities(unittest.TestCase):
	def test_it_announces_a_version(self):
		self.assertEqual(r.capabilities()["version"], r.RECEIVER_VERSION)
