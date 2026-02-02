import frappe
import json
from frappe.model.document import Document
from frappe.query_builder import DocType
from frappe.model.naming import make_autoname
from frappe.utils import now_datetime, now, getdate, validate_email_address


class PayrollEmail(Document):

	def autoname(self):
		if not self.company:
			frappe.throw("Company is required to generate Payroll Email ID")

		# Fetch Company Abbreviation
		company_abbr = frappe.db.get_value("Company", self.company, "abbr")
		if not company_abbr:
			frappe.throw(f"Company abbreviation not found for {self.company}")

		today = now_datetime()
		year = today.strftime("%Y")

		# Naming pattern
		naming_pattern = f"PEB-{company_abbr}-{year}-.#####"
		self.name = make_autoname(naming_pattern)
	
	def validate(self):

		if self.is_new():
			self.status = "Draft"

		self._validate_duplicate_employee_emails()
		self._validate_duplicate_salary_slips()

		self._set_total_slips()

	def _validate_duplicate_employee_emails(self):
		email_map = {}

		for row in self.payroll_email_details:
			if not row.employee_email:
				continue

			email = row.employee_email.strip().lower()

			if email in email_map:
				frappe.throw(
					msg=f"Duplicate employee email found: {frappe.bold(email)} <br> Employees: {frappe.bold(row.employee)} -- {row.employee_name or 'Unknown'}",
					title="Duplicate Employee Email"
				)

			email_map[email] = row.employee_name

	def _validate_duplicate_salary_slips(self):
		seen = set()

		for row in self.payroll_email_details:
			if not row.salary_slip:
				continue

			if row.salary_slip in seen:
				frappe.throw(
					msg=f"Duplicate Salary Slip found: {frappe.bold(row.salary_slip)}",
					title="Duplicate Salary"
				)

			seen.add(row.salary_slip)

	def _set_total_slips(self):
		self.total_slips = len(self.payroll_email_details)

		self.sent_count = len([row for row in self.payroll_email_details if row.status == "Sent"])
		self.failed_count = len([row for row in self.payroll_email_details if row.status == "Failed"])
		self.skipped_count = len([row for row in self.payroll_email_details if row.status == "Skipped"])


@frappe.whitelist()
def fetch_employees(filters):
    """
    Fetch Salary Slips based on Payroll Entry.
    Bank Entry must exist for the selected Payroll Entry.
    """

    if isinstance(filters, str):
        filters = json.loads(filters)

    # --------------------------------------------------
    # 1. BASIC VALIDATIONS
    # --------------------------------------------------
    required_fields = ["company", "payroll_entry"]

    for field in required_fields:
        if not filters.get(field):
            frappe.throw(f"{field.replace('_', ' ').title()} is required")

    # --------------------------------------------------
    # 2. VALIDATE PAYROLL ENTRY
    # --------------------------------------------------
    payroll_entry = frappe.get_doc("Payroll Entry", filters["payroll_entry"])

    if payroll_entry.company != filters["company"]:
        frappe.throw("Selected Payroll Entry does not belong to the selected Company")

    if payroll_entry.docstatus != 1:
        frappe.throw("Payroll Entry must be submitted")

    # --------------------------------------------------
    # 3. CHECK BANK ENTRY EXISTS
    # --------------------------------------------------
    JournalEntry = DocType("Journal Entry")
    JournalEntryAccount = DocType("Journal Entry Account")

    bank_entry_exists = (
        frappe.qb.from_(JournalEntry)
        .join(JournalEntryAccount)
        .on(JournalEntry.name == JournalEntryAccount.parent)
        .select(JournalEntry.name)
        .where(JournalEntry.docstatus == 1)
        .where(JournalEntry.voucher_type == "Bank Entry")
        .where(JournalEntryAccount.reference_type == "Payroll Entry")
        .where(JournalEntryAccount.reference_name == payroll_entry.name)
        .limit(1)
    ).run()

    if not bank_entry_exists:
        frappe.throw(
            f"Bank Entry is not created for Payroll Entry {payroll_entry.name}"
        )

    # --------------------------------------------------
    # 4. FETCH SALARY SLIPS
    # --------------------------------------------------
    SalarySlip = DocType("Salary Slip")
    Employee = DocType("Employee")

    query = (
        frappe.qb.from_(SalarySlip)
        .join(Employee)
        .on(SalarySlip.employee == Employee.name)
        .select(
            SalarySlip.name.as_("salary_slip"),
            SalarySlip.employee,
            SalarySlip.employee_name,
            Employee.company_email,
            Employee.personal_email
        )
        .where(SalarySlip.company == filters["company"])
        .where(SalarySlip.payroll_entry == payroll_entry.name)
        .where(SalarySlip.docstatus == 1)
    )

    # Optional filters
    if filters.get("department"):
        query = query.where(SalarySlip.department == filters["department"])

    if filters.get("designation"):
        query = query.where(SalarySlip.designation == filters["designation"])

    if filters.get("branch"):
        query = query.where(SalarySlip.branch == filters["branch"])

    salary_slips = query.run(as_dict=True)

    if not salary_slips:
        frappe.throw("No submitted Salary Slips found for the selected Payroll Entry")

    # --------------------------------------------------
    # 5. PREPARE RESPONSE
    # --------------------------------------------------
    results = []

    for slip in salary_slips:
        employee_email = slip.company_email or slip.personal_email
        if employee_email:
            employee_email = validate_email_address(employee_email)

        if not employee_email:
            status = "Skipped"
            reason = "No Email or Invalid Email"
        else:
            status = "Pending"
            reason = None

        results.append({
            "employee": slip.employee,
            "employee_name": slip.employee_name,
            "salary_slip": slip.salary_slip,
            "employee_email": employee_email,
            "status": status,
            "error_detail": reason
        })

    return results

@frappe.whitelist()
def send_payroll_emails(batch_name):
    doc = frappe.get_doc("Payroll Email", batch_name)

    # -------------------------------
    # Validations (same as before)
    # -------------------------------
    if doc.status not in ("Draft", "Partial Failed", "Failed"):
        frappe.throw("Emails can be sent only when status is Draft or Partial or Failed")

    if doc.status == "Sending":
        frappe.throw("Email sending is already in progress")

    if not doc.email_account:
        frappe.throw("Please select an Email Account")

    if not any(row.status in ["Pending", "Failed"] for row in doc.payroll_email_details):
        frappe.throw("No pending emails to send")

    email_account = frappe.get_doc("Email Account", doc.email_account)
    if not email_account.enable_outgoing:
        frappe.throw("Selected Email Account is not enabled for outgoing emails")

    # -------------------------------
    # Lock batch
    # -------------------------------
    doc.status = "Sending"
    doc.save(ignore_permissions=True)

    # -------------------------------
    # Enqueue background job
    # -------------------------------
    frappe.enqueue(
        method=process_payroll_email,
        queue="long",
        timeout=300,
        is_async=True,
        job_name=f"Payroll Email: {batch_name} - {now()}",
        batch_name=batch_name
    )

    frappe.msgprint(
        msg="Email sending has started in background.",
        title="Email Sending Started",
        indicator="green",
		alert=True
    )


def process_payroll_email(batch_name):
	"""
	Process payroll emails in the background.
	"""

	frappe.set_user("Administrator")  # required for background jobs

	doc = frappe.get_doc("Payroll Email", batch_name)

	sent_count = 0
	failed_count = 0

	email_account = frappe.get_doc("Email Account", doc.email_account)

	for row in doc.payroll_email_details:

		if row.status != "Pending":
			continue

		try:
			# ------------------------------------------
			# Salary Slip validation
			# ------------------------------------------
			salary_slip = frappe.get_doc("Salary Slip", row.salary_slip)
			if salary_slip.docstatus != 1:
				raise Exception("Salary Slip is not submitted")

			# ------------------------------------------
			# Duplicate protection
			# ------------------------------------------
			already_sent = frappe.db.exists(
				"Payroll Email Item",
				{
					"salary_slip": row.salary_slip,
					"status": "Sent"
				}
			)
			if already_sent:
				row.status = "Skipped"
				row.error_log = "Salary Slip already emailed in another batch"
				continue

			# ------------------------------------------
			# Email validation
			# ------------------------------------------
			if not row.employee_email:
				raise Exception("Employee email is missing")

			receiver = validate_email_address(row.employee_email)
			if not receiver:
				raise Exception(f"Invalid email address: {row.employee_email}")

			# ------------------------------------------
			# Generate PDF
			# ------------------------------------------
			payroll_settings = frappe.get_single("Payroll Settings")
			employee_doc = frappe.get_doc("Employee", row.employee)
			subject = f"Salary Slip - from {doc.from_date} to {doc.to_date}"
			message = "Please see attachment"
			if payroll_settings.email_template:
				email_template = frappe.get_doc("Email Template", payroll_settings.email_template)
				context = salary_slip.as_dict()
				subject = frappe.render_template(email_template.subject, context)
				message = frappe.render_template(email_template.response, context)
			
			password = None
			if payroll_settings.encrypt_salary_slips_in_emails:
				password = payroll_settings.password_policy.format(**employee_doc.as_dict())
				if not payroll_settings.email_template:
					message += "<br>" + "Note: Your salary slip is password protected, the password to unlock the PDF is of the format {0}.".format(payroll_settings.password_policy)

			# salary slip file method
			pdf_file_name = f"{row.salary_slip}-{frappe.generate_hash(length=5)}.pdf"		
			generated_file = frappe.attach_print("Salary Slip", row.salary_slip, file_name=pdf_file_name, password=password)	
			pdf_content = generated_file.get("fcontent")


			if receiver:
				email_args = {
					"sender": email_account.email_id,
					"recipients": [receiver],
					"message": message,
					"subject": subject,
					"attachments": [generated_file],
					"reference_doctype": doc.doctype,
					"reference_name": doc.name,
					"now": True
				}
				# ------------------------------------------
				# Send email
				# ------------------------------------------
				frappe.sendmail(**email_args)

			if pdf_content:
				file_doc = frappe.new_doc("File")
				file_doc.update({
					"file_name": pdf_file_name,
					"attached_to_doctype": doc.doctype,
					"attached_to_name": doc.name,
					"content": pdf_content,
					"is_private": 1
				})
				file_doc.insert(ignore_permissions=True)

				row.salary_slip_pdf = file_doc.file_url

			# ------------------------------------------
			# Success
			# ------------------------------------------
			row.status = "Sent"
			row.sent_on = now()
			row.error_detail = None
			sent_count += 1

		except Exception:
			row.status = "Failed"
			row.retry_count = (row.retry_count or 0) + 1
			row.error_detail = frappe.get_traceback()
			failed_count += 1
			frappe.log_error(
				title="Payroll Email Error", 
				message=frappe.get_traceback(),
				ref_doctype=doc.doctype,
				ref_name=doc.name
			)

	# ------------------------------------------
	# Finalize batch
	# ------------------------------------------
	doc.sent_count = sent_count
	doc.failed_count = failed_count

	if failed_count == 0:
		doc.status = "Sent"
	elif sent_count > 0:
		doc.status = "Partial Failed"
	else:
		doc.status = "Failed"

	doc.save(ignore_permissions=True)
