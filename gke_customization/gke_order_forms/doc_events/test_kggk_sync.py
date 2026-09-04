"""Tests for the Item / BOM / Manufacturing Plan push to KGGK.

Unit tests against patched boundaries rather than integration tests: the things worth
proving are a set of refusals, a report, a batching contract, and the fact that nothing here
can break a save or a submit - all of which must be provable without a second site to push
at.

Runs that would otherwise open a KGGK Sync Log pass ``log=k.LOG_NEVER``, so the reporting
tests stay pure and do not litter the database with documents.
"""

import unittest
from contextlib import ExitStack
from unittest.mock import ANY, patch

import frappe

from . import kggk_sync as k

MOD = "gke_customization.gke_order_forms.doc_events.kggk_sync"


def _settings(**overrides):
	base = {
		"from_site": "https://gk.example.com",
		"to_site": "https://kggk.example.com",
		"enable_sync": 1,
		"api_key": "key",
	}
	base.update(overrides)
	return frappe._dict(base)


def _run(**kwargs):
	kwargs.setdefault("log", k.LOG_NEVER)
	return k.SyncRun(**kwargs)


class TestConfigGuards(unittest.TestCase):
	def _resolve(self, settings, secret="secret", hosts=("gk.example.com",)):
		with patch.object(frappe.db, "get_value", return_value=settings), patch(
			f"{MOD}._api_secret", return_value=secret
		), patch.object(k, "current_site_hosts", return_value=set(hosts)):
			return k.get_sync_config()

	def test_switch_off_refuses_even_when_fully_configured(self):
		"""The switch is the switch. A complete configuration does not override it."""
		cfg, reason = self._resolve(_settings(enable_sync=0))
		self.assertIsNone(cfg)
		self.assertEqual(reason, k.SKIP_DISABLED)

	def test_no_target_refuses(self):
		cfg, reason = self._resolve(_settings(to_site=None))
		self.assertEqual(reason, k.SKIP_NO_TARGET)

	def test_no_key_refuses(self):
		cfg, reason = self._resolve(_settings(api_key=None))
		self.assertEqual(reason, k.SKIP_NO_CREDS)

	def test_unreadable_secret_refuses(self):
		"""A secret that reads back empty must refuse, not send an empty token."""
		cfg, reason = self._resolve(_settings(), secret=None)
		self.assertEqual(reason, k.SKIP_NO_CREDS)

	def test_target_is_this_site_refuses(self):
		"""A Single travels with a database restore, so a clone arrives pointed at itself."""
		cfg, reason = self._resolve(_settings(), hosts=("kggk.example.com",))
		self.assertIn("refusing to sync a site to itself", reason)

	def test_target_equals_from_site_refuses(self):
		cfg, reason = self._resolve(_settings(from_site="https://kggk.example.com"))
		self.assertIn("refusing to sync a site to itself", reason)

	def test_success_targets_the_to_site(self):
		cfg, reason = self._resolve(_settings())
		self.assertIsNone(reason)
		self.assertEqual(cfg.to_site, "https://kggk.example.com")
		self.assertEqual(cfg.headers["Authorization"], "token key:secret")


class TestSecretReading(unittest.TestCase):
	"""`api_secret` is a Data field today, but must survive becoming a Password."""

	def test_plain_value_is_used_as_is(self):
		with patch.object(frappe.db, "get_single_value", return_value="real"), patch(
			"frappe.utils.password.get_decrypted_password"
		) as gdp:
			self.assertEqual(k._api_secret(), "real")
		gdp.assert_not_called()

	def test_password_placeholder_falls_back_to_auth_table(self):
		"""'*****' in tabSingles authenticates as nothing; the 401 misleads completely."""
		with patch.object(frappe.db, "get_single_value", return_value="*****"), patch(
			"frappe.utils.password.get_decrypted_password", return_value="real"
		) as gdp:
			self.assertEqual(k._api_secret(), "real")
		gdp.assert_called_once()

	def test_failure_is_swallowed(self):
		with patch.object(frappe.db, "get_single_value", return_value=None), patch(
			"frappe.utils.password.get_decrypted_password", side_effect=Exception("boom")
		):
			self.assertIsNone(k._api_secret())


class TestBatchedExistence(unittest.TestCase):
	"""The fix for the timeout. One request per fifty names, not one per name."""

	def setUp(self):
		self.cfg = frappe._dict(to_site="https://t", headers={})

	def _ok(self, names):
		return k.Response(status_code=200, data={"data": [{"name": n} for n in names]})

	def test_limit_page_length_is_sent_explicitly(self):
		"""Without it the REST layer caps at 20 and thirty present records look missing."""
		with patch(f"{MOD}.api_get", return_value=self._ok(["I-1"])) as get:
			k.api_exists_many(self.cfg, "Item", ["I-1"])
		self.assertEqual(get.call_args.kwargs["params"]["limit_page_length"], 0)

	def test_names_are_batched_not_asked_one_by_one(self):
		names = [f"I-{i}" for i in range(120)]
		with patch(f"{MOD}.api_get", return_value=self._ok([])) as get:
			k.api_exists_many(self.cfg, "Item", names)
		# 120 names at 50 per request, versus 120 requests before.
		self.assertEqual(get.call_count, 3)

	def test_long_names_split_earlier_than_the_count_bound(self):
		"""Gunicorn refuses a request line over 4094 bytes; item codes are long."""
		names = [f"ITEM/{'X' * 120}/{i}" for i in range(50)]
		with patch(f"{MOD}.api_get", return_value=self._ok([])) as get:
			k.api_exists_many(self.cfg, "Item", names)
		self.assertGreater(get.call_count, 1)

	def test_present_and_absent_are_separated(self):
		with patch(f"{MOD}.api_get", return_value=self._ok(["I-1"])):
			found = k.api_exists_many(self.cfg, "Item", ["I-1", "I-2"])
		self.assertEqual(found, {"I-1": True, "I-2": False})

	def test_a_failed_batch_is_unknown_never_absent(self):
		"""A false 'absent' costs one redundant PUT. A false 'present' skips it forever."""
		run = _run(config=frappe._dict(to_site="https://t"))
		with patch(f"{MOD}.api_get", return_value=k.Response(status_code=500, text="nope")):
			found = k.api_exists_many(self.cfg, "Item", ["I-1", "I-2"], run=run)
		self.assertEqual(found, {})
		self.assertIn("LINK-UNKNOWN", " ".join(run.problems))

	def test_names_with_slashes_and_spaces_round_trip(self):
		"""Jewellery item codes legitimately contain both."""
		name = "GOLD RING/22K/01"
		with patch(f"{MOD}.api_get", return_value=self._ok([name])):
			self.assertEqual(k.api_exists_many(self.cfg, "Item", [name]), {name: True})

	def test_empty_input_asks_nothing(self):
		with patch(f"{MOD}.api_get") as get:
			self.assertEqual(k.api_exists_many(self.cfg, "Item", []), {})
		get.assert_not_called()


class TestConnectivityPreflight(unittest.TestCase):
	"""Three outcomes that look identical from inside a failed sync."""

	def setUp(self):
		self.cfg = frappe._dict(to_site="https://t", headers={})

	def test_unreachable_host(self):
		with patch(f"{MOD}.api_get", return_value=k.Response(error="connection failed: dns")):
			ok, message = k.check_connectivity(self.cfg)
		self.assertFalse(ok)
		self.assertIn("could not be reached", message)

	def test_bad_credentials_say_so(self):
		with patch(f"{MOD}.api_get", return_value=k.Response(status_code=401, text="no")):
			ok, message = k.check_connectivity(self.cfg)
		self.assertFalse(ok)
		self.assertIn("API Key", message)

	def test_success_names_the_user(self):
		reply = k.Response(status_code=200, data={"message": "sync@kggk"})
		with patch(f"{MOD}.api_get", return_value=reply):
			ok, message = k.check_connectivity(self.cfg)
		self.assertTrue(ok)
		self.assertIn("sync@kggk", message)

	def test_it_does_not_retry(self):
		"""Three attempts on a 30s timeout is 96 seconds - the thing being avoided."""
		with patch(f"{MOD}.api_get", return_value=k.Response(status_code=200, data={})) as get:
			k.check_connectivity(self.cfg)
		self.assertEqual(get.call_args.kwargs["attempts"], 1)


class TestRowSelection(unittest.TestCase):
	def _plan(self, rows):
		return frappe._dict(name="MP-0001", manufacturing_plan_table=[frappe._dict(r) for r in rows])

	def test_only_subcontracting_rows(self):
		items, boms = k.collect_records(
			self._plan(
				[
					{"item_code": "I-1", "manufacturing_bom": "B-1", "subcontracting": 1},
					{"item_code": "I-2", "manufacturing_bom": "B-2", "subcontracting": 0},
				]
			)
		)
		self.assertEqual((items, boms), (["I-1"], ["B-1"]))

	def test_manufacturing_bom_is_used_not_row_bom(self):
		"""row.bom is the Sales Order BOM and must never be selected."""
		items, boms = k.collect_records(
			self._plan([{"item_code": "I-1", "bom": "SO-BOM", "manufacturing_bom": "MFG", "subcontracting": 1}])
		)
		self.assertEqual(boms, ["MFG"])

	def test_duplicates_collapse(self):
		row = {"item_code": "I-1", "manufacturing_bom": "B-1", "subcontracting": 1}
		items, boms = k.collect_records(self._plan([row, dict(row)]))
		self.assertEqual((items, boms), (["I-1"], ["B-1"]))


class TestPlanRecordsIsOneQuery(unittest.TestCase):
	def test_child_rows_are_fetched_once_not_once_per_plan(self):
		plans = [f"MP-{i}" for i in range(40)]
		rows = [frappe._dict(item_code="I-1", manufacturing_bom="B-1")]
		with patch.object(frappe, "get_all", side_effect=[plans, rows]) as get_all:
			out_plans, items, boms = k._plan_records()
		self.assertEqual(get_all.call_count, 2)
		self.assertEqual((out_plans, items, boms), (plans, ["I-1"], ["B-1"]))

	def test_no_plans_asks_nothing_further(self):
		with patch.object(frappe, "get_all", side_effect=[[]]) as get_all:
			self.assertEqual(k._plan_records(), ([], [], []))
		self.assertEqual(get_all.call_count, 1)


class TestSaveAndSubmitNeverRaise(unittest.TestCase):
	"""The whole point of replacing the before_validate hooks."""

	def test_enqueue_failure_does_not_reach_submit(self):
		"""Redis down must not roll back the Manufacturing Plan.

		enqueue_after_commit only defers the handoff - frappe.enqueue still opens redis and
		runs its queue-size check inside the submit transaction.
		"""
		doc = frappe._dict(
			name="MP-0001",
			manufacturing_plan_table=[frappe._dict(item_code="I-1", manufacturing_bom="B-1", subcontracting=1)],
		)
		with patch.object(k, "get_sync_config", return_value=(frappe._dict(to_site="x"), None)), patch.object(
			k, "enqueue_sync", side_effect=ConnectionError("redis is down")
		):
			k.on_submit(doc)  # must not raise

	def test_enqueue_failure_does_not_reach_an_item_save(self):
		doc = frappe._dict(doctype="Item", name="I-1", setting_type="Close")
		with patch.object(k, "is_sync_enabled", return_value=True), patch.object(
			k, "setting", return_value=1
		), patch.object(
			k, "get_sync_config", return_value=(frappe._dict(to_site="https://t"), None)
		), patch.object(
			k, "enqueue_sync", side_effect=ConnectionError("redis is down")
		):
			k.item_on_update(doc)  # must not raise


class TestUpdateEligibility(unittest.TestCase):
	"""Who gets pushed on save, and who is left alone."""

	def setUp(self):
		self.cfg = frappe._dict(to_site="https://kggk.example.com")

	def _save(self, doc, synced=False, enabled=True, sync_updates=1):
		with patch.object(k, "is_sync_enabled", return_value=enabled), patch.object(
			k, "setting", return_value=sync_updates
		), patch.object(k, "get_sync_config", return_value=(self.cfg, None)), patch.object(
			k, "is_synced", return_value=synced
		), patch.object(
			k, "enqueue_sync"
		) as enqueue:
			k._on_master_update(doc)
		return enqueue

	def test_a_closed_item_is_pushed_even_if_kggk_has_never_seen_it(self):
		"""Exactly what the before_validate hook did. Not a behaviour change."""
		doc = frappe._dict(doctype="Item", name="I-1", setting_type="Close")
		enqueue = self._save(doc, synced=False)
		enqueue.assert_called_once()
		self.assertEqual(enqueue.call_args.kwargs["items"], ["I-1"])

	def test_an_unclosed_item_kggk_has_never_seen_is_left_alone(self):
		"""A live site holds tens of thousands KGGK has never asked for."""
		doc = frappe._dict(doctype="Item", name="I-1", setting_type="Open")
		self._save(doc, synced=False).assert_not_called()

	def test_an_unclosed_item_kggk_already_has_is_still_updated(self):
		"""This is 'transfer later changes'."""
		doc = frappe._dict(doctype="Item", name="I-1", setting_type="Open")
		self._save(doc, synced=True).assert_called_once()

	def test_a_bom_needs_template_as_well_as_closed(self):
		"""The BOM gate was stricter than the Item one; it stays stricter."""
		closed_only = frappe._dict(doctype="BOM", name="B-1", setting_type="Close", bom_type="Variant")
		self._save(closed_only, synced=False).assert_not_called()

		template = frappe._dict(doctype="BOM", name="B-1", setting_type="Close", bom_type="Template")
		enqueue = self._save(template, synced=False)
		enqueue.assert_called_once()
		self.assertEqual(enqueue.call_args.kwargs["boms"], ["B-1"])

	def test_the_switch_stops_it_before_anything_is_read(self):
		doc = frappe._dict(doctype="Item", name="I-1", setting_type="Close")
		with patch.object(k, "is_sync_enabled", return_value=False), patch.object(
			k, "get_sync_config"
		) as config, patch.object(k, "enqueue_sync") as enqueue:
			k._on_master_update(doc)
		enqueue.assert_not_called()
		# The cheap gate comes first: no field reads, no password decrypt, on every save.
		config.assert_not_called()

	def test_the_inbound_leg_of_a_sync_does_not_push_back(self):
		doc = frappe._dict(doctype="Item", name="I-1", setting_type="Close")
		frappe.flags.in_kggk_sync = True
		try:
			with patch.object(k, "is_sync_enabled") as enabled, patch.object(k, "enqueue_sync") as enqueue:
				k._on_master_update(doc)
			enqueue.assert_not_called()
			enabled.assert_not_called()
		finally:
			frappe.flags.in_kggk_sync = False

	def test_updates_can_be_switched_off_without_stopping_new_records(self):
		doc = frappe._dict(doctype="Item", name="I-1", setting_type="Open")
		self._save(doc, synced=True, sync_updates=0).assert_not_called()

		still_eligible = frappe._dict(doctype="Item", name="I-2", setting_type="Close")
		self._save(still_eligible, synced=False, sync_updates=0).assert_called_once()


class TestDeferredRelink(unittest.TestCase):
	"""Item.master_bom: dropped on the way out, and until now never put back."""

	def setUp(self):
		self.cfg = frappe._dict(to_site="https://t", headers={})
		self.run = _run(config=self.cfg)

	def test_a_dropped_link_is_remembered(self):
		doc = frappe._dict(doctype="Item", name="I-1")
		data = {"master_bom": "B-1", "item_group": "G-1"}
		with patch.object(k, "link_fields", return_value={"master_bom": ("BOM", False)}), patch.object(
			k, "_link_exists", return_value=False
		):
			blocking = k._strip_missing_links(self.cfg, doc, data, self.run, {})
		self.assertEqual(blocking, [])
		self.assertNotIn("master_bom", data)
		self.assertEqual(self.run.deferred, [("Item", "I-1", "master_bom", "B-1", "BOM")])

	def test_an_essential_link_blocks_instead_of_being_deferred(self):
		"""A BOM without its item is not a lesser BOM, it is a broken one."""
		doc = frappe._dict(doctype="BOM", name="B-1")
		data = {"item": "I-1"}
		with patch.object(k, "link_fields", return_value={"item": ("Item", True)}), patch.object(
			k, "_link_exists", return_value=False
		):
			blocking = k._strip_missing_links(self.cfg, doc, data, self.run, {})
		self.assertTrue(blocking)
		self.assertEqual(self.run.deferred, [])

	def test_the_link_is_put_back_once_the_bom_arrives(self):
		self.run.deferred = [("Item", "I-1", "master_bom", "B-1", "BOM")]
		with patch.object(k, "api_exists_many", return_value={"B-1": True}), patch.object(
			k, "api_put", return_value=k.Response(status_code=200)
		) as put:
			k._apply_deferred_links(self.cfg, self.run)

		# A one-key patch, not a re-push of the whole record.
		self.assertEqual(put.call_args.kwargs["json"], {"master_bom": "B-1"})
		self.assertEqual(self.run.deferred, [])

	def test_two_recovered_fields_on_one_record_cost_one_call(self):
		self.run.deferred = [
			("Item", "I-1", "master_bom", "B-1", "BOM"),
			("Item", "I-1", "other_bom", "B-2", "BOM"),
		]
		with patch.object(k, "api_exists_many", return_value={"B-1": True, "B-2": True}), patch.object(
			k, "api_put", return_value=k.Response(status_code=200)
		) as put:
			k._apply_deferred_links(self.cfg, self.run)
		self.assertEqual(put.call_count, 1)

	def test_what_is_still_missing_is_carried_to_the_next_chunk(self):
		self.run.deferred = [("Item", "I-1", "master_bom", "B-1", "BOM")]
		with patch.object(k, "api_exists_many", return_value={"B-1": False}), patch.object(
			k, "api_put"
		) as put:
			k._apply_deferred_links(self.cfg, self.run)
		put.assert_not_called()
		self.assertEqual(len(self.run.deferred), 1)

	def test_deferred_links_survive_a_chunk_boundary(self):
		"""The item is in chunk 1 and its BOM in chunk 3; both must still be linked."""
		first = _run(config=self.cfg)
		first.defer_link("Item", "I-1", "master_bom", "B-1", "BOM")
		second = _run(config=self.cfg, deferred=first.deferred)
		self.assertEqual(second.deferred, [("Item", "I-1", "master_bom", "B-1", "BOM")])


class TestTargetSchemaFailuresAreReported(unittest.TestCase):
	"""Every route to `None` must say so - a silent one looks like a clean run."""

	def setUp(self):
		self.run = _run(config=frappe._dict(to_site="https://t", from_site="https://f"))
		self.cfg = frappe._dict(to_site="https://t", headers={})
		# The cache key carries the target host, so repointing To Site cannot serve the
		# previous target's schema. Clear the key this test will actually use.
		frappe.cache().delete_value("kggk_target_fields::t::Item")

	tearDown = setUp

	def _kinds(self):
		return [p.split("|")[0].strip() for p in self.run.problems]

	def test_doctype_get_failure_is_reported(self):
		with patch(f"{MOD}.api_get", return_value=k.Response(status_code=500, text="nope")):
			self.assertIsNone(k.get_target_fields(self.cfg, "Item", run=self.run))
		self.assertIn("SCHEMA-UNKNOWN", self._kinds())

	def test_doctype_with_no_fields_is_reported(self):
		empty = k.Response(status_code=200, data={"data": {"fields": []}})
		with patch(f"{MOD}.api_get", return_value=empty):
			self.assertIsNone(k.get_target_fields(self.cfg, "Item", run=self.run))
		self.assertIn("SCHEMA-UNKNOWN", self._kinds())

	def test_custom_field_failure_is_a_failure_not_a_partial_answer(self):
		"""Standard fields known, custom ones not, would be a confident wrong answer."""
		ok = k.Response(status_code=200, data={"data": {"fields": [{"fieldname": "item_code"}]}})
		bad = k.Response(status_code=403, text="forbidden")
		with patch(f"{MOD}.api_get", side_effect=[ok, bad]):
			self.assertIsNone(k.get_target_fields(self.cfg, "Item", run=self.run))
		self.assertIn("SCHEMA-UNKNOWN", self._kinds())

	def test_success_returns_union(self):
		ok = k.Response(status_code=200, data={"data": {"fields": [{"fieldname": "item_code"}]}})
		custom = k.Response(status_code=200, data={"data": [{"fieldname": "custom_thing"}]})
		with patch(f"{MOD}.api_get", side_effect=[ok, custom]):
			fields = k.get_target_fields(self.cfg, "Item", run=self.run)
		self.assertLessEqual({"item_code", "custom_thing"}, fields)
		self.assertEqual(self.run.problems, [])

	def test_reported_once_per_doctype(self):
		with patch(f"{MOD}.api_get", return_value=k.Response(status_code=500)):
			k.get_target_fields(self.cfg, "Item", run=self.run)
			k.get_target_fields(self.cfg, "Item", run=self.run)
		self.assertEqual(len(self.run.problems), 1)

	def test_the_cache_is_scoped_to_the_target(self):
		"""Repointing To Site must not serve the old target's field list."""
		ok = k.Response(status_code=200, data={"data": {"fields": [{"fieldname": "item_code"}]}})
		custom = k.Response(status_code=200, data={"data": []})
		with patch(f"{MOD}.api_get", side_effect=[ok, custom]):
			k.get_target_fields(self.cfg, "Item", run=self.run)
		self.assertIsNotNone(
			frappe.cache().get_value("kggk_target_fields::t::Item", expires=True)
		)

	def test_the_schema_is_fetched_once_not_once_per_record(self):
		"""`push_item` asks per record. Without a working cache that is two round trips
		to the target for every item in the run."""
		ok = k.Response(status_code=200, data={"data": {"fields": [{"fieldname": "item_code"}]}})
		custom = k.Response(status_code=200, data={"data": []})
		with patch(f"{MOD}.api_get", side_effect=[ok, custom]) as get:
			k.get_target_fields(self.cfg, "Item", run=self.run)
			second = k.get_target_fields(self.cfg, "Item", run=self.run)
		self.assertEqual(get.call_count, 2)  # DocType + Custom Field, once between them
		self.assertIn("item_code", second)


class TestReporting(unittest.TestCase):
	def _run_with(self, n):
		run = _run(
			trigger="Manufacturing Plan",
			reference="MP-0001",
			config=frappe._dict(to_site="https://t", from_site="https://f", headers={}),
		)
		for i in range(n):
			run.mismatch("Item", f"I-{i}", "field 'x' does not exist on the target")
		return run

	def test_clean_run_writes_nothing(self):
		with patch(f"{MOD}.api_post") as post:
			self.assertFalse(self._run_with(0).report())
		post.assert_not_called()

	def test_many_problems_become_one_post(self):
		"""Per-record reporting would be hundreds of POSTs at the worst possible moment."""
		run = self._run_with(120)
		with patch(f"{MOD}.api_post", return_value=k.Response(status_code=200)) as post:
			self.assertTrue(run.report())
		self.assertEqual(post.call_count, 1)
		body = post.call_args.kwargs["json"]["error"]
		self.assertIn("I-0", body)
		self.assertIn("I-119", body)

	def test_report_is_capped(self):
		run = self._run_with(400)
		with patch(f"{MOD}.api_post", return_value=k.Response(status_code=200)) as post:
			run.report()
		body = post.call_args.kwargs["json"]["error"]
		self.assertIn("and 200 more", body)
		self.assertLessEqual(len(body), 60_000)

	def test_failed_report_falls_back_locally_without_raising(self):
		run = self._run_with(3)
		with patch(f"{MOD}.api_post", return_value=k.Response(status_code=403, text="denied")), patch(
			"frappe.log_error"
		) as log_error:
			self.assertFalse(run.report())
		self.assertIn("FALLBACK", log_error.call_args.args[0])

	def test_report_never_raises(self):
		run = self._run_with(1)
		with patch(f"{MOD}.api_post", side_effect=RuntimeError("boom")), patch("frappe.log_error"):
			self.assertFalse(run.report())


class TestCounters(unittest.TestCase):
	def test_counters_carry_forward(self):
		"""Chunk state rides in the job kwargs, and must keep doing so.

		The log document is a projection of a run, not its memory: if a log save fails, a
		DB-authoritative design would restart the next chunk's counters at zero and the
		numbers would quietly lie.
		"""
		first = _run()
		first.item_ok("I-1")
		first.bom_failed("B-1", "nope")
		second = _run(counters=first.counters())
		second.item_ok("I-2")
		self.assertEqual(second.counters()["items_synced"], 2)
		self.assertEqual(second.counters()["boms_failed"], 1)


class TestLogging(unittest.TestCase):
	"""A run's diary must never be able to break the run."""

	def test_a_never_logging_run_does_not_touch_the_database(self):
		with patch.object(frappe, "get_doc") as get_doc:
			run = _run(config=frappe._dict(to_site="https://t"))
			run.mismatch("Item", "I-1", "x")
			run.flush(k.STATUS_COMPLETED)
		get_doc.assert_not_called()

	def test_a_single_record_push_opens_no_log_until_something_fails(self):
		"""One log document per Item save, forever, is not a diary - it is a landfill."""
		with patch.object(k.SyncRun, "_open_log", return_value="LOG-1") as open_log:
			run = k.SyncRun(config=frappe._dict(to_site="https://t"), log=k.LOG_ON_PROBLEM)
			self.assertIsNone(run.log_name)
			open_log.assert_not_called()

			run.item_failed("I-1", "target said no")
			self.assertEqual(run.log_name, "LOG-1")

	def test_rows_are_capped_so_a_huge_run_stays_openable(self):
		run = _run(config=frappe._dict(to_site="https://t"))
		for i in range(k.MAX_LOG_ROWS + 25):
			run.row("Item", f"I-{i}", "Synced")
		self.assertEqual(len(run.rows), k.MAX_LOG_ROWS)
		self.assertEqual(run.rows_dropped, 25)

	def test_a_failing_log_save_does_not_abort_the_run(self):
		run = _run(config=frappe._dict(to_site="https://t"))
		run.log_mode = k.LOG_ALWAYS
		run.log_name = "LOG-1"
		with patch.object(frappe, "get_doc", side_effect=RuntimeError("db is unhappy")):
			run.flush(k.STATUS_COMPLETED)  # must not raise


class TestSyncStateIsNotAFeedbackLoop(unittest.TestCase):
	def test_state_is_never_written_onto_the_record_itself(self):
		"""A field on Item would bump Item.modified, so the reconciler would see it as
		stale, re-push it, write the field again - forever."""
		with patch.object(frappe.db, "get_value", return_value=None), patch.object(
			frappe, "get_doc"
		) as get_doc, patch.object(frappe.db, "set_value") as set_value:
			k.mark_state("Item", "I-1", "Synced", "kggk.example.com")
		set_value.assert_not_called()
		self.assertEqual(get_doc.call_args.args[0]["doctype"], k.STATE_DOCTYPE)

	def test_no_target_means_no_row(self):
		with patch.object(frappe, "get_doc") as get_doc:
			k.mark_state("Item", "I-1", "Synced", "")
		get_doc.assert_not_called()

	def test_a_bookkeeping_failure_is_swallowed(self):
		with patch.object(frappe.db, "get_value", side_effect=RuntimeError("boom")):
			k.mark_state("Item", "I-1", "Synced", "kggk.example.com")  # must not raise


class TestReconciler(unittest.TestCase):
	def test_it_does_nothing_unless_switched_on(self):
		with patch.object(k, "setting", return_value=0), patch.object(k, "get_sync_config") as config:
			k.reconcile_changes()
		config.assert_not_called()

	def test_it_refuses_when_the_sync_is_not_configured(self):
		with patch.object(k, "setting", return_value=1), patch.object(
			k, "get_sync_config", return_value=(None, "switch is off")
		), patch.object(k, "enqueue_sync") as enqueue:
			k.reconcile_changes()
		enqueue.assert_not_called()

	def test_it_queues_what_drifted(self):
		with patch.object(k, "setting", side_effect=lambda f, d=None: 1 if f == "auto_reconcile" else 200), patch.object(
			k, "get_sync_config", return_value=(frappe._dict(to_site="https://kggk.example.com"), None)
		), patch.object(k, "_drifted", side_effect=[["I-1"], ["B-1"]]), patch.object(
			k, "enqueue_sync"
		) as enqueue:
			k.reconcile_changes()
		enqueue.assert_called_once_with(
			items=["I-1"], boms=["B-1"], trigger="Reconcile", reference=ANY, job_id="kggk_reconcile"
		)

	def test_the_bom_budget_is_what_the_items_left(self):
		"""One pass has a ceiling; items must not be able to spend the BOMs' share twice."""
		captured = []

		def drifted(doctype, target, limit):
			captured.append(limit)
			return ["I-1"] if doctype == "Item" else []

		with patch.object(k, "setting", side_effect=lambda f, d=None: 1 if f == "auto_reconcile" else 200), patch.object(
			k, "get_sync_config", return_value=(frappe._dict(to_site="https://kggk.example.com"), None)
		), patch.object(k, "_drifted", side_effect=drifted), patch.object(k, "enqueue_sync"):
			k.reconcile_changes()
		self.assertEqual(captured, [200, 199])

	def test_nothing_drifted_queues_nothing(self):
		with patch.object(k, "setting", side_effect=lambda f, d=None: 1 if f == "auto_reconcile" else 200), patch.object(
			k, "get_sync_config", return_value=(frappe._dict(to_site="https://kggk.example.com"), None)
		), patch.object(k, "_drifted", return_value=[]), patch.object(k, "enqueue_sync") as enqueue:
			k.reconcile_changes()
		enqueue.assert_not_called()


class TestRetry(unittest.TestCase):
	def _log(self, rows, status="Partially Completed"):
		return frappe._dict(
			name="KGGK-SYNC-2026-00001",
			status=status,
			records=[frappe._dict(r) for r in rows],
		)

	def test_only_failed_and_pending_rows_are_retried(self):
		log = self._log(
			[
				{"record_doctype": "Item", "record_name": "I-1", "status": "Failed"},
				{"record_doctype": "Item", "record_name": "I-2", "status": "Synced"},
				{"record_doctype": "BOM", "record_name": "B-1", "status": "Pending"},
			]
		)
		new_log = frappe._dict(name="KGGK-SYNC-2026-00002", insert=lambda **kw: None)
		with patch("frappe.only_for"), patch.object(frappe, "get_doc", side_effect=[log, new_log]), patch.object(
			k, "get_sync_config", return_value=(frappe._dict(to_site="https://t"), None)
		), patch.object(k, "enqueue_sync") as enqueue:
			k.retry_log(log.name)

		self.assertEqual(enqueue.call_args.kwargs["items"], ["I-1"])
		self.assertEqual(enqueue.call_args.kwargs["boms"], ["B-1"])

	def test_a_clean_run_has_nothing_to_retry(self):
		log = self._log([{"record_doctype": "Item", "record_name": "I-1", "status": "Synced"}])
		with patch("frappe.only_for"), patch.object(frappe, "get_doc", return_value=log):
			with self.assertRaises(frappe.ValidationError):
				k.retry_log(log.name)

	def test_a_running_log_cannot_be_retried(self):
		log = self._log([], status="Running")
		with patch("frappe.only_for"), patch.object(frappe, "get_doc", return_value=log):
			with self.assertRaises(frappe.ValidationError):
				k.retry_log(log.name)


class TestPrefillStarter(unittest.TestCase):
	"""The regression test for the timeout: the request thread does almost nothing."""

	def setUp(self):
		self.cfg = frappe._dict(to_site="https://t", from_site="https://f", headers={})

	def test_it_refuses_when_not_configured(self):
		with patch.object(k, "get_sync_config", return_value=(None, "switch is off")), patch(
			"frappe.only_for"
		):
			with self.assertRaises(frappe.ValidationError):
				k.start_prefill(apply=0)

	def test_an_unreachable_target_is_a_sentence_not_a_gateway_timeout(self):
		with patch.object(k, "get_sync_config", return_value=(self.cfg, None)), patch.object(
			k, "check_connectivity", return_value=(False, "https://t could not be reached")
		), patch("frappe.only_for"), patch.object(frappe, "enqueue") as enqueue:
			with self.assertRaises(frappe.ValidationError):
				k.start_prefill(apply=0)
		enqueue.assert_not_called()

	def test_it_enqueues_and_returns_without_checking_a_single_record(self):
		log = frappe._dict(name="KGGK-SYNC-2026-00001", insert=lambda **kw: None)
		with patch.object(k, "get_sync_config", return_value=(self.cfg, None)), patch.object(
			k, "check_connectivity", return_value=(True, "Connected")
		), patch.object(k, "_prefill_in_flight", return_value=None), patch(
			"frappe.only_for"
		), patch.object(frappe, "get_doc", return_value=log), patch.object(
			frappe, "enqueue"
		) as enqueue, patch.object(
			k, "api_exists_many"
		) as exists, patch.object(
			k, "_plan_records"
		) as plans:
			out = k.start_prefill(apply=0)

		self.assertEqual(out["log"], log.name)
		enqueue.assert_called_once()
		# None of the slow work happens in the request. This is the bug.
		exists.assert_not_called()
		plans.assert_not_called()

	def test_it_refuses_to_start_a_second_prefill_on_top_of_a_running_one(self):
		with patch.object(k, "get_sync_config", return_value=(self.cfg, None)), patch.object(
			k, "check_connectivity", return_value=(True, "Connected")
		), patch.object(k, "_prefill_in_flight", return_value="KGGK-SYNC-2026-00001"), patch(
			"frappe.only_for"
		):
			with self.assertRaises(frappe.ValidationError):
				k.start_prefill(apply=0)


class TestPrefillWorker(unittest.TestCase):
	"""The job. First press must change nothing on the target."""

	def setUp(self):
		self.cfg = frappe._dict(to_site="https://t", from_site="https://f", headers={})

	def _worker(self, gaps, plans, presence, apply=0, create_result=(True, "created")):
		"""Run `run_prefill` against patched boundaries.

		Returns ``(result, create_mock, enqueue_mock)`` so each test can assert on what the
		worker did to the target as well as on what it reported.
		"""
		with ExitStack() as stack:
			enter = stack.enter_context
			enter(patch.object(k, "get_sync_config", return_value=(self.cfg, None)))
			enter(patch.object(k, "_field_gaps", return_value=gaps))
			enter(patch.object(k, "_plan_records", return_value=plans))
			enter(
				patch.object(
					k,
					"api_exists_many",
					side_effect=lambda cfg, doctype, names, run=None: presence.get(doctype, {}),
				)
			)
			enter(patch.object(k, "_close_prefill"))
			enter(patch.object(k.SyncRun, "_open_log", return_value="LOG-1"))
			enter(patch.object(k.SyncRun, "flush"))
			enter(patch.object(k.SyncRun, "report"))
			create = enter(patch.object(k, "_create_custom_field", return_value=create_result))
			enqueue = enter(patch.object(k, "enqueue_sync", return_value=True))

			result = k.run_prefill("LOG-1", apply=apply)
		return result, create, enqueue

	def test_dry_run_creates_nothing(self):
		out, create, enqueue = self._worker(
			gaps=([{"dt": "Item", "fieldname": "custom_x"}], [], []),
			plans=(["MP-1"], ["I-1"], ["B-1"]),
			presence={"Item": {"I-1": False}, "BOM": {"B-1": False}},
			apply=0,
		)
		create.assert_not_called()
		enqueue.assert_not_called()
		self.assertFalse(out["applied"])
		self.assertEqual(out["fields_to_create"], ["Item.custom_x"])
		self.assertEqual((out["items_missing"], out["boms_missing"]), (1, 1))

	def test_apply_creates_fields_and_queues_records(self):
		out, create, enqueue = self._worker(
			gaps=([{"dt": "Item", "fieldname": "custom_x"}], [], []),
			plans=(["MP-1"], ["I-1"], []),
			presence={"Item": {"I-1": False}},
			apply=1,
		)
		create.assert_called_once()
		enqueue.assert_called_once()
		self.assertEqual(out["fields_created"], ["Item.custom_x"])
		self.assertEqual(enqueue.call_args.kwargs["items"], ["I-1"])

	def test_standard_field_gaps_are_never_created(self):
		"""A missing standard field is a version mismatch, not something to paper over."""
		out, create, _ = self._worker(
			gaps=([], ["Item.some_v16_field (Data)"], []),
			plans=([], [], []),
			presence={},
			apply=1,
		)
		create.assert_not_called()
		self.assertEqual(out["standard_field_gaps"], ["Item.some_v16_field (Data)"])

	def test_unknown_existence_is_not_assumed_present(self):
		"""A name missing from the batch answer means 'we could not ask', not 'absent'."""
		out, _, enqueue = self._worker(
			gaps=([], [], []),
			plans=(["MP-1"], ["I-1"], []),
			presence={"Item": {}},
			apply=0,
		)
		self.assertEqual(out["items_missing"], 0)
		self.assertEqual(out["unchecked"], 1)

	def test_a_failed_field_leaves_the_run_partially_complete(self):
		out, create, _ = self._worker(
			gaps=([{"dt": "Item", "fieldname": "custom_x"}], [], []),
			plans=([], [], []),
			presence={},
			apply=1,
			create_result=(False, "target said no"),
		)
		create.assert_called_once()
		self.assertEqual(out["fields_failed"], ["Item.custom_x"])
		self.assertEqual(out["fields_created"], [])


class TestTargetNaming(unittest.TestCase):
	"""The target decides what it calls a record, and it often disagrees with us.

	ERPNext names a BOM `BOM-{item}-{index}` from the receiving site's own BOM count for that
	item. An item here carries Template, Quotation, Sales Order and Manufacturing Process
	BOMs while KGGK receives only the Template one, so the numbering almost never lines up.
	Addressing the record by our name after that 404s and pushes it again - one extra BOM per
	BOM per run.
	"""

	def setUp(self):
		self.cfg = frappe._dict(to_site="https://kggk.example.com", headers={})

	def test_the_created_name_is_read_back_from_the_target(self):
		created = k.Response(status_code=200, data={"data": {"name": "BOM-X-001"}})
		with patch.object(k, "api_put", return_value=k.Response(status_code=404)), patch.object(
			k, "api_post", return_value=created
		):
			response, action, assigned = k._send(self.cfg, "BOM", "BOM-X-002", {"item": "X"})
		self.assertEqual(action, "created")
		self.assertEqual(assigned, "BOM-X-001")

	def test_an_update_is_addressed_by_the_targets_name(self):
		with patch.object(k, "api_put", return_value=k.Response(status_code=200)) as put, patch.object(
			k, "api_post"
		) as post:
			response, action, assigned = k._send(
				self.cfg, "BOM", "BOM-X-002", {"item": "X"}, lookup="BOM-X-001"
			)
		self.assertEqual(action, "updated")
		self.assertEqual(assigned, "BOM-X-001")
		self.assertIn("BOM-X-001", put.call_args.args[1])
		post.assert_not_called()

	def test_an_unknown_record_maps_to_its_own_name(self):
		"""The right guess for a first push, and it must not invent one."""
		with patch.object(frappe, "get_all", return_value=[]):
			self.assertEqual(
				k.target_names("BOM", ["BOM-X-002"], "kggk.example.com"), {"BOM-X-002": "BOM-X-002"}
			)

	def test_a_recorded_rename_is_used(self):
		rows = [frappe._dict(record_name="BOM-X-002", target_name="BOM-X-001")]
		with patch.object(frappe, "get_all", return_value=rows):
			self.assertEqual(
				k.target_name_for("BOM", "BOM-X-002", "kggk.example.com"), "BOM-X-001"
			)

	def test_only_item_and_bom_are_mapped(self):
		"""Nothing else is pushed by this engine, so nothing else can be known to differ."""
		with patch.object(frappe, "get_all") as get_all:
			k.target_names("Item Group", ["Rings"], "kggk.example.com")
		get_all.assert_not_called()

	def test_a_link_carries_the_targets_name_not_ours(self):
		"""Sending our name would point master_bom at nothing on the other site."""
		doc = frappe._dict(doctype="Item", name="I-1")
		data = {"master_bom": "BOM-X-002"}
		run = _run(config=self.cfg)
		with patch.object(k, "link_fields", return_value={"master_bom": ("BOM", False)}), patch.object(
			k, "target_name_for", return_value="BOM-X-001"
		), patch.object(k, "_link_exists", return_value=True) as exists:
			k._strip_missing_links(self.cfg, doc, data, run, {})
		self.assertEqual(data["master_bom"], "BOM-X-001")
		self.assertEqual(exists.call_args.args[2], "BOM-X-001")

	def test_the_relink_pass_resolves_the_name_at_the_end_not_when_it_was_dropped(self):
		"""The BOM had no name on the target when the link was dropped - it had not been
		pushed yet. Freezing the translation in at that point would resolve to nothing."""
		run = _run(config=self.cfg)
		run.deferred = [("Item", "I-1", "master_bom", "BOM-X-002", "BOM")]
		with patch.object(
			k, "target_names", side_effect=lambda dt, names, t: {n: "BOM-X-001" for n in names}
		), patch.object(k, "target_name_for", side_effect=lambda dt, n, t: n), patch.object(
			k, "api_exists_many", return_value={"BOM-X-001": True}
		), patch.object(
			k, "api_put", return_value=k.Response(status_code=200)
		) as put:
			k._apply_deferred_links(self.cfg, run)
		self.assertEqual(put.call_args.kwargs["json"], {"master_bom": "BOM-X-001"})

	def test_the_prefill_asks_about_the_targets_names(self):
		"""Otherwise every renamed record reads as missing and is pushed again, forever."""
		asked = {}

		def exists_many(cfg, doctype, names, run=None):
			asked[doctype] = names
			return {n: True for n in names}

		with patch.object(k, "get_sync_config", return_value=(self.cfg, None)), patch.object(
			k, "_field_gaps", return_value=([], [], [])
		), patch.object(k, "_plan_records", return_value=(["MP-1"], [], ["BOM-X-002"])), patch.object(
			k, "target_names", side_effect=lambda dt, names, t: {n: "BOM-X-001" for n in names}
		), patch.object(k, "api_exists_many", side_effect=exists_many), patch.object(
			k, "_close_prefill"
		), patch.object(k.SyncRun, "_open_log", return_value="LOG-1"), patch.object(
			k.SyncRun, "flush"
		), patch.object(k.SyncRun, "report"), patch.object(k, "enqueue_sync"):
			out = k.run_prefill("LOG-1", apply=0)

		self.assertEqual(asked["BOM"], ["BOM-X-001"])
		self.assertEqual(out["boms_missing"], 0)


class TestSettingsValidation(unittest.TestCase):
	"""mandatory_depends_on only runs in the browser."""

	def _settings_doc(self, **kw):
		from gke_customization.gke_order_forms.doctype.data_migration_in_kggk import (
			data_migration_in_kggk as mod,
		)

		doc = mod.DataMigrationinKGGK(
			{"doctype": "Data Migration in KGGK", "name": "Data Migration in KGGK"}
		)
		doc.update({"enable_sync": 1, "to_site": "https://kggk.example.com",
		            "api_key": "k", "api_secret": "s", "from_site": ""})
		doc.update(kw)
		return doc

	def test_the_switch_cannot_be_turned_on_without_a_target(self):
		with patch.object(k, "current_site_hosts", return_value={"gk.example.com"}):
			with self.assertRaises(frappe.ValidationError):
				self._settings_doc(to_site="").validate_kggk_sync()

	def test_the_switch_cannot_be_turned_on_without_credentials(self):
		with patch.object(k, "current_site_hosts", return_value={"gk.example.com"}):
			with self.assertRaises(frappe.ValidationError):
				self._settings_doc(api_secret="").validate_kggk_sync()

	def test_pointing_it_at_this_site_is_refused_at_save_time(self):
		with patch.object(k, "current_site_hosts", return_value={"kggk.example.com"}):
			with self.assertRaises(frappe.ValidationError):
				self._settings_doc().validate_kggk_sync()

	def test_a_complete_configuration_saves(self):
		with patch.object(k, "current_site_hosts", return_value={"gk.example.com"}):
			self._settings_doc().validate_kggk_sync()

	def test_the_switch_being_off_validates_nothing(self):
		self._settings_doc(enable_sync=0, to_site="", api_key="", api_secret="").validate_kggk_sync()


class TestLegacyHooksStayUnwired(unittest.TestCase):
	def test_the_blocking_before_validate_push_is_not_registered(self):
		"""It aborted a local save when KGGK was down. A merge must not bring it back."""
		from gke_customization import hooks

		wired = frappe.as_json(hooks.doc_events)
		self.assertNotIn("create_item_kggk", wired)
		self.assertNotIn("create_bom_kggk", wired)
		self.assertIn("kggk_sync.item_on_update", wired)
		self.assertIn("kggk_sync.bom_on_update", wired)
