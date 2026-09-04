# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class DataMigrationinKGGK(Document):
	def validate(self):
		self.validate_kggk_sync()

	def validate_kggk_sync(self):
		"""Refuse to switch the sync on until it has somewhere to send things.

		`mandatory_depends_on` only runs in the browser, so a programmatic save - a patch, a
		fixture, `bench execute`, a restored Single - can leave the switch on with no target.
		The push would then refuse silently on every record, which looks exactly like a
		broken sync rather than a missing setting.
		"""
		if not cint(self.enable_sync):
			return

		missing = [
			label
			for label, value in (
				(_("To Site"), self.to_site),
				(_("API Key"), self.api_key),
				(_("API Secret"), self.api_secret),
			)
			if not value
		]
		if missing:
			frappe.throw(
				_("Fill in {0} before enabling KGGK Sync.").format(", ".join(missing)),
				title=_("KGGK Sync Not Configured"),
			)

		from gke_customization.gke_order_forms.doc_events.kggk_sync import (
			current_site_hosts,
			host_of,
		)

		target = host_of(self.to_site)
		if target in current_site_hosts():
			# The engine refuses this at push time too. Saying it here means it is found
			# when the mistake is made, not hours later in a log file.
			frappe.throw(
				_("To Site ({0}) is this site. A site cannot sync to itself.").format(target),
				title=_("Wrong Target"),
			)

		if self.from_site and host_of(self.from_site) == target:
			frappe.throw(
				_("From Site and To Site are both {0}.").format(target),
				title=_("Wrong Target"),
			)
