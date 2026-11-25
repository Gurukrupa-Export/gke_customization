# # Copyright (c) 2026, Gurukrupa Export and contributors
# # For license information, please see license.txt

from bisect import bisect_left, bisect_right
from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import CustomFunction
from frappe.query_builder.functions import Concat, Count, Date, IfNull, Min, Sum
from frappe.utils import (
    add_days,
    cint,
    flt,
    format_time,
    formatdate,
    get_datetime,
    get_time,
    getdate,
)
from hrms.hr.doctype.shift_assignment.shift_assignment import (
    get_employee_shift_timings,
    get_exact_shift,
    get_shift_timings,
)

try:
    from hrms.hr.doctype.shift_assignment.shift_assignment import (
        _adjust_overlapping_shifts,
        _is_shift_outside_assignment_period,
    )

    HRMS_SHIFT_HELPERS_AVAILABLE = True
except ImportError:
    # Private HRMS helpers: when missing, shift windows fall back to get_employee_shift_timings.
    HRMS_SHIFT_HELPERS_AVAILABLE = False

from gke_customization.gke_hrms.ot_resolver import (
    get_error_context,
    get_monthly_in_out_log_attendance,
    resolve_error_day,
)
from gke_customization.gke_hrms.utils import get_employee_shift

# ============================================================
# CONSTANTS
# ============================================================

STATUS = {
    "Absent": "Absent",
    "Present": "Present",
    "Half Day": "Half Day",
    "On Leave": "On Leave",
    "Leave Without Pay": "On Leave",
    "Sick Leave": "On Leave",
    "Casual Leave": "On Leave",
    "Marriage Leave": "On Leave",
    "Work From Home": "Work From Home",
}

REVERSE_STATUS = {v: k for k, v in STATUS.items()}

TOTAL_STATUS_ROWS = [
    "Total Hours",
    "Total Days",
    "Refund Min(P.Hrs)",
    "Penalty in Days",
    "Net Hrs",
    "Net Days",
    "Net Hrs w/o OT",
    "Net Days w/o OT",
]


# ============================================================
# DOCUMENT CONTROLLER
# ============================================================


class MonthlyInOutLog(Document):
    def validate(self):
        """
        By default populate on validate if employee + attendance_date present.
        Change this behavior if you want manual button-based population instead.
        """
        self.company = frappe.db.get_value("Employee", self.employee, "company")
        self.shit_type = get_employee_shift(self.employee, self.attendance_date)
        self.shift_hours = frappe.db.get_value(
            "Shift Type", self.shit_type, "shift_hours"
        )

        if not self.validate_duplicate_entry():
            self.populate_from_attendance()
            self.flags.attendance_populated = True
            self.flags.populated_attendance = self.attendance

    def on_submit(self):
        populated_in_validate = (
            self.flags.attendance_populated
            and self.flags.populated_attendance == self.attendance
        )
        if not populated_in_validate:
            self.populate_from_attendance()

        if not self.attendance:
            atten_doc = frappe.db.get_value(
                "Attendance",
                {
                    "employee": self.employee,
                    "attendance_date": self.attendance_date,
                    "docstatus": 1,
                },
                "name",
            )
            if atten_doc:
                self.db_set("attendance", atten_doc)

    def validate_duplicate_entry(self):
        """
        Prevent duplicate Monthly In-Out Log for same employee & date
        """

        if not self.employee or not self.attendance_date:
            return

        login_date = getdate(self.attendance_date)

        duplicate = frappe.db.exists(
            "Monthly In-Out Log",
            {
                "employee": self.employee,
                "attendance_date": login_date,
                "docstatus": ["in", [0, 1]],
                "name": ["!=", self.name],
            },
        )

        if duplicate:
            return True

    def on_cancel(self):
        self.db_set("resolution_status", "Cancelled", update_modified=False)

    def _persist(self, updates):
        """Write values to the database without bumping modified, so submitted cards can be refreshed."""
        if not self.is_new():
            frappe.db.set_value(self.doctype, self.name, updates, update_modified=False)
        for fieldname, value in updates.items():
            self.set(fieldname, value)

    def _hours_from(self, attendance, attendance_details=None):
        """Return the hours fields for this card, derived from the attendance.

        `attendance_details` is the precomputed result of `get_attendance_details_by_date`
        for this card. When it is passed, the values always come from its record, even
        when the attendance has no working hours. When it is None, the details are
        fetched here.
        """
        if attendance_details is None:
            if not attendance.working_hours:
                return {
                    "spent_hrs": 0,
                    "net_wrk_hrs": timedelta(0),
                    "p_out_hrs": timedelta(0),
                    "ot_hrs": timedelta(0),
                    "in_time": timedelta(0),
                    "out_time": timedelta(0),
                    "early_hrs": timedelta(0),
                    "late_hrs": timedelta(0),
                    "late": 0,
                    "status": self.status or attendance.status,
                }

            attendance_details = get_attendance_details_by_date(
                self.company, self.employee, getdate(self.attendance_date)
            )
        records = attendance_details.get("records") or []
        if not records:
            return {}

        record = records[0]
        net_wrk_hrs = record.get("net_wrk_hrs")
        if net_wrk_hrs and net_wrk_hrs < timedelta(0):
            net_wrk_hrs = -net_wrk_hrs

        return {
            "status": record.get("status"),
            "spent_hrs": to_duration_seconds(
                record.get("spent_hrs") or record.get("spent_hours")
            ),
            "net_wrk_hrs": fmt_td_or_value(net_wrk_hrs),
            "in_time": fmt_td_or_value(record.get("in_time")),
            "out_time": fmt_td_or_value(record.get("out_time")),
            "p_out_hrs": fmt_td_or_value(record.get("p_out_hrs")),
            "late": record.get("late") or record.get("late_entry") or 0,
            "late_hrs": fmt_td_or_value(record.get("late_hrs")),
            "early_hrs": fmt_td_or_value(record.get("early_hrs")),
            "ot_hrs": fmt_td_or_value(record.get("ot_hours") or record.get("othrs")),
        }

    @frappe.whitelist()
    def resolve_error(
        self, action, out_time=None, in_time=None, remarks=None, auto_fill=0
    ):
        return resolve_error_day(
            employee=self.employee,
            attendance_date=self.attendance_date,
            action=action,
            out_time=out_time,
            in_time=in_time,
            remarks=remarks,
            auto_fill=auto_fill,
        )

    @frappe.whitelist()
    def populate_from_attendance(self):
        """Populate hours and punch error ledger fields from the day's attendance."""
        self._populate_from_attendance()

    def _populate_from_attendance(self, attendance_details=None):
        """Populate the card from the attendance, optionally with precomputed attendance details."""
        try:
            attendance = get_monthly_in_out_log_attendance(self)
            if not attendance:
                return

            updates = get_error_context(self, attendance)
            if attendance.name != self.attendance:
                updates["attendance"] = attendance.name
            updates.update(self._hours_from(attendance, attendance_details))
            self._persist(updates)

        except Exception:
            frappe.log_error(
                title="MonthlyInOutLog.populate_from_attendance_error",
                message=frappe.get_traceback(with_context=True),
                reference_doctype=self.doctype,
            )


def to_duration_seconds(value):
    """Convert a timedelta, time-like string or number to whole seconds for Duration fields."""
    if value is None or value == "":
        return 0
    if isinstance(value, timedelta):
        return int(value.total_seconds())
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, datetime):
        return value.hour * 3600 + value.minute * 60 + value.second
    try:
        parts = [float(part) for part in str(value).split(":")]
    except ValueError:
        return 0
    parts += [0] * (3 - len(parts))
    hours, minutes, seconds = parts[:3]
    return int(hours * 3600 + minutes * 60 + seconds)


def refresh_monthly_in_out_logs(attendance_names):
    """Refresh the Monthly In-Out Log of each attendance with batched attendance details.

    Attendance details are computed once per company for the whole date range instead of
    once per card. Attendances without a card or without attendance details are skipped.
    """
    if not attendance_names:
        return

    attendance_by_name = {
        row.name: row
        for row in frappe.get_all(
            "Attendance",
            filters={"name": ["in", list(attendance_names)]},
            fields=["name", "company", "employee", "attendance_date"],
        )
    }
    attendances = [
        attendance_by_name[name]
        for name in attendance_names
        if name in attendance_by_name
    ]
    if not attendances:
        return

    employees = list({row.employee for row in attendances})
    attendance_dates = [getdate(row.attendance_date) for row in attendances]
    from_date = min(attendance_dates)
    to_date = max(attendance_dates)

    logs_by_company_employee_date = {}
    for log in frappe.get_all(
        "Monthly In-Out Log",
        filters={
            "employee": ["in", employees],
            "attendance_date": ["between", [from_date, to_date]],
            "docstatus": ["<", 2],
        },
        fields=["name", "employee", "attendance_date", "company"],
        order_by="creation desc",
    ):
        logs_by_company_employee_date.setdefault(
            (log.company, log.employee, getdate(log.attendance_date)), log
        )

    employees_by_company = {}
    for log in logs_by_company_employee_date.values():
        employees_by_company.setdefault(log.company, set()).add(log.employee)

    records_by_company_employee_date = get_attendance_records_by_employee_date(
        employees_by_company, from_date, to_date
    )

    for attendance in attendances:
        key = (
            attendance.company,
            attendance.employee,
            getdate(attendance.attendance_date),
        )
        log = logs_by_company_employee_date.get(key)
        if not log:
            continue

        record = records_by_company_employee_date.get(key)
        if not record:
            continue

        frappe.get_doc("Monthly In-Out Log", log.name)._populate_from_attendance(
            attendance_details={"records": [record]}
        )


def get_attendance_records_by_employee_date(
    employees_by_company, from_date, to_date, chunk_size=200
):
    """Return shaped daily attendance records keyed by (company, employee, date)."""
    records_by_key = {}
    for company, employees in employees_by_company.items():
        employees = sorted(employees)
        for start in range(0, len(employees), chunk_size):
            chunk = employees[start : start + chunk_size]
            results = fetch_attendance_data_for_employees(
                company, chunk, from_date, to_date
            )
            for employee, result in results.items():
                for record in result.get("records") or []:
                    if record.get("login_date"):
                        key = (company, employee, getdate(record["login_date"]))
                        records_by_key.setdefault(key, record)
    return records_by_key


# ============================================================
# WHITELISTED SERVICE (MODULE-LEVEL, REUSABLE)
# ============================================================


@frappe.whitelist()
def get_attendance_details_by_date(company, employee, attendance_date):
    """
    Whitelisted wrapper for the module-level fetcher.
    Normalizes input date and returns shaped result:
    {
      "employee": <employee id>,
      "attendance_date": <date>,
      "records": [ { daily record dict } ],
      "totals": [ { totals dicts } ]
    }
    """
    if not (company and employee and attendance_date):
        frappe.throw(_("Company, Employee and Attendance Date are required"))

    attendance_date = getdate(attendance_date)

    filters = {
        "company": company,
        "employee": employee,
        "from_date": attendance_date,
        "to_date": attendance_date,
    }

    return fetch_attendance_data(filters)


# ============================================================
# RESPONSE SHAPING (MODULE-LEVEL, REUSABLE)
# ============================================================


def fetch_attendance_data(filters):
    """
    Reusable service that returns shaped attendance data for the given filters.
    This function is intentionally module-level so other controllers / scripts can import it.
    """
    employee = filters.get("employee")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date") or from_date

    if not employee or not from_date:
        return get_empty_attendance_result(employee, from_date)

    if isinstance(employee, str):
        if getdate(from_date) == getdate(to_date):
            return fetch_attendance_data_for_single_day(
                filters.get("company"), employee, getdate(from_date)
            )

        results = fetch_attendance_data_for_employees(
            filters.get("company"), [employee], from_date, to_date
        )
        return results.get(employee) or get_empty_attendance_result(employee, from_date)

    return fetch_attendance_data_for_employees(
        filters.get("company"), list(employee), from_date, to_date
    )


def get_empty_attendance_result(employee, attendance_date):
    """Return the attendance result shape with no records and no totals."""
    return {
        "employee": employee,
        "attendance_date": attendance_date,
        "records": [],
        "totals": [],
    }


def fetch_attendance_data_for_single_day(company, employee, attendance_date):
    """Return shaped attendance data of one employee for one day.

    Gives the same result as `fetch_attendance_data_for_employees` for a single employee
    and day, but loads only the master data that day needs.
    """
    rows = get_attendance_rows(
        {
            "company": company,
            "employee": employee,
            "from_date": attendance_date,
            "to_date": attendance_date,
        }
    )
    if not rows:
        return get_empty_attendance_result(employee, attendance_date)

    for row in rows:
        row.pop("attendance_employee", None)

    context = build_single_day_attendance_context(employee, attendance_date, rows)
    employee_details = context.employees.get(employee) or {}
    shift = get_shift_from_rows(rows, employee_details)

    fetch_checkin_counts(context, {employee: shift}, attendance_date, attendance_date)
    context.week_off_checkins = get_week_off_checkins(
        context,
        {
            employee: get_week_off_shift_datetimes(
                context, employee, shift, attendance_date, attendance_date
            )
        },
    )

    filters = {
        "company": company,
        "employee": employee,
        "from_date": attendance_date,
        "to_date": attendance_date,
    }
    data = process_data(rows, filters, context)
    data.extend(get_totals(data, employee, context))
    return shape_attendance_data(data, employee_details, attendance_date)


def fetch_attendance_data_for_employees(
    company, employees, from_date, to_date, return_context=False
):
    """Return shaped attendance data for each employee, keyed by employee.

    The attendance rows, check-in counts and master data are fetched once for all
    employees instead of once per employee. When `return_context` is set, the master
    data context is returned along with the data so callers can reuse it.
    """
    if not from_date:
        frappe.throw(_("Attendance Date is required"))

    results = {}
    context = build_attendance_context(employees, from_date, to_date)
    if not employees:
        return (results, context) if return_context else results

    rows = get_attendance_rows(
        {
            "company": company,
            "employee": employees,
            "from_date": from_date,
            "to_date": to_date,
        }
    )

    rows_by_employee = {}
    for row in rows:
        rows_by_employee.setdefault(row.pop("attendance_employee"), []).append(row)

    employee_shifts = {}
    for employee, employee_rows in rows_by_employee.items():
        employee_shifts[employee] = get_shift_from_rows(
            employee_rows, context.employees.get(employee) or {}
        )
    if employee_shifts:
        fetch_checkin_counts(context, employee_shifts, from_date, to_date)
        context.week_off_checkins = get_week_off_checkins(
            context,
            {
                employee: get_week_off_shift_datetimes(
                    context, employee, shift, from_date, to_date
                )
                for employee, shift in employee_shifts.items()
            },
        )

    for employee in employees:
        employee_rows = rows_by_employee.get(employee)
        if not employee_rows:
            results[employee] = get_empty_attendance_result(employee, from_date)
            continue

        employee_filters = {
            "company": company,
            "employee": employee,
            "from_date": from_date,
            "to_date": to_date,
        }
        data = process_data(employee_rows, employee_filters, context)
        data.extend(get_totals(data, employee, context))
        results[employee] = shape_attendance_data(
            data, context.employees.get(employee) or {}, from_date
        )

    if return_context:
        return results, context
    return results


def get_shift_from_rows(rows, employee_details):
    """Return the shift of the last row that has one, else the employee's default shift."""
    shift = ""
    for row in rows:
        if row.get("shift_name"):
            shift = row.get("shift_name")

    return shift or employee_details.get("default_shift")


def shape_attendance_data(data, emp, from_date):
    """Split processed rows into daily records and totals rows."""
    records = []
    totals = []

    for row in data:
        # totals rows identified by status or by missing login_date + aggregate keys
        if row.get("status") in TOTAL_STATUS_ROWS:
            totals.append(row)
            continue

        if row.get("login_date") is None and any(
            k in row for k in ("total_pay_hrs", "ot_hours", "net_wrk_hrs")
        ):
            totals.append(row)
            continue

        records.append(
            {
                "employee": emp.get("name"),
                "employee_name": emp.get("employee_name"),
                "department": emp.get("department"),
                "designation": emp.get("designation"),
                "company": emp.get("company"),
                "punch_id": emp.get("attendance_device_id"),
                "login_date": row.get("login_date"),
                "shift_type": row.get("shift"),
                "shift_hours": row.get("shift_hours"),
                "status": row.get("status"),
                "spent_hrs": to_duration_seconds(row.get("spent_hours")),
                "punch_error": row.get("punch_error"),
                "net_wrk_hrs": row.get("net_wrk_hrs"),
                "in_time": row.get("in_time"),
                "out_time": row.get("out_time"),
                "p_out_hrs": row.get("p_out_hrs"),
                "p_out_deduction_hrs": row.get("p_out_deduction_hrs"),
                "late": row.get("late_entry"),
                "late_hrs": row.get("late_hrs"),
                "early_hrs": row.get("early_hrs"),
                "ot_hours": row.get("ot_hours"),
            }
        )

    return {
        "employee": emp.get("name"),
        "attendance_date": from_date,
        "records": records,
        "totals": totals,
    }


# ============================================================
# CORE REPORT LOGIC - get_attendance_rows, get_conditions, process_data, get_totals, get_date_range
# ============================================================


def get_attendance_rows(filters):
    """Return submitted Attendance rows for the filters, ordered by attendance date.

    filters.employee can be a single employee or a list of employees. Each row carries
    the employee in attendance_employee so the caller can group rows per employee.
    """
    Attendance = frappe.qb.DocType("Attendance")
    Employee = frappe.qb.DocType("Employee")
    ShiftType = frappe.qb.DocType("Shift Type")
    ShiftAssignment = frappe.qb.DocType("Shift Assignment")
    PersonalOutLog = frappe.qb.DocType("Personal Out Log")
    OTLog = frappe.qb.DocType("OT Log")

    TIME_FORMAT = CustomFunction("TIME_FORMAT", ["time", "format"])
    TIMEDIFF = CustomFunction("TIMEDIFF", ["time1", "time2"])
    SEC_TO_TIME = CustomFunction("SEC_TO_TIME", ["seconds"])
    TIME_TO_SEC = CustomFunction("TIME_TO_SEC", ["time"])
    IF = CustomFunction("IF", ["condition", "true_expr", "false_expr"])
    TIMESTAMP = CustomFunction("TIMESTAMP", ["date", "time"])
    TIME = CustomFunction("TIME", ["time"])
    ADDDATE = CustomFunction("ADDDATE", ["date", "days"])
    ADDTIME = CustomFunction("ADDTIME", ["date", "time"])

    conditions = get_conditions(filters)

    # Personal Out Log subquery
    pol_subquery = (
        frappe.qb.from_(PersonalOutLog)
        .select(
            PersonalOutLog.employee,
            PersonalOutLog.date,
            SEC_TO_TIME(IfNull(Sum(TIME_TO_SEC(PersonalOutLog.total_hours)), 0)).as_(
                "hrs"
            ),
        )
        .where(PersonalOutLog.is_cancelled == 0)
        .groupby(PersonalOutLog.employee, PersonalOutLog.date)
    ).as_("pol")

    # OT Log subquery
    ot_subquery = (
        frappe.qb.from_(OTLog).select("*").where(OTLog.is_cancelled == 0)
    ).as_("ot")

    # -----------------------------
    # SHIFT WINDOW (KEY FIX)
    # -----------------------------
    shift_start = TIMESTAMP(Attendance.attendance_date, ShiftType.start_time)

    shift_end = IF(
        ShiftType.start_time < ShiftType.end_time,
        TIMESTAMP(Attendance.attendance_date, ShiftType.end_time),
        TIMESTAMP(ADDDATE(Attendance.attendance_date, 1), ShiftType.end_time),
    )

    shift_start_with_grace = ADDTIME(
        shift_start, SEC_TO_TIME(ShiftType.late_entry_grace_period * 60)
    )

    effective_in = IF(
        Attendance.in_time <= shift_start_with_grace, shift_start, Attendance.in_time
    )

    effective_out = IF(Attendance.out_time > shift_end, shift_end, Attendance.out_time)
    pol_deduction_subquery = (
        frappe.qb.from_(PersonalOutLog)
        .select(
            IfNull(
                Sum(
                    IF(
                        TIME(PersonalOutLog.out_time)
                        > TIME(shift_end),  # NEW: out_time already past shift end?
                        0,  # → this personal out shouldn't count at all
                        TIME_TO_SEC(
                            TIMEDIFF(
                                IF(
                                    TIME(PersonalOutLog.in_time) > TIME(shift_end),
                                    TIME(shift_end),
                                    PersonalOutLog.in_time,
                                ),
                                PersonalOutLog.out_time,
                            )
                        ),
                    )
                ),
                0,
            )
        )
        .where(
            (PersonalOutLog.is_cancelled == 0)
            & (PersonalOutLog.employee == Attendance.employee)
            & (PersonalOutLog.date == Attendance.attendance_date)
        )
    )

    # Main Query
    query = (
        frappe.qb.from_(Attendance)
        .left_join(Employee)
        .on(Attendance.employee == Employee.name)
        .left_join(ShiftAssignment)
        .on(
            (Attendance.employee == ShiftAssignment.employee)
            & (
                Attendance.attendance_date.between(
                    ShiftAssignment.start_date, ShiftAssignment.end_date
                )
            )
        )
        .left_join(ShiftType)
        .on(
            (
                (ShiftAssignment.shift_type.isnotnull())
                & (ShiftAssignment.shift_type == ShiftType.name)
            )
            | (
                (ShiftAssignment.shift_type.isnull())
                & (Attendance.shift == ShiftType.name)
            )
        )
        .left_join(pol_subquery)
        .on(
            (Attendance.attendance_date == pol_subquery.date)
            & (Attendance.employee == pol_subquery.employee)
        )
        .left_join(ot_subquery)
        .on(
            (Attendance.attendance_date == ot_subquery.attendance_date)
            & (Attendance.employee == ot_subquery.employee)
        )
        .select(
            Attendance.attendance_date,
            IF(
                ShiftAssignment.shift_type.isnotnull(),
                ShiftAssignment.shift_type,
                Employee.default_shift,
            ).as_("shift_name"),
            Concat(
                TIME_FORMAT(ShiftType.start_time, "%H:%i:%s"),
                " TO ",
                TIME_FORMAT(ShiftType.end_time, "%H:%i:%s"),
            ).as_("shift"),
            TIME(Attendance.in_time).as_("in_time"),
            TIME(Attendance.out_time).as_("out_time"),
            Attendance.late_entry,
            IF(
                Attendance.late_entry,
                TIMEDIFF(
                    Attendance.in_time,
                    TIMESTAMP(Attendance.attendance_date, ShiftType.start_time),
                ),
                None,
            ).as_("late_hrs"),
            IF(
                Attendance.early_exit,
                TIMEDIFF(ShiftType.end_time, TIME(Attendance.out_time)),
                None,
            ).as_("early_hrs"),
            ################################################
            SEC_TO_TIME(
                IF(
                    Attendance.out_time.isnull(),
                    0,
                    TIME_TO_SEC(
                        TIMEDIFF(
                            IF(
                                Attendance.out_time < Attendance.in_time,
                                TIMESTAMP(
                                    ADDDATE(Date(Attendance.in_time), 1),
                                    TIME(Attendance.out_time),
                                ),
                                Attendance.out_time,
                            ),
                            Attendance.in_time,
                        )
                    ),
                )
            ).as_("spent_hours"),
            ################################################
            pol_subquery.hrs.as_("p_out_hrs"),
            pol_deduction_subquery.as_("p_out_deduction_hrs"),
            ################################################
            SEC_TO_TIME(
                IfNull(
                    IF(
                        Attendance.status.isin(["A", "ERR"]),
                        0,
                        TIME_TO_SEC(TIMEDIFF(effective_out, effective_in))
                        - pol_deduction_subquery,
                    ),
                    0,
                )
            ).as_("net_wrk_hrs"),
            ################################################
            ShiftType.shift_hours,
            IF(
                (
                    ShiftType.working_hours_threshold_for_half_day
                    > Attendance.working_hours
                )
                & (Attendance.working_hours > 0),
                1,
                0,
            ).as_("lh"),
            ot_subquery.allowed_ot.as_("ot_hours"),
            IfNull(Attendance.leave_type, Attendance.status).as_("status"),
            Attendance.punch_error.as_("punch_error"),
            Attendance.attendance_request,
            Attendance.employee.as_("attendance_employee"),
        )
        .where(Attendance.docstatus == 1)
        .orderby(Attendance.attendance_date, order=frappe.qb.asc)
    )

    for condition in conditions:
        query = query.where(condition)

    return query.run(as_dict=True)


# ============================================================
# HELPERS (UNCHANGED LOGIC)
# ============================================================


def get_conditions(filters):
    Attendance = frappe.qb.DocType("Attendance")
    if not filters.get("from_date"):
        frappe.throw(_("Attendance Date is required"))

    from_date = filters.get("from_date")
    to_date = filters.get("to_date") or from_date
    conditions = [Attendance.attendance_date.between(from_date, to_date)]

    employee = filters.get("employee")
    if isinstance(employee, (list, tuple)):
        conditions.append(Attendance.employee.isin(employee))
    elif employee:
        conditions.append(Attendance.employee == employee)

    return conditions


# small helper to format timedelta/time-like to HH:MM:SS string
def fmt_td_or_value(val):
    if not val:
        return "00:00:00"
    if isinstance(val, timedelta):
        secs = int(val.total_seconds())
        h = secs // 3600
        m = (secs % 3600) // 60
        s = secs % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
    if isinstance(val, datetime):
        # rarely expected, return date-time string
        return val.strftime("%Y-%m-%d %H:%M:%S")
    return val


def process_data(data, filters, context):
    employee = filters.get("employee")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    processed = {}
    result = []
    holidays = []
    wo = []
    emp_det = context.employees.get(employee)
    default_shift = emp_det.get("default_shift")
    shift = get_shift_from_rows(data, emp_det)

    shift_det = get_shift_type_from_context(context, shift)
    shift_hours = flt(shift_det.get("shift_hours") or 0)
    grace_period = shift_det.get("early_exit_grace_period") or 0

    if employee not in context.checkin_counts:
        fetch_checkin_counts(context, {employee: shift}, from_date, to_date)
    checkins = context.checkin_counts[employee]
    od = context.outdoor_duty.get(employee, [])

    holiday_dates = get_employee_holiday_dates(
        context, employee, shift, from_date, to_date
    )
    if holiday_dates:
        wo = holiday_dates.weekly_off
        holidays = holiday_dates.holidays

    leave_types = context.leave_types
    assignments = context.assignments.get(employee, [])

    for row in data:
        # security grace period logic
        if grace_period != 0:
            if not (row.get("early_hrs")):
                if row.get("status") == "Absent":
                    row["net_wrk_hrs"] = timedelta(0)
                    row["total_pay_hrs"] = timedelta(0)
                elif row.status == "Leave Without Pay":
                    row.net_wrk_hrs = timedelta(0)
                    row.total_pay_hrs = timedelta(0)
                elif row.get("late_hrs") or row.get("p_out_hrs"):
                    late = row.get("late_hrs") or timedelta(0)
                    p_out = timedelta(seconds=row.p_out_deduction_hrs or 0)
                    total = late + p_out

                    row["net_wrk_hrs"] = timedelta(hours=shift_hours) - total
                    row["total_pay_hrs"] = timedelta(0)
                else:
                    row["net_wrk_hrs"] = timedelta(hours=shift_hours)
                    row["total_pay_hrs"] = row.get("net_wrk_hrs") + (
                        row.get("ot_hours") or timedelta(0)
                    )

        if row.get("lh"):
            row.status = STATUS.get(row.status) or "LH"

        shift_hours_in_sec = ""
        if row.shift_hours:
            shift_hours_in_sec = row.shift_hours * 3600
            if row.status not in ["Leave Without Pay", "Absent"]:
                if (
                    row.net_wrk_hrs.total_seconds() > shift_hours_in_sec
                    or (shift_hours_in_sec - row.net_wrk_hrs.total_seconds()) < 60
                ):
                    row.net_wrk_hrs = timedelta(hours=row.shift_hours)
            if row.status in leave_types.earned:
                row.status = STATUS.get(row.status) or row.status
                row.net_wrk_hrs = timedelta(hours=row.shift_hours)
        else:
            row_shift_det = resolve_shift_for_date(
                assignments, context.shift_types, row.attendance_date, default_shift
            )
            row_shift_name = f"{format_time(row_shift_det.get('start_time'))} To {format_time(row_shift_det.get('end_time'))}"
            row.shift = row_shift_name

            is_earned_leave = row.get("status") in leave_types.earned
            is_continuous_leave = row.status in leave_types.continuous
            is_lwp = row.status in leave_types.lwp

            if is_lwp:
                row.status = STATUS.get(row.status) or row.status
                row.net_wrk_hrs = timedelta(0)
            elif is_earned_leave or is_continuous_leave:
                row["status"] = STATUS.get(row.status) or row.status
                row["net_wrk_hrs"] = timedelta(hours=shift_hours)
            else:
                row["net_wrk_hrs"] = timedelta(0)

        row["total_pay_hrs"] = row.get("net_wrk_hrs") + (
            row.get("ot_hours") or timedelta(0)
        )
        status = row.get("status")

        # Normalize all leave types to "On Leave"
        if status in leave_types.all or row.get("status") == "On Leave":
            row["status"] = "On Leave"

        elif status in (
            "Present",
            "Absent",
            "Half Day",
            "Work From Home",
            "OD",
            "WO",
            "H",
        ):
            row["status"] = status

        else:
            # safety fallback
            row["status"] = "Absent"

        processed[row.get("attendance_date")] = row

    ot_for_wo = {
        attendance_date: frappe._dict(ot_log)
        for attendance_date, ot_log in context.ot_for_wo.get(employee, {}).items()
    }
    date_range = get_date_range(from_date, to_date)
    date_of_joining = getdate(emp_det.get("date_of_joining"))

    shift_det_by_date = {
        date: resolve_shift_for_date(
            assignments, context.shift_types, date, default_shift
        )
        or frappe._dict()
        for date in date_range
    }

    wo_shift_datetimes = get_week_off_shift_datetimes(
        context, employee, shift, from_date, to_date
    )
    if employee not in context.week_off_checkins:
        context.week_off_checkins.update(
            get_week_off_checkins(context, {employee: wo_shift_datetimes})
        )
    wo_checkins = context.week_off_checkins[employee]

    for date in date_range:
        row = processed.get(date, ot_for_wo.get(date, {}))
        status = row.get("status") or "XX"

        # Check for odd checkin count first, but don't override WO/Holiday status later
        has_checkin_error = False
        if count := checkins.get(date):
            if count % 2 != 0:
                has_checkin_error = True

        date_shift_det = shift_det_by_date[date]
        date_shift_hours = flt(date_shift_det.get("shift_hours"))
        date_shift_name = f"{format_time(date_shift_det.get('start_time'))} To {format_time(date_shift_det.get('end_time'))}"

        if date in od:
            status = "OD"
            if ot_hours := row.get("ot_hours"):
                row["total_pay_hrs"] = ot_hours
            else:
                row["total_pay_hrs"] = row.get("total_pay_hrs")

        elif date in wo and date >= date_of_joining:
            status = "WO"

            # The checkins may include the previous day's night shift that ended on this WO date.
            wo_shift_datetime = wo_shift_datetimes.get(date)
            first_in_last_out = []
            if wo_shift_datetime is not None:
                first_in_last_out = wo_checkins.get(wo_shift_datetime, [])

            if first_in_last_out:
                for ci in first_in_last_out:
                    if ci.get("attendance"):
                        # Linked to a previous shift's attendance, so its times are not shown.
                        has_checkin_error = False
                        row["in_time"] = ""
                        row["out_time"] = ""
                    else:
                        # No attendance yet, likely OT work on the WO day.
                        row["in_time"] = get_time(first_in_last_out[0].get("time"))
                        row["out_time"] = get_time(first_in_last_out[-1].get("time"))
            else:
                has_checkin_error = False

            # OT Log is usually created 1-2 days after the work.
            if ot_hours := row.get("ot_hours"):
                row["total_pay_hrs"] = ot_hours

        elif (date in holidays) and date >= date_of_joining:
            if row.get("status") in ["LWP", "PL", "CL", "SL", "ML", "WFH"]:
                pass
            else:
                status = "H"
                row["net_wrk_hrs"] = timedelta(hours=date_shift_hours)
                row["total_pay_hrs"] = timedelta(hours=date_shift_hours)
        else:
            status = "XX"

        if has_checkin_error:
            row["net_wrk_hrs"] = timedelta(0)
            row["total_pay_hrs"] = timedelta(0)

        temp = {"login_date": date, "shift": date_shift_name, "status": status}
        if not row.get("spent_hours"):
            row["spent_hours"] = None
        temp.update(row)
        result.append(temp)

    return result


def fetch_checkin_counts(context, employee_shifts, from_date, to_date):
    """Store checkin counts per login date in context.checkin_counts for each employee.

    employee_shifts maps an employee to the shift used for the whole range. Employees
    whose shifts share the same night shift flag and start time are fetched in one query.
    """
    employees_by_shift_key = {}
    for employee, shift in employee_shifts.items():
        shift_det = get_shift_type_from_context(context, shift)
        start_time = shift_det.get("start_time")
        end_time = shift_det.get("end_time")
        is_night_shift = bool(start_time and end_time) and get_time(
            start_time
        ) > get_time(end_time)
        shift_start_time = shift_det.get("start_time") if is_night_shift else None
        shift_key = (is_night_shift, shift_start_time)
        employees_by_shift_key.setdefault(shift_key, []).append(employee)
        context.checkin_counts[employee] = {}

    EmployeeCheckin = frappe.qb.DocType("Employee Checkin")
    from_date_time = get_datetime(from_date)
    to_date_time = get_datetime(f"{add_days(to_date, 1)} 23:59:59")

    TIME = CustomFunction("TIME", ["time"])
    IF = CustomFunction("IF", ["condition", "true_expr", "false_expr"])

    for (is_night_shift, shift_start_time), employees in employees_by_shift_key.items():
        if is_night_shift:
            # Check-ins before the shift start belong to the previous day's shift.
            login_date = IF(
                TIME(EmployeeCheckin.time) < shift_start_time,
                Date(EmployeeCheckin.time - timedelta(days=1)),
                Date(EmployeeCheckin.time),
            )
        else:
            login_date = Date(EmployeeCheckin.time)

        checkins = (
            frappe.qb.from_(EmployeeCheckin)
            .select(
                EmployeeCheckin.employee,
                Min(login_date).as_("login_date"),
                EmployeeCheckin.attendance,
                Count(EmployeeCheckin.name).as_("cnt"),
            )
            .where(
                (EmployeeCheckin.time.between(from_date_time, to_date_time))
                & (EmployeeCheckin.employee.isin(employees))
                & (EmployeeCheckin.attendance.isnotnull())
                & (EmployeeCheckin.attendance != "")
            )
            .groupby(EmployeeCheckin.employee, EmployeeCheckin.attendance)
        ).run(as_dict=True)

        for row in checkins:
            context.checkin_counts[row.employee][row.login_date] = row.cnt


def get_shift_type_from_context(context, shift):
    """Return Shift Type details from the context, fetching and caching it when missing."""
    if not shift:
        return frappe._dict()
    if shift not in context.shift_types:
        context.shift_types[shift] = (
            frappe.db.get_value(
                "Shift Type",
                shift,
                [
                    "shift_hours",
                    "holiday_list",
                    "start_time",
                    "end_time",
                    "early_exit_grace_period",
                    "begin_check_in_before_shift_start_time",
                    "allow_check_out_after_shift_end_time",
                ],
                as_dict=1,
            )
            or frappe._dict()
        )
    return context.shift_types[shift]


def get_holidays_from_context(context, holiday_list, from_date, to_date):
    """Return weekly off and holiday dates of a Holiday List, fetching and caching it when missing."""
    if holiday_list not in context.holidays:
        holiday_dates = frappe._dict(weekly_off=[], holidays=[])
        for holiday in frappe.get_all(
            "Holiday",
            filters={
                "parent": holiday_list,
                "holiday_date": ["between", [from_date, to_date]],
            },
            fields=["holiday_date", "weekly_off"],
            ignore_permissions=True,
        ):
            if holiday.weekly_off:
                holiday_dates.weekly_off.append(holiday.holiday_date)
            else:
                holiday_dates.holidays.append(holiday.holiday_date)
        context.holidays[holiday_list] = holiday_dates
    return context.holidays[holiday_list]


def resolve_shift_for_date(assignments, shift_types, check_date, default_shift):
    """Return the Shift Type details active on `check_date`.

    `assignments` must be one employee's submitted Shift Assignments sorted by start_date desc.
    """
    check_date = getdate(check_date)
    shift = default_shift
    for assignment in assignments:
        if getdate(assignment.start_date) <= check_date:
            if not assignment.end_date or getdate(assignment.end_date) >= check_date:
                shift = assignment.shift_type
            break

    return shift_types.get(shift)


def get_employee_holiday_dates(context, employee, shift, from_date, to_date):
    """Return weekly off and holiday dates from the employee's or shift's Holiday List."""
    holiday_list = context.employees[employee].get("holiday_list")
    if shift and not holiday_list:
        holiday_list = get_shift_type_from_context(context, shift).get("holiday_list")

    if holiday_list:
        return get_holidays_from_context(context, holiday_list, from_date, to_date)


def get_week_off_shift_datetimes(context, employee, shift, from_date, to_date):
    """Return `{date: shift start datetime}` for the week off dates whose check-ins are shown."""
    holiday_dates = get_employee_holiday_dates(
        context, employee, shift, from_date, to_date
    )
    if not holiday_dates:
        return {}

    emp_det = context.employees[employee]
    date_of_joining = getdate(emp_det.get("date_of_joining"))
    od = context.outdoor_duty.get(employee, [])
    assignments = context.assignments.get(employee, [])

    shift_datetimes = {}
    for date in get_date_range(from_date, to_date):
        if (
            date not in od
            and date in holiday_dates.weekly_off
            and date >= date_of_joining
        ):
            date_shift_det = resolve_shift_for_date(
                assignments, context.shift_types, date, emp_det.get("default_shift")
            )
            if not date_shift_det:
                frappe.throw(
                    _(
                        "No shift found for Employee {0} on {1}. Please assign a shift or set a Default Shift for the employee."
                    ).format(frappe.bold(employee), frappe.bold(formatdate(date))),
                    title=_("Shift Not Found"),
                )
            shift_datetimes[date] = datetime.combine(
                getdate(date), get_time(date_shift_det.start_time)
            )
    return shift_datetimes


def get_week_off_checkins(context, shift_datetimes_by_employee):
    """Return `{employee: {shift_datetime: [checkin rows]}}` for many employees in two queries.

    Matches `get_checkins_for_dates` of Manual Punch: a checkin belongs to a date when its
    time falls inside that date's actual shift window, or when it is linked to that date's
    submitted Attendance.
    """
    checkins_by_employee = {}
    windows_by_employee = {}
    for employee, shift_datetimes in shift_datetimes_by_employee.items():
        checkins_by_date = {
            shift_datetime: []
            for shift_datetime in shift_datetimes.values()
            if shift_datetime
        }
        checkins_by_employee[employee] = checkins_by_date
        shift_windows = get_shift_windows(context, employee, checkins_by_date)
        if shift_windows:
            windows_by_employee[employee] = shift_windows

    if not windows_by_employee:
        return checkins_by_employee

    window_dates = {
        (employee, getdate(shift_datetime))
        for employee, shift_windows in windows_by_employee.items()
        for shift_datetime in shift_windows
    }
    attendance_by_date = {}
    attendance_list = frappe.get_all(
        "Attendance",
        filters={
            "employee": ["in", list(windows_by_employee)],
            "attendance_date": ["in", list({date for employee, date in window_dates})],
            "docstatus": 1,
        },
        fields=["employee", "name", "attendance_date"],
        order_by="creation asc",
    )
    for attendance in attendance_list:
        key = (attendance.employee, getdate(attendance.attendance_date))
        if key in window_dates:
            attendance_by_date.setdefault(key, attendance.name)

    all_windows = [
        window
        for shift_windows in windows_by_employee.values()
        for window in shift_windows.values()
    ]
    window_start = min(start for start, end in all_windows)
    window_end = max(end for start, end in all_windows)

    EmployeeCheckin = frappe.qb.DocType("Employee Checkin")
    checkin_condition = EmployeeCheckin.time[window_start:window_end]
    if attendance_by_date:
        checkin_condition = checkin_condition | EmployeeCheckin.attendance.isin(
            list(attendance_by_date.values())
        )

    checkins = (
        frappe.qb.from_(EmployeeCheckin)
        .select(
            EmployeeCheckin.employee,
            Date(EmployeeCheckin.time).as_("date"),
            EmployeeCheckin.log_type.as_("type"),
            EmployeeCheckin.time,
            EmployeeCheckin.source,
            EmployeeCheckin.name.as_("employee_checkin"),
            EmployeeCheckin.attendance,
        )
        .where(
            EmployeeCheckin.employee.isin(list(windows_by_employee)) & checkin_condition
        )
        .orderby(EmployeeCheckin.employee)
        .orderby(EmployeeCheckin.time)
    ).run(as_dict=True)

    checkins_of_employee = {}
    for checkin in checkins:
        checkins_of_employee.setdefault(checkin.pop("employee"), []).append(checkin)

    for employee, shift_windows in windows_by_employee.items():
        employee_checkins = checkins_of_employee.get(employee, [])
        checkin_times = [checkin.time for checkin in employee_checkins]
        indexes_by_attendance = {}
        for index, checkin in enumerate(employee_checkins):
            if checkin.attendance:
                indexes_by_attendance.setdefault(checkin.attendance, []).append(index)
        for shift_datetime, (actual_start, actual_end) in shift_windows.items():
            indexes = set(
                range(
                    bisect_left(checkin_times, actual_start),
                    bisect_right(checkin_times, actual_end),
                )
            )
            attendance = attendance_by_date.get((employee, getdate(shift_datetime)))
            if attendance:
                indexes.update(indexes_by_attendance.get(attendance, []))
            checkins_by_employee[employee][shift_datetime] = [
                frappe._dict(employee_checkins[index]) for index in sorted(indexes)
            ]

    return checkins_by_employee


def get_shift_windows(context, employee, shift_datetimes):
    """Return `{shift_datetime: (actual_start, actual_end)}` of the current shift on each datetime.

    Uses the context when possible and falls back to HRMS `get_employee_shift_timings`.
    """
    shift_windows = {}
    for shift_datetime in shift_datetimes:
        for_timestamp = get_datetime(shift_datetime)
        shift_window = get_shift_window_from_context(context, employee, for_timestamp)
        if shift_window is None:
            current_shift = get_employee_shift_timings(employee, for_timestamp, True)[1]
            if current_shift:
                shift_window = (current_shift.actual_start, current_shift.actual_end)
        if shift_window:
            shift_windows[shift_datetime] = shift_window
    return shift_windows


def get_shift_window_from_context(context, employee, for_timestamp):
    """Return the actual window of the current shift the same way as `get_employee_shift_timings`.

    Returns None when the current, previous or next shift cannot be found from the context.
    """
    current_shift = get_shift_details_from_context(context, employee, for_timestamp)
    if not current_shift:
        return None

    next_shift = get_shift_details_from_context(
        context, employee, current_shift.start_datetime + timedelta(days=1)
    )
    prev_shift = get_shift_details_from_context(
        context, employee, current_shift.end_datetime - timedelta(days=1)
    )
    if not (next_shift and prev_shift):
        return None

    # The window is clipped so it does not overlap the previous and next day's shifts.
    actual_start = max(current_shift.actual_start, prev_shift.end_datetime)
    next_actual_start = max(next_shift.actual_start, current_shift.end_datetime)
    actual_end = min(current_shift.actual_end, next_actual_start)
    return actual_start, actual_end


def get_shift_details_from_context(context, employee, for_timestamp):
    """Return the shift details HRMS `get_employee_shift` gives with the default shift considered.

    Returns None when the shift cannot be found from the context.
    """
    if not HRMS_SHIFT_HELPERS_AVAILABLE:
        return None

    for_date = for_timestamp.date()
    valid_shifts = []
    for assignment in context.assignments.get(employee, []):
        if assignment.status != "Active":
            continue
        if getdate(assignment.start_date) > add_days(for_date, 1):
            continue
        if assignment.end_date and getdate(assignment.end_date) < add_days(
            for_date, -1
        ):
            continue

        shift_details = get_shift_details_from_shift_type(
            context, assignment.shift_type, for_timestamp
        )
        if not shift_details:
            return None
        if _is_shift_outside_assignment_period(shift_details, assignment):
            continue
        if shift_details.actual_start <= for_timestamp <= shift_details.actual_end:
            valid_shifts.append(shift_details)

    valid_shifts.sort(key=lambda shift: shift.actual_start)
    _adjust_overlapping_shifts(valid_shifts)
    shift_details = get_exact_shift(valid_shifts, for_timestamp)
    if shift_details:
        return shift_details

    default_shift = context.employees[employee].get("default_shift")
    if not default_shift:
        return None
    return get_shift_details_from_shift_type(context, default_shift, for_timestamp)


def get_shift_details_from_shift_type(context, shift, for_timestamp):
    """Return start, end and actual start, end datetimes of a Shift Type from the context."""
    shift_type = context.shift_types.get(shift)
    if (
        not shift_type
        or shift_type.get("begin_check_in_before_shift_start_time") is None
    ):
        return None

    shift_timing = frappe._dict(
        start_time=shift_type.start_time,
        end_time=shift_type.end_time,
        begin_check_in_before_shift_start_time=cint(
            shift_type.begin_check_in_before_shift_start_time
        ),
        allow_check_out_after_shift_end_time=cint(
            shift_type.allow_check_out_after_shift_end_time
        ),
    )
    start_datetime, end_datetime = get_shift_timings(shift_timing, for_timestamp)
    return frappe._dict(
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        actual_start=start_datetime
        - timedelta(minutes=shift_timing.begin_check_in_before_shift_start_time),
        actual_end=end_datetime
        + timedelta(minutes=shift_timing.allow_check_out_after_shift_end_time),
    )


def build_attendance_context(employees, from_date, to_date):
    """Fetch, in bulk, the master data used to build attendance rows for many employees."""
    employees = list(employees or [])
    from_date = getdate(from_date)
    to_date = getdate(to_date)

    context = frappe._dict(
        employees={},
        leave_types=frappe._dict(all=set(), earned=set(), continuous=set(), lwp=set()),
        assignments={},
        shift_types={},
        holidays={},
        outdoor_duty={},
        ot_for_wo={},
        checkin_counts={},
        week_off_checkins={},
    )
    if not employees:
        return context

    employee_list = frappe.get_all(
        "Employee",
        filters={"name": ["in", employees]},
        fields=[
            "name",
            "employee_name",
            "department",
            "designation",
            "company",
            "attendance_device_id",
            "default_shift",
            "holiday_list",
            "date_of_joining",
            "allowed_personal_hours",
        ],
    )
    context.employees = {row.name: row for row in employee_list}

    for leave_type in frappe.get_all(
        "Leave Type",
        fields=["name", "is_earned_leave", "max_continuous_days_allowed", "is_lwp"],
    ):
        context.leave_types.all.add(leave_type.name)
        if leave_type.is_earned_leave:
            context.leave_types.earned.add(leave_type.name)
        if flt(leave_type.max_continuous_days_allowed) > 0:
            context.leave_types.continuous.add(leave_type.name)
        if leave_type.is_lwp:
            context.leave_types.lwp.add(leave_type.name)

    assignment_list = frappe.get_all(
        "Shift Assignment",
        filters={
            "employee": ["in", employees],
            "docstatus": 1,
            "start_date": ["<=", add_days(to_date, 2)],
        },
        fields=["employee", "shift_type", "start_date", "end_date", "status"],
        order_by="start_date desc",
    )
    for assignment in assignment_list:
        context.assignments.setdefault(assignment.employee, []).append(assignment)

    attendance_shifts = frappe.get_all(
        "Attendance",
        filters={
            "employee": ["in", employees],
            "attendance_date": ["between", [from_date, to_date]],
            "shift": ["is", "set"],
        },
        pluck="shift",
        distinct=True,
    )
    shift_names = set(attendance_shifts)
    shift_names.update(row.shift_type for row in assignment_list if row.shift_type)
    shift_names.update(row.default_shift for row in employee_list if row.default_shift)
    if shift_names:
        shift_type_list = frappe.get_all(
            "Shift Type",
            filters={"name": ["in", list(shift_names)]},
            fields=[
                "name",
                "shift_hours",
                "holiday_list",
                "start_time",
                "end_time",
                "early_exit_grace_period",
                "begin_check_in_before_shift_start_time",
                "allow_check_out_after_shift_end_time",
            ],
        )
        for shift_type in shift_type_list:
            context.shift_types[shift_type.pop("name")] = shift_type

    holiday_lists = {row.holiday_list for row in employee_list if row.holiday_list}
    holiday_lists.update(
        row.holiday_list for row in context.shift_types.values() if row.holiday_list
    )
    for holiday_list in holiday_lists:
        context.holidays[holiday_list] = frappe._dict(weekly_off=[], holidays=[])
    if holiday_lists:
        holiday_rows = frappe.get_all(
            "Holiday",
            filters={
                "parent": ["in", list(holiday_lists)],
                "holiday_date": ["between", [from_date, to_date]],
            },
            fields=["parent", "holiday_date", "weekly_off"],
            ignore_permissions=True,
        )
        for holiday in holiday_rows:
            if holiday.weekly_off:
                context.holidays[holiday.parent].weekly_off.append(holiday.holiday_date)
            else:
                context.holidays[holiday.parent].holidays.append(holiday.holiday_date)

    EmployeeCheckin = frappe.qb.DocType("Employee Checkin")
    outdoor_duty_rows = (
        frappe.qb.from_(EmployeeCheckin)
        .select(EmployeeCheckin.employee, Date(EmployeeCheckin.time).as_("login_date"))
        .where(
            (EmployeeCheckin.employee.isin(employees))
            & (EmployeeCheckin.source == "Outdoor Duty")
            & (EmployeeCheckin.time[from_date : add_days(to_date, 1)])
        )
        .groupby(EmployeeCheckin.employee, Date(EmployeeCheckin.time))
    ).run(as_dict=True)
    for row in outdoor_duty_rows:
        context.outdoor_duty.setdefault(row.employee, []).append(row.login_date)

    ot_log_list = frappe.get_all(
        "OT Log",
        filters={
            "employee": ["in", employees],
            "attendance_date": ["between", [from_date, to_date]],
            "is_cancelled": 0,
        },
        fields=[
            "employee",
            "attendance_date",
            "allowed_ot as ot_hours",
            "first_in as in_time",
            "last_out as out_time",
        ],
        ignore_permissions=True,
    )
    for ot_log in ot_log_list:
        employee = ot_log.pop("employee")
        context.ot_for_wo.setdefault(employee, {})[ot_log.attendance_date] = ot_log

    return context


def build_single_day_attendance_context(employee, attendance_date, rows):
    """Fetch the master data used to build the attendance of one employee for one day.

    Holds the same data as `build_attendance_context` for that day. OT Logs are not
    fetched because they are only used on dates without an Attendance row.
    """
    attendance_date = getdate(attendance_date)

    context = frappe._dict(
        employees={},
        leave_types=frappe._dict(all=set(), earned=set(), continuous=set(), lwp=set()),
        assignments={},
        shift_types={},
        holidays={},
        outdoor_duty={},
        ot_for_wo={},
        checkin_counts={},
        week_off_checkins={},
    )

    employee_details = frappe.db.get_value(
        "Employee",
        employee,
        [
            "name",
            "employee_name",
            "department",
            "designation",
            "company",
            "attendance_device_id",
            "default_shift",
            "holiday_list",
            "date_of_joining",
            "allowed_personal_hours",
        ],
        as_dict=True,
    )
    if employee_details:
        context.employees[employee] = employee_details

    load_leave_types_for_rows(context, rows)

    assignment_list = frappe.get_all(
        "Shift Assignment",
        filters={
            "employee": employee,
            "docstatus": 1,
            "start_date": ["<=", add_days(attendance_date, 2)],
        },
        fields=["employee", "shift_type", "start_date", "end_date", "status"],
        order_by="start_date desc",
    )
    if assignment_list:
        context.assignments[employee] = assignment_list

    shift_names = {row.shift_type for row in assignment_list if row.shift_type}
    if employee_details and employee_details.default_shift:
        shift_names.add(employee_details.default_shift)
    load_cached_shift_types(context, shift_names)

    holiday_lists = {
        row.holiday_list for row in context.shift_types.values() if row.holiday_list
    }
    if employee_details and employee_details.holiday_list:
        holiday_lists.add(employee_details.holiday_list)
    for holiday_list in holiday_lists:
        context.holidays[holiday_list] = frappe._dict(weekly_off=[], holidays=[])
    if holiday_lists:
        for holiday in frappe.get_all(
            "Holiday",
            filters={
                "parent": ["in", list(holiday_lists)],
                "holiday_date": attendance_date,
            },
            fields=["parent", "holiday_date", "weekly_off"],
            ignore_permissions=True,
        ):
            if holiday.weekly_off:
                context.holidays[holiday.parent].weekly_off.append(holiday.holiday_date)
            else:
                context.holidays[holiday.parent].holidays.append(holiday.holiday_date)

    EmployeeCheckin = frappe.qb.DocType("Employee Checkin")
    outdoor_duty_dates = (
        frappe.qb.from_(EmployeeCheckin)
        .select(Date(EmployeeCheckin.time).as_("login_date"))
        .where(
            (EmployeeCheckin.employee == employee)
            & (EmployeeCheckin.source == "Outdoor Duty")
            & (EmployeeCheckin.time[attendance_date : add_days(attendance_date, 1)])
        )
        .groupby(Date(EmployeeCheckin.time))
    ).run(pluck=True)
    if outdoor_duty_dates:
        context.outdoor_duty[employee] = outdoor_duty_dates

    return context


def load_leave_types_for_rows(context, rows):
    """Load into the context the Leave Types that the attendance row statuses can refer to.

    Rows whose status is a standard Attendance status never refer to a Leave Type, so the
    query runs only when a row carries a leave type name.
    """
    standard_statuses = {"Present", "Absent", "On Leave", "Half Day", "Work From Home"}
    row_statuses = {row.get("status") for row in rows if row.get("status")}
    if not row_statuses - standard_statuses:
        return

    candidate_names = set(row_statuses)
    candidate_names.update(STATUS.get(status) or status for status in row_statuses)
    candidate_names.add("LH")

    for leave_type in frappe.get_all(
        "Leave Type",
        filters={"name": ["in", list(candidate_names)]},
        fields=["name", "is_earned_leave", "max_continuous_days_allowed", "is_lwp"],
    ):
        context.leave_types.all.add(leave_type.name)
        if leave_type.is_earned_leave:
            context.leave_types.earned.add(leave_type.name)
        if flt(leave_type.max_continuous_days_allowed) > 0:
            context.leave_types.continuous.add(leave_type.name)
        if leave_type.is_lwp:
            context.leave_types.lwp.add(leave_type.name)


def load_cached_shift_types(context, shift_names):
    """Load Shift Type details into the context from the document cache."""
    for shift_name in shift_names:
        try:
            shift_type = frappe.get_cached_doc("Shift Type", shift_name)
        except frappe.DoesNotExistError:
            frappe.clear_last_message()
            continue

        context.shift_types[shift_name] = frappe._dict(
            shift_hours=shift_type.shift_hours,
            holiday_list=shift_type.holiday_list,
            start_time=shift_type.start_time,
            end_time=shift_type.end_time,
            early_exit_grace_period=shift_type.early_exit_grace_period,
            begin_check_in_before_shift_start_time=shift_type.begin_check_in_before_shift_start_time,
            allow_check_out_after_shift_end_time=shift_type.allow_check_out_after_shift_end_time,
        )


def get_totals(data, employee, context):
    totals = {
        "status": "Total Hours",
        "net_wrk_hrs": timedelta(0),
        "spent_hours": timedelta(0),
        "late_hrs": timedelta(0),
        "early_hrs": timedelta(0),
        "p_out_hrs": timedelta(0),
        "ot_hours": timedelta(0),
        "total_pay_hrs": timedelta(0),
    }
    late_count = 0
    penalty_days = 0
    personal_out_deduction = timedelta(0)

    for row in data:
        personal_out_deduction += timedelta(
            seconds=(row.get("p_out_deduction_hrs") or 0)
        )

        totals["net_wrk_hrs"] += row.get("net_wrk_hrs") or timedelta(0)
        totals["total_pay_hrs"] += row.get("total_pay_hrs") or timedelta(0)
        totals["ot_hours"] += row.get("ot_hours") or timedelta(0)
        totals["early_hrs"] += row.get("early_hrs") or timedelta(0)
        totals["late_hrs"] += row.get("late_hrs") or timedelta(0)
        totals["spent_hours"] += row.get("spent_hours") or timedelta(0)
        if row.get("late_entry"):
            late_count += 1
        if row.get("shift_hours"):
            totals["shift_hours"] = row.get("shift_hours")

    totals["p_out_hrs"] = personal_out_deduction or timedelta(0)

    if late_count > 4 and late_count < 10:
        penalty_days = 0.5
    if late_count >= 10 and late_count < 15:
        penalty_days = 1
    if late_count >= 15:
        penalty_days = 1.5

    total_days = {"status": "Total Days"}
    conversion_factor = 3600 * flt(totals.get("shift_hours") or 0)

    penalty_hrs = timedelta(hours=flt(totals.get("shift_hours") or 0) * penalty_days)
    for key, value in totals.items():
        if key in ["status", "shift_hours"]:
            continue
        total_days[key] = (
            flt(value.total_seconds() / conversion_factor, 2)
            if conversion_factor
            else 0.0
        )

    refund = {
        "ot_hours": "Refund Min(P.Hrs)",
        "total_pay_hrs": min(
            (context.employees.get(employee) or {}).get("allowed_personal_hours")
            or timedelta(0),
            (totals["early_hrs"] + totals["late_hrs"] + totals["p_out_hrs"]),
        ),
    }

    penalty_for_late_entry = {
        "ot_hours": "Penalty in Days",
        "total_pay_hrs": penalty_days,
    }

    net_pay_hrs = {
        "ot_hours": "Net Hrs",
        "total_pay_hrs": totals["net_wrk_hrs"]
        + totals["ot_hours"]
        + refund["total_pay_hrs"]
        - penalty_hrs,
    }

    net_pay_days = {
        "ot_hours": "Net Days",
        "total_pay_hrs": flt(
            net_pay_hrs["total_pay_hrs"].total_seconds() / conversion_factor, 2
        )
        if conversion_factor
        else 0.0,
    }

    net_pay_hrs_wo_ot = {
        "ot_hours": "Net Hrs w/o OT",
        "total_pay_hrs": totals["net_wrk_hrs"] + refund["total_pay_hrs"] - penalty_hrs,
    }

    net_pay_days_wo_ot = {
        "ot_hours": "Net Days w/o OT",
        "total_pay_hrs": flt(
            net_pay_hrs_wo_ot["total_pay_hrs"].total_seconds() / conversion_factor, 2
        )
        if conversion_factor
        else 0.0,
    }

    return [
        totals,
        total_days,
        refund,
        penalty_for_late_entry,
        net_pay_hrs,
        net_pay_days,
        net_pay_hrs_wo_ot,
        net_pay_days_wo_ot,
    ]


def get_date_range(start_date, end_date):
    start_date = getdate(start_date)
    end_date = getdate(end_date)

    range_list = []
    delta = timedelta(days=1)
    current_date = start_date

    while current_date <= end_date:
        range_list.append(current_date)
        current_date += delta

    return range_list


def create_monthly_in_out_log(doc, method=None):
    """
    Create Monthly In-Out Log when Attendance is submitted
    """

    # Safety checks
    if not doc.employee or not doc.attendance_date:
        return

    attendance_date = getdate(doc.attendance_date)

    # Prevent duplicate Monthly In-Out Log
    if frappe.db.exists(
        "Monthly In-Out Log",
        {
            "attendance": doc.name,
            "attendance_date": attendance_date,
            "docstatus": ["in", [0, 1]],  # only submitted,draft docs
        },
    ):
        return

    # Create Monthly In-Out Log
    monthly_log = frappe.new_doc("Monthly In-Out Log")
    monthly_log.employee = doc.employee
    monthly_log.attendance_date = attendance_date
    monthly_log.attendance = doc.name
    monthly_log.status = doc.status

    monthly_log.save()
    monthly_log.submit()


def cancel_monthly_in_out_log(doc, method=None):
    """
    Cancel Monthly In-Out Log when Attendance is cancelled
    """

    if not doc.employee or not doc.attendance_date:
        return

    attendance_date = getdate(doc.attendance_date)

    monthly_log_name = frappe.db.get_value(
        "Monthly In-Out Log",
        {
            "attendance": doc.name,
            "attendance_date": attendance_date,
            "docstatus": 1,  # only submitted docs
        },
        "name",
    )
    if not monthly_log_name:
        return

    monthly_log = frappe.get_doc("Monthly In-Out Log", monthly_log_name)
    monthly_log.cancel()
