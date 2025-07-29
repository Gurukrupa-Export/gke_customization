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
    if dt.weekday() == 6:  # Sunday
        return dt + timedelta(days=1)
    return dt

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

    # Parse cad_submission_time
    cad_time_raw = enabled_criteria.cad_submission_time
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

    # Set update_cad_delivery_date: order_date + cad_submission_time
    cad_datetime = datetime.combine(order_datetime.date(), cad_time)
    cad_datetime = skip_sunday(cad_datetime)
    result["update_cad_delivery_date"] = cad_datetime

    if workflow_type == "CAD":
        cad_days = int(enabled_criteria.cad_approval_day or 0)
        ibm_time_raw = enabled_criteria.cad_appoval_timefrom_ibm_team

        # Convert ibm_time_raw to timedelta
        if isinstance(ibm_time_raw, time):
            ibm_timedelta = timedelta(hours=ibm_time_raw.hour, minutes=ibm_time_raw.minute, seconds=ibm_time_raw.second)
        elif isinstance(ibm_time_raw, timedelta):
            ibm_timedelta = ibm_time_raw
        elif isinstance(ibm_time_raw, str):
            try:
                h, m, s = [int(x) for x in ibm_time_raw.strip().split(".")]
                ibm_timedelta = timedelta(hours=h, minutes=m, seconds=s)
            except:
                frappe.throw("Invalid IBM Approval Time format.")
        else:
            ibm_timedelta = timedelta()

        cad_delivery_datetime = datetime.combine(order_datetime.date() + timedelta(days=cad_days), cad_time)
        cad_delivery_datetime = skip_sunday(cad_delivery_datetime)

        ibm_delivery_datetime = cad_delivery_datetime + ibm_timedelta
        ibm_delivery_datetime = skip_sunday(ibm_delivery_datetime)

        result["cad_delivery_date"] = cad_delivery_datetime
        result["ibm_delivery_date"] = ibm_delivery_datetime

    elif workflow_type == "BOM":
        ibm_time_raw = enabled_criteria.cad_appoval_timefrom_ibm_team
        if isinstance(ibm_time_raw, time):
            ibm_timedelta = timedelta(hours=ibm_time_raw.hour, minutes=ibm_time_raw.minute, seconds=ibm_time_raw.second)
        elif isinstance(ibm_time_raw, timedelta):
            ibm_timedelta = ibm_time_raw
        elif isinstance(ibm_time_raw, str):
            try:
                h, m, s = [int(x) for x in ibm_time_raw.strip().split(".")]
                ibm_timedelta = timedelta(hours=h, minutes=m, seconds=s)
            except:
                frappe.throw("Invalid IBM Approval Time format.")
        else:
            ibm_timedelta = timedelta()

        dept_shift = next((row for row in order_criteria.get("department_shift") if not row.disable), None)
        if not dept_shift:
            frappe.throw("No enabled Department Shift found.")

        shift_start = dept_shift.shift_start_time
        shift_end = dept_shift.shift_end_time

        if not shift_start or not shift_end:
            frappe.throw("Shift Start or End Time is missing.")

        if isinstance(shift_start, timedelta):
            shift_start = (datetime.min + shift_start).time()
        if isinstance(shift_end, timedelta):
            shift_end = (datetime.min + shift_end).time()

        order_time = order_datetime.time()
        order_date = order_datetime.date()

        shift_start_dt = datetime.combine(order_date, shift_start)
        shift_end_dt = datetime.combine(order_date, shift_end)

        if order_time >= shift_end:
            ibm_delivery_datetime = datetime.combine(order_date + timedelta(days=1), shift_start) + ibm_timedelta
        else:
            remaining_today = shift_end_dt - order_datetime
            if remaining_today >= ibm_timedelta:
                ibm_delivery_datetime = order_datetime + ibm_timedelta
            else:
                remaining_next_day = ibm_timedelta - remaining_today
                ibm_delivery_datetime = datetime.combine(order_date + timedelta(days=1), shift_start) + remaining_next_day

        ibm_delivery_datetime = skip_sunday(ibm_delivery_datetime)
        result["ibm_delivery_date"] = ibm_delivery_datetime

    return result

