import frappe
import json
from frappe import _

@frappe.whitelist()
def get_department_wise_items(user_id=None, item_group=None):
    if not user_id and not item_group:
        frappe.throw("User ID or Item Group is required.")
    
    emp_detail = frappe.db.get_value("Employee", {'user_id': user_id}, ['name', 'department'], as_dict=True)
    if not emp_detail:
        frappe.throw("No employee found for the given user.")

    consumable_master = frappe.db.get_value("Consumable Master", {'department': emp_detail.department}, ['name'])
    if not consumable_master:
        frappe.throw("No Consumable Master found for this department.")

    department_wise_items = frappe.db.get_all(
        "Consumable Item Details", 
        filters={'parent': consumable_master}, 
        fields=['item_code']
    )

    all_items = []

    for item_row in department_wise_items:
        item_code = item_row.item_code

        item_code = item_row.item_code

        item_filters = {
            'name': item_code,
            'has_variants': 0
        }

        # Add item_group filter if passed
        if item_group:
            item_filters['item_group'] = item_group
        else:
            item_filters['item_group'] = ['in', [
                'Tools & Accessories', 'Chemicals', 'Machinery', 'Office Supplies', 'Electric Accessories'
            ]]

        item_detail = frappe.db.get_all(
            "Item",
            filters = item_filters,
            fields=['name', 'variant_of', 'item_group', 'item_code', 'image']
        )

        for itm in item_detail:
            if itm['variant_of']:
                child_attrs = frappe.db.get_all(
                    "Item Variant Attribute",
                    filters={'parent': itm['name']},
                    fields=['attribute', 'attribute_value']
                )
                for attr in child_attrs:
                    normalized_key = attr['attribute'].lower().replace(' ', '_')
                    itm[normalized_key] = attr['attribute_value']
            else:
                itm['consumable_type'] = itm['item_code']

            all_items.append(itm)

    frappe.response['message'] = all_items


@frappe.whitelist()
def create_consumable_material_req(items, user):
    if isinstance(items, str):
        items = json.loads(items)
    
    if not items:
        frappe.throw(_("No items provided."))
    
    required_by = items[0].get("required_by")
    if not required_by:
        frappe.throw(_("Required By date is missing."))

    employee_detail = frappe.db.get_value("Employee", {'user_id': user}, ['company','name','branch','department'], as_dict=True)
    if not employee_detail:
        frappe.throw(_("User Id is not linked to Employee."))
    
    target_emp_warehouse = frappe.db.get_value("Warehouse",
                    {'department': employee_detail.department,'company':employee_detail.company,'warehouse_type':'Consumables'}, 
                    ['name'])
    
    # frappe.throw(f"{target_emp_warehouse} , {user}")
    if not target_emp_warehouse:
        frappe.throw(_("Employee's Department is not linked to the Warehouse."))

    consumable_warehouse = frappe.db.get_value("Consumable Master", {'department': employee_detail.department}, ['warehouse'])
    source_warehouse = frappe.db.get_value("Warehouse",
            {   
                'name': consumable_warehouse,
                'custom_branch': employee_detail.branch,
                'company': employee_detail.company,
                'warehouse_type': 'Consumables',
                'parent_warehouse': ['like', 'Stores%']
            }, 
            ['name']) 
    
    if not source_warehouse:
        frappe.throw(_("Check Store Warehouse once in Warehouse."))

    material_req = frappe.new_doc('Material Request')
    material_req.material_request_type = 'Material Transfer'
    material_req.schedule_date = required_by
    material_req.company = employee_detail.company
    material_req.set_warehouse = target_emp_warehouse
    material_req.set_from_warehouse = source_warehouse

    for item in items:
        item_code = item.get("item_code")
        quantity = item.get("quantity")

        material_req.append('items', {
            'item_code': item_code,
            'qty': quantity,
            'from_warehouse': source_warehouse,
            'warehouse': target_emp_warehouse
        })

    material_req.insert()
    material_req.submit()

    frappe.db.set_value("Material Request", material_req.name, 'workflow_state', 'Submitted')
    
    return material_req.name
 