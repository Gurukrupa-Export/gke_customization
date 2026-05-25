import frappe
from frappe import _
from frappe.utils import flt
from gke_customization.gke_catalog.api.login import set_gold_value
from frappe.utils import getdate, add_days, nowdate, cint

@frappe.whitelist()
def get_item_price(customer=None,item_code=None, bom=None, diamond_quality=None,metal_touch=None,gold_rate_value=0,
        is_cust_diam=0,is_cust_stone=0 , is_cust_gold=0, cust_gold_wt=0):
    
    dia_quality_summary = {}
    dia_price_data = get_dia_price_list(customer, item_code, bom, diamond_quality, int(is_cust_diam))
    dia_total_cts = dia_total_gms = dia_total_amount = 0
    
    gem_summary = {}
    gem_price_data = get_gem_price_list(customer, item_code, bom)
    gem_total_cts = gem_total_gms = gem_total_amount = 0
    
    making_summary = {}
    making_price_data = get_making_charges(customer, item_code, float(gold_rate_value), bom, metal_touch, int(is_cust_gold), float(cust_gold_wt))
    
    finding_summary = {}
    finding_price_data = get_finding_charges(customer, item_code, float(gold_rate_value), bom, metal_touch)

    for row in dia_price_data:
        quality = row["diamond_quality"]

        if quality not in dia_quality_summary:
            dia_quality_summary[quality] = {
                "total_weight_in_cts": 0,
                "total_weight_in_gms": 0,
                "total_diamond_amount": 0,
                "total_base_rate": 0,
            }

        dia_quality_summary[quality]["total_weight_in_cts"] += row.get("total_weight_in_cts", 0)
        dia_quality_summary[quality]["total_weight_in_gms"] += row.get("total_weight_in_gms", 0)
        dia_quality_summary[quality]["total_diamond_amount"] += row.get("diamond_rate_for_specified_quantity", 0)
        dia_quality_summary[quality]["total_base_rate"] += row.get("base_rate", 0)

        dia_total_cts += row["total_weight_in_cts"]
        dia_total_gms += row["total_weight_in_gms"]
        dia_total_amount += row["diamond_rate_for_specified_quantity"]

    for gem_row in gem_price_data:
        gem_total_gms += gem_row.get("total_weight_in_gms", 0)
        gem_total_cts += gem_row.get("total_weight_in_cts", 0)
        gem_total_amount += gem_row.get("gemstone_rate_for_specified_quantity", 0) 
    
    gem_summary = { 
        "total_weight_in_cts": round(gem_total_cts, 3),
        "total_weight_in_gms": round(gem_total_gms, 3),
        "total_gemstone_amount": round(gem_total_amount, 2)
    }
    
    for met in making_price_data:
        metal_touch = met["metal_touch"]
        if metal_touch not in making_summary:
            making_summary[metal_touch] = {
                "setting_type": met["setting_type"],
                "gross_wt": 0,
                "gold_amount": 0,
                "making_charge": 0,
                "gold_rate": met["gold_rate"]
            }
        
        # making_summary[metal_touch]["gross_wt"] += met.get("gms", 0)
        making_summary[metal_touch]["gross_wt"] += met.get("gms", 0)
        making_summary[metal_touch]["gold_amount"] += met.get("gold_amount", 0)
        making_summary[metal_touch]["making_charge"] += met.get("making_amount", 0)
    
    for met in finding_price_data:
        metal_touch = met["metal_touch"]
        if metal_touch not in finding_summary:
            finding_summary[metal_touch] = {
                "setting_type": met["setting_type"],
                "gross_wt": 0,
                "finding_amount": 0,
                "finding_making_charge": 0
            }
        
        finding_summary[metal_touch]["gross_wt"] += met.get("gms", 0)
        finding_summary[metal_touch]["finding_amount"] += met.get("finding_amount", 0)
        finding_summary[metal_touch]["finding_making_charge"] += met.get("finding_making_amount", 0)
    
    
    # return dia_price_data
    return {
        "dia_quality_summary": dia_quality_summary,
        "dia_overall_summary": {
            "total_cts": round(dia_total_cts, 3),
            "total_gms": round(dia_total_gms, 3),
            "total_amount": round(dia_total_amount, 2)
        },
        "gem_summary": gem_summary,
        "metal_price_data": making_summary,
        "finding_price_data": finding_summary
    }

def get_dia_price_list(customer,item_code, bom, diamond_quality, is_cust):
    bom_dia_details = frappe.db.get_all(
        'BOM Diamond Detail',
        filters={'parent': bom},
        fields=['*']
    )

    a = []
    dia_price_data = []
    for d in bom_dia_details:
        dia_quality = ''
        if diamond_quality:
            dia_quality = diamond_quality
        else:
            dia_quality = d.quality
            
        customer_diamond_list = frappe.db.get_value(
            'Diamond Price List Table',
            {'parent': customer, 'diamond_shape': d.stone_shape},
            'diamond_price_list', as_dict=True
        )
        
        if not customer_diamond_list:
            continue
        
        price_list_type = customer_diamond_list["diamond_price_list"]    
        
        # Prepare common filters for Diamond Price List query
        common_filters = {
            "price_list": "Standard Selling",
            "price_list_type": price_list_type,
            "customer": customer,
            "diamond_type": d.diamond_type,
            "stone_shape": d.stone_shape,
            # "diamond_quality": d.quality
            "diamond_quality": dia_quality
        }
        
        if price_list_type == 'Sieve Size Range':
            sieve_filter = {**common_filters, "sieve_size_range": d.sieve_size_range}
            latest = frappe.db.get_value("Diamond Price List", sieve_filter,
                                        ["rate",'name','price_list_type',
                                        "outright_handling_charges_rate",
                                        "outright_handling_charges_in_percentage",
                                        "outwork_handling_charges_rate",
                                        "outwork_handling_charges_in_percentage"], as_dict=True)
        elif price_list_type == 'Weight (in cts)':
            common_conditions = " AND ".join([f"{k} = %s" for k in common_filters.keys()])
            
            rate_result =  frappe.db.sql(
                            f"""
                                SELECT 
                                    rate,name,price_list_type,
                                    outright_handling_charges_rate,
                                    outright_handling_charges_in_percentage,
                                    outwork_handling_charges_rate,
                                    outwork_handling_charges_in_percentage
                                FROM `tabDiamond Price List`
                                WHERE {common_conditions}
                                AND %s BETWEEN from_weight AND to_weight
                                LIMIT 1
                            """,
                            list(common_filters.values()) + [d.quantity],
                            as_dict=True
                        )
            latest = rate_result[0] if rate_result else None
            
        elif price_list_type == 'Size (in mm)':
            
            latest = frappe.db.get_value("Diamond Price List", {**common_filters, "diamond_size_in_mm": d.diamond_sieve_size},
                                        ["rate",'name','price_list_type',
                                        "outright_handling_charges_rate",
                                        "outright_handling_charges_in_percentage",
                                        "outwork_handling_charges_rate",
                                        "outwork_handling_charges_in_percentage"], as_dict=True)
        else:
            latest = None
            
        # frappe.throw(f"hii{latest}")
        if latest:
            base_rate = latest.get("rate", 0)
            out_rate = latest.get("outright_handling_charges_rate", 0)
            out_pct = latest.get("outright_handling_charges_in_percentage", 0)
            work_rate = latest.get("outwork_handling_charges_rate", 0)
            work_pct = latest.get("outwork_handling_charges_in_percentage", 0)
            
            # customer raw material
            # is_cust = 0
            
            handling_rate = 0
            total_rate = 0
            if is_cust:
                if work_rate:
                    total_rate = work_rate
                else:
                    total_rate = base_rate * (work_pct / 100)
            else:
                if out_rate:
                    handling_rate = out_rate
                elif out_pct:
                    handling_rate = base_rate + (base_rate * (out_pct / 100))
                else:
                    handling_rate = 0
                    
            handling_rate = handling_rate if not is_cust else total_rate
            
            total_diamond_rate = round(base_rate, 2)
            diamond_rate_for_specified_quantity = round(d.quantity * (total_diamond_rate + handling_rate),2 )
            
            # dummy data for now, need to change once we finalize the data to be sent in response
            a.append({
                "diamond_type": d.diamond_type,
                "stone_shape": d.stone_shape,
                "diamond_quality": dia_quality,
                # "diamond_quality": d.quality,
                "wgt_in_gms": d.weight_in_gms,
                "wgt_in_cts": d.quantity,
                "base_rate": base_rate,
                "handling_rate": handling_rate,
                "total_rate_per_carat": total_diamond_rate,
                "diamond_rate_for_specified_quantity": diamond_rate_for_specified_quantity
            })
            
            dia_price_data.append({
                "diamond_quality": dia_quality,
                "total_weight_in_gms": flt(d.quantity/5),
                "total_weight_in_cts": d.quantity,
                "base_rate": base_rate,
                "diamond_rate_for_specified_quantity": diamond_rate_for_specified_quantity
            })
    
    return  dia_price_data


def get_gem_price_list(customer,item_code, bom):
    bom_gem_details = frappe.db.get_all(
        'BOM Gemstone Detail',
        filters={'parent': bom},
        fields=['*']
    )

    a = []
    gem_price_data = []
    for gem in bom_gem_details:
        gemstone_price_list_customer = frappe.db.get_value("Customer",customer,"custom_gemstone_price_list_type")
        
        if not gemstone_price_list_customer:
            continue
        
        # Prepare common filters for Gemstone Price List query
        if gemstone_price_list_customer == "Fixed":
            gpc = frappe.get_all(
                "Gemstone Price List",
                filters={
                    "customer": customer,
                    "price_list_type": gemstone_price_list_customer,
                    "per_pc_or_per_carat": gem.get("per_pc_or_per_carat"),
                    "cut_or_cab": gem.get("cut_or_cab"),
                    "gemstone_type": gem.get("gemstone_type"),
                    "stone_shape": gem.get("stone_shape")
                },
                fields=["name", "price_list_type", "rate", "handling_rate","outwork_handling_charges_rate"],
            )
        
            if gpc:
                gpc_doc = frappe.get_doc("Gemstone Price List", gpc[0].name)
                rate = gpc_doc.rate if gpc_doc else 0
                        
                total_gemstone_rate = round(rate, 2)
                gemstone_rate_for_specified_quantity = (
                    float(rate) * float(gem.quantity)) if gem.per_pc_or_per_carat=='Per Carat' else (float(rate) * float(gem.pcs))
                gemstone_rate_amt =round(gemstone_rate_for_specified_quantity , 2) 
                
                # dummy data for now, need to change once we finalize the data to be sent in response
                a.append({
                    "gemstone_type": gem.gemstone_type,
                    "stone_shape": gem.stone_shape,
                    "gemstone_grade": gem.gemstone_grade,
                    "wgt_in_gms": gem.weight_in_gms,
                    "wgt_in_cts": gem.quantity,
                    "per_pc_or_per_carat": gem.per_pc_or_per_carat, 
                    "total_gemstone_rate": total_gemstone_rate,
                    "gemstone_rate_for_specified_quantity": gemstone_rate_amt
                })
                
                gem_price_data.append({
                    # "diamond_quality": gem.quality,
                    "gemstone_grade": gem.gemstone_grade,
                    "total_weight_in_gms": flt(gem.quantity/5),
                    "total_weight_in_cts": gem.quantity,
                    "total_gemstone_rate": total_gemstone_rate,
                    "gemstone_rate_for_specified_quantity": gemstone_rate_amt
                })
            else:
                gpc = None
    
    return  gem_price_data


def get_making_charges(customer, item_code,gold_rate_value, bom,metal_touch, is_cust, cust_gold_wt):
    gold_rate_value = gold_rate_value or set_gold_value()
    gold_rate = gold_rate_value / 10
    
    gold_gst_rate=frappe.db.get_single_value("Jewellery Settings", "gold_gst_rate")
    bom_values = frappe.db.get_value("BOM", bom, ["metal_and_finding_weight","metal_type","setting_type","total_diamond_pcs","item_subcategory"])
    metal_and_finding_weight = bom_values[0]
    metal_type = bom_values[1]
    setting_type = bom_values[2]
    diamond_pcs = bom_values[3]
    item_subcategory = bom_values[4]
    # metal_precision = frappe.db.get_value("Customer", customer, "custom_precision_for_metal")
    # if metal_precision is None:
    metal_precision = 3
				
    bom_metal_details = frappe.db.get_all(
        'BOM Metal Detail',
        filters={'parent': bom},
        fields=['*']
    )
    
    metal_price_data = []
    
    for s in bom_metal_details:
        touch = ''
        if metal_touch:
            touch = metal_touch
        else:
            touch = s.metal_touch
        filters={
            "customer": customer,
            "metal_type": s.metal_type,
            "setting_type": setting_type,
            "from_gold_rate": ["<=", gold_rate],
            "to_gold_rate": [">=", gold_rate],
            "metal_touch": touch
        }
        mc = frappe.get_all(
            "Making Charge Price",
            filters=filters,
            fields=["name"],
            limit=1
        )
        
        mc_name = mc[0]["name"] if mc else None
        # frappe.throw(f"mc name {mc_name} {item_subcategory}")
        
        sub = frappe.db.get_all(
            "Making Charge Price Item Subcategory",
            filters={"parent": mc_name, "subcategory": item_subcategory},
            fields=[
                "rate_per_gm",
                "rate_per_pc",
                "wastage",
                "rate_per_gm_threshold",
                "custom_subcontracting_rate",
                "to_diamond","from_diamond"
            ]
        )
        
        sub_info = sub[0] if sub else {}
        threshold = 2 if sub_info.get("rate_per_gm_threshold") == 0 else sub_info.get("rate_per_gm_threshold")
        
        customer_metal_purity = frappe.db.sql(f"""select metal_purity from `tabMetal Criteria` 
                                              where parent = '{customer}' 
                                              and metal_type = '{s.metal_type}' 
                                              and metal_touch = '{touch}'
                                              """, as_dict=True)[0]['metal_purity']
        
        calculated_gold_rate = (float(customer_metal_purity) * gold_rate) / (100 + int(gold_gst_rate))
        if not threshold:
            continue
        if metal_and_finding_weight < threshold:
            for s_row in sub:
                if s_row.from_diamond:
                    if int(s_row.from_diamond) <= int(diamond_pcs) <= int(s_row.to_diamond):
                        sub_info = s_row
        

        if not mc:
            frappe.throw(f"""Create a valid Making Charge Price for Customer: {customer}, Metal Type:{s.metal_type} "Setting Type":{s.setting_type} """)
        mc_name = mc[0]["name"]
        
        making_rate = 0
        if metal_and_finding_weight < threshold:
            # Use per piece rate, wastage might apply differently if needed
            making_rate = sub_info.get("rate_per_pc", 0)
        else:
            # Use per gram rate along with wastage value
            making_rate = sub_info.get("rate_per_gm", 0)
                        
        base_rate=round(calculated_gold_rate , 2)
        quantity = 0
        if cust_gold_wt:
            quantity = float(cust_gold_wt)
        else:
            quantity = round(s.quantity, metal_precision)
        metal_amount = round(base_rate * quantity,2 )
        subcontracting_rate = sub_info.get("custom_subcontracting_rate", 0)
        making_rate = making_rate 
        
        if is_cust:
            base_rate=0
            metal_amount=round(base_rate * quantity,2 )
            making_rate= subcontracting_rate 
            making_amount = making_rate * quantity
        else:
            if metal_and_finding_weight < 2:
                making_amount = making_rate
            else:
                making_amount = making_rate * quantity
            
        making_amount = making_amount
        # frappe.throw(f"making_amount {making_amount}  {quantity} {making_rate} {base_rate}")
		
        metal_price_data.append({
            "metal_type": s.metal_type,
            "setting_type": setting_type,
            "metal_touch": touch,
            "gms": quantity,
            "gold_rate": base_rate,
            "gold_amount": metal_amount,
            "making_rate": making_rate,
            "making_amount": making_amount
        })
        
    return metal_price_data

def get_finding_charges(customer, item_code,gold_rate_value, bom,metal_touch):
    gold_rate_value = gold_rate_value or set_gold_value()
    gold_rate = gold_rate_value / 10
    
    gold_gst_rate=frappe.db.get_single_value("Jewellery Settings", "gold_gst_rate")
    bom_values = frappe.db.get_value("BOM", bom, ["metal_and_finding_weight","metal_type","setting_type","total_diamond_pcs","item_subcategory"])
    metal_and_finding_weight = bom_values[0]
    metal_type = bom_values[1]
    setting_type = bom_values[2]
    diamond_pcs = bom_values[3]
    item_subcategory = bom_values[4]
    # metal_precision = frappe.db.get_value("Customer", customer, "custom_precision_for_metal")
    metal_precision = 3
    
    bom_finding_details = frappe.db.get_all(
        'BOM Finding Detail',
        filters={'parent': bom},
        fields=['*']
    )
    a = []
    finding_price_data = [] 
    finding_cache = {}
    
    for f in bom_finding_details:
        touch = ''
        if metal_touch:
            touch = metal_touch
        else:
            touch = f.metal_touch
        filters={
            "customer": customer,
            "metal_type": f.metal_type,
            "setting_type": setting_type,
            "from_gold_rate": ["<=", gold_rate],
            "to_gold_rate": [">=", gold_rate],
            "metal_touch": touch
        }
        mc = frappe.get_all("Making Charge Price", filters=filters,fields=["name"], limit=1 )
        mc_name = mc[0]["name"] if mc else None
        
        sub = frappe.db.get_all(
            "Making Charge Price Item Subcategory",
            filters={"parent": mc_name, "subcategory": item_subcategory},
            fields=[
                "rate_per_gm",
                "rate_per_pc",
                "wastage"
            ],
            limit=1
        )
        sub_info = sub[0] if sub else {}
        finding_type = f.finding_type
        if finding_type not in finding_cache:
            find = frappe.db.get_all(
                "Making Charge Price Finding Subcategory",
                filters={ "parent": mc_name, "subcategory": finding_type },
                fields=[
                    "rate_per_gm", 
                    "rate_per_pc",
                    "wastage"
                ],
                limit=1
            )
            
            if find:
                find_data = find[0]
            else:
                find = frappe.db.get_all(
                    "Making Charge Price Item Subcategory",
                    filters={"parent": mc_name, "subcategory": item_subcategory},
                    fields=[
                        "subcategory",
                        "rate_per_gm",
                        "rate_per_pc",
                        "wastage",
                        "name",
                        "to_diamond",
                        "from_diamond",
                        "rate_per_gm_threshold"
                    ]
                )
                find_data= find[0] if find else {}
                threshold = 2 if find_data.get("rate_per_gm_threshold") == 0 else find_data.get("rate_per_gm_threshold")

                if not threshold:
                    continue
                if metal_and_finding_weight < threshold:
                    for sf_row in find:
                        if sf_row.from_diamond:
                            if int(sf_row.from_diamond) <= int(diamond_pcs) <= int(sf_row.to_diamond):
                                find_data = sf_row
            
            gold_gst_rate=frappe.db.get_single_value("Jewellery Settings", "gold_gst_rate")
            calculated_gold_rate = (float(f.metal_purity) * gold_rate) / (100 + int(gold_gst_rate))
            
            gold_gst_rate=frappe.db.get_single_value("Jewellery Settings", "gold_gst_rate")
            customer_metal_purity = frappe.db.sql(f"""select metal_purity from `tabMetal Criteria` 
                                                where parent = '{customer}' and metal_type = '{f.metal_type}' and 
                                                metal_touch = '{touch}' """,as_dict=True)[0]['metal_purity']
            calculated_gold_rate = (float(customer_metal_purity) * gold_rate) / (100 + int(gold_gst_rate))
             
            base_rate=round(calculated_gold_rate , 2)
            quantity=round(f.quantity, metal_precision)
            finding_amount = round(base_rate * quantity,  2)
            finding_weight = metal_and_finding_weight

            if finding_weight is not None and finding_weight < 2:
                find_making_rate = find_data.get("rate_per_pc", 0) 
                finding_making_amount = find_making_rate 
            else:
                find_making_rate = find_data.get("rate_per_gm", 0) 
                finding_making_amount = find_making_rate * quantity

            find_making_rate = find_making_rate
            finding_making_amount = finding_making_amount
    
        finding_price_data.append({
            "setting_type": setting_type,
            "metal_touch": touch,
            "gms": quantity,
            "gold_rate": base_rate,
            "finding_amount": finding_amount,
            "finding_making_rate": find_making_rate,
            "finding_making_amount": finding_making_amount
        })
    
    return finding_price_data


@frappe.whitelist()
def get_item_price_as_per_payment_terms(customer=None,item_code=None, bom=None,is_cust_diam=0, is_cust_stone=0 , is_cust_gold=0, amount=None):
    customer_payment_term_doc = frappe.get_doc("Customer Payment Terms",{"customer": customer} )
    
    e_invoice_items = []
    e_invoice = []
    current_date = getdate(nowdate())
    
    for row in customer_payment_term_doc.customer_payment_details:
        item_type = row.item_type
        payment_term = row.payment_term
        e_invoice_item = frappe.get_doc("E Invoice Item", item_type)
        delivery_date = add_days(current_date, cint(payment_term or 0))
        if delivery_date == current_date:
            continue
        
        e_invoice_items.append({
            "item_type": item_type,
            "payment_term": payment_term,
            "delivery_date": delivery_date,
            "is_for_metal": e_invoice_item.is_for_metal,
            "is_for_labour": e_invoice_item.is_for_labour,
            "is_for_diamond": e_invoice_item.is_for_diamond,
            "diamond_type": e_invoice_item.diamond_type,
            "is_for_making": e_invoice_item.is_for_making,
            "is_for_finding": e_invoice_item.is_for_finding,
            "is_for_finding_making": e_invoice_item.is_for_finding_making,
            "is_for_gemstone": e_invoice_item.is_for_gemstone,
            "metal_type": e_invoice_item.metal_type,
            "metal_purity": e_invoice_item.metal_purity,
            "uom": e_invoice_item.uom,
            "finding_category": e_invoice_item.finding_category
        })
    # frappe.throw(f"customer_payment_term_doc {e_invoice_items}")
    bom_doc = frappe.get_doc("BOM", bom)

    for metal in bom_doc.metal_detail:
        if not is_cust_gold:
            for e_item in e_invoice_items:
                if (
                    e_item["is_for_metal"] and
                    metal.metal_type == e_item["metal_type"] and
                    metal.metal_touch == e_item["metal_purity"] and
                    metal.stock_uom == e_item["uom"]
                ):
                    e_invoice.append({
                        "type": "Metal",
                        "item_type": e_item["item_type"],
                        "uom": e_item["uom"],
                        "payment_term": e_item["payment_term"],
                        "delivery_date": e_item["delivery_date"]
                    })
                    break

            # frappe.throw(f"customer_payment_term_doc {e_invoice}")
            for e_item in e_invoice_items:
                if (
                    e_item["is_for_making"] and
                    metal.metal_type == e_item["metal_type"] and
                    metal.metal_touch == e_item["metal_purity"] and
                    metal.stock_uom == e_item["uom"]
                ):
                    e_invoice.append({
                        "type": "Metal Making Charge",
                        "item_type": e_item["item_type"],
                        "uom": e_item["uom"],
                        "payment_term": e_item["payment_term"],
                        "delivery_date": e_item["delivery_date"]
                    })
                    break

    for diamond in bom_doc.diamond_detail:
        if not is_cust_diam:

            for e_item in e_invoice_items:
                if (
                    e_item["is_for_diamond"] and
                    e_item["diamond_type"] == diamond.diamond_type and
                    e_item["uom"] == diamond.stock_uom
                ):
                    e_invoice.append({
                        "type": "Diamond",
                        "item_type": e_item["item_type"],
                        "uom": e_item["uom"],
                        "payment_term": e_item["payment_term"],
                        "delivery_date": e_item["delivery_date"]
                    })
                    break

        break

    for gemstone in bom_doc.gemstone_detail:
        if not is_cust_stone:

            for e_item in e_invoice_items:
                if (
                    e_item["is_for_gemstone"] and
                    e_item["uom"] == gemstone.stock_uom
                ):
                    e_invoice.append({
                        "type": "Gemstone",
                        "item_type": e_item["item_type"],
                        "uom": e_item["uom"],
                        "payment_term": e_item["payment_term"],
                        "delivery_date": e_item["delivery_date"]
                    })
                    break

        break

    for finding in bom_doc.finding_detail:

        finding_handled = False

        for e_item in e_invoice_items:
            if (
                e_item["is_for_finding"] and 
                e_item["metal_type"] == finding.metal_type and
                e_item["metal_purity"] == finding.metal_touch and
                e_item["uom"] == finding.stock_uom and
                e_item["finding_category"] == finding.finding_category
            ):
                finding_handled = True

                e_invoice.append({
                    "type": "Finding Chain",
                    "item_type": e_item["item_type"],
                    "uom": e_item["uom"],
                    "payment_term": e_item["payment_term"],
                    "delivery_date": e_item["delivery_date"]
                })

                break

        if not finding_handled:

            for e_item in e_invoice_items:
                if (
                    e_item["is_for_metal"] and 
                    finding.metal_type == e_item["metal_type"] and
                    finding.metal_touch == e_item["metal_purity"] and
                    finding.stock_uom == e_item["uom"] and
                    e_item["finding_category"] is None
                ):
                    e_invoice.append({
                        "type": "Finding Metal",
                        "item_type": e_item["item_type"],
                        "uom": e_item["uom"],
                        "payment_term": e_item["payment_term"],
                        "delivery_date": e_item["delivery_date"]
                    })

                    break

        finding_making_handled = False

        for e_item in e_invoice_items:
            if (
                e_item["is_for_finding_making"] and 
                e_item["metal_type"] == finding.metal_type and
                e_item["metal_purity"] == finding.metal_touch and
                e_item["uom"] == finding.stock_uom and
                e_item["finding_category"] == finding.finding_category
            ):
                finding_making_handled = True

                e_invoice.append({
                    "type": "Finding Chain Making Charge",
                    "item_type": e_item["item_type"],
                    "uom": e_item["uom"],
                    "payment_term": e_item["payment_term"],
                    "delivery_date": e_item["delivery_date"]
                })

                break

        if not finding_making_handled:

            for e_item in e_invoice_items:
                if (
                    e_item["is_for_making"] and 
                    e_item["metal_type"] == finding.metal_type and
                    e_item["metal_purity"] == finding.metal_touch and
                    e_item["uom"] == finding.stock_uom
                ):
                    e_invoice.append({
                        "type": "Finding Making Charge",
                        "item_type": e_item["item_type"],
                        "uom": e_item["uom"],
                        "payment_term": e_item["payment_term"],
                        "delivery_date": e_item["delivery_date"]
                    })

                    break

    # Remove duplicate item_type
    unique_items = []
    seen_item_types = set()

    amount = float(amount) if amount is not None else 0

    for item in e_invoice:
        if item["item_type"] not in seen_item_types:
            seen_item_types.add(item["item_type"])
            unique_items.append(item)

    # Total payment term
    total_payment_term = sum(
        cint(item.get("payment_term", 0))
        for item in unique_items
    ) 

    # Append percentage and amount for each item
    for item in unique_items:

        payment_term = cint(item.get("payment_term", 0))

        percentage = (
            (payment_term / total_payment_term) * 100
            if total_payment_term else 0
        )

        item_amount = ( amount * percentage / 100 )
    
        # item["total_payment_term"] = total_payment_term
        item["percentage"] = round(percentage, 2)
        item["amount"] = round(item_amount, 2)

    return unique_items 
    