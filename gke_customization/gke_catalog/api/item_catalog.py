import frappe

@frappe.whitelist(allow_guest=True)
def merge_data():
    try:
        sql_query = """
             SELECT
                item.name,
                bom.name,
                idf.company,
                COUNT(distinct(tsn.name)) as stock_count,
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
                GROUP_CONCAT(DISTINCT item.name) as variant_name,
                GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
                GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,
                GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
                GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
                GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
                GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,
                GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
                GROUP_CONCAT(DISTINCT gd.setting_type) AS sub_setting_type,
                GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,
                GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
                GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
                GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
                GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
                GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,
                GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_sub_category,
                GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size
            FROM
                `tabItem` AS item
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
                `tabItem Default` AS idf
            ON
                item.item_name = idf.parent
            LEFT JOIN
                `tabSerial No` AS tsn
            ON
                item.item_name = tsn.item_code
            WHERE
                bom.bom_type = "Finish Goods" AND bom.is_active = 1 
            GROUP BY
                item.name, item.creation, item.item_code, item.item_category, item.image, item.item_subcategory, bom.tag_no,
                bom.gross_weight, bom.metal_and_finding_weight, bom.total_diamond_weight_in_gms, bom.other_weight,
                bom.finding_weight_, bom.total_gemstone_weight_in_gms, item.item_name,item.variant_of
            ORDER BY
                item.name DESC;
        """
        
        result = frappe.db.sql(sql_query, as_dict=True)
        
        return result

    except Exception as e:
        return {"error": str(e)}

@frappe.whitelist()
def get_item_category():
    # Your code to fetch attribute values where is_category is checked
    itm_category = frappe.get_all("Attribute Value", filters={"is_category": 1})
    
    # Modify the structure of the list
    modified_data = [{"item_category": item["name"]} for item in itm_category]

    # Sort the modified_data list in ascending order by the "item_category" attribute
    modified_data = sorted(modified_data, key=lambda x: x["item_category"])
    
    return modified_data

@frappe.whitelist()
def get_item_subcategory():
    # Your code to fetch attribute values where is_category is checked
    itm_subcategory = frappe.get_all("Attribute Value", filters={"is_subcategory": 1})
    
    # Modify the structure of the list
    modified_data = [{"item_subcategory": item["name"]} for item in itm_subcategory]

    # Sort the modified_data list in ascending order by the "item_subcategory" attribute
    modified_data = sorted(modified_data, key=lambda x: x["item_subcategory"])
    
    return modified_data

@frappe.whitelist()
def get_setting_type():
    # Your code to fetch attribute values where is_setting_type is checked
    setting_type = frappe.get_all("Attribute Value", filters={"is_setting_type": 1})
    
    # Modify the structure of the list
    modified_data = [{"setting_type": item["name"]} for item in setting_type]

    # Sort the modified_data list in ascending order by the "setting_type" attribute
    modified_data = sorted(modified_data, key=lambda x: x["setting_type"])
    
    return modified_data

@frappe.whitelist()
def get_finding_subcategory():
    # Your code to fetch attribute values where is_setting_type is checked
    finding_sub_category = frappe.get_all("Attribute Value", filters={"is_finding_type": 1})
    
    # Modify the structure of the list
    modified_data = [{"finding_subcategory": item["name"]} for item in finding_sub_category]

    # Sort the modified_data list in ascending order by the "finding_sub_category" attribute
    modified_data = sorted(modified_data, key=lambda x: x["finding_subcategory"])
    
    return modified_data

@frappe.whitelist()
def get_metal_type():
    # Your code to fetch attribute values where is_setting_type is checked
    metal_type = frappe.get_all("Attribute Value", filters={"is_metal_type": 1})
    
    excluded_values = ["Genia-221","Lux-101","Lux-142","Lux-142 ProGold","Lux-160","Lux-173","Lux-189","Refined Gold"]
    # Modify the structure of the list
    modified_data = [{"metal_type": item["name"]} for item in metal_type if item["name"] not in excluded_values]

    # Sort the modified_data list in ascending order by the "metal_type" attribute
    modified_data = sorted(modified_data, key=lambda x: x["metal_type"])
    
    return modified_data

@frappe.whitelist()
def get_metal_touch():
    # Your code to fetch attribute values where is_setting_type is checked
    metal_touch = frappe.get_all("Attribute Value", filters={"is_metal_touch": 1})
    
    # Modify the structure of the list
    # modified_data = [{"metal_touch": item["name"]} for item in metal_touch]
    excluded_values = ["24KT"]
    modified_data = [{"metal_touch": item["name"]} for item in metal_touch if item["name"] not in excluded_values]


    # Sort the modified_data list in ascending order by the "metal_touch" attribute
    modified_data = sorted(modified_data, key=lambda x: x["metal_touch"])
    
    return modified_data

@frappe.whitelist()
def get_metal_color():
    # Your code to fetch attribute values where is_setting_type is checked
    metal_colour = frappe.get_all("Attribute Value", filters={"is_metal_colour": 1})
    
    # Modify the structure of the list
    modified_data = [{"metal_color": item["name"]} for item in metal_colour]

    # Sort the modified_data list in ascending order by the "metal_colour" attribute
    modified_data = sorted(modified_data, key=lambda x: x["metal_color"])
    
    return modified_data

@frappe.whitelist()
def get_stone_shape():
    # Your code to fetch attribute values where is_setting_type is checked
    stone_shape = frappe.get_all("Attribute Value", filters={"is_stone_shape": 1})
    
    # Modify the structure of the list
    # modified_data = [{"stone_shape": item["name"]} for item in stone_shape]

    # Modify the structure of the list and exclude specific values
    excluded_values = ["1 Mukhi","2 Mukhi","3 Mukhi","4 Mukhi","5 Mukhi","6 Mukhi","7 Mukhi","8 Mukhi","9 Mukhi","10 Mukhi", "Beeds", "Trillion"]
    modified_data = [{"stone_shape": item["name"]} for item in stone_shape if item["name"] not in excluded_values]

    # Sort the modified_data list in ascending order by the "stone_shape" attribute
    modified_data = sorted(modified_data, key=lambda x: x["stone_shape"])
    
    return modified_data

@frappe.whitelist()
def get_gemstone_stone():
    # Your code to fetch attribute values where is_setting_type is checked
    stone_shape = frappe.get_all("Attribute Value", filters={"is_stone_shape": 1})
    
    # Modify the structure of the list
    modified_data = [{"gemstone_stone": item["name"]} for item in stone_shape]

    # Sort the modified_data list in ascending order by the "gemstone_shape" attribute
    modified_data = sorted(modified_data, key=lambda x: x["gemstone_stone"])
    
    return modified_data

@frappe.whitelist()
def get_finding_size():
    # Your code to fetch attribute values where is_setting_type is checked
    finding_size = frappe.get_all("Attribute Value", filters={"is_finding_size": 1})
    
    # Modify the structure of the list
    modified_data = [{"finding_size": item["name"]} for item in finding_size]

    # Sort the modified_data list in ascending order by the "finding_size" attribute
    modified_data = sorted(modified_data, key=lambda x: x["finding_size"])
    
    return modified_data

@frappe.whitelist()
def get_size_range():
    # Your code to fetch attribute values where is_setting_type is checked
    diamond_sieve_size_range = frappe.get_all("Attribute Value", filters={"is_diamond_sieve_size_range": 1})
    
    # Modify the structure of the list
    modified_data = [{"size_range": item["name"]} for item in diamond_sieve_size_range]

    # Sort the modified_data list in ascending order by the "sieve_size_range" attribute
    modified_data = sorted(modified_data, key=lambda x: x["size_range"])
    
    return modified_data

@frappe.whitelist()
def get_sieve_size():
    # Your code to fetch attribute values where is_setting_type is checked
    diamond_sieve_size = frappe.get_all("Attribute Value", filters={"is_diamond_sieve_size": 1})
    
    # Modify the structure of the list
    modified_data = [{"sieve_size": item["name"]} for item in diamond_sieve_size]

    # Sort the modified_data list in ascending order by the "diamond_sieve_size" attribute
    modified_data = sorted(modified_data, key=lambda x: x["sieve_size"])
    
    return modified_data

@frappe.whitelist()
def get_diamond_size_in_mm():
    # Your code to fetch attribute values where is_setting_type is checked
    diamond_size_in_mm = frappe.get_all("Attribute Value", filters={"is_diamond_size_in_mm": 1})
    
    # Modify the structure of the list
    modified_data = [{"diamond_size_in_mm": item["name"]} for item in diamond_size_in_mm]

    # Sort the modified_data list in ascending order by the "diamond_size_in_mm" attribute
    modified_data = sorted(modified_data, key=lambda x: x["diamond_size_in_mm"])
    
    return modified_data

@frappe.whitelist()
def get_design_attributs():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"is_design_attribute": 1})
    
    # Modify the structure of the list
    modified_data = [{"design_attributs": item["name"]} for item in design_attributs]

    # Sort the modified_data list in ascending order by the "design_attributs" attribute
    modified_data = sorted(modified_data, key=lambda x: x["design_attributs"])
    
    return modified_data

@frappe.whitelist()
def get_age_group():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"custom_is_design_attribute": 1, "parent_attribute_value": "Age Group"})
    
    # Modify the structure of the list
    modified_data = [{"age_group": item["name"]} for item in design_attributs]

    # Sort the modified_data list in ascending order by the "age_group" attribute
    modified_data = sorted(modified_data, key=lambda x: x["age_group"])
    
    return modified_data

@frappe.whitelist()
def get_animals():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"custom_is_design_attribute": 1, "parent_attribute_value": "Animals"})
    
    # Modify the structure of the list
    modified_data = [{"animals": item["name"]} for item in design_attributs]

    # Sort the modified_data list in ascending order by the "animals" attribute
    modified_data = sorted(modified_data, key=lambda x: x["animals"])
    
    return modified_data

@frappe.whitelist()
def get_birds():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"custom_is_design_attribute": 1, "parent_attribute_value": "Birds"})
    
    # Modify the structure of the list
    modified_data = [{"birds": item["name"]} for item in design_attributs]

    # Sort the modified_data list in ascending order by the "birds" attribute
    modified_data = sorted(modified_data, key=lambda x: x["birds"])
    
    return modified_data

@frappe.whitelist()
def get_birthstone():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"custom_is_design_attribute": 1, "parent_attribute_value": "Birthstone"})
    
    # Modify the structure of the list
    modified_data = [{"birthstone": item["name"]} for item in design_attributs]

    # Sort the modified_data list in ascending order by the "birthstone" attribute
    modified_data = sorted(modified_data, key=lambda x: x["birthstone"])
    
    return modified_data

@frappe.whitelist()
def get_collection():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"custom_is_design_attribute": 1, "parent_attribute_value": "Collection"})
    
    # Modify the structure of the list
    modified_data = [{"collection": item["name"]} for item in design_attributs]

    # Sort the modified_data list in ascending order by the "collection" attribute
    modified_data = sorted(modified_data, key=lambda x: x["collection"])
    
    return modified_data

@frappe.whitelist()
def get_color_tone():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"custom_is_design_attribute": 1, "parent_attribute_value": "Color Tone"})
    
    # Modify the structure of the list
    modified_data = [{"color_tone": item["name"]} for item in design_attributs]

    # Sort the modified_data list in ascending order by the "color_tone" attribute
    modified_data = sorted(modified_data, key=lambda x: x["color_tone"])
    
    return modified_data

@frappe.whitelist()
def get_close_chilan():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"custom_is_design_attribute": 1, "parent_attribute_value": "Close Chilan"})
    
    # Modify the structure of the list
    modified_data = [{"close_chilan": item["name"]} for item in design_attributs]

    # Sort the modified_data list in ascending order by the "close_chilan" attribute
    modified_data = sorted(modified_data, key=lambda x: x["close_chilan"])
    
    return modified_data

@frappe.whitelist()
def get_design_style():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"custom_is_design_attribute": 1, "parent_attribute_value": "Design Style"})
    
    # Modify the structure of the list
    modified_data = [{"design_style": item["name"]} for item in design_attributs]

    # Sort the modified_data list in ascending order by the "design_style" attribute
    modified_data = sorted(modified_data, key=lambda x: x["design_style"])
    
    return modified_data

@frappe.whitelist()
def get_finish_type():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"custom_is_design_attribute": 1, "parent_attribute_value": "Finish Type"})
    
    # Modify the structure of the list
    modified_data = [{"finish_type": item["name"]} for item in design_attributs]

    # Sort the modified_data list in ascending order by the "finish_type" attribute
    modified_data = sorted(modified_data, key=lambda x: x["finish_type"])
    
    return modified_data

@frappe.whitelist()
def get_gender():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"custom_is_design_attribute": 1, "parent_attribute_value": "Gender"})
    
    # Modify the structure of the list
    modified_data = [{"gender": item["name"]} for item in design_attributs]

    # Sort the modified_data list in ascending order by the "gender" attribute
    modified_data = sorted(modified_data, key=lambda x: x["gender"])
    
    return modified_data

@frappe.whitelist()
def get_god():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"custom_is_design_attribute": 1, "parent_attribute_value": "God"})
    
    # Modify the structure of the list
    modified_data = [{"god": item["name"]} for item in design_attributs]

    # Sort the modified_data list in ascending order by the "god" attribute
    modified_data = sorted(modified_data, key=lambda x: x["god"])
    
    return modified_data

@frappe.whitelist()
def get_initial():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"custom_is_design_attribute": 1, "parent_attribute_value": "Initial"})
    
    # Modify the structure of the list
    modified_data = [{"initial": item["name"]} for item in design_attributs]

    # Sort the modified_data list in ascending order by the "initial" attribute
    modified_data = sorted(modified_data, key=lambda x: x["initial"])
    
    return modified_data

@frappe.whitelist()
def get_no_of_prong():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"custom_is_design_attribute": 1, "parent_attribute_value": "No of Prong"})
    
    # Modify the structure of the list
    modified_data = [{"design_attributes_1": item["name"]} for item in design_attributs]

    # Sort the modified_data list in ascending order by the "design_attributes_1" attribute
    modified_data = sorted(modified_data, key=lambda x: x["design_attributes_1"])
    
    return modified_data

@frappe.whitelist()
def get_occasion():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"custom_is_design_attribute": 1, "parent_attribute_value": "Occasion"})
    
    # Modify the structure of the list
    modified_data = [{"occasion": item["name"]} for item in design_attributs]

    # Sort the modified_data list in ascending order by the "occasion" attribute
    modified_data = sorted(modified_data, key=lambda x: x["occasion"])
    
    return modified_data

@frappe.whitelist()
def get_relationship():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"custom_is_design_attribute": 1, "parent_attribute_value": "Relationship"})
    
    # Modify the structure of the list
    modified_data = [{"relationship": item["name"]} for item in design_attributs]

    # Sort the modified_data list in ascending order by the "relationship" attribute
    modified_data = sorted(modified_data, key=lambda x: x["relationship"])
    
    return modified_data

@frappe.whitelist()
def get_setting_style():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"custom_is_design_attribute": 1, "parent_attribute_value": "Setting Style"})
    
    # Modify the structure of the list
    modified_data = [{"setting_style": item["name"]} for item in design_attributs]

    # Sort the modified_data list in ascending order by the "setting_style" attribute
    modified_data = sorted(modified_data, key=lambda x: x["setting_style"])
    
    return modified_data

@frappe.whitelist()
def get_shape():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"custom_is_design_attribute": 1, "parent_attribute_value": "Shape"})
    
    # Modify the structure of the list
    modified_data = [{"shape": item["name"]} for item in design_attributs]

    # Sort the modified_data list in ascending order by the "shape" attribute
    modified_data = sorted(modified_data, key=lambda x: x["shape"])
    
    return modified_data

@frappe.whitelist()
def get_temple():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"custom_is_design_attribute": 1, "parent_attribute_value": "Temple"})
    
    # Modify the structure of the list
    modified_data = [{"temple": item["name"]} for item in design_attributs]

    # Sort the modified_data list in ascending order by the "temple" attribute
    modified_data = sorted(modified_data, key=lambda x: x["temple"])
    
    return modified_data

@frappe.whitelist()
def get_zodiac():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"custom_is_design_attribute": 1, "parent_attribute_value": "Zodiac"})
    
    # Modify the structure of the list
    modified_data = [{"zodiac": item["name"]} for item in design_attributs]

    # Sort the modified_data list in ascending order by the "zodiac" attribute
    modified_data = sorted(modified_data, key=lambda x: x["zodiac"])
    
    return modified_data

@frappe.whitelist()
def get_creativity():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"custom_is_design_attribute": 1, "parent_attribute_value": "Creativity"})
    
    # Modify the structure of the list
    modified_data = [{"creativity": item["name"]} for item in design_attributs]

    # Sort the modified_data list in ascending order by the "design_attributes_1" attribute
    modified_data = sorted(modified_data, key=lambda x: x["creativity"])
    
    return modified_data

@frappe.whitelist()
def get_employee():
# Fetch specific fields from the Employee doctype
    employee_data = frappe.get_all("Employee", filters={}, fields=["employee_name", "user_id", "company"])
    return employee_data

# @frappe.whitelist()
# def get_employee_permission():
#         # Fetch specific fields from the User Permission doctype
#     user_permission_data = frappe.get_all("User Permission", filters={"allow":"Company"}, fields=["user", "for_value"])
    
#     formatted_data = []
#     for permission in user_permission_data:
#         formatted_permission = {
#             "user_id": permission["user"],
#             "company": permission["for_value"]
#         }
#         formatted_data.append(formatted_permission)
    
#     return formatted_data

# @frappe.whitelist()
# def get_employee_permission():
#         # Fetch specific fields from the User Permission doctype
#     user_permission_data = frappe.get_all("User Permission", filters={"allow":"Company"}, fields=["user", "for_value"])
    
#     formatted_data = []
#     for permission in user_permission_data:
#         formatted_permission = {
#             "user_id": permission["user"],
#             "company": permission["for_value"]
#         }
#         formatted_data.append(formatted_permission)
    
#     return formatted_data

@frappe.whitelist(allow_guest=True)
def get_employee_permission():
    try:
        sql_query = """
            SELECT `user` as user_id, GROUP_CONCAT(`for_value`) AS company
            FROM `tabUser Permission`
            WHERE `allow` = 'Company'
            GROUP BY `user`; """
        
        result = frappe.db.sql(sql_query, as_dict=True)
        
        return result

    except Exception as e:
        return {"error": str(e)}

@frappe.whitelist(allow_guest=True)
def cat_count():
    try:
        sql_query = """
             SELECT
                item.item_subcategory,
                COUNT(DISTINCT CASE
                    WHEN tav.is_subcategory = 1 AND item.item_subcategory IS NOT NULL THEN item.name
                    ELSE NULL
                END) AS item_count,
                COUNT(DISTINCT CASE
                    WHEN tav.is_subcategory = 1 AND item.item_subcategory IS NOT NULL
                        AND bom.bom_type = "Finish Goods" AND bom.is_active = 1 THEN item.name
                    ELSE NULL
                END) AS serial_count
            FROM `tabItem` AS item
            JOIN `tabAttribute Value` AS tav ON item.item_subcategory = tav.name
            LEFT JOIN `tabBOM` AS bom ON item.item_code = bom.item
            WHERE (tav.is_subcategory = 1 AND item.item_subcategory IS NOT NULL)
            OR (bom.bom_type = "Finish Goods" AND bom.is_active = 1)
            GROUP BY item.item_subcategory;
        """
        
        result = frappe.db.sql(sql_query, as_dict=True)
        
        return result

    except Exception as e:
        return {"error": str(e)}
    

@frappe.whitelist(allow_guest=True)
def var_count():
    try:
        sql_query = """
                select item.variant_of as variant_of, count(item.name) as var_count ,
                GROUP_CONCAT(distinct(item.name)) as item from tabItem item 
                where variant_of is not null group by item.variant_of;
            """
        
        result = frappe.db.sql(sql_query, as_dict=True)
        
        return result

    except Exception as e:
        return {"error": str(e)}
    
    #---------------------------------------------------------------------------------------------------------------------------
    #---------------------------------------------------------------------------------------------------------------------------
# exhibition
#employee
@frappe.whitelist(allow_guest=True)
def employee_data():
    try:
        sql_query = """
             select employee as employee_code ,employee_name ,designation ,company,branch,user_id  from tabEmployee te ;
        """
        
        result = frappe.db.sql(sql_query, as_dict=True)
        
        return result

    except Exception as e:
        return {"error": str(e)}
    
#Branch

@frappe.whitelist(allow_guest=True)
def branch_data():
    try:
        sql_query = """
             select DISTINCT (name) as branch_name from tabBranch tb  ;
        """
        
        result = frappe.db.sql(sql_query, as_dict=True)
        
        return result

    except Exception as e:
        return {"error": str(e)}

#Salesman
    
@frappe.whitelist(allow_guest=True)
def salesman_data():
    try:
        sql_query = """
             select employee as salesman_code ,employee_name as salesman_name,designation ,branch  from tabEmployee te where designation ='Sales Person' ;
        """
        
        result = frappe.db.sql(sql_query, as_dict=True)
        
        return result

    except Exception as e:
        return {"error": str(e)}
    
#customer
    
@frappe.whitelist(allow_guest=True)
def customer_data():
    try:
        sql_query = """
             select name as customer_id,customer_name,territory from tabCustomer tc  ;
        """
        
        result = frappe.db.sql(sql_query, as_dict=True)
        
        return result

    except Exception as e:
        return {"error": str(e)}
    
#Lead

@frappe.whitelist(allow_guest=True)
def lead_data():
    try:
        sql_query = """
        select title as lead from tabLead tl order by creation desc
        """

        result = frappe.db.sql(sql_query, as_dict=True)
        return result
    except Exception as e:
        return{"error": str(e)}


@frappe.whitelist(allow_guest=True)
def item_no_data():
    try:
        sql_query = """
        select * from `tabExhibition` order by no asc
        """

        result = frappe.db.sql(sql_query, as_dict=True)
        return result
    except Exception as e:
        return{"error": str(e)}


@frappe.whitelist(allow_guest=True)
def get_submited_data():
    return ''

#summary

@frappe.whitelist(allow_guest=True)
def summary_data():
    try:
        sql_query = """
            select date(tes.creation),tes.customer_name,tes.lead_name,tes.selectionperson,tes.branch,tes.salesman_name,tes.user,count(tse.item_no),sum(ex.gold_pure_weight),
            sum(ex.diamond_weight),sum(ex.gross_weight)   from `tabExhibition Selection` as tes
            join `tabSelection Exhibition` as tse on tes.name = tse.parent
            join 
            tabExhibition as ex on tse.item_no = ex.name
            group by date(tes.creation),tes.customer_name,tes.lead_name,tes.user ;
        """
        
        result = frappe.db.sql(sql_query, as_dict=True)
        
        return result

    except Exception as e:
        return {"error": str(e)}