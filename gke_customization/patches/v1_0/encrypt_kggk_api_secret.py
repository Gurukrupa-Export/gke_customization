"""Move the KGGK API secret out of `tabSingles` and into the encrypted store.

`api_secret` was a Data field, so its value sat in `tabSingles` in clear text - readable by
anything that can select from the table, and carried into every database backup, export and
`bench --site … backup` artefact ever taken while it was there. It is now a Password field,
which keeps the value in `__Auth` encrypted with the site's key.

Changing the fieldtype alone does not move the value: the plaintext row stays exactly where
it is and the new field reads as empty. This copies it across and then removes the row.

A secret that has been sitting in backups should be treated as exposed. Rotating the key on
the KGGK side after this runs is the only thing that actually undoes it - this patch just
stops it getting worse.
"""

import frappe

SETTINGS = "Data Migration in KGGK"


def execute():
	frappe.reload_doc("gke_order_forms", "doctype", "data_migration_in_kggk")

	# Raw SQL on purpose: `frappe.db.get_value` appends `order by modified`, and `tabSingles`
	# has no such column - it is (doctype, field, value) and nothing else.
	row = frappe.db.sql(
		"select value from tabSingles where doctype = %s and field = 'api_secret'",
		SETTINGS,
	)
	secret = row[0][0] if row else None

	# A Password field on a Single leaves a placeholder behind in `tabSingles`; that is the
	# new arrangement working, not a secret to migrate.
	if secret and set(str(secret)) != {"*"}:
		from frappe.utils.password import set_encrypted_password

		set_encrypted_password(SETTINGS, SETTINGS, secret, "api_secret")

	# Gone either way: either it has been copied into `__Auth`, or it was already the
	# placeholder. Neither belongs in `tabSingles` as a readable value.
	frappe.db.delete("Singles", {"doctype": SETTINGS, "field": "api_secret"})
	frappe.db.commit()
