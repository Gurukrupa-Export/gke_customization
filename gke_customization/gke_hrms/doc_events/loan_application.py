import frappe
from dateutil.relativedelta import relativedelta
from frappe import _
from frappe.utils import cint, flt, getdate


def get_grade_level(grade):
    level = (grade or "").split("-")[-1].strip()
    if not level.isdigit():
        frappe.throw(
            _("Could not read the level from Employee Grade {0}.").format(grade)
        )

    return cint(level)


def validate(self, method=None):
    loan_eligibility_months = 12

    if not self.applicant:
        return

    applicant = frappe.db.get_value(
        "Employee",
        self.applicant,
        ["ctc", "date_of_joining", "grade"],
        as_dict=True,
    )
    if not applicant:
        frappe.throw(_("Employee {0} not found.").format(self.applicant))

    last_app = frappe.get_all(
        "Loan Application",
        filters={
            "applicant": self.applicant,
            "name": ["!=", self.name],
            "docstatus": 1,
        },
        fields=["posting_date"],
        order_by="posting_date desc",
        limit=1,
    )
    max_loan_amount = 2 * flt(applicant.ctc)
    if flt(self.loan_amount) > max_loan_amount:
        frappe.throw(
            _("You can't apply for this loan amount. Maximum allowed is {0}").format(
                max_loan_amount
            )
        )
    joining_date_applicant = getdate(applicant.date_of_joining)
    current_posting_date = getdate(self.posting_date)

    if last_app:
        last_posting_date = getdate(last_app[0].posting_date)

        allowed_date = last_posting_date + relativedelta(months=+18)

        if current_posting_date < allowed_date:
            frappe.throw(
                _(
                    "You cannot apply for a loan before 1.5 years from your last loan application."
                )
            )

    allowed_date_applicant = joining_date_applicant + relativedelta(
        months=+loan_eligibility_months
    )
    if current_posting_date < allowed_date_applicant:
        frappe.throw(
            _("You cannot apply for a loan before 1 years from your Joining Date")
        )

    if not self.custom_loan_guarantor:
        return

    applicant_level = get_grade_level(applicant.grade)

    guarantor_ids = [g.employee for g in self.custom_loan_guarantor if g.employee]
    guarantor_details = {}
    if guarantor_ids:
        guarantor_details = {
            emp.name: emp
            for emp in frappe.get_all(
                "Employee",
                filters={"name": ["in", guarantor_ids]},
                fields=["name", "grade", "date_of_joining"],
            )
        }

    for g in self.custom_loan_guarantor:
        if not g.employee:
            continue
        guarantor = guarantor_details.get(g.employee)
        if not guarantor:
            continue
        if not guarantor.grade:
            continue
        g_level = get_grade_level(guarantor.grade)

        if g_level > applicant_level:
            frappe.throw(
                _("Guarantor {0} has a lower grade ({1}) than applicant ({2}).").format(
                    g.employee, guarantor.grade, applicant.grade
                )
            )

        joining_date = getdate(guarantor.date_of_joining)
        allowed_date_for_guarantor = joining_date + relativedelta(months=+18)
        if current_posting_date < allowed_date_for_guarantor:
            frappe.throw(
                _(
                    "Guarantor {0} cannot be selected before completing 1.5 years from their Joining Date."
                ).format(g.employee)
            )

    if not guarantor_ids:
        return

    existing = frappe.db.sql(
        """
        SELECT
            lg.employee,
            la.name,
            la.workflow_state
        FROM `tabLoan Guarantor` lg

        INNER JOIN `tabLoan Application` la
            ON la.name = lg.parent

        WHERE lg.employee IN %(employees)s
        AND lg.parenttype = 'Loan Application'
        AND lg.parent != %(current_parent)s
        AND IFNULL(la.workflow_state, '') NOT IN ('Rejected', 'Cancelled')
    """,
        {"employees": tuple(guarantor_ids), "current_parent": self.name},
        as_dict=True,
    )

    if existing:
        used = [
            f"{row.employee} (Loan: {row.name}, Status: {row.workflow_state})"
            for row in existing
        ]

        frappe.throw(
            _(
                "You cannot select this employee as guarantor because they are already "
                "assigned in another active loan application:<br><br>{0}"
            ).format("<br>".join(used))
        )
