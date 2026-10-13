from frappe.utils import getdate

from gke_customization.overrides.salary_structure_assignment import (
    SLIP_ONLY_FORMULA_FIELDS,
)


def seed_slip_only_formula_fields(doc, method=None):
    """Seed Salary Slip-only formula fields with safe defaults if unset."""
    numeric_fields = [
        fieldname
        for fieldname in SLIP_ONLY_FORMULA_FIELDS
        if fieldname != "custom_month"
    ]

    for fieldname in numeric_fields:
        if doc.get(fieldname) is None:
            doc.set(fieldname, 0)

    # Default to the salary slip month when not already populated.
    if doc.get("custom_month") is None and doc.start_date:
        doc.custom_month = getdate(doc.start_date).month
