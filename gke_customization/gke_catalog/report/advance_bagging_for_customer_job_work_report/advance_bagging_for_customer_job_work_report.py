import frappe
from frappe.utils import format_datetime


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    
    # Add total row
    if data:
        total_row = get_total_row(data)
        data.append(total_row)
    
    return columns, data


def get_columns():
    return [
        {"label": "Company", "fieldname": "company", "fieldtype": "Data", "width": 220},
        {"label": "BOM ID", "fieldname": "bom_id", "fieldtype": "Link", "options": "BOM", "width": 180},
        {"label": "BOM Type", "fieldname": "bom_type", "fieldtype": "Data", "width": 130},
        {"label": "BOM Creation", "fieldname": "bom_creation", "fieldtype": "Data", "width": 150},
        {"label": "Material Type", "fieldname": "material_type", "fieldtype": "Data", "width": 130},
        {"label": "Item Attributes", "fieldname": "item_attributes", "fieldtype": "Data", "width": 350},
        {"label": "Quantity", "fieldname": "qty", "fieldtype": "Float", "width": 100},
        {"label": "Pcs", "fieldname": "pcs", "fieldtype": "Int", "width": 80},
        {"label": "Design Code", "fieldname": "design_code", "fieldtype": "Data", "width": 180},
        {"label": "Item Category", "fieldname": "item_category", "fieldtype": "Data", "width": 150},
        {"label": "Item Sub Category", "fieldname": "item_sub_category", "fieldtype": "Data", "width": 150}
    ]


def get_data(filters):
    conditions = ["bom.bom_type = 'Template'"]
    values = {}

    if filters:
        if filters.get("from_date"):
            conditions.append("bom.creation >= %(from_date)s")
            values["from_date"] = filters["from_date"]
        if filters.get("to_date"):
            conditions.append("bom.creation <= %(to_date)s")
            values["to_date"] = filters["to_date"]
        if filters.get("bom_id"):
            conditions.append("bom.name = %(bom_id)s")
            values["bom_id"] = filters["bom_id"]
        if filters.get("design_code"):
            conditions.append("bom.item = %(design_code)s")
            values["design_code"] = filters["design_code"]
        # Fix for empty arrays - only add filter if array has values
        if filters.get("item_category") and len(filters["item_category"]) > 0:
            conditions.append("bom.item_category IN %(item_category)s")
            values["item_category"] = tuple(filters["item_category"])
        if filters.get("item_sub_category") and len(filters["item_sub_category"]) > 0:
            conditions.append("bom.item_subcategory IN %(item_sub_category)s")
            values["item_sub_category"] = tuple(filters["item_sub_category"])

    where_clause = " AND ".join(conditions)

    # UNION query with fixed BOM Other Detail logic
    query = f"""
        SELECT 
            'BOM Diamond Detail' AS source,
            bd.parent AS bom_id,
            bom.company,
            bom.creation AS bom_creation,
            bom.bom_type,
            bom.item_category,
            bom.item_subcategory,
            COALESCE(bom.item, bom.name) AS design_code,
            bd.item AS item_code,
            bd.quantity,
            COALESCE(bd.weight_in_gms, bd.quantity * 0.2, 0) AS weight_in_grams,
            bd.pcs,
            'Diamond' AS material_type
        FROM `tabBOM Diamond Detail` bd
        INNER JOIN `tabBOM` bom ON bom.name = bd.parent
        WHERE {where_clause}

        UNION ALL

        SELECT 
            'BOM Gemstone Detail' AS source,
            gd.parent AS bom_id,
            bom.company,
            bom.creation AS bom_creation,
            bom.bom_type,
            bom.item_category,
            bom.item_subcategory,
            COALESCE(bom.item, bom.name) AS design_code,
            gd.item AS item_code,
            gd.quantity,
            COALESCE(gd.weight_in_gms, gd.quantity * 0.2, 0) AS weight_in_grams,
            gd.pcs,
            'Gemstone' AS material_type
        FROM `tabBOM Gemstone Detail` gd
        INNER JOIN `tabBOM` bom ON bom.name = gd.parent
        WHERE {where_clause}

        UNION ALL

        SELECT 
            'BOM Metal Detail' AS source,
            md.parent AS bom_id,
            bom.company,
            bom.creation AS bom_creation,
            bom.bom_type,
            bom.item_category,
            bom.item_subcategory,
            COALESCE(bom.item, bom.name) AS design_code,
            md.item AS item_code,
            md.quantity,
            md.quantity AS weight_in_grams,
            0 AS pcs,
            'Metal' AS material_type
        FROM `tabBOM Metal Detail` md
        INNER JOIN `tabBOM` bom ON bom.name = md.parent
        WHERE {where_clause}

        UNION ALL

        SELECT 
            'BOM Finding Detail' AS source,
            fd.parent AS bom_id,
            bom.company,
            bom.creation AS bom_creation,
            bom.bom_type,
            bom.item_category,
            bom.item_subcategory,
            COALESCE(bom.item, bom.name) AS design_code,
            fd.item AS item_code,
            fd.quantity AS quantity,
            fd.actual_quantity AS weight_in_grams,
            0 AS pcs,
            'Finding' AS material_type
        FROM `tabBOM Finding Detail` fd
        INNER JOIN `tabBOM` bom ON bom.name = fd.parent
        WHERE {where_clause}

        UNION ALL

        SELECT 
            'BOM Other Detail' AS source,
            od.parent AS bom_id,
            bom.company,
            bom.creation AS bom_creation,
            bom.bom_type,
            bom.item_category,
            bom.item_subcategory,
            COALESCE(bom.item, bom.name) AS design_code,
            od.item_code AS item_code,
            od.qty AS quantity,
            od.qty AS weight_in_grams,
            0 AS pcs,
            'DEBUG-OTHER-DETAIL' AS material_type
        FROM `tabBOM Other Detail` od
        INNER JOIN `tabBOM` bom ON bom.name = od.parent
        WHERE {where_clause}
            AND od.item_code IS NOT NULL
            AND od.qty > 0

        UNION ALL

        SELECT 
            'BOM Item' AS source,
            bi.parent AS bom_id,
            bom.company,
            bom.creation AS bom_creation,
            bom.bom_type,
            bom.item_category,
            bom.item_subcategory,
            COALESCE(bom.item, bom.name) AS design_code,
            bi.item_code AS item_code,
            '' AS quantity,
            0 AS weight_in_grams,
            0 AS pcs,
            '' AS material_type
        FROM `tabBOM Item` bi
        INNER JOIN `tabBOM` bom ON bom.name = bi.parent
        WHERE {where_clause}
            AND NOT EXISTS (SELECT 1 FROM `tabBOM Diamond Detail` WHERE parent = bi.parent)
            AND NOT EXISTS (SELECT 1 FROM `tabBOM Gemstone Detail` WHERE parent = bi.parent)
            AND NOT EXISTS (SELECT 1 FROM `tabBOM Metal Detail` WHERE parent = bi.parent)
            AND NOT EXISTS (SELECT 1 FROM `tabBOM Finding Detail` WHERE parent = bi.parent)
            AND NOT EXISTS (SELECT 1 FROM `tabBOM Other Detail` WHERE parent = bi.parent)

        ORDER BY bom_id, source, item_code
    """

    rows = frappe.db.sql(query, values, as_dict=True)
    data = []

    for row in rows:
        if not row.get("item_code"):
            continue
            
        # Get item attributes from specific BOM detail table
        attributes = get_item_attributes(row["item_code"], row["source"], row["bom_id"], row.get("quantity"))

        data.append({
            "company": row["company"],
            "bom_id": row["bom_id"],
            "bom_type": row["bom_type"],
            "bom_creation": format_datetime(row["bom_creation"], "dd-MM-yyyy HH:mm:ss"),
            "material_type": row["material_type"],
            "item_attributes": attributes,
            "qty": row["quantity"] or 0,
            "pcs": row["pcs"] or 0,
            "design_code": row.get("design_code") or row.get("bom_id"),
            "item_category": row.get("item_category") or "",
            "item_sub_category": row.get("item_subcategory") or "",
            "weight_in_grams": row.get("weight_in_grams") or 0
        })

    return data


def get_item_attributes(item_code, source_table, bom_id, quantity=None):
    """Get formatted item attributes from specific BOM detail tables"""
    attributes = []
    
    if source_table == 'BOM Diamond Detail':
        # Match by quantity first, fallback without quantity
        if quantity:
            diamond_attrs = frappe.db.get_value("BOM Diamond Detail", 
                {"parent": bom_id, "item": item_code, "quantity": quantity}, 
                ["diamond_type", "stone_shape", "diamond_sieve_size"], 
                as_dict=True)
        else:
            # Fallback if no quantity provided
            diamond_attrs = frappe.db.get_value("BOM Diamond Detail", 
                {"parent": bom_id, "item": item_code}, 
                ["diamond_type", "stone_shape", "diamond_sieve_size"], 
                as_dict=True)
        
        if diamond_attrs:
            for field, value in diamond_attrs.items():
                if value and value != "None":
                    field_label = field.replace('_', ' ').title()
                    attributes.append(f"• {field_label}: {value}")
    
    elif source_table == 'BOM Gemstone Detail':
        # Match by quantity first, fallback without quantity
        if quantity:
            gemstone_attrs = frappe.db.get_value("BOM Gemstone Detail", 
                {"parent": bom_id, "item": item_code, "quantity": quantity}, 
                ["gemstone_type", "stone_shape", "gemstone_quality", "gemstone_grade", 
                 "gemstone_size", "cut_or_cab"], 
                as_dict=True)
        else:
            # Fallback if no quantity provided
            gemstone_attrs = frappe.db.get_value("BOM Gemstone Detail", 
                {"parent": bom_id, "item": item_code}, 
                ["gemstone_type", "stone_shape", "gemstone_quality", "gemstone_grade", 
                 "gemstone_size", "cut_or_cab"], 
                as_dict=True)
        
        if gemstone_attrs:
            for field, value in gemstone_attrs.items():
                if value and value != "None":
                    field_label = field.replace('_', ' ').title()
                    attributes.append(f"• {field_label}: {value}")
    
    elif source_table == 'BOM Metal Detail':
        # Match by quantity first, fallback without quantity
        if quantity:
            metal_attrs = frappe.db.get_value("BOM Metal Detail", 
                {"parent": bom_id, "item": item_code, "quantity": quantity}, 
                ["metal_type", "metal_touch", "metal_purity"], 
                as_dict=True)
        else:
            # Fallback if no quantity provided
            metal_attrs = frappe.db.get_value("BOM Metal Detail", 
                {"parent": bom_id, "item": item_code}, 
                ["metal_type", "metal_touch", "metal_purity"], 
                as_dict=True)
        
        if metal_attrs:
            for field, value in metal_attrs.items():
                if value and value != "None":
                    field_label = field.replace('_', ' ').title()
                    attributes.append(f"• {field_label}: {value}")
    
    elif source_table == 'BOM Finding Detail':
        # For Finding Detail, use quantity for matching (since that's what we're displaying)
        if quantity:
            finding_attrs = frappe.db.get_value("BOM Finding Detail", 
                {"parent": bom_id, "item": item_code, "quantity": quantity}, 
                ["metal_type", "finding_category", "finding_type", "finding_size", 
                 "metal_purity"], 
                as_dict=True)
        else:
            # Fallback if no quantity provided
            finding_attrs = frappe.db.get_value("BOM Finding Detail", 
                {"parent": bom_id, "item": item_code}, 
                ["metal_type", "finding_category", "finding_type", "finding_size", 
                 "metal_purity"], 
                as_dict=True)
        
        if finding_attrs:
            for field, value in finding_attrs.items():
                if value and value != "None":
                    field_label = field.replace('_', ' ').title()
                    attributes.append(f"• {field_label}: {value}")
    
    elif source_table == 'BOM Other Detail':
        # For Other Detail, use qty for matching
        if quantity:
            # Try to get attributes from BOM Other Detail itself first
            other_attrs = frappe.db.get_value("BOM Other Detail", 
                {"parent": bom_id, "item_code": item_code, "qty": quantity}, 
                ["item_code"], 
                as_dict=True)
            
            if other_attrs:
                # Use Item Variant Attribute table for Other Detail
                item_attrs = frappe.get_all("Item Variant Attribute",
                    filters={"parent": item_code},
                    fields=["attribute", "attribute_value"],
                    order_by="creation asc")
                
                if item_attrs:
                    attributes = [f"• {attr.attribute}: {attr.attribute_value}" for attr in item_attrs]
        else:
            # Fallback if no quantity provided
            item_attrs = frappe.get_all("Item Variant Attribute",
                filters={"parent": item_code},
                fields=["attribute", "attribute_value"],
                order_by="creation asc")
            
            if item_attrs:
                attributes = [f"• {attr.attribute}: {attr.attribute_value}" for attr in item_attrs]
    
    elif source_table == 'BOM Item':
        # Use Item Variant Attribute table for BOM Item
        item_attrs = frappe.get_all("Item Variant Attribute",
            filters={"parent": item_code},
            fields=["attribute", "attribute_value"],
            order_by="creation asc")
        
        if item_attrs:
            attributes = [f"• {attr.attribute}: {attr.attribute_value}" for attr in item_attrs]
    
    return ",  ".join(attributes) if attributes else ""


def get_total_row(data):
    """Generate total row with sum of weight from BOM table fields with fallback to detail tables"""
    valid_data = [row for row in data if row.get("bom_id")]
    
    total_count = len(valid_data)
    
    # Get unique BOM IDs to avoid double counting
    bom_ids = list(set(row.get("bom_id") for row in valid_data if row.get("bom_id")))
    
    total_diamond_weight = 0
    total_gemstone_weight = 0  
    total_finding_weight = 0
    total_metal_weight = 0
    total_other_weight = 0
    total_pcs = sum(int(row.get("pcs") or 0) for row in valid_data)
    
    # Get totals from BOM table weight fields with fallback to detail tables
    for bom_id in bom_ids:
        bom_weights = frappe.db.get_value("BOM", bom_id, 
            ["total_diamond_weight_in_gms", "total_gemstone_weight_in_gms", 
             "finding_weight", "metal_weight", "other_weight"], 
            as_dict=True)
        
        if bom_weights:
            # Try to get from BOM table first
            bom_diamond = float(bom_weights.get("total_diamond_weight_in_gms") or 0)
            bom_gemstone = float(bom_weights.get("total_gemstone_weight_in_gms") or 0)
            bom_finding = float(bom_weights.get("finding_weight") or 0)
            bom_metal = float(bom_weights.get("metal_weight") or 0)
            bom_other = float(bom_weights.get("other_weight") or 0)
            
            # If BOM table values are 0 or None, fallback to detail tables
            if bom_diamond == 0:
                # Calculate from Diamond Detail table
                diamond_details = frappe.get_all("BOM Diamond Detail",
                    filters={"parent": bom_id},
                    fields=["weight_in_gms", "quantity"])
                
                for diamond in diamond_details:
                    weight = float(diamond.get("weight_in_gms") or 0)
                    if weight == 0:
                        # Convert carats to grams (1 carat = 0.2 grams)
                        weight = float(diamond.get("quantity") or 0) * 0.2
                    bom_diamond += weight
            
            if bom_gemstone == 0:
                # Calculate from Gemstone Detail table
                gemstone_details = frappe.get_all("BOM Gemstone Detail",
                    filters={"parent": bom_id},
                    fields=["weight_in_gms", "quantity"])
                
                for gemstone in gemstone_details:
                    weight = float(gemstone.get("weight_in_gms") or 0)
                    if weight == 0:
                        # Convert carats to grams (1 carat = 0.2 grams)
                        weight = float(gemstone.get("quantity") or 0) * 0.2
                    bom_gemstone += weight
            
            if bom_finding == 0:
                # Calculate from Finding Detail table using quantity
                finding_details = frappe.get_all("BOM Finding Detail",
                    filters={"parent": bom_id},
                    fields=["quantity"])
                
                for finding in finding_details:
                    bom_finding += float(finding.get("quantity") or 0)
            
            if bom_metal == 0:
                # Calculate from Metal Detail table
                metal_details = frappe.get_all("BOM Metal Detail",
                    filters={"parent": bom_id},
                    fields=["quantity"])
                
                for metal in metal_details:
                    bom_metal += float(metal.get("quantity") or 0)
            
            if bom_other == 0:
                # Calculate from Other Detail table only (BOM Item excluded from weight)
                other_details = frappe.get_all("BOM Other Detail",
                    filters={"parent": bom_id},
                    fields=["qty"])
                
                for other in other_details:
                    bom_other += float(other.get("qty") or 0)
            
            # Add to totals
            total_diamond_weight += bom_diamond
            total_gemstone_weight += bom_gemstone
            total_finding_weight += bom_finding
            total_metal_weight += bom_metal
            total_other_weight += bom_other
    
    # Calculate final total weight in grams
    total_weight_grams = total_diamond_weight + total_gemstone_weight + total_finding_weight + total_metal_weight + total_other_weight
    
    return {
        "company": f"Total BOMs = {total_count}",
        "bom_id": "",
        "bom_type": "",
        "bom_creation": "",
        "material_type": "",
        "item_attributes": "",
        "qty": total_weight_grams,
        "pcs": total_pcs,
        "design_code": "",
        "item_category": "",
        "item_sub_category": ""
    }
