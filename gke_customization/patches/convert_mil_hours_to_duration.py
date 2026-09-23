# Copyright (c) 2026, <your org>
# License: GNU General Public License v3. See license.txt

import frappe


def execute():
	doctype = "Monthly In-Out Log"
	field = "spent_hrs"

	if not frappe.db.exists("DocType", doctype):
		return

	# migrate runs the doctype sync BEFORE patches, so by this point the
	# column is already Duration. MariaDB cast the old TIME values to
	# HHMMSS numbers ("28:00:00" -> 280000), not seconds. Read whatever
	# form is present and normalize every row to seconds.
	records = frappe.db.get_all(
		doctype,
		fields=["name", field],
		order_by="creation desc",
	)

	frappe.reload_doc("gke_hrms", "doctype", frappe.scrub(doctype), force=True)

	updates = {
		entry.name: {field: to_seconds(entry.get(field))}
		for entry in records
	}
	if updates:
		frappe.db.bulk_update(doctype, updates, update_modified=False)
	frappe.db.commit()


def to_seconds(value):
	"""Normalize a spent_hrs value to total seconds.

	Depending on when this runs the raw value can be:
	- datetime.timedelta (TIME column read via frappe)
	- "HH:MM:SS" string (TIME column read as raw text)
	- HHMMSS integer/float (MariaDB cast of TIME after the Duration ALTER,
	  e.g. "28:00:00" -> 280000)
	"""
	if not value:
		return 0
	if hasattr(value, "total_seconds"):
		return int(value.total_seconds())
	if isinstance(value, str):
		return hhmmss_to_seconds(value)
	if isinstance(value, (int, float)):
		return hhmmss_to_seconds(int(value))
	return 0


def hhmmss_to_seconds(value):
	"""Decode an HHMMSS number or colon string into total seconds."""
	if isinstance(value, int):
		if value < 0:
			return 0
		hours = value // 10000
		minutes = (value // 100) % 100
		seconds = value % 100
		# guard against garbage that is not a valid HHMMSS time
		if minutes > 59 or seconds > 59:
			return 0
		return (hours * 3600) + (minutes * 60) + seconds

	parts = str(value).strip().split(".")[0].split(":")
	try:
		nums = [int(p) for p in parts]
	except ValueError:
		return 0
	if len(nums) == 3:
		hours, minutes, seconds = nums
	elif len(nums) == 2:
		hours, minutes, seconds = nums[0], nums[1], 0
	elif len(nums) == 1:
		hours, minutes, seconds = nums[0], 0, 0
	else:
		return 0
	return (hours * 3600) + (minutes * 60) + seconds
