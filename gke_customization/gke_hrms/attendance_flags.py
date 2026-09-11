# Copyright (c) 2026, Gurukrupa Export
"""
Punch-error detection on Attendance.

Case 2 (odd punches / forgotten IN or OUT): the flagger inspects the
checkins linked to a submitted attendance; when the IN/OUT sequence is
not a clean alternating chain starting with IN and ending with OUT, the
attendance is flagged (`punch_error`).

Resolution order per the agreed flow:
  1. Approved OT Log exists for the day  -> auto-resolve (OT is authoritative
     evidence the employee worked: OUT = shift end + approved OT).
  2. Shift policy "Auto Close at Shift End".
  3. Flag + HR ToDo -> HR resolves from the Monthly In-Out Log
     (error ledger) or Manual Punch.
"""

import frappe
from frappe.utils import (
    add_days,
    get_datetime,
    get_time,
    now_datetime,
    time_diff_in_hours,
)

MISSING_OUT = "Missing OUT"
MISSING_IN = "Missing IN"
UNPAIRED = "Unpaired punch"


def flag_attendance_punch_errors(doc, method=None):
    """doc_events: Attendance.on_submit — set punch_error when the linked
    punch sequence is broken. Note: auto-attendance links checkins AFTER
    submit, so the authoritative flagging runs in the scheduled
    flag_recent_attendances() job; this hook covers manual submissions
    where checkins are linked beforehand."""
    if frappe.flags.in_punch_pairing_reconcile:
        return

    if doc.get("punch_error"):
        return

    return detect_and_apply(doc)


def detect_and_apply(doc) -> str | None:
    """Core logic: detect a broken punch chain on an attendance and resolve
    in priority order (approved OT -> auto-close policy -> flag)."""
    checkins = frappe.get_all(
        "Employee Checkin",
        filters={"attendance": doc.name},
        fields=["name", "log_type", "time"],
        order_by="time asc",
    )
    if not checkins:
        return None

    error = _detect_error(checkins)
    if not error:
        return None

    # 1) Approved OT first: an approved OT Log for the day is authoritative
    #    evidence the employee worked — resolve automatically
    if error == MISSING_OUT:
        try:
            from gke_customization.gke_hrms.ot_resolver import (
                try_resolve_with_approved_ot,
            )

            result = try_resolve_with_approved_ot(doc, error_hint=error)
            if result.get("status") == "resolved":
                return "resolved-via-approved-ot"
        except Exception:
            frappe.log_error(frappe.get_traceback(), "OT resolution failed")

    # 2) Shift policy: auto close at shift end
    if error == MISSING_OUT and _shift_policy(doc) == "Auto Close at Shift End":
        if _auto_close_missing_out(doc):
            return None
        # auto-close not applicable (no shift/in_time) -> fall through to flag

    # 3) Flag for HR
    doc.db_set("punch_error", error)
    _create_todo(doc, error)
    return error


def flag_recent_attendances(days: int = 3):
    """Scheduled after the daily auto-attendance run: flag attendances whose
    linked punch sequence is broken. This is the authoritative pass because
    auto-attendance links checkins to the attendance only AFTER submit."""
    from_date = add_days(now_datetime().date(), -days)
    names = frappe.get_all(
        "Attendance",
        filters={"attendance_date": [">=", from_date], "docstatus": 1},
        pluck="name",
    )
    flagged = 0
    for name in names:
        doc = frappe.get_doc("Attendance", name)
        if doc.get("punch_error"):
            continue
        try:
            result = detect_and_apply(doc)
            if result and result != "resolved-via-approved-ot":
                flagged += 1
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"punch flag failed: {name}")
    frappe.db.commit()
    return {"checked": len(names), "flagged": flagged}


def _detect_error(checkins) -> str | None:
    types = [c.log_type for c in checkins]

    # unknown direction anywhere -> needs regularization
    if any(t not in ("IN", "OUT") for t in types):
        return UNPAIRED

    # clean chain: IN, OUT, IN, OUT, ... AND properly closed (even count)
    clean = len(types) % 2 == 0 and all(
        t == ("IN" if i % 2 == 0 else "OUT") for i, t in enumerate(types)
    )
    if clean:
        return None

    if types and types[0] == "OUT":
        return MISSING_IN
    if types and types[0] == "IN":
        # starts with IN but doesn't alternate/close -> missing checkout
        return MISSING_OUT
    return UNPAIRED


def _shift_policy(doc) -> str:
    if not doc.shift:
        return "Flag"
    try:
        return (
            frappe.db.get_value("Shift Type", doc.shift, "missing_out_policy") or "Flag"
        )
    except Exception:
        return "Flag"


def _auto_close_missing_out(doc) -> bool:
    """Missing OUT policy 'Auto Close at Shift End': assume OUT at shift end
    (no OT), recompute working hours, do not flag. Returns True when applied."""
    shift = frappe.db.get_value(
        "Shift Type", doc.shift, ["start_time", "end_time"], as_dict=True
    )
    if not shift or not doc.in_time:
        return False
    end_time = get_time(shift.end_time)
    import datetime as _dt

    out = _dt.datetime.combine(doc.in_time.date(), end_time)
    if end_time <= get_time(shift.start_time):  # night shift ends next day
        out = get_datetime(out) + _dt.timedelta(days=1)
    # NOTE: frappe's time_diff_in_hours(end, start) — end first
    hours = time_diff_in_hours(out, get_datetime(doc.in_time))
    frappe.db.set_value(
        "Attendance",
        doc.name,
        {"out_time": out, "working_hours": hours, "punch_error": ""},
        update_modified=False,
    )
    return True


def _create_todo(doc, error):
    # throttle: one open ToDo per attendance
    exists = frappe.db.exists(
        {
            "doctype": "ToDo",
            "reference_type": "Attendance",
            "reference_name": doc.name,
            "status": "Open",
        }
    )
    if exists:
        return

    frappe.get_doc(
        {
            "doctype": "ToDo",
            "allocated_to": _get_hr_user(doc),
            "reference_type": "Attendance",
            "reference_name": doc.name,
            "description": (
                f"Attendance {doc.name} for {doc.employee_name} on "
                f"{doc.attendance_date} flagged: {error}. "
                "Please review in the Monthly In-Out Log or correct via Manual Punch."
            ),
            "priority": "High",
            "status": "Open",
        }
    ).insert(ignore_permissions=True)


def _get_hr_user(doc):
    user = None
    try:
        user = frappe.db.get_value(
            "Has Role", {"role": "HR Manager", "parenttype": "User"}, "parent"
        )
    except Exception:
        user = None
    return user or "Administrator"
