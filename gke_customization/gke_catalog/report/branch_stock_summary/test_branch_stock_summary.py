"""Branch Stock Summary: who may run its whitelisted methods, and that every statement
binds its values (review finding F-01)."""

import json
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from gke_customization.gke_catalog.report.branch_stock_summary import (
	branch_stock_summary as bss,
)

MOD = "gke_customization.gke_catalog.report.branch_stock_summary.branch_stock_summary"
STOCK_BALANCE = "erpnext.stock.report.stock_balance.stock_balance.execute"
STOCK_KEYS = (
	"work_order_stock",
	"employee_wip_stock",
	"supplier_wip_stock",
	"employee_msl_stock",
	"supplier_msl_stock",
	"raw_material_stock",
	"reserve_stock",
	"transit_stock",
	"scrap_stock",
	"manufacturing_wh_stock",
	"finished_goods",
)
COMPANY_FILTER = [{"fieldname": "company", "fieldtype": "Link", "options": "Company"}]
# Tables the report's own statements read; anything else is Frappe's metadata or cache.
REPORT_TABLES = (
	"`tabManufacturing Operation`",
	"`tabStock Ledger Entry`",
	"`tabMain Slip`",
	"`tabSerial No`",
	"`tabWarehouse`",
)


class RecordingSQL:
	"""Stands in for frappe.db.sql for the report's own statements and records them. Each is
	formatted the way mysqlclient does (query % values), so a stray % or a missing placeholder
	fails here too. Frappe's own queries (metadata, translations) go to the real database."""

	def __init__(self):
		self.real_sql = frappe.db.sql
		self.calls = []

	def __call__(self, query, *args, **kwargs):
		if not any(table in str(query) for table in REPORT_TABLES):
			return self.real_sql(query, *args, **kwargs)
		values = args[0] if args else kwargs.get("values")
		self.calls.append((query, values))
		if values is not None:
			query % {key: "''" for key in values}
		if "db_department" in query:
			return [frappe._dict(department="Dept'1", db_department="Dept'1 - GEPL")]
		if "w.name as warehouse" in query:
			return [frappe._dict(warehouse="WH'1", department="Dept'1 - GEPL")]
		return []

	def values(self):
		"""Every bound value, with IN tuples flattened."""
		flat = []
		for _query, values in self.calls:
			for value in (values or {}).values():
				flat.extend(value if isinstance(value, tuple) else [value])
		return flat


class _Case(UnitTestCase):
	def setUp(self):
		self.sql = RecordingSQL()
		self._patch_object(frappe.db, "sql", new=self.sql)
		self.stock_balance = self._patch(STOCK_BALANCE, return_value=([], []))
		self.log_error = self._patch_object(frappe, "log_error")

	def _patch(self, target, **kwargs):
		patcher = patch(target, **kwargs)
		self.addCleanup(patcher.stop)
		return patcher.start()

	def _patch_object(self, target, attribute, **kwargs):
		patcher = patch.object(target, attribute, **kwargs)
		self.addCleanup(patcher.stop)
		return patcher.start()

	@staticmethod
	def filters(**overrides):
		base = {
			"company": "CO'1",
			"raw_material_type": "Metal",
			"include_work_order_wip": 1,
			"include_finished_goods_metal": 1,
		}
		base.update(overrides)
		return base


class TestAccessGate(_Case):
	def test_summary_denied_before_any_query(self):
		self._patch(f"{MOD}.get_report_doc", side_effect=frappe.PermissionError)
		with self.assertRaises(frappe.PermissionError):
			bss.get_summary_comparison(json.dumps(self.filters()))
		self.assertEqual(self.sql.calls, [])
		self.stock_balance.assert_not_called()

	def test_stock_details_denied_before_any_query(self):
		self._patch(f"{MOD}.get_report_doc", side_effect=frappe.PermissionError)
		for key in STOCK_KEYS:
			with self.subTest(key), self.assertRaises(frappe.PermissionError):
				bss.get_stock_details("DP'1", "label", key, json.dumps(self.filters()))
		self.assertEqual(self.sql.calls, [])

	def test_company_checked_with_desk_rule(self):
		self._patch(f"{MOD}.get_report_doc")
		check = self._patch(f"{MOD}.validate_filters_permissions")
		bss.get_summary_comparison(json.dumps(self.filters()))
		bss.get_stock_details("DP'1", "label", "raw_material_stock", json.dumps(self.filters()))
		bss.execute(self.filters())
		self.assertEqual(check.call_count, 3)
		for call in check.call_args_list:
			report, filters, user, js_filters = call.args
			self.assertEqual((report, filters["company"], user), ("Branch Stock Summary", "CO'1", frappe.session.user))
			self.assertEqual(js_filters, COMPANY_FILTER)

	def test_company_denied_before_any_query(self):
		self._patch(f"{MOD}.get_report_doc")
		self._patch(f"{MOD}.validate_filters_permissions", side_effect=frappe.ValidationError)
		calls = (
			lambda: bss.get_summary_comparison(json.dumps(self.filters())),
			lambda: bss.get_stock_details("DP'1", "label", "raw_material_stock", json.dumps(self.filters())),
			lambda: bss.execute(self.filters()),
		)
		for call in calls:
			with self.assertRaises(frappe.ValidationError):
				call()
		self.assertEqual(self.sql.calls, [])

	def test_summary_requires_stock_balance_access(self):
		def deny_stock_balance(report_name):
			if report_name == "Stock Balance":
				raise frappe.PermissionError

		self._patch(f"{MOD}.get_report_doc", side_effect=deny_stock_balance)
		self._patch(f"{MOD}.validate_filters_permissions")
		with self.assertRaises(frappe.PermissionError):
			bss.get_summary_comparison(json.dumps(self.filters()))
		self.assertEqual(self.sql.calls, [])
		self.stock_balance.assert_not_called()
		# The View dialogs do not run Stock Balance and stay available.
		bss.get_stock_details("DP'1", "label", "raw_material_stock", json.dumps(self.filters()))
		self.assertEqual(len(self.sql.calls), 1)

	def test_stock_details_requires_company(self):
		self._patch(f"{MOD}.get_report_doc")
		self._patch(f"{MOD}.validate_filters_permissions")
		with self.assertRaisesRegex(frappe.ValidationError, "Company is required"):
			bss.get_stock_details("DP'1", "label", "raw_material_stock", json.dumps({"raw_material_type": "Metal"}))
		self.assertEqual(self.sql.calls, [])


class TestBoundQueries(_Case):
	"""Request values travel only as bound values, never as SQL text."""

	def setUp(self):
		super().setUp()
		self._patch(f"{MOD}.get_report_doc")
		self._patch(f"{MOD}.validate_filters_permissions")

	def assertNothingSpliced(self, markers, minimum):
		self.assertGreaterEqual(len(self.sql.calls), minimum)
		for query, values in self.sql.calls:
			self.assertIsInstance(values, dict, query)
			for marker in markers:
				self.assertNotIn(marker, query)
		bound = self.sql.values()
		for marker in markers:
			self.assertIn(marker, bound)
		self.log_error.assert_not_called()

	def test_summary_binds_every_value(self):
		bss.get_summary_comparison(
			json.dumps(self.filters(company="CO'1", manufacturer="MF'1", department="DP'1"))
		)
		self.assertNothingSpliced(["CO'1", "MF'1", "DP'1"], minimum=14)
		queries = " ".join(query for query, _values in self.sql.calls)
		for placeholder in ("%(departments)s", "%(dept_0)s", "%(warehouses)s", "%(warehouse_pattern)s"):
			self.assertIn(placeholder, queries)

	def test_branch_and_manufacturer_departments_are_bound(self):
		gepl = "Gurukrupa Export Private Limited"
		bss.get_summary_comparison(json.dumps(self.filters(company=gepl, branch="BR'1", manufacturer="Labh")))
		self.assertNothingSpliced(["BR'1"], minimum=14)
		queries = " ".join(query for query, _values in self.sql.calls)
		self.assertIn("%(allowed_departments)s", queries)
		self.assertIn("Casting - GEPL", self.sql.values())

	def test_stock_details_binds_every_value(self):
		filters = json.dumps(self.filters(manufacturer="MF'1"))
		for key in STOCK_KEYS:
			bss.get_stock_details("DP'1", "label", key, filters)
		self.assertNothingSpliced(["CO'1", "MF'1", "DP'1"], minimum=len(STOCK_KEYS))
		main_slip = [values for query, values in self.sql.calls if "`tabMain Slip` ms" in query]
		self.assertEqual([values["company"] for values in main_slip], ["CO'1", "CO'1"])

	def test_like_wildcards_are_literal(self):
		bss.get_finished_goods_details("100%_X - GEPL", "CO'1", "", "", ["Metal"])
		bss.get_finished_goods_details("Waxing - GEPL", "CO'1", "", "", ["Metal"])
		patterns = [values["warehouse_pattern"] for _query, values in self.sql.calls]
		self.assertEqual(patterns, ["%100\\%\\_X%", "%Waxing%"])

	def test_no_tracked_department_keeps_not_in_blank(self):
		self._patch(f"{MOD}.get_departments_list", return_value=[])
		bss.get_summary_comparison(json.dumps(self.filters()))
		scope_gap = [values for query, values in self.sql.calls if "NOT IN %(departments)s" in query]
		self.assertEqual([values["departments"] for values in scope_gap], [("",)])


class _Reached(Exception):
	pass


class TestAccessOnSite(IntegrationTestCase):
	"""The gate against the site's real roles, report permissions and User Permissions."""

	def setUp(self):
		super().setUp()
		self.addCleanup(frappe.db.rollback)

	def make_user(self, *roles):
		email = f"bss-{frappe.generate_hash(length=8)}@example.invalid"
		user = frappe.get_doc({"doctype": "User", "email": email, "first_name": "BSS Test", "send_welcome_email": 0})
		user.insert(ignore_permissions=True)
		user.add_roles(*roles)
		return email

	def companies(self):
		companies = frappe.get_all("Company", pluck="name", order_by="name", limit=2)
		if len(companies) < 2:
			self.skipTest("needs two companies")
		return companies

	def test_user_without_report_role_is_denied(self):
		email = self.make_user("Employee")
		filters = json.dumps({"company": self.companies()[0], "raw_material_type": "Metal"})
		with patch.object(bss, "get_departments_list") as departments, self.set_user(email):
			with self.assertRaises(frappe.PermissionError):
				bss.get_summary_comparison(filters)
			with self.assertRaises(frappe.PermissionError):
				bss.get_stock_details("Casting - GEPL", "Raw Material Stock", "raw_material_stock", filters)
		departments.assert_not_called()

	def test_user_cannot_cross_company(self):
		allowed, other = self.companies()
		email = self.make_user("System Manager", "Stock User")
		frappe.get_doc(
			{"doctype": "User Permission", "user": email, "allow": "Company", "for_value": allowed, "apply_to_all_doctypes": 1}
		).insert(ignore_permissions=True)
		filters = {"company": other, "raw_material_type": "Metal"}
		with patch.object(bss, "get_departments_list") as departments, self.set_user(email):
			with self.assertRaisesRegex(frappe.ValidationError, "permission to access Company"):
				bss.get_summary_comparison(json.dumps(filters))
			with self.assertRaisesRegex(frappe.ValidationError, "permission to access Company"):
				bss.get_stock_details("Casting - GEPL", "Raw Material Stock", "raw_material_stock", json.dumps(filters))
			# Desk's report runner without js_filters: execute() checks the Company itself.
			with self.assertRaisesRegex(frappe.ValidationError, "permission to access Company"):
				frappe.desk.query_report.run("Branch Stock Summary", filters=filters, ignore_prepared_report=True)
		departments.assert_not_called()

	def test_permitted_user_reaches_the_queries(self):
		allowed, _other = self.companies()
		email = self.make_user("System Manager", "Stock User")
		frappe.get_doc(
			{"doctype": "User Permission", "user": email, "allow": "Company", "for_value": allowed, "apply_to_all_doctypes": 1}
		).insert(ignore_permissions=True)
		filters = json.dumps({"company": allowed, "raw_material_type": "Metal"})
		with self.set_user(email):
			with patch.object(bss, "get_branch_stock_summary_optimized", side_effect=_Reached), self.assertRaises(
				_Reached
			):
				bss.get_summary_comparison(filters)
			with patch.object(bss, "get_raw_material_details", side_effect=_Reached), self.assertRaises(_Reached):
				bss.get_stock_details("Casting - GEPL", "Raw Material Stock", "raw_material_stock", filters)


class TestQueriesOnMariaDB(IntegrationTestCase):
	"""The bound statements against the real database, as Administrator."""

	def setUp(self):
		super().setUp()
		mwo = frappe.db.get_value(
			"Manufacturing Work Order", {"docstatus": 1, "branch": ("is", "set")}, ["company", "branch"], as_dict=True
		)
		if not mwo:
			self.skipTest("needs a submitted Manufacturing Work Order with a branch")
		# Gurukrupa Export Private Limited requires a branch filter.
		self.company, self.branch = mwo.company, mwo.branch
		self.log_error = patch.object(frappe, "log_error").start()
		self.addCleanup(patch.stopall)

	def test_quotes_stay_data(self):
		# The old text matched every company's departments.
		self.assertEqual(bss.get_departments_list({"company": "X' OR '1'='1"}), [])
		filters = json.dumps(
			{
				"company": self.company,
				"raw_material_type": "Metal",
				"include_work_order_wip": 1,
				"include_finished_goods_metal": 1,
			}
		)
		for key in STOCK_KEYS:
			with self.subTest(key):
				self.assertEqual(list(bss.get_stock_details("Casting' OR '1'='1", "label", key, filters)), [])
		self.log_error.assert_not_called()

	def test_every_statement_runs(self):
		"""Each statement once against MariaDB: a % left undoubled or an empty IN () would
		fail there, and the module would swallow it into Error Log. Other raw material types
		run the same statements with other values."""
		filters = {
			"company": self.company,
			"branch": self.branch,
			"raw_material_type": "Metal",
			"as_on_date": "2000-01-01",
			"include_work_order_wip": 1,
			"include_finished_goods_metal": 1,
		}
		bss.execute(dict(filters))
		departments = bss.get_departments_list(filters)
		if departments:
			for key in STOCK_KEYS:
				bss.get_stock_details(departments[0]["department"], "label", key, json.dumps(filters))
		with patch(STOCK_BALANCE, return_value=([], [])):
			bss.get_summary_comparison(json.dumps(filters))
		self.log_error.assert_not_called()
