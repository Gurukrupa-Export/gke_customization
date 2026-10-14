# 03 — Feature parity matrix

One row per production change (unit) plus the master-only feature groups. Columns follow the brief: ✅ present, ❌ absent, *newer* = master carries a newer version of the same behaviour, *reverted* = added and reverted on that branch. *Final status* links to the migration-branch commits for ported rows. Manufacturing relevance comes from the manufacturing lens of the classification (impact other than none).

## Manufacturing-related

| Feature | master | kggk_prod | gurukrupa-prod | Required in gk_prod | Source commits | Final status |
|---|:-:|:-:|:-:|:-:|---|---|
| Order: Reformats order.py and order_form.py from tabs to 4-space black style and refactors their logic. | ❌ | ✅ | ✅ | ✅ | `398707865a` #631 | ported → `48639f4` |
| Order: GC Ratio (the child table of GC Ratio Master) gets structured Type (Range/Above/Below), Range 1 and Range 2 fields, and its text… | ❌ | ✅ | ✅ | ✅ | `2f041b5969` #644 | ported → `71f72ef` `48639f4` |
| Patches: Registers gke_customization.patches.gc_ration_master in the previously empty patches.txt. | ❌ | ✅ | ✅ | ✅ | `a01ead8785` #645 | ported → `083c594` |
| Order: Adds GC Ratio Master.validate. | ❌ | ✅ | ✅ | ✅ | `c003e91b41` #646 | ported → `86232cd` |
| Order: make_quotation_batch now clears the Quotation's existing item rows before adding one row per selected Order. | ❌ | ✅ | ✅ | partial | `549b99bf40` #650 | ported (partial) → `48639f4` `ed24d61` |
| Order Form: Follow-up to the #631 refactor. | newer | ✅ | ✅ | master's version | `7de53ba167` #653 | superseded |
| Stock and inventory reports: Converts the standard report 'Warehouse wise Consumable Consumption' from Script Report to Query Report. | newer | ✅ | ✅ | master's version | `e7d0b7dbf9` | superseded |
| Order Form: A large Order Form update with these parts: - Customer-specific Excel export buttons on submitted Order Forms: GC format, code cr… | ❌ | ✅ | ✅ | ✅ | `9f3433b271` #749 | ported → `e673fd9` `083c594` `48639f4` |
| Price List and Revise Price: The Revise Gemstone Price List JSON gains multiplier tables, handling-charge fields, a PR-rate range, effective-from and grade fi… | ❌ | ✅ | ✅ | partial | `f946dc8b4e` #746 | ported (partial) → `47465ae` `6934d29` |
| Item and BOM creation and KGGK replication: Removes the trailing commas that made Item.item_group a tuple in create_item_template_from_order ('<subcategory> - T') and create… | ❌ | ✅ | ✅ | ✅ | `2bb0e3ccb1` #750 | ported → `48639f4` |
| Item and BOM creation and KGGK replication: Applies the same tuple-to-string item_group fix in create_only_variant_from_order, create_sufix_of_variant_template_from_order an… | ❌ | ✅ | ✅ | ✅ | `254f25877f` #752 | ported → `48639f4` |
| Order: Removes the stray third positional argument from frappe.get_doc('Timesheet', {'order': ...}, 'name') in Order.on_update_after_sub… | ✅ | ✅ | ✅ | ✅ | `3aa12e00e1` #758 | retained (already in master) |
| Order Form: Adds three Order Form Detail fields: jewelex_design_id (mandatory for Sketch Design), design_sourceroute (Curated/Co-Created/Desi… | ❌ | ✅ | ✅ | ✅ | `49a4c3da9c` #759 | ported → `48639f4` |
| Order: Changes create_bom_timesheet. | ❌ | ✅ | ✅ | ✅ | `0868e53bf7` #760 | ported → `48639f4` |
| Order Form: One-line guard in Order Form gc_export_to_excel, SET-item branch: write '' when no Customer RM Code Detail row matches instead of… | newer | ✅ | ✅ | master's version | `5ac322b67e` #762 | superseded |
| Order Form: Adds Float field sketch_approval_day to child DocType Order Criteria Table, a kggk-only MECH path. | ❌ | ✅ | ✅ | ✅ | `8effcc39a3` #763 | ported → `81de021` `48639f4` |
| Gold Rates: Fixes Gold Rates.set_gold_value, which wrote the first bullion feed's live rate to a misspelt key ('live_.rate' changed to 'live_… | ❌ | ✅ | ✅ | ✅ | `e6973785dd` #764 | ported → `64f15cf` `48639f4` |
| Order Form: Order Form exports: gc_export_to_excel and creation_export_to_excel skip Earrings rows that belong to a SET (uomset_of = SET). | ❌ | ✅ | ✅ | ✅ | `19f1882756` #770 | ported → `48639f4` |
| Packaging and config: Reformats hooks.py to the v16 app template: black-style layout and trailing commas, `from . | ❌ | ✅ | ✅ | partial | `5709d9cfde` #769 | ported (partial) → `083c594` |
| Order Form: Rewrites the whitelisted get_customer_order_form, which maps a Customer Order Form into an Order Form. | ❌ | ✅ | ✅ | ✅ | `5cf65cd5ac` #772 | ported → `48639f4` |
| Order Form: In get_design_creation, the BOM Finding Detail chain-weight lookup now filters parent by final_bom.name. | ❌ | ✅ | ✅ | ✅ | `faa55e2c8b` #774 | ported → `48639f4` |
| Order Form: Adds a customer-specific 'Get Cost Sheet' Excel export for submitted Order Forms: a JS button under Get File plus the whitelisted… | ❌ | ✅ | ✅ | ✅ | `3be028bdc8` #792 | ported → `c3ab935` `48639f4` |
| Gold Rates: Gold Rates: replaces the hand-rolled socket.io client in get_live_gold_rate, which feeds row 5, with a websocket-client SignalR c… | ❌ | ✅ | ✅ | ✅ | `4734bd2f40` #799 | ported → `117e4db` |
| Gold Rates: Disables the row-5 live-rate fetcher: set_gold_value_6 calls are commented out in run_gold_rate_scheduler and validate, and the w… | ❌ | ✅ | ✅ | ✅ | `f74d9a1610` #808 | ported → `3991b28` |
| Fixtures: Replaces fixtures/custom_field.json (5 rows -> 2084) and fixtures/doctype.json (1 custom DocType -> 51) with a full dump taken fr… | ❌ | ✅ | ✅ | partial | `c6b22dadd7` #809 | ported (partial) → `26bfda3` |
| Diamond and Gemstone pricing: Adds the child DocType Diamond Price List Table under GKE Order Forms. | ✅ | ✅ | ✅ | ✅ | `fa7ea703a5` #810 | retained (already in master) |
| Making charges: Revise Making Charge Price: before_save becomes before_insert. | ✅ | ✅ | ✅ | ✅ | `b0b2aeec21` #817 | retained (already in master) |
| Diamond and Gemstone pricing: Revise Diamond Price List crate_price_list now writes stone_code and the outright/outwork handling-charge percentage and rate und… | ✅ | ✅ | ✅ | ✅ | `d25f9f1688` #819 | retained (already in master) |
| Making charges: Restores the Revise Making Charge Price DocType JSON to a consistent submittable parent: customer, setting type, metal type and t… | ✅ | ✅ | ✅ | ✅ | `93da164324` #822 | retained (already in master) |
| Sales and HR reports: Adds four GKE Catalog script reports: Sales Invoice Detail Report (per invoice line BOM-derived metal/pure/diamond/gemstone/other… | ❌ | ✅ | ✅ | ✅ | `10f0cfa68e` #823 | ported → `5ff3d31` `be7e82f` `20e246a` `14793d7` `7ae741e` `8ae4219` `8eff717` `ade6ff3` |
| Price List and Revise Price: Renames the submittable DocType 'Revise Diamond Price List' (double space, folder revise_diamond_price__list) to 'Revise Diamond… | ❌ | ✅ | ✅ | ✅ | `d5541c6535` #825 | ported → `687a7dc` `6934d29` |
| Manufacturing reports: Branch Stock Summary JS gets dark-theme-aware styling, more robust View-details button handlers and a new 'Aloy' raw-material opt… | ❌ | ✅ | ✅ | ✅ | `5c19380b01` #833 | ported → `f36d428` |
| Product Return Order: Adds the Product Return Form doctype and flow (return of sold pieces: fetch sales BOM and invoice by serial, re-rate the BOM at i… | newer | ✅ | ✅ | master's version | `bcb4b9c1cc` #835 | superseded |
| Manufacturing reports: Adds Mould Report: for one required MWO, lists every Mould whose design references include the MWO's item, with mould no, rake/tr… | ❌ | ✅ | ✅ | ✅ | `c673ca33ff` #840 | ported → `0fbc6c7` `0ed99a0` |
| Manufacturing reports: Removes the 'Allow Loss' column (commented out) and the 'mo.allowed_loss_percentage as allow_loss' select from 'Employee issue re… | ❌ | ✅ | ✅ | ✅ | `efd81fa2d1` #841 | ported → `68a971d` |
| Sales Order, Delivery Note and Invoice hooks: Adds an explicit 'bom': 'bom' field mapping to gke's overridden Sales Order -> Delivery Note mapper (make_delivery_note) and to g… | ❌ | ✅ | ✅ | ✅ | `c6fdce26f2` | ported → `965a95d` `ed24d61` |
| Making charges: Appends whitelisted get_making_charge(customer, metal_type, setting_type, gold_rate, metal_touch, subcategory) to gke_order_forms… | ❌ | ✅ | ✅ | ✅ | `020d9624e0` #856 | ported → `ed24d61` |
| Making charges: Appends whitelisted get_finding_charge(parent, subcategory) and get_making_charge_price(parent, subcategory) to item.py: given a… | ❌ | ✅ | ✅ | ✅ | `057fbac944` #858 | ported → `ed24d61` |
| Diamond and Gemstone pricing: Adds 'parent' to get_making_charge's returned fields and appends whitelisted get_diamond_rate(customer, diamond_type, stone_shape… | ❌ | ✅ | ✅ | ✅ | `b140da522c` #861 | ported → `ed24d61` |
| Diamond and Gemstone pricing: Appends whitelisted get_fixed_retail_rate(...) (Fixed per-customer or Retail gemstone price row by per-pc/per-carat, cut/cab, typ… | ❌ | ✅ | ✅ | ✅ | `a887b4c45e` #862 | ported → `ed24d61` |
| Repair Order: Repair Order / Repair Order Form updates: CAD order form gets total_rows=1 and 'New Design' design type, slash-stripping of attri… | ✅ | ✅ | ✅ | ✅ | `4c231fda6b` #864 | retained (already in master) |
| Item and BOM creation and KGGK replication: Adds create_item_kggk and create_bom_kggk to gke_order_forms/doc_events/item.py and wires them as Item and BOM before_validate ho… | ✅ | ✅ | ✅ | ✅ | `c72dab2608` #867 | retained (already in master) |
| Repair Order: Repair Order changes. | ✅ | ✅ | ✅ | ✅ | `0ccb08995b` #869 | retained (already in master) |
| Item and BOM creation and KGGK replication: Adds 'import requests' at the top of doc_events/item.py. | ✅ | ✅ | ✅ | ✅ | `1d04e98ba8` #871 | retained (already in master) |
| Repair Order: Two small changes. | ✅ | ✅ | ✅ | ✅ | `7a1ea3d7b8` #872 | retained (already in master) |
| Item and BOM creation and KGGK replication: Temporarily switches off KGGK replication. | newer | ✅ | ✅ | master's version | `aebd145e48` #873 | superseded |
| Repair Order: Removes a trailing comma in Repair Order create_item_template_from_order, so Item.item_group is set to a string instead of a 1-tu… | newer | ✅ | ✅ | master's version | `43fddcb04c` #874 | superseded |
| Order: Order.create_item_template_from_order post_process sets the new template Item's item_code to the Order name. | — | reverted | reverted | ❌ | `a714c9922c` #877 | reverted - skipped |
| Item and BOM creation and KGGK replication: Introduces the 'Data Migration in KGGK' single doctype (from_site/to_site, System Manager only). | ❌ | ✅ | ✅ | ✅ | `a0e1050676` #879 | ported → `083c594` `ed24d61` |
| Item and BOM creation and KGGK replication: create_item_kggk: the PUT (update) payload leaves out variant_of; the POST (create) payload still carries it. | ✅ | ✅ | ✅ | ✅ | `41179f265d` #882 | retained (already in master) |
| Item and BOM creation and KGGK replication: The create_bom_kggk BOM payload reads and sends black_beed / black_beed_line instead of black_bead / black_bead_line. | newer | ✅ | ✅ | master's version | `324edbc5bd` #883 | superseded |
| Order: Comments out the 'target.item_code = source.name' line that unit 56 added to Order.create_item_template_from_order (PR body: reve… | — | reverted | reverted | ❌ | `0c191e3f66` #885 | reverted - skipped |
| Repair Order: Removes the trailing comma in Repair Order create_variant_of_template_from_order, which set Item.item_group for the '- V' variant… | newer | ✅ | ✅ | master's version | `3a75b2ee68` #887 | superseded |
| Repair Order: Order.on_update_after_submit: when an Order raised for a repair (is_repairing, repair_order set) reaches 'Approved', it writes th… | ✅ | ✅ | ✅ | ✅ | `31a2af21e9` #888 | retained (already in master) |
| Repair Order: Order doctype: adds a 'repair_order' Link (fetch_from cad_order_form.repair_order) under a new Tab Break at the end of the form. | ✅ | ✅ | ✅ | ✅ | `a2df7b513a` #890 | retained (already in master) |
| Item and BOM creation and KGGK replication: create_bom_kggk stops sending company in the BOM payload, so the remote BOM takes the remote site's default company. | ✅ | ✅ | ✅ | ✅ | `2f68217c73` #895 | retained (already in master) |
| Item and BOM creation and KGGK replication: create_item_kggk adds master_bom to the Item payload sent to KGGK. | ✅ | ✅ | ✅ | ✅ | `947cf74b68` #901 | retained (already in master) |
| Data Migration in KGGK: Data Migration in KGGK: adds a 'Get Pricing Details' section with from_site_1, and a 'User Details' section with api_key and api_… | ✅ | ✅ | ✅ | ✅ | `24f9193fe9` #911 | retained (already in master) |
| Order Form: 'Update Code From GkExport': replaces kggk's order_form.py and order_form.js wholesale with the gkexport (v15) code. | ✅ | ✅ | ✅ | ✅ | `174e9f1249` #908 | retained (already in master) |
| Manufacturing reports: Adds two Script Reports on diamond loss booked through Employee IR. | ❌ | ✅ | ✅ | ✅ | `f374adb9bc` #930 | ported → `c7c46e4` |
| Order Form: Corporate-customer Excel exports on Order Form. | ❌ | ✅ | ✅ | ✅ | `a8d94cd038` #928 | ported → `48639f4` |
| Manufacturing reports: Adds four manufacturing Script Reports. | ❌ | ✅ | ✅ | ✅ | `c480b15015` #935 | ported → `7d1eea5` |
| Manufacturing reports: Adds four manufacturing Script Reports. | ❌ | ✅ | ✅ | ✅ | `cdc4ecc02d` #943 | ported → `967e312` |
| Order Form: Corporate order updates. | ❌ | ✅ | ✅ | ✅ | `132daca436` #944 | ported → `d5c030e` `48639f4` |
| Manufacturing reports: Diamond Broken-Lost Report now values broken and missing diamonds at the item rate on the Finish Goods BOM, found via the latest… | ❌ | ✅ | ✅ | ✅ | `9727741f1a` #947 | ported → `8834d48` |
| Order Form: Changes how an Order Form is built from a Customer Order Form and updates the Proto Excel export. | ❌ | ✅ | ✅ | ✅ | `81ef3e9c30` #949 | ported → `4f95b9a` `48639f4` |
| Manufacturing reports: Adds 8 new GKE Catalog script reports: Assortment Report, Department Sample Issue Receive Report, Department Wise Diamond Stock,… | ❌ | ✅ | ✅ | ✅ | `6278f9019d` #961 | ported → `bc5198d` `dd838b8` |
| Manufacturing reports: Four report fixes. | ❌ | ✅ | ✅ | ✅ | `5ad362ebaa` #963 | ported → `450c974` |
| Product Return Order: Adds Product Hallmarking and Product Certification checkboxes to Product Return Form. | newer | ✅ | ✅ | master's version | `35481e8661` #967 | superseded |
| Stock and inventory reports: Adds a correctly named Serial No Detail Report (js/json/py). | — | reverted | reverted | ❌ | `b6335658d6` #973 | reverted - skipped |
| Product Return Order: Direct web-UI deletion of the Product Return Form DocType folder (code, JS, API, e-invoice logic, test). | ❌ | ✅ | ✅ | ✅ | `05d0bbb1a6` | ported → `87d5e26` |
| Product Return Order: Introduces Product Return Order Form (the renamed, extended successor of Product Return Form) and Product Return Order, with meta… | ❌ | ✅ | ✅ | ✅ | `c32d0cad7f` #977 | ported → `87d5e26` |
| Product Return Order: Comments out the 'if self.is_jewlex_credit_note: return' early return in Product Return Order Form on_submit, so Jewelex credit-n… | ✅ | ✅ | ✅ | ✅ | `cccbb2c097` #979 | retained (already in master) |
| Order Form: Order Form gains a Sales Type link and 'Repair' order and flow types. | ❌ | ✅ | ✅ | ✅ | `5142bd4ca5` #988 | ported → `48639f4` `6934d29` |
| Product Return Order: Rounds Product Return Order BOM re-pricing values (metal and finding rate and amount, making amount, diamond and gemstone amounts… | newer | ✅ | ✅ | master's version | `5fe374c1af` #991 | superseded |
| Stock and inventory reports: Adds the 'Item Code Serial No Detail' script report (gke_catalog/report/item_code_serial_no_detail). | ❌ | ✅ | ✅ | ✅ | `52797c9e2e` #995 | ported → `5c488a9` |
| Order Form: Adds Customer Gold/Diamond/Stone/Good/Finding Yes/No selects to the Order Form. | ✅ | ✅ | ✅ | ✅ | `9e18b4af8b` #996 | retained (patch-equivalent in master) |
| Manufacturing reports: Adds nine script reports: Consumables Stocks, Diamond & Gemstone Conversion Detail, Finish Good Item Details, Main Slip Details,… | ❌ | ✅ | ✅ | ✅ | `e050850422` #998 | ported → `895cf9a` |
| Manufacturing reports: 'v16 fixes for reports'. | ❌ | ✅ | ✅ | ✅ | `31cbd4dc28` #999 | ported → `5561eaf` |
| Manufacturing reports: Order Detail Report JS: the Company/Branch MultiSelect filters are commented out, and the dynamic filter options now use frappe.c… | ❌ | ✅ | ✅ | ✅ | `f86ab07a96` #1001 | ported → `cd21123` |
| Manufacturing reports: Department IR Report JS: From/To Department become MultiSelectList filters fed by frappe.db.get_link_options('Department'), repla… | ❌ | ✅ | ✅ | ✅ | `a3dfe421cf` #1003 | ported → `bb117c1` |
| Product Return Order: Large rework of Product Return Order and Product Return Order Form: Jewelex tag import, BOM recalculation, Serial No creation, GS… | newer | ✅ | ✅ | master's version | `582ab418b6` #1005 | superseded |
| Product Return Order: Adds is_jewelex_tag (Check) and jewelex_tag (Data) to the Product Return Form Item child table. | ✅ | ✅ | ✅ | ✅ | `16fec73930` #1007 | retained (already in master) |
| Item and BOM creation and KGGK replication: KGGK Item/BOM replication API update. | ✅ | ✅ | ✅ | ✅ | `7fbb3e841e` #1011 | retained (already in master) |
| Product Return Order: Adds metal_weight, finding_weight, gemstone_weight, diamond_pcs, gemstone_pcs and other_weight (with a new section) to the Produc… | ✅ | ✅ | ✅ | ✅ | `37499e78c5` #1014 | retained (already in master) |
| Manufacturing reports: Report updates. | ❌ | ✅ | ✅ | ✅ | `46b754fa3a` #1016 | ported → `1122c5a` |
| Repair Order: Repair Order / Repair Order Form overhaul (BOM fetch and creation, Serial No creation, product-type renames, CAD order form timin… | ❌ | ✅ | ✅ | ✅ | `7b4922f857` #1019 | ported → `48639f4` |
| Manufacturing reports: Adds the Batch Dashboard report, turns the Department Stock Detailed Report category and sub-category filters into Attribute Valu… | ❌ | ✅ | ✅ | ✅ | `d34dbe92ae` #1018 | ported → `8a94523` |
| Manufacturing reports: Order Detail Report: LEFT JOINs Item so the design image shows as a hover tooltip on the Design ID cell (HTML and inline JS built… | ❌ | ✅ | ✅ | ✅ | `a50376d183` #1021 | ported → `b82a01d` |
| Repair Order: Repair Order Form updates. | ❌ | ✅ | ✅ | partial | `33bdbd1d0a` #1025 | ported (partial) → `48639f4` |
| Repair Order: Adds order_form.get_bom_detail(design_id, doc), which merges Item variant attributes with the latest Finished Goods BOM or the It… | ✅ | ✅ | ✅ | ✅ | `fb172765bf` #1029 | retained (already in master) |
| Product Return Order: Adds read-only Check fields hallmarking_amounts and certification_amounts on Product Return Order, copied from the form's product… | newer | ✅ | ✅ | master's version | `d0efb8cd08` #1032 | superseded |
| Product Return Order: Passes a company code to the Jewelex credit-note API, mapped from the full company name to KGJPL or GEPL, in both the ProductRetu… | newer | ✅ | ✅ | master's version | `2893736db8` #1038 | superseded |
| Manufacturing reports: 'roles permission fix for kg gk'. | ❌ | ✅ | ✅ | ✅ | `939d28bccd` #1057 | ported → `5f1177c` `485f6f6` |
| Manufacturing reports: New script report 'FG History' (GKE Catalog, ref_doctype Order Form). | ❌ | ✅ | ✅ | ✅ | `205aea60e8` #1060 | ported → `a1371f4` |
| Product Return Order: Product Return Order Form changes. | ✅ | ✅ | ✅ | ✅ | `1e3ff5808e` #1072 | retained (already in master) |
| Manufacturing reports: RM Finding Item Details report: re-enables the Finding Size attribute pivot, matches Attribute Value Finding Type Weight rows als… | ❌ | ✅ | ✅ | ✅ | `638f440e5b` #1076 | ported → `e0643de` |
| Order: Order edit-item dialog: set_edit_order_form_detail now receives order_form_data and refills that same array in place, keeping the… | ✅ | ✅ | ✅ | ✅ | `3699372492` #1081 | retained (already in master) |
| Order: Order edit-item dialog loads the attribute table from the Order's design_id after dialog.show(), instead of from the dialog's ite… | ✅ | ✅ | ✅ | ✅ | `e26a0251f6` #1086 | retained (already in master) |
| Manufacturing reports: Sales Order without Manufacturing Plan report: a Sales Order now counts as planned when any Manufacturing Plan Table row referenc… | ❌ | ✅ | ✅ | ✅ | `5679b355dc` #1088 | ported → `964ac3e` |
| Order Form: Order Form Detail: chain_weight is read-only for 'As Per Design Type' only when the category is not Mugappu. | ✅ | ✅ | ✅ | ✅ | `9d165999ce` #1091 | retained (patch-equivalent in master) |
| Asset Item Master: Adds the Asset Item Master doctype (company/branch/warehouse/department plus a consumable items table) with autoname {abbr}-{bran… | ✅ | ✅ | ✅ | ✅ | `367bb9dd2c` #1101 | retained (already in master) |
| Item and BOM creation and KGGK replication: create_bom_kggk (BOM before_validate hook) sends finding_size as 0 when empty in the finding_detail payload replicated to the KGG… | ❌ | ✅ | ✅ | ✅ | `0b806e5de1` #1099 | ported → `ed24d61` |
| Manufacturing reports: Updates four reports plus Branch Stock Summary. | ❌ | ✅ | ✅ | ✅ | `a26b426d3c` #1103 | ported → `f19a00f` |
| Manufacturing reports: Order Detail Report adds a 'Jewelex Batch No' column from Parent Manufacturing Order.jewelex_batch_no. | ❌ | ✅ | ✅ | ✅ | `37606c2710` #1108 | ported → `d21fc64` |
| Manufacturing reports: Adds two new script reports. | ❌ | ✅ | ✅ | ✅ | `a67674c412` #1110 | ported → `f7aa06d` |
| Product Return Order: Repair/Product Return flow update. | ❌ | ✅ | ✅ | ✅ | `2ea8770fa2` #1119 | ported → `87d5e26` |
| Order Form + Product Return Order + HR payroll and salary withholding + Manufacturing reports: Big sync of v16_develop_aerele into kggk_prod (29 commits). | ❌ | ✅ | ✅ | partial | `ed9c4d3bbb` #1123 | ported (partial) → `7f39ed4` `083c594` `48639f4` `87d5e26` |
| Fixtures: Adds the Custom Field 'Purchase Order Item-custom_copy_bom' (Copy BOM, Link to BOM) to gke fixtures. | ❌ | ✅ | ✅ | ✅ | `63b1bbcd8c` #1170 | ported → `26bfda3` |
| Manufacturing reports: Three report changes. | ❌ | ✅ | ✅ | partial | `e699b95344` #1176 | ported (partial) → `fc388a1` `fe31a17` |
| Manufacturing reports: Production Report rework: per-department Gross Wt pivot columns from the latest main MWO per PMO, WIP MWO rows, order-type resolu… | ❌ | ✅ | ✅ | ✅ | `177ca4bdd1` #1185 | ported → `a03131d` `083c594` |
| Manufacturing reports: Production Report fixes: manufacturer filter removed, WIP MWO query excludes SN%/sample/consumable items and resolves order type… | ❌ | ✅ | ✅ | partial | `dd4aa34012` #1191 | ported (partial) → `00d6da5` `fe31a17` |
| Manufacturing reports: Rewrites the KGGK Jewelex tally data source: removes the pyodbc/SQL query and the cache file, and fetches rows from an HTTP order… | ❌ | ✅ | ✅ | ❌ | `d090a12db4` #1203 | excluded (KGGK-only) |
| Manufacturing reports: In the KGGK Jewelex tally compare mode, 'ERP Order Complete' becomes an Int count of fully submitted PMOs (0 when none) instead o… | ❌ | ✅ | ✅ | ❌ | `3c6741b515` #1205 | excluded (KGGK-only) |
| Material Request transfer to department: Fixture-only change to fixtures/custom_field.json. | ❌ | ✅ | ✅ | ✅ | `3629b4c6bc` #1194 | ported → `26bfda3` |
| Manufacturing reports: Fixes to five reports. | ❌ | ✅ | ✅ | partial | `e2b103762d` #1217 | ported (partial) → `6f32e00` `fe31a17` |
| Manufacturing reports: Adds Order Date from/to, Jewelex Order No and Jewelex Batch No filters to the 'KGGK Jewelex - ERP Order Tally' report. | ❌ | ✅ | ✅ | ❌ | `d1c7fe32d8` #1224 | excluded (KGGK-only) |
| Stock and inventory reports: Adds two script reports. | ❌ | ✅ | ✅ | ✅ | `35e21d2eba` #1229 | ported → `2f531e0` |
| Manufacturing Operation naming: The Manufacturing Operation autoname hook (gke_order_forms/doc_events/manufacturing_operation.py) now produces MOP-YYMM-XXXXXX: s… | ❌ | ✅ | ✅ | ✅ | `fc4caf290e` #1235 | ported → `8c59e22` |
| Manufacturing reports: Report fixes. | ❌ | ✅ | ✅ | ✅ | `e986264cdb` #1255 | ported → `13559f5` |
| Nova Glow rename: Renames the setting type 'Close' / 'Close Setting' to 'Nova Glow' / 'Nova Glow Setting' in five places: the CAD Report restricted… | ❌ | ✅ | ✅ | ✅ | `3d05870fd3` #1278 | ported → `e0e6adb` `ed24d61` |
| Nova Glow rename: Exact revert of #1278: restores 'Close' / 'Close Setting' in the CAD Report, item.py replication gates, Targets Form, Retailer Su… | — | reverted | reverted | ❌ | `3ec2f3376d` #1280 | reverted - skipped |
| Nova Glow rename: Revert of the revert: re-applies the #1278 Close -> Nova Glow rename unchanged. | — | reverted | reverted | ❌ | `c1f7ed5f7b` #1283 | reverted - skipped |
| Product Return Order: The net first-parent change has four parts. | ❌ | ✅ | ✅ | partial | `e0b01c1f35` #1288 | ported (partial) → `48639f4` `ed24d61` `87d5e26` |
| Manufacturing reports: Advance Bagging Report from MR re-enables the Alternative Item column. | ❌ | ✅ | ✅ | ✅ | `a264410c5b` #1293 | ported → `8b4e46d` |
| Manufacturing reports: Four gke_catalog report changes. | ❌ | ✅ | ❌ | ✅ | `3d6c61ac92` #1360 | ported → `c9c77f4` |

## Not manufacturing-related

| Feature | master | kggk_prod | gurukrupa-prod | Required in gk_prod | Source commits | Final status |
|---|:-:|:-:|:-:|:-:|---|---|
| Tests: Replaces the empty TestOrder/TestOrderForm stubs with integration tests. | ❌ | ✅ | ✅ | ✅ | `d0816eb1ab` #634 | ported → `be91292` |
| Patches: Adds [pre_model_sync] and [post_model_sync] section headers to patches.txt so that gc_ration_master runs after schema sync. | ✅ | ✅ | ✅ | ✅ | `b297393035` #651 | retained (already in master) |
| HR attendance and punches: Adds the Monthly In-Out Log doctype to the kggk line: a per-employee monthly attendance/punch summary filled from Attendance, shi… | ✅ | ✅ | ✅ | ✅ | `e93df539c4` #666 | retained (patch-equivalent in master) |
| HR attendance and punches: v16 sync of the HR developer's master work across 37 files. | ✅ | ✅ | ✅ | ✅ | `421656ee9e` #789 | retained (already in master) |
| Fixtures: Removes two Company custom fields from gke's custom_field fixture. | ❌ | ✅ | ✅ | ✅ | `d5878c4f98` | ported → `26bfda3` |
| Tests: TestOrderForm now resolves department and branch in a per-test setUp instead of setUpClass. | ❌ | ✅ | ✅ | ✅ | `310eb6a215` #818 | ported → `6545610` |
| Price List and Revise Price: New submittable DocType Customer Price List Approval with a child table, Customer Price List Approval Details (date, company_rate… | ❌ | ✅ | ✅ | ✅ | `a7163c1489` #820 | ported → `60b7449` |
| Product Return Order: Adds Credit Note Type (prompt-named master) and Credit Note Subtype (subtype_name + parent_type link to Credit Note Type, rate_ty… | ✅ | ✅ | ✅ | ✅ | `c24d209016` #850 | retained (already in master) |
| Product Return Order: Product Return Form (the old doctype): when building the Sales Invoice return, set company_address to an Address linked to the Co… | newer | ✅ | ✅ | master's version | `662fc2c0cb` #892 | superseded |
| Order Form: 'Updated V16 Code To Gkexport Code': resets order.py and order_form.js to the merge-base (v15 gkexport) content and rewrites orde… | — | reverted | reverted | ❌ | `099f93dadf` #900 | reverted - skipped |
| Order Form: GitHub revert of unit 67 (order.py, order_form.js and order_form.py restored). | — | reverted | reverted | ❌ | `d360a42f69` #902 | reverted - skipped |
| Order Form: Commented out the back-link that create_cad_orders writes from the originating Pre Order Form Details row to the Order Form (orde… | — | reverted | reverted | ❌ | `f87bdc5621` #914 | reverted - skipped |
| Order: Replaced kggk's Order controller and field layout (order.py, order.json), the Order Form JSON and the Order Form Detail JSON with… | — | reverted | reverted | ❌ | `f875de6858` #913 | reverted - skipped |
| Order Form: Revert of #914 (unit 71). | — | reverted | reverted | ❌ | `9067f1c4dd` #916 | reverted - skipped |
| Order: Revert of #913 (unit 72). | — | reverted | reverted | ❌ | `95b5b3b66b` #917 | reverted - skipped |
| HR attendance and punches: v16-line copy of the HRMS developer's late-June master changes. | ✅ | ✅ | ✅ | ✅ | `75d4195722` #920 | retained (patch-equivalent in master) |
| Manufacturing reports: Whitespace-only edit of order_detail_report.py: removes one blank line and the trailing newline. | ❌ | ✅ | ✅ | ✅ | `777eae6618` #926 | ported → `fc51b2f` |
| HR attendance and punches: v16 query fixes in gke_hrms. | ✅ | ✅ | ✅ | ✅ | `a10114d4ae` #931 | retained (patch-equivalent in master) |
| HR attendance and punches: Fixes the IndentationError that unit 79 introduced in Manual Punch Entry.cancel_linked_records by re-indenting the OT Log and Per… | ✅ | ✅ | ✅ | ✅ | `abf79b4a37` #933 | retained (already in master) |
| HR overtime: Removes the OT Allowance Entry dashboard connection (links[]) to OT Log via link_fieldname ot_allowance_entry. | ❌ | ✅ | ✅ | ✅ | `737198076c` #938 | ported → `a01fe9b` |
| HR payroll and salary withholding: Reworks the PF Challan and ESIC Challan reports (account-wise totals panel and print helper) and adds a PF Contribution Report (E… | ✅ | ✅ | ✅ | ✅ | `7b09193242` #948 | retained (patch-equivalent in master) |
| HR overtime: OT and Night Shift Report JS. | ❌ | ✅ | ✅ | ✅ | `cb9acada3f` #965 | ported → `544ca41` |
| HR employee lifecycle: Removes 'family_background' from the Employee Update on_submit field-copy list. | ❌ | ✅ | ✅ | ✅ | `8a3afd4d05` #968 | ported → `9faadcb` |
| Stock and inventory reports: Direct web-UI deletion of the broken gke_catalog/report/serial_no_detail_report folder that unit 39 (#833) created. | ❌ | ✅ | ✅ | ✅ | `ca7004c4a9` | ported → `7d4c4fa` |
| HR attendance and punches: Adds the "Today's Absent Employees" script report: active employees with no Employee Checkin on the chosen date, showing departme… | ❌ | ✅ | ✅ | ✅ | `1d0f40b5db` #981 | ported → `7b3cbb3` |
| Stock and inventory reports: Web-UI commit that deletes the serial_no_detail_report directory that unit 94 had added. | — | reverted | reverted | ❌ | `1bdd883466` | reverted - skipped |
| Product Return Order: Removes a duplicate amended_from field definition from the Product Return Order DocType JSON. | ✅ | ✅ | ✅ | ✅ | `40b04bc125` #1010 | retained (already in master) |
| Product Return Order: One-line JSON change: allow_bulk_edit=1 on the items Table field of Product Return Order Form. | ✅ | ✅ | ✅ | ✅ | `046589febe` #1020 | retained (already in master) |
| Repair Order: Adds @frappe.whitelist() to order_form.get_bom_detail, which unit 119 added without it, so its frappe.call failed. | ✅ | ✅ | ✅ | ✅ | `b2e1f1327f` #1030 | retained (already in master) |
| HR employee lifecycle: Adds the submittable Cross Company Employee Transfer doctype and its Cross Employee Transfer Details child. | ✅ | ✅ | ✅ | ✅ | `40bbae8d83` #1053 | retained (already in master) |
| Product Return Order: 'Added Precision': rounds the Product Return Order Form grand_total and the per-row diamond amount accumulation to 2 decimals in… | newer | ✅ | ✅ | master's version | `41defdf99b` #1051 | superseded |
| HR attendance and punches: HR and Survey changes. | ✅ | ✅ | ✅ | ✅ | `bba46393b9` #1074 | retained (already in master) |
| HR attendance and punches: Replaces frappe.get_list calls that used SQL-function field strings ('date(time) as login_date' + group_by) for Outdoor Duty chec… | ✅ | ✅ | ✅ | ✅ | `4153192426` #1077 | retained (already in master) |
| HR payroll and salary withholding: PF Challan report get_account_total_summary: re-indented with tabs. | ✅ | ✅ | ✅ | ✅ | `8b2d1c88ed` #1079 | retained (patch-equivalent in master) |
| HR attendance and punches: Fixes the SyntaxError that unit 130 introduced in gke_hrms/api/attendance_api.py (the wo = ... | ✅ | ✅ | ✅ | ✅ | `2299e0f89f` #1082 | retained (already in master) |
| Order: Adds console.log('DESIGN ID =', design_id) to edit_item_documents() in Order JS. | ❌ | ✅ | ✅ | ✅ | `e0c8c29de9` #1084 | ported → `48639f4` |
| HR attendance and punches: v16 query fixes across HR. | ✅ | ✅ | ✅ | ✅ | `1ac7132715` #1093 | retained (already in master) |
| HR payroll and salary withholding: Rewrites the Employee Advance validation (calculate_working_days doc_event). | ✅ | ✅ | ✅ | ✅ | `ba4549b284` #1129 | retained (already in master) |
| Packaging and config: Adds [tool.bench.frappe-dependencies] frappe = '>=15.0.0,<17.0.0' to pyproject.toml. | ✅ | ✅ | ✅ | ✅ | `83ee74422b` #1158 | retained (already in master) |
| Sales and HR reports: Adds the Department Wise Daily Attendance and Department Wise Daily Present reports with scheduled manager mails, plus the salary… | ✅ | ✅ | ✅ | ✅ | `7d75d56425` #1172 | retained (already in master) |
| HR employee lifecycle: Cross Company Employee Transfer update: target_site-driven REST calls, holiday list as a transferable property, reports_to taken… | ✅ | ✅ | ✅ | ✅ | `440dc086d6` #1175 | retained (already in master) |
| Sales and HR reports: Moves the department report mail crons to 08:30/10:30, adds a manager guard and hardcoded CC lists to the mailers, and tweaks the… | ✅ | ✅ | ✅ | ✅ | `624b695fff` #1182 | retained (already in master) |
| HR attendance and punches: Adds the Attendance Adjustment Tool (submittable doctype, module GKE HRMS), its child table Adjustment Details, and a large API m… | ❌ | ✅ | ✅ | ✅ | `ed98efe701` #1209 | ported → `e168048` |
| HR payroll and salary withholding: Adds overrides/salary_structure_assignment.py with CustomSalaryStructureAssignment, which overrides HRMS v16's _get_component_eva… | ❌ | ✅ | ✅ | ✅ | `50145bd6f9` #1208 | ported → `bcbe1c3` `083c594` |
| HR attendance and punches: Brings the attendance API (gke_hrms/api/attendance.py), the loan_application doc event and the ESIC challan and PF contribution r… | ✅ | ✅ | ✅ | ✅ | `d55b2445ba` #1240 | retained (already in master) |
| HR overtime: OT Allowance Entry adds Employee.old_employee_code to its attendance query. | ✅ | ✅ | ✅ | ✅ | `92071f775c` #1272 | retained (already in master) |
| HR misc: Adds the Employee Signature doctype (employee, branch, route, is_published, naming series EMP-SIG-) and its child table Employee… | ✅ | ✅ | ✅ | ✅ | `98ec5fbcad` #1297 | retained (already in master) |
| Sales and HR reports: Department-wise Daily Attendance and Department-wise Daily Present report mailers: the CC list becomes one fixed HR mailbox plus… | ✅ | ✅ | ✅ | ✅ | `9f631325a5` #1328 | retained (already in master) |
| HR overtime: OT Allowance Entry: fetched OT rows are sorted by old employee code then attendance date (previously by date only), grouping rows… | ✅ | ✅ | ✅ | ✅ | `cc654ee00a` #1335 | retained (already in master) |
| HR attendance and punches: Personal-out deduction clamped at shift end: a new correlated pol_deduction_subquery sums Personal Out Log durations with in_time… | ✅ | ✅ | ❌ | ✅ | `361835e1ad` #1350 | retained (already in master) |
| HR attendance and punches: In Monthly In-Out Log's personal-out deduction subquery, a Personal Out Log whose out_time is already past shift end now contribu… | ❌ | ✅ | ❌ | ✅ | `e7f8cf3fcb` #1357 | ported → `be0c216` |
| Catalogue portal and APIs: GK-live PR into gurukrupa-prod with three parts. | ❌ | ❌ | ✅ | ✅ | `20d3c28c8c` #1356 | ported → `be0c216` `dd838b8` |
| HR attendance and punches: Holiday Punch rewrite. | ✅ | ❌ | ✅ | ✅ | `c94f0475c5` #1358 | retained (already in master) |

## master-only functionality (retained)

Everything master has that neither production branch has is kept as master has it. master is the v15 line, so this code had never run on v16; it went through the v16 audit (static + runtime) and the fixes listed in 07.

| Group | master | kggk_prod | gurukrupa-prod | Required in gk_prod | Source | Final status |
|---|:-:|:-:|:-:|:-:|---|---|
| 30 DocTypes only on master: add_to_cart_portal_item, audit_analytical_review_detail, audit_customer_gold_reconciliation_details, audit_high_risk_observation_detail, audit_high_risk_return_summary, audit_management_response_tracker, audit_status_of_previous_audit_points, batch_pdd_change_reason, bulk_order_detail, cataloge_item_details, cataloge_master, catalogue_collection_details, csat_feedback, csat_questionnaire, csat_questionnaire_for_po, employee_mediclaim_table, employee_multiselect, gold_rate_cut, internal_catalog_master, kaizen_slip, kaizen_tracker, order_tracking, portal_order, portal_order_item, revise_diamond_price__list, revise_gemstone_pricelist_detail, secured_and_unsecured_loan, secured_and_unsecured_loan_repayment_schedule, size_wise_purchase, user_item_details | ✅ | ❌ | ❌ | ✅ | master | retained |
| 23 reports only on master: 24q_report, 26q_report, accounts_payable___sd, accounts_payable_summary___sd, accounts_receivable___sd, accounts_receivable_summary___sd, available_batch_report___gkb, batch_wise_purchase_cycle, batch_wise_sales_cycle, batch_wise_sales_cycle___sam, batch_wise_stock_balance, cad_dashboard_script, consumable_stock_balance, consumable_stock_report, dummy_monthly_report, employee_mediclaim_detailed_reports, gross_profit_si_and_batch_wise, item_with_tax, ot_report, pd_to_prod, purchase_cycle, purchase_report, purchase_return_report | ✅ | ❌ | ❌ | ✅ | master | retained (+ v16 fixes) |
| 1 API modules only on master | ✅ | ❌ | ❌ | ✅ | master | retained (+ v16 import fixes) |
| 20 portal/web files under www/ only on master | ✅ | ❌ | ❌ | ✅ | master | retained |
| Catalogue and portal API modules that GK live copied from master in #1356 | ✅ | ❌ | ✅ | ✅ | master + #1356 delta | retained; #1356's catalogue delta carried by `dd838b8` |

