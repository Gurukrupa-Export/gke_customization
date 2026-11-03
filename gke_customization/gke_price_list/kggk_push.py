# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

"""Remote pushes from Product Return Order (Form), run after the local save commits.

These pushes used to run inside the save, so the document, its naming Series row and every
row the save had locked stayed locked for each remote round-trip (15-30 s timeouts per call,
plus image uploads). They now run in one background job queued after commit, in the same
order as before. A failed push no longer rolls the local save back: it is logged against
the document in Error Log, added as a comment on the document, and shown to the user who
saved.
"""

import frappe
from frappe import _


def push_after_commit(reference_doctype, reference_name, steps):
	"""Queue ``steps`` to run in order once the current transaction commits.

	Each step is ``(method_path, doctype, docname, kwargs)``: the job loads the document and
	calls ``method(doc, **kwargs)``. The first failure stops the remaining steps, as it did
	when the pushes ran inline.
	"""
	if not steps:
		return
	frappe.enqueue(
		"gke_customization.gke_price_list.kggk_push.run_push",
		queue="short",
		timeout=900,
		enqueue_after_commit=True,
		reference_doctype=reference_doctype,
		reference_name=reference_name,
		steps=steps,
		user=frappe.session.user,
	)


def run_push(reference_doctype, reference_name, steps, user=None):
	for method_path, doctype, docname, kwargs in steps:
		try:
			frappe.get_attr(method_path)(frappe.get_doc(doctype, docname), **(kwargs or {}))
		except Exception as e:
			message = _("Remote sync of {0} {1} failed: {2}").format(doctype, docname, e)
			frappe.log_error(
				title=_("Remote sync failed for {0} {1}").format(reference_doctype, reference_name),
				reference_doctype=reference_doctype,
				reference_name=reference_name,
			)
			frappe.get_doc(reference_doctype, reference_name).add_comment("Comment", message)
			if user:
				frappe.publish_realtime(
					"msgprint",
					{"message": message, "title": _("Remote Sync Failed"), "indicator": "red"},
					user=user,
				)
			return
