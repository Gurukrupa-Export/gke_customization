
# import frappe
# import json

# from frappe.utils import data


# # ─────────────────────────────────────────────────────────────────────────────
# #  FILE PATH : gke_customization/gke_catalog/api/send_catalogue_mail.py
# #  TEMPLATE  : gke_customization/templates/emails/catalogue_mail.html
# # ─────────────────────────────────────────────────────────────────────────────


# def get_wishlist_items(customer):
#     """
#     Direct SQL se customer ki wishlist=1 wali items fetch .
#     """
#     # if not data:
#     #     return []
    
#     return  frappe.db.sql("""
#         SELECT
#             citm.item_code,
#             citm.item_name,
#             citm.wishlist,
#             citm.trending,
#             citm.folder,
#             item.item_category,
#             item.item_subcategory,
#             item.image,
#             item.sketch_image,
#             item.front_view                                     AS cad_image,
#             item.setting_type,
#             item.stylebio,
#             item.variant_of,
#             bom.tag_no,
#             bom.diamond_quality,
#             bom.metal_purity,
#             bom.metal_touch                                     AS bom_touch,
#             bom.metal_colour,
#             bom.navratna,
#             bom.height,
#             bom.length,
#             bom.width,
#             bom.product_size,
#             bom.sizer_type,
#             bom.design_style,
#             bom.detachable,
#             bom.total_diamond_pcs,
#             bom.total_gemstone_pcs,
#             bom.finding_pcs,
#             FORMAT(bom.gross_weight, 3)                         AS gross_metal_weight,
#             FORMAT(bom.metal_and_finding_weight, 3)             AS net_metal_finding_weight,
#             FORMAT(bom.total_diamond_weight_in_gms, 3)          AS total_diamond_weight_in_gms,
#             FORMAT(bom.total_gemstone_weight_in_gms, 3)         AS total_gemstone_weight_in_gms,
#             FORMAT(bom.gemstone_weight, 3)                      AS gemstone_weight,
#             FORMAT(bom.other_weight, 3)                         AS other_weight,
#             FORMAT(bom.finding_weight_, 3)                      AS finding_weight_,
#             FORMAT(bom.gold_to_diamond_ratio, 3)                AS gold_diamond_ratio,
#             FORMAT(bom.diamond_ratio, 3)                        AS diamond_ratio,
#             FORMAT(bom.metal_to_diamond_ratio_excl_of_finding, 3) AS metal_diamond_ratio,
#             GROUP_CONCAT(DISTINCT mt.metal_type)                AS metal_types,
#             GROUP_CONCAT(DISTINCT mt.metal_colour)              AS metal_color,
#             GROUP_CONCAT(DISTINCT mt.metal_touch)               AS metal_touch,
#             GROUP_CONCAT(DISTINCT mt.metal_purity)              AS metal_purities,
#             GROUP_CONCAT(DISTINCT dd.stone_shape)               AS diamond_stone_shape,
#             GROUP_CONCAT(DISTINCT dd.sub_setting_type)          AS diamond_setting_type,
#             GROUP_CONCAT(DISTINCT dd.diamond_sieve_size)        AS diamond_sieve_size,
#             GROUP_CONCAT(DISTINCT dd.sieve_size_range)          AS sieve_size_range,
#             GROUP_CONCAT(DISTINCT gd.stone_shape)               AS gemstone_shape,
#             GROUP_CONCAT(DISTINCT gd.cut_or_cab)                AS cut_or_cab,
#             GROUP_CONCAT(DISTINCT fd.finding_type)              AS finding_sub_category,
#             GROUP_CONCAT(DISTINCT fd.finding_category)          AS finding_category
#         FROM `tabCataloge Master`       AS ctm
#         JOIN `tabCataloge Item Details` AS citm ON citm.parent    = ctm.name
#         JOIN `tabItem`                  AS item ON item.name       = citm.item_code
#         LEFT JOIN `tabBOM`              AS bom  ON bom.item        = item.item_code
#                                                AND bom.bom_type    = 'Finish Goods'
#                                                AND bom.is_active   = 1
#         LEFT JOIN `tabBOM Metal Detail`   AS mt ON mt.parent       = bom.name
#         LEFT JOIN `tabBOM Diamond Detail` AS dd ON dd.parent       = bom.name
#         LEFT JOIN `tabBOM Gemstone Detail` AS gd ON gd.parent      = bom.name
#         LEFT JOIN `tabBOM Finding Detail`  AS fd ON fd.parent      = bom.name
#         WHERE
#             ctm.customer  = %(customer)s
#             AND citm.wishlist = 1
#         GROUP BY
#             citm.item_code
#     """, {"customer": customer}, as_dict=True)
    
#     # if not data:
#     #     frappe.throw("No Wishlist Item")


# def get_catalogue_items(customer, selectedSubcategory=None, metalType=None):
#     """
#     Direct Fetching customer from SQL all  catalogue items fetch  (wishlist fallback).
#     """
#     where_clause = "ctm.customer = %(customer)s AND bom.bom_type = 'Finish Goods' AND bom.is_active = 1"

#     if selectedSubcategory:
#         where_clause += f" AND item.item_subcategory = '{selectedSubcategory}'"

#     if metalType:
#         where_clause += f" AND bom.metal_type = '{metalType}'"

#     return frappe.db.sql(f"""
#         SELECT
#             citm.item_code,
#             citm.item_name,
#             citm.wishlist,
#             citm.trending,
#             citm.folder,
#             item.item_category,
#             item.item_subcategory,
#             item.image,
#             item.sketch_image,
#             item.front_view                                     AS cad_image,
#             item.setting_type,
#             item.stylebio,
#             item.variant_of,
#             bom.tag_no,
#             bom.diamond_quality,
#             bom.metal_purity,
#             bom.metal_touch                                     AS bom_touch,
#             bom.metal_colour,
#             bom.navratna,
#             bom.height,
#             bom.length,
#             bom.width,
#             bom.product_size,
#             bom.sizer_type,
#             bom.design_style,
#             bom.detachable,
#             bom.total_diamond_pcs,
#             bom.total_gemstone_pcs,
#             bom.finding_pcs,
#             FORMAT(bom.gross_weight, 3)                         AS gross_metal_weight,
#             FORMAT(bom.metal_and_finding_weight, 3)             AS net_metal_finding_weight,
#             FORMAT(bom.total_diamond_weight_in_gms, 3)          AS total_diamond_weight_in_gms,
#             FORMAT(bom.total_gemstone_weight_in_gms, 3)         AS total_gemstone_weight_in_gms,
#             FORMAT(bom.gemstone_weight, 3)                      AS gemstone_weight,
#             FORMAT(bom.other_weight, 3)                         AS other_weight,
#             FORMAT(bom.finding_weight_, 3)                      AS finding_weight_,
#             FORMAT(bom.gold_to_diamond_ratio, 3)                AS gold_diamond_ratio,
#             FORMAT(bom.diamond_ratio, 3)                        AS diamond_ratio,
#             FORMAT(bom.metal_to_diamond_ratio_excl_of_finding, 3) AS metal_diamond_ratio,
#             GROUP_CONCAT(DISTINCT mt.metal_type)                AS metal_types,
#             GROUP_CONCAT(DISTINCT mt.metal_colour)              AS metal_color,
#             GROUP_CONCAT(DISTINCT mt.metal_touch)               AS metal_touch,
#             GROUP_CONCAT(DISTINCT mt.metal_purity)              AS metal_purities,
#             GROUP_CONCAT(DISTINCT dd.stone_shape)               AS diamond_stone_shape,
#             GROUP_CONCAT(DISTINCT dd.sub_setting_type)          AS diamond_setting_type,
#             GROUP_CONCAT(DISTINCT dd.diamond_sieve_size)        AS diamond_sieve_size,
#             GROUP_CONCAT(DISTINCT dd.sieve_size_range)          AS sieve_size_range,
#             GROUP_CONCAT(DISTINCT gd.stone_shape)               AS gemstone_shape,
#             GROUP_CONCAT(DISTINCT gd.cut_or_cab)                AS cut_or_cab,
#             GROUP_CONCAT(DISTINCT fd.finding_type)              AS finding_sub_category,
#             GROUP_CONCAT(DISTINCT fd.finding_category)          AS finding_category
#         FROM `tabCataloge Master`         AS ctm
#         JOIN `tabCataloge Item Details`   AS citm ON citm.parent  = ctm.name
#         JOIN `tabItem`                    AS item ON item.name     = citm.item_code
#         LEFT JOIN `tabBOM`                AS bom  ON bom.item      = item.item_code
#                                                  AND bom.bom_type  = 'Finish Goods'
#                                                  AND bom.is_active = 1
#         LEFT JOIN `tabBOM Metal Detail`   AS mt ON mt.parent       = bom.name
#         LEFT JOIN `tabBOM Diamond Detail` AS dd ON dd.parent       = bom.name
#         LEFT JOIN `tabBOM Gemstone Detail` AS gd ON gd.parent      = bom.name
#         LEFT JOIN `tabBOM Finding Detail`  AS fd ON fd.parent      = bom.name
#         WHERE
#             {where_clause}
#         GROUP BY
#             citm.item_code
#         ORDER BY
#             item.name DESC
#     """, {"customer": customer}, as_dict=True)


# @frappe.whitelist(allow_guest=True)
# def send_catalogue_mail(customer, recipient_email=None, selectedSubcategory=None, metalType=None):
#     """
#     Send catalogue email to customer.

#     Logic:
#       1. Wishlist SQL  → citm.wishlist = 1 data hai?  → Wishlist mail send
#       2. Else         → Catalogue SQL fallback        → Catalogue mail send
#       3. Both empty    → early return, no email
#     """

#     if not customer:
#         frappe.throw("Customer is required.")

#     # ── 1. Recipient email resolve ────────────────────────────────────────────
#     # if not recipient_email:
#     name = frappe.db.get_value(
#         "Customer",
#         {"email_id": customer},
#         "name"
#     )

#     if not name:
#         frappe.throw(f"No email address found for customer '{name}'.")

#     # ── 2. Wishlist items fetch karo ──────────────────────────────────────────
#     wishlist_items = get_wishlist_items(name)

#     if wishlist_items:
#         # ✅ Wishlist mein data hai → wishlist bhejo
#         items_to_send = wishlist_items
#         source_label  = "Wishlist Items"

#     else:
#         # ⬇️ Wishlist empty → catalogue fallback
#         items_to_send = get_catalogue_items(
#             customer           = name,
#             selectedSubcategory = selectedSubcategory,
#             metalType          = metalType
#         )

#         if not items_to_send:
#             return {
#                 "status" : "no_data",
#                 "message": f"No items found for customer '{customer}' in wishlist or catalogue."
#             }

#         source_label = "Catalogue Items"

#     # ── 3. Customer display name ──────────────────────────────────────────────
#     customer_name = (
#         frappe.db.get_value("Customer", customer, "customer_name") or customer
#     )

#     # ── 4. Summary counts for template ───────────────────────────────────────
#     total_items    = len(items_to_send)
#     wishlist_count = sum(1 for i in items_to_send if i.get("wishlist") == 1)
#     trending_count = sum(1 for i in items_to_send if i.get("trending") == 1)

#     # ── 5. Jinja template render karo ────────────────────────────────────────
#     html_body = frappe.render_template(
#         "gke_customization/templates/emails/catalogue_mail.html",
#         {
#             "customer_name" : customer_name,
#             "source_label"  : source_label,
#             "items"         : items_to_send,
#             "total_items"   : total_items,
#             "wishlist_count": wishlist_count,
#             "trending_count": trending_count,
#         }
#     )

#     # ── 6. Email  ────────────────────────────────────────────────────────
#     frappe.sendmail(
#         sender = "shubham_s@gkexport.com",
#         recipients = [customer],
#         subject    = f"Your Catalogue Items – {customer_name}",
#         message    = html_body,
#         now        = True
#     )

#     # frappe.logger().info(
#     #     f"[send_catalogue_mail] {total_items} '{source_label}' "
#     #     f"sent to {customer} for customer '{name}'"
#     # )

#     return {
#         "status"     : "success",
#         "source"     : source_label,
#         "items_sent" : total_items,
#         "recipient"  : customer,
#         "message"    : f"Email sent to {customer} with {total_items} items ({source_label})."
#     }























# import frappe
# import json


# # ─────────────────────────────────────────────────────────────────────────────
# #  FILE PATH : gke_customization/gke_catalog/api/send_catalogue_mail.py
# #  TEMPLATE  : gke_customization/templates/emails/catalogue_mail.html
# # ─────────────────────────────────────────────────────────────────────────────


# def get_wishlist_items(customer_id):
#     """
#     Customer ki wishlist=1 wali items SQL se fetch karo.
#     """
#     return frappe.db.sql("""
#         SELECT
#             citm.item_code,
#             citm.item_name,
#             citm.wishlist,
#             citm.trending,
#             citm.folder,
#             item.item_category,
#             item.item_subcategory,
#             item.image,
#             item.sketch_image,
#             item.front_view                                       AS cad_image,
#             item.setting_type,
#             item.stylebio,
#             item.variant_of,
#             bom.tag_no,
#             bom.diamond_quality,
#             bom.metal_purity,
#             bom.metal_touch                                       AS bom_touch,
#             bom.metal_colour,
#             bom.navratna,
#             bom.height,
#             bom.length,
#             bom.width,
#             bom.product_size,
#             bom.sizer_type,
#             bom.design_style,
#             bom.detachable,
#             bom.total_diamond_pcs,
#             bom.total_gemstone_pcs,
#             bom.finding_pcs,
#             FORMAT(bom.gross_weight, 3)                           AS gross_metal_weight,
#             FORMAT(bom.metal_and_finding_weight, 3)               AS net_metal_finding_weight,
#             FORMAT(bom.total_diamond_weight_in_gms, 3)            AS total_diamond_weight_in_gms,
#             FORMAT(bom.total_gemstone_weight_in_gms, 3)           AS total_gemstone_weight_in_gms,
#             FORMAT(bom.gemstone_weight, 3)                        AS gemstone_weight,
#             FORMAT(bom.other_weight, 3)                           AS other_weight,
#             FORMAT(bom.finding_weight_, 3)                        AS finding_weight_,
#             FORMAT(bom.gold_to_diamond_ratio, 3)                  AS gold_diamond_ratio,
#             FORMAT(bom.diamond_ratio, 3)                          AS diamond_ratio,
#             FORMAT(bom.metal_to_diamond_ratio_excl_of_finding, 3) AS metal_diamond_ratio,
#             GROUP_CONCAT(DISTINCT mt.metal_type)                  AS metal_types,
#             GROUP_CONCAT(DISTINCT mt.metal_colour)                AS metal_color,
#             GROUP_CONCAT(DISTINCT mt.metal_touch)                 AS metal_touch,
#             GROUP_CONCAT(DISTINCT mt.metal_purity)                AS metal_purities,
#             GROUP_CONCAT(DISTINCT dd.stone_shape)                 AS diamond_stone_shape,
#             GROUP_CONCAT(DISTINCT dd.sub_setting_type)            AS diamond_setting_type,
#             GROUP_CONCAT(DISTINCT dd.diamond_sieve_size)          AS diamond_sieve_size,
#             GROUP_CONCAT(DISTINCT dd.sieve_size_range)            AS sieve_size_range,
#             GROUP_CONCAT(DISTINCT gd.stone_shape)                 AS gemstone_shape,
#             GROUP_CONCAT(DISTINCT gd.cut_or_cab)                  AS cut_or_cab,
#             GROUP_CONCAT(DISTINCT fd.finding_type)                AS finding_sub_category,
#             GROUP_CONCAT(DISTINCT fd.finding_category)            AS finding_category
#         FROM `tabCataloge Master`          AS ctm
#         JOIN `tabCataloge Item Details`    AS citm ON citm.parent  = ctm.name
#         JOIN `tabItem`                     AS item ON item.name     = citm.item_code
#         LEFT JOIN `tabBOM`                 AS bom  ON bom.item      = item.item_code
#                                                   AND bom.bom_type  = 'Finish Goods'
#                                                   AND bom.is_active = 1
#         LEFT JOIN `tabBOM Metal Detail`    AS mt   ON mt.parent     = bom.name
#         LEFT JOIN `tabBOM Diamond Detail`  AS dd   ON dd.parent     = bom.name
#         LEFT JOIN `tabBOM Gemstone Detail` AS gd   ON gd.parent     = bom.name
#         LEFT JOIN `tabBOM Finding Detail`  AS fd   ON fd.parent     = bom.name
#         WHERE
#             ctm.customer    = %(customer_id)s
#             AND citm.wishlist = 1
#         GROUP BY
#             citm.item_code
#     """, {"customer_id": customer_id}, as_dict=True)


# def get_catalogue_items(customer_id, selectedSubcategory=None, metalType=None):
#     """
#     Customer ke saare catalogue items SQL se fetch karo (fallback).
#     """
#     where_clause = (
#         "ctm.customer = %(customer_id)s "
#         "AND bom.bom_type = 'Finish Goods' "
#         "AND bom.is_active = 1"
#     )

#     if selectedSubcategory:
#         where_clause += f" AND item.item_subcategory = '{selectedSubcategory}'"
#     if metalType:
#         where_clause += f" AND bom.metal_type = '{metalType}'"

#     return frappe.db.sql(f"""
#         SELECT
#             citm.item_code,
#             citm.item_name,
#             citm.wishlist,
#             citm.trending,
#             citm.folder,
#             item.item_category,
#             item.item_subcategory,
#             item.image,
#             item.sketch_image,
#             item.front_view                                       AS cad_image,
#             item.setting_type,
#             item.stylebio,
#             item.variant_of,
#             bom.tag_no,
#             bom.diamond_quality,
#             bom.metal_purity,
#             bom.metal_touch                                       AS bom_touch,
#             bom.metal_colour,
#             bom.navratna,
#             bom.height,
#             bom.length,
#             bom.width,
#             bom.product_size,
#             bom.sizer_type,
#             bom.design_style,
#             bom.detachable,
#             bom.total_diamond_pcs,
#             bom.total_gemstone_pcs,
#             bom.finding_pcs,
#             FORMAT(bom.gross_weight, 3)                           AS gross_metal_weight,
#             FORMAT(bom.metal_and_finding_weight, 3)               AS net_metal_finding_weight,
#             FORMAT(bom.total_diamond_weight_in_gms, 3)            AS total_diamond_weight_in_gms,
#             FORMAT(bom.total_gemstone_weight_in_gms, 3)           AS total_gemstone_weight_in_gms,
#             FORMAT(bom.gemstone_weight, 3)                        AS gemstone_weight,
#             FORMAT(bom.other_weight, 3)                           AS other_weight,
#             FORMAT(bom.finding_weight_, 3)                        AS finding_weight_,
#             FORMAT(bom.gold_to_diamond_ratio, 3)                  AS gold_diamond_ratio,
#             FORMAT(bom.diamond_ratio, 3)                          AS diamond_ratio,
#             FORMAT(bom.metal_to_diamond_ratio_excl_of_finding, 3) AS metal_diamond_ratio,
#             GROUP_CONCAT(DISTINCT mt.metal_type)                  AS metal_types,
#             GROUP_CONCAT(DISTINCT mt.metal_colour)                AS metal_color,
#             GROUP_CONCAT(DISTINCT mt.metal_touch)                 AS metal_touch,
#             GROUP_CONCAT(DISTINCT mt.metal_purity)                AS metal_purities,
#             GROUP_CONCAT(DISTINCT dd.stone_shape)                 AS diamond_stone_shape,
#             GROUP_CONCAT(DISTINCT dd.sub_setting_type)            AS diamond_setting_type,
#             GROUP_CONCAT(DISTINCT dd.diamond_sieve_size)          AS diamond_sieve_size,
#             GROUP_CONCAT(DISTINCT dd.sieve_size_range)            AS sieve_size_range,
#             GROUP_CONCAT(DISTINCT gd.stone_shape)                 AS gemstone_shape,
#             GROUP_CONCAT(DISTINCT gd.cut_or_cab)                  AS cut_or_cab,
#             GROUP_CONCAT(DISTINCT fd.finding_type)                AS finding_sub_category,
#             GROUP_CONCAT(DISTINCT fd.finding_category)            AS finding_category
#         FROM `tabCataloge Master`          AS ctm
#         JOIN `tabCataloge Item Details`    AS citm ON citm.parent  = ctm.name
#         JOIN `tabItem`                     AS item ON item.name     = citm.item_code
#         LEFT JOIN `tabBOM`                 AS bom  ON bom.item      = item.item_code
#                                                   AND bom.bom_type  = 'Finish Goods'
#                                                   AND bom.is_active = 1
#         LEFT JOIN `tabBOM Metal Detail`    AS mt   ON mt.parent     = bom.name
#         LEFT JOIN `tabBOM Diamond Detail`  AS dd   ON dd.parent     = bom.name
#         LEFT JOIN `tabBOM Gemstone Detail` AS gd   ON gd.parent     = bom.name
#         LEFT JOIN `tabBOM Finding Detail`  AS fd   ON fd.parent     = bom.name
#         WHERE
#             {where_clause}
#         GROUP BY
#             citm.item_code
#         ORDER BY
#             item.name DESC
#     """, {"customer_id": customer_id}, as_dict=True)


# def resolve_customer_by_email(recipient_email):
#     """
#     Sirf email se Customer record dhundho.
#     Pehle email_id field check karo, warna User → Customer link try karo.
#     Returns: { name, customer_name, email_id } or None
#     """

#     # ── Try 1: Customer.email_id field ───────────────────────────────────────
#     customer = frappe.db.get_value(
#         "Customer",
#         {"email_id": recipient_email},
#         ["name", "customer_name", "email_id"],
#         as_dict=True
#     )
#     if customer:
#         return customer

#     # ── Try 2: Customer.name = email (kuch cases mein name hi email hota hai) ─
#     customer = frappe.db.get_value(
#         "Customer",
#         {"name": recipient_email},
#         ["name", "customer_name", "email_id"],
#         as_dict=True
#     )
#     if customer:
#         # email_id field empty ho sakta hai, override karo
#         customer["email_id"] = recipient_email
#         return customer

#     # ── Try 3: Portal User link (tabContact / tabDynamic Link) ───────────────
#     linked = frappe.db.sql("""
#         SELECT dl.link_name AS name
#         FROM `tabContact`      AS c
#         JOIN `tabContact Email` AS ce ON ce.parent = c.name
#         JOIN `tabDynamic Link`  AS dl ON dl.parent = c.name
#                                      AND dl.link_doctype = 'Customer'
#         WHERE ce.email_id = %(email)s
#         LIMIT 1
#     """, {"email": recipient_email}, as_dict=True)

#     if linked:
#         cname = linked[0]["name"]
#         customer = frappe.db.get_value(
#             "Customer",
#             cname,
#             ["name", "customer_name", "email_id"],
#             as_dict=True
#         )
#         if customer:
#             customer["email_id"] = customer["email_id"] or recipient_email
#             return customer

#     return None


# @frappe.whitelist()
# def send_mail_by_email(
#     recipient_email,
#     selectedSubcategory=None,
#     metalType=None
# ):
#     """
#     Sales person sirf recipient_email daale — baaki sab automatic.

#     Flow:
#       1. Email se Customer dhundho
#       2. Wishlist data check karo
#          → data hai  → Wishlist mail bhejo
#          → empty     → Catalogue data bhejo
#       3. Sender = logged-in sales person ka email (frappe.session.user)
#     """

#     # ── 1. Basic validation ───────────────────────────────────────────────────
#     if not recipient_email:
#         frappe.throw("Recipient email is required.")

#     # ── 2. Logged-in user = sender ────────────────────────────────────────────
#     logged_in_user = frappe.session.user
#     if not logged_in_user or logged_in_user == "Guest":
#         frappe.throw("You must be logged in to send emails.")

#     sender_full_name = (
#         frappe.db.get_value("User", logged_in_user, "full_name") or logged_in_user
#     )

#     # ── 3. Email se Customer resolve karo ────────────────────────────────────
#     customer_doc = resolve_customer_by_email(recipient_email)

#     if not customer_doc:
#         frappe.throw(
#             f"No Customer found with email '{recipient_email}'. "
#             "Please check the email address."
#         )

#     customer_id   = customer_doc["name"]
#     customer_name = customer_doc["customer_name"] or customer_id

#     # ── 4. Wishlist items try karo ────────────────────────────────────────────
#     wishlist_items = get_wishlist_items(customer_id)

#     if wishlist_items:
#         items_to_send = wishlist_items
#         source_label  = "Wishlist Items"
#     else:
#         # ── 5. Fallback: catalogue items ──────────────────────────────────────
#         items_to_send = get_catalogue_items(
#             customer_id         = customer_id,
#             selectedSubcategory = selectedSubcategory,
#             metalType           = metalType
#         )

#         if not items_to_send:
#             return {
#                 "status" : "no_data",
#                 "message": (
#                     f"No items found for '{customer_name}' "
#                     "in wishlist or catalogue."
#                 )
#             }

#         source_label = "Catalogue Items"

#     # ── 6. Summary counts ─────────────────────────────────────────────────────
#     total_items    = len(items_to_send)
#     wishlist_count = sum(1 for i in items_to_send if i.get("wishlist") == 1)
#     trending_count = sum(1 for i in items_to_send if i.get("trending") == 1)

#     # ── 7. Template render karo ───────────────────────────────────────────────
#     html_body = frappe.render_template(
#         "gke_customization/templates/emails/catalogue_mail.html",
#         {
#             "customer_name" : customer_name,
#             "source_label"  : source_label,
#             "items"         : items_to_send,
#             "total_items"   : total_items,
#             "wishlist_count": wishlist_count,
#             "trending_count": trending_count,
#             "sender_name"   : sender_full_name,
#             "sender_email"  : logged_in_user,
#         }
#     )

#     # ── 8. Email bhejo ────────────────────────────────────────────────────────
#     frappe.sendmail(
#         sender     = logged_in_user,       # ✅ logged-in sales person
#         recipients = [recipient_email],
#         subject    = f"Your Catalogue Items – {customer_name}",
#         message    = html_body,
#         now        = True
#     )

#     frappe.logger().info(
#         f"[send_mail_by_email] {sender_full_name} ({logged_in_user}) → "
#         f"{recipient_email} | {total_items} {source_label}"
#     )

#     return {
#         "status"       : "success",
#         "source"       : source_label,
#         "items_sent"   : total_items,
#         "sender"       : logged_in_user,
#         "recipient"    : recipient_email,
#         "customer_name": customer_name,
#         "message"      : (
#             f"Email sent from {logged_in_user} to {recipient_email} "
#             f"({customer_name}) with {total_items} {source_label}."
#         )
#     }


# # ─────────────────────────────────────────────────────────────────────────────
# #  PURANA FUNCTION — customer param se kaam karta hai (as before)
# # ─────────────────────────────────────────────────────────────────────────────

# @frappe.whitelist()
# def send_catalogue_mail(customer, selectedSubcategory=None, metalType=None):
#     """
#     Customer name/email se mail bhejo (purana flow).
#     """
#     if not customer:
#         frappe.throw("Customer is required.")

#     logged_in_user = frappe.session.user
#     if not logged_in_user or logged_in_user == "Guest":
#         frappe.throw("You must be logged in to send emails.")

#     sender_full_name = (
#         frappe.db.get_value("User", logged_in_user, "full_name") or logged_in_user
#     )

#     # customer email_id se resolve karo
#     customer_doc = resolve_customer_by_email(customer)
#     if not customer_doc:
#         customer_doc = frappe.db.get_value(
#             "Customer", customer,
#             ["name", "customer_name", "email_id"],
#             as_dict=True
#         )

#     if not customer_doc:
#         frappe.throw(f"Customer '{customer}' not found.")

#     customer_id     = customer_doc["name"]
#     customer_name   = customer_doc["customer_name"] or customer_id
#     recipient_email = customer_doc["email_id"] or customer

#     wishlist_items = get_wishlist_items(customer_id)

#     if wishlist_items:
#         items_to_send = wishlist_items
#         source_label  = "Wishlist Items"
#     else:
#         items_to_send = get_catalogue_items(customer_id, selectedSubcategory, metalType)
#         if not items_to_send:
#             return {
#                 "status" : "no_data",
#                 "message": f"No items found for customer '{customer_name}'."
#             }
#         source_label = "Catalogue Items"

#     total_items    = len(items_to_send)
#     wishlist_count = sum(1 for i in items_to_send if i.get("wishlist") == 1)
#     trending_count = sum(1 for i in items_to_send if i.get("trending") == 1)

#     html_body = frappe.render_template(
#         "gke_customization/templates/emails/catalogue_mail.html",
#         {
#             "customer_name" : customer_name,
#             "source_label"  : source_label,
#             "items"         : items_to_send,
#             "total_items"   : total_items,
#             "wishlist_count": wishlist_count,
#             "trending_count": trending_count,
#             "sender_name"   : sender_full_name,
#             "sender_email"  : logged_in_user,
#         }
#     )

#     frappe.sendmail(
#         sender     = logged_in_user,
#         recipients = [recipient_email],
#         subject    = f"Your Catalogue Items – {customer_name}",
#         message    = html_body,
#         now        = True
#     )

#     return {
#         "status"     : "success",
#         "source"     : source_label,
#         "items_sent" : total_items,
#         "sender"     : logged_in_user,
#         "recipient"  : recipient_email,
#         "message"    : (
#             f"Email sent from {logged_in_user} to {recipient_email} "
#             f"with {total_items} items ({source_label})."
#         )
#     }
















# import frappe
# import json


# # ─────────────────────────────────────────────────────────────
# # WISHLIST ITEMS
# # ─────────────────────────────────────────────────────────────
# def get_wishlist_items(customer_id):
#     return frappe.db.sql("""
#         SELECT
#             citm.item_code,
#             citm.item_name,
#             citm.wishlist,
#             citm.trending,
#             item.image
#         FROM `tabCataloge Master` ctm
#         JOIN `tabCataloge Item Details` citm ON citm.parent = ctm.name
#         JOIN `tabItem` item ON item.name = citm.item_code
#         WHERE ctm.customer = %(customer_id)s
#         AND citm.wishlist = 1
#     """, {"customer_id": customer_id}, as_dict=True)


# # ─────────────────────────────────────────────────────────────
# # CATALOGUE ITEMS (IMPORTANT CHANGE)
# # ─────────────────────────────────────────────────────────────
# def get_catalogue_items(customer_id=None, selectedSubcategory=None, metalType=None):

#     conditions = ["bom.bom_type = 'Finish Goods'", "bom.is_active = 1"]
#     values = {}

#     if customer_id:
#         conditions.append("ctm.customer = %(customer_id)s")
#         values["customer_id"] = customer_id

#     if selectedSubcategory:
#         conditions.append("item.item_subcategory = %(subcategory)s")
#         values["subcategory"] = selectedSubcategory

#     if metalType:
#         conditions.append("bom.metal_type = %(metal)s")
#         values["metal"] = metalType

#     where_clause = " AND ".join(conditions)

#     return frappe.db.sql(f"""
#         SELECT
#             citm.item_code,
#             citm.item_name,
#             citm.wishlist,
#             citm.trending,
#             item.image
#         FROM `tabCataloge Master` ctm
#         JOIN `tabCataloge Item Details` citm ON citm.parent = ctm.name
#         JOIN `tabItem` item ON item.name = citm.item_code
#         LEFT JOIN `tabBOM` bom ON bom.item = item.item_code
#         WHERE {where_clause}
#         GROUP BY citm.item_code
#         ORDER BY item.name DESC
#         LIMIT 20
#     """, values, as_dict=True)


# # ─────────────────────────────────────────────────────────────
# # CUSTOMER RESOLVE
# # ─────────────────────────────────────────────────────────────
# def resolve_customer_by_email(recipient_email):

#     customer = frappe.db.get_value(
#         "Customer",
#         {"email_id": recipient_email},
#         ["name", "customer_name", "email_id"],
#         as_dict=True
#     )

#     if customer:
#         return customer

#     return None


# # ─────────────────────────────────────────────────────────────
# # MAIN FUNCTION (FIXED)
# # ─────────────────────────────────────────────────────────────
# @frappe.whitelist()
# def send_catalogue_mail(recipient_email, selectedSubcategory=None, metalType=None):

#     # ✅ Validation
#     if not recipient_email:
#         frappe.throw("Recipient email is required.")

#     logged_in_user = frappe.session.user
#     if not logged_in_user or logged_in_user == "Guest":
#         frappe.throw("Login required.")

#     sender_name = frappe.db.get_value(
#         "User", logged_in_user, "full_name"
#     ) or logged_in_user

#     # ✅ Try to find customer
#     customer_doc = resolve_customer_by_email(recipient_email)

#     # ─────────────────────────────────────────────
#     # 🎯 CASE 1: CUSTOMER EXISTS
#     # ─────────────────────────────────────────────
#     if customer_doc:

#         customer_id = customer_doc["name"]
#         customer_name = customer_doc["customer_name"] or customer_id

#         wishlist_items = get_wishlist_items(customer_id)

#         if wishlist_items:
#             items_to_send = wishlist_items
#             source_label = "Wishlist Items"
#         else:
#             items_to_send = get_catalogue_items(
#                 customer_id=customer_id,
#                 selectedSubcategory=selectedSubcategory,
#                 metalType=metalType
#             )
#             source_label = "Catalogue Items"

#     # ─────────────────────────────────────────────
#     # 🎯 CASE 2: STRANGER (IMPORTANT)
#     # ─────────────────────────────────────────────
#     else:

#         customer_name = "Valued Customer"

#         items_to_send = get_catalogue_items(
#             selectedSubcategory=selectedSubcategory,
#             metalType=metalType
#         )

#         source_label = "General Catalogue"

#     # ✅ Safety check
#     if not items_to_send:
#         return {
#             "status": "no_data",
#             "message": "No items available to send."
#         }

#     # ✅ Counts
#     total_items = len(items_to_send)
#     wishlist_count = sum(1 for i in items_to_send if i.get("wishlist") == 1)
#     trending_count = sum(1 for i in items_to_send if i.get("trending") == 1)

#     # ✅ Email Template
#     html_body = frappe.render_template(
#         "gke_customization/templates/emails/catalogue_mail.html",
#         {
#             "customer_name": customer_name,
#             "source_label": source_label,
#             "items": items_to_send,
#             "total_items": total_items,
#             "wishlist_count": wishlist_count,
#             "trending_count": trending_count,
#             "sender_name": sender_name,
#             "sender_email": logged_in_user,
#         }
#     )

#     # ✅ Send Mail
#     frappe.sendmail(
#         sender=logged_in_user,
#         recipients=[recipient_email],
#         subject=f"Catalogue for You – {customer_name}",
#         message=html_body,
#         now=True
#     )

#     # ✅ Log
#     frappe.logger().info(
#         f"{sender_name} → {recipient_email} | {total_items} {source_label}"
#     )

#     return {
#         "status": "success",
#         "recipient": recipient_email,
#         "items_sent": total_items,
#         "source": source_label,
#         "message": f"Mail sent successfully to {recipient_email}"
#     }












import frappe
import json


# ─────────────────────────────────────────────────────────────
# WISHLIST ITEMS
# ─────────────────────────────────────────────────────────────
def get_wishlist_items(customer_id):
    return frappe.db.sql("""
        SELECT
            citm.item_code,
            citm.item_name,
            citm.wishlist,
            citm.trending,
            citm.folder,
            item.item_category,
            item.item_subcategory,
            item.image,
            item.sketch_image,
            item.front_view                                       AS cad_image,
            item.setting_type,
            item.stylebio,
            item.variant_of,
            bom.tag_no,
            bom.diamond_quality,
            bom.metal_purity,
            bom.metal_touch                                       AS bom_touch,
            bom.metal_colour,
            bom.navratna,
            bom.height,
            bom.length,
            bom.width,
            bom.product_size,
            bom.sizer_type,
            bom.design_style,
            bom.detachable,
            bom.total_diamond_pcs,
            bom.total_gemstone_pcs,
            bom.finding_pcs,
            FORMAT(bom.gross_weight, 3)                           AS gross_metal_weight,
            FORMAT(bom.metal_and_finding_weight, 3)               AS net_metal_finding_weight,
            FORMAT(bom.total_diamond_weight_in_gms, 3)            AS total_diamond_weight_in_gms,
            FORMAT(bom.total_gemstone_weight_in_gms, 3)           AS total_gemstone_weight_in_gms,
            FORMAT(bom.gemstone_weight, 3)                        AS gemstone_weight,
            FORMAT(bom.other_weight, 3)                           AS other_weight,
            FORMAT(bom.finding_weight_, 3)                        AS finding_weight_,
            FORMAT(bom.gold_to_diamond_ratio, 3)                  AS gold_diamond_ratio,
            FORMAT(bom.diamond_ratio, 3)                          AS diamond_ratio,
            FORMAT(bom.metal_to_diamond_ratio_excl_of_finding, 3) AS metal_diamond_ratio,
            GROUP_CONCAT(DISTINCT mt.metal_type)                  AS metal_types,
            GROUP_CONCAT(DISTINCT mt.metal_colour)                AS metal_color,
            GROUP_CONCAT(DISTINCT mt.metal_touch)                 AS metal_touch,
            GROUP_CONCAT(DISTINCT mt.metal_purity)                AS metal_purities,
            GROUP_CONCAT(DISTINCT dd.stone_shape)                 AS diamond_stone_shape,
            GROUP_CONCAT(DISTINCT dd.sub_setting_type)            AS diamond_setting_type,
            GROUP_CONCAT(DISTINCT dd.diamond_sieve_size)          AS diamond_sieve_size,
            GROUP_CONCAT(DISTINCT dd.sieve_size_range)            AS sieve_size_range,
            GROUP_CONCAT(DISTINCT gd.stone_shape)                 AS gemstone_shape,
            GROUP_CONCAT(DISTINCT gd.cut_or_cab)                  AS cut_or_cab,
            GROUP_CONCAT(DISTINCT fd.finding_type)                AS finding_sub_category,
            GROUP_CONCAT(DISTINCT fd.finding_category)            AS finding_category
        FROM `tabCataloge Master`          AS ctm
        JOIN `tabCataloge Item Details`    AS citm ON citm.parent  = ctm.name
        JOIN `tabItem`                     AS item ON item.name     = citm.item_code
        LEFT JOIN `tabBOM`                 AS bom  ON bom.item      = item.item_code
                                                  AND bom.bom_type  = 'Finish Goods'
                                                  AND bom.is_active = 1
        LEFT JOIN `tabBOM Metal Detail`    AS mt   ON mt.parent     = bom.name
        LEFT JOIN `tabBOM Diamond Detail`  AS dd   ON dd.parent     = bom.name
        LEFT JOIN `tabBOM Gemstone Detail` AS gd   ON gd.parent     = bom.name
        LEFT JOIN `tabBOM Finding Detail`  AS fd   ON fd.parent     = bom.name
        WHERE
            ctm.customer      = %(customer_id)s
            AND citm.wishlist = 1
        GROUP BY
            citm.item_code,
            citm.item_name,
            citm.wishlist,
            citm.trending,
            citm.folder,
            item.item_category,
            item.item_subcategory,
            item.image,
            item.sketch_image,
            item.front_view,
            item.setting_type,
            item.stylebio,
            item.variant_of,
            bom.tag_no,
            bom.diamond_quality,
            bom.metal_purity,
            bom.metal_touch,
            bom.metal_colour,
            bom.navratna,
            bom.height,
            bom.length,
            bom.width,
            bom.product_size,
            bom.sizer_type,
            bom.design_style,
            bom.detachable,
            bom.total_diamond_pcs,
            bom.total_gemstone_pcs,
            bom.finding_pcs,
            bom.gross_weight,
            bom.metal_and_finding_weight,
            bom.total_diamond_weight_in_gms,
            bom.total_gemstone_weight_in_gms,
            bom.gemstone_weight,
            bom.other_weight,
            bom.finding_weight_,
            bom.gold_to_diamond_ratio,
            bom.diamond_ratio,
            bom.metal_to_diamond_ratio_excl_of_finding
    """, {"customer_id": customer_id}, as_dict=True)


# ─────────────────────────────────────────────────────────────
# CATALOGUE ITEMS 
# ─────────────────────────────────────────────────────────────
def get_catalogue_items(customer_id=None, selectedSubcategory=None, metalType=None):

    conditions = ["bom.bom_type = 'Finish Goods'", "bom.is_active = 1"]
    values = {}

    if customer_id:
        conditions.append("ctm.customer = %(customer_id)s")
        values["customer_id"] = customer_id

    if selectedSubcategory:
        conditions.append("item.item_subcategory = %(subcategory)s")
        values["subcategory"] = selectedSubcategory

    if metalType:
        conditions.append("bom.metal_type = %(metal)s")
        values["metal"] = metalType

    where_clause = " AND ".join(conditions)

    return frappe.db.sql(f"""
        SELECT
            citm.item_code,
            citm.item_name,
            citm.wishlist,
            citm.trending,
            citm.folder,
            item.item_category,
            item.item_subcategory,
            item.image,
            item.sketch_image,
            item.front_view                                       AS cad_image,
            item.setting_type,
            item.stylebio,
            item.variant_of,
            bom.tag_no,
            bom.diamond_quality,
            bom.metal_purity,
            bom.metal_touch                                       AS bom_touch,
            bom.metal_colour,
            bom.navratna,
            bom.height,
            bom.length,
            bom.width,
            bom.product_size,
            bom.sizer_type,
            bom.design_style,
            bom.detachable,
            bom.total_diamond_pcs,
            bom.total_gemstone_pcs,
            bom.finding_pcs,
            FORMAT(bom.gross_weight, 3)                           AS gross_metal_weight,
            FORMAT(bom.metal_and_finding_weight, 3)               AS net_metal_finding_weight,
            FORMAT(bom.total_diamond_weight_in_gms, 3)            AS total_diamond_weight_in_gms,
            FORMAT(bom.total_gemstone_weight_in_gms, 3)           AS total_gemstone_weight_in_gms,
            FORMAT(bom.gemstone_weight, 3)                        AS gemstone_weight,
            FORMAT(bom.other_weight, 3)                           AS other_weight,
            FORMAT(bom.finding_weight_, 3)                        AS finding_weight_,
            FORMAT(bom.gold_to_diamond_ratio, 3)                  AS gold_diamond_ratio,
            FORMAT(bom.diamond_ratio, 3)                          AS diamond_ratio,
            FORMAT(bom.metal_to_diamond_ratio_excl_of_finding, 3) AS metal_diamond_ratio,
            GROUP_CONCAT(DISTINCT mt.metal_type)                  AS metal_types,
            GROUP_CONCAT(DISTINCT mt.metal_colour)                AS metal_color,
            GROUP_CONCAT(DISTINCT mt.metal_touch)                 AS metal_touch,
            GROUP_CONCAT(DISTINCT mt.metal_purity)                AS metal_purities,
            GROUP_CONCAT(DISTINCT dd.stone_shape)                 AS diamond_stone_shape,
            GROUP_CONCAT(DISTINCT dd.sub_setting_type)            AS diamond_setting_type,
            GROUP_CONCAT(DISTINCT dd.diamond_sieve_size)          AS diamond_sieve_size,
            GROUP_CONCAT(DISTINCT dd.sieve_size_range)            AS sieve_size_range,
            GROUP_CONCAT(DISTINCT gd.stone_shape)                 AS gemstone_shape,
            GROUP_CONCAT(DISTINCT gd.cut_or_cab)                  AS cut_or_cab,
            GROUP_CONCAT(DISTINCT fd.finding_type)                AS finding_sub_category,
            GROUP_CONCAT(DISTINCT fd.finding_category)            AS finding_category
        FROM `tabCataloge Master`          AS ctm
        JOIN `tabCataloge Item Details`    AS citm ON citm.parent  = ctm.name
        JOIN `tabItem`                     AS item ON item.name     = citm.item_code
        LEFT JOIN `tabBOM`                 AS bom  ON bom.item      = item.item_code
                                                  AND bom.bom_type  = 'Finish Goods'
                                                  AND bom.is_active = 1
        LEFT JOIN `tabBOM Metal Detail`    AS mt   ON mt.parent     = bom.name
        LEFT JOIN `tabBOM Diamond Detail`  AS dd   ON dd.parent     = bom.name
        LEFT JOIN `tabBOM Gemstone Detail` AS gd   ON gd.parent     = bom.name
        LEFT JOIN `tabBOM Finding Detail`  AS fd   ON fd.parent     = bom.name
        WHERE
            {where_clause}
        GROUP BY
            citm.item_code,
            citm.item_name,
            citm.wishlist,
            citm.trending,
            citm.folder,
            item.item_category,
            item.item_subcategory,
            item.image,
            item.sketch_image,
            item.front_view,
            item.setting_type,
            item.stylebio,
            item.variant_of,
            bom.tag_no,
            bom.diamond_quality,
            bom.metal_purity,
            bom.metal_touch,
            bom.metal_colour,
            bom.navratna,
            bom.height,
            bom.length,
            bom.width,
            bom.product_size,
            bom.sizer_type,
            bom.design_style,
            bom.detachable,
            bom.total_diamond_pcs,
            bom.total_gemstone_pcs,
            bom.finding_pcs,
            bom.gross_weight,
            bom.metal_and_finding_weight,
            bom.total_diamond_weight_in_gms,
            bom.total_gemstone_weight_in_gms,
            bom.gemstone_weight,
            bom.other_weight,
            bom.finding_weight_,
            bom.gold_to_diamond_ratio,
            bom.diamond_ratio,
            bom.metal_to_diamond_ratio_excl_of_finding
        ORDER BY
            item.name DESC
    """, values, as_dict=True) 


# ─────────────────────────────────────────────────────────────
# CUSTOMER 
# ─────────────────────────────────────────────────────────────
def resolve_customer_by_email(recipient_email):

    customer = frappe.db.get_value(
        "Customer",
        {"email_id": recipient_email},
        ["name", "customer_name", "email_id"],
        as_dict=True
    )

    if customer:
        return customer

    return None


# ─────────────────────────────────────────────────────────────
# MAIN FUNCTION
# ─────────────────────────────────────────────────────────────
@frappe.whitelist()
def send_catalogue_mail(recipient_email, selectedSubcategory=None, metalType=None):

    #  Validation
    if not recipient_email:
        frappe.throw("Recipient email is required.")

    logged_in_user = frappe.session.user
    if not logged_in_user or logged_in_user == "Guest":
        frappe.throw("Login required.")

    sender_name = frappe.db.get_value(
        "User", logged_in_user, "full_name"
    ) or logged_in_user

    #  Try to find customer
    customer_doc = resolve_customer_by_email(recipient_email)

    # ─────────────────────────────────────────────
    #  CASE 1: CUSTOMER EXISTS
    # ─────────────────────────────────────────────
    if customer_doc:

        customer_id   = customer_doc["name"]
        customer_name = customer_doc["customer_name"] or customer_id

        wishlist_items = get_wishlist_items(customer_id)

        if wishlist_items:
            items_to_send = wishlist_items
            source_label  = "Wishlist Items"
        else:
            items_to_send = get_catalogue_items(
                customer_id=customer_id,
                selectedSubcategory=selectedSubcategory,
                metalType=metalType
            )
            source_label = "Catalogue Items"

    # ─────────────────────────────────────────────
    #  CASE 2: STRANGER
    # ─────────────────────────────────────────────
    else:

        customer_name = "Valued Customer"

        items_to_send = get_catalogue_items(
            selectedSubcategory=selectedSubcategory,
            metalType=metalType
        )

        source_label = "General Catalogue"

    #  Safety check
    if not items_to_send:
        return {
            "status": "no_data",
            "message": "No items available to send."
        }

    #  FIX: Deduplicate by item_code as a final Python-level safety net.
    #    Even if the SQL GROUP BY somehow still returns dupes (e.g. item appears
    #    in multiple catalogue masters), this guarantees one row per item_code.
    seen         = set()
    unique_items = []
    for item in items_to_send:
        if item["item_code"] not in seen:
            seen.add(item["item_code"])
            unique_items.append(item)
    items_to_send = unique_items

    #  Counts — now based on deduplicated unique items only
    total_items    = len(items_to_send)
    wishlist_count = sum(1 for i in items_to_send if i.get("wishlist") == 1)
    trending_count = sum(1 for i in items_to_send if i.get("trending") == 1)

    #  Debug log — verify counts in bench logs before sending
    #    Run: bench --site <site> tail-logs   to watch this live
    #    Remove this block once counts are confirmed correct in production
    frappe.logger().info(
        f"[catalogue_mail] DEBUG | recipient: {recipient_email} | "
        f"total_items: {total_items} | wishlist_count: {wishlist_count} | "
        f"trending_count: {trending_count} | source: {source_label}"
    )

    #  Email Template
    html_body = frappe.render_template(
        "gke_customization/templates/emails/catalogue_mail.html",
        {
            "customer_name":  customer_name,
            "source_label":   source_label,
            "items":          items_to_send,
            "total_items":    total_items,        #  accurate unique item count
            "wishlist_count": wishlist_count,     #  accurate
            "trending_count": trending_count,     #  accurate
            "sender_name":    sender_name,
            "sender_email":   logged_in_user,
        }
    )

    #  Send Mail
    frappe.sendmail(
        sender=logged_in_user,
        recipients=[recipient_email],
        subject=f"Catalogue for You – {customer_name}",
        message=html_body,
        now=True
    )

    #  Log
    frappe.logger().info(
        f"[catalogue_mail] SENT | {sender_name} → {recipient_email} | "
        f"{total_items} items | source: {source_label}"
    )

    return {
        "status":     "success",
        "recipient":  recipient_email,
        "items_sent": total_items,
        "source":     source_label,
        "message":    f"Mail sent successfully to {recipient_email}"
    }
    
"""RI03079"""