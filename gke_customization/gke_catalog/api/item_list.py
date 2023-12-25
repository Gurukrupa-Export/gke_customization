import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def get_bom_list():
    # Implement your logic to fetch items and filter as needed
    #bom = frappe.get_all('BOM', filters={"docstatus": 1, "is_active": 1 ,"bom_type":'Finished Goods'}, fields=[
    bom = frappe.get_all('BOM', filters={"is_active": 1,"bom_type":'Finished Goods'}, fields=[
    
        'item',
        'name',
        'gross_weight',
        'metal_and_finding_weight',
        'diamond_weight',
        'other_weight',
        'gemstone_weight',
        'finding_weight_',
        'metal_colour', 
        'metal_purity',
        'total_diamond_pcs',
        'total_gemstone_pcs',
        'gold_to_diamond_ratio',
        'diamond_ratio',
        'metal_to_diamond_ratio_excl_of_finding',
        'navratna',
        'height',
        'length',
        'width',
        'breadth',
        'product_size',
        'sizer_type',
        'design_style',
        'nakshi_from',
        'vanki_type',
        'total_length',
        'detachable',
        'back_side_size',
        'changeable'
    ])

    bom_list = []
    
    # Create a set to store unique item codes from the BOMs
    item_codes = set()

    for bom_doc in bom:
        # Fetch data from the 'metal_detail' child table
        metal_details = frappe.get_all('BOM Metal Detail', filters={"parent": bom_doc['name']}, fields=[
            'metal_type',
            'metal_touch',
            'metal_colour'
            # Add other fields you need from the child table
        ])

        # Create a dictionary to store metal details
        metal_details_list = []

        for metal_detail in metal_details:
            metal_detail_dict = {
                "metal_type": metal_detail['metal_type'],
                "metal_touch": metal_detail['metal_touch'],
                "metal_colour": metal_detail['metal_colour'],
                # Add other fields from the child table as needed
            }
            metal_details_list.append(metal_detail_dict)

        # Fetch data from the 'finding_detail' child table
        finding_details = frappe.get_all('BOM Finding Detail', filters={"parent": bom_doc['name']}, fields=[
            'finding_type','finding_size'
            # Add other fields you need from the child table
        ])

        # Create a dictionary to store finding details
        finding_detail_list = []

        for finding_detail in finding_details:
            finding_detail_dict = {
                "finding_sub_category": finding_detail['finding_type'],
                "finding_size":finding_detail['finding_size']
                # Add other fields from the child table as needed
            }
            finding_detail_list.append(finding_detail_dict)

        # Fetch data from the 'diamond_detail' child table
        diamond_details = frappe.get_all('BOM Diamond Detail', filters={"parent": bom_doc['name']}, fields=[
            'stone_shape','sub_setting_type','diamond_sieve_size','size_in_mm','sieve_size_range'
            # Add other fields you need from the child table
        ])

        # Create a dictionary to store diamond details
        diamond_detail_list = []

        for diamond_detail in diamond_details:
            diamond_detail_dict = {
                "stone_shape": diamond_detail['stone_shape'],
                "sub_setting_type":diamond_detail['sub_setting_type'],
                "diamond_sieve_size":diamond_detail['diamond_sieve_size'],
                "size_in_mm":diamond_detail['size_in_mm'],
                "sieve_size_range":diamond_detail['sieve_size_range']
                # Add other fields from the child table as needed
            }
            diamond_detail_list.append(diamond_detail_dict)

        # Fetch data from the 'gemstone_detail' child table
        gemstone_details = frappe.get_all('BOM Gemstone Detail', filters={"parent": bom_doc['name']}, fields=[
            'stone_shape','sub_setting_type','cut_or_cab'
            # Add other fields you need from the child table
        ])

        # Create a dictionary to store gemstone details
        gemstone_detail_list = []

        for gemstone_detail in gemstone_details:
            gemstone_detail_dict = {
                "gemstone_shape": gemstone_detail['stone_shape'],
                "sub_setting_type": gemstone_detail['sub_setting_type'],
                "cut_or_cab":gemstone_detail['cut_or_cab']
                # Add other fields from the child table as needed
            }
            gemstone_detail_list.append(gemstone_detail_dict)

        # Fetch data from the 'design_attribute' child table
        design_attributes = frappe.get_all('Design Attributes', filters={"parent": bom_doc['name']}, fields=[
            'design_attributes',
            'design_attribute_value_1'
            # Add other fields you need from the child table
        ])

        # Create a dictionary to store design attribute details
        design_attribute_list = []

        for design_attribute in design_attributes:
            design_attribute_dict = {
                "design_attributes": design_attribute['design_attributes'],
                "design_attribute_value_1": design_attribute['design_attribute_value_1'],
                # Add other fields from the child table as needed
            }
            design_attribute_list.append(design_attribute_dict)

        item_codes.add(bom_doc['item'])
        bom_dict = {
            "item": bom_doc['item'],
            "name": bom_doc['name'],
            "gross_metal_weight": bom_doc['gross_weight'],
            "Net_metal_finding_weight": bom_doc['metal_and_finding_weight'],
            "Diamond_weight": bom_doc['diamond_weight'],
            "other_weight": bom_doc['other_weight'],
            "gemstone_weight": bom_doc['gemstone_weight'],
            "finding_weight": bom_doc['finding_weight_'],
            "metal_color": bom_doc['metal_colour'],
            "metal_purity": bom_doc['metal_purity'],
            "total_diamond_pcs": bom_doc['total_diamond_pcs'],
            "total_gemstone_pcs": bom_doc['total_gemstone_pcs'],
            "gold_to_diamond_ratio": bom_doc['gold_to_diamond_ratio'],
            "diamond_ratio": bom_doc['diamond_ratio'],
            "metal_to_diamond_ratio_excl_of_finding": bom_doc['metal_to_diamond_ratio_excl_of_finding'],
            "navratna": bom_doc['navratna'],
            "height": bom_doc['height'],
            "length": bom_doc['length'],
            "width": bom_doc['width'],
            "breadth": bom_doc['breadth'],
            "product_size": bom_doc['product_size'],
            "sizer_type": bom_doc['sizer_type'],
            "design_style": bom_doc['design_style'],
            "nakshi_from": bom_doc['nakshi_from'],
            "vanki_type": bom_doc['vanki_type'],
            "total_length": bom_doc['total_length'],
            "detachable": bom_doc['detachable'],
            "back_side_size": bom_doc['back_side_size'],
            "changeable": bom_doc['changeable'],
            "metal_details": metal_details_list,
            "finding_details": finding_detail_list,
            "diamond_details": diamond_detail_list,
            "gemstone_details": gemstone_detail_list,
            "design_attributes": design_attribute_list,  # Added design_attributes here
            "design_attributes": get_design_attributes(bom_doc['item']),  # Fetch design attributes for the item
        }
        bom_list.append(bom_dict)
        

    # Fetch additional fields from the 'Item' doctype for items available in the BOMs
    item_details = frappe.get_all('Item', filters={"item_code": ["in", list(item_codes)]}, fields=[
        'item_code',
        'image',
        'item_category',
        'item_subcategory',
        'setting_type'
    ])

    # Create a dictionary to map item codes to their details
    item_details_dict = {item['item_code']: item for item in item_details}

    # Update the bom_list with additional item details
    for bom_dict in bom_list:
        item_code = bom_dict['item']
        if item_code in item_details_dict:
            item_detail = item_details_dict[item_code]
            bom_dict['item_image'] = item_detail['image']
            bom_dict['item_category'] = item_detail['item_category']
            bom_dict['item_subcategory'] = item_detail['item_subcategory']
            bom_dict['setting_type'] = item_detail['setting_type']

    return bom_list
def get_design_attributes(item_code):
    # Fetch data from the 'Design Attributes' child table for the specified item
    design_attributes = frappe.get_all('Design Attributes', filters={"parent": item_code}, 
                                       fields=['design_attributes','design_attribute_value_1'],order_by='design_attributes')

    # Create a dictionary to store design attribute details
    design_attribute_list = []

    for design_attribute in design_attributes:
        design_attribute_dict = {
            "design_attributes": design_attribute['design_attributes'],
            "design_attribute_value_1": design_attribute['design_attribute_value_1'],
            
            # Add other fields from the child table as needed
        }
        design_attribute_list.append(design_attribute_dict)

    return design_attribute_list

# ... (The rest of your code for other whitelisted functions)
# for particular field filter api
@frappe.whitelist()
def get_category_attribute_values():
    # Your code to fetch attribute values where is_category is checked
    itm_category = frappe.get_all("Attribute Value", filters={"is_category": 1})
    
    # Modify the structure of the list
    modified_data = [{"item_category": item["name"]} for item in itm_category]
    
    return modified_data

@frappe.whitelist()
def get_subcategory():
    # Your code to fetch attribute values where is_category is checked
    itm_subcategory = frappe.get_all("Attribute Value", filters={"is_subcategory": 1})
    
    # Modify the structure of the list
    modified_data = [{"item_subcategory": item["name"]} for item in itm_subcategory]
    
    return modified_data

@frappe.whitelist()
def get_setting_types():
    # Your code to fetch attribute values where is_setting_type is checked
    setting_type = frappe.get_all("Attribute Value", filters={"is_setting_type": 1})
    
    # Modify the structure of the list
    modified_data = [{"setting_type": item["name"]} for item in setting_type]
    
    return modified_data

@frappe.whitelist()
def get_finding_sub_category():
    # Your code to fetch attribute values where is_setting_type is checked
    finding_sub_category = frappe.get_all("Attribute Value", filters={"is_finding_type": 1})
    
    # Modify the structure of the list
    modified_data = [{"finding_sub_category": item["name"]} for item in finding_sub_category]
    
    return modified_data

@frappe.whitelist()
def get_metal_type():
    # Your code to fetch attribute values where is_setting_type is checked
    metal_type = frappe.get_all("Attribute Value", filters={"is_metal_type": 1})
    
    # Modify the structure of the list
    modified_data = [{"metal_type": item["name"]} for item in metal_type]
    
    return modified_data

@frappe.whitelist()
def get_metal_touch():
    # Your code to fetch attribute values where is_setting_type is checked
    metal_touch = frappe.get_all("Attribute Value", filters={"is_metal_touch": 1})
    
    # Modify the structure of the list
    modified_data = [{"metal_touch": item["name"]} for item in metal_touch]
    
    return modified_data

@frappe.whitelist()
def get_metal_colour():
    # Your code to fetch attribute values where is_setting_type is checked
    metal_colour = frappe.get_all("Attribute Value", filters={"is_metal_colour": 1})
    
    # Modify the structure of the list
    modified_data = [{"metal_colour": item["name"]} for item in metal_colour]
    
    return modified_data

@frappe.whitelist()
def get_diamond_stone_shape():
    # Your code to fetch attribute values where is_setting_type is checked
    stone_shape = frappe.get_all("Attribute Value", filters={"is_stone_shape": 1})
    
    # Modify the structure of the list
    modified_data = [{"stone_shape": item["name"]} for item in stone_shape]
    
    return modified_data

@frappe.whitelist()
def get_gemstone_stone_shape():
    # Your code to fetch attribute values where is_setting_type is checked
    stone_shape = frappe.get_all("Attribute Value", filters={"is_stone_shape": 1})
    
    # Modify the structure of the list
    modified_data = [{"gemstone_shape": item["name"]} for item in stone_shape]
    
    return modified_data

@frappe.whitelist()
def get_finding_size():
    # Your code to fetch attribute values where is_setting_type is checked
    finding_size = frappe.get_all("Attribute Value", filters={"is_finding_size": 1})
    
    # Modify the structure of the list
    modified_data = [{"finding_size": item["name"]} for item in finding_size]
    
    return modified_data

@frappe.whitelist()
def get_diamond_sieve_size_range():
    # Your code to fetch attribute values where is_setting_type is checked
    diamond_sieve_size_range = frappe.get_all("Attribute Value", filters={"is_diamond_sieve_size_range": 1})
    
    # Modify the structure of the list
    modified_data = [{"sieve_size_range": item["name"]} for item in diamond_sieve_size_range]
    
    return modified_data

@frappe.whitelist()
def get_diamond_sieve_size():
    # Your code to fetch attribute values where is_setting_type is checked
    diamond_sieve_size = frappe.get_all("Attribute Value", filters={"is_diamond_sieve_size": 1})
    
    # Modify the structure of the list
    modified_data = [{"diamond_sieve_size": item["name"]} for item in diamond_sieve_size]
    
    return modified_data

@frappe.whitelist()
def get_diamond_size_in_mm():
    # Your code to fetch attribute values where is_setting_type is checked
    diamond_size_in_mm = frappe.get_all("Attribute Value", filters={"is_diamond_size_in_mm": 1})
    
    # Modify the structure of the list
    modified_data = [{"diamond_size_in_mm": item["name"]} for item in diamond_size_in_mm]
    
    return modified_data



@frappe.whitelist()
def get_design_attributs():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"is_design_attribute": 1})
    
    # Modify the structure of the list
    modified_data = [{"design_attributs": item["name"]} for item in design_attributs]
    
    return modified_data



@frappe.whitelist()
def get_age_group_design_attributs():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"is_design_attribute": 1,"parent_attribute_value":"Age Group"})
    
    # Modify the structure of the list
    modified_data = [{"design_attribute_value_1": item["name"]} for item in design_attributs]
    
    return modified_data

@frappe.whitelist()
def get_animals_design_attributs():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"is_design_attribute": 1,"parent_attribute_value":"Animals"})
    
    # Modify the structure of the list
    modified_data = [{"design_attribute_value_1": item["name"]} for item in design_attributs]
    
    return modified_data

@frappe.whitelist()
def get_birds_design_attributs():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"is_design_attribute": 1,"parent_attribute_value":"Birds"})
    
    # Modify the structure of the list
    modified_data = [{"design_attribute_value_1": item["name"]} for item in design_attributs]
    
    return modified_data

@frappe.whitelist()
def get_birthstone_design_attributs():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"is_design_attribute": 1,"parent_attribute_value":"Birthstone"})
    
    # Modify the structure of the list
    modified_data = [{"design_attribute_value_1": item["name"]} for item in design_attributs]
    
    return modified_data

@frappe.whitelist()
def get_collection_design_attributs():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"is_design_attribute": 1,"parent_attribute_value":"Collection"})
    
    # Modify the structure of the list
    modified_data = [{"design_attribute_value_1": item["name"]} for item in design_attributs]
    
    return modified_data

@frappe.whitelist()
def get_color_tone_design_attributs():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"is_design_attribute": 1,"parent_attribute_value":"Color Tone"})
    
    # Modify the structure of the list
    modified_data = [{"design_attribute_value_1": item["name"]} for item in design_attributs]
    
    return modified_data

@frappe.whitelist()
def get_close_chilan_design_attributs():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"is_design_attribute": 1,"parent_attribute_value":"Close Chilan"})
    
    # Modify the structure of the list
    modified_data = [{"design_attribute_value_1": item["name"]} for item in design_attributs]
    
    return modified_data

@frappe.whitelist()
def get_design_style_design_attributs():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"is_design_attribute": 1,"parent_attribute_value":"Design Style"})
    
    # Modify the structure of the list
    modified_data = [{"design_attribute_value_1": item["name"]} for item in design_attributs]
    
    return modified_data

@frappe.whitelist()
def get_finish_type_design_attributs():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"is_design_attribute": 1,"parent_attribute_value":"Finish Type"})
    
    # Modify the structure of the list
    modified_data = [{"design_attribute_value_1": item["name"]} for item in design_attributs]
    
    return modified_data

@frappe.whitelist()
def get_gender_design_attributs():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"is_design_attribute": 1,"parent_attribute_value":"Gender"})
    
    # Modify the structure of the list
    modified_data = [{"design_attribute_value_1": item["name"]} for item in design_attributs]
    
    return modified_data

@frappe.whitelist()
def get_god_design_attributs():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"is_design_attribute": 1,"parent_attribute_value":"God"})
    
    # Modify the structure of the list
    modified_data = [{"design_attribute_value_1": item["name"]} for item in design_attributs]
    
    return modified_data

@frappe.whitelist()
def get_initial_design_attributs():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"is_design_attribute": 1,"parent_attribute_value":"Initial"})
    
    # Modify the structure of the list
    modified_data = [{"design_attribute_value_1": item["name"]} for item in design_attributs]
    
    return modified_data

@frappe.whitelist()
def get_no_of_prong_design_attributs():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"is_design_attribute": 1,"parent_attribute_value":"No of Prong"})
    
    # Modify the structure of the list
    modified_data = [{"design_attribute_value_1": item["name"]} for item in design_attributs]
    
    return modified_data

@frappe.whitelist()
def get_occasion_design_attributs():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"is_design_attribute": 1,"parent_attribute_value":"Occasion"})
    
    # Modify the structure of the list
    modified_data = [{"design_attribute_value_1": item["name"]} for item in design_attributs]
    
    return modified_data

@frappe.whitelist()
def get_relationship_design_attributs():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"is_design_attribute": 1,"parent_attribute_value":"Relationship"})
    
    # Modify the structure of the list
    modified_data = [{"design_attribute_value_1": item["name"]} for item in design_attributs]
    
    return modified_data

@frappe.whitelist()
def get_setting_style_design_attributs():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"is_design_attribute": 1,"parent_attribute_value":"Setting Style"})
    
    # Modify the structure of the list
    modified_data = [{"design_attribute_value_1": item["name"]} for item in design_attributs]
    
    return modified_data

@frappe.whitelist()
def get_shape_design_attributs():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"is_design_attribute": 1,"parent_attribute_value":"Shape"})
    
    # Modify the structure of the list
    modified_data = [{"design_attribute_value_1": item["name"]} for item in design_attributs]
    
    return modified_data

@frappe.whitelist()
def get_temple_design_attributs():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"is_design_attribute": 1,"parent_attribute_value":"Temple"})
    
    # Modify the structure of the list
    modified_data = [{"design_attribute_value_1": item["name"]} for item in design_attributs]
    
    return modified_data


@frappe.whitelist()
def get_zodiac_design_attributs():
    # Your code to fetch attribute values where is_setting_type is checked
    design_attributs = frappe.get_all("Attribute Value", filters={"is_design_attribute": 1,"parent_attribute_value":"Zodiac"})
    
    # Modify the structure of the list
    modified_data = [{"design_attribute_value_1": item["name"]} for item in design_attributs]
    
    return modified_data


# Common function to fetch and sort data
def fetch_and_sort_data(filter_key, attribute_name):
    data = frappe.get_all("Attribute Value", filters={filter_key: 1})
    modified_data = [{attribute_name: item["name"]} for item in data]
    sorted_data = sorted(modified_data, key=lambda x: x[attribute_name])
    return sorted_data

# Example of one of your functions
@frappe.whitelist()
def get_category_attribute_values():
    return fetch_and_sort_data("is_category", "item_category")

