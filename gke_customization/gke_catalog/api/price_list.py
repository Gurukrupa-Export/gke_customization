import frappe

@frappe.whitelist(allow_guest=True)
def diamond_price_list():
    try:
        sql_query = """
            SELECT 
                customer,
                tc.customer_name,
                stone_shape as diamond_shape,
                price_list_type,
                sieve_size_range,
                size_in_mm,
                CONCAT(
                    ROUND(from_weight, 3),
                    ' - ',
                    ROUND(to_weight, 3)
                ) AS weight_range,
                to_weight,
                from_weight,
                rate 
            FROM `tabDiamond Price List` as tdp
            JOIN `tabCustomer` as tc ON tc.name = tdp.customer 
        """

        result = frappe.db.sql(sql_query, as_dict=True)
            
        return result
        # result_data = encrypt_data(result)
        # return result_data

    except Exception as e:
        return {"error": str(e)}
    
@frappe.whitelist(allow_guest=True)
def customer_diamond_price_list():
    try:
        sql_query = """
            SELECT 
                customer_name,
                price_list_type,
                dp.rate 
            FROM `tabDiamond Price List` as dp
            JOIN `tabCustomer` as tc ON tc.name = dp.customer 
            GROUP BY customer_name

        """

        result = frappe.db.sql(sql_query, as_dict=True)
            
        # return result
        result_data = encrypt_data(result)
        return result_data

    except Exception as e:
        return {"error": str(e)}


@frappe.whitelist()
def get_stone_shape():
    # Your code to fetch attribute values where is_setting_type is checked
    stone_shape = frappe.get_all("Attribute Value", filters={"is_stone_shape": 1})

    # Modify the structure of the list and exclude specific values
    excluded_values = ["1 Mukhi","2 Mukhi","3 Mukhi","4 Mukhi","5 Mukhi","6 Mukhi","7 Mukhi","8 Mukhi","9 Mukhi","10 Mukhi", "Beeds", "Trillion"]
    modified_data = [{"stone_shape": item["name"]} for item in stone_shape if item["name"] not in excluded_values]

    # Sort the modified_data list in ascending order by the "stone_shape" attribute
    modified_data = sorted(modified_data, key=lambda x: x["stone_shape"])
    
    # return modified_data
    result_data = encrypt_data(modified_data)
    return result_data

# encrypt 
crypt = {
    "a": "100",
    "b": "101",
    "c": "102",
    "d": "103",
    "e": "104",
    "f": "105",
    "g": "106",
    "h": "107",
    "i": "108",
    "j": "109",
    "k": "110",
    "l": "111",
    "m": "112",
    "n": "113",
    "o": "114",
    "p": "115",
    "q": "116",
    "r": "117",
    "s": "118",
    "t": "119",
    "u": "120",
    "v": "121",
    "w": "122",
    "x": "123",
    "y": "124",
    "z": "125",
    "A": "126",
    "B": "127",
    "C": "128",
    "D": "129",
    "E": "130",
    "F": "131",
    "G": "132",
    "H": "133",
    "I": "134",
    "J": "135",
    "K": "136",
    "L": "137",
    "M": "138",
    "N": "139",
    "O": "140",
    "P": "141",
    "Q": "142",
    "R": "143",
    "S": "144",
    "T": "145",
    "U": "146",
    "V": "147",
    "W": "148",
    "X": "149",
    "Y": "150",
    "Z": "151",
    " ": "152",  
    "(": "153",  
    ")": "154",
    ",": "155",    
    "'": "156",    
    "1": "a",
    "2": "b",
    "3": "c",
    "4": "d",
    "5": "e",
    "6": "f",
    "7": "g",
    "8": "h",
    "9": "i",
    "0": "j",
    "-": "k",
    "+": "l",
    ".": "m",  
    # "'": "n",  
    # ".": "o",  
}

import json
# Common function to encrypt data
@frappe.whitelist()
def encrypt_data(modified_data):
    encrypted_data = {"message": []}

    for item in modified_data:
        encrypted_item = {}
        for key, value in item.items():
            encrypted_value = "".join(crypt.get(char, char) for char in str(value))
            encrypted_item[key] = encrypted_value

        encrypted_data["message"].append(encrypted_item)
    print(encrypted_data["message"])
    return encrypted_data["message"]
