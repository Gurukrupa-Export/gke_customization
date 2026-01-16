import frappe
from frappe.utils import now_datetime,get_datetime, today
from frappe.sessions import clear_sessions
from datetime import datetime, time, timedelta

@frappe.whitelist()
def logout_users_after_shift():
    current_dt = now_datetime()

    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["user_id", "default_shift"],
    )
    # frappe.log_error("start time ",employees)
    for emp in employees:
        if not emp.default_shift or not emp.user_id:
            continue

        shift = frappe.get_doc("Shift Type", emp.default_shift)
        start_time = shift.start_time
        end_time = shift.end_time

        # Convert timedelta → time
        def td_to_time(td):
            seconds = int(td.total_seconds())
            h, rem = divmod(seconds, 3600)
            m, s = divmod(rem, 60)
            return time(h % 24, m, s)

        if isinstance(start_time, timedelta):
            start_time = td_to_time(start_time)

        if isinstance(end_time, timedelta):
            end_time = td_to_time(end_time)

        employee_id = frappe.db.get_value(
            "Employee",
            {"user_id": emp.user_id},
            "name"
        )

        # Get total OT (timedelta)
        ot_request = frappe.db.sql("""
            SELECT
                SEC_TO_TIME(SUM(TIME_TO_SEC(or_det.ot_hours))) AS total_ot
            FROM 
                `tabOvertime Request Details` or_det
            JOIN 
                `tabOT Request` ot ON ot.name = or_det.parent
            WHERE 
                or_det.employee_id = %s
            AND
                ot.date = %s
            AND 
                ot.docstatus = 1
        """, (employee_id, frappe.utils.today()), as_dict=1)

        total_ot_td = ot_request[0].total_ot if ot_request and ot_request[0].total_ot else timedelta(0)

        # Convert OT timedelta to seconds
        ot_seconds = total_ot_td.total_seconds()
        ot_hours = ot_seconds / 3600

        shift_start_hour = start_time.hour
        # Calculate end datetime
        shift_end_dt = datetime.combine(current_dt.date(), end_time)
        extended_end_dt = shift_end_dt + timedelta(seconds=ot_seconds)
        extended_hour = extended_end_dt.hour +  1
        shift_ed =  shift_end_dt.hour + 1
        # if ot_request:
        frappe.db.set_value("User", emp.user_id, "login_before", extended_hour )
        frappe.db.set_value("User", emp.user_id, "login_after", shift_start_hour )

        # Logout condition
        if current_dt > extended_end_dt:
            clear_sessions(user=emp.user_id)
            frappe.logger().info(
                f"Auto logout: {emp.user_id}, OT included: {ot_hours} hrs"
            )
            frappe.db.set_value("User", emp.user_id, "login_before", shift_ed )


def validate_login_time(login_manager):
    user = frappe.form_dict.get("usr")

    if user in ("Administrator", "Guest"):
        return

    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user, "status": "Active"},
        ["name", "default_shift"],
        as_dict=True
    )

    if not employee or not employee.default_shift:
        return

    shift = frappe.get_doc("Shift Type", employee.default_shift)

    start_time = shift.start_time
    end_time = shift.end_time

    now = get_datetime()
    current_time = timedelta(
        hours=now.hour,
        minutes=now.minute,
        seconds=now.second
    )
    ot_data = frappe.db.sql("""
        SELECT 
            SUM(or_det.ot_hours) AS total_ot
        FROM 
            `tabOvertime Request Details` or_det
        JOIN 
            `tabOT Request` ot ON ot.name = or_det.parent
        WHERE 
            or_det.employee_id = %s
        AND 
            ot.date = %s
    """, (employee.name, today()), as_dict=True)

    total_ot_hours = float(ot_data[0].total_ot) if ot_data and ot_data[0].total_ot else 0

    # Extend shift end time with OT
    end_time = end_time + timedelta(hours=total_ot_hours)
    if start_time < end_time:
        allowed = start_time <= current_time <= end_time
    else:
        allowed = current_time >= start_time or current_time <= end_time

    if not allowed:
        frappe.throw(
            "Login allowed only during assigned working hours.",
            frappe.AuthenticationError
        )


# Auto Upload Variant Image from Script
# import frappe
# import base64
# from frappe.utils.file_manager import save_file
# import re


# def normalize_size(size):
#     size = size.upper().replace(" X ", "*").replace("X", "*").replace("MM", " MM")
#     size = re.sub(r"\s+", " ", size) 
#     return size.strip()

# @frappe.whitelist(allow_guest=False)
# def upload_variant_image(
#     finding_category=None,
#     finding_sub_category=None,
#     finding_size=None,
#     color=None,
#     filename=None,
#     filedata=None
# ):
#     if not all([finding_category, finding_sub_category, finding_size, color, filename, filedata]):
#         frappe.throw("Missing required parameters")

#     finding_size = normalize_size(finding_size)

#     item = frappe.db.sql("""
#         SELECT i.name
#         FROM `tabItem` i
#         INNER JOIN `tabItem Variant Attribute` iva
#             ON iva.parent = i.name
#         WHERE (
#             (iva.attribute='Finding Category' AND TRIM(iva.attribute_value)=%s)
#             OR
#             (iva.attribute='Finding Sub-Category' AND TRIM(iva.attribute_value)=%s)
#             OR
#             (iva.attribute='Finding Size' AND REPLACE(TRIM(iva.attribute_value), '  ', ' ') LIKE %s)
#             OR
#             (iva.attribute='Metal Colour' AND TRIM(iva.attribute_value)=%s)
#         )
#         GROUP BY i.name
#         HAVING COUNT(DISTINCT iva.attribute)=4
#         LIMIT 1
#     """, (
#         finding_category,
#         finding_sub_category,
#         f"%{finding_size}%",
#         color
#     ), as_dict=True)

#     if not item:
#         frappe.throw(f"No Item found for given variant attributes: "
#                      f"{finding_category}, {finding_sub_category}, {finding_size}, {color}")

#     ITEM_NAME = item[0]["name"]

#     existing_files = frappe.get_all(
#         "File",
#         filters={
#             "attached_to_doctype": "Item",
#             "attached_to_name": ITEM_NAME
#         },
#         fields=["name"]
#     )
#     for f in existing_files:
#         frappe.delete_doc("File", f.name, force=1)

#     frappe.db.set_value("Item", ITEM_NAME, "image", None)

#     image_bytes = base64.b64decode(filedata)
#     file_doc = save_file(
#         fname=filename,
#         content=image_bytes,
#         dt="Item",
#         dn=ITEM_NAME,
#         is_private=0
#     )

#     frappe.db.set_value("Item", ITEM_NAME, "image", file_doc.file_url)

#     return {
#         "status": "success",
#         "item_code": ITEM_NAME,
#         "file_name": file_doc.file_name,
#         "file_url": file_doc.file_url,
#         "finding_category": finding_category,
#         "finding_sub_category": finding_sub_category,
#         "finding_size": finding_size,
#         "color": color
#     }

@frappe.whitelist()
def broadcast_message(message):
    frappe.publish_realtime(
        event="msgprint",
        message=message
    )