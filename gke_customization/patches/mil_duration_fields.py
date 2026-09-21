# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

"""Convert the MIL duration fields (spent_hrs / net_wrk_hrs / ot_hrs) to
Duration (DECIMAL seconds).

Time columns render as "Invalid date" on the desk for any value >= 24h
(moment.js limit), and long overnight days legitimately produce 26h+ spent
hours. Duration stores seconds and displays correctly at any length.

MariaDB cannot write TIME_TO_SEC() straight back into the TIME column being
read, so each field moves through a sidecar column: add -> copy+convert ->
swap. Works from both a TIME column (mil_field_fixes already ran) and a
legacy varchar column with HH:MM:SS strings (it did not).
"""

import frappe

MIL = "Monthly In-Out Log"
DURATION_FIELDS = ("net_wrk_hrs", "spent_hrs", "ot_hrs")


def _column_type(table, column):
    row = frappe.db.sql(
        """
        SELECT DATA_TYPE FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """,
        (table, column),
        as_dict=True,
    )
    return row[0]["DATA_TYPE"] if row else None


def execute():
    table = f"tab{MIL}"
    for field in DURATION_FIELDS:
        ctype = _column_type(table, field)
        if ctype is None or ctype == "decimal":
            continue  # missing (fresh install) or already converted

        sidecar = f"{field}__dur"
        if _column_type(table, sidecar):  # interrupted earlier attempt
            frappe.db.sql_ddl(f"ALTER TABLE `{table}` DROP COLUMN `{sidecar}`")

        frappe.db.sql_ddl(f"ALTER TABLE `{table}` ADD COLUMN `{sidecar}` DECIMAL(21,9) NULL")
        frappe.db.sql(
            f"UPDATE `{table}` SET `{sidecar}` = TIME_TO_SEC(`{field}`)"
        )
        frappe.db.sql_ddl(
            f"ALTER TABLE `{table}` DROP COLUMN `{field}`, "
            f"CHANGE COLUMN `{sidecar}` `{field}` DECIMAL(21,9) NULL"
        )
