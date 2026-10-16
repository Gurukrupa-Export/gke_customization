import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
from erpnext.projects.doctype.timesheet.timesheet import Timesheet


class CustomTimesheet(Timesheet):
    def validate_overlap(self, data):
        return
