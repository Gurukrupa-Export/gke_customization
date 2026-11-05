# Copyright (c) 2026, Gurukrupa Export
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Create the fields used by incremental absent marking in auto attendance."""
    frappe.delete_doc(
        "Custom Field",
        "HR Settings-custom_incremental_absent_marking_section",
        ignore_missing=True,
        force=True,
    )

    create_custom_fields(
        {
            "Shift Type": [
                dict(
                    fieldname="custom_absent_reconciled_till",
                    label="Absent Reconciled Till",
                    fieldtype="Date",
                    insert_after="last_sync_of_checkin",
                    read_only=1,
                    no_copy=1,
                    description="Absent marking has been completed up to this date. Set by the auto attendance jobs.",
                ),
            ],
            "HR Settings": [
                dict(
                    fieldname="custom_absent_marking_column_break",
                    fieldtype="Column Break",
                    insert_after="default_attendance_review_user",
                ),
                dict(
                    fieldname="custom_enable_incremental_absent_marking",
                    label="Enable Incremental Absent Marking",
                    fieldtype="Check",
                    default="0",
                    insert_after="custom_absent_marking_column_break",
                    description="Hourly auto attendance re-checks only the recent days for absent marking. A nightly run checks the full range.",
                ),
                dict(
                    fieldname="custom_absent_reconciliation_overlap_days",
                    label="Absent Reconciliation Overlap (Days)",
                    fieldtype="Int",
                    default="7",
                    insert_after="custom_enable_incremental_absent_marking",
                    depends_on="custom_enable_incremental_absent_marking",
                ),
            ],
        }
    )
