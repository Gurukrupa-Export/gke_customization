# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

"""Validate session-pairing settings configured on Shift Type.

The settings must ensure that:
  - The early check-in and late-entry window stays within 24 hours,
    so punches are not assigned to the wrong shift.
  - The maximum session length is long enough for the shift duration,
    but does not extend too far into the following day.
"""

import frappe
from frappe import _
from frappe.utils import cint, get_time

from datetime import datetime, timedelta

INTAKE_FLOOR_MINUTES = 120  # engine keeps intake open at least 2h past start
MAX_EARLY_HORIZON_MINUTES = 1320  # 22h: early horizon + 2h intake < 24h


def validate(doc, method=None):
    _validate_early_horizon(doc)
    _validate_max_session(doc)


def _validate_early_horizon(doc):
    early = cint(doc.early_check_in_horizon)
    if not early:
        return

    if early < 0:
        frappe.throw(_("Early Check-in Horizon cannot be negative."))

    intake_width = early + max(cint(doc.late_entry_grace_period), INTAKE_FLOOR_MINUTES)

    if intake_width >= 24 * 60:
        frappe.throw(
            _(
                "Early Check-in Horizon of {0} minutes is too large. "
                "The total check-in window would extend to 24 hours or more "
                "and may cause punches to be assigned to the wrong shift. "
                "Please reduce the Early Check-in Horizon to {1} minutes or less."
            ).format(early, MAX_EARLY_HORIZON_MINUTES)
        )


def _validate_max_session(doc):
    max_session = cint(doc.max_session_length)
    if not max_session:
        return

    if max_session < 60:
        frappe.throw(_("Max Session Length must be at least 60 minutes."))

    shift_span = _shift_span_minutes(doc)

    if shift_span and max_session < shift_span:
        frappe.throw(
            _(
                "Max Session Length of {0} hours is shorter than the "
                "shift duration of {1} hours. Please increase Max Session Length "
                "to at least {2} minutes."
            ).format(
                max_session / 60,
                shift_span / 60,
                shift_span,
            )
        )

    cap = 24 * 60 + cint(doc.early_check_in_horizon)

    if max_session > cap:
        frappe.throw(
            _(
                "Max Session Length of {0} hours is too long. "
                "It cannot exceed {1} hours for the current Early Check-in Horizon. "
                "A longer session may incorrectly include the next day's punch. "
                "Please reduce Max Session Length to {1} hours or less."
            ).format(
                max_session / 60,
                cap / 60,
            )
        )


def _shift_span_minutes(doc) -> int:
    try:
        start = get_time(doc.start_time)
        end = get_time(doc.end_time)
    except Exception:
        return 0

    start_dt = datetime.combine(datetime.min.date(), start)
    end_dt = datetime.combine(datetime.min.date(), end)

    if end_dt <= start_dt:  # night shift: ends next day
        end_dt += timedelta(days=1)

    return int((end_dt - start_dt).total_seconds() // 60)