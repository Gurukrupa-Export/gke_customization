import frappe


@frappe.whitelist()
def get_context(employee):
    employee_detail = []
    for i in frappe.get_list('Employee',['name','employee_name','department','designation','relieving_date','date_of_joining']):
        if i['name'] == employee:
            employee_detail.append(i)
            break
    return employee_detail