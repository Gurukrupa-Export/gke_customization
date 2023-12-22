# Copyright (c) 2023, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from gke_customization.gke_catalog.doc_events.qr_code import get_qr_code
from frappe.model.document import Document

class QRCodeDemo(Document):
	pass
	# def validate(self):
	# 	self.qr_code = get_qr_code(self.title)
