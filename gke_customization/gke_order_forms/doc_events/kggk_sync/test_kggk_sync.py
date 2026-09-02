"""Tests for the Manufacturing Plan -> KGGK testing push.

Deliberately unit tests against patched boundaries rather than integration tests: the thing
under test is a set of refusals and a report, and both must be provable without a second
site to push at.
"""

import unittest
from unittest.mock import MagicMock, patch

import frappe

from . import config as config_module
from . import payload as payload_module
from .client import Response
from .log import SyncRun

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
	"""Every refusal, and the one success."""

	def _run(self, settings, secret="secret", hosts=("gk.example.com",)):
		with patch.object(frappe.db, "get_value", return_value=settings), patch(
			f"{MOD}.config._testing_api_secret", return_value=secret
		), patch.object(config_module, "current_site_hosts", return_value=set(hosts)):
			return config_module.get_sync_config()

	def test_switch_off_refuses(self):
		cfg, reason = self._run(_settings(enable_testing_sync=0))
		self.assertIsNone(cfg)
		self.assertEqual(reason, config_module.SKIP_DISABLED)

	def test_switch_off_wins_even_when_fully_configured(self):
		"""The switch is the switch. A complete configuration does not override it."""
		cfg, reason = self._run(_settings(enable_testing_sync=0))
		self.assertIsNone(cfg)
		self.assertEqual(reason, config_module.SKIP_DISABLED)

	def test_no_target_refuses(self):
		cfg, reason = self._run(_settings(testing_site=None))
		self.assertIsNone(cfg)
		self.assertEqual(reason, config_module.SKIP_NO_TARGET)

	def test_no_key_refuses(self):
		cfg, reason = self._run(_settings(testing_api_key=None))
		self.assertIsNone(cfg)
		self.assertEqual(reason, config_module.SKIP_NO_CREDS)

	def test_unreadable_secret_refuses(self):
		"""A Password that comes back empty must refuse, not send an empty token."""
		cfg, reason = self._run(_settings(), secret=None)
		self.assertIsNone(cfg)
		self.assertEqual(reason, config_module.SKIP_NO_CREDS)

	def test_target_is_this_site_refuses(self):
		cfg, reason = self._run(_settings(), hosts=("kggk-test.example.com",))
		self.assertIsNone(cfg)
		self.assertIn("refusing to sync a site to itself", reason)

	def test_target_equals_from_site_refuses(self):
		cfg, reason = self._run(_settings(from_site="https://kggk-test.example.com"))
		self.assertIsNone(cfg)
		self.assertIn("refusing to sync a site to itself", reason)

	def test_target_is_the_live_site_refuses(self):
		"""Pasting the production URL into the testing field must not push to production."""
		cfg, reason = self._run(_settings(testing_site="https://kggk-live.example.com/"))
		self.assertIsNone(cfg)
		self.assertIn("production KGGK site", reason)

	def test_success_targets_the_testing_site(self):
		cfg, reason = self._run(_settings())
		self.assertIsNone(reason)
		# Named to_site because every request helper reads that key - but it is the
		# testing site, never the live one.
		self.assertEqual(cfg.to_site, "https://kggk-test.example.com")
		self.assertEqual(cfg.headers["Authorization"], "token key:secret")


class TestSecretIsNotReadFromSingles(unittest.TestCase):
	def test_secret_comes_from_get_decrypted_password(self):
		"""Reading a Password with get_value yields '*****' and a 401 that misleads."""
		with patch("frappe.utils.password.get_decrypted_password", return_value="real") as gdp:
			self.assertEqual(config_module._testing_api_secret(), "real")
		gdp.assert_called_once()

	def test_secret_failure_is_swallowed(self):
		with patch("frappe.utils.password.get_decrypted_password", side_effect=Exception("boom")):
			self.assertIsNone(config_module._testing_api_secret())


class TestRowSelection(unittest.TestCase):
	from gke_customization.gke_order_forms.doc_events import manufacturing_plan as mp

	def _plan(self, rows):
		return frappe._dict(name="MP-0001", manufacturing_plan_table=[frappe._dict(r) for r in rows])

	def test_only_subcontracting_rows(self):
		items, boms = self.mp.collect_records(
			self._plan(
				[
					{"item_code": "I-1", "manufacturing_bom": "B-1", "subcontracting": 1},
					{"item_code": "I-2", "manufacturing_bom": "B-2", "subcontracting": 0},
				]
			)
		)
		self.assertEqual(items, ["I-1"])
		self.assertEqual(boms, ["B-1"])

	def test_manufacturing_bom_is_used_not_row_bom(self):
		"""row.bom is the Sales Order BOM and must never be selected."""
		items, boms = self.mp.collect_records(
			self._plan(
				[{"item_code": "I-1", "bom": "SO-BOM", "manufacturing_bom": "MFG-BOM", "subcontracting": 1}]
			)
		)
		self.assertEqual(boms, ["MFG-BOM"])
		self.assertNotIn("SO-BOM", boms)

	def test_duplicates_collapse(self):
		items, boms = self.mp.collect_records(
			self._plan(
				[
					{"item_code": "I-1", "manufacturing_bom": "B-1", "subcontracting": 1},
					{"item_code": "I-1", "manufacturing_bom": "B-1", "subcontracting": 1},
				]
			)
		)
		self.assertEqual(items, ["I-1"])
		self.assertEqual(boms, ["B-1"])


class TestSubmitNeverRaises(unittest.TestCase):
	from gke_customization.gke_order_forms.doc_events import manufacturing_plan as mp

	def test_enqueue_failure_does_not_reach_submit(self):
		"""Redis down must not roll back the Manufacturing Plan."""
		doc = frappe._dict(
			name="MP-0001",
			manufacturing_plan_table=[
				frappe._dict(item_code="I-1", manufacturing_bom="B-1", subcontracting=1)
			],
		)
		with patch.object(
			self.mp, "get_sync_config", return_value=(frappe._dict(to_site="x"), None)
		), patch.object(self.mp, "enqueue_sync", side_effect=ConnectionError("redis is down")):
			self.mp.on_submit(doc)  # must not raise


class TestTargetSchemaFailuresAreReported(unittest.TestCase):
	"""Every route to `None` must say so - a silent one looks like a clean run."""

	def setUp(self):
		self.run = SyncRun(config=frappe._dict(to_site="https://t", from_site="https://f"))
		self.cfg = frappe._dict(to_site="https://t", headers={})
		frappe.cache().delete_value("kggk_target_fields::Item")

	def tearDown(self):
		frappe.cache().delete_value("kggk_target_fields::Item")

	def _kinds(self):
		return [p.split("|")[0].strip() for p in self.run.problems]

	def test_doctype_get_failure_is_reported(self):
		with patch(f"{MOD}.client.get", return_value=Response(status_code=500, text="nope")):
			self.assertIsNone(payload_module.get_target_fields(self.cfg, "Item", run=self.run))
		self.assertIn("SCHEMA-UNKNOWN", self._kinds())

	def test_doctype_with_no_fields_is_reported(self):
		ok_empty = Response(status_code=200, data={"data": {"fields": []}})
		with patch(f"{MOD}.client.get", return_value=ok_empty):
			self.assertIsNone(payload_module.get_target_fields(self.cfg, "Item", run=self.run))
		self.assertIn("SCHEMA-UNKNOWN", self._kinds())

	def test_custom_field_failure_is_a_failure_not_a_partial_answer(self):
		"""The dangerous branch: standard fields known, custom ones not.

		Returning that set would drop every custom field and report it missing - a
		confident wrong answer, cached.
		"""
		doctype_ok = Response(status_code=200, data={"data": {"fields": [{"fieldname": "item_code"}]}})
		custom_bad = Response(status_code=403, text="forbidden")
		with patch(f"{MOD}.client.get", side_effect=[doctype_ok, custom_bad]):
			self.assertIsNone(payload_module.get_target_fields(self.cfg, "Item", run=self.run))
		self.assertIn("SCHEMA-UNKNOWN", self._kinds())

	def test_success_returns_union_of_standard_and_custom(self):
		doctype_ok = Response(status_code=200, data={"data": {"fields": [{"fieldname": "item_code"}]}})
		custom_ok = Response(status_code=200, data={"data": [{"fieldname": "custom_thing"}]})
		with patch(f"{MOD}.client.get", side_effect=[doctype_ok, custom_ok]):
			fields = payload_module.get_target_fields(self.cfg, "Item", run=self.run)
		self.assertIn("item_code", fields)
		self.assertIn("custom_thing", fields)
		self.assertEqual(self.run.problems, [])

	def test_schema_problem_is_reported_once_per_doctype(self):
		with patch(f"{MOD}.client.get", return_value=Response(status_code=500)):
			payload_module.get_target_fields(self.cfg, "Item", run=self.run)
			payload_module.get_target_fields(self.cfg, "Item", run=self.run)
		self.assertEqual(len(self.run.problems), 1)


class TestReporting(unittest.TestCase):
	def _run_with(self, n_problems):
		run = SyncRun(
			trigger="Manufacturing Plan",
			reference="MP-0001",
			config=frappe._dict(to_site="https://t", from_site="https://f", headers={}),
		)
		for i in range(n_problems):
			run.mismatch("Item", f"I-{i}", "field 'x' does not exist on the target")
		return run

	def test_clean_run_writes_nothing(self):
		run = self._run_with(0)
		with patch(f"{MOD}.client.post") as post:
			self.assertFalse(run.report())
		post.assert_not_called()

	def test_many_problems_become_one_post(self):
		"""Per-record reporting would be hundreds of POSTs at the worst possible moment."""
		run = self._run_with(120)
		with patch(f"{MOD}.client.post", return_value=Response(status_code=200)) as post:
			self.assertTrue(run.report())
		self.assertEqual(post.call_count, 1)
		body = post.call_args.kwargs["json"]["error"]
		self.assertIn("I-0", body)
		self.assertIn("I-119", body)

	def test_report_is_capped(self):
		run = self._run_with(400)
		with patch(f"{MOD}.client.post", return_value=Response(status_code=200)) as post:
			run.report()
		body = post.call_args.kwargs["json"]["error"]
		self.assertIn("and 200 more", body)
		self.assertLessEqual(len(body), 60_000)

	def test_failed_report_falls_back_locally_without_raising(self):
		run = self._run_with(3)
		with patch(f"{MOD}.client.post", return_value=Response(status_code=403, text="denied")), patch(
			"frappe.log_error"
		) as log_error:
			self.assertFalse(run.report())  # must not raise
		self.assertTrue(log_error.called)
		self.assertIn("FALLBACK", log_error.call_args.args[0])

	def test_report_never_raises_even_if_client_explodes(self):
		run = self._run_with(1)
		with patch(f"{MOD}.client.post", side_effect=RuntimeError("boom")), patch("frappe.log_error"):
			self.assertFalse(run.report())


class TestCounters(unittest.TestCase):
	def test_counters_carry_forward(self):
		"""Chunk state rides in the job kwargs; there is no settings field to read back."""
		first = SyncRun()
		first.item_ok("I-1")
		first.bom_failed("B-1", "nope")
		second = SyncRun(counters=first.counters())
		second.item_ok("I-2")
		self.assertEqual(second.counters()["items_synced"], 2)
		self.assertEqual(second.counters()["boms_failed"], 1)
