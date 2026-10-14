import random
import string

import frappe
from frappe.utils import now_datetime

# Names are MOP-YYMM-XXXXXX, e.g. MOP-2609-4K7B2Q. The YYMM segment partitions the
# keyspace by month, so a name freed by a deleted operation can never be reissued in a
# later month -- and no new name can ever collide with a legacy MOP-XXXXX name.
MOP_CODE_LEN = 6
MOP_ALPHABET = string.ascii_uppercase + string.digits  # 36**6 = 2,176,782,336 per month


def generate_unique_alphanumeric(prefix):
    while True:
        random_code = "".join(random.choices(MOP_ALPHABET, k=MOP_CODE_LEN))

        # Check if it already exists
        if not frappe.db.exists("Manufacturing Operation", f"{prefix}{random_code}"):
            return random_code


def autoname(doc, method=None):
    # now_datetime() so the month follows the site timezone, not the server's
    prefix = f"MOP-{now_datetime().strftime('%y%m')}-"
    doc.name = prefix + generate_unique_alphanumeric(prefix)
    return
