# Copyright (c) 2026, Gurukrupa Export and Contributors
# See license.txt

"""Pins the replacement for ERPNext's daily overdue-Task job.

* THAT it selects exactly the Tasks ERPNext's rule would change, and no Task already Overdue
  (checked against the site's own Tasks, read only).
* THAT a Task is set the ERPNext way (``db_set`` without touching ``modified``) and re-checked
  on load; a Pending Review Task waits for its review date, one without a date does not.
* THAT each project is refreshed once per batch, and every batch is committed.
* THAT the patch stops only ERPNext's job, and hooks / patches.txt wire both in.

Run with (no bench run-tests needed):
  python -c "import frappe, unittest; frappe.init(site=...); frappe.connect(); \
    unittest.main(module='gke_customization.overrides.test_task_overdue', exit=False)"
"""

import os
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import frappe
from frappe.tests import UnitTestCase
from frappe.utils import add_days, getdate, today

from gke_customization import hooks
from gke_customization.overrides import task_overdue
from gke_customization.patches import stop_erpnext_set_tasks_as_overdue as stop_patch

MOD = "gke_customization.overrides.task_overdue"


def _erpnext_would_change(task, as_of):
    """ERPNext's set_tasks_as_overdue + Task.update_status, as a pure function of one row."""
    if task.status in ("Cancelled", "Completed", "Template"):
        return False
    if task.status == "Pending Review" and getdate(task.review_date) > as_of:
        return False
    is_overdue = bool(task.exp_end_date) and getdate(task.exp_end_date) < as_of
    return is_overdue and task.status != "Overdue"


class _Task(SimpleNamespace):
    @property
    def is_overdue(self):
        return bool(self.exp_end_date) and getdate(self.exp_end_date) < getdate()


def _task(status="Open", days_late=1, project="P-1", review_in_days=None):
    task = _Task(
        status=status,
        exp_end_date=add_days(today(), -days_late) if days_late is not None else None,
        project=project,
        review_date=add_days(today(), review_in_days)
        if review_in_days is not None
        else None,
    )
    task.db_set = MagicMock()
    return task


class TestSelection(UnitTestCase):
    def test_matches_erpnext_rule_on_this_sites_tasks(self):
        as_of = getdate(today())
        rows = frappe.get_all(
            "Task",
            fields=["name", "status", "exp_end_date", "review_date"],
            limit_page_length=0,
        )
        expected = sorted(r.name for r in rows if _erpnext_would_change(r, as_of))

        self.assertEqual(task_overdue.get_tasks_to_mark_overdue(), expected)

    def test_query_keeps_erpnexts_pending_review_rule(self):
        # A site may have no Pending Review Task without a review date, so pin the SQL too:
        # ERPNext processes those (getdate(None) is today), so the query must not drop them.
        sql = str(task_overdue._overdue_query(getdate("2026-11-16")))

        self.assertIn("`review_date` IS NULL", sql)
        self.assertIn("`review_date`<='2026-11-16'", sql)
        self.assertIn("`exp_end_date`<'2026-11-16'", sql)
        self.assertIn("'Overdue'", sql)

    def test_never_selects_a_task_already_overdue(self):
        names = set(task_overdue.get_tasks_to_mark_overdue())
        overdue = set(
            frappe.get_all("Task", filters={"status": "Overdue"}, pluck="name")
        )

        self.assertFalse(names & overdue)


class TestMarkOverdue(UnitTestCase):
    def _mark(self, task):
        with patch(f"{MOD}.frappe.get_doc", return_value=task):
            return task_overdue._mark_overdue("T-1")

    def test_late_open_task_is_set_overdue_without_touching_modified(self):
        task = _task()

        self.assertEqual(self._mark(task), "P-1")
        task.db_set.assert_called_once_with("status", "Overdue", update_modified=False)

    def test_task_without_project_returns_none_but_is_still_set(self):
        task = _task(project=None)

        self.assertIsNone(self._mark(task))
        task.db_set.assert_called_once()

    def test_already_overdue_or_finished_is_left_alone(self):
        for status in ("Overdue", "Completed", "Cancelled", "Template"):
            task = _task(status=status)
            self.assertIsNone(self._mark(task), status)
            task.db_set.assert_not_called()

    def test_not_yet_due_is_left_alone(self):
        for task in (_task(days_late=0), _task(days_late=-3), _task(days_late=None)):
            self.assertIsNone(self._mark(task))
            task.db_set.assert_not_called()

    def test_pending_review_waits_for_its_review_date(self):
        waiting = _task(status="Pending Review", review_in_days=2)
        due = _task(status="Pending Review", review_in_days=0)
        undated = _task(status="Pending Review")

        self.assertIsNone(self._mark(waiting))
        waiting.db_set.assert_not_called()
        self.assertEqual(self._mark(due), "P-1")
        self.assertEqual(self._mark(undated), "P-1")


class TestBatches(UnitTestCase):
    def setUp(self):
        self.commit = self._patch(f"{MOD}.frappe.db.commit")
        self.refresh = self._patch(f"{MOD}._refresh_projects")

    def _patch(self, target, **kwargs):
        patcher = patch(target, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def _run(self, names, project_of):
        self._patch(f"{MOD}.get_tasks_to_mark_overdue", return_value=names)
        self._patch(f"{MOD}._mark_overdue", side_effect=project_of)
        task_overdue.set_tasks_as_overdue()

    def test_commits_after_every_batch(self):
        size = task_overdue.BATCH_SIZE
        self._run([f"T-{i}" for i in range(2 * size + 1)], lambda name: None)

        self.assertEqual(self.commit.call_count, 3)

    def test_each_project_refreshed_once_per_batch(self):
        projects = {"T-1": "P-A", "T-2": "P-A", "T-3": "P-B", "T-4": None}
        self._run(list(projects), projects.get)

        self.refresh.assert_called_once_with({"P-A", "P-B"})

    def test_nothing_to_do_commits_nothing(self):
        self._run([], lambda name: None)

        self.commit.assert_not_called()
        self.refresh.assert_not_called()


class TestRefreshProjects(UnitTestCase):
    def test_refresh_loads_each_project_fresh_and_recomputes_it(self):
        project = MagicMock()
        with patch(f"{MOD}.frappe.get_doc", return_value=project) as get_doc:
            task_overdue._refresh_projects({"P-B", "P-A"})

        self.assertEqual(
            get_doc.call_args_list, [call("Project", "P-A"), call("Project", "P-B")]
        )
        self.assertEqual(project.update_project.call_count, 2)


class TestWiring(UnitTestCase):
    def test_patch_stops_only_erpnexts_job(self):
        with patch.object(
            stop_patch.frappe, "get_all", return_value=["job-1"]
        ) as get_all, patch.object(stop_patch.frappe.db, "set_value") as set_value:
            stop_patch.execute()

        self.assertEqual(
            get_all.call_args.kwargs["filters"],
            {
                "method": "erpnext.projects.doctype.task.task.set_tasks_as_overdue",
                "stopped": 0,
            },
        )
        set_value.assert_called_once_with(
            "Scheduled Job Type", "job-1", "stopped", 1, update_modified=False
        )

    def test_hooks_run_it_on_the_long_queue_daily(self):
        self.assertIn(
            f"{MOD}.set_tasks_as_overdue", hooks.scheduler_events["daily_maintenance"]
        )

    def test_patch_registered_once_after_post_model_sync(self):
        path = os.path.join(os.path.dirname(hooks.__file__), "patches.txt")
        with open(path) as f:
            lines = [line.split("#")[0].strip() for line in f]
        name = "gke_customization.patches.stop_erpnext_set_tasks_as_overdue"

        self.assertEqual(lines.count(name), 1)
        self.assertGreater(lines.index(name), lines.index("[post_model_sync]"))
