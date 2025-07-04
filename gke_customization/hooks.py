from . import __version__ as app_version
import gke_customization.overrides
app_name = "gke_customization"
app_title = "Gke Customization"
app_publisher = "Gurukrupa Export"
app_description = "App made for gurukrupa\'s internal development team"
app_email = "vishal@gurukrupaexport.in"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/gke_customization/css/gke_customization.css"
# app_include_js = "/assets/gke_customization/js/gke_customization.js"

# include js, css files in header of web template
# web_include_css = "/assets/gke_customization/css/gke_customization.css"
# web_include_js = "/assets/gke_customization/js/gke_customization.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "gke_customization/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Quotation" : "public/js/doctype_js/quotation.js",
    "Employee Onboarding" : "public/js/doctype_js/employee_onboarding.js",
    "Payment Entry" : "public/js/doctype_js/payment_entry.js",
    "Stock Entry" : "public/js/doctype_js/stock_entry.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
#	"methods": "gke_customization.utils.jinja_methods",
#	"filters": "gke_customization.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "gke_customization.install.before_install"
# after_install = "gke_customization.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "gke_customization.uninstall.before_uninstall"
# after_uninstall = "gke_customization.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "gke_customization.utils.before_app_install"
# after_app_install = "gke_customization.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "gke_customization.utils.before_app_uninstall"
# after_app_uninstall = "gke_customization.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "gke_customization.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
has_permission = {
	"Task": "gke_customization.gke_order_forms.doc_events.task.has_permission",
}

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	"Employee Incentive": "gke_customization.overrides.employee_incentive.CustomEmployeeIncentive",
	"Employee Checkin": "gke_customization.overrides.employee_checkin.CustomEmployeeCheckin",
    # "Parent Manufacturing Order": "gke_customization.overrides.parent_manufacturing_order.CustomParentManufacturingOrder"
}

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"Batch": {
# 		"validate": "gke_customization.gke_catalog.doc_events.qr_code.validate",
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {

# 	"all": [
# 		"gke_customization.gke_customization.gke_hrms.doc_events.user.test_uesr"
# 	],
# }

scheduler_events = {
    "daily": [
        "gke_customization.gke_hrms.utils.check",
        "gke_customization.gke_hrms.doc_events.leave_allocation.get_earned_leave_allocation",
        "gke_customization.gke_hrms.doc_events.leave_allocation.infirmary_leave_allocation",
        "gke_customization.gke_hrms.doc_events.leave_allocation.compOff_leave_allocation"    
    ],

}

# Testing
# -------

# before_tests = "gke_customization.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
	"hrms.hr.doctype.job_offer.job_offer.make_employee": "gke_customization.gke_hrms.doc_events.job_offer.make_employee",
    "erpnext.selling.doctype.sales_order.sales_order.make_delivery_note":"gke_customization.gke_customization.doc_events.sales_order.make_delivery_note",
    "erpnext.selling.doctype.delivery_note.delivery_note.make_sales_invoice":"gke_customization.gke_customization.doc_events.delivery_note.make_sales_invoice"
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#	"Task": "gke_customization.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["gke_customization.utils.before_request"]
# after_request = ["gke_customization.utils.after_request"]

# Job Events
# ----------
# before_job = ["gke_customization.utils.before_job"]
# after_job = ["gke_customization.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
#	{
#		"doctype": "{doctype_1}",
#		"filter_by": "{filter_by}",
#		"redact_fields": ["{field_1}", "{field_2}"],
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_2}",
#		"filter_by": "{filter_by}",
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_3}",
#		"strict": False,
#	},
#	{
#		"doctype": "{doctype_4}"
#	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
#	"gke_customization.auth.validate"
# ]

app_include_js = "gke_customization.gke_catalog.api.item_list.get_item_list"
app_include_js = "gke_customization.gke_catalog.api.item_list.get_bom_list"

app_include_js = "gke_customization.gke_catalog.api.attendance.attendance" 

app_include_js = "gke_customization.gke_catalog.api.item_catalog.merge_data"

app_include_js = "gke_customization.gke_catalog.api.item_catalog.get_attribute_values()"
app_include_js = "gke_customization.gke_catalog.api.item_catalog.update_xyz"

app_include_js = "gke_customization.gke_catalog.api.reposne.get_submited_data"

app_include_js = "gke_customization.gke_catalog.api.price_list.diamond_price_list"

doc_events = {
"SolitaireCalculator": {
    "validate": "gke_customization.gke_custom_export.doctype.solitaire_calculator.solitaire_calculator.calculate_rate"
},
"Employee Advance": {
	"validate": "gke_customization.gke_hrms.doc_events.employee_advance.calculate_working_days"
},
"Attendance Request": {
	"validate": "gke_customization.gke_hrms.doc_events.attendance_request.validate",
	"on_submit": "gke_customization.gke_hrms.doc_events.attendance_request.on_submit"	
},
"Leave Application":{
    "validate": "gke_customization.gke_hrms.doc_events.leave_application.validate",
    "on_submit": "gke_customization.gke_hrms.doc_events.leave_application.on_submit"
},
"Share Transfer":{
    "validate":"gke_customization.gke_customization.doc_events.share_transfer.validate",
    "on_trash":"gke_customization.gke_customization.doc_events.share_transfer.on_trash",
    "on_cancel":"gke_customization.gke_customization.doc_events.share_transfer.on_cancel",
},
# "Shareholder": {
#     "validate": "gke_customization.gke_order_forms.doc_events.shareholder.validate"
# },
# "Payment Entry": {
#     "on_update_after_submit": "gke_customization.gke_order_forms.doc_events.payment_entry.on_update_after_submit"
# },
"Journal Entry": {
    "on_submit": "gke_customization.gke_order_forms.doc_events.journal_entry.on_submit"
},
# "Item": {
#     "before_validate": "gke_customization.gke_order_forms.doc_events.item.before_validate"
# },
# "Department IR": {
#     "autoname": "gke_customization.gke_order_forms.doc_events.department_ir.autoname"
# },
# "Employee IR": {
#     "autoname": "gke_customization.gke_order_forms.doc_events.employee_ir.autoname"
# },
"Manufacturing Operation": {
    "autoname": "gke_customization.gke_order_forms.doc_events.manufacturing_operation.autoname"
},
"Sales Order":{
    "validate":"gke_customization.gke_customization.doc_events.sales_order.validate",
},
"Sales Invoice":{
    "validate":"gke_customization.gke_customization.doc_events.sales_invoice.validate",
},
"Delivery Note":{
    "validate":"gke_customization.gke_customization.doc_events.delivery_note.validate",
},
"Batch": {
    "autoname": "jewellery_erpnext.jewellery_erpnext.customization.batch.batch.autoname",
},
# "Stock Entry": {
#     "before_validate": "gke_customization.gke_order_forms.doc_events.stock_entry.before_validate",
# }
}
# app_include_js = [
#     '/assets/gke_customization/js/solitaire_calculator.js'
# ]

fixtures = [
    {
		"dt": "Custom Field", 
		"filters": [["module", "in", ["GKE Order Forms", "GKE Catalog"]]]
	},
    {
		"dt": "DocType", 
		"filters": [["module", "in", ["GKE Order Forms", "GKE Catalog"]], ['custom', "=", 1]]
	},
]
