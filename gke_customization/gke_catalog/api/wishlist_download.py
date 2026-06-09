import json
import os
import requests

import frappe

from frappe.utils import flt, cint
from frappe.utils.pdf import get_pdf

from gke_customization.gke_catalog.api.item_price_list import get_item_price

def calculate_finding_and_making_amounts(item, result):
    finding_amount_total = 0
    gold_amount_total = 0
    making_charge = 0
    chain_making = 0
    
    finding_price_data = result.get("finding_price_data", {})
    metal_price_data = result.get("metal_price_data", {})
    
    # if item == "MA00975-004":
    #     frappe.throw(f"{result}")
    diamond = result.get("dia_quality_summary", {})

    total_diamond_base_rate = 0
    total_diamond_amount = 0

    for key, values in diamond.items():

        diamond_rate = float(
            values.get("total_base_rate") or 0
        )

        diamond_amount = float(
            values.get("total_diamond_amount") or 0
        )

        total_diamond_base_rate += diamond_rate
        total_diamond_amount += diamond_amount
        
    for purity, finding_data in finding_price_data.items():
        finding_sub = (finding_data.get("finding_sub") or "").lower()
        finding_amount = float(finding_data.get("finding_amount") or 0)

        
        finding_making_charge = float(
            finding_data.get("finding_making_charge") or 0
        )

        # Chain case
        if "chain" in finding_sub:
            # if item == "MU01130-006":
            #     frappe.throw(f"{finding_amount}")
            finding_amount_total += finding_amount
            chain_making += finding_making_charge

        # Other findings
        else:
            gold_amount = float(
                metal_price_data.get(purity, {}).get("gold_amount") or 0
            )

            making_charge_amount = float(
                metal_price_data.get(purity, {}).get("making_charge") or 0
            )
           
            gold_amount_total += finding_amount + gold_amount
            making_charge += making_charge_amount + finding_making_charge

    # if item == "MA00975-004":
    #     frappe.throw(f"{l,gold_amount_total}")
        
    return {
        "finding_amount_total": finding_amount_total,
        "diamond_rate": total_diamond_base_rate,
        "diamond_amount": total_diamond_amount,
        "gold_amount_total": gold_amount_total,
        "making_charge": making_charge,
        "chain_making": chain_making,
    }

@frappe.whitelist(allow_guest=True)
def download_bom_pdf(boms, customer, company, customer_folder_name=None):

    if isinstance(boms, str):
        boms = json.loads(boms)

    data = []
    grand_total_amount = 0  
   

    for bom, values in boms.items():
        bom_name = frappe.db.get_value("BOM", {"name": bom}, "name")
        if not bom_name:
            continue

        bom_doc = frappe.get_doc("BOM", bom_name)

        # Diamond grouping — same as before
        diamond_group = {}
        diamond_total = 0

        for row in bom_doc.diamond_detail:
            rate = flt(row.total_diamond_rate)
            diamond_total += flt(row.diamond_rate_for_specified_quantity or 0)

            if rate not in diamond_group:
                diamond_group[rate] = {"pcs": 0, "cts": 0, "amount": 0, "rate": rate}

            diamond_group[rate]["pcs"] += cint(row.pcs or 0)
            diamond_group[rate]["cts"] = round(diamond_group[rate]["cts"] + flt(row.quantity or 0), 2)
            diamond_group[rate]["amount"] = round(diamond_group[rate]["amount"] + flt(row.diamond_rate_for_specified_quantity or 0), 3)

        diamond_rows = list(diamond_group.values())
  
                        
        result = get_item_price(
            customer=customer,
            item_code=bom_doc.item,
            bom=bom,
            # diamond_quality=values.get("diamond_quality") if values else None,
            # metal_touch=values.get("metal_touch") if values else None,
            gold_rate_value=float(values.get("gold_rate_value") or 0) if values else 0.0,
            is_cust_diam=int(values.get("is_cust_diam") or 0) if values else 0,
            is_cust_stone=int(values.get("is_cust_stone") or 0) if values else 0,
            is_cust_gold=int(values.get("is_cust_gold") or 0) if values else 0,
            # cust_gold_wt=float(values.get("cust_gold_wt") or 0) if values else 0.0,
        )
        

        amounts = calculate_finding_and_making_amounts(bom_doc.item, result)
        # amounts["total_diamond_amount"] , amounts["total_diamond_base_rate"],
        
        total_amount = round(
            amounts["diamond_amount"]
            + amounts["gold_amount_total"]
            + amounts["finding_amount_total"]
            + amounts["chain_making"]
        
            + amounts["making_charge"]
        
            + flt(bom_doc.total_gemstone_amount)
            + flt(bom_doc.certification_amount)
            + flt(bom_doc.hallmarking_amount),
            2
        )
        grand_total_amount += total_amount
        
        data.append({
            "customer": bom_doc.customer,
            "company": bom_doc.company,
            "item": bom_doc.item,
            "bom": bom_doc.name,
            "item_category": bom_doc.item_category,
            "diamond_quality": bom_doc.diamond_quality,
            "gross_weight": flt(getattr(bom_doc, "gross_weight", 0)),
            "gemstone_weight": flt(getattr(bom_doc, "gemstone_weight", 0)),
            "other_weight": flt(getattr(bom_doc, "other_weight", 0)),
            "net_weight": flt(getattr(bom_doc, "metal_and_finding_weight", 0)),
            "metal_purity": getattr(bom_doc, "metal_purity", ""),
            "chain_wt": flt(getattr(bom_doc, "chain_wt", 0)),
            "chain_amt": amounts["finding_amount_total"],        # ✅ item wise
            "chain_making": amounts["chain_making"],
            "chain_wastage": flt(getattr(bom_doc, "chain_wastage", 0)),
            "jewellery_making": amounts["making_charge"],
            "jewellery_wastage": flt(getattr(bom_doc, "jewellery_wastage", 0)),
            "stone_amt": flt(getattr(bom_doc, "total_gemstone_amount", 0)),
            "certification_amount": flt(getattr(bom_doc, "certification_amount", 0)),
            "hallmarking_amount": flt(getattr(bom_doc, "hallmarking_amount", 0)),
            "gold_amt": amounts["gold_amount_total"],            # ✅ item wise
            "total_diamond_pcs": sum(d["pcs"] for d in diamond_rows),
            "total_diamond_cts": sum(d["cts"] for d in diamond_rows),
            "total_diamond_amt": amounts["diamond_amount"],
            "total_diamond_base_rate": amounts["diamond_rate"],
            "total_amount": total_amount,
            "diamond_rows": diamond_rows,
        })

    # all column totals 
    total_diamond_pcs      = sum(row.get("total_diamond_pcs") or 0 for row in data)
    total_diamond_cts      = sum(row.get("total_diamond_cts") or 0 for row in data)
    total_diamond_amt      = sum(row.get("total_diamond_amt") or 0 for row in data)
    total_gross_weight     = round(sum(row.get("gross_weight") or 0 for row in data), 3)
    total_gemstone_weight  = round(sum(row.get("gemstone_weight") or 0 for row in data), 3)
    total_other_weight     = round(sum(row.get("other_weight") or 0 for row in data), 3)
    total_net_weight       = round(sum(row.get("net_weight") or 0 for row in data), 3)
    total_gold_amt         = sum(row.get("gold_amt") or 0 for row in data)
    total_chain_wt         = round(sum(row.get("chain_wt") or 0 for row in data), 3)
    total_chain_amt        = sum(row.get("chain_amt") or 0 for row in data)
    total_chain_making     = sum(row.get("chain_making") or 0 for row in data)
    total_chain_wastage    = sum(row.get("chain_wastage") or 0 for row in data)
    total_jewellery_making = sum(row.get("jewellery_making") or 0 for row in data)
    total_jewellery_wastage= sum(row.get("jewellery_wastage") or 0 for row in data)
    total_stone_amt        = sum(row.get("stone_amt") or 0 for row in data)
    total_certification    = sum(row.get("certification_amount") or 0 for row in data)
    total_hallmarking      = sum(row.get("hallmarking_amount") or 0 for row in data)

    #  GST & Grand Total calculations
    igst_rate   = 3.0
    igst_amount = round(grand_total_amount * (igst_rate / 100), 2)
    g_total_raw = grand_total_amount + igst_amount
    g_total     = round(g_total_raw, 2)
    round_off   = round(g_total - g_total_raw, 2)

    # Read HTML Template
    template_path = os.path.join(
        frappe.get_app_path("gke_customization"),
        "templates",
        "wishlist_download.html"
    )

    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    # all total
    final_html = frappe.render_template(template, {
        "data": data,
        "company": company,
        "customer": customer,
        "grand_total_amount": grand_total_amount,
        "total_diamond_pcs": total_diamond_pcs,
        "total_diamond_cts": total_diamond_cts,
        "total_diamond_amt": total_diamond_amt,
        "total_gross_weight": total_gross_weight,
        "total_gemstone_weight": total_gemstone_weight,
        "total_other_weight": total_other_weight,
        "total_net_weight": total_net_weight,
        "total_gold_amt": total_gold_amt,
        "total_chain_wt": total_chain_wt,
        "total_chain_amt": total_chain_amt,
        "total_chain_making": total_chain_making,
        "total_chain_wastage": total_chain_wastage,
        "total_jewellery_making": total_jewellery_making,
        "total_jewellery_wastage": total_jewellery_wastage,
        "total_stone_amt": total_stone_amt,
        "total_certification": total_certification,
        "total_hallmarking": total_hallmarking,
        "igst_rate": igst_rate,
        "igst_amount": igst_amount,
        "round_off": round_off,
        "g_total": g_total,
    })

    pdf = get_pdf(final_html)

    folder_name = customer_folder_name or "BOMs"
    frappe.local.response.filename = f"{folder_name}.pdf"
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "download"
    
    
    
# @frappe.whitelist(allow_guest=True)
# def download_bom_pdf(boms, customer, company, customer_folder_name=None):

#     if isinstance(boms, str):
#         boms = json.loads(boms)

#     data = []

#     for name in boms:

#         bom_name = frappe.db.get_value(
#             "BOM",
#             {"name": name},
#             "name"
#         )

#         if not bom_name:
#             continue

#         bom = frappe.get_doc("BOM", bom_name)

#         # Group Diamond Detail by Rate
#         diamond_group = {}
        
#         grand_total_amount = 0
#         diamond_total = 0
#         for row in bom.diamond_detail:
            
#             # Grand Total
            
#             rate = flt(row.total_diamond_rate)
            
#             diamond_total += flt(row.diamond_rate_for_specified_quantity or 0)

#             total_amount = (
#                 diamond_total
#                 + flt(bom.total_gemstone_amount)
#                 + flt(bom.certification_amount)
#                 + flt(bom.hallmarking_amount)
#             )
            
#             grand_total_amount += total_amount
            
#             if rate not in diamond_group:
#                 diamond_group[rate] = {
#                     "pcs": 0,
#                     "cts": 0,
#                     "amount": 0,
#                     "rate": rate
#                 }

#             diamond_group[rate]["pcs"] += cint(row.pcs or 0)

#             diamond_group[rate]["cts"] = round(
#                 diamond_group[rate]["cts"] + flt(row.quantity or 0),
#                 2
#             )

#             diamond_group[rate]["amount"] = round(
#                 diamond_group[rate]["amount"] + flt(row.diamond_rate_for_specified_quantity or 0),
#                 3
#             )

#         diamond_rows = list(diamond_group.values())
        
#         # frappe.throw(f"{diamond_rows}")

#         data.append({
#             "customer": bom.customer,
#             "company": bom.company,

#             "item": bom.item,
#             "bom":bom.name,
#             "item_category": bom.item_category,
#             "diamond_quality": bom.diamond_quality,

#             "dia_pcs": "",
#             "dia_wt": "",
#             "dia_rate": "",
#             "dia_amt": "",

#             "gross_weight": bom.gross_weight,
#             "gemstone_weight": bom.gemstone_weight,
#             "other_weight": bom.other_weight,
#             "net_weight": bom.metal_and_finding_weight,

#             "gold_amt": "",
#             "metal_purity": bom.metal_purity,

#             "chain_wt": "",
#             "chain_amt": "",
#             "touch": bom.metal_purity,
#             "chain_making": "",
#             "chain_wastage": "",

#             "jewellery_making": "",
#             "jewellery_wastage": "",

#             "stone_amt": bom.total_gemstone_amount,
#             "certification_amount": bom.certification_amount,
#             "hallmarking_amount": bom.hallmarking_amount,

#             "total_amount": total_amount,

#             # grouped diamond rows
#             "diamond_rows": diamond_rows
#         })

#     # Read HTML Template
#     template_path = os.path.join(
#         frappe.get_app_path("gke_customization"),
#         "templates",
#         "wishlist_download.html"
#     )

#     with open(template_path, "r", encoding="utf-8") as f:
#         template = f.read()

#     # frappe.throw(f"{grand_total_amount}")
#     # Render HTML
#     final_html = frappe.render_template(
#         template,
#         {
#             "data": data,
#             "company": company,
#             "customer": customer,
#             "grand_total_amount": grand_total_amount
#         }
#     )

#     # Generate PDF
#     pdf = get_pdf(final_html)

#     folder_name = customer_folder_name or "BOMs"

#     frappe.local.response.filename = f"{folder_name}.pdf"
#     frappe.local.response.filecontent = pdf
#     frappe.local.response.type = "download"




@frappe.whitelist(allow_guest=True)

def get_method(data):
    filter_keys = [
        "age_group",
        "custom_language",
        "custom_alphabetnumber",
        "occasion",
        "custom_animalbirds",
        "rhodium",
        "shapes",
        "religious",
        "design_style",
        "custom_collection",
        "custom_zodiac",
        "gender",
        "custom_lines__rows"
    ]
    
    available_keys = set()

    for item in data:

        for key in filter_keys:

            value = item.get(key)

            if value:
                available_keys.add(key)

    return {
        "design_attributes": sorted(list(available_keys))
    }
    
    
    
@frappe.whitelist(allow_guest=True)
def get_method1(data):
    filter_keys = [
        "age_group",
        "custom_language",
        "custom_alphabetnumber",
        "occasion",
        "custom_animalbirds",
        "rhodium",
        "shapes",
        "religious",
        "design_style",
        "custom_collection",
        "custom_zodiac",
        "gender",
        "custom_lines__rows"
    ]

    # Har key ke liye ek set banao unique values ke liye
    filter_map = {key: set() for key in filter_keys}

    for item in data:
        for key in filter_keys:
            value = item.get(key)
            if value:
                # Comma-separated values split karo
                # e.g. "Anniversary, Birthday, Diwali" → 3 alag values
                for v in str(value).split(","):
                    v = v.strip()
                    if v:
                        filter_map[key].add(v)

    # Sirf woh keys return karo jinmein kuch values hain
    return {
        key: sorted(list(values))
        for key, values in filter_map.items()
        if values  # empty lists mat bhejo
    }
    
    
    
import frappe
from frappe.utils.global_search import search, update_global_search, rebuild_for_doctype


# ─────────────────────────────────────────────
# Method 1 — Simple Global Search
# ─────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def search_global(search_text: str, doctype: str = "Item"):
    """
    Frappe ka built-in global search use karo.
    Saare indexed fields mein search karta hai.
    """
    if not search_text or not search_text.strip():
        return []

    # Built-in search function
    results = search(search_text, scope=doctype)

    return results


# ─────────────────────────────────────────────
# Method 2 — Custom Global Search (More Control)
# ─────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def search_items(search_text: str):
    """
    Global search table se directly Item search karo.
    __global_search table use karta hai jo Frappe maintain karta hai.
    """
    if not search_text or not search_text.strip():
        return []

    # Cache check
    cache     = frappe.cache()
    cache_key = f"gsearch:{search_text.lower().strip()}"
    cached    = cache.get_value(cache_key)
    if cached:
        import json
        return json.loads(cached)

    # Global search table query
    results = frappe.db.sql("""
        SELECT
            gs.doctype,
            gs.name,
            gs.content,
            gs.route,
            i.item_name,
            i.item_code,
            i.item_group,
            i.standard_rate,
            i.image
        FROM
            `__global_search` gs
        JOIN
            `tabItem` i ON i.name = gs.name
        WHERE
            gs.doctype = 'Item'
            AND i.disabled = 0
            AND i.is_sales_item = 1
            AND gs.content LIKE %(text)s
        LIMIT 20
    """, {"text": f"%{search_text}%"}, as_dict=True)

    import json
    cache.set_value(cache_key, json.dumps(results), expires_in_sec=300)

    return results


# ─────────────────────────────────────────────
# Method 3 — Multi-DocType Search
# ─────────────────────────────────────────────

@frappe.whitelist()
def search_multiple(search_text: str):
    """
    Ek saath multiple doctypes mein search karo.
    Item, Customer, Supplier sab mein.
    """
    if not search_text or not search_text.strip():
        return {}

    doctypes = ["Item", "Customer", "Supplier"]
    output   = {}

    for dt in doctypes:
        results      = search(search_text, scope=dt)
        output[dt]   = results[:5]  # har doctype se 5 results

    return output


# ─────────────────────────────────────────────
# Global Search Index Rebuild Karo
# ─────────────────────────────────────────────

@frappe.whitelist()
def rebuild_item_search_index():
    """
    Sirf Item doctype ka global search index rebuild karo.
    Run karo agar search mein purana/missing data aaye.

        bench execute your_app.global_search.rebuild_item_search_index
    """
    rebuild_for_doctype("Item")
    return {"message": "Item search index rebuild ho gaya!"}


@frappe.whitelist()
def rebuild_all_index():
    """
    Saare doctypes ka global search index rebuild karo.
    WARNING: Bohot time lagta hai agar data zyada ho.

        bench execute your_app.global_search.rebuild_all_index
    """
    from frappe.utils.global_search import rebuild_for_all_doctypes
    rebuild_for_all_doctypes()
    return {"message": "Saare doctypes ka search index rebuild ho gaya!"}