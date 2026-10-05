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
  adjust_punch_full_day - exclude the day's punches and re-mark Present with
      HR-supplied IN/OUT times. The submitted attendance is cancelled and a
      new one created; excluded punches stay with an audit comment. Blocked
      when an active OT Log exists or the day is on leave.

Every resolution creates a REAL Employee Checkin (OUT), links it to the
attendance and recomputes hours/status through the same helper Manual Punch
Entry uses, so the punch chain stays clean and the nightly flagger does not
re-flag the day.
"""

from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import (
    format_datetime,
    get_datetime,
    get_link_to_form,
    now,
    get_time,
    getdate,
    time_diff_in_hours,
)

from gke_customization.gke_hrms.utils import _log_exc

MIL_DOCTYPE = "Monthly In-Out Log"

RES_PENDING = "Pending HR"
RES_AUTO_OT = "Auto-Resolved (Approved OT)"
RES_AUTO_CLOSE = "Auto-Closed (Shift End)"
RES_HR = "HR-Approved"
RES_REJECTED = "Rejected"

HR_ACTIONS = ("approve_ot", "auto_close", "set_out", "reject", "adjust_punch_full_day")

FULL_DAY_BLOCK_STATUSES = ("On Leave", "Half Day", "Work From Home")

_ATT_FIELDS = [
    "name",
    "docstatus",
    "employee",
    "attendance_date",
    "status",
    "shift",
    "in_time",
    "punch_error",
    "leave_type",
    "leave_application",
    "attendance_request",
]
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


def get_active_ot_logs(employee, attendance_date):
    """Uncancelled OT Log names for the day, approved or not."""
    return frappe.get_all(
        "OT Log",
        filters={
            "employee": employee,
            "attendance_date": getdate(attendance_date),
            "is_cancelled": 0,
        },
        pluck="name",
    )


def get_monthly_in_out_log_attendance(mil_doc):
    """Submitted Attendance row for a card (linked one first, else employee+date).

    No fallback when the linked attendance exists but is not submitted: the
    card keeps its own ledger and error state instead of silently re-linking
    to a recreated attendance and wiping its punch error.
    """
    fields = [
        "name",
        "employee",
        "status",
        "attendance_date",
        "in_time",
        "out_time",
        "working_hours",
        "shift",
        "punch_error",
    ]
    if mil_doc.get("attendance"):
        return frappe.db.get_value(
            "Attendance",
            {"name": mil_doc.attendance, "docstatus": 1},
            fields,
            as_dict=True,
        )
    if mil_doc.get("employee") and mil_doc.get("attendance_date"):
        return frappe.db.get_value(
            "Attendance",
            {
                "employee": mil_doc.employee,
                "attendance_date": getdate(mil_doc.attendance_date),
                "docstatus": 1,
            },
            fields,
            as_dict=True,
        )
    return None


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

    Adopts an existing checkin with the same timestamp only when it is
    unlinked (e.g. a late-synced punch hrms skipped). A punch already linked
    to an attendance is a conflict and throws, so one day can never silently
    steal another day's punch.
    """
    existing = frappe.db.get_value(
        "Employee Checkin",
        {"employee": att.employee, "time": out_time},
        ["name", "attendance"],
        as_dict=True,
    )
    if existing and existing.attendance:
        other_date = frappe.db.get_value(
            "Attendance", existing.attendance, "attendance_date"
        )
        frappe.throw(
            _(
                "Cannot set check-out to {0}. A punch at this exact time already "
                "belongs to attendance {1} (dated {2}). Please enter a different "
                "check-out time, or resolve that attendance first."
            ).format(
                frappe.bold(format_datetime(out_time)),
                get_link_to_form("Attendance", existing.attendance),
                frappe.bold(frappe.format(other_date, {"fieldtype": "Date"})),
            ),
            title=_("Check-out Time Already Used"),
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
        name = existing.name
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


def _exclude_checkins(names, new_in, new_out, new_attendance, user) -> int:
    """Take punches out of the pairing chain and leave an audit comment on each.
 
    Rows are kept (never deleted) so biometric-sync dedupe and the audit trail
    stay intact. They are also UNLINKED: a punch left pointing at the cancelled
    attendance would still be counted by process_data()'s odd/even check-in test
    and could zero out a day.
 
    Was: get_all + (set_value + get_doc + add_comment) per punch.
    Now: one UPDATE + one INSERT, whatever the punch count.
    """
    names = list(names)
    if not names:
        return 0
    frappe.db.set_value(
        "Employee Checkin",
        {"name": ["in", names]},
        {"attendance": None, "skip_auto_attendance": 1, "punch_rule": "OVERRIDE"},
        update_modified=False,
    )
    text = _(
        "Punch excluded by 'Adjust Punch & Grant Full Day': day re-marked"
        " Present {0} to {1} in attendance {2}. By {3}."
    ).format(new_in, new_out, new_attendance, user)
    _add_comments(("Employee Checkin", n, text) for n in names)
    return len(names)

def _create_override_punches(attendance_name, employee, punches, shift_fields):
    """Create (or adopt) the IN and OUT punches of the granted Full Day and link
    them to the new attendance, same as Manual Punch Entry does.
 
    punches = [(datetime, "IN"|"OUT"), ...]
    ONE lookup for all punches (was one per punch). Adopts a same-timestamp
    checkin only when unlinked; one owned by another attendance is a conflict and
    throws BEFORE anything is created.
    """
    existing = {
        get_datetime(r.time): r
        for r in frappe.get_all(
            "Employee Checkin",
            filters={"employee": employee, "time": ["in", [p[0] for p in punches]]},
            fields=["name", "time", "attendance"],
        )
    }
    for when, _log_type in punches:
        row = existing.get(when)
        if row and row.attendance:
            frappe.throw(
                _(
                    "Employee Checkin {0} at {1} is already linked to attendance {2}."
                    " Resolve that day first."
                ).format(row.name, when, row.attendance)
            )
 
    for when, log_type in punches:
        row = existing.get(when)
        if row:
            name = row.name
        else:
            ci = frappe.new_doc("Employee Checkin")
            ci.employee = employee
            ci.time = when
            ci.log_type = log_type
            ci.source = "Manual Punch"
            ci.skip_auto_attendance = 0
            ci.flags.ignore_permissions = True
            ci.insert()
            name = ci.name
 
        values = {
            "attendance": attendance_name,
            "log_type": log_type,
            "offshift": 0,
            "skip_auto_attendance": 0,
            "punch_rule": "MANUAL",
            **shift_fields,
        }
        frappe.db.set_value("Employee Checkin", name, values, update_modified=False)



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
    if att.status in (
        "Present",
        "Absent",
        "Half Day",
    ):  # never overwrite leave / WFH etc.
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
    return {
        "status": "resolved",
        "out_time": expected_out,
        "hours": hours,
        "ot": ot.name,
    }


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


def adjust_punch_grant_full_day(
    attendance, in_time=None, out_time=None, resolved_by=None, remarks=None
) -> dict:
    """'Adjust Punch & Grant Full Day'.
 
    Re-marks the day Present with HR-supplied IN/OUT, excludes the day's punches
    (kept + commented, never deleted), cancels the old attendance and creates a
    new one. Runs inside a savepoint so a failure half-way cannot leave a
    cancelled attendance with no replacement.
 
    Only needs attendance.name / .employee / .attendance_date from the caller.
    """
    from gke_customization.gke_hrms.doctype.manual_punch_entry.manual_punch_entry import (
        get_attendance,
    )
 
    employee = attendance.employee
    attendance_date = getdate(attendance.attendance_date)
    actor = resolved_by or "System"
 
    # row lock + fresh read in ONE query (was lock query + read query)
    att = frappe.db.get_value(
        "Attendance", attendance.name, _ATT_FIELDS, as_dict=True, for_update=True
    )
    blocker = get_full_day_blocker(employee, attendance_date, att)
    if blocker:
        frappe.throw(blocker)
 
    if not (in_time and out_time):
        frappe.throw(_("IN and OUT times are required"))

    new_in = get_datetime(in_time)
    new_out = get_datetime(out_time)
    if new_out <= new_in:
        frappe.throw(_("OUT time must be after IN time"))
 
    st = frappe.get_cached_value(  # document cache: no DB hit after the first call
        "Shift Type",
        att.shift,
        [
            "start_time",
            "begin_check_in_before_shift_start_time",
            "allow_check_out_after_shift_end_time",
            "working_hours_threshold_for_half_day",
        ],
        as_dict=True,
    )
    shift_start = datetime.combine(attendance_date, get_time(st.start_time))
    shift_end = _shift_end_datetime(shift_start, att.shift)
    if not (shift_start <= new_in <= shift_end and shift_start <= new_out <= shift_end):
        frappe.throw(
            _(
                "IN and OUT must be inside the shift window {0} to {1}."
                " A Full Day cannot be granted over another day's punches."
            ).format(shift_start, shift_end)
        )
 
    # a 'Full Day' must actually be one: not below the shift's half-day threshold
    working_hours = round((new_out - new_in).total_seconds() / 3600, 2)
    threshold = st.working_hours_threshold_for_half_day or 0
    if threshold and working_hours < threshold:
        frappe.throw(
            _("{0} hrs is below the half-day threshold ({1} hrs); this is not a Full Day.").format(
                working_hours, threshold
            )
        )
 
    # ---- ONE punch read, classified in Python ------------------------------
    # was 3 reads: linked punches, overlap guard, stray unlinked punches.
    # [lo, hi] is a superset of [new_in, new_out]; punches linked to this
    # attendance are fetched even if they lie outside it.
    lo = shift_start - timedelta(minutes=st.begin_check_in_before_shift_start_time or 0)
    hi = shift_end + timedelta(minutes=st.allow_check_out_after_shift_end_time or 0)
 
    rows = frappe.get_all(
        "Employee Checkin",
        filters={"employee": employee},
        or_filters=[["attendance", "=", att.name], ["time", "between", [lo, hi]]],
        fields=["name", "time", "source", "attendance", "skip_auto_attendance"],
    )
    linked, strays, conflicts = [], [], set()
    for r in rows:
        if r.attendance == att.name:
            linked.append(r)
        elif new_in <= get_datetime(r.time) <= new_out:
            if r.attendance:
                conflicts.add(r.attendance)  # another day owns a punch in the window
            elif not r.skip_auto_attendance:
                strays.append(r)
 
    if conflicts:
        frappe.throw(
            _(
                "Punches inside this window already belong to attendance {0}."
                " Resolve that day first."
            ).format(", ".join(sorted(conflicts)))
        )
 
    # linked punches OUTSIDE this day's window belong to the neighbouring day
    # (next-day pairing bug): release them, never exclude them
    mine = [c for c in linked if lo <= get_datetime(c.time) <= hi]
    released = len(linked) - len(mine)
 
    candidates = {c.name: c for c in mine + strays}.values()
    if any(c.source == "Outdoor Duty" for c in candidates):
        frappe.throw(_("An Outdoor Duty punch is part of this day; it cannot be excluded here."))
 
    # a punch at exactly the new IN/OUT time is re-used as that punch, not
    # excluded and then re-adopted (that left a stale 'excluded' comment)
    reuse_times = {new_in, new_out}
    exclude_names = [c.name for c in candidates if get_datetime(c.time) not in reuse_times]
 
    shift_fields = {
        "shift": att.shift,
        "shift_start": shift_start,
        "shift_end": shift_end,
        "shift_actual_start": lo,
        "shift_actual_end": hi,
    }
 
    old_attendance = att.name

    # no savepoint here on purpose: attendance.submit() fires the
    # create_monthly_in_out_log hook, which commits; a commit destroys the
    # savepoint, so a mid-flow failure could not be rolled back anyway.
    # Every guard above runs before the first mutation.
    frappe.get_doc("Attendance", old_attendance).cancel()

    # explicit unlink, ONE UPDATE: do not rely on cancel() clearing the links
    if linked:
        frappe.db.set_value(
            "Employee Checkin",
            {"name": ["in", [c.name for c in linked]]},
            "attendance",
            None,
            update_modified=False,
        )

    att_doc = frappe.get_doc(
        {
            "doctype": "Attendance",
            "employee": employee,
            "attendance_date": attendance_date,
            "status": "Present",
            "shift": att.shift,
            "in_time": new_in,
            "out_time": new_out,
            "working_hours": working_hours,
            "late_entry": 0,
            "early_exit": 0,
        }
    )
    att_doc.flags.ignore_permissions = True
    att_doc.submit()  # new doc: ONE validate + insert + submit (was insert() then submit())

    # HRMS validate() can rewrite status (e.g. a leave created meanwhile).
    # The in-memory doc already reflects it: no re-query.
    if att_doc.status != "Present":
        frappe.throw(
            _("Attendance became {0} on save; Full Day cannot be granted.").format(
                att_doc.status
            )
        )

    excluded_count = _exclude_checkins(exclude_names, new_in, new_out, att_doc.name, actor)
    _create_override_punches(
        att_doc.name, employee, [(new_in, "IN"), (new_out, "OUT")], shift_fields
    )

    # same late / early / hours maths as Manual Punch Entry and Set OUT.
    # Status stays Present: HR explicitly granted the day.
    calc = get_attendance(
        frappe._dict(shift_name=att.shift),
        frappe.get_all(
            "Employee Checkin",
            filters={"attendance": att_doc.name},
            fields=["name", "time", "log_type", "shift_start", "shift_end"],
            order_by="time asc",
        ),
    )
    working_hours = round(calc["working_hours"] or working_hours, 2)
    frappe.db.set_value(
        "Attendance",
        att_doc.name,
        {
            "working_hours": working_hours,
            "late_entry": calc["late_entry"],
            "early_exit": calc["early_exit"],
            "in_time": new_in,
            "out_time": new_out,
        },
        update_modified=True,
    )

    # audit trail on both attendances: ONE INSERT, no get_doc round-trips
    _add_comments(
        [
            (
                "Attendance",
                old_attendance,
                _("Cancelled by 'Adjust Punch & Grant Full Day'. Replaced by {0}. By {1}.").format(
                    att_doc.name, actor
                ),
            ),
            (
                "Attendance",
                att_doc.name,
                _("Created by 'Adjust Punch & Grant Full Day' replacing {0}. By {1}.").format(
                    old_attendance, actor
                ),
            ),
        ]
    )

    # Re-link the live card to the new attendance (replaces _relink_monthly_log).
    # Submitted cards are already cancelled + re-created by the Attendance
    # server scripts; a DRAFT card is not, and would otherwise keep pointing at
    # the cancelled attendance. One read; the name is reused for the response.
    card = frappe.db.get_value(
        MIL_DOCTYPE,
        {"employee": employee, "attendance_date": attendance_date, "docstatus": ["<", 2]},
        ["name", "attendance"],
        as_dict=True,
    )
    if card and card.attendance != att_doc.name:
        frappe.db.set_value(
            MIL_DOCTYPE, card.name, "attendance", att_doc.name, update_modified=False
        )

    update_monthly_in_out_log_resolution(  # existing helper, unchanged
        employee,
        attendance_date,
        RES_HR,
        actor,
        "Punches excluded ({0}), released to neighbouring day ({1}); day re-marked "
        "Present {2} to {3}, new attendance {4}".format(
            excluded_count, released, new_in, new_out, att_doc.name
        ),
        remarks,
    )
    _close_todos(old_attendance)  # existing helper, unchanged

    return {
        "status": "resolved",
        "out_time": new_out,
        "hours": working_hours,
        "new_attendance": att_doc.name,
        "new_monthly_log": card.name if card else ensure_monthly_in_out_log(employee, attendance_date),
        "excluded": excluded_count,
        "released": released,
    }
 
 
@frappe.whitelist()
def get_resolution_options(employee, attendance_date) -> dict:
    attendance_date = getdate(attendance_date)
 
    # _ATT_FIELDS is a superset of the old field list; the same row is handed to
    # the blocker, so it is not read a second time
    attendance = frappe.db.get_value(
        "Attendance",
        {"employee": employee, "attendance_date": attendance_date, "docstatus": 1},
        _ATT_FIELDS,
        as_dict=True,
    )
 
    options = {
        "missing_out": False,
        "approved_ot": False,
        "approved_ot_hours": None,
        "expected_out": None,
        "shift_start": None,
        "shift_end": None,
        "punch_count": 0,
        "active_ot": False,
        "full_day_blocker": "",
    }
    if not attendance:
        return options
 
    frappe.has_permission("Attendance", "read", attendance.name, throw=True)
 
    # ONE OT read feeds both the active_ot flag and the Full Day blocker
    ot_names = get_active_ot_logs(employee, attendance_date)
    options["active_ot"] = bool(ot_names)
    options["full_day_blocker"] = get_full_day_blocker(
        employee, attendance_date, attendance, ot_names
    )
 
    shift_end = None
    if attendance.shift:
        st = frappe.get_cached_value("Shift Type", attendance.shift, "start_time")
        shift_start = datetime.combine(attendance_date, get_time(st))
        shift_end = _shift_end_datetime(shift_start, attendance.shift)
        options["shift_start"] = shift_start.strftime("%Y-%m-%d %H:%M:%S")
        options["shift_end"] = shift_end.strftime("%Y-%m-%d %H:%M:%S")
        options["punch_count"] = frappe.db.count(
            "Employee Checkin", {"attendance": attendance.name}
        )
 
    # unchanged existing logic
    if (
        attendance.punch_error == "Missing OUT"
        and attendance.in_time
        and attendance.shift
    ):
        options["missing_out"] = True
 
        ot = get_approved_ot(employee, attendance_date)
        if ot and ot.allowed_ot:
            expected_out = shift_end + timedelta(seconds=int(ot.allowed_ot.total_seconds()))
            options["approved_ot"] = True
            options["approved_ot_hours"] = _hhmm(ot.allowed_ot)
            options["expected_out"] = expected_out.strftime("%Y-%m-%d %H:%M:%S")
 
    return options
 

def _add_comments(rows):
    """Bulk-insert Comments: rows = [(reference_doctype, reference_name, content)].
 
    ONE INSERT instead of get_doc() + add_comment() per row (each of which also
    re-saves the reference doc's `_comments`). Trade-off: skips Comment.on_update,
    so the list-view comment count is not refreshed; the form timeline still shows
    the comments.
    """
    rows = list(rows)
    if not rows:
        return
    ts, user = now(), frappe.session.user
    frappe.db.bulk_insert(
        "Comment",
        fields=[
            "name",
            "creation",
            "modified",
            "modified_by",
            "owner",
            "docstatus",
            "idx",
            "comment_type",
            "comment_email",
            "reference_doctype",
            "reference_name",
            "content",
        ],
        values=[
            (frappe.generate_hash(length=10), ts, ts, user, user, 0, 0, "Comment", user, dt, dn, text)
            for dt, dn, text in rows
        ],
    )
 

def _check_attendance_has_error_and_shift(att) -> str:
    if not att.punch_error:
        return _("Attendance {0} has no open punch error").format(att.name)
    if not att.shift:
        return _("Attendance has no shift; Full Day cannot be granted.")
    return ""

def _check_not_leave_or_request(att) -> str:
    if att.leave_type or att.leave_application or att.status in FULL_DAY_BLOCK_STATUSES:
        return _("Day is marked {0}; Full Day cannot be granted over leave.").format(att.status)
    if att.attendance_request:
        return _(
            "Attendance was created from Attendance Request {0}. Amend the request instead."
        ).format(att.attendance_request)
    return ""

def _check_no_active_ot_log(employee, attendance_date, ot_names=None) -> str:
    if ot_names is None:
        ot_names = get_active_ot_logs(employee, attendance_date)
    if ot_names:
        return _("Active OT Log {0} exists for this day. Settle the OT Log first.").format(
            ", ".join(ot_names)
        )
    return ""

def _check_employee_active_on_date(employee, attendance_date) -> str:
    emp = frappe.db.get_value(
        "Employee", employee, ["status", "date_of_joining", "relieving_date"], as_dict=True
    )
    if not emp:
        return ""
    if emp.status != "Active":
        return _("Employee is {0}.").format(emp.status)
    if emp.date_of_joining and attendance_date < getdate(emp.date_of_joining):
        return _("Attendance date is before the joining date.")
    if emp.relieving_date and attendance_date > getdate(emp.relieving_date):
        return _("Attendance date is after the relieving date.")
    return ""

def _check_no_approved_leave(employee, attendance_date) -> str:
    # leave approved AFTER this attendance was created: HRMS would flip the new
    # attendance to On Leave during validate(), after the old one is cancelled
    leave = frappe.db.exists(
        "Leave Application",
        {
            "employee": employee,
            "docstatus": 1,
            "status": "Approved",
            "from_date": ["<=", attendance_date],
            "to_date": [">=", attendance_date],
        },
    )
    if leave:
        return _("Approved Leave Application {0} covers this day.").format(leave)
    return ""

def _check_no_salary_slip(employee, attendance_date) -> str:
    slip = frappe.db.exists(
        "Salary Slip",
        {
            "employee": employee,
            "docstatus": ["<", 2],
            "start_date": ["<=", attendance_date],
            "end_date": [">=", attendance_date],
        },
    )
    if slip:
        return _("Salary Slip {0} already covers this date. Cancel it first.").format(slip)
    return ""


def get_full_day_blocker(employee, attendance_date, att=None, ot_names=None) -> str:
    """Reason 'Adjust Punch & Grant Full Day' cannot run, or ''.

    Single source of truth for the dialog (get_resolution_options) AND the action.
    Pass `att` (fetched with _ATT_FIELDS) and `ot_names` (get_active_ot_logs) when
    the caller already has them: no re-reads. Checks run cheapest first and stop
    at the first failure.
    """
    attendance_date = getdate(attendance_date)
    att = att or frappe.db.get_value(
        "Attendance",
        {"employee": employee, "attendance_date": attendance_date, "docstatus": 1},
        _ATT_FIELDS,
        as_dict=True,
    )
    if not att or att.docstatus != 1:
        return _("No submitted attendance for {0} on {1}").format(employee, attendance_date)

    # lambdas keep this lazy: a DB check only runs if every check before it passed
    checks = (
        lambda: _check_attendance_has_error_and_shift(att),
        lambda: _check_not_leave_or_request(att),
        lambda: _check_no_active_ot_log(employee, attendance_date, ot_names),
        lambda: _check_employee_active_on_date(employee, attendance_date),
        lambda: _check_no_approved_leave(employee, attendance_date),
        lambda: _check_no_salary_slip(employee, attendance_date),
    )
    for check in checks:
        if reason := check():
            return reason
    return ""


@frappe.whitelist()
def resolve_error_day(
    employee, attendance_date, action, out_time=None, in_time=None, remarks=None
):
    """HR actions from the Monthly In-Out Log.

    approve_ot  - use the approved OT Log (OUT = shift end + approved OT)
    auto_close  - close at shift end (OUT = shift end, no OT)
    set_out     - HR supplies the actual check-out datetime
    reject      - mark rejected (attendance left as-is)
    adjust_punch_full_day - exclude the day's punches and re-mark Present
        with the supplied IN/OUT times
    """
    if action not in HR_ACTIONS:
        frappe.throw(_("Invalid action: {0}").format(action))

    attendance_date = getdate(attendance_date)
    attendance = frappe.db.get_value(
        "Attendance",
        {"employee": employee, "attendance_date": attendance_date, "docstatus": 1},
        [
            "name",
            "employee",
            "attendance_date",
            "in_time",
            "shift",
            "punch_error",
        ],
        as_dict=True,
    )
    if not attendance:
        frappe.throw(
            _("No submitted attendance for {0} on {1}").format(
                employee, attendance_date
            )
        )
    frappe.has_permission("Attendance", "write", attendance.name, throw=True)
    if not attendance.punch_error:
        frappe.throw(
            _("Attendance {0} has no open punch error").format(attendance.name)
        )

    user = frappe.session.user

    if action == "reject":
        update_monthly_in_out_log_resolution(
            employee,
            attendance_date,
            RES_REJECTED,
            user,
            "Resolution rejected",
            remarks,
        )
        _close_todos(attendance.name, "Cancelled")
        return {"status": "rejected"}

    if action == "approve_ot":
        result = try_resolve_with_approved_ot(
            attendance, resolved_by=user, remarks=remarks
        )
        if result["status"] != "resolved":
            frappe.throw(
                _(
                    "Could not resolve with approved OT: {0}. Use 'Set OUT' instead."
                ).format(result["status"])
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

    if action == "adjust_punch_full_day":
        frappe.has_permission("Attendance", "cancel", attendance.name, throw=True)
        frappe.has_permission("Attendance", "create", throw=True)
        return adjust_punch_grant_full_day(
            attendance,
            in_time=in_time,
            out_time=out_time,
            resolved_by=user,
            remarks=remarks,
        )

    # set_out
    if attendance.punch_error != "Missing OUT":
        frappe.throw(
            _(
                "'Set OUT' only fixes a Missing OUT. Correct '{0}' via Manual Punch."
            ).format(attendance.punch_error)
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
            _(
                "OUT is more than {0} hours after IN ({1}). Please check the date."
            ).format(max_min // 60, in_time)
        )

    hours = _set_attendance_out(attendance.name, in_time, new_out)
    update_monthly_in_out_log_resolution(
        employee, attendance_date, RES_HR, user, f"OUT set to {new_out}", remarks
    )
    return {"status": "resolved", "out_time": new_out, "hours": hours}


# ---------------------------------------------------------------------------
# Monthly In-Out Log card
# ---------------------------------------------------------------------------


def ensure_monthly_in_out_log(employee, attendance_date) -> str | None:
    """Get-or-create the card for an employee-date (creation auto-populates)."""
    attendance_date = getdate(attendance_date)
    name = frappe.db.exists(
        MIL_DOCTYPE,
        {
            "employee": employee,
            "attendance_date": attendance_date,
            "docstatus": ["<", 2],
        },
    )
    if name:
        return name
    try:
        mil = frappe.get_doc(
            {
                "doctype": MIL_DOCTYPE,
                "employee": employee,
                "attendance_date": attendance_date,
            }
        )
        mil.insert(ignore_permissions=True)
        return mil.name
    except Exception:
        _log_exc(
            f"Monthly In-Out Log auto-creation failed for {employee}/{attendance_date}"
        )
        return None


def update_monthly_in_out_log_resolution(
    employee, attendance_date, status, actor, text, remarks=None
):
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
        _log_exc(
            f"MIL refresh after resolution failed for {employee}/{attendance_date}"
        )
