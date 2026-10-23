"""Tests for the sandwich rule (gke_hrms.sandwich_rule).

A block of continuous public holidays and weekly offs, containing at least one
public holiday, becomes Leave Without Pay when both days around the block are
Casual Leave, Half Day or Absent and Casual Leave is involved. Weekly offs are
never converted.

Covered entry points:
	- sandwich_rule helpers (pure logic)
	- the daily scheduler gke_hrms.utils.check_sadwitch_rule
	- the Leave Application events (get_sandwich_dates and on_submit)

bench --site <site-name> run-tests --app gke_customization --module gke_customization.gke_hrms.tests.test_sandwich_rule

"""

import unittest
from datetime import date, timedelta

import frappe
from frappe.tests import UnitTestCase
from frappe.utils import add_days, getdate

from gke_customization.gke_hrms.doc_events.leave_application import get_sandwich_dates
from gke_customization.gke_hrms.sandwich_rule import (
	get_sandwiched_holidays,
	is_sandwiched,
)
from gke_customization.gke_hrms.tests.base import GKHRMSTestCase
from gke_customization.gke_hrms.tests.utils import (
	DEVICE_ID,
	make_attendance,
	make_attendance_request,
	make_leave_allocation,
)
from gke_customization.gke_hrms.utils import check_sadwitch_rule

CASUAL_LEAVE = "Casual Leave"
SICK_LEAVE = "Sick Leave"
MARRIAGE_LEAVE = "Marriage Leave"
LEAVE_WITHOUT_PAY = "Leave Without Pay"
PRESENT = "Present"
HALF_DAY = "Half Day"
ABSENT = "Absent"

# Monday of the week used by the dated scenarios (all in the past, inside 2025)
WEEK_START = date(2025, 3, 3)
TUESDAY = WEEK_START + timedelta(days=1)
WEDNESDAY = WEEK_START + timedelta(days=2)
THURSDAY = WEEK_START + timedelta(days=3)
FRIDAY = WEEK_START + timedelta(days=4)
SATURDAY = WEEK_START + timedelta(days=5)
SUNDAY = WEEK_START + timedelta(days=6)
NEXT_MONDAY = WEEK_START + timedelta(days=7)


class TestSandwichRuleLogic(UnitTestCase):
	"""Pure logic of sandwich_rule, no database access."""

	def test_casual_leave_on_either_side_sandwiches(self):
		self.assertTrue(is_sandwiched(CASUAL_LEAVE, CASUAL_LEAVE))
		self.assertTrue(is_sandwiched(CASUAL_LEAVE, HALF_DAY))
		self.assertTrue(is_sandwiched(HALF_DAY, CASUAL_LEAVE))
		self.assertTrue(is_sandwiched(CASUAL_LEAVE, ABSENT))
		self.assertTrue(is_sandwiched(ABSENT, CASUAL_LEAVE))

	def test_sides_without_casual_leave_do_not_sandwich(self):
		self.assertFalse(is_sandwiched(ABSENT, ABSENT))
		self.assertFalse(is_sandwiched(HALF_DAY, ABSENT))
		self.assertFalse(is_sandwiched(HALF_DAY, HALF_DAY))

	def test_casual_leave_applied_covers_the_missing_casual_leave(self):
		self.assertTrue(is_sandwiched(HALF_DAY, ABSENT, casual_leave_applied=True))

	def test_blocking_sides_never_sandwich(self):
		for blocking in (PRESENT, SICK_LEAVE, MARRIAGE_LEAVE, "Outdoor Duty"):
			with self.subTest(blocking=blocking):
				self.assertFalse(is_sandwiched(CASUAL_LEAVE, blocking))
				self.assertFalse(is_sandwiched(blocking, CASUAL_LEAVE))
				self.assertFalse(is_sandwiched(blocking, CASUAL_LEAVE, casual_leave_applied=True))

	def get_holidays(self, public_holidays, weekly_offs, statuses, attendance_request_dates=None):
		def get_status(day):
			return statuses.get(day, PRESENT)

		return get_sandwiched_holidays(
			set(public_holidays),
			set(weekly_offs),
			set(public_holidays),
			get_status,
			attendance_request_dates or set(),
		)

	def test_single_holiday(self):
		holidays = self.get_holidays(
			[TUESDAY], [], {WEEK_START: CASUAL_LEAVE, WEDNESDAY: CASUAL_LEAVE}
		)
		self.assertEqual(holidays, {TUESDAY})

	def test_multi_holiday_block(self):
		holidays = self.get_holidays(
			[TUESDAY, WEDNESDAY], [], {WEEK_START: CASUAL_LEAVE, THURSDAY: ABSENT}
		)
		self.assertEqual(holidays, {TUESDAY, WEDNESDAY})

	def test_weekly_offs_are_part_of_the_block_but_never_converted(self):
		holidays = self.get_holidays(
			[FRIDAY],
			[SATURDAY, SUNDAY],
			{THURSDAY: CASUAL_LEAVE, NEXT_MONDAY: CASUAL_LEAVE},
		)
		self.assertEqual(holidays, {FRIDAY})

	def test_weekly_off_next_to_the_holiday_moves_the_boundary(self):
		# Friday is the public holiday, Saturday and Sunday are weekly offs, so the
		# Casual Leave on Saturday is not a boundary and the block is still open
		holidays = self.get_holidays(
			[FRIDAY],
			[SATURDAY, SUNDAY],
			{THURSDAY: CASUAL_LEAVE, SATURDAY: CASUAL_LEAVE},
		)
		self.assertEqual(holidays, set())

	def test_attendance_request_on_the_block_or_a_side_blocks_the_sandwich(self):
		statuses = {WEEK_START: CASUAL_LEAVE, WEDNESDAY: CASUAL_LEAVE}
		for covered_day in (WEEK_START, TUESDAY, WEDNESDAY):
			with self.subTest(covered_day=covered_day):
				holidays = self.get_holidays([TUESDAY], [], statuses, {covered_day})
				self.assertEqual(holidays, set())

	def test_block_without_any_public_holiday_is_not_a_candidate(self):
		holidays = self.get_holidays(
			[], [SATURDAY, SUNDAY], {FRIDAY: CASUAL_LEAVE, NEXT_MONDAY: CASUAL_LEAVE}
		)
		self.assertEqual(holidays, set())


class SandwichRuleTestCase(GKHRMSTestCase):
	"""Shared fixture: one employee with a holiday list built by each test.

	The scheduler commits, so the rollback at the end of the class cannot be
	trusted to remove the data. Everything created for the employee is deleted
	in a cleanup instead.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		for leave_type in (CASUAL_LEAVE, SICK_LEAVE, MARRIAGE_LEAVE, LEAVE_WITHOUT_PAY):
			cls.ensure_leave_type(leave_type)

	@classmethod
	def ensure_leave_type(cls, leave_type):
		# include_holiday must stay off so core Leave Application submit does not
		# mark public holidays and weekly offs with the leave type; the sandwich
		# engine owns those days.
		if frappe.db.exists("Leave Type", leave_type):
			frappe.db.set_value(
				"Leave Type",
				leave_type,
				{"max_continuous_days_allowed": 0, "include_holiday": 0},
			)
			return
		cls._insert(
			{
				"doctype": "Leave Type",
				"leave_type_name": leave_type,
				"max_leaves_allowed": 30,
				"max_continuous_days_allowed": 0,
				"include_holiday": 0,
				"is_lwp": 1 if leave_type == LEAVE_WITHOUT_PAY else 0,
			}
		)

	def setUp(self):
		super().setUp()
		device_id = f"{DEVICE_ID}-{self._testMethodName}-{frappe.generate_hash(length=6)}"
		self.employee = self.create_employee("Test Sandwich Rule", attendance_device_id=device_id).name
		self.holiday_list_name = None
		self.addCleanup(self.delete_employee_records)

	def delete_employee_records(self):
		for doctype in (
			"Attendance",
			"Attendance Request",
			"Leave Ledger Entry",
			"Leave Application",
			"Leave Allocation",
		):
			frappe.db.delete(doctype, {"employee": self.employee})

		if self.holiday_list_name:
			frappe.db.set_value("Employee", self.employee, "holiday_list", None)
			frappe.db.delete("Holiday List Assignment", {"assigned_to": self.employee})
			frappe.delete_doc("Holiday List", self.holiday_list_name, force=1, ignore_permissions=True)

	def use_holidays(self, public_holidays=(), weekly_offs=(), from_date=None, to_date=None):
		"""Give the employee a fresh Holiday List with exactly these days off."""
		holidays = [
			{"holiday_date": day, "description": "Sandwich Test Holiday", "weekly_off": 0}
			for day in public_holidays
		] + [
			{"holiday_date": day, "description": "Sandwich Test Weekly Off", "weekly_off": 1}
			for day in weekly_offs
		]

		values = {
			"doctype": "Holiday List",
			"holiday_list_name": f"_Test Sandwich Holiday List {frappe.generate_hash(length=6)}",
			"from_date": from_date or date(2025, 1, 1),
			"to_date": to_date or date(2025, 12, 31),
			"holidays": holidays,
		}
		if frappe.get_meta("Holiday List").has_field("custom_company"):
			values["custom_company"] = self.company

		self.holiday_list_name = self._insert(values).name
		frappe.db.set_value("Employee", self.employee, "holiday_list", self.holiday_list_name)
		assignment = self._insert(
			{
				"doctype": "Holiday List Assignment",
				"applicable_for": "Employee",
				"assigned_to": self.employee,
				"holiday_list": self.holiday_list_name,
				"from_date": values["from_date"],
			}
		)
		assignment.submit()

	def clear_attendance(self):
		frappe.db.delete("Attendance", {"employee": self.employee})
		frappe.db.delete("Attendance Request", {"employee": self.employee})

	def mark_day(self, day, status):
		"""Mark a day as Present (no row), Half Day, Absent or a leave type."""
		if status in (None, PRESENT):
			return
		if status in (HALF_DAY, ABSENT):
			make_attendance(self.employee, day, status)
		else:
			make_attendance(self.employee, day, "On Leave", leave_type=status)

	def get_attendance(self, day):
		return frappe.get_all(
			"Attendance",
			filters={"employee": self.employee, "attendance_date": day, "docstatus": 1},
			fields=["name", "status", "leave_type", "leave_application"],
		)

	def get_leave_without_pay_dates(self):
		return {
			getdate(attendance.attendance_date)
			for attendance in frappe.get_all(
				"Attendance",
				filters={
					"employee": self.employee,
					"docstatus": 1,
					"status": "On Leave",
					"leave_type": LEAVE_WITHOUT_PAY,
				},
				fields=["attendance_date"],
			)
		}


class TestSandwichRuleScheduler(SandwichRuleTestCase):
	"""Daily scheduler path: check_sadwitch_rule marks holidays as Leave Without Pay."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("DocType", "Biometric Settings"):
			raise unittest.SkipTest("gurukrupa_biometric app is not installed on this site")

	def setUp(self):
		super().setUp()
		settings = frappe.db.get_singles_dict("Biometric Settings")
		self.addCleanup(self.restore_window, settings)

	def restore_window(self, settings):
		# The doctype default for From Date is the placeholder text "dd-mm-yyyy",
		# which is not a date, so only real dates are written back.
		frappe.db.set_single_value("Biometric Settings", "manual", settings.get("manual") or 0)
		for fieldname in ("from_date", "to_date"):
			value = settings.get(fieldname)
			try:
				value = str(getdate(value)) if value else None
			except Exception:
				frappe.clear_last_message()
				value = None
			frappe.db.set_single_value("Biometric Settings", fieldname, value)
		frappe.db.commit()

	def set_window(self, from_date, to_date):
		frappe.db.set_single_value("Biometric Settings", "manual", 1)
		frappe.db.set_single_value("Biometric Settings", "from_date", str(from_date))
		frappe.db.set_single_value("Biometric Settings", "to_date", str(to_date))

	def run_scheduler(self, from_date=WEEK_START, to_date=NEXT_MONDAY):
		self.set_window(from_date, to_date)
		check_sadwitch_rule()

	def check_single_holiday(self, left_status, right_status, expected_leave_without_pay):
		"""Tuesday holiday between Monday (left) and Wednesday (right)."""
		self.clear_attendance()
		self.mark_day(WEEK_START, left_status)
		self.mark_day(WEDNESDAY, right_status)
		self.run_scheduler()

		expected = {TUESDAY} if expected_leave_without_pay else set()
		self.assertEqual(
			self.get_leave_without_pay_dates(),
			expected,
			msg=f"left={left_status}, right={right_status}",
		)

	def test_single_holiday_between_leave_and_other_statuses(self):
		self.use_holidays(public_holidays=[TUESDAY])

		# (left, right) paired with the leave type used for the leave side
		for leave_type in (CASUAL_LEAVE, SICK_LEAVE, MARRIAGE_LEAVE):
			is_casual = leave_type == CASUAL_LEAVE
			rows = [
				# Leave / Present and Present / Leave never sandwich
				((leave_type, PRESENT), False),
				((PRESENT, leave_type), False),
				# Casual Leave with another leave, Half Day or Absent sandwiches
				((leave_type, leave_type), is_casual),
				((leave_type, HALF_DAY), is_casual),
				((HALF_DAY, leave_type), is_casual),
				((leave_type, ABSENT), is_casual),
				((ABSENT, leave_type), is_casual),
			]
			for (left_status, right_status), expected in rows:
				with self.subTest(leave_type=leave_type, left=left_status, right=right_status):
					self.check_single_holiday(left_status, right_status, expected)

	def test_casual_leave_with_another_leave_type_is_paid(self):
		self.use_holidays(public_holidays=[TUESDAY])
		for left_status, right_status in (
			(CASUAL_LEAVE, SICK_LEAVE),
			(SICK_LEAVE, CASUAL_LEAVE),
			(CASUAL_LEAVE, MARRIAGE_LEAVE),
		):
			with self.subTest(left=left_status, right=right_status):
				self.check_single_holiday(left_status, right_status, False)

	def test_without_casual_leave_the_holiday_is_paid(self):
		self.use_holidays(public_holidays=[TUESDAY])
		for left_status, right_status in (
			(ABSENT, ABSENT),
			(HALF_DAY, ABSENT),
			(ABSENT, HALF_DAY),
			(HALF_DAY, HALF_DAY),
		):
			with self.subTest(left=left_status, right=right_status):
				self.check_single_holiday(left_status, right_status, False)

	def test_attendance_request_on_a_side_keeps_the_holiday_paid(self):
		self.use_holidays(public_holidays=[TUESDAY])
		self.mark_day(WEEK_START, CASUAL_LEAVE)
		self.mark_day(WEDNESDAY, ABSENT)
		make_attendance_request(self.employee, WEDNESDAY, WEDNESDAY, self.company)

		self.run_scheduler()

		self.assertEqual(self.get_leave_without_pay_dates(), set())

	def test_multi_holiday_block_is_converted_as_a_whole(self):
		self.use_holidays(public_holidays=[TUESDAY, WEDNESDAY])
		self.mark_day(WEEK_START, CASUAL_LEAVE)
		self.mark_day(THURSDAY, CASUAL_LEAVE)

		self.run_scheduler()

		self.assertEqual(self.get_leave_without_pay_dates(), {TUESDAY, WEDNESDAY})

	def test_weekly_offs_are_never_converted(self):
		# Friday is the public holiday, Saturday and Sunday are weekly offs
		self.use_holidays(public_holidays=[FRIDAY], weekly_offs=[SATURDAY, SUNDAY])
		self.mark_day(THURSDAY, CASUAL_LEAVE)
		self.mark_day(NEXT_MONDAY, CASUAL_LEAVE)

		self.run_scheduler()

		self.assertEqual(self.get_leave_without_pay_dates(), {FRIDAY})
		self.assertEqual(self.get_attendance(SATURDAY), [])
		self.assertEqual(self.get_attendance(SUNDAY), [])

	def test_weekly_off_block_with_sick_leave_is_paid(self):
		self.use_holidays(public_holidays=[FRIDAY], weekly_offs=[SATURDAY, SUNDAY])
		self.mark_day(THURSDAY, SICK_LEAVE)
		self.mark_day(NEXT_MONDAY, CASUAL_LEAVE)

		self.run_scheduler()

		self.assertEqual(self.get_leave_without_pay_dates(), set())

	def test_second_run_does_not_create_duplicates(self):
		self.use_holidays(public_holidays=[TUESDAY])
		self.mark_day(WEEK_START, CASUAL_LEAVE)
		self.mark_day(WEDNESDAY, CASUAL_LEAVE)

		self.run_scheduler()
		self.run_scheduler()

		self.assertEqual(len(self.get_attendance(TUESDAY)), 1)
		self.assertEqual(self.get_leave_without_pay_dates(), {TUESDAY})

	def test_existing_attendance_on_the_holiday_is_kept(self):
		self.use_holidays(public_holidays=[TUESDAY])
		self.mark_day(WEEK_START, CASUAL_LEAVE)
		self.mark_day(WEDNESDAY, CASUAL_LEAVE)
		present = make_attendance(self.employee, TUESDAY, "Present")

		self.run_scheduler()

		attendance = self.get_attendance(TUESDAY)
		self.assertEqual([row.name for row in attendance], [present.name])
		self.assertEqual(attendance[0].status, "Present")
		self.assertEqual(self.get_leave_without_pay_dates(), set())

	def test_default_window_covers_the_last_fifteen_days(self):
		today = getdate()
		holiday = add_days(today, -6)
		self.use_holidays(
			public_holidays=[holiday],
			from_date=add_days(today, -60),
			to_date=add_days(today, 60),
		)
		self.mark_day(add_days(holiday, -1), CASUAL_LEAVE)
		self.mark_day(add_days(holiday, 1), CASUAL_LEAVE)

		frappe.db.set_single_value("Biometric Settings", "manual", 0)
		check_sadwitch_rule()

		self.assertEqual(self.get_leave_without_pay_dates(), {holiday})

	def test_holiday_outside_the_default_window_is_ignored(self):
		today = getdate()
		holiday = add_days(today, -40)
		self.use_holidays(
			public_holidays=[holiday],
			from_date=add_days(today, -60),
			to_date=add_days(today, 60),
		)
		self.mark_day(add_days(holiday, -1), CASUAL_LEAVE)
		self.mark_day(add_days(holiday, 1), CASUAL_LEAVE)

		frappe.db.set_single_value("Biometric Settings", "manual", 0)
		check_sadwitch_rule()

		self.assertEqual(self.get_leave_without_pay_dates(), set())


class TestSandwichRuleLeaveApplication(SandwichRuleTestCase):
	"""Leave Application path: the application itself is the Casual Leave side."""

	def setUp(self):
		super().setUp()
		self.addCleanup(frappe.set_user, frappe.session.user)
		self.approver_doc = frappe.get_doc("User", self.approver)
		self.approver_doc.add_roles("Leave Approver")
		for leave_type in (CASUAL_LEAVE, SICK_LEAVE):
			make_leave_allocation(self.employee, leave_type, date(2025, 1, 1), date(2025, 12, 31), 12)

	def make_application(self, leave_type, from_date, to_date, submit=True):
		application = frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": self.employee,
				"leave_type": leave_type,
				"from_date": from_date,
				"to_date": to_date,
				"status": "Approved",
				"leave_approver": self.approver,
				"company": self.company,
			}
		)
		application.insert(ignore_permissions=True)
		if submit:
			application.submit()
		return application

	def get_dates_for(self, leave_type, from_date, to_date):
		return get_sandwich_dates(
			frappe._dict(
				employee=self.employee, leave_type=leave_type, from_date=from_date, to_date=to_date
			)
		)

	def test_casual_leave_over_a_holiday_block_converts_only_the_public_holiday(self):
		self.use_holidays(public_holidays=[FRIDAY], weekly_offs=[SATURDAY, SUNDAY])

		application = self.make_application(CASUAL_LEAVE, THURSDAY, NEXT_MONDAY)

		holiday_attendance = self.get_attendance(FRIDAY)
		self.assertEqual(len(holiday_attendance), 1)
		self.assertEqual(holiday_attendance[0].status, "On Leave")
		self.assertEqual(holiday_attendance[0].leave_type, LEAVE_WITHOUT_PAY)
		self.assertFalse(holiday_attendance[0].leave_application)

		for working_day in (THURSDAY, NEXT_MONDAY):
			attendance = self.get_attendance(working_day)
			self.assertEqual(len(attendance), 1)
			self.assertEqual(attendance[0].leave_type, CASUAL_LEAVE)
			self.assertEqual(attendance[0].leave_application, application.name)

		self.assertEqual(self.get_attendance(SATURDAY), [])
		self.assertEqual(self.get_attendance(SUNDAY), [])

	def test_sick_leave_over_a_holiday_block_stays_paid(self):
		self.use_holidays(public_holidays=[FRIDAY], weekly_offs=[SATURDAY, SUNDAY])

		self.make_application(SICK_LEAVE, THURSDAY, NEXT_MONDAY)

		self.assertEqual(self.get_leave_without_pay_dates(), set())
		self.assertEqual(self.get_attendance(SATURDAY), [])
		self.assertEqual(self.get_attendance(SUNDAY), [])

	def test_sandwich_dates_only_for_casual_leave(self):
		self.use_holidays(public_holidays=[FRIDAY], weekly_offs=[SATURDAY, SUNDAY])

		self.assertEqual(self.get_dates_for(CASUAL_LEAVE, THURSDAY, NEXT_MONDAY), [FRIDAY])
		self.assertEqual(self.get_dates_for(SICK_LEAVE, THURSDAY, NEXT_MONDAY), [])
		self.assertEqual(self.get_dates_for(MARRIAGE_LEAVE, THURSDAY, NEXT_MONDAY), [])

	def test_no_sandwich_dates_without_a_public_holiday_in_range(self):
		self.use_holidays(public_holidays=[FRIDAY], weekly_offs=[SATURDAY, SUNDAY])

		self.assertEqual(self.get_dates_for(CASUAL_LEAVE, WEEK_START, WEDNESDAY), [])
		# only the weekly offs are inside the range
		self.assertEqual(self.get_dates_for(CASUAL_LEAVE, SATURDAY, SUNDAY), [])

	def test_half_day_on_the_other_side_completes_the_sandwich(self):
		self.use_holidays(public_holidays=[TUESDAY])
		self.mark_day(WEDNESDAY, HALF_DAY)

		self.assertEqual(self.get_dates_for(CASUAL_LEAVE, WEEK_START, TUESDAY), [TUESDAY])

	def test_absent_on_the_other_side_completes_the_sandwich(self):
		self.use_holidays(public_holidays=[TUESDAY])
		self.mark_day(WEDNESDAY, ABSENT)

		self.assertEqual(self.get_dates_for(CASUAL_LEAVE, WEEK_START, TUESDAY), [TUESDAY])

	def test_present_or_other_leave_on_the_other_side_blocks_the_sandwich(self):
		self.use_holidays(public_holidays=[TUESDAY])

		with self.subTest(other_side=PRESENT):
			self.assertEqual(self.get_dates_for(CASUAL_LEAVE, WEEK_START, TUESDAY), [])

		with self.subTest(other_side=SICK_LEAVE):
			self.mark_day(WEDNESDAY, SICK_LEAVE)
			self.assertEqual(self.get_dates_for(CASUAL_LEAVE, WEEK_START, TUESDAY), [])

	def test_attendance_request_on_the_other_side_blocks_the_sandwich(self):
		self.use_holidays(public_holidays=[TUESDAY])
		self.mark_day(WEDNESDAY, ABSENT)
		make_attendance_request(self.employee, WEDNESDAY, WEDNESDAY, self.company)

		self.assertEqual(self.get_dates_for(CASUAL_LEAVE, WEEK_START, TUESDAY), [])
