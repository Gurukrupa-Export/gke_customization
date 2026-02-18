import frappe
from frappe import _
from frappe.utils import flt
import pyotp
import hmac
import hashlib
import base64
from frappe.auth import LoginManager
from datetime import datetime, timedelta, timezone, date
import pytz
from frappe.integrations.oauth2 import get_oauth_server
import requests
import json
from frappe.utils import validate_email_address, now_datetime


from gke_customization.gke_catalog.api.notifications import notify_user
from gke_customization.gke_catalog.api.login import get_address_by_link_name


@frappe.whitelist(allow_guest=True)
def get_created_issue_by_customer_and_supplier(customer):
    if isinstance(customer, str):
        try:
            customer = json.loads(customer)
        except Exception:
            customer = [customer]  # fallback if not valid JSON string


    format_strings = ','.join(['%s'] * len(customer))
    try: 
        query = f"""
            SELECT
                ti.name,
                ti.subject,
                ti.raised_by,
                ti.status,
                ti.priority,
                ti.issue_type,
                ti.description,
                ti.opening_date,
                ti.response_by,
                ti.resolution_details,
                ti.opening_time,
                ti.resolution_date,
                ti.customer,
                tc.customer_name,
                ti.company,
                ti.attachment
            FROM `tabIssue` as ti
            JOIN `tabCustomer` as tc ON ti.customer = tc.name
            WHERE ti.customer IN ({format_strings})
            ORDER BY
                ti.creation DESC, 
                CASE
                    WHEN ti.priority = 'High' THEN 1
                    WHEN ti.priority = 'Medium' THEN 2
                    WHEN ti.priority = 'Low' THEN 3 
                END ASC;
        """
        get_issue_list = frappe.db.sql(query, customer, as_dict=True)
        return get_issue_list

    
    except Exception as e:
        frappe.log_error(f"Error in get_item: {str(e)}")
        return {"success": False, "message": "Failed to fetch Item"}
    

@frappe.whitelist(allow_guest=True)
def add_issues_by_customer(data):
    try:
        subject = data.get('subject')
        priority = data.get('priority')
        issue_type = data.get('issue_type')
        description = data.get('description')

        # frappe.throw("{subject} {priority} {issue_type} {description}")

        if not subject or not priority or not issue_type or not description:
            return {"success": False, "message": "Missing required fields"}

        query = """
                INSERT INTO `tabIssue` (subject, priority, issue_type, description)
                VALUES (%s, %s, %s, %s)
            """
        values = (subject, priority, issue_type, description)

        frappe.db.sql(query, values)
        frappe.db.commit()

            # Query the inserted record to return it (assuming subject + description uniquely identifies it)
        select_query = """
                SELECT * FROM `tabIssue`
                WHERE subject = %s AND priority = %s AND issue_type = %s AND description = %s
                ORDER BY creation DESC
                LIMIT 1
            """
        inserted_data = frappe.db.sql(select_query, values, as_dict=True)

        return inserted_data

    except Exception as e:
        frappe.log_error(f"Error in add_issues_by_customer: {str(e)}")
        return {"success": False, "message": "Failed to create Issue"}


@frappe.whitelist(allow_guest=True)
def reply_on_issues(ticket_id=None, subject=None, frm=None, qry_status=None,
                     comment_by=None):
    try:
        uploaded_file_url = None
        file_obj = None
        file_content = None
        html_content = ""

        # ---------- FILE UPLOAD ----------
        if "file" in frappe.request.files:
            file_obj = frappe.request.files["file"]
            file_content = file_obj.read()

        # ---------- CREATE DOCUMENT ----------
        doc = frappe.get_doc({
            "doctype": "Comment",
            "comment_type":"Comment",
            "reference_name":ticket_id,
            "comment_by":comment_by,
            "subject": subject,
            "comment_email": frm,
            "status": qry_status,
            "reference_doctype": "Issue",
        })

        doc.insert(ignore_permissions=True)

        # ---------- ATTACH FILE ----------
        if file_obj and file_content:
            uploaded_file = frappe.utils.file_manager.save_file(
                file_obj.filename,
                file_content,
                "Comment",
                doc.name,
                is_private=0
            )

            uploaded_file_url = uploaded_file.file_url

            html_content = f"""
                <img src="http://ec2-13-234-27-130.ap-south-1.compute.amazonaws.com:8001{uploaded_file_url}" />
                <h3>{subject or ''}</h3>
            """
            # save file URL to doc
            # full_url = "http://ec2-13-234-27-130.ap-south-1.compute.amazonaws.com:8001" + uploaded_file_url
    
            doc.content = html_content
            doc.save(ignore_permissions=True)

            # first resolution added here below


        frappe.db.commit()

        check_first_value = frappe.get_all(
                    "Comment",
                    filters={"reference_name": ticket_id},
                    fields=["name", "subject"]
        )

        if len(check_first_value) == 1:
                frappe.db.set_value(
                    "Issue",
                    ticket_id,
                    {
                        "first_responded_on": doc.creation,
                    }
                )

        if qry_status == "Closed":
            resolution = subject
            if not resolution or check_first_value:
                resolution = (
                    check_first_value[-1]["subject"]
                    + " | "
                    + str(now_datetime())
                )
                # frappe.throw("HERE")

            if resolution:
                frappe.db.set_value(
                    "Issue",
                    ticket_id,
                    "resolution_details",
                    resolution
                )


        return {
            "success": True,
            "message": "Record created successfully",
            "name": doc.name,
            "content": html_content,
            "val": check_first_value[-1]
        }

    except Exception as e:
        frappe.log_error(f"Error in reply_on_issues: {str(e)}", "Portal Communication Error")
        return {"success": False, "error": str(e)}


@frappe.whitelist(allow_guest=True)
def get_communications(ticket_id=None):
    try:
        filters = {}
        if ticket_id:
            filters["reference_name"] = ticket_id

        data = frappe.get_all(
            "Comment",
            filters=filters,
            fields=["name", "subject", "comment_email", "content", "creation"],
            order_by="creation asc"
        )

        return {"success": True, "data": data}

    except Exception as e:
        frappe.log_error(f"Error in get_communications: {str(e)}", "Communication API Error")
        return {"success": False, "error": str(e)}


@frappe.whitelist(allow_guest=True)
def get_new_created_issue(user_id, user_type, customer, subject, issue_type, description, priority):
    try:
        # Set current user
        frappe.set_user(user_id)

        # Create the Issue first
        issue = frappe.get_doc({
            "doctype": "Issue",
            "subject": subject,
            "raised_by": user_id,
            "customer": customer,
            "issue_type": issue_type,
            "description": description,
            "priority": priority,
            "owner": user_id
        })
        issue.insert(ignore_permissions=True)

        # ✅ Handle file upload (from FormData)
        file = frappe.request.files.get('attachment')
        if file:
            _file = frappe.get_doc({
                "doctype": "File",
                "file_name": file.filename,
                "attached_to_doctype": "Issue",
                "attached_to_name": issue.name,
                "content": file.stream.read(),
                "is_private": 0  # or 1 if you want it private
            })
            _file.insert(ignore_permissions=True)
            frappe.db.commit()

            # Save file URL to Issue for easy access
            issue.db_set("attachment", _file.file_url)

        # ✅ Return full Issue details (including attachment URL)
        issue_data = frappe.db.get_value(
            "Issue",
            issue.name,
            ["name", "subject", "raised_by", "status", "priority", "issue_type",
             "description", "opening_date", "resolution_date",
             "resolution_details", "attachment"],
            as_dict=True
        )

        return {
            "success": True,
            "message": issue_data
        }

    except Exception as e:
        frappe.log_error(f"Error in get_new_created_issue: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to create issue: {str(e)}"
        }


@frappe.whitelist(allow_guest=True)
def update_status_of_issue(ticket_id=None, new_status=None):
    if not ticket_id or not new_status:
        return {
            "success": False,
            "message": "ticket_id or new_status missing"
        }

    try:
        frappe.db.set_value("Issue", ticket_id, "status", new_status)
        frappe.db.commit()

        check_first_value = frappe.get_all(
                    "Comment",
                    filters={"reference_name": ticket_id},
                    fields=["name", "subject", "creation"]
        )


        if new_status == "Closed":
            if check_first_value:
                resolution = (
                    check_first_value[-1]["subject"]
                    + " | "
                    + str(now_datetime())
                )
                
            if resolution:
                frappe.db.set_value(
                    "Issue",
                    ticket_id,
                    "resolution_details",
                    resolution
                )

        return {
            "success": True,
            "message": "Status updated successfully",
            "ticket_id": ticket_id,
            "new_status": new_status
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Issue Status Update Error")
        return {
            "success": False,
            "message": f"Failed to update status: {str(e)}"
        }
