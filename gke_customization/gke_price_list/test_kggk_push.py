# Copyright (c) 2026, Gurukrupa Export and Contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import UnitTestCase

from gke_customization.gke_price_list import kggk_push

MOD = "gke_customization.gke_price_list.kggk_push"


class TestRunPush(UnitTestCase):
	"""run_push runs the queued steps in order and stops at the first failure."""

	def setUp(self):
		self.calls = []
		self.reference = MagicMock()
		self._patch("frappe.get_doc", side_effect=self.get_doc)
		self.realtime = self._patch("frappe.publish_realtime")
		self.log_error = self._patch("frappe.log_error")

	def _patch(self, target, **kwargs):
		patcher = patch(target, **kwargs)
		self.addCleanup(patcher.stop)
		return patcher.start()

	def get_doc(self, doctype, name):
		if doctype == "Product Return Order":
			return self.reference
		return frappe._dict(doctype=doctype, name=name)

	def push(self, doc, **kwargs):
		self.calls.append((doc.name, kwargs))
		if doc.name == "FAIL":
			frappe.throw("remote said no")

	def run_steps(self, *names):
		real_get_attr = frappe.get_attr
		get_attr = lambda path: self.push if path == "m" else real_get_attr(path)  # noqa: E731
		with patch("frappe.get_attr", side_effect=get_attr):
			kggk_push.run_push(
				"Product Return Order",
				"PRO-1",
				[("m", "Item", name, {"k": 1}) for name in names],
				user="u@example.invalid",
			)

	def test_steps_run_in_order(self):
		self.run_steps("A", "B")
		self.assertEqual(self.calls, [("A", {"k": 1}), ("B", {"k": 1})])
		self.reference.add_comment.assert_not_called()
		self.realtime.assert_not_called()

	def test_failure_stops_the_rest_and_is_reported(self):
		self.run_steps("A", "FAIL", "B")
		self.assertEqual([name for name, _ in self.calls], ["A", "FAIL"])
		self.log_error.assert_called_once()
		self.reference.add_comment.assert_called_once()
		self.assertIn("remote said no", self.reference.add_comment.call_args.args[1])
		self.assertEqual(self.realtime.call_args.kwargs["user"], "u@example.invalid")


class TestPushAfterCommit(UnitTestCase):
	def test_queues_one_job_after_commit(self):
		with patch("frappe.enqueue") as enqueue:
			kggk_push.push_after_commit("Product Return Order", "PRO-1", [("m", "BOM", "B", {})])
		enqueue.assert_called_once()
		self.assertTrue(enqueue.call_args.kwargs["enqueue_after_commit"])
		self.assertEqual(enqueue.call_args.args[0], f"{MOD}.run_push")

	def test_nothing_to_push_queues_nothing(self):
		with patch("frappe.enqueue") as enqueue:
			kggk_push.push_after_commit("Product Return Order", "PRO-1", [])
		enqueue.assert_not_called()
