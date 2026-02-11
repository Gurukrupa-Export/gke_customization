import frappe


def execute():
    gc_ratio_master = frappe.db.get_all(
        "GC Ratio",
        {"parent": "GC Ratio Master", "type": ["is", "not set"]},
        ["metal_to_gold_ratio_group", "name"],
    )
    for row in gc_ratio_master:
        range_text = row.metal_to_gold_ratio_group.strip()
        if "-" in range_text:
            lower, upper = [float(x.strip()) for x in range_text.split("-")]
            frappe.db.set_value(
                "GC Ratio",
                row.name,
                {"type": "Range", "range_1": lower, "range_2": upper},
            )

        elif "Above" in range_text:
            frappe.db.set_value(
                "GC Ratio",
                row.name,
                {
                    "type": "Above",
                    "range_1": float(range_text.split("Above")[1].strip()),
                },
            )
        elif "Below" in range_text:
            frappe.db.set_value(
                "GC Ratio",
                row.name,
                {
                    "type": "Below",
                    "range_1": float(range_text.split("Below")[1].strip()),
                },
            )
