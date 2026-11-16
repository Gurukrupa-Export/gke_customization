# Copyright (c) 2026, Gurukrupa Export
# License: GNU General Public License v3. See license.txt

"""Mark overdue Tasks without re-processing the ones already marked.

Replaces ERPNext's ``erpnext.projects.doctype.task.task.set_tasks_as_overdue`` (stopped by the
``stop_erpnext_set_tasks_as_overdue`` patch). The ERPNext job loads EVERY Task that is not
Cancelled / Completed / Template -- including the ones already Overdue -- and for each runs
``get_doc`` + ``db_set("status", "Overdue")`` + a full ``Project.update_project()``, all in one
transaction. On production it ran into the long queue's 1500 s timeout every day: the timeout
rolled the whole day's work back, the Scheduled Job Log stayed at "Start", the final commit raised
MySQLdb 2014 "Commands out of sync", and the only long-queue worker was busy for 25 minutes.

This job keeps ERPNext's rule and side effects and changes only how much it touches:

* It selects only Tasks that need to change: not Cancelled / Completed / Template / already
  Overdue, with ``exp_end_date`` before today. A Pending Review Task is skipped while its
  ``review_date`` is in the future, exactly as ERPNext does (``getdate(None)`` is today, so a
  Pending Review Task without a review date is still processed).
* It sets the status with the same ``db_set("status", "Overdue", update_modified=False)``.
* It recomputes each affected Project once per batch with the same ``Project.update_project()``,
  instead of once per Task, and loads the Project fresh rather than from the document cache.
* It commits every ``BATCH_SIZE`` Tasks, so a timeout or restart keeps the work already done and
  never holds row locks on thousands of Tasks at once.
"""

import frappe
from frappe.query_builder import Criterion
from frappe.utils import getdate, today

BATCH_SIZE = 200

DONE_STATUSES = ("Cancelled", "Completed", "Template", "Overdue")


def get_tasks_to_mark_overdue(as_of=None):
    """Names of the Tasks that should become Overdue as of ``as_of`` (default today)."""
    return _overdue_query(getdate(as_of or today())).run(pluck=True)


def _overdue_query(as_of):
    task = frappe.qb.DocType("Task")
    return (
        frappe.qb.from_(task)
        .select(task.name)
        .where(task.status.notin(DONE_STATUSES))
        .where(task.exp_end_date.isnotnull())
        .where(task.exp_end_date < as_of)
        .where(
            Criterion.any(
                [
                    task.status != "Pending Review",
                    task.review_date.isnull(),
                    task.review_date <= as_of,
                ]
            )
        )
        .orderby(task.name)
    )


def _mark_overdue(name):
    """Set one Task to Overdue the way ERPNext's ``Task.update_status`` does, minus the
    per-Task project refresh. Returns the Task's project when it changed, else None."""
    doc = frappe.get_doc("Task", name)
    # Re-check on the loaded row: the list was read before this batch started.
    if doc.status in DONE_STATUSES or not doc.is_overdue:
        return None
    if (
        doc.status == "Pending Review"
        and doc.review_date
        and getdate(doc.review_date) > getdate(today())
    ):
        return None
    doc.db_set("status", "Overdue", update_modified=False)
    return doc.project or None


def _refresh_projects(projects):
    for project in sorted(projects):
        frappe.get_doc("Project", project).update_project()


def set_tasks_as_overdue():
    names = get_tasks_to_mark_overdue()
    for start in range(0, len(names), BATCH_SIZE):
        projects = set()
        for name in names[start : start + BATCH_SIZE]:
            project = _mark_overdue(name)
            if project:
                projects.add(project)
        _refresh_projects(projects)
        frappe.db.commit()  # nosemgrep: keep each batch; see module docstring
