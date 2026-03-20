import frappe
import requests, json
from frappe.utils import flt


# ------------------------------------------------------------------
# Stage 1: Send to Item & BOM Creation
# ------------------------------------------------------------------
@frappe.whitelist()
def send_to_item_bom_creation(docname):
    """
    Transition Product Return Form from Draft to 'Item & BOM Creation' stage.

    Validations:
        - Document must be in Draft status
        - is_jewlex_credit_note must be checked
        - At least one child row must have a tag_no

    Updates:
        - status = 'Item & BOM Creation'
        - Saves document
    """
    doc = frappe.get_doc("Product Return Form", docname)

    if doc.status != "Draft":
        frappe.throw(f"Status must be Draft to send to Item & BOM Creation. Current status: {frappe.bold(doc.status)}")

    if not doc.is_jewlex_credit_note:
        frappe.throw("This action is only available for Jewlex Credit Notes.")

    has_tag = any(row.tag_no for row in doc.items)
    if not has_tag:
        frappe.throw("At least one item row must have a Tag No before proceeding.")

    doc.status = "Item & BOM Creation"

    error_dict = {}
    success_dict = {}

    for row in doc.items:
        tag_no = row.tag_no if hasattr(row, 'tag_no') else None
        row_idx = row.idx if hasattr(row, 'idx') else None

        if not tag_no:
            error_key = row_idx or row.name or "unknown"
            error_dict[error_key] = "Tag No is missing"
            continue

        try:
            data = get_data_from_jwelex(tag_no)
            
            if data and data.get("customer_info", {}).get("customer_id"):  # assuming get_data_from_jwelex returns dict / None / falsy on failure
                success_dict[tag_no] = data
            else:
                error_dict[tag_no] = "No data returned for this tag"
                
        except Exception as e:
            # You can also do: frappe.log_error(...) here if you want traceability
            error_key = tag_no if tag_no else (row_idx or "row-error")
            error_dict[error_key] = f"Failed to fetch data: {str(e)}"

    if error_dict:
        frappe.log_error(
            message="Following items have errors: " + ", ".join([f"{k}: {v}" for k, v in error_dict.items()]), 
            title="Product Return Form Item Errors",
            reference_doctype="Product Return Form",
            reference_name=docname,
        )

    doc.jwelex_credit_note_data = None
    doc.jwelex_credit_note_data = frappe.as_json(success_dict)
    doc.save(ignore_permissions=True)
    frappe.msgprint("Status updated to Item & BOM Creation.", indicator="yellow", alert=True)

    return doc.status


# ------------------------------------------------------------------
# Stage 2: Update Items from Tag (Auto-link items)
# ------------------------------------------------------------------
@frappe.whitelist()
def update_items_from_tag(docname):
    """
    For each child row in Product Return Form Item that has a tag_no,
    find the matching Item where item.old_tag_no == child.tag_no
    and set child.item_code = item.name.

    After successful update, transitions status to 'Send to Pricing'
    and triggers automatic pricing calculation.

    Validations:
        - Document must be in 'Item & BOM Creation' status
        - Each tag_no must match exactly one enabled Item
    """
    doc = frappe.get_doc("Product Return Form", docname)

    if doc.status != "Item & BOM Creation":
        frappe.throw(
            f"Status must be 'Item & BOM Creation' to update items from tag. "
            f"Current status: {frappe.bold(doc.status)}"
        )

    updated_count = 0
    not_found_tags = []

    for row in doc.items:
        if not row.tag_no:
            continue

        # Find Item where old_tag_no matches child.tag_no
        matching_items = frappe.get_all(
            "Item",
            filters={"old_tag_no": row.tag_no, "disabled": 0},
            fields=["name", "master_bom"],
            limit=1,
        )

        if not matching_items:
            not_found_tags.append(f"Row {row.idx}: Tag No {frappe.bold(row.tag_no)}")
            continue

        item_name = matching_items[0].name
        master_bom = matching_items[0].master_bom
        row.item_code = item_name

        if not master_bom:
            # Also fetch the BOM for this item (latest active default BOM)
            default_bom = frappe.db.get_value(
                "BOM",
                {"item": item_name, "is_active": 1, "is_default": 1},
                "name",
            )
            if default_bom:
                master_bom = default_bom
        
        if not master_bom:
            frappe.throw(
                f"No BOM found for Item {frappe.bold(item_name)}"
            )
        row.bom = master_bom

        updated_count += 1

    if not_found_tags:
        frappe.throw(
            "No matching Item found for the following Tag Numbers:<br>"
            + "<br>".join(not_found_tags)
        )

    if updated_count == 0:
        frappe.throw("No rows with Tag No found to update.")

    # Transition to pricing stage
    doc.status = "Send to Pricing"

    # Trigger pricing calculation
    trigger_pricing_calculation(doc)

    doc.save(ignore_permissions=True)
    frappe.msgprint(
        f"Successfully linked {updated_count} item(s) from Tag No. "
        f"Pricing calculation completed.",
        indicator="green",
        alert=True,
    )

    return doc.status


# ------------------------------------------------------------------
# Stage 3: Trigger Pricing Calculation (BOM-based)
# ------------------------------------------------------------------
def trigger_pricing_calculation(doc):
    """
    BOM-based pricing calculation for Jewelex credit notes.
    Routes to the correct calculation logic based on credit_note_type
    and credit_note_subtype, mirroring the validate() dispatch in
    ProductReturnForm.

    Calculation mapping:
        (Actual, Sale Without Payment-Actual)     → _calc_bom_standard
        (Actual, Sale With Payment-Actual)         → _calc_bom_standard
        (Repair, QC Fail-Repair)                   → _calc_bom_standard
        (Repair, Physical-Repair)                  → _calc_bom_physical_repair
        (Consignment, Finish Goods-Consignment)    → _calc_bom_standard
        (Consignment, Raw Material-Consignment)    → _calc_bom_raw_material_consignment
    """
    if doc.status in ["Draft", "Item & BOM Creation"]:
        return

    credit_note_key = (doc.credit_note_type, doc.credit_note_subtype)

    calc_mapping = {
        ("Actual", "Sale Without Payment-Actual"): _calc_bom_pcpm,
        ("Actual", "Sale With Payment-Actual"): _calc_bom_bbpm,
        ("Repair", "QC Fail-Repair"): _calc_bom_pcpm,
        ("Repair", "Physical-Repair"): _calc_bom_physical_repair,
        ("Consignment", "Finish Goods-Consignment"): _calc_bom_pcpm,
        ("Consignment", "Raw Material-Consignment"): _calc_bom_raw_material_consignment,
    }

    calc_fn = calc_mapping.get(credit_note_key)
    if not calc_fn:
        frappe.throw(
            f"Pricing calculation not supported for credit note type: "
            f"{frappe.bold(doc.credit_note_type)} / {frappe.bold(doc.credit_note_subtype)}"
        )

    calc_fn(doc)

    # Recalculate taxes and totals using existing class methods
    doc.calculate_taxes_and_totals()
    doc.set_total_in_words()


# ==================================================================
# SHARED HELPERS
# ==================================================================
def _get_common_setup(doc):
    """Setup variables common to all BOM-based calculations."""
    gold_gst_rate = flt(
        frappe.db.get_single_value("Jewellery Settings", "gold_gst_rate") or 0
    )
    customer_group = frappe.db.get_value("Customer", doc.customer, "customer_group")
    gemstone_price_list_type = frappe.db.get_value(
        "Customer", doc.customer, "custom_gemstone_price_list_type"
    )
    return gold_gst_rate, customer_group, gemstone_price_list_type


def _calc_metal_amount(doc, bom_doc, mc_name, gold_gst_rate):
    """
    Calculate metal amount from BOM metal_detail.
    Returns (metal_total, wastage_total).
    """
    row_metal_amt_total = 0
    row_wastage_amt_total = 0

    if not hasattr(bom_doc, "metal_detail"):
        return row_metal_amt_total, row_wastage_amt_total

    for md_row in bom_doc.metal_detail:
        sub_info = frappe.db.get_value(
            "Making Charge Price Item Subcategory",
            {
                "parent": mc_name,
                "subcategory": bom_doc.item_subcategory,
            },
            [
                "rate_per_gm",
                "rate_per_pc",
                "wastage",
                "rate_per_gm_threshold",
            ],
            as_dict=True,
        )

        if not sub_info:
            frappe.throw(
                f"Making Charge Subcategory {bom_doc.item_subcategory} not found"
            )

        threshold = flt(sub_info.rate_per_gm_threshold) or 2
        weight_for_calc = flt(bom_doc.metal_and_finding_weight)

        if weight_for_calc < threshold:
            wastage_rate = 0
        else:
            wastage_rate = flt(sub_info.wastage) / 100

        customer_metal_purity = frappe.db.get_value(
            "Metal Criteria",
            {
                "parent": doc.customer,
                "metal_type": md_row.metal_type,
                "metal_touch": md_row.metal_touch,
            },
            "metal_purity",
        )

        if not customer_metal_purity:
            frappe.throw("Metal Purity not found for Customer")

        calculated_gold_rate = (
            flt(customer_metal_purity) * doc.gold_rate_with_gst
        ) / (100 + gold_gst_rate)

        line_gold_amt = round(calculated_gold_rate * md_row.quantity, 2)
        line_wastage_amt = line_gold_amt * wastage_rate

        row_metal_amt_total += line_gold_amt
        row_wastage_amt_total += line_wastage_amt

    return row_metal_amt_total, row_wastage_amt_total


def _calc_finding_amount(doc, bom_doc, mc_name, gold_gst_rate):
    """
    Calculate finding amount from BOM finding_detail.
    Returns (finding_total, wastage_total).
    """
    row_finding_amt_total = 0
    row_wastage_amt_total = 0

    if not hasattr(bom_doc, "finding_detail"):
        return row_finding_amt_total, row_wastage_amt_total

    for fd_row in bom_doc.finding_detail:
        find = frappe.db.get_all(
            "Making Charge Price Finding Subcategory",
            filters={
                "parent": mc_name,
                "subcategory": fd_row.finding_type,
            },
            fields=["rate_per_gm", "rate_per_pc"],
            limit=1,
        )

        # Fallback to Item Subcategory
        if not find:
            find = frappe.db.get_all(
                "Making Charge Price Item Subcategory",
                filters={
                    "parent": mc_name,
                    "subcategory": bom_doc.item_subcategory,
                },
                fields=["rate_per_gm", "rate_per_pc"],
                limit=1,
            )

        if not find:
            frappe.throw(
                f"Finding rate not found for {fd_row.finding_type}"
            )

        find_info = find[0]

        customer_metal_purity = frappe.db.sql(
            f"""select metal_purity from `tabMetal Criteria`
            where parent = '{doc.customer}'
            and metal_type = '{fd_row.metal_type}'
            and metal_touch = '{fd_row.metal_touch}'""",
            as_dict=True,
        )[0]["metal_purity"]

        calculated_gold_rate = (
            float(customer_metal_purity) * doc.gold_rate_with_gst
        ) / (100 + int(gold_gst_rate))

        line_finding_rate = round(calculated_gold_rate, 2)
        line_finding_amt = round(line_finding_rate * fd_row.quantity, 2)

        finding_weight = getattr(bom_doc, "metal_and_finding_weight", None)
        if finding_weight is not None and finding_weight < 2:
            wastage_rate = 0
        else:
            wastage_rate = find_info.get("wastage", 0) / 100.0

        row_finding_amt_total += line_finding_amt
        row_wastage_amt_total += wastage_rate * line_finding_amt

    return row_finding_amt_total, row_wastage_amt_total


def _calc_making_from_bom(doc, bom_doc, mc_name):
    """
    Calculate making charges from BOM metal_detail + finding_detail.
    Used for Physical Repair type (accumulates from BOM, not invoice).
    Returns making_total.
    """
    row_making_amt_total = 0
    # frappe.msgprint(f"MC Name: {mc_name}")
    if hasattr(bom_doc, "metal_detail"):
        for md_row in bom_doc.metal_detail:
            sub_info = frappe.db.get_value(
                "Making Charge Price Item Subcategory",
                {
                    "parent": mc_name,
                    "subcategory": bom_doc.item_subcategory,
                },
                [
                    "rate_per_gm",
                    "rate_per_pc",
                    "rate_per_gm_threshold",
                ],
                as_dict=True,
            )

            if not sub_info:
                continue

            threshold = flt(sub_info.rate_per_gm_threshold) or 2
            weight_for_calc = flt(bom_doc.metal_and_finding_weight)

            if weight_for_calc < threshold:
                making_rate = flt(sub_info.rate_per_pc)
                line_making_amt = making_rate
            else:
                making_rate = flt(sub_info.rate_per_gm)
                line_making_amt = making_rate * md_row.quantity

            row_making_amt_total += line_making_amt

    if hasattr(bom_doc, "finding_detail"):
        for fd_row in bom_doc.finding_detail:
            find = frappe.db.get_all(
                "Making Charge Price Finding Subcategory",
                filters={
                    "parent": mc_name,
                    "subcategory": fd_row.finding_type,
                },
                fields=["rate_per_gm", "rate_per_pc"],
                limit=1,
            )

            if not find:
                find = frappe.db.get_all(
                    "Making Charge Price Item Subcategory",
                    filters={
                        "parent": mc_name,
                        "subcategory": bom_doc.item_subcategory,
                    },
                    fields=["rate_per_gm", "rate_per_pc"],
                    limit=1,
                )

            if not find:
                continue

            find_info = find[0]
            finding_weight = getattr(bom_doc, "metal_and_finding_weight", None)

            if finding_weight is not None and finding_weight < 2:
                making_rate = find_info.get("rate_per_pc", 0)
                line_making_amt = making_rate
            else:
                making_rate = find_info.get("rate_per_gm", 0)
                line_making_amt = making_rate * fd_row.quantity

            row_making_amt_total += line_making_amt

    return row_making_amt_total


def _calc_diamond_amount(doc, bom_doc, customer_group, use_handling_charges=False):
    """
    Calculate diamond amount from BOM diamond_detail.

    Args:
        use_handling_charges: If True (Physical-Repair), apply outright/outwork
            handling charges to diamond rate. If False (BBPM/PCPM), use base rate only.
    Returns diamond_total.
    """
    row_diamond_amt_total = 0

    if not hasattr(bom_doc, "diamond_detail"):
        return row_diamond_amt_total

    for diamond_row in bom_doc.diamond_detail:
        customer_price_list = frappe.db.sql(
            """
            SELECT diamond_price_list
            FROM `tabDiamond Price List Table`
            WHERE parent = %s AND diamond_shape = %s
            """,
            (doc.customer, diamond_row.stone_shape),
            as_dict=True,
        )

        if not customer_price_list:
            continue

        diamond_price_list = customer_price_list[0].diamond_price_list

        common_filters = {
            "price_list": "Standard Selling",
            "price_list_type": diamond_price_list,
            "customer": doc.customer,
            "diamond_type": diamond_row.diamond_type,
            "stone_shape": diamond_row.stone_shape,
            "diamond_quality": diamond_row.quality,
        }

        weight_per_piece = (
            diamond_row.quantity / diamond_row.pcs
            if diamond_row.pcs else 0
        )
        weight_per_piece = round(weight_per_piece, 3)

        diamond_price_row = None

        if diamond_price_list == "Sieve Size Range":
            diamond_price_row = frappe.db.get_value(
                "Diamond Price List",
                {**common_filters, "sieve_size_range": diamond_row.sieve_size_range},
                [
                    "rate",
                    "outright_handling_charges_rate",
                    "outwork_handling_charges_rate",
                    "outright_handling_charges_in_percentage",
                    "outwork_handling_charges_in_percentage",
                    "supplier_fg_purchase_rate",
                ],
                as_dict=True,
            )

        elif diamond_price_list == "Weight (in cts)":
            filter_conditions = " AND ".join(
                [f"{key} = %s" for key in common_filters]
            )
            rate_result = frappe.db.sql(
                f"""
                SELECT
                    name,
                    rate,
                    outright_handling_charges_rate,
                    outright_handling_charges_in_percentage,
                    outwork_handling_charges_rate,
                    outwork_handling_charges_in_percentage,
                    supplier_fg_purchase_rate
                FROM `tabDiamond Price List`
                WHERE {filter_conditions}
                AND %s BETWEEN from_weight AND to_weight
                LIMIT 1
                """,
                list(common_filters.values()) + [weight_per_piece],
                as_dict=True,
            )
            diamond_price_row = rate_result[0] if rate_result else None

        elif diamond_price_list == "Size (in mm)":
            diamond_price_row = frappe.db.get_value(
                "Diamond Price List",
                {**common_filters, "diamond_size_in_mm": diamond_row.diamond_sieve_size},
                [
                    "rate",
                    "outright_handling_charges_rate",
                    "outwork_handling_charges_rate",
                    "outright_handling_charges_in_percentage",
                    "outwork_handling_charges_in_percentage",
                    "supplier_fg_purchase_rate",
                ],
                as_dict=True,
            )

        if not diamond_price_row:
            continue

        # -------------------------------------------------
        # RATE CALCULATION
        # -------------------------------------------------
        base_rate = diamond_price_row.get("rate", 0)

        if use_handling_charges:
            # Physical-Repair: apply outright/outwork handling
            outright_rate = diamond_price_row.get("outright_handling_charges_rate", 0)
            outright_pct = diamond_price_row.get("outright_handling_charges_in_percentage", 0)
            is_customer_item = getattr(diamond_row, "is_customer_item", False)

            if is_customer_item:
                total_rate = outright_rate or (base_rate * (outright_pct / 100))
            else:
                if outright_rate:
                    total_rate = base_rate + outright_rate
                else:
                    total_rate = base_rate + (base_rate * (outright_pct / 100))
        else:
            # BBPM/PCPM: use base rate only
            total_rate = base_rate

        # -------------------------------------------------
        # COMPANY & CUSTOMER GROUP LOGIC
        # -------------------------------------------------
        if (
            doc.company == "KG GK Jewellers Private Limited"
            and customer_group == "Internal"
        ):
            diamond_rate = diamond_row.se_rate
            quantity = round(diamond_row.quantity, 3)
            diamond_amount = round(quantity * diamond_rate, 2)

        elif (
            doc.company == "Gurukrupa Export Private Limited"
            and customer_group == "Internal"
        ):
            diamond_rate = diamond_price_row.get("supplier_fg_purchase_rate", 0)
            quantity = round(diamond_row.quantity, 3)
            diamond_amount = round(quantity * diamond_rate, 2)

        else:
            diamond_rate = round(total_rate, 2)
            quantity = round(diamond_row.quantity, 3)
            diamond_amount = round(quantity * diamond_rate, 2)

        row_diamond_amt_total += diamond_amount

    return row_diamond_amt_total


def _calc_gemstone_amount(doc, bom_doc, customer_group, gemstone_price_list_type):
    """Calculate gemstone amount from BOM gemstone_detail. Returns gemstone_total."""
    row_gemstone_amt_total = 0

    if not (hasattr(bom_doc, "gemstone_detail") and bom_doc.gemstone_detail):
        return row_gemstone_amt_total

    def calculate_percentage_amount(rate, base_value):
        return round((flt(rate) / 100) * flt(base_value), 2)

    for gs_row in bom_doc.gemstone_detail:

        # Internal customer – Company specific
        if doc.company == "Gurukrupa Export Private Limited" and customer_group == "Internal":
            rate = gs_row.fg_purchase_rate
            row_gemstone_amt_total += calculate_percentage_amount(rate, gs_row.quantity)
            continue

        if doc.company == "KG GK Jewellers Private Limited" and customer_group == "Internal":
            rate = gs_row.se_rate
            row_gemstone_amt_total += calculate_percentage_amount(rate, gs_row.quantity)
            continue

        # Fixed Price List – Non-Retail
        if gemstone_price_list_type == "Fixed" and customer_group != "Retail":
            price_list = frappe.get_all(
                "Gemstone Price List",
                filters={
                    "customer": doc.customer,
                    "price_list_type": gemstone_price_list_type,
                    "gemstone_grade": gs_row.gemstone_grade,
                    "cut_or_cab": gs_row.cut_or_cab,
                    "gemstone_type": gs_row.gemstone_type,
                    "stone_shape": gs_row.stone_shape,
                },
                fields=["rate", "handling_rate"],
                limit=1,
            )

            if not price_list:
                frappe.throw("No Gemstone Price List found")

            rate = price_list[0].rate
            row_gemstone_amt_total += calculate_percentage_amount(rate, gs_row.quantity)
            continue

        # Retail Customer – Fixed Price
        if customer_group == "Retail":
            price_list = frappe.get_all(
                "Gemstone Price List",
                filters={
                    "is_retail_customer": 1,
                    "price_list_type": gemstone_price_list_type,
                    "gemstone_grade": gs_row.gemstone_grade,
                    "cut_or_cab": gs_row.cut_or_cab,
                    "gemstone_type": gs_row.gemstone_type,
                    "stone_shape": gs_row.stone_shape,
                },
                fields=["rate", "outwork_handling_charges_rate"],
                limit=1,
            )

            if not price_list:
                frappe.throw("No Retail Gemstone Price List found")

            rate = (
                price_list[0].outwork_handling_charges_rate
                if gs_row.is_customer_item
                else price_list[0].rate
            )
            row_gemstone_amt_total += calculate_percentage_amount(rate, gs_row.quantity)
            continue

        # Diamond Range – Non-Retail
        if gemstone_price_list_type == "Diamond Range" and customer_group != "Retail":
            price_list = frappe.get_all(
                "Gemstone Price List",
                filters={
                    "customer": doc.customer,
                    "price_list_type": gemstone_price_list_type,
                    "cut_or_cab": gs_row.cut_or_cab,
                    "gemstone_grade": gs_row.gemstone_grade,
                    "from_gemstone_pr_rate": ["<=", gs_row.gemstone_pr],
                    "to_gemstone_pr_rate": [">=", gs_row.gemstone_pr],
                },
                fields=["name"],
                limit=1,
            )

            if not price_list:
                frappe.throw("Gemstone Diamond Range price list not found")

            price_list_doc = frappe.get_doc("Gemstone Price List", price_list[0].name)

            rate = 0.0
            for mul in price_list_doc.gemstone_multiplier:
                if (
                    mul.gemstone_type == gs_row.gemstone_type
                    and flt(mul.from_weight) <= flt(gs_row.gemstone_pr) <= flt(mul.to_weight)
                ):
                    if gs_row.is_customer_item:
                        rate = {
                            "Precious": mul.outwork_precious_percentage,
                            "Semi-Precious": mul.outwork_semi_precious_percentage,
                            "Synthetic": mul.outwork_synthetic_percentage,
                        }.get(gs_row.gemstone_quality, 0)
                    else:
                        rate = {
                            "Precious": mul.precious_percentage,
                            "Semi-Precious": mul.semi_precious_percentage,
                            "Synthetic": mul.synthetic_percentage,
                        }.get(gs_row.gemstone_quality, 0)
                    break

            row_gemstone_amt_total += calculate_percentage_amount(rate, gs_row.gemstone_pr)
            continue

        # Diamond Range – Retail
        if gemstone_price_list_type == "Diamond Range" and customer_group == "Retail":
            price_list = frappe.get_all(
                "Gemstone Price List",
                filters={
                    "is_retail_customer": 1,
                    "price_list_type": gemstone_price_list_type,
                    "cut_or_cab": gs_row.cut_or_cab,
                    "gemstone_grade": gs_row.gemstone_grade,
                    "from_gemstone_pr_rate": ["<=", gs_row.gemstone_pr],
                    "to_gemstone_pr_rate": [">=", gs_row.gemstone_pr],
                },
                fields=["name"],
                limit=1,
            )

            if not price_list:
                frappe.throw("Retail Gemstone Diamond Range price list not found")

            price_list_doc = frappe.get_doc("Gemstone Price List", price_list[0].name)

            rate = 0.0
            for mul in price_list_doc.get("gemstone_multiplier", []):
                if (
                    mul.gemstone_type == gs_row.gemstone_type
                    and flt(mul.from_weight) <= flt(gs_row.gemstone_pr) <= flt(mul.to_weight)
                ):
                    rate = {
                        "Precious": mul.precious_percentage,
                        "Semi-Precious": mul.semi_precious_percentage,
                        "Synthetic": mul.synthetic_percentage,
                    }.get(gs_row.gemstone_quality, 0)
                    break

            row_gemstone_amt_total += calculate_percentage_amount(rate, gs_row.gemstone_pr)

    return row_gemstone_amt_total


def _get_mc_name(doc, bom_doc):
    """Lookup Making Charge Price for the given doc and BOM."""
    mc = frappe.get_all(
        "Making Charge Price",
        filters={
            "customer": doc.customer,
            "metal_type": bom_doc.metal_type,
            "setting_type": bom_doc.setting_type,
            "from_gold_rate": ["<=", doc.gold_rate_with_gst],
            "to_gold_rate": [">=", doc.gold_rate_with_gst],
            "metal_touch": bom_doc.metal_touch,
        },
        fields=["name"],
        limit=1,
    )

    if not mc:
        frappe.throw(
            f"Create a valid Making Charge Price for "
            f"{bom_doc.metal_type} / {bom_doc.metal_touch}"
        )

    return mc[0]["name"]


# ==================================================================
# CALCULATION TYPE: STANDARD (BBPM)
# ==================================================================
def _calc_bom_bbpm(doc):
    """
    - Gold rate should be taken as the current day rate. (on the date of the creditnote).
    - Diamond and gemstone rates should be applied as per the updated live price list.
    - Making charges must be applied exactly as per the original invoice rate or as selected in the form.
    """
    gold_gst_rate, customer_group, gemstone_price_list_type = _get_common_setup(doc)

    total_taxable = 0
    total_gst = 0
    doc.sales_taxes_and_charges = []

    for row in doc.items:
        if not row.item_code or not row.bom:
            continue

        bom_doc = frappe.get_doc("BOM", row.bom)
        mc_name = _get_mc_name(doc, bom_doc)

        row_metal_amt, _ = _calc_metal_amount(doc, bom_doc, mc_name, gold_gst_rate)
        row_finding_amt, _ = _calc_finding_amount(doc, bom_doc, mc_name, gold_gst_rate)
        row_diamond_amt = _calc_diamond_amount(doc, bom_doc, customer_group, use_handling_charges=False)
        row_gemstone_amt = _calc_gemstone_amount(doc, bom_doc, customer_group, gemstone_price_list_type)

        row.metal_amount = row_metal_amt
        row.finding_amount = row_finding_amt
        row.diamond_amount = row_diamond_amt
        row.gemstone_amount = row_gemstone_amt

        # Making charges from original Sales Invoice
        # Find matching item in jwelex_data
        tag_no = row.get("tag_no")
        making_amount = 0
        if tag_no:
            jwelex_data = doc.get("jwelex_credit_note_data")
            if not jwelex_data:
                frappe.throw(f"JWELEX Data is required for {frappe.bold(doc.credit_note_subtype)} calculation")
            jwelex_data = json.loads(jwelex_data)
            matching_item = jwelex_data.get(tag_no)
            
            if not matching_item:
                frappe.throw(f"Tag No {tag_no} not found in JWELEX Data")
            
            # frappe.throw(f"Matching Item: {matching_item}")

            charges_info = matching_item.get("charges_info", {})
            making_amount = charges_info.get("chain_making_amount", 0) + charges_info.get("metal_making_amount", 0)

            # Making charges Type
            if doc.making_charges_type == "Without":
                making_amount = 0
            elif doc.making_charges_type == "With":
                making_amount = making_amount
            elif doc.making_charges_type == "Half":
                making_amount = making_amount * 0.5
            else:
                making_amount = 0

            row.making_amount = making_amount

        row.rate = (
            row.metal_amount
            + row.finding_amount
            + row.diamond_amount
            + row.gemstone_amount
            + making_amount
        )
        row.amount = row.rate * row.qty

        total_taxable += row.amount

    doc.total_taxes_and_charges = total_gst
    doc.grand_total = total_taxable + total_gst

# ==================================================================
# CALCULATION TYPE: PCPM, QC Fail-Repair, Finish Goods-Consignment
# ==================================================================
def _calc_bom_pcpm(doc):
    """
    same product rate mentioned in the invoice must be used
    No new or revised rates should be applied.
    """

    jwelex_data = doc.get("jwelex_credit_note_data")
    if not jwelex_data:
        frappe.throw(f"JWELEX Data is required for {frappe.bold(doc.credit_note_subtype)} calculation")
    
    jwelex_data = json.loads(jwelex_data)

    # TODO: Implement PCPM calculation logic
    # Use jwelex_data to calculate rates
    # Apply same product rate as invoice
    # No new or revised rates
    
    for row_item in doc.items:
        tag_no = row_item.get("tag_no")
        if not tag_no:
            continue
        
        # Find matching item in jwelex_data
        matching_item = jwelex_data.get(tag_no)
        
        if not matching_item:
            frappe.throw(f"Tag No {tag_no} not found in JWELEX Data")
        
        # frappe.throw(f"Matching Item: {matching_item}")

        charges_info = matching_item.get("charges_info", {})
        making_amount = charges_info.get("chain_making_amount", 0) + charges_info.get("metal_making_amount", 0)
        hm_charges = charges_info.get("hm_charges", 0)
        certificate_charges = charges_info.get("certificate_charges", 0)

        materials = matching_item.get("materials", {})
        diamond_details = materials.get("diamond_details", [])
        finding_details = materials.get("finding_details", [])
        metal_details = materials.get("metal_details", [])
        other_details = materials.get("other_details", [])
        stone_details = materials.get("stone_details", [])


        metal_amount = 0
        for metal in metal_details:
            metal_amount += metal.get("Amount", 0)
            
        diamon_amount = 0
        for diamond in diamond_details:
            diamon_amount += diamond.get("Amount", 0)
        
        finding_amount = 0
        for finding in finding_details:
            finding_amount += finding.get("Amount", 0)
        
        stone_amount = 0
        for stone in stone_details:
            stone_amount += stone.get("Amount", 0)
        
        other_amount = 0
        for other in other_details:
            other_amount += other.get("Amount", 0)


        # Making charges Type
        if doc.making_charges_type == "Without":
            making_amount = 0
        elif doc.making_charges_type == "With":
            making_amount = making_amount
        elif doc.making_charges_type == "Half":
            making_amount = making_amount * 0.5
        else:
            making_amount = 0
        
        row_item.metal_amount = metal_amount
        row_item.diamond_amount = diamon_amount
        row_item.finding_amount = finding_amount
        row_item.stone_amount = stone_amount
        row_item.other_material_amount = other_amount
        row_item.making_amount = making_amount
        row_item.hallmarking_amount = hm_charges
        row_item.certification_amount = certificate_charges
        
        total_amount = metal_amount + diamon_amount + finding_amount + stone_amount + other_amount + making_amount + hm_charges + certificate_charges
        
        row_item.rate = total_amount / row_item.get("qty", 1)
        row_item.amount = total_amount
        

# ==================================================================
# CALCULATION TYPE: PHYSICAL REPAIR
# ==================================================================
def _calc_bom_physical_repair(doc):
    """
    Physical Repair BOM-based calculation.
    Same as standard BUT:
      - Making charges accumulated from BOM (not invoice)
      - Diamond has outright/outwork handling charges applied

    Used for:
      - Physical-Repair
    """
    gold_gst_rate, customer_group, gemstone_price_list_type = _get_common_setup(doc)

    total_taxable = 0
    total_gst = 0
    doc.sales_taxes_and_charges = []

    for row in doc.items:
        if not row.item_code or not row.bom:
            continue

        bom_doc = frappe.get_doc("BOM", row.bom)
        mc_name = _get_mc_name(doc, bom_doc)

        row_metal_amt, _ = _calc_metal_amount(doc, bom_doc, mc_name, gold_gst_rate)
        row_finding_amt, _ = _calc_finding_amount(doc, bom_doc, mc_name, gold_gst_rate)
        row_diamond_amt = _calc_diamond_amount(doc, bom_doc, customer_group, use_handling_charges=True)
        row_gemstone_amt = _calc_gemstone_amount(doc, bom_doc, customer_group, gemstone_price_list_type)

        row.metal_amount = row_metal_amt
        row.finding_amount = row_finding_amt
        row.diamond_amount = row_diamond_amt
        row.gemstone_amount = row_gemstone_amt

        # Making charges accumulated from BOM
        row_making_amt_total = _calc_making_from_bom(doc, bom_doc, mc_name)

        # Making charges Type
        if doc.making_charges_type == "Without":
            row.making_amount = 0
        elif doc.making_charges_type == "With":
            row.making_amount = row_making_amt_total
        elif doc.making_charges_type == "Half":
            row.making_amount = row_making_amt_total * 0.5
        else:
            row.making_amount = 0

        row.rate = (
            row.metal_amount
            + row.finding_amount
            + row.diamond_amount
            + row.gemstone_amount
            + row.making_amount
        )
        row.amount = row.rate * row.qty

        total_taxable += row.amount

    doc.total_taxes_and_charges = total_gst
    doc.grand_total = total_taxable + total_gst


# ==================================================================
# CALCULATION TYPE: RAW MATERIAL CONSIGNMENT
# ==================================================================
def _calc_bom_raw_material_consignment(doc):
    """
    Raw Material Consignment BOM-based calculation.
    Special rules:
      - making_charges_type forced to 'With'
      - return_material_type forced to 'Diamond-Gemstone'
      - Making = 50% of BOM-based making
      - Material type filter: zero out metal/finding for Diamond-Gemstone
      - Custom Duty = (making + diamond + gemstone) × 6% × 50%
      - Rate = (making + diamond + gemstone) - custom_duty

    Used for:
      - Raw Material-Consignment
    """

    doc.making_charges_type = "With"
    doc.return_material_type = "Diamond-Gemstone"

    jwelex_data = doc.get("jwelex_credit_note_data")
    if not jwelex_data:
        frappe.throw(f"JWELEX Data is required for {frappe.bold(doc.credit_note_subtype)} calculation")
    
    jwelex_data = json.loads(jwelex_data)

    # TODO: Implement PCPM calculation logic
    # Use jwelex_data to calculate rates
    # Apply same product rate as invoice
    # No new or revised rates
    
    for row_item in doc.items:
        factor = flt(row_item.qty)
        tag_no = row_item.get("tag_no")
        if not tag_no:
            continue
        
        # Find matching item in jwelex_data
        matching_item = jwelex_data.get(tag_no)
        
        if not matching_item:
            frappe.throw(f"Tag No {tag_no} not found in JWELEX Data")
        
        # frappe.throw(f"Matching Item: {matching_item}")

        charges_info = matching_item.get("charges_info", {})
        making_amount = charges_info.get("chain_making_amount", 0) + charges_info.get("metal_making_amount", 0)
        hm_charges = charges_info.get("hm_charges", 0)
        certificate_charges = charges_info.get("certificate_charges", 0)

        materials = matching_item.get("materials", {})
        diamond_details = materials.get("diamond_details", [])
        finding_details = materials.get("finding_details", [])
        metal_details = materials.get("metal_details", [])
        other_details = materials.get("other_details", [])
        stone_details = materials.get("stone_details", [])


        metal_amount = 0
        for metal in metal_details:
            metal_amount += metal.get("Amount", 0)
            
        diamon_amount = 0
        for diamond in diamond_details:
            diamon_amount += diamond.get("Amount", 0)
        
        finding_amount = 0
        for finding in finding_details:
            finding_amount += finding.get("Amount", 0)
        
        stone_amount = 0
        for stone in stone_details:
            stone_amount += stone.get("Amount", 0)
        
        other_amount = 0
        for other in other_details:
            other_amount += other.get("Amount", 0)


        # Making charges Type
        if doc.making_charges_type == "Without":
            making_amount = 0
        elif doc.making_charges_type == "With":
            making_amount = making_amount
        elif doc.making_charges_type == "Half":
            making_amount = making_amount * 0.5
        else:
            making_amount = 0
        
        proportional_fields = [
            "amount",
            "base_amount",
            "metal_amount",
            "diamond_amount",
            "finding_amount",
            "making_amount",
            "certification_amount",
            "freight_amount",
            "gemstone_amount",
            "other_material_amount",
            "hallmarking_amount",
            "custom_duty_amount",
            "other_amount",
            ]

        for field in proportional_fields:
            row_item.set(field, 0)
        
        

        # makeing charge: 50% labour charges
        row_item.set("making_amount", making_amount * factor * 0.5)
        
        # diamond and gemstone amount as invoice item amount
        row_item.set("diamond_amount", diamon_amount * factor)
        row_item.set("gemstone_amount", stone_amount * factor)

        if doc.return_material_type == "Metal-Finding":
            row_item.set("diamond_amount", 0)
            row_item.set("gemstone_amount", 0)
        elif doc.return_material_type == "Diamond-Gemstone":
            row_item.set("metal_amount", 0)
            row_item.set("finding_amount", 0)

        total_amount = row_item.diamond_amount + row_item.gemstone_amount + row_item.making_amount - row_item.custom_duty_amount
        # frappe.msgprint(f"Total Amount: {total_amount}")
        
        row_item.rate = total_amount / row_item.get("qty", 1)
        row_item.amount = total_amount


@frappe.whitelist()
def get_data_from_jwelex(tag_no):

    url = f"http://3.108.219.130:8008/credit-note?tag_no={tag_no}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # raises exception for 4xx/5xx
        
        data = response.json()
        return data
        
    except requests.exceptions.RequestException:
        return None
    except ValueError:
        return None