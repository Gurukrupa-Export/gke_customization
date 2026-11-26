import frappe
from frappe import _
import json

@frappe.whitelist()
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
        collection=collection,
    )
    
    
    #mansi 25-11-2026
    catalogue_names = [c["name"] for c in catalogue_list]
    
    if catalogue_names:
            # child table se items
            child_filters = {"parent": ["in", catalogue_names]}
            if collection:
                child_filters["collection"] = collection
    
            child_rows = frappe.get_all(
                "Catalogue Collection Details",
                filters=child_filters,
                fields=["item_code"],
            )
            item_codes = list({r["item_code"] for r in child_rows if r.get("item_code")})
    
            image_map = {}
            bom_map = {}
            if item_codes:
                images = frappe.get_all(
                    "Item",
                    filters={"name": ["in", item_codes]},
                    fields=[
                        "name", 
                        "custom_catalogue_image", 
                        "custom_silver_image",
                    ],
                )
                image_map = {i["name"]: i for i in images}
                
                bom_fields = [
                    "gross_weight", "metal_and_finding_weight", "total_diamond_weight_in_gms",
                    "total_diamond_pcs", "diamond_quality", "metal_touch", "metal_colour", "setting_type", 
                    "metal_type", "total_gemstone_pcs", "gemstone_weight",
                ]

                boms = frappe.get_all(
                    "BOM",
                    filters={
                        "item": ["in", item_codes],
                        "is_active": 1,
                        "docstatus": 1,
                    },
                    fields=["name as bom", "item"] + bom_fields,
                    order_by="is_default desc, creation desc",
                )
                for b in boms:
                    if b["item"] not in bom_map:
                        bom_map[b["item"]] = b
                        
            # if isinstance(data, list):
            #     for row in data:
            #         img = image_map.get(row.get("item_code"), {})
            #         row["custom_catalogue_image"] = img.get("custom_catalogue_image")
            #         row["custom_silver_image"] = img.get("custom_silver_image")
            

            catalogues = data if isinstance(data, list) else [data]

            for cat in catalogues:
                if not isinstance(cat, dict):
                    continue
                for row in cat.get("catalogue_collection_details", []):
                    code = row.get("item_code")
                    img = image_map.get(code, {})
                    bom = bom_map.get(code, {})

                    row["custom_catalogue_image"] = img.get("custom_catalogue_image")
                    row["custom_silver_image"] = img.get("custom_silver_image")

                    row["bom"] = bom.get("bom")
                    for f in bom_fields:
                        row[f] = bom.get(f)

        #mansi 25-11-2026
    # return {
        # "success": True,
        # "data": data,
    # }
    return data


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
                        "custom_catalogue_image":  item.get("custom_catalogue_image") if item else "",   #mansi 25-11-2026 
                        "item_category": item.get("item_category") if item else "",
                        "item_subcategory": item.get("item_subcategory") if item else "",
                    })

        final_data.append({
            "customer": doc.customer,
            "catalogue_collection_details": rows,
        })
    return final_data

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
    
    
    
#mansi 25-11-2026   
@frappe.whitelist()
def get_catalogue_collection_item_data(selectedSubcategory, itemCode):
    selectedSubcategory = frappe.form_dict.get("item_subcategory")
    itemCode = frappe.form_dict.get("itemCode") 

    where_clause = """
        item.item_group != 'Design DNU' #bhavika 25-11-2026
        AND item.disabled = 0 #bhavika 25-11-2026
        idf.company = 'Gurukrupa Export Private Limited'
        # AND (bom.bom_type = 'Finish Goods' OR bom.bom_type = 'Template')
    """

    if selectedSubcategory:
        where_clause = where_clause + f" AND item.item_subcategory = '{selectedSubcategory}' "
    
    if itemCode:
        where_clause = where_clause + f" AND item.item_code = {frappe.db.escape(itemCode, percent=False)} " 

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