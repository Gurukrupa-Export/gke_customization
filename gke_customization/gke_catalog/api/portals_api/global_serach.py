import frappe
from frappe import _

@frappe.whitelist()
def global_search(query=None, customer=None, user=None):
    if not query or len(query) < 2:
        return []

    like_query = f"%{query}%"
    values = {"like_query": like_query}

    # Design Attribute tab ke multiselect fields (Gender, Occasion, Shapes, ...)
    ms_clause = get_design_multiselect_clause()

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
                sn.name AS serial_no,
                sn.custom_bom_no AS serial_bom_no,
                (
                    SELECT GROUP_CONCAT(DISTINCT ms.design_attribute SEPARATOR ', ')
                    FROM `tabDesign Attribute - Multiselect` AS ms
                    WHERE ms.parent = item.name
                      AND ms.parentfield = 'custom_design_style'
                ) AS design_style,
                COALESCE(
                    NULLIF(item.custom_catalogue_image, ''),
                    NULLIF(item.custom_silver_image, '')
                ) AS custom_catalogue_image,
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
            -- CHANGED: BOM ab serial ke custom_bom_no se aa raha hai
            INNER JOIN `tabSerial No` AS sn
                ON sn.name = (
                    SELECT sn2.name
                    FROM `tabSerial No` AS sn2
                    WHERE sn2.item_code = item.item_code
                    ORDER BY sn2.creation ASC, sn2.name ASC
                    LIMIT 1
                )
            INNER JOIN `tabBOM` AS bom
                ON bom.name = sn.custom_bom_no
                AND bom.bom_type = 'Finish Goods'
            LEFT JOIN `tabItem Default` AS idf
                ON item.item_name = idf.parent
            WHERE
                idf.company = 'Gurukrupa Export Private Limited'
                AND (
                    item.item_code LIKE %(like_query)s
                    OR item.item_category LIKE %(like_query)s
                    OR item.item_subcategory LIKE %(like_query)s
                    OR EXISTS (
                        SELECT 1
                        FROM `tabDesign Attributes` AS da
                        WHERE da.parent = item.name
                          AND (
                              da.design_attributes LIKE %(like_query)s
                              OR da.design_attribute_value_1 LIKE %(like_query)s
                              OR da.design_attribute_value_2 LIKE %(like_query)s
                              OR da.design_attribute_value_3 LIKE %(like_query)s
                              OR da.design_attribute_value_4 LIKE %(like_query)s
                              OR da.design_attribute_value_5 LIKE %(like_query)s
                              OR da.design_attribute_value_6 LIKE %(like_query)s
                              OR da.design_attribute_value_7 LIKE %(like_query)s
                              OR da.design_attribute_value_8 LIKE %(like_query)s
                          )
                    )
                    OR (/*MS_CLAUSE*/)
                )
                # AND (
                #     NULLIF(item.custom_catalogue_image, '') IS NOT NULL
                #     OR
                #     NULLIF(item.custom_silver_image, '') IS NOT NULL
                # )
            ORDER BY item.item_subcategory, item.item_code
        """.replace("/*MS_CLAUSE*/", ms_clause), values, as_dict=True)

    # ----------------------------------------------------------------
    # USER
    # ----------------------------------------------------------------
    elif user:
        db_data = frappe.db.sql("""
            SELECT
                item.item_code,
                item.item_category,
                item.item_subcategory,
                sn.name AS serial_no,
                sn.custom_bom_no AS serial_bom_no,
                (
                    SELECT GROUP_CONCAT(DISTINCT ms.design_attribute SEPARATOR ', ')
                    FROM `tabDesign Attribute - Multiselect` AS ms
                    WHERE ms.parent = item.name
                      AND ms.parentfield = 'custom_design_style'
                ) AS design_style,
                COALESCE(
                    NULLIF(item.custom_catalogue_image, ''),
                    NULLIF(item.custom_silver_image, '')
                ) AS custom_catalogue_image,
                bom.metal_touch,
                bom.metal_colour,
                FORMAT(bom.gross_weight, 3) AS gross_metal_weight,
                FORMAT(bom.total_diamond_weight_in_gms, 3) AS total_diamond_weight_in_gms,
                bom.diamond_quality
            FROM `tabItem` AS item
            -- CHANGED: BOM ab serial ke custom_bom_no se aa raha hai
            INNER JOIN `tabSerial No` AS sn
                ON sn.name = (
                    SELECT sn2.name
                    FROM `tabSerial No` AS sn2
                    WHERE sn2.item_code = item.item_code
                    ORDER BY sn2.creation ASC, sn2.name ASC
                    LIMIT 1
                )
            INNER JOIN `tabBOM` AS bom
                ON bom.name = sn.custom_bom_no
                AND bom.bom_type = 'Finish Goods'
            INNER JOIN `tabItem Default` AS idf
                ON item.item_name = idf.parent
                AND idf.company = 'Gurukrupa Export Private Limited'
            WHERE
                item.item_group != 'Design DNU'
                AND (
                    item.item_code LIKE %(like_query)s
                    OR item.item_category LIKE %(like_query)s
                    OR item.item_subcategory LIKE %(like_query)s
                    OR EXISTS (
                        SELECT 1
                        FROM `tabDesign Attributes` AS da
                        WHERE da.parent = item.name
                          AND (
                              da.design_attributes LIKE %(like_query)s
                              OR da.design_attribute_value_1 LIKE %(like_query)s
                              OR da.design_attribute_value_2 LIKE %(like_query)s
                              OR da.design_attribute_value_3 LIKE %(like_query)s
                              OR da.design_attribute_value_4 LIKE %(like_query)s
                              OR da.design_attribute_value_5 LIKE %(like_query)s
                              OR da.design_attribute_value_6 LIKE %(like_query)s
                              OR da.design_attribute_value_7 LIKE %(like_query)s
                              OR da.design_attribute_value_8 LIKE %(like_query)s
                          )
                    )
                    OR (/*MS_CLAUSE*/)
                )
                # AND (
                #     NULLIF(item.custom_catalogue_image, '') IS NOT NULL
                #     OR
                #     NULLIF(item.custom_silver_image, '') IS NOT NULL
                # )
            ORDER BY item.item_subcategory, item.item_code
        """.replace("/*MS_CLAUSE*/", ms_clause), values, as_dict=True)

    else:
        return []

    # ----------------------------------------------------------------
    # Smart filter — NO LIMIT in SQL, Python handle
    # ----------------------------------------------------------------
    q_lower = query.lower()

    # Item code search detect karo
    is_item_code_search = any(
        (row.get("item_code") or "").lower().startswith(q_lower)
        for row in db_data
    )

    if is_item_code_search:
        # Item code search — exact matching items, max 8
        matched = [
            row for row in db_data
            if (row.get("item_code") or "").lower().startswith(q_lower)
        ]
        return matched[:8]
    else:
        # Category/Subcategory/Design attribute search — 1 per subcategory
        seen = set()
        final = []
        for row in db_data:
            sub = row.get("item_subcategory") or row.get("item_category") or ""
            if sub not in seen:
                final.append(row)
                seen.add(sub)
        return final
        # secure = SecureJSON()
        # enc_data = secure.encrypt(final)
        # return enc_data

    
DESIGN_MULTISELECT_LABELS = {
    "Age Group", "Language", "Alphabet/Number", "Occasion", "Animal/Birds",
    "Rhodium", "Collection", "Religious", "Design Style", "Shapes",
    "Gender", "Zodiac", "Lines & Rows",
}


def get_design_multiselect_clause():
    """Item ke Table MultiSelect fields ke liye EXISTS conditions banata hai.

    Fieldnames / doctype names frappe meta se aate hain (user input se nahi),
    isliye SQL injection ka risk nahi. User ki value sirf %(like_query)s se jaati hai.
    """
    meta = frappe.get_meta("Item")
    clauses = []

    for df in meta.get("fields", {"fieldtype": "Table MultiSelect"}):
        if df.label not in DESIGN_MULTISELECT_LABELS:
            continue

        child_meta = frappe.get_meta(df.options)
        link_df = next((f for f in child_meta.fields if f.fieldtype == "Link"), None)
        if not link_df:
            continue

        clauses.append(f"""
            EXISTS (
                SELECT 1 FROM `tab{df.options}` AS ms
                WHERE ms.parent = item.name
                  AND ms.parentfield = '{df.fieldname}'
                  AND ms.`{link_df.fieldname}` LIKE %(like_query)s
            )""")

    return " OR ".join(clauses) if clauses else "1=0"

