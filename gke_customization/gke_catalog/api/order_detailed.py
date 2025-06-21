import frappe, json
from frappe.utils import today
from frappe.utils import (
	get_datetime,get_first_day,get_last_day,nowdate,
    add_days,getdate
)

# /home/frappe/frappe-bench/apps/gke_customization/gke_customization/gke_catalog/api/order_detailed.py

# initial call
# http://192.168.200.207:8001/api/method/gke_customization.gke_order_forms.doc_events.sketch_order.get_sketch_order?

# http://192.168.200.207:8001/api/method/gke_customization.gke_catalog.api.order_detailed.get_order?

@frappe.whitelist()
def get_order(from_date=None, to_date=None, of_docstatus=None, branch=None, order_form=None, customer=None, workflow_state=None, docstatus=None):
    from_date = frappe.utils.getdate(from_date)
    to_date = frappe.utils.getdate(to_date)
    of_doc_status = int(of_docstatus) or 0
   
    filters = {
        'order_date': ["between", [from_date, to_date]],
        # 'company': company,
        'docstatus': of_doc_status
    }

    if branch:
        filters['branch'] = branch
    if order_form:
        filters['name'] = order_form  # Assuming this is the primary key of Sketch Order Form
    if customer:
        filters['customer_code'] = customer
        

    if to_date and from_date:
        order_forms = frappe.db.get_list("Order Form",
            filters = filters,
            fields=["name", "docstatus", "company", "branch","workflow_state","order_date","customer_code"]
        )

        valid_sketch_order_forms = []
        for form in order_forms:
            order_filters = {'cad_order_form': form.name}
            if docstatus:
                o_doc_status = int(docstatus)
                order_filters['docstatus'] = o_doc_status
            if workflow_state:
                order_filters['workflow_state'] = workflow_state

            orders = frappe.db.get_list(
                "Order",
                filters=order_filters,
                fields=["name", "docstatus", "company", "branch","customer_code","cad_order_form","workflow_state",
                        "order_type","flow_type","order_date","delivery_date","cad_file",
                        "creation","owner","modified","_assign","item","new_bom","category"
                    ]
                )
            # if not orders:
            #     continue

            for order in orders:
            #     final_items = frappe.db.get_list("Item",
            #            filters={
            #                'custom_cad_order_form_id': order["cad_order_form"]},
            #            fields=["name", "custom_cad_order_form_id","image","description"]
            # ) 
                final_items = []
                item_code = order.get("item")

                if item_code:
                   item_data = frappe.db.get_value("Item", item_code, 
                            ["name", "item_group", "image", "description", "stock_uom"], as_dict=True
                            )
                   if item_data:
                        final_items.append(item_data)

                bom_detail = frappe.db.get_list("BOM",
                    filters={
                        'name': order["new_bom"],
                        'bom_type': 'Template'
                    },
                    fields = [
                            "item",
                            "image",
                            "metal_weight",
                            "total_diamond_weight_in_gms",
                            "total_finding_weight_per_gram",
                            "total_gemstone_weight_in_gms",
                            "other_weight",
                            "finding_weight_",
                            "diamond_weight",
                            "gemstone_weight",
                            "front_view_finish"

                        ]
                ) 
                    
                
                
                assign_raw = order.get("_assign")
                if assign_raw:
                    try:
                        assign_list = json.loads(assign_raw)
                        first_user = assign_list[0] if assign_list else None
                        order["_assign"] = first_user
                        order["assigned_depart"] = None
                        if first_user:
                            employee_dept = frappe.db.get_value("Employee",{'user_id': order["_assign"]},['department'])
                            order["assigned_depart"] = employee_dept
                    except Exception:
                        order["_assign"] = None
                        order["assigned_depart"] = None
                else:
                    order["_assign"] = None
                
                owner_raw = order.get("owner")
                if owner_raw:
                    try: 
                        order["owner_id"] = None
                        order["owner_dept"] = None
                        order["owner_desig"] = None
                        employee = frappe.db.get_value("Employee", {'user_id': owner_raw}, ['name', 'department', 'designation'], as_dict=True)
                        if employee:
                            order["owner_id"] = employee.name
                            order["owner_dept"] = employee.department
                            order["owner_desig"] = employee.designation

                    except Exception:
                        order["owner_id"] = None
                        order["owner_dept"] = None
                        order["owner_desig"] = None 
            
                order["order_id"] = order.pop("name")
                order["workflow_state"] = order.pop("workflow_state")
                order["items"] = final_items  
                order["bom_detail"] = bom_detail
            
            if form["docstatus"] == 0 or orders:
                form["of_docstatus"] = form.pop("docstatus")
                form["orderform_id"] = form.pop("name")
                form["of_workflow_state"] = form.pop("workflow_state")
                if orders:
                    form["order"] = orders
             
            
                valid_sketch_order_forms.append(form)  # ✅ Collect only valid forms

    return valid_sketch_order_forms


      # form["sketch_order"] = orders
          
                # order["bom_detail"] = bom_detail