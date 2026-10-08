"""Tests for the biometric punch sync (gke_hrms.sync_checkin).

The biometric API is faked, so the tests do not need the device server.
Master data and server script setup live in GKHRMSTestCase (base.py).

Expected behaviour under test: within one sync run and across successive
hourly runs, a punch that falls within Biometric Settings.time_threshold
seconds of the employee's last seen punch must be ignored, and only punches
beyond the threshold must create Employee Checkins.

bench --site <site-name> run-tests --app gke_customization --module gke_customization.gke_hrms.tests.test_sync_checkin

"""

import unittest
from unittest import mock

import frappe

from gke_customization.gke_hrms import sync_checkin
from gke_customization.gke_hrms.tests.base import GKHRMSTestCase
from gke_customization.gke_hrms.tests.utils import (
	DEVICE_ID,
	apply_sync_settings,
	make_api_log,
)


class TestBiometricSyncTimeThreshold(GKHRMSTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("DocType", "Biometric Settings"):
			raise unittest.SkipTest("gurukrupa_biometric app is not installed on this site")

	def setUp(self):
		super().setUp()
		# attendance_device_id is unique; sync commits internally, so the
		# employee of a previous test can survive its rollback
		self.device_id = f"{DEVICE_ID}-{frappe.generate_hash(length=6)}"
		self.ensure_server_scripts()
		self.employee = self.create_employee("Test Threshold Sync", attendance_device_id=self.device_id)
		apply_sync_settings()

	def run_sync(self, punch_times):
		"""Run one sync cycle against a faked API response and return the result
		together with the created checkin times as HH:MM strings."""
		response = mock.Mock(status_code=200)
		response.json.return_value = {
			"event-ta": [make_api_log(t, i, self.device_id) for i, t in enumerate(punch_times, 1)]
		}
		with mock.patch.object(sync_checkin.requests, "get", return_value=response):
			result = sync_checkin.sync_biometric_checkins()
		self.assertEqual(
			result.get("errors"),
			0,
			msg=f"sync reported unexpected errors: {result}",
		)
		return result, self.get_checkin_times()

	def get_checkin_times(self):
		times = frappe.get_all(
			"Employee Checkin",
			filters={"employee": self.employee.name},
			order_by="time asc",
			pluck="time",
		)
		return [t.strftime("%H:%M") for t in times]

	def test_first_punch_of_employee_is_created(self):
		result, times = self.run_sync(["11:42"])

		self.assertEqual(result["created"], 1)
		self.assertEqual(times, ["11:42"])

	def test_punch_within_threshold_of_previous_punch_is_ignored(self):
		"""Two punches 120s apart with a 120s threshold: only the first is kept."""
		result, times = self.run_sync(["11:42", "11:44"])

		self.assertEqual(result["created"], 1)
		self.assertEqual(result["skipped"], 1)
		self.assertEqual(times, ["11:42"])

	def test_punch_beyond_threshold_is_created(self):
		"""A punch beyond the threshold of the last punch must not be dropped."""
		result, times = self.run_sync(["11:42", "11:44", "14:00"])

		self.assertEqual(times, ["11:42", "14:00"])

	def test_all_burst_punches_after_the_first_are_ignored(self):
		"""A rapid punch burst must keep measuring against the last seen punch.

		11:44 is ignored (120s after 11:42), so 11:46 must be measured against
		11:44 (120s) and ignored too, instead of against 11:42 (240s).
		"""
		result, times = self.run_sync(["11:42", "11:44", "11:46"])

		self.assertEqual(times, ["11:42"])

	def test_duplicate_punch_in_same_minute_is_ignored(self):
		result, times = self.run_sync(["11:42", "11:42"])

		self.assertEqual(times, ["11:42"])

	def test_punches_delivered_in_a_later_run_are_still_filtered(self):
		"""Punches delivered after an earlier sync run must stay filtered.

		Mirrors the reported production issue: the first run creates 09:45 and
		11:42 and ignores 11:44; a later run delivers the remaining logs and
		must only add 18:35, not resurrect 11:46 from the ignored burst.
		"""
		self.run_sync(["09:45", "11:42", "11:44"])

		result, times = self.run_sync(["09:45", "11:42", "11:44", "11:46", "18:35"])

		self.assertEqual(times, ["09:45", "11:42", "18:35"])