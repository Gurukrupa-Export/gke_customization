"""Add the columns that BOM and Item Custom Fields were left without.

A Custom Field is saved first and its column added second, and MariaDB commits whatever is
pending before it runs an ``ALTER TABLE``. So when that ALTER failed -- ``tabBOM`` was full::

    ALTER TABLE `tabBOM` ADD COLUMN `custom_kggk_source_doctype` varchar(140), ...
    (1118, 'Row size too large ...')

-- the Custom Field stayed and its column never arrived. Every save of the doctype after that
builds an UPDATE naming the column and fails::

    (1054, "Unknown column 'custom_kggk_source_doctype' in 'SET'")

which on KGGK is every BOM save, including the one the Serial Number Creator makes on submit.

``remove_bom_row_size_fields`` frees the room; this runs after it and gives each such field its
column. ``frappe.db.updatedb`` rebuilds the table from the doctype's meta and adds exactly the
columns that are missing, so nothing else is touched. Idempotent: a doctype with no missing
column is skipped. Can also be run ad hoc::

    bench --site <site> execute gke_customization.patches.add_missing_custom_field_columns.execute
"""

import frappe
from frappe.model import no_value_fields, table_fields

DOCTYPES = ("BOM", "Item")


def execute():
	for doctype in DOCTYPES:
		missing = missing_columns(doctype)
		if not missing:
			continue

		frappe.clear_cache(doctype=doctype)
		# Raises 1118 if the table is still too full; that is the right outcome - a migrate
		# that cannot fix this must say so, not leave every save of the doctype failing.
		frappe.db.updatedb(doctype)
		frappe.clear_cache(doctype=doctype)

		still_missing = missing_columns(doctype)
		added = [f for f in missing if f not in still_missing]
		frappe.logger().info(
			f"add_missing_custom_field_columns: {doctype}: added {', '.join(added) or 'none'}"
		)
		if still_missing:
			frappe.logger().warning(
				f"add_missing_custom_field_columns: {doctype} still has no column for "
				+ ", ".join(still_missing)
			)


def missing_columns(doctype):
	"""Custom Fields of ``doctype`` that store a value but have no column in its table."""
	columns = set(frappe.db.get_table_columns(doctype))
	return [
		row.fieldname
		for row in frappe.get_all(
			"Custom Field",
			filters={"dt": doctype},
			fields=["fieldname", "fieldtype", "is_virtual"],
			order_by="creation asc",
		)
		if row.fieldname
		and row.fieldtype not in no_value_fields
		and row.fieldtype not in table_fields
		and not row.is_virtual
		and row.fieldname not in columns
	]
