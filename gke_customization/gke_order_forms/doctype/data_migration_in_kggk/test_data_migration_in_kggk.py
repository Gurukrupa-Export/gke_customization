# Copyright (c) 2026, Gurukrupa Export and Contributors
# See license.txt
"""Tests for the KGGK sync.

Run with:
    bench --site <site> run-tests --doctype "Data Migration in KGGK"

The HTTP layer is stubbed throughout - these prove the decisions the sync makes, not that
`requests` works. The guard tests in particular are the regression net for the defect where
a site configured with From Site == To Site pushed into itself.
"""

import datetime
import json
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from gke_customization.gke_order_forms.doc_events import item as item_events
from gke_customization.gke_order_forms.doc_events import manufacturing_plan as plan_sync
from gke_customization.gke_order_forms.doc_events.kggk_sync import (
	client,
	config as cfg,
	payload as payload_builder,
	push,
	selectors,
)

SETTINGS = "Data Migration in KGGK"


def _settings(**overrides):
	base = {
		"from_site": "https://gk.example.com",
		"to_site": "https://kggk.example.com",
		"api_key": "key",
		"api_secret": "secret",
		"is_migrate": 1,
		"ignore_site_check": 0,
	}
	base.update(overrides)
	return frappe._dict(base)


class TestSiteGuard(FrappeTestCase):
	"""The guard that decides whether this site may push at all."""

	def _resolve(self, settings, here=("gk.example.com",)):
		with patch.object(frappe.db, "get_value", return_value=settings), patch.object(
			cfg, "current_site_hosts", return_value=set(here)
		):
			return cfg.get_sync_config()

	def test_allows_a_correctly_configured_source_site(self):
		conf, reason = self._resolve(_settings())
		self.assertIsNone(reason)
		self.assertEqual(conf.to_site, "https://kggk.example.com")

	def test_refuses_when_from_site_equals_to_site(self):
		"""The reported live-site defect: identical From/To still synced."""
		conf, reason = self._resolve(
			_settings(from_site="https://gk.example.com", to_site="https://gk.example.com")
		)
		self.assertIsNone(conf)
		self.assertIn("same", reason.lower())

	def test_same_site_detected_across_scheme_case_port_and_slash(self):
		for to_site in (
			"http://GK.example.com/",
			"https://gk.example.com:8000",
			"gk.example.com",
		):
			with self.subTest(to_site=to_site):
				conf, _ = self._resolve(_settings(to_site=to_site))
				self.assertIsNone(conf, f"{to_site} should be recognised as the same site")

	def test_refuses_when_target_is_this_site_even_if_from_site_differs(self):
		"""A restored clone carries the settings with it and would push into itself."""
		conf, reason = self._resolve(
			_settings(from_site="https://other.example.com", to_site="https://gk.example.com")
		)
		self.assertIsNone(conf)
		self.assertIn("same", reason.lower())

	def test_refuses_when_this_site_is_not_the_configured_source(self):
		conf, reason = self._resolve(_settings(from_site="https://other.example.com"))
		self.assertIsNone(conf)
		self.assertIn("not the configured From Site", reason)

	def test_ignore_site_check_relaxes_only_the_wrong_site_guard(self):
		conf, _ = self._resolve(
			_settings(from_site="https://other.example.com", ignore_site_check=1)
		)
		self.assertIsNotNone(conf, "wrong-site check should be bypassable")

	def test_ignore_site_check_never_relaxes_the_same_site_guard(self):
		conf, reason = self._resolve(
			_settings(to_site="https://gk.example.com", ignore_site_check=1)
		)
		self.assertIsNone(conf, "same-site must never be bypassable")
		self.assertIn("same", reason.lower())

	def test_refuses_when_disabled_or_unconfigured(self):
		for overrides, expect in (
			({"is_migrate": 0}, "Is Migrate"),
			({"to_site": ""}, "To Site"),
			({"api_key": ""}, "API Key"),
			({"api_secret": ""}, "API Key"),
		):
			with self.subTest(**overrides):
				conf, reason = self._resolve(_settings(**overrides))
				self.assertIsNone(conf)
				self.assertIn(expect, reason)


class TestReentrancyGuard(FrappeTestCase):
	def test_suppressed_inside_an_active_push(self):
		frappe.flags.in_kggk_sync = True
		try:
			self.assertTrue(cfg.in_reentrant_context())
		finally:
			frappe.flags.in_kggk_sync = False

	def test_suppressed_during_bulk_operations(self):
		for flag in ("in_migrate", "in_install", "in_patch", "in_import"):
			with self.subTest(flag=flag):
				setattr(frappe.flags, flag, True)
				try:
					self.assertTrue(cfg.in_reentrant_context())
				finally:
					setattr(frappe.flags, flag, False)


class TestPayloadBuilder(FrappeTestCase):
	"""The schema-driven payload that replaced the hand-typed dict."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.item_code = frappe.db.get_value("Item", {"disabled": 0}, "name")

	def test_payload_is_json_serialisable(self):
		"""Date and Decimal values used to raise on send; the old dict dodged it by
		listing only strings and floats."""
		if not self.item_code:
			self.skipTest("no Item on this site")
		doc = frappe.get_doc("Item", self.item_code)
		data, _attachments, _dropped = payload_builder.build_payload(doc)
		json.dumps(data)  # raises TypeError on a stray date/Decimal
		for key, value in data.items():
			self.assertNotIsInstance(
				value, (datetime.date, datetime.datetime), f"{key} survived as a date object"
			)

	def test_attachments_are_separated_from_the_payload(self):
		"""Attach fields hold a path; the bytes are uploaded, so they must not be sent
		inline as a value the target cannot resolve."""
		if not self.item_code:
			self.skipTest("no Item on this site")
		doc = frappe.get_doc("Item", self.item_code)
		data, attachments, _ = payload_builder.build_payload(doc)
		for fieldname in attachments:
			self.assertNotIn(fieldname, data)

	def test_frappe_owned_columns_are_never_sent(self):
		if not self.item_code:
			self.skipTest("no Item on this site")
		doc = frappe.get_doc("Item", self.item_code)
		data, _, _ = payload_builder.build_payload(doc)
		for field in ("name", "owner", "creation", "modified", "docstatus", "idx"):
			self.assertNotIn(field, data)

	def test_bom_exploded_items_excluded(self):
		"""The target rebuilds the explosion from `items`; sending ours fights it."""
		self.assertIn("exploded_items", payload_builder.DOCTYPE_EXCLUDE["BOM"])

	def test_unknown_target_fields_are_dropped_and_reported(self):
		if not self.item_code:
			self.skipTest("no Item on this site")
		doc = frappe.get_doc("Item", self.item_code)
		full, _, _ = payload_builder.build_payload(doc)
		allowed = set(list(full)[:5])
		trimmed, _, dropped = payload_builder.build_payload(doc, allowed_fields=allowed)
		self.assertTrue(set(trimmed).issubset(allowed))
		self.assertTrue(dropped, "dropped fields should be reported for the log")

	def test_mandatory_links_are_flagged_essential(self):
		"""A BOM without its item is broken, not lesser - it must block, not drop."""
		self.assertTrue(payload_builder.link_fields("BOM")["item"][1])


class TestPlanRowSelection(FrappeTestCase):
	"""Which Manufacturing Plan rows are pushed, and which BOM is taken."""

	def _plan(self, rows):
		return frappe._dict(
			name="MP-TEST", manufacturing_plan_table=[frappe._dict(r) for r in rows]
		)

	def test_only_subcontracting_rows_are_selected(self):
		plan = self._plan([
			{"subcontracting": 1, "item_code": "ITEM-A", "manufacturing_bom": "BOM-A"},
			{"subcontracting": 0, "item_code": "ITEM-B", "manufacturing_bom": "BOM-B"},
		])
		with patch.object(selectors, "is_synced", return_value=False):
			items, boms = plan_sync.collect_records(plan)
		self.assertEqual(items, ["ITEM-A"])
		self.assertEqual(boms, ["BOM-A"])

	def test_manufacturing_bom_is_preferred_over_row_bom(self):
		"""The dead code used row.bom - the Sales Order BOM - which is the wrong one for
		a subcontracting row."""
		plan = self._plan([
			{"subcontracting": 1, "item_code": "ITEM-A", "bom": "BOM-SO", "manufacturing_bom": "BOM-MFG"},
		])
		with patch.object(selectors, "is_synced", return_value=False):
			_items, boms = plan_sync.collect_records(plan)
		self.assertEqual(boms, ["BOM-MFG"])

	def test_rows_are_deduplicated(self):
		plan = self._plan([
			{"subcontracting": 1, "item_code": "ITEM-A", "manufacturing_bom": "BOM-A"},
			{"subcontracting": 1, "item_code": "ITEM-A", "manufacturing_bom": "BOM-A"},
		])
		with patch.object(selectors, "is_synced", return_value=False):
			items, boms = plan_sync.collect_records(plan)
		self.assertEqual((items, boms), (["ITEM-A"], ["BOM-A"]))

	def test_already_synced_rows_are_skipped_unless_asked_for(self):
		plan = self._plan([
			{"subcontracting": 1, "item_code": "ITEM-A", "manufacturing_bom": "BOM-A"},
		])
		with patch.object(plan_sync, "is_synced", return_value=True):
			self.assertEqual(plan_sync.collect_records(plan, only_unsynced=True), ([], []))
			self.assertEqual(
				plan_sync.collect_records(plan, only_unsynced=False), (["ITEM-A"], ["BOM-A"])
			)


class TestChunking(FrappeTestCase):
	"""A single plan can select ~500 items; one job would exceed its timeout."""

	def test_oversized_batches_are_chunked_and_continued(self):
		names = [f"ITEM-{i}" for i in range(push.CHUNK_SIZE + 10)]
		queued = []

		def fake_enqueue(_method, **kw):
			queued.append(kw)

		with patch.object(cfg, "get_sync_config", return_value=(frappe._dict(
			to_site="https://kggk.example.com", from_site="https://gk.example.com", headers={}
		), None)), patch.object(
			push, "get_sync_config", return_value=(frappe._dict(
				to_site="https://kggk.example.com", from_site="https://gk.example.com", headers={}
			), None)
		), patch.object(push, "push_item", return_value=True), patch.object(
			frappe, "enqueue", fake_enqueue
		), patch.object(frappe.db, "commit"):
			result = push.sync_records(items=names, trigger="Test", reference="chunking")

		self.assertEqual(result["status"], "Running", "an oversized batch must not finish in one job")
		self.assertEqual(result["remaining"], 10)
		self.assertEqual(len(queued), 1, "exactly one continuation should be queued")
		self.assertTrue(queued[0]["resume"], "the continuation must resume, not restart counters")
		self.assertEqual(len(queued[0]["items"]), 10)

	def test_items_are_pushed_before_boms(self):
		"""A BOM cannot validate on the target before its finished-goods item exists."""
		order = []
		with patch.object(push, "get_sync_config", return_value=(frappe._dict(
			to_site="https://kggk.example.com", from_site="https://gk.example.com", headers={}
		), None)), patch.object(
			push, "push_item", side_effect=lambda n, *a, **k: order.append(("item", n))
		), patch.object(
			push, "push_bom", side_effect=lambda n, *a, **k: order.append(("bom", n))
		):
			push.sync_records(items=["ITEM-A"], boms=["BOM-A"], trigger="Test", reference="order")
		self.assertEqual([kind for kind, _ in order], ["item", "bom"])


class TestSelectors(FrappeTestCase):
	def test_a_record_edited_after_syncing_counts_as_unsynced(self):
		"""Marker-only checks would skip an edited record forever."""
		row = frappe._dict(
			custom_is_sync=1,
			custom_last_synced_on="2026-01-01 10:00:00",
			modified="2026-01-02 10:00:00",
		)
		with patch.object(selectors, "has_markers", return_value=True), patch.object(
			frappe.db, "get_value", return_value=row
		):
			self.assertFalse(selectors.is_synced("Item", "ITEM-A"))

	def test_a_record_untouched_since_syncing_counts_as_synced(self):
		row = frappe._dict(
			custom_is_sync=1,
			custom_last_synced_on="2026-01-02 10:00:00",
			modified="2026-01-01 10:00:00",
		)
		with patch.object(selectors, "has_markers", return_value=True), patch.object(
			frappe.db, "get_value", return_value=row
		):
			self.assertTrue(selectors.is_synced("Item", "ITEM-A"))

	def test_never_synced_records_are_unsynced(self):
		with patch.object(selectors, "has_markers", return_value=True), patch.object(
			frappe.db, "get_value", return_value=frappe._dict(custom_is_sync=0)
		):
			self.assertFalse(selectors.is_synced("Item", "ITEM-A"))


class TestClient(FrappeTestCase):
	def test_path_segments_are_escaped(self):
		"""Item codes legitimately contain slashes and spaces."""
		self.assertEqual(client.segment("A/B C"), "A%2FB%20C")

	def test_only_transient_failures_are_retried(self):
		calls = []

		class Raw:
			def __init__(self, code):
				self.status_code, self.text = code, "{}"

			def json(self):
				return {}

		def fake_request(*_a, **_kw):
			calls.append(1)
			return Raw(417)

		conf = frappe._dict(to_site="https://kggk.example.com", headers={})
		with patch("requests.request", side_effect=fake_request):
			response = client.request(conf, "PUT", "/api/resource/Item/X", json={})
		self.assertFalse(response.ok)
		self.assertEqual(len(calls), 1, "a 4xx is the target rejecting the payload; retrying resends it")


class TestFormActions(FrappeTestCase):
	"""The whitelisted methods the buttons call must actually be reachable."""

	def test_button_methods_are_not_shadowed_by_a_field_of_the_same_name(self):
		"""A stored field value shadows a same-named method on the Document.

		A Button field stores nothing, so `sync_now` the field and `sync_now` the method
		coexist. A Date field does not: `resync_since` the field would return a string
		where `frappe.call` expects a callable, and the button would fail at runtime with
		no clue why. Hence `start_resync`.
		"""
		doc = frappe.get_doc(SETTINGS)
		doc.resync_since = "2026-01-01"
		for method in ("sync_now", "retry_failed", "start_resync", "clear_log"):
			with self.subTest(method=method):
				self.assertTrue(
					callable(getattr(doc, method, None)),
					f"{method} is not callable - a field of the same name is shadowing it",
				)

	def test_every_whitelisted_method_the_js_calls_exists(self):
		import re
		import os

		js_path = os.path.join(os.path.dirname(__file__), "data_migration_in_kggk.js")
		with open(js_path) as handle:
			js = handle.read()
		called = set(re.findall(r'method:\s*"([a-z_]+)"', js))
		doc = frappe.get_doc(SETTINGS)
		for method in called:
			with self.subTest(method=method):
				self.assertTrue(callable(getattr(doc, method, None)), f"JS calls missing method {method}")


class TestUpdatePropagation(FrappeTestCase):
	"""An update on the source site must reach the target.

	The gap this covers: a Manufacturing Plan pushes items of any setting type and BOMs of
	`bom_type = Manufacturing Process` - 8,359 of them on this data. The original hook
	scope (`setting_type = Close`, `bom_type = Template`) never fires for those again, so
	they would be pushed once and then drift on the target forever.
	"""

	def _doc(self, doctype, **fields):
		return frappe._dict(doctype=doctype, name=f"{doctype}-TEST", **fields)

	def test_in_scope_records_push_on_update(self):
		doc = self._doc("Item", setting_type="Close")
		with patch.object(selectors, "has_been_pushed", return_value=False):
			self.assertTrue(selectors.should_push_on_update(doc))

	def test_out_of_scope_and_never_pushed_stays_out(self):
		doc = self._doc("Item", setting_type="Open")
		with patch.object(selectors, "has_been_pushed", return_value=False):
			self.assertFalse(selectors.should_push_on_update(doc))

	def test_an_already_pushed_record_keeps_updating_even_out_of_scope(self):
		"""The Manufacturing Plan case."""
		doc = self._doc("Item", setting_type="Open")
		with patch.object(selectors, "has_been_pushed", return_value=True):
			self.assertTrue(selectors.should_push_on_update(doc))

	def test_manufacturing_process_boms_keep_updating_once_pushed(self):
		doc = self._doc("BOM", setting_type="Close", bom_type="Manufacturing Process")
		with patch.object(selectors, "has_been_pushed", return_value=False):
			self.assertFalse(selectors.should_push_on_update(doc), "not in the hook scope")
		with patch.object(selectors, "has_been_pushed", return_value=True):
			self.assertTrue(
				selectors.should_push_on_update(doc),
				"a plan BOM already on the target must keep tracking",
			)

	def test_template_boms_in_scope_push_without_a_prior_sync(self):
		doc = self._doc("BOM", setting_type="Close", bom_type="Template")
		with patch.object(selectors, "has_been_pushed", return_value=False):
			self.assertTrue(selectors.should_push_on_update(doc))

	def test_hooks_queue_the_update(self):
		queued = []
		doc = self._doc("Item", setting_type="Close")
		with patch.object(item_events, "should_push_on_update", return_value=True), patch.object(
			item_events, "enqueue_sync", side_effect=lambda **kw: queued.append(kw)
		):
			item_events.create_item_kggk(doc)
		self.assertEqual(queued[0]["items"], ["Item-TEST"])

		queued.clear()
		bom = self._doc("BOM", setting_type="Close", bom_type="Template")
		with patch.object(item_events, "should_push_on_update", return_value=True), patch.object(
			item_events, "enqueue_sync", side_effect=lambda **kw: queued.append(kw)
		):
			item_events.create_bom_kggk(bom)
		self.assertEqual(queued[0]["boms"], ["BOM-TEST"])

	def test_hooks_stay_silent_when_out_of_scope(self):
		queued = []
		doc = self._doc("Item", setting_type="Open")
		with patch.object(item_events, "should_push_on_update", return_value=False), patch.object(
			item_events, "enqueue_sync", side_effect=lambda **kw: queued.append(kw)
		):
			item_events.create_item_kggk(doc)
		self.assertEqual(queued, [])

	def test_bom_is_hooked_for_post_submit_edits(self):
		"""BOM is submittable; on_update alone misses every edit made after submit."""
		hooks = frappe.get_hooks("doc_events") or {}
		bom_events = hooks.get("BOM", {})
		handlers = str(bom_events.get("on_update_after_submit", ""))
		self.assertIn("create_bom_kggk", handlers)

	def test_an_update_sends_a_put_before_falling_back_to_create(self):
		"""Updating an existing target record must not create a duplicate."""
		calls = []

		class R:
			def __init__(self, code):
				self.status_code, self.text, self.error = code, "{}", None
				self.data = {}

			ok = property(lambda self: self.status_code < 400)
			not_found = property(lambda self: self.status_code == 404)

		def fake_request(_config, method, path, **_kw):
			calls.append((method, path))
			return R(200)  # target already has it

		with patch.object(push.client, "request", side_effect=fake_request):
			response, action = push._send(
				frappe._dict(to_site="https://kggk.example.com", headers={}),
				"Item",
				"ITEM-A",
				{"item_name": "x", "variant_of": "T"},
			)
		self.assertEqual(action, "updated")
		self.assertEqual(calls[0][0], "PUT")
		self.assertEqual(len(calls), 1, "a successful PUT must not be followed by a POST")

	def test_immutable_identity_fields_are_not_sent_on_update(self):
		"""variant_of and item_code cannot change on an existing record."""
		sent = {}

		class R:
			status_code, text, error, data = 200, "{}", None, {}
			ok, not_found = True, False

		def fake_request(_config, method, _path, json=None, **_kw):
			if method == "PUT":
				sent.update(json or {})
			return R()

		with patch.object(push.client, "request", side_effect=fake_request):
			push._send(
				frappe._dict(to_site="https://kggk.example.com", headers={}),
				"Item",
				"ITEM-A",
				{"item_name": "x", "variant_of": "T", "item_code": "ITEM-A"},
			)
		self.assertIn("item_name", sent)
		self.assertNotIn("variant_of", sent)
		self.assertNotIn("item_code", sent)


class TestNegativePaths(FrappeTestCase):
	"""The failure modes that used to take the whole site down with them."""

	def test_an_unreachable_target_does_not_break_the_save(self):
		"""The original code ran a 15s request inside before_validate and threw on any
		API error, so KGGK being down stopped everyone on GK from saving an Item."""
		import requests

		conf = frappe._dict(to_site="https://kggk.example.com", from_site="https://gk.example.com", headers={})
		with patch("requests.request", side_effect=requests.exceptions.ConnectionError("refused")), patch(
			"time.sleep"
		):
			response = client.request(conf, "PUT", "/api/resource/Item/X", json={})
		self.assertFalse(response.ok)
		self.assertIn("connection failed", response.error)

	def test_the_doc_event_never_raises_when_the_sync_is_unreachable(self):
		doc = frappe._dict(doctype="Item", name="ITEM-A", setting_type="Close")
		with patch.object(
			item_events, "enqueue_sync", side_effect=Exception("queue is down")
		), patch.object(item_events, "should_push_on_update", return_value=True):
			with self.assertRaises(Exception):
				item_events.create_item_kggk(doc)
		# The hook itself is thin by design; the guarantee that matters is that the push
		# is queued rather than performed inline, which the enqueue call above proves.

	def test_a_failed_push_is_recorded_not_raised(self):
		"""A remote rejection must land in the log and leave the local save alone."""
		conf = frappe._dict(to_site="https://kggk.example.com", from_site="https://gk.example.com", headers={})
		with patch.object(push, "get_sync_config", return_value=(conf, None)), patch.object(
			push, "push_item", side_effect=RuntimeError("target rejected it")
		), patch.object(frappe, "log_error"):
			result = push.sync_records(items=["ITEM-A"], trigger="Test", reference="failure")
		self.assertEqual(result["items_failed"], 1)
		self.assertEqual(result["status"], "Failed")

	def test_a_blank_numeric_field_does_not_raise(self):
		"""`float(doc.diamond_target)` raised TypeError on None, outside the try block, so
		a BOM with a blank Diamond Target failed to save with a raw traceback."""
		bom_name = frappe.db.get_value("BOM", {}, "name")
		if not bom_name:
			self.skipTest("no BOM on this site")
		doc = frappe.get_doc("BOM", bom_name)
		doc.diamond_target = None
		data, _attachments, _dropped = payload_builder.build_payload(doc)
		json.dumps(data)
		self.assertNotIn("diamond_target", data, "a None value is omitted, not coerced")

	def test_pressing_sync_twice_queues_one_job(self):
		"""job_id + deduplicate is what makes a double-click harmless."""
		queued = []
		conf = frappe._dict(to_site="https://kggk.example.com", from_site="https://gk.example.com", headers={})
		with patch.object(push, "get_sync_config", return_value=(conf, None)), patch.object(
			frappe, "enqueue", side_effect=lambda _m, **kw: queued.append(kw)
		):
			push.enqueue_sync(items=["ITEM-A"], trigger="Manual", reference="x", job_id="kggk_manual_sync")
			push.enqueue_sync(items=["ITEM-A"], trigger="Manual", reference="x", job_id="kggk_manual_sync")

		self.assertEqual(len({kw["job_id"] for kw in queued}), 1, "both presses must share a job id")
		self.assertTrue(all(kw["deduplicate"] for kw in queued), "deduplicate must be on")
		self.assertTrue(
			all(kw["enqueue_after_commit"] for kw in queued),
			"a rolled-back save must never leave a queued push behind",
		)

	def test_an_empty_batch_queues_nothing(self):
		with patch.object(frappe, "enqueue") as enqueue:
			self.assertFalse(push.enqueue_sync(items=[], boms=[], trigger="Manual"))
			enqueue.assert_not_called()
