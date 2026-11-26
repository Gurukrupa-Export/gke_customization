"""
Faster versions of the portal catalogue list APIs.

The old functions in catalogue_data_api.py are not changed. The portal is
switched to these only after the comparison shows the same results
(see docs/api-fix-plan.md in the portal repo).

Why faster: the old catalogue_data built the variant-count sub-query `vc` for
every item in the catalogue (~240k items) on every call; that was ~80% of the
time. Here the 48 items of the page are found first, and `vc`, `set_check`
and `similar_check` are built for those items only.
"""
import hashlib
import json

import frappe

DEFAULT_COMPANY = "Gurukrupa Export Private Limited"
MAX_ROWS = 48

STAFF_SORT = {
	"creation_ntl": "item.creation DESC, item.item_code ASC",
	"creation_otn": "item.creation ASC, item.item_code ASC",
	"gc_lth": "IFNULL(bom.custom_rating, 0) ASC, item.item_code ASC",
	"gc_htl": "IFNULL(bom.custom_rating, 0) DESC, item.item_code ASC",
}

# Same first-serial rule as the old query: the oldest Serial No of the item.
FIRST_SERIAL_JOIN = """
	INNER JOIN `tabSerial No` AS sn
		ON sn.name = (
			SELECT sn2.name
			FROM `tabSerial No` AS sn2
			WHERE sn2.item_code = item.item_code
			ORDER BY sn2.creation ASC, sn2.name ASC
			LIMIT 1
		)
"""


def _arg(name, value):
	return value if value is not None else frappe.form_dict.get(name)


def _staff_conditions(selectedSubcategory, itemCategory, itemCode, metalType, company, customer, sort_by):
	"""Same WHERE parts as catalogue_data_api.catalogue_data."""
	values = {}
	sub_where = """b.is_active AND i.item_group != 'Design Dnu' AND i.disabled = 0
		AND EXISTS (SELECT 1 FROM `tabSerial No` sn0 WHERE sn0.item_code = i.item_code)"""
	where = "1=1 AND item.item_group != 'Design DNU' AND item.disabled = 0"

	if metalType:
		sub_where += " AND b.metal_type = %(metalType)s"
		where += " AND bom.metal_type = %(metalType)s"
		values["metalType"] = metalType
	if selectedSubcategory:
		sub_where += " AND i.item_subcategory = %(selectedSubcategory)s"
		where += " AND item.item_subcategory = %(selectedSubcategory)s"
		values["selectedSubcategory"] = selectedSubcategory
	if itemCategory:
		sub_where += " AND i.item_category = %(itemCategory)s"
		where += " AND item.item_category = %(itemCategory)s"
		values["itemCategory"] = itemCategory
	if itemCode:
		sub_where += " AND i.item_code = %(itemCode)s"
		where += " AND item.item_code = %(itemCode)s"
		values["itemCode"] = itemCode

	values["company"] = company or DEFAULT_COMPANY
	sub_where += " AND idf3.company = %(company)s"
	where += " AND idf.company = %(company)s"

	if customer:
		wishlist_case = (
			"MAX(CASE WHEN tci.wishlist = 1 AND tcm.wishlist = 1 "
			"AND tcm.customer IS NOT NULL THEN 1 ELSE 0 END) AS wishlist"
		)
		customer_join = "AND tcm.customer = %(customer)s"
		values["customer"] = customer
	else:
		wishlist_case = "0 AS wishlist"
		customer_join = ""

	if sort_by == "Trending":
		where += " AND tci.trending = 1"
		if customer:
			where += " AND tcm.customer = %(customer)s"

	return sub_where, where, values, wishlist_case, customer_join


def _add_multiselect_attributes(rows):
	"""Same post-processing as the old function."""
	codes = [r.item_code for r in rows]
	attr_map = {}
	if codes:
		for r in frappe.db.sql(
			"""
			SELECT parent, parentfield,
			       GROUP_CONCAT(design_attribute ORDER BY design_attribute SEPARATOR ', ') AS design_attributes
			FROM `tabDesign Attribute - Multiselect`
			WHERE parent IN %(codes)s
			GROUP BY parent, parentfield
			""",
			{"codes": tuple(codes)},
			as_dict=True,
		):
			attr_map.setdefault(r.parent, {})[r.parentfield.replace("custom_", "")] = r.design_attributes
	for row in rows:
		row.update(attr_map.get(row.item_code, {}))
		for key in (
			"custom_collection",
			"custom_language",
			"custom_zodiac",
			"custom_animalbirds",
			"custom_alphabetnumber",
			"religious",
		):
			row[key] = row.get(key) or None


@frappe.whitelist()  # no allow_guest: only logged-in users
def catalogue_data(
	selectedSubcategory=None,
	itemCategory=None,
	itemCode=None,
	metalType=None,
	company=None,
	customer=None,
	page=None,
	page_size=48,
	is_filter=None,
	search=None,
	sort_by=None,
):
	page = _arg("page", page)
	if page is None:
		return {"data": []}

	page = max(int(page), 1)
	page_size = int(_arg("page_size", page_size) or 48)
	offset = (page - 1) * page_size

	sub_where, where, values, wishlist_case, customer_join = _staff_conditions(
		_arg("selectedSubcategory", selectedSubcategory),
		_arg("itemCategory", itemCategory),
		_arg("itemCode", itemCode),
		_arg("metalType", metalType),
		company,
		customer,
		sort_by,
	)

	if int(_arg("is_filter", is_filter) or 0) == 1:
		data, total_count = _filter_page(
			search, values, wishlist_case, sub_where, customer_join, where,
			STAFF_SORT.get(sort_by) or "item.creation DESC",
			page_size, offset, company_given=bool(company),
		)
		return {
			"data": data,
			"total_count": total_count,
			"page": page,
			"page_size": page_size,
			"has_more": (offset + page_size) < total_count,
		}
	order_by = STAFF_SORT.get(sort_by) or "item.item_code ASC"

	# ---- Step 1: which items are on this page (same rules as the old list) ----
	list_from = f"""
		FROM `tabItem` AS item
		INNER JOIN (
			SELECT IFNULL(i.variant_of, i.item_code) AS group_key,
			       MIN(i.item_code) AS first_item_code
			FROM `tabItem` AS i
			INNER JOIN `tabBOM` AS b ON i.item_code = b.item
			INNER JOIN `tabItem Default` AS idf3 ON i.item_name = idf3.parent
			WHERE {sub_where}
			GROUP BY IFNULL(i.variant_of, i.item_code)
		) AS first_variant ON item.item_code = first_variant.first_item_code
		{FIRST_SERIAL_JOIN}
		LEFT JOIN `tabCataloge Item Details` AS tci ON tci.item_code = item.name
		LEFT JOIN `tabCataloge Master` AS tcm ON tcm.name = tci.parent {customer_join}
		LEFT JOIN `tabBOM` AS bom ON bom.name = sn.custom_bom_no
		LEFT JOIN `tabItem Default` AS idf ON item.item_name = idf.parent
		WHERE {where}
	"""
	page_rows = frappe.db.sql(
		f"""
		SELECT item.item_code, item.variant_of
		{list_from}
		GROUP BY item.item_code, item.variant_of
		ORDER BY {order_by}
		LIMIT %(limit)s OFFSET %(offset)s
		""",
		{**values, "limit": min(page_size, MAX_ROWS), "offset": offset},
		as_dict=True,
	)

	# Count with the same rules as the list.
	total_count = frappe.db.sql(f"SELECT COUNT(DISTINCT item.item_code) {list_from}", values)[0][0]

	result = {
		"data": [],
		"filters": None,
		"total_count": total_count,
		"page": page,
		"page_size": page_size,
		"has_more": (offset + page_size) < total_count,
	}
	if not page_rows:
		return result

	# ---- Step 2: full details for these items only ----
	codes = tuple(r.item_code for r in page_rows)
	# Same key as the old vc join: COALESCE(variant_of, item_code). Keep '' as ''.
	group_keys = tuple({r.variant_of if r.variant_of is not None else r.item_code for r in page_rows})

	rows = frappe.db.sql(
		f"""
		SELECT
			item.name,
			bom.name,
			bom.sub_setting_type1,
			idf.company,
			tci.trending,
			tci.name as catalog_item_details_name,
			{wishlist_case},
			item.creation,
			item.item_code,
			sn.name AS serial_no,
			sn.creation AS serial_creation,
			sn.status AS serial_status,
			sn.custom_bom_no AS serial_bom_no,
			item.item_category,
			item.image,
			item.sketch_image,
			item.custom_catalogue_image,
			item.custom_silver_image,
			item.front_view AS cad_image,
			CASE
				WHEN item.front_view = item.image THEN 'CAD Image'
				ELSE 'FG Image'
			END AS image_remark,
			item.item_subcategory,
			item.stylebio,
			bom.tag_no,
			bom.diamond_quality,
			item.setting_type,

			FORMAT(bom.gross_weight, 3) AS gross_metal_weight,
			FORMAT(bom.metal_and_finding_weight, 3) AS net_metal_finding_weight,
			FORMAT(bom.total_diamond_weight_in_gms, 3) AS total_diamond_weight_in_gms,
			FORMAT(bom.other_weight, 3) AS other_weight,
			FORMAT(bom.finding_weight, 3) AS finding_weight_,

			bom.metal_colour,
			bom.metal_touch,
			bom.metal_purity,
			FORMAT(bom.total_gemstone_weight_in_gms, 3) AS total_gemstone_weight_in_gms,

			bom.total_diamond_pcs,
			bom.total_gemstone_pcs,
			FORMAT(bom.gemstone_weight, 3) AS gemstone_weight,

			FORMAT(bom.gold_to_diamond_ratio, 3) AS gold_diamond_ratio,
			FORMAT(bom.diamond_ratio, 3) AS diamond_ratio,
			FORMAT(bom.metal_to_diamond_ratio_excl_of_finding, 3) AS metal_diamond_ratio,

			bom.navratna,
			bom.lock_type,
			bom.feature,
			bom.enamal,
			bom.rhodium,
			bom.sizer_type,

			bom.height,
			bom.length,
			bom.width,
			bom.breadth,
			bom.product_size,

			bom.design_style,
			bom.nakshi_from,
			bom.vanki_type,
			bom.total_length,
			bom.detachable,
			bom.back_side_size,
			bom.changeable,

			item.variant_of,

			CASE
				WHEN vc.variant_count > 1 THEN 1
				ELSE 0
			END AS rn,

			CASE
				WHEN item.custom_is_set_item = 1 AND set_check.is_set_item = 1 THEN 1
				ELSE 0
			END AS is_set_item,

			CASE
				WHEN item.custom_is_similar_item = 1 AND similar_check.is_similar_item = 1 THEN 1
				ELSE 0
			END AS is_similar_item,

			bom.finding_pcs,
			bom.total_other_pcs,
			bom.total_other_weight,
			bom.custom_rating AS rating,

			GROUP_CONCAT(DISTINCT item.name ORDER BY item.creation ASC) AS variant_name,

			GROUP_CONCAT(DISTINCT td.design_attributes) AS design_attributes,
			GROUP_CONCAT(DISTINCT td.design_attribute_value_1) AS design_attributes_1,

			GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
			GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
			GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
			GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,

			GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
			GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
			GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
			GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm, 3)) AS size_in_mm,
			GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,

			GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
			GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
			GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size, 3)) AS finding_size
		FROM `tabItem` AS item

		LEFT JOIN (
			SELECT
				COALESCE(i.variant_of, i.item_code) AS group_key,
				COUNT(DISTINCT i.item_code) AS variant_count
			FROM `tabItem` AS i
			INNER JOIN `tabItem Default` AS idf3
				ON i.item_name = idf3.parent
				AND idf3.company = 'Gurukrupa Export Private Limited'
			WHERE
				i.item_group != 'Design DNU'
				AND i.disabled = 0
				AND (i.item_code IN %(group_keys)s OR i.variant_of IN %(group_keys)s)
				AND EXISTS (
					SELECT 1
					FROM `tabSerial No` AS s
					INNER JOIN `tabBOM` AS b ON b.name = s.custom_bom_no
					WHERE s.item_code = i.item_code
				)
			GROUP BY COALESCE(i.variant_of, i.item_code)
		) vc ON vc.group_key = COALESCE(item.variant_of, item.item_code)

		LEFT JOIN (
			SELECT
				sit.parent AS item_code,
				1 AS is_set_item
			FROM `tabSet Item Table` sit
			WHERE sit.parenttype = 'Item'
			  AND sit.parentfield = 'custom_set_item_table'
			  AND sit.parent IN %(codes)s
			  AND EXISTS (
				  SELECT 1
				  FROM `tabSerial No` AS s
				  INNER JOIN `tabBOM` AS b ON b.name = s.custom_bom_no
				  WHERE s.item_code = sit.item_code
			  )
			GROUP BY sit.parent
		) AS set_check ON set_check.item_code = item.item_code

		LEFT JOIN (
			SELECT
				sit.parent AS item_code,
				1 AS is_similar_item
			FROM `tabSimilar Item Table` sit
			WHERE sit.parenttype = 'Item'
			  AND sit.parentfield = 'custom_similar_item_table'
			  AND sit.parent IN %(codes)s
			  AND EXISTS (
				  SELECT 1
				  FROM `tabSerial No` AS s
				  INNER JOIN `tabBOM` AS b ON b.name = s.custom_bom_no
				  WHERE s.item_code = sit.item_code
			  )
			GROUP BY sit.parent
		) AS similar_check ON similar_check.item_code = item.item_code

		{FIRST_SERIAL_JOIN}
		LEFT JOIN `tabCataloge Item Details` AS tci ON tci.item_code = item.name
		LEFT JOIN `tabCataloge Master` AS tcm ON tcm.name = tci.parent {customer_join}
		LEFT JOIN `tabBOM` AS bom ON bom.name = sn.custom_bom_no
		LEFT JOIN `tabDesign Attributes` AS td ON item.item_code = td.parent
		LEFT JOIN `tabBOM Metal Detail` AS mt ON bom.name = mt.parent
		LEFT JOIN `tabBOM Diamond Detail` AS dd ON bom.name = dd.parent
		LEFT JOIN `tabBOM Finding Detail` AS fd ON bom.name = fd.parent
		LEFT JOIN `tabItem Default` AS idf ON item.item_name = idf.parent

		WHERE {where} AND item.item_code IN %(codes)s
		GROUP BY item.item_code, item.variant_of
		""",
		{**values, "codes": codes, "group_keys": group_keys},
		as_dict=True,
	)

	# Keep the page order from step 1.
	position = {code: n for n, code in enumerate(codes)}
	rows.sort(key=lambda r: position[r.item_code])
	_add_multiselect_attributes(rows)

	result["data"] = rows
	return result


# ---------------------------------------------------------------------------
# Filter / search path (is_filter=1)
#
# Same results as catalogue_data_api.get_is_filter, which (1) matched the search
# against every item with a correlated "first serial" sub-query per item, then
# (2) built every matching item in full, with variant/set checks and an attribute
# pivot over the whole catalogue, and kept one page in Python (5-10 s).
# Here the first serial of each item is computed once, the page is chosen with
# LIMIT, and the details are built for that page only.
# ---------------------------------------------------------------------------

# Oldest Serial No per item: same rule as the old correlated
# "WHERE item_code = ... ORDER BY creation ASC, name ASC LIMIT 1".
FIRST_SERIAL_TABLE = """(
	SELECT fs0.name, fs0.item_code, fs0.creation, fs0.status, fs0.custom_bom_no
	FROM (
		SELECT name, item_code, creation, status, custom_bom_no,
		       ROW_NUMBER() OVER (PARTITION BY item_code ORDER BY creation ASC, name ASC) AS rn
		FROM `tabSerial No`
		WHERE item_code IS NOT NULL
	) fs0
	WHERE fs0.rn = 1
)"""

def _first_serial(alias, item_expr):
	"""Join the oldest Serial No of one item (for steps that touch only a few items)."""
	return f"""INNER JOIN `tabSerial No` AS {alias} ON {alias}.name = (
		SELECT fs1.name FROM `tabSerial No` AS fs1
		WHERE fs1.item_code = {item_expr}
		ORDER BY fs1.creation ASC, fs1.name ASC
		LIMIT 1
	)"""


MULTISELECT_FIELDS = (
	"custom_collection", "custom_language", "custom_zodiac", "custom_animalbirds",
	"custom_alphabetnumber", "custom_religious", "custom_age_group", "custom_gender",
	"custom_design_style", "custom_rhodium", "custom_occasion",
)


def _filter_page(search, values, wishlist_case, sub_where, customer_join, where, order_by,
                 page_size, offset, company_given):
	if not search:
		return [], 0
	terms = [x.strip() for x in search.split(",") if x.strip()]
	if not terms:
		return [], 0
	values = dict(values)

	# ---- Step 1: designs matching every search term (same rules as the old code) ----
	conditions = []
	for i, term in enumerate(terms):
		values[f"search_{i}"] = f"%{term}%"
		values[f"exact_search_{i}"] = term
		conditions.append(f"""(
			item.item_category LIKE %(search_{i})s
			OR item.item_subcategory LIKE %(search_{i})s
			OR item.setting_type LIKE %(search_{i})s
			OR bom.sub_setting_type1 LIKE %(search_{i})s
			OR bom.metal_touch LIKE %(search_{i})s
			OR bom.metal_colour LIKE %(search_{i})s
			OR bom.diamond_quality LIKE %(search_{i})s
			OR bom.design_style LIKE %(search_{i})s
			OR bom.rhodium LIKE %(search_{i})s
			OR dam.design_attribute = %(exact_search_{i})s
		)""")
	if "Open" in terms:
		setting_filter = "AND bom.sub_setting_type1 != 'Close-Open Setting'"
	elif "Close-Open Setting" in terms:
		setting_filter = "AND bom.sub_setting_type1 = 'Close-Open Setting' AND item.setting_type = 'Open'"
	elif "Nova Glow" in terms:
		setting_filter = "AND item.setting_type = 'Nova Glow'"
	else:
		setting_filter = ""

	match_sql = f"""
		SELECT DISTINCT IFNULL(item.variant_of, item.item_code), item.item_name
		FROM `tabItem` item
		INNER JOIN {FIRST_SERIAL_TABLE} sn ON sn.item_code = item.item_code
		INNER JOIN `tabBOM` bom ON bom.name = sn.custom_bom_no
		LEFT JOIN `tabItem Default` idf ON idf.parent = item.item_name
		LEFT JOIN `tabDesign Attribute - Multiselect` dam ON dam.parent = item.item_code
		WHERE 1=1
			{"AND idf.company = %(company)s" if company_given else ""}
			AND ({" AND ".join(conditions)})
			{setting_filter}
	"""
	# The match covers the whole catalogue (~0.5 s) and is the same for every page
	# of a search, so it is kept for 5 minutes (like the category counts).
	match_args = {k: v for k, v in values.items() if k.startswith(("search_", "exact_search_"))}
	if company_given:
		match_args["company"] = values["company"]
	cache_key = "portal_filter_match_" + hashlib.sha1(
		json.dumps([match_sql, match_args], sort_keys=True).encode()
	).hexdigest()
	matched = frappe.cache().get_value(cache_key)
	if matched is None:
		matched = [list(r) for r in frappe.db.sql(match_sql, values)]
		frappe.cache().set_value(cache_key, matched, expires_in_sec=300)
	if not matched:
		return [], 0
	values["item_codes"] = tuple({r[0] for r in matched})
	values["item_name"] = tuple({r[1] for r in matched})
	where += """
		AND item.item_name IN %(item_name)s
		AND IFNULL(item.variant_of, item.item_code) IN %(item_codes)s
	"""

	# ---- Step 2: which items are on this page, and how many in total ----
	list_from = f"""
		FROM `tabItem` item
		INNER JOIN (
			SELECT IFNULL(i.variant_of, i.item_code) AS group_key, MIN(i.item_code) AS first_item_code
			FROM `tabItem` i
			INNER JOIN `tabBOM` b ON i.item_code = b.item
			INNER JOIN `tabItem Default` idf3 ON i.item_name = idf3.parent
			WHERE {sub_where}
			GROUP BY IFNULL(i.variant_of, i.item_code)
		) first_variant ON item.item_code = first_variant.first_item_code
		LEFT JOIN `tabCataloge Item Details` tci ON tci.item_code = item.name
		LEFT JOIN `tabCataloge Master` tcm ON tcm.name = tci.parent {customer_join}
		{_first_serial("sn", "item.item_code")}
		LEFT JOIN `tabBOM` bom ON bom.name = sn.custom_bom_no
		LEFT JOIN `tabItem Default` idf ON item.item_name = idf.parent
		WHERE {where}
	"""
	# Tie-breaker so pages never overlap or skip items with equal sort values.
	stable_order = order_by if "item_code" in order_by else f"{order_by}, item.item_code ASC"
	page_rows = frappe.db.sql(
		f"""
		SELECT item.item_code, item.variant_of
		{list_from}
		GROUP BY item.item_code
		ORDER BY {stable_order}
		LIMIT %(limit)s OFFSET %(offset)s
		""",
		{**values, "limit": page_size, "offset": offset},
		as_dict=True,
	)
	count_sql = f"SELECT COUNT(DISTINCT item.item_code) {list_from}"
	count_key = "portal_filter_count_" + hashlib.sha1(
		json.dumps([count_sql, values], sort_keys=True, default=str).encode()
	).hexdigest()
	total_count = frappe.cache().get_value(count_key)
	if total_count is None:
		total_count = frappe.db.sql(count_sql, values)[0][0]
		frappe.cache().set_value(count_key, total_count, expires_in_sec=300)
	if not page_rows:
		return [], total_count

	# ---- Step 3: full details for this page only ----
	codes = tuple(r.item_code for r in page_rows)
	group_keys = tuple({r.variant_of if r.variant_of is not None else r.item_code for r in page_rows})
	pivot = ",\n".join(
		f"GROUP_CONCAT(CASE WHEN dam.parentfield='{f}' THEN dam.design_attribute END) AS {f}"
		for f in MULTISELECT_FIELDS
	)
	rows = frappe.db.sql(
		f"""
		SELECT
			item.name,
			bom.name AS bom_name,
			bom.sub_setting_type1,
			idf.company,
			tci.trending,
			tci.name AS catalog_item_details_name,
			{wishlist_case},
			item.creation,
			item.item_code,
			item.item_category,
			sn.name AS serial_no,
			sn.creation AS serial_creation,
			sn.status AS serial_status,
			sn.custom_bom_no AS serial_bom_no,
			item.image,
			item.sketch_image,
			item.custom_catalogue_image,
			item.custom_silver_image,
			item.front_view AS cad_image,
			CASE WHEN item.front_view = item.image THEN 'CAD Image' ELSE 'FG Image' END AS image_remark,
			item.item_subcategory,
			item.stylebio,
			bom.tag_no,
			bom.diamond_quality,
			item.setting_type,
			FORMAT(bom.gross_weight,3) AS gross_metal_weight,
			FORMAT(bom.metal_and_finding_weight,3) AS net_metal_finding_weight,
			FORMAT(bom.total_diamond_weight_in_gms,3) AS total_diamond_weight_in_gms,
			FORMAT(bom.other_weight,3) AS other_weight,
			FORMAT(bom.finding_weight_,3) AS finding_weight_,
			bom.metal_colour,
			bom.metal_touch,
			bom.metal_purity,
			FORMAT(bom.total_gemstone_weight_in_gms,3) AS total_gemstone_weight_in_gms,
			bom.total_diamond_pcs,
			bom.total_gemstone_pcs,
			FORMAT(bom.gemstone_weight,3) AS gemstone_weight,
			FORMAT(bom.gold_to_diamond_ratio,3) AS gold_diamond_ratio,
			FORMAT(bom.diamond_ratio,3) AS diamond_ratio,
			FORMAT(bom.metal_to_diamond_ratio_excl_of_finding,3) AS metal_diamond_ratio,
			bom.navratna, bom.lock_type, bom.feature, bom.enamal, bom.rhodium, bom.sizer_type,
			bom.height, bom.length, bom.width, bom.breadth, bom.product_size,
			bom.design_style, bom.nakshi_from, bom.vanki_type, bom.total_length,
			bom.detachable, bom.back_side_size, bom.changeable,
			item.variant_of,
			CASE WHEN vc.variant_count > 1 THEN 1 ELSE 0 END AS rn,
			CASE WHEN item.custom_is_set_item = 1 AND set_check.is_set_item = 1 THEN 1 ELSE 0 END AS is_set_item,
			CASE WHEN item.custom_is_similar_item = 1 AND similar_check.is_similar_item = 1 THEN 1 ELSE 0 END AS is_similar_item,
			bom.finding_pcs,
			bom.total_other_pcs,
			bom.total_other_weight,
			bom.custom_rating AS rating,
			GROUP_CONCAT(DISTINCT item.name ORDER BY item.creation ASC) AS variant_name,
			GROUP_CONCAT(DISTINCT mt.metal_type) AS metal_types,
			GROUP_CONCAT(DISTINCT mt.metal_colour) AS metal_color,
			GROUP_CONCAT(DISTINCT mt.metal_purity) AS metal_purities,
			GROUP_CONCAT(DISTINCT mt.metal_touch) AS metal_touch,
			GROUP_CONCAT(DISTINCT gd.stone_shape) AS gemstone_shape,
			GROUP_CONCAT(DISTINCT gd.cut_or_cab) AS cut_or_cab,
			GROUP_CONCAT(DISTINCT dd.stone_shape) AS diamond_stone_shape,
			GROUP_CONCAT(DISTINCT dd.sub_setting_type) AS diamond_setting_type,
			GROUP_CONCAT(DISTINCT dd.diamond_sieve_size) AS diamond_sieve_size,
			GROUP_CONCAT(DISTINCT FORMAT(dd.size_in_mm,3)) AS size_in_mm,
			GROUP_CONCAT(DISTINCT dd.sieve_size_range) AS sieve_size_range,
			GROUP_CONCAT(DISTINCT fd.finding_type) AS finding_sub_category,
			GROUP_CONCAT(DISTINCT fd.finding_category) AS finding_category,
			GROUP_CONCAT(DISTINCT FORMAT(fd.finding_size,3)) AS finding_size,
			{", ".join(f"dam_pivot.{f}" for f in MULTISELECT_FIELDS)}
		FROM `tabItem` item
		LEFT JOIN (
			SELECT COALESCE(i.variant_of, i.item_code) AS group_key, COUNT(DISTINCT i.item_code) AS variant_count
			FROM `tabItem` AS i
			INNER JOIN `tabItem Default` AS idf3
				ON i.item_name = idf3.parent AND idf3.company = 'Gurukrupa Export Private Limited'
			{_first_serial("sn3", "i.item_code")}
			INNER JOIN `tabBOM` AS b ON b.name = sn3.custom_bom_no
			WHERE i.item_group != 'Design DNU'
			  AND i.disabled = 0
			  AND (i.item_code IN %(group_keys)s OR i.variant_of IN %(group_keys)s)
			GROUP BY COALESCE(i.variant_of, i.item_code)
		) vc ON vc.group_key = COALESCE(item.variant_of, item.item_code)
		LEFT JOIN (
			SELECT sit.parent AS item_code, 1 AS is_set_item
			FROM `tabSet Item Table` sit
			{_first_serial("sn5", "sit.item_code")}
			INNER JOIN `tabBOM` AS b2 ON b2.name = sn5.custom_bom_no
			WHERE sit.parenttype = 'Item'
			  AND sit.parentfield = 'custom_set_item_table'
			  AND sit.parent IN %(codes)s
			GROUP BY sit.parent
		) AS set_check ON set_check.item_code = item.item_code
		LEFT JOIN (
			SELECT sit.parent AS item_code, 1 AS is_similar_item
			FROM `tabSimilar Item Table` sit
			WHERE sit.parenttype = 'Item'
			  AND sit.parentfield = 'custom_similar_item_table'
			  AND sit.parent IN %(codes)s
			  AND EXISTS (
				  SELECT 1 FROM `tabSerial No` AS s
				  INNER JOIN `tabBOM` AS b ON b.name = s.custom_bom_no
				  WHERE s.item_code = sit.item_code
			  )
			GROUP BY sit.parent
		) AS similar_check ON similar_check.item_code = item.item_code
		LEFT JOIN `tabCataloge Item Details` tci ON tci.item_code = item.name
		LEFT JOIN `tabCataloge Master` tcm ON tcm.name = tci.parent {customer_join}
		{_first_serial("sn", "item.item_code")}
		LEFT JOIN `tabBOM` bom ON bom.name = sn.custom_bom_no
		LEFT JOIN `tabBOM Metal Detail` mt ON bom.name = mt.parent
		LEFT JOIN `tabBOM Gemstone Detail` gd ON bom.name = gd.parent
		LEFT JOIN `tabBOM Diamond Detail` dd ON bom.name = dd.parent
		LEFT JOIN `tabBOM Finding Detail` fd ON bom.name = fd.parent
		LEFT JOIN `tabItem Default` idf ON item.item_name = idf.parent
		LEFT JOIN (
			SELECT dam.parent, {pivot}
			FROM `tabDesign Attribute - Multiselect` dam
			WHERE dam.parent IN %(codes)s
			GROUP BY dam.parent
		) dam_pivot ON dam_pivot.parent = item.item_code
		WHERE {where} AND item.item_code IN %(codes)s
		GROUP BY item.item_code
		""",
		{**values, "codes": codes, "group_keys": group_keys},
		as_dict=True,
	)
	position = {code: n for n, code in enumerate(codes)}
	rows.sort(key=lambda r: position[r.item_code])
	return rows, total_count
