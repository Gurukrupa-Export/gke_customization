# Copyright (c) 2026, Gurukrupa Export
"""
Golden scenario harness for the Session-Based Punch Pairing engine
and the error-punch -> approved-OT resolution flow.

Creates throwaway shift types + employees in the site, inserts real
Employee Checkins (through the engine), runs HRMS auto-attendance,
applies the flag/resolution passes and asserts every expected outcome:

  S1 sheet rows 3-6  : 9:00 IN -> next-day 3:00 OUT, 5:00 IN, 12:00 OUT
  S2 sheet rows 11-14: forgot checkout; next-day 9:00 IN, 18:30 OUT -> flagged
  S3 sheet rows 16-17: 9:00 IN -> next-day 11:40 OUT (26.67h)
  S4 Issue 2         : 5:00 AM check-in (4h before 9:00 shift)
  S5 night shift     : 21:00 IN, personal out 23:00-23:30, 06:30 OUT
  S6 forgot check-in : single 18:30 punch -> flagged
  S7 HR resolution   : set_out action from the report flow
  S8 approved OT     : Missing OUT + approved OT Log -> auto-resolved

Run (from bench root):  env/bin/python run_pp_tests.py
Cleans up everything it creates.
"""

import frappe
from frappe.utils import get_datetime

D1, D2 = "2026-09-01", "2026-09-02"
DAY_SHIFT = "PP-TEST 9:00 TO 18:30"
NIGHT_SHIFT = "PP-TEST NIGHT 21:00 TO 07:00"
HOLIDAY_LIST = "PP-TEST-HOLIDAYS"
CODES = ["PP-A", "PP-B", "PP-C", "PP-D", "PP-E", "PP-F", "PP-G", "PP-H"]

results = []


def run():
    frappe.flags.in_test = True
    try:
        from gke_customization.patches.punch_pairing_fields import (
            execute as install_fields,
        )

        install_fields()  # idempotent; ensures all custom fields exist
    except Exception:
        frappe.log_error(frappe.get_traceback(), "PP test: field install failed")

    _setup()
    try:
        _insert_all_punches()
        # single processing pass AFTER all punches exist, so the absent-
        # marking pass never pre-creates Absent rows for pending scenarios
        _process(DAY_SHIFT)
        _process(NIGHT_SHIFT)
        _scenario_s1()
        _scenario_s2()
        _scenario_s3()
        _scenario_s4()
        _scenario_s5()
        _scenario_s6()
        _scenario_s7()
        _scenario_s8()
        _report()
    finally:
        _cleanup()
    return results


def _insert_all_punches():
    punches = {
        "PP-A": [
            f"{D1} 09:00:00",
            f"{D2} 03:00:00",
            f"{D2} 05:00:00",
            f"{D2} 12:00:00",
        ],
        "PP-B": [f"{D1} 09:00:00", f"{D2} 09:00:00", f"{D2} 18:30:00"],
        "PP-C": [f"{D1} 09:00:00", f"{D2} 11:40:00"],
        "PP-D": [
            f"{D1} 09:00:00",
            f"{D1} 18:30:00",
            f"{D2} 05:00:00",
            f"{D2} 18:30:00",
        ],
        "PP-E": [
            f"{D1} 21:00:00",
            f"{D1} 23:00:00",
            f"{D1} 23:30:00",
            f"{D2} 06:30:00",
        ],
        "PP-F": [f"{D1} 18:30:00"],
        "PP-G": [f"{D1} 09:00:00"],
        "PP-H": [f"{D1} 09:00:00"],
    }
    for code, times in punches.items():
        for t in times:
            _punch(code, t)


# ---------------------------------------------------------------------------
# setup / cleanup
# ---------------------------------------------------------------------------


def _setup():
    if not frappe.db.exists("Holiday List", HOLIDAY_LIST):
        hl = frappe.get_doc(
            {
                "doctype": "Holiday List",
                "holiday_list_name": HOLIDAY_LIST,
                "from_date": "2026-01-01",
                "to_date": "2026-12-31",
                "holidays": [
                    {
                        "holiday_date": "2026-12-25",
                        "description": "Xmas (out of test range)",
                    }
                ],
            }
        ).insert(ignore_permissions=True)
        hl.submit()

    common = dict(
        holiday_list=HOLIDAY_LIST,
        enable_auto_attendance=1,
        determine_check_in_and_check_out="Alternating entries as IN and OUT during the same shift",
        working_hours_calculation_based_on="First Check-in and Last Check-out",
        begin_check_in_before_shift_start_time=120,
        allow_check_out_after_shift_end_time=120,
        enable_late_entry_marking=1,
        late_entry_grace_period=5,
        process_attendance_after="2026-08-30",
        last_sync_of_checkin="2026-09-04 07:00:00",
    )
    if not frappe.db.exists("Shift Type", DAY_SHIFT):
        frappe.get_doc(
            {
                "doctype": "Shift Type",
                "name": DAY_SHIFT,
                "start_time": "09:00:00",
                "end_time": "18:30:00",
                **common,
            }
        ).insert(ignore_permissions=True)
    if not frappe.db.exists("Shift Type", NIGHT_SHIFT):
        frappe.get_doc(
            {
                "doctype": "Shift Type",
                "name": NIGHT_SHIFT,
                "start_time": "21:00:00",
                "end_time": "07:00:00",
                **common,
            }
        ).insert(ignore_permissions=True)

    company = frappe.db.get_value("Company", {}, "name")
    for code in CODES:
        shift = NIGHT_SHIFT if code == "PP-E" else DAY_SHIFT
        if not frappe.db.exists("Employee", {"attendance_device_id": code}):
            frappe.get_doc(
                {
                    "doctype": "Employee",
                    "employee_name": f"Punch Pairing Test {code}",
                    "company": company,
                    "gender": "Male",
                    "date_of_joining": "2026-08-01",
                    "date_of_birth": "1990-01-01",
                    "status": "Active",
                    "attendance_device_id": code,
                    "default_shift": shift,
                    "holiday_list": HOLIDAY_LIST,
                }
            ).insert(ignore_permissions=True, ignore_mandatory=True)


def _emp(code):
    return frappe.db.get_value("Employee", {"attendance_device_id": code}, "name")


def _cleanup():
    for code in CODES:
        employee = frappe.db.get_value(
            "Employee", {"attendance_device_id": code}, "name"
        )
        if not employee:
            continue
        attendances = frappe.get_all("Attendance", {"employee": employee}, pluck="name")
        todo_names = frappe.get_all(
            "ToDo",
            {"reference_type": "Attendance", "reference_name": ["in", attendances]},
            pluck="name",
        )
        comment_names = frappe.get_all(
            "Comment",
            {"reference_doctype": "Attendance", "reference_name": ["in", attendances]},
            pluck="name",
        )
        for name in todo_names + comment_names:
            try:
                frappe.delete_doc(
                    "ToDo" if name in todo_names else "Comment",
                    name,
                    force=True,
                    ignore_permissions=True,
                )
            except Exception:
                frappe.db.delete("ToDo", {"name": name})
                frappe.db.delete("Comment", {"name": name})
        for name in attendances:
            try:
                doc = frappe.get_doc("Attendance", name)
                if doc.docstatus == 1:
                    doc.cancel()
                frappe.delete_doc(
                    "Attendance", name, force=True, ignore_permissions=True
                )
            except Exception:
                frappe.db.delete("Attendance", {"name": name})
        for name in frappe.get_all(
            "Employee Checkin", {"employee": employee}, pluck="name"
        ):
            try:
                frappe.delete_doc(
                    "Employee Checkin", name, force=True, ignore_permissions=True
                )
            except Exception:
                frappe.db.delete("Employee Checkin", {"name": name})
        for name in frappe.get_all("OT Log", {"employee": employee}, pluck="name"):
            frappe.db.delete("OT Log", {"name": name})
        for name in frappe.get_all(
            "Monthly In-Out Log", {"employee": employee}, pluck="name"
        ):
            try:
                frappe.delete_doc(
                    "Monthly In-Out Log", name, force=True, ignore_permissions=True
                )
            except Exception:
                frappe.db.delete("Monthly In-Out Log", {"name": name})
        try:
            frappe.delete_doc("Employee", employee, force=True, ignore_permissions=True)
        except Exception:
            frappe.db.delete("Employee", {"name": employee})
    for shift in (DAY_SHIFT, NIGHT_SHIFT):
        if frappe.db.exists("Shift Type", shift):
            try:
                frappe.delete_doc(
                    "Shift Type", shift, force=True, ignore_permissions=True
                )
            except Exception:
                frappe.db.delete("Shift Type", {"name": shift})
    if frappe.db.exists("Holiday List", HOLIDAY_LIST):
        try:
            doc = frappe.get_doc("Holiday List", HOLIDAY_LIST)
            if doc.docstatus == 1:
                doc.cancel()
            frappe.delete_doc(
                "Holiday List", HOLIDAY_LIST, force=True, ignore_permissions=True
            )
        except Exception:
            frappe.db.delete("Holiday", {"parent": HOLIDAY_LIST})
            frappe.db.delete("Holiday List", {"name": HOLIDAY_LIST})
    frappe.db.commit()


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _punch(code, when):
    """Insert an Employee Checkin through the full ORM path (engine runs in
    fetch_shift)."""
    doc = frappe.get_doc(
        {
            "doctype": "Employee Checkin",
            "employee": _emp(code),
            "time": when,
            "device_id": "PP-TEST",
        }
    ).insert(ignore_permissions=True)
    frappe.db.commit()
    return doc


def _process(shift):
    doc = frappe.get_cached_doc("Shift Type", shift)
    doc.process_auto_attendance()  # synchronous path, no background enqueue
    frappe.db.commit()


def _flag(employee):
    """Apply the 08:05-style flag/resolution pass to the employee's
    attendances (detect_and_apply = what the scheduled job runs per doc)."""
    from gke_customization.gke_hrms.attendance_flags import detect_and_apply

    for name in frappe.get_all(
        "Attendance", {"employee": employee, "docstatus": 1}, pluck="name"
    ):
        detect_and_apply(frappe.get_doc("Attendance", name))
    frappe.db.commit()


def _att(code, date):
    return frappe.db.get_value(
        "Attendance",
        {"employee": _emp(code), "attendance_date": date},
        ["name", "status", "in_time", "out_time", "working_hours", "punch_error"],
        as_dict=True,
    )


def _check(label, cond, detail=""):
    results.append({"scenario": label, "pass": bool(cond), "detail": detail})
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {label} {detail}")


def _fmt(att):
    if not att or not att.name:
        return "no attendance"
    return (
        f"in={att.in_time} out={att.out_time} wh={att.working_hours} "
        f"status={att.status} err={att.punch_error}"
    )


# ---------------------------------------------------------------------------
# scenarios
# ---------------------------------------------------------------------------


def _scenario_s1():
    _flag(_emp("PP-A"))

    d1, d2 = _att("PP-A", D1), _att("PP-A", D2)
    _check(
        "S1 D1 paired across midnight (9:00 -> 3:00 = 18h)",
        d1
        and get_datetime(d1.out_time) == get_datetime(f"{D2} 03:00:00")
        and abs(d1.working_hours - 18.0) < 0.01,
        _fmt(d1),
    )
    _check(
        "S1 D2 own session (5:00 -> 12:00 = 7h)",
        d2
        and get_datetime(d2.in_time) == get_datetime(f"{D2} 05:00:00")
        and get_datetime(d2.out_time) == get_datetime(f"{D2} 12:00:00")
        and abs(d2.working_hours - 7.0) < 0.01
        and not d2.punch_error,
        _fmt(d2),
    )


def _scenario_s2():
    _flag(_emp("PP-B"))

    d1, d2 = _att("PP-B", D1), _att("PP-B", D2)
    _check(
        "S2 D1 flagged Missing OUT (not silently 0h)",
        d1 and not d1.out_time and d1.punch_error == "Missing OUT",
        _fmt(d1),
    )
    _check(
        "S2 D2 normal (9:00 -> 18:30 = 9.5h)",
        d2 and abs(d2.working_hours - 9.5) < 0.01 and not d2.punch_error,
        _fmt(d2),
    )


def _scenario_s3():
    _flag(_emp("PP-C"))

    d1 = _att("PP-C", D1)
    _check(
        "S3 next-day 11:40 paired with D1 (26.67h)",
        d1
        and get_datetime(d1.out_time) == get_datetime(f"{D2} 11:40:00")
        and abs(d1.working_hours - 26.67) < 0.02
        and not d1.punch_error,
        _fmt(d1),
    )


def _scenario_s4():
    _flag(_emp("PP-D"))

    d2 = _att("PP-D", D2)
    _check(
        "S4 early 5:00 IN captured on correct day (13.5h)",
        d2
        and get_datetime(d2.in_time) == get_datetime(f"{D2} 05:00:00")
        and abs(d2.working_hours - 13.5) < 0.01
        and not d2.punch_error,
        _fmt(d2),
    )


def _scenario_s5():
    _flag(_emp("PP-E"))

    d1 = _att("PP-E", D1)
    _check(
        "S5 night shift first-in 21:00 -> last-out 06:30 (9.5h)",
        d1
        and get_datetime(d1.in_time) == get_datetime(f"{D1} 21:00:00")
        and get_datetime(d1.out_time) == get_datetime(f"{D2} 06:30:00")
        and abs(d1.working_hours - 9.5) < 0.01
        and not d1.punch_error,
        _fmt(d1),
    )


def _scenario_s6():
    _flag(_emp("PP-F"))

    d1 = _att("PP-F", D1)
    _check(
        "S6 single punch day flagged for regularization",
        d1 and d1.punch_error in ("Missing IN", "Missing OUT", "Unpaired punch"),
        _fmt(d1),
    )


def _scenario_s7():
    """HR resolution flow: Missing OUT resolved by HR setting the OUT time
    (the 'Resolve Error Punch' action on the Monthly In-Out Log)."""
    from gke_customization.gke_hrms.ot_resolver import resolve_error_day

    _flag(_emp("PP-G"))  # no approved OT -> flagged

    d1 = _att("PP-G", D1)
    _check(
        "S7a flagged before HR action", d1 and d1.punch_error == "Missing OUT", _fmt(d1)
    )

    res = resolve_error_day(
        _emp("PP-G"), D1, action="set_out", out_time=f"{D1} 21:00:00", remarks="PP test"
    )
    d1 = _att("PP-G", D1)
    _check(
        "S7b HR set_out resolves (OUT 21:00, 12h, flag cleared)",
        res.get("status") == "resolved"
        and d1
        and get_datetime(d1.out_time) == get_datetime(f"{D1} 21:00:00")
        and abs(d1.working_hours - 12.0) < 0.01
        and not d1.punch_error,
        _fmt(d1),
    )


def _scenario_s8():
    """Approved-OT flow: Missing OUT + approved OT Log (2h) -> auto-resolved
    with OUT = shift end + approved OT."""

    att = _att("PP-H", D1)
    ot = frappe.get_doc(
        {
            "doctype": "OT Log",
            "employee": _emp("PP-H"),
            "employee_name": "Punch Pairing Test PP-H",
            "attendance_date": D1,
            "attn_ot_hrs": "02:00:00",
            "allowed_ot": "02:00:00",
            "allow": 1,
            "attendance": att.name if att else None,
        }
    ).insert(ignore_permissions=True)
    frappe.db.commit()

    _flag(_emp("PP-H"))  # resolution order: approved OT first

    d1 = _att("PP-H", D1)
    _check(
        "S8 approved OT auto-resolves Missing OUT (OUT = 18:30 + 2h = 20:30, 11.5h)",
        d1
        and get_datetime(d1.out_time) == get_datetime(f"{D1} 20:30:00")
        and abs(d1.working_hours - 11.5) < 0.01
        and not d1.punch_error,
        _fmt(d1),
    )


def _report():
    total = len(results)
    passed = len([r for r in results if r["pass"]])
    print(f"\n=== PUNCH PAIRING SCENARIOS: {passed}/{total} passed ===")
    for r in results:
        if not r["pass"]:
            print(f"  FAILED: {r['scenario']} -> {r['detail']}")
    frappe.db.commit()
