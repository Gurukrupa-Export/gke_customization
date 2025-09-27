# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, throw
from frappe.model.document import Document


class LedgerCreationRequest(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        account: DF.Data | None
        account_name: DF.Data
        account_type: DF.Literal["", "Accumulated Depreciation", "Asset Received But Not Billed", "Bank", "Cash", "Chargeable", "Capital Work in Progress", "Cost of Goods Sold", "Current Asset", "Current Liability", "Depreciation", "Direct Expense", "Direct Income", "Equity", "Expense Account", "Expenses Included In Asset Valuation", "Expenses Included In Valuation", "Fixed Asset", "Income Account", "Indirect Expense", "Indirect Income", "Liability", "Payable", "Receivable", "Round Off", "Round Off for Opening", "Stock", "Stock Adjustment", "Stock Received But Not Billed", "Service Received But Not Billed", "Tax", "Temporary"]
        amended_from: DF.Link | None
        balance_type: DF.Literal["Debit", "Credit"]
        company: DF.Link
        currency: DF.Link
        opening_amount: DF.Data | None
        opening_date: DF.Date | None
        parent_account: DF.Link
        report_type: DF.Literal["Balance Sheet", "Profit And Loss"]
        root_type: DF.Literal["", "Asset", "Liability", "Income", "Expense", "Equity"]
        user_id: DF.Link | None
    # end: auto-generated types
    pass
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	# from typing import TYPE_CHECKING

	# if TYPE_CHECKING:
	# 	from frappe.types import DF

	# 	alias_name: DF.Data | None
	# 	balance_type: DF.Data | None
	# 	company: DF.Link
	# 	cost_center: DF.Data | None
	# 	currency: DF.Link
	# 	descriptionnotes: DF.Data | None
	# 	disable_account: DF.Check
	# 	frozen: DF.Check
	# 	gst_rate: DF.Data | None
	# 	hsn_sac_code: DF.Data | None
	# 	is_group: DF.Check
	# 	ledger_name: DF.Data
	# 	maintain_balance_bill_by_bill: DF.Check
	# 	opening_amount: DF.Data | None
	# 	opening_date: DF.Date | None
	# 	parent_account: DF.Data
	# 	report_type: DF.Literal["Balance Sheet", "Profit And Loss"]
	# 	root_type: DF.Data
	# 	set_opening_balance: DF.Check
	# 	tax_category: DF.Data | None
	# 	tds_rate: DF.Data | None
	# # end: auto-generated types

	# from typing import TYPE_CHECKING

	# if TYPE_CHECKING:
	# 	from frappe.types import DF

	# 	account_type: DF.Literal[
	# 		"",
	# 		"Accumulated Depreciation",
	# 		"Asset Received But Not Billed",
	# 		"Bank",
	# 		"Cash",
	# 		"Chargeable",
	# 		"Capital Work in Progress",
	# 		"Cost of Goods Sold",
	# 		"Current Asset",
	# 		"Current Liability",
	# 		"Depreciation",
	# 		"Direct Expense",
	# 		"Direct Income",
	# 		"Equity",
	# 		"Expense Account",
	# 		"Expenses Included In Asset Valuation",
	# 		"Expenses Included In Valuation",
	# 		"Fixed Asset",
	# 		"Income Account",
	# 		"Indirect Expense",
	# 		"Indirect Income",
	# 		"Liability",
	# 		"Payable",
	# 		"Receivable",
	# 		"Round Off",
	# 		"Round Off for Opening",
	# 		"Stock",
	# 		"Stock Adjustment",
	# 		"Stock Received But Not Billed",
	# 		"Service Received But Not Billed",
	# 		"Tax",
	# 		"Temporary",
	# 	]

	# def validate_parent_child_account_type(self):
	# 	if self.parent_account:
	# 		if self.account_type in [
	# 			"Direct Income",
	# 			"Indirect Income",
	# 			"Current Asset",
	# 			"Current Liability",
	# 			"Direct Expense",
	# 			"Indirect Expense",
	# 		]:
	# 			parent_account_type = frappe.db.get_value("Account", self.parent_account, ["account_type"])
	# 			if parent_account_type == self.account_type:
	# 				throw(_("Only Parent can be of type {0}").format(self.account_type))


	# def validate_parent(self):
	# 	"""Fetch Parent Details and validate parent account"""
	# 	if self.parent_account:
	# 		par = frappe.get_cached_value(
	# 			"Account", self.parent_account, ["name", "is_group", "company"], as_dict=1
	# 		)
	# 		if not par:
	# 			throw(
	# 				_("Account {0}: Parent account {1} does not exist").format(self.name, self.parent_account)
	# 			)
	# 		elif par.name == self.name:
	# 			throw(_("Account {0}: You can not assign itself as parent account").format(self.name))
	# 		elif not par.is_group:
	# 			throw(
	# 				_("Account {0}: Parent account {1} can not be a ledger").format(
	# 					self.name, self.parent_account
	# 				)
	# 			)
	# 		elif par.company != self.company:
	# 			throw(
	# 				_("Account {0}: Parent account {1} does not belong to company: {2}").format(
	# 					self.name, self.parent_account, self.company
	# 				)
	# 			)
    
def get_parent_account(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql(
		"""select name from tabAccount
		where is_group = 1 and docstatus != 2 and company = {}
		and {} like {} order by name limit {} offset {}""".format("%s", searchfield, "%s", "%s", "%s"),
		(filters["company"], "%%%s%%" % txt, page_len, start),
		as_list=1,
	)