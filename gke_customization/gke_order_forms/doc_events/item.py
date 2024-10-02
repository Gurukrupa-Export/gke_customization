import frappe

def before_validate(self,method):
    if self.custom_is_similar_item:
        create_group_for_similar(self)

    if self.custom_is_sufix_item == 1:
        create_group_for_sufix(self)

    if self.custom_is_set_item:
        create_group_for_set(self)

def create_group_for_similar(self):

    #item from similar item table
    lastSimilar_itemcode = self.custom_similar_item_table[-1].get('item_code')
    item_ref_doc = get_item_ref_doc(self,lastSimilar_itemcode, "tabSimilar Item Table", type='Similar')    

    # same similar item code as parent item code - add into exiting item code
    nameitem_ref_doc = get_nameitem_ref_doc(self,"tabSimilar Item Table", type='Similar')    
    
    #item from reference group when add item in same child table 
    same_ref_doc = get_same_ref_doc(self,"tabSimilar Item Table", type='Similar')
    
    # frappe.throw(f" gr{nameitem_ref_doc} || {same_ref_doc}")
    
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
                # frappe.delete_doc("Item Reference Group", same_ref_doc[-1].get('name'))

            # frappe.throw(f" 1heloo000000 {same_ref_doc} || {item_ref_doc}")

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
            # frappe.throw(f"{same_ref_doc[-1].get('name')}")

            # if same_ref_doc:
                # frappe.delete_doc("Item Reference Group", same_ref_doc[-1].get('name'))

            # frappe.throw(f"heloo000000 {existing_item_codes} || {name} || {item_ref_doc} || {same_ref_doc}")

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

        # frappe.throw(f"heloo0000001 {existing_item_codes} || {name} ")
        
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

            # frappe.throw(f"heloo0000002 {existing_item_codes} || {name} || {nameitem_ref_doc}")
    # create new group
    else:
        # frappe.throw(f"hi ")
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
 