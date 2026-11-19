# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

from datetime import timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_to_date, get_datetime, get_time, getdate, today
from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift_timings
from pypika.functions import Date

from gke_customization.gke_hrms.utils import get_employees_by_shift


class HolidayPunch(Document):
    @frappe.whitelist()
    def validate_punch(self):
        shift_datetime = get_datetime(
            f"{getdate(self.date)} {get_time(self.start_time)}"
        )

        shift_det = get_employee_shift_timings(
            self.employee,
            shift_datetime,
            True,
        )[1]

        if not (
            get_datetime(self.new_punch) > shift_det.actual_start
            and get_datetime(self.new_punch) < shift_det.actual_end
        ):
            frappe.throw(
                _("Punch must be between {0} and {1}").format(
                    shift_det.actual_start, shift_det.actual_end
                )
            )

    def update_emp_checkin(self):
        for punch in self.details:
            if punch.employee_checkin:
                doc = frappe.get_doc("Employee Checkin", punch.employee_checkin)
            else:
                doc = frappe.new_doc("Employee Checkin")
                doc.time = punch.time
                doc.employee = punch.employee
            doc.skip_auto_attendance = 0
            doc.log_type = punch.type
            doc.source = punch.source
            doc.save()
            if not punch.employee_checkin:
                punch.db_set("employee_checkin", doc.name, update_modified=False)

    @frappe.whitelist()
    def search_checkin(self):
        self.details = []
        shift_datetime = get_datetime(
            f"{getdate(self.date)} {get_time(self.start_time)}"
        )

        employees = [
            emp.get("employee") for emp in self.employees if emp.get("employee")
        ]

        return self.get_checkins(shift_datetime, employees)

    def get_checkins(self, shift_datetime, employee_lst=None):
        employee_list = (
            get_employees_by_shift(self.shift_name, getdate(shift_datetime)) or []
        )

        filters = {}
        if self.get("department"):
            filters["department"] = self.department
            filters["name"] = ["in", employee_list]
        if employee_lst:
            filter_emp = [emp for emp in employee_list if emp in employee_lst]
            filters["name"] = ["in", filter_emp]

        if filters:
            employee_list = frappe.get_all("Employee", filters, pluck="name")

        EmployeeCheckin = frappe.qb.DocType("Employee Checkin")

        data_list = []
        if not employee_list:
            return data_list

        attendance_by_employee = {}
        if employee_list:
            for attendance in frappe.get_all(
                "Attendance",
                filters={
                    "employee": ["in", employee_list],
                    "attendance_date": getdate(shift_datetime),
                    "docstatus": 1,
                },
                fields=["name", "employee"],
            ):
                attendance_by_employee.setdefault(attendance.employee, attendance.name)

        window_by_employee = {}
        for employee in employee_list:
            shift_timings = get_employee_shift_timings(
                employee, get_datetime(shift_datetime), True
            )[1]
            if shift_timings:
                window_by_employee[employee] = (
                    shift_timings.actual_start,
                    shift_timings.actual_end,
                )

        if not window_by_employee and not attendance_by_employee:
            return data_list

        condition = None
        if window_by_employee:
            window_start = min(window[0] for window in window_by_employee.values())
            window_end = max(window[1] for window in window_by_employee.values())
            condition = EmployeeCheckin.time.between(window_start, window_end)

        if attendance_by_employee:
            attendance_condition = EmployeeCheckin.attendance.isin(
                list(attendance_by_employee.values())
            )
            condition = (
                attendance_condition
                if condition is None
                else condition | attendance_condition
            )

        rows = (
            frappe.qb.from_(EmployeeCheckin)
            .select(
                Date(EmployeeCheckin.time).as_("date"),
                EmployeeCheckin.log_type.as_("type"),
                EmployeeCheckin.time,
                EmployeeCheckin.source,
                EmployeeCheckin.name.as_("employee_checkin"),
                EmployeeCheckin.employee,
                EmployeeCheckin.employee_name.as_("custom_employee_name"),
                EmployeeCheckin.attendance,
            )
            .where(EmployeeCheckin.employee.isin(employee_list))
            .where(condition)
            .orderby(EmployeeCheckin.time)
            .run(as_dict=True)
        )

        rows_by_employee = {}
        for row in rows:
            employee = row.employee
            linked_attendance = row.pop("attendance")
            window = window_by_employee.get(employee)
            in_window = bool(window) and window[0] <= row.time <= window[1]
            linked = bool(linked_attendance) and (
                linked_attendance == attendance_by_employee.get(employee)
            )
            if in_window or linked:
                rows_by_employee.setdefault(employee, []).append(row)

        for employee in employee_list:
            if rows_by_employee.get(employee):
                data_list.append(rows_by_employee[employee])
        return data_list


def process_attendance_from_rows(rows, employee, shift_type, date):
    date = getdate(date)

    # -------------------------------------------------
    # Skip if there is no missing employee_checkin
    # -------------------------------------------------
    if not any(row.get("employee_checkin") is not None for row in rows):
        return

    # -------------------------------------------------
    # Get Shift Type
    # -------------------------------------------------.
    shift = frappe.get_cached_doc("Shift Type", shift_type)

    start_time = shift.start_time
    end_time = shift.end_time

    late_entry_grace_period = shift.late_entry_grace_period or 0

    # -------------------------------------------------
    # Cancel old attendance
    # -------------------------------------------------
    existing_attendance = frappe.db.exists(
        "Attendance",
        {
            "employee": employee,
            "attendance_date": date,
            "docstatus": 1,
        },
    )

    if existing_attendance:
        old_attendance = frappe.get_doc("Attendance", existing_attendance)
        old_attendance.cancel()

    # -------------------------------------------------
    # Collect punches
    # -------------------------------------------------
    punches = []

    # Don't modify original rows
    sorted_rows = sorted(
        rows,
        key=lambda x: get_datetime(x.time) if x.time else get_datetime("1900-01-01"),
    )

    for row in sorted_rows:
        if not row.get("time"):
            continue

        dt = get_datetime(row.get("time"))

        punches.append(dt)

    # No punches
    if not punches:
        return

    # -------------------------------------------------
    # First IN / Last OUT
    # -------------------------------------------------
    in_time = punches[0]
    out_time = punches[-1]

    # Invalid punch sequence
    if out_time <= in_time:
        return

    # -------------------------------------------------
    # Working Hours
    # -------------------------------------------------
    working_hours = (out_time - in_time).total_seconds() / 3600

    # -------------------------------------------------
    # Shift Start / End
    # -------------------------------------------------
    shift_start = get_datetime(f"{date} {start_time}")

    shift_end = get_datetime(f"{date} {end_time}")

    # -------------------------------------------------
    # Overnight Shift
    # -------------------------------------------------
    if shift_end <= shift_start:
        shift_end = add_days(shift_end, 1)

    # -------------------------------------------------
    # Late Entry
    # -------------------------------------------------
    late_entry = 0

    allowed_late_time = shift_start + timedelta(minutes=late_entry_grace_period)

    if in_time > allowed_late_time:
        late_entry = 1

    # -------------------------------------------------
    # Early Exit
    # -------------------------------------------------
    early_exit = 0

    if out_time < shift_end:
        early_exit = 1

    # -------------------------------------------------
    # Create Attendance
    # -------------------------------------------------
    att = frappe.new_doc("Attendance")

    att.employee = employee
    att.attendance_date = date
    att.shift = shift_type

    att.in_time = in_time
    att.out_time = out_time
    att.working_hours = working_hours

    att.late_entry = late_entry
    att.early_exit = early_exit

    # -------------------------------------------------
    # Attendance Status
    # -------------------------------------------------
    if working_hours > 0:
        att.status = "Present"
    else:
        att.status = "Absent"

    att.insert()
    att.submit()

    # -------------------------------------------------
    # Link Employee Checkins with Attendance
    # -------------------------------------------------
    frappe.db.set_value(
        "Employee Checkin",
        {
            "employee": employee,
            "time": ["between", [in_time, out_time]],
        },
        "attendance",
        att.name,
    )


@frappe.whitelist()
def add_checkins(details, date, shift_name):
    if isinstance(details, str):
        details = frappe.json.loads(details)

    date = getdate(date)
    employee_details = {}

    # group by employee
    for entry in details:
        emp = entry["employee"]
        employee_details.setdefault(emp, []).append(entry)

    merged_data = []

    for emp, emp_rows in employee_details.items():
        one_data = check_employee_punch(emp_rows, date, shift_name)

        merged_data.extend(one_data)

    # fix idx
    for i, row in enumerate(merged_data, start=1):
        row["idx"] = i

    return merged_data


def check_employee_punch(employee_details, shift_date, shift_name):
    if not employee_details:
        return employee_details

    shift_doc = frappe.get_cached_doc("Shift Type", shift_name)

    start_time_obj = get_time(shift_doc.start_time)
    end_time_obj = get_time(shift_doc.end_time)

    is_night_shift = start_time_obj > end_time_obj

    employee_details.sort(key=lambda x: get_datetime(x["time"]))

    shift_start_dt = get_datetime(f"{shift_date} {start_time_obj}")

    if is_night_shift:
        shift_end_date = add_to_date(shift_date, days=1)
    else:
        shift_end_date = shift_date

    shift_end_dt = get_datetime(f"{shift_end_date} {end_time_obj}")

    # -----------------------------------------
    # Saare actual punches ka first/last nikaalo
    # (window ke andar-bahar filter mat karo)
    # -----------------------------------------

    all_punch_times = [get_datetime(d["time"]) for d in employee_details]

    if not all_punch_times:
        return employee_details

    first_dt = min(all_punch_times)
    last_dt = max(all_punch_times)

    # -----------------------------------------
    # Missing time BEFORE first actual punch
    # Sirf tab add karo jab first punch shift
    # start ke BAAD hua ho (pehle se hua ho to
    # kuch add nahi karna)
    # -----------------------------------------

    if first_dt > shift_start_dt:
        new_in = make_row(employee_details, "IN", shift_start_dt)

        new_out = make_row(employee_details, "OUT", first_dt)

        employee_details.append(new_in)
        employee_details.append(new_out)

    # -----------------------------------------
    # Missing time AFTER last actual punch
    # Sirf tab add karo jab last punch shift
    # end se PEHLE hua ho
    # -----------------------------------------

    if last_dt < shift_end_dt:
        new_in = make_row(employee_details, "IN", last_dt)

        new_out = make_row(employee_details, "OUT", shift_end_dt)

        employee_details.append(new_in)
        employee_details.append(new_out)

    # -----------------------------------------
    # Final sorting
    # -----------------------------------------

    employee_details.sort(key=lambda x: get_datetime(x["time"]))

    return employee_details


def make_row(employee_details, punch_type, dt):
    last = employee_details[-1]

    return {
        "date": str(dt.date()),
        "type": punch_type,
        "employee": last.get("employee"),
        "custom_employee_name": last.get("custom_employee_name"),
        "time": dt,
        "source": "Employee Checkin",
        "idx": "",
    }


def process_checkins(docname):
    try:
        doc = frappe.get_doc("Holiday Punch", docname)

        # Step 1: Cancel old attendance
        employees = list({row.employee for row in doc.details if row.employee})
        if employees:
            attendances = frappe.get_all(
                "Attendance",
                filters={
                    "employee": ["in", employees],
                    "attendance_date": doc.date,
                    "docstatus": 1,
                },
                pluck="name",
            )
            if attendances:
                frappe.db.set_value(
                    "Attendance", {"name": ["in", attendances]}, "docstatus", 2
                )

        # Step 2: Create / Update checkins
        doc.update_emp_checkin()

        # Step 3: Update workflow state
        frappe.db.set_value(doc.doctype, doc.name, "workflow_state", "Checkin Created")

        frappe.db.commit()

    except Exception:
        frappe.db.rollback()
        log = frappe.log_error(
            title=f"Holiday Punch: {docname}", message=frappe.get_traceback()
        )

        frappe.db.set_value(
            "Holiday Punch",
            docname,
            {
                "workflow_state": "Failed",
                "error_details": "Process failed. Check Error Log: {0}".format(
                    log.name
                ),
            },
        )

        frappe.db.commit()


def process_attendance(docname):
    try:
        doc = frappe.get_doc("Holiday Punch", docname)

        emp_map = {}

        # Group by employee
        for row in doc.details:
            if not row.employee:
                continue
            emp_map.setdefault(row.employee, []).append(row)

        failed_employees = []
        for emp, rows in emp_map.items():
            frappe.db.savepoint("holiday_punch_attendance")
            try:
                process_attendance_from_rows(rows, emp, doc.shift_name, doc.date)
            except Exception:
                frappe.db.rollback(save_point="holiday_punch_attendance")
                log = frappe.log_error(
                    title=f"Holiday Punch: {docname} ({emp})",
                    message=frappe.get_traceback(),
                )
                failed_employees.append("{0} (Error Log: {1})".format(emp, log.name))

        if failed_employees:
            frappe.db.set_value(
                doc.doctype,
                doc.name,
                {
                    "workflow_state": "Failed",
                    "error_details": "Attendance failed for: {0}".format(
                        ", ".join(failed_employees)
                    ),
                },
            )
        else:
            frappe.db.set_value(
                doc.doctype, doc.name, "workflow_state", "Attendance Created"
            )

        frappe.db.commit()

    except Exception:
        frappe.db.rollback()
        log = frappe.log_error(
            title=f"Holiday Punch: {docname}", message=frappe.get_traceback()
        )

        frappe.db.set_value(
            "Holiday Punch",
            docname,
            {
                "workflow_state": "Failed",
                "error_details": "Process failed. Check Error Log: {0}".format(
                    log.name
                ),
            },
        )

        frappe.db.commit()


@frappe.whitelist()
def enqueue_modify_checkin(docname):
    job = frappe.enqueue(
        method="gke_customization.gke_hrms.doctype.holiday_punch.holiday_punch.process_checkins",
        queue="long",
        timeout=10000,
        job_name=f"Modify Checkin {docname}",
        job_id=f"holiday_punch::process_checkins::{docname}",
        deduplicate=True,
        now=False,
        docname=docname,
    )

    if not job:
        frappe.msgprint(_("A job for {0} is already queued or running.").format(docname))
        return None

    frappe.msgprint(_("Job Enqueued: {0}").format(job.id))
    return job.id


@frappe.whitelist()
def enqueue_modify_attendance(docname):
    job = frappe.enqueue(
        method="gke_customization.gke_hrms.doctype.holiday_punch.holiday_punch.process_attendance",
        queue="long",
        timeout=10000,
        job_name=f"Modify Attendance {docname}",
        job_id=f"holiday_punch::process_attendance::{docname}",
        deduplicate=True,
        now=False,
        docname=docname,
    )

    if not job:
        frappe.msgprint(_("A job for {0} is already queued or running.").format(docname))
        return None

    frappe.msgprint(_("Job Enqueued: {0}").format(job.id))
    return job.id


@frappe.whitelist()
def get_employees(doc):
    doc = frappe._dict(frappe.parse_json(doc))

    # store combined employee + shift assignment data
    merge_data = []

    # =====================================================
    # Employee Filters
    # =====================================================
    employee_filters = {
        "company": doc.company,
        "default_shift": doc.shift_name,
        "status": "Active",
    }

    # add department filter dynamically
    if doc.department:
        employee_filters["department"] = doc.department

    # =====================================================
    # Fetch employees whose default shift
    # matches selected shift
    # =====================================================
    employee_data = frappe.get_all(
        "Employee",
        filters=employee_filters,
        fields=["name", "employee_name", "default_shift"],
    )
    merge_data.extend(employee_data)

    # =====================================================
    # Fetch employees having valid shift assignment
    # for selected date and shift
    # =====================================================
    shift_assignments = get_shift(doc.company, doc.shift_name, doc.date)

    # merge shift assignment records
    merge_data.extend(shift_assignments)

    # =====================================================
    # Remove duplicate employees  Duplicate check based on employee ID (name)
    # =====================================================
    employee_data = []
    seen = set()

    for row in merge_data:
        if row["name"] not in seen:
            employee_data.append(row)
            seen.add(row["name"])

    # =====================================================
    # Cross verify actual shift of employee # Shift Assignment takes priority over default shift
    # =====================================================
    data = []
    for row in get_employees_shift([row["name"] for row in employee_data], doc.date):
        if row.get("default_shift") == doc.shift_name:
            data.append(row)

    return data


# get shift  with name, employee_name, default_shift
@frappe.whitelist()
def get_shift(company, shift_type, for_date=None):
    if not for_date:
        for_date = today()

    for_date = getdate(for_date)

    # =====================================================
    # Fetch valid shift assignments
    #
    # Conditions:
    # 1. start_date <= selected date
    # 2. end_date is blank (open assignment)
    #    OR
    # 3. end_date >= selected date
    # =====================================================
    shift_data = frappe.get_all(
        "Shift Assignment",
        filters={
            "company": company,
            "shift_type": shift_type,
            "docstatus": 1,
            "status": "Active",
        },
        or_filters=[
            {"start_date": ("<=", for_date)},
            {"start_date": (">=", for_date)},
            {"end_date": ("is", "not set")},
            {"end_date": (">=", for_date)},
        ],
        fields=["employee as name", "employee_name", "shift_type as default_shift"],
    )

    return shift_data


# Get employee final shift for selected date
@frappe.whitelist()
def get_employee_shift(employee, for_date=None):
    if not for_date:
        for_date = today()

    for_date = getdate(for_date)

    # Fetch active shift assignment
    #
    # Conditions:
    # 1. start_date <= selected date
    # 2. end_date is blank OR
    # 3. end_date exists
    shift = frappe.db.get_all(
        "Shift Assignment",
        filters={"employee": employee, "docstatus": 1, "status": "Active"},
        or_filters=[
            {"start_date": ("<=", for_date)},
            {"start_date": (">=", for_date)},
            {"end_date": ("is", "not set")},
            {"end_date": ("is", "set")},
        ],
        fields=["shift_type as default_shift", "employee as name"],
    )

    # =====================================================
    # If valid shift assignment exists,
    # return assigned shift
    # =====================================================
    if shift:
        return shift

    # =====================================================
    # Fallback to Employee default shift
    # when no Shift Assignment exists
    # ====================================================
    return frappe.db.get_all(
        "Employee", filters={"name": employee}, fields=["default_shift", "name"]
    )


def get_employees_shift(employees, for_date=None):
    """Batched version of get_employee_shift for a list of employees."""
    if not employees:
        return []

    for_date = getdate(for_date or today())

    assignments = frappe.get_all(
        "Shift Assignment",
        filters={"employee": ["in", employees], "docstatus": 1, "status": "Active"},
        or_filters=[
            {"start_date": ("<=", for_date)},
            {"start_date": (">=", for_date)},
            {"end_date": ("is", "not set")},
            {"end_date": ("is", "set")},
        ],
        fields=["shift_type as default_shift", "employee as name"],
    )
    assigned_employees = {row.name for row in assignments}

    missing_employees = [
        employee for employee in employees if employee not in assigned_employees
    ]
    default_shifts = {}
    if missing_employees:
        default_shifts = {
            row.name: row
            for row in frappe.get_all(
                "Employee",
                filters={"name": ["in", missing_employees]},
                fields=["default_shift", "name"],
            )
        }

    assignments_by_employee = {}
    for row in assignments:
        assignments_by_employee.setdefault(row.name, []).append(row)

    result = []
    for employee in employees:
        if employee in assignments_by_employee:
            result.extend(assignments_by_employee[employee])
        elif employee in default_shifts:
            result.append(default_shifts[employee])
    return result
