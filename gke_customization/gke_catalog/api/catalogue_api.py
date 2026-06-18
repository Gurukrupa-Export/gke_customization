from warnings import filters
import frappe
from frappe import _
from frappe.utils import flt
from frappe.utils.password import encrypt
from gke_customization.gke_catalog.api.item_catalog import get_collection, get_rhodium
from pydantic import Secret
import pyotp
import hmac
import hashlib
import base64
from frappe.auth import LoginManager
from datetime import datetime, timedelta, timezone
import pytz
from frappe.integrations.oauth2 import get_oauth_server
import requests
import json
from gke_customization.gke_catalog.api.notifications import notify_user
from gke_customization.gke_catalog.api.wishlist_download import get_method
from gke_customization.gke_catalog.api.wishlist_download import get_method1
from gke_customization.gke_catalog.api.encryption_response import encrypt_response

from cryptography.fernet import Fernet


@frappe.whitelist(allow_guest=True)
def catalogue_data(selectedSubcategory=None, itemCategory=None, itemCode=None, metalType = None, company = None, customer = None):
    # selectedSubcategory = frappe.form_dict.get("selectedSubcategory")
    # itemCode = frappe.form_dict.get("itemCode")
    # itemCategory = frappe.form_dict.get("itemCategory")
    # metalType = frappe.form_dict.get("metalType")

    # Only fallback if argument not passed
    if selectedSubcategory is None:
        selectedSubcategory = frappe.form_dict.get("selectedSubcategory")

    if itemCode is None:
        itemCode = frappe.form_dict.get("itemCode")

    if metalType is None:
        metalType = frappe.form_dict.get("metalType")

    if itemCategory is None:
        itemCategory = frappe.form_dict.get("itemCategory")
   
    where_clause = ""

    if selectedSubcategory:
        where_clause += f" item.item_subcategory = '{selectedSubcategory}'"

    if metalType:
        where_clause += f" AND bom.metal_type = '{metalType}'"
 
    if company:
        where_clause += f" AND idf.company = '{company}'"
    else:
        where_clause += " AND idf.company = 'Gurukrupa Export Private Limited'"


    where_clause += " AND bom.bom_type = 'Finish Goods'"

    if itemCode:
        where_clause = where_clause + f" AND item.item_code = '{itemCode}' "
    if itemCategory:
        where_clause = where_clause + f" AND item.item_category = '{itemCategory}' "
        
    values = {}

    if customer:
        wishlist_case = "MAX(CASE WHEN tci.wishlist = 1 AND tcm.customer IS NOT NULL THEN 1 ELSE 0 END) AS wishlist"
        trending_case = "MAX(CASE WHEN tci.trending = 1 AND tcm.customer IS NOT NULL THEN 1 ELSE 0 END) AS trending"
        customer_join = "AND tcm.customer = %(customer)s"
    else:
        wishlist_case = "0 AS wishlist"
        trending_case = "0 AS trending"
        customer_join = ""  


    if customer:
        values["customer"] = customer
        

    # where_clause += " AND item.item_code = 'EA01809-001'"
    # frappe.throw(repr(where_clause))

    # frappe.throw(where_clause)
    
    # if metalType == 'Gold':
    #     where_clause = where_clause + f" AND bom.metal_type = '{metalType}' AND (bom.bom_type = 'Finish Goods') " #  OR bom.bom_type = 'Template'
    # if metalType == 'Silver':
    #     where_clause = where_clause + f" AND bom.metal_type = '{metalType}' AND (bom.bom_type = 'Finish Goods'  OR bom.bom_type = 'Template') "
    
    # frappe.throw(f"{where_clause}")

    db_data = frappe.db.sql(
        f""" SELECT
                item.name,
                bom.name,
                idf.company,
                tci.trending,
                # {trending_case},
                {wishlist_case},
                item.creation,
                item.item_code,
                item.item_category,
                item.custom_catalogue_image,
                item.sketch_image,
                item.front_view as cad_image,
                CASE
                    WHEN item.front_view = item.image THEN 'CAD Image'
                    ELSE 'FG Image'
                END AS image_remark,
                # item.`3d_videos_1` ,
                item.item_subcategory,
                item.stylebio,
                bom.tag_no,
                bom.diamond_quality, 
                item.setting_type,
                FORMAT(bom.gross_weight,3) AS gross_metal_weight,
                FORMAT(bom.metal_and_finding_weight, 3) AS net_metal_finding_weight,
                FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
                FORMAT(bom.other_weight,3) AS other_weight,
                FORMAT(bom.finding_weight_,3) AS finding_weight_,
                bom.metal_colour,
                bom.metal_touch as bom_touch,
                bom.metal_purity,
                FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,
                bom.total_diamond_pcs,
                bom.total_gemstone_pcs,
                FORMAT(bom.gemstone_weight,3) AS gemstone_weight,
                FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
                FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
                FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,
                bom.navratna,
                bom.lock_type,
                bom.feature,
                bom.enamal,
                bom.rhodium,
                bom.sizer_type,
                bom.height,
                bom.length,
                bom.width,
                bom.breadth,
                bom.product_size,
                bom.sizer_type,
                bom.design_style,
                bom.nakshi_from,
                bom.vanki_type,
                bom.total_length,
                bom.detachable,
                bom.back_side_size,
                bom.changeable,
                item.variant_of,
                bom.finding_pcs,
                bom.total_other_pcs,
                bom.total_other_weight,
                GROUP_CONCAT(DISTINCT item.name) as variant_name,
                GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
                GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,
                GROUP_CONCAT(
                        DISTINCT CASE 
                            WHEN td.design_attributes = 'Collection' 
                            THEN td.design_attribute_value_1 
                        END
                ) AS custom_collection,

                GROUP_CONCAT(
                        DISTINCT CASE 
                            WHEN td.design_attributes = 'Language' 
                            THEN td.design_attribute_value_1 
                        END
                ) AS custom_language,

                GROUP_CONCAT(
                        DISTINCT CASE 
                            WHEN td.design_attributes = 'Zodiac' 
                            THEN td.design_attribute_value_1 
                        END
                ) AS custom_zodiac,
                
                GROUP_CONCAT(
                        DISTINCT CASE 
                            WHEN td.design_attributes = 'Animal/Birds' 
                            THEN td.design_attribute_value_1 
                        END
                ) AS custom_animalbirds,
                
                GROUP_CONCAT(
                        DISTINCT CASE 
                            WHEN td.design_attributes = 'Alphabet/Number' 
                            THEN td.design_attribute_value_1 
                        END
                ) AS custom_alphabetnumber,
                
                GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
                GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
                GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
                GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,
                GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
                GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,
                GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
                GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
                GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
                GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
                GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,
                GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
                GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
                GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size
            FROM
                `tabItem` AS item
            LEFT JOIN 
                `tabCataloge Item Details` AS tci 
            ON 
                tci.item_code = item.name
            LEFT JOIN 
                `tabCataloge Master` AS tcm 
            ON 
                tcm.name = tci.parent
                {customer_join}  
            LEFT JOIN
                `tabBOM` AS bom
            ON
                item.item_code = bom.item
            # LEFT JOIN
            #     `tabSerial No` AS sn
            # ON
            #     sn.name = bom.tag_no
            LEFT JOIN
                `tabDesign Attributes`  AS td
            ON
                item.item_code = td.parent
            LEFT JOIN
                `tabBOM Metal Detail` AS mt
            ON
                bom.name = mt.parent
            LEFT JOIN
                `tabBOM Gemstone Detail` AS gd
            ON
                bom.name = gd.parent
            LEFT JOIN
                `tabBOM Diamond Detail` AS dd
            ON
                bom.name = dd.parent
            LEFT JOIN
                `tabBOM Finding Detail` AS fd
            ON
                bom.name = fd.parent
            LEFT JOIN
                `tabBOM Other Detail` AS od
            ON
                bom.name = od.parent
            LEFT JOIN
                `tabItem Default` AS idf
            ON
                item.item_name = idf.parent
            WHERE
                {where_clause}
            # GROUP BY
            #     item.name, item.creation, item.item_code, item.item_category, item.image, item.item_subcategory, bom.tag_no,
            #     bom.gross_weight, bom.metal_and_finding_weight, bom.total_diamond_weight_in_gms, bom.other_weight,
            #     bom.finding_weight_, bom.total_gemstone_weight_in_gms, item.item_name,item.variant_of
            GROUP BY
                item.item_code, item.variant_of
            ORDER BY
                item.name DESC 
            # limit 200
    """,
    values,
    as_dict=True)

    item_codes = [row.item_code for row in db_data]

    if item_codes:
        db_res = frappe.db.sql(
            """
            SELECT 
                parent,
                parentfield,
                GROUP_CONCAT(design_attribute ORDER BY design_attribute SEPARATOR ', ') AS design_attributes
            FROM `tabDesign Attribute - Multiselect`
            WHERE parent IN %(data)s
            GROUP BY parent, parentfield
            """,
            {"data": tuple(item_codes)},
            as_dict=True
        )
    else:
        db_res = []

    attr_map = {}

    for row in db_res:
        parent = row["parent"]
        field = row["parentfield"]
        value = row["design_attributes"]

        # remove custom_ prefix
        clean_field = field.replace("custom_", "")

        if parent not in attr_map:
            attr_map[parent] = {}

        attr_map[parent][clean_field] = value


    # merge into main data
    for row in db_data:
        attrs = attr_map.get(row.item_code, {})

        for key, value in attrs.items():
            row[key] = value

    return db_data

# Changes by rajan
# @frappe.whitelist(allow_guest=True)
# def customer_wise_item(selectedSubcategory, customer = None, user = None, metalType = None):
#     selectedSubcategory = frappe.form_dict.get("selectedSubcategory")
#     itemCode = frappe.form_dict.get("itemCode")
#     itemCategory = frappe.form_dict.get("itemCategory")
#     metalType = frappe.form_dict.get("metalType")

#     where_clause = """
#     idf.company = 'Gurukrupa Export Private Limited'
#     AND bom.bom_type = 'Finish Goods'
#     AND bom.name IS NOT NULL
#     AND bom.is_active = 1
#     AND bom.is_default = 1
#     """

#     if selectedSubcategory:
#         where_clause = where_clause + f" AND item.item_subcategory = '{selectedSubcategory}' "
#     if metalType:
#         where_clause = where_clause + f" AND bom.metal_type = '{metalType}' "
#     if customer:
#         where_clause = where_clause + f" AND tcm.customer = '{customer}' "
#     if user:
#         where_clause = where_clause + f" AND icm.user = '{user}' "
#     if itemCode:
#         where_clause = where_clause + f" AND item.item_code = '{itemCode}' "
#     if itemCategory:
#         where_clause = where_clause + f" AND item.item_category = '{itemCategory}' "

#     db_data = frappe.db.sql(
#         f""" SELECT
#                 item.name,
#                 bom.name,
#                 idf.company,
#                 tci.trending,
#                 tci.folder,
#                 tci.wishlist,
#                 uid.folder as internal_catalog_folder,
#                 uid.wishlist as internal_catalog_wishlist,
#                 item.creation,
#                 item.item_code,
#                 item.item_category,
#                 item.stylebio,
#                 item.image,
#                 item.sketch_image,
#                 item.front_view as cad_image,
#                 CASE
#                     WHEN item.front_view = item.image THEN 'CAD Image'
#                     ELSE 'FG Image'
#                 END AS image_remark,
                
#                 CASE 
#                     WHEN vc.variant_count > 1 THEN 1 
#                     ELSE 0 
#                 END AS rn,
                
#                 CASE 
#                    WHEN set_check.is_set_item = 1 THEN 1 
#                    ELSE 0 
#                 END AS is_set_item,
                
#                 CASE 
#                     WHEN similar_check.is_similar_item = 1 THEN 1 
#                     ELSE 0 
#                 END AS is_similar_item,
            
#                 item.item_subcategory,
#                 bom.tag_no,
#                 bom.diamond_quality,
#                 item.setting_type,
#                 FORMAT(bom.gross_weight,3) AS gross_metal_weight,
#                 FORMAT(bom.metal_and_finding_weight, 3) AS net_metal_finding_weight,
#                 FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
#                 FORMAT(bom.other_weight,3) AS other_weight,
#                 FORMAT(bom.finding_weight_,3) AS finding_weight_,
#                 bom.metal_touch as bom_touch,
#                 bom.metal_purity,
#                 FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,
#                 bom.total_diamond_pcs,
#                 bom.total_gemstone_pcs,
#                 FORMAT(bom.gemstone_weight,3) AS gemstone_weight,
#                 FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
#                 FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
#                 FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,
#                 bom.navratna,
#                 bom.height,
#                 bom.length,
#                 bom.width,
#                 bom.breadth,
#                 bom.product_size,
#                 bom.sizer_type,
#                 bom.design_style,
#                 bom.nakshi_from,
#                 bom.vanki_type,
#                 bom.total_length,
#                 bom.detachable,
#                 bom.back_side_size,
#                 bom.changeable,
#                 item.variant_of,
#                 bom.finding_pcs,
#                 bom.total_other_pcs,
#                 bom.total_other_weight,
#                 GROUP_CONCAT(DISTINCT item.name) as variant_name,
#                 GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
#                 GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,
#                 GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
#                 GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
#                 GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
#                 GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,
#                 GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
#                 GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,
#                 GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
#                 GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
#                 GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
#                 GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
#                 GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,
#                 GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
#                 GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
#                 GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size
#             FROM 
#                 `tabItem` AS item
#             LEFT JOIN 
#                 `tabCataloge Item Details` AS tci 
#             ON 
#                 tci.item_code = item.name
                
#             LEFT JOIN (
#                 SELECT 
#                     IFNULL(i.variant_of, i.item_code) AS group_key,
#                     COUNT(DISTINCT i.item_code) AS variant_count
#                 FROM `tabItem` AS i
#                 INNER JOIN `tabBOM` AS b 
#                     ON i.item_code = b.item
#                     AND b.bom_type = 'Finish Goods'
#                     AND b.is_active = 1
#                     AND b.is_default = 1
#                 INNER JOIN `tabCataloge Item Details` AS tci2
#                     ON tci2.item_code = i.item_code
#                 INNER JOIN `tabCataloge Master` AS tcm2
#                     ON tcm2.name = tci2.parent
#                 GROUP BY IFNULL(i.variant_of, i.item_code)
#             ) vc 
#             ON vc.group_key = IFNULL(item.variant_of, item.item_code)
            
#             LEFT JOIN (
#                 SELECT 
#                     sit.parent AS item_code,
#                     CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END AS is_set_item
#                 FROM `tabSet Item Table` sit
#                 GROUP BY sit.parent
#             ) AS set_check ON set_check.item_code = item.item_code
            
#             LEFT JOIN (
#             SELECT 
#                 sit.parent AS item_code,
#                 CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END AS is_similar_item
#                 FROM `tabSimilar Item Table` sit
#                 WHERE sit.parenttype = 'Item'
#                 GROUP BY sit.parent
#             ) AS similar_check ON similar_check.item_code = item.item_code
        
#             LEFT JOIN 
#                 `tabCataloge Master` AS tcm 
#             ON 
#                 tcm.name = tci.parent
                
#             LEFT JOIN 
#                 `tabUser Item Details` AS uid 
#             ON 
#                 uid.item_code = item.name
#             LEFT JOIN 
#                 `tabInternal Catalog Master` AS icm 
#             ON 
#                 icm.name = uid.parent
#             LEFT JOIN
#                 `tabBOM` AS bom
#             ON
#                 item.item_code = bom.item
#             LEFT JOIN
#                 `tabDesign Attributes`  AS td
#             ON
#                 item.item_code = td.parent
#             LEFT JOIN
#                 `tabBOM Metal Detail` AS mt
#             ON
#                 bom.name = mt.parent
#             LEFT JOIN
#                 `tabBOM Gemstone Detail` AS gd
#             ON
#                 bom.name = gd.parent
#             LEFT JOIN
#                 `tabBOM Diamond Detail` AS dd
#             ON
#                 bom.name = dd.parent
#             LEFT JOIN
#                 `tabBOM Finding Detail` AS fd
#             ON
#                 bom.name = fd.parent
#             LEFT JOIN
#                 `tabBOM Other Detail` AS od
#             ON
#                 bom.name = od.parent
#             LEFT JOIN
#                 `tabItem Default` AS idf
#             ON
#                 item.item_name = idf.parent
#             WHERE
#                 {where_clause}
#             GROUP BY
#                 item.item_code, item.variant_of
#             ORDER BY
#                 item.name DESC 
#     """,
#     as_dict=True)

#     d = {}
#     int_c_f = {}

#     for row in db_data:
#         if row.folder:
#             folder = row.folder.split(",")
#             for fd in folder:
#                 if fd not in d:
#                     d[fd] = []
#                 d[fd].append(row)
    
#     for row in db_data:
#         if row.internal_catalog_folder:
#             internal_catalog_folder = row.internal_catalog_folder.split(",")
#             for fd in internal_catalog_folder:
#                 if fd not in int_c_f:
#                     int_c_f[fd] = []
#                 int_c_f[fd].append(row)

#     return {
#         "db_data" : db_data,
#         "folder": d,
#         "internal_catalog_folder" : int_c_f
#     }

# changes by rajan
@frappe.whitelist(allow_guest=True)
def customer_wise_item(selectedSubcategory=None, customer = None, user = None, metalType = None):
    allow_excel_permission = 0
    selectedSubcategory = frappe.form_dict.get("selectedSubcategory")
    itemCode = frappe.form_dict.get("itemCode")
    itemCategory = frappe.form_dict.get("itemCategory")
    metalType = frappe.form_dict.get("metalType")

    where_clause = """
    idf.company = 'Gurukrupa Export Private Limited'
    AND bom.bom_type = 'Finish Goods'
    AND bom.name IS NOT NULL
    AND bom.is_active = 1
    AND bom.is_default = 1
    """
    if selectedSubcategory:
        where_clause = where_clause + f" AND item.item_subcategory = '{selectedSubcategory}' "
    if metalType:
        where_clause = where_clause + f" AND bom.metal_type = '{metalType}' "
    if customer:
        where_clause = where_clause + f" AND tcm.customer = '{customer}' "
        allow_excel_permission = frappe.db.get_value(
            "Cataloge Master",
            {"customer": customer},
            "allow_excel_permission"
        )
    if user:
        where_clause = where_clause + f" AND icm.user = '{user}' "
    if itemCode:
        where_clause = where_clause + f" AND item.item_code = '{itemCode}' "
    if itemCategory:
        where_clause = where_clause + f" AND item.item_category = '{itemCategory}' "

    db_data = frappe.db.sql(
        f""" SELECT
                item.name,
                bom.name,
                idf.company,
                tci.trending,
                tci.name as catalog_item_details_name,
                tci.folder,
                tci.wishlist,
                tci.as_per_design,
                tci.job_work,
                tci.as_per_customized,
                tci.customized_data,
                tci.customer_gold,
                tci.customer_diamond,
                tci.customer_stone,
                uid.folder as internal_catalog_folder,
                uid.wishlist as internal_catalog_wishlist,
                item.creation,
                item.item_code,
                item.item_category,
                item.stylebio,
                item.image,
                item.sketch_image,
                item.front_view as cad_image,
                CASE
                    WHEN item.front_view = item.image THEN 'CAD Image'
                    ELSE 'FG Image'
                END AS image_remark,

                CASE 
                    WHEN vc.variant_count > 1 THEN 1 
                    ELSE 0 
                END AS rn,

                CASE 
                   WHEN set_check.is_set_item = 1 THEN 1 
                   ELSE 0 
                END AS is_set_item,

                CASE 
                    WHEN similar_check.is_similar_item = 1 THEN 1 
                    ELSE 0 
                END AS is_similar_item,

                item.item_subcategory,
                bom.tag_no,
                bom.diamond_quality,
                item.setting_type,
                FORMAT(bom.gross_weight,3) AS gross_metal_weight,
                FORMAT(bom.metal_and_finding_weight, 3) AS net_metal_finding_weight,
                FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
                FORMAT(bom.other_weight,3) AS other_weight,
                FORMAT(bom.finding_weight_,3) AS finding_weight_,
                bom.metal_touch as bom_touch,
                bom.metal_purity,
                FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,
                bom.total_diamond_pcs,
                bom.total_gemstone_pcs,
                FORMAT(bom.gemstone_weight,3) AS gemstone_weight,
                FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
                FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
                FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,
                bom.navratna,
                bom.height,
                bom.length,
                bom.width,
                bom.breadth,
                bom.product_size,
                bom.sizer_type,
                bom.design_style,
                bom.nakshi_from,
                bom.vanki_type,
                bom.total_length,
                bom.detachable,
                bom.back_side_size,
                bom.changeable,
                item.variant_of,
                bom.finding_pcs,
                bom.total_other_pcs,
                bom.total_other_weight,
                GROUP_CONCAT(DISTINCT item.name) as variant_name,
                GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
                GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,
                GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
                GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
                GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
                GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,
                GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
                GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,
                GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
                GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
                GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
                GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
                GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,
                GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
                GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
                GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size
            FROM
                `tabItem` AS item
            LEFT JOIN
                `tabCataloge Item Details` AS tci
            ON
                tci.item_code = item.name

            LEFT JOIN (
                SELECT
                    COALESCE(i.variant_of, i.item_code) AS group_key,
                    tci2.parent AS catalog_parent,
                    COUNT(DISTINCT i.item_code) AS variant_count,
                    MAX(tci2.as_per_design) AS as_per_design,
                    MAX(tci2.job_work) AS job_work,
                    MAX(tci2.as_per_customized) AS as_per_customized
                FROM `tabItem` AS i
                INNER JOIN `tabBOM` AS b
                    ON i.item_code = b.item 
                    AND b.bom_type = 'Finish Goods'
                    AND b.is_active = 1
                    AND b.is_default = 1
                LEFT JOIN `tabCataloge Item Details` AS tci2
                    ON tci2.item_code = i.item_code
                LEFT JOIN `tabCataloge Master` AS tcm2
                    ON tcm2.name = tci2.parent
                GROUP BY COALESCE(i.variant_of, i.item_code), tci2.parent  -- tci2.parent add kiya
            ) vc ON vc.group_key = COALESCE(item.variant_of, item.item_code)
                    AND vc.catalog_parent = tci.parent  
        
            LEFT JOIN (
                SELECT
                    sit.parent AS item_code,
                    CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END AS is_set_item
                FROM `tabSet Item Table` sit
                                
                INNER JOIN `tabCataloge Item Details` tci
                    ON tci.item_code = sit.item_code
                    
                WHERE sit.parenttype = 'Item'
                GROUP BY sit.parent
            ) AS set_check ON set_check.item_code = item.item_code

            LEFT JOIN (
                SELECT
                    sit.parent AS item_code,
                    tci.parent AS catalog_parent,
                    CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END AS is_similar_item
                FROM `tabSimilar Item Table` sit
            
                -- customer catalogue me similar item hona chahiye
                INNER JOIN `tabCataloge Item Details` tci
                    ON tci.item_code = sit.item_code
            
                WHERE sit.parenttype = 'Item'
            
                GROUP BY sit.parent, tci.parent
            
            ) AS similar_check 
            ON similar_check.item_code = item.item_code
            AND similar_check.catalog_parent = tci.parent

            LEFT JOIN
                `tabCataloge Master` AS tcm
            ON
                tcm.name = tci.parent
                
            LEFT JOIN
                `tabUser Item Details` AS uid
            ON
                uid.item_code = item.name
            LEFT JOIN
                `tabInternal Catalog Master` AS icm
            ON
                icm.name = uid.parent
            LEFT JOIN
                `tabBOM` AS bom
            ON
                item.item_code = bom.item
            LEFT JOIN
                `tabDesign Attributes` AS td
            ON
                item.item_code = td.parent
            LEFT JOIN
                `tabBOM Metal Detail` AS mt
            ON
                bom.name = mt.parent
            LEFT JOIN
                `tabBOM Gemstone Detail` AS gd
            ON
                bom.name = gd.parent
            LEFT JOIN
                `tabBOM Diamond Detail` AS dd
            ON
                bom.name = dd.parent
            LEFT JOIN
                `tabBOM Finding Detail` AS fd
            ON
                bom.name = fd.parent
            LEFT JOIN
                `tabBOM Other Detail` AS od
            ON
                bom.name = od.parent
            LEFT JOIN
                `tabItem Default` AS idf
            ON
                item.item_name = idf.parent
            WHERE
                {where_clause}
           GROUP BY
                item.item_code, item.variant_of, tci.parent,  tci.name
            ORDER BY
                item.name DESC
    """,
    as_dict=True)

    
    d = {}
    int_c_f = {}

    for row in db_data:
        if row.folder:
            folder = row.folder.split(",")
            for fd in folder:
                if fd not in d:
                    d[fd] = []
                d[fd].append(row)

    for row in db_data:
        if row.internal_catalog_folder:
            internal_catalog_folder = row.internal_catalog_folder.split(",")
            for fd in internal_catalog_folder:
                if fd not in int_c_f:
                    int_c_f[fd] = []
                int_c_f[fd].append(row)
            
    return {
        "db_data": db_data,
        "allow_excel_permission":allow_excel_permission,
        "folder": d,
        "internal_catalog_folder": int_c_f
    }




# @frappe.whitelist(allow_guest=True)
# def customer_wise_item(selectedSubcategory, customer = None, user = None,  metalType = None):
#     selectedSubcategory = frappe.form_dict.get("selectedSubcategory")
#     itemCode = frappe.form_dict.get("itemCode")
#     itemCategory = frappe.form_dict.get("itemCategory")
#     metalType = frappe.form_dict.get("metalType")

#     where_clause = """
#         idf.company = 'Gurukrupa Export Private Limited'
#     """
#         # AND bom.bom_type = 'Finish Goods'
#         #   OR bom.bom_type = 'Template')

#     if selectedSubcategory:
#         where_clause = where_clause + f" AND item.item_subcategory = '{selectedSubcategory}' "
#     if metalType == 'Gold':
#         where_clause = where_clause + f" AND bom.metal_type = '{metalType}' AND (bom.bom_type = 'Finish Goods') " #  OR bom.bom_type = 'Template'
#     if metalType == 'Silver':
#         where_clause = where_clause + f" AND bom.metal_type = '{metalType}' AND (bom.bom_type = 'Finish Goods'  OR bom.bom_type = 'Template') "
#     if customer:
#         where_clause = where_clause + f" AND tcm.customer = '{customer}' "

#     if user:
#         where_clause = where_clause + f" AND icm.user = '{user}' "
    
#     if itemCode:
#         where_clause = where_clause + f" AND item.item_code = '{itemCode}' "
#     if itemCategory:
#         where_clause = where_clause + f" AND item.item_category = '{itemCategory}' "
    

#     db_data = frappe.db.sql(
#         f""" SELECT
#                 item.name,
#                 bom.name,
#                 idf.company,
#                 tci.trending,
#                 tci.folder,
#                 tci.wishlist,
#                 uid.folder as internal_catalog_folder,
#                 uid.wishlist as internal_catalog_wishlist,
#                 item.creation,
#                 item.item_code,
#                 item.item_category,
#                 item.stylebio,
#                 item.image,
#                 item.sketch_image,
#                 item.front_view as cad_image,
#                 CASE
#                     WHEN item.front_view = item.image THEN 'CAD Image'
#                     ELSE 'FG Image'
#                 END AS image_remark,
#                 item.item_subcategory,
#                 bom.tag_no,
#                 bom.diamond_quality,
#                 item.setting_type,
#                 FORMAT(bom.gross_weight,3) AS gross_metal_weight,
#                 FORMAT(bom.metal_and_finding_weight, 3) AS net_metal_finding_weight,
#                 FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
#                 FORMAT(bom.other_weight,3) AS other_weight,
#                 FORMAT(bom.finding_weight_,3) AS finding_weight_,
#                 bom.metal_touch as bom_touch,
#                 # bom.metal_colour,
#                 bom.metal_purity,
#                 FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,
#                 bom.total_diamond_pcs,
#                 bom.total_gemstone_pcs,
#                 FORMAT(bom.gemstone_weight,3) AS gemstone_weight,
#                 FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
#                 FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
#                 FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,
#                 bom.navratna,
#                 bom.height,
#                 bom.length,
#                 bom.width,
#                 bom.breadth,
#                 bom.product_size,
#                 bom.sizer_type,
#                 bom.design_style,
#                 bom.nakshi_from,
#                 bom.vanki_type,
#                 bom.total_length,
#                 bom.detachable,
#                 bom.back_side_size,
#                 bom.changeable,
#                 item.variant_of,
#                 bom.finding_pcs,
#                 bom.total_other_pcs,
#                 bom.total_other_weight,
#                 GROUP_CONCAT(DISTINCT item.name) as variant_name,
#                 GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
#                 GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,

#                 GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
#                 GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
#                 GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
#                 GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,
#                 GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
#                 GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,
#                 GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
#                 GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
#                 GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
#                 GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
#                 GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,
#                 GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
#                 GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
#                 GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size
#             FROM 
#                 `tabItem` AS item
#             LEFT JOIN 
#                 `tabCataloge Item Details` AS tci 
#             ON 
#                 tci.item_code = item.name
#             LEFT JOIN 
#                 `tabCataloge Master` AS tcm 
#             ON 
#                 tcm.name = tci.parent

#             LEFT JOIN 
#                 `tabUser Item Details` AS uid 
#             ON 
#                 uid.item_code = item.name
#             LEFT JOIN 
#                 `tabInternal Catalog Master` AS icm 
#             ON 
#                 icm.name = uid.parent

#             LEFT JOIN
#                 `tabBOM` AS bom
#             ON
#                 item.item_code = bom.item
#             LEFT JOIN
#                 `tabDesign Attributes`  AS td
#             ON
#                 item.item_code = td.parent
#             LEFT JOIN
#                 `tabBOM Metal Detail` AS mt
#             ON
#                 bom.name = mt.parent
#             LEFT JOIN
#                 `tabBOM Gemstone Detail` AS gd
#             ON
#                 bom.name = gd.parent
#             LEFT JOIN
#                 `tabBOM Diamond Detail` AS dd
#             ON
#                 bom.name = dd.parent
#             LEFT JOIN
#                 `tabBOM Finding Detail` AS fd
#             ON
#                 bom.name = fd.parent
#             LEFT JOIN
#                 `tabBOM Other Detail` AS od
#             ON
#                 bom.name = od.parent
#             LEFT JOIN
#                 `tabItem Default` AS idf
#             ON
#                 item.item_name = idf.parent
#             WHERE
#                 {where_clause}
#             # GROUP BY
#             #     item.name, item.creation, item.item_code, item.item_category, item.image, item.item_subcategory, bom.tag_no,
#             #     bom.gross_weight, bom.metal_and_finding_weight, bom.total_diamond_weight_in_gms, bom.other_weight,
#             #     bom.finding_weight_, bom.total_gemstone_weight_in_gms, item.item_name,item.variant_of
#             GROUP BY
#                 item.item_code, item.variant_of
#             ORDER BY
#                 item.name DESC 
#             # limit 200
#     """,
#     as_dict=True)

#     d = {}

#     int_c_f = {}

#     for row in db_data:
#         if row.folder:
#             folder = row.folder.split(",")
#             for fd in folder:
#                 if fd not in d:
#                     d[fd] = []
#                 d[fd].append(row)
    
#     for row in db_data:
#         if row.internal_catalog_folder:
#             internal_catalog_folder = row.internal_catalog_folder.split(",")
#             for fd in internal_catalog_folder:
#                 if fd not in int_c_f:
#                     int_c_f[fd] = []
#                 int_c_f[fd].append(row)

#     # frappe.throw(f"{d}")
#     return {
#         "db_data" : db_data,
#         "folder": d,
#         "internal_catalog_folder" : int_c_f
#     } 


# This subcategory_count count all item including variants
# @frappe.whitelist(allow_guest=True)
# def subcategory_count(categoryName, user_type, customer=None):
#     try:
#         if user_type == "Customer":
#             sql_query = """
#                 SELECT 
#                     ti.item_category,
#                     ti.item_subcategory,
#                     tb.metal_type,
#                     COUNT(DISTINCT ti.name) AS item_count,
#                     COUNT(DISTINCT ti.name) AS serial_count,
#                     MIN(ti.image) AS first_image
                    
#                 FROM `tabCataloge Item Details` AS tci
        
#                 JOIN `tabCataloge Master` AS tcm 
#                     ON tcm.name = tci.parent
#                     AND tcm.customer = %s
        
#                 JOIN `tabItem` AS ti 
#                     ON ti.name = tci.item_code
#                     AND ti.item_category = %s
        
#                 JOIN `tabAttribute Value` AS tav 
#                     ON tav.name = ti.item_subcategory
#                     AND tav.is_subcategory = 1
        
#                 JOIN `tabBOM` AS tb 
#                     ON tb.item = ti.name
#                     AND tb.is_active = 1
#                     AND tb.bom_type = 'Finish Goods'
        
#                 -- Serial count: count actual serial nos linked to this item
#                 LEFT JOIN `tabSerial No` AS se
#                     ON se.item_code = ti.name
#                     AND se.status = 'Active'
        
#                 WHERE 
#                     ti.item_subcategory IS NOT NULL
        
#                 GROUP BY 
#                     ti.item_category,
#                     ti.item_subcategory,
#                     tb.metal_type
        
#                 ORDER BY 
#                     ti.item_category,
#                     ti.item_subcategory,
#                     tb.metal_type
#             """
#             result = frappe.db.sql(sql_query, (customer, categoryName), as_dict=True)

#         else:
#             sql_query = """
#                 SELECT
#                     item.item_subcategory,

#                     COUNT(DISTINCT CASE
#                         WHEN bom.bom_type = 'Finish Goods' AND bom.is_active = 1 
#                         THEN item.name
#                     END) AS item_count,

#                     COUNT(DISTINCT CASE
#                         WHEN bom.bom_type = 'Finish Goods' AND bom.is_active = 1 
#                         THEN item.name
#                     END) AS serial_count,

#                     (
#                         SELECT item2.image
#                         FROM `tabItem` AS item2
#                         INNER JOIN (
#                             SELECT
#                                 IFNULL(i.variant_of, i.item_code) AS group_key,
#                                 MIN(i.item_code) AS first_item_code
#                             FROM `tabItem` AS i
#                             INNER JOIN `tabBOM` AS b 
#                                 ON i.item_code = b.item 
#                                 AND b.bom_type = 'Finish Goods'
#                             INNER JOIN `tabItem Default` AS idf3 
#                                 ON i.item_name = idf3.parent
#                                 AND idf3.company = 'Gurukrupa Export Private Limited'
#                             GROUP BY IFNULL(i.variant_of, i.item_code)
#                         ) AS first_variant
#                             ON item2.item_code = first_variant.first_item_code
#                         WHERE 
#                             item2.item_subcategory = item.item_subcategory
#                             AND item2.image IS NOT NULL
#                             AND (item2.front_view IS NULL OR item2.image != item2.front_view)
#                         ORDER BY item2.creation DESC
#                         LIMIT 1
#                     ) AS first_image

#                 FROM `tabItem` AS item

#                 JOIN `tabAttribute Value` AS tav 
#                     ON item.item_subcategory = tav.name

#                 LEFT JOIN `tabBOM` AS bom 
#                     ON item.item_code = bom.item

#                 WHERE 
#                     tav.is_subcategory = 1
#                     AND item.item_subcategory IS NOT NULL
#                     AND item.item_category = %s

#                 GROUP BY 
#                     item.item_subcategory

#                 ORDER BY 
#                     item.item_subcategory
#             """

#             result = frappe.db.sql(sql_query, (categoryName,), as_dict=True)

#         return result

#     except Exception as e:
#         return {"error": str(e)}


# @frappe.whitelist(allow_guest=True)
# def subcategory_count(categoryName, user_type, customer=None):
#     try:
#         if user_type == "Customer":
#             sql_query = """
#                 SELECT 
#                     ti.item_category,
#                     ti.item_subcategory,
#                     tb.metal_type,
#                     COUNT(DISTINCT IFNULL(ti.variant_of, ti.name)) AS item_count,
#                     COUNT(DISTINCT IFNULL(ti.variant_of, ti.name)) AS serial_count,
#                     MIN(ti.image) AS first_image
                    
#                 FROM `tabCataloge Item Details` AS tci
        
#                 JOIN `tabCataloge Master` AS tcm 
#                     ON tcm.name = tci.parent
#                     AND tcm.customer = %s
        
#                 JOIN `tabItem` AS ti 
#                     ON ti.name = tci.item_code
#                     AND ti.item_category = %s
        
#                 JOIN `tabAttribute Value` AS tav 
#                     ON tav.name = ti.item_subcategory
#                     AND tav.is_subcategory = 1
        
#                 JOIN `tabBOM` AS tb 
#                     ON tb.item = ti.name
#                     AND tb.is_active = 1
#                     AND tb.bom_type = 'Finish Goods'
        
#                 LEFT JOIN `tabSerial No` AS se
#                     ON se.item_code = ti.name
#                     AND se.status = 'Active'
        
#                 WHERE 
#                     ti.item_subcategory IS NOT NULL
        
#                 GROUP BY 
#                     ti.item_category,
#                     ti.item_subcategory,
#                     tb.metal_type
        
#                 ORDER BY 
#                     ti.item_category,
#                     ti.item_subcategory,
#                     tb.metal_type
#             """
#             result = frappe.db.sql(sql_query, (customer, categoryName), as_dict=True)

#         else:
#             sql_query = """
#                 SELECT
#                     item.item_subcategory,

#                     COUNT(DISTINCT CASE
#                         WHEN bom.bom_type = 'Finish Goods' AND bom.is_active = 1 
#                         THEN IFNULL(item.variant_of, item.name)
#                     END) AS item_count,

#                     COUNT(DISTINCT CASE
#                         WHEN bom.bom_type = 'Finish Goods' AND bom.is_active = 1 
#                         THEN IFNULL(item.variant_of, item.name)
#                     END) AS serial_count,

#                     (
#                         SELECT item2.image
#                         FROM `tabItem` AS item2
#                         INNER JOIN (
#                             SELECT
#                                 IFNULL(i.variant_of, i.item_code) AS group_key,
#                                 MIN(i.item_code) AS first_item_code
#                             FROM `tabItem` AS i
#                             INNER JOIN `tabBOM` AS b 
#                                 ON i.item_code = b.item 
#                                 AND b.bom_type = 'Finish Goods'
#                             INNER JOIN `tabItem Default` AS idf3 
#                                 ON i.item_name = idf3.parent
#                                 AND idf3.company = 'Gurukrupa Export Private Limited'
#                             GROUP BY IFNULL(i.variant_of, i.item_code)
#                         ) AS first_variant
#                             ON item2.item_code = first_variant.first_item_code
#                         WHERE 
#                             item2.item_subcategory = item.item_subcategory
#                             AND item2.image IS NOT NULL
#                             AND (item2.front_view IS NULL OR item2.image != item2.front_view)
#                         ORDER BY item2.creation DESC
#                         LIMIT 1
#                     ) AS first_image

#                 FROM `tabItem` AS item

#                 JOIN `tabAttribute Value` AS tav 
#                     ON item.item_subcategory = tav.name

#                 LEFT JOIN `tabBOM` AS bom 
#                     ON item.item_code = bom.item

#                 WHERE 
#                     tav.is_subcategory = 1
#                     AND item.item_subcategory IS NOT NULL
#                     AND item.item_category = %s

#                 GROUP BY 
#                     item.item_subcategory

#                 ORDER BY 
#                     item.item_subcategory
#             """

#             result = frappe.db.sql(sql_query, (categoryName,), as_dict=True)

#         return result

#     except Exception as e:
#         return {"error": str(e)}


@frappe.whitelist(allow_guest=True)
def subcategory_count(categoryName, user_type, customer=None):
    try:
        if user_type == "Customer":
            # ── Redis Cache (customer-specific) ─────────────────────────────
            cache_key = f"subcat_count_{categoryName}_{customer}"
            cached = frappe.cache().get_value(cache_key)
            if cached:
                return cached

            # ── STEP 1: Count query ──────────────────────────────────────────
            count_query = """
                SELECT 
                    ti.item_category,
                    ti.item_subcategory,
                    tb.metal_type,
                    COUNT(DISTINCT IFNULL(ti.variant_of, ti.name)) AS item_count,
                    COUNT(DISTINCT se.name)                         AS serial_count

                FROM `tabCataloge Item Details` AS tci

                JOIN `tabCataloge Master` AS tcm 
                    ON tcm.name = tci.parent
                    AND tcm.customer = %s

                JOIN `tabItem` AS ti 
                    ON ti.name = tci.item_code
                    AND ti.item_category = %s

                JOIN `tabAttribute Value` AS tav 
                    ON tav.name = ti.item_subcategory
                    AND tav.is_subcategory = 1

                JOIN `tabBOM` AS tb 
                    ON tb.item = ti.name
                    AND tb.is_active = 1
                    AND tb.is_default = 1
                    AND tb.bom_type = 'Finish Goods'

                LEFT JOIN `tabSerial No` AS se
                    ON se.item_code = ti.name
                    AND se.status = 'Active'

                WHERE 
                    ti.item_subcategory IS NOT NULL

                GROUP BY 
                    ti.item_category,
                    ti.item_subcategory,
                    tb.metal_type

                ORDER BY 
                    ti.item_category,
                    ti.item_subcategory,
                    tb.metal_type
            """
            result = frappe.db.sql(count_query, (customer, categoryName), as_dict=True)

            # ── STEP 2: first_image alag IN query se ────────────────────────
            if result:
                subcategories = list({row.item_subcategory for row in result if row.item_subcategory})

                if subcategories:
                    image_rows = frappe.db.sql("""
                        SELECT 
                            item2.item_subcategory,
                            item2.image AS first_image
                        FROM `tabItem` AS item2
                        INNER JOIN (
                            SELECT 
                                item_subcategory,
                                MAX(creation) AS latest_creation
                            FROM `tabItem`
                            WHERE 
                                item_subcategory IN %(subs)s
                                AND image IS NOT NULL
                                AND item_category = %(cat)s
                                AND (front_view IS NULL OR image != front_view)
                            GROUP BY item_subcategory
                        ) AS latest
                            ON item2.item_subcategory = latest.item_subcategory
                            AND item2.creation = latest.latest_creation
                        WHERE 
                            item2.item_subcategory IN %(subs)s
                            AND item2.image IS NOT NULL
                        GROUP BY item2.item_subcategory
                    """, {"subs": tuple(subcategories), "cat": categoryName}, as_dict=True)

                    image_map = {r.item_subcategory: r.first_image for r in image_rows}

                    for row in result:
                        row["first_image"] = image_map.get(row.item_subcategory)

            # ── Cache save karo 5 min ke liye ───────────────────────────────
            frappe.cache().set_value(cache_key, result, expires_in_sec=300)

        else:
            # ── Redis Cache check (non-customer data same hota hai) ──────────
            cache_key = f"subcat_count_{categoryName}"
            cached = frappe.cache().get_value(cache_key)
            if cached:
                return cached

            # ── STEP 1: Count query ──────────────────────────────────────────
            count_query = """
                SELECT
                    item.item_subcategory,
                    COUNT(DISTINCT IFNULL(item.variant_of, item.item_code)) AS item_count,
                    COUNT(DISTINCT se.name)                                  AS serial_count

                FROM `tabItem` AS item

                JOIN `tabAttribute Value` AS tav 
                    ON item.item_subcategory = tav.name
                    AND tav.is_subcategory = 1

                INNER JOIN `tabBOM` AS bom 
                    ON item.item_code = bom.item
                    AND bom.is_active = 1
                    AND bom.bom_type = 'Finish Goods'

                INNER JOIN `tabItem Default` AS idf
                    ON item.item_code = idf.parent
                    AND idf.company = 'Gurukrupa Export Private Limited'

                LEFT JOIN `tabSerial No` AS se
                    ON se.item_code = item.item_code
                    AND se.status = 'Active'

                WHERE 
                    item.item_subcategory IS NOT NULL
                    AND item.item_category = %s

                GROUP BY 
                    item.item_subcategory

                ORDER BY 
                    item.item_subcategory
            """
            result = frappe.db.sql(count_query, (categoryName,), as_dict=True)

            # ── STEP 2: first_image alag IN query se ────────────────────────
            if result:
                subcategories = list({row.item_subcategory for row in result if row.item_subcategory})

                if subcategories:
                    image_rows = frappe.db.sql("""
                        SELECT 
                            item2.item_subcategory,
                            item2.image AS first_image
                        FROM `tabItem` AS item2
                        INNER JOIN (
                            SELECT 
                                item_subcategory,
                                MAX(creation) AS latest_creation
                            FROM `tabItem`
                            WHERE 
                                item_subcategory IN %(subs)s
                                AND image IS NOT NULL
                                AND item_category = %(cat)s
                                AND (front_view IS NULL OR image != front_view)
                            GROUP BY item_subcategory
                        ) AS latest
                            ON item2.item_subcategory = latest.item_subcategory
                            AND item2.creation = latest.latest_creation
                        WHERE 
                            item2.item_subcategory IN %(subs)s
                            AND item2.image IS NOT NULL
                        GROUP BY item2.item_subcategory
                    """, {"subs": tuple(subcategories), "cat": categoryName}, as_dict=True)

                    image_map = {r.item_subcategory: r.first_image for r in image_rows}

                    for row in result:
                        row["first_image"] = image_map.get(row.item_subcategory)

            # ── Cache save karo 5 min ke liye ───────────────────────────────
            frappe.cache().set_value(cache_key, result, expires_in_sec=300)

        return result

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "subcategory_count Error")
        return {"error": str(e)}

       
# @frappe.whitelist()
# def category_count(user_type, customer=None):
#     try:
#         if user_type == "Customer":
#             # sql_query = """
#             #     SELECT 
#             #         ti.item_category,
#             #         ti.item_subcategory, 
#             #         COUNT(
#             #             DISTINCT CASE
#             #                 WHEN fbom.bom_type = 'Finish Goods' 
#             #                     AND fbom.is_active = 1 
#             #                 THEN fbom.item
#             #             END
#             #         ) AS item_count,
#             #         COUNT(
#             #             DISTINCT CASE
#             #                 WHEN fbom.bom_type = 'Finish Goods' 
#             #                     AND fbom.is_active = 1 
#             #                 THEN fbom.item
#             #             END
#             #         ) AS serial_count
#             #         COUNT(
#             #             DISTINCT CASE
#             #                 WHEN fbom.bom_type = 'Finish Goods' 
#             #                     AND fbom.is_active = 1 
#             #                 THEN fbom.item
#             #             END
#             #         ) AS total_item_count
#             #     FROM `tabCataloge Item Details` AS tci
#             #     LEFT JOIN `tabCataloge Master` AS tcm ON tcm.name = tci.parent
#             #     LEFT JOIN `tabItem` AS ti ON ti.name = tci.item_code
#             #     LEFT JOIN `tabBOM` AS tb ON ti.name = tb.item
#             #     LEFT JOIN `tabBOM` AS fbom ON fbom.item = ti.name  -- For serial_count
#             #     JOIN `tabAttribute Value` AS tav ON ti.item_category = tav.name
#             #     WHERE  
#             #         ((tav.is_category = 1 AND ti.item_category IS NOT NULL)
#             #         OR 
#             #         (fbom.bom_type = 'Finish Goods' AND tb.is_active = 1))
#             #         AND
#             #         tcm.customer = %(customer)s
#             #         AND tb.is_active = 1
#             #     GROUP BY 
#             #         ti.item_category,
#             #         # ti.item_subcategory
#             #     ORDER BY 
#             #         ti.item_category,
#             #         ti.item_subcategory
        
#             # """
#             sql_query = """
#                 SELECT 
#                     ti.item_category,
#                     COUNT(
#                         DISTINCT CASE
#                             WHEN fbom.bom_type = 'Finish Goods' 
#                                 AND fbom.is_active = 1 
#                             THEN fbom.item
#                         END
#                     ) AS item_count,
#                     COUNT(
#                         DISTINCT CASE
#                             WHEN fbom.bom_type = 'Finish Goods' 
#                                 AND fbom.is_active = 1 
#                             THEN fbom.item
#                         END
#                     ) AS serial_count
#                 FROM `tabCataloge Item Details` AS tci
#                 LEFT JOIN `tabCataloge Master` AS tcm ON tcm.name = tci.parent
#                 LEFT JOIN `tabItem` AS ti ON ti.name = tci.item_code
#                 LEFT JOIN `tabBOM` AS tb ON ti.name = tb.item
#                 LEFT JOIN `tabBOM` AS fbom ON fbom.item = ti.name
#                 JOIN `tabAttribute Value` AS tav ON ti.item_category = tav.name
#                 WHERE  
#                     ((tav.is_category = 1 AND ti.item_category IS NOT NULL)
#                     OR 
#                     (fbom.bom_type = 'Finish Goods' AND tb.is_active = 1))
#                     AND tcm.customer = %(customer)s
#                     AND tb.is_active = 1
#                 GROUP BY 
#                     ti.item_category
#                 ORDER BY 
#                     ti.item_category
#             """

#             values = {"customer": customer}
#         else:
#             # sql_query = """
#             #     SELECT
#             #         item.item_category,
#             #         # item.item_subcategory,
#             #         COUNT(
#             #             DISTINCT CASE
#             #                 WHEN tav.is_category = 1 
#             #                      AND item.item_category IS NOT NULL 
#             #                      AND bom.bom_type = 'Finish Goods' 
#             #                      AND bom.is_active = 1
#             #                 THEN item.name
#             #             END
#             #         ) AS item_count,
#             #         COUNT(
#             #             DISTINCT CASE
#             #                 WHEN tav.is_category = 1 
#             #                      AND item.item_category IS NOT NULL
#             #                      AND bom.bom_type = 'Finish Goods' 
#             #                      AND bom.is_active = 1 
#             #                 THEN item.name
#             #             END
#             #         ) AS serial_count
#             #     FROM 
#             #         `tabItem` AS item
#             #     JOIN 
#             #         `tabAttribute Value` AS tav ON item.item_category = tav.name
#             #     LEFT JOIN 
#             #         `tabBOM` AS bom ON item.item_code = bom.item
#             #     WHERE 
#             #         (tav.is_category = 1 AND item.item_category IS NOT NULL)
#             #         OR 
#             #         (bom.bom_type = 'Finish Goods' AND bom.is_active = 1)
#             #     GROUP BY 
#             #         item.item_category
#             #         limit 5
#             # """
#             sql_query = """
#             SELECT
#                     item.item_category,
#                     COUNT(DISTINCT CASE WHEN bom.item_code IS NOT NULL THEN item.name END) AS item_count
#                 FROM
#                     `tabItem` AS item
#                 JOIN
#                     `tabAttribute Value` AS tav
#                         ON item.item_category = tav.name
#                 LEFT JOIN (
#                     SELECT DISTINCT item AS item_code
#                     FROM `tabBOM`
#                     WHERE bom_type = 'Finish Goods'
#                     AND is_active = 1
#                 ) AS bom ON item.item_code = bom.item_code
#                 WHERE
#                     tav.is_category = 1
#                     AND item.item_category IS NOT NULL
#                 GROUP BY
#                     item.item_category
#             """
#             values = {}

#         # Execute query safely
#         result = frappe.db.sql(sql_query, values=values, as_dict=True)
#         return result

#     except Exception as e:
#         frappe.log_error(f"Category Count Error: {str(e)}", "category_count")
#         return {"error": str(e)}


@frappe.whitelist()
def category_count(user_type, customer=None):
    try:

        if user_type == "Customer":

            sql_query = """
                SELECT 
                    ti.item_category,

                    COUNT(
                        DISTINCT IFNULL(
                            ti.variant_of,
                            ti.name
                        )
                    ) AS item_count

                FROM `tabCataloge Item Details` AS tci

                INNER JOIN `tabCataloge Master` AS tcm
                    ON tcm.name = tci.parent
                    AND tcm.customer = %(customer)s

                INNER JOIN `tabItem` AS ti
                    ON ti.name = tci.item_code

                INNER JOIN `tabAttribute Value` AS tav
                    ON ti.item_category = tav.name
                    AND tav.is_category = 1

                INNER JOIN `tabBOM` AS bom
                    ON ti.name = bom.item
                    AND bom.is_active = 1
                    AND bom.bom_type = 'Finish Goods'
                    AND is_default=1

                WHERE
                    ti.item_category IS NOT NULL

                GROUP BY
                    ti.item_category

                ORDER BY
                    ti.item_category
            """

            values = {
                "customer": customer
            }

        else:

            sql_query = """
                SELECT
                    item.item_category,

                    COUNT(
                        DISTINCT IFNULL(
                            item.variant_of,
                            item.name
                        )
                    ) AS item_count

                FROM `tabItem` AS item

                INNER JOIN `tabAttribute Value` AS tav
                    ON item.item_category = tav.name
                    AND tav.is_category = 1

                INNER JOIN `tabBOM` AS bom
                    ON item.name = bom.item
                    AND bom.is_active = 1
                    AND bom.bom_type = 'Finish Goods'
                    # AND bom.is_default = 1

                INNER JOIN `tabItem Default` AS idf
                    ON item.name = idf.parent
                    AND idf.company = 'Gurukrupa Export Private Limited'

                WHERE
                    item.item_category IS NOT NULL

                GROUP BY
                    item.item_category

                ORDER BY
                    item.item_category
            """

            values = {}

        # ── Execute Query ─────────────────────────────────────
        result = frappe.db.sql(
            sql_query,
            values=values,
            as_dict=True
        )

        return result

    except Exception as e:

        frappe.log_error(
            frappe.get_traceback(),
            "category_count Error"
        )

        return {
            "error": str(e)
        }


@frappe.whitelist(allow_guest=True)
def get_attribute_data():
    # Get setting types
    setting_type = frappe.get_all("Attribute Value", filters={"is_setting_type": 1}, pluck="name")
    setting_type = sorted(setting_type)
    setting_type_data = [{"setting_type": name} for name in setting_type]

    # Get metal types
    excluded_values = ["Gold", "Silver", "Platinum"]
    metal_type = frappe.get_all("Attribute Value", filters={"is_metal_type": 1}, pluck="name")
    metal_type = [name for name in metal_type if name in excluded_values]
    metal_type = sorted(metal_type)
    metal_type_data = [{"metal_type": name} for name in metal_type]

    #Get metal touch
    metal_touch = frappe.get_all("Attribute Value", filters={"is_metal_touch": 1}, pluck="name")
    metal_touch = sorted(metal_touch)
    metal_touch_data = [{"metal_touch": name} for name in metal_touch ]
    
    metal_color = frappe.get_all("Attribute Value", filters={"is_metal_colour": 1}, pluck="name")
    metal_color = sorted(metal_color)
    metal_color_data = [{"metal_color": name} for name in metal_color ]
    
    diamond_quality = frappe.get_all("Attribute Value", filters={"is_diamond_quality": 1}, pluck="name")
    diamond_quality = sorted(diamond_quality)
    diamond_quality_data = [{"diamond_quality": name} for name in diamond_quality ]

    stone_excluded_values = ["1 Mukhi","2 Mukhi","3 Mukhi","4 Mukhi","5 Mukhi","6 Mukhi","7 Mukhi","8 Mukhi","9 Mukhi","10 Mukhi", "Beeds", "Trillion"]
    stone_shape = frappe.get_all("Attribute Value", filters={"is_stone_shape": 1}, pluck="name")
    stone_shape = [name for name in stone_shape if name not in stone_excluded_values]
    stone_shape = sorted(stone_shape)
    diamond_stone_shape = [{"stone_shape": name} for name in stone_shape] 

    gemstone_stone = frappe.get_all("Attribute Value", filters={"is_stone_shape": 1}, pluck="name")
    gemstone_stone = sorted(gemstone_stone)
    gemstone_stone_data = [{"gemstone_shape": name} for name in gemstone_stone ]
    
    diamond_sieve_size_range = frappe.get_all("Attribute Value", filters={"is_diamond_sieve_size_range": 1}, pluck="name")
    diamond_sieve_size_range = sorted(diamond_sieve_size_range)
    diamond_sieve_size_range_data = [{"sieve_size_range": name} for name in diamond_sieve_size_range ]
   
    diamond_sieve_size = frappe.get_all("Attribute Value", filters={"is_diamond_sieve_size": 1}, pluck="name")
    diamond_sieve_size = sorted(diamond_sieve_size)
    diamond_sieve_size_data = [{"sieve_size": name} for name in diamond_sieve_size ]
    
   # Get occasion values from Item Attribute child table    
    occasion = frappe.get_all(
        "Item Attribute Value",
        filters={"parent":"Occasion"},
        pluck="attribute_value"
    )
    occasion = sorted(occasion)
    occasion_data = [{"occasion":name} for name in occasion]
    
    
    # occasion = frappe.get_all(
    #     "Item Attribute Value",
    #     filters={"parent": "Occasion"},
    #     pluck="attribute_value"
    # )

    # # Clean + remove null + strip spaces
    # occasion = [o.strip() for o in occasion if o]

    # # Remove duplicates + sort
    # occasion = sorted(list(set(occasion)))

    # # Convert to dict format
    # occasion_data = [{"occasion": name} for name in occasion]
    
    
    finding_sub_category = frappe.get_all("Attribute Value", filters={"is_finding_type": 1}, pluck="name")
    finding_sub_category = sorted(finding_sub_category)
    finding_subcategory_data = [{"finding_sub_category": name} for name in finding_sub_category ]
    
     # Age Group — same pattern as occasion
    age_group = frappe.get_all(
        "Item Attribute Value",
        filters={"parent": "Age Group"},
        pluck="attribute_value"
    )
    age_group = sorted(age_group)
    age_group_data = [{"age_group": name} for name in age_group]
    
  # Gender — original function ki tarah
    gender = frappe.get_all(
        "Attribute Value",
        filters={"parent_attribute_value": "Gender"},
        pluck="name"
    )
    gender = sorted(gender)
    gender_data = [{"gender": name} for name in gender]
    
    # design_style
    design_style = frappe.get_all(
        "Attribute Value",
        filters={"parent_attribute_value": "Design Style"},
        pluck="name"
    )
    
    design_style = sorted(design_style)
    design_style = [{"design_style": name} for name in design_style]
    
    # religious
    custom_religious = frappe.get_all(
        "Attribute Value",
        filters={"parent_attribute_value": "Religious"},
        pluck="name"
    )
    
    custom_religious = sorted(custom_religious)
    custom_religious = [{"custom_religious": name} for name in custom_religious]
    
    
    # Collection
    collection = frappe.get_all(
        "Attribute Value",
        filters={"parent_attribute_value": "Collection"},
        pluck="name"
    )
    collection=sorted(collection)
    get_collection = [{"collection":name} for name in collection]
   

    Rhodium = frappe.get_doc("Item Attribute", "Rhodium")
    rhodium_data = [
        {"rhodium": row.attribute_value}
        for row in Rhodium.item_attribute_values
    ]
    return {
        "setting_types": setting_type_data,
        "metal_types": metal_type_data,
        "metal_touch": metal_touch_data,
        "diamond_quality": diamond_quality_data,
        "metal_color": metal_color_data,
        "stone_shape": diamond_stone_shape,
        "gemstone_shape": gemstone_stone_data,
        "sieve_size_range": diamond_sieve_size_range_data,
        "occasion": occasion_data,
        # "sieve_size": diamond_sieve_size_data,
        "finding_sub_category": finding_subcategory_data,
        "age_group":age_group_data,
        "gender_data":gender_data,
        "collection_data":get_collection,
        "rhodium":rhodium_data,
        "custom_religious":custom_religious,
        "design_style":design_style
    }


@frappe.whitelist(allow_guest=True)
def get_customers_attribute_data(customer):
    setting_type = frappe.get_all("Attribute Value", filters={"is_setting_type": 1}, pluck="name")
    setting_type = sorted(setting_type)
    setting_type_data = [{"setting_type": name} for name in setting_type]

    # Metal Criteria
    metal_touch = frappe.get_all("Metal Criteria", filters={"parent": customer}, pluck="metal_touch")
    metal_touch = sorted(metal_touch)
    metal_touch_data = [{"metal_touch": name} for name in metal_touch ]
    
    # Customer Diamond Grade
    # diamond_quality = frappe.get_all("Customer Diamond Grade", filters={"parent": customer}, pluck="diamond_quality")
    # diamond_quality = sorted(diamond_quality)
    # diamond_quality_data = [{"diamond_quality": name} for name in diamond_quality ]
    
    catalog_master = frappe.get_value(
        "Cataloge Master",
        {"customer": customer},
        "name"
    )

    if catalog_master:
        catalog_doc = frappe.get_doc("Cataloge Master", catalog_master)
        cust_dia = frappe.get_all("Customer Diamond Grade", filters={"parent": customer}, pluck="diamond_quality")

        diamond_quality_data = []
        for row in catalog_doc.diamond_quality:
            if row.diamond_quality in cust_dia:
                diamond_quality_data.append({"diamond_quality": row.diamond_quality})
        
    stone_excluded_values = ["1 Mukhi","2 Mukhi","3 Mukhi","4 Mukhi","5 Mukhi","6 Mukhi","7 Mukhi","8 Mukhi","9 Mukhi","10 Mukhi", "Beeds", "Trillion"]
    stone_shape = frappe.get_all("Attribute Value", filters={"is_stone_shape": 1}, pluck="name")
    stone_shape = [name for name in stone_shape if name not in stone_excluded_values]
    stone_shape = sorted(stone_shape)
    diamond_stone_shape = [{"stone_shape": name} for name in stone_shape] 

    gemstone_stone = frappe.get_all("Attribute Value", filters={"is_stone_shape": 1}, pluck="name")
    gemstone_stone = sorted(gemstone_stone)
    gemstone_stone_data = [{"gemstone_shape": name} for name in gemstone_stone ]

    metal_color = frappe.get_all("Attribute Value", filters={"is_metal_colour": 1}, pluck="name")
    metal_color = sorted(metal_color)
    metal_color_data = [{"metal_color": name} for name in metal_color ]
    
    finding_sub_category = frappe.get_all("Attribute Value", filters={"is_finding_type": 1}, pluck="name")
    finding_sub_category = sorted(finding_sub_category)
    finding_subcategory_data = [{"finding_sub_category": name} for name in finding_sub_category ]
    
       # Get occasion values from Item Attribute child table    
    occasion = frappe.get_all(
        "Item Attribute Value",
        filters={"parent":"Occasion"},
        pluck="attribute_value"
    )
    occasion = sorted(occasion)
    occasion_data = [{"occasion":name} for name in occasion]
    
     # Age Group — same pattern as occasion
    age_group = frappe.get_all(
        "Item Attribute Value",
        filters={"parent": "Age Group"},
        pluck="attribute_value"
    )
    age_group = sorted(age_group)
    age_group_data = [{"age_group": name} for name in age_group]
    
      # Gender — original function ki tarah
    gender = frappe.get_all(
        "Attribute Value",
        filters={"parent_attribute_value": "Gender"},
        pluck="name"
    )
    gender = sorted(gender)
    gender_data = [{"gender": name} for name in gender]
    
      # Collection
    collection = frappe.get_all(
        "Attribute Value",
        filters={"parent_attribute_value": "Collection"},
        pluck="name"
    )
    collection=sorted(collection)
    get_collection = [{"collection":name} for name in collection]
    
    Rhodium = frappe.get_doc("Item Attribute", "Rhodium")
    rhodium_data = [
        {"rhodium": row.attribute_value}
        for row in Rhodium.item_attribute_values
    ]

    return { 
        "setting_types": setting_type_data,
        "metal_touch": metal_touch_data,
        "diamond_quality": diamond_quality_data, 
        "metal_color": metal_color_data,
        "diamond_stone_shape":diamond_stone_shape,
        "gemstone_stone_data":gemstone_stone_data,
        "occasion":occasion_data,
        "finding_subcategory_data":finding_subcategory_data,
        "age_group":age_group_data,
        "gender_data":gender_data,
        "collection_data":get_collection,
        "rhodium":rhodium_data
    }

@frappe.whitelist()
def get_selected_item_for_customer_by_user(items, customers):
    """
    Save selected items to 'Cataloge Master' for one or more customers.
    Supports trending value updates item added by user to the customer.
    """

    # Parse JSON if string
    if isinstance(items, str):
        items = json.loads(items)

    if isinstance(customers, str):
        customers = json.loads(customers)

    if not items or not customers:
        frappe.throw("Both 'items' and 'customers' are required.")

    # items = [ { item1: trending1, item2: trending2 } ]
    items_dict = items[0]

    results = []

    for customer in customers:

        customer_found = frappe.db.get_list(
            "Cataloge Master",
            filters={"customer": customer},
            fields=["name"]
        )

        customer_id = frappe.db.get_list(
            "Customer",
            filters={"name": customer},
            fields=["email_id"]
        )

        # frappe.throw(f"{customer_id}")

        # ---------------------------------------------------------
        # CUSTOMER EXISTS
        # ---------------------------------------------------------
        if customer_found:

            catalog_doc = frappe.get_doc("Cataloge Master", customer_found[0].name)

            # Build lookup: existing item_code → trending
            existing_items = {
                row.item_code: row.trending
                for row in catalog_doc.cataloge_item_details
            }

            added = []
            updated = []

            for item_code, trending_value in items_dict.items():

                # ----------------- NEW ITEM -----------------
                if item_code not in existing_items:
                    catalog_doc.append("cataloge_item_details", {
                        "item_code": item_code,
                        "item_name": item_code,
                        "trending": trending_value
                    })
                    added.append(item_code)

                # ----------------- UPDATE TRENDING -----------------
                # else:
                #     if row.item_code == item_code:
                #         if row.trending == 1:
                #             frappe.throw("Item already exists.")
                #     old_val = existing_items[item_code]
                #     if old_val != trending_value:
                #         for row in catalog_doc.cataloge_item_details:
                #             if row.item_code == item_code:
                #                 row.trending = trending_value
                #                 updated.append(item_code)
                #                 break
                else:
                    old_val = existing_items[item_code]
                
                    for row in catalog_doc.cataloge_item_details:
                        if row.item_code == item_code:
                
                            if row.trending == 1:
                                frappe.throw("Item already exists.")
                
                            if old_val != trending_value:
                                row.trending = trending_value
                                updated.append(item_code)
                
                            break

            catalog_doc.save()
            frappe.db.commit()

            results.append({
                "customer": customer,
                "added_items": added,
                "updated_items": updated,
                "message": f"Added {len(added)}, Updated {len(updated)} for customer {customer}"
            })

            # notify_user(customer_id[0].email_id, f"Cataloge Master Added {len(added)}, Updated {len(updated)} for customer You", f"Cataloge Master Added {len(added)}, Updated {len(updated)} for customer You")

        # ---------------------------------------------------------
        # NEW CUSTOMER → CREATE CATALOG
        # ---------------------------------------------------------
        else:
            catalog_doc = frappe.new_doc("Cataloge Master")
            catalog_doc.customer = customer

            for item_code, trending_value in items_dict.items():
                catalog_doc.append("cataloge_item_details", {
                    "item_code": item_code,
                    "item_name": item_code,
                    "trending": trending_value
                })

            catalog_doc.insert()
            frappe.db.commit()

            results.append({
                "customer": customer,
                "added_items": list(items_dict.keys()),
                "updated_items": [],
                "message": f"Created new Cataloge Master for {customer}"
            })

            # notify_user(customer_id[0].email_id, "Cataloge Master New Catloug Master Created For You", "Cataloge Master New Catloug Master Created For You")

    return {
        "status": "success",
        "results": results
    }

# //shubham
@frappe.whitelist(allow_guest=True)
def catalogue_data_with_trending_item(selectedSubcategory, customer, metalType = None):
    selectedSubcategory = frappe.form_dict.get("selectedSubcategory")
    itemCode = frappe.form_dict.get("itemCode")
    itemCategory = frappe.form_dict.get("itemCategory")
    metalType = frappe.form_dict.get("metalType")

    where_clause = """
        # idf.company = 'Gurukrupa Export Private Limited'
        # AND (bom.bom_type = 'Finish Goods' OR bom.bom_type = 'Template'
        idf.company = 'Gurukrupa Export Private Limited' AND 
        bom.bom_type = 'Finish Goods'
        #   OR bom.bom_type = 'Template'
    """

    if selectedSubcategory:
        where_clause = where_clause + f" AND item.item_subcategory = '{selectedSubcategory}' "
    if metalType:
        where_clause = where_clause + f" AND bom.metal_type = '{metalType}' "
    
    if itemCode:
        where_clause = where_clause + f" AND item.item_code = '{itemCode}' "
    if itemCategory:
        where_clause = where_clause + f" AND item.item_category = '{itemCategory}' "
    # if customer:
    #     where_clause = where_clause + f" AND cm."

    db_data = frappe.db.sql(
        f""" SELECT
                item.name,
                bom.name,
                idf.company,
                item.creation,
                item.item_code,
                item.item_category,
                item.image,
                item.sketch_image,
                item.cad_3d_image,
                item.`3d_videos_1` ,
                item.item_subcategory,
                bom.tag_no,
                item.setting_type,
                FORMAT(bom.gross_weight,3) AS gross_metal_weight,
                FORMAT(bom.metal_and_finding_weight, 3) AS net_metal_finding_weight,
                FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
                FORMAT(bom.other_weight,3) AS other_weight,
                FORMAT(bom.finding_weight_,3) AS finding_weight_,
                bom.metal_colour,
                bom.metal_purity,
                FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,
                bom.total_diamond_pcs,
                bom.total_gemstone_pcs,
                FORMAT(bom.gemstone_weight,3) AS gemstone_weight,
                FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
                FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
                FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,
                bom.navratna,
                bom.height,
                bom.length,
                bom.width,
                bom.breadth,
                bom.product_size,
                bom.sizer_type,
                bom.design_style,
                bom.nakshi_from,
                bom.vanki_type,
                bom.total_length,
                bom.detachable,
                bom.back_side_size,
                bom.changeable,
                item.variant_of,
                bom.finding_pcs,
                bom.total_other_pcs,
                bom.total_other_weight,
                cm.trending,
                GROUP_CONCAT(DISTINCT item.name) as variant_name,
                GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
                GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,
                GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
                GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
                GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
                GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,
                GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
                GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,
                GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
                GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
                GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
                GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
                GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,
                GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
                GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
                GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size
                
                # GROUP_CONCAT(DISTINCT od.finding_category) AS finding_category,
            FROM
                `tabItem` AS item
            LEFT JOIN
                `tabBOM` AS bom
            ON
                item.item_code = bom.item
            # LEFT JOIN
            #     `tabSerial No` AS sn
            # ON
            #     sn.name = bom.tag_no
            LEFT JOIN
                `tabDesign Attributes`  AS td
            ON
                item.item_code = td.parent
            LEFT JOIN
                `tabBOM Metal Detail` AS mt
            ON
                bom.name = mt.parent
            LEFT JOIN
                `tabBOM Gemstone Detail` AS gd
            ON
                bom.name = gd.parent
            LEFT JOIN
                `tabBOM Diamond Detail` AS dd
            ON
                bom.name = dd.parent
            LEFT JOIN
                `tabBOM Finding Detail` AS fd
            ON
                bom.name = fd.parent
            LEFT JOIN
                `tabBOM Other Detail` AS od
            ON
                bom.name = od.parent
            LEFT JOIN
                `tabItem Default` AS idf
            ON
                item.item_name = idf.parent
                
            INNER JOIN `tabCataloge Master` AS CT
                ON CT.customer = '{customer}'

            INNER JOIN `tabCataloge Item Details` AS cm
                ON cm.parent = CT.name
                AND cm.item_code = item.name

            WHERE
                {where_clause}
            # GROUP BY
            #     item.name, item.creation, item.item_code, item.item_category, item.image, item.item_subcategory, bom.tag_no,
            #     bom.gross_weight, bom.metal_and_finding_weight, bom.total_diamond_weight_in_gms, bom.other_weight,
            #     bom.finding_weight_, bom.total_gemstone_weight_in_gms, item.item_name,item.variant_of
            GROUP BY
                item.item_code, item.variant_of

            ORDER BY
                item.name DESC 
            limit 200
    """,
    as_dict=True)

    return db_data
    
@frappe.whitelist(allow_guest=True)
# def get_catalogue_collection_details(customers, collection, item_category=None, username=None):
def get_catalogue_collection_details(customers, collection=None, username=None):
    
    customer_list = []

    if customers:
        if isinstance(customers, str):
            try:
                customer_list = json.loads(customers)
            except Exception:
                customer_list = [customers]
        else:
            customer_list = customers
    
    elif username:
        user_customers = frappe.db.sql("""
            SELECT parent AS customer
            FROM `tabCustomer Representatives`
            WHERE user_id = %s
        """, (username,), as_dict=True)
        customer_list = [row["customer"] for row in user_customers]

    if not customer_list:
        return {"success": False, "message": "No customers found"}

    catalogue_list = frappe.get_all(
        "Cataloge Master",
        filters={"customer": ["in", customer_list]},
        fields=["name"],
    )

    data = get_data_for_multiple_customer_collections_details(
        catalogue_list=catalogue_list,
        # item_category=item_category,
        collection=collection
    )

    # frappe.throw(f"hii {data}")
    # return {
        # "success": True,
        # "data": data,
    # }
    return data


# def get_data_for_multiple_customer_collections_details(catalogue_list, item_category=None, collection=None):
def get_data_for_multiple_customer_collections_details(catalogue_list, collection=None):
    final_data = []

    for row_doc in catalogue_list:
        doc = frappe.get_doc("Cataloge Master", row_doc.name)

        rows = []
        l = []
        for row in doc.catalogue_collection_details:
            if not collection or row.collection == collection:
                item = frappe.db.get_value(
                    "Item",
                    # {'name': row.item_code, 'item_category': item_category},
                    {'name': row.item_code},
                    ["item_category","item_subcategory", "image"],  # fetch fields you need
                    as_dict=True
                )

                if item and item.get("item_category"):
                    rows.append({
                        "idx": row.idx,
                        "item_code": row.item_code,
                        "collection": row.collection,
                        "name": row.name,
                        "image": item.get("image") if item else "",
                        "item_category": item.get("item_category") if item else "",
                        "item_subcategory": item.get("item_subcategory") if item else "",
                    })

        final_data.append({
            "customer": doc.customer,
            "catalogue_collection_details": rows,
        })
    return final_data

@frappe.whitelist(allow_guest=True)
def get_catalogue_collection_item_data(selectedSubcategory, itemCode):
    selectedSubcategory = frappe.form_dict.get("item_subcategory")
    itemCode = frappe.form_dict.get("itemCode") 

    where_clause = """
        idf.company = 'Gurukrupa Export Private Limited'
        AND (bom.bom_type = 'Finish Goods' OR bom.bom_type = 'Template')
    """

    if selectedSubcategory:
        where_clause = where_clause + f" AND item.item_subcategory = '{selectedSubcategory}' "
    
    if itemCode:
        where_clause = where_clause + f" AND item.item_code = '{itemCode}' " 

    db_data = frappe.db.sql(
        f""" SELECT
                item.name,
                bom.name,
                idf.company,
                tci.trending,
                item.creation,
                item.item_code,
                item.item_category,
                item.stylebio,
                item.image,
                item.sketch_image,
                item.front_view as cad_image,
                CASE
                    WHEN item.front_view = item.image THEN 'CAD Image'
                    ELSE 'FG Image'
                END AS image_remark,
                # item.`3d_videos_1` ,
                item.item_subcategory,
                bom.tag_no,
                bom.diamond_quality,
                item.setting_type,
                FORMAT(bom.gross_weight,3) AS gross_metal_weight,
                FORMAT(bom.metal_and_finding_weight, 3) AS net_metal_finding_weight,
                FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
                FORMAT(bom.other_weight,3) AS other_weight,
                FORMAT(bom.finding_weight_,3) AS finding_weight_,
                bom.metal_touch as bom_touch,
                bom.metal_colour,
                bom.metal_purity,
                FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,
                bom.total_diamond_pcs,
                bom.total_gemstone_pcs,
                FORMAT(bom.gemstone_weight,3) AS gemstone_weight,
                FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
                FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
                FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,
                bom.navratna,
                bom.height,
                bom.length,
                bom.width,
                bom.breadth,
                bom.product_size,
                bom.sizer_type,
                bom.design_style,
                bom.nakshi_from,
                bom.vanki_type,
                bom.total_length,
                bom.detachable,
                bom.back_side_size,
                bom.changeable,
                item.variant_of,
                bom.finding_pcs,
                bom.total_other_pcs,
                bom.total_other_weight,
                GROUP_CONCAT(DISTINCT item.name) as variant_name,
                GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
                GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,
                GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
                GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
                GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
                GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,
                GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
                GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,
                GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
                GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
                GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
                GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
                GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,
                GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
                GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
                GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size
            FROM 
                `tabItem` AS item
            LEFT JOIN 
                `tabCataloge Item Details` AS tci 
            ON 
                tci.item_code = item.name
            LEFT JOIN 
                `tabCataloge Master` AS tcm 
            ON 
                tcm.name = tci.parent
            LEFT JOIN
                `tabBOM` AS bom
            ON
                item.item_code = bom.item
            LEFT JOIN
                `tabDesign Attributes`  AS td
            ON
                item.item_code = td.parent
            LEFT JOIN
                `tabBOM Metal Detail` AS mt
            ON
                bom.name = mt.parent
            LEFT JOIN
                `tabBOM Gemstone Detail` AS gd
            ON
                bom.name = gd.parent
            LEFT JOIN
                `tabBOM Diamond Detail` AS dd
            ON
                bom.name = dd.parent
            LEFT JOIN
                `tabBOM Finding Detail` AS fd
            ON
                bom.name = fd.parent
            LEFT JOIN
                `tabBOM Other Detail` AS od
            ON
                bom.name = od.parent
            LEFT JOIN
                `tabItem Default` AS idf
            ON
                item.item_name = idf.parent
            WHERE
                {where_clause}
            # GROUP BY
            #     item.name, item.creation, item.item_code, item.item_category, item.image, item.item_subcategory, bom.tag_no,
            #     bom.gross_weight, bom.metal_and_finding_weight, bom.total_diamond_weight_in_gms, bom.other_weight,
            #     bom.finding_weight_, bom.total_gemstone_weight_in_gms, item.item_name,item.variant_of
            GROUP BY
                item.item_code, item.variant_of
            ORDER BY
                item.name DESC 
            # limit 200
    """,
    as_dict=True)

    return db_data

@frappe.whitelist(allow_guest=True)
def get_selected_item_count_for_customet_wise(customer_id, collection):
    try:
        # Get all Catalogue Masters for this customer
        catalogue_master_names = frappe.get_all(
            "Cataloge Master",
            filters={"customer": customer_id},
            pluck="name"
        )

        if not catalogue_master_names:
            return []
        
        # Get item codes from child table
        data = frappe.get_all(
            "Catalogue Collection Details",
            filters={
                "parent": ["in", catalogue_master_names],
                "collection": collection 
            },
            fields=["item_code"]
        )

        c = {}

        for i in data:
            get_category = frappe.db.get_value(
                "Item",
                i.item_code,
                ["item_category", "item_code"],
                as_dict=True
            )
            if get_category.item_category in c:
                c[get_category.item_category] += 1
            else:
                c[get_category.item_category] = 1
          
        return c

    except Exception as e:
        frappe.log_error(f"Error in get_selected_item_count_for_customet_wise: {e}")
        return e
    

@frappe.whitelist(allow_guest=True)
def get_wishlist_item_for_customer_by_user(items, customers):
    """
    Save selected items to 'Cataloge Master' for one or more customers.
    Supports trending value updates.
    """

    # Parse JSON if string
    if isinstance(items, str):
        items = frappe.parse_json(items)

    if isinstance(customers, str):
        customers = json.loads(customers)

    if not items or not customers:
        frappe.throw("Both 'items' and 'customers' are required.")

    # if user_type == "User":
    #     frappe.throw("User is not allowed to add the item to wishlist.")

    # items = [ { item1: trending1, item2: trending2 } ]
    items_dict = items[0]

    results = []

    for customer in customers:

        customer_found = frappe.db.get_all(
            "Cataloge Master",
            filters={"customer": customer},
            fields=["name"]
        )

        # frappe.throw(f"{customer_id}")

        # ---------------------------------------------------------
        # CUSTOMER EXISTS
        # ---------------------------------------------------------
        if customer_found:

            catalog_doc = frappe.get_doc("Cataloge Master", customer_found[0].name)
            # catalog_doc.flags.ignore_permissions = True

            # Build lookup: existing item_code → trending
            existing_items = {
                row.item_code: row
                for row in catalog_doc.cataloge_item_details
            }

            added = []
            updated = []

         
            for item_code, trending_value in items_dict.items():

                # skip metadata fields
                if item_code in [
                    "item",
                    "is_folder",
                    "status",
                    "folder_name",
                    "name",
                    "as_per_customized",
                    "job_work",
                    "customized_data",
                    "customer_gold",
                    "customer_diamond",
                    "customer_stone",
                    "as_per_design",
                    "is_duplicate"
                ]:
                    continue

                is_folder = items_dict.get("is_folder")
                as_per_design = items_dict.get("as_per_design")
                job_work = items_dict.get("job_work")
                as_per_customized = items_dict.get("as_per_customized")
                customized_data = items_dict.get("customized_data")
                status = items_dict.get("status")
                folder_name = items_dict.get("folder_name")
                is_duplicate  = items_dict.get("is_duplicate")
                name = items_dict.get("name")
                customer_gold = items_dict.get("customer_gold")
                customer_diamond = items_dict.get("customer_diamond")
                customer_stone = items_dict.get("customer_stone")
                
                # ----------------- NEW ITEM -----------------
                if item_code not in existing_items:

                    row_data = {
                        "item_code": item_code,
                        "item_name": item_code,
                        "wishlist": trending_value,
                        "job_work": job_work,
                        "as_per_customized": as_per_customized,
                        "as_per_design": as_per_design,
                        "customized_data": customized_data,
                        "customer_stone": customer_stone,
                        "customer_diamond": customer_diamond,
                        "customer_gold": customer_gold
                    }

                    catalog_doc.append(
                        "cataloge_item_details",
                        row_data
                    )

                    added.append(item_code)

                    # =====================================================
                    # SAVE FIRST BEFORE FOLDER CREATION
                    # =====================================================

                    catalog_doc.flags.ignore_version = True

                    catalog_doc.save(
                        ignore_permissions=True,
                        ignore_version=True
                    )

                    frappe.db.commit()

                    # reload latest doc to avoid timestamp mismatch
                    # catalog_doc.reload()

                    # rebuild existing_items
                    existing_items = {
                        row.item_code: row
                        for row in catalog_doc.cataloge_item_details
                    }

                    # =====================================================
                    # ADD IN FOLDER
                    # =====================================================

                    if (
                        is_folder == "Yes"
                        and as_per_design == 1
                    ):

                        add_item_in_folder(
                            status,
                            folder_name,
                            items_dict.get("item"),
                            customer
                        )

                    elif (
                        is_folder == "Yes"
                        and as_per_customized == 1
                        and (
                            customer_gold == 1
                            or customer_diamond == 1
                            or customer_stone == 1
                        )
                        and customized_data
                    ):

                        add_item_in_folder(
                            status,
                            folder_name,
                            items_dict.get("item"),
                            customer
                        )

                    elif (
                        is_folder == "Yes"
                        and job_work == 1
                        and as_per_customized == 1
                        and (
                            customer_gold == 1
                            or customer_diamond == 1
                            or customer_stone == 1
                        )
                        and customized_data
                    ):

                        add_item_in_folder(
                            status,
                            folder_name,
                            items_dict.get("item"),
                            customer
                        )

                    elif (
                        is_folder == "Yes"
                        and job_work == 1
                        and (
                            customer_gold == 1
                            or customer_diamond == 1
                            or customer_stone == 1
                        )
                        and customized_data
                    ):

                        add_item_in_folder(
                            status,
                            folder_name,
                            items_dict.get("item"),
                            customer
                        )

                # ----------------- UPDATE ITEM -----------------
                else:
                    old_val = existing_items[item_code]

                    if old_val != trending_value:
                        
                        if is_duplicate == 1:
                            row_data = {
                                "item_code": item_code,
                                "item_name": item_code,
                                "wishlist": trending_value,
                                "job_work": job_work,
                                "as_per_customized": as_per_customized,
                                "as_per_design": as_per_design,
                                "customized_data": customized_data,
                                "customer_stone": customer_stone,
                                "customer_diamond": customer_diamond,
                                "customer_gold": customer_gold
                            }
                            
                            catalog_doc.append(
                                "cataloge_item_details",
                                row_data
                            )

                            added.append(item_code)

                            # =====================================================
                            # SAVE FIRST BEFORE FOLDER CREATION
                            # =====================================================

                            catalog_doc.flags.ignore_version = True

                            catalog_doc.save(
                                ignore_permissions=True,
                                ignore_version=True
                            )

                            frappe.db.commit()      
                        else:
                            row = next(
                                (d for d in catalog_doc.cataloge_item_details if d.item_code == item_code),
                                None
                            )
                            # frappe.throw(f"{row.name}")
                            if row:
                                    row.wishlist = trending_value
                                    row.job_work = job_work
                                    row.as_per_customized = as_per_customized
                                    row.as_per_design = as_per_design
                                    row.customized_data = customized_data
                                    row.customer_gold = customer_gold
                                    row.customer_diamond = customer_diamond
                                    row.customer_stone = customer_stone

                                    updated.append(item_code)
                                    
                                    catalog_doc.flags.ignore_version = True
                                    
                                    catalog_doc.save(
                                        ignore_permissions=True,
                                        ignore_version=True
                                    )

                                    frappe.db.commit()
                            
                                
                                    # same conditions here
                                    if (
                                        is_folder == "Yes"
                                        and as_per_design == 1
                                    ):
                                        # if row.as_per_design == as_per_design and row.item_code == item_code:
                                        #     frappe.throw(f"Item {row.item_code} Is alreday Exist With Design and Folder")
                                        
                                        add_item_in_folder(
                                            status,
                                            folder_name,
                                            items_dict.get("item"),
                                            customer
                                        )

                                    elif (
                                        is_folder == "Yes"
                                        and as_per_customized == 1
                                        and customized_data
                                    ):
                                        # if row.as_per_customized == as_per_customized and row.item_code == item_code and row.customized_data == customized_data:
                                            # frappe.throw(f"Item {row.item_code} Is alreday Exist With Customized and Folder")
                                        
                                        add_item_in_folder(
                                            status,
                                            folder_name,
                                            items_dict.get("item"),
                                            customer
                                        )
                                        
                                    elif (
                                        is_folder == "Yes"
                                        and job_work == 1
                                        and (customer_gold == 1 
                                            or customer_diamond == 1 
                                            or customer_stone == 1
                                            )
                                        and customized_data
                                        ):
                                        
                                        # if row.job_work == job_work and row.item_code == item_code and row.customized_data == customized_data and (row.customer_gold == customer_gold or row.customer_diamond == customer_diamond or row.customer_stone == customer_stone):
                                            # frappe.throw(f"Item {row.item_code} Is alreday Exist With Job Work and Folder")
                                            
                                        add_item_in_folder(
                                            status,
                                            folder_name,
                                            items_dict.get("item"),
                                            customer
                                        )

                                    elif (
                                        is_folder == "Yes"
                                        and job_work == 1 and as_per_customized == 1
                                        and customized_data
                                        and (customer_gold == 1 
                                            or customer_diamond == 1 
                                            or customer_stone == 1
                                        )
                                    ):
                                        # if row.job_work == job_work and row.as_per_customized == as_per_customized and row.item_code == item_code and row.customized_data == customized_data and (row.customer_gold == customer_gold or row.customer_diamond == customer_diamond or row.customer_stone == customer_stone):
                                            # frappe.throw(f"Item {row.item_code} Is alreday Exist With Job Work and Folder")
                                            
                                        add_item_in_folder(
                                            status,
                                            folder_name,
                                            items_dict.get("item"),
                                            customer
                                        )          
                    else:
                           row.wishlist = trending_value
                           row.job_work = job_work
                           row.as_per_customized = as_per_customized
                           row.as_per_design = as_per_design
                           row.customized_data = customized_data
                           row.customer_gold = customer_gold
                           row.customer_diamond = customer_diamond
                           row.customer_stone = customer_stone 
                           
                           updated.append(item_code)
                           
                           catalog_doc.flags.ignore_version = True

                           catalog_doc.save(
                                ignore_permissions=True,
                                ignore_version=True
                            )

                           frappe.db.commit()
                           
                           add_item_in_folder(
                                status,
                                folder_name,
                                items_dict.get("item"),
                                customer
                           )

            results.append({
                "customer": customer,
                "added_items": added,
                "updated_items": updated,
                "message": f"Added {len(added)}, Updated {len(updated)} for customer {customer}"
            })

            # notify_user(customer_id[0].email_id, f"Cataloge Master Added {len(added)}, Updated {len(updated)} for customer You", f"Cataloge Master Added {len(added)}, Updated {len(updated)} for customer You")

        # ---------------------------------------------------------
        # NEW CUSTOMER → CREATE CATALOG
        # ---------------------------------------------------------
        else:
            catalog_doc = frappe.new_doc("Cataloge Master")
            catalog_doc.customer = customer

            added_items = []

            for item_code, trending_value in items_dict.items():

                # skip metadata fields
                if item_code in [
                    "item",
                    "is_folder",
                    "status",
                    "name",
                    "folder_name",
                    "as_per_customized",
                    "job_work",
                    "customized_data",
                    "customer_gold",
                    "customer_diamond",
                    "customer_stone",
                    "as_per_design"
                ]:
                    continue

                is_folder = items_dict.get("is_folder")
                as_per_design = items_dict.get("as_per_design")
                job_work = items_dict.get("job_work")
                as_per_customized = items_dict.get("as_per_customized")
                customized_data = items_dict.get("customized_data")
                status = items_dict.get("status")
                name = items_dict.get("name")
                folder_name = items_dict.get("folder_name")

                customer_gold = items_dict.get("customer_gold")
                customer_diamond = items_dict.get("customer_diamond")
                customer_stone = items_dict.get("customer_stone")

                # if folder and design type == As Per Design
                catalog_doc.append("cataloge_item_details", {
                        "item_code": item_code,
                        "item_name": item_code,
                        "wishlist": trending_value,
                        "job_work" : job_work,
                        "as_per_customized":as_per_customized,
                        "customer_gold":customer_gold,
                        "customer_stone" : customer_stone,
                        "customer_diamond" : customer_diamond,
                        "customized_data": customized_data
                })

                added_items.append(item_code)

                catalog_doc.insert(ignore_permissions=True)
                
                catalog_doc.save(
                            ignore_permissions=True,
                            ignore_version=True
                )

                frappe.db.commit()
                
                if (
                    is_folder == "Yes"
                    and as_per_design == 1
                ):            
                    add_item_in_folder(
                            status,
                            folder_name,
                            items_dict.get("item"),
                            customer
                    )

                elif (
                    is_folder == "Yes"
                    and as_per_customized == 1
                    and customized_data
                ):               
                    add_item_in_folder(
                        status,
                        folder_name,
                        items_dict.get("item"),
                        customer
                    )
                    
                elif (is_folder == "Yes" 
                      and job_work == 1 
                      and (customer_gold == 1 
                            or customer_diamond == 1 
                            or customer_stone == 1
                        ) 
                      and customized_data
                    ):               
                        add_item_in_folder(
                            status,
                            folder_name,
                            items_dict.get("item"),
                            customer
                        )
                
                elif (is_folder == "Yes" 
                      and job_work == 1 and as_per_customized == 1
                      and (customer_gold == 1 
                            or customer_diamond == 1 
                            or customer_stone == 1
                        ) 
                      and customized_data
                    ):                 
                        add_item_in_folder(
                            status,
                            folder_name,
                            items_dict.get("item"),
                            customer
                        )           

                

            results.append({
                "customer": customer,
                "added_items": added_items,
                "updated_items": [],
                "message": f"Created new Cataloge Master for {customer}"
            })
            # notify_user(customer_id[0].email_id, "Cataloge Master New Catloug Master Created For You", "Cataloge Master New Catloug Master Created For You")
            

    return {
        "status": "success",
        "results": results
    }


# @frappe.whitelist(allow_guest=True)
# def get_wishlist_item_for_customer_by_user(items, customers):
#     """
#     Save selected items to 'Cataloge Master' for one or more customers.
#     Supports trending value updates.
#     """

#     # Parse JSON if string
#     if isinstance(items, str):
#         items = frappe.parse_json(items)

#     if isinstance(customers, str):
#         customers = json.loads(customers)

#     if not items or not customers:
#         frappe.throw("Both 'items' and 'customers' are required.")

#     # if user_type == "User":
#     #     frappe.throw("User is not allowed to add the item to wishlist.")

#     # items = [ { item1: trending1, item2: trending2 } ]
#     items_dict = items[0]

#     results = []

#     for customer in customers:

#         customer_found = frappe.db.get_all(
#             "Cataloge Master",
#             filters={"customer": customer},
#             fields=["name"]
#         )

#         # frappe.throw(f"{customer_id}")

#         # ---------------------------------------------------------
#         # CUSTOMER EXISTS
#         # ---------------------------------------------------------
#         if customer_found:

#             catalog_doc = frappe.get_doc("Cataloge Master", customer_found[0].name)
#             # catalog_doc.flags.ignore_permissions = True

#             # Build lookup: existing item_code → trending
#             existing_items = {
#                 row.item_code: row
#                 for row in catalog_doc.cataloge_item_details
#             }

#             added = []
#             updated = []

#             # for item_code, trending_value in items_dict.items():

#             #     # ----------------- NEW ITEM -----------------
#             #     if item_code not in existing_items:
#             #         # if folder and design type == As Per Design then 
#             #         if items_dict.is_folder == "Yes" and items_dict.design_type == "As Per Design":
#             #             add_item_in_folder(items.item_code, items.status, items.name)
#             #             catalog_doc.append("cataloge_item_details", {
#             #                 "item_code": item_code,
#             #                 "item_name": item_code,
#             #                 "wishlist": trending_value,
#             #                 "design_type" : items_dict.design_type
#             #             })
                    
#             #         # if not folder and design type == As Per Customized then 
#             #         if items_dict.is_folder == "No" and items_dict.design_type == "As Per Customized" and items_dict.customized_data:
#             #             # add_item_in_folder(items.item_code, items.status, items.name)
#             #             catalog_doc.append("cataloge_item_details", {
#             #                 "item_code": item_code,
#             #                 "item_name": item_code,
#             #                 "wishlist": trending_value,
#             #                 "design_type" : items_dict.design_type,
#             #                 "customized_data" : items_dict.customized_data
#             #             })
                        
#             #         # if folder and design type == As Per Customized then 
#             #         if items_dict.is_folder == "Yes" and items_dict.design_type == "As Per Customized" and items_dict.customized_data:
#             #             add_item_in_folder(items.item_code, items.status, items.name)
#             #             catalog_doc.append("cataloge_item_details", {
#             #                 "item_code": item_code,
#             #                 "item_name": item_code,
#             #                 "wishlist": trending_value,
#             #                 "design_type" : items_dict.design_type,
#             #                 "customized_data" : items_dict.customized_data
#             #             })
#             #         # if not folder and design type == As Per Design then 
#             #         catalog_doc.append("cataloge_item_details", {
#             #             "item_code": item_code,
#             #             "item_name": item_code,
#             #             "wishlist": trending_value,
#             #             "design_type" : items_dict.design_type
#             #         })
#             #         added.append(item_code)

#             #     # ----------------- UPDATE TRENDING -----------------
#             #     else:
#             #         old_val = existing_items[item_code]
#             #         if old_val != trending_value:
#             #             for row in catalog_doc.cataloge_item_details:
#             #                 if row.item_code == item_code:
#             #                     row.wishlist = trending_value
#             #                     updated.append(item_code)
#             #                     break
#             for item_code, trending_value in items_dict.items():

#                 # skip metadata fields
#                 if item_code in [
#                     "item",
#                     "is_folder",
#                     "status",
#                     "name",
#                     "as_per_customized",
#                     "job_work",
#                     "customized_data",
#                     "customer_gold",
#                     "customer_diamond",
#                     "customer_stone",
#                     "as_per_design",
#                     "is_duplicate"
#                 ]:
#                     continue

#                 is_folder = items_dict.get("is_folder")
#                 as_per_design = items_dict.get("as_per_design")
#                 job_work = items_dict.get("job_work")
#                 as_per_customized = items_dict.get("as_per_customized")
#                 customized_data = items_dict.get("customized_data")
#                 status = items_dict.get("status")
#                 name = items_dict.get("name")
#                 is_duplicate  = items_dict.get("is_duplicate")

#                 customer_gold = items_dict.get("customer_gold")
#                 customer_diamond = items_dict.get("customer_diamond")
#                 customer_stone = items_dict.get("customer_stone")
                
#                 # ----------------- NEW ITEM -----------------
#                 if item_code not in existing_items:

#                     row_data = {
#                         "item_code": item_code,
#                         "item_name": item_code,
#                         "wishlist": trending_value,
#                         "job_work": job_work,
#                         "as_per_customized": as_per_customized,
#                         "as_per_design": as_per_design,
#                         "customized_data": customized_data,
#                         "customer_stone": customer_stone,
#                         "customer_diamond": customer_diamond,
#                         "customer_gold": customer_gold
#                     }

#                     catalog_doc.append(
#                         "cataloge_item_details",
#                         row_data
#                     )

#                     added.append(item_code)

#                     # =====================================================
#                     # SAVE FIRST BEFORE FOLDER CREATION
#                     # =====================================================

#                     catalog_doc.flags.ignore_version = True

#                     catalog_doc.save(
#                         ignore_permissions=True,
#                         ignore_version=True
#                     )

#                     frappe.db.commit()

#                     # reload latest doc to avoid timestamp mismatch
#                     # catalog_doc.reload()

#                     # rebuild existing_items
                    
#                     existing_items = {
#                         row.item_code: row
#                         for row in catalog_doc.cataloge_item_details
#                     }
                                     
#                     # =====================================================
#                     # ADD IN FOLDER
#                     # =====================================================

#                     if (
#                         is_folder == "Yes"
#                         and as_per_design == 1
#                     ):

#                         add_item_in_folder(
#                             status,
#                             name,
#                             items_dict.get("item"),
#                             customer
#                         )

#                     elif (
#                         is_folder == "Yes"
#                         and as_per_customized == 1
#                         and (
#                             customer_gold == 1
#                             or customer_diamond == 1
#                             or customer_stone == 1
#                         )
#                         and customized_data
#                     ):

#                         add_item_in_folder(
#                             status,
#                             name,
#                             items_dict.get("item"),
#                             customer
#                         )

#                     elif (
#                         is_folder == "Yes"
#                         and job_work == 1
#                         and as_per_customized == 1
#                         and (
#                             customer_gold == 1
#                             or customer_diamond == 1
#                             or customer_stone == 1
#                         )
#                         and customized_data
#                     ):

#                         add_item_in_folder(
#                             status,
#                             name,
#                             items_dict.get("item"),
#                             customer
#                         )

#                     elif (
#                         is_folder == "Yes"
#                         and job_work == 1
#                         and (
#                             customer_gold == 1
#                             or customer_diamond == 1
#                             or customer_stone == 1
#                         )
#                         and customized_data
#                     ):

#                         add_item_in_folder(
#                             status,
#                             name,
#                             items_dict.get("item"),
#                             customer
#                         )

#                 # ----------------- UPDATE ITEM -----------------
#                 else:
#                     old_val = existing_items[item_code]

#                     if old_val != trending_value:
                        
#                         if is_duplicate == 1:
#                             row_data = {
#                                 "item_code": item_code,
#                                 "item_name": item_code,
#                                 "wishlist": trending_value,
#                                 "job_work": job_work,
#                                 "as_per_customized": as_per_customized,
#                                 "as_per_design": as_per_design,
#                                 "customized_data": customized_data,
#                                 "customer_stone": customer_stone,
#                                 "customer_diamond": customer_diamond,
#                                 "customer_gold": customer_gold
#                             }

#                             catalog_doc.append(
#                                 "cataloge_item_details",
#                                 row_data
#                             )

#                             added.append(item_code)

#                             # =====================================================
#                             # SAVE FIRST BEFORE FOLDER CREATION
#                             # =====================================================

#                             catalog_doc.flags.ignore_version = True

#                             catalog_doc.save(
#                                 ignore_permissions=True,
#                                 ignore_version=True
#                             )

#                             frappe.db.commit()
                                    
#                         else:
                            
#                             for row in catalog_doc.cataloge_item_details:

#                                 if row.item_code == item_code:
#                                     row.wishlist = trending_value
#                                     row.job_work = job_work
#                                     row.as_per_customized = as_per_customized
#                                     row.as_per_design = as_per_design
#                                     row.customized_data = customized_data
#                                     row.customer_gold = customer_gold
#                                     row.customer_diamond = customer_diamond
#                                     row.customer_stone = customer_stone

#                                     updated.append(item_code)
                                    
#                                     catalog_doc.flags.ignore_version = True
#                                     catalog_doc.save(
#                                         ignore_permissions=True,
#                                         ignore_version=True
#                                     )

#                                     # same conditions here
#                                     if (
#                                         is_folder == "Yes"
#                                         and as_per_design == 1
#                                     ):
#                                         if row.as_per_design == as_per_design and row.item_code == item_code:
#                                             frappe.throw(f"Item {row.item_code} Is alreday Exist With Design and Folder")
                                        
#                                         add_item_in_folder(
#                                             status,
#                                             name,
#                                             items_dict.get("item"),
#                                             customer
#                                         )

#                                     elif (
#                                         is_folder == "Yes"
#                                         and as_per_customized == 1
#                                         and customized_data
#                                     ):
#                                         if row.as_per_customized == as_per_customized and row.item_code == item_code and row.customized_data == customized_data:
#                                             frappe.throw(f"Item {row.item_code} Is alreday Exist With Customized and Folder")
                                        
#                                         add_item_in_folder(
#                                             status,
#                                             name,
#                                             items_dict.get("item"),
#                                             customer
#                                         )
                                        
#                                     elif (
#                                         is_folder == "Yes"
#                                         and job_work == 1
#                                         and (customer_gold == 1 
#                                             or customer_diamond == 1 
#                                             or customer_stone == 1
#                                             )
#                                         and customized_data
#                                         ):
                                        
#                                         if row.job_work == job_work and row.item_code == item_code and row.customized_data == customized_data and (row.customer_gold == customer_gold or row.customer_diamond == customer_diamond or row.customer_stone == customer_stone):
#                                             frappe.throw(f"Item {row.item_code} Is alreday Exist With Job Work and Folder")
                                            
#                                         add_item_in_folder(
#                                             status,
#                                             name,
#                                             items_dict.get("item"),
#                                             customer
#                                         )

#                                     elif (
#                                         is_folder == "Yes"
#                                         and job_work == 1 and as_per_customized == 1
#                                         and customized_data
#                                         and (customer_gold == 1 
#                                             or customer_diamond == 1 
#                                             or customer_stone == 1
#                                         )
#                                     ):
#                                         if row.job_work == job_work and row.as_per_customized == as_per_customized and row.item_code == item_code and row.customized_data == customized_data and (row.customer_gold == customer_gold or row.customer_diamond == customer_diamond or row.customer_stone == customer_stone):
#                                             frappe.throw(f"Item {row.item_code} Is alreday Exist With Job Work and Folder")
                                            
#                                         add_item_in_folder(
#                                             status,
#                                             name,
#                                             items_dict.get("item"),
#                                             customer
#                                         )          
#                     else:
#                            row.wishlist = trending_value
#                            row.job_work = job_work
#                            row.as_per_customized = as_per_customized
#                            row.as_per_design = as_per_design
#                            row.customized_data = customized_data
#                            row.customer_gold = customer_gold
#                            row.customer_diamond = customer_diamond
#                            row.customer_stone = customer_stone 
                           
#                            updated.append(item_code)
                           
#                            catalog_doc.flags.ignore_version = True

#                            catalog_doc.save(
#                                 ignore_permissions=True,
#                                 ignore_version=True
#                             )

#                            frappe.db.commit()
                           
#                            add_item_in_folder(
#                                 status,
#                                 name,
#                                 items_dict.get("item"),
#                                 customer
#                            )

#             results.append({
#                 "customer": customer,
#                 "added_items": added,
#                 "updated_items": updated,
#                 "message": f"Added {len(added)}, Updated {len(updated)} for customer {customer}"
#             })

#             # notify_user(customer_id[0].email_id, f"Cataloge Master Added {len(added)}, Updated {len(updated)} for customer You", f"Cataloge Master Added {len(added)}, Updated {len(updated)} for customer You")

#         # ---------------------------------------------------------
#         # NEW CUSTOMER → CREATE CATALOG
#         # ---------------------------------------------------------
#         else:
#             # catalog_doc = frappe.new_doc("Cataloge Master")
#             # catalog_doc.customer = customer

#             # for item_code, trending_value in items_dict.items():
#             #     catalog_doc.append("cataloge_item_details", {
#             #         "item_code": item_code,
#             #         "item_name": item_code,
#             #         "wishlist": trending_value
#             #     })

#             # catalog_doc.insert(ignore_permissions=True)

#             # frappe.db.commit()

#             # results.append({
#             #     "customer": customer,
#             #     "added_items": list(items_dict.keys()),
#             #     "updated_items": [],
#             #     "message": f"Created new Cataloge Master for {customer}"
#             # })

#             catalog_doc = frappe.new_doc("Cataloge Master")
#             catalog_doc.customer = customer

#             added_items = []

#             for item_code, trending_value in items_dict.items():

#                 # skip metadata fields
#                 if item_code in [
#                     "item",
#                     "is_folder",
#                     "status",
#                     "name",
#                     "as_per_customized",
#                     "job_work",
#                     "customized_data",
#                     "customer_gold",
#                     "customer_diamond",
#                     "customer_stone",
#                     "as_per_design"
#                 ]:
#                     continue

#                 is_folder = items_dict.get("is_folder")
#                 as_per_design = items_dict.get("as_per_design")
#                 job_work = items_dict.get("job_work")
#                 as_per_customized = items_dict.get("as_per_customized")
#                 # frappe.throw(f"Customized Value => {as_per_customized}")
#                 customized_data = items_dict.get("customized_data")
#                 status = items_dict.get("status")
#                 name = items_dict.get("name")

#                 customer_gold = items_dict.get("customer_gold")
#                 customer_diamond = items_dict.get("customer_diamond")
#                 customer_stone = items_dict.get("customer_stone")

#                 # if folder and design type == As Per Design
#                 catalog_doc.append("cataloge_item_details", {
#                         "item_code": item_code,
#                         "item_name": item_code,
#                         "wishlist": trending_value,
#                         "job_work": job_work,
                
#                         # IMPORTANT
#                         "as_per_design": as_per_design,
#                         "as_per_customized": as_per_customized,
                
#                         "customer_gold": customer_gold,
#                         "customer_stone": customer_stone,
#                         "customer_diamond": customer_diamond,
                
#                         "customized_data": customized_data
#                 })

#                 added_items.append(item_code)

#                 catalog_doc.insert(ignore_permissions=True)
                
#                 catalog_doc.save(
#                             ignore_permissions=True,
#                             ignore_version=True
#                 )

#                 frappe.db.commit()
                
#                 if (
#                     is_folder == "Yes"
#                     and as_per_design == 1
#                 ):            
#                     add_item_in_folder(
#                             status,
#                             name,
#                             items_dict.get("item"),
#                             customer
#                     )

#                 elif (
#                     is_folder == "Yes"
#                     and as_per_customized == 1
#                     and customized_data
#                 ):               
#                     add_item_in_folder(
#                         status,
#                         name,
#                         items_dict.get("item"),
#                         customer
#                     )
                    
#                 elif (is_folder == "Yes" 
#                       and job_work == 1 
#                       and (customer_gold == 1 
#                             or customer_diamond == 1 
#                             or customer_stone == 1
#                         ) 
#                       and customized_data
#                     ):               
#                         add_item_in_folder(
#                             status,
#                             name,
#                             items_dict.get("item"),
#                             customer
#                         )
                
#                 elif (is_folder == "Yes" 
#                       and job_work == 1 and as_per_customized == 1
#                       and (customer_gold == 1 
#                             or customer_diamond == 1 
#                             or customer_stone == 1
#                         ) 
#                       and customized_data
#                     ):                 
#                         add_item_in_folder(
#                             status,
#                             name,
#                             items_dict.get("item"),
#                             customer
#                         )           

                

#             results.append({
#                 "customer": customer,
#                 "added_items": added_items,
#                 "updated_items": [],
#                 "message": f"Created new Cataloge Master for {customer}"
#             })
#             # notify_user(customer_id[0].email_id, "Cataloge Master New Catloug Master Created For You", "Cataloge Master New Catloug Master Created For You")
            

#     return {
#         "status": "success",
#         "results": results
#     }


@frappe.whitelist(allow_guest=True)
def add_item_in_folder(status=None, name=None, item=None, customer=None):
    if not customer:
        frappe.throw("Customer is required")

    # Only required for ADD and REMOVE
    if status in ["ADD", "REMOVE"] and not item:
        frappe.throw("Item list is required")

    # Convert JSON string to list safely
    if isinstance(item, str):
        item = frappe.parse_json(item)

    item = item or []
    items = tuple(item)

    sql_query = """
        SELECT 
            citm.folder, 
            citm.item_code, 
            citm.wishlist,
            ctm.name as parent_name
        FROM `tabCataloge Master` AS ctm
        LEFT JOIN `tabCataloge Item Details` AS citm
            ON citm.parent = ctm.name
        WHERE ctm.customer = %(customer)s
    """

    # Add condition only for ADD and REMOVE
    if status in ["ADD", "REMOVE"]:
        sql_query += " AND citm.item_code IN %(items)s"


    values = {
        "customer": customer,
        "items": items if items else None
    }

    result = frappe.db.sql(sql_query, values=values, as_dict=True)

    if not result:
        frappe.throw("No matching records found")

    parent_name = result[0]["parent_name"]

    catalog_doc = frappe.get_doc(
        "Cataloge Master",
        parent_name,
        ignore_permissions=True
    )

    # ---------------- ADD ----------------
    if status == "ADD":
        for row in catalog_doc.cataloge_item_details:
            if row.wishlist == 1 and row.item_code in item:

                if not row.folder:
                    row.folder = name
                else:
                    folders = row.folder.split(",")
                    if name not in folders:
                        folders.append(name)
                        row.folder = ",".join(folders)

    # ---------------- REMOVE ----------------
    if status == "REMOVE":
        for row in catalog_doc.cataloge_item_details:
            if row.wishlist == 1 and row.item_code in item and row.folder:

                folders = row.folder.split(",")

                if name in folders:
                    folders.remove(name)

                    if folders:
                        row.folder = ",".join(folders)
                    else:
                        row.folder = None

    # ---------------- DELETE ----------------
    if status == "DELETE" and name:
        for row in catalog_doc.cataloge_item_details:

            if row.wishlist == 1 and row.folder:

                folders = row.folder.split(",")

                if name in folders:
                    folders.remove(name)

                    if folders:
                        row.folder = ",".join(folders)
                    else:
                        row.folder = None

    catalog_doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {"message": "Updated successfully"}


# @frappe.whitelist(allow_guest=True)
# def get_similar_item(item_code):

#     if not item_code:
#         return []

#     # Step 1: Get similar item codes
#     similar_item_codes = frappe.db.sql("""
#         SELECT sit.item_code
#         FROM `tabItem` i
#         LEFT JOIN `tabSimilar Item Table` sit
#             ON sit.parent = i.name
#             AND sit.parenttype = 'Item'
#             AND sit.parentfield = 'custom_similar_item_table'
#         WHERE i.name = %s
#         AND i.custom_is_similar_item = 1
#     """, (item_code,), pluck=True)

#     if not similar_item_codes:
#         return []

#     # Convert to tuple for IN condition
#     codes_tuple = tuple(similar_item_codes)

#     # Step 2: Get all item details in single query
#     items = frappe.db.sql("""
#         SELECT item_code, image
#         FROM `tabItem`
#         WHERE name IN %(codes)s
#     """, {
#         "codes": codes_tuple
#     }, as_dict=True)

#     return items

# @frappe.whitelist(allow_guest=True)
# def get_similar_item(item_code, customer=None, user=None):

#     if not item_code:
#         return []

#     # Step 1: Similar item codes nikalo
#     similar_item_codes = frappe.db.sql("""
#         SELECT sit.item_code
#         FROM `tabItem` i
#         LEFT JOIN `tabSimilar Item Table` sit
#             ON sit.parent = i.name
#             AND sit.parenttype = 'Item'
#             AND sit.parentfield = 'custom_similar_item_table'
#         WHERE i.name = %s
#         AND i.custom_is_similar_item = 1
#     """, (item_code,), pluck=True)

#     if not similar_item_codes:
#         return []

#     codes_tuple = tuple(similar_item_codes)

#     # Step 2: Customer ke liye catalogue filter
#     if customer:
#         items = frappe.db.sql("""
#             SELECT 
#                 item.item_code, 
#                 item.image
#             FROM `tabItem` AS item
#             INNER JOIN `tabCataloge Item Details` AS tci
#                 ON tci.item_code = item.name
#             INNER JOIN `tabCataloge Master` AS tcm
#                 ON tcm.name = tci.parent
#             WHERE item.name IN %(codes)s
#             AND tcm.customer = %(customer)s
#         """, {
#             "codes": codes_tuple,
#             "customer": customer
#         }, as_dict=True)

#     # Step 3: User ke liye internal catalogue filter
#     elif user:
#         items = frappe.db.sql("""
#             SELECT 
#                 item.item_code, 
#                 item.image
#             FROM `tabItem` AS item
#             INNER JOIN `tabUser Item Details` AS uid
#                 ON uid.item_code = item.name
#             INNER JOIN `tabInternal Catalog Master` AS icm
#                 ON icm.name = uid.parent
#             WHERE item.name IN %(codes)s
#             AND icm.user = %(user)s
#         """, {
#             "codes": codes_tuple,
#             "user": user
#         }, as_dict=True)

#     # Step 4: Koi filter nahi — seedha item se
#     else:
#         items = frappe.db.sql("""
#             SELECT item_code, image
#             FROM `tabItem`
#             WHERE name IN %(codes)s
#         """, {
#             "codes": codes_tuple
#         }, as_dict=True)

#     return items


# @frappe.whitelist(allow_guest=True)
# def get_similar_item(item_code, customer=None):

#     if not item_code:
#         return []

#     # Similar items jo customer catalogue me bhi ho
#     items = frappe.db.sql("""
#         SELECT DISTINCT
#             item.item_code,
#             item.image

#         FROM `tabSimilar Item Table` sit

#         INNER JOIN `tabItem` item
#             ON item.name = sit.item_code

#         INNER JOIN `tabCataloge Item Details` tci
#             ON tci.item_code = item.name

#         INNER JOIN `tabCataloge Master` tcm
#             ON tcm.name = tci.parent

#         WHERE sit.parent = %(item_code)s
#         AND sit.parenttype = 'Item'
#         AND sit.parentfield = 'custom_similar_item_table'

#         AND tcm.customer = %(customer)s
#     """, {
#         "item_code": item_code,
#         "customer": customer
#     }, as_dict=True)

#     return items

@frappe.whitelist(allow_guest=True)
def get_similar_item(item_code, customer=None, user=None):

    if not item_code:
        return []

    # =========================
    # CUSTOMER CATALOGUE
    # =========================
    if customer:

        items = frappe.db.sql("""
            SELECT DISTINCT
                item.item_code,
                item.image

            FROM `tabSimilar Item Table` sit

            INNER JOIN `tabItem` item
                ON item.name = sit.item_code

            INNER JOIN `tabCataloge Item Details` tci
                ON tci.item_code = item.name

            INNER JOIN `tabCataloge Master` tcm
                ON tcm.name = tci.parent

            WHERE sit.parent = %(item_code)s
            AND sit.parenttype = 'Item'
            AND sit.parentfield = 'custom_similar_item_table'

            AND tcm.customer = %(customer)s
        """, {
            "item_code": item_code,
            "customer": customer
        }, as_dict=True)

        return items

    # =========================
    # INTERNAL USER CATALOGUE
    # =========================
    elif user:

        items = frappe.db.sql("""
            SELECT DISTINCT
                item.item_code,
                item.image

            FROM `tabSimilar Item Table` sit

            INNER JOIN `tabItem` item
                ON item.name = sit.item_code

            INNER JOIN `tabUser Item Details` uid
                ON uid.item_code = item.name

            INNER JOIN `tabInternal Catalog Master` icm
                ON icm.name = uid.parent

            WHERE sit.parent = %(item_code)s
            AND sit.parenttype = 'Item'
            AND sit.parentfield = 'custom_similar_item_table'

            AND icm.user = %(user)s
        """, {
            "item_code": item_code,
            "user": user
        }, as_dict=True)

        return items

    # =========================
    # NO FILTER
    # =========================
    else:

        items = frappe.db.sql("""
            SELECT DISTINCT
                item.item_code,
                item.image

            FROM `tabSimilar Item Table` sit

            INNER JOIN `tabItem` item
                ON item.name = sit.item_code

            WHERE sit.parent = %(item_code)s
            AND sit.parenttype = 'Item'
            AND sit.parentfield = 'custom_similar_item_table'
        """, {
            "item_code": item_code
        }, as_dict=True)

        return items


# @frappe.whitelist(allow_guest=True)
# def get_item_of_customer_by_user(customer):
#     if not customer:
#         return {"message": "Customer not found"}

#     catalog_names = frappe.get_all(
#         "Cataloge Master",
#         filters={"customer": customer},
#         pluck="name"
#     )

#     items = frappe.get_all(
#         "Cataloge Item Details",
#         filters={"parent": ["in", catalog_names]},
#         fields=["parent", "item_code", "item_name", "trending", "folder", "wishlist"]
#     )

#     return items



@frappe.whitelist(allow_guest=True)
def get_item_of_customer_by_user(customer):
    if not customer:
        return {"message": "Customer not found"}

    catalog_names = frappe.get_all(
        "Cataloge Master",
        filters={"customer": customer},
        pluck="name"
    )

    if not catalog_names:
        return []

    items = frappe.db.sql("""
        SELECT
            cid.parent,
            cid.item_code,
            cid.item_name,
            cid.trending,
            cid.folder,
            cid.wishlist,

            i.item_category,
            i.item_subcategory,

            i.image,
            
            CASE
                WHEN i.front_view = i.image THEN 'CAD Image'
                ELSE 'FG Image'
            END AS image_remark

        FROM `tabCataloge Item Details` cid
        LEFT JOIN `tabItem` i
            ON cid.item_code = i.name

        WHERE cid.parent IN %(catalog_names)s
    """, {
        "catalog_names": tuple(catalog_names)
    }, as_dict=True)

    return items



@frappe.whitelist(allow_guest=True)
def remove_item_of_customer_by_user(customer, item_code):

    if not customer:
        return {"message": "Customer not found"}

    # convert item_code to list
    if isinstance(item_code, str):
        try:
            item_code = json.loads(item_code)
        except:
            item_code = [item_code]

    catalog_names = frappe.get_all(
        "Cataloge Master",
        filters={"customer": customer},
        pluck="name"
    )

    if not catalog_names:
        return {"message": "No catalog found for customer"}

    deleted_items = []

    for catalog in catalog_names:

        doc = frappe.get_doc("Cataloge Master", catalog)

        new_rows = []

        for row in doc.cataloge_item_details:

            if row.item_code not in item_code:
                new_rows.append(row)
            else:
                deleted_items.append(row.item_code)

        doc.set("cataloge_item_details", [])
        doc.set("cataloge_item_details", new_rows)
        doc.save(ignore_permissions=True)

    frappe.db.commit()

    return {
        "deleted_items": deleted_items
    }


@frappe.whitelist(allow_guest=True)
def get_wishlist_item_customer_wise(customer):

    if not customer:
        return {"message": "Customer not found"}

    catalog_name = frappe.db.get_value(
        "Cataloge Master",
        {"customer": customer},
        "name"
    )

    if not catalog_name:
        return {"message": "No catalog found for customer"}

    doc = frappe.get_doc("Cataloge Master", catalog_name)

    new_rows = []

    for row in doc.cataloge_item_details:
        if row.wishlist == 1:
            new_rows.append({
                "item_code": row.item_code,
                "item_name": row.item_name,
                "trending": row.trending,
                "folder": row.folder,
                "wishlist": row.wishlist
            })

    return {
        "new_rows": new_rows
    }
    
    # NE00968
 





# @frappe.whitelist(allow_guest=True)
# def catalogue_data2(selectedSubcategory=None, itemCategory=None, itemCode=None, metalType=None, company=None, customer=None):

#     if selectedSubcategory is None:
#         selectedSubcategory = frappe.form_dict.get("selectedSubcategory")

#     if itemCode is None:
#         itemCode = frappe.form_dict.get("itemCode")

#     if metalType is None:
#         metalType = frappe.form_dict.get("metalType")

#     if itemCategory is None:
#         itemCategory = frappe.form_dict.get("itemCategory")

#     values = {}

#     # ---------------- FILTERS ----------------
#     sub_where = "b.bom_type = 'Finish Goods' AND i.item_group != 'Design DNU'"
#     where_clause = "1=1 AND bom.bom_type = 'Finish Goods' AND item.item_group != 'Design DNU'"

#     if metalType:
#         sub_where += " AND b.metal_type = %(metalType)s"
#         where_clause += " AND bom.metal_type = %(metalType)s"
#         values["metalType"] = metalType

#     if selectedSubcategory:
#         sub_where += " AND i.item_subcategory = %(selectedSubcategory)s"
#         where_clause += " AND item.item_subcategory = %(selectedSubcategory)s"
#         values["selectedSubcategory"] = selectedSubcategory

#     if itemCategory:
#         sub_where += " AND i.item_category = %(itemCategory)s"
#         where_clause += " AND item.item_category = %(itemCategory)s"
#         values["itemCategory"] = itemCategory

#     if itemCode:
#         sub_where += " AND i.item_code = %(itemCode)s"
#         where_clause += " AND item.item_code = %(itemCode)s"
#         values["itemCode"] = itemCode

#     if company:
#         sub_where += " AND idf3.company = %(company)s"
#         where_clause += " AND idf.company = %(company)s"
#         values["company"] = company
#     else:
#         sub_where += " AND idf3.company = 'Gurukrupa Export Private Limited'"
#         where_clause += " AND idf.company = 'Gurukrupa Export Private Limited'"

#     # wishlist
#     if customer:
#         wishlist_case = "MAX(CASE WHEN tci.wishlist = 1 AND tcm.customer IS NOT NULL THEN 1 ELSE 0 END) AS wishlist"
#         customer_join = "AND tcm.customer = %(customer)s"
#         values["customer"] = customer
#     else:
#         wishlist_case = "0 AS wishlist"
#         customer_join = ""

#     db_data = frappe.db.sql(f"""
#         SELECT
#             item.name,
#             bom.name,
#             idf.company,
#             tci.trending,
#             tci.name as catalog_item_details_name,
#             {wishlist_case},
#             item.creation,
#             item.item_code,
#             item.item_category,
#             item.image,
#             item.sketch_image,
#             item.front_view AS cad_image,
#             CASE
#                 WHEN item.front_view = item.image THEN 'CAD Image'
#                 ELSE 'FG Image'
#             END AS image_remark,
#             item.item_subcategory,
#             item.stylebio,
#             bom.tag_no,
#             bom.diamond_quality,
#             item.setting_type,

#             FORMAT(bom.gross_weight,3) AS gross_metal_weight,
#             FORMAT(bom.metal_and_finding_weight,3) AS net_metal_finding_weight,
#             FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
#             FORMAT(bom.other_weight,3) AS other_weight,
#             FORMAT(bom.finding_weight_,3) AS finding_weight_,

#             bom.metal_colour,
#             bom.metal_touch,
#             bom.metal_purity,
#             FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,

#             bom.total_diamond_pcs,
#             bom.total_gemstone_pcs,
#             FORMAT(bom.gemstone_weight,3) AS gemstone_weight,

#             FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
#             FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
#             FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,

#             bom.navratna,
#             bom.lock_type,
#             bom.feature,
#             bom.enamal,
#             bom.rhodium,
#             bom.sizer_type,

#             bom.height,
#             bom.length,
#             bom.width,
#             bom.breadth,
#             bom.product_size,

#             bom.design_style,
#             bom.nakshi_from,
#             bom.vanki_type,
#             bom.total_length,
#             bom.detachable,
#             bom.back_side_size,
#             bom.changeable,

#             item.variant_of,

#             CASE 
#                 WHEN vc.variant_count > 1 THEN 1 
#                 ELSE 0 
#             END AS rn,

#             CASE 
#                WHEN set_check.is_set_item = 1 THEN 1 
#                ELSE 0 
#             END AS is_set_item,
            
#             CASE 
#                 WHEN similar_check.is_similar_item = 1 THEN 1 
#                 ELSE 0 
#             END AS is_similar_item,

#             bom.finding_pcs,
#             bom.total_other_pcs,
#             bom.total_other_weight,
#             bom.custom_rating AS rating, 

#             GROUP_CONCAT(DISTINCT item.name ORDER BY item.creation ASC) AS variant_name,

#             GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
#             GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,

#             GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
#             GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
#             GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
#             GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,

#             GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
#             GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,

#             GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
#             GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
#             GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
#             GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
#             GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,

#             GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
#             GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
#             GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size

#         FROM `tabItem` AS item

#         LEFT JOIN (
#             SELECT 
#                 IFNULL(i.variant_of, i.item_code) AS group_key,
#                 COUNT(DISTINCT i.item_code) AS variant_count
#             FROM `tabItem` AS i
#             INNER JOIN `tabBOM` AS b ON i.item_code = b.item AND b.bom_type = 'Finish Goods'
#             GROUP BY IFNULL(i.variant_of, i.item_code)
#         ) vc ON vc.group_key = IFNULL(item.variant_of, item.item_code)

#         LEFT JOIN (
#             SELECT 
#                 sit.parent AS item_code,
#                 CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END AS is_set_item
#             FROM `tabSet Item Table` sit
#             GROUP BY sit.parent
#         ) AS set_check ON set_check.item_code = item.item_code
        
#         LEFT JOIN (
#         SELECT 
#             sit.parent AS item_code,
#             CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END AS is_similar_item
#             FROM `tabSimilar Item Table` sit
#             WHERE sit.parenttype = 'Item'
#             GROUP BY sit.parent
#         ) AS similar_check ON similar_check.item_code = item.item_code

#         INNER JOIN (
#             SELECT
#                 IFNULL(i.variant_of, i.item_code) AS group_key,
#                 MIN(i.item_code) AS first_item_code
#             FROM `tabItem` AS i
#             INNER JOIN `tabBOM` AS b ON i.item_code = b.item
#             INNER JOIN `tabItem Default` AS idf3 ON i.item_name = idf3.parent
#             WHERE {sub_where}
#             GROUP BY IFNULL(i.variant_of, i.item_code)
#         ) AS first_variant
#             ON item.item_code = first_variant.first_item_code

#         LEFT JOIN `tabCataloge Item Details` AS tci ON tci.item_code = item.name
#         LEFT JOIN `tabCataloge Master` AS tcm ON tcm.name = tci.parent {customer_join}
#         LEFT JOIN `tabBOM` AS bom ON item.item_code = bom.item
#         LEFT JOIN `tabDesign Attributes` AS td ON item.item_code = td.parent
#         LEFT JOIN `tabBOM Metal Detail` AS mt ON bom.name = mt.parent
#         LEFT JOIN `tabBOM Gemstone Detail` AS gd ON bom.name = gd.parent
#         LEFT JOIN `tabBOM Diamond Detail` AS dd ON bom.name = dd.parent
#         LEFT JOIN `tabBOM Finding Detail` AS fd ON bom.name = fd.parent
#         LEFT JOIN `tabBOM Other Detail` AS od ON bom.name = od.parent
#         LEFT JOIN `tabItem Default` AS idf ON item.item_name = idf.parent

#         WHERE {where_clause}
#         GROUP BY item.item_code, item.variant_of
#         ORDER BY item.creation DESC

#     """, values, as_dict=True)

#     # -------- MULTISELECT ATTRIBUTES --------
#     item_codes = [row.item_code for row in db_data]
#     # frappe.throw(f"Total Records: {len(db_data)}")
#     if item_codes:
#         db_res = frappe.db.sql("""
#             SELECT parent, parentfield,
#             GROUP_CONCAT(design_attribute ORDER BY design_attribute SEPARATOR ', ') AS design_attributes
#             FROM `tabDesign Attribute - Multiselect`
#             WHERE parent IN %(data)s
#             GROUP BY parent, parentfield
#         """, {"data": tuple(item_codes)}, as_dict=True)
#     else:
#         db_res = []

#     attr_map = {}
#     for row in db_res:
#         parent = row["parent"]
#         field = row["parentfield"].replace("custom_", "")
#         value = row["design_attributes"]
#         if parent not in attr_map:
#             attr_map[parent] = {}
#         attr_map[parent][field] = value

#     for row in db_data:
#         attrs = attr_map.get(row.item_code, {})
#         for key, value in attrs.items():
#             row[key] = value

#         row["custom_collection"] = row.get("custom_collection") or None
#         row["custom_language"] = row.get("custom_language") or None
#         row["custom_zodiac"] = row.get("custom_zodiac") or None
#         row["custom_animalbirds"] = row.get("custom_animalbirds") or None
#         row["custom_alphabetnumber"] = row.get("custom_alphabetnumber") or None
#         row["religious"] = row.get("religious") or None

#     # frappe.throw(f"Total Records: {len(db_data)}")
#     encrypted_data = encrypt_response(db_data)
#     return{
#         encrypted_data
#     }
#     # return db_data

@frappe.whitelist(allow_guest=True)
def catalogue_data2(selectedSubcategory=None, itemCategory=None, itemCode=None, metalType=None, company=None, customer=None, page=1, page_size=50, is_filter=None, search=None):

    if selectedSubcategory is None:
        selectedSubcategory = frappe.form_dict.get("selectedSubcategory")

    if itemCode is None:
        itemCode = frappe.form_dict.get("itemCode")

    if metalType is None:
        metalType = frappe.form_dict.get("metalType")

    if itemCategory is None:
        itemCategory = frappe.form_dict.get("itemCategory")
        
    values = {}

    # ---------------- FILTERS ----------------
    sub_where = "b.bom_type = 'Finish Goods' AND i.item_group != 'Design DNU'"
    where_clause = "1=1 AND bom.bom_type = 'Finish Goods' AND item.item_group != 'Design DNU'"

    if metalType:
        sub_where += " AND b.metal_type = %(metalType)s"
        where_clause += " AND bom.metal_type = %(metalType)s"
        values["metalType"] = metalType

    if selectedSubcategory:
        sub_where += " AND i.item_subcategory = %(selectedSubcategory)s"
        where_clause += " AND item.item_subcategory = %(selectedSubcategory)s"
        values["selectedSubcategory"] = selectedSubcategory

    if itemCategory:
        sub_where += " AND i.item_category = %(itemCategory)s"
        where_clause += " AND item.item_category = %(itemCategory)s"
        values["itemCategory"] = itemCategory

    if itemCode:
        sub_where += " AND i.item_code = %(itemCode)s"
        where_clause += " AND item.item_code = %(itemCode)s"
        values["itemCode"] = itemCode

    if company:
        sub_where += " AND idf3.company = %(company)s"
        where_clause += " AND idf.company = %(company)s"
        values["company"] = company
    else:
        sub_where += " AND idf3.company = 'Gurukrupa Export Private Limited'"
        where_clause += " AND idf.company = 'Gurukrupa Export Private Limited'"

    # wishlist
    if customer:
        wishlist_case = "MAX(CASE WHEN tci.wishlist = 1 AND tcm.customer IS NOT NULL THEN 1 ELSE 0 END) AS wishlist"
        customer_join = "AND tcm.customer = %(customer)s"
        values["customer"] = customer
    else:
        wishlist_case = "0 AS wishlist"
        customer_join = ""
        
    page_param = frappe.form_dict.get("page")
    
    if page_param is None:
        return {
            "data": []
        }
    
    page = int(page_param)
    is_filter = int(frappe.form_dict.get("is_filter", 0) or 0)

    if is_filter == 1:
        page = frappe.form_dict.get("page", page)
        page_size = frappe.form_dict.get("page_size", page_size)
        
        page = int(page)
        page_size = int(page_size)
        
        offset = (page - 1) * page_size
        
        values["page_size"] = page_size
        values["offset"] = offset
        
        db_filter_data = get_is_filter(search, values, wishlist_case, sub_where, customer_join, where_clause)
        
        return db_filter_data
    
    
    base_query = f"""
        SELECT
            item.name,
            bom.name,
            bom.sub_setting_type1,
            idf.company,
            tci.trending,
            tci.name as catalog_item_details_name,
            {wishlist_case},
            item.creation,
            item.item_code,
            item.item_category,
            item.image,
            item.sketch_image,
            item.front_view AS cad_image,
            CASE
                WHEN item.front_view = item.image THEN 'CAD Image'
                ELSE 'FG Image'
            END AS image_remark,
            item.item_subcategory,
            item.stylebio,
            bom.tag_no,
            bom.diamond_quality,
            item.setting_type,

            FORMAT(bom.gross_weight,3) AS gross_metal_weight,
            FORMAT(bom.metal_and_finding_weight,3) AS net_metal_finding_weight,
            FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
            FORMAT(bom.other_weight,3) AS other_weight,
            FORMAT(bom.finding_weight_,3) AS finding_weight_,

            bom.metal_colour,
            bom.metal_touch,
            bom.metal_purity,
            FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,

            bom.total_diamond_pcs,
            bom.total_gemstone_pcs,
            FORMAT(bom.gemstone_weight,3) AS gemstone_weight,

            FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
            FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
            FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,

            bom.navratna,
            bom.lock_type,
            bom.feature,
            bom.enamal,
            bom.rhodium,
            bom.sizer_type,

            bom.height,
            bom.length,
            bom.width,
            bom.breadth,
            bom.product_size,

            bom.design_style,
            bom.nakshi_from,
            bom.vanki_type,
            bom.total_length,
            bom.detachable,
            bom.back_side_size,
            bom.changeable,

            item.variant_of,

            CASE 
                WHEN vc.variant_count > 1 THEN 1 
                ELSE 0 
            END AS rn,

            CASE 
               WHEN set_check.is_set_item = 1 THEN 1 
               ELSE 0 
            END AS is_set_item,
            
            CASE 
                WHEN similar_check.is_similar_item = 1 THEN 1 
                ELSE 0 
            END AS is_similar_item,

            bom.finding_pcs,
            bom.total_other_pcs,
            bom.total_other_weight,
            bom.custom_rating AS rating, 

            GROUP_CONCAT(DISTINCT item.name ORDER BY item.creation ASC) AS variant_name,

            GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
            GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,

            GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
            GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
            GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
            GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,

            GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
            GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,

            GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
            GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
            GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
            GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
            GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,

            GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
            GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
            GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size

        FROM `tabItem` AS item

        LEFT JOIN (
            SELECT 
                IFNULL(i.variant_of, i.item_code) AS group_key,
                COUNT(DISTINCT i.item_code) AS variant_count
            FROM `tabItem` AS i
            INNER JOIN `tabBOM` AS b ON i.item_code = b.item AND b.bom_type = 'Finish Goods'
            GROUP BY IFNULL(i.variant_of, i.item_code)
        ) vc ON vc.group_key = IFNULL(item.variant_of, item.item_code)

        LEFT JOIN (
            SELECT 
                sit.parent AS item_code,
                CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END AS is_set_item
            FROM `tabSet Item Table` sit
            GROUP BY sit.parent
        ) AS set_check ON set_check.item_code = item.item_code
        
        LEFT JOIN (
        SELECT 
            sit.parent AS item_code,
            CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END AS is_similar_item
            FROM `tabSimilar Item Table` sit
            WHERE sit.parenttype = 'Item'
            GROUP BY sit.parent
        ) AS similar_check ON similar_check.item_code = item.item_code

        INNER JOIN (
            SELECT
                IFNULL(i.variant_of, i.item_code) AS group_key,
                MIN(i.item_code) AS first_item_code
            FROM `tabItem` AS i
            INNER JOIN `tabBOM` AS b ON i.item_code = b.item
            INNER JOIN `tabItem Default` AS idf3 ON i.item_name = idf3.parent
            WHERE {sub_where}
            GROUP BY IFNULL(i.variant_of, i.item_code)
        ) AS first_variant
            ON item.item_code = first_variant.first_item_code

        LEFT JOIN `tabCataloge Item Details` AS tci ON tci.item_code = item.name
        LEFT JOIN `tabCataloge Master` AS tcm ON tcm.name = tci.parent {customer_join}
        LEFT JOIN `tabBOM` AS bom ON item.item_code = bom.item
        LEFT JOIN `tabDesign Attributes` AS td ON item.item_code = td.parent
        LEFT JOIN `tabBOM Metal Detail` AS mt ON bom.name = mt.parent
        LEFT JOIN `tabBOM Gemstone Detail` AS gd ON bom.name = gd.parent
        LEFT JOIN `tabBOM Diamond Detail` AS dd ON bom.name = dd.parent
        LEFT JOIN `tabBOM Finding Detail` AS fd ON bom.name = fd.parent
        LEFT JOIN `tabBOM Other Detail` AS od ON bom.name = od.parent
        LEFT JOIN `tabItem Default` AS idf ON item.item_name = idf.parent

        WHERE {where_clause}
        GROUP BY item.item_code, item.variant_of
        ORDER BY item.creation DESC
        # LIMIT %(page_size)s OFFSET %(offset)s
    """
    
    db_data = None
    
    filters = None
    
    page = frappe.form_dict.get("page", page)
    page_size = frappe.form_dict.get("page_size", page_size)
        
    page = int(page)
    page_size = int(page_size)
        
    offset = (page - 1) * page_size
        
    values["page_size"] = page_size
    values["offset"] = offset
    
    if page == 1 and is_filter == 0:
        db_data = frappe.db.sql(
            base_query,
            values,
            as_dict=True
        )
        
    else:
        paginated_query = base_query + """
            LIMIT %(page_size)s OFFSET %(offset)s
        """

        db_data = frappe.db.sql(
            paginated_query,
            values,
            as_dict=True
        )
    

    # -------- MULTISELECT ATTRIBUTES --------
    item_codes = [row.item_code for row in db_data]
    # frappe.throw(f"Total Records: {len(db_data)}")
    if item_codes:
        db_res = frappe.db.sql("""
            SELECT parent, parentfield,
            GROUP_CONCAT(design_attribute ORDER BY design_attribute SEPARATOR ', ') AS design_attributes
            FROM `tabDesign Attribute - Multiselect`
            WHERE parent IN %(data)s
            GROUP BY parent, parentfield
        """, {"data": tuple(item_codes)}, as_dict=True)
    else:
        db_res = []
        
    count_query = frappe.db.sql(f"""
   SELECT COUNT(*)
    FROM (
        SELECT IFNULL(item.variant_of, item.item_code)
        FROM `tabItem` item
        LEFT JOIN `tabBOM` bom ON item.item_code = bom.item
        LEFT JOIN `tabItem Default` idf ON item.item_name = idf.parent
        WHERE {where_clause}
        GROUP BY IFNULL(item.variant_of, item.item_code)
    ) t
    """, values)

    total_count = count_query[0][0]

    attr_map = {}
    for row in db_res:
        parent = row["parent"]
        field = row["parentfield"].replace("custom_", "")
        value = row["design_attributes"]
        if parent not in attr_map:
            attr_map[parent] = {}
        attr_map[parent][field] = value

    for row in db_data:
        attrs = attr_map.get(row.item_code, {})
        for key, value in attrs.items():
            row[key] = value

        row["custom_collection"] = row.get("custom_collection") or None
        row["custom_language"] = row.get("custom_language") or None
        row["custom_zodiac"] = row.get("custom_zodiac") or None
        row["custom_animalbirds"] = row.get("custom_animalbirds") or None
        row["custom_alphabetnumber"] = row.get("custom_alphabetnumber") or None
        row["religious"] = row.get("religious") or None

    # if page == 1 and is_filter == 0:
    #     filters = get_method(db_data)
    #     return {
    #         "data": db_data[0:50],
    #         "filters":filters,
    #         "total_count": total_count,
    #         "page": page,
    #         "page_size": page_size,
    #         "has_more": (offset + page_size) <total_count
    #     }
        
    # # frappe.throw(f"Total Records: {len(db_data)}")
    # return {
    #     "data": db_data,
    #     "filters":filters,
    #     "total_count": total_count,
    #     "page": page,
    #     "page_size": page_size,
    #     "has_more": (offset + page_size) <total_count
    # }
    if page == 1 and is_filter == 0:
        filters = get_method(db_data)
    
        response_data = {
            "data": db_data[0:50],
            "filters": filters,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "has_more": (offset + page_size) < total_count
    }
    else:
        response_data = {
            "data": db_data,
            "filters": filters,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "has_more": (offset + page_size) < total_count
        }
    
    return {
        "encrypted_data": encrypt_response(response_data)
    }
   



# def get_is_filter(search, values, wishlist_case, sub_where, customer_join, where_clause):
#     if search:
#         values["search"] = f"%{search}%"
#     else:
#         values["search"] = "%%"

#     # where_clause += """
#     #         AND (
#     #             item.item_category LIKE %(search)s
#     #             OR item.item_subcategory LIKE %(search)s
#     #             OR item.setting_type LIKE %(search)s

#     #             OR bom.metal_touch LIKE %(search)s
#     #             OR bom.metal_colour LIKE %(search)s
#     #             OR bom.diamond_quality LIKE %(search)s
#     #             OR bom.design_style LIKE %(search)s
#     #             OR bom.rhodium LIKE %(search)s

#     #             OR gd.stone_shape LIKE %(search)s
#     #             OR dd.stone_shape LIKE %(search)s

#     #             OR fd.finding_type LIKE %(search)s

#     #             OR dam.design_attribute LIKE %(search)s
#     #         )
#     #     """
    
#     matched_item_codes = []
#     if search:

#         search_terms = [x.strip() for x in search.split(",") if x.strip()]
#         # frappe.throw(f"{search_terms}")
#         search_conditions = []

#         for i, term in enumerate(search_terms):

#             values[f"search_{i}"] = f"%{term}%"

#             search_conditions.append(f"""               
#                 item.item_category LIKE %(search_{i})s
#                 OR item.item_subcategory LIKE %(search_{i})s
#                 OR item.setting_type LIKE %(search_{i})s
#                 OR bom.sub_setting_type1 LIKE %(search_{i})s
#                 OR bom.metal_touch LIKE %(search_{i})s
#                 OR bom.metal_colour LIKE %(search_{i})s
#                 OR bom.diamond_quality LIKE %(search_{i})s
#                 OR bom.design_style LIKE %(search_{i})s
#                 OR bom.rhodium LIKE %(search_{i})s
#                 OR dam.design_attribute LIKE %(search_{i})s
#             """)

#         search_where = " OR ".join(search_conditions)
        
#         # add this condition
#         setting_filter = ""

#         if "Open" in search_terms:
#             setting_filter = """
#                 AND bom.sub_setting_type1 != 'Close-Open Setting'
#             """

#         elif "Close-Open Setting" in search_terms:
#             setting_filter = """
#                 AND bom.sub_setting_type1 = 'Close-Open Setting'
#                 AND item.setting_type = 'Open'
#             """
            

#         matched_item_codes = frappe.db.sql(
#             f"""
#             SELECT DISTINCT item.item_code
#             FROM `tabItem` item

#             INNER JOIN `tabBOM` bom
#                 ON bom.item = item.item_code

#             LEFT JOIN `tabItem Default` idf
#                 ON idf.parent = item.item_name

#             LEFT JOIN `tabDesign Attribute - Multiselect` dam
#                 ON dam.parent = item.item_code

#             WHERE
#                 bom.bom_type = 'Finish Goods'
#                 {"AND idf.company = %(company)s" if values.get("company") else ""}

#                 AND (
#                     {search_where}
#                 )
                
#                 {setting_filter}
                
#             """,
#             values,
#             as_list=True
#         )
    

#         matched_item_codes = [row[0] for row in matched_item_codes]
        
#         # frappe.throw(f"{matched_item_codes}")
        
#         if not matched_item_codes:
#             return []

#         values["item_codes"] = tuple(matched_item_codes)
        
#         # frappe.throw(f"{values.get("item_codes")}")

#         where_clause += """
#             AND item.item_code IN %(item_codes)s
#         """
        
#     base_query = f"""
#         SELECT
#             item.name,
#             bom.name,
#             bom.sub_setting_type1,
#             idf.company,
#             tci.trending,
#             tci.name AS catalog_item_details_name,
#             {wishlist_case},
#             item.creation,
#             item.item_code,
#             item.item_category,
#             item.image,
#             item.sketch_image,
#             item.front_view AS cad_image,

#             CASE
#                 WHEN item.front_view = item.image THEN 'CAD Image'
#                 ELSE 'FG Image'
#             END AS image_remark,

#             item.item_subcategory,
#             item.stylebio,
#             bom.tag_no,
#             bom.diamond_quality,
#             item.setting_type,

#             FORMAT(bom.gross_weight,3) AS gross_metal_weight,
#             FORMAT(bom.metal_and_finding_weight,3) AS net_metal_finding_weight,
#             FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
#             FORMAT(bom.other_weight,3) AS other_weight,
#             FORMAT(bom.finding_weight_,3) AS finding_weight_,

#             bom.metal_colour,
#             bom.metal_touch,
#             bom.metal_purity,
#             FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,

#             bom.total_diamond_pcs,
#             bom.total_gemstone_pcs,
#             FORMAT(bom.gemstone_weight,3) AS gemstone_weight,

#             FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
#             FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
#             FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,

#             bom.navratna,
#             bom.lock_type,
#             bom.feature,
#             bom.enamal,
#             bom.rhodium,
#             bom.sizer_type,

#             bom.height,
#             bom.length,
#             bom.width,
#             bom.breadth,
#             bom.product_size,

#             bom.design_style,
#             bom.nakshi_from,
#             bom.vanki_type,
#             bom.total_length,
#             bom.detachable,
#             bom.back_side_size,
#             bom.changeable,

#             item.variant_of,

#             CASE
#                 WHEN vc.variant_count > 1 THEN 1
#                 ELSE 0
#             END AS rn,

#             CASE
#                 WHEN set_check.is_set_item = 1 THEN 1
#                 ELSE 0
#             END AS is_set_item,

#             CASE
#                 WHEN similar_check.is_similar_item = 1 THEN 1
#                 ELSE 0
#             END AS is_similar_item,

#             bom.finding_pcs,
#             bom.total_other_pcs,
#             bom.total_other_weight,
#             bom.custom_rating AS rating,

#             GROUP_CONCAT(DISTINCT item.name ORDER BY item.creation ASC) AS variant_name,

#             GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
#             GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
#             GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
#             GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,

#             GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
#             GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,

#             GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
#             GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
#             GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
#             GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
#             GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,

#             GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
#             GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
#             GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size

#         FROM `tabItem` item

#         LEFT JOIN (
#             SELECT
#                 IFNULL(i.variant_of, i.item_code) AS group_key,
#                 COUNT(DISTINCT i.item_code) AS variant_count
#             FROM `tabItem` i
#             INNER JOIN `tabBOM` b
#                 ON i.item_code = b.item
#                 AND b.bom_type = 'Finish Goods'
#             GROUP BY IFNULL(i.variant_of, i.item_code)
#         ) vc
#             ON vc.group_key = IFNULL(item.variant_of, item.item_code)

#         LEFT JOIN (
#             SELECT
#                 parent AS item_code,
#                 1 AS is_set_item
#             FROM `tabSet Item Table`
#             GROUP BY parent
#         ) set_check
#             ON set_check.item_code = item.item_code

#         LEFT JOIN (
#             SELECT
#                 parent AS item_code,
#                 1 AS is_similar_item
#             FROM `tabSimilar Item Table`
#             WHERE parenttype = 'Item'
#             GROUP BY parent
#         ) similar_check
#             ON similar_check.item_code = item.item_code

#         LEFT JOIN `tabCataloge Item Details` tci
#             ON tci.item_code = item.name

#         LEFT JOIN `tabCataloge Master` tcm
#             ON tcm.name = tci.parent
#             {customer_join}

#         LEFT JOIN `tabBOM` bom
#             ON item.item_code = bom.item

#         LEFT JOIN `tabBOM Metal Detail` mt
#             ON bom.name = mt.parent

#         LEFT JOIN `tabBOM Gemstone Detail` gd
#             ON bom.name = gd.parent

#         LEFT JOIN `tabBOM Diamond Detail` dd
#             ON bom.name = dd.parent

#         LEFT JOIN `tabBOM Finding Detail` fd
#             ON bom.name = fd.parent

#         LEFT JOIN `tabItem Default` idf
#             ON item.item_name = idf.parent

#         WHERE
#             {where_clause}
#             AND item.item_code IN %(item_codes)s

#         GROUP BY item.item_code

#         ORDER BY item.creation DESC
#         """
    
#     # base_query = f"""
#     #     SELECT
#     #         item.name,
#     #         bom.name,
#     #         idf.company,
#     #         tci.trending,
#     #         tci.name AS catalog_item_details_name,
#     #         {wishlist_case},

#     #         item.creation,
#     #         item.item_code,
#     #         item.item_category,
#     #         item.image,
#     #         item.sketch_image,
#     #         item.front_view AS cad_image,

#     #         CASE
#     #             WHEN item.front_view = item.image THEN 'CAD Image'
#     #             ELSE 'FG Image'
#     #         END AS image_remark,

#     #         item.item_subcategory,
#     #         item.stylebio,

#     #         bom.tag_no,
#     #         bom.diamond_quality,
#     #         item.setting_type,

#     #         FORMAT(bom.gross_weight, 3) AS gross_metal_weight,
#     #         FORMAT(bom.metal_and_finding_weight, 3) AS net_metal_finding_weight,
#     #         FORMAT(bom.total_diamond_weight_in_gms, 3) AS total_diamond_weight_in_gms,
#     #         FORMAT(bom.other_weight, 3) AS other_weight,
#     #         FORMAT(bom.finding_weight_, 3) AS finding_weight_,

#     #         bom.metal_colour,
#     #         bom.metal_touch,
#     #         bom.metal_purity,

#     #         FORMAT(bom.total_gemstone_weight_in_gms, 3) AS total_gemstone_weight_in_gms,

#     #         bom.total_diamond_pcs,
#     #         bom.total_gemstone_pcs,

#     #         FORMAT(bom.gemstone_weight, 3) AS gemstone_weight,
#     #         FORMAT(bom.gold_to_diamond_ratio, 3) AS gold_diamond_ratio,
#     #         FORMAT(bom.diamond_ratio, 3) AS diamond_ratio,
#     #         FORMAT(bom.metal_to_diamond_ratio_excl_of_finding, 3) AS metal_diamond_ratio,

#     #         bom.navratna,
#     #         bom.lock_type,
#     #         bom.feature,
#     #         bom.enamal,
#     #         bom.rhodium,
#     #         bom.sizer_type,

#     #         bom.height,
#     #         bom.length,
#     #         bom.width,
#     #         bom.breadth,
#     #         bom.product_size,

#     #         bom.design_style,
#     #         bom.nakshi_from,
#     #         bom.vanki_type,
#     #         bom.total_length,
#     #         bom.detachable,
#     #         bom.back_side_size,
#     #         bom.changeable,

#     #         item.variant_of,

#     #         CASE
#     #             WHEN vc.variant_count > 1 THEN 1
#     #             ELSE 0
#     #         END AS rn,

#     #         CASE
#     #             WHEN set_check.is_set_item = 1 THEN 1
#     #             ELSE 0
#     #         END AS is_set_item,

#     #         CASE
#     #             WHEN similar_check.is_similar_item = 1 THEN 1
#     #             ELSE 0
#     #         END AS is_similar_item,

#     #         bom.finding_pcs,
#     #         bom.total_other_pcs,
#     #         bom.total_other_weight,
#     #         bom.custom_rating AS rating,

#     #         GROUP_CONCAT(
#     #             DISTINCT item.name
#     #             ORDER BY item.creation ASC
#     #         ) AS variant_name,

#     #         GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
#     #         GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
#     #         GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
#     #         GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,

#     #         GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
#     #         GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,

#     #         GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
#     #         GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
#     #         GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
#     #         GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm, 3)) AS size_in_mm,
#     #         GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,

#     #         GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
#     #         GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
#     #         GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size, 3)) AS finding_size,

#     #         GROUP_CONCAT(
#     #             DISTINCT CASE
#     #                 WHEN dam.parentfield = 'custom_age_group'
#     #                 THEN dam.design_attribute
#     #             END
#     #         ) AS age_group,

#     #         GROUP_CONCAT(
#     #             DISTINCT CASE
#     #                 WHEN dam.parentfield = 'custom_gender'
#     #                 THEN dam.design_attribute
#     #             END
#     #         ) AS gender,

#     #         GROUP_CONCAT(
#     #             DISTINCT CASE
#     #                 WHEN dam.parentfield = 'custom_occasion'
#     #                 THEN dam.design_attribute
#     #             END
#     #         ) AS occasion,

#     #         GROUP_CONCAT(
#     #             DISTINCT CASE
#     #                 WHEN dam.parentfield = 'custom_shapes'
#     #                 THEN dam.design_attribute
#     #             END
#     #         ) AS shapes,

#     #         GROUP_CONCAT(
#     #             DISTINCT CASE
#     #                 WHEN dam.parentfield = 'custom_collection'
#     #                 THEN dam.design_attribute
#     #             END
#     #         ) AS custom_collection,

#     #         GROUP_CONCAT(
#     #             DISTINCT CASE
#     #                 WHEN dam.parentfield = 'custom_language'
#     #                 THEN dam.design_attribute
#     #             END
#     #         ) AS custom_language,

#     #         GROUP_CONCAT(
#     #             DISTINCT CASE
#     #                 WHEN dam.parentfield = 'custom_zodiac'
#     #                 THEN dam.design_attribute
#     #             END
#     #         ) AS custom_zodiac,

#     #         GROUP_CONCAT(
#     #             DISTINCT CASE
#     #                 WHEN dam.parentfield = 'custom_animalbirds'
#     #                 THEN dam.design_attribute
#     #             END
#     #         ) AS custom_animalbirds,

#     #         GROUP_CONCAT(
#     #             DISTINCT CASE
#     #                 WHEN dam.parentfield = 'custom_alphabetnumber'
#     #                 THEN dam.design_attribute
#     #             END
#     #         ) AS custom_alphabetnumber,

#     #         GROUP_CONCAT(
#     #             DISTINCT CASE
#     #                 WHEN dam.parentfield = 'custom_religious'
#     #                 THEN dam.design_attribute
#     #             END
#     #         ) AS religious

#     #     FROM `tabItem` AS item

#     #     LEFT JOIN (
#     #         SELECT
#     #             IFNULL(i.variant_of, i.item_code) AS group_key,
#     #             COUNT(DISTINCT i.item_code) AS variant_count
#     #         FROM `tabItem` AS i
#     #         INNER JOIN `tabBOM` AS b
#     #             ON i.item_code = b.item
#     #             AND b.bom_type = 'Finish Goods'
#     #         GROUP BY IFNULL(i.variant_of, i.item_code)
#     #     ) vc
#     #         ON vc.group_key = IFNULL(item.variant_of, item.item_code)

#     #     LEFT JOIN (
#     #         SELECT
#     #             sit.parent AS item_code,
#     #             CASE
#     #                 WHEN COUNT(*) > 0 THEN 1
#     #                 ELSE 0
#     #             END AS is_set_item
#     #         FROM `tabSet Item Table` sit
#     #         GROUP BY sit.parent
#     #     ) AS set_check
#     #         ON set_check.item_code = item.item_code

#     #     LEFT JOIN (
#     #         SELECT
#     #             sit.parent AS item_code,
#     #             CASE
#     #                 WHEN COUNT(*) > 0 THEN 1
#     #                 ELSE 0
#     #             END AS is_similar_item
#     #         FROM `tabSimilar Item Table` sit
#     #         WHERE sit.parenttype = 'Item'
#     #         GROUP BY sit.parent
#     #     ) AS similar_check
#     #         ON similar_check.item_code = item.item_code

#     #     INNER JOIN (
#     #         SELECT
#     #             IFNULL(i.variant_of, i.item_code) AS group_key,
#     #             MIN(i.item_code) AS first_item_code
#     #         FROM `tabItem` AS i
#     #         INNER JOIN `tabBOM` AS b
#     #             ON i.item_code = b.item
#     #         INNER JOIN `tabItem Default` AS idf3
#     #             ON i.item_name = idf3.parent
#     #         WHERE {sub_where}
#     #         GROUP BY IFNULL(i.variant_of, i.item_code)
#     #     ) AS first_variant
#     #         ON item.item_code = first_variant.first_item_code

#     #     LEFT JOIN `tabCataloge Item Details` AS tci
#     #         ON tci.item_code = item.name

#     #     LEFT JOIN `tabCataloge Master` AS tcm
#     #         ON tcm.name = tci.parent
#     #         {customer_join}

#     #     LEFT JOIN `tabBOM` AS bom
#     #         ON item.item_code = bom.item

#     #     LEFT JOIN `tabBOM Metal Detail` AS mt
#     #         ON bom.name = mt.parent

#     #     LEFT JOIN `tabBOM Gemstone Detail` AS gd
#     #         ON bom.name = gd.parent

#     #     LEFT JOIN `tabBOM Diamond Detail` AS dd
#     #         ON bom.name = dd.parent

#     #     LEFT JOIN `tabBOM Finding Detail` AS fd
#     #         ON bom.name = fd.parent

#     #     LEFT JOIN `tabBOM Other Detail` AS od
#     #         ON bom.name = od.parent

#     #     LEFT JOIN `tabItem Default` AS idf
#     #         ON item.item_name = idf.parent
            
#     #     LEFT JOIN `tabDesign Attribute - Multiselect` dam
#     #            ON dam.parent = item.item_code

#     #     WHERE
#     #         {where_clause}
           
#     #     GROUP BY
#     #         item.item_code,
#     #         item.variant_of

#     #     ORDER BY
#     #         item.creation DESC
#     # """
    
#     db_data = frappe.db.sql(
#             base_query,
#             values,
#             as_dict=True
#     )
    
#     start = values.get("offset", 0)
#     end = start + values.get("page_size", 50)
    
#     return db_data[start:end]


def get_is_filter(search, values, wishlist_case, sub_where, customer_join, where_clause):
    if search:
        values["search"] = f"%{search}%"
    else:
        values["search"] = "%%"

    matched_item_codes = []
    if search:

        search_terms = [x.strip() for x in search.split(",") if x.strip()]
        search_conditions = []

        for i, term in enumerate(search_terms):
            values[f"search_{i}"] = f"%{term}%"
            values[f"exact_search_{i}"] = term
            search_conditions.append(f"""               
                item.item_category LIKE %(search_{i})s
                OR item.item_subcategory LIKE %(search_{i})s
                OR item.setting_type LIKE %(search_{i})s
                OR bom.sub_setting_type1 LIKE %(search_{i})s
                OR bom.metal_touch LIKE %(search_{i})s
                OR bom.metal_colour LIKE %(search_{i})s
                OR bom.diamond_quality LIKE %(search_{i})s
                OR bom.design_style LIKE %(search_{i})s
                OR bom.rhodium LIKE %(search_{i})s
                OR dam.design_attribute = %(exact_search_{i})s
            """)

        search_where = " OR ".join(search_conditions)

        setting_filter = ""

        if "Open" in search_terms:
            setting_filter = """
                AND bom.sub_setting_type1 != 'Close-Open Setting'
            """
        elif "Close-Open Setting" in search_terms:
            setting_filter = """
                AND bom.sub_setting_type1 = 'Close-Open Setting'
                AND item.setting_type = 'Open'
            """
        elif "Close" in search_terms:  
            setting_filter = """
                 AND item.setting_type = 'Close'
            """

        matched_item_codes = frappe.db.sql(
            f"""
            SELECT DISTINCT
                IFNULL(item.variant_of, item.item_code) AS item_code
            FROM `tabItem` item

            INNER JOIN `tabBOM` bom
                ON bom.item = item.item_code

            LEFT JOIN `tabItem Default` idf
                ON idf.parent = item.item_name

            LEFT JOIN `tabDesign Attribute - Multiselect` dam
                ON dam.parent = item.item_code

            WHERE
                bom.bom_type = 'Finish Goods'
                {"AND idf.company = %(company)s" if values.get("company") else ""}
                AND (
                    {search_where}
                )
                {setting_filter}
            """,
            values,
            as_list=True
        )

        matched_item_codes = list(set(row[0] for row in matched_item_codes))

        if not matched_item_codes:
            return []

        values["item_codes"] = tuple(matched_item_codes)

        where_clause += """
            AND IFNULL(item.variant_of, item.item_code) IN %(item_codes)s
        """

    base_query = f"""
        SELECT
            item.name,
            bom.name,
            bom.sub_setting_type1,
            idf.company,
            tci.trending,
            tci.name AS catalog_item_details_name,
            {wishlist_case},
            item.creation,
            item.item_code,
            item.item_category,
            item.image,
            item.sketch_image,
            item.front_view AS cad_image,

            CASE
                WHEN item.front_view = item.image THEN 'CAD Image'
                ELSE 'FG Image'
            END AS image_remark,

            item.item_subcategory,
            item.stylebio,
            bom.tag_no,
            bom.diamond_quality,
            item.setting_type,

            FORMAT(bom.gross_weight,3) AS gross_metal_weight,
            FORMAT(bom.metal_and_finding_weight,3) AS net_metal_finding_weight,
            FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
            FORMAT(bom.other_weight,3) AS other_weight,
            FORMAT(bom.finding_weight_,3) AS finding_weight_,

            bom.metal_colour,
            bom.metal_touch,
            bom.metal_purity,
            FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,

            bom.total_diamond_pcs,
            bom.total_gemstone_pcs,
            FORMAT(bom.gemstone_weight,3) AS gemstone_weight,

            FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
            FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
            FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,
            
            bom.navratna,
            bom.lock_type,
            bom.feature,
            bom.enamal,
            bom.rhodium,
            bom.sizer_type,

            bom.height,
            bom.length,
            bom.width,
            bom.breadth,
            bom.product_size,

            bom.design_style,
            bom.nakshi_from,
            bom.vanki_type,
            bom.total_length,
            bom.detachable,
            bom.back_side_size,
            bom.changeable,

            item.variant_of,

            CASE
                WHEN vc.variant_count > 1 THEN 1
                ELSE 0
            END AS rn,

            CASE
                WHEN set_check.is_set_item = 1 THEN 1
                ELSE 0
            END AS is_set_item,

            CASE
                WHEN similar_check.is_similar_item = 1 THEN 1
                ELSE 0
            END AS is_similar_item,

            bom.finding_pcs,
            bom.total_other_pcs,
            bom.total_other_weight,
            bom.custom_rating AS rating,

            GROUP_CONCAT(DISTINCT item.name ORDER BY item.creation ASC) AS variant_name,

            GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
            GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
            GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
            GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,

            GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
            GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,

            GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
            GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
            GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
            GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
            GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,

            GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
            GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
            GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size,
            
            GROUP_CONCAT(DISTINCT CASE WHEN td.design_attributes = 'Age Group' THEN td.design_attribute_value_1 END) AS age_group,
            GROUP_CONCAT(DISTINCT CASE WHEN td.design_attributes = 'Gender' THEN td.design_attribute_value_1 END) AS gender,
            GROUP_CONCAT(DISTINCT CASE WHEN td.design_attributes = 'Occasion' THEN td.design_attribute_value_1 END) AS occasion,
            GROUP_CONCAT(DISTINCT CASE WHEN td.design_attributes = 'Shapes' THEN td.design_attribute_value_1 END) AS shapes


        FROM `tabItem` item

        INNER JOIN (
            SELECT
                IFNULL(i.variant_of, i.item_code) AS group_key,
                MIN(i.item_code) AS first_item_code
            FROM `tabItem` i
            INNER JOIN `tabBOM` b
                ON i.item_code = b.item
            INNER JOIN `tabItem Default` idf3
                ON i.item_name = idf3.parent
            WHERE {sub_where}
            GROUP BY IFNULL(i.variant_of, i.item_code)
        ) first_variant
            ON item.item_code = first_variant.first_item_code

        LEFT JOIN (
            SELECT
                IFNULL(i.variant_of, i.item_code) AS group_key,
                COUNT(DISTINCT i.item_code) AS variant_count
            FROM `tabItem` i
            INNER JOIN `tabBOM` b
                ON i.item_code = b.item
                AND b.bom_type = 'Finish Goods'
            GROUP BY IFNULL(i.variant_of, i.item_code)
        ) vc
            ON vc.group_key = IFNULL(item.variant_of, item.item_code)

        LEFT JOIN (
            SELECT
                parent AS item_code,
                1 AS is_set_item
            FROM `tabSet Item Table`
            GROUP BY parent
        ) set_check
            ON set_check.item_code = item.item_code

        LEFT JOIN (
            SELECT
                parent AS item_code,
                1 AS is_similar_item
            FROM `tabSimilar Item Table`
            WHERE parenttype = 'Item'
            GROUP BY parent
        ) similar_check
            ON similar_check.item_code = item.item_code

        LEFT JOIN `tabCataloge Item Details` tci
            ON tci.item_code = item.name

        LEFT JOIN `tabCataloge Master` tcm
            ON tcm.name = tci.parent
            {customer_join}

        LEFT JOIN `tabBOM` bom
            ON item.item_code = bom.item

        LEFT JOIN `tabBOM Metal Detail` mt
            ON bom.name = mt.parent

        LEFT JOIN `tabBOM Gemstone Detail` gd
            ON bom.name = gd.parent

        LEFT JOIN `tabBOM Diamond Detail` dd
            ON bom.name = dd.parent

        LEFT JOIN `tabBOM Finding Detail` fd
            ON bom.name = fd.parent

        LEFT JOIN `tabItem Default` idf
            ON item.item_name = idf.parent
            
        LEFT JOIN `tabDesign Attributes` td      
            ON td.parent = item.item_code

        WHERE
            {where_clause}

        GROUP BY item.item_code

        ORDER BY item.creation DESC
    """

    db_data = frappe.db.sql(
        base_query,
        values,
        as_dict=True
    )

    item_codes = [row.item_code for row in db_data]
    if item_codes:
        db_res = frappe.db.sql("""
            SELECT parent, parentfield,
            GROUP_CONCAT(design_attribute ORDER BY design_attribute SEPARATOR ', ') AS design_attributes
            FROM `tabDesign Attribute - Multiselect`
            WHERE parent IN %(data)s
            GROUP BY parent, parentfield
        """, {"data": tuple(item_codes)}, as_dict=True)

        attr_map = {}
        for row in db_res:
            parent = row["parent"]
            field = row["parentfield"].replace("custom_", "")
            value = row["design_attributes"]
            if parent not in attr_map:
                attr_map[parent] = {}
            attr_map[parent][field] = value

        for row in db_data:
            attrs = attr_map.get(row.item_code, {})
            for key, value in attrs.items():
                row[key] = value

            row["custom_collection"] = row.get("custom_collection") or None
            row["custom_language"] = row.get("custom_language") or None
            row["custom_zodiac"] = row.get("custom_zodiac") or None
            row["custom_animalbirds"] = row.get("custom_animalbirds") or None
            row["custom_alphabetnumber"] = row.get("custom_alphabetnumber") or None
            row["religious"] = row.get("religious") or None

    start = values.get("offset", 0)
    end = start + values.get("page_size", 50)

    return db_data[start:end]


@frappe.whitelist(allow_guest=True)
def catalogue_data22(selectedSubcategory=None, itemCategory=None, itemCode=None, metalType=None, company=None, customer=None, page=1, page_size=50, is_filter=None, search=None):

    if selectedSubcategory is None:
        selectedSubcategory = frappe.form_dict.get("selectedSubcategory")

    if itemCode is None:
        itemCode = frappe.form_dict.get("itemCode")

    if metalType is None:
        metalType = frappe.form_dict.get("metalType")

    if itemCategory is None:
        itemCategory = frappe.form_dict.get("itemCategory")
        
    values = {}

    # ---------------- FILTERS ----------------
    sub_where = "b.bom_type = 'Finish Goods' AND i.item_group != 'Design DNU'"
    where_clause = "1=1 AND bom.bom_type = 'Finish Goods' AND item.item_group != 'Design DNU'"

    if metalType:
        sub_where += " AND b.metal_type = %(metalType)s"
        where_clause += " AND bom.metal_type = %(metalType)s"
        values["metalType"] = metalType

    if selectedSubcategory:
        sub_where += " AND i.item_subcategory = %(selectedSubcategory)s"
        where_clause += " AND item.item_subcategory = %(selectedSubcategory)s"
        values["selectedSubcategory"] = selectedSubcategory

    if itemCategory:
        sub_where += " AND i.item_category = %(itemCategory)s"
        where_clause += " AND item.item_category = %(itemCategory)s"
        values["itemCategory"] = itemCategory

    if itemCode:
        sub_where += " AND i.item_code = %(itemCode)s"
        where_clause += " AND item.item_code = %(itemCode)s"
        values["itemCode"] = itemCode

    if company:
        sub_where += " AND idf3.company = %(company)s"
        where_clause += " AND idf.company = %(company)s"
        values["company"] = company
    else:
        sub_where += " AND idf3.company = 'Gurukrupa Export Private Limited'"
        where_clause += " AND idf.company = 'Gurukrupa Export Private Limited'"

    # wishlist
    if customer:
        wishlist_case = "MAX(CASE WHEN tci.wishlist = 1 AND tcm.customer IS NOT NULL THEN 1 ELSE 0 END) AS wishlist"
        customer_join = "AND tcm.customer = %(customer)s"
        values["customer"] = customer
    else:
        wishlist_case = "0 AS wishlist"
        customer_join = ""
        
    page_param = frappe.form_dict.get("page")
    
    if page_param is None:
        return {
            "data": []
        }
    
    page = int(page_param)
    is_filter = int(frappe.form_dict.get("is_filter", 0) or 0)

    if is_filter == 1:
        page = frappe.form_dict.get("page", page)
        page_size = frappe.form_dict.get("page_size", page_size)
        
        page = int(page)
        page_size = int(page_size)
        
        offset = (page - 1) * page_size
        
        values["page_size"] = page_size
        values["offset"] = offset
        
        db_filter_data = get_is_filter(search, values, wishlist_case, sub_where, customer_join, where_clause)
        
        return db_filter_data
    
    
    base_query = f"""
        SELECT
            item.name,
            bom.name,
            bom.sub_setting_type1,
            idf.company,
            tci.trending,
            tci.name as catalog_item_details_name,
            {wishlist_case},
            item.creation,
            item.item_code,
            item.item_category,
            item.image,
            item.sketch_image,
            item.front_view AS cad_image,
            CASE
                WHEN item.front_view = item.image THEN 'CAD Image'
                ELSE 'FG Image'
            END AS image_remark,
            item.item_subcategory,
            item.stylebio,
            bom.tag_no,
            bom.diamond_quality,
            item.setting_type,

            FORMAT(bom.gross_weight,3) AS gross_metal_weight,
            FORMAT(bom.metal_and_finding_weight,3) AS net_metal_finding_weight,
            FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
            FORMAT(bom.other_weight,3) AS other_weight,
            FORMAT(bom.finding_weight_,3) AS finding_weight_,

            bom.metal_colour,
            bom.metal_touch,
            bom.metal_purity,
            FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,

            bom.total_diamond_pcs,
            bom.total_gemstone_pcs,
            FORMAT(bom.gemstone_weight,3) AS gemstone_weight,

            FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
            FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
            FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,

            bom.navratna,
            bom.lock_type,
            bom.feature,
            bom.enamal,
            bom.rhodium,
            bom.sizer_type,

            bom.height,
            bom.length,
            bom.width,
            bom.breadth,
            bom.product_size,

            bom.design_style,
            bom.nakshi_from,
            bom.vanki_type,
            bom.total_length,
            bom.detachable,
            bom.back_side_size,
            bom.changeable,

            item.variant_of,

            CASE 
                WHEN vc.variant_count > 1 THEN 1 
                ELSE 0 
            END AS rn,

            CASE 
               WHEN set_check.is_set_item = 1 THEN 1 
               ELSE 0 
            END AS is_set_item,
            
            CASE 
                WHEN similar_check.is_similar_item = 1 THEN 1 
                ELSE 0 
            END AS is_similar_item,

            bom.finding_pcs,
            bom.total_other_pcs,
            bom.total_other_weight,
            bom.custom_rating AS rating, 

            GROUP_CONCAT(DISTINCT item.name ORDER BY item.creation ASC) AS variant_name,

            GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
            GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,

            GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
            GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
            GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
            GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,

            GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
            GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,

            GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
            GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
            GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
            GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
            GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,

            GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
            GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
            GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size

        FROM `tabItem` AS item

        LEFT JOIN (
            SELECT 
                IFNULL(i.variant_of, i.item_code) AS group_key,
                COUNT(DISTINCT i.item_code) AS variant_count
            FROM `tabItem` AS i
            INNER JOIN `tabBOM` AS b ON i.item_code = b.item AND b.bom_type = 'Finish Goods'
            GROUP BY IFNULL(i.variant_of, i.item_code)
        ) vc ON vc.group_key = IFNULL(item.variant_of, item.item_code)

        LEFT JOIN (
            SELECT 
                sit.parent AS item_code,
                CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END AS is_set_item
            FROM `tabSet Item Table` sit
            GROUP BY sit.parent
        ) AS set_check ON set_check.item_code = item.item_code
        
        LEFT JOIN (
        SELECT 
            sit.parent AS item_code,
            CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END AS is_similar_item
            FROM `tabSimilar Item Table` sit
            WHERE sit.parenttype = 'Item'
            GROUP BY sit.parent
        ) AS similar_check ON similar_check.item_code = item.item_code

        INNER JOIN (
            SELECT
                IFNULL(i.variant_of, i.item_code) AS group_key,
                MIN(i.item_code) AS first_item_code
            FROM `tabItem` AS i
            INNER JOIN `tabBOM` AS b ON i.item_code = b.item
            INNER JOIN `tabItem Default` AS idf3 ON i.item_name = idf3.parent
            WHERE {sub_where}
            GROUP BY IFNULL(i.variant_of, i.item_code)
        ) AS first_variant
            ON item.item_code = first_variant.first_item_code

        LEFT JOIN `tabCataloge Item Details` AS tci ON tci.item_code = item.name
        LEFT JOIN `tabCataloge Master` AS tcm ON tcm.name = tci.parent {customer_join}
        LEFT JOIN `tabBOM` AS bom ON item.item_code = bom.item
        LEFT JOIN `tabDesign Attributes` AS td ON item.item_code = td.parent
        LEFT JOIN `tabBOM Metal Detail` AS mt ON bom.name = mt.parent
        LEFT JOIN `tabBOM Gemstone Detail` AS gd ON bom.name = gd.parent
        LEFT JOIN `tabBOM Diamond Detail` AS dd ON bom.name = dd.parent
        LEFT JOIN `tabBOM Finding Detail` AS fd ON bom.name = fd.parent
        LEFT JOIN `tabBOM Other Detail` AS od ON bom.name = od.parent
        LEFT JOIN `tabItem Default` AS idf ON item.item_name = idf.parent

        WHERE {where_clause}
        GROUP BY item.item_code, item.variant_of
        ORDER BY item.creation DESC
        # LIMIT %(page_size)s OFFSET %(offset)s
    """
    
    db_data = None
    
    filters = None
    
    page = frappe.form_dict.get("page", page)
    page_size = frappe.form_dict.get("page_size", page_size)
        
    page = int(page)
    page_size = int(page_size)
        
    offset = (page - 1) * page_size
        
    values["page_size"] = page_size
    values["offset"] = offset
    
    if page == 1 and is_filter == 0:
        db_data = frappe.db.sql(
            base_query,
            values,
            as_dict=True
        )
        
    else:
        paginated_query = base_query + """
            LIMIT %(page_size)s OFFSET %(offset)s
        """

        db_data = frappe.db.sql(
            paginated_query,
            values,
            as_dict=True
        )
    

    # -------- MULTISELECT ATTRIBUTES --------
    item_codes = [row.item_code for row in db_data]
    # frappe.throw(f"Total Records: {len(db_data)}")
    if item_codes:
        db_res = frappe.db.sql("""
            SELECT parent, parentfield,
            GROUP_CONCAT(design_attribute ORDER BY design_attribute SEPARATOR ', ') AS design_attributes
            FROM `tabDesign Attribute - Multiselect`
            WHERE parent IN %(data)s
            GROUP BY parent, parentfield
        """, {"data": tuple(item_codes)}, as_dict=True)
    else:
        db_res = []
        
    count_query = frappe.db.sql(f"""
    SELECT COUNT(*)
        FROM (
            SELECT IFNULL(item.variant_of, item.item_code)
            FROM `tabItem` item
            LEFT JOIN `tabBOM` bom ON item.item_code = bom.item
            LEFT JOIN `tabItem Default` idf ON item.item_name = idf.parent
            WHERE {where_clause}
            GROUP BY IFNULL(item.variant_of, item.item_code)
        ) t
        """, values)

    total_count = count_query[0][0]

    attr_map = {}
    for row in db_res:
        parent = row["parent"]
        field = row["parentfield"].replace("custom_", "")
        value = row["design_attributes"]
        if parent not in attr_map:
            attr_map[parent] = {}
        attr_map[parent][field] = value

    for row in db_data:
        attrs = attr_map.get(row.item_code, {})
        for key, value in attrs.items():
            row[key] = value

        row["custom_collection"] = row.get("custom_collection") or None
        row["custom_language"] = row.get("custom_language") or None
        row["custom_zodiac"] = row.get("custom_zodiac") or None
        row["custom_animalbirds"] = row.get("custom_animalbirds") or None
        row["custom_alphabetnumber"] = row.get("custom_alphabetnumber") or None
        row["religious"] = row.get("religious") or None

    if page == 1 and is_filter == 0:
        filters = get_method(db_data)
        return {
            "data": db_data[0:50],
            "filters":filters,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "has_more": (offset + page_size) <total_count
        }
        
    # frappe.throw(f"Total Records: {len(db_data)}")
    return {
        "data": db_data,
        "filters":filters,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "has_more": (offset + page_size) < total_count
    }


# @frappe.whitelist(allow_guest=True)
# def catalogue_data_final(selectedSubcategory=None, itemCategory=None, itemCode=None, metalType=None, company=None, customer=None):

#     if selectedSubcategory is None:
#         selectedSubcategory = frappe.form_dict.get("selectedSubcategory")

#     if itemCode is None:
#         itemCode = frappe.form_dict.get("itemCode")

#     if metalType is None:
#         metalType = frappe.form_dict.get("metalType")

#     if itemCategory is None:
#         itemCategory = frappe.form_dict.get("itemCategory")

#     values = {}

#     # ---------------- FILTERS ----------------
#     sub_where = "b.bom_type = 'Finish Goods'"
#     where_clause = "1=1 AND bom.bom_type = 'Finish Goods'"

#     if metalType:
#         sub_where += " AND b.metal_type = %(metalType)s"
#         where_clause += " AND bom.metal_type = %(metalType)s"
#         values["metalType"] = metalType

#     if selectedSubcategory:
#         sub_where += " AND i.item_subcategory = %(selectedSubcategory)s"
#         where_clause += " AND item.item_subcategory = %(selectedSubcategory)s"
#         values["selectedSubcategory"] = selectedSubcategory

#     if itemCategory:
#         sub_where += " AND i.item_category = %(itemCategory)s"
#         where_clause += " AND item.item_category = %(itemCategory)s"
#         values["itemCategory"] = itemCategory

#     if itemCode:
#         sub_where += " AND i.item_code = %(itemCode)s"
#         where_clause += " AND item.item_code = %(itemCode)s"
#         values["itemCode"] = itemCode

#     if company:
#         sub_where += " AND idf3.company = %(company)s"
#         where_clause += " AND idf.company = %(company)s"
#         values["company"] = company
#     else:
#         sub_where += " AND idf3.company = 'Gurukrupa Export Private Limited'"
#         where_clause += " AND idf.company = 'Gurukrupa Export Private Limited'"

#     # wishlist
#     if customer:
#         wishlist_case = "MAX(CASE WHEN tci.wishlist = 1 AND tcm.customer IS NOT NULL THEN 1 ELSE 0 END) AS wishlist"
#         customer_join = "AND tcm.customer = %(customer)s"
#         values["customer"] = customer
#     else:
#         wishlist_case = "0 AS wishlist"
#         customer_join = ""

#     db_data = frappe.db.sql(f"""
#         SELECT
#             item.name,
#             bom.name,
#             idf.company,
#             tci.trending,
#             {wishlist_case},
#             item.creation,
#             item.item_code,
#             item.item_category,
#             item.image,
#             item.sketch_image,
#             item.front_view AS cad_image,
#             CASE
#                 WHEN item.front_view = item.image THEN 'CAD Image'
#                 ELSE 'FG Image'
#             END AS image_remark,
#             item.item_subcategory,
#             item.stylebio,
#             bom.tag_no,
#             bom.diamond_quality,
#             item.setting_type,

#             FORMAT(bom.gross_weight,3) AS gross_metal_weight,
#             FORMAT(bom.metal_and_finding_weight,3) AS net_metal_finding_weight,
#             FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
#             FORMAT(bom.other_weight,3) AS other_weight,
#             FORMAT(bom.finding_weight_,3) AS finding_weight_,

#             bom.metal_colour,
#             bom.metal_touch,
#             bom.metal_purity,
#             FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,

#             bom.total_diamond_pcs,
#             bom.total_gemstone_pcs,
#             FORMAT(bom.gemstone_weight,3) AS gemstone_weight,

#             FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
#             FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
#             FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,

#             bom.navratna,
#             bom.lock_type,
#             bom.feature,
#             bom.enamal,
#             bom.rhodium,
#             bom.sizer_type,

#             bom.height,
#             bom.length,
#             bom.width,
#             bom.breadth,
#             bom.product_size,

#             bom.design_style,
#             bom.nakshi_from,
#             bom.vanki_type,
#             bom.total_length,
#             bom.detachable,
#             bom.back_side_size,
#             bom.changeable,

#             item.variant_of,
            
#             CASE 
#                 WHEN vc.variant_count > 1 THEN 1 
#                 ELSE 0 
#             END AS rn,
            
#             CASE 
#                WHEN set_check.is_set_item = 1 THEN 1 
#                ELSE 0 
#             END AS is_set_item,
            
#             bom.finding_pcs,
#             bom.total_other_pcs,
#             bom.total_other_weight,
#             bom.custom_rating AS rating, 

#             GROUP_CONCAT(DISTINCT item.name ORDER BY item.creation ASC) AS variant_name,

#             GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
#             GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,

#             GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
#             GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
#             GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
#             GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,

#             GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
#             GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,

#             GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
#             GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
#             GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
#             GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
#             GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,

#             GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
#             GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
#             GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size

#         FROM `tabItem` AS item
        
#         LEFT JOIN (
#             SELECT 
#                 IFNULL(i.variant_of, i.item_code) AS group_key,
#                 COUNT(DISTINCT i.item_code) AS variant_count
#             FROM `tabItem` AS i
#             INNER JOIN `tabBOM` AS b ON i.item_code = b.item AND b.bom_type = 'Finish Goods'
#             GROUP BY IFNULL(i.variant_of, i.item_code)
#         ) vc ON vc.group_key = IFNULL(item.variant_of, item.item_code)
        
#         LEFT JOIN (
#                   SELECT 
#                       sit.parent AS item_code,
#                       CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END AS is_set_item
#                   FROM `tabSet Item Table` sit
#                   GROUP BY sit.parent
#         ) AS set_check ON set_check.item_code = item.item_code

#         INNER JOIN (
#             SELECT
#                 IFNULL(i.variant_of, i.item_code) AS group_key,
#                 MIN(i.item_code) AS first_item_code
#             FROM `tabItem` AS i
#             INNER JOIN `tabBOM` AS b ON i.item_code = b.item
#             INNER JOIN `tabItem Default` AS idf3 ON i.item_name = idf3.parent
#             WHERE {sub_where}
#             GROUP BY IFNULL(i.variant_of, i.item_code)
#         ) AS first_variant
#             ON item.item_code = first_variant.first_item_code

#         LEFT JOIN `tabCataloge Item Details` AS tci ON tci.item_code = item.name
#         LEFT JOIN `tabCataloge Master` AS tcm ON tcm.name = tci.parent {customer_join}
#         LEFT JOIN `tabBOM` AS bom ON item.item_code = bom.item
#         LEFT JOIN `tabDesign Attributes` AS td ON item.item_code = td.parent
#         LEFT JOIN `tabBOM Metal Detail` AS mt ON bom.name = mt.parent
#         LEFT JOIN `tabBOM Gemstone Detail` AS gd ON bom.name = gd.parent
#         LEFT JOIN `tabBOM Diamond Detail` AS dd ON bom.name = dd.parent
#         LEFT JOIN `tabBOM Finding Detail` AS fd ON bom.name = fd.parent
#         LEFT JOIN `tabBOM Other Detail` AS od ON bom.name = od.parent
#         LEFT JOIN `tabItem Default` AS idf ON item.item_name = idf.parent

#         WHERE {where_clause}
#         GROUP BY item.item_code, item.variant_of
#         ORDER BY item.creation DESC

#     """, values, as_dict=True)

#     # -------- MULTISELECT ATTRIBUTES --------
#     item_codes = [row.item_code for row in db_data]

#     if item_codes:
#         db_res = frappe.db.sql("""
#             SELECT parent, parentfield,
#             GROUP_CONCAT(design_attribute ORDER BY design_attribute SEPARATOR ', ') AS design_attributes
#             FROM `tabDesign Attribute - Multiselect`
#             WHERE parent IN %(data)s
#             GROUP BY parent, parentfield
#         """, {"data": tuple(item_codes)}, as_dict=True)
#     else:
#         db_res = []

#     attr_map = {}
#     for row in db_res:
#         parent = row["parent"]
#         field = row["parentfield"].replace("custom_", "")
#         value = row["design_attributes"]
#         if parent not in attr_map:
#             attr_map[parent] = {}
#         attr_map[parent][field] = value

#     for row in db_data:
#         attrs = attr_map.get(row.item_code, {})
#         for key, value in attrs.items():
#             row[key] = value

#         # ensure all fields present
#         row["custom_collection"] = row.get("custom_collection") or None
#         row["custom_language"] = row.get("custom_language") or None
#         row["custom_zodiac"] = row.get("custom_zodiac") or None
#         row["custom_animalbirds"] = row.get("custom_animalbirds") or None
#         row["custom_alphabetnumber"] = row.get("custom_alphabetnumber") or None
#         row["religious"] = row.get("religious") or None

#     # -------- SIMILAR ITEMS TABLE --------
#     # Step 1: Get all similar item_codes linked to main items (direct Item child)
#     if item_codes:
#         similar_links = frappe.db.sql("""
#             SELECT
#                 sit.parent AS main_item_code,
#                 sit.item_code AS similar_item_code
#             FROM `tabSimilar Item Table` AS sit
#             WHERE sit.parenttype = 'Item'
#             AND sit.parent IN %(item_codes)s
#         """, {"item_codes": tuple(item_codes)}, as_dict=True)
#     else:
#         similar_links = []

#     # Build map: { main_item_code -> [similar_item_codes] }
#     similar_link_map = {}
#     for row in similar_links:
#         main = row["main_item_code"]
#         if main not in similar_link_map:
#             similar_link_map[main] = []
#         similar_link_map[main].append(row["similar_item_code"])

#     # Collect all unique similar item codes
#     all_similar_codes = list({code for codes in similar_link_map.values() for code in codes})

#     # Step 2: Fetch full details for all similar items — NO BOM type filter (template + finish goods both)
#     if all_similar_codes:
#         similar_details_rows = frappe.db.sql("""
#             SELECT
#                 item.name,
#                 bom.name AS bom_name,
#                 idf.company,
#                 tci.trending,
#                 0 AS wishlist,
#                 item.creation,
#                 item.item_code,
#                 item.item_category,
#                 item.image,
#                 item.sketch_image,
#                 item.front_view AS cad_image,
#                 CASE
#                     WHEN item.front_view = item.image THEN 'CAD Image'
#                     ELSE 'FG Image'
#                 END AS image_remark,
#                 item.item_subcategory,
#                 item.stylebio,
#                 bom.tag_no,
#                 bom.diamond_quality,
#                 item.setting_type,

#                 FORMAT(bom.gross_weight,3) AS gross_metal_weight,
#                 FORMAT(bom.metal_and_finding_weight,3) AS net_metal_finding_weight,
#                 FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
#                 FORMAT(bom.other_weight,3) AS other_weight,
#                 FORMAT(bom.finding_weight_,3) AS finding_weight_,

#                 bom.metal_colour,
#                 bom.metal_touch,
#                 bom.metal_purity,
#                 FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,

#                 bom.total_diamond_pcs,
#                 bom.total_gemstone_pcs,
#                 FORMAT(bom.gemstone_weight,3) AS gemstone_weight,

#                 FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
#                 FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
#                 FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,

#                 bom.navratna,
#                 bom.lock_type,
#                 bom.feature,
#                 bom.enamal,
#                 bom.rhodium,
#                 bom.sizer_type,

#                 bom.height,
#                 bom.length,
#                 bom.width,
#                 bom.breadth,
#                 bom.product_size,

#                 bom.design_style,
#                 bom.nakshi_from,
#                 bom.vanki_type,
#                 bom.total_length,
#                 bom.detachable,
#                 bom.back_side_size,
#                 bom.changeable,

#                 item.variant_of,
#                 bom.finding_pcs,
#                 bom.total_other_pcs,
#                 bom.total_other_weight,
#                 item.item_code AS variant_name,

#                 GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
#                 GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,

#                 GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
#                 GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
#                 GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
#                 GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,

#                 GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
#                 GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,

#                 GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
#                 GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
#                 GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
#                 GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
#                 GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,

#                 GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
#                 GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
#                 GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size

#             FROM `tabItem` AS item
#             LEFT JOIN `tabBOM` AS bom ON item.item_code = bom.item
#             LEFT JOIN `tabCataloge Item Details` AS tci ON tci.item_code = item.name
#             LEFT JOIN `tabDesign Attributes` AS td ON item.item_code = td.parent
#             LEFT JOIN `tabBOM Metal Detail` AS mt ON bom.name = mt.parent
#             LEFT JOIN `tabBOM Gemstone Detail` AS gd ON bom.name = gd.parent
#             LEFT JOIN `tabBOM Diamond Detail` AS dd ON bom.name = dd.parent
#             LEFT JOIN `tabBOM Finding Detail` AS fd ON bom.name = fd.parent
#             LEFT JOIN `tabBOM Other Detail` AS od ON bom.name = od.parent
#             LEFT JOIN `tabItem Default` AS idf ON item.item_name = idf.parent

#             WHERE item.item_code IN %(similar_codes)s
#             GROUP BY item.item_code
#         """, {"similar_codes": tuple(all_similar_codes)}, as_dict=True)
#     else:
#         similar_details_rows = []

#     # Build map: { similar_item_code -> full detail dict }
#     similar_details_map = {row["item_code"]: row for row in similar_details_rows}

#     # Step 3: Attach full similar item details to each main row
#     for row in db_data:
#         linked_codes = similar_link_map.get(row.item_code, [])
#         row["similar_items"] = [
#             similar_details_map[code]
#             for code in linked_codes
#             if code in similar_details_map
#         ]

#     return db_data


# @frappe.whitelist(allow_guest=True)
# def catalogue_data2(selectedSubcategory=None, itemCategory=None, itemCode=None, metalType=None, company=None, customer=None):

#     if selectedSubcategory is None:
#         selectedSubcategory = frappe.form_dict.get("selectedSubcategory")

#     if itemCode is None:
#         itemCode = frappe.form_dict.get("itemCode")

#     if metalType is None:
#         metalType = frappe.form_dict.get("metalType")

#     if itemCategory is None:
#         itemCategory = frappe.form_dict.get("itemCategory")

#     values = {}

#     # ---------------- FILTERS ----------------
#     sub_where = "b.bom_type = 'Finish Goods'"
#     where_clause = "1=1 AND bom.bom_type = 'Finish Goods'"

#     if metalType:
#         sub_where += " AND b.metal_type = %(metalType)s"
#         where_clause += " AND bom.metal_type = %(metalType)s"
#         values["metalType"] = metalType

#     if selectedSubcategory:
#         sub_where += " AND i.item_subcategory = %(selectedSubcategory)s"
#         where_clause += " AND item.item_subcategory = %(selectedSubcategory)s"
#         values["selectedSubcategory"] = selectedSubcategory

#     if itemCategory:
#         sub_where += " AND i.item_category = %(itemCategory)s"
#         where_clause += " AND item.item_category = %(itemCategory)s"
#         values["itemCategory"] = itemCategory

#     if itemCode:
#         sub_where += " AND i.item_code = %(itemCode)s"
#         where_clause += " AND item.item_code = %(itemCode)s"
#         values["itemCode"] = itemCode

#     if company:
#         sub_where += " AND idf3.company = %(company)s"
#         where_clause += " AND idf.company = %(company)s"
#         values["company"] = company
#     else:
#         sub_where += " AND idf3.company = 'Gurukrupa Export Private Limited'"
#         where_clause += " AND idf.company = 'Gurukrupa Export Private Limited'"

#     # wishlist
#     if customer:
#         wishlist_case = "MAX(CASE WHEN tci.wishlist = 1 AND tcm.customer IS NOT NULL THEN 1 ELSE 0 END) AS wishlist"
#         customer_join = "AND tcm.customer = %(customer)s"
#         values["customer"] = customer
#     else:
#         wishlist_case = "0 AS wishlist"
#         customer_join = ""

#     db_data = frappe.db.sql(f"""
#         SELECT
#             item.name,
#             bom.name,
#             idf.company,
#             tci.trending,
#             {wishlist_case},
#             item.creation,
#             item.item_code,
#             item.item_category,
#             item.image,
#             item.sketch_image,
#             item.front_view AS cad_image,
#             CASE
#                 WHEN item.front_view = item.image THEN 'CAD Image'
#                 ELSE 'FG Image'
#             END AS image_remark,
#             item.item_subcategory,
#             item.stylebio,
#             bom.tag_no,
#             bom.diamond_quality,
#             item.setting_type,

#             FORMAT(bom.gross_weight,3) AS gross_metal_weight,
#             FORMAT(bom.metal_and_finding_weight,3) AS net_metal_finding_weight,
#             FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
#             FORMAT(bom.other_weight,3) AS other_weight,
#             FORMAT(bom.finding_weight_,3) AS finding_weight_,

#             bom.metal_colour,
#             bom.metal_touch,
#             bom.metal_purity,
#             FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,

#             bom.total_diamond_pcs,
#             bom.total_gemstone_pcs,
#             FORMAT(bom.gemstone_weight,3) AS gemstone_weight,

#             FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
#             FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
#             FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,

#             bom.navratna,
#             bom.lock_type,
#             bom.feature,
#             bom.enamal,
#             bom.rhodium,
#             bom.sizer_type,

#             bom.height,
#             bom.length,
#             bom.width,
#             bom.breadth,
#             bom.product_size,

#             bom.design_style,
#             bom.nakshi_from,
#             bom.vanki_type,
#             bom.total_length,
#             bom.detachable,
#             bom.back_side_size,
#             bom.changeable,

#             item.variant_of,
            
#             CASE 
#                 WHEN vc.variant_count >1 THEN 1 
#                 ELSE 0 
#             END AS rn,
            
#             bom.finding_pcs,
#             bom.total_other_pcs,
#             bom.total_other_weight,

#             GROUP_CONCAT(DISTINCT item.name ORDER BY item.creation ASC) AS variant_name,

#             GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
#             GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,

#             GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
#             GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
#             GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
#             GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,

#             GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
#             GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,

#             GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
#             GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
#             GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
#             GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
#             GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,

#             GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
#             GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
#             GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size

#         FROM `tabItem` AS item
        
#         LEFT JOIN (
#             SELECT 
#                 IFNULL(i.variant_of, i.item_code) AS group_key,
#                 COUNT(DISTINCT i.item_code) AS variant_count
#             FROM `tabItem` AS i
#             INNER JOIN `tabBOM` AS b ON i.item_code = b.item AND b.bom_type = 'Finish Goods'
#             GROUP BY IFNULL(i.variant_of, i.item_code)
#         ) vc ON vc.group_key = IFNULL(item.variant_of, item.item_code)


#         INNER JOIN (
#             SELECT
#                 IFNULL(i.variant_of, i.item_code) AS group_key,
#                 MIN(i.item_code) AS first_item_code
#             FROM `tabItem` AS i
#             INNER JOIN `tabBOM` AS b ON i.item_code = b.item
#             INNER JOIN `tabItem Default` AS idf3 ON i.item_name = idf3.parent
#             WHERE {sub_where}
#             GROUP BY IFNULL(i.variant_of, i.item_code)
#         ) AS first_variant
#             ON item.item_code = first_variant.first_item_code

#         LEFT JOIN `tabCataloge Item Details` AS tci ON tci.item_code = item.name
#         LEFT JOIN `tabCataloge Master` AS tcm ON tcm.name = tci.parent {customer_join}
#         LEFT JOIN `tabBOM` AS bom ON item.item_code = bom.item
#         LEFT JOIN `tabDesign Attributes` AS td ON item.item_code = td.parent
#         LEFT JOIN `tabBOM Metal Detail` AS mt ON bom.name = mt.parent
#         LEFT JOIN `tabBOM Gemstone Detail` AS gd ON bom.name = gd.parent
#         LEFT JOIN `tabBOM Diamond Detail` AS dd ON bom.name = dd.parent
#         LEFT JOIN `tabBOM Finding Detail` AS fd ON bom.name = fd.parent
#         LEFT JOIN `tabBOM Other Detail` AS od ON bom.name = od.parent
#         LEFT JOIN `tabItem Default` AS idf ON item.item_name = idf.parent

#         WHERE {where_clause}
#         GROUP BY item.item_code, item.variant_of
#         ORDER BY item.creation DESC

#     """, values, as_dict=True)

#     # -------- MULTISELECT ATTRIBUTES --------
#     item_codes = [row.item_code for row in db_data]

#     if item_codes:
#         db_res = frappe.db.sql("""
#             SELECT parent, parentfield,
#             GROUP_CONCAT(design_attribute ORDER BY design_attribute SEPARATOR ', ') AS design_attributes
#             FROM `tabDesign Attribute - Multiselect`
#             WHERE parent IN %(data)s
#             GROUP BY parent, parentfield
#         """, {"data": tuple(item_codes)}, as_dict=True)
#     else:
#         db_res = []

#     attr_map = {}
#     for row in db_res:
#         parent = row["parent"]
#         field = row["parentfield"].replace("custom_", "")
#         value = row["design_attributes"]
#         if parent not in attr_map:
#             attr_map[parent] = {}
#         attr_map[parent][field] = value

#     for row in db_data:
#         attrs = attr_map.get(row.item_code, {})
#         for key, value in attrs.items():
#             row[key] = value

#         # ensure all 76 fields present
#         row["custom_collection"] = row.get("custom_collection") or None
#         row["custom_language"] = row.get("custom_language") or None
#         row["custom_zodiac"] = row.get("custom_zodiac") or None
#         row["custom_animalbirds"] = row.get("custom_animalbirds") or None
#         row["custom_alphabetnumber"] = row.get("custom_alphabetnumber") or None
#         row["religious"] = row.get("religious") or None

#     return db_data


@frappe.whitelist(allow_guest=True)
def get_variants_by_itemcode(itemCode=None, customer=None):

    itemCode = frappe.form_dict.get("itemCode") or itemCode
    customer = frappe.form_dict.get("customer") or customer

    if not itemCode:
        return "Item Code Required"

    base_code = itemCode.split("-")[0]
    # base_code = itemCode

    # wishlist
    if customer:
        wishlist_case = "MAX(CASE WHEN tci.wishlist = 1 AND tcm.customer IS NOT NULL THEN 1 ELSE 0 END) AS wishlist"
        customer_join = "AND tcm.customer = %(customer)s"
    else:
        wishlist_case = "0 AS wishlist"
        customer_join = ""

    db_data = frappe.db.sql(f"""
        SELECT
            item.name,
            bom.name,
            tci.trending,
            {wishlist_case},
            item.creation,
            item.item_code,
            item.item_category,
            item.image,
            item.sketch_image,
            item.front_view AS cad_image,

            CASE
                WHEN item.front_view = item.image THEN 'CAD Image'
                ELSE 'FG Image'
            END AS image_remark,

            item.item_subcategory,
            item.stylebio,
            bom.tag_no,
            bom.diamond_quality,
            item.setting_type,

            -- FIXED ATTRIBUTE SOURCE
            GROUP_CONCAT(DISTINCT CASE WHEN td.design_attributes = 'Age Group' THEN td.design_attribute_value_1 END) AS age_group,
            GROUP_CONCAT(DISTINCT CASE WHEN td.design_attributes = 'Gender' THEN td.design_attribute_value_1 END) AS gender,
            GROUP_CONCAT(DISTINCT CASE WHEN td.design_attributes = 'Occasion' THEN td.design_attribute_value_1 END) AS occasion,
            GROUP_CONCAT(DISTINCT CASE WHEN td.design_attributes = 'Shapes' THEN td.design_attribute_value_1 END) AS shapes,

            FORMAT(bom.gross_weight,3) AS gross_metal_weight,
            FORMAT(bom.metal_and_finding_weight,3) AS net_metal_finding_weight,
            FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
            FORMAT(bom.other_weight,3) AS other_weight,
            FORMAT(bom.finding_weight_,3) AS finding_weight_,

            bom.metal_colour,
            bom.metal_touch,
            bom.metal_purity,
            bom.metal_type,   
            FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,

            bom.total_diamond_pcs,
            bom.total_gemstone_pcs,
            FORMAT(bom.gemstone_weight,3) AS gemstone_weight,

            FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
            FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
            FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,

            bom.navratna,
            bom.lock_type,
            bom.feature,
            bom.enamal,
            bom.rhodium,
            bom.sizer_type,

            bom.height,
            bom.length,
            bom.width,
            bom.breadth,
            bom.product_size,

            bom.design_style,
            bom.nakshi_from,
            bom.vanki_type,
            bom.total_length,
            bom.detachable,
            bom.back_side_size,
            bom.changeable,

            item.variant_of,
            bom.finding_pcs,
            bom.total_other_pcs,
            bom.total_other_weight,

            item.item_code AS variant_name,

            GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
            GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,

            GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
            GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
            GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
            GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_detail_touch,  

            GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
            GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,

            GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
            GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
            GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
            GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
            GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,

            GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
            GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
            GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size

        FROM `tabItem` AS item

        LEFT JOIN `tabCataloge Item Details` AS tci ON tci.item_code = item.name
        LEFT JOIN `tabCataloge Master` AS tcm ON tcm.name = tci.parent {customer_join}

        INNER JOIN `tabBOM` bom
            ON item.item_code = bom.item
            AND bom.bom_type = 'Finish Goods'

        LEFT JOIN `tabDesign Attributes` AS td ON item.item_code = td.parent
        LEFT JOIN `tabBOM Metal Detail` AS mt ON bom.name = mt.parent
        LEFT JOIN `tabBOM Gemstone Detail` AS gd ON bom.name = gd.parent
        LEFT JOIN `tabBOM Diamond Detail` AS dd ON bom.name = dd.parent
        LEFT JOIN `tabBOM Finding Detail` AS fd ON bom.name = fd.parent

        LEFT JOIN `tabItem Default` AS idf ON item.item_name = idf.parent

        # WHERE
        #     item.item_code LIKE %(base_code)s
        #     AND idf.company = 'Gurukrupa Export Private Limited'
        WHERE
            item.item_code LIKE %(base_code)s
            AND item.item_code != %(itemCode)s
            AND idf.company = 'Gurukrupa Export Private Limited'

        GROUP BY item.item_code
        ORDER BY item.creation ASC
    """, {"base_code": base_code + "%", "customer": customer, "itemCode": itemCode} , as_dict=True)
    # """, {"base_code": base_code + "%", "customer": customer}, as_dict=True)

    # -------- MULTISELECT MERGE --------
    item_codes = [row.item_code for row in db_data]

    if item_codes:
        db_res = frappe.db.sql("""
            SELECT parent, parentfield,
            GROUP_CONCAT(design_attribute SEPARATOR ', ') AS design_attributes
            FROM `tabDesign Attribute - Multiselect`
            WHERE parent IN %(data)s
            GROUP BY parent, parentfield
        """, {"data": tuple(item_codes)}, as_dict=True)
    else:
        db_res = []

    attr_map = {}
    for row in db_res:
        parent = row["parent"]
        field = row["parentfield"].replace("custom_", "")
        value = row["design_attributes"]
        attr_map.setdefault(parent, {})[field] = value

    for row in db_data:
        attrs = attr_map.get(row.item_code, {})
        for key, value in attrs.items():
            row[key] = value

        row["custom_collection"] = row.get("custom_collection") or None
        row["custom_language"] = row.get("custom_language") or None
        row["custom_zodiac"] = row.get("custom_zodiac") or None
        row["custom_animalbirds"] = row.get("custom_animalbirds") or None
        row["custom_alphabetnumber"] = row.get("custom_alphabetnumber") or None
        row["religious"] = row.get("religious") or None

    return db_data


# @frappe.whitelist(allow_guest=True)
# def get_set_by_itemcode2(itemCode=None, customer=None):
#     itemCode = frappe.form_dict.get("itemCode") or itemCode
#     customer = frappe.form_dict.get("customer") or customer

#     if not itemCode:
#         return {"error": "Item Code Required"}

#     # Check karo ki item "Is Set Item" hai ya nahi
#     is_set_item = frappe.db.get_value("Item", itemCode, "custom_is_set_item")

#     if not is_set_item:
#         return {"error": "This item is not a Set Item", "is_set_item": False}

#     # Set Item Table se linked item codes nikalo
#     set_items = frappe.db.sql("""
#         SELECT item_code
#         FROM `tabSet Item Table`
#         WHERE parent = %(itemCode)s
#     """, {"itemCode": itemCode}, as_dict=True)

#     if not set_items:
#         return {"is_set_item": True, "items": []}

#     linked_item_codes = [row.item_code for row in set_items]

#     # Wishlist logic
#     if customer:
#         wishlist_case = "MAX(CASE WHEN tci.wishlist = 1 AND tcm.customer IS NOT NULL THEN 1 ELSE 0 END) AS wishlist"
#         customer_join = "AND tcm.customer = %(customer)s"
#     else:
#         wishlist_case = "0 AS wishlist"
#         customer_join = ""

#     # IN clause ke liye placeholders
#     placeholders = ", ".join([f"%(item_{i})s" for i in range(len(linked_item_codes))])
#     item_params = {f"item_{i}": code for i, code in enumerate(linked_item_codes)}
#     item_params["customer"] = customer

#     db_data = frappe.db.sql(f"""
#         SELECT
#             item.name,
#             bom.name,
#             tci.trending,
#             {wishlist_case},
#             item.creation,
#             item.item_code,
#             item.item_category,
#             item.image,
#             item.sketch_image,
#             item.front_view AS cad_image,

#             CASE
#                 WHEN item.front_view = item.image THEN 'CAD Image'
#                 ELSE 'FG Image'
#             END AS image_remark,

#             item.item_subcategory,
#             item.stylebio,
#             bom.tag_no,
#             bom.diamond_quality,
#             item.setting_type,

#             GROUP_CONCAT(DISTINCT CASE WHEN td.design_attributes = 'Age Group' THEN td.design_attribute_value_1 END) AS age_group,
#             GROUP_CONCAT(DISTINCT CASE WHEN td.design_attributes = 'Gender' THEN td.design_attribute_value_1 END) AS gender,
#             GROUP_CONCAT(DISTINCT CASE WHEN td.design_attributes = 'Occasion' THEN td.design_attribute_value_1 END) AS occasion,
#             GROUP_CONCAT(DISTINCT CASE WHEN td.design_attributes = 'Shapes' THEN td.design_attribute_value_1 END) AS shapes,

#             FORMAT(bom.gross_weight,3) AS gross_metal_weight,
#             FORMAT(bom.metal_and_finding_weight,3) AS net_metal_finding_weight,
#             FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
#             FORMAT(bom.other_weight,3) AS other_weight,
#             FORMAT(bom.finding_weight_,3) AS finding_weight_,

#             bom.metal_colour,
#             bom.metal_touch,
#             bom.metal_purity,
#             bom.metal_type,
#             FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,

#             bom.total_diamond_pcs,
#             bom.total_gemstone_pcs,
#             FORMAT(bom.gemstone_weight,3) AS gemstone_weight,

#             FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
#             FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
#             FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,

#             bom.navratna,
#             bom.lock_type,
#             bom.feature,
#             bom.enamal,
#             bom.rhodium,
#             bom.sizer_type,

#             bom.height,
#             bom.length,
#             bom.width,
#             bom.breadth,
#             bom.product_size,

#             bom.design_style,
#             bom.nakshi_from,
#             bom.vanki_type,
#             bom.total_length,
#             bom.detachable,
#             bom.back_side_size,
#             bom.changeable,

#             item.variant_of,
#             bom.finding_pcs,
#             bom.total_other_pcs,
#             bom.total_other_weight,

#             item.item_code AS variant_name,

#             GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
#             GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,

#             GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
#             GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
#             GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
#             GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_detail_touch,

#             GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
#             GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,

#             GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
#             GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
#             GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
#             GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
#             GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,

#             GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
#             GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
#             GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size

#         FROM `tabItem` AS item

#         LEFT JOIN `tabCataloge Item Details` AS tci ON tci.item_code = item.name
#         LEFT JOIN `tabCataloge Master` AS tcm ON tcm.name = tci.parent {customer_join}

#         # INNER JOIN `tabBOM` bom
#             # ON item.item_code = bom.item
#             # AND bom.bom_type = 'Finish Goods'

#         LEFT JOIN `tabDesign Attributes` AS td ON item.item_code = td.parent
#         LEFT JOIN `tabBOM Metal Detail` AS mt ON bom.name = mt.parent
#         LEFT JOIN `tabBOM Gemstone Detail` AS gd ON bom.name = gd.parent
#         LEFT JOIN `tabBOM Diamond Detail` AS dd ON bom.name = dd.parent
#         LEFT JOIN `tabBOM Finding Detail` AS fd ON bom.name = fd.parent
#         LEFT JOIN `tabItem Default` AS idf ON item.item_name = idf.parent

#         WHERE
#             item.item_code IN ({placeholders})
#             AND idf.company = 'Gurukrupa Export Private Limited'

#         GROUP BY item.item_code
#         ORDER BY item.creation ASC
#     """, item_params, as_dict=True)

#     # Multiselect Merge
#     item_codes = [row.item_code for row in db_data]

#     if item_codes:
#         db_res = frappe.db.sql("""
#             SELECT parent, parentfield,
#             GROUP_CONCAT(design_attribute SEPARATOR ', ') AS design_attributes
#             FROM `tabDesign Attribute - Multiselect`
#             WHERE parent IN %(data)s
#             GROUP BY parent, parentfield
#         """, {"data": tuple(item_codes)}, as_dict=True)
#     else:
#         db_res = []

#     attr_map = {}
#     for row in db_res:
#         parent = row["parent"]
#         field = row["parentfield"].replace("custom_", "")
#         value = row["design_attributes"]
#         attr_map.setdefault(parent, {})[field] = value

#     for row in db_data:
#         attrs = attr_map.get(row.item_code, {})
#         for key, value in attrs.items():
#             row[key] = value

#         row["custom_collection"] = row.get("custom_collection") or None
#         row["custom_language"] = row.get("custom_language") or None
#         row["custom_zodiac"] = row.get("custom_zodiac") or None
#         row["custom_animalbirds"] = row.get("custom_animalbirds") or None
#         row["custom_alphabetnumber"] = row.get("custom_alphabetnumber") or None
#         row["religious"] = row.get("religious") or None

#     return db_data


@frappe.whitelist(allow_guest=True)
def get_set_by_itemcode(itemCode=None, customer=None):
    itemCode = frappe.form_dict.get("itemCode") or itemCode
    customer = frappe.form_dict.get("customer") or customer

    if not itemCode:
        return {"error": "Item Code Required"}

    is_set_item = frappe.db.get_value("Item", itemCode, "custom_is_set_item")

    if not is_set_item:
        return {"error": "This item is not a Set Item", "is_set_item": False}

    set_items = frappe.db.sql("""
        SELECT item_code
        FROM `tabSet Item Table`
        WHERE parent = %(itemCode)s
    """, {"itemCode": itemCode}, as_dict=True)

    if not set_items:
        return []

    linked_item_codes = [row.item_code for row in set_items]

    if customer:
        placeholders_check = ", ".join([f"%(chk_{i})s" for i in range(len(linked_item_codes))])
        check_params = {f"chk_{i}": code for i, code in enumerate(linked_item_codes)}
        check_params["customer"] = customer

        catalogue_items = frappe.db.sql(f"""
            SELECT DISTINCT tci.item_code
            FROM `tabCataloge Item Details` AS tci
            INNER JOIN `tabCataloge Master` AS tcm 
                ON tcm.name = tci.parent
                AND tcm.customer = %(customer)s
            WHERE tci.item_code IN ({placeholders_check})
        """, check_params, as_dict=True)

        allowed_codes = [row.item_code for row in catalogue_items]

        if not allowed_codes:
            return []

        linked_item_codes = allowed_codes

        wishlist_case = """MAX(CASE WHEN tci.wishlist = 1 
                          AND tcm.customer = %(customer)s 
                          THEN 1 ELSE 0 END) AS wishlist"""
        customer_join = "AND tcm.customer = %(customer)s"

    else:
        wishlist_case = "0 AS wishlist"
        customer_join = ""

    placeholders = ", ".join([f"%(item_{i})s" for i in range(len(linked_item_codes))])
    item_params = {f"item_{i}": code for i, code in enumerate(linked_item_codes)}
    item_params["customer"] = customer

    db_data = frappe.db.sql(f"""
        SELECT
            item.name,
            tci.trending,
            {wishlist_case},
            item.creation,
            item.item_code,
            item.item_category,
            item.image,
            item.sketch_image,
            item.front_view AS cad_image,

            CASE
                WHEN item.front_view = item.image THEN 'CAD Image'
                ELSE 'FG Image'
            END AS image_remark,

            item.item_subcategory,
            item.stylebio,
            item.setting_type,
            item.variant_of,
            item.item_code AS variant_name,

            GROUP_CONCAT(DISTINCT CASE WHEN td.design_attributes = 'Age Group' THEN td.design_attribute_value_1 END) AS age_group,
            GROUP_CONCAT(DISTINCT CASE WHEN td.design_attributes = 'Gender' THEN td.design_attribute_value_1 END) AS gender,
            GROUP_CONCAT(DISTINCT CASE WHEN td.design_attributes = 'Occasion' THEN td.design_attribute_value_1 END) AS occasion,
            GROUP_CONCAT(DISTINCT CASE WHEN td.design_attributes = 'Shapes' THEN td.design_attribute_value_1 END) AS shapes,

            bom.tag_no,
            bom.diamond_quality,

            FORMAT(bom.gross_weight,3) AS gross_metal_weight,
            FORMAT(bom.metal_and_finding_weight,3) AS net_metal_finding_weight,
            FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
            FORMAT(bom.other_weight,3) AS other_weight,
            FORMAT(bom.finding_weight_,3) AS finding_weight_,

            bom.metal_colour,
            bom.metal_touch,
            bom.metal_purity,
            bom.metal_type,
            FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,

            bom.total_diamond_pcs,
            bom.total_gemstone_pcs,
            FORMAT(bom.gemstone_weight,3) AS gemstone_weight,

            FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
            FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
            FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,

            bom.navratna,
            bom.lock_type,
            bom.feature,
            bom.enamal,
            bom.rhodium,
            bom.sizer_type,

            bom.height,
            bom.length,
            bom.width,
            bom.breadth,
            bom.product_size,

            bom.design_style,
            bom.nakshi_from,
            bom.vanki_type,
            bom.total_length,
            bom.detachable,
            bom.back_side_size,
            bom.changeable,

            bom.finding_pcs,
            bom.total_other_pcs,
            bom.total_other_weight,

            GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
            GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,

            GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
            GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
            GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
            GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_detail_touch,

            GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
            GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,

            GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
            GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
            GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
            GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
            GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,

            GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
            GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
            GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size

        FROM `tabItem` AS item

        LEFT JOIN `tabCataloge Item Details` AS tci ON tci.item_code = item.name
        LEFT JOIN `tabCataloge Master` AS tcm ON tcm.name = tci.parent {customer_join}

        LEFT JOIN `tabBOM` bom ON item.item_code = bom.item

        LEFT JOIN `tabDesign Attributes` AS td ON item.item_code = td.parent
        LEFT JOIN `tabBOM Metal Detail` AS mt ON bom.name = mt.parent
        LEFT JOIN `tabBOM Gemstone Detail` AS gd ON bom.name = gd.parent
        LEFT JOIN `tabBOM Diamond Detail` AS dd ON bom.name = dd.parent
        LEFT JOIN `tabBOM Finding Detail` AS fd ON bom.name = fd.parent
        LEFT JOIN `tabItem Default` AS idf ON item.item_name = idf.parent

        WHERE
            item.item_code IN ({placeholders})
            AND (idf.company = 'Gurukrupa Export Private Limited' OR idf.company IS NULL)

        GROUP BY item.item_code
        ORDER BY item.creation ASC
    """, item_params, as_dict=True)

    item_codes = [row.item_code for row in db_data]

    if item_codes:
        db_res = frappe.db.sql("""
            SELECT parent, parentfield,
            GROUP_CONCAT(design_attribute SEPARATOR ', ') AS design_attributes
            FROM `tabDesign Attribute - Multiselect`
            WHERE parent IN %(data)s
            GROUP BY parent, parentfield
        """, {"data": tuple(item_codes)}, as_dict=True)
    else:
        db_res = []

    attr_map = {}
    for row in db_res:
        parent = row["parent"]
        field = row["parentfield"].replace("custom_", "")
        value = row["design_attributes"]
        attr_map.setdefault(parent, {})[field] = value

    for row in db_data:
        attrs = attr_map.get(row.item_code, {})
        for key, value in attrs.items():
            row[key] = value

        row["custom_collection"] = row.get("custom_collection") or None
        row["custom_language"] = row.get("custom_language") or None
        row["custom_zodiac"] = row.get("custom_zodiac") or None
        row["custom_animalbirds"] = row.get("custom_animalbirds") or None
        row["custom_alphabetnumber"] = row.get("custom_alphabetnumber") or None
        row["religious"] = row.get("religious") or None

    return db_data




@frappe.whitelist(allow_guest=True)
def global_search(query=None, customer=None, user=None):
    if not query or len(query) < 2:
        return []

    like_query = f"%{query}%"
    values = {"like_query": like_query}

    # ----------------------------------------------------------------
    # CUSTOMER
    # ----------------------------------------------------------------
    if customer:
        values["customer"] = customer

        db_data = frappe.db.sql("""
            SELECT
                item.item_code,
                item.item_category,
                item.item_subcategory,
                item.image,
                bom.metal_touch,
                bom.metal_colour,
                FORMAT(bom.gross_weight, 3) AS gross_metal_weight,
                FORMAT(bom.total_diamond_weight_in_gms, 3) AS total_diamond_weight_in_gms,
                bom.diamond_quality
            FROM `tabItem` AS item
            INNER JOIN `tabCataloge Item Details` AS tci
                ON tci.item_code = item.name
            INNER JOIN `tabCataloge Master` AS tcm
                ON tcm.name = tci.parent
                AND tcm.customer = %(customer)s
            LEFT JOIN `tabBOM` AS bom
                ON item.item_code = bom.item
                AND bom.bom_type = 'Finish Goods'
                AND bom.is_active = 1
                AND bom.is_default = 1
            LEFT JOIN `tabItem Default` AS idf
                ON item.item_name = idf.parent
            WHERE
                idf.company = 'Gurukrupa Export Private Limited'
                AND bom.name IS NOT NULL
                AND (
                    item.item_code LIKE %(like_query)s
                    OR item.item_category LIKE %(like_query)s
                    OR item.item_subcategory LIKE %(like_query)s
                )
            ORDER BY item.item_subcategory, item.item_code
        """, values, as_dict=True)

    # ----------------------------------------------------------------
    # USER
    # ----------------------------------------------------------------
    elif user:
        db_data = frappe.db.sql("""
            SELECT
                # item.item_code,
                item.item_category,
                item.item_subcategory,
                item.image,
                bom.metal_touch,
                bom.metal_colour,
                FORMAT(bom.gross_weight, 3) AS gross_metal_weight,
                FORMAT(bom.total_diamond_weight_in_gms, 3) AS total_diamond_weight_in_gms,
                bom.diamond_quality
            FROM `tabItem` AS item
            INNER JOIN `tabBOM` AS bom
                ON item.item_code = bom.item
                AND bom.bom_type = 'Finish Goods'
                AND bom.is_active = 1
                AND bom.is_default = 1
            INNER JOIN `tabItem Default` AS idf
                ON item.item_name = idf.parent
                AND idf.company = 'Gurukrupa Export Private Limited'
            WHERE
                item.item_group != 'Design DNU'
                AND (
                    item.item_code LIKE %(like_query)s
                    OR item.item_category LIKE %(like_query)s
                    OR item.item_subcategory LIKE %(like_query)s
                )
            ORDER BY item.item_subcategory, item.item_code
        """, values, as_dict=True)

    else:
        return []

    # ----------------------------------------------------------------
    # Smart filter — NO LIMIT in SQL, Python mein handle karo
    # ----------------------------------------------------------------
    q_lower = query.lower()

    # Item code search detect karo
    is_item_code_search = any(
        row.get("item_code", "").lower().startswith(q_lower)
        for row in db_data
    )

    if is_item_code_search:
        # Item code search — exact matching items, max 8
        matched = [
            row for row in db_data
            if row.get("item_code", "").lower().startswith(q_lower)
        ]
        return matched[:8]
    else:
        # Category/Subcategory search — GUARANTEED 1 per subcategory, no skip
        seen = set()
        final = []
        for row in db_data:
            sub = row.get("item_subcategory") or row.get("item_category") or ""
            if sub not in seen:
                final.append(row)
                seen.add(sub)
        return final



# @frappe.whitelist(allow_guest=True)
# def global_search(query=None, customer=None, user=None):

#     if not query or len(query.strip()) < 2:
#         return []

#     q = query.strip().lower()

#     values = {
#         "like_query": f"%{q}%",
#         "start_query": f"{q}%"
#     }

#     # ==================================================
#     # CUSTOMER SEARCH
#     # ==================================================
#     if customer:

#         values["customer"] = customer

#         db_data = frappe.db.sql("""
#             SELECT
#                 # item.item_code,
#                 item.item_category,
#                 item.item_subcategory,
#                 item.image,

#                 bom.metal_touch,
#                 bom.metal_colour,

#                 FORMAT(bom.gross_weight,3) AS gross_metal_weight,
#                 FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
#                 bom.diamond_quality,

#                 CASE
#                     WHEN LOWER(item.item_code) LIKE %(start_query)s THEN 100
#                     WHEN LOWER(item.item_code) LIKE %(like_query)s THEN 80
#                     WHEN LOWER(item.item_subcategory) LIKE %(like_query)s THEN 60
#                     WHEN LOWER(item.item_category) LIKE %(like_query)s THEN 40
#                     ELSE 0
#                 END AS score

#             FROM `tabItem` item

#             INNER JOIN `tabCataloge Item Details` tci
#                 ON tci.item_code = item.name

#             INNER JOIN `tabCataloge Master` tcm
#                 ON tcm.name = tci.parent
#                 AND tcm.customer = %(customer)s

#             LEFT JOIN `tabBOM` bom
#                 ON item.item_code = bom.item
#                 AND bom.bom_type = 'Finish Goods'
#                 AND bom.is_active = 1
#                 AND bom.is_default = 1

#             LEFT JOIN `tabItem Default` idf
#                 ON item.item_name = idf.parent

#             WHERE
#                 idf.company = 'Gurukrupa Export Private Limited'
#                 AND bom.name IS NOT NULL
#                 AND (
#                     LOWER(item.item_code) LIKE %(like_query)s
#                     OR LOWER(item.item_category) LIKE %(like_query)s
#                     OR LOWER(item.item_subcategory) LIKE %(like_query)s
#                 )

#             ORDER BY score DESC,
#                      item.item_subcategory,
#                      item.item_code

#             LIMIT 200
#         """, values, as_dict=True)

#     # ==================================================
#     # INTERNAL USER SEARCH
#     # ==================================================
#     elif user:

#         db_data = frappe.db.sql("""
#             SELECT

#                 # item.item_code,
#                 item.item_category,
#                 item.item_subcategory,
#                 item.image,

#                 bom.metal_touch,
#                 bom.metal_colour,

#                 FORMAT(bom.gross_weight,3) AS gross_metal_weight,
#                 FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
#                 bom.diamond_quality,

#                 CASE
#                     WHEN LOWER(item.item_code) LIKE %(start_query)s THEN 100
#                     WHEN LOWER(item.item_code) LIKE %(like_query)s THEN 80
#                     WHEN LOWER(item.item_subcategory) LIKE %(like_query)s THEN 60
#                     WHEN LOWER(item.item_category) LIKE %(like_query)s THEN 40
#                     ELSE 0
#                 END AS score

#             FROM `tabItem` item

#             INNER JOIN `tabBOM` bom
#                 ON item.item_code = bom.item
#                 AND bom.bom_type = 'Finish Goods'
#                 AND bom.is_active = 1
#                 AND bom.is_default = 1

#             INNER JOIN `tabItem Default` idf
#                 ON item.item_name = idf.parent
#                 AND idf.company = 'Gurukrupa Export Private Limited'

#             WHERE
#                 item.item_group != 'Design DNU'
#                 AND (
#                     LOWER(item.item_code) LIKE %(like_query)s
#                     OR LOWER(item.item_category) LIKE %(like_query)s
#                     OR LOWER(item.item_subcategory) LIKE %(like_query)s
#                 )

#             ORDER BY score DESC,
#                      item.item_subcategory,
#                      item.item_code

#             LIMIT 200
#         """, values, as_dict=True)

#     else:
#         return []

#     # ==================================================
#     # ITEM CODE SEARCH
#     # ==================================================

#     is_item_code_search = any(
#         (row.get("item_code") or "").lower().startswith(q)
#         for row in db_data
#     )

#     if is_item_code_search:

#         matched = [
#             row for row in db_data
#             if (row.get("item_code") or "").lower().startswith(q)
#         ]

#         return matched[:8]

#     # ==================================================
#     # CATEGORY / SUBCATEGORY SEARCH
#     # ==================================================

#     seen = set()
#     final = []

#     for row in db_data:

#         key = (
#             row.get("item_subcategory")
#             or row.get("item_category")
#             or ""
#         )

#         if key not in seen:
#             final.append(row)
#             seen.add(key)

#         if len(final) >= 8:
#             break

#     return final

# @frappe.whitelist(allow_guest=True)
# def get_set_by_itemcode(item_code, customer=None, user=None):

#     if not item_code:
#         return []

#     # =========================
#     # CUSTOMER CATALOGUE
#     # =========================
#     if customer:

#         items = frappe.db.sql("""
#             SELECT DISTINCT
#                 item.item_code,
#                 item.image

#             FROM `tabSet Item Table` sit

#             INNER JOIN `tabItem` item
#                 ON item.name = sit.item_code

#             INNER JOIN `tabCataloge Item Details` tci
#                 ON tci.item_code = item.name

#             INNER JOIN `tabCataloge Master` tcm
#                 ON tcm.name = tci.parent

#             WHERE sit.parent = %(item_code)s

#             AND tcm.customer = %(customer)s
#         """, {
#             "item_code": item_code,
#             "customer": customer
#         }, as_dict=True)

#         return items

#     # =========================
#     # INTERNAL USER CATALOGUE
#     # =========================
#     elif user:

#         items = frappe.db.sql("""
#             SELECT DISTINCT
#                 item.item_code,
#                 item.image

#             FROM `tabSet Item Table` sit

#             INNER JOIN `tabItem` item
#                 ON item.name = sit.item_code

#             INNER JOIN `tabUser Item Details` uid
#                 ON uid.item_code = item.name

#             INNER JOIN `tabInternal Catalog Master` icm
#                 ON icm.name = uid.parent

#             WHERE sit.parent = %(item_code)s

#             AND icm.user = %(user)s
#         """, {
#             "item_code": item_code,
#             "user": user
#         }, as_dict=True)

#         return items

#     # =========================
#     # NO FILTER
#     # =========================
#     else:

#         items = frappe.db.sql("""
#             SELECT DISTINCT
#                 item.item_code,
#                 item.image

#             FROM `tabSet Item Table` sit

#             INNER JOIN `tabItem` item
#                 ON item.name = sit.item_code

#             WHERE sit.parent = %(item_code)s
#         """, {
#             "item_code": item_code
#         }, as_dict=True)

#         return items

# @frappe.whitelist(allow_guest=True)
# def customer_wise_item(selectedSubcategory, customer = None, user = None, metalType = None):
#     selectedSubcategory = frappe.form_dict.get("selectedSubcategory")
#     itemCode = frappe.form_dict.get("itemCode")
#     itemCategory = frappe.form_dict.get("itemCategory")
#     metalType = frappe.form_dict.get("metalType")

#     where_clause = """
#     idf.company = 'Gurukrupa Export Private Limited'
#     AND bom.bom_type = 'Finish Goods'
#     AND bom.name IS NOT NULL
#     AND bom.is_active = 1
#     AND bom.is_default = 1
#     """

#     if selectedSubcategory:
#         where_clause = where_clause + f" AND item.item_subcategory = '{selectedSubcategory}' "
#     if metalType:
#         where_clause = where_clause + f" AND bom.metal_type = '{metalType}' "
#     if customer:
#         where_clause = where_clause + f" AND tcm.customer = '{customer}' "
#     if user:
#         where_clause = where_clause + f" AND icm.user = '{user}' "
#     if itemCode:
#         where_clause = where_clause + f" AND item.item_code = '{itemCode}' "
#     if itemCategory:
#         where_clause = where_clause + f" AND item.item_category = '{itemCategory}' "

#     db_data = frappe.db.sql(
#         f""" SELECT
#                 item.name,
#                 bom.name,
#                 idf.company,
#                 tci.trending,
#                 tci.folder,
#                 tci.wishlist,
#                 uid.folder as internal_catalog_folder,
#                 uid.wishlist as internal_catalog_wishlist,
#                 item.creation,
#                 item.item_code,
#                 item.item_category,
#                 item.stylebio,
#                 item.image,
#                 item.sketch_image,
#                 item.front_view as cad_image,
#                 CASE
#                     WHEN item.front_view = item.image THEN 'CAD Image'
#                     ELSE 'FG Image'
#                 END AS image_remark,
                
#                 CASE 
#                     WHEN vc.variant_count > 1 THEN 1 
#                     ELSE 0 
#                 END AS rn,
                
#                 CASE 
#                    WHEN set_check.is_set_item = 1 THEN 1 
#                    ELSE 0 
#                 END AS is_set_item,
                
#                 CASE 
#                     WHEN similar_check.is_similar_item = 1 THEN 1 
#                     ELSE 0 
#                 END AS is_similar_item,
            
#                 item.item_subcategory,
#                 bom.tag_no,
#                 bom.diamond_quality,
#                 item.setting_type,
#                 FORMAT(bom.gross_weight,3) AS gross_metal_weight,
#                 FORMAT(bom.metal_and_finding_weight, 3) AS net_metal_finding_weight,
#                 FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
#                 FORMAT(bom.other_weight,3) AS other_weight,
#                 FORMAT(bom.finding_weight_,3) AS finding_weight_,
#                 bom.metal_touch as bom_touch,
#                 bom.metal_purity,
#                 FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,
#                 bom.total_diamond_pcs,
#                 bom.total_gemstone_pcs,
#                 FORMAT(bom.gemstone_weight,3) AS gemstone_weight,
#                 FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
#                 FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
#                 FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,
#                 bom.navratna,
#                 bom.height,
#                 bom.length,
#                 bom.width,
#                 bom.breadth,
#                 bom.product_size,
#                 bom.sizer_type,
#                 bom.design_style,
#                 bom.nakshi_from,
#                 bom.vanki_type,
#                 bom.total_length,
#                 bom.detachable,
#                 bom.back_side_size,
#                 bom.changeable,
#                 item.variant_of,
#                 bom.finding_pcs,
#                 bom.total_other_pcs,
#                 bom.total_other_weight,
#                 GROUP_CONCAT(DISTINCT item.name) as variant_name,
#                 GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
#                 GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,
#                 GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
#                 GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
#                 GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
#                 GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,
#                 GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
#                 GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,
#                 GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
#                 GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
#                 GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
#                 GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
#                 GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,
#                 GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
#                 GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
#                 GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size
#             FROM 
#                 `tabItem` AS item
#             LEFT JOIN 
#                 `tabCataloge Item Details` AS tci 
#             ON 
#                 tci.item_code = item.name
                
#             LEFT JOIN (
#                 SELECT 
#                     IFNULL(i.variant_of, i.item_code) AS group_key,
#                     COUNT(DISTINCT i.item_code) AS variant_count
#                 FROM `tabItem` AS i
#                 INNER JOIN `tabBOM` AS b 
#                     ON i.item_code = b.item
#                     AND b.bom_type = 'Finish Goods'
#                     AND b.is_active = 1
#                     AND b.is_default = 1
#                 INNER JOIN `tabCataloge Item Details` AS tci2
#                     ON tci2.item_code = i.item_code
#                 INNER JOIN `tabCataloge Master` AS tcm2
#                     ON tcm2.name = tci2.parent
#                 GROUP BY IFNULL(i.variant_of, i.item_code)
#             ) vc 
#             ON vc.group_key = IFNULL(item.variant_of, item.item_code)
            
#             # LEFT JOIN (
#             #     SELECT 
#             #         sit.parent AS item_code,
#             #         CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END AS is_set_item
#             #     FROM `tabSet Item Table` sit
#             #     GROUP BY sit.parent
#             # ) AS set_check ON set_check.item_code = item.item_code
            
#             LEFT JOIN (
#                 SELECT 
#                     sit.parent AS item_code,
#                     CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END AS is_set_item
#                 FROM `tabSet Item Table` sit
#                 INNER JOIN `tabBOM` AS b
#                     ON sit.item_code = b.item
#                     AND b.bom_type = 'Finish Goods'
#                     AND b.is_active = 1
#                     AND b.is_default = 1
#                 WHERE sit.parenttype = 'Item'
#                 GROUP BY sit.parent
#             ) AS set_check ON set_check.item_code = item.item_code
            
#             LEFT JOIN (
#             SELECT 
#                 sit.parent AS item_code,
#                 CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END AS is_similar_item
#                 FROM `tabSimilar Item Table` sit
#                 WHERE sit.parenttype = 'Item'
#                 GROUP BY sit.parent
#             ) AS similar_check ON similar_check.item_code = item.item_code
            
#             # LEFT JOIN (
#             #     SELECT 
#             #         sit.parent AS item_code,
#             #         CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END AS is_similar_item
#             #     FROM `tabSimilar Item Table` sit
#             #     INNER JOIN `tabBOM` AS b 
#             #         ON sit.item_code = b.item
#             #         AND b.bom_type = 'Finish Goods'
#             #         AND b.is_active = 1
#             #         AND b.is_default = 1
#             #     WHERE sit.parenttype = 'Item'
#             #     GROUP BY sit.parent
#             # ) AS similar_check ON similar_check.item_code = item.item_code
        
#             LEFT JOIN 
#                 `tabCataloge Master` AS tcm 
#             ON 
#                 tcm.name = tci.parent
                
#             LEFT JOIN 
#                 `tabUser Item Details` AS uid 
#             ON 
#                 uid.item_code = item.name
#             LEFT JOIN 
#                 `tabInternal Catalog Master` AS icm 
#             ON 
#                 icm.name = uid.parent
#             LEFT JOIN
#                 `tabBOM` AS bom
#             ON
#                 item.item_code = bom.item
#             LEFT JOIN
#                 `tabDesign Attributes`  AS td
#             ON
#                 item.item_code = td.parent
#             LEFT JOIN
#                 `tabBOM Metal Detail` AS mt
#             ON
#                 bom.name = mt.parent
#             LEFT JOIN
#                 `tabBOM Gemstone Detail` AS gd
#             ON
#                 bom.name = gd.parent
#             LEFT JOIN
#                 `tabBOM Diamond Detail` AS dd
#             ON
#                 bom.name = dd.parent
#             LEFT JOIN
#                 `tabBOM Finding Detail` AS fd
#             ON
#                 bom.name = fd.parent
#             LEFT JOIN
#                 `tabBOM Other Detail` AS od
#             ON
#                 bom.name = od.parent
#             LEFT JOIN
#                 `tabItem Default` AS idf
#             ON
#                 item.item_name = idf.parent
#             WHERE
#                 {where_clause}
#             GROUP BY
#                 item.item_code, item.variant_of
#             ORDER BY
#                 item.name DESC 
#     """,
#     as_dict=True)

#     d = {}
#     int_c_f = {}

#     for row in db_data:
#         if row.folder:
#             folder = row.folder.split(",")
#             for fd in folder:
#                 if fd not in d:
#                     d[fd] = []
#                 d[fd].append(row)
    
#     for row in db_data:
#         if row.internal_catalog_folder:
#             internal_catalog_folder = row.internal_catalog_folder.split(",")
#             for fd in internal_catalog_folder:
#                 if fd not in int_c_f:
#                     int_c_f[fd] = []
#                 int_c_f[fd].append(row)

#     return {
#         "db_data" : db_data,
#         "folder": d,
#         "internal_catalog_folder" : int_c_f
#     }









# @frappe.whitelist(allow_guest=True)
# def subcategory_count1(categoryName, user_type, customer=None):
#     try:
#         if user_type == "Customer":
#             # ── Redis Cache (customer-specific) ─────────────────────────────
#             cache_key = f"subcat_count_{categoryName}_{customer}"
#             cached = frappe.cache().get_value(cache_key)
#             if cached:
#                 return cached

#             # ── STEP 1: Count query ──────────────────────────────────────────
#             count_query = """
#                 SELECT 
#                     ti.item_category,
#                     ti.item_subcategory,
#                     tb.metal_type,
#                     COUNT(DISTINCT IFNULL(ti.variant_of, ti.name)) AS item_count,
#                     COUNT(DISTINCT se.name)                         AS serial_count

#                 FROM `tabCataloge Item Details` AS tci

#                 JOIN `tabCataloge Master` AS tcm 
#                     ON tcm.name = tci.parent
#                     AND tcm.customer = %s

#                 JOIN `tabItem` AS ti 
#                     ON ti.name = tci.item_code
#                     AND ti.item_category = %s

#                 JOIN `tabAttribute Value` AS tav 
#                     ON tav.name = ti.item_subcategory
#                     AND tav.is_subcategory = 1

#                 JOIN `tabBOM` AS tb 
#                     ON tb.item = ti.name
#                     AND tb.is_active = 1
#                     AND tb.is_default = 1
#                     AND tb.bom_type = 'Finish Goods'

#                 LEFT JOIN `tabSerial No` AS se
#                     ON se.item_code = ti.name
#                     AND se.status = 'Active'

#                 WHERE 
#                     ti.item_subcategory IS NOT NULL

#                 GROUP BY 
#                     ti.item_category,
#                     ti.item_subcategory,
#                     tb.metal_type

#                 ORDER BY 
#                     ti.item_category,
#                     ti.item_subcategory,
#                     tb.metal_type
#             """
#             result = frappe.db.sql(count_query, (customer, categoryName), as_dict=True)

#             # ── STEP 2: first_image alag IN query se ────────────────────────
#             if result:
#                 subcategories = list({row.item_subcategory for row in result if row.item_subcategory})

#                 if subcategories:
#                     image_rows = frappe.db.sql("""
#                         SELECT 
#                             item2.item_subcategory,
#                             item2.image AS first_image
#                         FROM `tabItem` AS item2
#                         INNER JOIN (
#                             SELECT 
#                                 item_subcategory,
#                                 MAX(creation) AS latest_creation
#                             FROM `tabItem`
#                             WHERE 
#                                 item_subcategory IN %(subs)s
#                                 AND image IS NOT NULL
#                                 AND item_category = %(cat)s
#                                 AND (front_view IS NULL OR image != front_view)
#                             GROUP BY item_subcategory
#                         ) AS latest
#                             ON item2.item_subcategory = latest.item_subcategory
#                             AND item2.creation = latest.latest_creation
#                         WHERE 
#                             item2.item_subcategory IN %(subs)s
#                             AND item2.image IS NOT NULL
#                         GROUP BY item2.item_subcategory
#                     """, {"subs": tuple(subcategories), "cat": categoryName}, as_dict=True)

#                     image_map = {r.item_subcategory: r.first_image for r in image_rows}

#                     for row in result:
#                         row["first_image"] = image_map.get(row.item_subcategory)

#             # ── Cache save karo 5 min ke liye ───────────────────────────────
#             frappe.cache().set_value(cache_key, result, expires_in_sec=300)

#         else:
#             # ── Redis Cache check (non-customer data same hota hai) ──────────
#             cache_key = f"subcat_count_{categoryName}"
#             cached = frappe.cache().get_value(cache_key)
#             if cached:
#                 return cached

#             # ── STEP 1: Count query ──────────────────────────────────────────
#             count_query = """
#                 SELECT
#                     item.item_subcategory,
#                     COUNT(DISTINCT IFNULL(item.variant_of, item.item_code)) AS item_count,
#                     COUNT(DISTINCT se.name)                                  AS serial_count

#                 FROM `tabItem` AS item

#                 JOIN `tabAttribute Value` AS tav 
#                     ON item.item_subcategory = tav.name
#                     AND tav.is_subcategory = 1

#                 INNER JOIN `tabBOM` AS bom 
#                     ON item.item_code = bom.item
#                     AND bom.is_active = 1
#                     AND bom.bom_type = 'Finish Goods'

#                 INNER JOIN `tabItem Default` AS idf
#                     ON item.item_code = idf.parent
#                     AND idf.company = 'Gurukrupa Export Private Limited'

#                 LEFT JOIN `tabSerial No` AS se
#                     ON se.item_code = item.item_code
#                     AND se.status = 'Active'

#                 WHERE 
#                     item.item_subcategory IS NOT NULL
#                     AND item.item_category = %s

#                 GROUP BY 
#                     item.item_subcategory

#                 ORDER BY 
#                     item.item_subcategory
#             """
#             result = frappe.db.sql(count_query, (categoryName,), as_dict=True)

#             # ── STEP 2: first_image alag IN query se ────────────────────────
#             if result:
#                 subcategories = list({row.item_subcategory for row in result if row.item_subcategory})

#                 if subcategories:
#                     image_rows = frappe.db.sql("""
#                         SELECT 
#                             item2.item_subcategory,
#                             item2.image AS first_image
#                         FROM `tabItem` AS item2
#                         INNER JOIN (
#                             SELECT 
#                                 item_subcategory,
#                                 MAX(creation) AS latest_creation
#                             FROM `tabItem`
#                             WHERE 
#                                 item_subcategory IN %(subs)s
#                                 AND image IS NOT NULL
#                                 AND item_category = %(cat)s
#                                 AND (front_view IS NULL OR image != front_view)
#                             GROUP BY item_subcategory
#                         ) AS latest
#                             ON item2.item_subcategory = latest.item_subcategory
#                             AND item2.creation = latest.latest_creation
#                         WHERE 
#                             item2.item_subcategory IN %(subs)s
#                             AND item2.image IS NOT NULL
#                         GROUP BY item2.item_subcategory
#                     """, {"subs": tuple(subcategories), "cat": categoryName}, as_dict=True)

#                     image_map = {r.item_subcategory: r.first_image for r in image_rows}

#                     for row in result:
#                         row["first_image"] = image_map.get(row.item_subcategory)

#             # ── Cache save karo 5 min ke liye ───────────────────────────────
#             frappe.cache().set_value(cache_key, result, expires_in_sec=300)

#         return result

#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), "subcategory_count Error")
#         return {"error": str(e)}


# @frappe.whitelist(allow_guest=True)
# def subcategory_count1(categoryName, user_type, customer=None):
#         try:
#             if user_type == "Customer":
        
#                 # ── Redis Cache (customer-specific) ─────────────────────────────
#                 cache_key = f"subcat_count_{categoryName}_{customer}"
#                 cached = frappe.cache().get_value(cache_key)
        
#                 if cached:
#                     return cached
        
#                 # ── STEP 1: Count query ──────────────────────────────────────────
#                 count_query = """
#                     SELECT 
#                         ti.item_category,
#                         ti.item_subcategory,
        
#                         tb.name AS bom_name,
#                         tb.bom_type,
#                         tb.metal_type,
#                         tb.is_active,
#                         tb.is_default,
        
#                         COUNT(DISTINCT IFNULL(ti.variant_of, ti.name)) AS item_count,
#                         COUNT(DISTINCT se.name) AS serial_count
        
#                     FROM `tabCataloge Item Details` AS tci
        
#                     JOIN `tabCataloge Master` AS tcm 
#                         ON tcm.name = tci.parent
#                         AND tcm.customer = %s
        
#                     JOIN `tabItem` AS ti 
#                         ON ti.name = tci.item_code
#                         AND ti.item_category = %s
        
#                     JOIN `tabAttribute Value` AS tav 
#                         ON tav.name = ti.item_subcategory
#                         AND tav.is_subcategory = 1
        
#                     JOIN `tabBOM` AS tb 
#                         ON tb.item = ti.name
#                         AND tb.is_active = 1
#                         AND tb.bom_type = 'Finish Goods'
        
#                     LEFT JOIN `tabSerial No` AS se
#                         ON se.item_code = ti.name
#                         AND se.status = 'Active'
        
#                     WHERE 
#                         ti.item_subcategory IS NOT NULL
        
#                     GROUP BY 
#                         ti.item_category,
#                         ti.item_subcategory,
#                         tb.name,
#                         tb.bom_type,
#                         tb.metal_type,
#                         tb.is_active,
#                         tb.is_default
        
#                     ORDER BY 
#                         ti.item_category,
#                         ti.item_subcategory,
#                         tb.metal_type
#                 """
        
#                 result = frappe.db.sql(
#                     count_query,
#                     (customer, categoryName),
#                     as_dict=True
#                 )
        
#                 # ── DEBUG THROW ──────────────────────────────────────────────────
#                 debug_summary = []
        
#                 for row in result:
#                     debug_summary.append(
#                         f"""
#                         <b>Subcategory:</b> {row.get('item_subcategory')}
#                         <br>
        
#                         <b>BOM Name:</b> {row.get('bom_name')}
#                         <br>
        
#                         <b>BOM Type:</b> {row.get('bom_type')}
#                         <br>
        
#                         <b>Metal Type:</b> {row.get('metal_type')}
#                         <br>
        
#                         <b>Is Active:</b> {row.get('is_active')}
#                         <br>
        
#                         <b>Is Default:</b> {row.get('is_default')}
#                         <br>
        
#                         <b>Item Count:</b> {row.get('item_count')}
#                         <br>
        
#                         <b>Serial Count:</b> {row.get('serial_count')}
#                         <br>
        
#                         <hr>
#                         """
#                     )
        
#                 frappe.throw(
#                     "".join(debug_summary) or "No BOM Data Found"
#                 )
        
#                 # ── STEP 2: first_image alag IN query se ────────────────────────
#                 if result:
        
#                     subcategories = list({
#                         row.item_subcategory
#                         for row in result
#                         if row.item_subcategory
#                     })
        
#                     if subcategories:
        
#                         image_rows = frappe.db.sql("""
#                             SELECT 
#                                 item2.item_subcategory,
#                                 item2.image AS first_image
        
#                             FROM `tabItem` AS item2
        
#                             INNER JOIN (
#                                 SELECT 
#                                     item_subcategory,
#                                     MAX(creation) AS latest_creation
        
#                                 FROM `tabItem`
        
#                                 WHERE 
#                                     item_subcategory IN %(subs)s
#                                     AND image IS NOT NULL
#                                     AND item_category = %(cat)s
#                                     AND (
#                                         front_view IS NULL 
#                                         OR image != front_view
#                                     )
        
#                                 GROUP BY item_subcategory
        
#                             ) AS latest
        
#                                 ON item2.item_subcategory = latest.item_subcategory
#                                 AND item2.creation = latest.latest_creation
        
#                             WHERE 
#                                 item2.item_subcategory IN %(subs)s
#                                 AND item2.image IS NOT NULL
        
#                             GROUP BY item2.item_subcategory
        
#                         """, {
#                             "subs": tuple(subcategories),
#                             "cat": categoryName
#                         }, as_dict=True)
        
#                         image_map = {
#                             r.item_subcategory: r.first_image
#                             for r in image_rows
#                         }
        
#                         for row in result:
#                             row["first_image"] = image_map.get(
#                                 row.item_subcategory
#                             )
        
#                 # ── Cache save karo 5 min ke liye ───────────────────────────────
#                 frappe.cache().set_value(
#                     cache_key,
#                     result,
#                     expires_in_sec=300
#                 )
        
#                 return result
        
#         except Exception as e:
#             frappe.log_error(
#                 frappe.get_traceback(),
#                 "subcategory_count Error"
#             )
        
#             return {
#                 "error": str(e)
#             }

#         else:
#             # ── Redis Cache check (non-customer data same hota hai) ──────────
#             cache_key = f"subcat_count_{categoryName}"
#             cached = frappe.cache().get_value(cache_key)
#             if cached:
#                 return cached

#             # ── STEP 1: Count query ──────────────────────────────────────────
#             count_query = """
#                 SELECT
#                     item.item_subcategory,
#                     COUNT(DISTINCT IFNULL(item.variant_of, item.item_code)) AS item_count,
#                     COUNT(DISTINCT se.name)                                  AS serial_count

#                 FROM `tabItem` AS item

#                 JOIN `tabAttribute Value` AS tav 
#                     ON item.item_subcategory = tav.name
#                     AND tav.is_subcategory = 1

#                 INNER JOIN `tabBOM` AS bom 
#                     ON item.item_code = bom.item
#                     AND bom.is_active = 1
#                     AND bom.bom_type = 'Finish Goods'

#                 INNER JOIN `tabItem Default` AS idf
#                     ON item.item_code = idf.parent
#                     AND idf.company = 'Gurukrupa Export Private Limited'

#                 LEFT JOIN `tabSerial No` AS se
#                     ON se.item_code = item.item_code
#                     AND se.status = 'Active'

#                 WHERE 
#                     item.item_subcategory IS NOT NULL
#                     AND item.item_category = %s

#                 GROUP BY 
#                     item.item_subcategory

#                 ORDER BY 
#                     item.item_subcategory
#             """
#             result = frappe.db.sql(count_query, (categoryName,), as_dict=True)

#             # ── STEP 2: first_image alag IN query se ────────────────────────
#             if result:
#                 subcategories = list({row.item_subcategory for row in result if row.item_subcategory})

#                 if subcategories:
#                     image_rows = frappe.db.sql("""
#                         SELECT 
#                             item2.item_subcategory,
#                             item2.image AS first_image
#                         FROM `tabItem` AS item2
#                         INNER JOIN (
#                             SELECT 
#                                 item_subcategory,
#                                 MAX(creation) AS latest_creation
#                             FROM `tabItem`
#                             WHERE 
#                                 item_subcategory IN %(subs)s
#                                 AND image IS NOT NULL
#                                 AND item_category = %(cat)s
#                                 AND (front_view IS NULL OR image != front_view)
#                             GROUP BY item_subcategory
#                         ) AS latest
#                             ON item2.item_subcategory = latest.item_subcategory
#                             AND item2.creation = latest.latest_creation
#                         WHERE 
#                             item2.item_subcategory IN %(subs)s
#                             AND item2.image IS NOT NULL
#                         GROUP BY item2.item_subcategory
#                     """, {"subs": tuple(subcategories), "cat": categoryName}, as_dict=True)

#                     image_map = {r.item_subcategory: r.first_image for r in image_rows}

#                     for row in result:
#                         row["first_image"] = image_map.get(row.item_subcategory)

#             # ── Cache save karo 5 min ke liye ───────────────────────────────
#             frappe.cache().set_value(cache_key, result, expires_in_sec=300)

#         return result

#     # except Exception as e:
#         # frappe.log_error(frappe.get_traceback(), "subcategory_count Error")
#         # return {"error": str(e)}


# @frappe.whitelist(allow_guest=True)
# def subcategory_count1(categoryName, user_type, customer=None):
#     try:
#         if user_type == "Customer":
#             # ── Redis Cache (customer-specific) ─────────────────────────────
#             cache_key = f"subcat_count_{categoryName}_{customer}"
#             cached = frappe.cache().get_value(cache_key)
#             if cached:
#                 return cached

#             # ── STEP 1: Count query — same logic as user ─────────────────────
#             count_query = """
#                 SELECT
#                     item.item_subcategory,
#                     item.item_category,
#                     COUNT(DISTINCT IFNULL(item.variant_of, item.item_code)) AS item_count,
#                     COUNT(DISTINCT se.name)                                  AS serial_count

#                 FROM (
#                     SELECT DISTINCT tci.item_code
#                     FROM `tabCataloge Item Details` AS tci
#                     JOIN `tabCataloge Master` AS tcm
#                         ON tcm.name = tci.parent
#                         AND tcm.customer = %s
#                 ) AS unique_items

#                 JOIN `tabItem` AS item
#                     ON item.item_code = unique_items.item_code
#                     AND item.item_category = %s

#                 JOIN `tabAttribute Value` AS tav
#                     ON item.item_subcategory = tav.name
#                     AND tav.is_subcategory = 1

#                 INNER JOIN `tabBOM` AS bom
#                     ON item.item_code = bom.item
#                     AND bom.is_active = 1
#                     AND bom.bom_type = 'Finish Goods'

#                 INNER JOIN `tabItem Default` AS idf
#                     ON item.item_code = idf.parent
#                     AND idf.company = 'Gurukrupa Export Private Limited'

#                 LEFT JOIN `tabSerial No` AS se
#                     ON se.item_code = item.item_code
#                     AND se.status = 'Active'

#                 WHERE
#                     item.item_subcategory IS NOT NULL

#                 GROUP BY
#                     item.item_category,
#                     item.item_subcategory

#                 ORDER BY
#                     item.item_subcategory
#             """
#             result = frappe.db.sql(count_query, (customer, categoryName), as_dict=True)

#             # ── STEP 2: first_image — same logic as user ─────────────────────
#             if result:
#                 subcategories = list({row.item_subcategory for row in result if row.item_subcategory})

#                 if subcategories:
#                     image_rows = frappe.db.sql("""
#                         SELECT 
#                             item2.item_subcategory,
#                             item2.image AS first_image
#                         FROM `tabItem` AS item2
#                         INNER JOIN (
#                             SELECT 
#                                 item_subcategory,
#                                 MAX(creation) AS latest_creation
#                             FROM `tabItem`
#                             WHERE 
#                                 item_subcategory IN %(subs)s
#                                 AND image IS NOT NULL
#                                 AND item_category = %(cat)s
#                                 AND (front_view IS NULL OR image != front_view)
#                             GROUP BY item_subcategory
#                         ) AS latest
#                             ON item2.item_subcategory = latest.item_subcategory
#                             AND item2.creation = latest.latest_creation
#                         WHERE 
#                             item2.item_subcategory IN %(subs)s
#                             AND item2.image IS NOT NULL
#                         GROUP BY item2.item_subcategory
#                     """, {"subs": tuple(subcategories), "cat": categoryName}, as_dict=True)

#                     image_map = {r.item_subcategory: r.first_image for r in image_rows}

#                     for row in result:
#                         row["first_image"] = image_map.get(row.item_subcategory)

#             # ── Cache save karo 5 min ke liye ────────────────────────────────
#             frappe.cache().set_value(cache_key, result, expires_in_sec=300)

#         else:
#             # ── Redis Cache check ─────────────────────────────────────────────
#             cache_key = f"subcat_count_{categoryName}"
#             cached = frappe.cache().get_value(cache_key)
#             if cached:
#                 return cached

#             # ── STEP 1: Count query ───────────────────────────────────────────
#             count_query = """
#                 SELECT
#                     item.item_subcategory,
#                     COUNT(DISTINCT IFNULL(item.variant_of, item.item_code)) AS item_count,
#                     COUNT(DISTINCT se.name)                                  AS serial_count

#                 FROM `tabItem` AS item

#                 JOIN `tabAttribute Value` AS tav 
#                     ON item.item_subcategory = tav.name
#                     AND tav.is_subcategory = 1

#                 INNER JOIN `tabBOM` AS bom 
#                     ON item.item_code = bom.item
#                     AND bom.is_active = 1
#                     AND bom.bom_type = 'Finish Goods'

#                 INNER JOIN `tabItem Default` AS idf
#                     ON item.item_code = idf.parent
#                     AND idf.company = 'Gurukrupa Export Private Limited'

#                 LEFT JOIN `tabSerial No` AS se
#                     ON se.item_code = item.item_code
#                     AND se.status = 'Active'

#                 WHERE 
#                     item.item_subcategory IS NOT NULL
#                     AND item.item_category = %s

#                 GROUP BY 
#                     item.item_subcategory

#                 ORDER BY 
#                     item.item_subcategory
#             """
#             result = frappe.db.sql(count_query, (categoryName,), as_dict=True)

#             # ── STEP 2: first_image alag IN query se ─────────────────────────
#             if result:
#                 subcategories = list({row.item_subcategory for row in result if row.item_subcategory})

#                 if subcategories:
#                     image_rows = frappe.db.sql("""
#                         SELECT 
#                             item2.item_subcategory,
#                             item2.image AS first_image
#                         FROM `tabItem` AS item2
#                         INNER JOIN (
#                             SELECT 
#                                 item_subcategory,
#                                 MAX(creation) AS latest_creation
#                             FROM `tabItem`
#                             WHERE 
#                                 item_subcategory IN %(subs)s
#                                 AND image IS NOT NULL
#                                 AND item_category = %(cat)s
#                                 AND (front_view IS NULL OR image != front_view)
#                             GROUP BY item_subcategory
#                         ) AS latest
#                             ON item2.item_subcategory = latest.item_subcategory
#                             AND item2.creation = latest.latest_creation
#                         WHERE 
#                             item2.item_subcategory IN %(subs)s
#                             AND item2.image IS NOT NULL
#                         GROUP BY item2.item_subcategory
#                     """, {"subs": tuple(subcategories), "cat": categoryName}, as_dict=True)

#                     image_map = {r.item_subcategory: r.first_image for r in image_rows}

#                     for row in result:
#                         row["first_image"] = image_map.get(row.item_subcategory)

#             # ── Cache save karo 5 min ke liye ────────────────────────────────
#             frappe.cache().set_value(cache_key, result, expires_in_sec=300)

#         return result

#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), "subcategory_count Error")
#         return {"error": str(e)}


# @frappe.whitelist(allow_guest=True)
# def subcategory_count1(categoryName, user_type, customer=None):
#     try:
#         if user_type == "Customer":
#             # ── Redis Cache (customer-specific) ─────────────────────────────
#             cache_key = f"subcat_count_{categoryName}_{customer}"
#             cached = frappe.cache().get_value(cache_key)
#             if cached:
#                 return cached

#             # ── STEP 1: Count query ──────────────────────────────────────────
#             count_query = """
#                 SELECT 
#                     ti.item_category,
#                     ti.item_subcategory,
#                     tb.metal_type,
#                     COUNT(DISTINCT IFNULL(ti.variant_of, ti.name)) AS item_count,
#                     COUNT(DISTINCT se.name)                         AS serial_count

#                 FROM `tabCataloge Item Details` AS tci

#                 JOIN `tabCataloge Master` AS tcm 
#                     ON tcm.name = tci.parent
#                     AND tcm.customer = %s

#                 JOIN `tabItem` AS ti 
#                     ON ti.name = tci.item_code
#                     AND ti.item_category = %s

#                 JOIN `tabAttribute Value` AS tav 
#                     ON tav.name = ti.item_subcategory
#                     AND tav.is_subcategory = 1

#                 JOIN `tabBOM` AS tb 
#                     ON tb.item = ti.name
#                     AND tb.is_active = 1
#                     AND tb.is_default = 1
#                     AND tb.bom_type = 'Finish Goods'

#                 LEFT JOIN `tabSerial No` AS se
#                     ON se.item_code = ti.name
#                     AND se.status = 'Active'

#                 WHERE 
#                     ti.item_subcategory IS NOT NULL

#                 GROUP BY 
#                     ti.item_category,
#                     ti.item_subcategory,
#                     tb.metal_type

#                 ORDER BY 
#                     ti.item_category,
#                     ti.item_subcategory,
#                     tb.metal_type
#             """
#             result = frappe.db.sql(count_query, (customer, categoryName), as_dict=True)

#             # ── STEP 2: first_image alag IN query se ────────────────────────
#             if result:
#                 subcategories = list({row.item_subcategory for row in result if row.item_subcategory})

#                 if subcategories:
#                     image_rows = frappe.db.sql("""
#                         SELECT 
#                             item2.item_subcategory,
#                             item2.image AS first_image
#                         FROM `tabItem` AS item2
#                         INNER JOIN (
#                             SELECT 
#                                 item_subcategory,
#                                 MAX(creation) AS latest_creation
#                             FROM `tabItem`
#                             WHERE 
#                                 item_subcategory IN %(subs)s
#                                 AND image IS NOT NULL
#                                 AND item_category = %(cat)s
#                                 AND (front_view IS NULL OR image != front_view)
#                             GROUP BY item_subcategory
#                         ) AS latest
#                             ON item2.item_subcategory = latest.item_subcategory
#                             AND item2.creation = latest.latest_creation
#                         WHERE 
#                             item2.item_subcategory IN %(subs)s
#                             AND item2.image IS NOT NULL
#                         GROUP BY item2.item_subcategory
#                     """, {"subs": tuple(subcategories), "cat": categoryName}, as_dict=True)

#                     image_map = {r.item_subcategory: r.first_image for r in image_rows}

#                     for row in result:
#                         row["first_image"] = image_map.get(row.item_subcategory)

#             # ── Cache save karo 5 min ke liye ───────────────────────────────
#             frappe.cache().set_value(cache_key, result, expires_in_sec=300)

#         else:
#             # ── Redis Cache check (non-customer data same hota hai) ──────────
#             cache_key = f"subcat_count_{categoryName}"
#             cached = frappe.cache().get_value(cache_key)
#             if cached:
#                 return cached

#             # ── STEP 1: Count query ──────────────────────────────────────────
#             count_query = """
#                 SELECT
#                     item.item_subcategory,
#                     COUNT(DISTINCT IFNULL(item.variant_of, item.item_code)) AS item_count,
#                     COUNT(DISTINCT se.name)                                  AS serial_count

#                 FROM `tabItem` AS item

#                 JOIN `tabAttribute Value` AS tav 
#                     ON item.item_subcategory = tav.name
#                     AND tav.is_subcategory = 1

#                 INNER JOIN `tabBOM` AS bom 
#                     ON item.item_code = bom.item
#                     AND bom.is_active = 1
#                     AND bom.bom_type = 'Finish Goods'

#                 INNER JOIN `tabItem Default` AS idf
#                     ON item.item_code = idf.parent
#                     AND idf.company = 'Gurukrupa Export Private Limited'

#                 LEFT JOIN `tabSerial No` AS se
#                     ON se.item_code = item.item_code
#                     AND se.status = 'Active'

#                 WHERE 
#                     item.item_subcategory IS NOT NULL
#                     AND item.item_category = %s

#                 GROUP BY 
#                     item.item_subcategory

#                 ORDER BY 
#                     item.item_subcategory
#             """
#             result = frappe.db.sql(count_query, (categoryName,), as_dict=True)

#             # ── STEP 2: first_image alag IN query se ────────────────────────
#             if result:
#                 subcategories = list({row.item_subcategory for row in result if row.item_subcategory})

#                 if subcategories:
#                     image_rows = frappe.db.sql("""
#                         SELECT 
#                             item2.item_subcategory,
#                             item2.image AS first_image
#                         FROM `tabItem` AS item2
#                         INNER JOIN (
#                             SELECT 
#                                 item_subcategory,
#                                 MAX(creation) AS latest_creation
#                             FROM `tabItem`
#                             WHERE 
#                                 item_subcategory IN %(subs)s
#                                 AND image IS NOT NULL
#                                 AND item_category = %(cat)s
#                                 AND (front_view IS NULL OR image != front_view)
#                             GROUP BY item_subcategory
#                         ) AS latest
#                             ON item2.item_subcategory = latest.item_subcategory
#                             AND item2.creation = latest.latest_creation
#                         WHERE 
#                             item2.item_subcategory IN %(subs)s
#                             AND item2.image IS NOT NULL
#                         GROUP BY item2.item_subcategory
#                     """, {"subs": tuple(subcategories), "cat": categoryName}, as_dict=True)

#                     image_map = {r.item_subcategory: r.first_image for r in image_rows}

#                     for row in result:
#                         row["first_image"] = image_map.get(row.item_subcategory)

#             # ── Cache save karo 5 min ke liye ───────────────────────────────
#             frappe.cache().set_value(cache_key, result, expires_in_sec=300)

#         return result

#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), "subcategory_count Error")
#         return {"error": str(e)}


@frappe.whitelist(allow_guest=True)
def remove_trending_item(customer, item_code, trending):

    trending = frappe.parse_json(trending) if isinstance(trending, str) else trending

    # Customer ke catalogue records
    get_catalogue_data = frappe.get_all(
        "Cataloge Master",
        filters={"customer": customer},
        fields=["name"]
    )

    parent_names = [d.name for d in get_catalogue_data]

    # Matching item rows
    items = frappe.get_all(
        "Cataloge Item Details",
        filters={
            "parent": ["in", parent_names],
            "item_code": item_code
        },
        fields=["name"]
    )

    for item in items:
        frappe.db.set_value(
            "Cataloge Item Details",
            item.name,
            "trending",
            trending
        )

    frappe.db.commit()

    return {
        "message": "Trending status updated",
        "item_code": item_code,
        "trending": trending
    }