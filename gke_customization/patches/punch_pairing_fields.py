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
            # NOTE: 'source' and 'custom_unique_id' are referenced by the sync
            # jobs and the Monthly In-Out Log report (OD detection), but the
            # columns may be missing after app resets — recreate if absent.
            dict(
                fieldname="source",
                label="Source",
                fieldtype="Select",
                options="\nEmployee Checkin\nManual Punch\nBiometric\nOutdoor Duty\nWork From Home",
                insert_after="device_id",
                description="Origin of the punch (biometric sync, manual punch, attendance request...).",
            ),
            dict(
                fieldname="custom_unique_id",
                label="Biometric Punch ID",
                fieldtype="Data",
                read_only=1,
                no_copy=1,
                insert_after="source",
                description="Device indexno of the biometric event (dedupe key for syncs).",
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
        ],
    }

    create_custom_fields(custom_fields, ignore_validate=True, update=True)

    # enable by default on sites where the fields were just created
    for fieldname, value in [
        ("enable_session_pairing", 1),
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

    frappe.db.commit()
