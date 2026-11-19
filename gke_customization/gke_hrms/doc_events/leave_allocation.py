from datetime import datetime, timedelta

import frappe
from frappe.utils import add_days, flt, get_first_day, get_last_day, getdate


@frappe.whitelist()
def get_earned_leave_allocation():
    """Allocate earned leaves to employees as per the new attendance-wise policy."""
    e_leave_types = get_earned_leaves()
    today = frappe.flags.current_date or getdate()

    current_month_start = get_first_day(today)
    current_month_end = get_last_day(today)

    for e_leave_type in e_leave_types:
        leave_allocations = get_leave_allocations(today, e_leave_type.name)
        if not leave_allocations:
            continue

        policy_by_assignment = get_leave_policy_by_assignment(leave_allocations)
        allocations_with_ledger = get_allocations_with_monthly_ledger(
            leave_allocations, e_leave_type.name, current_month_start, current_month_end
        )
        attendance_count = get_attendance_count_by_from_date(leave_allocations, today)
        annual_allocation_by_policy = {}

        for allocation in leave_allocations:
            if not allocation.leave_policy_assignment and not allocation.leave_policy:
                continue

            leave_policy = (
                allocation.leave_policy
                if allocation.leave_policy
                else policy_by_assignment.get(allocation.leave_policy_assignment)
            )

            if leave_policy not in annual_allocation_by_policy:
                annual_allocation_by_policy[leave_policy] = get_annual_allocation(
                    leave_policy, e_leave_type.name
                )
            annual_allocation = annual_allocation_by_policy[leave_policy]

            total_attendance = attendance_count.get(
                (getdate(allocation.from_date), allocation.employee), 0
            )

            if not total_attendance or total_attendance < e_leave_type.applicable_after:
                continue

            if (allocation.name, allocation.employee) in allocations_with_ledger:
                continue

            update_attendance_wise_leave(
                allocation, annual_allocation, e_leave_type, total_attendance
            )


def get_attendance_count_by_from_date(leave_allocations, to_date):
    """Return present attendance count keyed by (allocation from_date, employee)."""
    employees_by_from_date = {}
    for allocation in leave_allocations:
        employees_by_from_date.setdefault(getdate(allocation.from_date), set()).add(
            allocation.employee
        )

    attendance_count = {}
    for from_date, employees in employees_by_from_date.items():
        rows = frappe.get_all(
            "Attendance",
            filters={
                "status": ["in", ["Present", "Work From Home"]],
                "docstatus": 1,
                "employee": ["in", list(employees)],
                "attendance_date": ["between", [from_date, to_date]],
            },
            fields=["employee", "count(name) as total_attendance"],
            group_by="employee",
        )
        for row in rows:
            attendance_count[(from_date, row.employee)] = row.total_attendance

    return attendance_count


def get_leave_policy_by_assignment(leave_allocations):
    assignment_names = list(
        {
            allocation.leave_policy_assignment
            for allocation in leave_allocations
            if allocation.leave_policy_assignment and not allocation.leave_policy
        }
    )
    if not assignment_names:
        return {}

    return dict(
        frappe.get_all(
            "Leave Policy Assignment",
            filters={"name": ["in", assignment_names]},
            fields=["name", "leave_policy"],
            as_list=True,
        )
    )


def get_allocations_with_monthly_ledger(
    leave_allocations, leave_type, month_start, month_end
):
    """Return (allocation, employee) pairs that already have a ledger entry this month."""
    ledger_entries = frappe.get_all(
        "Leave Ledger Entry",
        filters={
            "leave_type": leave_type,
            "transaction_type": "Leave Allocation",
            "transaction_name": [
                "in",
                [allocation.name for allocation in leave_allocations],
            ],
            "from_date": ["between", [month_start, month_end]],
            "is_expired": 0,
        },
        fields=["transaction_name", "employee"],
    )
    return {(entry.transaction_name, entry.employee) for entry in ledger_entries}


def update_attendance_wise_leave(
    allocation,
    annual_allocation,
    e_leave_type,
    total_attendance,
):
    """Allocate attendance-wise earned leave as per the leave policy."""
    allocation = frappe.get_doc("Leave Allocation", allocation.name)
    already_allocated = flt(allocation.total_leaves_allocated)

    # get total earned with rounding

    earned_total = get_monthly_attendance_wise_leave(
        annual_allocation,
        e_leave_type.earned_leave_frequency,
        e_leave_type.applicable_after,
        e_leave_type.rounding,
        total_attendance,
    )

    # respect max allowed

    max_allowed = e_leave_type.max_leaves_allowed

    if max_allowed and earned_total > max_allowed:
        earned_total = max_allowed

    # calculate new leaves

    earned_leaves = flt(earned_total) - flt(already_allocated)

    if earned_leaves <= 0:
        return

    # check annual limit

    new_allocation = already_allocated + earned_leaves

    if annual_allocation and new_allocation > annual_allocation:
        earned_leaves = annual_allocation - already_allocated
        new_allocation = annual_allocation

    if earned_leaves <= 0:
        return

    today_date = frappe.flags.current_date or getdate()

    # update allocation

    allocation.db_set(
        "new_leaves_allocated",
        new_allocation,
        update_modified=False,
    )

    allocation.db_set(
        "total_leaves_allocated",
        new_allocation,
        update_modified=False,
    )

    # ledger

    create_additional_leave_ledger_entry(
        allocation,
        earned_leaves,
        today_date,
    )

    allocation.add_comment(
        comment_type="Info",
        text=f"Allocated {earned_leaves} leave(s) via scheduler",
    )


def get_monthly_attendance_wise_leave(
    annual_leaves, leave_frequency, leave_applicable, leave_rounding, total_attendance
):
    earned_leaves = 0.0
    if total_attendance >= leave_applicable:
        earned_units = 0.0
        if leave_rounding == "0.5":
            earned_units = round(total_attendance / leave_applicable)
        else:
            earned_units = flt(total_attendance / leave_applicable)

        earned_leaves = round_earned_leaves(earned_units, leave_rounding)

    return earned_leaves


def round_earned_leaves(earned_units, rounding):
    if not rounding:
        return earned_units

    if rounding == "0.5":
        earned_units = flt(earned_units) * flt(rounding)
    else:
        earned_units = round(earned_units)

    return earned_units


def create_additional_leave_ledger_entry(allocation, leaves, date):
    """Create a leave ledger entry for the additionally allocated leaves."""
    allocation.new_leaves_allocated = leaves
    allocation.from_date = date
    allocation.unused_leaves = 0
    if allocation.leave_type == "Compensatory Off":
        leave_type = frappe.db.get_value(
            "Leave Type", {"name": allocation.leave_type}, ["applicable_after"]
        )
        allocation.to_date = frappe.utils.add_days(date, leave_type)
    allocation.create_leave_ledger_entry()


def get_annual_allocation(leave_policy, leave_type):
    """Return the annual allocation of the leave type from the Leave Policy details."""
    annual_allocation = frappe.db.get_value(
        "Leave Policy Detail",
        filters={"parent": leave_policy, "leave_type": leave_type},
        fieldname=["annual_allocation"],
    )

    return annual_allocation


def get_earned_leaves():
    return frappe.get_all(
        "Leave Type",
        fields=[
            "name",
            "max_leaves_allowed",
            "earned_leave_frequency",
            "rounding",
            "allocate_on_day",
            "applicable_after",
        ],
        filters={"is_earned_leave": 1},
    )


def get_leave_allocations(date, leave_type):
    employee = frappe.qb.DocType("Employee")
    leave_allocation = frappe.qb.DocType("Leave Allocation")
    query = (
        frappe.qb.from_(leave_allocation)
        .join(employee)
        .on(leave_allocation.employee == employee.name)
        .select(
            leave_allocation.name,
            leave_allocation.employee,
            leave_allocation.from_date,
            leave_allocation.to_date,
            leave_allocation.leave_type,
            leave_allocation.leave_policy_assignment,
            leave_allocation.leave_policy,
        )
        .where(
            (date >= leave_allocation.from_date)
            & (date <= leave_allocation.to_date)
            & (leave_allocation.docstatus == 1)
            & (leave_allocation.leave_type == leave_type)
            & (employee.status != "Left")
        )
    )
    data = query.run(as_dict=1) or []

    return data


# infirmary_leave
@frappe.whitelist()
def infirmary_leave_allocation():
    leave_type = frappe.db.get_value(
        "Leave Type",
        {
            "is_carry_forward": 0,
            "is_earned_leave": 0,
            "is_lwp": 0,
            "is_compensatory": 0,
        },
        ["name", "applicable_after"],
        as_dict=True,
    )
    if not leave_type:
        return

    today = datetime.today().date()
    one_year_ago = today - timedelta(days=leave_type.applicable_after)

    emp_leave_grade = frappe.db.get_all(
        "Leave Employee Grade",
        filters={"parent": leave_type.name},
        fields=["employee_grade"],
    )

    annual_allocation_by_policy = {}

    for emp_grade in emp_leave_grade:
        employees = frappe.get_all(
            "Employee",
            filters={"status": "Active", "grade": emp_grade.employee_grade},
            fields=["name", "date_of_joining", "grade"],
        )
        if not employees:
            continue

        employee_names = [emp.name for emp in employees]
        policy_assignment_by_employee = get_policy_assignment_by_employee(
            employee_names
        )
        allocations_by_assignment = get_allocations_by_policy_assignment(
            employee_names, leave_type.name
        )

        for emp in employees:
            doj = getdate(emp.date_of_joining)

            leave_policy_ass = policy_assignment_by_employee.get(emp.name)
            if not leave_policy_ass:
                continue

            from_date = leave_policy_ass.effective_from
            to_date = leave_policy_ass.effective_to

            if leave_policy_ass.leave_policy not in annual_allocation_by_policy:
                annual_allocation_by_policy[
                    leave_policy_ass.leave_policy
                ] = get_annual_allocation(
                    leave_policy_ass.leave_policy, leave_type.name
                )
            annual_allocation = annual_allocation_by_policy[
                leave_policy_ass.leave_policy
            ]
            if not annual_allocation:
                continue

            existing_allocations = [
                alloc
                for alloc in allocations_by_assignment.get(
                    (emp.name, leave_policy_ass.name), []
                )
                if alloc.from_date == from_date and alloc.to_date == to_date
            ]

            # If employee has completed 1 year
            if doj and doj <= one_year_ago:
                if existing_allocations:
                    for alloc in existing_allocations:
                        allocation_doc = frappe.get_doc("Leave Allocation", alloc.name)
                        if allocation_doc.total_leaves_allocated == annual_allocation:
                            allocation_doc.db_set(
                                "total_leaves_allocated",
                                annual_allocation,
                                update_modified=False,
                            )
                            allocation_doc.db_set(
                                "new_leaves_allocated",
                                annual_allocation,
                                update_modified=False,
                            )
                else:
                    # No existing allocation, create a new one
                    allocation = frappe.new_doc("Leave Allocation")
                    allocation.employee = emp.name
                    allocation.leave_type = leave_type.name
                    allocation.from_date = from_date
                    allocation.to_date = to_date
                    allocation.leave_policy_assignment = leave_policy_ass.name
                    allocation.new_leaves_allocated = annual_allocation
                    allocation.total_leaves_allocated = annual_allocation
                    allocation.insert(ignore_permissions=True)
                    allocation.submit()

            # If employee has NOT completed 1 year then cancel
            else:
                for alloc in existing_allocations:
                    allocation_doc = frappe.get_doc("Leave Allocation", alloc.name)
                    allocation_doc.cancel()


@frappe.whitelist()
def compOff_leave_allocation():
    """Allocate Compensatory Off leave."""
    leave_type = frappe.db.get_value(
        "Leave Type", {"is_compensatory": 1}, ["name", "applicable_after"], as_dict=True
    )
    if not leave_type:
        return

    emp_leave_grade = frappe.db.get_all(
        "Leave Employee Grade",
        filters={"parent": leave_type.name},
        fields=["employee_grade"],
    )

    allowed_grades = [e.employee_grade for e in emp_leave_grade]

    today = frappe.utils.today()
    yesterday = frappe.utils.add_days(today, -1)

    emp_checkin = frappe.db.sql(
        """
                SELECT distinct(employee) as employee,date(time) as date
                    FROM `tabEmployee Checkin`
                    WHERE DATE(time) BETWEEN %s AND %s
            """,
        (yesterday, today),
        as_dict=1,
    )

    employee_ids = list({emp.employee for emp in emp_checkin if emp.employee})
    if not employee_ids:
        return

    employee_details = {
        row.name: row
        for row in frappe.get_all(
            "Employee",
            filters={"name": ["in", employee_ids]},
            fields=["name", "grade", "holiday_list"],
        )
    }
    weekly_off_dates = get_weekly_off_dates(
        [row.holiday_list for row in employee_details.values() if row.holiday_list],
        yesterday,
        today,
    )
    policy_assignment_by_employee = get_policy_assignment_by_employee(employee_ids)

    for emp in emp_checkin:
        employee_id = emp.get("employee")
        checkin_date = emp.get("date")

        if not employee_id or not checkin_date:
            continue

        employee = employee_details.get(employee_id)
        if not employee or not employee.holiday_list:
            continue

        weekoff_date = getdate(checkin_date)
        if (employee.holiday_list, weekoff_date) not in weekly_off_dates:
            continue

        if employee.grade not in allowed_grades:
            continue

        leave_policy_ass = policy_assignment_by_employee.get(employee_id)
        if not leave_policy_ass:
            continue

        from_date = weekoff_date
        to_date = add_days(weekoff_date, leave_type.applicable_after)

        allocation = frappe.get_all(
            "Leave Allocation",
            filters={
                "employee": employee_id,
                "leave_type": leave_type.name,
                "leave_policy_assignment": leave_policy_ass.name,
                "docstatus": 1,
                "from_date": ["between", ["2025-05-01", leave_policy_ass.effective_to]],
                "to_date": ["between", ["2025-05-01", leave_policy_ass.effective_to]],
            },
        )

        if allocation:
            # Already exists - update and create ledger
            alloc_doc = frappe.get_doc("Leave Allocation", allocation[0].name)

            # Avoid duplicate ledger entry on same weekoff_date
            existing_entry = frappe.db.exists(
                "Leave Ledger Entry",
                {
                    "transaction_name": alloc_doc.name,
                    "transaction_type": "Leave Allocation",
                    "from_date": from_date,
                    "to_date": to_date,
                },
            )
            if existing_entry:
                continue

            alloc_doc.total_leaves_allocated += 1
            alloc_doc.db_set(
                "total_leaves_allocated",
                alloc_doc.total_leaves_allocated,
                update_modified=False,
            )
            create_additional_leave_ledger_entry(alloc_doc, 1, weekoff_date)

        else:
            # Create new allocation
            alloc_doc = frappe.new_doc("Leave Allocation")
            alloc_doc.employee = employee_id
            alloc_doc.leave_type = leave_type.name
            alloc_doc.leave_policy_assignment = leave_policy_ass.name
            alloc_doc.from_date = leave_policy_ass.effective_from
            alloc_doc.to_date = leave_policy_ass.effective_to
            alloc_doc.new_leaves_allocated = 1
            alloc_doc.total_leaves_allocated = 1
            alloc_doc.docstatus = 1
            alloc_doc.insert(ignore_permissions=True)
            alloc_doc.submit()


def get_weekly_off_dates(holiday_lists, from_date, to_date):
    """Return a set of (holiday_list, date) pairs for weekly offs in the date range."""
    if not holiday_lists:
        return set()

    holidays = frappe.get_all(
        "Holiday",
        filters={
            "parent": ["in", list(set(holiday_lists))],
            "weekly_off": 1,
            "holiday_date": ["between", [from_date, to_date]],
        },
        fields=["parent", "holiday_date"],
    )
    return {(row.parent, getdate(row.holiday_date)) for row in holidays}


def get_policy_assignment_by_employee(employees):
    """Return the first submitted Leave Policy Assignment of each employee."""
    policy_assignment_by_employee = {}
    for row in frappe.get_all(
        "Leave Policy Assignment",
        filters={"employee": ["in", employees], "docstatus": 1},
        fields=["name", "employee", "effective_from", "effective_to", "leave_policy"],
    ):
        policy_assignment_by_employee.setdefault(row.employee, row)

    return policy_assignment_by_employee


def get_allocations_by_policy_assignment(employees, leave_type):
    """Return submitted Leave Allocations grouped by (employee, leave_policy_assignment)."""
    allocations_by_assignment = {}
    for row in frappe.get_all(
        "Leave Allocation",
        filters={
            "employee": ["in", employees],
            "leave_type": leave_type,
            "docstatus": 1,
        },
        fields=[
            "name",
            "employee",
            "leave_policy_assignment",
            "from_date",
            "to_date",
        ],
    ):
        allocations_by_assignment.setdefault(
            (row.employee, row.leave_policy_assignment), []
        ).append(row)

    return allocations_by_assignment
