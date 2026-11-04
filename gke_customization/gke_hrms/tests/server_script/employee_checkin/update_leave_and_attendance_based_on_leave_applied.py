check_leave_application = frappe.db.sql("""
    SELECT name, employee, from_date, to_date, status
    FROM `tabLeave Application`
    WHERE employee = %s
    AND DATE(%s) BETWEEN from_date AND to_date
    AND docstatus = 1
    AND status = 'Approved'
""", (doc.employee, doc.time), as_dict=1)

if check_leave_application:
    leave = check_leave_application[0]
    if frappe.utils.getdate(doc.time) == leave.from_date:
        # Employee returns on the FIRST leave day

        attendance_list = frappe.db.sql("""
                SELECT name
                FROM `tabAttendance`
                WHERE employee = %s
                AND attendance_date BETWEEN %s AND %s
                AND docstatus = 1
            """, (doc.employee, frappe.utils.getdate(doc.time), leave.to_date), as_dict=1)

        for att in attendance_list:
            att_doc = frappe.get_doc("Attendance", att.name)
            att_doc.cancel()

        leave_doc = frappe.get_doc("Leave Application", leave.name)
        leave_doc.cancel()
        frappe.db.set_value("Leave Application", leave.name, {"workflow_state": "Cancelled"})

        ledger_name = frappe.db.get_value("Leave Ledger Entry", {"transaction_name": leave.name}, "name")

        leave_doc.add_comment(
            "Comment",
            f"Employee returned on same date {frappe.utils.getdate(doc.time)}. Leave cancelled."
        )
        frappe.msgprint(f"Leave Application {leave.name} Updated")
    else:
        # Employee returns BEFORE leave ends
        if check_leave_application:

            leave_name = leave.name
            original_to_date = leave.to_date

            checkin_date = frappe.utils.getdate(doc.time)
            new_to_date = frappe.utils.add_days(checkin_date, -1)
            total_days = frappe.utils.date_diff(new_to_date, leave.from_date) + 1
            emp_holiday = frappe.db.get_value("Employee", doc.employee, 'holiday_list')

            # emp holiday on holidays
            while True:
                public_holidays = frappe.db.exists("Holiday", {
                            "parent": emp_holiday,
                            "weekly_off": 0,
                            "holiday_date": new_to_date
                        })

                if not public_holidays:
                    break
                new_to_date = frappe.utils.add_days(new_to_date, -1)
                total_days = total_days - 1

            # emp holiday sunday wo
            wo_holiday = frappe.db.exists("Holiday", {
                        "parent": emp_holiday,
                        "weekly_off": 1,
                        "holiday_date": ["between", [leave.from_date, new_to_date]]
                    })
            if wo_holiday:
                total_days = total_days - 1

            attendance_list = frappe.db.sql("""
                SELECT name
                FROM `tabAttendance`
                WHERE employee = %s
                AND attendance_date BETWEEN %s AND %s
                AND docstatus = 1
            """, (doc.employee, checkin_date, original_to_date), as_dict=1)

            for att in attendance_list:
                frappe.db.set_value("Attendance", att.name, "docstatus", 2)

            frappe.db.set_value("Leave Application", leave_name, {"to_date": new_to_date, "total_leave_days": total_days})

            ledger_name = frappe.db.get_value("Leave Ledger Entry", {"transaction_name": leave.name}, "name")

            # ledger total
            leaves_total = frappe.utils.date_diff(leave.from_date, new_to_date) - 1
            if wo_holiday:
                leaves_total = leaves_total + 1

            frappe.db.set_value("Leave Ledger Entry", ledger_name, {"to_date": new_to_date, "leaves": leaves_total})

            leave_doc = frappe.get_doc("Leave Application", leave_name)
            leave_doc.add_comment("Comment", f"Employee returned early on {checkin_date}. to_date updated from {original_to_date} to {new_to_date}.")

            frappe.msgprint(f"Leave Application {leave_name} updated: to_date={new_to_date}, total_leave_days={total_days}")