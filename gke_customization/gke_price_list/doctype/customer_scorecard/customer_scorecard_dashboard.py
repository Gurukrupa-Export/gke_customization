from frappe import _


# def get_data():
# 	return {
# 		"heatmap": True,
# 		"heatmap_message": _("This covers all scorecards tied to this Setup"),
# 		"fieldname": "customer",
# 		"method": "erpnext.buying.doctype.supplier_scorecard.supplier_scorecard.get_timeline_data",
# 		"transactions": [{"label": _("Scorecards"), "items": ["Supplier Scorecard Period"]}],
# 	}

def get_data():
	return {
		"heatmap": True,
		"heatmap_message": _("This covers all scorecards tied to this Setup"),
		"fieldname": "customer",
		"method": "gke_customization.gke_price_list.doctype.customer_scorecard.customer_scorecard.get_timeline_data",
		"transactions": [{"label": _("Scorecards"), "items": ["Customer Scorecard Period"]}],
	}