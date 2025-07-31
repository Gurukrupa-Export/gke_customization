# Copyright (c) 2025, Gurukrupa Export and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class OrderCriteria(Document):
	pass

from datetime import datetime, timedelta, time
import frappe
from frappe.utils import get_datetime

def skip_sunday(dt):
    while dt.weekday() == 6:  # Sunday
        dt += timedelta(days=1)
    return dt

def parse_time_or_duration(val):
    if isinstance(val, time):
        return val
    elif isinstance(val, timedelta):
        return (datetime.min + val).time()
    elif isinstance(val, str):
        try:
            h, m, s = [int(x) for x in val.strip().split(".")]
            return time(h, m, s)
        except:
            pass
    return time(0, 0, 0)

def add_working_hours(start_dt, hours_to_add, shift_start, shift_end):
    remaining = timedelta(hours=hours_to_add)
    current_dt = start_dt

    shift_start_dt = lambda d: datetime.combine(d, shift_start)
    shift_end_dt = lambda d: datetime.combine(d, shift_end)

    while remaining.total_seconds() > 0:
        current_dt = skip_sunday(current_dt)
        current_date = current_dt.date()

        work_start = shift_start_dt(current_date)
        work_end = shift_end_dt(current_date)

        if current_dt < work_start:
            current_dt = work_start

        if current_dt >= work_end:
            current_dt = datetime.combine(current_date + timedelta(days=1), time(0, 0))
            continue

        time_left_today = work_end - current_dt
        if remaining <= time_left_today:
            current_dt += remaining
            remaining = timedelta(0)
        else:
            remaining -= time_left_today
            current_dt = datetime.combine(current_date + timedelta(days=1), time(0, 0))

    return current_dt

@frappe.whitelist()
def get_order_criteria(workflow_type, order_date_str, docname=None):
    order_criteria = frappe.get_single("Order Criteria")
    criteria_rows = order_criteria.get("order")
    enabled_criteria = next((row for row in criteria_rows if not row.disable), None)

    if not enabled_criteria:
        frappe.throw("No enabled Order Criteria found.")

    try:
        order_datetime = get_datetime(order_date_str)
    except Exception:
        frappe.throw("Invalid order date format.")

    result = {}

    # CAD time parsing
    cad_time_raw = enabled_criteria.cad_submission_time
    cad_time = parse_time_or_duration(cad_time_raw)
    cad_datetime = datetime.combine(order_datetime.date(), cad_time)
    cad_datetime = skip_sunday(cad_datetime)
    result["update_cad_delivery_date"] = cad_datetime
    
    if workflow_type == "CAD":
        cad_days = int(enabled_criteria.cad_approval_day or 0)
        cad_delivery_datetime = datetime.combine(order_datetime.date() + timedelta(days=cad_days), cad_time)
        cad_delivery_datetime = skip_sunday(cad_delivery_datetime)
        frappe.throw(f"{cad_delivery_datetime}")
        ibm_time = parse_time_or_duration(enabled_criteria.cad_appoval_timefrom_ibm_team)
        ibm_timedelta = timedelta(hours=ibm_time.hour, minutes=ibm_time.minute, seconds=ibm_time.second)

        shift_rows = order_criteria.get("department_shift") or []
        enabled_shift = next((s for s in shift_rows if not s.disable), None)
        if not enabled_shift:
            frappe.throw("No enabled Department Shift found.")

        shift_start = parse_time_or_duration(enabled_shift.shift_start_time)
        shift_end = parse_time_or_duration(enabled_shift.shift_end_time)

        # Tentative IBM delivery time
        tentative_ibm_datetime = cad_delivery_datetime + ibm_timedelta

        shift_end_datetime = datetime.combine(cad_delivery_datetime.date(), shift_end)

        if tentative_ibm_datetime > shift_end_datetime:
            # Compute extra time to add next day from shift_start
            exceeded_time = tentative_ibm_datetime - shift_end_datetime
            next_day_start = datetime.combine(cad_delivery_datetime.date() + timedelta(days=1), shift_start)
            next_day_start = skip_sunday(next_day_start)
            ibm_delivery_datetime = next_day_start + exceeded_time
        else:
            ibm_delivery_datetime = tentative_ibm_datetime

        ibm_delivery_datetime = skip_sunday(ibm_delivery_datetime)

        result["cad_delivery_date"] = cad_delivery_datetime
        result["ibm_delivery_date"] = ibm_delivery_datetime

    elif workflow_type == "BOM":
        ibm_time = parse_time_or_duration(enabled_criteria.cad_appoval_timefrom_ibm_team)
        hours_to_add = ibm_time.hour + (ibm_time.minute / 60) + (ibm_time.second / 3600)

        shift_rows = order_criteria.get("department_shift") or []
        enabled_shift = next((s for s in shift_rows if not s.disable), None)

        if not enabled_shift:
            frappe.throw("No enabled Department Shift found.")

        shift_start = parse_time_or_duration(enabled_shift.shift_start_time)
        shift_end = parse_time_or_duration(enabled_shift.shift_end_time)

        ibm_delivery_datetime = add_working_hours(order_datetime, hours_to_add, shift_start, shift_end)
        ibm_delivery_datetime = skip_sunday(ibm_delivery_datetime)

        result["ibm_delivery_date"] = ibm_delivery_datetime

    return result


@frappe.whitelist()
def apply_cad_time_on_selected_date(selected_date_str):
    from datetime import datetime, time, timedelta
    from frappe.utils import getdate

    # Fetch enabled order criteria row
    order_criteria = frappe.get_single("Order Criteria")
    criteria_rows = order_criteria.get("order")
    enabled_criteria = next((row for row in criteria_rows if not row.disable), None)

    if not enabled_criteria or not enabled_criteria.cad_submission_time:
        frappe.throw("CAD Submission Time not found in enabled Order Criteria row.")

    cad_time_raw = enabled_criteria.cad_submission_time

    # Convert to time object
    if isinstance(cad_time_raw, time):
        cad_time = cad_time_raw
    elif isinstance(cad_time_raw, timedelta):
        cad_time = (datetime.min + cad_time_raw).time()
    elif isinstance(cad_time_raw, str):
        try:
            h, m, s = [int(x) for x in cad_time_raw.strip().split(".")]
            cad_time = time(h, m, s)
        except:
            frappe.throw("Invalid CAD Submission Time format.")
    else:
        cad_time = time(0, 0, 0)

    # Combine selected date and cad time
    try:
        selected_date = getdate(selected_date_str)
    except Exception:
        frappe.throw("Invalid date format provided.")

    update_cad_datetime = datetime.combine(selected_date, cad_time)

    # Add cad_approval_timefrom_ibm_team to above datetime
    ibm_time_raw = enabled_criteria.cad_appoval_timefrom_ibm_team
    if not ibm_time_raw:
        frappe.throw("CAD Approval Time from IBM Team not set in Order Criteria.")

    # Convert ibm_time_raw to timedelta
    if isinstance(ibm_time_raw, time):
        ibm_delta = timedelta(hours=ibm_time_raw.hour, minutes=ibm_time_raw.minute, seconds=ibm_time_raw.second)
    elif isinstance(ibm_time_raw, timedelta):
        ibm_delta = ibm_time_raw
    elif isinstance(ibm_time_raw, str):
        try:
            h, m, s = [int(x) for x in ibm_time_raw.strip().split(".")]
            ibm_delta = timedelta(hours=h, minutes=m, seconds=s)
        except:
            frappe.throw("Invalid IBM Approval Time format.")
    else:
        ibm_delta = timedelta(0)

    ibm_delivery_datetime = update_cad_datetime + ibm_delta

    return {
        "update_cad_delivery_date": update_cad_datetime,
        "ibm_delivery_date": ibm_delivery_datetime
    }
