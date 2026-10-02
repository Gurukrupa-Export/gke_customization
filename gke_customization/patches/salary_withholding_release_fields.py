from frappe.custom.doctype.custom_field.custom_field import (
	create_custom_fields,
)


def execute():
	"""Create custom fields for salary withholding release tracking."""
	create_custom_fields(
		{
			"Salary Withholding": [
				dict(
					fieldname="custom_release_history",
					label="Release History",
					fieldtype="Table",
					options="Salary Withholding Release",
					insert_after="cycles",
					read_only=1,
					cannot_add_rows=1,
					allow_bulk_edit=0,
					no_copy=1,
				),
			],
			"Salary Withholding Cycle": [
				dict(
					fieldname="custom_released_amount",
					label="Released Amount",
					fieldtype="Currency",
					insert_after="journal_entry",
					read_only=1,
					no_copy=1,
					print_hide=1,
				),
			],
		}
	)