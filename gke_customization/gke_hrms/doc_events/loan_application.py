
import frappe
from frappe import _
from datetime import datetime
from dateutil.relativedelta import relativedelta

def validate(self, method=None):
    loan_eligibility_months=12
    guarantors = [s for s in self.custom_loan_guarantor if s.employee]

    last_app = frappe.get_all("Loan Application",
        filters={
            "applicant": self.applicant,
            "name": ["!=", self.name],
            "docstatus": 1
        },
        fields=["posting_date"],
        order_by="posting_date desc",
        limit=1
    )
    applicant = frappe.get_doc("Employee", self.applicant)
    if self.loan_amount > 2 * applicant.ctc:
        frappe.throw(f"You can't apply for this loan amount.Maximum allowed is {2* applicant.ctc}")
    joining_date_applicant=applicant.date_of_joining
    current_posting_date = self.posting_date
    if isinstance(joining_date_applicant, str):
            joining_date_applicant = datetime.strptime(joining_date_applicant, "%Y-%m-%d").date()
    if isinstance(current_posting_date, str):
            current_posting_date = datetime.strptime(current_posting_date, "%Y-%m-%d").date()

    if last_app:
        last_posting_date = last_app[0].posting_date

        if isinstance(last_posting_date, str):
            last_posting_date = datetime.strptime(last_posting_date, "%Y-%m-%d").date()

        allowed_date = last_posting_date + relativedelta(months=+18)

        if current_posting_date < allowed_date:
            frappe.throw(
                _("You cannot apply for a loan before 1.5 years from your last loan application.")
            )

    allowed_date_applicant=joining_date_applicant + relativedelta(months=+loan_eligibility_months)
    if current_posting_date < allowed_date_applicant:
        frappe.throw(
            _("You cannot apply for a loan before 1 years from your Joining Date")
        )
    
    if not self.applicant or not self.custom_loan_guarantor:
        return

    applicant = frappe.get_doc("Employee", self.applicant)    
    applicant_level = int(applicant.grade.split("-")[-1])
    
    for g in self.custom_loan_guarantor:
        if not g.employee:
            continue
        guarantor = frappe.get_doc("Employee", g.employee)
        if not guarantor.grade:
            continue
        g_level = int(guarantor.grade.split("-")[-1])
        
        if g_level > applicant_level:
            frappe.throw(
                f"Guarantor {g.employee} has a lower grade ({guarantor.grade}) than applicant ({applicant.grade})."
            )

        joining_date=guarantor.date_of_joining
        current_posting_date = self.posting_date
        if isinstance(joining_date, str):
            joining_date = datetime.strptime(joining_date, "%Y-%m-%d").date()
        if isinstance(current_posting_date, str):
            current_posting_date = datetime.strptime(current_posting_date, "%Y-%m-%d").date()	
        allowed_date_for_guarantor = joining_date + relativedelta(months=+18)	
        if current_posting_date < allowed_date_for_guarantor:
            frappe.throw("Guarantor cannot apply for a loan before 1.5 years from your Joining")
    
    guarantor_ids = []
    for row in self.custom_loan_guarantor:
        if row.employee:
            guarantor_ids.append(row.employee)
            
    # existing = frappe.db.get_all("Loan Guarantor",
    #     filters={
    #         "employee": ["in", guarantor_ids],
    #         "parenttype": "Loan Application",
    #         "parent": ["!=", self.name]
    #     },
    #     fields=["employee", "parent"]
    # )
    
    # if existing:
    #     used = [f"{row.employee} (in {row.parent})" for row in existing]
    #     used_list = ", ".join(used)
    #     frappe.throw("You cannot select this employee as they are already a guarantor in another loan application")

    # shubham - 17-07-2026
    existing = frappe.db.sql("""
        SELECT
            lg.employee,
            la.name,
            la.workflow_state
        FROM `tabLoan Guarantor` lg

        INNER JOIN `tabLoan Application` la
            ON la.name = lg.parent

        WHERE lg.employee IN %(employees)s
        AND lg.parent != %(current_parent)s
        AND la.workflow_state NOT IN ('Rejected', 'Cancelled')
    """, {
        "employees": tuple(guarantor_ids),
        "current_parent": self.name
    }, as_dict=True)

    # frappe.throw(f"{existing}")
    if existing:

        used = [
            f"{row.employee} (Loan: {row.name}, Status: {row.workflow_state})"
            for row in existing
        ]

        frappe.throw(
            "You cannot select this employee as guarantor because they are already "
            "assigned in another active loan application:<br><br>"
            + "<br>".join(used)
        )