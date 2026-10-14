# 04 — Commit promotion matrix

One row per logical change (unit). *kggk_prod SHA* is the unit's merge or direct commit; *gurukrupa-prod SHA* is the same commit when GK live has it (gurukrupa-prod is kggk_prod minus its last 7 commits plus 2 own units). *New SHA* lists the migration-branch commits that carry the change — replayed commits, consolidated port commits and decision commits. Port methods follow the brief's vocabulary; a unit can have more than one.

| Unit | Logical change | Original PR | kggk_prod SHA | gurukrupa-prod SHA | Master equivalent | Port method | New SHA |
|---|---|---|---|---|---|---|---|
| kggk:1 | Replaces the empty TestOrder/TestOrderForm stubs with integration tests. | #634 | `d0816eb1ab` | `d0816eb1ab` | — | direct-cherry-pick | `be91292` |
| kggk:2 | Reformats order.py and order_form.py from tabs to 4-space black style and refactors their logic. | #631 | `398707865a` | `398707865a` | — | manual-logical-port | `48639f4` |
| kggk:3 | GC Ratio (the child table of GC Ratio Master) gets structured Type (Range/Above/Below), Range 1 and Range 2 fields, and its text label beco… | #644 | `2f041b5969` | `2f041b5969` | — | direct-cherry-pick + manual-logical-port | `71f72ef` `48639f4` |
| kggk:4 | Registers gke_customization.patches.gc_ration_master in the previously empty patches.txt. | #645 | `a01ead8785` | `a01ead8785` | — | manual-logical-port | `083c594` |
| kggk:5 | Adds GC Ratio Master.validate. | #646 | `c003e91b41` | `c003e91b41` | — | direct-cherry-pick | `86232cd` |
| kggk:6 | make_quotation_batch now clears the Quotation's existing item rows before adding one row per selected Order. | #650 | `549b99bf40` | `549b99bf40` | — | manual-logical-port | `48639f4` `ed24d61` |
| kggk:7 | Adds [pre_model_sync] and [post_model_sync] section headers to patches.txt so that gc_ration_master runs after schema sync. | #651 | `b297393035` | `b297393035` | — | retained-from-master | — |
| kggk:8 | Follow-up to the #631 refactor. | #653 | `7de53ba167` | `7de53ba167` | — | superseded | — |
| kggk:9 | Adds the Monthly In-Out Log doctype to the kggk line: a per-employee monthly attendance/punch summary filled from Attendance, shift, person… | #666 | `e93df539c4` | `e93df539c4` | c72c86b50a | retained-from-master | — |
| kggk:10 | Converts the standard report 'Warehouse wise Consumable Consumption' from Script Report to Query Report. | direct | `e7d0b7dbf9` | `e7d0b7dbf9` | — | superseded | `dd838b8` |
| kggk:11 | A large Order Form update with these parts: - Customer-specific Excel export buttons on submitted Order Forms: GC format, code creation, de… | #749 | `9f3433b271` | `9f3433b271` | — | squashed-port + manual-logical-port | `e673fd9` `083c594` `48639f4` |
| kggk:12 | The Revise Gemstone Price List JSON gains multiplier tables, handling-charge fields, a PR-rate range, effective-from and grade fields, and… | #746 | `f946dc8b4e` | `f946dc8b4e` | — | direct-cherry-pick + manual-logical-port | `47465ae` `6934d29` |
| kggk:13 | Removes the trailing commas that made Item.item_group a tuple in create_item_template_from_order ('<subcategory> - T') and create_variant_o… | #750 | `2bb0e3ccb1` | `2bb0e3ccb1` | — | manual-logical-port | `48639f4` |
| kggk:14 | Applies the same tuple-to-string item_group fix in create_only_variant_from_order, create_sufix_of_variant_template_from_order and create_v… | #752 | `254f25877f` | `254f25877f` | — | manual-logical-port | `48639f4` |
| kggk:15 | Removes the stray third positional argument from frappe.get_doc('Timesheet', {'order': ...}, 'name') in Order.on_update_after_submit (Appro… | #758 | `3aa12e00e1` | `3aa12e00e1` | — | retained-from-master | — |
| kggk:16 | Adds three Order Form Detail fields: jewelex_design_id (mandatory for Sketch Design), design_sourceroute (Curated/Co-Created/Designed) and… | #759 | `49a4c3da9c` | `49a4c3da9c` | — | manual-logical-port | `48639f4` |
| kggk:17 | Changes create_bom_timesheet. | #760 | `0868e53bf7` | `0868e53bf7` | — | manual-logical-port | `48639f4` |
| kggk:18 | One-line guard in Order Form gc_export_to_excel, SET-item branch: write '' when no Customer RM Code Detail row matches instead of indexing… | #762 | `5ac322b67e` | `5ac322b67e` | — | superseded | — |
| kggk:19 | Adds Float field sketch_approval_day to child DocType Order Criteria Table, a kggk-only MECH path. | #763 | `8effcc39a3` | `8effcc39a3` | — | direct-cherry-pick + manual-logical-port | `81de021` `48639f4` |
| kggk:20 | Fixes Gold Rates.set_gold_value, which wrote the first bullion feed's live rate to a misspelt key ('live_.rate' changed to 'live_rate'). | #764 | `e6973785dd` | `e6973785dd` | — | direct-cherry-pick + manual-logical-port | `64f15cf` `48639f4` |
| kggk:21 | Order Form exports: gc_export_to_excel and creation_export_to_excel skip Earrings rows that belong to a SET (uomset_of = SET). | #770 | `19f1882756` | `19f1882756` | — | manual-logical-port | `48639f4` |
| kggk:22 | Reformats hooks.py to the v16 app template: black-style layout and trailing commas, `from . | #769 | `5709d9cfde` | `5709d9cfde` | — | manual-logical-port | `083c594` |
| kggk:23 | Rewrites the whitelisted get_customer_order_form, which maps a Customer Order Form into an Order Form. | #772 | `5cf65cd5ac` | `5cf65cd5ac` | — | manual-logical-port | `48639f4` |
| kggk:24 | In get_design_creation, the BOM Finding Detail chain-weight lookup now filters parent by final_bom.name. | #774 | `faa55e2c8b` | `faa55e2c8b` | — | manual-logical-port | `48639f4` |
| kggk:25 | v16 sync of the HR developer's master work across 37 files. | #789 | `421656ee9e` | `421656ee9e` | — | retained-from-master | — |
| kggk:26 | Adds a customer-specific 'Get Cost Sheet' Excel export for submitted Order Forms: a JS button under Get File plus the whitelisted get_cost_… | #792 | `3be028bdc8` | `3be028bdc8` | — | direct-cherry-pick + manual-logical-port | `c3ab935` `48639f4` |
| kggk:27 | Gold Rates: replaces the hand-rolled socket.io client in get_live_gold_rate, which feeds row 5, with a websocket-client SignalR client, and… | #799 | `4734bd2f40` | `4734bd2f40` | — | direct-cherry-pick | `117e4db` |
| kggk:28 | Disables the row-5 live-rate fetcher: set_gold_value_6 calls are commented out in run_gold_rate_scheduler and validate, and the websocket c… | #808 | `f74d9a1610` | `f74d9a1610` | — | direct-cherry-pick | `3991b28` |
| kggk:29 | Replaces fixtures/custom_field.json (5 rows -> 2084) and fixtures/doctype.json (1 custom DocType -> 51) with a full dump taken from the v16… | #809 | `c6b22dadd7` | `c6b22dadd7` | — | retained-from-master | `26bfda3` |
| kggk:30 | Removes two Company custom fields from gke's custom_field fixture. | direct | `d5878c4f98` | `d5878c4f98` | — | retained-from-master | `26bfda3` |
| kggk:31 | Adds the child DocType Diamond Price List Table under GKE Order Forms. | #810 | `fa7ea703a5` | `fa7ea703a5` | 2efb4021ba | retained-from-master | — |
| kggk:32 | TestOrderForm now resolves department and branch in a per-test setUp instead of setUpClass. | #818 | `310eb6a215` | `310eb6a215` | — | direct-cherry-pick | `6545610` |
| kggk:33 | Revise Making Charge Price: before_save becomes before_insert. | #817 | `b0b2aeec21` | `b0b2aeec21` | — | retained-from-master | — |
| kggk:34 | Revise Diamond Price List crate_price_list now writes stone_code and the outright/outwork handling-charge percentage and rate under their s… | #819 | `d25f9f1688` | `d25f9f1688` | — | retained-from-master | — |
| kggk:35 | New submittable DocType Customer Price List Approval with a child table, Customer Price List Approval Details (date, company_rate, customer… | #820 | `a7163c1489` | `a7163c1489` | — | direct-cherry-pick | `60b7449` |
| kggk:36 | Restores the Revise Making Charge Price DocType JSON to a consistent submittable parent: customer, setting type, metal type and touch, date… | #822 | `93da164324` | `93da164324` | — | retained-from-master | — |
| kggk:37 | Adds four GKE Catalog script reports: Sales Invoice Detail Report (per invoice line BOM-derived metal/pure/diamond/gemstone/other weights,… | #823 | `10f0cfa68e` | `10f0cfa68e` | — | direct-cherry-pick | `5ff3d31` `be7e82f` `20e246a` `14793d7` `7ae741e` `8ae4219` `8eff717` `ade6ff3` |
| kggk:38 | Renames the submittable DocType 'Revise Diamond Price List' (double space, folder revise_diamond_price__list) to 'Revise Diamond Price List… | #825 | `d5541c6535` | `d5541c6535` | — | squashed-port + manual-logical-port | `687a7dc` `6934d29` |
| kggk:39 | Branch Stock Summary JS gets dark-theme-aware styling, more robust View-details button handlers and a new 'Aloy' raw-material option. | #833 | `5c19380b01` | `5c19380b01` | — | squashed-port | `f36d428` |
| kggk:40 | Adds the Product Return Form doctype and flow (return of sold pieces: fetch sales BOM and invoice by serial, re-rate the BOM at invoice/cur… | #835 | `bcb4b9c1cc` | `bcb4b9c1cc` | — | superseded | — |
| kggk:41 | Adds Mould Report: for one required MWO, lists every Mould whose design references include the MWO's item, with mould no, rake/tray/box loc… | #840 | `c673ca33ff` | `c673ca33ff` | — | direct-cherry-pick | `0fbc6c7` `0ed99a0` |
| kggk:42 | Removes the 'Allow Loss' column (commented out) and the 'mo.allowed_loss_percentage as allow_loss' select from 'Employee issue receive repo… | #841 | `efd81fa2d1` | `efd81fa2d1` | — | direct-cherry-pick | `68a971d` |
| kggk:43 | Adds Credit Note Type (prompt-named master) and Credit Note Subtype (subtype_name + parent_type link to Credit Note Type, rate_type Invoice… | #850 | `c24d209016` | `c24d209016` | — | retained-from-master | — |
| kggk:44 | Adds an explicit 'bom': 'bom' field mapping to gke's overridden Sales Order -> Delivery Note mapper (make_delivery_note) and to gke's Deliv… | direct | `c6fdce26f2` | `c6fdce26f2` | — | direct-cherry-pick + manual-logical-port | `965a95d` `ed24d61` |
| kggk:45 | Appends whitelisted get_making_charge(customer, metal_type, setting_type, gold_rate, metal_touch, subcategory) to gke_order_forms/doc_event… | #856 | `020d9624e0` | `020d9624e0` | — | manual-logical-port | `ed24d61` |
| kggk:46 | Appends whitelisted get_finding_charge(parent, subcategory) and get_making_charge_price(parent, subcategory) to item.py: given a Making Cha… | #858 | `057fbac944` | `057fbac944` | — | manual-logical-port | `ed24d61` |
| kggk:47 | Adds 'parent' to get_making_charge's returned fields and appends whitelisted get_diamond_rate(customer, diamond_type, stone_shape, diamond_… | #861 | `b140da522c` | `b140da522c` | — | manual-logical-port | `ed24d61` |
| kggk:48 | Appends whitelisted get_fixed_retail_rate(...) (Fixed per-customer or Retail gemstone price row by per-pc/per-carat, cut/cab, type, shape,… | #862 | `a887b4c45e` | `a887b4c45e` | — | manual-logical-port | `ed24d61` |
| kggk:49 | Repair Order / Repair Order Form updates: CAD order form gets total_rows=1 and 'New Design' design type, slash-stripping of attribute names… | #864 | `4c231fda6b` | `4c231fda6b` | — | retained-from-master | — |
| kggk:50 | Adds create_item_kggk and create_bom_kggk to gke_order_forms/doc_events/item.py and wires them as Item and BOM before_validate hooks in hoo… | #867 | `c72dab2608` | `c72dab2608` | — | retained-from-master | — |
| kggk:51 | Repair Order changes. | #869 | `0ccb08995b` | `0ccb08995b` | — | retained-from-master | — |
| kggk:52 | Adds 'import requests' at the top of doc_events/item.py. | #871 | `1d04e98ba8` | `1d04e98ba8` | 2959ad2285 a646f7f74d c6083d123e | retained-from-master | — |
| kggk:53 | Two small changes. | #872 | `7a1ea3d7b8` | `7a1ea3d7b8` | — | retained-from-master | — |
| kggk:54 | Temporarily switches off KGGK replication. | #873 | `aebd145e48` | `aebd145e48` | 2959ad2285 a646f7f74d c6083d123e | superseded | — |
| kggk:55 | Removes a trailing comma in Repair Order create_item_template_from_order, so Item.item_group is set to a string instead of a 1-tuple. | #874 | `43fddcb04c` | `43fddcb04c` | — | superseded | — |
| kggk:56 | Order.create_item_template_from_order post_process sets the new template Item's item_code to the Order name. | #877 | `a714c9922c` | `a714c9922c` | — | reverted | — |
| kggk:57 | Introduces the 'Data Migration in KGGK' single doctype (from_site/to_site, System Manager only). | #879 | `a0e1050676` | `a0e1050676` | — | manual-logical-port | `083c594` `ed24d61` |
| kggk:58 | create_item_kggk: the PUT (update) payload leaves out variant_of; the POST (create) payload still carries it. | #882 | `41179f265d` | `41179f265d` | — | retained-from-master | — |
| kggk:59 | The create_bom_kggk BOM payload reads and sends black_beed / black_beed_line instead of black_bead / black_bead_line. | #883 | `324edbc5bd` | `324edbc5bd` | — | superseded | `ed24d61` |
| kggk:60 | Comments out the 'target.item_code = source.name' line that unit 56 added to Order.create_item_template_from_order (PR body: revert changes… | #885 | `0c191e3f66` | `0c191e3f66` | — | reverted | — |
| kggk:61 | Removes the trailing comma in Repair Order create_variant_of_template_from_order, which set Item.item_group for the '- V' variant to a 1-tu… | #887 | `3a75b2ee68` | `3a75b2ee68` | — | superseded | — |
| kggk:62 | Order.on_update_after_submit: when an Order raised for a repair (is_repairing, repair_order set) reaches 'Approved', it writes the Order's… | #888 | `31a2af21e9` | `31a2af21e9` | — | retained-from-master | — |
| kggk:63 | Order doctype: adds a 'repair_order' Link (fetch_from cad_order_form.repair_order) under a new Tab Break at the end of the form. | #890 | `a2df7b513a` | `a2df7b513a` | 06b208f6a5 | retained-from-master | — |
| kggk:64 | Product Return Form (the old doctype): when building the Sales Invoice return, set company_address to an Address linked to the Company thro… | #892 | `662fc2c0cb` | `662fc2c0cb` | — | superseded | — |
| kggk:65 | create_bom_kggk stops sending company in the BOM payload, so the remote BOM takes the remote site's default company. | #895 | `2f68217c73` | `2f68217c73` | — | retained-from-master | — |
| kggk:66 | create_item_kggk adds master_bom to the Item payload sent to KGGK. | #901 | `947cf74b68` | `947cf74b68` | — | retained-from-master | — |
| kggk:67 | 'Updated V16 Code To Gkexport Code': resets order.py and order_form.js to the merge-base (v15 gkexport) content and rewrites order_form.py… | #900 | `099f93dadf` | `099f93dadf` | — | reverted | — |
| kggk:68 | GitHub revert of unit 67 (order.py, order_form.js and order_form.py restored). | #902 | `d360a42f69` | `d360a42f69` | — | reverted | — |
| kggk:69 | Data Migration in KGGK: adds a 'Get Pricing Details' section with from_site_1, and a 'User Details' section with api_key and api_secret, bo… | #911 | `24f9193fe9` | `24f9193fe9` | — | retained-from-master | — |
| kggk:70 | 'Update Code From GkExport': replaces kggk's order_form.py and order_form.js wholesale with the gkexport (v15) code. | #908 | `174e9f1249` | `174e9f1249` | — | retained-from-master | — |
| kggk:71 | Commented out the back-link that create_cad_orders writes from the originating Pre Order Form Details row to the Order Form (order_form_id). | #914 | `f87bdc5621` | `f87bdc5621` | — | reverted | — |
| kggk:72 | Replaced kggk's Order controller and field layout (order.py, order.json), the Order Form JSON and the Order Form Detail JSON with the gkexp… | #913 | `f875de6858` | `f875de6858` | — | reverted | — |
| kggk:73 | Revert of #914 (unit 71). | #916 | `9067f1c4dd` | `9067f1c4dd` | — | reverted | — |
| kggk:74 | Revert of #913 (unit 72). | #917 | `95b5b3b66b` | `95b5b3b66b` | — | reverted | — |
| kggk:75 | v16-line copy of the HRMS developer's late-June master changes. | #920 | `75d4195722` | `75d4195722` | — | retained-from-master | — |
| kggk:76 | Whitespace-only edit of order_detail_report.py: removes one blank line and the trailing newline. | #926 | `777eae6618` | `777eae6618` | — | direct-cherry-pick | `fc51b2f` |
| kggk:77 | Adds two Script Reports on diamond loss booked through Employee IR. | #930 | `f374adb9bc` | `f374adb9bc` | — | squashed-port | `c7c46e4` |
| kggk:78 | Corporate-customer Excel exports on Order Form. | #928 | `a8d94cd038` | `a8d94cd038` | — | manual-logical-port | `48639f4` |
| kggk:79 | v16 query fixes in gke_hrms. | #931 | `a10114d4ae` | `a10114d4ae` | — | retained-from-master | — |
| kggk:80 | Fixes the IndentationError that unit 79 introduced in Manual Punch Entry.cancel_linked_records by re-indenting the OT Log and Personal Out… | #933 | `abf79b4a37` | `abf79b4a37` | — | retained-from-master | — |
| kggk:81 | Adds four manufacturing Script Reports. | #935 | `c480b15015` | `c480b15015` | — | squashed-port | `7d1eea5` |
| kggk:82 | Removes the OT Allowance Entry dashboard connection (links[]) to OT Log via link_fieldname ot_allowance_entry. | #938 | `737198076c` | `737198076c` | — | direct-cherry-pick | `a01fe9b` |
| kggk:83 | Adds four manufacturing Script Reports. | #943 | `cdc4ecc02d` | `cdc4ecc02d` | — | squashed-port | `967e312` |
| kggk:84 | Corporate order updates. | #944 | `132daca436` | `132daca436` | — | squashed-port + manual-logical-port | `d5c030e` `48639f4` |
| kggk:85 | Diamond Broken-Lost Report now values broken and missing diamonds at the item rate on the Finish Goods BOM, found via the latest finished T… | #947 | `9727741f1a` | `9727741f1a` | — | direct-cherry-pick | `8834d48` |
| kggk:86 | Reworks the PF Challan and ESIC Challan reports (account-wise totals panel and print helper) and adds a PF Contribution Report (EPF/EPS/EDL… | #948 | `7b09193242` | `7b09193242` | 00def16 | retained-from-master | — |
| kggk:87 | Changes how an Order Form is built from a Customer Order Form and updates the Proto Excel export. | #949 | `81ef3e9c30` | `81ef3e9c30` | — | direct-cherry-pick + manual-logical-port | `4f95b9a` `48639f4` |
| kggk:88 | Adds 8 new GKE Catalog script reports: Assortment Report, Department Sample Issue Receive Report, Department Wise Diamond Stock, Diamond St… | #961 | `6278f9019d` | `6278f9019d` | — | squashed-port + manual-logical-port | `bc5198d` `dd838b8` |
| kggk:89 | Four report fixes. | #963 | `5ad362ebaa` | `5ad362ebaa` | — | squashed-port | `450c974` |
| kggk:90 | OT and Night Shift Report JS. | #965 | `cb9acada3f` | `cb9acada3f` | — | squashed-port | `544ca41` |
| kggk:91 | Adds Product Hallmarking and Product Certification checkboxes to Product Return Form. | #967 | `35481e8661` | `35481e8661` | — | superseded | — |
| kggk:92 | Removes 'family_background' from the Employee Update on_submit field-copy list. | #968 | `8a3afd4d05` | `8a3afd4d05` | — | direct-cherry-pick | `9faadcb` |
| kggk:93 | Direct web-UI deletion of the broken gke_catalog/report/serial_no_detail_report folder that unit 39 (#833) created. | direct | `ca7004c4a9` | `ca7004c4a9` | — | direct-cherry-pick | `7d4c4fa` |
| kggk:94 | Adds a correctly named Serial No Detail Report (js/json/py). | #973 | `b6335658d6` | `b6335658d6` | — | reverted | — |
| kggk:95 | Direct web-UI deletion of the Product Return Form DocType folder (code, JS, API, e-invoice logic, test). | direct | `05d0bbb1a6` | `05d0bbb1a6` | — | manual-logical-port | `87d5e26` |
| kggk:96 | Introduces Product Return Order Form (the renamed, extended successor of Product Return Form) and Product Return Order, with metal, finding… | #977 | `c32d0cad7f` | `c32d0cad7f` | — | manual-logical-port | `87d5e26` |
| kggk:97 | Comments out the 'if self.is_jewlex_credit_note: return' early return in Product Return Order Form on_submit, so Jewelex credit-note forms… | #979 | `cccbb2c097` | `cccbb2c097` | 6a2ccb2cda c97b25f8a5 | retained-from-master | — |
| kggk:98 | Adds the "Today's Absent Employees" script report: active employees with no Employee Checkin on the chosen date, showing department, design… | #981 | `1d0f40b5db` | `1d0f40b5db` | — | squashed-port | `7b3cbb3` |
| kggk:99 | Order Form gains a Sales Type link and 'Repair' order and flow types. | #988 | `5142bd4ca5` | `5142bd4ca5` | — | manual-logical-port | `48639f4` `6934d29` |
| kggk:100 | Rounds Product Return Order BOM re-pricing values (metal and finding rate and amount, making amount, diamond and gemstone amounts) to 2 dec… | #991 | `5fe374c1af` | `5fe374c1af` | — | superseded | — |
| kggk:101 | Adds the 'Item Code Serial No Detail' script report (gke_catalog/report/item_code_serial_no_detail). | #995 | `52797c9e2e` | `52797c9e2e` | — | squashed-port | `5c488a9` |
| kggk:102 | Web-UI commit that deletes the serial_no_detail_report directory that unit 94 had added. | direct | `1bdd883466` | `1bdd883466` | — | reverted | — |
| kggk:103 | Adds Customer Gold/Diamond/Stone/Good/Finding Yes/No selects to the Order Form. | #996 | `9e18b4af8b` | `9e18b4af8b` | — | retained-from-master | — |
| kggk:104 | Adds nine script reports: Consumables Stocks, Diamond & Gemstone Conversion Detail, Finish Good Item Details, Main Slip Details, Manufactur… | #998 | `e050850422` | `e050850422` | — | squashed-port | `895cf9a` |
| kggk:105 | 'v16 fixes for reports'. | #999 | `31cbd4dc28` | `31cbd4dc28` | — | direct-cherry-pick | `5561eaf` |
| kggk:106 | Order Detail Report JS: the Company/Branch MultiSelect filters are commented out, and the dynamic filter options now use frappe.client.get_… | #1001 | `f86ab07a96` | `f86ab07a96` | — | squashed-port | `cd21123` |
| kggk:107 | Department IR Report JS: From/To Department become MultiSelectList filters fed by frappe.db.get_link_options('Department'), replacing Selec… | #1003 | `a3dfe421cf` | `a3dfe421cf` | — | squashed-port | `bb117c1` |
| kggk:108 | Large rework of Product Return Order and Product Return Order Form: Jewelex tag import, BOM recalculation, Serial No creation, GST/tax-cate… | #1005 | `582ab418b6` | `582ab418b6` | — | superseded | `87d5e26` |
| kggk:109 | Adds is_jewelex_tag (Check) and jewelex_tag (Data) to the Product Return Form Item child table. | #1007 | `16fec73930` | `16fec73930` | — | retained-from-master | — |
| kggk:110 | Removes a duplicate amended_from field definition from the Product Return Order DocType JSON. | #1010 | `40b04bc125` | `40b04bc125` | — | retained-from-master | — |
| kggk:111 | KGGK Item/BOM replication API update. | #1011 | `7fbb3e841e` | `7fbb3e841e` | — | retained-from-master | — |
| kggk:112 | Adds metal_weight, finding_weight, gemstone_weight, diamond_pcs, gemstone_pcs and other_weight (with a new section) to the Product Return F… | #1014 | `37499e78c5` | `37499e78c5` | — | retained-from-master | — |
| kggk:113 | Report updates. | #1016 | `46b754fa3a` | `46b754fa3a` | — | squashed-port | `1122c5a` |
| kggk:114 | Repair Order / Repair Order Form overhaul (BOM fetch and creation, Serial No creation, product-type renames, CAD order form timing, Datetim… | #1019 | `7b4922f857` | `7b4922f857` | — | manual-logical-port | `48639f4` |
| kggk:115 | Adds the Batch Dashboard report, turns the Department Stock Detailed Report category and sub-category filters into Attribute Value links, a… | #1018 | `d34dbe92ae` | `d34dbe92ae` | — | direct-cherry-pick | `8a94523` |
| kggk:116 | One-line JSON change: allow_bulk_edit=1 on the items Table field of Product Return Order Form. | #1020 | `046589febe` | `046589febe` | 6a2ccb2cda c97b25f8a5 | retained-from-master | — |
| kggk:117 | Order Detail Report: LEFT JOINs Item so the design image shows as a hover tooltip on the Design ID cell (HTML and inline JS built by the se… | #1021 | `a50376d183` | `a50376d183` | — | direct-cherry-pick | `b82a01d` |
| kggk:118 | Repair Order Form updates. | #1025 | `33bdbd1d0a` | `33bdbd1d0a` | — | manual-logical-port | `48639f4` |
| kggk:119 | Adds order_form.get_bom_detail(design_id, doc), which merges Item variant attributes with the latest Finished Goods BOM or the Item master… | #1029 | `fb172765bf` | `fb172765bf` | b86ee8f | retained-from-master | — |
| kggk:120 | Adds @frappe.whitelist() to order_form.get_bom_detail, which unit 119 added without it, so its frappe.call failed. | #1030 | `b2e1f1327f` | `b2e1f1327f` | — | retained-from-master | — |
| kggk:121 | Adds read-only Check fields hallmarking_amounts and certification_amounts on Product Return Order, copied from the form's product_hallmarki… | #1032 | `d0efb8cd08` | `d0efb8cd08` | — | superseded | — |
| kggk:122 | Passes a company code to the Jewelex credit-note API, mapped from the full company name to KGJPL or GEPL, in both the ProductReturnOrderFor… | #1038 | `2893736db8` | `2893736db8` | — | superseded | — |
| kggk:123 | Adds the submittable Cross Company Employee Transfer doctype and its Cross Employee Transfer Details child. | #1053 | `40bbae8d83` | `40bbae8d83` | — | retained-from-master | — |
| kggk:124 | 'roles permission fix for kg gk'. | #1057 | `939d28bccd` | `939d28bccd` | — | squashed-port | `5f1177c` `485f6f6` |
| kggk:125 | 'Added Precision': rounds the Product Return Order Form grand_total and the per-row diamond amount accumulation to 2 decimals in the manual… | #1051 | `41defdf99b` | `41defdf99b` | — | superseded | — |
| kggk:126 | New script report 'FG History' (GKE Catalog, ref_doctype Order Form). | #1060 | `205aea60e8` | `205aea60e8` | — | squashed-port | `a1371f4` |
| kggk:127 | Product Return Order Form changes. | #1072 | `1e3ff5808e` | `1e3ff5808e` | 6a2ccb2cda c97b25f8a5 | retained-from-master | — |
| kggk:128 | HR and Survey changes. | #1074 | `bba46393b9` | `bba46393b9` | — | retained-from-master | — |
| kggk:129 | RM Finding Item Details report: re-enables the Finding Size attribute pivot, matches Attribute Value Finding Type Weight rows also on custo… | #1076 | `638f440e5b` | `638f440e5b` | — | squashed-port | `e0643de` |
| kggk:130 | Replaces frappe.get_list calls that used SQL-function field strings ('date(time) as login_date' + group_by) for Outdoor Duty checkins, and… | #1077 | `4153192426` | `4153192426` | — | retained-from-master | — |
| kggk:131 | PF Challan report get_account_total_summary: re-indented with tabs. | #1079 | `8b2d1c88ed` | `8b2d1c88ed` | d1554adb64 | retained-from-master | — |
| kggk:132 | Order edit-item dialog: set_edit_order_form_detail now receives order_form_data and refills that same array in place, keeping the grid's da… | #1081 | `3699372492` | `3699372492` | — | retained-from-master | — |
| kggk:133 | Fixes the SyntaxError that unit 130 introduced in gke_hrms/api/attendance_api.py (the wo = ... | #1082 | `2299e0f89f` | `2299e0f89f` | — | retained-from-master | — |
| kggk:134 | Adds console.log('DESIGN ID =', design_id) to edit_item_documents() in Order JS. | #1084 | `e0c8c29de9` | `e0c8c29de9` | — | manual-logical-port | `48639f4` |
| kggk:135 | Order edit-item dialog loads the attribute table from the Order's design_id after dialog.show(), instead of from the dialog's item field be… | #1086 | `e26a0251f6` | `e26a0251f6` | — | retained-from-master | — |
| kggk:136 | Sales Order without Manufacturing Plan report: a Sales Order now counts as planned when any Manufacturing Plan Table row references it (NOT… | #1088 | `5679b355dc` | `5679b355dc` | — | squashed-port | `964ac3e` |
| kggk:137 | Order Form Detail: chain_weight is read-only for 'As Per Design Type' only when the category is not Mugappu. | #1091 | `9d165999ce` | `9d165999ce` | 7d355dc8b9 cba7b21106 | retained-from-master | — |
| kggk:138 | v16 query fixes across HR. | #1093 | `1ac7132715` | `1ac7132715` | — | retained-from-master | — |
| kggk:139 | Adds the Asset Item Master doctype (company/branch/warehouse/department plus a consumable items table) with autoname {abbr}-{branch}-ASM-##… | #1101 | `367bb9dd2c` | `367bb9dd2c` | — | retained-from-master | — |
| kggk:140 | create_bom_kggk (BOM before_validate hook) sends finding_size as 0 when empty in the finding_detail payload replicated to the KGGK site. | #1099 | `0b806e5de1` | `0b806e5de1` | — | manual-logical-port | `ed24d61` |
| kggk:141 | Updates four reports plus Branch Stock Summary. | #1103 | `a26b426d3c` | `a26b426d3c` | — | squashed-port | `f19a00f` |
| kggk:142 | Order Detail Report adds a 'Jewelex Batch No' column from Parent Manufacturing Order.jewelex_batch_no. | #1108 | `37606c2710` | `37606c2710` | — | squashed-port | `d21fc64` |
| kggk:143 | Adds two new script reports. | #1110 | `a67674c412` | `a67674c412` | — | squashed-port | `f7aa06d` |
| kggk:144 | Repair/Product Return flow update. | #1119 | `2ea8770fa2` | `2ea8770fa2` | — | manual-logical-port | `87d5e26` |
| kggk:145 | Rewrites the Employee Advance validation (calculate_working_days doc_event). | #1129 | `ba4549b284` | `ba4549b284` | — | retained-from-master | — |
| kggk:146 | Adds [tool.bench.frappe-dependencies] frappe = '>=15.0.0,<17.0.0' to pyproject.toml. | #1158 | `83ee74422b` | `83ee74422b` | — | retained-from-master | — |
| kggk:147 | Big sync of v16_develop_aerele into kggk_prod (29 commits). | #1123 | `ed9c4d3bbb` | `ed9c4d3bbb` | — | squashed-port + manual-logical-port | `7f39ed4` `083c594` `48639f4` `87d5e26` |
| kggk:148 | Adds the Department Wise Daily Attendance and Department Wise Daily Present reports with scheduled manager mails, plus the salary register… | #1172 | `7d75d56425` | `7d75d56425` | — | retained-from-master | — |
| kggk:149 | Adds the Custom Field 'Purchase Order Item-custom_copy_bom' (Copy BOM, Link to BOM) to gke fixtures. | #1170 | `63b1bbcd8c` | `63b1bbcd8c` | — | retained-from-master | `26bfda3` |
| kggk:150 | Cross Company Employee Transfer update: target_site-driven REST calls, holiday list as a transferable property, reports_to taken from new_v… | #1175 | `440dc086d6` | `440dc086d6` | — | retained-from-master | — |
| kggk:151 | Three report changes. | #1176 | `e699b95344` | `e699b95344` | — | squashed-port | `fc388a1` `fe31a17` |
| kggk:152 | Moves the department report mail crons to 08:30/10:30, adds a manager guard and hardcoded CC lists to the mailers, and tweaks the report JS. | #1182 | `624b695fff` | `624b695fff` | — | retained-from-master | — |
| kggk:153 | Production Report rework: per-department Gross Wt pivot columns from the latest main MWO per PMO, WIP MWO rows, order-type resolution throu… | #1185 | `177ca4bdd1` | `177ca4bdd1` | — | squashed-port + manual-logical-port | `a03131d` `083c594` |
| kggk:154 | Production Report fixes: manufacturer filter removed, WIP MWO query excludes SN%/sample/consumable items and resolves order type via Order,… | #1191 | `dd4aa34012` | `dd4aa34012` | — | squashed-port | `00d6da5` `fe31a17` |
| kggk:155 | Rewrites the KGGK Jewelex tally data source: removes the pyodbc/SQL query and the cache file, and fetches rows from an HTTP order-tally API… | #1203 | `d090a12db4` | `d090a12db4` | — | not-required | `3a509ec` `fe31a17` |
| kggk:156 | In the KGGK Jewelex tally compare mode, 'ERP Order Complete' becomes an Int count of fully submitted PMOs (0 when none) instead of a sales-… | #1205 | `3c6741b515` | `3c6741b515` | — | not-required | `5533247` `fe31a17` |
| kggk:157 | Adds the Attendance Adjustment Tool (submittable doctype, module GKE HRMS), its child table Adjustment Details, and a large API module gke_… | #1209 | `ed98efe701` | `ed98efe701` | — | direct-cherry-pick | `e168048` |
| kggk:158 | Adds overrides/salary_structure_assignment.py with CustomSalaryStructureAssignment, which overrides HRMS v16's _get_component_eval_context… | #1208 | `50145bd6f9` | `50145bd6f9` | — | direct-cherry-pick + manual-logical-port | `bcbe1c3` `083c594` |
| kggk:159 | Fixture-only change to fixtures/custom_field.json. | #1194 | `3629b4c6bc` | `3629b4c6bc` | — | retained-from-master | `26bfda3` |
| kggk:160 | Fixes to five reports. | #1217 | `e2b103762d` | `e2b103762d` | — | squashed-port | `6f32e00` `fe31a17` |
| kggk:161 | Adds Order Date from/to, Jewelex Order No and Jewelex Batch No filters to the 'KGGK Jewelex - ERP Order Tally' report. | #1224 | `d1c7fe32d8` | `d1c7fe32d8` | dce267ec30 | not-required | `a850c8f` `fe31a17` |
| kggk:162 | Adds two script reports. | #1229 | `35e21d2eba` | `35e21d2eba` | — | squashed-port | `2f531e0` |
| kggk:163 | The Manufacturing Operation autoname hook (gke_order_forms/doc_events/manufacturing_operation.py) now produces MOP-YYMM-XXXXXX: six charact… | #1235 | `fc4caf290e` | `fc4caf290e` | — | direct-cherry-pick | `8c59e22` |
| kggk:164 | Brings the attendance API (gke_hrms/api/attendance.py), the loan_application doc event and the ESIC challan and PF contribution reports in… | #1240 | `d55b2445ba` | `d55b2445ba` | — | retained-from-master | — |
| kggk:165 | Report fixes. | #1255 | `e986264cdb` | `e986264cdb` | — | squashed-port | `13559f5` |
| kggk:166 | OT Allowance Entry adds Employee.old_employee_code to its attendance query. | #1272 | `92071f775c` | `92071f775c` | 820ded9 | retained-from-master | — |
| kggk:167 | Renames the setting type 'Close' / 'Close Setting' to 'Nova Glow' / 'Nova Glow Setting' in five places: the CAD Report restricted-user sett… | #1278 | `3d05870fd3` | `3d05870fd3` | — | direct-cherry-pick + manual-logical-port | `e0e6adb` `ed24d61` |
| kggk:168 | Exact revert of #1278: restores 'Close' / 'Close Setting' in the CAD Report, item.py replication gates, Targets Form, Retailer Survey and O… | #1280 | `3ec2f3376d` | `3ec2f3376d` | — | reverted | — |
| kggk:169 | Revert of the revert: re-applies the #1278 Close -> Nova Glow rename unchanged. | #1283 | `c1f7ed5f7b` | `c1f7ed5f7b` | — | reverted | — |
| kggk:170 | The net first-parent change has four parts. | #1288 | `e0b01c1f35` | `e0b01c1f35` | — | manual-logical-port | `48639f4` `ed24d61` `87d5e26` |
| kggk:171 | Advance Bagging Report from MR re-enables the Alternative Item column. | #1293 | `a264410c5b` | `a264410c5b` | — | squashed-port | `8b4e46d` |
| kggk:172 | Adds the Employee Signature doctype (employee, branch, route, is_published, naming series EMP-SIG-) and its child table Employee Signature… | #1297 | `98ec5fbcad` | `98ec5fbcad` | 8b1b9b3 | retained-from-master | — |
| kggk:173 | Department-wise Daily Attendance and Department-wise Daily Present report mailers: the CC list becomes one fixed HR mailbox plus the HR use… | #1328 | `9f631325a5` | `9f631325a5` | 757b589cdf | retained-from-master | — |
| kggk:174 | OT Allowance Entry: fetched OT rows are sorted by old employee code then attendance date (previously by date only), grouping rows per emplo… | #1335 | `cc654ee00a` | `cc654ee00a` | 33fd0160fa | retained-from-master | — |
| kggk:175 | Personal-out deduction clamped at shift end: a new correlated pol_deduction_subquery sums Personal Out Log durations with in_time capped at… | #1350 | `361835e1ad` | — | 2160feb366 af896a3cb5 | retained-from-master | — |
| kggk:176 | In Monthly In-Out Log's personal-out deduction subquery, a Personal Out Log whose out_time is already past shift end now contributes 0. | #1357 | `e7f8cf3fcb` | — | — | manual-logical-port | `be0c216` |
| kggk:177 | Four gke_catalog report changes. | #1360 | `3d6c61ac92` | — | — | squashed-port | `c9c77f4` |
| gkp:1 | GK-live PR into gurukrupa-prod with three parts. | #1356 | — | `20d3c28c8c` | af896a3cb5 | manual-logical-port | `be0c216` `dd838b8` |
| gkp:2 | Holiday Punch rewrite. | #1358 | — | `c94f0475c5` | 70308a6 | retained-from-master | — |

## Consolidated port commits

| Commit | Cluster | Files | Ported-from (production units) |
|---|---|---:|---|
| `083c594` | c1-hooks-patches-pyproject | 3 | #645, #651, #749, #769, #789, #867, #873, #879, #920, #948, #1158, #1123, #1172, #1182, #1185, #1208 |
| `be0c216` | c6-hrms | 12 | #666, #789, #920, #931, #933, #948, #1053, #1074, #1077, #1079, #1093, #1101, #1175, #1272, #1335, #1350, #1357, #1356, #1358 |
| `48639f4` | c2-order-family | 10 | #631, #644, #650, #653, #749, #750, #752, #758, #759, #760, #762, #763, #764, #770, #772, #774, #792, #864, #877, #885, #888, #890, #900, #902, #908, #914, #913, #916, #917, #928, #944, #949, #988, #996, #1019, #1025, #1029, #1030, #1081, #1084, #1086, #1091, #1123, #1288 |
| `ed24d61` | c3-pricing-sales-hooks | 5 | #650, #856, #858, #861, #862, #867, #871, #872, #873, #879, #882, #883, #895, #901, #911, #1011, #1099, #1278, #1280, #1283, #1288 |
| `87d5e26` | c4-product-return | 14 | #835, #850, #977, #979, #991, #1005, #1007, #1010, #1014, #1020, #1032, #1038, #1051, #1072, #1119, #1123, #1288 |
| `dd838b8` | c7-catalogue-survey | 6 | #961, #1074, #1356 |
| `6934d29` | c5-revise-price-lists | 7 | #645, #651, #746, #817, #819, #822, #825, #988, #1123 |

## Decision commits

| Commit | What |
|---|---|
| `26bfda3` | fix(fixtures): curate custom_field.json and doctype.json for gk_prod |
| `485f6f6` | fix(report permissions): restore the GK roles that #1057 removed |
| `7a2da24` | fix(product return): push only Jewelex-tag and KGGK-serial returns to KGGK |
| `fe31a17` | exclude: drop the KGGK Jewelex - ERP Order Tally report |
| `1275046` | fix(v16): report queries and scripts that v16 rejects |
| `145b2de` | fix(v16): import failures and DocType metadata in master-only code |
| `f57144d` | fix(reports): guard fields GK sites may lack, drop fields that do not exist |
| `670242a` | fix(v16): load report filter options without "distinct" field strings |
| `f482786` | fix(security): require login for the Attendance Adjustment Tool endpoints |
| `de33ad3` | fix(fixtures): order custom fields so a missing app only skips its own rows |
| `ecd9b53` | fix(fixtures): keep GK's current layout and flags on 32 fields |
