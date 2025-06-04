# # Copyright (c) 2025, Gurukrupa Export and contributors
# # For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.csvutils import read_csv_content_from_attached_file
from frappe.utils import add_days, cstr, date_diff, getdate
from frappe.utils.csvutils import UnicodeWriter

class CodeCreationTool(Document):
    pass

@frappe.whitelist()
def upload():
    # Read the uploaded CSV file
    rows = read_csv_content_from_attached_file(frappe.get_doc("Code Creation Tool", "Code Creation Tool"))

    if not rows or len(rows) < 2:
        frappe.throw("No data found in the uploaded file.")

    headers = rows[4]  # First row is headers
    data_rows = rows[5:]  # Remaining rows are data
    processed_data = [headers + ["Status"]]  # Add "Status" column for response

    # Create a mapping of headers to indexes
    header_map = {col.lower().strip().replace(' ','_'): idx for idx, col in enumerate(headers)}

    child_table_fieldname = "custom_item_theme_code"  # Update with your actual child table fieldname

    for row in data_rows:
        item_name = row[header_map.get("id", -1)]
        customer = row[header_map.get("customer", -1)]
        theme_code = row[header_map.get("theme_code", -1)]
        digit_14 = row[header_map.get("14_digit_code", -1)] if "14_digit_code" in header_map else None
        digit_18 = row[header_map.get("18_digit_code", -1)] if "18_digit_code" in header_map else None
        digit_15 = row[header_map.get("15_digit_code", -1)] if "15_digit_code" in header_map else None
        sku_code = row[header_map.get("sku_code", -1)] if "sku_code" in header_map else None

        if not item_name or not theme_code:
            continue  # Skip if required fields are missing
        
        # Fetch the Item document
        item_doc = frappe.get_doc("Item", item_name)

        if not hasattr(item_doc, child_table_fieldname):
            frappe.throw(f"Child table not found in Item: {item_name}")

        child_table = getattr(item_doc, child_table_fieldname)

        # Check if the combination (theme_code + customer + 14_digit_code) exists
        already_exists = False
        insert_required = True

        for child in child_table:
            if child.theme_code == theme_code and child.customer == customer:
                # Check all codes
                match_14 = child.digit_14code == digit_14
                match_15 = child.digit_15code == digit_15
                match_18 = child.digit_18code == digit_18
                match_sku = child.sku_code == sku_code

                if match_14 and match_15 and match_18 and match_sku:
                    already_exists = True
                    insert_required = False
                    break
                else:
                    # Same customer and theme, but any code is different → Insert required
                    insert_required = True

        if already_exists:
            processed_data.append(row + ["Already Exists"])
        elif insert_required:
            item_doc.append(child_table_fieldname, {
                "customer": customer,
                "theme_code": theme_code,
                "digit_14code": digit_14,
                "digit_15code": digit_15,
                "digit_18code": digit_18,
                "sku_code": sku_code
            })
            item_doc.save()
            processed_data.append(row + ["Inserted"])
        else:
            processed_data.append(row + ["Skipped"])

    return processed_data

@frappe.whitelist()
def get_template():
	args = frappe.local.form_dict

	w = UnicodeWriter()
	w = add_header(w)

	# write out response as a type csv
	frappe.response["result"] = cstr(w.getvalue())
	frappe.response["type"] = "csv"
	frappe.response["doctype"] = "Item"

def add_header(w):
	w.writerow(["Notes:"])
	w.writerow(["Please do not change the template headings"])
	w.writerow(["SKU Code for Caratlane, 14digit for Titan, 15digit for Novel, 18digit for Reliance"])
	w.writerow(["If you are overwriting existing Item records, 'ID' column mandatory"])
	w.writerow(
		["ID", "Customer", "Theme Code", "SKU Code", "14 Digit Code", "15 Digit Code", "18 Digit Code"]
	)
	return w

# @frappe.whitelist()
# def upload():
#     # Read the uploaded CSV file
#     rows = read_csv_content_from_attached_file(frappe.get_doc("Code Creation Tool", "Code Creation Tool"))

#     if not rows or len(rows) < 2:
#         frappe.throw("No data found in the uploaded file.")

#     headers = rows[4]  # First row is headers
#     data_rows = rows[5:]  # Remaining rows are data
#     processed_data = [headers + ["Status"]]  # Add "Status" column for response

#     # Create a mapping of headers to indexes
#     header_map = {col.lower().strip().replace(' ','_'): idx for idx, col in enumerate(headers)}

#     child_table_fieldname = "custom_item_theme_code"  # Update with your actual child table fieldname

#     for row in data_rows:
#         item_name = row[header_map.get("id", -1)]
#         customer = row[header_map.get("customer", -1)]
#         theme_code = row[header_map.get("theme_code", -1)]
#         digit_14 = row[header_map.get("14_digit_code", -1)] if "14_digit_code" in header_map else None
#         digit_18 = row[header_map.get("18_digit_code", -1)] if "18_digit_code" in header_map else None
#         digit_15 = row[header_map.get("15_digit_code", -1)] if "15_digit_code" in header_map else None
#         sku_code = row[header_map.get("sku_code", -1)] if "sku_code" in header_map else None

#         if not item_name or not theme_code:
#             continue  # Skip if required fields are missing
        
#         # Fetch the Item document
#         item_doc = frappe.get_doc("Item", item_name)

#         if not hasattr(item_doc, child_table_fieldname):
#             frappe.throw(f"Child table not found in Item: {item_name}")

#         child_table = getattr(item_doc, child_table_fieldname)

#         # Check if the combination (theme_code + customer + 14_digit_code) exists
#         existing_row = None
#         for child in child_table:
#             check_14 = child.digit_14code == digit_14
#             check_15 = child.digit_15code == digit_15
#             check_18 = child.digit_18code == digit_18
#             check_sku = child.sku_code == sku_code
#             if  (child.theme_code == theme_code and child.customer == customer and (check_14 or check_15 or check_18 or check_sku)) :
#                 existing_row = child
#                 break

#         # frappe.throw(f"{existing_row}")
#         if existing_row:
#             # If row exists but other codes are different, update it
#             if (
#                 existing_row.digit_18code != digit_18 or
#                 existing_row.digit_15code != digit_15 or
#                 existing_row.sku_code != sku_code
#             ):
#                 existing_row.digit_18code = digit_18
#                 existing_row.digit_15code = digit_15
#                 existing_row.sku_code = sku_code
#                 item_doc.save()
#                 processed_data.append(row + ["Updated"])
#             else:
#                 processed_data.append(row + ["Already Exists"])
#         else:
#             # Always insert a new row in the child table
#             item_doc.append(child_table_fieldname, {
#                 "customer": customer,
#                 "theme_code": theme_code,
#                 "digit_14code": digit_14,
#                 "digit_18code": digit_18,
#                 "digit_15code": digit_15,
#                 "sku_code": sku_code
#             })
#             item_doc.save()
#             processed_data.append(row + ["Inserted"])

#     return processed_data