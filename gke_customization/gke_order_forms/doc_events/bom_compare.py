import frappe
import json
from frappe.model import no_value_fields, table_fields
from frappe.model.document import Document

@frappe.whitelist()
def get_bom_diff(bom1, bom2):
    from frappe.model import table_fields

    if bom1 == bom2:
        frappe.throw(
            ("BOM 1 {0} and BOM 2 {1} should not be same").format(frappe.bold(bom1), frappe.bold(bom2))
        )

    doc1 = frappe.get_doc("BOM", bom1)
    doc2 = frappe.get_doc("BOM", bom2)

    # Fields to be shown at the parent level
    parent_fields = {"item_category","item_subcategory","product_size","sizer_type","detachable","metal_target","diamond_target",
                     "metal_type","metal_colour","metal_touch","metal_purity","setting_type","sub_setting_type1","sub_setting_type2",
                     "qty","gemstone_type","gemstone_quality","stone_changeable","chain","chain_type","chain_thickness","chain_length","chain_weight",
                     "lock_type","capganthan","feature","back_chain","back_chain_size","back_belt","back_belt_length","distance_between_kadi_to_mugappu",
                     "space_between_mugappu","number_of_ant","count_of_spiral_turns","kadi_to_mugappu","back_belt_patti","rhodium","enamal","black_beed","black_beed_line",
                     "charm","two_in_one","back_side_size"
                     "metal_weight","diamond_weight","finding_weight_","gemstone_weight","total_diamond_weight_in_gms","total_gemstone_weight_in_gms","gross_weight","metal_and_finding_weight","other_weight"}

    # Child tables and their specific fields to include
    child_table_fields = {
        "metal_detail": {"metal_type","metal_touch","metal_purity","metal_colour","quantity"},
        "diamond_detail":{"diamond_type","stone_shape","sub_setting_type","diamond_sieve_size","sieve_size_range","size_in_mm","pcs","weight_per_pcs","quantity"},
        "finding_detail":{"metal_type","metal_touch","metal_purity","metal_colour","finding_category","finding_type","finding_size","qty","quantity"},
        "gemstone_detail":{"gemstone_type","cut_or_cab","stone_shape","gemstone_quality","gemstone_size","sub_setting_type","pcs","quantity"}

    }

    out = frappe._dict(changed=[], row_changed=[], added=[], removed=[], all_values={})

    meta = doc1.meta

    identifiers = {
        "metal_detail": "metal_touch",
        "diamond_detail": "diamond_sieve_size",
        "finding_detail":"finding_size",
        "gemstone_detail":"gemstone_type"
    }

    # Include all parent field values
    for field in parent_fields:
        out.all_values[field] = {
            "bom1": doc1.get(field),
            "bom2": doc2.get(field)
        }

    # Include all child table values for specified fields
    for df in meta.fields:
        if df.fieldtype in table_fields and df.fieldname in child_table_fields:
            identifier_field = identifiers.get(df.fieldname, "name")
            allowed_fields = child_table_fields[df.fieldname]

            old_row_by_identifier = {d.get(identifier_field): d for d in doc1.get(df.fieldname)}
            new_row_by_identifier = {d.get(identifier_field): d for d in doc2.get(df.fieldname)}

            child_values = []

            for key in set(old_row_by_identifier.keys()).union(new_row_by_identifier.keys()):
                old_row = old_row_by_identifier.get(key, frappe._dict())
                new_row = new_row_by_identifier.get(key, frappe._dict())

                row_data = {
                    identifier_field: key,  # Show the field name instead of generic "identifier"
                    "values": {
                        field: {
                            "bom1": old_row.get(field),
                            "bom2": new_row.get(field)
                        } for field in allowed_fields
                    }
                }
                child_values.append(row_data)

            out.all_values[df.fieldname] = child_values

    return out
