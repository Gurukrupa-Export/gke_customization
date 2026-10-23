import frappe
from frappe import _


def validate_reports_to(doc, method=None):
	"""Reports To is mandatory for every employee except the first one of the
	company. The first employee (the org head) has no existing employee to
	report to, so an unconditional mandatory check on the field can never be
	satisfied; this keeps the rule but exempts that one case."""
	if doc.reports_to:
		return

	if not frappe.get_meta("Employee").has_field("reports_to"):
		return

	has_other_employee = frappe.db.exists(
		"Employee", {"company": doc.company, "name": ("!=", doc.name)}
	)
	if has_other_employee:
		frappe.throw(_("Reports To is mandatory once the company has other employees"))
