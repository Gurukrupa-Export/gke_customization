"""Base test case for the gke_customization payroll tests.

Builds on GKHRMSTestCase (company, shift, employee helpers) and adds the
payroll masters: accounts, salary components, salary structure, structure
assignment, payroll entry, salary slips and salary withholding.

Fixed amounts per employee: Basic 10000, Test Deduction 1000, so the net pay
of every slip is 9000. The statistical component (5000) must never count
towards a payment.
"""

import frappe
from frappe.utils import (
    add_days,
    add_months,
    get_first_day,
    get_last_day,
    nowdate,
)
from hrms.payroll.doctype.payroll_entry.payroll_entry import (
    create_salary_slips_for_employees,
    submit_salary_slips_for_employees,
)
from hrms.payroll.doctype.salary_component.test_salary_component import (
    create_salary_component,
)
from hrms.payroll.doctype.salary_structure.test_salary_structure import (
    make_salary_structure,
)

from gke_customization.gke_hrms.tests.base import GKHRMSTestCase

BASIC_COMPONENT = "_Test GKE Basic"
DEDUCTION_COMPONENT = "_Test GKE Deduction"
STATISTICAL_COMPONENT = "_Test GKE Statistical"
SALARY_STRUCTURE = "_Test GKE Payroll Structure"

BASIC_AMOUNT = 10000
DEDUCTION_AMOUNT = 1000
STATISTICAL_AMOUNT = 5000
NET_PAY = BASIC_AMOUNT - DEDUCTION_AMOUNT


class PayrollTestCase(GKHRMSTestCase):
    payroll_payable_account = None
    bank_account = None
    cost_center = None
    salary_structure = None
    start_date = None
    end_date = None

    @classmethod
    def setup_master_data(cls):
        super().setup_master_data()
        cls.start_date = get_first_day(add_months(nowdate(), -1))
        cls.end_date = get_last_day(cls.start_date)
        cls.cost_center = cls.ensure_cost_center()
        cls.payroll_payable_account = cls.ensure_account(
            "_Test GKE Payroll Payable", "Payable", "Current Liabilities"
        )
        cls.bank_account = cls.ensure_account("_Test GKE Bank", "Bank", "Bank Accounts")
        cls.ensure_salary_component(BASIC_COMPONENT, "Earning")
        cls.ensure_salary_component(DEDUCTION_COMPONENT, "Deduction")
        cls.ensure_salary_component(
            STATISTICAL_COMPONENT, "Earning", statistical_component=1
        )
        cls.salary_structure = cls.ensure_salary_structure()
        frappe.db.set_single_value("Payroll Settings", "payroll_based_on", "Leave")

    # ---------- accounts ----------

    @classmethod
    def ensure_cost_center(cls) -> str:
        name = frappe.db.get_value(
            "Cost Center", {"company": cls.company, "is_group": 0}, "name"
        )
        if name:
            return name
        return frappe.db.get_value(
            "Cost Center", {"company": cls.company, "is_group": 1}, "name"
        )

    @classmethod
    def ensure_account(
        cls, account_name: str, account_type: str, parent_account_name: str
    ) -> str:
        abbr = frappe.get_cached_value("Company", cls.company, "abbr")
        name = f"{account_name} - {abbr}"
        if frappe.db.exists("Account", name):
            return name
        parent = frappe.db.get_value(
            "Account",
            {
                "company": cls.company,
                "account_name": parent_account_name,
                "is_group": 1,
            },
            "name",
        )
        return cls._insert(
            {
                "doctype": "Account",
                "account_name": account_name,
                "company": cls.company,
                "parent_account": parent,
                "account_type": account_type,
                "is_group": 0,
            }
        ).name

    # ---------- salary masters ----------

    @classmethod
    def ensure_salary_component(
        cls, component: str, component_type: str, **extra
    ) -> str:
        """Reuses the hrms core helper, which only accepts the component type,
        so any extra fields (for example statistical_component) are set after."""
        salary_component = create_salary_component(component, type=component_type)
        for fieldname, value in extra.items():
            if salary_component.get(fieldname) != value:
                salary_component.db_set(fieldname, value)
        return salary_component.name

    @classmethod
    def ensure_salary_structure(cls) -> str:
        if frappe.db.exists("Salary Structure", SALARY_STRUCTURE):
            return SALARY_STRUCTURE
        return make_salary_structure(
            SALARY_STRUCTURE,
            "Monthly",
            company=cls.company,
            earnings=[
                {"salary_component": BASIC_COMPONENT, "amount": BASIC_AMOUNT},
                {
                    "salary_component": STATISTICAL_COMPONENT,
                    "amount": STATISTICAL_AMOUNT,
                },
            ],
            deductions=[
                {"salary_component": DEDUCTION_COMPONENT, "amount": DEDUCTION_AMOUNT}
            ],
        ).name

    @classmethod
    def set_employee_wise_accounting(cls, enabled: bool):
        frappe.db.set_single_value(
            "Payroll Settings",
            "process_payroll_accounting_entry_based_on_employee",
            int(enabled),
        )

    # ---------- employees, withholding, payroll entry ----------

    @classmethod
    def create_payroll_employee(cls, label: str) -> str:
        # The core create_salary_structure_assignment is not used: it hardcodes
        # _Test Company, base 50000 and deletes other assignments.
        device_id = f"GKE-T-PAY-{label}-{frappe.generate_hash(length=6)}"
        employee = cls.create_employee(f"Payroll {label}", device_id)
        cls._insert(
            {
                "doctype": "Salary Structure Assignment",
                "employee": employee.name,
                "salary_structure": cls.salary_structure,
                "from_date": add_days(cls.start_date, -30),
                "company": cls.company,
                "currency": "INR",
                "base": BASIC_AMOUNT,
            }
        ).submit()
        return employee.name

    @classmethod
    def create_salary_withholding(cls, employee: str, cycles: int = 1):
        withholding = cls._insert(
            {
                "doctype": "Salary Withholding",
                "employee": employee,
                "company": cls.company,
                "posting_date": cls.end_date,
                "from_date": cls.start_date,
                "number_of_withholding_cycles": cycles,
                "payroll_frequency": "Monthly",
            }
        )
        withholding.submit()
        return withholding

    @classmethod
    def create_payroll_entry(cls, employees: list[str]):
        entry = frappe.get_doc(
            {
                "doctype": "Payroll Entry",
                "company": cls.company,
                "posting_date": cls.end_date,
                "payroll_frequency": "Monthly",
                "start_date": cls.start_date,
                "end_date": cls.end_date,
                "currency": "INR",
                "exchange_rate": 1,
                "cost_center": cls.cost_center,
                "payroll_payable_account": cls.payroll_payable_account,
                "payment_account": cls.bank_account,
                "employees": [{"employee": employee} for employee in employees],
            }
        )
        entry.insert(ignore_permissions=True)
        entry.submit()
        return frappe.get_doc("Payroll Entry", entry.name)

    @classmethod
    def create_salary_slips(cls, entry, employees: list[str]) -> dict[str, str]:
        """Create and submit the slips directly, bypassing the queued stock job.
        Returns {employee: salary slip name}."""
        args = frappe._dict(
            payroll_entry=entry.name,
            payroll_frequency=entry.payroll_frequency,
            start_date=entry.start_date,
            end_date=entry.end_date,
            company=entry.company,
            posting_date=entry.posting_date,
        )
        create_salary_slips_for_employees(employees, args, publish_progress=False)
        slips = frappe.get_all(
            "Salary Slip",
            filters={"payroll_entry": entry.name, "docstatus": 0},
            fields=["name", "employee"],
        )
        submit_salary_slips_for_employees(
            entry, [[slip.name] for slip in slips], publish_progress=False
        )
        return {slip.employee: slip.name for slip in slips}

    @classmethod
    def create_withheld_payroll(cls, employee_count: int = 1):
        """Employees with a submitted withholding, a submitted payroll entry and
        withheld salary slips. Returns (payroll entry, [employees])."""
        employees = [
            cls.create_payroll_employee(f"W{index}") for index in range(employee_count)
        ]
        for employee in employees:
            cls.create_salary_withholding(employee)
        entry = cls.create_payroll_entry(employees)
        cls.create_salary_slips(entry, employees)
        return entry, employees

    @classmethod
    def release_withheld_salaries(
        cls, entry, employees=None, release_amounts=None, submit=True
    ):
        """Create the release Journal Entry through the Payroll Entry override."""
        journal_entry = entry.make_bank_entry(
            for_withheld_salaries=True,
            employees=employees,
            release_amounts=release_amounts,
        )
        if journal_entry and submit:
            journal_entry.submit()
        return journal_entry

    # ---------- readers ----------

    @staticmethod
    def get_cycle(employee: str) -> dict:
        return frappe.db.get_value(
            "Salary Withholding Cycle",
            {
                "parent": (
                    "in",
                    frappe.get_all(
                        "Salary Withholding",
                        {"employee": employee, "docstatus": 1},
                        pluck="name",
                    ),
                )
            },
            [
                "name",
                "parent",
                "custom_released_amount",
                "journal_entry",
                "is_salary_released",
            ],
            as_dict=True,
        )

    @staticmethod
    def get_slip_status(employee: str, payroll_entry: str) -> str:
        return frappe.db.get_value(
            "Salary Slip",
            {"employee": employee, "payroll_entry": payroll_entry, "docstatus": 1},
            "status",
        )
