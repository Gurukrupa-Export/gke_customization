"""Base test case for gke_customization HRMS tests."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate

from gke_customization.gke_hrms.tests.utils import DEVICE_ID, TEST_COMPANY, load_server_scripts

REPORTS_MANAGER_DEVICE_ID = f"{DEVICE_ID}-REPORTS-MANAGER"


class GKHRMSTestCase(IntegrationTestCase):
	"""Base test case for gke_customization HRMS tests.

	setUpClass builds the master data once, in dependency order (link masters,
	warehouse type, company, holiday list, department, shift, approver user,
	reports manager), so concrete test classes only create the documents
	under test. Records are rolled back when the class finishes its run.
	"""

	DEFAULT_APPROVER = "test_default_approver@hr.com"
	SERVER_SCRIPT_DOCTYPES = None  # None = load every folder; e.g. ["employee_checkin"]

	# handles populated by setup_master_data
	gender = None
	salutation = None
	employment_type = None
	company = None
	holiday_list = None
	department = None
	shift = None
	approver = None
	insurance_provider = None
	reports_manager = None

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.setup_master_data()

	@classmethod
	def setup_master_data(cls):
		"""Create the master records the suites depend on, in dependency order."""
		cls.gender = cls.ensure_gender("Male")
		cls.salutation = cls.ensure_salutation("Mr")
		cls.employment_type = cls.ensure_employment_type("Full-time")
		cls.ensure_warehouse_type("Transit")
		cls.company = cls.create_company().name
		cls.holiday_list = cls.ensure_holiday_list(cls.company)
		cls.department = cls.ensure_department("Central", cls.company)
		cls.shift = cls.ensure_shift("test shift 9-18", company=cls.company)
		cls.approver = cls.ensure_user(cls.DEFAULT_APPROVER)
		cls.ensure_designation("Accountant")
		cls.insurance_provider = cls.ensure_insurance_provider("Care Health Insurance")
		cls.reports_manager = cls.ensure_reports_manager()

	# ---------- generic helpers ----------

	@staticmethod
	def _insert(doc: dict):
		return frappe.get_doc(doc).insert(ignore_permissions=True)

	@staticmethod
	def existing_master(doctype: str, name: str) -> str | None:
		"""Return name if the master exists, else None (the link value is then
		dropped; the site's core setup is expected to have it)."""
		return name if frappe.db.exists(doctype, name) else None

	def ensure_server_scripts(self):
		"""Create (or re-enable) the production server scripts the tests depend on."""
		for record in load_server_scripts(self.SERVER_SCRIPT_DOCTYPES):
			if frappe.db.exists("Server Script", record["name"]):
				frappe.db.set_value("Server Script", record["name"], "disabled", 0)
			else:
				self._insert(record)

		# the doc-event map is cached, and rollback doesn't clear it
		frappe.client_cache.delete_value("server_script_map")
		self.addCleanup(frappe.client_cache.delete_value, "server_script_map")

	# ---------- masters ----------

	@classmethod
	def ensure_gender(cls, gender: str) -> str:
		if frappe.db.exists("Gender", gender):
			return gender
		return cls._insert({"doctype": "Gender", "gender": gender}).name

	@classmethod
	def ensure_salutation(cls, salutation: str) -> str:
		if frappe.db.exists("Salutation", salutation):
			return salutation
		return cls._insert({"doctype": "Salutation", "salutation": salutation}).name

	@classmethod
	def ensure_employment_type(cls, employment_type: str) -> str:
		if frappe.db.exists("Employment Type", employment_type):
			return employment_type
		return cls._insert(
			{"doctype": "Employment Type", "employee_type_name": employment_type}
		).name

	@classmethod
	def ensure_warehouse_type(cls, warehouse_type: str) -> str:
		if frappe.db.exists("Warehouse Type", warehouse_type):
			return warehouse_type
		return cls._insert(
			{
				"doctype": "Warehouse Type",
				"__newname": warehouse_type,
				"warehouse_type": warehouse_type,
			}
		).name

	@classmethod
	def ensure_designation(cls, designation: str) -> str:
		if frappe.db.exists("Designation", designation):
			return designation
		return cls._insert(
			{"doctype": "Designation", "designation_name": designation}
		).name

	@classmethod
	def ensure_insurance_provider(cls, insurance: str) -> str:
		if frappe.db.exists("Employee Health Insurance", insurance):
			return insurance
		return cls._insert(
			{"doctype": "Employee Health Insurance", "health_insurance_name": insurance}
		).name

	@classmethod
	def ensure_user(cls, email: str) -> str:
		if frappe.db.exists("User", email):
			return email
		return cls._insert(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"send_welcome_email": 0,
				"enabled": 1,
			}
		).name

	@classmethod
	def ensure_department(cls, dept_name: str, company: str) -> str:
		existing = frappe.db.get_value(
			"Department", {"department_name": dept_name, "company": company}, "name"
		)
		if existing:
			return existing

		# Department names carry the company abbr suffix, so the root exists
		# as "All Departments" (no company) or "All Departments - <abbr>"
		root = frappe.db.get_value("Department", "All Departments")
		if not root:
			root = frappe.db.get_value(
				"Department", {"department_name": "All Departments"}, "name"
			)
		if not root:
			root = cls._insert(
				{
					"doctype": "Department",
					"department_name": "All Departments",
					"company": company,
					"is_group": 1,
				}
			).name

		return cls._insert(
			{
				"doctype": "Department",
				"department_name": dept_name,
				"company": company,
				"parent_department": root,
			}
		).name

	@classmethod
	def ensure_shift(
		cls, shift_name: str, start="09:00:00", end="18:00:00", company: str | None = None
	) -> str:
		if frappe.db.exists("Shift Type", shift_name):
			return shift_name
		values = {
			"doctype": "Shift Type",
			"__newname": shift_name,
			"start_time": start,
			"end_time": end,
		}
		if company and frappe.get_meta("Shift Type").has_field("custom_company"):
			values["custom_company"] = company
		return cls._insert(values).name

	@classmethod
	def ensure_holiday_list(cls, company: str | None = None) -> str:
		"""Reuse the dedicated test Holiday List for this company, or create it
		with Sunday offs. Scoped by company so tests never adopt an unrelated
		Holiday List that happens to already exist on the site."""
		list_name = f"_Test GKE Holiday List - {company}" if company else "_Test GKE Holiday List"
		if frappe.db.exists("Holiday List", list_name):
			return list_name

		today = getdate()
		values = {
			"doctype": "Holiday List",
			"holiday_list_name": list_name,
			"from_date": today.replace(month=1, day=1),
			"to_date": today.replace(month=12, day=31),
			"weekly_off": "Sunday",
		}

		if frappe.get_meta("Holiday List").has_field("custom_company"):
			values["custom_company"] = company

		return cls._insert(values).name

	# ---------- company ----------

	@classmethod
	def create_company(cls):
		"""Return the dedicated test company, creating it if needed.

		Always uses the fixed TEST_COMPANY name rather than the site's default
		or first company, so test behaviour doesn't depend on which site the
		suite runs against.
		"""
		if frappe.db.exists("Company", TEST_COMPANY):
			return frappe.get_doc("Company", TEST_COMPANY)
		return cls._insert(
			{
				"doctype": "Company",
				"company_name": TEST_COMPANY,
				"abbr": "_GSC",
				"default_currency": "INR",
				"country": "India",
				"gst_category": "Unregistered",
				"valuation_method": "FIFO",
			}
		)

	# ---------- employee ----------

	@classmethod
	def ensure_reports_manager(cls) -> str:
		"""Return the shared manager Employee that test employees report to.

		Created before any other employee of the test company, so it is the
		exempt "first employee" under the reports_to rule (mandatory once the
		company has other employees).
		"""
		name = frappe.db.get_value(
			"Employee", {"attendance_device_id": REPORTS_MANAGER_DEVICE_ID}, "name"
		)
		if name:
			return name
		return cls.create_employee("Test GKE Reports Manager", REPORTS_MANAGER_DEVICE_ID).name

	@classmethod
	def create_employee(cls, employee_name: str, attendance_device_id: str):
		"""Create an Employee with complete mandatory data, reporting to the
		shared test manager."""
		meta = frappe.get_meta("Employee")
		first_name, _, rest = employee_name.partition(" ")

		values = {
			"doctype": "Employee",
			"naming_series": "HR-EMP-",
			"first_name": first_name,
			"middle_name": "GKE",
			"last_name": rest,
			"salutation": cls.salutation,
			"gender": cls.gender,
			"date_of_birth": "2001-09-01",
			"date_of_joining": "2021-01-01",
			"status": "Active",
			"company": cls.company,
			"department": cls.department,
			"designation": "Accountant",
			"employment_type": cls.employment_type,
			"default_shift": cls.shift,
			"holiday_list": cls.holiday_list,
			"salary_currency": cls.existing_master("Currency", "INR"),
			"health_insurance_provider": cls.insurance_provider,
			"marital_status": "Single",
			"attendance_device_id": attendance_device_id,
			"create_user_permission": 1,
			"create_user_automatically": 0,
			"expense_approver": cls.approver,
			"leave_approver": cls.approver,
			"shift_request_approver": cls.approver,
			"reports_to": cls.reports_manager,
			# custom fields (dropped below if they don't exist on this site)
			"old_employee_code": "TEST-001",
			"old_punch_id": "90001",
			"custom_notice_dayes": "30",
			"custom_health_insurance_status": "Pending",
			"custom_sum_assured_": "1 Lakh",
			"custom_accident_insurance_provider": cls.insurance_provider,
			"custom_accident_insurance_status": "Pending",
			"custom_sum_assured_accident_insurance_": "10 Lakh",
			"aadhar_number": "123456789012",
			"name_as_per_aadhar": employee_name,
			"allowed_personal_hours": "3:00:00",
			"product_incentive_applicable": 1,
			"cell_number": "9000000000",
			"current_address": "Test Address, Test City",
			"permanent_address": "Test Address, Test City",
			"is_pf_applicable": 0,
			"custom_is_esic_applicable": 0,
			"is_physical_handicap": 0,
			"handicap_percenatge": 0,
			"variable_in": 0,
			"notice_number_of_days": 0,
			"ctc": 0,
		}

		# masters ensured only for fields on this site, and None placeholders
		# for the same reason
		values = {
			k: v
			for k, v in values.items()
			if (k == "doctype" or v is not None) and (k == "doctype" or meta.has_field(k))
		}
		return cls._insert(values)
