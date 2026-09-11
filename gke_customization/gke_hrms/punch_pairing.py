# Copyright (c) 2026, Gurukrupa Export
"""
Hybrid Session-Based Punch Pairing Engine.

Classifies Employee Checkin punches (IN/OUT) and binds them to shift
instances using an open-work-session state machine instead of pure
time-window containment. Works for any shift timing (day, night,
rotating) because every rule anchors on shift instances, never on
calendar dates.

Rules (evaluated in order):
  R1 Intake   : punch within [S - early_horizon, S + max(grace, INTAKE_MIN)] of a
                shift-instance start S -> IN, new session bound to that instance.
  R2 Close    : open session exists and punch is within max_session_length of the
                session IN -> OUT, closes the session (works across midnight).
  R3 Return   : no open session, punch inside a shift's [S, shift_end] span ->
                IN (return from personal out), bound to that instance.
  R4 Stale    : open session older than max_session_length -> punch starts a NEW
                session (IN); the stale session surfaces as a punch_error on
                attendance instead of creating a 24h+ session silently.
  R5 Orphan   : none of the above -> direction-less punch, offshift=1, routed to
                the regularization queue (never silently dropped).

Classification is deterministic over the punch stream, so the nightly
reconciliation job can re-run it and converge to the same result even
when biometric data arrives late or out of order.

Rollout switches (HR Settings):
  enable_session_pairing       (default on)  master switch
  session_pairing_parallel_run (default off) when on, legacy behaviour is kept
                                             and engine decisions are only logged
"""

from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import cint, get_datetime
from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift_timings

# ---------------------------------------------------------------------------
# Constants / config
# ---------------------------------------------------------------------------

DEFAULT_EARLY_HORIZON_MIN = 300  # 5 hours: punch up to 5h before shift start is an IN
DEFAULT_MAX_SESSION_MIN = 1680  # 28 hours: longest payable IN->OUT stretch
INTAKE_MIN_MINUTES = 120  # intake zone stays open at least 2h past shift start
HISTORY_WINDOW_HOURS = 48  # punch history considered when classifying live
RECONCILE_DAYS = 3  # nightly reconciliation look-back

SESSION_PAIRING_LOG = "punch_pairing"


def get_mode() -> str:
    settings = frappe.db.get_value(
        "HR Settings",
        None,
        ["enable_session_pairing", "session_pairing_parallel_run"],
        as_dict=True,
    )

    if not cint(settings.enable_session_pairing):
        return "off"

    return "log" if cint(settings.session_pairing_parallel_run) else "live"


def is_live() -> bool:
    return get_mode() == "live"


def _log(message):
    frappe.log_error(_("Punch Pairing"), _(message))


def get_shift_cfg(shift_name: str) -> dict:
    """Shift-level knobs for the engine. Falls back to defaults when the
    custom columns/fields are not present yet (pre-patch)."""
    cfg = {
        "early": DEFAULT_EARLY_HORIZON_MIN,
        "max_session": DEFAULT_MAX_SESSION_MIN,
        "grace": 0,
    }
    if not shift_name:
        return cfg
    try:
        vals = frappe.db.get_value(
            "Shift Type",
            shift_name,
            [
                "late_entry_grace_period",
                "early_check_in_horizon",
                "max_session_length",
            ],
            as_dict=True,
        )
    except Exception:
        # custom columns missing (patch not run yet)
        vals = frappe.db.get_value(
            "Shift Type", shift_name, ["late_entry_grace_period"], as_dict=True
        )
    if not vals:
        return cfg
    cfg["grace"] = cint(vals.get("late_entry_grace_period"))
    cfg["early"] = cint(vals.get("early_check_in_horizon")) or DEFAULT_EARLY_HORIZON_MIN
    cfg["max_session"] = cint(vals.get("max_session_length")) or DEFAULT_MAX_SESSION_MIN
    return cfg


# ---------------------------------------------------------------------------
# Shift instances around a timestamp
# ---------------------------------------------------------------------------


def _instance_cache():
    if not hasattr(frappe.local, "_pp_instance_cache"):
        frappe.local._pp_instance_cache = {}
    return frappe.local._pp_instance_cache


def get_instances_around(employee: str, for_dt: datetime) -> list[dict]:
    """Shift instances (prev/curr/next) around a datetime, with engine knobs.

    Each instance: shift_type, start_datetime, end_datetime, actual_start,
    actual_end, early, grace, max_session.
    """
    key = (employee, for_dt.replace(second=0, microsecond=0))
    cache = _instance_cache()
    if key in cache:
        return cache[key]

    instances = []
    seen = set()
    try:
        prev, curr, nxt = get_employee_shift_timings(employee, for_dt, True)
    except Exception:
        prev = curr = nxt = None

    for s in (prev, curr, nxt):
        if not s or not s.get("start_datetime") or not s.get("shift_type"):
            continue
        k = (s.shift_type.name, s.start_datetime)
        if k in seen:
            continue
        seen.add(k)
        cfg = get_shift_cfg(s.shift_type.name)
        instances.append(
            {
                "shift_type": s.shift_type.name,
                "start_datetime": s.start_datetime,
                "end_datetime": s.end_datetime,
                "actual_start": s.actual_start,
                "actual_end": s.actual_end,
                "early": cfg["early"],
                "grace": cfg["grace"],
                "max_session": cfg["max_session"],
            }
        )

    instances.sort(key=lambda x: x["start_datetime"])
    cache[key] = instances
    return instances


# ---------------------------------------------------------------------------
# Rule engine (pure, given instances + session state)
# ---------------------------------------------------------------------------


def _intake_window(inst: dict) -> tuple[datetime, datetime]:
    start = inst["start_datetime"]
    intake_end_minutes = max(inst["grace"], INTAKE_MIN_MINUTES)
    return (
        start - timedelta(minutes=inst["early"]),
        start + timedelta(minutes=intake_end_minutes),
    )


def _apply_rules(
    for_dt: datetime, instances: list[dict], open_session: dict | None
) -> dict:
    # R1 - intake: nearest shift wins on overlapping zones (iterate reversed).
    # Exception: if a session is ALREADY open for this same shift instance,
    # the punch CLOSES it (personal out / gate bounce inside the intake
    # window) instead of re-opening a duplicate session. Intake only wins
    # over an open session of a DIFFERENT (earlier) instance — that is what
    # keeps the forgot-checkout case (next-day arrival) starting a new day.
    for inst in reversed(instances):
        intake_start, intake_end = _intake_window(inst)
        if intake_start <= for_dt <= intake_end:
            if (
                open_session
                and open_session.get("instance")
                and open_session["instance"].get("start_datetime")
                == inst["start_datetime"]
            ):
                return {"rule": "R2", "log_type": "OUT", "instance": inst, "flag": None}
            return {"rule": "R1", "log_type": "IN", "instance": inst, "flag": None}

    if open_session:
        inst = open_session.get("instance")
        max_session = inst["max_session"] if inst else DEFAULT_MAX_SESSION_MIN
        elapsed = for_dt - open_session["time"]
        if elapsed <= timedelta(minutes=max_session):
            # R2 - close the open session (spans midnight / next day)
            return {"rule": "R2", "log_type": "OUT", "instance": inst, "flag": None}

        # R4 - stale session: punch starts a new session; old session will
        # surface as a punch_error via the attendance flagger (odd sequence)
        for inst2 in reversed(instances):
            if inst2["start_datetime"] <= for_dt <= inst2["end_datetime"]:
                return {
                    "rule": "R4",
                    "log_type": "IN",
                    "instance": inst2,
                    "flag": "STALE_SESSION",
                }
        return {
            "rule": "R4",
            "log_type": None,
            "instance": None,
            "flag": "STALE_SESSION",
        }

    # R3 - return from personal out (inside an active shift span)
    for inst in reversed(instances):
        if inst["start_datetime"] <= for_dt <= inst["end_datetime"]:
            return {"rule": "R3", "log_type": "IN", "instance": inst, "flag": None}

    # R5 - orphan
    return {"rule": "R5", "log_type": None, "instance": None, "flag": "ORPHAN"}


def classify_stream(punches: list[dict], instances_getter) -> list[dict]:
    """Classify an ordered punch stream in memory.

    punches: [{name, time, ...}] chronological.
    instances_getter(employee, time) -> list of instance dicts.
    Returns the punches with `result` attached.
    """
    employee = punches[0]["employee"] if punches else None
    open_session = None  # {"time": datetime, "instance": dict|None}

    out = []
    for p in punches:
        dt = get_datetime(p["time"])
        instances = instances_getter(employee, dt)
        result = _apply_rules(dt, instances, open_session)

        if result["rule"] in ("R1", "R3", "R4"):
            if result["log_type"] == "IN":
                open_session = {"time": dt, "instance": result["instance"]}
        elif result["rule"] == "R2":
            open_session = None
        # R5 leaves state unchanged

        p = dict(p)
        p["result"] = result
        out.append(p)
    return out


# ---------------------------------------------------------------------------
# Live classification (reads punch history from DB)
# ---------------------------------------------------------------------------


def _history(employee: str, before_dt: datetime) -> list[dict]:
    """Last punches before before_dt inside the history window."""
    rows = frappe.get_all(
        "Employee Checkin",
        filters=[
            ["employee", "=", employee],
            ["time", ">", before_dt - timedelta(hours=HISTORY_WINDOW_HOURS)],
            ["time", "<", before_dt],
        ],
        fields=["name", "employee", "time", "log_type"],
        order_by="time asc",
        limit=50,
    )
    return rows


def classify_punch(employee: str, punch_dt: datetime) -> dict:
    """Classify one punch against the employee's recent punch history.
    Returns {rule, log_type, instance, flag}."""
    punch_dt = get_datetime(punch_dt)
    history = _history(employee, punch_dt)
    stream = history + [
        {"name": None, "employee": employee, "time": punch_dt, "log_type": None}
    ]
    results = classify_stream(stream, get_instances_around)
    return results[-1]["result"]


# ---------------------------------------------------------------------------
# Checkin binding
# ---------------------------------------------------------------------------


def bind_checkin(doc, result: dict) -> None:
    """Stamp an Employee Checkin doc with the classification result."""
    if not result or result.get("rule") == "R5":
        doc.shift = None
        doc.offshift = 1
        if not doc.log_type:
            doc.log_type = None
        if hasattr(doc, "punch_rule"):
            doc.punch_rule = result.get("rule") if result else None
        return

    inst = result.get("instance")
    doc.offshift = 0
    if inst:
        doc.shift = inst["shift_type"]
        doc.shift_start = inst["start_datetime"]
        doc.shift_end = inst["end_datetime"]
        doc.shift_actual_start = inst["actual_start"]
        doc.shift_actual_end = inst["actual_end"]
    else:
        doc.shift = None
        doc.shift_start = None
        doc.shift_end = None
        doc.shift_actual_start = None
        doc.shift_actual_end = None

    if not doc.log_type and result.get("log_type"):
        doc.log_type = result["log_type"]
    if hasattr(doc, "punch_rule"):
        doc.punch_rule = result.get("rule")


# ---------------------------------------------------------------------------
# Nightly reconciliation
# ---------------------------------------------------------------------------


def _reclassify_range(employee: str, from_dt: datetime, to_dt: datetime) -> dict:
    """Re-run the engine over a window and correct stored classifications.

    Only touches checkins that are not linked to a submitted attendance
    (those are flagged for human review instead of silently rewritten).
    """
    punches = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": employee,
            "time": ["between", [from_dt, to_dt]],
        },
        fields=[
            "name",
            "employee",
            "time",
            "log_type",
            "shift",
            "shift_start",
            "shift_end",
            "shift_actual_start",
            "shift_actual_end",
            "offshift",
            "attendance",
        ],
        order_by="time asc",
    )
    if not punches:
        return {"checked": 0, "corrected": 0, "flagged": 0}

    results = classify_stream(punches, get_instances_around)
    corrected = flagged = 0

    for p, with_result in zip(punches, results):
        result = with_result["result"]

        def _differs(p, result):
            inst = result.get("instance")
            new_log = result.get("log_type")
            changed = False
            if new_log and p.log_type != new_log:
                changed = True
            if inst:
                if p.shift != inst["shift_type"]:
                    changed = True
                elif p.shift_start and get_datetime(p.shift_start) != get_datetime(
                    inst["start_datetime"]
                ):
                    changed = True
            elif result.get("rule") == "R5" and not cint(p.offshift or 0):
                changed = True
            return changed

        if not _differs(p, result):
            continue

        if p.attendance:
            # linked to (possibly submitted) attendance - flag, don't rewrite
            att_status = frappe.db.get_value("Attendance", p.attendance, "docstatus")
            if att_status == 1:
                frappe.db.set_value(
                    "Attendance",
                    p.attendance,
                    "punch_error",
                    "Reclassification needed",
                    update_modified=False,
                )
                flagged += 1
            continue

        inst = result.get("instance")
        update = {"punch_rule": result.get("rule")} if _has_punch_rule_column() else {}
        if result.get("rule") == "R5":
            update.update({"offshift": 1, "shift": None, "log_type": None})
        else:
            update.update({"offshift": 0})
            if inst:
                update.update(
                    {
                        "shift": inst["shift_type"],
                        "shift_start": inst["start_datetime"],
                        "shift_end": inst["end_datetime"],
                        "shift_actual_start": inst["actual_start"],
                        "shift_actual_end": inst["actual_end"],
                    }
                )
            if result.get("log_type"):
                update["log_type"] = result["log_type"]
        if update:
            frappe.db.set_value(
                "Employee Checkin", p["name"], update, update_modified=False
            )
            corrected += 1

    return {"checked": len(punches), "corrected": corrected, "flagged": flagged}


def _has_punch_rule_column() -> bool:
    try:
        return bool(
            frappe.db.sql(
                "SELECT `fieldname` FROM `tabCustom Field` "
                "WHERE `dt`='Employee Checkin' AND `fieldname`='punch_rule'",
                as_dict=True,
            )
        )
    except Exception:
        return False


def rebuild_employee(employee: str, from_dt: datetime = None) -> dict:
    """Public helper: re-run classification for one employee (used by tests
    and correction flows)."""
    from_dt = get_datetime(from_dt) or frappe.utils.now_datetime() - timedelta(
        days=RECONCILE_DAYS
    )
    return _reclassify_range(employee, from_dt, frappe.utils.now_datetime())


def nightly_reconciliation():
    """Scheduled daily (04:00): reprocess recent punches, correct delayed or
    out-of-order biometric data, and flag mismatched attendances."""
    if not is_live():
        return

    now = frappe.utils.now_datetime()
    from_dt = now - timedelta(days=RECONCILE_DAYS)

    employees = frappe.get_all(
        "Employee Checkin",
        filters={"time": [">=", from_dt]},
        pluck="employee",
        distinct=True,
    )

    totals = {"employees": len(employees), "checked": 0, "corrected": 0, "flagged": 0}
    for i, employee in enumerate(employees):
        try:
            stats = _reclassify_range(employee, from_dt, now)
            for k in ("checked", "corrected", "flagged"):
                totals[k] += stats[k]
        except Exception:
            _log(f"Reconciliation failed for {employee}.\n" f"{frappe.get_traceback()}")
        if i % 100 == 99:
            frappe.db.commit()

    # flag attendances whose linked punch sequence is not a clean IN..OUT chain
    _flag_recent_attendances(from_dt, now)
    # surface orphan punches (R5) that belong to no session/shift so they
    # reach the regularization queue instead of being silently invisible
    _flag_orphan_checkins(from_dt)

    frappe.db.commit()
    _log(f"Nightly reconciliation completed.\n" f"Totals: {totals}")
    return totals


def _flag_recent_attendances(from_dt, to_dt):
    """Flag submitted attendances whose linked punch sequence is broken."""
    from gke_customization.gke_hrms.attendance_flags import flag_recent_attendances

    flag_recent_attendances()


def _flag_orphan_checkins(from_dt):
    """Raise one ToDo per employee/day for punches that the engine could not
    classify (R5: offshift / no direction). Throttled: skips if an open ToDo
    already references a checkin of that employee+day."""
    orphans = frappe.get_all(
        "Employee Checkin",
        filters={
            "time": [">=", from_dt],
            "skip_auto_attendance": 0,
            "attendance": ("is", "not set"),
        },
        or_filters=[["offshift", "=", 1], ["log_type", "is", "not set"]],
        fields=["name", "employee", "employee_name", "time"],
        order_by="time asc",
    )

    seen_days = set()
    for o in orphans:
        try:
            day_key = (o.employee, o.time.date())
            if day_key in seen_days:
                continue
            seen_days.add(day_key)
            existing = frappe.db.exists(
                {
                    "doctype": "ToDo",
                    "reference_type": "Employee Checkin",
                    "reference_name": o.name,
                    "status": "Open",
                }
            )
            if existing:
                continue
            frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "allocated_to": _get_hr_user(),
                    "reference_type": "Employee Checkin",
                    "reference_name": o.name,
                    "description": (
                        f"Unpaired punch for {o.employee_name} at {o.time} "
                        "(no shift/session match). Please regularize via Manual Punch."
                    ),
                    "priority": "Medium",
                    "status": "Open",
                }
            ).insert(ignore_permissions=True)
        except Exception:
            _log(
                f"Orphan ToDo creation failed for {o.get('name')}.\n"
                f"{frappe.get_traceback()}"
            )


def _get_hr_user():
    try:
        user = frappe.db.get_value(
            "Has Role", {"role": "HR Manager", "parenttype": "User"}, "parent"
        )
    except Exception:
        user = None
    return user or "Administrator"
