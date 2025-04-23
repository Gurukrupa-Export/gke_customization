
import frappe
from frappe import local
def has_permission(doc, ptype, user):
    if ptype != "read":
        return True  # allow other permissions normally
        
    if "Task Manager" in frappe.get_roles(user):
        return True

    if doc.owner == user:
        return True
    # Check if this task is assigned to the current user
    assigned = frappe.db.exists("ToDo", {
        "reference_type": "Task",
        "reference_name": doc.name,
        "allocated_to": user
    })

    return bool(assigned)
