# # from frappe import _


# def get_data():
# 	return {
# 		"fieldname": "order",
# # 		"non_standard_fieldnames": {
# # 			"Journal Entry": "reference_name",
# # 			"Payment Entry": "reference_name",
# # 			"Payment Request": "reference_name",
# # 			"Landed Cost Voucher": "receipt_document",
# # 			"Purchase Invoice": "return_against",
# # 			"Auto Repeat": "reference_document",
# # 		},
# 		"internal_links": {
# 			"Order Form": ["order_details", "order"],
# 		},
# # 		"transactions": [
# # 			{"label": _("Payment"), "items": ["Payment Entry", "Payment Request", "Journal Entry"]},
# # 			{
# # 				"label": _("Reference"),
# # 				"items": ["Purchase Order", "Purchase Receipt", "Asset", "Landed Cost Voucher"],
# # 			},
# # 			{"label": _("Returns"), "items": ["Purchase Invoice"]},
# # 			{"label": _("Subscription"), "items": ["Auto Repeat"]},
# # 		],
# 	}
