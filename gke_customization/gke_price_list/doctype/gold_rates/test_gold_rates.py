# Copyright (c) 2026, Gurukrupa Export and Contributors
# See license.txt

"""The daily Gold Rates job: registered for all three runs, and honest about how each ended.

Every bullion feed is patched out, the job runs against a date no real record has, and
``frappe.db.commit`` is a no-op, so each test rolls back everything it wrote.
"""

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import frappe
from croniter import croniter

from gke_customization import hooks
from gke_customization.gke_price_list.doctype.gold_rates import gold_rates
from gke_customization.gke_price_list.doctype.gold_rates.gold_rates import GoldRates

METHOD = "gke_customization.gke_price_list.doctype.gold_rates.gold_rates.run_gold_rate_scheduler"
#: No real Gold Rates record is dated this far out, so the job always creates its own.
RUN_DATE = "2099-01-01"
FEEDS = (
    "set_gold_value",
    "get_gold_value_1",
    "set_gold_rate_2",
    "get_gold_rate_3",
    "get_gold_rate_4",
    "set_gold_rate_5",
)


class TestSchedulerRegistration(unittest.TestCase):
    def _entries(self):
        return [
            cron
            for cron, methods in hooks.scheduler_events["cron"].items()
            if METHOD in methods
        ]

    def test_the_job_is_registered_under_exactly_one_cron_entry(self):
        """Frappe keys a Scheduled Job Type by method. Three entries collapsed into the 23:00 one."""
        self.assertEqual(len(self._entries()), 1, self._entries())

    def test_that_entry_runs_at_09_15_and_23(self):
        (cron,) = self._entries()
        runs = croniter(cron, datetime(2026, 9, 24, 0, 0))
        self.assertEqual([runs.get_next(datetime).hour for _ in range(3)], [9, 15, 23])


class TestSchedulerRun(unittest.TestCase):
    def setUp(self):
        self.addCleanup(frappe.db.rollback)
        self.log_error = MagicMock()
        patches = [
            patch("frappe.utils.today", return_value=RUN_DATE),
            patch.object(frappe.db, "commit"),
            patch.object(frappe, "log_error", self.log_error),
        ]
        patches += [patch.object(GoldRates, feed) for feed in FEEDS]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def _records(self):
        return frappe.get_all("Gold Rates", filters={"date": RUN_DATE}, pluck="name")

    def test_a_successful_run_is_not_logged_as_a_failure(self):
        """``action`` was commented out, so the success log raised NameError after the commit."""
        gold_rates.run_gold_rate_scheduler()
        self.log_error.assert_not_called()
        self.assertEqual(len(self._records()), 1)

    def test_a_second_run_updates_the_same_days_record(self):
        gold_rates.run_gold_rate_scheduler()
        gold_rates.run_gold_rate_scheduler()
        self.assertEqual(len(self._records()), 1)
        self.log_error.assert_not_called()

    def test_a_failing_feed_logs_the_failure_and_writes_nothing(self):
        with patch.object(
            GoldRates, "get_gold_value_1", side_effect=ConnectionError("feed down")
        ):
            gold_rates.run_gold_rate_scheduler()
        self.assertEqual(self._records(), [])
        self.log_error.assert_called_once()
        self.assertEqual(self.log_error.call_args.args[1], "Gold Rate Scheduler Error")
