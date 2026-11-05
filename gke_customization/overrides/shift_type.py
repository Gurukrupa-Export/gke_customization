# Copyright (c) 2026, Gurukrupa Export
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import add_days, cint, getdate
from hrms.hr.doctype.shift_type.shift_type import ShiftType

DEFAULT_OVERLAP_DAYS = 7


class CustomShiftType(ShiftType):
    """Auto attendance that re-checks only recent days for absent marking.

    The standard run rebuilds absent dates from Process Attendance After to Last Sync of
    Checkin for every employee on every run. Here the hourly run starts from the date absent
    marking last completed, minus an overlap. The nightly run covers the full range.
    """

    def _process(self, logs):
        original_start = self.process_attendance_after
        start_date = self.get_absent_marking_start_date()

        if start_date:
            self.process_attendance_after = start_date

        try:
            super()._process(logs)
        finally:
            self.process_attendance_after = original_start

        self.update_absent_reconciled_till()

    def get_absent_marking_start_date(self):
        """Return the clamped start date, or None when the full range must be processed."""
        if self.flags.get("full_absent_reconciliation"):
            return None

        settings = get_incremental_settings()
        if not settings.enabled or not self.get("custom_absent_reconciled_till"):
            return None

        start_date = add_days(
            getdate(self.custom_absent_reconciled_till), -settings.overlap_days
        )
        return max(getdate(self.process_attendance_after), getdate(start_date))

    def update_absent_reconciled_till(self):
        reconciled_till = add_days(getdate(self.last_sync_of_checkin), -1)
        self.custom_absent_reconciled_till = reconciled_till
        frappe.db.set_value(
            "Shift Type",
            self.name,
            "custom_absent_reconciled_till",
            reconciled_till,
            update_modified=False,
        )


def get_incremental_settings():
    values = frappe.db.get_singles_dict("HR Settings")
    overlap_days = cint(values.get("custom_absent_reconciliation_overlap_days"))
    return frappe._dict(
        enabled=cint(values.get("custom_enable_incremental_absent_marking")),
        overlap_days=overlap_days if overlap_days > 0 else DEFAULT_OVERLAP_DAYS,
    )


def process_full_absent_reconciliation():
    """Nightly job: process absent marking for the full range, as the standard run does."""
    shift_names = frappe.get_all(
        "Shift Type", filters={"enable_auto_attendance": 1}, pluck="name"
    )
    for shift_name in shift_names:
        shift = frappe.get_cached_doc("Shift Type", shift_name)
        shift.flags.full_absent_reconciliation = True
        try:
            shift.process_auto_attendance()
        finally:
            shift.flags.full_absent_reconciliation = False
