import frappe
import json
import frappe
from frappe import _
from frappe.contacts.doctype.address.address import get_company_address
from frappe.desk.notifications import clear_doctype_notifications
from frappe.model.mapper import get_mapped_doc
from frappe.model.utils import get_fetch_values
from frappe.utils import cint, flt
from erpnext.controllers.accounts_controller import get_taxes_and_charges, merge_taxes

def validate(self,method=None):
	for r in self.items :
		if not r.against_sales_order:
					frappe.throw(
						"Row {0} : Delivery can be created from Delivery Note Company".format(r.idx)
					)
	if self.company=='Sadguru Diamond':
		for r in self.items :
			if not r.batch_no and not r.diamond_grade:
				frappe.throw("Batch no and Diamond grade are mandatory")
			elif not r.batch_no:
				frappe.throw("Batch no is mandatory")
			elif not r.diamond_grade:
				frappe.throw("Diamond grade is mandatory")
				
@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None, args=None):
	doc = frappe.get_doc("Delivery Note", source_name)

	to_make_invoice_qty_map = {}
	returned_qty_map = get_returned_qty_map(source_name)
	invoiced_qty_map = get_invoiced_qty_map(source_name)

	def set_missing_values(source, target):
		target.run_method("set_missing_values")
		target.run_method("set_po_nos")

		if len(target.get("items")) == 0:
			frappe.throw(_("All these items have already been Invoiced/Returned"))

		if args and args.get("merge_taxes"):
			merge_taxes(source.get("taxes") or [], target)

		target.run_method("calculate_taxes_and_totals")

		# set company address
		if source.company_address:
			target.update({"company_address": source.company_address})
		else:
			# set company address
			target.update(get_company_address(target.company))

		if target.company_address:
			target.update(get_fetch_values("Sales Invoice", "company_address", target.company_address))

	def update_item(source_doc, target_doc, source_parent):
		target_doc.qty = to_make_invoice_qty_map[source_doc.name]

	def get_pending_qty(item_row):
		pending_qty = item_row.qty - invoiced_qty_map.get(item_row.name, 0)

		returned_qty = 0
		if returned_qty_map.get(item_row.name, 0) > 0:
			returned_qty = flt(returned_qty_map.get(item_row.name, 0))
			returned_qty_map[item_row.name] -= pending_qty

		if returned_qty:
			if returned_qty >= pending_qty:
				pending_qty = 0
				returned_qty -= pending_qty
			else:
				pending_qty -= returned_qty
				returned_qty = 0

		to_make_invoice_qty_map[item_row.name] = pending_qty

		return pending_qty

	doc = get_mapped_doc(
		"Delivery Note",
		source_name,
		{
			"Delivery Note": {
				"doctype": "Sales Invoice",
				"field_map": {"is_return": "is_return"},
				"validation": {"docstatus": ["=", 1]},
			},
			"Delivery Note Item": {
				"doctype": "Sales Invoice Item",
				"field_map": {
					"name": "dn_detail",
					"parent": "delivery_note",
					"so_detail": "so_detail",
					"against_sales_order": "sales_order",
					"cost_center": "cost_center",
					"diamond_grade":"diamond_grade"
				},
				"postprocess": update_item,
				"filter": lambda d: get_pending_qty(d) <= 0
				if not doc.get("is_return")
				else get_pending_qty(d) > 0,
			},
			"Sales Taxes and Charges": {
				"doctype": "Sales Taxes and Charges",
				"reset_value": not (args and args.get("merge_taxes")),
				"ignore": args.get("merge_taxes") if args else 0,
			},
			"Sales Team": {
				"doctype": "Sales Team",
				"field_map": {"incentives": "incentives"},
				"add_if_empty": True,
			},
		},
		target_doc,
		set_missing_values,
	)

	automatically_fetch_payment_terms = cint(
		frappe.db.get_single_value("Accounts Settings", "automatically_fetch_payment_terms")
	)
	if automatically_fetch_payment_terms and not doc.is_return:
		doc.set_payment_schedule()

	return doc

def get_returned_qty_map(delivery_note):
	"""returns a map: {so_detail: returned_qty}"""
	returned_qty_map = frappe._dict(
		frappe.db.sql(
			"""select dn_item.dn_detail, abs(dn_item.qty) as qty
		from `tabDelivery Note Item` dn_item, `tabDelivery Note` dn
		where dn.name = dn_item.parent
			and dn.docstatus = 1
			and dn.is_return = 1
			and dn.return_against = %s
	""",
			delivery_note,
		)
	)

	return returned_qty_map

def get_invoiced_qty_map(delivery_note):
	"""returns a map: {dn_detail: invoiced_qty}"""
	invoiced_qty_map = {}

	for dn_detail, qty in frappe.db.sql(
		"""select dn_detail, qty from `tabSales Invoice Item`
		where delivery_note=%s and docstatus=1""",
		delivery_note,
	):
		if not invoiced_qty_map.get(dn_detail):
			invoiced_qty_map[dn_detail] = 0
		invoiced_qty_map[dn_detail] += qty

	return invoiced_qty_map


