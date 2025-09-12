import frappe

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": "No.", "fieldname": "idx", "fieldtype": "Int", "width": 50},
        {"label": "Manufacturing Work Order", "fieldname": "work_order_id", "fieldtype": "Link", "options": "Manufacturing Work Order", "width": 180},
        {"label": "Department", "fieldname": "department", "fieldtype": "Data", "width": 120},
        {"label": "Department Process", "fieldname": "department_process", "fieldtype": "Data", "width": 120},
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
        {"label": "Time (hour)", "fieldname": "time_hour", "fieldtype": "Data", "width": 90},
        {"label": "Time (day)", "fieldname": "time_day", "fieldtype": "Float", "width": 90},
    ]

def get_data(filters):
    conditions = ""
    params = {}

    if filters and filters.get("manufacturing_work_order"):
        conditions += " AND mwo.name = %(manufacturing_work_order)s"
        params["manufacturing_work_order"] = filters.get("manufacturing_work_order")

    query = """
        SELECT
            ROW_NUMBER() OVER (ORDER BY COALESCE(mop.start_time, mop.creation)) AS idx,
            mwo.name AS work_order_id,
            mop.department,
            mop.department AS department_process,
            mop.name AS operation_id,
            mop.operation AS operation_name,
            mop.status AS operation_status,
            CASE 
                WHEN mop.for_subcontracting = 1 THEN mop.subcontractor
                ELSE emp.employee_name 
            END AS employee_name,
            mop.main_slip_no AS main_slip_id,
            CASE WHEN mop.for_subcontracting = 1 THEN 'Yes' ELSE 'No' END AS for_subcontracting,
            CASE WHEN mop.is_finding = 1 THEN 'Yes' ELSE 'No' END AS is_finding,
            
            -- Fields from Employee IR Operation
            COALESCE(eiro.gross_wt, 0) AS gross_wt,
            COALESCE(eiro.received_gross_wt, 0) AS received_gross_wt,
            
            -- Fields from Manufacturing Operation
            COALESCE(mop.net_wt, 0) AS net_wt,
            COALESCE(mop.finding_wt, 0) AS finding_wt,
            COALESCE(mop.diamond_wt, 0) AS diamond_wt,
            COALESCE(mop.diamond_pcs, 0) AS diamond_pcs,
            COALESCE(mop.gemstone_wt, 0) AS gemstone_wt,
            COALESCE(mop.gemstone_pcs, 0) AS gemstone_pcs,
            COALESCE(mop.other_wt, 0) AS other_wt,
            
            motl.time_in_hour AS time_hour,
            COALESCE(motl.total_time_day, 0) AS time_day

        FROM `tabManufacturing Work Order` mwo
        INNER JOIN `tabManufacturing Operation` mop ON mop.manufacturing_work_order = mwo.name
        LEFT JOIN `tabEmployee` emp ON mop.employee = emp.name
        LEFT JOIN `tabEmployee IR Operation` eiro ON eiro.manufacturing_operation = mop.name 
            AND eiro.docstatus = 1 
            AND eiro.gross_wt > 0 
            AND eiro.received_gross_wt > 0
        LEFT JOIN (
            SELECT 
                parent,
                MAX(time_in_hour) AS time_in_hour,
                SUM(time_in_days) AS total_time_day
            FROM `tabManufacturing Operation Time Log`
            GROUP BY parent
        ) motl ON motl.parent = mop.name

        WHERE 1=1 """ + conditions + """
        ORDER BY COALESCE(mop.start_time, mop.creation) DESC
    """

    operations = frappe.db.sql(query, params, as_dict=True)

    # Step 2: For each operation, calculate loss_wt and fetch loss data using Python
    for op in operations:
        operation_id = op['operation_id']
        
        # Calculate loss_wt using Employee IR Operation data: gross_wt - received_gross_wt (only when gross_wt > received_gross_wt)
        gross_wt = op.get('gross_wt', 0) or 0
        received_gross_wt = op.get('received_gross_wt', 0) or 0
        
        if gross_wt and received_gross_wt and gross_wt > received_gross_wt:
            op['loss_wt'] = gross_wt - received_gross_wt
        else:
            op['loss_wt'] = 0
        
        # Initialize loss values
        op['finding_loss'] = 0.0
        op['diamond_loss'] = 0.0
        op['metal_loss'] = 0.0
        op['gemstone_loss'] = 0.0

        # Get Employee Loss Details directly linked to manufacturing operation
        employee_losses = frappe.db.sql("""
            SELECT variant_of, proportionally_loss
            FROM `tabEmployee Loss Details`
            WHERE manufacturing_operation = %(operation)s AND docstatus = 1
        """, {'operation': operation_id}, as_dict=True)

        # Get Manually Book Loss Details through Manufacturing Operation document
        try:
            # Get the Manufacturing Operation document to access its child tables
            mo_doc = frappe.get_doc("Manufacturing Operation", operation_id)
            
            # Check if Manufacturing Operation has manually_book_loss_details child table
            manually_book_losses = []
            if hasattr(mo_doc, 'manually_book_loss_details'):
                for loss_row in mo_doc.manually_book_loss_details:
                    manually_book_losses.append({
                        'variant_of': getattr(loss_row, 'variant_of', ''),
                        'proportionally_loss': getattr(loss_row, 'proportionally_loss', 0) or getattr(loss_row, 'qty', 0)
                    })
            
            # Alternative approach: Check if it's linked through Employee IR
            if not manually_book_losses:
                # Find Employee IR documents that might contain manually book loss details for this operation
                employee_ir_docs = frappe.db.sql("""
                    SELECT DISTINCT parent 
                    FROM `tabEmployee Loss Details` 
                    WHERE manufacturing_operation = %(operation)s AND docstatus = 1
                """, {'operation': operation_id}, as_dict=True)
                
                for ir_doc in employee_ir_docs:
                    # Get Manually Book Loss Details from the same Employee IR
                    manual_losses = frappe.db.sql("""
                        SELECT variant_of, proportionally_loss
                        FROM `tabManually Book Loss Details`
                        WHERE parent = %(parent)s AND docstatus = 1
                    """, {'parent': ir_doc['parent']}, as_dict=True)
                    manually_book_losses.extend(manual_losses)

        except Exception as e:
            frappe.log_error(f"Error fetching manually book losses for {operation_id}: {str(e)}")
            manually_book_losses = []

        # Combine all losses and categorize
        all_losses = employee_losses + manually_book_losses
        
        for loss in all_losses:
            variant = loss.get('variant_of', '')
            loss_qty = loss.get('proportionally_loss', 0)
            
            if variant == 'F':
                op['finding_loss'] += loss_qty
            elif variant == 'D':
                op['diamond_loss'] += loss_qty
            elif variant == 'M':
                op['metal_loss'] += loss_qty
            elif variant == 'G':
                op['gemstone_loss'] += loss_qty
            else:
                # NULL or unclassified variants go to metal loss
                op['metal_loss'] += loss_qty

        # Calculate any remaining metal loss from calculated loss weight
        total_categorized_loss = (op['diamond_loss'] + op['finding_loss'] + 
                                 op['metal_loss'] + op['gemstone_loss'])
        total_loss_wt = op.get('loss_wt', 0.0)
        remaining_loss = max(0, total_loss_wt - total_categorized_loss)
        op['metal_loss'] += remaining_loss

        # Calculate time in days from time_day if not present
        if not op.get('time_day'):
            op['time_day'] = 0

    # Step 3: Replace ALL zero values with None (blank/null) for better display
    for op in operations:
        # Process ALL fields in the operation record
        for field_name, field_value in list(op.items()):
            # Check if the value represents zero in any form
            if field_value in (0, 0.0, 0.00, 0.000, '0', '0.0', '0.00', '0.000', '0.0000'):
                op[field_name] = None
            
            # Also handle string representations that might be empty or None
            elif field_value in ('', 'None', 'null'):
                op[field_name] = None
        
        # Special handling for time_hour field - preserve meaningful time formats
        time_hour_value = op.get('time_hour')
        if time_hour_value in ('00:00:00', '0:00:00', '00:00', '0:00'):
            op['time_hour'] = None

    return operations
