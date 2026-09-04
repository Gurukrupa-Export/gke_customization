"""Remove the separate KGGK "testing site" credentials.

The sync used to carry two targets: the live ``to_site`` and a ``testing_site`` with its own
key and secret. There is one target now, so those three fields are gone from the doctype.

Frappe drops the fields but leaves their values behind: ``tabSingles`` keeps orphan rows
forever, and ``testing_api_secret`` was a Password field, so its real value sits in
``__Auth`` where nothing will ever look at it again. A live API credential left in the
database is worth deleting on the way past.
"""

import frappe

SETTINGS = "Data Migration in KGGK"
GONE = ("testing_site", "testing_api_key", "testing_api_secret", "enable_testing_sync")


def execute():
	frappe.db.delete("Singles", {"doctype": SETTINGS, "field": ("in", GONE)})

	try:
		from frappe.utils.password import remove_encrypted_password

		remove_encrypted_password(SETTINGS, SETTINGS, "testing_api_secret")
	except Exception:
		# Nothing stored, or the helper is not available on this version. Either way the
		# Singles rows above are gone and there is nothing left to point at it.
		pass
