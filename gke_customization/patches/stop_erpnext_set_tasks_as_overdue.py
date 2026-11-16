# Copyright (c) 2026, Gurukrupa Export
# License: GNU General Public License v3. See license.txt

import frappe

ERPNEXT_METHOD = "erpnext.projects.doctype.task.task.set_tasks_as_overdue"


def execute():
    """Stop ERPNext's daily overdue-Task job; ``overrides.task_overdue`` replaces it.

    ``stopped`` survives later migrates: the scheduler sync only updates a job's frequency and
    cron format. To go back, untick Stopped on the Scheduled Job Type and remove the
    ``daily_maintenance`` entry for ``gke_customization.overrides.task_overdue`` from hooks.py.
    """
    for name in frappe.get_all(
        "Scheduled Job Type",
        filters={"method": ERPNEXT_METHOD, "stopped": 0},
        pluck="name",
    ):
        frappe.db.set_value(
            "Scheduled Job Type", name, "stopped", 1, update_modified=False
        )
