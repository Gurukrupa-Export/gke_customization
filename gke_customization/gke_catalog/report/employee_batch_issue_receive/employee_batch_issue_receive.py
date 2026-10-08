# Employee Batch Issue Receive
# Copyright (c) 2024, Jewellery ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _

# Most rows the report returns. get_main_data keeps only issued-but-not-received
# operations before applying it, so it is reached only when that many are
# outstanding - and execute() then says so instead of dropping rows silently.
ROW_LIMIT = 10000

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)

    message = None
    if len(data) > ROW_LIMIT:
        data = data[:ROW_LIMIT]
        message = _(
            "Only the newest {0} outstanding operations are shown. Narrow the filters to see the rest."
        ).format(ROW_LIMIT)

    return columns, data, message

def get_columns():
    return [
        {
            "label": _("Manufacturing Work Order"),
            "fieldname": "manufacturing_work_order",
            "fieldtype": "Link",
            "options": "Manufacturing Work Order",
            "width": 180
        },
        {
            "label": _("Manufacturing Operation"),
            "fieldname": "manufacturing_operation",
            "fieldtype": "Link",
            "options": "Manufacturing Operation",
            "width": 180
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 100
        },
        # {
        #     "label": _("Company"),
        #     "fieldname": "company",
        #     "fieldtype": "Link",
        #     "options": "Company",
        #     "width": 150
        # },
        # {
        #     "label": _("Branch"),
        #     "fieldname": "branch",
        #     "fieldtype": "Link",
        #     "options": "Branch",
        #     "width": 120
        # },
        {
            "label": _("Manufacturer"),
            "fieldname": "manufacturer",
            "fieldtype": "Link",
            "options": "Manufacturer",
            "width": 120
        },
        {
            "label": _("Department"),
            "fieldname": "department",
            "fieldtype": "Link",
            "options": "Department",
            "width": 150
        },
        {
            "label": _("Operation"),
            "fieldname": "operation",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("Issue ID"),
            "fieldname": "issue_ir",
            "fieldtype": "Link",
            "options": "Employee IR",
            "width": 130
        },
        {
            "label": _("Receive ID"),
            "fieldname": "receive_ir",
            "fieldtype": "Link",
            "options": "Employee IR",
            "width": 130
        },
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("Employee ID"),
            "fieldname": "employee_id",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 120
        },
        {
            "label": _("Gross Wt"),
            "fieldname": "gross_wt",
            "fieldtype": "Float",
            "width": 100,
            "precision": 3
        },
        {
            "label": _("Receive Gross Wt"),
            "fieldname": "received_gross_wt",
            "fieldtype": "Float",
            "width": 130,
            "precision": 3
        },
        {
            "label": _("Net Wt"),
            "fieldname": "net_wt",
            "fieldtype": "Float",
            "width": 100,
            "precision": 3
        },
        {
            "label": _("Finding Wt"),
            "fieldname": "finding_wt",
            "fieldtype": "Float",
            "width": 100,
            "precision": 3
        },
        {
            "label": _("Metal Wt (Net + Finding)"),
            "fieldname": "metal_wt",
            "fieldtype": "Float",
            "width": 150,
            "precision": 3
        },
        {
            "label": _("Diamond Wt"),
            "fieldname": "diamond_wt",
            "fieldtype": "Float",
            "width": 110,
            "precision": 3
        },
        {
            "label": _("Diamond Pcs"),
            "fieldname": "diamond_pcs",
            "fieldtype": "Int",
            "width": 110
        },
        {
            "label": _("Gemstone Wt"),
            "fieldname": "gemstone_wt",
            "fieldtype": "Float",
            "width": 120,
            "precision": 3
        },
        {
            "label": _("Gemstone Pcs"),
            "fieldname": "gemstone_pcs",
            "fieldtype": "Int",
            "width": 120
        },
        {
            "label": _("Other Wt"),
            "fieldname": "other_wt",
            "fieldtype": "Float",
            "width": 100,
            "precision": 3
        },
        {
            "label": _("Loss Wt"),
            "fieldname": "loss_wt",
            "fieldtype": "Float",
            "width": 100,
            "precision": 3
        },
        {
            "label": _("Issue Date"),
            "fieldname": "issue_date",
            "fieldtype": "Datetime",
            "width": 150
        },
        {
            "label": _("Receive Date"),
            "fieldname": "receive_date",
            "fieldtype": "Datetime",
            "width": 150
        },
        {
            "label": _("Time Diff (D:H:M)"),
            "fieldname": "time_diff",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("Issue By"),
            "fieldname": "issue_by",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Receive By"),
            "fieldname": "receive_by",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Customer"),
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 150
        }
    ]

def get_data(filters):
    # Get main data - outstanding operations only (see get_main_data)
    main_data = get_main_data(filters)
    if not main_data:
        return []

    # Get Employee IR data for those operations only
    ir_data = get_employee_ir_data(filters, [row.get("manufacturing_operation") for row in main_data])

    # Create a mapping for faster lookup.
    # ir_data is ordered by date_time DESC, so the first Issue/Receive seen
    # for a given key is the most recent one - keep that, ignore older ones.
    ir_mapping = {}
    for ir_row in ir_data:
        key = (ir_row.get("manufacturing_operation"), ir_row.get("employee"))
        if key not in ir_mapping:
            ir_mapping[key] = {"issue": None, "receive": None}

        if ir_row.get("type") == "Issue" and not ir_mapping[key]["issue"]:
            ir_mapping[key]["issue"] = ir_row
        elif ir_row.get("type") == "Receive" and not ir_mapping[key]["receive"]:
            ir_mapping[key]["receive"] = ir_row

    # Merge Employee IR data into main data
    for row in main_data:
        key = (row.get("manufacturing_operation"), row.get("employee_id"))

        if key in ir_mapping:
            if ir_mapping[key]["issue"]:
                row["issue_date"] = ir_mapping[key]["issue"].get("date_time")
                row["issue_by"] = ir_mapping[key]["issue"].get("full_name") or ir_mapping[key]["issue"].get("owner")
                row["issue_ir"] = ir_mapping[key]["issue"].get("employee_ir")

            if ir_mapping[key]["receive"]:
                row["receive_date"] = ir_mapping[key]["receive"].get("date_time")
                row["receive_by"] = ir_mapping[key]["receive"].get("full_name") or ir_mapping[key]["receive"].get("owner")
                row["receive_ir"] = ir_mapping[key]["receive"].get("employee_ir")

        row["time_diff"] = get_time_diff_str(row.get("issue_date"), row.get("receive_date"))

    # Only keep rows that were issued to an employee but not yet received.
    # get_main_data already selects these before its LIMIT; this only drops a row
    # whose latest Issue has no date, as before.
    main_data = [row for row in main_data if row.get("issue_date") and not row.get("receive_date")]

    return main_data

def get_time_diff_str(issue_date, receive_date):
    if not issue_date or not receive_date:
        return ""

    issue_date = frappe.utils.get_datetime(issue_date)
    receive_date = frappe.utils.get_datetime(receive_date)

    seconds = (receive_date - issue_date).total_seconds()
    if seconds < 0:
        return ""

    days, remainder = divmod(int(seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60

    return f"{days}d:{hours:02d}h:{minutes:02d}m"

def get_main_data(filters):
    conditions = get_conditions(filters)

    # `outstanding` = each (operation, employee) pair with a submitted Issue and no
    # submitted Receive - the rule get_data applies - so ORDER BY/LIMIT below work on
    # outstanding operations, not on the whole operation history. <=> matches the
    # NULL employee of subcontracting rows the way get_data's tuple key does.
    # A filtered run applies its filters inside `outstanding` as well, so it groups only
    # the matching operations' IR rows instead of the whole IR history. That is exact:
    # the join below requires the same operation and employee anyway.
    outstanding_filter = ""
    if filters.get("employee_id"):
        outstanding_filter += " AND eir.employee = %(employee_id)s"
    op_conditions = get_conditions(filters, alias="op")
    if op_conditions:
        outstanding_filter += f"""
                AND eiro.manufacturing_operation IN (
                    SELECT op.name
                    FROM `tabManufacturing Operation` op
                    WHERE op.operation IS NOT NULL
                        AND op.operation != ''
                        AND op.status IN ('WIP', 'Finished')
                        {op_conditions}
                )"""

    query = f"""
        SELECT 
            mo.manufacturing_work_order,
            mo.name as manufacturing_operation,
            mo.status,
            mo.company,
            mwo.branch,
            mo.manufacturer,
            mo.department,
            mo.operation,
            emp.employee_name,
            mo.employee as employee_id,
            mo.gross_wt,
            mo.received_gross_wt,
            mo.net_wt,
            mo.finding_wt,
            (COALESCE(mo.net_wt, 0) + COALESCE(mo.finding_wt, 0)) as metal_wt,
            mo.diamond_wt,
            mo.diamond_pcs,
            mo.gemstone_wt,
            mo.gemstone_pcs,
            mo.other_wt,
            CASE 
                WHEN mo.loss_wt < 0 THEN ABS(mo.loss_wt)
                ELSE NULL 
            END as loss_wt,
            mwo.customer
        FROM 
            `tabManufacturing Operation` mo
        INNER JOIN (
            SELECT
                eiro.manufacturing_operation,
                eir.employee
            FROM
                `tabEmployee IR` eir
            INNER JOIN
                `tabEmployee IR Operation` eiro ON eiro.parent = eir.name
            WHERE
                eir.type IN ('Issue', 'Receive')
                AND eir.docstatus = 1
                {outstanding_filter}
            GROUP BY
                eiro.manufacturing_operation, eir.employee
            HAVING
                SUM(eir.type = 'Issue') > 0
                AND SUM(eir.type = 'Receive') = 0
        ) outstanding ON outstanding.manufacturing_operation = mo.name
            AND outstanding.employee <=> mo.employee
        LEFT JOIN
            `tabManufacturing Work Order` mwo ON mo.manufacturing_work_order = mwo.name
        LEFT JOIN 
            `tabEmployee` emp ON mo.employee = emp.name
        WHERE 
            mo.operation IS NOT NULL 
            AND mo.operation != ''
            AND mo.status IN ('WIP', 'Finished')
            {conditions}
        ORDER BY 
            mo.creation DESC
        LIMIT {ROW_LIMIT + 1}
    """
    
    result = frappe.db.sql(query, filters, as_dict=True)

    return result

def get_employee_ir_data(filters, manufacturing_operations):
    # Separate query for Employee IR data - only for Issue/Receive columns,
    # and only for the operations get_main_data returned
    operation_conditions = ""

    if filters.get("operation"):
        operation_conditions += " AND mo.operation = %(operation)s"
    
    if filters.get("department"):
        operation_conditions += " AND mo.department = %(department)s"
    
    if filters.get("employee_id"):
        operation_conditions += " AND eir.employee = %(employee_id)s"

    query = f"""
        SELECT
            eir.name as employee_ir,
            eiro.manufacturing_operation,
            eir.employee,
            eir.type,
            eir.date_time,
            eir.owner,
            u.full_name
        FROM 
            `tabEmployee IR` eir
        INNER JOIN 
            `tabEmployee IR Operation` eiro ON eiro.parent = eir.name
        INNER JOIN
            `tabManufacturing Operation` mo ON mo.name = eiro.manufacturing_operation
        LEFT JOIN 
            `tabUser` u ON eir.owner = u.name
        WHERE 
            eir.type IN ('Issue', 'Receive')
            AND eiro.manufacturing_operation IS NOT NULL
            AND eiro.manufacturing_operation IN %(manufacturing_operations)s
            AND eir.docstatus = 1
            {operation_conditions}
        ORDER BY 
            eir.date_time DESC
    """
    
    values = {**filters, "manufacturing_operations": tuple(manufacturing_operations)}
    result = frappe.db.sql(query, values, as_dict=True)

    return result

def get_conditions(filters, alias="mo"):
    conditions = ""

    # # Branch filter optional - includes NULL values
    # if filters.get("branch"):
    #     conditions += " AND (mwo.branch = %(branch)s OR mwo.branch IS NULL)"
    
    if filters.get("manufacturer"):
        conditions += f" AND {alias}.manufacturer = %(manufacturer)s"
        
    if filters.get("department"):
        conditions += f" AND {alias}.department = %(department)s"
        
    if filters.get("operation"):
        conditions += f" AND {alias}.operation = %(operation)s"
        
    if filters.get("employee_id"):
        conditions += f" AND {alias}.employee = %(employee_id)s"

    return conditions


# Whitelisted method to get employees by operation
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_employees_by_operation(doctype, txt, searchfield, start, page_len, filters):
    """Get employees who worked on a specific operation"""
    department = filters.get("department")
    operation = filters.get("operation")

    # If no operation selected, return all active employees
    if not operation:
        return frappe.db.sql("""
            SELECT DISTINCT
                emp.name,
                emp.employee_name
            FROM `tabEmployee` emp
            WHERE
                emp.status = 'Active'
                AND (emp.name LIKE %(txt)s OR emp.employee_name LIKE %(txt)s)
            ORDER BY emp.employee_name
            LIMIT %(start)s, %(page_len)s
        """, {
            "txt": "%" + txt + "%",
            "start": start,
            "page_len": page_len
        })

    # If operation selected, filter employees who worked on that operation
    conditions = "mo.operation = %(operation)s"

    if department:
        conditions += " AND mo.department = %(department)s"

    return frappe.db.sql(f"""
        SELECT DISTINCT
            emp.name,
            emp.employee_name
        FROM `tabEmployee` emp
        INNER JOIN `tabManufacturing Operation` mo
            ON mo.employee = emp.name
        WHERE
            {conditions}
            AND emp.status = 'Active'
            AND (emp.name LIKE %(txt)s OR emp.employee_name LIKE %(txt)s)
        ORDER BY emp.employee_name
        LIMIT %(start)s, %(page_len)s
    """, {
        "department": department,
        "operation": operation,
        "txt": "%" + txt + "%",
        "start": start,
        "page_len": page_len
    })
