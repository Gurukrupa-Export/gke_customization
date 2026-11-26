import frappe
from frappe import _
from gke_customization.gke_catalog.api.notifications import notify_user
from gke_customization.gke_catalog.api.wishlist_download import get_method

from gke_customization.gke_catalog.api.encryption_response import SecureJSON

@frappe.whitelist()
def category_count(user_type, customer=None):
    # Same 5-minute cache as subcategory_count: the counts change rarely and the
    # staff query counts every item (~0.3 s).
    cache_key = f"portal_cat_count_{user_type}_{customer if user_type == 'Customer' else ''}"
    cached = frappe.cache().get_value(cache_key)
    if cached:
        return cached
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
        if result:
            frappe.cache().set_value(cache_key, result, expires_in_sec=300)
        return result

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
        is_customer = user_type == "Customer"

        cache_key = (
            f"subcat_count_v4_{categoryName}_{customer}"
            if is_customer else
            f"subcat_count_v4_{categoryName}"
        )
        cached = frappe.cache().get_value(cache_key)
        if cached:
            return SecureJSON().encrypt(cached)

        # ── FROM + WHERE: exact like category_count  ────────────────────
        if is_customer:
            base_sql = """
                FROM `tabCataloge Item Details` AS tci
                INNER JOIN `tabCataloge Master` AS tcm
                    ON tcm.name = tci.parent
                    AND tcm.customer = %(customer)s
                INNER JOIN `tabItem` AS ti
                    ON ti.name = tci.item_code
                INNER JOIN `tabAttribute Value` AS tavc
                    ON tavc.name = ti.item_category
                    AND tavc.is_category = 1
                INNER JOIN `tabBOM` AS bom
                    ON bom.item = ti.name
                    AND bom.is_active = 1
                    AND bom.bom_type = 'Finish Goods'
                LEFT JOIN `tabAttribute Value` AS tav
                    ON tav.name = ti.item_subcategory
                    AND tav.is_subcategory = 1
                WHERE
                    ti.item_category = %(cat)s
                    AND EXISTS (
                        SELECT 1 FROM `tabSerial No` AS sn0
                        WHERE sn0.item_code = ti.name
                    )
            """
        else:
            base_sql = """
                FROM `tabItem` AS ti
                INNER JOIN `tabAttribute Value` AS tavc
                    ON tavc.name = ti.item_category
                    AND tavc.is_category = 1
                INNER JOIN `tabItem Default` AS idf
                    ON idf.parent = ti.name
                    AND idf.company = 'Gurukrupa Export Private Limited'
                LEFT JOIN `tabAttribute Value` AS tav
                    ON tav.name = ti.item_subcategory
                    AND tav.is_subcategory = 1
                WHERE
                    ti.item_category = %(cat)s
                    AND ti.item_group != 'Design DNU'
                    AND ti.disabled = 0
                    AND EXISTS (
                        SELECT 1 FROM `tabBOM` AS bom
                        WHERE bom.item = ti.name
                        AND bom.is_active = 1
                    )
                    AND EXISTS (
                        SELECT 1 FROM `tabSerial No` AS sn0
                        WHERE sn0.item_code = ti.name
                    )
            """

        values = {"customer": customer, "cat": categoryName}

        # ── STEP 1: Count ────────────────────────────────────────────────
        result = frappe.db.sql(f"""
            SELECT
                ti.item_category,
                IFNULL(tav.name, 'Other') AS item_subcategory,
                COUNT(DISTINCT IFNULL(ti.variant_of, ti.name)) AS item_count,
                COUNT(DISTINCT CASE WHEN se.status = 'Active' THEN se.name END) AS serial_count
            {base_sql.replace("WHERE", '''
                LEFT JOIN `tabSerial No` AS se
                    ON se.item_code = ti.name
                WHERE''', 1)}
            GROUP BY ti.item_category, IFNULL(tav.name, 'Other')
        """, values, as_dict=True)

        # "Other" sabse last me, baaki A-Z
        result.sort(key=lambda r: (r.item_subcategory == "Other", r.item_subcategory))

        # ── STEP 2: Har subcategory ki latest image (same filters) ───────
        if result:
            image_rows = frappe.db.sql(f"""
                SELECT
                    IFNULL(tav.name, 'Other') AS item_subcategory,
                    ti.image AS first_image,
                    ti.custom_catalogue_image,
                    ti.custom_silver_image
                {base_sql}
                    AND ti.image IS NOT NULL
                    AND ti.front_view IS NOT NULL
                    AND ti.image != ti.front_view
                ORDER BY ti.creation DESC
            """, values, as_dict=True)

            image_map = {}
            for row in image_rows:
                image_map.setdefault(row.item_subcategory, row)

            for row in result:
                img = image_map.get(row.item_subcategory) or {}
                row["first_image"] = img.get("first_image")
                row["custom_catalogue_image"] = img.get("custom_catalogue_image")
                row["custom_silver_image"] = img.get("custom_silver_image")

        frappe.cache().set_value(cache_key, result, expires_in_sec=300)
        # return result
        secure = SecureJSON()
        enc_data = secure.encrypt(result)
        return enc_data

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "subcategory_count Error")
        return {"error": str(e)}