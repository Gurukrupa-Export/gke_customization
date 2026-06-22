import frappe
import requests


def before_validate(self,method):
    if self.custom_is_similar_item:
        create_group_for_similar(self)

    if self.custom_is_sufix_item == 1:
        create_group_for_sufix(self)

    if self.custom_is_set_item:
        create_group_for_set(self)

def create_group_for_similar(self):
    old_len = frappe.db.sql(f"""select count(*) from `tabSimilar Item Table` where parent = '{self.name}'""",as_dict=1)[0]['count(*)']
    
    if old_len != len(self.custom_similar_item_table):
        #item from similar item table
        lastSimilar_itemcode = self.custom_similar_item_table[-1].get('item_code')
     
        item_ref_doc = get_item_ref_doc(self,lastSimilar_itemcode, "tabSimilar Item Table", type='Similar')    

        # same similar item code as parent item code - add into exiting item code
        nameitem_ref_doc = get_nameitem_ref_doc(self,"tabSimilar Item Table", type='Similar')    
        
        #item from reference group when add item in same child table 
        same_ref_doc = get_same_ref_doc(self,"tabSimilar Item Table", type='Similar')
        
        # add item in exiting group
        if item_ref_doc: 
            for ref in item_ref_doc:
                name = ref.get("name")

                new_item_ref_doc = frappe.get_doc("Item Reference Group", {
                    "name": name,
                    "item_reference_type": "Similar"
                })       

                existing_item_codes = [d.item_code for d in new_item_ref_doc.similar_item_table]
                
                for i in self.custom_similar_item_table:
                    if i.item_code not in existing_item_codes:
                        item_similar_log = new_item_ref_doc.append("similar_item_table", {})
                        item_similar_log.item_code = i.item_code
                    elif self.name not in existing_item_codes:
                        item_similar_log = new_item_ref_doc.append("similar_item_table", {})
                        item_similar_log.item_code = self.name

                new_item_ref_doc.save()

                # if same_ref_doc:
                #     frappe.delete_doc("Item Reference Group", same_ref_doc[-1].get('name'))

        # add item in exiting main item code
        elif same_ref_doc:
            for ref in same_ref_doc:
                name = ref.get("name")

            new_item_ref_doc = frappe.get_doc("Item Reference Group", {
                "name": name,
                "item_reference_type": "Similar"
            })       

            existing_item_codes = [d.item_code for d in new_item_ref_doc.similar_item_table]
            
            for i in self.custom_similar_item_table:
                if i.item_code not in existing_item_codes:
                    item_similar_log = new_item_ref_doc.append("similar_item_table", {})
                    item_similar_log.item_code = i.item_code
                elif self.name not in existing_item_codes:
                    item_similar_log = new_item_ref_doc.append("similar_item_table", {})
                    item_similar_log.item_code = self.name

            new_item_ref_doc.save()

            # frappe.throw(f"heloo0000001 {existing_item_codes} || {name} ")
            
        elif nameitem_ref_doc:
            for ref in nameitem_ref_doc:
                name = ref.get("name")

                new_item_ref_doc = frappe.get_doc("Item Reference Group", {
                    "name": name,
                    "item_reference_type": "Similar"
                })       

                existing_item_codes = [d.item_code for d in new_item_ref_doc.similar_item_table]
                
                for i in self.custom_similar_item_table:
                    if i.item_code not in existing_item_codes:
                        item_similar_log = new_item_ref_doc.append("similar_item_table", {})
                        item_similar_log.item_code = i.item_code
                    elif self.name not in existing_item_codes:
                        item_similar_log = new_item_ref_doc.append("similar_item_table", {})
                        item_similar_log.item_code = self.name

                new_item_ref_doc.save()

                # frappe.throw(f"heloo0000002 {existing_item_codes} || {name} || {nameitem_ref_doc}")
    
        # create new group
        else:
            # frappe.throw(f"hi ")
            new_item_ref_doc = frappe.new_doc("Item Reference Group")
            new_item_ref_doc.item_code = self.name
            new_item_ref_doc.item_reference_type = 'Similar'
            for i in self.custom_similar_item_table:
                item_similar_log = new_item_ref_doc.append("similar_item_table", {})
                item_similar_log.item_code = i.item_code

            current_item_log = new_item_ref_doc.append("similar_item_table", {})
            current_item_log.item_code = self.name

            new_item_ref_doc.save()

def create_group_for_set(self):
    old_len = frappe.db.sql(f"""select count(*) from `tabSet Item Table` where parent = '{self.name}'""",as_dict=1)[0]['count(*)']
    
    if old_len != len(self.custom_set_item_table):

        #item from set item table
        lastSet_itemcode = self.custom_set_item_table[-1].get('item_code')
        item_ref_doc = get_item_ref_doc(self,lastSet_itemcode,"tabSet Item Table", type='Set')    

        # same Set item code as parent item code - add into exiting item code
        nameitem_ref_doc = get_nameitem_ref_doc(self,"tabSet Item Table", type='Set')    
        
        #item from reference group when add item in same child table 
        same_ref_doc = get_same_ref_doc(self,"tabSet Item Table", type='Set')

        # add item in exiting group
        if item_ref_doc: 
            for ref in item_ref_doc:
                name = ref.get("name")

                new_item_ref_doc = frappe.get_doc("Item Reference Group", {
                    "name": name,
                    "item_reference_type": "Set"
                })       

                existing_item_codes = [d.item_code for d in new_item_ref_doc.set_item_table]
                
                for i in self.custom_set_item_table:
                    if i.item_code not in existing_item_codes:
                        item_similar_log = new_item_ref_doc.append("set_item_table", {})
                        item_similar_log.item_code = i.item_code
                    elif self.name not in existing_item_codes:
                        item_similar_log = new_item_ref_doc.append("set_item_table", {})
                        item_similar_log.item_code = self.name

                new_item_ref_doc.save() 

                # if same_ref_doc:
                #     frappe.delete_doc("Item Reference Group", same_ref_doc[-1].get('name'))    

        # add item in exiting main item code
        elif same_ref_doc:
            for ref in same_ref_doc:
                name = ref.get("name")

            new_item_ref_doc = frappe.get_doc("Item Reference Group", {
                "name": name,
                "item_reference_type": "Set"
            })       

            existing_item_codes = [d.item_code for d in new_item_ref_doc.set_item_table]
            
            for i in self.custom_set_item_table:
                if i.item_code not in existing_item_codes:
                    item_similar_log = new_item_ref_doc.append("set_item_table", {})
                    item_similar_log.item_code = i.item_code
                elif self.name not in existing_item_codes:
                    item_similar_log = new_item_ref_doc.append("set_item_table", {})
                    item_similar_log.item_code = self.name

            new_item_ref_doc.save() 
            
        elif nameitem_ref_doc:
            for ref in nameitem_ref_doc:
                name = ref.get("name")

                new_item_ref_doc = frappe.get_doc("Item Reference Group", {
                    "name": name,
                    "item_reference_type": "Set"
                })       

                existing_item_codes = [d.item_code for d in new_item_ref_doc.set_item_table]
                
                for i in self.custom_set_item_table:
                    if i.item_code not in existing_item_codes:
                        item_similar_log = new_item_ref_doc.append("set_item_table", {})
                        item_similar_log.item_code = i.item_code
                    elif self.name not in existing_item_codes:
                        item_similar_log = new_item_ref_doc.append("set_item_table", {})
                        item_similar_log.item_code = self.name

                new_item_ref_doc.save()
    
        # create new group
        else: 
            new_item_ref_doc = frappe.new_doc("Item Reference Group")
            new_item_ref_doc.item_code = self.name
            new_item_ref_doc.item_reference_type = 'Set'
            for i in self.custom_set_item_table:
                item_similar_log = new_item_ref_doc.append("set_item_table", {})
                item_similar_log.item_code = i.item_code

            current_item_log = new_item_ref_doc.append("set_item_table", {})
            current_item_log.item_code = self.name

            new_item_ref_doc.save()

def create_group_for_sufix(self):
    old_len = frappe.db.sql(f"""select count(*) from `tabSufix Item Table` where parent = '{self.name}'""",as_dict=1)[0]['count(*)']
    if old_len != len(self.custom_sufix_item_table):
        # frappe.throw("IF Sufix")
        #item from Sufix item table
        lastSufix_itemcode = self.custom_sufix_item_table[-1].get('item_code')
        item_ref_doc = get_item_ref_doc(self, lastSufix_itemcode ,"tabSufix Item Table", type='Sufix')    

        # same Sufix item code as parent item code - add into exiting item code
        nameitem_ref_doc = get_nameitem_ref_doc(self,"tabSufix Item Table", type='Sufix')    
        
        #item from reference group when add item in same child table 
        same_ref_doc = get_same_ref_doc(self,"tabSufix Item Table", type='Sufix')
        
        # add item in exiting group
        if item_ref_doc: 
            for ref in item_ref_doc:
                name = ref.get("name")

                new_item_ref_doc = frappe.get_doc("Item Reference Group", {
                    "name": name,
                    "item_reference_type": "Sufix"
                })       

                existing_item_codes = [d.item_code for d in new_item_ref_doc.sufix_item_table]
                
                for i in self.custom_sufix_item_table:
                    if i.item_code not in existing_item_codes:
                        item_sufix_log = new_item_ref_doc.append("sufix_item_table", {})
                        item_sufix_log.item_code = i.item_code
                    elif self.name not in existing_item_codes:
                        item_sufix_log = new_item_ref_doc.append("sufix_item_table", {})
                        item_sufix_log.item_code = self.name

                new_item_ref_doc.save()
                # if same_ref_doc:
                #     frappe.delete_doc("Item Reference Group", same_ref_doc[-1].get('name'))

        # add item in exiting main item code
        elif same_ref_doc:
            for ref in same_ref_doc:
                name = ref.get("name")

            new_item_ref_doc = frappe.get_doc("Item Reference Group", {
                "name": name,
                "item_reference_type": "Sufix"
            })       

            existing_item_codes = [d.item_code for d in new_item_ref_doc.sufix_item_table]
            
            for i in self.custom_sufix_item_table:
                if i.item_code not in existing_item_codes:
                    item_sufix_log = new_item_ref_doc.append("sufix_item_table", {})
                    item_sufix_log.item_code = i.item_code
                elif self.name not in existing_item_codes:
                    item_sufix_log = new_item_ref_doc.append("sufix_item_table", {})
                    item_sufix_log.item_code = self.name

            new_item_ref_doc.save()
            
        elif nameitem_ref_doc:
            for ref in nameitem_ref_doc:
                name = ref.get("name")

                new_item_ref_doc = frappe.get_doc("Item Reference Group", {
                    "name": name,
                    "item_reference_type": "Sufix"
                })       

                existing_item_codes = [d.item_code for d in new_item_ref_doc.sufix_item_table]
                
                for i in self.custom_sufix_item_table:
                    if i.item_code not in existing_item_codes:
                        item_sufix_log = new_item_ref_doc.append("sufix_item_table", {})
                        item_sufix_log.item_code = i.item_code
                    elif self.name not in existing_item_codes:
                        item_sufix_log = new_item_ref_doc.append("sufix_item_table", {})
                        item_sufix_log.item_code = self.name

                new_item_ref_doc.save()

        # create new group
        else:
            new_item_ref_doc = frappe.new_doc("Item Reference Group")
            new_item_ref_doc.item_code = self.name
            new_item_ref_doc.item_reference_type = 'Sufix'
            for i in self.custom_sufix_item_table:
                item_sufix_log = new_item_ref_doc.append("sufix_item_table", {})
                item_sufix_log.item_code = i.item_code

            current_item_log = new_item_ref_doc.append("sufix_item_table", {})
            current_item_log.item_code = self.name

            new_item_ref_doc.save()


def get_item_ref_doc(self,last_itemCode,table_name, type):
    return frappe.db.sql(f"""
        select tsit.item_code,trg.name 
            from `tabItem Reference Group` as trg
        left join `{table_name}` as tsit 
            on tsit.parent = trg.name 
        where tsit.item_code = '{last_itemCode}' and trg.item_reference_type = '{type}'
    """, as_dict=1) 

def get_nameitem_ref_doc(self,table_name, type):
    return frappe.db.sql(f"""
        select tsit.item_code,trg.name 
            from `tabItem Reference Group` as trg
        left join `{table_name}` as tsit 
            on tsit.parent = trg.name and trg.item_code = tsit.item_code
        where tsit.item_code = '{self.name}' and trg.item_reference_type = '{type}'
    """, as_dict=1)

def get_same_ref_doc(self,table_name, type):
    return frappe.db.sql(f"""
        select DISTINCT (trg.name) ,tsit.item_code
            from `tabItem Reference Group` as trg
        left join `{table_name}` as tsit 
            on tsit.parent = trg.name and trg.item_code = tsit.item_code
        where trg.item_code = '{self.name}' and trg.item_reference_type = '{type}'
    """, as_dict=1)











def create_item_kggk(doc, method=None):
    base_url = "https://kggk-uat.m.frappe.cloud"
    # base_url = "https://gkexport-dummy-v16.m.frappe.cloud"

    headers = {
        # "Authorization": "token efffaa047a1663f:fe9e9c5b6461c5c",# from local to dummy site 
        "Authorization": "token 94efdb20934f180:7cf6b4e2bdf7217", #from dummy site to uat kggk
        "Content-Type": "application/json"
    }
    if doc.setting_type == "Close":
        item_code = doc.name

        payload = {
            "item_code": doc.name,
            "item_name": doc.item_name,
            "item_group": doc.item_group,
            "stock_uom": doc.stock_uom,
            "description": doc.description,
            # "has_variants":doc.has_variants,
            "disabled": doc.disabled,
            "is_stock_item": doc.is_stock_item,
            "gst_hsn_code": doc.gst_hsn_code,
            "include_item_in_manufacturing": doc.include_item_in_manufacturing,
            "custom_is_manufacturing_item": doc.custom_is_manufacturing_item,
            "custom_inventory_type_can_be_customer_goods": doc.custom_inventory_type_can_be_customer_goods,
            "custom_reason_for_design_code_": doc.custom_reason_for_design_code_,
            "old_tag_no": doc.old_tag_no,
            "stylebio": doc.stylebio,
            "item_category": doc.item_category,
            "item_subcategory": doc.item_subcategory,
            "setting_type": doc.setting_type,
            "sub_setting_type": doc.sub_setting_type,
            "approx_gold": doc.approx_gold,
            "approx_diamond": doc.approx_diamond,
            "custom_old_item_category": doc.custom_old_item_category,
            "designer": doc.designer,
            "product_dimension": doc.product_dimension,
            "sizer_type": doc.sizer_type,
            "product_shape": doc.product_shape,
            "productivity": doc.productivity,
            "manufacturing_type": doc.manufacturing_type,
            "variant_of": doc.variant_of,
            "attributes": [
                {
                    "attribute": row.attribute,
                    "attribute_value": row.attribute_value
                }
                for row in (doc.attributes or [])
            ],
            "asset_naming_series": doc.asset_naming_series,
            "asset_category": doc.asset_category,
            "is_grouped_asset": doc.is_grouped_asset,
            "auto_create_assets": doc.auto_create_assets
        }

        try:
            # Try update first
            response = requests.put(
                f"{base_url}/api/resource/Item/{item_code}",
                headers=headers,
                json=payload,
                timeout=15
            )

            # If item doesn't exist, create it
            if response.status_code == 404:
                response = requests.post(
                    f"{base_url}/api/resource/Item",
                    headers=headers,
                    json=payload,
                    timeout=15
                )

            # Log full response for debugging
            frappe.logger().info(
                f"Status Code: {response.status_code}\nResponse: {response.text}"
            )

            # Handle API errors
            if response.status_code >= 400:
                frappe.log_error(
                    title="KGGK API Error",
                    message=f"""
                    URL: {response.url}

                    Status Code: {response.status_code}

                    Response:
                    {response.text}

                    Payload:
                    {frappe.as_json(payload)}
                    """
                )

                frappe.throw(
                    f"API Error ({response.status_code})<br><br>{response.text}"
                )

            frappe.logger().info(
                f"Item {item_code} synced successfully."
            )

        except Exception:
            frappe.log_error(
                title="Item Sync Error",
                message=frappe.get_traceback()
            )
            raise




def create_bom_kggk(doc, method=None):
    base_url = "https://kggk-uat.m.frappe.cloud"
    # base_url = "https://gkexport-dummy-v16.m.frappe.cloud"

    headers = {
        "Authorization": "token 94efdb20934f180:7cf6b4e2bdf7217", #from dummy site to uat kggk
        # "Authorization": "token efffaa047a1663f:fe9e9c5b6461c5c",#from local to dummy site
        "Content-Type": "application/json"
    }
    if doc.setting_type == "Close" and doc.bom_type == "Template":
        bom = doc.name

        payload = {
            "item": doc.item,
            "bom_type": doc.bom_type,
            "is_default": doc.is_default,
            "is_active": doc.is_active,
            "company": doc.company,
            # "has_variants":doc.has_variants,
            "selling_price_list": doc.selling_price_list,
            "customer": doc.customer,
            "uom": doc.uom,
            "metal_detail": [
                {
                    "metal_purity": row.metal_purity,
                    "metal_type": row.metal_type,
                    "metal_touch": row.metal_touch,
                    "cad_weight": row.cad_weight,
                    "customer_metal_purity": row.customer_metal_purity,
                    "metal_colour": row.metal_colour,
                    "wastage_amount": row.wastage_amount,
                    "wastage_rate": row.wastage_rate,
                    "quantity": row.quantity,
                    "cad_to_finish_ratio": row.cad_to_finish_ratio,
                    "cad_finish_ratio": row.cad_finish_ratio,
                    "quantity_3": row.quantity_3,
                    "is_customer_item": row.is_customer_item,
                    "rate": row.rate,
                    "amount": row.amount,
                    "making_rate": row.making_rate,
                    "making_amount": row.making_amount,
                    "item_variant": row.item_variant,
                    "fg_purchase_rate": row.fg_purchase_rate,
                    "wax_weight": row.wax_weight,
                    "cam_weight": row.cam_weight,
                    "casting_weight": row.casting_weight,
                    "finish_loss_grams": row.finish_loss_grams,
                    "finish_loss_percentage": row.finish_loss_percentage,
                    "finish_product_weight": row.finish_product_weight,
                    "custom_wastage_rate": row.custom_wastage_rate,
                    "custom_rate": row.custom_rate,
                    "custom_making_rate": row.custom_making_rate,
                }
                for row in (doc.metal_detail or [])
            ],
            "finding_detail": [
               {
                "amount": row.amount,
                "customer_metal_purity": row.customer_metal_purity,
                "difference": row.difference,
                "fg_purchase_rate": row.fg_purchase_rate,
                "finding_category": row.finding_category,
                "finding_size": row.finding_size,
                "finding_type": row.finding_type,
                "ignore_work_order": row.ignore_work_order,
                "is_customer_item": row.is_customer_item,
                "is_manufacturing_item": row.is_manufacturing_item,
                "item": row.item,
                "making_amount": row.making_amount,
                "making_rate": row.making_rate,
                "metal_colour": row.metal_colour,
                "metal_purity": row.metal_purity,
                "metal_touch": row.metal_touch,
                "metal_type": row.metal_type,
                "not_finding_rate": row.not_finding_rate,
                "purity_percentage": row.purity_percentage,
                "qty": row.qty,
                "quantity": row.quantity,
                "quantity_3": row.quantity_3,
                "rate": row.rate,
                "stock_uom": row.stock_uom,
                "wastage_amount": row.wastage_amount,
                "wastage_rate": row.wastage_rate
            }
                for row in (doc.finding_detail or [])
            ],
            "diamond_detail": [
               {
                "diamond_cut": row.diamond_cut,
                "diamond_grade": row.diamond_grade,
                "diamond_rate_for_specified_quantity": row.diamond_rate_for_specified_quantity,
                "diamond_sieve_size": row.diamond_sieve_size,
                "diamond_size_in_mm": row.diamond_size_in_mm,
                "diamond_type": row.diamond_type,
                "fg_purchase_amount": row.fg_purchase_amount,
                "fg_purchase_rate": row.fg_purchase_rate,
                "handling_rate": row.handling_rate,
                "is_customer_item": row.is_customer_item,
                "item": row.item,
                "pcs": row.pcs,
                "quality": row.quality,
                "quantity": row.quantity,
                "quantity_3": row.quantity_3,
                "sieve_size_color": row.sieve_size_color,
                "sieve_size_range": row.sieve_size_range,
                "size_in_mm": row.size_in_mm,
                "size_type": row.size_type,
                "stock_uom": row.stock_uom,
                "stone_shape": row.stone_shape,
                "sub_setting_type": row.sub_setting_type,
                "total_diamond_rate": row.total_diamond_rate,
                "weight_per_pcs": row.weight_per_pcs
            }
                for row in (doc.diamond_detail or [])
            ],
            "gemstone_detail": [
              {
                "cut_or_cab": row.cut_or_cab,
                "fg_purchase_rate": row.fg_purchase_rate,
                "gemstone_code": row.gemstone_code,
                "gemstone_grade": row.gemstone_grade,
                "gemstone_pr": row.gemstone_pr,
                "gemstone_quality": row.gemstone_quality,
                "gemstone_rate_for_specified_quantity": row.gemstone_rate_for_specified_quantity,
                "gemstone_size": row.gemstone_size,
                "gemstone_type": row.gemstone_type,
                "is_customer_item": row.is_customer_item,
                "item": row.item,
                "item_category": row.item_category,
                "pcs": row.pcs,
                "per_pc_or_per_carat": row.per_pc_or_per_carat,
                "price_list_type": row.price_list_type,
                "quantity": row.quantity,
                "quantity_3": row.quantity_3,
                "size_height": row.size_height,
                "size_weight": row.size_weight,
                "stock_uom": row.stock_uom,
                "stone_shape": row.stone_shape,
                "sub_setting_type": row.sub_setting_type,
                "total_gemstone_rate": row.total_gemstone_rate
            }
                for row in (doc.gemstone_detail or [])
            ],
            "other_detail": [
             {
                "amount": row.amount,
                # "rate": row.rate,
                # "bom_no": row.bom_no,
                # "child_docname": row.child_docname,
                # "conversion_factor": row.conversion_factor,
                # "description": row.description,
                # "discount_percentage": row.discount_percentage,
                # "has_margin": row.has_margin,
                # "image": row.image,
                # "include_item_in_manufacturing": row.include_item_in_manufacturing,
                "item_code": row.item_code,
                # "item_name": row.item_name,
                # "price_list_rate": row.price_list_rate,
                # "pricing_rules": row.pricing_rules,
                "qty": row.qty,
                "quantity": row.quantity,
                "rate": row.rate,
                # "sourced_by_supplier": row.sourced_by_supplier,
                # "stock_qty": row.stock_qty,
                # "stock_uom": row.stock_uom,
                "uom": row.uom
            }
                for row in (doc.other_detail or [])
            ],
            "metal_weight": doc.metal_weight,
            "diamond_weight": doc.diamond_weight,
            "finding_weight_": doc.finding_weight_,
            "gross_weight": doc.gross_weight,
            "gemstone_weight": doc.gemstone_weight,
            "total_diamond_weight_in_gms": doc.total_diamond_weight_in_gms,
            "metal_and_finding_weight": doc.metal_and_finding_weight,
            "other_weight": doc.other_weight,
            "total_gemstone_weight_in_gms": doc.total_gemstone_weight_in_gms,
            "gold_to_diamond_ratio": doc.gold_to_diamond_ratio,
            "diamond_ratio": doc.diamond_ratio,
            "metal_to_diamond_ratio_excl_of_finding": doc.metal_to_diamond_ratio_excl_of_finding,
            "custom_rating": doc.custom_rating,
            "diamond_inclusive": doc.diamond_inclusive,
            "net_wt": doc.net_wt,
             "items": [
            {
                "allow_alternative_item": row.allow_alternative_item,
                "amount": row.amount,
                "base_amount": row.base_amount,
                "base_rate": row.base_rate,
                "bom_no": row.bom_no,
                "conversion_factor": row.conversion_factor,
                "description": row.description,
                "do_not_explode": row.do_not_explode,
                "has_variants": row.has_variants,
                "image": row.image,
                "include_item_in_manufacturing": row.include_item_in_manufacturing,
                "is_stock_item": row.is_stock_item,
                "item_code": row.item_code,
                "item_name": row.item_name,
                "qty": row.qty,
                "qty_consumed_per_unit": row.qty_consumed_per_unit,
                "rate": row.rate,
                "source_warehouse": row.source_warehouse,
                "sourced_by_supplier": row.sourced_by_supplier,
                "stock_qty": row.stock_qty,
                "stock_uom": row.stock_uom,
                "uom": row.uom
            }
                for row in (doc.items or [])
            ],
            "custom_order_form_type":doc.custom_order_form_type,
            "custom_cad_order_form_id":doc.custom_cad_order_form_id,
            "custom_order_id":doc.custom_order_id,
            "product_size":doc.product_size,
            "changeable":doc.changeable,
            "detachable":doc.detachable,
            "total_length":doc.total_length,
            "sizer_type":doc.sizer_type,
            "nakshi_from":doc.nakshi_from,
            "two_in_one":doc.two_in_one,
            "back_side_size":doc.back_side_size,
            "charm":doc.charm,
            "metal_target":doc.metal_target,
            "diamond_target":doc.diamond_target,
            "metal_purity":doc.metal_purity,
            "metal_colour":doc.metal_colour,
            "metal_touch":doc.metal_touch,
            "metal_type":doc.metal_type,
            "sub_setting_type2":doc.sub_setting_type2,
            "sub_setting_type1":doc.sub_setting_type1,
            "setting_type":doc.setting_type,
            "diamond_quality":doc.diamond_quality,
            "qty":doc.qty,
            "stone_changeable":doc.stone_changeable,
            "gemstone_quality":doc.gemstone_quality,
            "gemstone_type1":doc.gemstone_type1,
            "lock_type":doc.lock_type,
            "chain_length":doc.chain_length,
            "chain_type":doc.chain_type,
            "finding_metal_type":doc.finding_metal_type,
            "finding_category":doc.finding_category,
            "custom_finding_amount":doc.custom_finding_amount,
            "chain_weight":doc.chain_weight,
            "chain_thickness":doc.chain_thickness,
            "chain":doc.chain,
            "feature":doc.feature,
            "capganthan":doc.capganthan,
            "back_chain":doc.back_chain,
            "back_belt_length":doc.back_belt_length,
            "back_belt":doc.back_belt,
            "back_chain_size":doc.back_chain_size,
            "kadi_to_mugappu":doc.kadi_to_mugappu,
            "number_of_ant":doc.number_of_ant,
            "distance_between_kadi_to_mugappu":doc.distance_between_kadi_to_mugappu,
            "back_belt_patti":doc.back_belt_patti,
            "space_between_mugappu":doc.space_between_mugappu,
            "count_of_spiral_turns":doc.count_of_spiral_turns,
            "rhodium":doc.rhodium,
            "black_bead":doc.black_bead,
            "custom_other_item_2":doc.custom_other_item_2,
            "custom_other_item_1":doc.custom_other_item_1,
            "enamal":doc.enamal,
            "black_bead_line":doc.black_bead_line,
            "custom_other_wt_2":doc.custom_other_wt_2,
            "custom_other_wt_1":doc.custom_other_wt_1,
            "customer_voucher_no":doc.customer_voucher_no,
            "customer_chain":doc.customer_chain,
            "customer_stone":doc.customer_stone,
            "customer_diamond":doc.customer_diamond,
            # "custom_total_metal_weight2_digits":doc.custom_total_metal_weight2_digits,
            "total_metal_weight":doc.total_metal_weight,
            "total_wastage_amount":doc.total_wastage_amount,
            "total_making_amount":doc.total_making_amount,
            "total_metal_amount":doc.total_metal_amount,
            "custom_finding_weight2_digits":doc.custom_finding_weight2_digits,
            "total_finding_amount":doc.total_finding_amount,
            "total_finding_weight_per_gram":doc.total_finding_weight_per_gram,
            "finding_weight":doc.finding_weight,
            "finding_pcs":doc.finding_pcs,
            "total_diamond_amount":doc.total_diamond_amount,
            "total_diamond_pcs":doc.total_diamond_pcs,
            "total_gemstone_amount":doc.total_gemstone_amount,
            "total_gemstone_weight_per_gram":doc.total_gemstone_weight_per_gram,
            # "custom_total_gemstone_weight2_digits":doc.custom_total_gemstone_weight2_digits,
            "total_gemstone_weight":doc.total_gemstone_weight,
            "total_gemstone_pcs":doc.total_gemstone_pcs,
            "total_other_weight":doc.total_other_weight,
            "total_other_pcs":doc.total_other_pcs,
            "gemstone_bom_amount":doc.gemstone_bom_amount,
            "diamond_bom_amount":doc.diamond_bom_amount,
            "gold_bom_amount":doc.gold_bom_amount,
            "gold_rate_with_gst":doc.gold_rate_with_gst,
            "total_bom_amount":doc.total_bom_amount,
            "making_charge":doc.making_charge,
            "other_bom_amount":doc.other_bom_amount,
            "finding_bom_amount":doc.finding_bom_amount,
            "sale_amount":doc.sale_amount,
            "hallmarking_amount":doc.hallmarking_amount,
            "certification_amount":doc.certification_amount,
            "freight_amount":doc.freight_amount,
            "custom_duty_amount":doc.custom_duty_amount,
            "gemstone_fg_purchase":doc.gemstone_fg_purchase,
            "diamond_fg_purchase":doc.diamond_fg_purchase,
            "making_fg_purchase":doc.making_fg_purchase,
            "description":doc.description,
            "item_name":doc.item_name,
        }

        try:
            # Try update first
            response = requests.put(
                f"{base_url}/api/resource/BOM/{bom}",
                headers=headers,
                json=payload,
                timeout=15
            )

            # If item doesn't exist, create it
            if response.status_code == 404:
                response = requests.post(
                    f"{base_url}/api/resource/BOM",
                    headers=headers,
                    json=payload,
                    timeout=15
                )

            # Log full response for debugging
            frappe.logger().info(
                f"Status Code: {response.status_code}\nResponse: {response.text}"
            )

            # Handle API errors
            if response.status_code >= 400:
                frappe.log_error(
                    title="KGGK API Error",
                    message=f"""
                    URL: {response.url}

                    Status Code: {response.status_code}

                    Response:
                    {response.text}

                    Payload:
                    {frappe.as_json(payload)}
                    """
                )

                frappe.throw(
                    f"API Error ({response.status_code})<br><br>{response.text}"
                )

            frappe.logger().info(
                f"Item {bom} synced successfully."
            )

        except Exception:
            frappe.log_error(
                title="Item Sync Error",
                message=frappe.get_traceback()
            )
            raise
        
        



        
import frappe

@frappe.whitelist()
def get_making_charge(
    customer,
    metal_type,
    setting_type,
    gold_rate,
    metal_touch,
    subcategory
):
    filters = {
        "customer": customer,
        "metal_type": metal_type,
        "setting_type": setting_type,
        "from_gold_rate": ["<=", gold_rate],
        "to_gold_rate": [">=", gold_rate],
        "metal_touch": metal_touch,
    }

    mc = frappe.get_all(
        "Making Charge Price",
        filters=filters,
        fields=["name"],
        limit=1,
    )

    if not mc:
        return {}

    mc_name = mc[0]["name"]

    sub_rows = frappe.get_all(
        "Making Charge Price Item Subcategory",
        filters={
            "parent": mc_name,
            "subcategory": subcategory,
        },
        fields=[
            "subcategory",
            "rate_per_gm",
            "parent",
            "rate_per_pc",
            "supplier_fg_purchase_rate",
            "wastage",
            "wastage_per_pcs",
            "subcontracting_rate",
            "subcontracting_wastage",
            "rate_per_gm_threshold",
            "to_diamond",
            "from_diamond",
        ],
    )

    if not sub_rows:
        return {}

    return sub_rows[0]



@frappe.whitelist()
def get_finding_charge(
    parent,
    subcategory
):
   
    sub_rows = frappe.get_all(
        "Making Charge Price Finding Subcategory",
        filters={
            "parent": parent,
            "subcategory": subcategory,
        },
        fields=[
            "rate_per_gm",
            "rate_per_pc",
            "wastage",
            "wastage_per_pcs",
            "supplier_fg_purchase_rate",
            "subcontracting_rate",
            "subcontracting_wastage",
        ],
        limit=1,
    )

    if not sub_rows:
        return {}

    return sub_rows[0]
@frappe.whitelist()
def get_making_charge_price(
    parent,
    subcategory
):
   
    sub_rows = frappe.get_all(
        "Making Charge Price Item Subcategory",
        filters={
            "parent": parent,
            "subcategory": subcategory,
        },
        fields=[
            "subcategory",
            "rate_per_gm",
            "rate_per_pc",
            "supplier_fg_purchase_rate",
            "wastage",
            "subcontracting_rate",
            "subcontracting_wastage",
            "wastage_per_pcs",
            "name",
            "to_diamond",
            "from_diamond",
            "rate_per_gm_threshold",
        ],
        limit=1,
    )

    if not sub_rows:
        return {}

    return sub_rows[0]
 


 
@frappe.whitelist()
def get_diamond_rate(
    customer,
    diamond_type,
    stone_shape,
    diamond_quality,
    price_list_type,
    sieve_size_range=None,
    weight_per_pcs=None,
    diamond_size_in_mm=None,
):
    filters = {
        "price_list": "Standard Selling",
        "price_list_type": price_list_type,
        "customer": customer,
        "diamond_type": diamond_type,
        "stone_shape": stone_shape,
        "diamond_quality": diamond_quality,
    }

    fields = [
        "rate",
        "outright_handling_charges_rate",
        "outright_handling_charges_in_percentage",
        "outwork_handling_charges_rate",
        "outwork_handling_charges_in_percentage",
        "supplier_fg_purchase_rate",
    ]

    # Sieve Size Range
    if price_list_type == "Sieve Size Range":
        if not sieve_size_range:
            return {}

        data = frappe.db.get_value(
            "Diamond Price List",
            {**filters, "sieve_size_range": sieve_size_range},
            fields,
            as_dict=True,
        )

        return data or {}

    # Weight (in cts)
    elif price_list_type == "Weight (in cts)":
        if not weight_per_pcs:
            return {}

        conditions = " AND ".join(f"`{k}` = %s" for k in filters)

        rows = frappe.db.sql(
            f"""
            SELECT {", ".join(fields)}
            FROM `tabDiamond Price List`
            WHERE {conditions}
              AND %s BETWEEN from_weight AND to_weight
            LIMIT 1
            """,
            list(filters.values()) + [weight_per_pcs],
            as_dict=True,
        )

        return rows[0] if rows else {}

    # Size (in mm)
    elif price_list_type == "Size (in mm)":
        if not diamond_size_in_mm:
            return {}

        data = frappe.db.get_value(
            "Diamond Price List",
            {**filters, "diamond_size_in_mm": diamond_size_in_mm},
            fields,
            as_dict=True,
        )

        return data or {}

    return {}






import frappe
from frappe.utils import flt, cint

@frappe.whitelist()
def get_fixed_retail_rate(
    customer=None,
    customer_group=None,
    price_list_type=None,
    per_pc_or_per_carat=None,
    cut_or_cab=None,
    gemstone_type=None,
    stone_shape=None,
    gemstone_grade=None,
):
    # ---------------- Fixed ----------------
    if price_list_type == "Fixed" and customer_group != "Retail":
        row = frappe.get_all(
            "Gemstone Price List",
            filters={
                "customer":            customer,
                "price_list_type":     price_list_type,
                "per_pc_or_per_carat": per_pc_or_per_carat,
                "cut_or_cab":          cut_or_cab,
                "gemstone_type":       gemstone_type,
                "stone_shape":         stone_shape,
                "gemstone_grade":      gemstone_grade,
            },
            fields=["name", "price_list_type", "rate", "handling_rate",
                    "outwork_handling_charges_rate"],
            limit=1,
        )
        return row[0] if row else {}

    # ---------------- Retail ----------------
    elif customer_group == "Retail":
        row = frappe.get_all(
            "Gemstone Price List",
            filters={
                "is_retail_customer":  1,
                "price_list_type":     price_list_type,
                "per_pc_or_per_carat": per_pc_or_per_carat,
                "cut_or_cab":          cut_or_cab,
                "gemstone_type":       gemstone_type,
                "stone_shape":         stone_shape,
            },
            fields=["name", "price_list_type", "rate", "handling_rate",
                    "outwork_handling_charges_rate"],
            limit=1,
        )
        return row[0] if row else {}

    return {}


@frappe.whitelist()
def get_diamond_range_rate(
    customer=None,
    cut_or_cab=None,
    gemstone_grade=None,
):
    gpc = frappe.get_all(
        "Gemstone Price List",
        filters={
            "customer":        customer,
            "price_list_type": "Diamond Range",
            "cut_or_cab":      cut_or_cab,
            "gemstone_grade":  gemstone_grade,
        },
        fields=["name"],
        limit=1,
    )

    if not gpc:
        return {}

    doc = frappe.get_doc("Gemstone Price List", gpc[0].name)

    return {
        "name": gpc[0].name,
        "doc":  doc.as_dict(),
    }

