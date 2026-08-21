"""Create the KGGK sync marker fields on Item and BOM.

`custom_is_sync` was referenced by the old Manufacturing Plan sync but existed in no
fixture and on no site, so every `get_value` for it returned None and nothing was ever
recorded as synced. Created here so the field exists whether or not fixtures are imported.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

MODULE = "GKE Order Forms"

FIELDS = {
	doctype: [
		{
			"fieldname": "custom_kggk_sync_section",
			"label": "KGGK Sync",
			"fieldtype": "Section Break",
			"insert_after": insert_after,
			"collapsible": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_is_sync",
			"label": "Synced to KGGK",
			"fieldtype": "Check",
			"insert_after": "custom_kggk_sync_section",
			"read_only": 1,
			"in_standard_filter": 1,
			"module": MODULE,
			"description": "Set by the KGGK sync. Untick to make the next run push this record again.",
		},
		{
			"fieldname": "custom_last_synced_on",
			"label": "Last Synced On",
			"fieldtype": "Datetime",
			"insert_after": "custom_is_sync",
			"read_only": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_sync_error",
			"label": "Last Sync Error",
			"fieldtype": "Small Text",
			"insert_after": "custom_last_synced_on",
			"read_only": 1,
			"module": MODULE,
			"depends_on": "eval:doc.custom_sync_error",
		},
	]
	for doctype, insert_after in (("Item", "gst_hsn_code"), ("BOM", "item_name"))
}


def execute():
	create_custom_fields(FIELDS, ignore_validate=True)
	frappe.clear_cache()
