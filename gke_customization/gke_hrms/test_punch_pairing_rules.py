# Copyright (c) 2026, Gurukrupa Export
"""
Tests for the session-based punch pairing engine. Run with:
bench --site <site_name> run-tests --module gke_customization.gke_hrms.test_punch_pairing_rules

Uses IntegrationTestCase so no Frappe/ERPNext test records are bootstrapped;
all master data (shifts, employee, holiday list) is created here if missing.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, get_datetime

DAY_SHIFT = "8:30 TO 18:30 - KGJPL"
LONG_DAY_SHIFT = "7:30 TO 18:30 - KGJPL"
NIGHT_SHIFT = "20:00 TO 08:00 - KGJPL"

TEST_EMPLOYEE_ID = "PP-TEST-ENG"
TEST_MANAGER_ID = "PP-TEST-MGR"
TEST_HOLIDAY_LIST = "KGJPL-Holiday"
TEST_COMPANY = "KGJPL Test"
TEST_DEPARTMENT = "Central - KGJPL"
TEST_DESIGNATION = "Accountant"
TEST_APPROVER_EMAIL = "pp.account@kggk.com"
BASE_DATE = "2026-12-01"

# (name, start_time, end_time, allow_check_out_after_shift_end_time,
#  begin_check_in_before_shift_start_time) as configured on kggk.local
SHIFT_CONFIGS = [
    (DAY_SHIFT, "08:30:00", "18:30:00", 715, 120),
    (LONG_DAY_SHIFT, "07:30:00", "18:30:00", 655, 120),
    (NIGHT_SHIFT, "20:00:00", "08:00:00", 660, 59),
]


def _get_or_insert(doctype: str, name: str, values: dict) -> str:
    existing = frappe.db.exists(doctype, name)
    if existing:
        return existing
    return frappe.get_doc({"doctype": doctype, **values}).insert().name


# Never auto-created by the generic helpers below; the suite creates or
# resolves these explicitly (Company/User/Employee) or they are too central to guess.
_NEVER_AUTOCREATE = frozenset({"Employee", "User", "Company"})


def _dummy_value(df, depth: int):
    """A valid throw-away value for a mandatory field, based on its fieldtype."""
    ft = df.fieldtype
    if ft in ("Data", "Small Text", "Text", "Long Text", "Text Editor", "Markdown Editor", "Read Only"):
        option = (df.options or "").strip()
        return {"Email": "pp.test@example.com", "Phone": "9999999999", "URL": "https://example.com"}.get(
            option, "Test"
        )
    if ft == "Select":
        options = [o for o in (df.options or "").split("\n") if o]
        return options[0] if options else None
    if ft == "Link":
        return _any_master(df.options, depth + 1)
    if ft == "Date":
        return "2020-01-01"
    if ft == "Datetime":
        return "2020-01-01 00:00:00"
    if ft == "Time":
        return "00:00:00"
    if ft in ("Int", "Float", "Currency", "Percent"):
        return 1
    return None


def _fill_mandatory(doctype: str, values: dict, depth: int = 0) -> dict:
    """Fill every still-empty mandatory field of `doctype` in `values`, so masters
    (and the employee) survive extra `reqd` fields added by custom apps."""
    skip_types = set(frappe.model.no_value_fields) | {"Check", "Table", "Table MultiSelect"}
    for df in frappe.get_meta(doctype).fields:
        if not df.reqd or df.fieldtype in skip_types or df.fetch_from or df.default:
            continue
        if values.get(df.fieldname) not in (None, ""):
            continue
        value = _dummy_value(df, depth)
        if value is not None:
            values[df.fieldname] = value
    return values


def _ensure_master(doctype: str, name: str, values: dict | None = None, depth: int = 0) -> str:
    """Return `name` if the record exists, else insert it with just enough data
    (naming field from the doctype's autoname + every mandatory field).
    Returns the record's actual name (may differ if autoname is not name-based)."""
    if frappe.db.exists(doctype, name):
        return name

    doc_values = {"doctype": doctype, **(values or {})}
    autoname = (frappe.get_meta(doctype).autoname or "").strip()
    if autoname.startswith("field:"):
        doc_values.setdefault(autoname[len("field:") :], name)
    elif autoname.lower() in ("prompt", ""):
        doc_values["__newname"] = name

    _fill_mandatory(doctype, doc_values, depth)
    _ensure_links(doctype, doc_values, depth)
    return frappe.get_doc(doc_values).insert(ignore_permissions=True).name


def _any_master(doctype: str, depth: int = 0):
    existing = frappe.get_all(doctype, limit=1, pluck="name")
    if existing:
        return existing[0]
    if depth > 3 or doctype in _NEVER_AUTOCREATE:
        return None
    return _ensure_master(doctype, f"PP Test {doctype}", depth=depth)


def _ensure_links(doctype: str, values: dict, depth: int = 0) -> dict:
    """Make sure every Link value in `values` (including child-table rows) points
    to an existing master, creating the missing ones."""
    for df in frappe.get_meta(doctype).fields:
        value = values.get(df.fieldname)
        if not value:
            continue
        if df.fieldtype == "Link" and df.options and df.options not in _NEVER_AUTOCREATE:
            if not frappe.db.exists(df.options, value):
                values[df.fieldname] = _ensure_master(df.options, value, depth=depth + 1)
        elif df.fieldtype == "Table":
            for row in value:
                _ensure_links(df.options, row, depth)
    return values


def ensure_master_data() -> None:
    """Create every master the test employee/checkins depend on, so the
    suite runs on a fresh site. Existing records are left untouched."""
    company = frappe.db.get_value("Company", {"is_group": 0}, "name")
    if not company:
        company = frappe.get_doc(
            {
                "doctype": "Company",
                "company_name": TEST_COMPANY,
                "abbr": "KGT",
                "country": "India",
                "default_currency": "INR",
                "is_group": 0,
            }
        ).insert().name

    for name, start_time, end_time, allow_checkout, begin_checkin in SHIFT_CONFIGS:
        if not frappe.db.exists("Shift Type", name):
            frappe.get_doc(
                {
                    "doctype": "Shift Type",
                    "__newname": name,
                    "start_time": start_time,
                    "end_time": end_time,
                    "enable_auto_attendance": 1,
                    "allow_check_out_after_shift_end_time": allow_checkout,
                    "begin_check_in_before_shift_start_time": begin_checkin,
                    "late_entry_grace_period": 5,
                    "determine_check_in_and_check_out": (
                        "Alternating entries as IN and OUT during the same shift"
                    ),
                }
            ).insert()

    # Department autoname appends the company abbr (e.g. "Central - KGJPL - D"),
    # so only ensure it exists here; the employee resolves the actual name
    if not frappe.db.get_value("Department", {"department_name": TEST_DEPARTMENT}, "name"):
        frappe.get_doc(
            {
                "doctype": "Department",
                "department_name": TEST_DEPARTMENT,
                "company": company,
                "is_group": 0,
            }
        ).insert()

    _get_or_insert(
        "Designation", TEST_DESIGNATION, {"designation_name": TEST_DESIGNATION}
    )

    if not frappe.db.exists("User", TEST_APPROVER_EMAIL):
        frappe.get_doc(
            {
                "doctype": "User",
                "email": TEST_APPROVER_EMAIL,
                "first_name": "Accounts",
                "last_name": "KGJPL",
                "roles": [
                    {"role": role}
                    for role in ("Leave Approver", "Expense Approver", "HR Manager")
                    if frappe.db.exists("Role", role)
                ],
            }
        ).insert(ignore_permissions=True)


def build_employee_values(employee_number: str, name: str, manager: str | None = None) -> dict:
    """Employee values mirroring a real record on kggk.local (personal data replaced
    with dummy values). Every Link master it points to is created if missing, and any
    other mandatory field the site adds later is filled generically."""
    first, middle, last = name.split(" ", 2)
    email = "pp.test@example.com"
    values = {
        "doctype": "Employee",
        "naming_series": "HR-EMP-",
        "first_name": first,
        "middle_name": middle,
        "last_name": last,
        "employee_name": name,
        "employee_number": employee_number,
        "gender": "Male",
        "salutation": "Mr",
        "date_of_birth": "1990-01-01",
        "date_of_joining": "2020-01-01",
        "old_employee_code": employee_number,
        "old_punch_id": employee_number,
        "attendance_device_id": employee_number,
        "status": "Active",
        "create_user_permission": 1,
        "create_user_automatically": 0,
        "company": frappe.db.get_value("Company", {"is_group": 0}, "name"),
        # autoname may suffix the company abbr, so resolve by name
        "department": frappe.db.get_value("Department", {"department_name": TEST_DEPARTMENT}, "name"),
        "employment_type": "Full-time",
        "custom_probation_period_days": "90",
        "designation": TEST_DESIGNATION,
        "manufacturer": "Labh",
        "branch": "KGJPL-ST-0001",
        "grade": "RL-10",
        "scheduled_confirmation_date": "2020-01-01",
        "final_confirmation_date": "2020-03-30",
        "notice_number_of_days": 0,
        "custom_notice_dayes": "30",
        "cell_number": "9999999999",
        "personal_email": email,
        "prefered_contact_email": "Personal Email",
        "prefered_email": email,
        "unsubscribed": 0,
        "current_address": "Test Address",
        "current_accommodation_type": "Rented",
        "same_as_current_address": 0,
        "custom_city": "Surat",
        "permanent_address": "Test Address",
        "permanent_accommodation_type": "Owned",
        "allowed_personal_hours": "3:00:00",
        "product_incentive_applicable": 1,
        "holiday_list": _ensure_master(
            "Holiday List", TEST_HOLIDAY_LIST, {"from_date": "2026-01-01", "to_date": "2027-12-31"}
        ),
        "default_shift": DAY_SHIFT,
        "expense_approver": TEST_APPROVER_EMAIL,
        "leave_approver": TEST_APPROVER_EMAIL,
        "shift_request_approver": TEST_APPROVER_EMAIL,
        "ctc": 0,
        "salary_currency": "INR",
        "salary_mode": "Bank",
        "employee_name_as_per_bank_account": "0",
        "bank_name": "0",
        "bank_ac_no": "0",
        "ifsc_code": "0",
        "marital_status": "Single",
        "health_insurance_provider": "New India Assurance",
        "custom_health_insurance_status": "Pending",
        "custom_sum_assured_": "1 Lakh",
        "custom_accident_insurance_provider": "Care Health Insurance",
        "custom_accident_insurance_status": "Pending",
        "custom_sum_assured_accident_insurance_": "10 Lakh",
        "religon": "Hindu",
        "employee_cast": "ST",
        "reference_type": "Employee Referral",
        "reference_employee_name": "PP Pairing Manager",
        "reference_contact": "9999999999",
        "reference_address": "Test Address",
        "aadhar_number": "123412341234",
        "name_as_per_aadhar": name,
        "leave_encashed": "Yes",
        "is_pf_applicable": 0,
        "custom_is_esic_applicable": 0,
        "pan_number": "ABCDE1234F",
        "name_as_pe_pan": name,
        "handicap_percenatge": 0,
        "is_physical_handicap": 0,
        "variable_in": 0,
        "education": [{"level": "Under Graduate", "year_of_passing": 0}],
        "external_work_history": [{"salary": 0}],
        "employee_family_background": [
            {
                "name1": "PP Father",
                "relation": "Father",
                "birth_date": "1987-01-01",
                "document_name": "Adharcard",
                "document_number": "123412341234",
                "same_as_present": 1,
                "same_as_permanent": 0,
                "is_nominee": 0,
                "nominee_share": 0,
            },
            {
                "name1": "PP Mother",
                "relation": "Mother",
                "birth_date": "1990-01-01",
                "document_name": "Adharcard",
                "document_number": "123412341234",
                "same_as_present": 0,
                "same_as_permanent": 0,
                "is_nominee": 0,
                "nominee_share": 0,
            },
        ],
        "emergency_contact_details_table": [
            {"emergency_contact_name": "PP Uncle", "emergency_phone": "9999999999", "relation": "Uncle"},
            {"emergency_contact_name": "PP Mother", "emergency_phone": "9999999999", "relation": "Mother"},
        ],
    }
    if manager:
        values["reports_to"] = manager
        values["reference_employee_code"] = manager

    _fill_mandatory("Employee", values)
    _ensure_links("Employee", values)
    return values


def punch_time(day_offset: int, time_str: str):
    return get_datetime(f"{add_days(BASE_DATE, day_offset)} {time_str}")


class TestPunchPairing(IntegrationTestCase):
    # Deliberately empty: do not let Frappe/ERPNext generate test records for
    # Employee, Company, Holiday List, etc. ensure_master_data() owns all data.
    EXTRA_TEST_RECORD_DEPENDENCIES: list[str] = []

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ensure_master_data()
        cls._enable_session_pairing()
        cls.employee = cls._get_or_create_test_employee()

    @staticmethod
    def _enable_session_pairing():
        if not frappe.get_meta("HR Settings").has_field("enable_session_pairing") or not frappe.get_meta(
            "Employee Checkin"
        ).has_field("punch_rule"):
            raise AssertionError(
                "Punch pairing custom fields are missing on this site; run "
                "`bench --site kggk.test migrate` (patch gke_customization.patches.punch_pairing_fields)."
            )
        frappe.db.set_single_value("HR Settings", "enable_session_pairing", 1)

    @classmethod
    def _get_or_create_test_employee(cls) -> str:
        existing = frappe.db.exists("Employee", {"employee_number": TEST_EMPLOYEE_ID})
        if existing:
            return existing

        # reports_to is mandatory on this site and links to another Employee, so the
        # manager is created first. It is the only record inserted with
        # ignore_mandatory, because its own reports_to would otherwise be circular.
        manager = frappe.db.exists("Employee", {"employee_number": TEST_MANAGER_ID})
        if not manager:
            manager_doc = frappe.get_doc(build_employee_values(TEST_MANAGER_ID, "PP Pairing Manager"))
            manager_doc.flags.ignore_mandatory = True
            manager = manager_doc.insert().name

        values = build_employee_values(TEST_EMPLOYEE_ID, "PP Pairing Test", manager)
        return frappe.get_doc(values).insert().name

    def set_shift(self, shift_type: str):
        frappe.db.set_value("Employee", self.employee, "default_shift", shift_type)

    def checkin(self, punch_dt):
        doc = frappe.get_doc(
            {
                "doctype": "Employee Checkin",
                "employee": self.employee,
                "time": punch_dt,
                "source": "Biometric",
            }
        ).insert()
        # fresh read, not get_cached_doc: the class rollback reuses the same checkin
        # names (naming series) on the next run, so a cached doc can be a stale copy
        return frappe.get_doc("Employee Checkin", doc.name)

    def assert_punch(self, doc, expected_rule, expected_log_type, shift_type):
        self.assertEqual(doc.punch_rule, expected_rule)
        self.assertEqual(doc.log_type, expected_log_type)
        self.assertEqual(doc.shift, shift_type)
        self.assertFalse(doc.offshift)

    # ---- cases -----------------------------------------------------

    def test_post_shift_end_return_binds_inside_checkout_window(self):
        """19:05 is inside [08:30, 18:30 + 715min = 06:25 next day] -> legacy parity."""
        self.set_shift(DAY_SHIFT)
        c1 = self.checkin(punch_time(0, "06:57:00"))
        c2 = self.checkin(punch_time(0, "08:52:00"))
        c3 = self.checkin(punch_time(0, "19:05:00"))

        self.assert_punch(c1, "R1", "IN", DAY_SHIFT)
        self.assert_punch(c2, "R2", "OUT", DAY_SHIFT)
        self.assert_punch(c3, "R3", "IN", DAY_SHIFT)

    def test_personal_out_and_return_inside_shift_span(self):
        self.set_shift(DAY_SHIFT)
        c1 = self.checkin(punch_time(5, "08:10:00"))
        c2 = self.checkin(punch_time(5, "12:00:00"))
        c3 = self.checkin(punch_time(5, "13:00:00"))

        self.assert_punch(c1, "R1", "IN", DAY_SHIFT)
        self.assert_punch(c2, "R2", "OUT", DAY_SHIFT)
        self.assert_punch(c3, "R3", "IN", DAY_SHIFT)

    def test_early_morning_punch_closes_previous_long_session(self):
        """Checkout window of 7:30-18:30 shift ends 05:25 next day; 04:35 is
        closer to that end than to the 07:30 start, so it closes the
        previous 21h session instead of opening a new one."""
        self.set_shift(LONG_DAY_SHIFT)
        c1 = self.checkin(punch_time(10, "07:27:00"))
        c2 = self.checkin(punch_time(11, "04:35:00"))
        c3 = self.checkin(punch_time(11, "07:26:00"))
        c4 = self.checkin(punch_time(11, "16:23:00"))
        c5 = self.checkin(punch_time(12, "07:28:00"))

        self.assert_punch(c1, "R1", "IN", LONG_DAY_SHIFT)
        self.assert_punch(c2, "R2", "OUT", LONG_DAY_SHIFT)
        self.assert_punch(c3, "R1", "IN", LONG_DAY_SHIFT)
        self.assert_punch(c4, "R2", "OUT", LONG_DAY_SHIFT)
        self.assert_punch(c5, "R1", "IN", LONG_DAY_SHIFT)

    def test_forgot_checkout_inside_checkout_window_becomes_late_out(self):
        self.set_shift(DAY_SHIFT)
        c1 = self.checkin(punch_time(15, "09:00:00"))
        c2 = self.checkin(punch_time(16, "05:00:00"))

        self.assert_punch(c1, "R1", "IN", DAY_SHIFT)
        self.assert_punch(c2, "R2", "OUT", DAY_SHIFT)

    def test_next_day_punch_after_checkout_window_starts_new_day(self):
        self.set_shift(DAY_SHIFT)
        c1 = self.checkin(punch_time(20, "09:00:00"))
        c2 = self.checkin(punch_time(21, "10:00:00"))

        self.assert_punch(c1, "R1", "IN", DAY_SHIFT)
        self.assert_punch(c2, "R1", "IN", DAY_SHIFT)

    def test_night_shift_in_before_midnight_out_after(self):
        self.set_shift(NIGHT_SHIFT)
        c1 = self.checkin(punch_time(25, "19:55:00"))
        c2 = self.checkin(punch_time(26, "06:30:00"))
        c3 = self.checkin(punch_time(26, "19:30:00"))

        self.assert_punch(c1, "R1", "IN", NIGHT_SHIFT)
        self.assert_punch(c2, "R2", "OUT", NIGHT_SHIFT)
        self.assert_punch(c3, "R1", "IN", NIGHT_SHIFT)

    def test_device_bounce_is_skipped(self):
        self.set_shift(DAY_SHIFT)
        c1 = self.checkin(punch_time(30, "08:00:00"))
        c2 = self.checkin(punch_time(30, "08:01:00"))

        self.assert_punch(c1, "R1", "IN", DAY_SHIFT)
        self.assertEqual(c2.punch_rule, "DUP")
        self.assertEqual(c2.skip_auto_attendance, 1)

    def test_stale_session_beyond_max_session_starts_new_session(self):
        self.set_shift(DAY_SHIFT)
        c1 = self.checkin(punch_time(35, "09:00:00"))
        c2 = self.checkin(punch_time(36, "15:00:00"))

        self.assert_punch(c1, "R1", "IN", DAY_SHIFT)
        self.assert_punch(c2, "R4", "IN", DAY_SHIFT)

    def test_overnight_punch_closer_to_checkout_end_closes_session(self):
        self.set_shift(DAY_SHIFT)
        c1 = self.checkin(punch_time(40, "09:00:00"))
        c2 = self.checkin(punch_time(41, "02:00:00"))

        self.assert_punch(c1, "R1", "IN", DAY_SHIFT)
        self.assert_punch(c2, "R2", "OUT", DAY_SHIFT)