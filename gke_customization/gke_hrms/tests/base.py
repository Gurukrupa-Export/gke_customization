"""Base test case for gke_customization HRMS tests."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate

from gke_customization.gke_hrms.tests.utils import TEST_COMPANY, load_server_scripts


class GKHRMSTestCase(IntegrationTestCase):
	"""Base test case for gke_customization HRMS tests.

	Handles master data creation (company, link masters, employee) and server
	script setup so concrete test classes only deal with the behaviour under
	test. Records are rolled back when the class finishes its run.
	"""

	DEFAULT_APPROVER = "test_default_approver@hr.com"
	SERVER_SCRIPT_DOCTYPES = None  # None = load every folder; e.g. ["employee_checkin"]

	# ---------- generic helpers ----------

	@staticmethod
	def _insert(doc: dict):
		return frappe.get_doc(doc).insert(ignore_permissions=True, ignore_mandatory=True)

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

	def existing_master(self, doctype: str, name: str) -> str | None:
		"""Return name if a core-provided master exists, else None (the link
		value is then dropped; the site's core setup is expected to have it)."""
		return name if frappe.db.exists(doctype, name) else None

	def ensure_user(self, email: str) -> str:
		if frappe.db.exists("User", email):
			return email
		return self._insert(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"send_welcome_email": 0,
				"enabled": 1,
			}
		).name

	def ensure_department(self, dept_name: str, company: str) -> str:
		existing = frappe.db.get_value(
			"Department", {"department_name": dept_name, "company": company}, "name"
		)
		if existing:
			return existing
		if not frappe.db.exists("Department", "All Departments"):
			self._insert({"doctype": "Department", "department_name": "All Departments"})
		return self._insert(
			{
				"doctype": "Department",
				"department_name": dept_name,
				"company": company,
				"parent_department": "All Departments",
			}
		).name

	def ensure_shift(self, shift_name: str, start="09:00:00", end="18:00:00") -> str:
		if frappe.db.exists("Shift Type", shift_name):
			return shift_name
		return self._insert(
			{
				"doctype": "Shift Type",
				"__newname": shift_name,
				"start_time": start,
				"end_time": end,
			}
		).name

	def ensure_holiday_list(self):
		"""Reuse an existing Holiday List, or create a test one with Sunday offs."""
		existing = frappe.get_all("Holiday List", pluck="name", limit=1)
		if existing:
			return existing[0]
		today = getdate()
		return self._insert(
			{
				"doctype": "Holiday List",
				"holiday_list_name": "_Test GKE Holiday List",
				"from_date": today.replace(month=1, day=1),
				"to_date": today.replace(month=12, day=31),
				"weekly_off": "Sunday",
			}
		).name

	# ---------- company ----------

	def create_company(self):
		"""Reuse the site default company, or create a stub company for tests."""
		name = frappe.db.get_single_value("Global Defaults", "default_company") or (
			frappe.get_all("Company", pluck="name", limit=1) or [None]
		)[0]
		if name and frappe.db.exists("Company", name):
			return frappe.get_doc("Company", name)

		return self._insert(
			{
				"doctype": "Company",
				"company_name": TEST_COMPANY,
				"default_currency": "INR",
				"country": "India",
			}
		)

	# ---------- employee ----------

	def create_employee(self, employee_name: str, attendance_device_id: str, **overrides):
		"""Create an Employee covering the fields this stack marks mandatory,
		modelled on a production employee record but with test-only data.

		Any Employee field can be passed via overrides, e.g. reports_to=...,
		department="Central", approver_email="x@y.com".
		"""
		meta = frappe.get_meta("Employee")
		company = overrides.pop("company", None) or self.create_company().name

		# core-provided masters: reuse if present, drop the link value otherwise
		gender = self.existing_master("Gender", overrides.pop("gender", "Male"))
		salutation = self.existing_master("Salutation", overrides.pop("salutation", "Mr"))
		employment_type = self.existing_master(
			"Employment Type", overrides.pop("employment_type", "Full-time")
		)
		salary_currency = self.existing_master(
			"Currency", overrides.pop("salary_currency", "INR")
		)
		department = self.ensure_department(overrides.pop("department", "Central"), company)
		approver = self.ensure_user(overrides.pop("approver_email", self.DEFAULT_APPROVER))
		holiday_list = self.ensure_holiday_list()
		default_shift = (
			self.ensure_shift(overrides.pop("default_shift", "test shift 9-18"))
			if meta.has_field("default_shift")
			else None
		)

		# required on this stack and not provided by core setup: create if missing
		designation = overrides.pop("designation", "Accountant")
		if not frappe.db.exists("Designation", designation):
			self._insert({"doctype": "Designation", "designation_name": designation})

		insurance = None
		if meta.has_field("health_insurance_provider"):
			insurance = overrides.pop("health_insurance_provider", "Care Health Insurance")
			if not frappe.db.exists("Employee Health Insurance", insurance):
				self._insert(
					{"doctype": "Employee Health Insurance", "health_insurance_name": insurance}
				)
		else:
			overrides.pop("health_insurance_provider", None)

		first_name, _, rest = employee_name.partition(" ")

		values = {
			"doctype": "Employee",
			"naming_series": "HR-EMP-",
			"first_name": first_name,
			"middle_name": "GKE",
			"last_name": rest,
			"salutation": salutation,
			"gender": gender,
			"date_of_birth": "2001-09-01",
			"date_of_joining": "2021-01-01",
			"status": "Active",
			"company": company,
			"department": department,
			"designation": designation,
			"employment_type": employment_type,
			"default_shift": default_shift,
			"holiday_list": holiday_list,
			"salary_currency": salary_currency,
			"health_insurance_provider": insurance,
			"marital_status": "Single",
			"attendance_device_id": attendance_device_id,
			"create_user_permission": 1,
			"create_user_automatically": 0,
			"expense_approver": approver,
			"leave_approver": approver,
			"shift_request_approver": approver,
			# custom fields (dropped below if they don't exist on this site)
			"old_employee_code": "TEST-001",
			"old_punch_id": "90001",
			"custom_notice_dayes": "30",
			"custom_health_insurance_status": "Pending",
			"custom_sum_assured_": "1 Lakh",
			"custom_accident_insurance_provider": insurance,
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
		values.update(overrides)

		# reports_to links to another Employee: keep only if it exists
		reports_to = values.get("reports_to")
		if reports_to and not frappe.db.exists("Employee", reports_to):
			values.pop("reports_to")

		# masters ensured only for fields on this site, and None placeholders
		# for the same reason
		values = {
			k: v
			for k, v in values.items()
			if (k == "doctype" or v is not None) and (k == "doctype" or meta.has_field(k))
		}

		return self._insert(values)