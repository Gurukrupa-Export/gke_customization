import frappe
from frappe import _
from frappe.utils import (
    getdate, 
    flt, 
    formatdate, 
    add_days, 
    get_first_day,
	get_last_day
    )
from datetime import timedelta, datetime

#as per new policy
"""Allocate earned leaves to Employees"""
@frappe.whitelist()
def get_earned_leave_allocation():
    e_leave_types = get_earned_leaves()
    today = frappe.flags.current_date or getdate()
	
    # frappe.throw(f"{e_leave_types}") 
    for e_leave_type in e_leave_types:
        leave_allocations = get_leave_allocations(today, e_leave_type.name)
        
        # frappe.throw(f"{leave_allocations}")
        for allocation in leave_allocations:
            if not allocation.leave_policy_assignment and not allocation.leave_policy:
                continue
            
            """geting leave policy from Allocation or Policy Assignment"""
            leave_policy = (
                allocation.leave_policy
                if allocation.leave_policy
                else frappe.db.get_value(
                    "Leave Policy Assignment", allocation.leave_policy_assignment, ["leave_policy"]
                )
            )

            """geting leave type's annual allocation from leave Policy's child table"""
            annual_allocation = get_annual_allocation(leave_policy, e_leave_type.name)

            from_date = allocation.from_date
            # from_date = '2025-05-01'
            total_attendance = frappe.db.count("Attendance", {
                "status": ["in", ["Present", "Work From Home"]],
                "docstatus": 1,
                "employee": allocation.employee,
                "attendance_date": ["between", [from_date, today]]
            })
            
            if not total_attendance or total_attendance < e_leave_type.applicable_after:
                continue
            
            current_month_start = get_first_day(today)
            current_month_end = get_last_day(today)

            # Check if ledger entry already exists for this employee in current month
            existing_ledger = frappe.db.exists("Leave Ledger Entry", {
                "employee": allocation.employee,
                "leave_type": e_leave_type.name,
                "transaction_type": "Leave Allocation",
                "transaction_name": allocation.name,
                "from_date": ["between", [current_month_start, current_month_end]],
                "to_date": ["between", [allocation.to_date, allocation.to_date]],
                "is_expired": 0,
                "leaves": [">", 0]
            })
 
            if existing_ledger:
                continue
            
            update_attendance_wise_leave(allocation, annual_allocation, e_leave_type, total_attendance)

"""get leave accural attendance wise as per the policy"""
def update_attendance_wise_leave(allocation, annual_allocation, e_leave_type, total_attendance):
    allocation = frappe.get_doc("Leave Allocation", allocation.name)
    annual_allocation = flt(annual_allocation, allocation.precision("total_leaves_allocated"))

    """get attendance wise earned leaves"""
    earned_leaves = get_monthly_attendance_wise_leave(
        annual_allocation,
        e_leave_type.earned_leave_frequency,
        e_leave_type.applicable_after,
        e_leave_type.rounding,
        total_attendance
    )
    
    """checking exiting leaves count"""
    new_allocation = flt(allocation.total_leaves_allocated) + flt(earned_leaves)
    new_allocation_without_cf = flt(
        flt(allocation.get_existing_leave_count()) + flt(earned_leaves),
        allocation.precision("total_leaves_allocated"),
    )

    """checking max leaves allowed condition"""
    if new_allocation > e_leave_type.max_leaves_allowed and e_leave_type.max_leaves_allowed > 0:
        new_allocation = e_leave_type.max_leaves_allowed

    """ annual allocation as per policy should not be exceeded """
    if (new_allocation != allocation.total_leaves_allocated and new_allocation_without_cf <= annual_allocation):
        today_date = frappe.flags.current_date or getdate()

        allocation.db_set("total_leaves_allocated", new_allocation, update_modified=False)
        create_additional_leave_ledger_entry(allocation, earned_leaves, today_date) #creating ledger as per new allocation

        if e_leave_type.allocate_on_day:
            text = _(
                "Allocated {0} leave(s) via scheduler on {1} based on the 'Allocate on Day' option set to {2}"
            ).format(
                frappe.bold(earned_leaves), frappe.bold(formatdate(today_date)), e_leave_type.allocate_on_day
            )

        allocation.add_comment(comment_type="Info", text=text)
            
def get_monthly_attendance_wise_leave(annual_leaves,leave_frequency,leave_applicable,leave_rounding, total_attendance):
    earned_leaves = 0.0
    if total_attendance >= leave_applicable:
        earned_units = 0.0
        if leave_rounding == "0.5":
            earned_units = round(total_attendance / leave_applicable)
        else:
            earned_units = flt(total_attendance / leave_applicable)
        
        earned_leaves = round_earned_leaves(earned_units, leave_rounding)
        # frappe.throw(f"monthly {total_attendance} || {leave_applicable} || {earned_units} || {earned_leaves} || {leave_rounding}")
    # frappe.throw(f"earned_leaves {earned_leaves}")
    return earned_leaves

def round_earned_leaves(earned_units, rounding):
    if not rounding:
        return earned_units

    if rounding == "0.5":
        earned_units = flt(earned_units) * flt(rounding)
    else:
        earned_units = round(earned_units)

    return earned_units

"""Create leave ledger entry for leave types"""
def create_additional_leave_ledger_entry(allocation, leaves, date):
    # frappe.throw(f"{allocation.to_date}, {leave_type}, {date}")
    allocation.new_leaves_allocated = leaves
    allocation.from_date = date
    allocation.unused_leaves = 0
    if allocation.leave_type == 'Compensatory Off':
        leave_type = frappe.db.get_value("Leave Type", 
            {'name': allocation.leave_type}, ['applicable_after'] )
        allocation.to_date = frappe.utils.add_days(date, leave_type)
    allocation.create_leave_ledger_entry()

"""geting leave type's annual allocation from leave Policy's child table"""
def get_annual_allocation(leave_policy, leave_type):
    annual_allocation = frappe.db.get_value(
        "Leave Policy Detail",
        filters={"parent": leave_policy, "leave_type": leave_type},
        fieldname=["annual_allocation"],
    )

    return annual_allocation

"""get Earned leave from leave type"""
def get_earned_leaves():
	return frappe.get_all(
		"Leave Type",
		fields=[
			"name",
			"max_leaves_allowed",
			"earned_leave_frequency",
			"rounding",
			"allocate_on_day",
            "applicable_after"
		],
		filters={"is_earned_leave": 1},
	)

"""get employee leave allocations"""
def get_leave_allocations(date, leave_type):
    emp_leave_grade = frappe.db.get_all("Leave Employee Grade", filters={'parent': leave_type}, fields=['employee_grade'])
    allowed_grades = [g.employee_grade for g in emp_leave_grade]

    if not allowed_grades:
        return []
    
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
            & (employee.grade.isin(allowed_grades))
        )
    )
    data = query.run(as_dict=1) or []

    return data

# infirmary_leave
@frappe.whitelist()
def infirmary_leave_allocation():
    leave_type = frappe.db.get_value("Leave Type", {'is_carry_forward':0,'is_earned_leave': 0,'is_lwp':0,'is_compensatory':0} ,
                    ['name','applicable_after'], as_dict=True)

    today = datetime.today().date()
    one_year_ago = today - timedelta(days=leave_type.applicable_after)
    
    emp_leave_grade = frappe.db.get_all("Leave Employee Grade", filters={'parent': leave_type.name}, fields=['employee_grade'])
    
    for emp_grade in emp_leave_grade:
        employees = frappe.get_all("Employee", 
                filters={"status": "Active",'grade': emp_grade.employee_grade }, fields=["name", "date_of_joining", "grade"] )

        for emp in employees: 
            doj = getdate(emp.date_of_joining)

            # Get leave policy assignment for the employee
            leave_policy_ass = frappe.db.get_value(
                "Leave Policy Assignment", 
                    {'employee': emp.name, 'docstatus': 1},
                    ['name', 'effective_from', 'effective_to','leave_policy'], 
                as_dict=True
            )

            if not leave_policy_ass:
                continue
            
            from_date = leave_policy_ass.effective_from
            to_date = leave_policy_ass.effective_to
            annual_allocation = get_annual_allocation(leave_policy_ass.leave_policy, leave_type.name)
            if not annual_allocation:
                continue

            existing_allocations = frappe.get_all("Leave Allocation", filters={
                "employee": emp.name,
                "leave_type": leave_type.name,
                "leave_policy_assignment": leave_policy_ass.name,
                "from_date": from_date,
                "to_date": to_date,
                "docstatus": 1
            })
            
            # If employee has completed 1 year
            if doj and doj <= one_year_ago:
                if existing_allocations:
                    for alloc in existing_allocations:
                        allocation_doc = frappe.get_doc("Leave Allocation", alloc.name)
                        if allocation_doc.total_leaves_allocated == annual_allocation: 
                            allocation_doc.db_set("total_leaves_allocated", annual_allocation, update_modified=False)
                            allocation_doc.db_set("new_leaves_allocated", annual_allocation, update_modified=False)
                            # create_additional_leave_ledger_entry(allocation, earned_leaves, today_date) #creating ledger as per new allocation
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
                    # allocation_doc.insert(ignore_permissions=True)

"""Compenstory off leave"""
@frappe.whitelist()
def compOff_leave_allocation():
    # frappe.throw(f"{from_date} {to_date}")
    leave_type = frappe.db.get_value("Leave Type", {'is_compensatory': 1} , ['name','applicable_after'], as_dict=True)
    emp_leave_grade = frappe.db.get_all("Leave Employee Grade", filters={'parent': leave_type.name}, fields=['employee_grade'])
    
    allowed_grades = [e.employee_grade for e in emp_leave_grade]

    # today = to_date #frappe.utils.today()
    # yesterday =  from_date #frappe.utils.add_days(today, -1)
    
    # if to_date and from_date
    today = frappe.utils.today()
    yesterday =  frappe.utils.add_days(today, -1)

    emp_checkin = frappe.db.sql("""
                SELECT distinct(employee) as employee,date(time) as date
                    FROM `tabEmployee Checkin`
                    WHERE DATE(time) BETWEEN %s AND %s
            """, (yesterday, today), as_dict=1)
 
    # frappe.throw(f"{leave_type} {emp_checkin}")
    ab = []
    for emp in emp_checkin:
        employee_id = emp.get("employee")
        checkin_date = emp.get("date")

        if not employee_id or not checkin_date:
            continue

        weekoff_date = is_holiday_or_weekoff(checkin_date, employee_id)
        if not weekoff_date:
            continue
        ab.append(weekoff_date)
        # ab.append(employee_id)

        emp_grade = frappe.db.get_value("Employee", employee_id, "grade")
        if emp_grade not in allowed_grades:
            continue
        
        leave_policy_ass = frappe.db.get_value(
                "Leave Policy Assignment", 
                    {'employee': employee_id, 'docstatus': 1},
                    ['name', 'effective_from', 'effective_to','leave_policy'], 
                as_dict=True
            )
        if not leave_policy_ass:
            continue
        
        from_date = weekoff_date
        to_date = add_days(weekoff_date, leave_type.applicable_after)
        leaves = 1

        allocation = frappe.get_all("Leave Allocation", 
            filters={
                "employee": employee_id,
                "leave_type": leave_type.name,
                "leave_policy_assignment": leave_policy_ass.name,
                "docstatus": 1,
                # "from_date": leave_policy_ass.effective_from,
                "from_date": ["between", ['2025-05-01', leave_policy_ass.effective_to]],
                # "to_date": leave_policy_ass.effective_to
                "to_date": ["between", ['2025-05-01', leave_policy_ass.effective_to]],
            })
        
        # frappe.throw(f"{weekoff_date},  {to_date} == {allocation} --- {employee_id} {leave_policy_ass.effective_from} {leave_policy_ass.effective_to}")
        if allocation:
            # Already exists - update and create ledger
            alloc_doc = frappe.get_doc("Leave Allocation", allocation)

            # Avoid duplicate ledger entry on same weekoff_date
            existing_entry = frappe.db.exists("Leave Ledger Entry", {
                "transaction_name": alloc_doc.name,
                "transaction_type": "Leave Allocation",
                "from_date": from_date,
                "to_date": to_date
            })
            if existing_entry:
                continue

            alloc_doc.total_leaves_allocated += 1
            alloc_doc.db_set("total_leaves_allocated", alloc_doc.total_leaves_allocated, update_modified=False)
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
            # create_additional_leave_ledger_entry(alloc_doc, 1, posting_date=weekoff_date)
           
def is_holiday_or_weekoff(date, employee):
    holiday_list = frappe.db.get_value("Employee", employee, "holiday_list")
    
    if not holiday_list:
        return None

    holiday_date = frappe.db.exists("Holiday", {
        "parent": holiday_list,
        "weekly_off": 1,
        "holiday_date": getdate(date)
        })
    
    return getdate(date) if holiday_date else None
