# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt

from gke_customization.gke_catalog.report.accounts_receivable___sd.accounts_receivable___sd import (
	ReceivablePayableReport,
)


def execute(filters=None):
	args = {
		"account_type": "Payable",
		"naming_by": ["Buying Settings", "supp_master_name"],
	}
	return ReceivablePayableReport(filters).run(args)
