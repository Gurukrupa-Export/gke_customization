import frappe
from frappe.utils import flt

# Temporary Sales Type as per user request
TEMP_SALES_TYPE = "Finished Goods"

def validate_e_invoice_items(doc):
	"""
	Generates E-Invoice Items in the child table `credit_note_invoice_item`.
	
	Logic Overview:
	1. Identify Payment Terms for the Customer.
	2. Load E-Invoice Item configurations that match the Sales Type.
	3. Loop through return items and their corresponding BOMs.
	4. For each BOM component (Metal, Diamond, etc.), find the matching E-Invoice Item.
	5. Aggregate Quantities and Amounts for each E-Invoice Item.
	6. Populate the child table `credit_note_invoice_item`.
	"""
	
	# --- 1. Validation & Setup ---
	if not doc.customer or not doc.items:
		return

	# Fetch linked Payment Terms
	customer_payment_term_name = frappe.db.get_value("Customer Payment Terms", {"customer": doc.customer}, "name")
	if not customer_payment_term_name:
		return

	payment_terms = frappe.get_doc("Customer Payment Terms", customer_payment_term_name)
	
	# Current Sales Type
	sales_type = doc.sales_type or TEMP_SALES_TYPE 
	
	# Making Charges Logic
	making_charges_multiplier = 1.0 # with
	if doc.making_charges_type == "Half":
		making_charges_multiplier = 0.5 # half
	elif doc.making_charges_type == "Without":
		making_charges_multiplier = 0.0 # without
	
	
	# --- 2. Build Configuration List ---
	# Load all relevant E-Invoice Items configured in Payment Terms 
	# and filter them by the current Sales Type.
	
	e_invoice_config_items = []
	
	for row in payment_terms.customer_payment_details:
		item_type = row.item_type
		
		# Validation: Ensure Master Exists
		if not frappe.db.exists("E Invoice Item", item_type):
			continue

		e_invoice_item = frappe.get_doc("E Invoice Item", item_type)
		
		# Return Material Type Filter
		if doc.return_material_type == "Diamond-Gemstone":
			if not (e_invoice_item.is_for_diamond or e_invoice_item.is_for_gemstone or e_invoice_item.is_for_making):
				continue

			making_charges_multiplier = 0.5 # makeing charge: 50% labour charges as per SOP
		
		# Find settings for current Sales Type (e.g. Tax Rate)
		# We look for a row in the child table 'sales_type' that matches our current sales_type
		matched_sales_type_row = next((st for st in e_invoice_item.sales_type if st.sales_type == sales_type), None)
		
		if not matched_sales_type_row:
			continue

		# Store configuration for easier access later
		e_invoice_config_items.append({
			"item_type": item_type,
			"obj": e_invoice_item,
			"tax_rate": matched_sales_type_row.tax_rate,
			"uom": e_invoice_item.uom,
			
			# Boolean Flags (what does this item represent?)
			"is_for_metal": e_invoice_item.is_for_metal,
			"is_for_hallmarking": e_invoice_item.is_for_hallmarking,
			"is_for_labour": e_invoice_item.is_for_labour,
			"is_for_diamond": e_invoice_item.is_for_diamond,
			"is_for_gemstone": e_invoice_item.is_for_gemstone,
			"is_for_finding": e_invoice_item.is_for_finding,
			"is_for_making": e_invoice_item.is_for_making,
			"is_for_finding_making": e_invoice_item.is_for_finding_making,
			
			# Attributes for Matching
			"metal_type": e_invoice_item.metal_type,
			"metal_purity": e_invoice_item.metal_purity,
			"diamond_type": e_invoice_item.diamond_type,
			"finding_category": e_invoice_item.finding_category,
		})

	# --- 3. Helper Functions ---

	aggregated_data = {} # Stores final totals. Key: (item_code, uom)

	def add_to_aggregate(e_item_config, qty, amount):
		"""
		Accumulates Qty and Amount for a specific E-Invoice Item.
		Calculates Tax immediately.
		"""
		key = (e_item_config["item_type"], e_item_config["uom"])
		
		if key not in aggregated_data:
			# Initialize if new
			aggregated_data[key] = {
				"item_code": e_item_config["item_type"],
				"item_name": e_item_config["item_type"],
				"uom": e_item_config["uom"],
				"qty": 0.0,
				"rate": 0.0,
				"amount": 0.0,
				"tax_rate": e_item_config["tax_rate"],
				"tax_amount": 0.0,
				"amount_with_tax": 0.0,
				"delivery_date": doc.date
			}
		
		entry = aggregated_data[key]
		entry["qty"] += flt(qty)
		entry["amount"] += flt(amount)
		
		# Tax Calculation
		entry["tax_amount"] = entry["amount"] * (entry["tax_rate"] / 100.0)
		entry["amount_with_tax"] = entry["amount"] + entry["tax_amount"]

	def find_e_item_by_criteria(**kwargs):
		"""
		Finds the first E-Invoice configuration that matches ALL provided criteria.
		Usage: find_e_item_by_criteria(is_for_metal=1, metal_type="Gold")
		"""
		for e in e_invoice_config_items:
			match = True
			for key, value in kwargs.items():
				# Careful: Frappe often invokes checks on None vs 0 vs 1.
				# We check exact equality.
				if e.get(key) != value:
					match = False
					break
			if match:
				return e
		return None


	# --- 4. Process Return Items ---
	for item in doc.items:
		if not item.bom:
			continue
			
		bom_doc = frappe.get_doc("BOM", item.bom)
		
		# --- A. Hallmarking ---
		# if bom_doc.hallmarking_amount:
		# 	e_item = find_e_item_by_criteria(is_for_hallmarking=1)
		# 	if e_item:
		# 		add_to_aggregate(e_item, item.qty, flt(bom_doc.hallmarking_amount) * item.qty)

		# --- B. Metal Details ---
		if hasattr(bom_doc, "metal_detail"):
			for metal in bom_doc.metal_detail:
				multiplied_qty = metal.quantity * item.qty
				
				if not metal.is_customer_item:
					# 1. Metal Value
					e_item = find_e_item_by_criteria(
						is_for_metal=1,
						metal_type=metal.metal_type,
						metal_purity=metal.metal_touch,
						uom=metal.stock_uom
					)
					
					if e_item:
						# Special Rate Logic for specific company/customer
						metal_rate = metal.se_rate if (doc.company == "KG GK Jewellers Private Limited" and doc.customer == "GJCU0009") else metal.rate
						add_to_aggregate(e_item, multiplied_qty, metal_rate * multiplied_qty)
					
					# 2. Making Charges (for Metal)
					if not doc.making_charges_type == "Without":
						e_item_making = find_e_item_by_criteria(
							is_for_making=1,
							metal_type=metal.metal_type,
							metal_purity=metal.metal_touch,
							uom=metal.stock_uom
						)
						
						if e_item_making:
							add_to_aggregate(e_item_making, multiplied_qty, metal.making_amount * item.qty * making_charges_multiplier)
						
				else:
					# 3. Labour (Customer Item)
					# Fallback to any Labour item
					e_item_labour = find_e_item_by_criteria(is_for_labour=1)
					if e_item_labour:
						add_to_aggregate(e_item_labour, multiplied_qty, metal.making_rate * multiplied_qty * making_charges_multiplier)

		# --- C. Diamond Details ---
		if hasattr(bom_doc, "diamond_detail"):
			for diamond in bom_doc.diamond_detail:
				multiplied_qty = diamond.quantity * item.qty
				
				if not diamond.is_customer_item:
					# 1. Diamond Value
					e_item = find_e_item_by_criteria(
						is_for_diamond=1,
						diamond_type=diamond.diamond_type,
						uom=diamond.stock_uom
					)
					
					if e_item:
						amt = flt(diamond.diamond_rate_for_specified_quantity) * item.qty
						add_to_aggregate(e_item, multiplied_qty, amt)
				else:
					# 2. Labour (Customer Diamond)
					e_item_labour = find_e_item_by_criteria(is_for_labour=1)
					if e_item_labour:
						amt = flt(diamond.diamond_rate_for_specified_quantity) * item.qty * making_charges_multiplier
						# Note: Divided by 5 as per reference logic
						add_to_aggregate(e_item_labour, multiplied_qty / 5, amt)

		# --- D. Gemstone Details ---
		if hasattr(bom_doc, "gemstone_detail"):
			for gemstone in bom_doc.gemstone_detail:
				multiplied_qty = gemstone.quantity * item.qty
				
				if not gemstone.is_customer_item:
					# 1. Gemstone Value
					e_item = find_e_item_by_criteria(
						is_for_gemstone=1,
						uom=gemstone.stock_uom
					)
					
					if e_item:
						amt = flt(gemstone.gemstone_rate_for_specified_quantity) * item.qty
						add_to_aggregate(e_item, multiplied_qty, amt)
				else:
					# 2. Labour (Customer Gemstone)
					e_item_labour = find_e_item_by_criteria(
						is_for_labour=1,
						uom=gemstone.stock_uom
					)
					
					if e_item_labour:
						amt = flt(gemstone.gemstone_rate_for_specified_quantity) * item.qty * making_charges_multiplier
						add_to_aggregate(e_item_labour, multiplied_qty / 5, amt)

		# --- E. Finding Details ---
		if hasattr(bom_doc, "finding_detail"):
			for finding in bom_doc.finding_detail:
				multiplied_qty = finding.quantity * item.qty
				
				if not finding.is_customer_item:
					finding_handled = False
					
					# 1. Finding Item (Specific Category)
					e_item = find_e_item_by_criteria(
						is_for_finding=1,
						metal_type=finding.metal_type,
						metal_purity=finding.metal_touch,
						uom=finding.stock_uom,
						finding_category=finding.finding_category
					)
					
					if e_item:
						finding_rate = finding.se_rate if (doc.company == "KG GK Jewellers Private Limited" and doc.customer == "GJCU0009") else finding.rate
						add_to_aggregate(e_item, multiplied_qty, finding_rate * multiplied_qty)
						finding_handled = True
					
					# 2. Fallback to Metal Item (if Finding specific item not found)
					if not finding_handled:
						e_item_metal = find_e_item_by_criteria(
							is_for_metal=1,
							metal_type=finding.metal_type,
							metal_purity=finding.metal_touch,
							uom=finding.stock_uom,
							finding_category=None
						)
						
						if e_item_metal:
							finding_rate = finding.se_rate if (doc.company == "KG GK Jewellers Private Limited" and doc.customer == "GJCU0009") else finding.rate
							add_to_aggregate(e_item_metal, multiplied_qty, finding_rate * multiplied_qty)
					
					# 3. Finding Making Charges
					if doc.making_charges_type != "Without":
						e_item_making = find_e_item_by_criteria(
							is_for_finding_making=1,
							metal_type=finding.metal_type,
							metal_purity=finding.metal_touch,
							uom=finding.stock_uom,
							finding_category=finding.finding_category
						)
						
						if e_item_making:
							add_to_aggregate(e_item_making, multiplied_qty, finding.making_rate * multiplied_qty * making_charges_multiplier)
							# frappe.msgprint(f"Finding Making Item: {e_item_making['item_type']} <br> Rate: {finding.making_rate} <br> Qty: {multiplied_qty} <br> Amount: {finding.making_rate * multiplied_qty * making_charges_multiplier}")
						else:
							# Fallback to Metal Making
							e_item_metal_making = find_e_item_by_criteria(
								is_for_making=1,
								metal_type=finding.metal_type,
								metal_purity=finding.metal_touch,
								uom=finding.stock_uom
							)
						
							if e_item_metal_making:
								add_to_aggregate(e_item_metal_making, multiplied_qty, finding.making_rate * multiplied_qty * making_charges_multiplier)
								# frappe.msgprint(f"Finding Making Item (Metal Fallback): {e_item_metal_making['item_type']} <br> Rate: {finding.making_rate} <br> Qty: {multiplied_qty} <br> Amount: {finding.making_rate * multiplied_qty * making_charges_multiplier}")
							# else:
								# frappe.msgprint(f"Finding Making Item not found for {finding.finding_category}")
				else:
					# 4. Labour (Customer Finding)
					e_item_labour = find_e_item_by_criteria(is_for_labour=1)
					if e_item_labour:
						add_to_aggregate(e_item_labour, multiplied_qty, finding.making_rate * multiplied_qty * making_charges_multiplier)

	# --- 5. Populate Child Table ---
	doc.set("credit_note_invoice_item", [])
	
	for key, val in aggregated_data.items():
		if val.get("qty"):
			val["rate"] = val["amount"] / val["qty"]
			# if not val.get("rate"): continue

			doc.append("credit_note_invoice_item", val)
		