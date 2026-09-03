"""Tests for the Manufacturing Plan -> KGGK testing push.

Unit tests against patched boundaries rather than integration tests: the things worth
proving are a set of refusals, a report, and the fact that nothing here can break a submit -
all of which must be provable without a second site to push at.
"""

import unittest
from unittest.mock import patch

import frappe

from . import kggk_sync as k

MOD = "gke_customization.gke_order_forms.doc_events.kggk_sync"


def _settings(**overrides):
	base = {
		"from_site": "https://gk.example.com",
		"to_site": "https://kggk-live.example.com",
		"enable_testing_sync": 1,
		"testing_site": "https://kggk-test.example.com",
		"testing_api_key": "key",
	}
	base.update(overrides)
	return frappe._dict(base)


class TestConfigGuards(unittest.TestCase):
	def _run(self, settings, secret="secret", hosts=("gk.example.com",)):
		with patch.object(frappe.db, "get_value", return_value=settings), patch(
			f"{MOD}._testing_api_secret", return_value=secret
		), patch.object(k, "current_site_hosts", return_value=set(hosts)):
			return k.get_sync_config()

	def test_switch_off_refuses_even_when_fully_configured(self):
		"""The switch is the switch. A complete configuration does not override it."""
		cfg, reason = self._run(_settings(enable_testing_sync=0))
		self.assertIsNone(cfg)
		self.assertEqual(reason, k.SKIP_DISABLED)

	def test_no_target_refuses(self):
		cfg, reason = self._run(_settings(testing_site=None))
		self.assertEqual(reason, k.SKIP_NO_TARGET)

	def test_no_key_refuses(self):
		cfg, reason = self._run(_settings(testing_api_key=None))
		self.assertEqual(reason, k.SKIP_NO_CREDS)

	def test_unreadable_secret_refuses(self):
		"""A Password that reads back empty must refuse, not send an empty token."""
		cfg, reason = self._run(_settings(), secret=None)
		self.assertEqual(reason, k.SKIP_NO_CREDS)

	def test_target_is_this_site_refuses(self):
		cfg, reason = self._run(_settings(), hosts=("kggk-test.example.com",))
		self.assertIn("refusing to sync a site to itself", reason)

	def test_target_equals_from_site_refuses(self):
		cfg, reason = self._run(_settings(from_site="https://kggk-test.example.com"))
		self.assertIn("refusing to sync a site to itself", reason)

	def test_target_is_the_live_site_refuses(self):
		"""Pasting the production URL into the testing field must not push to production."""
		cfg, reason = self._run(_settings(testing_site="https://kggk-live.example.com/"))
		self.assertIn("production KGGK site", reason)

	def test_success_targets_the_testing_site(self):
		cfg, reason = self._run(_settings())
		self.assertIsNone(reason)
		self.assertEqual(cfg.to_site, "https://kggk-test.example.com")
		self.assertEqual(cfg.headers["Authorization"], "token key:secret")


class TestSecretIsNotReadFromSingles(unittest.TestCase):
	def test_secret_comes_from_get_decrypted_password(self):
		"""get_value on a Password returns '*****' and the 401 misleads."""
		with patch("frappe.utils.password.get_decrypted_password", return_value="real") as gdp:
			self.assertEqual(k._testing_api_secret(), "real")
		gdp.assert_called_once()

	def test_secret_failure_is_swallowed(self):
		with patch("frappe.utils.password.get_decrypted_password", side_effect=Exception("boom")):
			self.assertIsNone(k._testing_api_secret())


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


class TestSubmitNeverRaises(unittest.TestCase):
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


class TestTargetSchemaFailuresAreReported(unittest.TestCase):
	"""Every route to `None` must say so - a silent one looks like a clean run."""

	def setUp(self):
		self.run = k.SyncRun(config=frappe._dict(to_site="https://t", from_site="https://f"))
		self.cfg = frappe._dict(to_site="https://t", headers={})
		frappe.cache().delete_value("kggk_target_fields::Item")

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


class TestReporting(unittest.TestCase):
	def _run_with(self, n):
		run = k.SyncRun(
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
		"""Chunk state rides in the job kwargs; there is no settings field to read back."""
		first = k.SyncRun()
		first.item_ok("I-1")
		first.bom_failed("B-1", "nope")
		second = k.SyncRun(counters=first.counters())
		second.item_ok("I-2")
		self.assertEqual(second.counters()["items_synced"], 2)
		self.assertEqual(second.counters()["boms_failed"], 1)


class TestPrefill(unittest.TestCase):
	"""The button. First press must change nothing on the target."""

	def setUp(self):
		self.cfg = frappe._dict(to_site="https://t", from_site="https://f", headers={})

	def test_dry_run_creates_nothing(self):
		with patch.object(k, "get_sync_config", return_value=(self.cfg, None)), patch.object(
			k, "_field_gaps", return_value=([{"dt": "Item", "fieldname": "custom_x"}], [], [])
		), patch.object(k, "_plan_records", return_value=(["MP-1"], ["I-1"], ["B-1"])), patch.object(
			k, "api_exists", return_value=False
		), patch.object(
			k, "_create_custom_field"
		) as create, patch.object(
			k, "enqueue_sync"
		) as enqueue, patch.object(
			k.SyncRun, "report"
		), patch(
			"frappe.only_for"
		):
			out = k.prefill_testing_site(apply=0)

		create.assert_not_called()
		enqueue.assert_not_called()
		self.assertFalse(out["applied"])
		self.assertEqual(out["fields_to_create"], ["Item.custom_x"])
		self.assertEqual((out["items_missing"], out["boms_missing"]), (1, 1))

	def test_apply_creates_fields_and_queues_records(self):
		with patch.object(k, "get_sync_config", return_value=(self.cfg, None)), patch.object(
			k, "_field_gaps", return_value=([{"dt": "Item", "fieldname": "custom_x"}], [], [])
		), patch.object(k, "_plan_records", return_value=(["MP-1"], ["I-1"], [])), patch.object(
			k, "api_exists", return_value=False
		), patch.object(
			k, "_create_custom_field", return_value=(True, "created")
		) as create, patch.object(
			k, "enqueue_sync", return_value=True
		) as enqueue, patch.object(
			k.SyncRun, "report"
		), patch(
			"frappe.only_for"
		):
			out = k.prefill_testing_site(apply=1)

		create.assert_called_once()
		enqueue.assert_called_once()
		self.assertEqual(out["fields_created"], ["Item.custom_x"])

	def test_standard_field_gaps_are_never_created(self):
		"""A missing standard field is a version mismatch, not something to paper over."""
		with patch.object(k, "get_sync_config", return_value=(self.cfg, None)), patch.object(
			k, "_field_gaps", return_value=([], ["Item.some_v16_field (Data)"], [])
		), patch.object(k, "_plan_records", return_value=([], [], [])), patch.object(
			k, "_create_custom_field"
		) as create, patch.object(
			k, "enqueue_sync"
		), patch.object(
			k.SyncRun, "report"
		), patch(
			"frappe.only_for"
		):
			out = k.prefill_testing_site(apply=1)

		create.assert_not_called()
		self.assertEqual(out["standard_field_gaps"], ["Item.some_v16_field (Data)"])

	def test_refuses_when_not_configured(self):
		with patch.object(k, "get_sync_config", return_value=(None, "switch is off")), patch(
			"frappe.only_for"
		):
			with self.assertRaises(frappe.ValidationError):
				k.prefill_testing_site(apply=0)

	def test_unknown_existence_is_not_assumed_present(self):
		"""api_exists returns None when the check failed - that is not 'it is there'."""
		with patch.object(k, "get_sync_config", return_value=(self.cfg, None)), patch.object(
			k, "_field_gaps", return_value=([], [], [])
		), patch.object(k, "_plan_records", return_value=(["MP-1"], ["I-1"], [])), patch.object(
			k, "api_exists", return_value=None
		), patch.object(
			k.SyncRun, "report"
		), patch(
			"frappe.only_for"
		):
			out = k.prefill_testing_site(apply=0)

		self.assertEqual(out["items_missing"], 0)
		self.assertEqual(out["unchecked"], 1)
