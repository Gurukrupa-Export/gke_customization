# Copyright (c) 2026, Gurukrupa Export
"""
Punch-error detection on Attendance.

Case 2 (odd punches / forgotten IN or OUT): the flagger inspects the
checkins linked to a submitted attendance. When the IN/OUT sequence is
not a clean alternating chain starting with IN and ending with OUT,
the attendance is flagged (`punch_error`).

Resolution flow:
  1. Approved OT Log exists for the day -> auto-resolve the missing OUT.
     (Retried on every flag run: OT Logs are often approved 1-2 days later.)
  2. Otherwise -> flag the attendance and create an HR ToDo for
     regularization through the Monthly In-Out Log or Manual Punch.

Timing note: hrms links checkins to the attendance AFTER submitting it
(query-builder UPDATE, no doc events), so the on_submit hook cannot see the
punches. It therefore enqueues the check to run after the transaction commits.
"""

import frappe
from frappe.utils import add_days, now_datetime

from gke_customization.gke_hrms.punch_pairing import _get_hr_user
from gke_customization.gke_hrms.ot_resolver import ensure_mil, try_resolve_with_approved_ot, MIL_DOCTYPE, RES_REJECTED
from gke_customization.gke_hrms.utils import _log_exc

MISSING_OUT = "Missing OUT"
MISSING_IN = "Missing IN"
UNPAIRED = "Unpaired punch"


def flag_attendance_punch_errors(doc, method=None):
    """Attendance on_submit hook.

    Auto-attendance links checkins AFTER submit, so re-check once the
    surrounding transaction has committed (checkins linked by then).
    flag_recent_attendances() remains the safety net.
    """
    if frappe.flags.in_punch_pairing_reconcile:
        return

    if doc.get("punch_error") or not doc.get("in_time"):
        return  # already flagged, or a leave/absent row with no punches

    frappe.enqueue(
        "gke_customization.gke_hrms.attendance_flags.flag_attendance_by_name",
        attendance=doc.name,
        queue="short",
        enqueue_after_commit=True,
        job_id=f"flag_att_{doc.name}",
        deduplicate=True,
    )


def flag_attendance_by_name(attendance):
    """Background job: detect the punch error, then refresh the MIL card."""
    doc = frappe.get_doc("Attendance", attendance)
    if doc.docstatus != 1:  # cancelled / draft since enqueue
        return
    if doc.get("punch_error"):  # already flagged
        return

    try:
        result = detect_and_apply(doc)  # flagged path already refreshes the card
        if not result:
            _refresh_mil_card(doc)  # clean day: card ledger was built before linking
    except Exception:
        _log_exc(f"punch flag failed: {attendance}")
    frappe.db.commit()


def detect_and_apply(doc) -> str | None:
    """Detect a broken punch chain and resolve it using approved OT.

    If approved OT cannot resolve the missing OUT, the attendance is
    flagged for HR regularization.
    """
    checkins = frappe.get_all(
        "Employee Checkin",
        filters={"attendance": doc.name},
        pluck="log_type",
        order_by="time asc",
    )
    if not checkins:
        return None

    error = _detect_error(checkins)
    if not error:
        return None

    # Approved OT is the only automatic resolution.
    if error == MISSING_OUT:
        try:
            result = try_resolve_with_approved_ot(doc, error_hint=error)
            if result.get("status") == "resolved":
                return "resolved-via-approved-ot"
        except Exception:
            _log_exc("OT resolution failed")

    # No approved OT or OT resolution failed.
    # Send the attendance to HR for regularization.
    doc.db_set("punch_error", error)
    _create_todo(doc, error)

    try:
        

        ensure_mil(doc.employee, doc.attendance_date)
    except Exception:
        _log_exc("MIL auto-creation failed")

    # The card usually exists already (created on attendance submit, before the
    # punches were linked). Repopulate it now that the error is on the attendance.
    _refresh_mil_card(doc)

    return error


def flag_recent_attendances(days: int = 3):
    """Flag recent attendances whose linked punch sequence is broken.

    This is the authoritative pass because auto-attendance links checkins
    to Attendance after submission.
    """
    from_date = add_days(now_datetime().date(), -days)

    names = frappe.get_all(
        "Attendance",
        filters={
            "attendance_date": [">=", from_date],
            "docstatus": 1,
        },
        pluck="name",
    )

    flagged = 0

    for name in names:
        doc = frappe.get_doc("Attendance", name)

        # Keep the existing Monthly In-Out Log card synchronized.
        _refresh_mil_card(doc)

        if doc.get("punch_error"):
            # Already flagged: OT may have been approved since. Retry.
            _retry_ot_resolution(doc)
            continue

        try:
            result = detect_and_apply(doc)

            if result and result != "resolved-via-approved-ot":
                flagged += 1

        except Exception:
            _log_exc(f"punch flag failed: {name}")

    frappe.db.commit()

    return {
        "checked": len(names),
        "flagged": flagged,
    }


def _retry_ot_resolution(doc):
    """OT Logs are often approved 1-2 days after the day itself: give an
    already-flagged Missing OUT another chance to auto-resolve.

    An explicit HR rejection is never overridden.
    """
    if doc.get("punch_error") != MISSING_OUT:
        return

    try:
        status = frappe.db.get_value(
            MIL_DOCTYPE,
            {
                "employee": doc.employee,
                "attendance_date": doc.attendance_date,
                "docstatus": ["<", 2],
            },
            "resolution_status",
        )
        if status == RES_REJECTED:
            return

        # on success: OUT checkin created, ToDo closed, card updated
        try_resolve_with_approved_ot(doc)
    except Exception:
        _log_exc(f"OT retry failed: {doc.name}")


def _refresh_mil_card(attendance_doc):
    """Refresh the employee-date Monthly In-Out Log card if it exists."""
    try:
        mil_name = frappe.db.exists(
            "Monthly In-Out Log",
            {
                "employee": attendance_doc.employee,
                "attendance_date": attendance_doc.attendance_date,
                "docstatus": ["<", 2],
            },
        )

        if mil_name:
            frappe.get_doc(
                "Monthly In-Out Log",
                mil_name,
            ).populate_from_attendance()

    except Exception:
        _log_exc(
            f"MIL refresh failed for "
            f"{attendance_doc.employee}/{attendance_doc.attendance_date}"
        )


def _detect_error(checkins) -> str | None:
    # Unknown direction.
    if any(t not in ("IN", "OUT") for t in checkins):
        return UNPAIRED

    # Clean chain: IN, OUT, IN, OUT, ...
    n = len(checkins)
    expected = ["IN", "OUT"] * (n // 2)
    clean = n % 2 == 0 and checkins == expected

    if clean:
        return None

    if checkins[0] == "OUT":
        return MISSING_IN

    if checkins[0] == "IN":
        return MISSING_OUT

    return UNPAIRED


def _create_todo(doc, error):
    """Create one open HR ToDo for the attendance error."""
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