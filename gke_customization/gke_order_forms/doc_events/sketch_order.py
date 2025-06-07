import frappe, json
from frappe.utils import today
from frappe.utils import (
	get_datetime,get_first_day,get_last_day,nowdate,
    add_days,getdate
)

# /home/frappe/frappe-bench/apps/gke_customization/gke_customization/gke_order_forms/doc_events/sketch_order.py

# initial call
# http://192.168.200.207:8001/api/method/gke_customization.gke_order_forms.doc_events.sketch_order.get_sketch_order?

# with filters
# ?from_date=2025-06-03&to_date=2025-06-05&company=Gurukrupa%20Export%20Private%20Limited&sof_docstatus=1


@frappe.whitelist()
def get_sketch_order(from_date=None, to_date=None, company=None, sof_docstatus=None, branch=None, sketch_order_form=None, customer=None, workflow_state=None, docstatus=None):
    from_date = frappe.utils.getdate(from_date)
    to_date = frappe.utils.getdate(to_date)
    sof_doc_status = int(sof_docstatus)
   
    filters = {
        'order_date': ["between", [from_date, to_date]],
        'company': company,
        'docstatus': sof_doc_status
    }

    if branch:
        filters['branch'] = branch
    if sketch_order_form:
        filters['name'] = sketch_order_form  # Assuming this is the primary key of Sketch Order Form
    if customer:
        filters['customer_code'] = customer
        

    if to_date and from_date:
        sketch_order_forms = frappe.db.get_list("Sketch Order Form",
            filters = filters,
            fields=["name", "docstatus", "company", "branch","workflow_state","order_date","customer_code"]
        )

        valid_sketch_order_forms = []
        for form in sketch_order_forms:
            order_filters = {'sketch_order_form': form.name}
            if docstatus:
                so_doc_status = int(docstatus)
                order_filters['docstatus'] = so_doc_status
            if workflow_state:
                order_filters['workflow_state'] = workflow_state

            orders = frappe.db.get_list(
                "Sketch Order",
                filters=order_filters,
                fields=["name", "docstatus", "company", "branch","customer_code","sketch_order_form","workflow_state","sketch_image",
                        "order_type","flow_type","order_date","delivery_date",
                        "creation","owner","modified","_assign"
                        ]
            )
            if not orders:
                continue

            for order in orders:
                final_items = frappe.db.get_all("Final Sketch Approval CMO",
                    filters={
                        'parent': order["name"]
                    },
                    fields=["sketch_image", "designer", "item", "category", "sub_category","setting_type","gold_wt_approx",
                            "diamond_wt_approx", ]
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
            
                order["sketch_order_id"] = order.pop("name")
                order["workflow_state"] = order.pop("workflow_state")
                order["items"] = final_items
            
            
            form["sof_docstatus"] = form.pop("docstatus")
            form["sketch_orderform_id"] = form.pop("name")
            form["sof_workflow_state"] = form.pop("workflow_state")
            form["sketch_order"] = orders  # Attach enriched orders to the form
            
            valid_sketch_order_forms.append(form)  # ✅ Collect only valid forms

    return valid_sketch_order_forms

 
        # form["sketch_order"] = orders
            # for item in items:
            #     bom_detail = frappe.db.get_list("BOM",
            #         filters={
            #             'item': item["custom_sketch_order_id"],
            #             'bom_type': 'Template'
            #         },
            #         fields = [
            #                 "item"
            #                 "metal_weight",
            #                 "total_diamond_weight_in_gms",
            #                 "total_finding_weight_per_gram",
            #                 "total_gemstone_weight_in_gms",
            #                 "other_weight"
            #             ]
            #     )
                # order["bom_detail"] = bom_detail