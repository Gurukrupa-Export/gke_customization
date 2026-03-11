import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import format_duration, get_link_to_form, time_diff_in_seconds
import hrms

from hrms.hr.doctype.job_requisition.job_requisition import JobRequisition

class CustomJobRequisition(JobRequisition):
    def autoname(self):
        if self.custom_branch:
            parts = self.custom_branch.split("-")
            branch_prefix = "-".join(parts[:2])

            series_number = frappe.model.naming.make_autoname("HIREQ-.#####")
            series = f"{branch_prefix}-HIREQ-{series_number.split('-')[-1]}"

            self.name = series
        else:
            company_abbr = frappe.db.get_value("Company", self.company, "abbr")
            series = f"{company_abbr}-HIREQ-.#####"
            
            self.name = frappe.model.naming.make_autoname(series)

    def validate(self):
        self.validate_duplicates()
        self.set_time_to_fill()

    def validate_duplicates(self):
        duplicate = frappe.db.exists(
            "Job Requisition",
            {
                "designation": self.designation,
                "department": self.department,
                "requested_by": self.requested_by,
                "custom_branch": self.custom_branch  or "",
                "status": ("not in", ["Cancelled", "Filled"]),
                "name": ("!=", self.name),
            },
        )

        if duplicate:
            frappe.throw(
                _("A Job Requisition for {0} requested by {1} already exists: {2}").format(
                    frappe.bold(self.designation),
                    frappe.bold(self.requested_by),
                    get_link_to_form("Job Requisition", duplicate),
                ),
                title=_("Duplicate Job Requisition"),
            )