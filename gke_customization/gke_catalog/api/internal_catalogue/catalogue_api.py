# from turtle import update
from warnings import filters
from attr import field
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

from gke_customization.gke_catalog.api.encryption_response import SecureJSON    # shubham encrypted fun

from cryptography.fernet import Fernet

# ---------------------------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def category_count(user_type):
    try:

        sql_query = """
            SELECT
                item.item_category,

                COUNT(
                    DISTINCT IFNULL(
                        item.variant_of,
                        item.item_code
                    )
                ) AS item_count

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
                    SELECT 1
                    FROM `tabBOM` AS bom
                    WHERE
                        bom.item = item.item_code
                        AND bom.is_active = 1
                )

            GROUP BY
                item.item_category

            ORDER BY
                item.item_category
        """

        result = frappe.db.sql(
            sql_query,
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

# ---------------------------------------------------------------------------


@frappe.whitelist(allow_guest=True)
def subcategory_count(categoryName, user_type, customer=None):
    try:
        # Redis Cache
        cache_key = f"subcat_count_{categoryName}"
        cached = frappe.cache().get_value(cache_key)

        if cached:
            return cached

        # STEP 1
        count_query = """
            SELECT
                products.item_subcategory,

                COUNT(*) AS item_count,

                (
                    SELECT COUNT(DISTINCT se.name)
                    FROM `tabSerial No` AS se
                    INNER JOIN `tabItem` AS si
                        ON si.item_code = se.item_code
                    WHERE
                        se.status = 'Active'
                        AND si.item_subcategory = products.item_subcategory
                        AND si.item_category = %s
                        AND si.item_group != 'Design DNU'
                        AND si.disabled = 0
                ) AS serial_count

            FROM (
                SELECT
                    item.item_code,
                    item.item_subcategory,
                    item.variant_of

                FROM `tabItem` AS item

                INNER JOIN `tabItem Default` AS idf
                    ON item.item_code = idf.parent
                    AND idf.company = 'Gurukrupa Export Private Limited'

                INNER JOIN `tabBOM` AS bom
                    ON item.item_code = bom.item
                    AND bom.is_active = 1

                WHERE
                    item.item_subcategory IS NOT NULL
                    AND item.item_category = %s
                    AND item.item_group != 'Design DNU'
                    AND item.disabled = 0

                GROUP BY
                    item.item_code,
                    item.variant_of,
                    item.item_subcategory
            ) AS products

            GROUP BY
                products.item_subcategory

            ORDER BY
                products.item_subcategory
        """

        result = frappe.db.sql(
            count_query,
            (
                categoryName,
                categoryName
            ),
            as_dict=True
        )

        # STEP 2
        if result:

            subcategories = list({
                row.item_subcategory
                for row in result
                if row.item_subcategory
            })

            if subcategories:

                image_rows = frappe.db.sql("""
                    SELECT
                        ti.item_subcategory,
                        ti.image AS first_image,
                        ti.custom_catalogue_image AS custom_catalogue_image

                    FROM `tabItem` ti

                    INNER JOIN `tabBOM` tb
                        ON tb.item = ti.name
                        AND tb.is_active = 1

                    INNER JOIN `tabItem Default` idf
                        ON ti.name = idf.parent
                        AND idf.company = 'Gurukrupa Export Private Limited'

                    WHERE
                        ti.item_category = %(cat)s
                        AND ti.item_subcategory IN %(subs)s
                        AND ti.item_group != 'Design DNU'
                        AND ti.disabled = 0

                        AND ti.image IS NOT NULL
                        AND ti.front_view IS NOT NULL
                        AND ti.image != ti.front_view

                    ORDER BY
                        ti.creation DESC
                """, {
                    "cat": categoryName,
                    "subs": tuple(subcategories)
                }, as_dict=True)

                image_map = {}

                for row in image_rows:
                    if row.item_subcategory not in image_map:
                        image_map[row.item_subcategory] = {
                            "first_image": row.first_image,
                            "custom_catalogue_image": row.custom_catalogue_image
                        }

                for row in result:

                    image_data = image_map.get(
                        row.item_subcategory,
                        {}
                    )

                    row["first_image"] = image_data.get(
                        "first_image"
                    )

                    row["custom_catalogue_image"] = image_data.get(
                        "custom_catalogue_image"
                    )

        frappe.cache().set_value(
            cache_key,
            result,
            expires_in_sec=300
        )

        return result

    except Exception as e:

        frappe.log_error(
            frappe.get_traceback(),
            "subcategory_count Error"
        )

        return {
            "error": str(e)
        }


@frappe.whitelist(allow_guest=True)
def catalogue_data(selectedSubcategory=None, itemCategory=None, itemCode=None,
                    metalType=None, company=None, customer=None):

    if selectedSubcategory is None:
        selectedSubcategory = frappe.form_dict.get("selectedSubcategory")

    if itemCode is None:
        itemCode = frappe.form_dict.get("itemCode")

    if metalType is None:
        metalType = frappe.form_dict.get("metalType")

    if itemCategory is None:
        itemCategory = frappe.form_dict.get("itemCategory")

    conditions = []
    values = {}

    if selectedSubcategory:
        conditions.append("item.item_subcategory = %(selectedSubcategory)s")
        values["selectedSubcategory"] = selectedSubcategory

    if metalType:
        conditions.append("bom.metal_type = %(metalType)s")
        values["metalType"] = metalType

    if company:
        conditions.append("idf.company = %(company)s")
        values["company"] = company
    else:
        conditions.append("idf.company = %(company)s")
        values["company"] = "Gurukrupa Export Private Limited"

    if itemCode:
        conditions.append("item.item_code = %(itemCode)s")
        values["itemCode"] = itemCode

    if itemCategory:
        conditions.append("item.item_category = %(itemCategory)s")
        values["itemCategory"] = itemCategory

    conditions.append("item.disabled = 0")
    conditions.append("item.item_group != 'Design DNU'")
    conditions.append("bom.is_active = 1")

    where_clause = " AND ".join(conditions)
    if customer:
        wishlist_case = "MAX(CASE WHEN tci.wishlist = 1 THEN 1 ELSE 0 END) AS wishlist"
        trending_case = "MAX(CASE WHEN tci.trending = 1 THEN 1 ELSE 0 END) AS trending"
        customer_join = "AND tcm.customer = %(customer)s"
        values["customer"] = customer
    else:
        wishlist_case = "0 AS wishlist"
        trending_case = "0 AS trending"
        customer_join = ""

    db_data = frappe.db.sql(
        f""" SELECT
                item.name,
                bom.name,
                idf.company,
                tci.trending,
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
                item.item_code = idf.parent
            WHERE
                {where_clause}
            GROUP BY
                item.item_code, item.variant_of
            ORDER BY
                item.name DESC
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
           
