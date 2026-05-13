import frappe
from frappe import _
from frappe.utils import flt
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
from gke_customization.gke_catalog.api.portal_live_api.notifications import notify_user


@frappe.whitelist(allow_guest = True)
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


    if customer:
        wishlist_case = "MAX(CASE WHEN tci.wishlist = 1 AND tcm.customer IS NOT NULL THEN 1 ELSE 0 END) AS wishlist"
        trending_case = "MAX(CASE WHEN tci.trending = 1 AND tcm.customer IS NOT NULL THEN 1 ELSE 0 END) AS trending"
        customer_join = "AND tcm.customer = %(customer)s"
    else:
        wishlist_case = "0 AS wishlist"
        trending_case = "0 AS trending"
        customer_join = ""  # ✅ No customer filter in JOIN


    values = {}

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
                item.image,
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

@frappe.whitelist()
def customer_wise_item(selectedSubcategory, customer = None, user = None,  metalType = None):
    selectedSubcategory = frappe.form_dict.get("selectedSubcategory")
    itemCode = frappe.form_dict.get("itemCode")
    itemCategory = frappe.form_dict.get("itemCategory")
    metalType = frappe.form_dict.get("metalType")

    where_clause = """
        idf.company = 'Gurukrupa Export Private Limited'
    """
        # AND bom.bom_type = 'Finish Goods'
        #   OR bom.bom_type = 'Template')

    if selectedSubcategory:
        where_clause = where_clause + f" AND item.item_subcategory = '{selectedSubcategory}' "
    if metalType == 'Gold':
        where_clause = where_clause + f" AND bom.metal_type = '{metalType}' AND (bom.bom_type = 'Finish Goods') " #  OR bom.bom_type = 'Template'
    if metalType == 'Silver':
        where_clause = where_clause + f" AND bom.metal_type = '{metalType}' AND (bom.bom_type = 'Finish Goods'  OR bom.bom_type = 'Template') "
    if customer:
        where_clause = where_clause + f" AND tcm.customer = '{customer}' "

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
                tci.folder,
                tci.wishlist,
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
                # bom.metal_colour,
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

    # frappe.throw(f"{d}")
    return {
        "db_data" : db_data,
        "folder": d,
        "internal_catalog_folder" : int_c_f
    } 

@frappe.whitelist()
def subcategory_count(categoryName, user_type, customer=None):
    try:
        if user_type == "Customer":
            sql_query = """
                SELECT 
                    ti.item_category, ti.item_subcategory, tb.metal_type,
                    COUNT(
                        DISTINCT CASE
                            WHEN tav.is_subcategory = 1  
                                AND ti.item_subcategory IS NOT NULL
                                AND fbom.bom_type = 'Finish Goods' 
                                AND fbom.is_active = 1  
                            THEN ti.name
                        END
                    ) AS item_count,
                    COUNT(
                        DISTINCT CASE
                            WHEN tav.is_subcategory = 1 
                                AND ti.item_subcategory IS NOT NULL 
                                AND fbom.bom_type = 'Finish Goods' 
                                AND fbom.is_active = 1 
                            THEN ti.name
                        END
                    ) AS serial_count
                FROM `tabCataloge Item Details` AS tci
                LEFT JOIN `tabCataloge Master` AS tcm 
                    ON tcm.name = tci.parent
                LEFT JOIN `tabItem` AS ti 
                    ON ti.name = tci.item_code
                LEFT JOIN `tabBOM` AS tb 
                    ON ti.name = tb.item
                LEFT JOIN `tabBOM` AS fbom 
                    ON fbom.item = ti.name  -- For serial_count
                JOIN `tabAttribute Value` AS tav 
                    ON ti.item_subcategory = tav.name  -- ✅ Changed to subcategory join
                WHERE  
                    (
                    (tav.is_subcategory = 1 AND ti.item_subcategory IS NOT NULL)
                    OR 
                    (fbom.bom_type = 'Finish Goods' AND fbom.is_active = 1)
                    )
                    AND tcm.customer = %s
                    AND tb.is_active = 1
                    AND ti.item_category = %s
                GROUP BY 
                    ti.item_category, ti.item_subcategory , tb.metal_type
                ORDER BY 
                    ti.item_category, ti.item_subcategory ,tb.metal_type
                    # , ti.item_code, ti.variant_of
            """
            result = frappe.db.sql(sql_query, (customer, categoryName), as_dict=True)

        else:
            sql_query = """
                SELECT
                    item.item_subcategory,
                    # COALESCE(tbm.metal_type, 'Unknown') AS metal_type,
                    # COUNT(DISTINCT item.name) AS item_count,
                    COUNT(
                        DISTINCT CASE
                            WHEN bom.bom_type = 'Finish Goods' AND bom.is_active = 1 THEN item.name
                        END
                    ) AS item_count,
                    COUNT(
                        DISTINCT CASE
                            WHEN bom.bom_type = 'Finish Goods' AND bom.is_active = 1 THEN item.name
                        END
                    ) AS serial_count
                FROM `tabItem` AS item
                JOIN `tabAttribute Value` AS tav 
                    ON item.item_subcategory = tav.name
                LEFT JOIN `tabBOM` AS bom 
                    ON item.item_code = bom.item
                LEFT JOIN `tabBOM Metal Detail` AS tbm 
                    ON tbm.parent = bom.name
                WHERE 
                    tav.is_subcategory = 1
                    AND item.item_subcategory IS NOT NULL
                    AND item.item_category = %s
                    # AND tbm.metal_type IN ('Gold', 'Silver')
                GROUP BY 
                    item.item_subcategory
                    # tbm.metal_type
                    # ,item.item_code, item.variant_of

                ORDER BY 
                    item.item_subcategory,
                    tbm.metal_type;
                    
                """
            result = frappe.db.sql(sql_query, (categoryName,), as_dict=True)

        return result

    except Exception as e:
        return {"error": str(e)}

@frappe.whitelist()
def category_count(user_type, customer=None):
    try:
        if user_type == "Customer":
            # sql_query = """
            #     SELECT 
            #         ti.item_category,
            #         ti.item_subcategory, 
            #         COUNT(
            #             DISTINCT CASE
            #                 WHEN fbom.bom_type = 'Finish Goods' 
            #                     AND fbom.is_active = 1 
            #                 THEN fbom.item
            #             END
            #         ) AS item_count,
            #         COUNT(
            #             DISTINCT CASE
            #                 WHEN fbom.bom_type = 'Finish Goods' 
            #                     AND fbom.is_active = 1 
            #                 THEN fbom.item
            #             END
            #         ) AS serial_count
            #         COUNT(
            #             DISTINCT CASE
            #                 WHEN fbom.bom_type = 'Finish Goods' 
            #                     AND fbom.is_active = 1 
            #                 THEN fbom.item
            #             END
            #         ) AS total_item_count
            #     FROM `tabCataloge Item Details` AS tci
            #     LEFT JOIN `tabCataloge Master` AS tcm ON tcm.name = tci.parent
            #     LEFT JOIN `tabItem` AS ti ON ti.name = tci.item_code
            #     LEFT JOIN `tabBOM` AS tb ON ti.name = tb.item
            #     LEFT JOIN `tabBOM` AS fbom ON fbom.item = ti.name  -- For serial_count
            #     JOIN `tabAttribute Value` AS tav ON ti.item_category = tav.name
            #     WHERE  
            #         ((tav.is_category = 1 AND ti.item_category IS NOT NULL)
            #         OR 
            #         (fbom.bom_type = 'Finish Goods' AND tb.is_active = 1))
            #         AND
            #         tcm.customer = %(customer)s
            #         AND tb.is_active = 1
            #     GROUP BY 
            #         ti.item_category,
            #         # ti.item_subcategory
            #     ORDER BY 
            #         ti.item_category,
            #         ti.item_subcategory
        
            # """
            sql_query = """
                SELECT 
                    ti.item_category,
                    COUNT(
                        DISTINCT CASE
                            WHEN fbom.bom_type = 'Finish Goods' 
                                AND fbom.is_active = 1 
                            THEN fbom.item
                        END
                    ) AS item_count,
                    COUNT(
                        DISTINCT CASE
                            WHEN fbom.bom_type = 'Finish Goods' 
                                AND fbom.is_active = 1 
                            THEN fbom.item
                        END
                    ) AS serial_count
                FROM `tabCataloge Item Details` AS tci
                LEFT JOIN `tabCataloge Master` AS tcm ON tcm.name = tci.parent
                LEFT JOIN `tabItem` AS ti ON ti.name = tci.item_code
                LEFT JOIN `tabBOM` AS tb ON ti.name = tb.item
                LEFT JOIN `tabBOM` AS fbom ON fbom.item = ti.name
                JOIN `tabAttribute Value` AS tav ON ti.item_category = tav.name
                WHERE  
                    ((tav.is_category = 1 AND ti.item_category IS NOT NULL)
                    OR 
                    (fbom.bom_type = 'Finish Goods' AND tb.is_active = 1))
                    AND tcm.customer = %(customer)s
                    AND tb.is_active = 1
                GROUP BY 
                    ti.item_category
                ORDER BY 
                    ti.item_category
            """

            values = {"customer": customer}
        else:
            # sql_query = """
            #     SELECT
            #         item.item_category,
            #         # item.item_subcategory,
            #         COUNT(
            #             DISTINCT CASE
            #                 WHEN tav.is_category = 1 
            #                      AND item.item_category IS NOT NULL 
            #                      AND bom.bom_type = 'Finish Goods' 
            #                      AND bom.is_active = 1
            #                 THEN item.name
            #             END
            #         ) AS item_count,
            #         COUNT(
            #             DISTINCT CASE
            #                 WHEN tav.is_category = 1 
            #                      AND item.item_category IS NOT NULL
            #                      AND bom.bom_type = 'Finish Goods' 
            #                      AND bom.is_active = 1 
            #                 THEN item.name
            #             END
            #         ) AS serial_count
            #     FROM 
            #         `tabItem` AS item
            #     JOIN 
            #         `tabAttribute Value` AS tav ON item.item_category = tav.name
            #     LEFT JOIN 
            #         `tabBOM` AS bom ON item.item_code = bom.item
            #     WHERE 
            #         (tav.is_category = 1 AND item.item_category IS NOT NULL)
            #         OR 
            #         (bom.bom_type = 'Finish Goods' AND bom.is_active = 1)
            #     GROUP BY 
            #         item.item_category
            #         limit 5
            # """
            sql_query = """
            SELECT
                    item.item_category,
                    COUNT(DISTINCT CASE WHEN bom.item_code IS NOT NULL THEN item.name END) AS item_count
                FROM
                    `tabItem` AS item
                JOIN
                    `tabAttribute Value` AS tav
                        ON item.item_category = tav.name
                LEFT JOIN (
                    SELECT DISTINCT item AS item_code
                    FROM `tabBOM`
                    WHERE bom_type = 'Finish Goods'
                    AND is_active = 1
                ) AS bom ON item.item_code = bom.item_code
                WHERE
                    tav.is_category = 1
                    AND item.item_category IS NOT NULL
                GROUP BY
                    item.item_category
            """
            values = {}

        # Execute query safely
        result = frappe.db.sql(sql_query, values=values, as_dict=True)
        return result

    except Exception as e:
        frappe.log_error(f"Category Count Error: {str(e)}", "category_count")
        return {"error": str(e)}

@frappe.whitelist()
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
   
    finding_sub_category = frappe.get_all("Attribute Value", filters={"is_finding_type": 1}, pluck="name")
    finding_sub_category = sorted(finding_sub_category)
    finding_subcategory_data = [{"finding_sub_category": name} for name in finding_sub_category ]
   
    # Return both in structured response
    return {
        "setting_types": setting_type_data,
        "metal_types": metal_type_data,
        "metal_touch": metal_touch_data,
        "diamond_quality": diamond_quality_data,
        "metal_color": metal_color_data,
        "stone_shape": diamond_stone_shape,
    "gemstone_shape": gemstone_stone_data,
        "sieve_size_range": diamond_sieve_size_range_data,
        # "sieve_size": diamond_sieve_size_data,
        "finding_sub_category": finding_subcategory_data
    }

@frappe.whitelist()
def get_customers_attribute_data(customer):
    setting_type = frappe.get_all("Attribute Value", filters={"is_setting_type": 1}, pluck="name")
    setting_type = sorted(setting_type)
    setting_type_data = [{"setting_type": name} for name in setting_type]

    # Metal Criteria
    metal_touch = frappe.get_all("Metal Criteria", filters={"parent": customer}, pluck="metal_touch")
    metal_touch = sorted(metal_touch)
    metal_touch_data = [{"metal_touch": name} for name in metal_touch ]
    
    # Customer Diamond Grade
    diamond_quality = frappe.get_all("Customer Diamond Grade", filters={"parent": customer}, pluck="diamond_quality")
    diamond_quality = sorted(diamond_quality)
    diamond_quality_data = [{"diamond_quality": name} for name in diamond_quality ]

    metal_color = frappe.get_all("Attribute Value", filters={"is_metal_colour": 1}, pluck="name")
    metal_color = sorted(metal_color)
    metal_color_data = [{"metal_color": name} for name in metal_color ]

    return { 
        "setting_types": setting_type_data,
        "metal_touch": metal_touch_data,
        "diamond_quality": diamond_quality_data, 
        "metal_color": metal_color_data
    }

@frappe.whitelist()
def get_selected_item_for_customer_by_user(items, customers):
    """
    Save selected items to 'Cataloge Master' for one or more customers.
    Supports trending value updates.
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
                else:
                    old_val = existing_items[item_code]
                    if old_val != trending_value:
                        for row in catalog_doc.cataloge_item_details:
                            if row.item_code == item_code:
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

            notify_user(customer_id[0].email_id, f"Cataloge Master Added {len(added)}, Updated {len(updated)} for customer You", f"Cataloge Master Added {len(added)}, Updated {len(updated)} for customer You")

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

            notify_user(customer_id[0].email_id, "Cataloge Master New Catloug Master Created For You", "Cataloge Master New Catloug Master Created For You")

    return {
        "status": "success",
        "results": results
    }

# //shubham
@frappe.whitelist()
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
    
@frappe.whitelist()
# def get_catalogue_collection_details(customers, collection, item_category=None, username=None):
def get_catalogue_collection_details(customers, collection, username=None):
    
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

@frappe.whitelist()
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

@frappe.whitelist()
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
    

@frappe.whitelist()
def get_wishlist_item_for_customer_by_user(items, user_type, customers):
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
                row.item_code: row.wishlist
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
                        "wishlist": trending_value,
                    })
                    added.append(item_code)

                # ----------------- UPDATE TRENDING -----------------
                else:
                    old_val = existing_items[item_code]
                    if old_val != trending_value:
                        for row in catalog_doc.cataloge_item_details:
                            if row.item_code == item_code:
                                row.wishlist = trending_value
                                updated.append(item_code)
                                break

            catalog_doc.save(ignore_permissions=True)

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
                    "wishlist": trending_value
                })

            catalog_doc.insert(ignore_permissions=True)

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

@frappe.whitelist()
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


@frappe.whitelist()
def get_similar_item(item_code):

    if not item_code:
        return []

    # Step 1: Get similar item codes
    similar_item_codes = frappe.db.sql("""
        SELECT sit.item_code
        FROM `tabItem` i
        LEFT JOIN `tabSimilar Item Table` sit
            ON sit.parent = i.name
            AND sit.parenttype = 'Item'
            AND sit.parentfield = 'custom_similar_item_table'
        WHERE i.name = %s
        AND i.custom_is_similar_item = 1
    """, (item_code,), pluck=True)

    if not similar_item_codes:
        return []

    # Convert to tuple for IN condition
    codes_tuple = tuple(similar_item_codes)

    # Step 2: Get all item details in single query
    items = frappe.db.sql("""
        SELECT item_code, image
        FROM `tabItem`
        WHERE name IN %(codes)s
    """, {
        "codes": codes_tuple
    }, as_dict=True)

    return items



@frappe.whitelist()
def get_item_of_customer_by_user(customer):
    if not customer:
        return {"message": "Customer not found"}

    catalog_names = frappe.get_all(
        "Cataloge Master",
        filters={"customer": customer},
        pluck="name"
    )

    items = frappe.get_all(
        "Cataloge Item Details",
        filters={"parent": ["in", catalog_names]},
        fields=["parent", "item_code", "item_name", "trending", "folder", "wishlist"]
    )

    return items


@frappe.whitelist()
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


import frappe

@frappe.whitelist()
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