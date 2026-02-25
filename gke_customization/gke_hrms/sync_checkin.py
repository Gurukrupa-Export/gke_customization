import frappe
from frappe import _
from frappe.utils import cint, get_datetime, getdate
from datetime import datetime, timedelta
import requests

from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift_timings


def _log_error(title, message):
    debug = False  # Set to True to print errors instead of logging
    if debug:
        print(f"{title} -- {message}")
    else:
        frappe.log_error(title=title, message=message)

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
@frappe.whitelist()
def sync_biometric_checkins():
    """Fetch biometric check-in logs from the Biomatrix API and sync them
    into the Employee Checkin DocType.

    * Shift-aware Log Type (IN / OUT) — works for day *and* night shifts
    * Duplicate prevention via (employee, timestamp) uniqueness
    * Time-threshold filtering to ignore rapid successive punches
    * Comprehensive error logging

    from gke_customization.gke_hrms.sync_checkin import sync_biometric_checkins

    """
    settings = frappe.get_cached_doc("Biometric Settings", "Biometric Settings")

    from_date, to_date = _resolve_date_range(settings)
    formatted_from = from_date.strftime("%d%m%Y")
    formatted_to = to_date.strftime("%d%m%Y")

    # Pre-fetch existing checkins for fast duplicate lookup
    existing = _build_existing_checkins_set(from_date, to_date)

    # Track last punch per employee for time-threshold checks (in-memory)
    last_punch_map = _build_last_punch_map(from_date, to_date)

    time_threshold = float(settings.time_threshold or 0)

    # ── Fetch from API ────────────────────────────────────────────────
    url = f"{settings.biometric_api};date-range={formatted_from}-{formatted_to}"
    api_key = settings.biometric_api_key

    headers = {
        "Authorization": api_key,
    }

    try:
        response = requests.get(url, headers=headers, timeout=60)
    except requests.exceptions.RequestException as exc:
        _log_error(
            title="Biometric Sync — API Request Failed",
            message=frappe.get_traceback(),
        )
        return {"status": "error", "message": str(exc)}

    if response.status_code != 200:
        _log_error(
            title=f"Biometric Sync — HTTP {response.status_code}",
            message=response.text[:2000],
        )
        return {"status": "error", "message": f"HTTP {response.status_code}"}

    try:
        data = response.json().get("event-ta", [])
    except Exception:
        _log_error(
            title="Biometric Sync — Invalid JSON",
            message=response.text[:2000],
        )
        return {"status": "error", "message": "Invalid JSON response"}

    # ── Sort chronologically (critical for correct IN/OUT toggle) ──────
    data = sorted(data, key=lambda r: _parse_datetime_safe(r.get("edatetime_e", "")))

    created = 0
    skipped = 0
    errors = 0

    for log in data:
        try:
            # if not log.get("userid", "") == "71372":
            # if log.get("userid", "") not in ["4445", "2714", "4220", "2305"]:
            # if log.get("userid", "") not in ["50007", "50014", "67196",]:
                # continue
            result = _process_single_log(log, existing, last_punch_map, time_threshold)
            if result == "created":
                created += 1
            else:
                skipped += 1
        except Exception:
            errors += 1
            _log_error(
                title=f"Biometric Sync — Error processing log {log.get('indexno', '?')}",
                message=frappe.get_traceback(),
            )

    frappe.db.commit()

    # summary = f"Sync complete: {created} created, {skipped} skipped, {errors} errors"
    return {"status": "ok", "created": created, "skipped": skipped, "errors": errors}


# ---------------------------------------------------------------------------
# Per-record processing
# ---------------------------------------------------------------------------
def _process_single_log(log, existing, last_punch_map, time_threshold):
    """Process a single biometric log entry.

    Returns:
        "created" if an Employee Checkin was inserted, "skipped" otherwise.
    """
    # ── Parse datetime ────────────────────────────────────────────────
    raw_dt = log.get("edatetime_e", "")
    log_dt = _parse_datetime(raw_dt)
    if log_dt is None:
        _log_error(
            title="Biometric Sync — Invalid datetime",
            message=f"Could not parse '{raw_dt}' for userid={log.get('userid')} indexno={log.get('indexno')}",
        )
        return "skipped"

    log_dt_str = log_dt.strftime("%Y-%m-%d %H:%M:%S")

    # ── Resolve employee ──────────────────────────────────────────────
    userid = log.get("userid", "")
    employee = frappe.db.get_value(
        "Employee",
        {"attendance_device_id": userid, "status": "Active"},
        "name",
    )

    if not employee:
        _log_error(
            title="Biometric Sync — Employee not found",
            message=f"No active employee with attendance_device_id='{userid}' (username={log.get('username')})",
        )
        return "skipped"

    # ── Duplicate check ───────────────────────────────────────────────
    checkin_key = f"{employee}/{log_dt.strftime('%Y-%m-%d %H:%M')}"
    if checkin_key in existing:
        return "skipped"

    # ── Time threshold check ──────────────────────────────────────────
    if time_threshold > 0:
        last_dt = last_punch_map.get(employee)
        if last_dt:
            diff_seconds = (log_dt - last_dt).total_seconds()
            if 0 < diff_seconds <= time_threshold:
                return "skipped"

    # ── Determine Log Type (shift-aware) ──────────────────────────────
    log_type = _determine_log_type(employee, log_dt)

    # ── Create Employee Checkin ───────────────────────────────────────
    device_name = log.get("device_name", "")
    unique_id = log.get("indexno", "")

    checkin = frappe.get_doc({
        "doctype": "Employee Checkin",
        "employee": employee,
        "time": log_dt_str,
        "log_type": log_type,
        "device_id": device_name,
        "source": "Biometric",
        "custom_unique_id": unique_id,
    })
    checkin.insert(ignore_permissions=True)

    # Update tracking structures so subsequent logs in the same batch
    # can reference this newly-created checkin.
    existing.add(checkin_key)
    last_punch_map[employee] = log_dt

    return "created"


# ---------------------------------------------------------------------------
# Log Type determination (shift-aware, supports day + night shifts)
# ---------------------------------------------------------------------------
def _determine_log_type(employee, log_dt):
    """Decide whether a punch is IN or OUT based on the employee's shift
    assignment and prior checkins within the same shift window.

    Handles:
      ✅ Day shifts      (e.g. 09:00 – 18:00)
      ✅ Night shifts     (e.g. 21:00 – 06:00)
      ✅ After-midnight punches for previous-day night shifts
      ✅ Multiple punches — toggles IN→OUT→IN→OUT
      ✅ Missing OUT — next shift window starts fresh with IN
      ✅ Late entry / early exit within grace window
    """
    try:
        _prev_shift, curr_shift, _next_shift = get_employee_shift_timings(
            employee, get_datetime(log_dt), True
        )
    except Exception:
        # If shift lookup fails, default to IN
        _log_error(
            title="Biometric Sync — Shift lookup failed",
            message=f"employee={employee}, time={log_dt}\n{frappe.get_traceback()}",
        )
        return "IN"

    if not curr_shift:
        return "IN"

    # Check if the punch falls within the shift's actual window
    actual_start = curr_shift.get("actual_start")
    actual_end = curr_shift.get("actual_end")

    if actual_start and actual_end:
        punch_dt = get_datetime(log_dt)
        if not (actual_start <= punch_dt <= actual_end):
            # Outside the shift window — treat as a standalone IN
            return "IN"

    # ── Query last checkin within this shift's actual window ─────────
    # Use actual_start/actual_end (which include the grace period) so that
    # early-arrival punches (e.g. 20:59 for a 21:00 shift) are included
    # in the lookup.  This is critical for correct IN/OUT toggling.
    query_start = actual_start or curr_shift.get("start_datetime")
    query_end = actual_end or curr_shift.get("end_datetime")

    if query_start and query_end:
        last_log = frappe.db.sql(
            """
            SELECT log_type
            FROM `tabEmployee Checkin`
            WHERE employee = %s
              AND time >= %s
              AND time <= %s
              AND time < %s
            ORDER BY time DESC
            LIMIT 1
            """,
            (employee, query_start, query_end, log_dt),
            as_dict=True,
        )
    else:
        # Fallback: look at same calendar day
        log_date_str = log_dt.strftime("%Y-%m-%d")
        last_log = frappe.db.sql(
            """
            SELECT log_type
            FROM `tabEmployee Checkin`
            WHERE employee = %s
              AND DATE(time) = %s
              AND time < %s
            ORDER BY time DESC
            LIMIT 1
            """,
            (employee, log_date_str, log_dt),
            as_dict=True,
        )

    if not last_log:
        return "IN"

    # Toggle: IN→OUT, OUT→IN
    return "OUT" if last_log[0]["log_type"] == "IN" else "IN"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _resolve_date_range(settings):
    """Return (from_date, to_date) as `datetime.date` objects."""
    today = datetime.now().date()

    if cint(settings.manual):
        from_date = settings.from_date if isinstance(settings.from_date, datetime) else \
            datetime.strptime(str(settings.from_date), "%Y-%m-%d").date() if settings.from_date else today
        to_date = settings.to_date if isinstance(settings.to_date, datetime) else \
            datetime.strptime(str(settings.to_date), "%Y-%m-%d").date() if settings.to_date else today
        # frappe Date fields may already be date objects
        if hasattr(from_date, "date"):
            from_date = from_date.date()
        if hasattr(to_date, "date"):
            to_date = to_date.date()
    else:
        day_threshold = cint(settings.day_threshold) or 1
        from_date = today - timedelta(days=day_threshold)
        to_date = today

    # from_date = getdate("2026-01-01")
    # to_date = getdate("2026-01-31")

    return from_date, to_date


def _build_existing_checkins_set(from_date, to_date):
    """Return a set of 'employee/YYYY-MM-DD HH:MM' strings for all
    Employee Checkins in the date range — used for O(1) duplicate checks."""
    rows = frappe.db.sql(
        """
        SELECT employee, time
        FROM `tabEmployee Checkin`
        WHERE DATE(time) BETWEEN %s AND %s
        """,
        (from_date, to_date),
        as_dict=True,
    )
    result = set()
    for r in rows:
        t = r["time"]
        if isinstance(t, str):
            t = datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
        result.add(f"{r['employee']}/{t.strftime('%Y-%m-%d %H:%M')}")
    return result


def _build_last_punch_map(from_date, to_date):
    """Return a dict { employee: last_punch_datetime } for time-threshold
    filtering.  Only considers the latest punch per employee in the range."""
    rows = frappe.db.sql(
        """
        SELECT employee, MAX(time) as last_time
        FROM `tabEmployee Checkin`
        WHERE DATE(time) BETWEEN %s AND %s
        GROUP BY employee
        """,
        (from_date, to_date),
        as_dict=True,
    )
    result = {}
    for r in rows:
        t = r["last_time"]
        if isinstance(t, str):
            t = datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
        result[r["employee"]] = t
    return result


def _parse_datetime(raw):
    """Parse 'DD/MM/YYYY HH:MM' → datetime, or return None."""
    if not raw:
        return None
    try:
        return datetime.strptime(raw.strip(), "%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return None


def _parse_datetime_safe(raw):
    """Parse for sorting — returns a very old date on failure so bad
    records don't crash the sort."""
    dt = _parse_datetime(raw)
    return dt if dt else datetime(1970, 1, 1)