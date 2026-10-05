# Copyright (c) 2026, Gurukrupa Export and Contributors
# See license.txt

from datetime import timedelta
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from frappe.utils import get_datetime

from gke_customization.gke_catalog.report.employee_batch_issue_receive import (
	employee_batch_issue_receive as report,
)


class FakeSQL:
	"""Answers the report's two queries and records them; anything else (e.g. a
	translation lookup on a cold cache) goes to the real database."""

	def __init__(self, main_rows, ir_rows=()):
		self.real_sql = frappe.db.sql
		self.main_rows, self.ir_rows, self.calls = main_rows, ir_rows, []

	def __call__(self, query, *args, **kwargs):
		text = " ".join(str(query).split())
		if "eir.name as employee_ir" in text:
			rows = self.ir_rows
		elif "`tabManufacturing Operation` mo" in text:
			rows = self.main_rows
		else:
			return self.real_sql(query, *args, **kwargs)
		self.calls.append((text, args[0] if args else kwargs.get("values")))
		return [frappe._dict(row) for row in rows]


def mop(name, employee="EMP-1"):
	return {"manufacturing_operation": name, "employee_id": employee, "status": "WIP"}


def issue(name, operation, employee="EMP-1", date_time="2026-09-01 10:00:00"):
	return {
		"employee_ir": name,
		"manufacturing_operation": operation,
		"employee": employee,
		"type": "Issue",
		"date_time": date_time,
		"owner": "user@example.com",
		"full_name": None,
	}


class TestEmployeeBatchIssueReceive(UnitTestCase):
	def run_report(self, main_rows, ir_rows=(), **filters):
		fake = FakeSQL(main_rows, ir_rows)
		with patch.object(frappe.db, "sql", fake):
			_columns, data, message = report.execute(frappe._dict(filters))
		return data, message, fake.calls

	def test_outstanding_rule_is_applied_before_the_limit(self):
		_data, _message, calls = self.run_report([])
		query = calls[0][0]
		self.assertIn("HAVING SUM(eir.type = 'Issue') > 0 AND SUM(eir.type = 'Receive') = 0", query)
		self.assertIn("outstanding.employee <=> mo.employee", query)
		self.assertLess(query.index("HAVING"), query.index(f"LIMIT {report.ROW_LIMIT + 1}"))

	def test_employee_ir_query_reads_only_the_selected_operations(self):
		_data, _message, calls = self.run_report(
			[mop("MOP-2"), mop("MOP-1")], [issue("EIR-1", "MOP-1")], department="D-1"
		)
		query, values = calls[1]
		self.assertIn("eiro.manufacturing_operation IN %(manufacturing_operations)s", query)
		self.assertEqual(values["manufacturing_operations"], ("MOP-2", "MOP-1"))
		self.assertEqual(values["department"], "D-1")

	def test_nothing_outstanding_skips_the_employee_ir_query(self):
		data, message, calls = self.run_report([])
		self.assertEqual((data, message, len(calls)), ([], None, 1))

	def test_latest_issue_is_shown(self):
		data, _message, _calls = self.run_report(
			[mop("MOP-1")],
			[
				issue("EIR-NEW", "MOP-1", date_time="2026-09-02 10:00:00"),
				issue("EIR-OLD", "MOP-1", date_time="2026-09-01 10:00:00"),
			],
		)
		self.assertEqual(data[0].issue_ir, "EIR-NEW")

	def test_subcontracting_row_without_employee_is_kept(self):
		data, _message, _calls = self.run_report(
			[mop("MOP-1", employee=None)], [issue("EIR-1", "MOP-1", employee=None)]
		)
		self.assertEqual([row.issue_ir for row in data], ["EIR-1"])

	def test_issue_without_date_is_still_dropped(self):
		data, _message, _calls = self.run_report([mop("MOP-1")], [issue("EIR-1", "MOP-1", date_time=None)])
		self.assertEqual(data, [])

	def test_cap_is_reported_not_silent(self):
		rows = [mop(f"MOP-{i}") for i in range(3)]
		irs = [issue(f"EIR-{i}", f"MOP-{i}") for i in range(3)]
		with patch.object(report, "ROW_LIMIT", 2):
			data, message, calls = self.run_report(rows, irs)
		self.assertEqual([row.manufacturing_operation for row in data], ["MOP-0", "MOP-1"])
		self.assertTrue(message)
		self.assertIn("LIMIT 3", calls[0][0])

	def test_no_message_below_the_cap(self):
		with patch.object(report, "ROW_LIMIT", 2):
			data, message, _calls = self.run_report([mop("MOP-1")], [issue("EIR-1", "MOP-1")])
		self.assertEqual((len(data), message), (1, None))


class TestEmployeeBatchIssueReceiveOnMariaDB(IntegrationTestCase):
	"""Runs the report's real SQL against rows inserted directly (a submitted Employee IR
	needs the whole manufacturing setup). Each test uses its own department value, so the
	site's own operations are filtered out, and is rolled back."""

	def setUp(self):
		super().setUp()
		self.addCleanup(frappe.db.rollback)
		self.prefix = "_T-EBIR-" + frappe.generate_hash(length=8)
		self.seq = 0

	def at(self, minutes):
		return get_datetime("2001-01-01 00:00:00") + timedelta(minutes=minutes)

	def next_name(self, kind):
		self.seq += 1
		return f"{self.prefix}-{kind}-{self.seq}"

	def make_mop(self, status, employee, minutes):
		name = self.next_name("MOP")
		frappe.db.bulk_insert(
			"Manufacturing Operation",
			["name", "creation", "modified", "status", "operation", "department", "employee"],
			[(name, self.at(minutes), self.at(minutes), status, "_Test Operation", self.prefix, employee)],
		)
		return name

	def make_ir(self, ir_type, operation, employee, minutes, docstatus=1):
		name = self.next_name("EIR")
		frappe.db.bulk_insert(
			"Employee IR",
			["name", "creation", "modified", "docstatus", "type", "employee", "date_time"],
			[(name, self.at(minutes), self.at(minutes), docstatus, ir_type, employee, self.at(minutes))],
		)
		frappe.db.bulk_insert(
			"Employee IR Operation",
			["name", "parent", "parenttype", "parentfield", "idx", "docstatus", "manufacturing_operation"],
			[(f"{name}-1", name, "Employee IR", "employee_ir_operations", 1, docstatus, operation)],
		)
		return name

	def run_report(self):
		_columns, data, message = report.execute(frappe._dict(department=self.prefix))
		return {row.manufacturing_operation: row for row in data}, message

	def test_old_outstanding_operation_survives_newer_finished_history(self):
		"""The review's case, scaled down: with the cap at 3 the newest operations were all
		issued and received, and the old outstanding one fell outside the page."""
		old = self.make_mop("WIP", "EMP-A", minutes=0)
		self.make_ir("Issue", old, "EMP-A", minutes=1)
		for i in range(4):
			done = self.make_mop("Finished", "EMP-A", minutes=10 + i)
			self.make_ir("Issue", done, "EMP-A", minutes=20 + i)
			self.make_ir("Receive", done, "EMP-A", minutes=30 + i)
		with patch.object(report, "ROW_LIMIT", 3):
			rows, message = self.run_report()
		self.assertEqual(list(rows), [old])
		self.assertIsNone(message)

	def test_which_operations_count_as_outstanding(self):
		subcontracted = self.make_mop("WIP", None, minutes=1)
		self.make_ir("Issue", subcontracted, None, minutes=2)
		receive_cancelled = self.make_mop("WIP", "EMP-A", minutes=3)
		self.make_ir("Issue", receive_cancelled, "EMP-A", minutes=4)
		self.make_ir("Receive", receive_cancelled, "EMP-A", minutes=5, docstatus=2)
		received_by_other = self.make_mop("WIP", "EMP-A", minutes=6)
		self.make_ir("Issue", received_by_other, "EMP-A", minutes=7)
		self.make_ir("Receive", received_by_other, "EMP-B", minutes=8)
		two_issues = self.make_mop("WIP", "EMP-A", minutes=9)
		self.make_ir("Issue", two_issues, "EMP-A", minutes=10)
		newest_issue = self.make_ir("Issue", two_issues, "EMP-A", minutes=11)
		received = self.make_mop("Finished", "EMP-A", minutes=12)
		self.make_ir("Issue", received, "EMP-A", minutes=13)
		self.make_ir("Receive", received, "EMP-A", minutes=14)
		issue_cancelled = self.make_mop("WIP", "EMP-A", minutes=15)
		self.make_ir("Issue", issue_cancelled, "EMP-A", minutes=16, docstatus=2)
		issued_to_other = self.make_mop("WIP", "EMP-A", minutes=17)
		self.make_ir("Issue", issued_to_other, "EMP-B", minutes=18)
		blank_employee = self.make_mop("WIP", "", minutes=19)
		self.make_ir("Issue", blank_employee, None, minutes=20)

		rows, message = self.run_report()

		self.assertEqual(set(rows), {subcontracted, receive_cancelled, received_by_other, two_issues})
		self.assertEqual(rows[two_issues].issue_ir, newest_issue)
		self.assertIsNone(message)

	def test_cap_is_reported(self):
		for i in range(2):
			operation = self.make_mop("WIP", "EMP-A", minutes=i)
			self.make_ir("Issue", operation, "EMP-A", minutes=10 + i)
		with patch.object(report, "ROW_LIMIT", 1):
			rows, message = self.run_report()
		self.assertEqual(len(rows), 1)
		self.assertTrue(message)
