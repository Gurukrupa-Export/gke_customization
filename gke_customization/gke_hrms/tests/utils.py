"""Shared constants and helper functions for gke_hrms tests."""

import json
from datetime import datetime
from pathlib import Path

import frappe
from frappe.utils import getdate

TEST_COMPANY = "_Test GKE Sync Company"
DEVICE_ID = "GKE-T-BIO-9001"
TIME_THRESHOLD = 120

LEAVE_ATTENDANCE_SCRIPT = "Update Leave And Attendance Based On Leave Applied"
SERVER_SCRIPT_DIR = Path(__file__).parent / "server_script"


def load_server_scripts(doctypes: list[str] | None = None) -> list[dict]:
	"""Load Server Script records from server_script/<doctype_name>/<script_name>.{json,py}.

	The .json holds the record fields (including the real script name), the .py
	holds the script body. The filename must be the scrubbed script name.
	Pass doctypes (e.g. ["employee_checkin"]) to load only those folders.
	"""
	records = []
	for meta_path in sorted(SERVER_SCRIPT_DIR.glob("*/*.json")):
		if doctypes and meta_path.parent.name not in doctypes:
			continue

		record = json.loads(meta_path.read_text())

		expected_stem = frappe.scrub(record["name"])
		if meta_path.stem != expected_stem:
			raise ValueError(
				f"{meta_path.name}: filename must match the script name, "
				f"expected '{expected_stem}.json'"
			)

		record["doctype"] = "Server Script"
		record["script"] = meta_path.with_suffix(".py").read_text()
		records.append(record)
	return records


def apply_sync_settings():
	"""Point Biometric Settings at today's punches with the test threshold."""
	settings = frappe.get_doc("Biometric Settings", "Biometric Settings")
	settings.manual = 0
	settings.day_threshold = 1
	settings.time_threshold = str(TIME_THRESHOLD)
	settings.biometric_api = settings.biometric_api or "https://biometric.example.test/api"
	settings.biometric_api_key = settings.biometric_api_key or "test-key"
	settings.save(ignore_permissions=True)


def make_api_log(punch_time, indexno, userid):
	"""Build one log entry in the device server format (DD/MM/YYYY HH:MM)."""
	punch_dt = datetime.combine(getdate(), datetime.strptime(punch_time, "%H:%M").time())
	return {
		"userid": userid,
		"device_name": "Test Device",
		"indexno": str(indexno),
		"edatetime_e": punch_dt.strftime("%d/%m/%Y %H:%M"),
	}


def make_leave_allocation(employee, leave_type, from_date, to_date, days):
	"""Create and submit a Leave Allocation."""
	allocation = frappe.get_doc(
		{
			"doctype": "Leave Allocation",
			"employee": employee,
			"leave_type": leave_type,
			"from_date": from_date,
			"to_date": to_date,
			"new_leaves_allocated": days,
		}
	)
	allocation.insert(ignore_permissions=True)
	allocation.submit()
	return allocation


def make_attendance(employee, attendance_date, status, leave_type=None):
	"""Create and submit an Attendance. leave_type is only used for On Leave."""
	attendance = frappe.get_doc(
		{
			"doctype": "Attendance",
			"employee": employee,
			"attendance_date": attendance_date,
			"status": status,
			"leave_type": leave_type,
		}
	)
	attendance.insert(ignore_permissions=True)
	attendance.submit()
	return attendance


def make_attendance_request(employee, from_date, to_date, company):
	"""Create an On Duty Attendance Request and mark it submitted without running
	on_submit, which would create attendance rows of its own."""
	request = frappe.get_doc(
		{
			"doctype": "Attendance Request",
			"employee": employee,
			"from_date": from_date,
			"to_date": to_date,
			"reason": "On Duty",
			"company": company,
		}
	)
	request.flags.ignore_mandatory = True
	request.insert(ignore_permissions=True)
	frappe.db.set_value("Attendance Request", request.name, "docstatus", 1)
	return request