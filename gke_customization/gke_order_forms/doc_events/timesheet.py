



import frappe
from frappe.utils import now_datetime, time_diff_in_hours

def validate(doc, method):
    validate_workflow(doc)
    current_time = now_datetime()
    
    # 1. Designing
    if doc.workflow_state == "Designing":
        found_prev = False

        for row in reversed(doc.time_logs):
            if row.activity_type in ["QC Activity", "Design Rework in Progress", "Sent to QC - On-Hold", "CAD Designing - On-Hold"]:
                if not row.to_time:
                    row.to_time = current_time
                    if row.from_time:
                        row.hours = time_diff_in_hours(row.to_time, row.from_time)
                    else:
                        row.hours = 0.0
                    from_time = row.to_time
                else:
                    from_time = row.to_time

                new_row = doc.append("time_logs", {})
                new_row.activity_type = "CAD Designing"
                new_row.from_time = from_time
                found_prev = True
                break

        if not found_prev and doc.docstatus != 0:
            new_row = doc.append("time_logs", {})
            new_row.activity_type = "CAD Designing"
            new_row.from_time = current_time

    # 2. Designing - On-Hold
    elif doc.workflow_state == "Designing - On-Hold":
        for row in reversed(doc.time_logs):
            if row.activity_type == "CAD Designing":
                if not row.to_time:
                    row.to_time = current_time
                    if row.from_time:
                        row.hours = time_diff_in_hours(row.to_time, row.from_time)
                    else:
                        row.hours = 0.0
                    from_time = row.to_time
                else:
                    from_time = row.to_time

                new_row = doc.append("time_logs", {})
                new_row.activity_type = "CAD Designing - On-Hold"
                new_row.from_time = from_time
                break

    # 3. Sent to QC
    elif doc.workflow_state == "Sent to QC":
        for row in reversed(doc.time_logs):
            if row.activity_type in ["CAD Designing", "CAD Designing - On-Hold", "Design Rework in Progress - On Hold"]:
                if not row.to_time:
                    row.to_time = current_time
                    if row.from_time:
                        row.hours = time_diff_in_hours(row.to_time, row.from_time)
                    else:
                        row.hours = 0.0
                    from_time = row.to_time
                else:
                    from_time = row.to_time

                new_row = doc.append("time_logs", {})
                new_row.activity_type = "QC Activity"
                new_row.from_time = from_time
                break
        else:
            frappe.throw("No valid prior activity (CAD/On-Hold/Rework-Hold) found before starting QC Activity.")

    # 4. Sent to QC - On-Hold
    elif doc.workflow_state == "Sent to QC - On-Hold":
        for row in reversed(doc.time_logs):
            if row.activity_type == "QC Activity" and not row.to_time:
                row.to_time = current_time
                if row.from_time:
                    row.hours = time_diff_in_hours(row.to_time, row.from_time)
                else:
                    row.hours = 0.0

                new_row = doc.append("time_logs", {})
                new_row.activity_type = "Sent to QC - On-Hold"
                new_row.from_time = row.to_time
                break

    # 5. Design Rework in Progress
    elif doc.workflow_state == "Design Rework in Progress":
        for row in reversed(doc.time_logs):
            if row.activity_type in ["QC Activity", "Customer Approval"]:
                if not row.to_time:
                    row.to_time = current_time
                    if row.from_time:
                        row.hours = time_diff_in_hours(row.to_time, row.from_time)
                    else:
                        row.hours = 0.0
                    from_time = row.to_time
                else:
                    from_time = row.to_time

                new_row = doc.append("time_logs", {})
                new_row.activity_type = "Design Rework in Progress"
                new_row.from_time = from_time
                break

    # 6. Design Rework in Progress - On Hold
    elif doc.workflow_state == "Design Rework in Progress - On Hold":
        for row in reversed(doc.time_logs):
            if row.activity_type == "Design Rework in Progress":
                if not row.to_time:
                    row.to_time = current_time
                    if row.from_time:
                        row.hours = time_diff_in_hours(row.to_time, row.from_time)
                    else:
                        row.hours = 0.0
                    from_time = row.to_time
                else:
                    from_time = row.to_time

                new_row = doc.append("time_logs", {})
                new_row.activity_type = "Design Rework in Progress - On Hold"
                new_row.from_time = from_time
                break

    # 7. QC Activity (after rework)
    elif doc.workflow_state == "QC Activity":
        for row in reversed(doc.time_logs):
            if row.activity_type == "Design Rework in Progress" and not row.to_time:
                row.to_time = current_time
                if row.from_time:
                    row.hours = time_diff_in_hours(row.to_time, row.from_time)
                else:
                    row.hours = 0.0

                new_row = doc.append("time_logs", {})
                new_row.activity_type = "QC Activity"
                new_row.from_time = row.to_time
                break

    # 8. Customer Approval
    elif doc.workflow_state == "Customer Approval":
        for row in reversed(doc.time_logs):
            if row.activity_type == "QC Activity" and not row.to_time:
                row.to_time = current_time
                if row.from_time:
                    row.hours = time_diff_in_hours(row.to_time, row.from_time)
                else:
                    row.hours = 0.0

                new_row = doc.append("time_logs", {})
                new_row.activity_type = "Customer Approval"
                new_row.from_time = row.to_time
                break

    # 9. Final Approval
    elif doc.workflow_state == "Approved":
        if doc.time_logs:
            last_row = doc.time_logs[-1]
            if not last_row.to_time:
                last_row.to_time = current_time
                if last_row.from_time:
                    last_row.hours = time_diff_in_hours(last_row.to_time, last_row.from_time)
                else:
                    last_row.hours = 0.0
                frappe.msgprint("Auto-closed last open activity during approval.")




def on_submit(doc, method):
    if doc.order:
        update_order_status_from_timesheets(doc.order)

def on_update(doc, method):
    if doc.order:
        update_order_status_from_timesheets(doc.order)



import frappe

def update_order_status_from_timesheets(order_name):
    workflow_type = frappe.db.get_value("Order", order_name, "workflow_type")
    bom_or_cad = frappe.db.get_value("Order", order_name, "bom_or_cad")

    if workflow_type != "CAD":
        return

    # Fetch all timesheets linked to this order excluding cancelled
    timesheets = frappe.get_all(
        "Timesheet",
        filters={"order": order_name, "docstatus": ("!=", 2)},
        fields=["name", "workflow_state", "creation"],
        order_by="creation asc"
    )

    if not timesheets:
        return

  
    current_order_state = frappe.db.get_value("Order", order_name, "workflow_state")
    if current_order_state == "Update Designer" and len(timesheets) > 1:
      
        first_ts = timesheets[0]["name"]
        try:
            ts_doc = frappe.get_doc("Timesheet", first_ts)
            if ts_doc.docstatus != 2: 
                ts_doc.cancel()
        except Exception as e:
            frappe.log_error(f"Failed to cancel old timesheet {first_ts}: {str(e)}")

       
        timesheets = frappe.get_all(
            "Timesheet",
            filters={"order": order_name, "docstatus": ("!=", 2)},
            fields=["name", "workflow_state", "creation"],
            order_by="creation asc"
        )
        if not timesheets:
            return

    
    states = {ts["workflow_state"] for ts in timesheets}

    
    if len(states) == 1:
        latest_state = list(states)[0]

      
        if latest_state == "Approved":
            if bom_or_cad == "Check":
                new_state = "Approved"
            else:
                new_state = "Update Item"
        else:
            new_state = latest_state

        
        if current_order_state != new_state:
            frappe.db.set_value("Order", order_name, "workflow_state", new_state)
            frappe.db.commit()
    else:
       
        return


def validate_workflow(doc):
    if doc.order:
        cad_order_form = frappe.db.get_value("Order", doc.order, "cad_order_form")
        if cad_order_form:
            required_approval = frappe.db.get_value("Order Form", cad_order_form, "required_customer_approval")

            if required_approval == 1:
                doc.custom_required_customer_approval = 1
                
                