# import frappe
# from datetime import datetime, timedelta
# from frappe.utils import fmt_money

# def calculate_working_days(doc, method=None):
#     # added by shubham
#     check_already_exist_loan_application = frappe.db.get_list(
#             "Employee Advance",
#             filters={"employee": doc.employee},
#             fields=["status", "name"]
#     )

#     unpaid_advance = next(
#         (row for row in check_already_exist_loan_application if row["status"] in ["Unpaid", "Draft"]),
#         None
#     )

#     if unpaid_advance:
#         frappe.throw(
#             f"You are not eligible to apply for a new advance because old advance {unpaid_advance['name']} is still unpaid."
#         )
#     # till here shubham

#     salary = frappe.db.get_value("Employee", doc.employee, "ctc")  
#     holiday_list = frappe.db.get_value("Employee", doc.employee, "holiday_list")
#     default_shift = frappe.db.get_value("Employee", doc.employee, "default_shift")

#     if not holiday_list:
#         frappe.throw("No holiday list linked to the employee.")
    
#     # Ensure posting_date is a datetime object 
#     posting_date = doc.posting_date
#     if isinstance(posting_date, str):
#         posting_date = datetime.strptime(posting_date, '%Y-%m-%d').date()  # Convert from string to date
    
#     # Get the first day of the month
#     start_date = posting_date.replace(day=1)
#     mid_of_month = start_date.replace(day=15)
    
#     last_day = start_date.replace(day=28) + timedelta(days=4)
    
#     # Subtract days to get the last day of the current month 
#     end_date = last_day - timedelta(days=last_day.day)  
    
#     days_to_posting_date = (posting_date - start_date).days + 1
    
#     # SQL query to count holidays between start_date and posting_date using frappe.db.sql
#     working_hours_query = """
#         SELECT SUM(working_hours) 
#         FROM `tabAttendance`
#         WHERE employee = %s
#         AND attendance_date BETWEEN %s AND %s
#         AND status IN ('Present', 'Absent', 'On Leave', 'Half Day', 'Work From Home')
#         AND docstatus = 1
#     """
#     working_hours = frappe.db.sql(working_hours_query, (doc.employee, start_date, posting_date), as_list=True)[0][0]
#     # frappe.throw(f"{working_hours}")
    
#     working_hours = working_hours or 0  
#     query = """
#         SELECT COUNT(*) 
#         FROM `tabHoliday` h
#         JOIN `tabHoliday List` hl ON h.parent = hl.name
#         WHERE hl.name = %s 
#         AND h.holiday_date BETWEEN %s AND %s
#     """
#     # Execute the SQL query to count holidays between start_date and end_date
#     holiday_count = frappe.db.sql(query, (holiday_list, start_date, end_date), as_list=True)[0][0]

#     # Calculate total days and working days
#     total_days = (end_date - start_date).days + 1  # Inclusive of both dates
#     working_days = total_days - holiday_count
    
#     # Get the shift hours from the "Shift Type" linked to the default_shift of the employee
#     if default_shift:
#         shift_hours = frappe.db.get_value("Shift Type", default_shift, "shift_hours")
#         if shift_hours is None:
#             frappe.throw(f"Shift Type {default_shift} does not have working hours set.")
#     else:
#         frappe.throw("No default shift set for the employee.")
    
#     # Calculate the hourly salary and validate the advance amount
#     if (salary and shift_hours):
        
#         # from here shubham
#         pending_advance = frappe.db.exists(
#             "Employee Advance",
#             {
#                 "employee": doc.employee,
#                 "docstatus": 1,
#                 "status": "Unpaid",
#             }
#         )
        
#         if pending_advance:
#             frappe.throw(
#                 "You cannot create a new advance request while a previous Amount is Unpaid"
#             )
            
#         day_salary = salary / working_days

#         hourly_salary = day_salary / shift_hours
        
#         earned_amount = working_hours * hourly_salary
        
#         allowed_amt = earned_amount * 70 / 100
        
#         paid_advance = frappe.db.sql("""
#             SELECT SUM(advance_amount)
#             FROM `tabEmployee Advance`
#             WHERE employee=%s
#             AND docstatus=1
#             AND workflow_state IN ('Send to Account', 'Approved')
#         """, doc.employee)[0][0] or 0
        
#         remaining_amount = allowed_amt - paid_advance
        
#         # if doc.advance_amount > remaining_amount:
#         #     frappe.throw(
#         #         f"Maximum remaining advance allowed is {remaining_amount}"
#         #     )
        
#         # to here shubham
#         # monthly_salary = salary / working_days
#         # hourly_salary = monthly_salary / shift_hours
        
#         total_amount = working_hours * hourly_salary
        
#         # allowed_amt = (85 * total_amount/100)
        
#         if doc.advance_amount > remaining_amount:
#             frappe.throw(f"You are not eligible for this advance amount of {fmt_money(doc.advance_amount, precision=2)}. The maximum eligible amount based on your working hours is {fmt_money(allowed_amt, precision=2)}. and remaning amount is {fmt_money(remaining_amount, precision=2)}")
#         if posting_date > mid_of_month:
#             if doc.advance_amount > salary: 
#                 frappe.throw(f"Advance amount cannot be greater than the monthly salary. Monthly Salary: {fmt_money(salary, precision=2)}, Advance amount: {fmt_money(doc.advance_amount, precision=2)}")
#         else:
#             if doc.advance_amount > total_amount: 
#                 frappe.throw(f"Advance amount cannot be greater than the total amount. Total amount: {fmt_money(total_amount, precision=2)}, Advance amount: {fmt_money(doc.advance_amount, precision=2)}")
       


# bhavika
import frappe
from datetime import datetime, timedelta
from frappe.utils import fmt_money

def calculate_working_days(doc, method=None):
    # added by shubham
    check_already_exist_loan_application = frappe.db.get_list(
            "Employee Advance",
            filters={"employee": doc.employee, "workflow_state": ["not in", ["Send to manager","Send to HR"]]},
            fields=["status", "name"]
    )
    
    unpaid_advance = next(
        (row for row in check_already_exist_loan_application if row["status"] in ["Unpaid", "Draft"]),
        None
    )

    if unpaid_advance:
        frappe.throw(
            f"You are not eligible to apply for a new advance because old advance {unpaid_advance['name']} is still unpaid."
        )
    # till here shubham

    salary = frappe.db.get_value("Employee", doc.employee, "ctc")  
    holiday_list = frappe.db.get_value("Employee", doc.employee, "holiday_list")
    default_shift = frappe.db.get_value("Employee", doc.employee, "default_shift")

    if not holiday_list:
        frappe.throw("No holiday list linked to the employee.")
    
    # Ensure posting_date is a datetime object 
    posting_date = doc.posting_date
    if isinstance(posting_date, str):
        posting_date = datetime.strptime(posting_date, '%Y-%m-%d').date()  # Convert from string to date
    
    # Get the first day of the month
    start_date = posting_date.replace(day=1)
    mid_of_month = start_date.replace(day=15)
    
    last_day = start_date.replace(day=28) + timedelta(days=4)
    
    # Subtract days to get the last day of the current month 
    end_date = last_day - timedelta(days=last_day.day)  
    
    days_to_posting_date = (posting_date - start_date).days + 1
    
    # SQL query to count holidays between start_date and posting_date using frappe.db.sql
    working_hours_query = """
        SELECT SUM(working_hours) 
        FROM `tabAttendance`
        WHERE employee = %s
        AND attendance_date BETWEEN %s AND %s
        AND status IN ('Present', 'Absent', 'On Leave', 'Half Day', 'Work From Home')
        AND docstatus = 1
    """
    working_hours = frappe.db.sql(working_hours_query, (doc.employee, start_date, posting_date), as_list=True)[0][0]
    # frappe.throw(f"{working_hours}")
    
    working_hours = working_hours or 0  
    query = """
        SELECT COUNT(*) 
        FROM `tabHoliday` h
        JOIN `tabHoliday List` hl ON h.parent = hl.name
        WHERE hl.name = %s 
        AND h.holiday_date BETWEEN %s AND %s
    """
    # Execute the SQL query to count holidays between start_date and end_date
    holiday_count = frappe.db.sql(query, (holiday_list, start_date, end_date), as_list=True)[0][0]

    # Calculate total days and working days
    total_days = (end_date - start_date).days + 1  # Inclusive of both dates
    working_days = total_days - holiday_count
    
    # Get the shift hours from the "Shift Type" linked to the default_shift of the employee
    if default_shift:
        shift_hours = frappe.db.get_value("Shift Type", default_shift, "shift_hours")
        if shift_hours is None:
            frappe.throw(f"Shift Type {default_shift} does not have working hours set.")
    else:
        frappe.throw("No default shift set for the employee.")
    
    # Calculate the hourly salary and validate the advance amount
    if (salary and shift_hours):
        
        # from here shubham
        pending_advance = frappe.db.exists(
            "Employee Advance",
            {
                "employee": doc.employee,
                "docstatus": 1,
                "status": "Unpaid",
            }
        )
        
        if pending_advance:
            frappe.throw(
                "You cannot create a new advance request while a previous Amount is Unpaid"
            )
            
        day_salary = salary / working_days

        hourly_salary = day_salary / shift_hours
        
        earned_amount = working_hours * hourly_salary
        
        allowed_amt = earned_amount * 70 / 100
        
        paid_advance = frappe.db.sql("""
            SELECT COALESCE(SUM(advance_amount), 0)
            FROM `tabEmployee Advance`
            WHERE employee = %s
            AND docstatus = 1
            AND posting_date BETWEEN %s AND %s
            AND workflow_state IN ('Send to Account', 'Approved')
        """, (doc.employee, start_date, end_date))[0][0]

        remaining_amount = allowed_amt - paid_advance
        # if doc.advance_amount > remaining_amount:
        #     frappe.throw(
        #         f"Maximum remaining advance allowed is {remaining_amount}"
        #     )
        
        # to here shubham
        # monthly_salary = salary / working_days
        # hourly_salary = monthly_salary / shift_hours
        
        total_amount = working_hours * hourly_salary
        
        # allowed_amt = (85 * total_amount/100)
        
        if doc.advance_amount > remaining_amount:
            frappe.throw(f"You are not eligible for this advance amount of {fmt_money(doc.advance_amount, precision=2)}. The maximum eligible amount based on your working hours is {fmt_money(allowed_amt, precision=2)}. and remaning amount is {fmt_money(remaining_amount, precision=2)}")
        if posting_date > mid_of_month:
            if doc.advance_amount > salary: 
                frappe.throw(f"Advance amount cannot be greater than the monthly salary. Monthly Salary: {fmt_money(salary, precision=2)}, Advance amount: {fmt_money(doc.advance_amount, precision=2)}")
        else:
            if doc.advance_amount > total_amount: 
                frappe.throw(f"Advance amount cannot be greater than the total amount. Total amount: {fmt_money(total_amount, precision=2)}, Advance amount: {fmt_money(doc.advance_amount, precision=2)}")
       


