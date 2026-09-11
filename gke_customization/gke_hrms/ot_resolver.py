# Copyright (c) 2026, Gurukrupa Export
"""
Approved-OT based error-punch resolution — the bridge between the
session-pairing engine's error flags and the OT Log approvals.

Flow (per the requirement):
  Error Punch → shown in Monthly In-Out Log (ledger + case + OT check)
    → Approved OT exists & punch sequence matches
        → attendance auto-processed (OUT = shift end + approved OT)
    → No approved OT
        → HR verifies & approves from the report → attendance marked

Nothing here touches punches, OT tools, or payroll — it only reads
approved OT Log rows and updates the Attendance record's
in_time/out_time/working_hours/punch_error (same mechanism the
existing OT Request / Attendance Request flows already use).
"""

from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import flt, get_datetime, get_time, getdate, time_diff_in_hours

MIL_DOCTYPE = "Monthly In-Out Log"

# error case labels shown in the Monthly In-Out Log
CASE_MISSING_OUT = "Forgot Check-out"
CASE_NEXT_DAY = "Next-Day Check-out"
CASE_BEYOND_SHIFT = "Beyond Shift"
CASE_ODD = "Odd Punch"
CASE_ORPHAN = "Orphan Punch"

OT_NONE = "No Approved OT"
OT_MATCHED = "Approved OT Matched"
OT_EXCEEDS = "Approved OT Exceeds"

RES_PENDING = "Pending HR"
RES_AUTO_OT = "Auto-Resolved (Approved OT)"
RES_AUTO_CLOSE = "Auto-Closed (Shift End)"
RES_HR = "HR-Approved"
RES_REJECTED = "Rejected"


# ---------------------------------------------------------------------------
# Classification & ledger
# ---------------------------------------------------------------------------


def classify_error_case(attendance) -> str | None:
    """Map an attendance's punch_error to a human case label."""
    if not attendance.get("punch_error"):
        return None
    err = attendance.punch_error
    out_time = attendance.get("out_time")
    in_time = attendance.get("in_time")
    if err == "Missing OUT":
        return CASE_MISSING_OUT
    if err == "Missing IN":
        return CASE_ODD
    if err == "Unpaired punch":
        if (
            out_time
            and in_time
            and get_datetime(out_time).date() > get_datetime(in_time).date()
        ):
            return CASE_NEXT_DAY
        return CASE_BEYOND_SHIFT
    if err == "Reclassification needed":
        return CASE_ODD
    return CASE_ODD


def build_punch_ledger(attendance_name) -> str:
    """Ledger line: the exact punch sequence with rules and shift window."""
    checkins = frappe.get_all(
        "Employee Checkin",
        filters={"attendance": attendance_name},
        fields=["time", "log_type", "punch_rule"],
        order_by="time asc",
    )
    att = frappe.db.get_value(
        "Attendance",
        attendance_name,
        ["attendance_date", "in_time", "out_time", "shift"],
        as_dict=True,
    )
    shift = (
        frappe.db.get_value(
            "Shift Type", att.shift, ["start_time", "end_time"], as_dict=True
        )
        if att and att.shift
        else None
    )

    parts = []
    for c in checkins:
        t = get_datetime(c.time)
        day_mark = "+1" if att and t.date() > getdate(att.attendance_date) else ""
        label = f"{t.strftime('%H:%M')}{day_mark} {c.log_type or '?'}"
        if c.punch_rule:
            label += f" ({c.punch_rule})"
        parts.append(label)
    if not parts:
        if att and att.in_time:
            parts.append(
                f"{get_datetime(att.in_time).strftime('%H:%M')} IN (attendance)"
            )
        else:
            parts.append("no punches linked")

    window = ""
    if shift:
        window = f" | shift {shift.start_time}–{shift.end_time}"
    return " → ".join(parts) + window


def get_approved_ot(employee, attendance_date, attendance_name=None):
    """Approved (allowed, uncancelled) OT Log row for the day."""
    filters = {
        "employee": employee,
        "attendance_date": getdate(attendance_date),
        "allow": 1,
        "is_cancelled": 0,
        "docstatus": ["<", 2],
    }
    return frappe.db.get_value(
        "OT Log",
        filters,
        ["name", "allowed_ot", "attn_ot_hrs", "attendance"],
        as_dict=True,
    )


# ---------------------------------------------------------------------------
# Auto-resolution with approved OT
# ---------------------------------------------------------------------------


def _shift_end_datetime(in_time: datetime, shift: str) -> datetime:
    """Shift-end datetime on the in_time's date, night-shift safe."""
    st = frappe.db.get_value(
        "Shift Type", shift, ["start_time", "end_time"], as_dict=True
    )
    end = datetime.combine(getdate(in_time), get_time(st.end_time))
    if get_time(st.end_time) <= get_time(st.start_time):  # night shift ends next day
        end += timedelta(days=1)
    return end


def try_resolve_with_approved_ot(attendance_doc, error_hint: str | None = None) -> dict:
    """If the attendance has a Missing-OUT error and an approved OT Log exists
    for the day, auto-complete the attendance:
    OUT = shift end + approved allowed_ot, hours recomputed, error cleared.

    error_hint lets the caller pass the freshly detected error (the flag
    pass detects Missing OUT from the punch chain BEFORE punch_error is
    stored on the attendance).

    Returns {status: resolved|no_ot|conflict|skip, ...}
    """
    error = attendance_doc.get("punch_error") or error_hint
    if error != "Missing OUT" or not attendance_doc.get("in_time"):
        return {"status": "skip"}

    ot = get_approved_ot(
        attendance_doc.employee, attendance_doc.attendance_date, attendance_doc.name
    )
    if not ot or not ot.allowed_ot:
        return {"status": "no_ot"}

    in_time = get_datetime(attendance_doc.in_time)
    shift_end = _shift_end_datetime(in_time, attendance_doc.shift)
    expected_out = shift_end + timedelta(seconds=int(ot.allowed_ot.total_seconds()))

    # punch-sequence compatibility: no stray unlinked punches inside the
    # window that would contradict the assumed close time
    stray = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": attendance_doc.employee,
            "time": ["between", [in_time, expected_out]],
            "attendance": ("is", "not set"),
            "skip_auto_attendance": 0,
        },
        pluck="name",
        limit=1,
    )
    if stray:
        return {"status": "conflict", "stray": stray[0], "expected_out": expected_out}

    # NOTE: frappe's time_diff_in_hours(end, start) — end first
    hours = round(time_diff_in_hours(expected_out, in_time), 2)
    frappe.db.set_value(
        "Attendance",
        attendance_doc.name,
        {"out_time": expected_out, "working_hours": hours, "punch_error": ""},
        update_modified=True,
    )
    _update_mil(
        attendance_doc.employee,
        attendance_doc.attendance_date,
        {
            "ot_check_status": OT_MATCHED,
            "resolution_status": RES_AUTO_OT,
            "resolved_by": "System (Approved OT)",
            "resolution_remarks": f"OUT set to {expected_out} per approved OT {ot.name}",
        },
    )
    return {
        "status": "resolved",
        "out_time": expected_out,
        "hours": hours,
        "ot": ot.name,
    }


# ---------------------------------------------------------------------------
# HR resolution (from the Monthly In-Out Log)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def resolve_error_day(employee, attendance_date, action, out_time=None, remarks=None):
    """HR actions from the Monthly In-Out Log.

    action:
      approve_ot  — use the approved OT Log (same math as auto-resolution)
      set_out     — HR supplies the actual check-out datetime
      auto_close  — close at shift end (no OT)
      reject      — mark resolution rejected (attendance left as-is)
    """
    attendance = frappe.db.get_value(
        "Attendance",
        {
            "employee": employee,
            "attendance_date": getdate(attendance_date),
            "docstatus": 1,
        },
        ["name", "in_time", "shift", "punch_error"],
        as_dict=True,
    )
    if not attendance:
        frappe.throw(
            _("No submitted attendance for {0} on {1}").format(
                employee, attendance_date
            )
        )

    resolution = RES_HR
    if action == "approve_ot":
        result = try_resolve_with_approved_ot(attendance)
        if result["status"] != "resolved":
            frappe.throw(
                _(
                    "Could not resolve with approved OT: {0}. Use 'Set OUT' instead."
                ).format(result["status"])
            )
        _update_mil(
            employee,
            attendance_date,
            {
                "resolution_status": RES_AUTO_OT,
                "resolved_by": frappe.session.user,
                "resolution_remarks": remarks
                or f"HR-approved via OT {result.get('ot')}",
            },
        )
        return result

    if action == "reject":
        _update_mil(
            employee,
            attendance_date,
            {
                "resolution_status": RES_REJECTED,
                "resolved_by": frappe.session.user,
                "resolution_remarks": remarks,
            },
        )
        return {"status": "rejected"}

    # set_out / auto_close -> compute the out_time
    if not attendance.in_time:
        frappe.throw(
            _("Attendance has no IN time; correct the punches via Manual Punch first.")
        )
    in_time = get_datetime(attendance.in_time)
    if action == "auto_close":
        new_out = _shift_end_datetime(in_time, attendance.shift)
    else:
        if not out_time:
            frappe.throw(_("OUT time is required for 'Set OUT'"))
        new_out = get_datetime(out_time)

    # NOTE: frappe's time_diff_in_hours(end, start) — end first
    hours = round(time_diff_in_hours(new_out, in_time), 2)
    frappe.db.set_value(
        "Attendance",
        attendance.name,
        {"out_time": new_out, "working_hours": hours, "punch_error": ""},
        update_modified=True,
    )
    if action == "auto_close":
        resolution = RES_AUTO_CLOSE
    _update_mil(
        employee,
        attendance_date,
        {
            "resolution_status": resolution,
            "resolved_by": frappe.session.user,
            "resolution_remarks": remarks or f"OUT set to {new_out} by HR",
        },
    )
    return {"status": "resolved", "out_time": new_out, "hours": hours}


# ---------------------------------------------------------------------------
# Monthly In-Out Log context
# ---------------------------------------------------------------------------


def apply_error_context(mil_doc) -> None:
    """Attach error case, punch ledger and OT-check status to a
    Monthly In-Out Log document. Safe: never raises, never overwrites
    an existing resolution."""
    try:
        att_name = mil_doc.get("attendance")
        if not att_name and mil_doc.employee and mil_doc.attendance_date:
            att_name = frappe.db.get_value(
                "Attendance",
                {
                    "employee": mil_doc.employee,
                    "attendance_date": mil_doc.attendance_date,
                    "docstatus": 1,
                },
                "name",
            )
        if not att_name:
            return
        att = frappe.db.get_value(
            "Attendance",
            att_name,
            ["name", "punch_error", "in_time", "out_time", "shift"],
            as_dict=True,
        )
        if not att:
            return

        mil_doc.punch_error = att.punch_error or ""
        mil_doc.error_case = classify_error_case(att) or ""
        mil_doc.punch_ledger = build_punch_ledger(att.name)

        ot = get_approved_ot(mil_doc.employee, mil_doc.attendance_date)
        if att.punch_error:
            mil_doc.ot_check_status = OT_MATCHED if ot else OT_NONE
            if not mil_doc.resolution_status:
                mil_doc.resolution_status = RES_PENDING
        elif ot and att.out_time and att.in_time:
            # annotate non-error days whose OT claim exceeds the approval
            shift_end = _shift_end_datetime(get_datetime(att.in_time), att.shift)
            actual_ot = time_diff_in_hours(shift_end, get_datetime(att.out_time))
            if (
                actual_ot
                > flt(ot.allowed_ot.total_seconds() / 3600 if ot.allowed_ot else 0)
                + 1 / 60
            ):
                mil_doc.ot_check_status = OT_EXCEEDS
            else:
                mil_doc.ot_check_status = OT_MATCHED
        else:
            mil_doc.ot_check_status = ""
    except Exception:
        frappe.log_error(
            title="Monthly In-Out Log: error context failed",
            message=frappe.get_traceback(),
        )


def _update_mil(employee, attendance_date, updates: dict):
    """Push resolution fields to the existing MIL document (if any)."""
    name = frappe.db.exists(
        MIL_DOCTYPE,
        {
            "employee": employee,
            "attendance_date": getdate(attendance_date),
            "docstatus": ["<", 2],
        },
    )
    if name:
        frappe.db.set_value(MIL_DOCTYPE, name, updates, update_modified=True)
