import frappe


def execute():
	"""Add indexes needed by the Order Detail Report to avoid full table scans."""
	frappe.db.add_index("Manufacturing Work Order", ["for_fg"])
	frappe.db.add_index("Manufacturing Work Order", ["manufacturing_operation"])
	frappe.db.add_index("Manufacturing Work Order", ["manufacturing_order"])
	frappe.db.add_index("Manufacturing Work Order", ["customer"])
	frappe.db.add_index("Manufacturing Work Order", ["posting_date"])

	frappe.db.add_index("Manufacturing Operation", ["status"])
	frappe.db.add_index("Manufacturing Operation", ["department"])

	frappe.db.add_index("Serial Number Creator", ["manufacturing_operation"])
