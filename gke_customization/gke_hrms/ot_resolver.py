# Copyright (c) 2026, Gurukrupa Export
"""
Approved-OT based error-punch resolution.

Monthly In-Out Log (MIL) ledger fields used here:
  punch_error, punch_ledger, resolution_status, resolution_remarks

HR actions (resolve_error_day):
  approve_ot  - OUT = shift end + approved OT
  auto_close  - OUT = shift end (no OT considered)
  set_out     - HR supplies the actual check-out datetime
  reject      - mark rejected (attendance left as-is)

Every resolution creates a REAL Employee Checkin (OUT), links it to the
attendance and recomputes hours/status through the same helper Manual Punch
Entry uses, so the punch chain stays clean and the nightly flagger does not
re-flag the day.
"""

from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import get_datetime, get_time, getdate, time_diff_in_hours
from gke_customization.gke_hrms.utils import _log_exc

MIL_DOCTYPE = "Monthly In-Out Log"

RES_PENDING = "Pending HR"
RES_AUTO_OT = "Auto-Resolved (Approved OT)"
RES_AUTO_CLOSE = "Auto-Closed (Shift End)"
RES_HR = "HR-Approved"
RES_REJECTED = "Rejected"

HR_ACTIONS = ("approve_ot", "auto_close", "set_out", "reject")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hhmm(value: timedelta) -> str:
    secs = int(value.total_seconds())
    return f"{secs // 3600:02d}:{secs % 3600 // 60:02d}"


def _shift_end_datetime(in_time: datetime, shift: str) -> datetime:
    """Shift-end datetime on the in_time's date, night-shift safe."""
    st = frappe.get_cached_value(
        "Shift Type", shift, ["start_time", "end_time"], as_dict=True
    )
    end = datetime.combine(getdate(in_time), get_time(st.end_time))
    if get_time(st.end_time) <= get_time(st.start_time):  # ends next day
        end += timedelta(days=1)
    return end


def get_approved_ot(employee, attendance_date):
    """Approved (allowed, uncancelled) OT Log row for the day."""
    return frappe.db.get_value(
        "OT Log",
        {
            "employee": employee,
            "attendance_date": getdate(attendance_date),
            "allow": 1,
            "is_cancelled": 0,
            "docstatus": ["<", 2],
        },
        ["name", "allowed_ot", "attn_ot_hrs"],
        as_dict=True,
    )


def get_monthly_in_out_log_attendance(mil_doc):
    """Submitted Attendance row for a card (linked one first, else employee+date)."""
    filters = {"docstatus": 1}
    if mil_doc.get("attendance"):
        filters["name"] = mil_doc.attendance
    elif mil_doc.get("employee") and mil_doc.get("attendance_date"):
        filters.update(
            employee=mil_doc.employee,
            attendance_date=getdate(mil_doc.attendance_date),
        )
    else:
        return None
    return frappe.db.get_value(
        "Attendance",
        filters,
        [
            "name", "employee", "status", "attendance_date", "in_time", "out_time",
            "working_hours", "shift", "punch_error",
        ],
        as_dict=True,
    )


def _close_todos(attendance_name, status="Closed"):
    """Close the open HR ToDo(s) raised for this attendance's punch error."""
    for name in frappe.get_all(
        "ToDo",
        filters={
            "reference_type": "Attendance",
            "reference_name": attendance_name,
            "status": "Open",
        },
        pluck="name",
    ):
        frappe.db.set_value("ToDo", name, "status", status)


# ---------------------------------------------------------------------------
# Ledger (punches + shift window + OT note, one text field)
# ---------------------------------------------------------------------------


def _ot_note(att, ot) -> str:
    if ot and ot.allowed_ot:
        note = f"OT approved {_hhmm(ot.allowed_ot)}"
        if not att.punch_error and att.in_time and att.out_time and att.shift:
            shift_end = _shift_end_datetime(get_datetime(att.in_time), att.shift)
            # frappe's time_diff_in_hours(end, start): end first
            actual = time_diff_in_hours(get_datetime(att.out_time), shift_end)
            if actual > ot.allowed_ot.total_seconds() / 3600 + 1 / 60:
                note += " (actual OT exceeds approval)"
        return note
    return "no approved OT" if att.punch_error else ""


def get_unlinked_punches_note(att) -> str:
    """Punches hrms skipped because the attendance already existed (late sync).

    hrms marks them skip_auto_attendance=1 and never links them, so they are
    invisible everywhere else. Show them so HR can pick that exact time in
    'Set OUT' (the resolver adopts a checkin with the same timestamp).
    Debounced duplicates (punch_rule = DUP) are not real punches: skipped.
    """
    if not (att.punch_error and att.get("employee") and att.in_time):
        return ""

    attendance_date = getdate(att.attendance_date)
    in_dt = get_datetime(att.in_time)
    rows = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": att.employee,
            "attendance": ("is", "not set"),
            "skip_auto_attendance": 1,
            "time": ["between", [in_dt, in_dt + timedelta(hours=28)]],
        },
        fields=["time", "punch_rule"],
        order_by="time asc",
    )

    labels = []
    for r in rows:
        if r.punch_rule == "DUP":
            continue
        t = get_datetime(r.time)
        day_mark = "+1" if t.date() > attendance_date else ""
        labels.append(f"{t:%H:%M}{day_mark}")
    return f"unlinked (skipped): {', '.join(labels)}" if labels else ""


def build_punch_ledger(att, ot=None) -> str:
    attendance_date = getdate(att.attendance_date)
    checkins = frappe.get_all(
        "Employee Checkin",
        filters={"attendance": att.name},
        fields=["time", "log_type", "punch_rule"],
        order_by="time asc",
    )

    parts = []
    for c in checkins:
        t = get_datetime(c.time)
        day_mark = "+1" if t.date() > attendance_date else ""
        label = f"{t:%H:%M}{day_mark} {c.log_type or '?'}"
        if c.punch_rule:
            label += f" ({c.punch_rule})"
        parts.append(label)
    if not parts:
        parts.append(
            f"{get_datetime(att.in_time):%H:%M} IN (attendance)"
            if att.in_time
            else "no punches linked"
        )

    line = " → ".join(parts)
    if att.shift:
        shift = frappe.get_cached_value(
            "Shift Type", att.shift, ["start_time", "end_time"], as_dict=True
        )
        if shift:
            line += f" | shift {shift.start_time}–{shift.end_time}"

    stranded = get_unlinked_punches_note(att)
    if stranded:
        line += f" | {stranded}"

    note = _ot_note(att, ot)
    return f"{line} | {note}" if note else line


# ---------------------------------------------------------------------------
# Card context: pure function, returns ONLY the fields that changed
# ---------------------------------------------------------------------------


def get_error_context(mil_doc, att) -> dict:
    """{fieldname: value} for punch_error / punch_ledger / resolution_*.
    Writes nothing — the caller persists everything in ONE operation."""
    if not att:
        return {}
    try:
        ot = get_approved_ot(mil_doc.employee, mil_doc.attendance_date)
        ctx = {
            "punch_error": att.punch_error or "",
            "punch_ledger": build_punch_ledger(att, ot),
        }

        current = mil_doc.get("resolution_status") or ""
        if att.punch_error:
            # new error, or an error re-opened after a resolution.
            # Rejected stays rejected (explicit HR decision).
            if current not in (RES_PENDING, RES_REJECTED):
                ctx["resolution_status"] = RES_PENDING
                if current:
                    ctx["resolution_remarks"] = ""
        elif current == RES_PENDING:
            # day self-healed (late punch / regenerated attendance)
            ctx["resolution_status"] = ""

        return {k: v for k, v in ctx.items() if (mil_doc.get(k) or "") != v}
    except Exception:
        _log_exc("Monthly In-Out Log: error context failed")
        return {}


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


def _ensure_out_checkin(att, out_time, source="Manual Punch") -> str:
    """Create (or adopt) the OUT Employee Checkin and link it to the attendance,
    same as Manual Punch Entry.update_emp_checkin + the link step.

    Adopts an existing checkin with the same timestamp (e.g. a late-synced
    punch hrms skipped), so HR can pick that exact time in 'Set OUT'.
    """
    existing = frappe.db.get_value(
        "Employee Checkin", {"employee": att.employee, "time": out_time}, "name"
    )
    # copy shift binding from the IN punch so IN/OUT belong to the same instance
    in_ci = frappe.db.get_value(
        "Employee Checkin",
        {"attendance": att.name, "log_type": "IN"},
        ["shift", "shift_start", "shift_end", "shift_actual_start", "shift_actual_end"],
        as_dict=True,
        order_by="time asc",
    )

    if existing:
        name = existing
    else:
        ci = frappe.new_doc("Employee Checkin")
        ci.employee = att.employee
        ci.time = out_time
        ci.log_type = "OUT"
        ci.source = source
        ci.skip_auto_attendance = 0
        ci.flags.ignore_permissions = True
        ci.insert()
        name = ci.name

    values = {
        "attendance": att.name,
        "log_type": "OUT",
        "offshift": 0,
        "skip_auto_attendance": 0,
        "punch_rule": "MANUAL",
    }
    if in_ci:
        values.update(in_ci)
    # overwrite whatever fetch_shift/session-pairing stamped on insert
    frappe.db.set_value("Employee Checkin", name, values, update_modified=False)
    return name


def _set_attendance_out(attendance_name, in_time, out_time) -> float:
    """Close the day the way Manual Punch Entry does: real OUT checkin, linked,
    then out_time / working hours / status recomputed from the linked punches."""
    from gke_customization.gke_hrms.doctype.manual_punch_entry.manual_punch_entry import (
        get_attendance,
    )

    att = frappe.db.get_value(
        "Attendance",
        attendance_name,
        ["name", "employee", "shift", "status", "attendance_date"],
        as_dict=True,
    )
    out_time = get_datetime(out_time)
    _ensure_out_checkin(att, out_time)

    logs = frappe.get_all(
        "Employee Checkin",
        filters={"attendance": att.name},
        fields=["name", "time", "log_type", "shift_start", "shift_end"],
        order_by="time asc",
    )

    # get_attendance() reads logs[0]["shift_start"/"shift_end"] for late/early
    # marking: never let a punch without a shift binding break the resolution.
    if logs and not (logs[0].get("shift_start") and logs[0].get("shift_end")):
        st = frappe.get_cached_value("Shift Type", att.shift, "start_time")
        shift_start = datetime.combine(getdate(att.attendance_date), get_time(st))
        shift_end = _shift_end_datetime(shift_start, att.shift)
        for log in logs:
            log["shift_start"] = shift_start
            log["shift_end"] = shift_end

    calc = get_attendance(frappe._dict(shift_name=att.shift), logs)

    updates = {
        "out_time": calc["out_time"] or out_time,
        "working_hours": round(calc["working_hours"] or 0, 2),
        "late_entry": calc["late_entry"],
        "early_exit": calc["early_exit"],
        "punch_error": "",
    }
    if att.status in ("Present", "Absent", "Half Day"):  # never overwrite leave / WFH etc.
        updates["status"] = calc["status"]

    frappe.db.set_value("Attendance", att.name, updates, update_modified=True)
    _close_todos(att.name)
    return updates["working_hours"]


def get_unlinked_punch_between(employee, start, end):
    """First unlinked, non-skipped punch inside [start, end], or None.
    Shared conflict guard for both auto-resolution paths below."""
    rows = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": employee,
            "time": ["between", [start, end]],
            "attendance": ("is", "not set"),
            "skip_auto_attendance": 0,
        },
        pluck="name",
        limit=1,
    )
    return rows[0] if rows else None


def try_resolve_with_approved_ot(
    attendance_doc, error_hint=None, resolved_by=None, remarks=None
) -> dict:
    """Missing OUT + approved OT Log -> OUT = shift end + approved OT.

    resolved_by=None  -> automatic (System, RES_AUTO_OT)
    resolved_by=user  -> HR action  (RES_HR)
    Returns {status: resolved|no_ot|conflict|skip, ...}
    """
    error = attendance_doc.get("punch_error") or error_hint
    if (
        error != "Missing OUT"
        or not attendance_doc.get("in_time")
        or not attendance_doc.get("shift")
    ):
        return {"status": "skip"}

    ot = get_approved_ot(attendance_doc.employee, attendance_doc.attendance_date)
    if not ot or not ot.allowed_ot:
        return {"status": "no_ot"}

    in_time = get_datetime(attendance_doc.in_time)
    expected_out = _shift_end_datetime(in_time, attendance_doc.shift) + timedelta(
        seconds=int(ot.allowed_ot.total_seconds())
    )

    # no unlinked punch inside the window contradicting the assumed close
    stray = get_unlinked_punch_between(attendance_doc.employee, in_time, expected_out)
    if stray:
        return {"status": "conflict", "stray": stray, "expected_out": expected_out}

    hours = _set_attendance_out(attendance_doc.name, in_time, expected_out)
    update_monthly_in_out_log_resolution(
        attendance_doc.employee,
        attendance_doc.attendance_date,
        RES_HR if resolved_by else RES_AUTO_OT,
        resolved_by or "System",
        f"OUT set to {expected_out} per approved OT {ot.name}",
        remarks,
    )
    return {"status": "resolved", "out_time": expected_out, "hours": hours, "ot": ot.name}


def auto_close_at_shift_end(attendance_doc, resolved_by=None, remarks=None) -> dict:
    """Missing OUT without OT -> OUT = shift end.

    resolved_by=user -> HR action (RES_AUTO_CLOSE)
    Returns {status: resolved|conflict|skip, ...}
    """
    if (
        attendance_doc.get("punch_error") != "Missing OUT"
        or not attendance_doc.get("in_time")
        or not attendance_doc.get("shift")
    ):
        return {"status": "skip"}

    in_time = get_datetime(attendance_doc.in_time)
    expected_out = _shift_end_datetime(in_time, attendance_doc.shift)
    if expected_out <= in_time:
        return {"status": "skip"}

    # same guard as the approved-OT path: no unlinked punch contradicting the close
    stray = get_unlinked_punch_between(attendance_doc.employee, in_time, expected_out)
    if stray:
        return {"status": "conflict", "stray": stray, "expected_out": expected_out}

    hours = _set_attendance_out(attendance_doc.name, in_time, expected_out)
    update_monthly_in_out_log_resolution(
        attendance_doc.employee,
        attendance_doc.attendance_date,
        RES_AUTO_CLOSE,
        resolved_by or "System",
        f"OUT set to {expected_out} (shift end, no OT)",
        remarks,
    )
    return {"status": "resolved", "out_time": expected_out, "hours": hours}


@frappe.whitelist()
def get_resolution_options(employee, attendance_date) -> dict:
    attendance_date = getdate(attendance_date)

    attendance = frappe.db.get_value(
        "Attendance",
        {
            "employee": employee,
            "attendance_date": attendance_date,
            "docstatus": 1,
        },
        ["punch_error", "in_time", "shift"],
        as_dict=True,
    )

    options = {
        "missing_out": False,
        "approved_ot": False,
        "approved_ot_hours": None,
        "expected_out": None,
        "shift_end": None,
    }

    if (
        attendance
        and attendance.punch_error == "Missing OUT"
        and attendance.in_time
        and attendance.shift
    ):
        options["missing_out"] = True

        in_time = get_datetime(attendance.in_time)
        shift_end = _shift_end_datetime(in_time, attendance.shift)
        options["shift_end"] = shift_end.strftime("%Y-%m-%d %H:%M:%S")

        ot = get_approved_ot(employee, attendance_date)
        if ot and ot.allowed_ot:
            expected_out = shift_end + timedelta(seconds=int(ot.allowed_ot.total_seconds()))

            options["approved_ot"] = True
            options["approved_ot_hours"] = _hhmm(ot.allowed_ot)
            options["expected_out"] = expected_out.strftime(
                "%Y-%m-%d %H:%M:%S"
            )

    return options

@frappe.whitelist()
def resolve_error_day(employee, attendance_date, action, out_time=None, remarks=None):
    """HR actions from the Monthly In-Out Log.

    approve_ot  - use the approved OT Log (OUT = shift end + approved OT)
    auto_close  - close at shift end (OUT = shift end, no OT)
    set_out     - HR supplies the actual check-out datetime
    reject      - mark rejected (attendance left as-is)
    """
    if action not in HR_ACTIONS:
        frappe.throw(_("Invalid action: {0}").format(action))

    attendance_date = getdate(attendance_date)
    attendance = frappe.db.get_value(
        "Attendance",
        {"employee": employee, "attendance_date": attendance_date, "docstatus": 1},
        ["name", "employee", "attendance_date", "in_time", "shift", "punch_error"],
        as_dict=True,
    )
    if not attendance:
        frappe.throw(
            _("No submitted attendance for {0} on {1}").format(employee, attendance_date)
        )
    frappe.has_permission("Attendance", "write", attendance.name, throw=True)
    if not attendance.punch_error:
        frappe.throw(_("Attendance {0} has no open punch error").format(attendance.name))

    user = frappe.session.user

    if action == "reject":
        update_monthly_in_out_log_resolution(
            employee, attendance_date, RES_REJECTED, user, "Resolution rejected", remarks
        )
        _close_todos(attendance.name, "Cancelled")
        return {"status": "rejected"}

    if action == "approve_ot":
        result = try_resolve_with_approved_ot(
            attendance, resolved_by=user, remarks=remarks
        )
        if result["status"] != "resolved":
            frappe.throw(
                _("Could not resolve with approved OT: {0}. Use 'Set OUT' instead.").format(
                    result["status"]
                )
            )
        return result

    if action == "auto_close":
        result = auto_close_at_shift_end(attendance, resolved_by=user, remarks=remarks)
        if result["status"] != "resolved":
            frappe.throw(
                _("Could not close at shift end: {0}. Use 'Set OUT' instead.").format(
                    result["status"]
                )
            )
        return result

    # set_out
    if attendance.punch_error != "Missing OUT":
        frappe.throw(
            _("'Set OUT' only fixes a Missing OUT. Correct '{0}' via Manual Punch.").format(
                attendance.punch_error
            )
        )
    if not attendance.in_time:
        frappe.throw(
            _("Attendance has no IN time; correct the punches via Manual Punch first.")
        )
    if not attendance.shift:
        frappe.throw(_("Attendance has no shift; cannot recalculate hours."))
    if not out_time:
        frappe.throw(_("OUT time is required for 'Set OUT'"))

    in_time = get_datetime(attendance.in_time)
    new_out = get_datetime(out_time)

    # OUT must come after the LAST linked punch (not just the first IN), or a
    # chain like IN, OUT, IN gets a second OUT sorted into the middle.
    last_punch = frappe.db.get_value(
        "Employee Checkin",
        {"attendance": attendance.name},
        "time",
        order_by="time desc",
    )
    floor = get_datetime(last_punch) if last_punch else in_time
    if new_out <= floor:
        frappe.throw(_("OUT time must be after the last punch ({0})").format(floor))

    # sanity cap: same limit the pairing engine uses for one IN -> OUT session
    from gke_customization.gke_hrms.punch_pairing import get_shift_config

    max_min = get_shift_config(attendance.shift)["max_session"]
    if new_out - in_time > timedelta(minutes=max_min):
        frappe.throw(
            _("OUT is more than {0} hours after IN ({1}). Please check the date.").format(
                max_min // 60, in_time
            )
        )

    hours = _set_attendance_out(attendance.name, in_time, new_out)
    update_monthly_in_out_log_resolution(employee, attendance_date, RES_HR, user, f"OUT set to {new_out}", remarks)
    return {"status": "resolved", "out_time": new_out, "hours": hours}


# ---------------------------------------------------------------------------
# Monthly In-Out Log card
# ---------------------------------------------------------------------------


def ensure_monthly_in_out_log(employee, attendance_date) -> str | None:
    """Get-or-create the card for an employee-date (creation auto-populates)."""
    attendance_date = getdate(attendance_date)
    name = frappe.db.exists(
        MIL_DOCTYPE,
        {"employee": employee, "attendance_date": attendance_date, "docstatus": ["<", 2]},
    )
    if name:
        return name
    try:
        mil = frappe.get_doc(
            {"doctype": MIL_DOCTYPE, "employee": employee, "attendance_date": attendance_date}
        )
        mil.insert(ignore_permissions=True)
        return mil.name
    except Exception:
        _log_exc(f"Monthly In-Out Log auto-creation failed for {employee}/{attendance_date}")
        return None


def update_monthly_in_out_log_resolution(employee, attendance_date, status, actor, text, remarks=None):
    """Write the resolution to the card (creating it if needed), then
    re-populate so ledger / hours reflect the resolved state."""
    name = ensure_monthly_in_out_log(employee, attendance_date)
    if not name:
        return
    note = f"{actor}: {text}" + (f" | {remarks}" if remarks else "")
    frappe.db.set_value(
        MIL_DOCTYPE,
        name,
        {"resolution_status": status, "resolution_remarks": note},
        update_modified=True,
    )
    try:
        frappe.get_doc(MIL_DOCTYPE, name).populate_from_attendance()
    except Exception:
        _log_exc(f"MIL refresh after resolution failed for {employee}/{attendance_date}")