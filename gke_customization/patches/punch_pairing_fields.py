import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Custom fields for the Session-Based Punch Pairing engine and the
    error-punch ledger on the Monthly In-Out Log."""

    custom_fields = {
        "Shift Type": [
            dict(
                fieldname="early_check_in_horizon",
                label="Early Check-in Horizon (mins)",
                fieldtype="Int",
                insert_after="begin_check_in_before_shift_start_time",
                description=(
                    "Punches up to this many minutes BEFORE shift start are treated as "
                    "an IN for that shift (session pairing). Default 300 (5 hours)."
                ),
            ),
            dict(
                fieldname="max_session_length",
                label="Max Session Length (mins)",
                fieldtype="Int",
                insert_after="allow_check_out_after_shift_end_time",
                description=(
                    "Longest IN -> OUT stretch the engine will pair as one session. "
                    "Default 1680 (28 hours). Beyond this a punch starts a new session "
                    "and the old one is flagged for regularization."
                ),
            ),
            dict(
                fieldname="missing_out_policy",
                label="Missing OUT Policy",
                fieldtype="Select",
                options="Flag\nAuto Close at Shift End",
                default="Flag",
                insert_after="max_session_length",
                description=(
                    "Flag: attendance waits for human regularization (recommended; an "
                    "approved OT Log resolves automatically). Auto Close at Shift End: "
                    "OUT assumed at shift end (no OT)."
                ),
            ),
        ],
        "Employee Checkin": [
            dict(
                fieldname="punch_rule",
                label="Punch Pairing Rule",
                fieldtype="Data",
                read_only=1,
                no_copy=1,
                insert_after="offshift",
                description="Which session-pairing rule classified this punch (R1-R5).",
            ),
        ],
        "Attendance": [
            dict(
                fieldname="punch_error",
                label="Punch Error",
                fieldtype="Select",
                # NOTE: leading blank option — frappe defaults new docs to the
                # FIRST option of a Select field, so it must start empty.
                options="\nMissing IN\nMissing OUT\nUnpaired punch\nReclassification needed",
                read_only=1,
                no_copy=1,
                insert_after="early_exit",
                description="Set automatically when the linked punch sequence is broken (odd punches).",
            ),
        ],
        "Monthly In-Out Log": [
            dict(
                fieldname="punch_error",
                label="Punch Error",
                fieldtype="Select",
                options="\nMissing IN\nMissing OUT\nUnpaired punch\nReclassification needed",
                read_only=1,
                no_copy=1,
                insert_after="attendance",
            ),
            dict(
                fieldname="error_case",
                label="Error Case",
                fieldtype="Select",
                options="\nForgot Check-out\nNext-Day Check-out\nBeyond Shift\nOdd Punch\nOrphan Punch",
                read_only=1,
                no_copy=1,
                insert_after="punch_error",
                description="Business case shown to HR: forgot checkout / next-day checkout / beyond-shift error punch.",
            ),
            dict(
                fieldname="punch_ledger",
                label="Punch Ledger",
                fieldtype="Small Text",
                read_only=1,
                no_copy=1,
                insert_after="error_case",
                description="Exact punch sequence with pairing rules and the shift window.",
            ),
            dict(
                fieldname="ot_check_status",
                label="Approved OT Check",
                fieldtype="Select",
                options="\nNo Approved OT\nApproved OT Matched\nApproved OT Exceeds",
                read_only=1,
                no_copy=1,
                insert_after="punch_ledger",
            ),
            dict(
                fieldname="resolution_status",
                label="Resolution Status",
                fieldtype="Select",
                options="\nPending HR\nAuto-Resolved (Approved OT)\nAuto-Closed (Shift End)\nHR-Approved\nRejected",
                insert_after="ot_check_status",
                no_copy=1,
            ),
            dict(
                fieldname="resolved_by",
                label="Resolved By",
                fieldtype="Data",
                read_only=1,
                no_copy=1,
                insert_after="resolution_status",
            ),
            dict(
                fieldname="resolution_remarks",
                label="Resolution Remarks",
                fieldtype="Small Text",
                insert_after="resolved_by",
            ),
        ],
        "HR Settings": [
            dict(
                fieldname="enable_session_pairing",
                label="Enable Session-Based Punch Pairing",
                fieldtype="Check",
                default="1",
                insert_after="allow_geolocation_tracking",
                description=(
                    "ON: punches are classified via the session engine (handles "
                    "next-day checkouts, early check-ins, forgotten punches). "
                    "OFF: legacy window-containment behaviour."
                ),
            ),
            dict(
                fieldname="session_pairing_parallel_run",
                label="Session Pairing Parallel Run (log only)",
                fieldtype="Check",
                default="0",
                insert_after="enable_session_pairing",
                description=(
                    "ON: legacy behaviour is kept and engine decisions are only "
                    "logged (safe rollout mode)."
                ),
            ),
        ],
    }

    create_custom_fields(custom_fields, ignore_validate=True, update=True)

    # enable by default on sites where the fields were just created
    for fieldname, value in [
        ("enable_session_pairing", 1),
        ("session_pairing_parallel_run", 0),
    ]:
        existing = frappe.db.sql(
            "SELECT `value` FROM `tabSingles` WHERE `doctype`='HR Settings' AND `field`=%s",
            (fieldname,),
        )
        if not existing:
            frappe.db.sql(
                "INSERT INTO `tabSingles` (`doctype`, `field`, `value`) VALUES ('HR Settings', %s, %s)",
                (fieldname, str(value)),
            )

    # scrub values polluted by an earlier first-option default (if any)
    frappe.db.sql(
        "UPDATE `tabAttendance` SET `punch_error` = '' WHERE `punch_error` = 'Missing IN'"
    )
    frappe.db.sql(
        "UPDATE `tabMonthly In-Out Log` SET `punch_error` = '' WHERE `punch_error` = 'Missing IN'"
    )

    frappe.db.commit()
