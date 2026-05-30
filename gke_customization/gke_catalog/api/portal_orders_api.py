import frappe
import json
from frappe import _
from gke_customization.gke_catalog.api.item_price_list import get_item_price


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def _get_customer_assigned_users(customer):
    users = frappe.get_all(
        "Customer Representatives",
        filters={"parent": customer},
        pluck="user_id",
    )
    return [u for u in users if u]


def _get_full_name(user):
    if not user:
        return ""
    return frappe.db.get_value("User", user, "full_name") or user



def _serialize_items(items, status_filter=None):
    result = []
    for row in items:
        row_status = getattr(row, "status", "Draft") or "Draft"

        if status_filter:
            if row_status != status_filter:
                continue
        else:
            if row_status == "Cancel Order":
                continue

        item_data = frappe.db.get_value("Item", row.item_code, ["image", "name"], as_dict=True) or {}
        bom_data = frappe.db.get_value("BOM", row.bom, ["gross_weight","metal_and_finding_weight","total_diamond_weight_in_gms","metal_touch"], as_dict=True) or {}

        result.append({
            "name":                         row.name,
            "item_code":                    row.item_code,
            "quantity":                     row.quantity or 0,
            "rate":                         row.rate or 0,
            "amount":                       (row.quantity or 0) * (row.rate or 0),
            "bom":                          row.bom or "",
            "image":                        item_data.get("image") or "",
            "gross_Weight":                 bom_data.get("gross_weight") or "",
            "net_weight":                   bom_data.get("metal_and_finding_weight") or "",
            "total_diamond_weight_in_gms":  bom_data.get("total_diamond_weight_in_gms") or "",
            "metal_touch":                  bom_data.get("metal_touch") or "",
            "user":                         getattr(row, "user", "") or "",
            "status":                       row_status,
            "design": "Customized" if (getattr(row, "as_per_customization", 0) or 0) else "As Per Design",
            "customized_data":              row.customized_data or "",
            "jobwork":                      getattr(row, "jobwork", 0) or 0,
            "job_work":                     getattr(row, "job_work", "") or "",
            "customer_gold":                getattr(row, "customer_gold", 0) or 0,
            "customer_diamond":             getattr(row, "customer_diamond", 0) or 0,
            "customer_stone":               getattr(row, "customer_stone", 0) or 0,
            "weight":                       getattr(row, "weight", 0) or 0,
        })
    return result






def _recalculate_totals(doc):
    draft_rows = [row for row in doc.items if getattr(row, "status", "Draft") == "Draft"]
    
    doc.total_quantity = sum(row.quantity or 0 for row in draft_rows)
    doc.total_amount   = round(sum((row.quantity or 0) * (row.rate or 0) for row in draft_rows), 2)

# ─────────────────────────────────────────────
#  ADD TO CART
# ───────────────────────────────────────────── 

# @frappe.whitelist(allow_guest=True)
# def add_to_cart1(
#     customer,
#     item_code,
#     quantity=1,
#     rate=0,
#     bom=None,
#     user=None,
#     diamond_quality=None,
#     metal_touch=None,
#     design_portal=None,
#     customized_data=None,
#     job_work=None,
#     customer_gold=None,
#     customer_diamond=None,
#     customer_stone=None,):
#     if not customer:
#         frappe.throw(_("Customer required"))

#     qty = int(quantity or 0)
#     calculated_rate = float(rate or 0)

#     # ── BOM auto-fetch ─────────────────────────────────────
#     if not bom:
#         bom = frappe.db.get_value(
#             "BOM",
#             {"item": item_code, "is_active": 1, "bom_type": "Finish Goods", "is_default": 1},
#             "name",
#             order_by="creation desc"
#         )

#     # ── diamond_quality auto-fetch ─────────────────────────
#     if bom and not diamond_quality:
#         diamond_quality = frappe.db.get_value("BOM", bom, "diamond_quality")

#     # ── metal_touch auto-fetch ─────────────────────────────
#     if bom and not metal_touch:
#         metal_touch = frappe.db.get_value("BOM", bom, "metal_touch")

#     # ── design_portal default ──────────────────────────────
#     if not design_portal:
#         design_portal = "As Per Design"

#     # ── design portal checkboxes ───────────────────────────
#     is_as_per_design        = 1 if design_portal == "As Per Design" else 0
#     is_as_per_customization = 1 if design_portal == "AS Per Customized" else 0

#     # ── jobwork flags ──────────────────────────────────────
#     cg = 1 if customer_gold else 0
#     cd = 1 if customer_diamond else 0
#     cs = 1 if customer_stone else 0
#     is_jobwork = 1 if (cg or cd or cs) else 0

#     # ── Price calculate ────────────────────────────────────
#     if bom and (not rate or float(rate) == 0):
#         try:
#             price_data = get_item_price(
#                 customer=customer,
#                 item_code=item_code,
#                 bom=bom,
#                 diamond_quality=diamond_quality,
#                 metal_touch=metal_touch
#             )
#             dia_amount    = price_data["dia_overall_summary"]["total_amount"]
#             gem_amount    = price_data["gem_summary"]["total_gemstone_amount"]
#             metal_total   = sum(
#                 v.get("gold_amount", 0) + v.get("making_charge", 0)
#                 for v in price_data["metal_price_data"].values()
#             )
#             finding_total = sum(
#                 v.get("finding_amount", 0) + v.get("finding_making_charge", 0)
#                 for v in price_data["finding_price_data"].values()
#             )
#             calculated_rate = round(dia_amount + gem_amount + metal_total + finding_total, 2)
#         except Exception as e:
#             frappe.log_error(f"Price calc failed for {item_code}: {str(e)}", "Cart Price Error")
#             calculated_rate = float(rate or 0)

#     # ── Fix: validate user exists in Frappe User doctype ──
#     raw_user = user or frappe.session.user
#     user_exists = frappe.db.exists("User", raw_user)
#     current_user = raw_user if user_exists else ""

#     item_image = frappe.db.get_value("Item", item_code, "image") or ""

#     # ── Find active cart ───────────────────────────────────
#     active_cart = frappe.db.get_value(
#         "Portal Order",
#         {"customer": customer, "status": "Draft"},
#         "name",
#         order_by="creation asc"
#     )

#     if active_cart:
#         doc = frappe.get_doc("Portal Order", active_cart)
#     else:
#         doc = frappe.new_doc("Portal Order")
#         doc.customer = customer
#         doc.status   = "Draft"
#         doc.company  = frappe.defaults.get_user_default("Company")
#         doc.currency = "INR"

#     # ── Normalize helpers ──────────────────────────────────
#     def normalize(val):
#         return (val or "").strip()

#     def normalize_json(val):
#         v = (val or "").strip()
#         if not v:
#             return ""
#         try:
#             import json
#             parsed = json.loads(v)
#             return json.dumps(parsed, sort_keys=True, ensure_ascii=False)
#         except Exception:
#             return v

#     # ── Incoming values for match ──────────────────────────
#     # Note: metal_touch & diamond_quality Portal Order Item mein
#     # field nahi hai, isliye sirf inhi se match karenge jo hain
# # ── Incoming values for match ──────────────────────────
#     incoming_customized_data = normalize_json(customized_data)
#     incoming_cg = cg
#     incoming_cd = cd
#     incoming_cs = cs
    
#     # ── Update existing item (only Draft rows) ─────────────
#     item_found = False
#     for row in doc.items:
#         row_status = getattr(row, "status", "Draft")
#         if row.item_code != item_code or row_status != "Draft":
#             continue
    
#         same_customized_data = normalize_json(row.customized_data) == incoming_customized_data
#         # ✅ design_portal field nahi hai — checkboxes se compare karo
#         same_as_per_design        = (row.as_per_design or 0)        == is_as_per_design
#         same_as_per_customization = (row.as_per_customization or 0) == is_as_per_customization
#         same_cg = (row.customer_gold    or 0) == incoming_cg
#         same_cd = (row.customer_diamond or 0) == incoming_cd
#         same_cs = (row.customer_stone   or 0) == incoming_cs
    
#         if (same_customized_data
#                 and same_as_per_design
#                 and same_as_per_customization
#                 and same_cg and same_cd and same_cs):
#             # Same → qty badhao
#             row.quantity             = row.quantity + qty
#             row.rate                 = calculated_rate
#             row.amount               = row.quantity * calculated_rate
#             row.user                 = current_user
#             row.as_per_design        = is_as_per_design
#             row.as_per_customization = is_as_per_customization
#             row.customer_gold        = cg
#             row.customer_diamond     = cd
#             row.customer_stone       = cs
#             row.jobwork              = is_jobwork
#             row.job_work             = job_work or ""
#             item_found = True
#             break
#         # Alag customization → naya row banega

#     # ── Add new item ───────────────────────────────────────
#     if not item_found:
#         doc.append("items", {
#             "item_code":             item_code,
#             "quantity":              qty,
#             "rate":                  calculated_rate,
#             "amount":                qty * calculated_rate,
#             "bom":                   bom or "",
#             "image":                 item_image,
#             "user":                  current_user,
#             "status":                "Draft",
#             "design_portal":         design_portal,
#             "customized_data":       customized_data or "",
#             "job_work":              job_work or "",
#             "as_per_design":         is_as_per_design,
#             "as_per_customization":  is_as_per_customization,
#             "customer_gold":         cg,
#             "customer_diamond":      cd,
#             "customer_stone":        cs,
#             "jobwork":               is_jobwork,
#         })

#     _recalculate_totals(doc)
#     doc.save(ignore_permissions=True)
#     frappe.db.commit() 

#     return {
#         "success":        True,
#         "order":          doc.name,
#         "total_quantity": doc.total_quantity,
#         "total_amount":   doc.total_amount,
#         "item_rate":      calculated_rate,
#     } 

# @frappe.whitelist(allow_guest=True)
# def add_to_cart1(
#     customer,
#     item_code,
#     quantity=1,
#     rate=0,
#     bom=None,
#     user=None,
#     diamond_quality=None,
#     metal_touch=None,
#     design_portal=None,
#     customized_data=None,
#     job_work=None,
#     customer_gold=None,
#     customer_diamond=None,
#     customer_stone=None,):
#     if not customer:
#         frappe.throw(_("Customer required"))

#     qty = int(quantity or 0)
#     calculated_rate = float(rate or 0)

#     # ── BOM auto-fetch ─────────────────────────────────────
#     if not bom:
#         bom = frappe.db.get_value(
#             "BOM",
#             {"item": item_code, "is_active": 1, "bom_type": "Finish Goods", "is_default": 1},
#             "name",
#             order_by="creation desc"
#         )

#     # ── diamond_quality auto-fetch ─────────────────────────
#     if bom and not diamond_quality:
#         diamond_quality = frappe.db.get_value("BOM", bom, "diamond_quality")

#     # ── metal_touch auto-fetch ─────────────────────────────
#     if bom and not metal_touch:
#         metal_touch = frappe.db.get_value("BOM", bom, "metal_touch")

#     # ── design_portal default ──────────────────────────────
#     if not design_portal:
#         design_portal = "As Per Design"

#     # ── design portal checkboxes ───────────────────────────
#     is_as_per_design        = 1 if design_portal == "As Per Design" else 0
#     is_as_per_customization = 1 if design_portal == "As Per Customized" else 0

#     # ── jobwork flags ──────────────────────────────────────
#     cg = 1 if customer_gold else 0
#     cd = 1 if customer_diamond else 0
#     cs = 1 if customer_stone else 0
#     is_jobwork = 1 if (cg or cd or cs) else 0

#     # ── Price calculate ────────────────────────────────────
#     if bom and (not rate or float(rate) == 0):
#         try:
#             price_data = get_item_price(
#                 customer=customer,
#                 item_code=item_code,
#                 bom=bom,
#                 diamond_quality=diamond_quality,
#                 metal_touch=metal_touch
#             )
#             dia_amount    = price_data["dia_overall_summary"]["total_amount"]
#             gem_amount    = price_data["gem_summary"]["total_gemstone_amount"]
#             metal_total   = sum(
#                 v.get("gold_amount", 0) + v.get("making_charge", 0)
#                 for v in price_data["metal_price_data"].values()
#             )
#             finding_total = sum(
#                 v.get("finding_amount", 0) + v.get("finding_making_charge", 0)
#                 for v in price_data["finding_price_data"].values()
#             )
#             calculated_rate = round(dia_amount + gem_amount + metal_total + finding_total, 2)
#         except Exception as e:
#             frappe.log_error(f"Price calc failed for {item_code}: {str(e)}", "Cart Price Error")
#             calculated_rate = float(rate or 0)

#     # ── Fix: validate user exists in Frappe User doctype ──
#     raw_user = user or frappe.session.user
#     user_exists = frappe.db.exists("User", raw_user)
#     current_user = raw_user if user_exists else ""

#     item_image = frappe.db.get_value("Item", item_code, "image") or ""

#     # ── Find active cart ───────────────────────────────────
#     active_cart = frappe.db.get_value(
#         "Portal Order",
#         {"customer": customer, "status": "Draft"},
#         "name",
#         order_by="creation asc"
#     )

#     if active_cart:
#         doc = frappe.get_doc("Portal Order", active_cart)
#     else:
#         doc = frappe.new_doc("Portal Order")
#         doc.customer = customer
#         doc.status   = "Draft"
#         doc.company  = frappe.defaults.get_user_default("Company")
#         doc.currency = "INR"

#     # ── Normalize helpers ──────────────────────────────────
#     def normalize(val):
#         return (val or "").strip()

#     def normalize_json(val):
#         v = (val or "").strip()
#         if not v:
#             return ""
#         try:
#             import json
#             parsed = json.loads(v)
#             return json.dumps(parsed, sort_keys=True, ensure_ascii=False)
#         except Exception:
#             return v

#     # ── Incoming values for match ──────────────────────────
#     # Note: metal_touch & diamond_quality Portal Order Item mein
#     # field nahi hai, isliye sirf inhi se match karenge jo hain
    
#     incoming_customized_data = normalize_json(customized_data)
#     incoming_cg = cg
#     incoming_cd = cd
#     incoming_cs = cs
    
#     # ── Update existing item (only Draft rows) ─────────────
#     item_found = False
#     for row in doc.items:
#         row_status = getattr(row, "status", "Draft")
#         if row.item_code != item_code or row_status != "Draft":
#             continue
    
#         same_customized_data = normalize_json(row.customized_data) == incoming_customized_data
#         # design_portal field nahi hai — checkboxes se compare karo
#         same_as_per_design        = (row.as_per_design or 0)        == is_as_per_design
#         same_as_per_customization = (row.as_per_customization or 0) == is_as_per_customization
#         same_cg = (row.customer_gold    or 0) == incoming_cg
#         same_cd = (row.customer_diamond or 0) == incoming_cd
#         same_cs = (row.customer_stone   or 0) == incoming_cs
    
#         if (same_customized_data
#                 and same_as_per_design
#                 and same_as_per_customization
#                 and same_cg and same_cd and same_cs):
#             # Same → qty badhao
#             row.quantity             = row.quantity + qty
#             row.rate                 = calculated_rate
#             row.amount               = row.quantity * calculated_rate
#             row.user                 = current_user
#             row.as_per_design        = is_as_per_design
#             row.as_per_customization = is_as_per_customization
#             row.customer_gold        = cg
#             row.customer_diamond     = cd
#             row.customer_stone       = cs
#             row.jobwork              = is_jobwork
#             row.job_work             = job_work or ""
#             item_found = True
#             break
#         # Alag customization → naya row banega

#     # ── Add new item ───────────────────────────────────────
#     if not item_found:
#         doc.append("items", {
#        "item_code":             item_code,
#        "quantity":              qty,
#        "rate":                  calculated_rate,
#        "amount":                qty * calculated_rate,
#        "bom":                   bom or "",
#        "image":                 item_image,
#        "user":                  current_user,
#        "status":                "Draft",
#        "as_per_design":         is_as_per_design,
#        "as_per_customization":  is_as_per_customization,
#        "customized_data":       customized_data or "",
#        "job_work":              job_work or "",
#        "customer_gold":         cg,
#        "customer_diamond":      cd,
#        "customer_stone":        cs,
#        "jobwork":               is_jobwork,
#    })

#     _recalculate_totals(doc)
#     doc.save(ignore_permissions=True)
#     frappe.db.commit()

#     return {
#         "success":        True,
#         "order":          doc.name,
#         "total_quantity": doc.total_quantity,
#         "total_amount":   doc.total_amount,
#         "item_rate":      calculated_rate,
#     } 

@frappe.whitelist(allow_guest=True)
def add_to_cart1(
    customer,
    item_code,
    quantity=1,
    rate=0,
    bom=None,
    user=None,
    diamond_quality=None,
    metal_touch=None,
    design_portal=None,
    customized_data=None,
    job_work=None,
    customer_gold=None,
    customer_diamond=None,
    customer_stone=None,):
    if not customer:
        frappe.throw(_("Customer required"))

    qty = int(quantity or 0)
    calculated_rate = float(rate or 0)

    # ── BOM auto-fetch ─────────────────────────────────────
    if not bom:
        bom = frappe.db.get_value(
            "BOM",
            {"item": item_code, "is_active": 1, "bom_type": "Finish Goods", "is_default": 1},
            "name",
            order_by="creation desc"
        )

    # ── diamond_quality auto-fetch ─────────────────────────
    if bom and not diamond_quality:
        diamond_quality = frappe.db.get_value("BOM", bom, "diamond_quality")

    # ── metal_touch auto-fetch ─────────────────────────────
    if bom and not metal_touch:
        metal_touch = frappe.db.get_value("BOM", bom, "metal_touch")

    # ── design_portal default ──────────────────────────────
    if not design_portal:
        design_portal = "As Per Design"

    # ── design portal checkboxes ───────────────────────────
    is_as_per_design        = 1 if design_portal == "As Per Design" else 0
    is_as_per_customization = 1 if design_portal == "As Per Customized" else 0

    # ── jobwork flags ──────────────────────────────────────
    cg = 1 if customer_gold else 0
    cd = 1 if customer_diamond else 0
    cs = 1 if customer_stone else 0
    is_jobwork = 1 if (cg or cd or cs) else 0

    # ── Price calculate ────────────────────────────────────
    if bom and (not rate or float(rate) == 0):
        try:
            price_data = get_item_price(
                customer=customer,
                item_code=item_code,
                bom=bom,
                diamond_quality=diamond_quality,
                metal_touch=metal_touch
            )
            dia_amount    = price_data["dia_overall_summary"]["total_amount"]
            gem_amount    = price_data["gem_summary"]["total_gemstone_amount"]
            metal_total   = sum(
                v.get("gold_amount", 0) + v.get("making_charge", 0)
                for v in price_data["metal_price_data"].values()
            )
            finding_total = sum(
                v.get("finding_amount", 0) + v.get("finding_making_charge", 0)
                for v in price_data["finding_price_data"].values()
            )
            calculated_rate = round(dia_amount + gem_amount + metal_total + finding_total, 2)
        except Exception as e:
            frappe.log_error(f"Price calc failed for {item_code}: {str(e)}", "Cart Price Error")
            calculated_rate = float(rate or 0)

    # ── Fix: validate user exists in Frappe User doctype ──
    raw_user = user or frappe.session.user
    user_exists = frappe.db.exists("User", raw_user)
    current_user = raw_user if user_exists else ""

    item_image = frappe.db.get_value("Item", item_code, "image") or ""

    # ── Find active cart ───────────────────────────────────
    active_cart = frappe.db.get_value(
        "Portal Order",
        {"customer": customer, "status": "Draft"},
        "name",
        order_by="creation asc"
    )

    if active_cart:
        doc = frappe.get_doc("Portal Order", active_cart)
    else:
        doc = frappe.new_doc("Portal Order")
        doc.customer = customer
        doc.status   = "Draft"
        doc.company  = frappe.defaults.get_user_default("Company")
        doc.currency = "INR"

    # ── Normalize helpers ──────────────────────────────────
    def normalize_json(val):
        v = (val or "").strip()
        if not v:
            return ""
        try:
            import json
            parsed = json.loads(v)
            return json.dumps(parsed, sort_keys=True, ensure_ascii=False)
        except Exception:
            return v

    # ── Incoming values for match ──────────────────────────
    incoming_customized_data = normalize_json(customized_data)
    incoming_cg = cg
    incoming_cd = cd
    incoming_cs = cs

    # ── Update existing item (only Draft rows) ─────────────
    item_found = False
    for row in doc.items:
        row_status = getattr(row, "status", "Draft")
        if row.item_code != item_code or row_status != "Draft":
            continue

        same_customized_data      = normalize_json(row.customized_data) == incoming_customized_data
        same_as_per_design        = (row.as_per_design or 0)        == is_as_per_design
        same_as_per_customization = (row.as_per_customization or 0) == is_as_per_customization
        same_cg = (row.customer_gold    or 0) == incoming_cg
        same_cd = (row.customer_diamond or 0) == incoming_cd
        same_cs = (row.customer_stone   or 0) == incoming_cs

        if (same_customized_data
                and same_as_per_design
                and same_as_per_customization
                and same_cg and same_cd and same_cs):
            row.quantity             = row.quantity + qty
            row.rate                 = calculated_rate
            row.amount               = row.quantity * calculated_rate
            row.user                 = current_user
            row.as_per_design        = is_as_per_design
            row.as_per_customization = is_as_per_customization
            row.customer_gold        = cg
            row.customer_diamond     = cd
            row.customer_stone       = cs
            row.job_work             = is_jobwork  # ✅ Outwork checkbox
            row.jobwork              = is_jobwork  # ✅ jobwork checkbox
            item_found = True
            break

    # ── Add new item ───────────────────────────────────────
    if not item_found:
        doc.append("items", {
            "item_code":             item_code,
            "quantity":              qty,
            "rate":                  calculated_rate,
            "amount":                qty * calculated_rate,
            "bom":                   bom or "",
            "image":                 item_image,
            "user":                  current_user,
            "status":                "Draft",
            "as_per_design":         is_as_per_design,
            "as_per_customization":  is_as_per_customization,
            "customized_data":       customized_data or "",
            "job_work":              is_jobwork,   # ✅ Outwork checkbox
            "customer_gold":         cg,
            "customer_diamond":      cd,
            "customer_stone":        cs,
            "jobwork":               is_jobwork,   # ✅ jobwork checkbox
        })

    _recalculate_totals(doc)
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "success":        True,
        "order":          doc.name,
        "total_quantity": doc.total_quantity,
        "total_amount":   doc.total_amount,
        "item_rate":      calculated_rate,
    }

# ─────────────────────────────────────────────
#  GET CART ORDERS  (Draft)
# ─────────────────────────────────────────────

# @frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
# def get_cart_orders(customer=None, user=None):
    
#     if customer:
#         active_cart = frappe.db.get_value(
#             "Portal Order",
#             {
#                 "customer": customer,
#                 "status": ["in", ["Draft"]] 
#             },
#             "name"
#         )

#         if not active_cart:
#             return {"success": True, "orders": []}

#         cart = frappe.get_doc("Portal Order", active_cart)
#         return {
#             "success": True,
#             "orders": [{
#                 "name": cart.name,
#                 "customer": cart.customer,
#                 "status": cart.status,
#                 "total_quantity": cart.total_quantity or 0,
#                 "total_amount": cart.total_amount or 0,
#                 "items": _serialize_items(cart.items),  
#             }]
#         }

#     if user:
#         assigned_customers = frappe.get_all(
#             "Customer Representatives",
#             filters={"user_id": user},
#             pluck="parent"
#         )

#         if not assigned_customers:
#             return {"success": True, "orders": []}

#         result = []
#         for cust in assigned_customers:
#             active_cart = frappe.db.get_value(
#                 "Portal Order",
#                 {"customer": cust, "status": "Draft"}, 
#                 "name"
#             )

#             if not active_cart:
#                 continue

#             cart = frappe.get_doc("Portal Order", active_cart)
#             draft_items = _serialize_items(cart.items)  

#             if not draft_items:
#                 continue

#             result.append({
#                 "name": cart.name,
#                 "customer": cart.customer,
#                 "status": cart.status,
#                 "total_quantity": cart.total_quantity or 0,
#                 "total_amount": cart.total_amount or 0,
#                 "items": _serialize_items(cart.items),
#             })

#         return {"success": True, "orders": result}

#     frappe.throw(_("Customer or User required"))

@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def get_cart_orders(customer=None, user=None):
    
    if customer:
        active_cart = frappe.db.get_value(
            "Portal Order",
            {"customer": customer, "status": ["in", ["Draft"]]},
            "name"
        )
        if not active_cart:
            return {"success": True, "orders": []}

        cart = frappe.get_doc("Portal Order", active_cart)
        return {
            "success": True,
            "orders": [{
                "name": cart.name,
                "customer": cart.customer,
                "status": cart.status,
                "total_quantity": cart.total_quantity or 0,
                "total_amount": cart.total_amount or 0,
                "items": _serialize_items(cart.items),
            }]
        }

    if user:
        assigned_customers = frappe.get_all(
            "Customer Representatives",
            filters={"user_id": user},
            pluck="parent"
        )
        if not assigned_customers:
            return {"success": True, "orders": []}

        result = []
        for cust in assigned_customers:
            active_cart = frappe.db.get_value(
                "Portal Order",
                {"customer": cust, "status": "Draft"},
                "name"
            )
            if not active_cart:
                continue

            cart = frappe.get_doc("Portal Order", active_cart)
            items = _serialize_items(cart.items)  

            if not items:
                continue

            result.append({
                "name": cart.name,
                "customer": cart.customer,
                "status": cart.status,
                "total_quantity": cart.total_quantity or 0,
                "total_amount": cart.total_amount or 0,
                "items": items,  # ✅ reuse
            })

        return {"success": True, "orders": result}

    frappe.throw(_("Customer or User required"))

# ─────────────────────────────────────────────
#  GET CART COUNT
# ─────────────────────────────────────────────

@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def get_cancelled_orders(customer=None, user=None):
    
    if customer:
        active_cart = frappe.db.get_value(
            "Portal Order",
            {"customer": customer, "status": ["in", ["Draft"]]},
            "name"
        )
        if not active_cart:
            return {"success": True, "orders": []}

        cart = frappe.get_doc("Portal Order", active_cart)
        return {
            "success": True,
            "orders": [{
                "name": cart.name,
                "customer": cart.customer,
                "status": cart.status,
                "total_quantity": cart.total_quantity or 0,
                "total_amount": cart.total_amount or 0,
                "items": _serialize_items(cart.items, status_filter="Cancel Order"),
                # "items": _serialize_items(doc.items, status_filter="Ordered"), 
            }]
        }

    if user:
        assigned_customers = frappe.get_all(
            "Customer Representatives",
            filters={"user_id": user},
            pluck="parent"
        )
        if not assigned_customers:
            return {"success": True, "orders": []}

        result = []
        for cust in assigned_customers:
            active_cart = frappe.db.get_value(
                "Portal Order",
                {"customer": cust, "status": "Cancel Order"},
                "name"
            )
            if not active_cart:
                continue

            cart = frappe.get_doc("Portal Order", active_cart)
            items = _serialize_items(cart.items)  

            if not items:
                continue

            result.append({
                "name": cart.name,
                "customer": cart.customer,
                "status": cart.status,
                "total_quantity": cart.total_quantity or 0,
                "total_amount": cart.total_amount or 0,
                "items": items,  
            })

        return {"success": True, "orders": result}

    frappe.throw(_("Customer or User required"))


@frappe.whitelist(allow_guest=True, methods=["POST"])
def add_back_cancelled_item(order_name=None, row_name=None):
    """
    Cancelled item ki status wapas Draft karo using exact row name
    """
    if not order_name or not row_name:
        frappe.throw(_("Order name and row name required"))

    cart = frappe.get_doc("Portal Order", order_name)

    item_found = False
    for item in cart.items:
        if item.name == row_name:
            # Status check - sirf cancelled item hi revert ho
            if item.status != "Cancel Order":
                frappe.throw(_("This item is not in cancelled state"))
            
            item.status = "Draft"
            item_found = True
            break

    if not item_found:
        frappe.throw(_("Item row not found in this order"))
        
    _recalculate_totals(cart)

    cart.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "success": True,
        "message": "Item added back to cart",
        "row_name": row_name,
        "order_name": cart.name
    }


# ─────────────────────────────────────────────
#  UPDATE CART ITEM QTY
# ─────────────────────────────────────────────

# @frappe.whitelist(allow_guest=True)
# def update_cart_item_qty(order_name, item_code, quantity, user=None):
#     qty = float(quantity or 0)
#     if qty < 1:
#         frappe.throw(_("Quantity must be at least 1"))

#     doc = frappe.get_doc("Portal Order", order_name)

#     if doc.status == "Cancel Order":
#         frappe.throw(_("Cannot modify a cancelled order"))

#     found = False
#     old_qty = None  

#     for row in doc.items:
#         if row.item_code == item_code:
#             if row.status == "Cancel Order":
#                 frappe.throw(_("Cannot modify a cancelled item"))
            
#             old_qty = row.quantity  
#             row.quantity = qty
#             row.amount = qty * (row.rate or 0)
#             found = True
#             break

#     if not found:
#         frappe.throw(_("Item not found in order"))

#     _recalculate_totals_draft_only(doc)
#     doc.save(ignore_permissions=True)

#     changed_by = user or frappe.session.user

#     if old_qty is not None and old_qty != qty and doc.status == "Ordered":
#         doc.add_comment(
#             comment_type="Info",
#             text=f" <b>{changed_by}</b> changed quantity of <b>{item_code}</b> from <b>{int(old_qty)}</b> to <b>{int(qty)}</b>"
#         )

#     frappe.db.commit()

#     return {
#         "success": True,
#         "order": doc.name,
#         "total_quantity": doc.total_quantity,
#         "total_amount": doc.total_amount,
#     }
   
    
@frappe.whitelist(allow_guest=True)
def update_cart_item_qty(order_name, item_code, quantity, row_name=None, user=None):
    qty = float(quantity or 0)
    if qty < 1:
        frappe.throw(_("Quantity must be at least 1"))

    max_retries = 3
    for attempt in range(max_retries):
        try:
            doc = frappe.get_doc("Portal Order", order_name)

            if doc.status == "Cancel Order":
                frappe.throw(_("Cannot modify a cancelled order"))

            found   = False
            old_qty = None

            for row in doc.items:
                if row.item_code != item_code:
                    continue

                row_status = getattr(row, "status", "Draft")
                if row_status == "Cancel Order":
                    continue

                # row_name se exact row match
                if row_name and row.name != row_name:
                    continue

                old_qty      = row.quantity
                row.quantity = qty
                row.amount   = qty * (row.rate or 0)
                found        = True
                break

            if not found:
                frappe.throw(_("Item not found in order"))

            _recalculate_totals_draft_only(doc)
            doc.save(ignore_permissions=True)

            changed_by = user or frappe.session.user
            if old_qty is not None and old_qty != qty and doc.status == "Ordered":
                doc.add_comment(
                    comment_type="Info",
                    text=f"<b>{changed_by}</b> changed quantity of <b>{item_code}</b> from <b>{int(old_qty)}</b> to <b>{int(qty)}</b>"
                )

            frappe.db.commit()

            return {
                "success":        True,
                "order":          doc.name,
                "total_quantity": doc.total_quantity,
                "total_amount":   doc.total_amount,
            }

        except frappe.exceptions.TimestampMismatchError:
            if attempt == max_retries - 1:
                frappe.throw(_("Too many simultaneous updates. Please try again."))
            import time
            time.sleep(0.1 * (attempt + 1))
            continue

# ─────────────────────────────────────────────
#  REMOVE CART ITEM
# ─────────────────────────────────────────────

# @frappe.whitelist(allow_guest=True)
# def cancel_cart_item(order_name, item_code, user=None):
#     doc = frappe.get_doc("Portal Order", order_name)

#     for row in doc.items:
#         if row.item_code == item_code:
#             row.status = "Cancel Order"
#             break

#     # Check karo - check there is any draft is here?
#     draft_items = [r for r in doc.items if getattr(r, "status", "Draft") == "Draft"]
    
#     if not draft_items:
#         # every items cancel → whole Order cancel 
#         doc.status = "Cancel Order"
    
#     _recalculate_totals_draft_only(doc)
#     doc.save(ignore_permissions=True)
#     frappe.db.commit()

#     return {
#         "success": True,
#         "order": doc.name,
#         "order_cancelled": doc.status == "Cancel Order",
#         "remaining_draft_items": len(draft_items),
#     }


@frappe.whitelist(allow_guest=True)
def cancel_cart_item(order_name, item_code, row_name=None, user=None):
    doc = frappe.get_doc("Portal Order", order_name)

    for row in doc.items:
        if row.item_code != item_code:
            continue
        if getattr(row, "status", "Draft") != "Draft":
            continue

        # row_name hai to exact row match karo
        if row_name and row.name != row_name:
            continue

        row.status = "Cancel Order"
        break

    # only active draft items
    draft_items = [
        r for r in doc.items
        if getattr(r, "status", "Draft") == "Draft"
    ]

    # all items cancelled
    if not draft_items:
        doc.status = "Cancel Order"

    _recalculate_totals_draft_only(doc)
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "success": True,
        "order": doc.name,
        "order_cancelled": doc.status == "Cancel Order",
        "remaining_draft_items": len(draft_items),
    }

def _recalculate_totals_draft_only(doc):
    """Only Draft items total calculate """
    total_qty = 0
    total_amt = 0
    for row in doc.items:
        # Cancelled items skip 
        if getattr(row, "status", "Draft") == "Cancel Order":
            continue
        total_qty += row.quantity or 0
        total_amt += (row.quantity or 0) * (row.rate or 0)
    doc.total_quantity = total_qty
    doc.total_amount = total_amt
# ─────────────────────────────────────────────
#  PLACE ORDER  (Draft → Ordered + new cart)
# ─────────────────────────────────────────────

# @frappe.whitelist(allow_guest=True)
# def confirm_cart_orders(customer, order_date=None, notes=None):
#     if not customer:
#         frappe.throw(_("Customer required"))

#     active_cart = frappe.db.get_value(
#         "Portal Order",
#         {"customer": customer, "status": "Draft"},
#         "name"
#     )

#     if not active_cart:
#         frappe.throw(_("No active cart found"))

#     cart = frappe.get_doc("Portal Order", active_cart)


#     draft_items = [r for r in cart.items if getattr(r, "status", "Draft") == "Draft"]

#     if not draft_items:
#         frappe.throw(_("No active items in cart"))


#     cart.status = "Ordered"
#     cart.order_date = order_date or frappe.utils.today()
#     if notes:
#         cart.notes = notes
        
#     # for row in cart.items:
#     #     if getattr(row, "status", "Draft") == "Draft":
#     #         row.status = "Ordered"
#     for row in cart.items:
#         if row.status == "Draft":
#             frappe.db.set_value(
#                 "Portal Order Item",   
#                 row.name,             
#                 "status",
#                 "Ordered"
#             )

#     cart.save(ignore_permissions=True)
#     frappe.db.commit()

#     return {
#         "success": True,
#         "ordered_cart": cart.name,
#         "order_date": str(cart.order_date),
#         "message": "Order placed successfully!",
#     }

@frappe.whitelist(allow_guest=True)
def confirm_cart_orders(customer, order_date=None, notes=None, user=None): 
    if not customer:
        frappe.throw(_("Customer required"))

    active_cart = frappe.db.get_value(
        "Portal Order",
        {"customer": customer, "status": "Draft"},
        "name"
    )

    if not active_cart:
        frappe.throw(_("No active cart found"))

    cart = frappe.get_doc("Portal Order", active_cart)

    draft_items = [r for r in cart.items if getattr(r, "status", "Draft") == "Draft"]
    if not draft_items:
        frappe.throw(_("No active items in cart"))

    final_order_date = frappe.utils.getdate(order_date) if order_date else frappe.utils.today()
    current_user = user or frappe.session.user   # ✅ who is confirming

    cart.status     = "Ordered"
    cart.order_date = final_order_date
    cart.order_by   = current_user               # ✅ your field name is order_by

    if notes:
        cart.notes = notes

    for row in cart.items:
        if row.status == "Draft":
            row.status = "Ordered"

    cart.save(ignore_permissions=True)

    
    frappe.db.set_value("Portal Order", cart.name, {
        "order_date": final_order_date,
        "order_by":   current_user,             
    }, update_modified=False)

    frappe.db.commit()

    return {
        "success":      True,
        "ordered_cart": cart.name,
        "order_date":   str(final_order_date),
        "order_by":     current_user,           
        "message":      "Order placed successfully!",
    }

# ─────────────────────────────────────────────
#  GET PLACED ORDERS  (Ordered)
# ─────────────────────────────────────────────
# @frappe.whitelist(allow_guest=True)
# def get_placed_orders(customer=None, user=None):

#     # ── CASE 1: Customer login ──
#     if customer:
#         filters = {"customer": customer, "status": "Ordered"}
#         orders = frappe.get_all(
#             "Portal Order",
#             filters=filters,
#             fields=["name", "customer", "user", "order_date", "status", "total_quantity", "total_amount"],
#             order_by="order_date desc",
#         )

#     # ── CASE 2: Rep/User login ──
#     elif user:
#         assigned_customers = frappe.get_all(
#             "Customer Representatives",
#             filters={"user_id": user},
#             pluck="parent"
#         )

#         if not assigned_customers:
#             return {"success": True, "count": 0, "orders": []}

#         orders = frappe.get_all(
#             "Portal Order",
#             filters={
#                 "customer": ["in", assigned_customers],
#                 "status": "Ordered"
#             },
#             fields=["name", "customer", "user", "order_date", "status", "total_quantity", "total_amount"],
#             order_by="order_date desc",
#         )

#     else:
#         frappe.throw(_("Customer or User required"))

#     if not orders:
#         return {"success": True, "count": 0, "orders": []}

#     result = []
#     for order in orders:
#         doc = frappe.get_doc("Portal Order", order["name"])
#         result.append({
#             "name": doc.name,
#             "customer": doc.customer,
#             "order_by": doc.order_by,
#             # "order_by": getattr(doc, "order_by", "") or "",
#             # "user_full_name": _get_full_name(doc.user),
#             "order_date": str(doc.order_date) if doc.order_date else "",
#             "status": doc.status,
#             "total_quantity": doc.total_quantity,
#             "total_amount": doc.total_amount,
#             "items": _serialize_items(doc.items),
#             "items": _serialize_items(doc.items, status_filter="Ordered")
            
#         })

#     return {"success": True, "count": len(result), "orders": result}

@frappe.whitelist(allow_guest=True)
def get_placed_orders(customer=None, user=None):

    # ── CASE 1: Customer login ──
    if customer:
        filters = {"customer": customer, "status": "Ordered"}
        orders = frappe.get_all(
            "Portal Order",
            filters=filters,
            fields=["name", "customer", "user", "order_date", "status", "total_quantity", "total_amount"],
            order_by="order_date desc",
        )

    # ── CASE 2: Rep/User login ──
    elif user:
        assigned_customers = frappe.get_all(
            "Customer Representatives",
            filters={"user_id": user},
            pluck="parent"
        )

        if not assigned_customers:
            return {"success": True, "count": 0, "orders": []}

        orders = frappe.get_all(
            "Portal Order",
            filters={
                "customer": ["in", assigned_customers],
                "status": "Ordered"
            },
            fields=["name", "customer", "user", "order_date", "status", "total_quantity", "total_amount"],
            order_by="order_date desc",
        )

    else:
        frappe.throw(_("Customer or User required"))

    if not orders:
        return {"success": True, "count": 0, "orders": []}

    result = []
    for order in orders:
        doc = frappe.get_doc("Portal Order", order["name"])
        result.append({
            "name": doc.name,
            "customer": doc.customer,
            "order_by": getattr(doc, "order_by", "") or "",
            "order_date": str(doc.order_date) if doc.order_date else "",
            "status": doc.status,
            "total_quantity": doc.total_quantity,
            "total_amount": doc.total_amount,
            "items": _serialize_items(doc.items, status_filter="Ordered"), 
        })

    return {"success": True, "count": len(result), "orders": result}

@frappe.whitelist(allow_guest=True)
def cancel_order(order_name):
    """Whole Order cancel"""
    doc = frappe.get_doc("Portal Order", order_name)

    if doc.status == "Cancel Order":
        frappe.throw(_("Order already cancelled"))

    doc.status = "Cancel Order"
    for row in doc.items:
        row.status = "Cancel Order"

    _recalculate_totals_draft_only(doc)  
    doc.save()
    frappe.db.commit()

    return {
        "success": True,
        "order": doc.name,
        "message": "Order cancelled successfully",
    }


    """Only one item cancel"""
    doc = frappe.get_doc("Portal Order", order_name)

    if doc.status == "Cancel Order":
        frappe.throw(_("Order is already cancelled"))

    found = False
    for row in doc.items:
        if row.item_code == item_code:
            if row.status == "Cancel Order":
                frappe.throw(_("Item already cancelled"))
            row.status = "Cancel Order"
            found = True
            break

    if not found:
        frappe.throw(_("Item not found in order"))

    all_cancelled = all(
        getattr(r, "status", "") == "Cancel Order" for r in doc.items
    )
    if all_cancelled:
        doc.status = "Cancel Order"

    _recalculate_totals_draft_only(doc) 
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "success": True,
        "order": doc.name,
        "order_cancelled": doc.status == "Cancel Order",
        "message": f"Item {item_code} cancelled successfully",
    }
    
    
@frappe.whitelist(allow_guest=True)
def cancel_order_item(order_name, item_code, row_name=None):
    """Only one item cancel"""
    doc = frappe.get_doc("Portal Order", order_name)

    if doc.status == "Cancel Order":
        frappe.throw(_("Order is already cancelled"))

    found = False
    for row in doc.items:
        if row.item_code != item_code:
            continue

        row_status = getattr(row, "status", "Draft")
        if row_status == "Cancel Order":
            continue

        # ✅ row_name hai to exact row match karo
        if row_name and row.name != row_name:
            continue

        row.status = "Cancel Order"
        found = True
        break

    if not found:
        frappe.throw(_("Item not found in order"))

    all_cancelled = all(
        getattr(r, "status", "") == "Cancel Order" for r in doc.items
    )
    if all_cancelled:
        doc.status = "Cancel Order"

    _recalculate_totals_draft_only(doc)
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "success":         True,
        "order":           doc.name,
        "order_cancelled": doc.status == "Cancel Order",
        "message":         f"Item {item_code} cancelled successfully",
    }

# -----------------------------------------
    
# @frappe.whitelist()
# def subcategory_count(categoryName, user_type, customer=None):
#     try:
#         if user_type == "Customer":
#             sql_query = """
#                 SELECT 
#                     ti.item_category, 
#                     ti.item_subcategory, 
#                     tb.metal_type,

#                     COUNT(DISTINCT CASE
#                         WHEN tav.is_subcategory = 1  
#                             AND ti.item_subcategory IS NOT NULL
#                             AND fbom.bom_type = 'Finish Goods' 
#                             AND fbom.is_active = 1  
#                         THEN IFNULL(ti.variant_of, ti.item_code)
#                     END) AS item_count,

#                     COUNT(DISTINCT CASE
#                         WHEN tav.is_subcategory = 1 
#                             AND ti.item_subcategory IS NOT NULL 
#                             AND fbom.bom_type = 'Finish Goods' 
#                             AND fbom.is_active = 1 
#                         THEN IFNULL(ti.variant_of, ti.item_code)
#                     END) AS serial_count,

#                     ( 
#                         SELECT item.image
#                         FROM `tabItem` AS item 
#                         INNER JOIN ( 
#                             SELECT 
#                                 IFNULL(i.variant_of, i.item_code) AS group_key,
#                                 MIN(i.item_code) AS first_item_code
#                             FROM `tabItem` AS i
#                             INNER JOIN `tabBOM` AS b 
#                                 ON i.item_code = b.item 
#                                 AND b.bom_type = 'Finish Goods'
#                             LEFT JOIN `tabItem Default` AS idf3 
#                                 ON i.item_name = idf3.parent
#                                 AND idf3.company = 'Gurukrupa Export Private Limited'
#                             GROUP BY IFNULL(i.variant_of, i.item_code)
#                         ) AS first_variant
#                             ON item.item_code = first_variant.first_item_code
#                         WHERE 
#                             item.item_subcategory = ti.item_subcategory
#                             AND item.image IS NOT NULL
#                             AND (item.front_view IS NULL OR item.image != item.front_view)
#                         ORDER BY item.creation DESC
#                         LIMIT 1
#                     ) AS first_image

#                 FROM `tabCataloge Item Details` AS tci

#                 LEFT JOIN `tabCataloge Master` AS tcm 
#                     ON tcm.name = tci.parent

#                 LEFT JOIN `tabItem` AS ti 
#                     ON ti.name = tci.item_code

#                 LEFT JOIN `tabBOM` AS tb 
#                     ON ti.name = tb.item

#                 LEFT JOIN `tabBOM` AS fbom 
#                     ON fbom.item = ti.name  

#                 JOIN `tabAttribute Value` AS tav 
#                     ON ti.item_subcategory = tav.name  

#                 WHERE  
#                     (
#                         (tav.is_subcategory = 1 AND ti.item_subcategory IS NOT NULL)
#                         OR 
#                         (fbom.bom_type = 'Finish Goods' AND fbom.is_active = 1)
#                     )
#                     AND tcm.customer = %s
#                     AND tb.is_active = 1
#                     AND ti.item_category = %s

#                 GROUP BY 
#                     ti.item_category, 
#                     ti.item_subcategory, 
#                     tb.metal_type

#                 ORDER BY 
#                     ti.item_category, 
#                     ti.item_subcategory, 
#                     tb.metal_type
#             """

#             result = frappe.db.sql(sql_query, (customer, categoryName), as_dict=True)

#         else:
#             sql_query = """
#                 SELECT
#                     item.item_subcategory,

#                     COUNT(DISTINCT CASE
#                         WHEN bom.bom_type = 'Finish Goods' AND bom.is_active = 1 
#                         THEN IFNULL(item.variant_of, item.item_code)
#                     END) AS item_count,

#                     COUNT(DISTINCT CASE
#                         WHEN bom.bom_type = 'Finish Goods' AND bom.is_active = 1 
#                         THEN IFNULL(item.variant_of, item.item_code)
#                     END) AS serial_count,

#                     (
#                         SELECT item2.image
#                         FROM `tabItem` AS item2
#                         INNER JOIN (
#                             SELECT
#                                 IFNULL(i.variant_of, i.item_code) AS group_key,
#                                 MIN(i.item_code) AS first_item_code
#                             FROM `tabItem` AS i
#                             INNER JOIN `tabBOM` AS b 
#                                 ON i.item_code = b.item 
#                                 AND b.bom_type = 'Finish Goods'
#                             LEFT JOIN `tabItem Default` AS idf3 
#                                 ON i.item_name = idf3.parent
#                                 AND idf3.company = 'Gurukrupa Export Private Limited'
#                             GROUP BY IFNULL(i.variant_of, i.item_code)
#                         ) AS first_variant
#                             ON item2.item_code = first_variant.first_item_code
#                         WHERE 
#                             item2.item_subcategory = item.item_subcategory
#                             AND item2.image IS NOT NULL
#                             AND (item2.front_view IS NULL OR item2.image != item2.front_view)
#                         ORDER BY item2.creation DESC
#                         LIMIT 1
#                     ) AS first_image

#                 FROM `tabItem` AS item

#                 JOIN `tabAttribute Value` AS tav 
#                     ON item.item_subcategory = tav.name

#                 LEFT JOIN `tabBOM` AS bom 
#                     ON item.item_code = bom.item

#                 WHERE 
#                     tav.is_subcategory = 1
#                     AND item.item_subcategory IS NOT NULL
#                     AND item.item_category = %s

#                 GROUP BY 
#                     item.item_subcategory

#                 ORDER BY 
#                     item.item_subcategory
#             """

#             result = frappe.db.sql(sql_query, (categoryName,), as_dict=True)

#         return result

#     except Exception as e:
#         return {"error": str(e)}

# ----------------------------

# @frappe.whitelist(allow_guest=True)
# def catalogue_data2(selectedSubcategory=None, itemCategory=None, itemCode=None, metalType=None, company=None, customer=None):

#     if selectedSubcategory is None:
#         selectedSubcategory = frappe.form_dict.get("selectedSubcategory")

#     if itemCode is None:
#         itemCode = frappe.form_dict.get("itemCode")

#     if metalType is None:
#         metalType = frappe.form_dict.get("metalType")

#     if itemCategory is None:
#         itemCategory = frappe.form_dict.get("itemCategory")

#     values = {}

#     # ---------------- FILTERS ----------------
#     sub_where = "b.bom_type = 'Finish Goods'"
#     where_clause = "1=1 AND bom.bom_type = 'Finish Goods'"

#     if metalType:
#         sub_where += " AND b.metal_type = %(metalType)s"
#         where_clause += " AND bom.metal_type = %(metalType)s"
#         values["metalType"] = metalType

#     if selectedSubcategory:
#         sub_where += " AND i.item_subcategory = %(selectedSubcategory)s"
#         where_clause += " AND item.item_subcategory = %(selectedSubcategory)s"
#         values["selectedSubcategory"] = selectedSubcategory

#     if itemCategory:
#         sub_where += " AND i.item_category = %(itemCategory)s"
#         where_clause += " AND item.item_category = %(itemCategory)s"
#         values["itemCategory"] = itemCategory

#     if itemCode:
#         sub_where += " AND i.item_code = %(itemCode)s"
#         where_clause += " AND item.item_code = %(itemCode)s"
#         values["itemCode"] = itemCode

#     # ✅ company filter sirf where_clause mein, sub_where se hataya
#     if company:
#         where_clause += " AND idf.company = %(company)s"
#         values["company"] = company
#         company_join_condition = "AND idf3.company = %(company)s"
#     else:
#         where_clause += " AND idf.company = 'Gurukrupa Export Private Limited'"
#         company_join_condition = "AND idf3.company = 'Gurukrupa Export Private Limited'"

#     if customer:
#         wishlist_case = "MAX(CASE WHEN tci.wishlist = 1 AND tcm.customer IS NOT NULL THEN 1 ELSE 0 END) AS wishlist"
#         customer_join = "AND tcm.customer = %(customer)s"
#         values["customer"] = customer
#     else:
#         wishlist_case = "0 AS wishlist"
#         customer_join = ""

#     db_data = frappe.db.sql(f"""
#         SELECT
#             item.name,
#             bom.name,
#             idf.company,
#             tci.trending,
#             {wishlist_case},
#             item.creation,
#             item.item_code,
#             item.item_category,
#             item.image,
#             item.sketch_image,
#             item.front_view AS cad_image,
#             CASE
#                 WHEN item.front_view = item.image THEN 'CAD Image'
#                 ELSE 'FG Image'
#             END AS image_remark,
#             item.item_subcategory,
#             item.stylebio,
#             bom.tag_no,
#             bom.diamond_quality,
#             item.setting_type,
#             FORMAT(bom.gross_weight,3) AS gross_metal_weight,
#             FORMAT(bom.metal_and_finding_weight,3) AS net_metal_finding_weight,
#             FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
#             FORMAT(bom.other_weight,3) AS other_weight,
#             FORMAT(bom.finding_weight_,3) AS finding_weight_,
#             bom.metal_colour,
#             bom.metal_touch,
#             bom.metal_purity,
#             FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,
#             bom.total_diamond_pcs,
#             bom.total_gemstone_pcs,
#             FORMAT(bom.gemstone_weight,3) AS gemstone_weight,
#             FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
#             FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
#             FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,
#             bom.navratna,
#             bom.lock_type,
#             bom.feature,
#             bom.enamal,
#             bom.rhodium,
#             bom.sizer_type,
#             bom.height,
#             bom.length,
#             bom.width,
#             bom.breadth,
#             bom.product_size,
#             bom.design_style,
#             bom.nakshi_from,
#             bom.vanki_type,
#             bom.total_length,
#             bom.detachable,
#             bom.back_side_size,
#             bom.changeable,
#             item.variant_of,
#             CASE 
#                 WHEN vc.variant_count > 1 THEN 1 
#                 ELSE 0 
#             END AS rn,
#             bom.finding_pcs,
#             bom.total_other_pcs,
#             bom.total_other_weight,
#             GROUP_CONCAT(DISTINCT item.name ORDER BY item.creation ASC) AS variant_name,
#             GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
#             GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,
#             GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
#             GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
#             GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
#             GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,
#             GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
#             GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,
#             GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
#             GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
#             GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
#             GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
#             GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,
#             GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
#             GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
#             GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size

#         FROM `tabItem` AS item

#         LEFT JOIN (
#             SELECT 
#                 IFNULL(i.variant_of, i.item_code) AS group_key,
#                 COUNT(DISTINCT i.item_code) AS variant_count
#             FROM `tabItem` AS i
#             INNER JOIN `tabBOM` AS b ON i.item_code = b.item AND b.bom_type = 'Finish Goods'
#             GROUP BY IFNULL(i.variant_of, i.item_code)
#         ) vc ON vc.group_key = IFNULL(item.variant_of, item.item_code)

#         INNER JOIN (
#             SELECT
#                 IFNULL(i.variant_of, i.item_code) AS group_key,
#                 MIN(i.item_code) AS first_item_code
#             FROM `tabItem` AS i
#             INNER JOIN `tabBOM` AS b ON i.item_code = b.item
#             LEFT JOIN `tabItem Default` AS idf3
#                 ON i.item_name = idf3.parent
#                 {company_join_condition}
#             WHERE {sub_where}
#             GROUP BY IFNULL(i.variant_of, i.item_code)
#         ) AS first_variant
#             ON item.item_code = first_variant.first_item_code

#         LEFT JOIN `tabCataloge Item Details` AS tci ON tci.item_code = item.name
#         LEFT JOIN `tabCataloge Master` AS tcm ON tcm.name = tci.parent {customer_join}
#         LEFT JOIN `tabBOM` AS bom ON item.item_code = bom.item
#         LEFT JOIN `tabDesign Attributes` AS td ON item.item_code = td.parent
#         LEFT JOIN `tabBOM Metal Detail` AS mt ON bom.name = mt.parent
#         LEFT JOIN `tabBOM Gemstone Detail` AS gd ON bom.name = gd.parent
#         LEFT JOIN `tabBOM Diamond Detail` AS dd ON bom.name = dd.parent
#         LEFT JOIN `tabBOM Finding Detail` AS fd ON bom.name = fd.parent
#         LEFT JOIN `tabBOM Other Detail` AS od ON bom.name = od.parent
#         LEFT JOIN `tabItem Default` AS idf ON item.item_name = idf.parent

#         WHERE {where_clause}
#         GROUP BY item.item_code, item.variant_of
#         ORDER BY item.creation DESC

#     """, values, as_dict=True)

#     # -------- MULTISELECT ATTRIBUTES --------
#     item_codes = [row.item_code for row in db_data]

#     if item_codes:
#         db_res = frappe.db.sql("""
#             SELECT parent, parentfield,
#             GROUP_CONCAT(design_attribute ORDER BY design_attribute SEPARATOR ', ') AS design_attributes
#             FROM `tabDesign Attribute - Multiselect`
#             WHERE parent IN %(data)s
#             GROUP BY parent, parentfield
#         """, {"data": tuple(item_codes)}, as_dict=True)
#     else:
#         db_res = []

#     attr_map = {}
#     for row in db_res:
#         parent = row["parent"]
#         field = row["parentfield"].replace("custom_", "")
#         value = row["design_attributes"]
#         if parent not in attr_map:
#             attr_map[parent] = {}
#         attr_map[parent][field] = value

#     for row in db_data:
#         attrs = attr_map.get(row.item_code, {})
#         for key, value in attrs.items():
#             row[key] = value

#         row["custom_collection"] = row.get("custom_collection") or None
#         row["custom_language"] = row.get("custom_language") or None
#         row["custom_zodiac"] = row.get("custom_zodiac") or None
#         row["custom_animalbirds"] = row.get("custom_animalbirds") or None
#         row["custom_alphabetnumber"] = row.get("custom_alphabetnumber") or None
#         row["religious"] = row.get("religious") or None

#     # -------- SIMILAR ITEMS TABLE --------
#     if item_codes:
#         similar_links = frappe.db.sql("""
#             SELECT sit.parent AS main_item_code, sit.item_code AS similar_item_code
#             FROM `tabSimilar Item Table` AS sit
#             WHERE sit.parenttype = 'Item'
#             AND sit.parent IN %(item_codes)s
#         """, {"item_codes": tuple(item_codes)}, as_dict=True)
#     else:
#         similar_links = []

#     all_similar_codes = list({lnk["similar_item_code"] for lnk in similar_links})

#     if all_similar_codes:
#         sim_rows = frappe.db.sql("""
#             SELECT
#                 item.name,
#                 bom.name AS bom_name,
#                 idf.company,
#                 tci.trending,
#                 0 AS wishlist,
#                 item.creation,
#                 item.item_code,
#                 item.item_category,
#                 item.image,
#                 item.sketch_image,
#                 item.front_view AS cad_image,
#                 CASE WHEN item.front_view = item.image THEN 'CAD Image' ELSE 'FG Image' END AS image_remark,
#                 item.item_subcategory,
#                 item.stylebio,
#                 bom.tag_no,
#                 bom.diamond_quality,
#                 item.setting_type,
#                 FORMAT(bom.gross_weight,3) AS gross_metal_weight,
#                 FORMAT(bom.metal_and_finding_weight,3) AS net_metal_finding_weight,
#                 FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
#                 FORMAT(bom.other_weight,3) AS other_weight,
#                 FORMAT(bom.finding_weight_,3) AS finding_weight_,
#                 bom.metal_colour,
#                 bom.metal_touch,
#                 bom.metal_purity,
#                 FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,
#                 bom.total_diamond_pcs,
#                 bom.total_gemstone_pcs,
#                 FORMAT(bom.gemstone_weight,3) AS gemstone_weight,
#                 FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
#                 FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
#                 FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,
#                 bom.navratna, bom.lock_type, bom.feature, bom.enamal, bom.rhodium, bom.sizer_type,
#                 bom.height, bom.length, bom.width, bom.breadth, bom.product_size,
#                 bom.design_style, bom.nakshi_from, bom.vanki_type, bom.total_length,
#                 bom.detachable, bom.back_side_size, bom.changeable,
#                 item.variant_of,
#                 bom.finding_pcs, bom.total_other_pcs, bom.total_other_weight,
#                 GROUP_CONCAT(DISTINCT item.name ORDER BY item.creation ASC) AS variant_name,
#                 GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
#                 GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,
#                 GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
#                 GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
#                 GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
#                 GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,
#                 GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
#                 GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,
#                 GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
#                 GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
#                 GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
#                 GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
#                 GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,
#                 GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
#                 GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
#                 GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size
#             FROM `tabItem` AS item
#             LEFT JOIN `tabBOM` AS bom ON item.item_code = bom.item
#             LEFT JOIN `tabCataloge Item Details` AS tci ON tci.item_code = item.name
#             LEFT JOIN `tabDesign Attributes` AS td ON item.item_code = td.parent
#             LEFT JOIN `tabBOM Metal Detail` AS mt ON bom.name = mt.parent
#             LEFT JOIN `tabBOM Gemstone Detail` AS gd ON bom.name = gd.parent
#             LEFT JOIN `tabBOM Diamond Detail` AS dd ON bom.name = dd.parent
#             LEFT JOIN `tabBOM Finding Detail` AS fd ON bom.name = fd.parent
#             LEFT JOIN `tabBOM Other Detail` AS od ON bom.name = od.parent
#             LEFT JOIN `tabItem Default` AS idf ON item.item_name = idf.parent
#             WHERE item.item_code IN %(similar_codes)s
#             GROUP BY item.item_code, item.variant_of
#         """, {"similar_codes": tuple(all_similar_codes)}, as_dict=True)

#         sim_item_codes = [r.item_code for r in sim_rows]
#         if sim_item_codes:
#             sim_attr_res = frappe.db.sql("""
#                 SELECT parent, parentfield,
#                 GROUP_CONCAT(design_attribute ORDER BY design_attribute SEPARATOR ', ') AS design_attributes
#                 FROM `tabDesign Attribute - Multiselect`
#                 WHERE parent IN %(data)s
#                 GROUP BY parent, parentfield
#             """, {"data": tuple(sim_item_codes)}, as_dict=True)
#             sim_attr_map = {}
#             for r in sim_attr_res:
#                 sim_attr_map.setdefault(r["parent"], {})[r["parentfield"].replace("custom_", "")] = r["design_attributes"]
#             for r in sim_rows:
#                 for k, v in sim_attr_map.get(r.item_code, {}).items():
#                     r[k] = v
#                 r["custom_collection"] = r.get("custom_collection") or None
#                 r["custom_language"] = r.get("custom_language") or None
#                 r["custom_zodiac"] = r.get("custom_zodiac") or None
#                 r["custom_animalbirds"] = r.get("custom_animalbirds") or None
#                 r["custom_alphabetnumber"] = r.get("custom_alphabetnumber") or None
#                 r["religious"] = r.get("religious") or None

#         # ✅ FIXED - similar items nested, flat extend nahi
#         existing_item_codes = {row.item_code for row in db_data}
#         sim_row_map = {r["item_code"]: r for r in sim_rows}

#         sim_map = {}
#         for lnk in similar_links:
#             main = lnk["main_item_code"]
#             sim_code = lnk["similar_item_code"]
#             if sim_code not in existing_item_codes and sim_code in sim_row_map:
#                 sim_map.setdefault(main, []).append(sim_row_map[sim_code])

#         for row in db_data:
#             row["similar_items"] = sim_map.get(row.item_code, [])

#     else:
#         for row in db_data:
#             row["similar_items"] = []

#     return db_data

# ---------------
# @frappe.whitelist(allow_guest=True)
# def catalogue_data2(selectedSubcategory=None, itemCategory=None, itemCode=None, metalType=None, company=None, customer=None):

    if selectedSubcategory is None:
        selectedSubcategory = frappe.form_dict.get("selectedSubcategory")

    if itemCode is None:
        itemCode = frappe.form_dict.get("itemCode")

    if metalType is None:
        metalType = frappe.form_dict.get("metalType")

    if itemCategory is None:
        itemCategory = frappe.form_dict.get("itemCategory")

    values = {}

    # ---------------- FILTERS ----------------
    sub_where = "b.bom_type = 'Finish Goods'"
    where_clause = "1=1 AND bom.bom_type = 'Finish Goods'"

    if metalType:
        sub_where += " AND b.metal_type = %(metalType)s"
        where_clause += " AND bom.metal_type = %(metalType)s"
        values["metalType"] = metalType

    if selectedSubcategory:
        sub_where += " AND i.item_subcategory = %(selectedSubcategory)s"
        where_clause += " AND item.item_subcategory = %(selectedSubcategory)s"
        values["selectedSubcategory"] = selectedSubcategory

    if itemCategory:
        sub_where += " AND i.item_category = %(itemCategory)s"
        where_clause += " AND item.item_category = %(itemCategory)s"
        values["itemCategory"] = itemCategory

    if itemCode:
        sub_where += " AND i.item_code = %(itemCode)s"
        where_clause += " AND item.item_code = %(itemCode)s"
        values["itemCode"] = itemCode

    # ✅ company filter SIRF where_clause mein, sub_where se HATAYA
    if company:
        where_clause += " AND idf.company = %(company)s"
        values["company"] = company
        company_join_condition = "AND idf3.company = %(company)s"
    else:
        where_clause += " AND idf.company = 'Gurukrupa Export Private Limited'"
        company_join_condition = "AND idf3.company = 'Gurukrupa Export Private Limited'"

    # wishlist
    if customer:
        wishlist_case = "MAX(CASE WHEN tci.wishlist = 1 AND tcm.customer IS NOT NULL THEN 1 ELSE 0 END) AS wishlist"
        customer_join = "AND tcm.customer = %(customer)s"
        values["customer"] = customer
    else:
        wishlist_case = "0 AS wishlist"
        customer_join = ""

    db_data = frappe.db.sql(f"""
        SELECT
            item.name,
            bom.name,
            idf.company,
            tci.trending,
            {wishlist_case},
            item.creation,
            item.item_code,
            item.item_category,
            item.image,
            item.sketch_image,
            item.front_view AS cad_image,
            CASE
                WHEN item.front_view = item.image THEN 'CAD Image'
                ELSE 'FG Image'
            END AS image_remark,
            item.item_subcategory,
            item.stylebio,
            bom.tag_no,
            bom.diamond_quality,
            item.setting_type,

            FORMAT(bom.gross_weight,3) AS gross_metal_weight,
            FORMAT(bom.metal_and_finding_weight,3) AS net_metal_finding_weight,
            FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
            FORMAT(bom.other_weight,3) AS other_weight,
            FORMAT(bom.finding_weight_,3) AS finding_weight_,

            bom.metal_colour,
            bom.metal_touch,
            bom.metal_purity,
            FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,

            bom.total_diamond_pcs,
            bom.total_gemstone_pcs,
            FORMAT(bom.gemstone_weight,3) AS gemstone_weight,

            FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
            FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
            FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,

            bom.navratna,
            bom.lock_type,
            bom.feature,
            bom.enamal,
            bom.rhodium,
            bom.sizer_type,

            bom.height,
            bom.length,
            bom.width,
            bom.breadth,
            bom.product_size,

            bom.design_style,
            bom.nakshi_from,
            bom.vanki_type,
            bom.total_length,
            bom.detachable,
            bom.back_side_size,
            bom.changeable,

            item.variant_of,

            CASE 
                WHEN vc.variant_count > 1 THEN 1 
                ELSE 0 
            END AS rn,

            bom.finding_pcs,
            bom.total_other_pcs,
            bom.total_other_weight,

            GROUP_CONCAT(DISTINCT item.name ORDER BY item.creation ASC) AS variant_name,

            GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
            GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,

            GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
            GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
            GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
            GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,

            GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
            GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,

            GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
            GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
            GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
            GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
            GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,

            GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
            GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
            GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size

        FROM `tabItem` AS item

        LEFT JOIN (
            SELECT 
                IFNULL(i.variant_of, i.item_code) AS group_key,
                COUNT(DISTINCT i.item_code) AS variant_count
            FROM `tabItem` AS i
            INNER JOIN `tabBOM` AS b ON i.item_code = b.item AND b.bom_type = 'Finish Goods'
            GROUP BY IFNULL(i.variant_of, i.item_code)
        ) vc ON vc.group_key = IFNULL(item.variant_of, item.item_code)

        INNER JOIN (
            SELECT
                IFNULL(i.variant_of, i.item_code) AS group_key,
                MIN(i.item_code) AS first_item_code
            FROM `tabItem` AS i
            INNER JOIN `tabBOM` AS b ON i.item_code = b.item
            LEFT JOIN `tabItem Default` AS idf3
                ON i.item_name = idf3.parent
                {company_join_condition}
            WHERE {sub_where}
            GROUP BY IFNULL(i.variant_of, i.item_code)
        ) AS first_variant
            ON item.item_code = first_variant.first_item_code

        LEFT JOIN `tabCataloge Item Details` AS tci ON tci.item_code = item.name
        LEFT JOIN `tabCataloge Master` AS tcm ON tcm.name = tci.parent {customer_join}
        LEFT JOIN `tabBOM` AS bom ON item.item_code = bom.item
        LEFT JOIN `tabDesign Attributes` AS td ON item.item_code = td.parent
        LEFT JOIN `tabBOM Metal Detail` AS mt ON bom.name = mt.parent
        LEFT JOIN `tabBOM Gemstone Detail` AS gd ON bom.name = gd.parent
        LEFT JOIN `tabBOM Diamond Detail` AS dd ON bom.name = dd.parent
        LEFT JOIN `tabBOM Finding Detail` AS fd ON bom.name = fd.parent
        LEFT JOIN `tabBOM Other Detail` AS od ON bom.name = od.parent
        LEFT JOIN `tabItem Default` AS idf ON item.item_name = idf.parent

        WHERE {where_clause}
        GROUP BY item.item_code, item.variant_of
        ORDER BY item.creation DESC

    """, values, as_dict=True)

    # -------- MULTISELECT ATTRIBUTES --------
    item_codes = [row.item_code for row in db_data]

    if item_codes:
        db_res = frappe.db.sql("""
            SELECT parent, parentfield,
            GROUP_CONCAT(design_attribute ORDER BY design_attribute SEPARATOR ', ') AS design_attributes
            FROM `tabDesign Attribute - Multiselect`
            WHERE parent IN %(data)s
            GROUP BY parent, parentfield
        """, {"data": tuple(item_codes)}, as_dict=True)
    else:
        db_res = []

    attr_map = {}
    for row in db_res:
        parent = row["parent"]
        field = row["parentfield"].replace("custom_", "")
        value = row["design_attributes"]
        if parent not in attr_map:
            attr_map[parent] = {}
        attr_map[parent][field] = value

    for row in db_data:
        attrs = attr_map.get(row.item_code, {})
        for key, value in attrs.items():
            row[key] = value

        row["custom_collection"] = row.get("custom_collection") or None
        row["custom_language"] = row.get("custom_language") or None
        row["custom_zodiac"] = row.get("custom_zodiac") or None
        row["custom_animalbirds"] = row.get("custom_animalbirds") or None
        row["custom_alphabetnumber"] = row.get("custom_alphabetnumber") or None
        row["religious"] = row.get("religious") or None

    # -------- SIMILAR ITEMS TABLE --------
    if item_codes:
        similar_links = frappe.db.sql("""
            SELECT sit.parent AS main_item_code, sit.item_code AS similar_item_code
            FROM `tabSimilar Item Table` AS sit
            WHERE sit.parenttype = 'Item'
            AND sit.parent IN %(item_codes)s
        """, {"item_codes": tuple(item_codes)}, as_dict=True)
    else:
        similar_links = []

    all_similar_codes = list({lnk["similar_item_code"] for lnk in similar_links})

    if all_similar_codes:
        sim_rows = frappe.db.sql("""
            SELECT
                item.name,
                bom.name AS bom_name,
                idf.company,
                tci.trending,
                0 AS wishlist,
                item.creation,
                item.item_code,
                item.item_category,
                item.image,
                item.sketch_image,
                item.front_view AS cad_image,
                CASE WHEN item.front_view = item.image THEN 'CAD Image' ELSE 'FG Image' END AS image_remark,
                item.item_subcategory,
                item.stylebio,
                bom.tag_no,
                bom.diamond_quality,
                item.setting_type,
                FORMAT(bom.gross_weight,3) AS gross_metal_weight,
                FORMAT(bom.metal_and_finding_weight,3) AS net_metal_finding_weight,
                FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
                FORMAT(bom.other_weight,3) AS other_weight,
                FORMAT(bom.finding_weight_,3) AS finding_weight_,
                bom.metal_colour,
                bom.metal_touch,
                bom.metal_purity,
                FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,
                bom.total_diamond_pcs,
                bom.total_gemstone_pcs,
                FORMAT(bom.gemstone_weight,3) AS gemstone_weight,
                FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
                FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
                FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,
                bom.navratna, bom.lock_type, bom.feature, bom.enamal, bom.rhodium, bom.sizer_type,
                bom.height, bom.length, bom.width, bom.breadth, bom.product_size,
                bom.design_style, bom.nakshi_from, bom.vanki_type, bom.total_length,
                bom.detachable, bom.back_side_size, bom.changeable,
                item.variant_of,
                bom.finding_pcs, bom.total_other_pcs, bom.total_other_weight,
                GROUP_CONCAT(DISTINCT item.name ORDER BY item.creation ASC) AS variant_name,
                GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
                GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,
                GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
                GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
                GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
                GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,
                GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
                GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,
                GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
                GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
                GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
                GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
                GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,
                GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
                GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
                GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size
            FROM `tabItem` AS item
            LEFT JOIN `tabBOM` AS bom ON item.item_code = bom.item
            LEFT JOIN `tabCataloge Item Details` AS tci ON tci.item_code = item.name
            LEFT JOIN `tabDesign Attributes` AS td ON item.item_code = td.parent
            LEFT JOIN `tabBOM Metal Detail` AS mt ON bom.name = mt.parent
            LEFT JOIN `tabBOM Gemstone Detail` AS gd ON bom.name = gd.parent
            LEFT JOIN `tabBOM Diamond Detail` AS dd ON bom.name = dd.parent
            LEFT JOIN `tabBOM Finding Detail` AS fd ON bom.name = fd.parent
            LEFT JOIN `tabBOM Other Detail` AS od ON bom.name = od.parent
            LEFT JOIN `tabItem Default` AS idf ON item.item_name = idf.parent
            WHERE item.item_code IN %(similar_codes)s
            GROUP BY item.item_code, item.variant_of
        """, {"similar_codes": tuple(all_similar_codes)}, as_dict=True)

        # Apply multiselect attributes to similar items
        sim_item_codes = [r.item_code for r in sim_rows]
        if sim_item_codes:
            sim_attr_res = frappe.db.sql("""
                SELECT parent, parentfield,
                GROUP_CONCAT(design_attribute ORDER BY design_attribute SEPARATOR ', ') AS design_attributes
                FROM `tabDesign Attribute - Multiselect`
                WHERE parent IN %(data)s
                GROUP BY parent, parentfield
            """, {"data": tuple(sim_item_codes)}, as_dict=True)
            sim_attr_map = {}
            for r in sim_attr_res:
                sim_attr_map.setdefault(r["parent"], {})[r["parentfield"].replace("custom_", "")] = r["design_attributes"]
            for r in sim_rows:
                for k, v in sim_attr_map.get(r.item_code, {}).items():
                    r[k] = v
                r["custom_collection"] = r.get("custom_collection") or None
                r["custom_language"] = r.get("custom_language") or None
                r["custom_zodiac"] = r.get("custom_zodiac") or None
                r["custom_animalbirds"] = r.get("custom_animalbirds") or None
                r["custom_alphabetnumber"] = r.get("custom_alphabetnumber") or None
                r["religious"] = r.get("religious") or None

        # ✅ FIXED - similar items nested karo, flat extend nahi
        existing_item_codes = {row.item_code for row in db_data}

        # sim_code -> full sim row map
        sim_row_map = {r["item_code"]: r for r in sim_rows}

        # main item ke saath similar items attach karo
        sim_map = {}
        for lnk in similar_links:
            main = lnk["main_item_code"]
            sim_code = lnk["similar_item_code"]
            if sim_code not in existing_item_codes and sim_code in sim_row_map:
                sim_map.setdefault(main, []).append(sim_row_map[sim_code])

        for row in db_data:
            row["similar_items"] = sim_map.get(row.item_code, [])

    else:
        # similar items koi nahi toh empty list
        for row in db_data:
            row["similar_items"] = []

    return db_data