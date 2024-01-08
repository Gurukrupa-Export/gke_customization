from . import __version__ as app_version

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
# doctype_js = {"doctype" : "public/js/doctype.js"}
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
# has_permission = {
#	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
#	"ToDo": "custom_app.overrides.CustomToDo"
# }

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
#	"all": [
#		"gke_customization.tasks.all"
#	],
#	"daily": [
#		"gke_customization.tasks.daily"
#	],
#	"hourly": [
#		"gke_customization.tasks.hourly"
#	],
#	"weekly": [
#		"gke_customization.tasks.weekly"
#	],
#	"monthly": [
#		"gke_customization.tasks.monthly"
#	],
# }

# Testing
# -------

# before_tests = "gke_customization.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#	"frappe.desk.doctype.event.event.get_events": "gke_customization.event.get_events"
# }
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


app_include_js = "gke_customization.gke_catalog.api.item_catalog.merge_data"

app_include_js = "gke_customization.gke_catalog.api.item_catalog.get_attribute_values()"
app_include_js = "gke_customization.gke_catalog.api.item_catalog.update_xyz"

app_include_js = "gke_customization.gke_catalog.api.reposne.get_submited_data"

doc_events = {
"SolitaireCalculator": {
    "validate": "gke_customization.gke_custom_export.doctype.solitaire_calculator.solitaire_calculator.calculate_rate"
}
}
app_include_js = [
    '/assets/gke_customization/js/solitaire_calculator.js'
]

fixtures = [
    {
		"dt": "Custom Field", 
		"filters": [["module", "=", "GKE Order Forms"]]
	},
]