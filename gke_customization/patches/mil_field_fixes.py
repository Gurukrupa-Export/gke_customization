# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

"""One-time data migration for the Monthly In-Out Log doctype fixes.

1. rename the shit_type column to shift_type (keep data, then sync the JSON)
2. convert the duration columns (net_wrk_hrs / spent_hrs / ot_hrs) from
   Data (varchar) to Time so reports can aggregate them
3. add a unique index on (employee, attendance_date) when no duplicates
   exist; otherwise fall back to a plain index and log the duplicates

DDL follows the frappe/erpnext patch convention: schema statements run via
frappe.db.sql_ddl / frappe.db.add_unique, which commit first because DDL
auto-commits in MariaDB (frappe.db.sql raises ImplicitCommitError for DDL
once the patch has pending writes). Every step is guarded so the patch is
idempotent and safe on fresh installs and on re-runs after a failure.
"""

import frappe

MIL = "Monthly In-Out Log"
DURATION_FIELDS = ("net_wrk_hrs", "spent_hrs", "ot_hrs")


def _column_exists(table, column):
    return frappe.db.sql(
        """
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """,
        (table, column),
    )


def execute():
    table = f"tab{MIL}"

    # -- data phase (transactional) -----------------------------------------
    # blank out values that are not valid HH:MM:SS before the column type
    # change; MariaDB would otherwise coerce them to garbage times
    for field in DURATION_FIELDS:
        if _column_exists(table, field):
            frappe.db.sql(
                f"""
                UPDATE `{table}`
                SET `{field}` = NULL
                WHERE `{field}` IS NOT NULL
                  AND `{field}` NOT REGEXP '^[0-9]+:[0-9]{{2}}:[0-9]{{2}}$'
                """
            )

    # -- schema phase (each statement auto-commits) --------------------------
    if _column_exists(table, "shit_type") and not _column_exists(table, "shift_type"):
        frappe.db.sql_ddl(
            f"ALTER TABLE `{table}` CHANGE COLUMN `shit_type` `shift_type` VARCHAR(140)"
        )

    for field in DURATION_FIELDS:
        if _column_exists(table, field):
            frappe.db.sql_ddl(
                f"ALTER TABLE `{table}` MODIFY COLUMN `{field}` TIME NULL"
            )

    # -- index phase ---------------------------------------------------------
    # one card per employee + date; add_unique commits on its own
    duplicates = frappe.db.sql(
        f"""
        SELECT employee, attendance_date, COUNT(*) AS c
        FROM `{table}`
        WHERE docstatus < 2
        GROUP BY employee, attendance_date
        HAVING c > 1
        """,
        as_dict=True,
    )
    if duplicates:
        frappe.logger("patch").warning(
            f"mil_field_fixes: {len(duplicates)} duplicate employee/date rows; "
            "created a non-unique index instead"
        )
        frappe.db.add_index(
            MIL,
            ["employee", "attendance_date"],
            index_name="employee_attendance_date_index",
        )
    else:
        frappe.db.add_unique(MIL, ["employee", "attendance_date"])
