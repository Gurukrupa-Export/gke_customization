"""Branch Stock Summary: who may run its whitelisted methods, that every statement binds
its values (review finding F-01), and that Transit, Reserve and Scrap balances are netted
per department and item (review finding F-06)."""

import json
import re
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from frappe.utils import flt

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
	@staticmethod
	def deny_report(report_name):
		"""Only this report's own gate refuses, so the test fails if that gate is dropped."""
		if report_name == "Branch Stock Summary":
			raise frappe.PermissionError

	def test_summary_denied_before_any_query(self):
		gate = self._patch(f"{MOD}.get_report_doc", side_effect=self.deny_report)
		self._patch(f"{MOD}.validate_filters_permissions")
		with self.assertRaises(frappe.PermissionError):
			bss.get_summary_comparison(json.dumps(self.filters()))
		self.assertEqual(gate.call_args_list[0].args, ("Branch Stock Summary",))
		self.assertEqual(self.sql.calls, [])
		self.stock_balance.assert_not_called()

	def test_stock_details_denied_before_any_query(self):
		gate = self._patch(f"{MOD}.get_report_doc", side_effect=self.deny_report)
		self._patch(f"{MOD}.validate_filters_permissions")
		for key in STOCK_KEYS:
			with self.subTest(key), self.assertRaises(frappe.PermissionError):
				bss.get_stock_details("DP'1", "label", key, json.dumps(self.filters()))
		self.assertEqual({call.args for call in gate.call_args_list}, {("Branch Stock Summary",)})
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

	def assertMainSlipScoped(self, expected_statements, company="CO'1"):
		"""Main Slip figures follow the selected company: the condition must be in the SQL,
		not only its value in the bound parameters."""
		main_slip = [(query, values) for query, values in self.sql.calls if "`tabMain Slip` ms" in query]
		self.assertEqual(len(main_slip), expected_statements)
		for query, values in main_slip:
			self.assertIn("ms.company = %(company)s", query)
			self.assertEqual(values["company"], company)

	def test_summary_binds_every_value(self):
		bss.get_summary_comparison(
			json.dumps(self.filters(company="CO'1", manufacturer="MF'1", department="DP'1"))
		)
		self.assertNothingSpliced(["CO'1", "MF'1", "DP'1"], minimum=14)
		queries = " ".join(query for query, _values in self.sql.calls)
		for placeholder in ("%(departments)s", "%(dept_0)s", "%(warehouses)s", "%(warehouse_pattern)s"):
			self.assertIn(placeholder, queries)
		self.assertMainSlipScoped(2)  # Employee and Supplier MSL

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
		self.assertMainSlipScoped(2)  # Employee and Supplier MSL drill-downs

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
		self.assertTrue(set(roles) <= set(frappe.get_roles(email)), "a role was stripped on save")
		return email

	def companies(self):
		"""(allowed, other). `other` is never Gurukrupa Export Private Limited, whose report
		also requires a branch filter before it checks the Company."""
		names = frappe.get_all("Company", pluck="name", order_by="name")
		others = [name for name in names if name != "Gurukrupa Export Private Limited"]
		if len(names) < 2 or not others:
			self.skipTest("needs two companies")
		other = others[0]
		allowed = next(name for name in names if name != other)
		return allowed, other

	def test_user_without_report_role_is_denied(self):
		email = self.make_user("Purchase User")  # a desk role outside the report's roles
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
				department = "Casting' OR 'a'='a' OR 'b'='b"  # still a tautology after the suffix
				self.assertEqual(list(bss.get_stock_details(department, "label", key, filters)), [])
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
		departments = bss.get_departments_list(filters)
		if not departments:
			self.skipTest("the chosen company and branch track no department")
		real_sql, statements = frappe.db.sql, []

		def recording_sql(query, *args, **kwargs):
			statements.append(str(query))
			return real_sql(query, *args, **kwargs)

		with patch.object(frappe.db, "sql", new=recording_sql):
			bss.execute(dict(filters))
			for key in STOCK_KEYS:
				bss.get_stock_details(departments[0]["department"], "label", key, json.dumps(filters))
			with patch(STOCK_BALANCE, return_value=([], [])):
				bss.get_summary_comparison(json.dumps(filters))
		self.log_error.assert_not_called()
		ran = " ".join(statements)
		for marker in (
			"db_department",  # department list
			"mop.status = 'Not Started'",  # Work Order
			"mop.for_subcontracting = 0",  # Employee WIP
			"`tabMain Slip` ms",  # MSL
			"SELECT DISTINCT w.name as warehouse",  # warehouse maps
			"w.warehouse_type = 'Raw Material'",
			"w.warehouse_type = 'Manufacturing'",
			"`tabSerial No` sn",  # Finished Goods
			"as 'Item Code'",  # SLE drill-downs
			"NOT IN %(departments)s",  # scope gap
		):
			self.assertIn(marker, ran)


COMPANY = "_Test BSS Company"
CASTING = "_Test BSS Casting - GEPL"
WAXING = "_Test BSS Waxing - GEPL"
ITEM_75 = "_Test-BSS-M-75.0"  # extract_purity_from_item_code -> 75.0
ITEM_916 = "_Test-BSS-M-91.6"  # -> 91.6
ITEM_NO_PURITY = "_Test-BSS-M"
METAL_GROUPS = ["Metal - V", "Metal DNU"]
AS_ON = "2026-10-05"


def _fail_on_swallowed_error(title=None, message=None, *args, **kwargs):
	"""get_bulk_stock_data logs and swallows exceptions; surface them instead."""
	raise AssertionError(f"{title}: {message}")


class FakeStockDB:
	"""Answers get_bulk_stock_data's warehouse-resolution and per-warehouse SLE queries.

	The SLE query's HAVING clause is applied the way the database would, so the tests see
	exactly the rows the real query hands to the netting step. The report's other queries
	return no rows; Frappe's own queries go to the real database.
	"""

	def __init__(self, warehouses, balances):
		self.real_sql = frappe.db.sql
		self.warehouses = warehouses  # {"Reserve": [(warehouse, department), ...]}
		self.balances = balances  # {(warehouse, item_code): signed balance}

	def __call__(self, query, *args, **kwargs):
		if not any(table in str(query) for table in REPORT_TABLES):
			return self.real_sql(query, *args, **kwargs)
		values = args[0] if args else kwargs.get("values")
		if "SELECT DISTINCT w.name as warehouse" in query:
			stock_type = next(t for t in ("Transit", "Reserve", "Scrap") if f" {t} - GEPL" in query)
			return [frappe._dict(warehouse=w, department=d) for w, d in self.warehouses.get(stock_type, [])]
		if "GROUP BY sle.warehouse, sle.item_code" in query:
			operator = re.search(r"HAVING SUM\(sle\.actual_qty\) (>|!=) 0", query).group(1)
			return [
				frappe._dict(warehouse=warehouse, item_code=item_code, weight=qty)
				for (warehouse, item_code), qty in self.balances.items()
				if warehouse in values["warehouses"] and (qty > 0 if operator == ">" else qty != 0)
			]
		return []


class TestWarehouseStockNetting(UnitTestCase):
	"""Netting rule, with frappe.db.sql answered by FakeStockDB (no site data)."""

	def setUp(self):
		patcher = patch.object(frappe, "log_error", side_effect=_fail_on_swallowed_error)
		patcher.start()
		self.addCleanup(patcher.stop)

	def _bulk(self, warehouses, balances, departments=(CASTING, WAXING)):
		with patch.object(frappe.db, "sql", new=FakeStockDB(warehouses, balances)):
			return bss.get_bulk_stock_data(
				COMPANY,
				METAL_GROUPS,
				["M"],
				AS_ON,
				"",
				["Metal"],
				list(departments),
				include_finished_goods_metal=False,
				include_work_order_wip=False,
			)

	def assertStock(self, entry, quantity, pure_gold):
		self.assertAlmostEqual(entry["quantity"], quantity, places=9)
		self.assertAlmostEqual(entry["pure_gold_weight"], pure_gold, places=9)

	def test_negative_balance_in_one_warehouse_offsets_another(self):
		bulk = self._bulk(
			{"Reserve": [("RA", CASTING), ("RB", CASTING)]}, {("RA", ITEM_75): 10.0, ("RB", ITEM_75): -3.0}
		)
		self.assertStock(bulk["reserve"][CASTING], 7.0, 5.25)

	def test_department_item_net_negative_is_hidden(self):
		bulk = self._bulk(
			{"Reserve": [("RA", CASTING), ("RB", CASTING)]}, {("RA", ITEM_75): 3.0, ("RB", ITEM_75): -10.0}
		)
		self.assertNotIn(CASTING, bulk["reserve"])

	def test_zero_net_is_dropped_despite_float_noise(self):
		# 0.1 + 0.2 - 0.3 is 5.55e-17 in float arithmetic but exactly 0 in decimal(21,9)
		bulk = self._bulk(
			{"Reserve": [("RA", CASTING), ("RB", CASTING), ("RC", CASTING)]},
			{("RA", ITEM_75): 0.1, ("RB", ITEM_75): 0.2, ("RC", ITEM_75): -0.3},
		)
		self.assertNotIn(CASTING, bulk["reserve"])

	def test_purity_is_applied_per_item_on_the_net(self):
		bulk = self._bulk(
			{"Reserve": [("RA", CASTING), ("RB", CASTING)]},
			{
				("RA", ITEM_75): 10.0,
				("RB", ITEM_75): -3.0,  # 7 at 75% -> 5.25
				("RA", ITEM_916): 5.0,
				("RB", ITEM_916): -1.0,  # 4 at 91.6% -> 3.664
				("RB", ITEM_NO_PURITY): -2.0,  # negative-only item: hidden, offsets nothing else
			},
		)
		self.assertStock(bulk["reserve"][CASTING], 11.0, 8.914)

	def test_all_positive_balances_are_unchanged(self):
		bulk = self._bulk(
			{"Reserve": [("RA", CASTING), ("RB", CASTING)]},
			{("RA", ITEM_75): 10.0, ("RB", ITEM_75): 4.0, ("RB", ITEM_916): 2.0},
		)
		self.assertStock(bulk["reserve"][CASTING], 16.0, 12.332)

	def test_departments_do_not_offset_each_other(self):
		bulk = self._bulk(
			{"Reserve": [("RA", CASTING), ("RW", WAXING)]}, {("RA", ITEM_75): 10.0, ("RW", ITEM_75): -5.0}
		)
		self.assertStock(bulk["reserve"][CASTING], 10.0, 7.5)
		self.assertNotIn(WAXING, bulk["reserve"])

	def test_transit_and_scrap_net_the_same_way(self):
		bulk = self._bulk(
			{"Transit": [("TA", CASTING), ("TB", CASTING)], "Scrap": [("SA", CASTING), ("SB", CASTING)]},
			{("TA", ITEM_75): 10.0, ("TB", ITEM_75): -3.0, ("SA", ITEM_75): 10.0, ("SB", ITEM_75): -3.0},
		)
		self.assertStock(bulk["transit"][CASTING], 7.0, 5.25)
		self.assertStock(bulk["scrap"][CASTING], 7.0, 5.25)

	def test_warehouse_matching_two_departments_counts_in_each(self):
		bulk = self._bulk({"Reserve": [("RX", CASTING), ("RX", WAXING)]}, {("RX", ITEM_75): 6.0})
		self.assertStock(bulk["reserve"][CASTING], 6.0, 4.5)  # GK live counted it in both
		self.assertStock(bulk["reserve"][WAXING], 6.0, 4.5)

	def test_report_rows_and_totals_use_the_net(self):
		fake = FakeStockDB(
			{"Reserve": [("RA", CASTING), ("RB", CASTING)]}, {("RA", ITEM_75): 10.0, ("RB", ITEM_75): -3.0}
		)
		departments = [{"department": "_Test BSS Casting", "db_department": CASTING}]
		with (
			patch.object(frappe.db, "sql", new=fake),
			patch.object(bss, "get_departments_list", return_value=departments),
			patch(f"{MOD}.validate_filters_permissions"),
		):
			_columns, data = bss.execute({"company": COMPANY, "raw_material_type": "Metal", "as_on_date": AS_ON})
		totals = {
			row["section"]: (row["quantity"], row["pure_gold_weight"])
			for row in data
			if row.get("is_stock_type") or row.get("is_department_total") or row.get("is_grand_total")
		}
		self.assertEqual(
			totals,
			{"Reserve Stock": (7.0, 5.25), "_Test BSS Casting Total": (7.0, 5.25), "Grand Total": (7.0, 5.25)},
		)


class TestWarehouseNettingInDatabase(IntegrationTestCase):
	"""The same rule through the real SQL, checked against the View drill-downs.

	Inserts its own Item / Warehouse / Stock Ledger Entry rows with db_insert (no
	validations, no site data needed) and rolls them back after each test.
	"""

	DEPT = "_Test BSS DB Casting - GEPL"
	DEPT_CLEAN = "_Test BSS DB Casting"

	def setUp(self):
		super().setUp()
		self.addCleanup(frappe.db.rollback)
		patcher = patch.object(frappe, "log_error", side_effect=_fail_on_swallowed_error)
		patcher.start()
		self.addCleanup(patcher.stop)
		for item_code in (ITEM_75, ITEM_916):
			frappe.get_doc(
				{
					"doctype": "Item",
					"name": item_code,
					"item_code": item_code,
					"item_name": item_code,
					"item_group": "Metal - V",
					"stock_uom": "Nos",
				}
			).db_insert()

	def _warehouse(self, warehouse_name, **fields):
		name = f"{warehouse_name} - _TBSS"
		frappe.get_doc(
			{"doctype": "Warehouse", "name": name, "warehouse_name": warehouse_name, "company": COMPANY, **fields}
		).db_insert()
		return name

	def _sle(self, warehouse, item_code, qty):
		frappe.get_doc(
			{
				"doctype": "Stock Ledger Entry",
				"name": frappe.generate_hash(length=12),
				"company": COMPANY,
				"warehouse": warehouse,
				"item_code": item_code,
				"posting_date": "2026-01-01",
				"actual_qty": qty,
				"docstatus": 1,
				"is_cancelled": 0,
			}
		).db_insert()

	def test_summary_nets_like_the_drill_down(self):
		cases = (
			("Reserve", "reserve", bss.get_reserve_stock_details),
			("Scrap", "scrap", bss.get_scrap_stock_details),
			("Transit", "transit", bss.get_transit_stock_details),
		)
		for stock_type, _key, _details in cases:
			if stock_type == "Transit":
				# Transit matches by name only: two names matching different suffixes
				first = self._warehouse(f"{self.DEPT_CLEAN} Transit - GEPL")
			else:
				# matched through the department column, not the name
				first = self._warehouse(
					f"{self.DEPT_CLEAN} {stock_type} A", warehouse_type=stock_type, department=self.DEPT
				)
			second = self._warehouse(f"{self.DEPT_CLEAN} {stock_type}")  # matched by name
			self._sle(first, ITEM_75, 10)
			self._sle(second, ITEM_75, -3)  # nets to 7
			self._sle(first, ITEM_916, 3)
			self._sle(second, ITEM_916, -10)  # nets negative: hidden

		bulk = bss.get_bulk_stock_data(
			COMPANY,
			METAL_GROUPS,
			["M"],
			AS_ON,
			"",
			["Metal"],
			[self.DEPT],
			include_finished_goods_metal=False,
			include_work_order_wip=False,
		)
		for stock_type, key, get_details in cases:
			with self.subTest(stock_type):
				self.assertAlmostEqual(bulk[key][self.DEPT]["quantity"], 7.0, places=9)
				self.assertAlmostEqual(bulk[key][self.DEPT]["pure_gold_weight"], 5.25, places=9)
				details = get_details(self.DEPT, COMPANY, "", "", ["Metal"], AS_ON)
				self.assertEqual([(d["Item Code"], flt(d["Weight"])) for d in details], [(ITEM_75, 7.0)])
