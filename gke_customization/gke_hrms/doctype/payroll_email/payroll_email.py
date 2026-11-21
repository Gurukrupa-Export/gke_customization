import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.query_builder import DocType
from frappe.utils import now, now_datetime, validate_email_address


class PayrollEmail(Document):
    def autoname(self):
        if not self.company:
            frappe.throw(_("Company is required to generate Payroll Email ID"))

        # Fetch Company Abbreviation
        company_abbr = frappe.db.get_value("Company", self.company, "abbr")
        if not company_abbr:
            frappe.throw(
                _("Company abbreviation not found for {0}").format(self.company)
            )

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
                    msg=_(
                        "Duplicate employee email found: {0} <br> Employees: {1} -- {2}"
                    ).format(
                        frappe.bold(email),
                        frappe.bold(row.employee),
                        row.employee_name or _("Unknown"),
                    ),
                    title=_("Duplicate Employee Email"),
                )

            email_map[email] = row.employee_name

    def _validate_duplicate_salary_slips(self):
        seen = set()

        for row in self.payroll_email_details:
            if not row.salary_slip:
                continue

            if row.salary_slip in seen:
                frappe.throw(
                    msg=_("Duplicate Salary Slip found: {0}").format(
                        frappe.bold(row.salary_slip)
                    ),
                    title=_("Duplicate Salary"),
                )

            seen.add(row.salary_slip)

    def _set_total_slips(self):
        self.total_slips = len(self.payroll_email_details)

        self.sent_count = len(
            [row for row in self.payroll_email_details if row.status == "Sent"]
        )
        self.failed_count = len(
            [row for row in self.payroll_email_details if row.status == "Failed"]
        )
        self.skipped_count = len(
            [row for row in self.payroll_email_details if row.status == "Skipped"]
        )


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
    required_fields = {"company": _("Company"), "payroll_entry": _("Payroll Entry")}

    for field, label in required_fields.items():
        if not filters.get(field):
            frappe.throw(_("{0} is required").format(label))

    # --------------------------------------------------
    # 2. VALIDATE PAYROLL ENTRY
    # --------------------------------------------------
    payroll_entry = frappe.db.get_value(
        "Payroll Entry",
        filters["payroll_entry"],
        ["name", "company", "docstatus"],
        as_dict=True,
    )
    if not payroll_entry:
        frappe.throw(_("Payroll Entry {0} not found").format(filters["payroll_entry"]))

    if payroll_entry.company != filters["company"]:
        frappe.throw(
            _("Selected Payroll Entry does not belong to the selected Company")
        )

    if payroll_entry.docstatus != 1:
        frappe.throw(_("Payroll Entry must be submitted"))

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
            _("Bank Entry is not created for Payroll Entry {0}").format(
                payroll_entry.name
            )
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
            Employee.personal_email,
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
        frappe.throw(
            _("No submitted Salary Slips found for the selected Payroll Entry")
        )

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
            reason = _("No Email or Invalid Email")
        else:
            status = "Pending"
            reason = None

        results.append(
            {
                "employee": slip.employee,
                "employee_name": slip.employee_name,
                "salary_slip": slip.salary_slip,
                "employee_email": employee_email,
                "status": status,
                "error_detail": reason,
            }
        )

    return results


@frappe.whitelist()
def send_payroll_emails(batch_name):
    doc = frappe.get_doc("Payroll Email", batch_name)

    # -------------------------------
    # Validations (same as before)
    # -------------------------------
    if doc.status == "Sending":
        frappe.throw(_("Email sending is already in progress"))

    if doc.status not in ("Draft", "Partial Failed", "Failed"):
        frappe.throw(
            _("Emails can be sent only when status is Draft or Partial or Failed")
        )

    if not doc.email_account:
        frappe.throw(_("Please select an Email Account"))

    if not any(
        row.status in ["Pending", "Failed"] for row in doc.payroll_email_details
    ):
        frappe.throw(_("No pending emails to send"))

    if not frappe.db.get_value("Email Account", doc.email_account, "enable_outgoing"):
        frappe.throw(_("Selected Email Account is not enabled for outgoing emails"))

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
        timeout=max(300, len(doc.payroll_email_details) * 30),
        is_async=True,
        job_name=f"Payroll Email: {batch_name} - {now()}",
        batch_name=batch_name,
    )

    frappe.msgprint(
        msg=_("Email sending has started in background."),
        title=_("Email Sending Started"),
        indicator="green",
        alert=True,
    )


def process_payroll_email(batch_name):
    """
    Process payroll emails in the background.
    """

    original_user = frappe.session.user
    frappe.set_user("Administrator")  # required for background jobs

    try:
        _process_payroll_email(batch_name)
    except Exception:
        frappe.db.rollback()
        _release_batch_lock(batch_name)
        frappe.log_error(
            title="Payroll Email Error",
            message=frappe.get_traceback(),
            ref_doctype="Payroll Email",
            ref_name=batch_name,
        )
    finally:
        frappe.set_user(original_user)


def _release_batch_lock(batch_name):
    """Move a batch stuck in Sending to a retryable status, keeping rows already sent."""
    has_sent_rows = frappe.db.exists(
        "Payroll Email Detail",
        {"parent": batch_name, "parenttype": "Payroll Email", "status": "Sent"},
    )
    status = "Partial Failed" if has_sent_rows else "Failed"
    frappe.db.set_value("Payroll Email", batch_name, "status", status)
    frappe.db.commit()


def _process_payroll_email(batch_name):
    doc = frappe.get_doc("Payroll Email", batch_name)

    payroll_settings = frappe.get_single("Payroll Settings")
    payroll_email_template = payroll_settings.get("email_template")

    sent_count = 0
    failed_count = 0

    sender_email = frappe.db.get_value("Email Account", doc.email_account, "email_id")

    retryable_statuses = ("Pending", "Failed")
    pending_slips = [
        row.salary_slip
        for row in doc.payroll_email_details
        if row.status in retryable_statuses
    ]
    slip_docstatus = dict(
        frappe.get_all(
            "Salary Slip",
            filters={"name": ["in", pending_slips]},
            fields=["name", "docstatus"],
            as_list=True,
        )
    )
    already_sent_slips = set(
        frappe.get_all(
            "Payroll Email Detail",
            filters={
                "salary_slip": ["in", pending_slips],
                "status": "Sent",
                "parent": ["!=", doc.name],
            },
            pluck="salary_slip",
        )
    )

    for row in doc.payroll_email_details:
        if row.status not in retryable_statuses:
            continue

        try:
            # ------------------------------------------
            # Salary Slip validation
            # ------------------------------------------
            if slip_docstatus.get(row.salary_slip) != 1:
                raise Exception(_("Salary Slip is not submitted"))

            # ------------------------------------------
            # Duplicate protection
            # ------------------------------------------
            if row.salary_slip in already_sent_slips:
                row.status = "Skipped"
                row.error_detail = _("Salary Slip already emailed in another batch")
                continue

            # ------------------------------------------
            # Email validation
            # ------------------------------------------
            if not row.employee_email:
                raise Exception(_("Employee email is missing"))

            receiver = validate_email_address(row.employee_email)
            if not receiver:
                raise Exception(
                    _("Invalid email address: {0}").format(row.employee_email)
                )

            # ------------------------------------------
            # Generate PDF
            # ------------------------------------------
            subject = _("Salary Slip - from {0} to {1}").format(
                doc.from_date, doc.to_date
            )
            message = _("Please see attachment")
            if payroll_email_template:
                email_template = frappe.get_cached_doc(
                    "Email Template", payroll_email_template
                )
                context = frappe.get_doc("Salary Slip", row.salary_slip).as_dict()
                subject = frappe.render_template(email_template.subject, context)
                message = frappe.render_template(email_template.response, context)

            password = None
            if payroll_settings.encrypt_salary_slips_in_emails:
                employee_doc = frappe.get_doc("Employee", row.employee)
                password = payroll_settings.password_policy.format(
                    **employee_doc.as_dict()
                )
                if not payroll_email_template:
                    message += "<br>" + _(
                        "Note: Your salary slip is password protected, the password to unlock the PDF is of the format {0}."
                    ).format(payroll_settings.password_policy)

            # salary slip file method
            pdf_file_name = f"{row.salary_slip}-{frappe.generate_hash(length=5)}.pdf"
            generated_file = frappe.attach_print(
                "Salary Slip",
                row.salary_slip,
                file_name=pdf_file_name,
                password=password,
            )
            pdf_content = generated_file.get("fcontent")

            frappe.sendmail(
                sender=sender_email,
                recipients=[receiver],
                message=message,
                subject=subject,
                attachments=[generated_file],
                reference_doctype=doc.doctype,
                reference_name=doc.name,
                now=True,
            )

            # Mark as sent before saving the PDF so a failed File insert never re-sends the email
            row.status = "Sent"
            row.sent_on = now()
            row.error_detail = None
            sent_count += 1

            if pdf_content:
                try:
                    file_doc = frappe.new_doc("File")
                    file_doc.update(
                        {
                            "file_name": pdf_file_name,
                            "attached_to_doctype": doc.doctype,
                            "attached_to_name": doc.name,
                            "content": pdf_content,
                            "is_private": 1,
                        }
                    )
                    file_doc.insert(ignore_permissions=True)

                    row.salary_slip_pdf = file_doc.file_url
                except Exception:
                    frappe.log_error(
                        title="Payroll Email PDF Attach Error",
                        message=frappe.get_traceback(),
                        ref_doctype=doc.doctype,
                        ref_name=doc.name,
                    )

        except Exception as e:
            row.status = "Failed"
            row.retry_count = (row.retry_count or 0) + 1
            row.error_detail = str(e)
            failed_count += 1
            frappe.log_error(
                title="Payroll Email Error",
                message=frappe.get_traceback(),
                ref_doctype=doc.doctype,
                ref_name=doc.name,
            )

        finally:
            # Persist each row so a crash or rerun never re-sends rows already sent
            row.db_update()
            frappe.db.commit()

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
