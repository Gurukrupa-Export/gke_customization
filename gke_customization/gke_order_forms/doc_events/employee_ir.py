import frappe
import random
import string

def generate_unique_alphanumeric():
    while True:
        # Ensure at least one letter and one number
        letters = random.choices(string.ascii_uppercase, k=2)  # At least 2 letters
        digits = random.choices(string.digits, k=3)  # At least 3 numbers
        random_code = ''.join(random.sample(letters + digits, 5))  # Shuffle & combine

        # Check if it already exists
        existing_doc = frappe.get_value("Employee IR", {"name": f"Employee IR - {random_code}"}, "name")

        if not existing_doc:  # If unique, return it
            return random_code

def autoname(doc,method=None):
    unique_code = generate_unique_alphanumeric()
    doc.name = f"Employee-IR-{unique_code}"
    return
