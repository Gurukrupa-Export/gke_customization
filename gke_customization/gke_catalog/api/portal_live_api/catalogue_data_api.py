

import frappe
from frappe import _
from frappe.utils import flt
from gke_customization.gke_catalog.api.encryption_response import SecureJSON
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
                    
                WHERE 
                    ti.item_category IS NOT NULL
                    AND EXISTS(
                        SELECT 1 FROM `tabSerial No` AS sn0
                        WHERE sn0.item_code = ti.item_code
                    )
                
                GROUP BY
                    ti.item_category
                ORDER BY 
                    ti.item_category
            """
            
            values = {
                "customer":customer
            }
        else:
            sql_query = """
                SELECT 
                    item.item_category,
                    COUNT(DISTINCT IFNULL(item.variant_of, item.item_code)) AS item_count
                FROM `tabItem` AS item
                INNER JOIN `tabAttribute Value` AS tav
                    ON item.item_category = tav.name
                    AND tav.is_category = 1
                INNER JOIN `tabItem Default` AS idf
                    ON item.item_code = idf.parent
                    AND idf.company = 'Gurukrupa Export Private Limited'
                WHERE
                    item.item_category IS NOT NULL
                    AND item.item_group != 'Design DNU'
                    AND item.disabled = 0
                    
                    AND EXISTS (
                        SELECT 1 FROM `tabBOM` AS bom
                        WHERE bom.item = item.item_code
                        AND bom.is_active = 1
                    )
                    AND EXISTS(
                        SELECT 1 FROM `tabSerial No` AS sn0
                        WHERE sn0.item_code = item.item_code
                    )
                GROUP BY item.item_category
                ORDER BY item.item_category
            """
            values = {}
            
        result = frappe.db.sql(
            sql_query,
            values = values,
            as_dict = True
        )
        
        # return result
        secure = SecureJSON()
        enc_data = secure.encrypt(
            result
        )
        return enc_data
        
  
        
    
    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            "Category_count Error"
        )
        return {
            "error": str(e)
        }



@frappe.whitelist()
def subcategory_count(categoryName, user_type, customer=None):
    try:
        if user_type == "Customer":
            # ── Redis Cache (customer-specific) ─────────────────────────────
            cache_key = f"subcat_count_{categoryName}_{customer}"
            cached = frappe.cache().get_value(cache_key)
            if cached:
                # return cached
                secure = SecureJSON()
                return secure.encrypt(cached)
        
            # ── STEP 1: Count query ──────────────────────────────────────────
            count_query = """
                SELECT 
                    ti.item_category,
                    ti.item_subcategory,
                    # COUNT(DISTINCT IFNULL(ti.variant_of, ti.name)) AS item_count,
                    COUNT(DISTINCT IFNULL(ti.variant_of, ti.item_code)) AS item_count,  
                    COUNT(DISTINCT se.name) AS serial_count
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
                LEFT JOIN `tabSerial No` AS se
                    ON se.item_code = ti.name
                    AND se.status = 'Active'
                WHERE 
                    ti.item_subcategory IS NOT NULL
                    AND ti.item_group != 'Design DNU'
                    AND ti.disabled = 0
                    AND EXISTS (
                        SELECT 1 FROM `tabBOM` AS tb
                        WHERE tb.item = ti.name
                        AND tb.is_active = 1
                        AND tb.is_default = 1
                        AND tb.bom_type = 'Finish Goods'
                    )
                    AND EXISTS(
                        SELECT 1 FROM `tabSerial No` AS sn0
                        WHERE sn0.item_code = ti.item_code
                    )
                GROUP BY 
                    ti.item_category,
                    ti.item_subcategory
                ORDER BY 
                    ti.item_category,
                    ti.item_subcategory
            """
            result = frappe.db.sql(count_query, (customer, categoryName), as_dict=True)
        
        
            # ── STEP 2: FG image - saare items check karo ───────────────────
            if result:
                subcategories = list({row.item_subcategory for row in result if row.item_subcategory})
                if subcategories:
                    image_rows = frappe.db.sql("""
                        SELECT 
                            ti.item_subcategory, 
                            ti.image AS first_image,
                            ti.custom_catalogue_image,
                            ti.custom_silver_image
                        FROM `tabCataloge Item Details` tci
                        INNER JOIN `tabCataloge Master` tcm ON tcm.name = tci.parent
                        INNER JOIN `tabItem` ti ON ti.name = tci.item_code
                        INNER JOIN `tabBOM` tb ON tb.item = ti.name AND tb.is_active = 1
                        # AND tb.is_default = 1
                        WHERE tcm.customer = %(customer)s
                        AND EXISTS(
                            SELECT 1 FROM `tabSerial No` AS sn0
                            WHERE sn0.item_code = ti.item_code
                        )
                        AND ti.item_category = %(cat)s
                        AND ti.item_subcategory IN %(subs)s
                        AND ti.item_group != 'Design DNU'
                        AND ti.image IS NOT NULL
                        AND ti.front_view IS NOT NULL
                        AND ti.image != ti.front_view
                        ORDER BY ti.creation DESC
                    """, {
                        "customer": customer,
                        "cat": categoryName,
                        "subs": tuple(subcategories)
                    }, as_dict=True)
        
                    image_map = {}
                    # for row in image_rows:
                    #     if row.item_subcategory not in image_map:
                    #         image_map[row.item_subcategory] = row.first_image
                    
                    for row in image_rows:
                        if row.item_subcategory not in image_map:
                            image_map[row.item_subcategory] = {
                                "first_image": row.first_image,
                                "custom_catalogue_image": row.custom_catalogue_image,
                                "custom_silver_image": row.custom_silver_image
                            }

                    # for row in result:
                    #     row["first_image"] = image_map.get(row.item_subcategory)
                    for row in result:
                        images = image_map.get(row.item_subcategory, {})
                        row["first_image"] = images.get("first_image")
                        row["custom_catalogue_image"] = images.get("custom_catalogue_image")
                        row["custom_silver_image"] = images.get("custom_silver_image")
        
                # ── Cache save karo 5 min ke liye ───────────────────────────────
                frappe.cache().set_value(cache_key, result, expires_in_sec=300)
                
            # return result
            secure = SecureJSON()
            enc_Data = secure.encrypt(result)
            return enc_Data
                    
            
        else:
            # ── Redis Cache ──────────────────────────────────────────────────
            cache_key = f"subcat_count_{categoryName}"
            cached = frappe.cache().get_value(cache_key)
            if cached:
                # return cached
                secure = SecureJSON()
                return secure.encrypt(cached)

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

                INNER JOIN `tabItem Default` AS idf
                    ON item.item_code = idf.parent
                    AND idf.company = 'Gurukrupa Export Private Limited'

                LEFT JOIN `tabSerial No` AS se
                    ON se.item_code = item.item_code
                    AND se.status = 'Active'

                WHERE 
                    item.item_subcategory IS NOT NULL
                    AND item.item_category = %s
                    AND item.item_group != 'Design DNU'        
                    AND item.disabled = 0                       
                    AND EXISTS (
                        SELECT 1 FROM `tabBOM` AS bom
                        WHERE bom.item = item.item_code
                        AND bom.is_active = 1
                        # AND bom.bom_type = 'Finish Goods'
                    )
                    AND EXISTS(
                        SELECT 1 FROM `tabSerial No` AS sn0
                        WHERE sn0.item_code = item.item_code
                    )

                GROUP BY 
                    item.item_subcategory

                ORDER BY 
                    item.item_subcategory
            """
            result = frappe.db.sql(count_query, (categoryName,), as_dict=True)

            # ── STEP 2: FG image - directly tabItem se, NO catalogue filter ─
            if result:
                subcategories = list({row.item_subcategory for row in result if row.item_subcategory})

                if subcategories:
                    image_rows = frappe.db.sql("""
                        SELECT
                            ti.item_subcategory,
                            ti.image AS first_image,
                            ti.custom_catalogue_image,
                            ti.custom_silver_image
                        FROM `tabItem` ti
                        INNER JOIN `tabBOM` tb
                            ON tb.item = ti.name
                            AND tb.is_active = 1
                            # AND tb.bom_type = 'Finish Goods'
                        INNER JOIN `tabItem Default` idf
                            ON ti.name = idf.parent
                            AND idf.company = 'Gurukrupa Export Private Limited'
                        WHERE
                            ti.item_category = %(cat)s
                            AND ti.item_subcategory IN %(subs)s
                            AND ti.item_group != 'Design DNU'
                            AND ti.image IS NOT NULL
                            AND ti.front_view IS NOT NULL
                            AND ti.image != ti.front_view
                        ORDER BY ti.creation DESC
                    """, {
                        "cat": categoryName,
                        "subs": tuple(subcategories)
                    }, as_dict=True)

                    image_map = {}
                    # for row in image_rows:
                    #     if row.item_subcategory not in image_map:
                    #         image_map[row.item_subcategory] = row.first_image
                    
                    for row in image_rows:
                        if row.item_subcategory not in image_map:
                            image_map[row.item_subcategory] = {
                                "first_image":row.first_image,
                                "custom_catalogue_image":row.custom_catalogue_image,
                                "custom_silver_image":row.custom_silver_iamge
                            }
                    
                    # for row in result:
                    #     row["first_image"] = image_map.get(row.item_subcategory)
                    
                    for row in result:
                        images = image_map.get(row.item_subcategory, {})
                        row["first_image"] = images.get("first_image")
                        row["custom_catalogue_image"] = images.get("custom_catalogue_image")
                        row["custom_silver_image"] = images.get("custom_silver_image")

            # ── Cache save karo 5 min ke liye ───────────────────────────────
            frappe.cache().set_value(cache_key, result, expires_in_sec=300)
            
            # return result
            
            secure = SecureJSON()
            enc_data = secure.encrypt(result)
            return enc_data

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "subcategory_count Error")
        return {"error": str(e)}


def get_is_filter(search, values, wishlist_case, sub_where, customer_join, where_clause,order_by="item.creation DESC"):
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
            # Wrap each term's OR-group in its own parentheses
            search_conditions.append(f"""(
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
            )""")

        search_where = " AND ".join(search_conditions)

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
        elif "Nova Glow" in search_terms:
            setting_filter = """
                AND item.setting_type = 'Nova Glow'
            """
        # frappe.throw(f"{ where_clause}")
        
        matched_item_codes = frappe.db.sql(
            f"""
            SELECT DISTINCT
                IFNULL(item.variant_of, item.item_code) AS item_code,
                item.item_name
            FROM `tabItem` item
            INNER JOIN `tabSerial No` sn
                ON sn.name = (
                    SELECT sn2.name
                    FROM `tabSerial No` sn2
                    WHERE sn2.item_code = item.item_code
                    ORDER BY sn2.creation ASC, sn2.name ASC
                    LIMIT 1
                )
            INNER JOIN `tabBOM` bom
                ON bom.name = sn.custom_bom_no
            LEFT JOIN `tabItem Default` idf
                ON idf.parent = item.item_name
            LEFT JOIN `tabDesign Attribute - Multiselect` dam
                ON dam.parent = item.item_code
     
            WHERE 1=1
                # bom.bom_type = 'Finish Goods'
                {"AND idf.company = %(company)s" if values.get("company") else ""}
                AND (
                    {search_where}
                )
                {setting_filter}
            """,
            values,
            as_list=True
        )
    
    # frappe.throw(f"{matched_item_codes}")

   
    item_code_list = list({row[0] for row in matched_item_codes})
    item_name_list = list({row[1] for row in matched_item_codes})

    
    matched_item_codes = item_code_list
    matched_item_name = item_name_list

    values["item_name"] = tuple(matched_item_name) if matched_item_name else ('',)
    where_clause += """
            AND item.item_name IN %(item_name)s
        """

    if not matched_item_codes:
        return [], 0

    if len(matched_item_codes) == 1:
        values["single_item_code"] = matched_item_codes[0]
        where_clause += """
            AND IFNULL(item.variant_of, item.item_code) = %(single_item_code)s
        """
    else:
        values["item_codes"] = tuple(matched_item_codes)
        where_clause += """
            AND IFNULL(item.variant_of, item.item_code) IN %(item_codes)s
        """
        
    base_query = f"""
        SELECT
            item.name,
            bom.name AS bom_name,
            bom.sub_setting_type1,
            idf.company,
            tci.trending,
            tci.name AS catalog_item_details_name,
            {wishlist_case},
            item.creation,
            item.item_code,
            item.item_category,
            sn.name AS serial_no,
            sn.creation AS serial_creation,
            sn.status AS serial_status,
            sn.custom_bom_no AS serial_bom_no,
            item.image,
            item.sketch_image,
            item.custom_catalogue_image,
            item.custom_silver_image, 
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
                WHEN item.custom_is_set_item = 1 AND set_check.is_set_item = 1 THEN 1
                ELSE 0
            END AS is_set_item,

            CASE
                WHEN item.custom_is_similar_item = 1 AND similar_check.is_similar_item = 1 THEN 1
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

           
            dam_pivot.custom_collection,
            dam_pivot.custom_language,
            dam_pivot.custom_zodiac,
            dam_pivot.custom_animalbirds,
            dam_pivot.custom_alphabetnumber,
            dam_pivot.custom_religious,
            dam_pivot.custom_age_group,
            dam_pivot.custom_gender,
            dam_pivot.custom_design_style,
            dam_pivot.custom_rhodium,
            dam_pivot.custom_occasion

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
                COALESCE(i.variant_of, i.item_code) AS group_key,
                COUNT(DISTINCT i.item_code) AS variant_count
            FROM `tabItem` AS i
            INNER JOIN `tabItem Default` AS idf3
                ON i.item_name = idf3.parent
                AND idf3.company = 'Gurukrupa Export Private Limited'
            INNER JOIN `tabSerial No` AS sn3
                ON sn3.name = (
                    SELECT sn4.name
                    FROM `tabSerial No` AS sn4
                    WHERE sn4.item_code = i.item_code
                    ORDER BY sn4.creation ASC, sn4.name ASC
                    LIMIT 1
                )
            INNER JOIN `tabBOM` AS b
                ON b.name = sn3.custom_bom_no
            WHERE
                i.item_group != 'Design DNU'
                AND i.disabled = 0
            GROUP BY COALESCE(i.variant_of, i.item_code)
        ) vc ON vc.group_key = COALESCE(item.variant_of, item.item_code)


        # LEFT JOIN (
        #     SELECT
        #         parent AS item_code,
        #         1 AS is_set_item
        #     FROM `tabSet Item Table`
        #     WHERE parenttype = 'Item'
        #       AND parentfield = 'custom_set_item_table'
        #     GROUP BY parent
        # ) set_check ON set_check.item_code = item.item_code
        
        LEFT JOIN(
            SELECT
                sit.parent AS item_code,
                1 AS is_set_item
            FROM `tabSet Item Table` sit
            INNER JOIN `tabSerial No` AS sn5
                ON sn5.name = (
                    SELECT sn6.name
                    FROM `tabSerial No` AS sn6
                    WHERE sn6.item_code = sit.item_code
                    ORDER BY sn6.creation ASC, sn6.name ASC
                    LIMIT 1
                )
            INNER JOIN `tabBOM` AS b2
                ON b2.name = sn5.custom_bom_no
            WHERE sit.parenttype = 'Item'
              AND sit.parentfield = 'custom_set_item_table'
            GROUP BY sit.parent
        ) AS set_check ON set_check.item_code = item.item_code

        LEFT JOIN(
            SELECT
                sit.parent AS item_code,
                1 AS is_similar_item
            FROM `tabSimilar Item Table` sit
            WHERE sit.parenttype = 'Item'
              AND sit.parentfield = 'custom_similar_item_table'
              AND EXISTS (
                  SELECT 1
                  FROM `tabSerial No` AS s
                  INNER JOIN `tabBOM` AS b ON b.name = s.custom_bom_no
                  WHERE s.item_code = sit.item_code
              )
            GROUP BY sit.parent
        ) AS similar_check ON similar_check.item_code = item.item_code

        LEFT JOIN `tabCataloge Item Details` tci
            ON tci.item_code = item.name

        LEFT JOIN `tabCataloge Master` tcm
            ON tcm.name = tci.parent
            {customer_join}

        INNER JOIN `tabSerial No` AS sn
            ON sn.name = (
                SELECT sn2.name
                FROM `tabSerial No` AS sn2
                WHERE sn2.item_code = item.item_code
                ORDER BY sn2.creation ASC, sn2.name ASC
                LIMIT 1
            )
            
        LEFT JOIN `tabBOM` bom
            ON bom.name = sn.custom_bom_no

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

        LEFT JOIN (
            SELECT
                dam.parent,
                GROUP_CONCAT(CASE WHEN dam.parentfield='custom_collection' THEN dam.design_attribute END) AS custom_collection,
                GROUP_CONCAT(CASE WHEN dam.parentfield='custom_language' THEN dam.design_attribute END) AS custom_language,
                GROUP_CONCAT(CASE WHEN dam.parentfield='custom_zodiac' THEN dam.design_attribute END) AS custom_zodiac,
                GROUP_CONCAT(CASE WHEN dam.parentfield='custom_animalbirds' THEN dam.design_attribute END) AS custom_animalbirds,
                GROUP_CONCAT(CASE WHEN dam.parentfield='custom_alphabetnumber' THEN dam.design_attribute END) AS custom_alphabetnumber,
                GROUP_CONCAT(CASE WHEN dam.parentfield='custom_religious' THEN dam.design_attribute END) AS custom_religious,
                GROUP_CONCAT(CASE WHEN dam.parentfield='custom_age_group' THEN dam.design_attribute END) AS custom_age_group,
                GROUP_CONCAT(CASE WHEN dam.parentfield='custom_gender' THEN dam.design_attribute END) AS custom_gender,
                GROUP_CONCAT(CASE WHEN dam.parentfield='custom_design_style' THEN dam.design_attribute END) AS custom_design_style,
                GROUP_CONCAT(CASE WHEN dam.parentfield='custom_rhodium' THEN dam.design_attribute END) AS custom_rhodium,
                GROUP_CONCAT(CASE WHEN dam.parentfield='custom_occasion' THEN dam.design_attribute END) AS custom_occasion
            FROM `tabDesign Attribute - Multiselect` dam
            GROUP BY dam.parent
        ) dam_pivot
            ON dam_pivot.parent = item.item_code

        WHERE
            {where_clause}

        GROUP BY item.item_code

        # ORDER BY item.creation DESC
        ORDER BY {order_by}
    """
    
    
    # LEFT JOIN (
    #         SELECT
    #             parent,
    #             MAX(CASE WHEN parentfield = 'custom_collection'     THEN attrs END) AS custom_collection,
    #             MAX(CASE WHEN parentfield = 'custom_language'       THEN attrs END) AS custom_language,
    #             MAX(CASE WHEN parentfield = 'custom_zodiac'         THEN attrs END) AS custom_zodiac,
    #             MAX(CASE WHEN parentfield = 'custom_animalbirds'    THEN attrs END) AS custom_animalbirds,
    #             MAX(CASE WHEN parentfield = 'custom_alphabetnumber' THEN attrs END) AS custom_alphabetnumber,
    #             MAX(CASE WHEN parentfield = 'custom_occasion'      THEN attrs END) AS custom_occasion,
    #             MAX(CASE WHEN parentfield = 'custom_rhodium'      THEN attrs END) AS custom_rhodium,
    #             MAX(CASE WHEN parentfield = 'custom_gender'      THEN attrs END) AS custom_gender,
    #             MAX(CASE WHEN parentfield = 'custom_age_group'      THEN attrs END) AS custom_age_group,
    #             MAX(CASE WHEN parentfield = 'custom_design_style'      THEN attrs END) AS custom_design_style,
    #             MAX(CASE WHEN parentfield = 'custom_religious'      THEN attrs END) AS custom_religious
    #         FROM (
    #             SELECT
    #                 parent,
    #                 parentfield,
    #                 GROUP_CONCAT(design_attribute ORDER BY design_attribute SEPARATOR ', ') AS attrs
    #             FROM `tabDesign Attribute - Multiselect`
    #             GROUP BY parent, parentfield
    #         ) grouped
    #         GROUP BY parent
    #     ) dam_pivot
    #         ON dam_pivot.parent = item.item_code
    
    db_data = frappe.db.sql(
        base_query,
        values,
        as_dict=True
    )
    
    start = values.get("offset", 0)
    end = start + values.get("page_size", 48)

    # return db_data[start:end], len(db_data)
    data = db_data[start:end], len(db_data)
    secure = SecureJSON()
    enc_data = secure.encrypt(data)
    return enc_data


@frappe.whitelist(allow_guest=True)
def catalogue_data(selectedSubcategory=None, itemCategory=None, itemCode=None, metalType=None, company=None, customer=None, page=1, page_size=48, is_filter=None, search=None,sort_by=None):
    
    SORT_MAP = {
        "creation_ntl": "item.creation DESC, item.item_code ASC",
        "creation_otn": "item.creation ASC, item.item_code ASC",
        "gc_lth": "IFNULL(bom.custom_rating, 0) ASC, item.item_code ASC",
        "gc_htl": "IFNULL(bom.custom_rating, 0) DESC, item.item_code ASC",
    }
    sort_order = SORT_MAP.get(sort_by)
        
        
    if selectedSubcategory is None:
        selectedSubcategory = frappe.form_dict.get("selectedSubcategory")
        
    if itemCode is None:
        itemCode = frappe.form_dict.get("itemCode")
        
    if metalType is None:
        metalType = frappe.form_dict.get("metalType")
        
    if itemCategory is None:
        itemCategory = frappe.form_dict.get("itemCategory")
        
    values = {}
    
    # sub_where  = "b.is_active AND i.item_group != 'Design Dnu' AND i.disabled = 0"
    sub_where  = """b.is_active AND i.item_group != 'Design Dnu' AND i.disabled = 0
                AND EXISTS (
                    SELECT 1 FROM `tabSerial No` sn0
                    WHERE sn0.item_code = i.item_code
                )"""
    # CHANGED: bom.is_active = 1 hata diya, kyunki ab BOM serial ke custom_bom_no se aa raha hai
    where_clause = "1=1 AND item.item_group != 'Design DNU' AND item.disabled = 0"
    
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
            
    if customer:
        wishlist_case = "MAX(CASE WHEN tci.wishlist = 1 AND tcm.wishlist = 1 AND tcm.customer IS NOT NULL THEN 1 ELSE 0 END) AS wishlist"
        customer_join = "AND tcm.customer = %(customer)s"
        values["customer"] = customer
    else:
        wishlist_case = "0 AS wishlist"
        customer_join = ""
        
    page_param = frappe.form_dict.get("page")
    
    # if page_param is None:
    #     return {
    #         "data": []
    #     }
    if page_param is None:
        secure = SecureJSON()
        return secure.encrypt({
            "data": []
        })
        
    if sort_by == "Trending":
        where_clause += " AND tci.trending = 1"
        if customer:
            where_clause += " AND tcm.customer = %(customer)s"
            
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
        
        # data, total_count = get_is_filter(search, values, wishlist_case, sub_where, customer_join, where_clause)
        data, total_count = get_is_filter(
            search, values, wishlist_case, sub_where, customer_join, where_clause,
            sort_order or "item.creation DESC",
        )
        
        data = {
            "data": data,
            "total_count": total_count,
            "page":page,
            "page_size":page_size,
            "has_more": (offset + page_size) < total_count
        }
        secure = SecureJSON()
        enc_data = secure.encrypt(data)
        return enc_data
    order_by_final = sort_order or "item.item_code ASC"
    base_query = f"""
        SELECT
            item.name,
            bom.name AS bom,
            bom.sub_setting_type1,
            idf.company,
            tci.trending,
            tci.name as catalog_item_details_name,
            {wishlist_case},
            item.creation,
            item.item_code,
            sn.name AS serial_no,
            sn.creation AS serial_creation,
            sn.status AS serial_status,
            sn.custom_bom_no AS serial_bom_no,
            item.item_category,
            item.image,
            item.sketch_image,
            item.custom_catalogue_image,
            item.custom_silver_image,
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
            
            FORMAT(bom.gross_weight, 3) AS gross_metal_weight,
            FORMAT(bom.metal_and_finding_weight, 3) AS net_metal_finding_weight,
            FORMAT(bom.total_diamond_weight_in_gms, 3) AS total_diamond_weight_in_gms,
            FORMAT(bom.other_weight, 3) AS other_weight,
            FORMAT(bom.finding_weight, 3) AS finding_weight_,
            
            bom.metal_colour,
            bom.metal_touch,
            bom.metal_purity,
            FORMAT(bom.total_gemstone_weight_in_gms, 3) AS total_gemstone_weight_in_gms,
            
            bom.total_diamond_pcs,
            bom.total_gemstone_pcs,
            FORMAT(bom.gemstone_weight, 3) AS gemstone_weight,
            
            FORMAT(bom.gold_to_diamond_ratio, 3) AS gold_diamond_ratio,
            FORMAT(bom.diamond_ratio, 3) AS diamond_ratio,
            FORMAT(bom.metal_to_diamond_ratio_excl_of_finding, 3) AS metal_diamond_ratio,
            
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
                WHEN item.custom_is_set_item = 1 AND set_check.is_set_item = 1 THEN 1
                ELSE 0
            END AS is_set_item,
            
            CASE
                WHEN item.custom_is_similar_item = 1 AND similar_check.is_similar_item = 1 THEN 1
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
            
            GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
            GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
            GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
            GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm, 3)) AS size_in_mm,
            GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,
            
            GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
            GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
            GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size, 3)) AS finding_size
        FROM `tabItem` AS item
        
        LEFT JOIN(
            SELECT
                COALESCE(i.variant_of, i.item_code) AS group_key,
                COUNT(DISTINCT i.item_code) AS variant_count
            FROM `tabItem` AS i
            INNER JOIN `tabItem Default` AS idf3
                ON i.item_name = idf3.parent
                AND idf3.company = 'Gurukrupa Export Private Limited'
            WHERE
                i.item_group != 'Design DNU'
                AND i.disabled = 0
                AND EXISTS (
                    SELECT 1
                    FROM `tabSerial No` AS s
                    INNER JOIN `tabBOM` AS b ON b.name = s.custom_bom_no
                    WHERE s.item_code = i.item_code
                )
            GROUP BY COALESCE(i.variant_of, i.item_code)
        ) vc ON vc.group_key = COALESCE(item.variant_of, item.item_code)
        
        LEFT JOIN(
            SELECT
                sit.parent AS item_code,
                1 AS is_set_item
            FROM `tabSet Item Table` sit
            WHERE sit.parenttype = 'Item'
              AND sit.parentfield = 'custom_set_item_table'
              AND EXISTS (
                  SELECT 1
                  FROM `tabSerial No` AS s
                  INNER JOIN `tabBOM` AS b ON b.name = s.custom_bom_no
                  WHERE s.item_code = sit.item_code
              )
            GROUP BY sit.parent
        ) AS set_check ON set_check.item_code = item.item_code
        
        LEFT JOIN(
            SELECT
                sit.parent AS item_code,
                1 AS is_similar_item
            FROM `tabSimilar Item Table` sit
            WHERE sit.parenttype = 'Item'
              AND sit.parentfield = 'custom_similar_item_table'
              AND EXISTS (
                  SELECT 1
                  FROM `tabSerial No` AS s
                  INNER JOIN `tabBOM` AS b ON b.name = s.custom_bom_no
                  WHERE s.item_code = sit.item_code
              )
            GROUP BY sit.parent
        ) AS similar_check ON similar_check.item_code = item.item_code
        
        INNER JOIN(
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
            
        INNER JOIN `tabSerial No` AS sn
            ON sn.name = (
                SELECT sn2.name
                FROM `tabSerial No` AS sn2
                WHERE sn2.item_code = item.item_code
                ORDER BY sn2.creation ASC, sn2.name ASC
                LIMIT 1
            )
            
        LEFT JOIN `tabCataloge Item Details` AS tci ON tci.item_code = item.name
        LEFT JOIN `tabCataloge Master` AS tcm ON tcm.name = tci.parent {customer_join}
        -- CHANGED: BOM ab serial ke custom_bom_no se join ho raha hai
        LEFT JOIN `tabBOM` AS bom ON bom.name = sn.custom_bom_no
        LEFT JOIN `tabDesign Attributes` AS td ON item.item_code = td.parent
        LEFT JOIN `tabBOM Metal Detail` AS mt ON bom.name = mt.parent
        LEFT JOIN `tabBOM Gemstone Detail` AS gd ON bom.name = gd.parent
        LEFT JOIN `tabBOM Diamond Detail` AS dd ON bom.name = dd.parent
        LEFT JOIN `tabBOM Finding Detail` AS fd ON bom.name = fd.parent
        LEFT JOIN `tabBOM Other Detail` AS od ON bom.name = od.parent
        LEFT JOIN `tabItem Default` AS idf ON item.item_name = idf.parent
        
        WHERE {where_clause}
        #   AND serial_bom.bom_type = 'Finish Goods'
        GROUP BY item.item_code, item.variant_of
        # ORDER BY item.item_code ASC
        ORDER BY {order_by_final}
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
            as_dict = True
        )
    else:
        # paginated_query = base_query + """
        #     LIMIT %(page_size)s OFFSET %(offset)s
        # """
        
        # db_data = frappe.db.sql(
        #     paginated_query,
        #     values,
        #     as_dict=True
        # )
        paginated_query = base_query + " LIMIT %(page_size)s OFFSET %(offset)s"
                
        db_data = frappe.db.sql(paginated_query, values, as_dict=True)
        
    # -------------MULTISELECT ATTRIBUTES-----------
    item_codes = [row.item_code for row in db_data]
    
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
        
    # CHANGED: sn join pehle, phir BOM sn.custom_bom_no se (base_query ke jaisa)
    count_query = frappe.db.sql(f"""
    SELECT COUNT(*)
        FROM(
            SELECT IFNULL(item.variant_of, item.item_code)
            FROM `tabItem` item
            LEFT JOIN `tabItem Default` idf ON item.item_name = idf.parent
            INNER JOIN `tabSerial No` AS sn
                ON sn.name = (
                    SELECT sn2.name
                    FROM `tabSerial No` AS sn2
                    WHERE sn2.item_code = item.item_code
                    ORDER BY sn2.creation ASC, sn2.name ASC
                    LIMIT 1
                )
            LEFT JOIN `tabBOM` bom ON bom.name = sn.custom_bom_no
            LEFT JOIN `tabCataloge Item Details` tci ON tci.item_code = item.name
            LEFT JOIN `tabCataloge Master` tcm ON tcm.name = tci.parent {customer_join}
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
            attr_map[parent]={}
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
        
    if page == 1 and is_filter ==0:
        data = {
            "data": db_data[0:48],
            "filters":filters,
            "total_count":total_count,
            "page":page,
            "page_size":page_size,
            "has_more":(offset + page_size) < total_count
        }
        secure = SecureJSON()
        enc_data = secure.encrypt(data)
        return enc_data
        
    data =  {
        "data":db_data[0:48],
        "filters":filters,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "has_more":(offset + page_size) < total_count
    }
    
    secure = SecureJSON()
    enc_data = secure.encrypt(data)
    return enc_data


@frappe.whitelist()
def get_variants_by_itemcode(itemCode=None, customer=None):
    
    current_user = frappe.session.user
    
    is_customer = frappe.db.exists("Customer", {"user": current_user})
    
    if is_customer:
        bom_condition = "AND bom.bom_type = 'Finish Goods'"
    else:
        bom_condition = ""

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
            sn.name AS serial_no,
            sn.custom_bom_no AS serial_bom_no,
            item.custom_catalogue_image AS custom_catalogue_image,
            item.custom_silver_image AS custom_silver_image,
            
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

        # INNER JOIN `tabBOM` bom
        #     ON item.item_code = bom.item
        #     {bom_condition}
        
        INNER JOIN `tabSerial No` AS sn
            ON sn.name = (
                SELECT sn2.name
                FROM `tabSerial No` AS sn2
                WHERE sn2.item_code = item.item_code
                ORDER BY sn2.creation ASC, sn2.name ASC
                LIMIT 1
            )
        INNER JOIN `tabBOM` bom
            ON bom.name = sn.custom_bom_no
            {bom_condition}

        LEFT JOIN `tabDesign Attributes` AS td ON item.item_code = td.parent
        LEFT JOIN `tabBOM Metal Detail` AS mt ON bom.name = mt.parent
        LEFT JOIN `tabBOM Gemstone Detail` AS gd ON bom.name = gd.parent
        LEFT JOIN `tabBOM Diamond Detail` AS dd ON bom.name = dd.parent
        LEFT JOIN `tabBOM Finding Detail` AS fd ON bom.name = fd.parent

        LEFT JOIN `tabItem Default` AS idf ON item.item_name = idf.parent

        WHERE
            item.item_code LIKE %(base_code)s
            AND idf.company = 'Gurukrupa Export Private Limited'
            AND item.item_group != 'Design DNU'

        GROUP BY item.item_code
        ORDER BY item.creation ASC
    """, {"base_code": base_code + "%", "customer": customer, "itemCode": itemCode} , as_dict=True)
    # """, {"base_code": base_code + "%", "customer": customer}, as_dict=True)

    if len(db_data) <= 1:
        return []

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

    secure = SecureJSON()

    enc_data = secure.encrypt(
        db_data
    )

    return enc_data
    # return db_data


@frappe.whitelist()
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

    # parent hamesha list mein rahega (set table khali ho tab bhi)
    linked_item_codes = [itemCode]
    for row in set_items:
        if row.item_code not in linked_item_codes:
            linked_item_codes.append(row.item_code)

    # ---------------- CUSTOMER SIDE ----------------
    if customer:
        placeholders_check = ", ".join([f"%(chk_{i})s" for i in range(len(linked_item_codes))])
        check_params = {f"chk_{i}": code for i, code in enumerate(linked_item_codes)}
        check_params["customer"] = customer

        # sirf wahi items jo is customer ke catalogue mein hain
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

        # trending / wishlist sirf isi customer ke catalogue se
        trending_col = "COALESCE(cat.trending, 0) AS trending"
        wishlist_col = "COALESCE(cat.wishlist, 0) AS wishlist"
        catalogue_join = """
            LEFT JOIN (
                SELECT
                    tci.item_code,
                    MAX(tci.trending) AS trending,
                    MAX(tci.wishlist) AS wishlist
                FROM `tabCataloge Item Details` AS tci
                INNER JOIN `tabCataloge Master` AS tcm
                    ON tcm.name = tci.parent
                    AND tcm.customer = %(customer)s
                GROUP BY tci.item_code
            ) AS cat ON cat.item_code = item.name
        """

    # ---------------- USER SIDE (jaisa pehle tha, same) ----------------
    else:
        trending_col = "tci.trending"
        wishlist_col = "0 AS wishlist"
        catalogue_join = """
            LEFT JOIN `tabCataloge Item Details` AS tci ON tci.item_code = item.name
            LEFT JOIN `tabCataloge Master` AS tcm ON tcm.name = tci.parent
        """

    placeholders = ", ".join([f"%(item_{i})s" for i in range(len(linked_item_codes))])
    item_params = {f"item_{i}": code for i, code in enumerate(linked_item_codes)}
    item_params["customer"] = customer

    db_data = frappe.db.sql(f"""
        SELECT
            item.name,
            {trending_col},
            {wishlist_col},
            item.creation,
            item.item_code,
            item.item_category,
            sn.name AS serial_no,
            sn.custom_bom_no AS serial_bom_no,
            item.custom_catalogue_image AS custom_catalogue_image,
            item.custom_silver_image AS custom_silver_image,
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

        {catalogue_join}

        INNER JOIN `tabSerial No` AS sn
            ON sn.name = (
                SELECT sn2.name
                FROM `tabSerial No` AS sn2
                WHERE sn2.item_code = item.item_code
                ORDER BY sn2.creation ASC, sn2.name ASC
                LIMIT 1
            )
        INNER JOIN `tabBOM` bom
            ON bom.name = sn.custom_bom_no

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

    # return db_data
    secure = SecureJSON()
    enc_data = secure.encrypt(db_data)
    return enc_data


@frappe.whitelist()
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
            AND EXISTS (
                SELECT 1
                FROM `tabSerial No` AS s
                INNER JOIN `tabBOM` AS b ON b.name = s.custom_bom_no
                WHERE s.item_code = item.item_code
            )
        """, {
            "item_code": item_code,
            "customer": customer
        }, as_dict=True)

        # return items
        secure = SecureJSON()
        enc_data = secure.encrypt(items)
        return enc_data

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
            AND EXISTS (
                SELECT 1
                FROM `tabSerial No` AS s
                INNER JOIN `tabBOM` AS b ON b.name = s.custom_bom_no
                WHERE s.item_code = item.item_code
            )
        """, {
            "item_code": item_code,
            "user": user
        }, as_dict=True)

        # return items
        secure = SecureJSON()
        enc_data = secure.encrypt(items)
        return enc_data

    # =========================
    # NO FILTER
    # =========================
    else:

        # items = frappe.db.sql("""
        #     SELECT DISTINCT
        #         item.item_code,
        #         item.image

        #     FROM `tabSimilar Item Table` sit

        #     INNER JOIN `tabItem` item
        #         ON item.name = sit.item_code

        #     WHERE sit.parent = %(item_code)s
        #     AND sit.parenttype = 'Item'
        #     AND sit.parentfield = 'custom_similar_item_table'
        # """, {
        #     "item_code": item_code
        # }, as_dict=True)
        
        
        
        
        
        # items = frappe.db.sql(f"""
        #     SELECT
        #         item.name,
        #         item.item_code,
        #         item.image,
        #         item.custom_catalogue_image AS catalogue_image,
        #         item.sketch_image,
        #         item.front_view AS cad_image,

        #         item.item_category,
        #         item.item_subcategory,
        #         item.setting_type,
        #         item.stylebio,
        #         item.variant_of,

        #         bom.name AS bom_name,
        #         bom.sub_setting_type1,
        #         bom.tag_no,
        #         bom.diamond_quality,

        #         FORMAT(bom.gross_weight,3) AS gross_metal_weight,
        #         FORMAT(bom.metal_and_finding_weight,3) AS net_metal_finding_weight,
        #         FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
        #         FORMAT(bom.other_weight,3) AS other_weight,
        #         FORMAT(bom.finding_weight_,3) AS finding_weight_,

        #         bom.metal_colour,
        #         bom.metal_touch,
        #         bom.metal_purity,

        #         idf.company

        #     FROM `tabSimilar Item Table` sit
            
        #     INNER JOIN `tabItem` item
        #         ON item.name = sit.item_code

        #     LEFT JOIN `tabBOM` bom
        #         ON bom.item = item.item_code

        #     LEFT JOIN `tabItem Default` idf
        #         ON idf.parent = item.item_name

        #     WHERE sit.parent = %(item_code)s
        #     AND sit.parenttype = 'Item'
        #     AND sit.parentfield = 'custom_similar_item_table'
            
        #     """, {
        #         "item_code": item_code
        #     }, as_dict=True)

        # return items
        
        items = frappe.db.sql("""
            SELECT
                item.name,
                item.item_code,
                item.image,
                item.custom_catalogue_image AS custom_catalogue_image,
                item.custom_silver_image AS custom_silver_image,
                sn.name AS serial_no,
                sn.custom_bom_no AS serial_bom_no,
                
                # COALESCE(
                #     NULLIF(item.custom_catalogue_image, ''),
                #     NULLIF(item.custom_silver_image, '')
                # ) AS image,
                
                item.sketch_image,
                item.front_view AS cad_image,
        
                item.item_category,
                item.item_subcategory,
                item.setting_type,
                item.stylebio,
                item.variant_of,
        
                bom.name AS bom_name,
                bom.sub_setting_type1,
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
        
                idf.company
        
            FROM `tabItem` item
        
            # LEFT JOIN `tabBOM` bom
            #     ON bom.item = item.item_code
            #     AND bom.is_active = 1
            
            INNER JOIN `tabSerial No` AS sn
                ON sn.name = (
                    SELECT sn2.name
                    FROM `tabSerial No` AS sn2
                    WHERE sn2.item_code = item.item_code
                    ORDER BY sn2.creation ASC, sn2.name ASC
                    LIMIT 1
                )
            INNER JOIN `tabBOM` bom
                ON bom.name = sn.custom_bom_no
        
            LEFT JOIN `tabItem Default` idf
                ON idf.parent = item.item_name
        
            WHERE
                (
                    item.item_code = %(item_code)s
                    OR item.item_code IN (
                        SELECT sit.item_code
                        FROM `tabSimilar Item Table` sit
                        WHERE sit.parent = %(item_code)s
                          AND sit.parenttype = 'Item'
                          AND sit.parentfield = 'custom_similar_item_table'
                    )
                )
                # AND (
                #     NULLIF(item.custom_catalogue_image, '') IS NOT NULL
                #     OR
                #     NULLIF(item.custom_silver_image, '') IS NOT NULL
                # )
        
            GROUP BY item.item_code
            ORDER BY (item.item_code = %(item_code)s) DESC, item.item_code ASC
        """, {"item_code": item_code}, as_dict=True)
        
        # return items
        secure = SecureJSON()
        enc_data = secure.encrypt(items)
        return enc_data



SEARCH_MATCH_ALL = True       
USE_DEFAULT_BOM_ONLY = False  


def _default_bom_cond(alias="bom"):
    return f"AND {alias}.is_default = 1" if USE_DEFAULT_BOM_ONLY else ""


def get_customer_filter(search, values, customer_join, where_clause, page, page_size,order_by="item.creation DESC, item.item_code ASC",set_customer_cond="", has_customer=False):
    empty_response = {
        "db_data": [],
        "folder": {},
        "internal_catalog_folder": {},
        "total_count": 0,
        "has_more": False,
        "page": page,
        "page_size": page_size,
        "filters": None,
    }

    # ── Step 1: search se matching item codes ─────────────────────────
    search_terms = [x.strip() for x in (search or "").split(",") if x.strip()]

    if search_terms:
        search_conditions = []

        for i, term in enumerate(search_terms):
            values[f"search_{i}"] = f"%{term}%"
            values[f"exact_search_{i}"] = term
            search_conditions.append(f"""(
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
            )""")

        joiner = " AND " if SEARCH_MATCH_ALL else " OR "
        search_where = joiner.join(search_conditions)

        setting_filter = ""
        if "Open" in search_terms:
            setting_filter = "AND IFNULL(bom.sub_setting_type1, '') != 'Close-Open Setting'"
        elif "Close-Open Setting" in search_terms:
            setting_filter = """
                AND bom.sub_setting_type1 = 'Close-Open Setting'
                AND item.setting_type = 'Open'
            """
        elif "Nova Glow" in search_terms:
            setting_filter = "AND item.setting_type = 'Nova Glow'"

        customer_only = "AND tcm.name IS NOT NULL" if has_customer else ""

        rows = frappe.db.sql(
            f"""
            SELECT DISTINCT
                COALESCE(item.variant_of, item.item_code) AS item_code
            FROM `tabItem` item
            INNER JOIN `tabBOM` bom ON bom.item = item.item_code
            LEFT JOIN `tabDesign Attribute - Multiselect` dam ON dam.parent = item.item_code
            LEFT JOIN `tabCataloge Item Details` tci ON tci.item_code = item.name
            LEFT JOIN `tabCataloge Master` tcm ON tcm.name = tci.parent {customer_join}
            WHERE
                bom.bom_type = 'Finish Goods'
                AND bom.is_active = 1
                {_default_bom_cond()}
                {customer_only}
                AND ({search_where})
                {setting_filter}
            """,
            values,
            as_list=True,
        )

        matched_item_codes = list({row[0] for row in rows})

        if not matched_item_codes:
            return empty_response

        values["item_codes"] = tuple(matched_item_codes)
        where_clause += "\n AND COALESCE(item.variant_of, item.item_code) IN %(item_codes)s"

    # ── Step 2: full data ─────────────────────────────────────────────
    db_data = frappe.db.sql(
        f"""SELECT
                MIN(item.name) AS name,
                MIN(bom.name) AS bom,
                bom.sub_setting_type1,
                idf.company,
                tci.trending,
                tci.name AS catalog_item_details_name,
                tci.folder,
                tci.wishlist,
                tci.as_per_design,
                tci.job_work,
                tci.as_per_customized,
                tci.customized_data,
                tci.customer_gold,
                tci.customer_diamond,
                tci.customer_stone,
                uid.folder AS internal_catalog_folder,
                uid.wishlist AS internal_catalog_wishlist,
                item.creation,
                MIN(item.name) AS item_code,
                item.item_category,
                item.stylebio,
                MIN(item.image) AS image,
                item.custom_catalogue_image,
                item.sketch_image,
                item.front_view AS cad_image,
                CASE
                    WHEN item.front_view = item.image THEN 'CAD Image'
                    ELSE 'FG Image'
                END AS image_remark,

                CASE WHEN vc.variant_count > 1 THEN 1 ELSE 0 END AS rn,
                CASE WHEN set_check.is_set_item = 1 THEN 1 ELSE 0 END AS is_set_item,
                CASE WHEN similar_check.is_similar_item = 1 THEN 1 ELSE 0 END AS is_similar_item,

                item.item_subcategory,
                bom.tag_no,
                bom.diamond_quality,
                item.setting_type,

                FORMAT(bom.gross_weight,3) AS gross_metal_weight,
                FORMAT(bom.metal_and_finding_weight,3) AS net_metal_finding_weight,
                FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
                FORMAT(bom.other_weight,3) AS other_weight,
                FORMAT(bom.finding_weight_,3) AS finding_weight_,

                bom.metal_colour,
                bom.metal_touch AS bom_touch,
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
                GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size,

                GROUP_CONCAT(DISTINCT CASE WHEN td.design_attributes = 'Age Group' THEN td.design_attribute_value_1 END) AS age_group,
                GROUP_CONCAT(DISTINCT CASE WHEN td.design_attributes = 'Gender' THEN td.design_attribute_value_1 END) AS gender,
                GROUP_CONCAT(DISTINCT CASE WHEN td.design_attributes = 'Occasion' THEN td.design_attribute_value_1 END) AS occasion,
                GROUP_CONCAT(DISTINCT CASE WHEN td.design_attributes = 'Shapes' THEN td.design_attribute_value_1 END) AS shapes

            FROM `tabItem` AS item

            LEFT JOIN `tabCataloge Item Details` AS tci ON tci.item_code = item.name

            LEFT JOIN (
                SELECT
                    COALESCE(i.variant_of, i.item_code) AS group_key,
                    tci2.parent AS catalog_parent,
                    COUNT(DISTINCT i.item_code) AS variant_count
                FROM `tabItem` AS i
                INNER JOIN `tabBOM` AS b
                    ON i.item_code = b.item
                    AND b.bom_type = 'Finish Goods'
                    AND b.is_active = 1
                    {_default_bom_cond("b")}
                LEFT JOIN `tabCataloge Item Details` AS tci2 ON tci2.item_code = i.item_code
                GROUP BY COALESCE(i.variant_of, i.item_code), tci2.parent
            ) vc ON vc.group_key = COALESCE(item.variant_of, item.item_code)
                AND vc.catalog_parent = tci.parent

            LEFT JOIN (
                SELECT sit.parent AS item_code, 1 AS is_set_item
                FROM `tabSet Item Table` sit
                INNER JOIN `tabCataloge Item Details` cdi ON cdi.item_code = sit.item_code
                INNER JOIN `tabCataloge Master` cm ON cm.name = cdi.parent {set_customer_cond}
                WHERE sit.parenttype = 'Item'
                  AND sit.item_code != sit.parent
                GROUP BY sit.parent
            ) AS set_check ON set_check.item_code = item.item_code

            LEFT JOIN (
                SELECT sit.parent AS item_code, tci3.parent AS catalog_parent, 1 AS is_similar_item
                FROM `tabSimilar Item Table` sit
                INNER JOIN `tabCataloge Item Details` tci3 ON tci3.item_code = sit.item_code
                WHERE sit.parenttype = 'Item'
                GROUP BY sit.parent, tci3.parent
            ) AS similar_check
                ON similar_check.item_code = item.item_code
                AND similar_check.catalog_parent = tci.parent

            LEFT JOIN `tabCataloge Master` AS tcm ON tcm.name = tci.parent {customer_join}
            LEFT JOIN `tabUser Item Details` AS uid ON uid.item_code = item.name
            LEFT JOIN `tabInternal Catalog Master` AS icm ON icm.name = uid.parent
            LEFT JOIN `tabBOM` AS bom ON item.item_code = bom.item
            LEFT JOIN `tabDesign Attributes` AS td ON item.item_code = td.parent
            LEFT JOIN `tabBOM Metal Detail` AS mt ON bom.name = mt.parent
            LEFT JOIN `tabBOM Gemstone Detail` AS gd ON bom.name = gd.parent
            LEFT JOIN `tabBOM Diamond Detail` AS dd ON bom.name = dd.parent
            LEFT JOIN `tabBOM Finding Detail` AS fd ON bom.name = fd.parent
            LEFT JOIN `tabBOM Other Detail` AS od ON bom.name = od.parent
            LEFT JOIN `tabItem Default` AS idf ON item.item_name = idf.parent

            WHERE {where_clause}
            GROUP BY COALESCE(item.variant_of, item.item_code), tci.parent
            ORDER BY {order_by}
        """,
        values,
        as_dict=True,
    )

    # ── Multiselect attributes ────────────────────────────────────────
    item_codes_list = [row.item_code for row in db_data]
    if item_codes_list:
        db_res = frappe.db.sql(
            """
            SELECT parent, parentfield,
                   GROUP_CONCAT(design_attribute ORDER BY design_attribute SEPARATOR ', ') AS design_attributes
            FROM `tabDesign Attribute - Multiselect`
            WHERE parent IN %(data)s
            GROUP BY parent, parentfield
            """,
            {"data": tuple(item_codes_list)},
            as_dict=True,
        )

        attr_map = {}
        for r in db_res:
            field = r["parentfield"].replace("custom_", "")
            attr_map.setdefault(r["parent"], {})[field] = r["design_attributes"]

        for row in db_data:
            for key, value in attr_map.get(row.item_code, {}).items():
                row[key] = value
            row["custom_collection"] = row.get("custom_collection") or None
            row["custom_language"] = row.get("custom_language") or None
            row["custom_zodiac"] = row.get("custom_zodiac") or None
            row["custom_animalbirds"] = row.get("custom_animalbirds") or None
            row["custom_alphabetnumber"] = row.get("custom_alphabetnumber") or None
            row["religious"] = row.get("religious") or None

    total_count = len(db_data)

    # ── Pagination (hamesha page_size se slice) ───────────────────────
    offset = (page - 1) * page_size
    page_data = db_data[offset: offset + page_size]
    has_more = (offset + page_size) < total_count

    # ── Dynamic filters — sirf page 1 pe ──────────────────────────────
    filters = get_method(db_data) if page == 1 else None

    # ── Folder grouping ───────────────────────────────────────────────
    d, int_c_f = {}, {}
    for row in page_data:
        if row.folder:
            for name in row.folder.split(","):
                name = name.strip()
                if name:
                    d.setdefault(name, []).append(row)
        if row.internal_catalog_folder:
            for name in row.internal_catalog_folder.split(","):
                name = name.strip()
                if name:
                    int_c_f.setdefault(name, []).append(row)

    return {
        "db_data": page_data,
        "folder": d,
        "internal_catalog_folder": int_c_f,
        "total_count": total_count,
        "has_more": has_more,
        "page": page,
        "page_size": page_size,
        "filters": filters,
    }


@frappe.whitelist()
def customer_wise_item(selectedSubcategory=None, customer=None, user=None, metalType=None):
    allow_excel_permission = 0

    selectedSubcategory = frappe.form_dict.get("selectedSubcategory")
    itemCode            = frappe.form_dict.get("itemCode")
    itemCategory        = frappe.form_dict.get("itemCategory")
    metalType           = frappe.form_dict.get("metalType")
    customer            = frappe.form_dict.get("customer", customer)
    user                = frappe.form_dict.get("user", user)
    search              = frappe.form_dict.get("search")

    # ── Pagination params ──────────────────────────────────────────────────
    page_param = frappe.form_dict.get("page")
    if page_param is None:
        return {"db_data": [], "folder": {}, "internal_catalog_folder": {}}

    page      = int(page_param)
    page_size = int(frappe.form_dict.get("page_size", 48))
    is_filter = int(frappe.form_dict.get("is_filter", 0) or 0)

    # ── WHERE clause ───────────────────────────────────────────────────────

    where_clause = """
    idf.company = 'Gurukrupa Export Private Limited'
    AND bom.bom_type = 'Finish Goods'
    AND bom.name IS NOT NULL
    AND bom.is_active = 1
    # AND bom.is_default = 1
    """

    if selectedSubcategory:
        where_clause += f" AND item.item_subcategory = {frappe.db.escape(selectedSubcategory)} "
    if metalType:
        where_clause += f" AND bom.metal_type = {frappe.db.escape(metalType)} "
    if customer:
        where_clause += f" AND tcm.customer = {frappe.db.escape(customer)} "
        allow_excel_permission = frappe.db.get_value(
            "Cataloge Master", {"customer": customer}, "allow_excel_permission"
        ) or 0
    if user:
        where_clause += f" AND icm.user = {frappe.db.escape(user)} "
    if itemCode:
        where_clause += f" AND item.item_code = {frappe.db.escape(itemCode)} "
    if itemCategory:
        where_clause += f" AND item.item_category = {frappe.db.escape(itemCategory)} "

    customer_join = f"AND tcm.customer = {frappe.db.escape(customer)}" if customer else ""

    # set_check ke liye: customer ho to sirf usi ke catalogue ke set items gino
    set_customer_cond = f"AND cm.customer = {frappe.db.escape(customer)}" if customer else ""

    values = {}

    # ── is_filter = 1  →  search/filter flow ──────────────────────────────
    if is_filter == 1:
        result = get_customer_filter(search, values, customer_join, where_clause, page, page_size)
        result["allow_excel_permission"] = allow_excel_permission
        return result

    # ── Normal flow ────────────────────────────────────────────────────────
    db_data = frappe.db.sql(
        f"""SELECT
                MIN(item.name) AS name,
                MIN(bom.name) AS bom,
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
                MIN(item.name) AS item_code,
                item.item_category,
                item.stylebio,
                MIN(item.image) AS image,
                item.custom_catalogue_image,
                item.sketch_image,
                item.front_view as cad_image,
                CASE
                    WHEN item.front_view = item.image THEN 'CAD Image'
                    ELSE 'FG Image'
                END AS image_remark,
                CASE WHEN vc.variant_count > 1 THEN 1 ELSE 0 END AS rn,
                CASE WHEN set_check.is_set_item = 1 THEN 1 ELSE 0 END AS is_set_item,
                CASE WHEN similar_check.is_similar_item = 1 THEN 1 ELSE 0 END AS is_similar_item,
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
                GROUP_CONCAT(DISTINCT item.name ORDER BY item.creation ASC) as variant_name,
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
                GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size,
                GROUP_CONCAT(DISTINCT CASE WHEN td.design_attributes = 'Age Group' THEN td.design_attribute_value_1 END) AS age_group,
                GROUP_CONCAT(DISTINCT CASE WHEN td.design_attributes = 'Gender' THEN td.design_attribute_value_1 END) AS gender,
                GROUP_CONCAT(DISTINCT CASE WHEN td.design_attributes = 'Occasion' THEN td.design_attribute_value_1 END) AS occasion,
                GROUP_CONCAT(DISTINCT CASE WHEN td.design_attributes = 'Shapes' THEN td.design_attribute_value_1 END) AS shapes
            FROM `tabItem` AS item
            LEFT JOIN `tabCataloge Item Details` AS tci ON tci.item_code = item.name
            LEFT JOIN (
                SELECT
                    COALESCE(i.variant_of, i.item_code) AS group_key,
                    tci2.parent AS catalog_parent,
                    COUNT(DISTINCT i.item_code) AS variant_count,
                    MAX(tci2.as_per_design) AS as_per_design,
                    MAX(tci2.job_work) AS job_work,
                    MAX(tci2.as_per_customized) AS as_per_customized
                FROM `tabItem` AS i
                INNER JOIN `tabBOM` AS b ON i.item_code = b.item AND b.bom_type = 'Finish Goods' AND b.is_active = 1 AND b.is_default = 1
                LEFT JOIN `tabCataloge Item Details` AS tci2 ON tci2.item_code = i.item_code
                LEFT JOIN `tabCataloge Master` AS tcm2 ON tcm2.name = tci2.parent
                GROUP BY COALESCE(i.variant_of, i.item_code), tci2.parent
            ) vc ON vc.group_key = COALESCE(item.variant_of, item.item_code) AND vc.catalog_parent = tci.parent

            LEFT JOIN (
                SELECT sit.parent AS item_code, 1 AS is_set_item
                FROM `tabSet Item Table` sit
                INNER JOIN `tabCataloge Item Details` cdi ON cdi.item_code = sit.item_code
                INNER JOIN `tabCataloge Master` cm ON cm.name = cdi.parent {set_customer_cond}
                WHERE sit.parenttype = 'Item'
                  AND sit.item_code != sit.parent
                GROUP BY sit.parent
            ) AS set_check ON set_check.item_code = item.item_code

            LEFT JOIN (
                SELECT sit.parent AS item_code, tci.parent AS catalog_parent, CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END AS is_similar_item
                FROM `tabSimilar Item Table` sit
                INNER JOIN `tabCataloge Item Details` tci ON tci.item_code = sit.item_code
                WHERE sit.parenttype = 'Item'
                GROUP BY sit.parent, tci.parent
            ) AS similar_check ON similar_check.item_code = item.item_code AND similar_check.catalog_parent = tci.parent
            LEFT JOIN `tabCataloge Master` AS tcm ON tcm.name = tci.parent
            LEFT JOIN `tabUser Item Details` AS uid ON uid.item_code = item.name
            LEFT JOIN `tabInternal Catalog Master` AS icm ON icm.name = uid.parent
            LEFT JOIN `tabBOM` AS bom ON item.item_code = bom.item
            LEFT JOIN `tabDesign Attributes` AS td ON item.item_code = td.parent
            LEFT JOIN `tabBOM Metal Detail` AS mt ON bom.name = mt.parent
            LEFT JOIN `tabBOM Gemstone Detail` AS gd ON bom.name = gd.parent
            LEFT JOIN `tabBOM Diamond Detail` AS dd ON bom.name = dd.parent
            LEFT JOIN `tabBOM Finding Detail` AS fd ON bom.name = fd.parent
            LEFT JOIN `tabBOM Other Detail` AS od ON bom.name = od.parent
            LEFT JOIN `tabItem Default` AS idf ON item.item_name = idf.parent
            WHERE {where_clause}
            GROUP BY COALESCE(item.variant_of, item.item_code), tci.parent
            ORDER BY MIN(item.name) DESC
        """,
        as_dict=True,
    )

    # ── Multiselect attributes ─────────────────────────────────────────────
    item_codes_list = [row.item_code for row in db_data]
    if item_codes_list:
        db_res = frappe.db.sql("""
            SELECT parent, parentfield,
            GROUP_CONCAT(design_attribute ORDER BY design_attribute SEPARATOR ', ') AS design_attributes
            FROM `tabDesign Attribute - Multiselect`
            WHERE parent IN %(data)s
            GROUP BY parent, parentfield
        """, {"data": tuple(item_codes_list)}, as_dict=True)

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
            row["custom_collection"]     = row.get("custom_collection") or None
            row["custom_language"]       = row.get("custom_language") or None
            row["custom_zodiac"]         = row.get("custom_zodiac") or None
            row["custom_animalbirds"]    = row.get("custom_animalbirds") or None
            row["custom_alphabetnumber"] = row.get("custom_alphabetnumber") or None
            row["religious"]             = row.get("religious") or None

    total_count = len(db_data)

    # ── Pagination ─────────────────────────────────────────────────────────
    if total_count > page_size:
        offset = (page - 1) * page_size
        page_data = db_data[offset: offset + page_size]
        has_more = (offset + page_size) < total_count
    else:
        page_data = db_data
        has_more = False

    # ── Dynamic filters — sirf page 1 pe ──────────────────────────────────
    filters = get_method(db_data) if page == 1 else None

    # ── Folder grouping ────────────────────────────────────────────────────
    d = {}
    int_c_f = {}
    for row in page_data:
        if row.folder:
            for fd in row.folder.split(","):
                fd = fd.strip()
                if fd:
                    if fd not in d:
                        d[fd] = []
                    d[fd].append(row)
        if row.internal_catalog_folder:
            for fd in row.internal_catalog_folder.split(","):
                fd = fd.strip()
                if fd:
                    if fd not in int_c_f:
                        int_c_f[fd] = []
                    int_c_f[fd].append(row)

    data = {
        "db_data":                 page_data,
        "allow_excel_permission":  allow_excel_permission,
        "folder":                  d,
        "internal_catalog_folder": int_c_f,
        "total_count":             total_count,
        "has_more":                has_more,
        "page":                    page,
        "page_size":               page_size,
        "filters":                 filters,
    }
    secure = SecureJSON()
    enc_data = secure.encrypt(data)
    return enc_data


@frappe.whitelist()
def get_customers_attribute_data(customer):

    sales_type = frappe.get_all(
        "Sales Type Multiselect",              
        filters={"parent": customer},
        pluck="sales_type"        
    )

    setting_type = frappe.get_all(
        "Attribute Value",
        filters={"is_setting_type": 1},
        pluck="name"
    )
    setting_type = sorted(setting_type)
    setting_type_data = [{"setting_type": name} for name in setting_type]

    # Metal Criteria
    metal_touch = frappe.get_all(
        "Metal Criteria",
        filters={"parent": customer},
        pluck="metal_touch"
    )
    metal_touch = sorted(metal_touch)
    metal_touch_data = [{"metal_touch": name} for name in metal_touch]

    # Customer Diamond Grade
    catalog_master = frappe.get_value(
        "Cataloge Master",
        {"customer": customer},
        "name"
    )

    diamond_quality_data = []

    if catalog_master:
        catalog_doc = frappe.get_doc(
            "Cataloge Master",
            catalog_master
        )

        cust_dia = frappe.get_all(
            "Customer Diamond Grade",
            filters={"parent": customer},
            pluck="diamond_quality"
        )

        for row in catalog_doc.diamond_quality:
            if row.diamond_quality in cust_dia:
                diamond_quality_data.append({
                    "diamond_quality": row.diamond_quality
                })

    stone_excluded_values = [
        "1 Mukhi", "2 Mukhi", "3 Mukhi", "4 Mukhi",
        "5 Mukhi", "6 Mukhi", "7 Mukhi", "8 Mukhi",
        "9 Mukhi", "10 Mukhi", "Beeds", "Trillion"
    ]

    stone_shape = frappe.get_all(
        "Attribute Value",
        filters={"is_stone_shape": 1},
        pluck="name"
    )
    stone_shape = [
        name for name in stone_shape
        if name not in stone_excluded_values
    ]
    stone_shape = sorted(stone_shape)

    diamond_stone_shape = [
        {"stone_shape": name}
        for name in stone_shape
    ]

    gemstone_stone = frappe.get_all(
        "Attribute Value",
        filters={"is_stone_shape": 1},
        pluck="name"
    )
    gemstone_stone = sorted(gemstone_stone)

    gemstone_stone_data = [
        {"gemstone_shape": name}
        for name in gemstone_stone
    ]

    metal_color = frappe.get_all(
        "Attribute Value",
        filters={"is_metal_colour": 1},
        pluck="name"
    )
    metal_color = sorted(metal_color)

    metal_color_data = [
        {"metal_color": name}
        for name in metal_color
    ]

    finding_sub_category = frappe.get_all(
        "Attribute Value",
        filters={"is_finding_type": 1},
        pluck="name"
    )
    finding_sub_category = sorted(finding_sub_category)

    finding_subcategory_data = [
        {"finding_sub_category": name}
        for name in finding_sub_category
    ]

    # Occasion
    occasion = frappe.get_all(
        "Item Attribute Value",
        filters={"parent": "Occasion"},
        pluck="attribute_value"
    )
    occasion = sorted(occasion)

    occasion_data = [
        {"occasion": name}
        for name in occasion
    ]

    # Age Group
    age_group = frappe.get_all(
        "Item Attribute Value",
        filters={"parent": "Age Group"},
        pluck="attribute_value"
    )
    age_group = sorted(age_group)

    age_group_data = [
        {"age_group": name}
        for name in age_group
    ]

    # Gender
    gender = frappe.get_all(
        "Attribute Value",
        filters={"parent_attribute_value": "Gender"},
        pluck="name"
    )
    gender = sorted(gender)

    gender_data = [
        {"gender": name}
        for name in gender
    ]

    # Collection
    collection = frappe.get_all(
        "Attribute Value",
        filters={"parent_attribute_value": "Collection"},
        pluck="name"
    )
    collection = sorted(collection)

    collection_data = [
        {"collection": name}
        for name in collection
    ]

    # Rhodium
    rhodium = frappe.get_doc(
        "Item Attribute",
        "Rhodium"
    )

    rhodium_data = [
        {"rhodium": row.attribute_value}
        for row in rhodium.item_attribute_values
    ]

    data = {
        "sales_type": sales_type,
        "setting_types": setting_type_data,
        "metal_touch": metal_touch_data,
        "diamond_quality": diamond_quality_data,
        "metal_color": metal_color_data,
        "diamond_stone_shape": diamond_stone_shape,
        "gemstone_stone_data": gemstone_stone_data,
        "occasion": occasion_data,
        "finding_subcategory_data": finding_subcategory_data,
        "age_group": age_group_data,
        "gender_data": gender_data,
        "collection_data": collection_data,
        "rhodium": rhodium_data
    }
    secure = SecureJSON()
    enc_data = secure.encrypt(data)
    return enc_data


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
    data = {
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
    secure = SecureJSON()
    enc_data = secure.encrypt(data)
    return enc_data


@frappe.whitelist()
def get_catalogue_collection_item_data(selectedSubcategory, itemCode):
    selectedSubcategory = frappe.form_dict.get("item_subcategory")
    itemCode = frappe.form_dict.get("itemCode") 

    where_clause = """
        idf.company = 'Gurukrupa Export Private Limited'
        # AND (bom.bom_type = 'Finish Goods' OR bom.bom_type = 'Template')
    """

    if selectedSubcategory:
        where_clause = where_clause + f" AND item.item_subcategory = '{selectedSubcategory}' "
    
    if itemCode:
        where_clause = where_clause + f" AND item.item_code = '{itemCode}' " 

    db_data = frappe.db.sql(
        f""" SELECT
                item.name,
                bom.name AS bom,
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
def get_customer_wishlist_items(customer=None, user_type=None, user=None):

    if user_type == "customer":
        customer = frappe.form_dict.get("customer") or customer
    elif user_type == "user":
        user = frappe.form_dict.get("user") or user

    # where_clause = """
    # idf.company = 'Gurukrupa Export Private Limited'
    # AND bom.bom_type = 'Finish Goods'
    # AND bom.name IS NOT NULL
    # AND bom.is_active = 1
    # # AND bom.is_default = 1
    # AND tci.wishlist = 1
    # """

    # if customer:
    #     where_clause += f" AND tcm.customer = '{customer}' "
    # if user:
    #     where_clause += f" AND tcm.user = '{user}' "
    
    where_clause = """
    idf.company = 'Gurukrupa Export Private Limited'
    AND bom.bom_type = 'Finish Goods'
    AND bom.name IS NOT NULL
    AND bom.is_active = 1
    AND tci.wishlist = 1
    """
    params = {}
    
    if customer:
        where_clause += " AND tcm.customer = %(customer)s "
        params["customer"] = customer
    if user:
        where_clause += " AND tcm.user = %(user)s "
        params["user"] = user

    # frappe.throw(where_clause)

    db_data = frappe.db.sql(
        f"""SELECT
                MIN(item.name) AS name,
                MIN(bom.name) AS bom,
                idf.company,
                tci.trending,
                tci.name as catalog_item_details_name,
                tci.folder,
                tci.wishlist,
                tcm.allow_excel_permission,
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
                MIN(item.name) AS item_code,
                item.item_category,
                item.stylebio,
                MIN(item.image) AS image,
                item.custom_catalogue_image,
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
                `tabCataloge Item Details` AS tci ON tci.item_code = item.name
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
                    # AND b.is_default = 1
                LEFT JOIN `tabCataloge Item Details` AS tci2 ON tci2.item_code = i.item_code
                LEFT JOIN `tabCataloge Master` AS tcm2 ON tcm2.name = tci2.parent
                GROUP BY COALESCE(i.variant_of, i.item_code), tci2.parent
            ) vc ON vc.group_key = COALESCE(item.variant_of, item.item_code)
                 AND vc.catalog_parent = tci.parent
            LEFT JOIN (
                SELECT
                    sit.parent AS item_code,
                    CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END AS is_set_item
                FROM `tabSet Item Table` sit
                INNER JOIN `tabCataloge Item Details` tci ON tci.item_code = sit.item_code
                WHERE sit.parenttype = 'Item'
                GROUP BY sit.parent
            ) AS set_check ON set_check.item_code = item.item_code
            LEFT JOIN (
                SELECT
                    sit.parent AS item_code,
                    tci.parent AS catalog_parent,
                    CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END AS is_similar_item
                FROM `tabSimilar Item Table` sit
                INNER JOIN `tabCataloge Item Details` tci ON tci.item_code = sit.item_code
                WHERE sit.parenttype = 'Item'
                GROUP BY sit.parent, tci.parent
            ) AS similar_check
                ON similar_check.item_code = item.item_code
                AND similar_check.catalog_parent = tci.parent
            LEFT JOIN `tabCataloge Master` AS tcm ON tcm.name = tci.parent
            LEFT JOIN `tabUser Item Details` AS uid ON uid.item_code = item.name
            LEFT JOIN `tabInternal Catalog Master` AS icm ON icm.name = uid.parent
            LEFT JOIN `tabBOM` AS bom ON item.item_code = bom.item
            LEFT JOIN `tabDesign Attributes` AS td ON item.item_code = td.parent
            LEFT JOIN `tabBOM Metal Detail` AS mt ON bom.name = mt.parent
            LEFT JOIN `tabBOM Gemstone Detail` AS gd ON bom.name = gd.parent
            LEFT JOIN `tabBOM Diamond Detail` AS dd ON bom.name = dd.parent
            LEFT JOIN `tabBOM Finding Detail` AS fd ON bom.name = fd.parent
            LEFT JOIN `tabBOM Other Detail` AS od ON bom.name = od.parent
            LEFT JOIN `tabItem Default` AS idf ON item.item_name = idf.parent
            WHERE
                {where_clause}
            GROUP BY
                COALESCE(item.variant_of, item.item_code), tci.parent, tci.name  
            ORDER BY
                MIN(item.name) DESC
        """,
                params,          
        as_dict=True
    )

    d = {}
    for row in db_data:
        if row.folder:
            for fd in row.folder.split(","):
                if fd not in d:
                    d[fd] = []
                d[fd].append(row)



    secure = SecureJSON()
    
    enc_data = secure.encrypt(
            {
            "db_data": db_data,
            "total": len(db_data),
            "folder": d
        }
    ) 
    
    return enc_data

    # return {
    #     "db_data": db_data,
    #     "total": len(db_data),
    #     "folder": d
    # }
