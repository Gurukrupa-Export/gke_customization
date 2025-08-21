import frappe

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": "Manufacturing Work Order", "fieldname": "work_order_id", "fieldtype": "Link", "options": "Manufacturing Work Order", "width": 180},
        {"label": "Department", "fieldname": "department", "fieldtype": "Data", "width": 120},
        {"label": "Department Process", "fieldname": "department_process", "fieldtype": "Data", "width": 140},
        {"label": "Manufacturing Operation", "fieldname": "operation_id", "fieldtype": "Link", "options": "Manufacturing Operation", "width": 150},
        {"label": "Operation", "fieldname": "operation_name", "fieldtype": "Data", "width": 120},
        {"label": "Manufacturing Operation Status", "fieldname": "operation_status", "fieldtype": "Data", "width": 160},
        {"label": "Employee", "fieldname": "employee_name", "fieldtype": "Data", "width": 160},
        {"label": "Main Slip ID", "fieldname": "main_slip_id", "fieldtype": "Data", "width": 120},
        {"label": "For Sub Contracting", "fieldname": "for_subcontracting", "fieldtype": "Data", "width": 140},
        {"label": "Is Finding", "fieldname": "is_finding", "fieldtype": "Data", "width": 80},
        {"label": "Gross Wt", "fieldname": "gross_wt", "fieldtype": "Float", "width": 90},
        {"label": "Net Wt", "fieldname": "net_wt", "fieldtype": "Float", "width": 90},
        {"label": "Finding Wt", "fieldname": "finding_wt", "fieldtype": "Float", "width": 90},
        {"label": "Diamond Wt", "fieldname": "diamond_wt", "fieldtype": "Float", "width": 90},
        {"label": "Diamond Pcs", "fieldname": "diamond_pcs", "fieldtype": "Int", "width": 90},
        {"label": "Gemstone Wt", "fieldname": "gemstone_wt", "fieldtype": "Float", "width": 90},
        {"label": "Gemstone Pcs", "fieldname": "gemstone_pcs", "fieldtype": "Int", "width": 90},
        {"label": "Other Wt", "fieldname": "other_wt", "fieldtype": "Float", "width": 90},
        {"label": "Loss Wt", "fieldname": "loss_wt", "fieldtype": "Float", "width": 90},
        {"label": "Metal Loss", "fieldname": "metal_loss", "fieldtype": "Float", "width": 90},
        {"label": "Finding Loss", "fieldname": "finding_loss", "fieldtype": "Float", "width": 90},
        {"label": "Diamond Loss", "fieldname": "diamond_loss", "fieldtype": "Float", "width": 90},
        {"label": "Gemstone Loss", "fieldname": "gemstone_loss", "fieldtype": "Float", "width": 90},
        {"label": "Time (mins)", "fieldname": "time_min", "fieldtype": "Float", "width": 80},
        {"label": "Time (hours)", "fieldname": "time_hour", "fieldtype": "Float", "width": 90},
        {"label": "Time (days)", "fieldname": "time_day", "fieldtype": "Float", "width": 90},
    ]

def get_data(filters):
    conditions = ""
    params = {}

    if filters and filters.get("manufacturing_work_order"):
        conditions += " AND mwo.name = %(manufacturing_work_order)s"
        params["manufacturing_work_order"] = filters.get("manufacturing_work_order")

    query = f"""
        SELECT
            mwo.name AS work_order_id,
            mop.department,
            COALESCE(mop.department_process, mop.operation) AS department_process,
            mop.name AS operation_id,
            mop.operation AS operation_name,
            mop.status AS operation_status,
            emp.employee_name,
            mop.main_slip_no AS main_slip_id,
            CASE WHEN mop.for_subcontracting = 1 THEN 'Yes' ELSE 'No' END AS for_subcontracting,
            CASE WHEN mop.is_finding = 1 THEN 'Yes' ELSE 'No' END AS is_finding,
            mop.gross_wt,
            mop.net_wt,
            mop.finding_wt,
            mop.diamond_wt,
            mop.diamond_pcs,
            mop.gemstone_wt,
            mop.gemstone_pcs,
            mop.other_wt,
            mop.loss_wt,
            COALESCE(SUM(CASE WHEN LOWER(it.item_group) LIKE '%%diamond%%' THEN mbl.proportionally_loss ELSE 0 END), 0) AS diamond_loss,
            COALESCE(SUM(CASE WHEN LOWER(it.item_group) LIKE '%%gemstone%%' THEN mbl.proportionally_loss ELSE 0 END), 0) AS gemstone_loss,
            COALESCE(SUM(CASE WHEN LOWER(it.item_group) LIKE '%%finding%%' THEN mbl.proportionally_loss ELSE 0 END), 0) AS finding_loss,
            COALESCE(motl.total_time_min, 0) AS time_min,
            COALESCE(motl.total_time_hour, 0) AS time_hour,
            COALESCE(motl.total_time_day, 0) AS time_day

        FROM `tabManufacturing Work Order` mwo
        INNER JOIN `tabManufacturing Operation` mop ON mop.manufacturing_work_order = mwo.name
        LEFT JOIN `tabEmployee` emp ON mop.employee = emp.name
        LEFT JOIN `tabManually Book Loss Details` mbl ON mbl.manufacturing_operation = mop.name AND mbl.docstatus = 1
        LEFT JOIN `tabItem` it ON mbl.item_code = it.item_code
        LEFT JOIN (
            SELECT 
                parent,
                SUM(time_in_mins) AS total_time_min,
                SUM(time_in_hour) AS total_time_hour,
                SUM(time_in_days) AS total_time_day
            FROM `tabManufacturing Operation Time Log`
            GROUP BY parent
        ) motl ON motl.parent = mop.name

        WHERE 1=1
        {conditions}
        GROUP BY mop.name, motl.total_time_min, motl.total_time_hour, motl.total_time_day
        ORDER BY mwo.name DESC, mop.idx DESC
    """

    operations = frappe.db.sql(query, params, as_dict=True)

    for op in operations:
        # Metal loss logic
        if op['diamond_loss'] > 0 or op['gemstone_loss'] > 0 or op['finding_loss'] > 0:
            op['metal_loss'] = 0.0
        else:
            op['metal_loss'] = op.get('loss_wt', 0.0)

        # Dynamic hour and day calculation from minutes if zero
        time_min = op.get('time_min') or 0.0
        if not op.get('time_hour'):
            op['time_hour'] = time_min / 60
        if not op.get('time_day'):
            op['time_day'] = time_min / 1440  # 1440 minutes per day

    return operations
