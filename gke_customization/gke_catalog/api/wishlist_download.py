import frappe


# @frappe.whitelist()
# def download_bom_pdf(items):
    # items - bom / customer
    # import json
    # from frappe.utils.pdf import get_pdf

    # if isinstance(items, str):
    #     items = json.loads(items)

    # all_rows_html = ""
    # first_doc = None
    # first_customer_na = ""
    # first_gstin = ""
    # first_company_add1 = ""
    # row_number = 1

    # for item_code in items:
    #     bom_name = frappe.db.get_value("BOM", {"item": item_code}, "name")
    #     if not bom_name:
    #         continue

    #     doc = frappe.get_doc("BOM", bom_name)

    #     if not first_doc:
    #         first_doc = doc

    #     # Customer
    #     customer = frappe.db.get_value('Customer', doc.customer, 'name')
    #     customer_na = frappe.db.get_value('Customer', doc.customer, 'customer_name') or ''
    #     customer_link = frappe.db.get_value('Dynamic Link', {
    #         'parenttype': 'Address', 'link_doctype': 'Customer', 'link_name': customer
    #     }, 'parent')
    #     gst = frappe.db.get_value('Address', customer_link, 'gstin') or ''

    #     # Company Address
    #     company = doc.company
    #     addresses = frappe.db.get_all('Dynamic Link', {
    #         'parenttype': 'Address', 'link_doctype': 'Company', 'link_name': company
    #     }, ['parent'])
    #     company_address_name = ''
    #     for addr in addresses:
    #         if frappe.db.get_value('Address', addr.parent, 'city') == 'Chennai':
    #             company_address_name = addr.parent
    #             break
    #     company_add1 = frappe.db.get_value('Address', company_address_name, 'address_line1') or ''
    #     gstin = frappe.db.get_value('Address', company_address_name, 'gstin') or ''

    #     if row_number == 1:
    #         first_customer_na = customer_na
    #         first_gstin = gstin
    #         first_company_add1 = company_add1

    #     # Metal
    #     metal_amt = making_amt = metal_rate = wastage_amount = 0
    #     for g in frappe.get_all('BOM Metal Detail', filters={'parent': doc.name},
    #             fields=['rate', 'wastage_amount', 'making_rate', 'amount', 'making_amount']):
    #         metal_amt   += g.amount or 0
    #         making_amt  += g.making_amount or 0
    #         metal_rate   = g.rate or 0
    #         wastage_amount = g.wastage_amount or 0

    #     # Findings
    #     chain = chain_w = chain_making = chain_amt = 0
    #     find_making_amt = find_making = find_wastage = 0
    #     for f in frappe.get_all('BOM Finding Detail', filters={'parent': doc.name},
    #             fields=['wastage_amount', 'making_amount', 'amount', 'making_rate', 'quantity', 'finding_category']):
    #         if f.finding_category == "Chains":
    #             chain        = f.quantity or 0
    #             chain_w     += f.wastage_amount or 0
    #             chain_making += f.making_amount or 0
    #             chain_amt   += f.amount or 0
    #         else:
    #             find_making_amt += f.amount or 0
    #             find_making     += f.making_amount or 0
    #             find_wastage    += f.wastage_amount or 0

    #     metal_amount = metal_amt + find_making_amt
    #     metal_making = making_amt + find_making
    #     meta_wastage = wastage_amount + find_wastage

    #     # Diamonds grouped
    #     grouped = {}
    #     for d in frappe.db.get_all('BOM Diamond Detail', {'parent': doc.name},
    #             ['weight_in_gms', 'pcs', 'quantity', 'total_diamond_rate', 'stone_shape']):
    #         key = '%.2f' % (d.total_diamond_rate or 0)
    #         if key in grouped:
    #             grouped[key]['pcs']           += d.pcs or 0
    #             grouped[key]['quantity']      += d.quantity or 0
    #             grouped[key]['weight_in_gms'] += d.weight_in_gms or 0
    #         else:
    #             grouped[key] = {
    #                 'pcs': d.pcs or 0,
    #                 'quantity': d.quantity or 0,
    #                 'weight_in_gms': d.weight_in_gms or 0,
    #                 'stone_shape': d.stone_shape,
    #                 'rate': d.total_diamond_rate or 0
    #             }

    #     diamond_details = list(grouped.values())
    #     max_rows = len(diamond_details) if diamond_details else 1

    #     for i in range(max_rows):
    #         diamond     = diamond_details[i] if i < len(diamond_details) else None
    #         rounded_qty = round(diamond['quantity'], 2) if diamond else 0
    #         diamond_amo = round((diamond['rate'] * rounded_qty), 2) if diamond else 0

    #         bg = '#ffffff' if row_number % 2 == 0 else '#fafafa'

    #         if i == 0:
    #             row_total = round(
    #                 metal_amount + diamond_amo + chain_making + chain_w +
    #                 metal_making + meta_wastage +
    #                 (doc.total_gemstone_amount or 0) +
    #                 (doc.certification_amount or 0) +
    #                 (doc.hallmarking_amount or 0) + chain_amt, 2)
    #         else:
    #             row_total = diamond_amo

    #         def c(val, show=True):
    #             """Format cell - empty string if not show"""
    #             if not show:
    #                 return ''
    #             if isinstance(val, float):
    #                 return '%.2f' % val
    #             return str(val) if val else '0'

    #         def money(val):
    #             if not val:
    #                 return '0.00'
    #             return '{:,.2f}'.format(float(val))

    #         all_rows_html += f"""
    #         <tr style='background:{bg}; text-align:center;'>
    #             <td>{row_number if i == 0 else ''}</td>
    #             <td>{c(doc.item, i==0)}</td>
    #             <td>{c(doc.item_category, i==0)}</td>
    #             <td>{c(doc.diamond_quality, i==0)}</td>
    #             <td>{c(diamond['pcs']) if diamond else ''}</td>
    #             <td>{'%.2f' % rounded_qty if diamond else ''}</td>
    #             <td>{money(diamond['rate']) if diamond else ''}</td>
    #             <td>{money(diamond_amo) if diamond else ''}</td>
    #             <td>{c(doc.gross_weight, i==0)}</td>
    #             <td>{c(doc.gemstone_weight, i==0)}</td>
    #             <td>{c(doc.other_weight, i==0)}</td>
    #             <td>{c(doc.metal_and_finding_weight, i==0)}</td>
    #             <td>{money(metal_amount) if i==0 else ''}</td>
    #             <td>{c(doc.metal_purity, i==0)}</td>
    #             <td>{c(chain, i==0)}</td>
    #             <td>{money(chain_amt) if i==0 else ''}</td>
    #             <td>{c(doc.metal_purity, i==0)}</td>
    #             <td>{money(chain_making) if i==0 else ''}</td>
    #             <td>{money(chain_w) if i==0 else ''}</td>
    #             <td>{money(metal_making) if i==0 else ''}</td>
    #             <td>{money(meta_wastage) if i==0 else ''}</td>
    #             <td>{money(doc.total_gemstone_amount) if i==0 else ''}</td>
    #             <td>{money(doc.certification_amount) if i==0 else ''}</td>
    #             <td>{money(doc.hallmarking_amount) if i==0 else ''}</td>
    #             <td style='font-weight:bold'>{money(row_total)}</td>
    #         </tr>
    #         """

    #     row_number += 1

    # # date_str = frappe.utils.formatdate(first_doc.transaction_date, 'dd-mm-yyyy') if first_doc else ''

    # final_html = f"""
    # <!DOCTYPE html>
    # <html>
    # <head>
    #     <meta name="pdfkit-orientation" content="Landscape"/>
    #     <style>
    #         * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    #         body {{ font-family: Arial, sans-serif; font-size: 8px; padding: 10px; }}

    #         h3 {{ text-align: center; font-size: 14px; margin-bottom: 4px; }}
    #         h6 {{ text-align: center; font-size: 9px; margin-bottom: 2px; font-weight: normal; }}
    #         h5 {{ text-align: center; font-size: 11px; margin-bottom: 10px; text-decoration: underline; }}

    #         .info-block {{ margin-bottom: 6px; }}
    #         .info-block p {{ margin: 2px 0; font-size: 9px; font-weight: bold; }}
    #         .date-ref {{ text-align: right; font-size: 9px; font-weight: bold; margin-bottom: 8px; }}

    #         table {{
    #             width: 100%;
    #             border-collapse: collapse;
    #             table-layout: fixed;
    #         }}

    #         /* Header */
    #         thead tr {{
    #             background: #2c3e50;
    #             color: white;
    #         }}
    #         thead td {{
    #             padding: 5px 3px;
    #             text-align: center;
    #             font-size: 7.5px;
    #             font-weight: bold;
    #             border: 1px solid #1a252f;
    #             word-wrap: break-word;
    #             line-height: 1.3;
    #         }}

    #         /* Body rows */
    #         tbody tr {{
    #             border-bottom: 1px solid #ddd;
    #         }}
    #         tbody td {{
    #             padding: 4px 3px;
    #             border: 1px solid #ddd;
    #             text-align: center;
    #             font-size: 7.5px;
    #             word-wrap: break-word;
    #             vertical-align: middle;
    #         }}
    #         tbody tr:hover {{ background: #eaf4fb !important; }}

    #         /* Last column highlight */
    #         tbody td:last-child {{
    #             background: #fffde7;
    #             font-weight: bold;
    #             color: #c0392b;
    #         }}

    #         /* Column widths */
    #         col.no    {{ width: 2.5%; }}
    #         col.code  {{ width: 3.5%; }}
    #         col.name  {{ width: 6%; }}
    #         col.qwa   {{ width: 4%; }}
    #         col.std   {{ width: 3.5%; }}
    #         col.total {{ width: 5%; }}
    #     </style>
    # </head>
    # <body>
    #     <h3>{first_doc.company if first_doc else ''}</h3>
    #     <h6>{first_company_add1} &nbsp;&nbsp; GST NO: {first_gstin}</h6>
    #     <h5>DETAILS FOR STUDDED DIAMOND JEWELLERY</h5>

    #     <div style='display:flex; justify-content:space-between; margin-bottom:8px;'>
    #         <p style='font-size:9px; font-weight:bold;'>To: {first_customer_na}</p>
    #         <div style='text-align:right; font-size:9px; font-weight:bold;'>
              
    #             <p>REF.INV.No: ___________</p>
    #         </div>
    #     </div>

    #     <table>
    #         <colgroup>
    #             <col class='no'><col class='code'><col class='name'><col class='qwa'>
    #             <col class='std'><col class='std'><col class='std'><col class='std'>
    #             <col class='std'><col class='std'><col class='std'><col class='std'>
    #             <col class='std'><col class='std'><col class='std'><col class='std'>
    #             <col class='std'><col class='std'><col class='std'><col class='std'>
    #             <col class='std'><col class='std'><col class='std'><col class='std'>
    #             <col class='total'>
    #         </colgroup>
    #         <thead>
    #             <tr>
    #                 <td>NO</td>
    #                 <td>Code</td>
    #                 <td>Item Name</td>
    #                 <td>Qwa</td>
    #                 <td>Dia Pcs</td>
    #                 <td>Dia Wt</td>
    #                 <td>Dia Rate</td>
    #                 <td>Dia Amt</td>
    #                 <td>Gr.Wt</td>
    #                 <td>St.Wt</td>
    #                 <td>Oth.Wt</td>
    #                 <td>Nt.Wt</td>
    #                 <td>Gold Amt</td>
    #                 <td>Purity</td>
    #                 <td>Ch.Wt</td>
    #                 <td>Ch.Amt</td>
    #                 <td>Touch</td>
    #                 <td>Ch.M/c</td>
    #                 <td>Chain Wastage</td>
    #                 <td>Jwl M/c</td>
    #                 <td>Jwl Wastage</td>
    #                 <td>St.Amt</td>
    #                 <td>Cert</td>
    #                 <td>HM</td>
    #                 <td>Total Amt</td>
    #             </tr>
    #         </thead>
    #         <tbody>
    #             {all_rows_html}
    #         </tbody>
    #     </table>
    # </body>
    # </html>
    # """

    # pdf = get_pdf(final_html)
    # frappe.local.response.filename = "BOMs.pdf"
    # frappe.local.response.filecontent = pdf
    # frappe.local.response.type = "download"


import json
import frappe
from frappe.utils.pdf import get_pdf
import requests

import json
import os

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

@frappe.whitelist()
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
    
    
    
# @frappe.whitelist()
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




@frappe.whitelist()

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
    
    
    
@frappe.whitelist()
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
    
   
   
 
# import pikepdf
# import io

# import frappe
# import io
# import pikepdf

# from frappe.utils.pdf import get_pdf

# @frappe.whitelist()
# def add_password_to_pdf(doctype, name, print_format, receiver):

#     # Generate PDF from Print Format
#     pdf_data = get_pdf(
#         frappe.get_print(
#             doctype,
#             name,
#             print_format=print_format
#         )
#     )


#     # Dynamic password = receiver mail ke first 5 letters
#     password = receiver.split("@")[0][:5]


#     # Encrypt PDF
#     pdf = pikepdf.open(io.BytesIO(pdf_data))

#     output = io.BytesIO()

#     pdf.save(
#         output,
#         encryption=pikepdf.Encryption(
#             user=password,
#             owner=password,
#             allow=pikepdf.Permissions(
#                 extract=False,
#                 modify_annotation=False,
#                 modify_form=False
#             )
#         )
#     )


#     encrypted_pdf = output.getvalue()


#     # Send Mail
#     frappe.sendmail(
#         recipients=[receiver],
#         sender="customer_portal@gkexport.com",
#         subject="Protected PDF",
#         message=f"""
#         Dear User,

#         PDF attached.

#         Password: {password}
#         """,
#         attachments=[
#             {
#                 "fname": f"{name}.pdf",
#                 "fcontent": encrypted_pdf
#             }
#         ]
#     )
