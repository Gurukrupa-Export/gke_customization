# 05 — Rejected commit register

Every unit that was **not** carried into gk_prod, with its member commits and the reason. Nothing was dropped silently: each skip below was either proven by the dry run (removing it leaves the final tree identical) or decided at the 2026-10-02 business checkpoint.

| Decision | Units | Commits |
|---|---:|---:|
| SKIP_ALREADY_IN_MASTER | 50 | 125 |
| SKIP_PATCH_EQUIVALENT | 7 | 15 |
| SKIP_SUPERSEDED | 15 | 44 |
| SKIP_REVERTED | 12 | 30 |
| SKIP_UNRELATED | 3 | 9 |

## SKIP_ALREADY_IN_MASTER

_master already has the change (same content reached master through its own PRs); replaying it would only duplicate it._

### kggk:7 — fix: add to post_model_sync (#651)

- **SHA:** `b297393035231c887579a4d560a122f64b788ea6` (PR #651), 2 commit(s): `bf903bc944`, `b297393035`
- **Message:** fix: add to post_model_sync (#651)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Adds [pre_model_sync] and [post_model_sync] section headers to patches.txt so that gc_ration_master runs after schema sync.
- **Reason:** Master's patches.txt already contains the identical '[pre_model_sync]' and '[post_model_sync]' headers, added with master's nova-glow patch. The unit's only lasting effect is where unit 4's line sits, and unit 4's d_path_notes carry that. The script reports absorbed=false only because the hunk's context line (the gc patch) is missing from master.

### kggk:15 — fix: remove unnecessary argument in timesheet retrieval (#758)

- **SHA:** `3aa12e00e1026a70bee8f9752f6e17da79281cab` (PR #758), 2 commit(s): `4167adcfdf`, `3aa12e00e1`
- **Message:** fix: remove unnecessary argument in timesheet retrieval (#758)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Removes the stray third positional argument from frappe.get_doc('Timesheet', {'order': ...}, 'name') in Order.on_update_after_submit (Approved branch).
- **Reason:** Master made the identical change at the same call site in cc4d793 (2026-08-18); see master order.py:118. d_hunk_containment is 1/1. absorbed=false only because of the tab/space reformat.

### kggk:25 — 18-05-2026 bhavika's updates in version-16 (#789)

- **SHA:** `421656ee9e04bbfa676cb0d8ee5e935f00a15d0d` (PR #789), 2 commit(s): `6dc2adec05`, `421656ee9e`
- **Message:** 18-05-2026 bhavika's updates in version-16 (#789)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** v16 sync of the HR developer's master work across 37 files.
- **Reason:** Already in master. 22 of the 37 paths are 'same', meaning kggk head equals master. For the 15 'both' paths, a line-level check found every non-comment added line in master, except 31 lines in ot_allowance_entry.py that are multi-line formatting of expressions master holds in compact form. Lines the unit removed that master still shows are duplicates of the same text elsewhere in those files. The remaining kggk-vs-master residue in these files is whitespace or comes from later units. There are no MECH paths.

### kggk:31 — Add Table For Diamond Price List (#810)

- **SHA:** `fa7ea703a538a9c9cedde656467a1fb53a5df727` (PR #810), 2 commit(s): `0cc916b56d`, `fa7ea703a5`
- **Message:** Add Table For Diamond Price List (#810)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Adds the child DocType Diamond Price List Table under GKE Order Forms.
- **Reason:** absorbed=true. Master's files are byte-identical, and the leaf's patch-id equals master commit 2efb4021ba.
- **Master equivalent:** 2efb4021ba

### kggk:33 — updating revise making charge price list (#817)

- **SHA:** `b0b2aeec211b1379b42ccd8aa79d70c5040f54b9` (PR #817), 3 commit(s): `4c50778a66`, `047a10398c`, `b0b2aeec21`
- **Message:** updating revise making charge price list (#817)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Revise Making Charge Price: before_save becomes before_insert.
- **Reason:** Already in master. Of the 54 non-comment Python lines added, all are in master except `making_charge_price_doc.metal_type = self.metal_touch`, a bug master replaced with correct assignments. The JSON part was an intermediate broken state, finished by unit 36, and its final shape equals master's. The internal merge only carried earlier units into the PR branch.
- **Superseded by:** 36

### kggk:34 — updating Revise diamond changes (#819)

- **SHA:** `d25f9f16886dc094bb1bfc3de52be23bf5c4a6e4` (PR #819), 3 commit(s): `144d907e27`, `9c1dff51bc`, `d25f9f1688`
- **Message:** updating Revise diamond changes (#819)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Revise Diamond Price List crate_price_list now writes stone_code and the outright/outwork handling-charge percentage and rate under their standard fieldnames, without the custom_ prefix, on new Diamond Price List documents.
- **Reason:** Already in master: d_hunk_containment is 3/3, and master's active code (revise_diamond_price__list.py:342-352) writes the same fieldnames. survival 0.0 only reflects unit 38 commenting out this path and moving the code.
- **Superseded by:** 38

### kggk:36 — Updating Revise Making Charges doctype (#822)

- **SHA:** `93da164324070955c8d8315bca2fc8a627609ce9` (PR #822), 4 commit(s): `97cd594214`, `a564de5ee6`, `0ea31da40c`, `93da164324`
- **Message:** Updating Revise Making Charges doctype (#822)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Restores the Revise Making Charge Price DocType JSON to a consistent submittable parent: customer, setting type, metal type and touch, date, the item and finding tables, the from/to gold-rate fields, and allow_import.
- **Reason:** Already in master. 17 of 18 hunks are absorbed; the remaining one is the modified timestamp, and master's is newer (2026-07-22 vs 2026-02-10). The internal merges only synced the base and remote branches.

### kggk:43 — V16 dharm (#850)

- **SHA:** `c24d209016f74ea4ef0b45c12311e3d10f99f859` (PR #850), 3 commit(s): `5b0f901a97`, `424f28b34c`, `c24d209016`
- **Message:** V16 dharm (#850)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Adds Credit Note Type (prompt-named master) and Credit Note Subtype (subtype_name + parent_type link to Credit Note Type, rate_type Invoice Rate/Current Rate, named subtype-parent) doctypes.
- **Reason:** Functionally already in master: controller, JS, test and init files are identical (path class same) and the JSONs match on fields, naming and permissions. The only differences are doctype metadata (Credit Note Type: kggk has track_changes=1, master has allow_rename=1; a section-break fieldname; timestamps/owner), which the script's hunk check counts as not absorbed.

### kggk:49 — V16 dharm (#864)

- **SHA:** `4c231fda6b596968df0185ed0389528fe9a23fd6` (PR #864), 3 commit(s): `b71d507e98`, `3001454cdc`, `4c231fda6b`
- **Message:** V16 dharm (#864)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Repair Order / Repair Order Form updates: CAD order form gets total_rows=1 and 'New Design' design type, slash-stripping of attribute names, sizer_type dropped from the hidden-attribute list, create_bom copies the serial-number BOM (serial_no_bom) when present, get_bom_details returns serial_no_bom/bom/diamond_quality, the form JS sets tag_no and serial_no_bom on rows; JSON adds serial_no_bom to…
- **Reason:** Every surviving effect of this unit is in master (path class same for six files; the seventh differs only by a trailing newline). Nothing to port. Latent bug present in both lines: get_bom_details raises UnboundLocalError (serial_no_bom) when called without a serial number.

### kggk:50 — Create item and bom in uat kggk site (#867)

- **SHA:** `c72dab2608366913d50babbeefe0da7cc4f6b969` (PR #867), 2 commit(s): `6e963fc210`, `c72dab2608`
- **Message:** Create item and bom in uat kggk site (#867)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Adds create_item_kggk and create_bom_kggk to gke_order_forms/doc_events/item.py and wires them as Item and BOM before_validate hooks in hooks.py.
- **Reason:** Master already has this feature. Master commit ece7b4e ('Item Creation Code', 2026-07-28, same developer) ported create_item_kggk/create_bom_kggk, the Data Migration in KGGK doctype and the Item/BOM before_validate hooks. Master head wires the same hooks with the same gating (setting_type Nova Glow, bom_type Template, from_site/to_site set). This unit's own specifics (hardcoded URL/token, the 'Close' filter) are also gone at kggk head, replaced by units 57 and 111 and the Nova Glow rename. As merged, the unit was broken: item.py had no 'import requests', so every qualifying save raised NameError. Unit 52 fixed that the next day. Later kggk-vs-master differences in these functions come from other units (black_beed naming in unit 59, a finding_size default, has_variants omission) and are classified there. The feature exists to feed the KGGK site from the GK site; GK wants it, and master ha
- **Superseded by:** 57, 111, 167, 169

### kggk:51 — V16 dharm (#869)

- **SHA:** `0ccb08995b8b9b81c2b04c59f489829c5f3846c1` (PR #869), 3 commit(s): `d0e61af457`, `e37e7af214`, `0ccb08995b`
- **Message:** V16 dharm (#869)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Repair Order changes.
- **Reason:** path_classes is 'same' for all three files, so master head equals kggk head. Every line of this unit that survives (75-100%) is therefore in master. Spot-checked: the sketch_items guard, the design_image_1/stone_changeable/metal_colour copies, 'Template and Variant', the JSON property changes and the refresh() prefill.

### kggk:52 — Sb aerele l (#871)

- **SHA:** `1d04e98ba85393fb1e43b1161ecf7bfc4df25c19` (PR #871), 3 commit(s): `0ad99e8b69`, `24cfed6505`, `1d04e98ba8`
- **Message:** Sb aerele l (#871)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Adds 'import requests' at the top of doc_events/item.py.
- **Reason:** d_hunk_containment is 1/1 absorbed, and master item.py line 2 is 'import requests'. This is a fix to unit 50, which is itself in master.
- **Master equivalent:** 2959ad2285 a646f7f74d c6083d123e

### kggk:53 — Sb aerele l (#872)

- **SHA:** `7a1ea3d7b8a3c33ad314580dc36168b320aaa554` (PR #872), 3 commit(s): `edbf20cd47`, `75f6702ab6`, `7a1ea3d7b8`
- **Message:** Sb aerele l (#872)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Two small changes.
- **Reason:** item.py hunks are 2/2 absorbed: master create_bom_kggk lines 971 and 985 are the same commented lines. repair_order.py has path class 'same' (master == kggk head), and the tag_no branch survives (survival 1.0) inside master's evolved version.

### kggk:58 — update Item in GKgk (#882)

- **SHA:** `41179f265deb8a0d2587d46d9867c1885d3f642c` (PR #882), 2 commit(s): `90f32340c3`, `41179f265d`
- **Message:** update Item in GKgk (#882)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** create_item_kggk: the PUT (update) payload leaves out variant_of; the POST (create) payload still carries it.
- **Reason:** Master already leaves variant_of out of updates, in a corrected and extended form. Nothing extra from this unit needs carrying, and kggk's string-membership form should not be ported.

### kggk:62 — Sb aerele l (#888)

- **SHA:** `31a2af21e9041afc9de1eff7a94a7d8230583ab3` (PR #888), 3 commit(s): `df79853eed`, `fd54dc7c40`, `31a2af21e9`
- **Message:** Sb aerele l (#888)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Order.on_update_after_submit: when an Order raised for a repair (is_repairing, repair_order set) reaches 'Approved', it writes the Order's item and new BOM back to the Repair Order (new_item_code, new_bom) and sets the Repair Order's workflow_state to Approved via frappe.db.set_value.
- **Reason:** Master has the same logic in Order.on_update_after_submit, as a superset with the product_bom write. The hunk was not textually absorbed only because master uses tab indentation and has the extra line. The workflow_state is set directly with db.set_value, bypassing workflow transition checks; master does the same.

### kggk:63 — V16 dharm (#890)

- **SHA:** `a2df7b513a04f5c38da1068b8445e74fdf63f653` (PR #890), 3 commit(s): `4712df710f`, `4c09e0b674`, `a2df7b513a`
- **Message:** V16 dharm (#890)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Order doctype: adds a 'repair_order' Link (fetch_from cad_order_form.repair_order) under a new Tab Break at the end of the form.
- **Reason:** Only the layout differs from master; the field and its behaviour are already there. The title match with master 06b208f6a5 is coincidental: that commit is an unrelated 5-line deletion from April.
- **Master equivalent:** 06b208f6a5

### kggk:65 — Update for BOM API (#895)

- **SHA:** `2f68217c736c10944d2463ded3e863e5f450e195` (PR #895), 2 commit(s): `841c098fed`, `2f68217c73`
- **Message:** Update for BOM API (#895)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** create_bom_kggk stops sending company in the BOM payload, so the remote BOM takes the remote site's default company.
- **Reason:** absorbed=true is confirmed: master item.py create_bom_kggk has '# "company": doc.company,'.

### kggk:66 — updating Api for Item Creation (#901)

- **SHA:** `947cf74b689dacf5a0e3916fb21535e461ceb335` (PR #901), 2 commit(s): `66fc8b5d1d`, `947cf74b68`
- **Message:** updating Api for Item Creation (#901)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** create_item_kggk adds master_bom to the Item payload sent to KGGK.
- **Reason:** The behaviour survives at kggk head only through unit 111's rewritten line; this unit's exact line now sits in a commented-out copy (survival 0.0). Master's active create_item_kggk already sends master_bom.
- **Superseded by:** 111

### kggk:69 — update Data Migration Single Doc (#911)

- **SHA:** `24f9193fe9c384135d79a607f6de3def3003e732` (PR #911), 2 commit(s): `5401ac8b7f`, `24f9193fe9`
- **Message:** update Data Migration Single Doc (#911)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Data Migration in KGGK: adds a 'Get Pricing Details' section with from_site_1, and a 'User Details' section with api_key and api_secret, both plain Data fields.
- **Reason:** Every field this unit adds exists in master's data_migration_in_kggk.json with the same fieldtype. Master's JSON is a superset (it adds MWO/CAD site, testing-sync, PRF and serial-no sections).

### kggk:70 — Shrutib aerele (#908)

- **SHA:** `174e9f1249e48daf32234388a5d175d8c721a666` (PR #908), 4 commit(s): `b3ff744ba9`, `6d9313248d`, `90a123f5ac`, `174e9f1249`
- **Message:** Shrutib aerele (#908)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** 'Update Code From GkExport': replaces kggk's order_form.py and order_form.js wholesale with the gkexport (v15) code.
- **Reason:** Blob identity: after this unit, order_form.py (d5728a1) and order_form.js (f86f381) equal refs/recon/base/mb's blobs and master's as of 2026-06-25. Master head differs from them only by its own later commits (py +226/-3, js +22/-1); the 3 removed lines are commented out at kggk head too. Nothing in this unit is missing from master. Note for earlier batches: this unit wiped the order_form.py/js edits of kggk units #631, #653, #749, #762, #763, #764, #770, #772, #774 and #792. Any trace of them at kggk head was re-added by later units, so their own D-path effect on these files is superseded.

### kggk:80 — update in manual_punch_entry py file (#933)

- **SHA:** `abf79b4a3780262b84aec1d9146dcc8b10a857f8` (PR #933), 2 commit(s): `33aeed7402`, `abf79b4a37`
- **Message:** update in manual_punch_entry py file (#933)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Fixes the IndentationError that unit 79 introduced in Manual Punch Entry.cancel_linked_records by re-indenting the OT Log and Personal Out Log qb queries with tabs.
- **Reason:** absorbed=true is confirmed: master's cancel_linked_records is the identical tab-indented qb version. It only matters relative to unit 79, which is also skipped.

### kggk:97 — Sb aerele l (#979)

- **SHA:** `cccbb2c097b484445e78446dcf86132a834281ca` (PR #979), 4 commit(s): `4e8ce12da9`, `bf4005eea4`, `49bfc9ff51`, `cccbb2c097`
- **Message:** Sb aerele l (#979)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Comments out the 'if self.is_jewlex_credit_note: return' early return in Product Return Order Form on_submit, so Jewelex credit-note forms also create Product Return Orders.
- **Reason:** The behaviour is already in master: master's PROF on_submit has the same commented-out guard ('# if self.yu: return'), which came with the 2026-07-31 import. The literal hunk differs only because #1005 (unit 108) rewrote the comment text, which is why the script reported it as not absorbed. title_master_match (6a2ccb2/c97b25f) points to unrelated later commits with a similar title.
- **Superseded by:** 108
- **Master equivalent:** 6a2ccb2cda c97b25f8a5

### kggk:109 — V16 dharm (#1007)

- **SHA:** `16fec73930e4f77a48375ef6701cb54b214f3a75` (PR #1007), 3 commit(s): `1e1cbd424f`, `736e1f82c5`, `16fec73930`
- **Message:** V16 dharm (#1007)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Adds is_jewelex_tag (Check) and jewelex_tag (Data) to the Product Return Form Item child table.
- **Reason:** Master's product_return_form_item.json, via 6c9838c, has both fields. is_jewelex_tag is identical, and jewelex_tag adds depends_on is_jewelex_tag==1, a later master refinement. The 0/2 hunk containment reflects position and that refinement, not missing behaviour.

### kggk:110 — Update json of Prodcut Return Order (#1010)

- **SHA:** `40b04bc125fe72900e8341bd12595048d2d72603` (PR #1010), 2 commit(s): `cc10c5f82c`, `40b04bc125`
- **Message:** Update json of Prodcut Return Order (#1010)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Removes a duplicate amended_from field definition from the Product Return Order DocType JSON.
- **Reason:** absorbed=true: master's product_return_order.json already has exactly one amended_from, and so does kggk head.

### kggk:111 — KGGK item Migration API Update (#1011)

- **SHA:** `7fbb3e841e9cd8209c32f64c34df6253ed32a965` (PR #1011), 2 commit(s): `4c6705d7c8`, `7fbb3e841e`
- **Message:** KGGK item Migration API Update (#1011)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** KGGK Item/BOM replication API update.
- **Reason:** Every non-comment line this unit added exists in master: 302 of the 304 missing lines are comments, and the other two are JSON field_order/modified noise. No removed line survives in master. All 8 new Data Migration in KGGK fields are identical in master. Master got the change via ece7b4e ('Item Creation Code', 2026-07-28, same author) and later dc3ffe4, then extended it with remote file sync and testing-sync settings.

### kggk:112 — Sb aerele l (#1014)

- **SHA:** `37499e78c51711a9501e7cb6674ce99cd303cb8d` (PR #1014), 3 commit(s): `869d62765b`, `b3b1493131`, `37499e78c5`
- **Message:** Sb aerele l (#1014)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Adds metal_weight, finding_weight, gemstone_weight, diamond_pcs, gemstone_pcs and other_weight (with a new section) to the Product Return Form Item, and moves diamond_weight into that section.
- **Reason:** All 7 added fields are identical in master, and master's field_order around section_break_bynu matches the unit exactly (via 6c9838c).

### kggk:116 — Sb aerele l (#1020)

- **SHA:** `046589febe548d240c961cee2cb05f5cdcceef30` (PR #1020), 3 commit(s): `9136bc77da`, `8194e9073e`, `046589febe`
- **Message:** Sb aerele l (#1020)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** One-line JSON change: allow_bulk_edit=1 on the items Table field of Product Return Order Form.
- **Reason:** absorbed=true, and the code confirms it: master's product_return_order_form.json already sets allow_bulk_edit:1 on fieldname items (d_hunk 1/1 absorbed). Nothing needs carrying.
- **Master equivalent:** 6a2ccb2cda c97b25f8a5

### kggk:119 — update Repair order form (#1029)

- **SHA:** `fb172765bfb2ae34150553a980b996c65aedc1de` (PR #1029), 3 commit(s): `278d75d0ff`, `ac6d358668`, `fb172765bf`
- **Message:** update Repair order form (#1029)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Adds order_form.get_bom_detail(design_id, doc), which merges Item variant attributes with the latest Finished Goods BOM or the Item master BOM fields.
- **Reason:** Master already has an identical get_bom_detail (same body, @frappe.whitelist), added by master commit b86ee8f in #1035, at a different position after get_customer_orderType. d_hunk shows 0/1 only because of that position. The JS hunks were later removed by unit 170, and repair_order_form.js is identical in kggk and master.
- **Superseded by:** 170
- **Master equivalent:** b86ee8f

### kggk:120 — Update order_form.py (#1030)

- **SHA:** `b2e1f1327fd2783eba212c25b59f9dd461c5484d` (PR #1030), 2 commit(s): `4a3b653b75`, `b2e1f1327f`
- **Message:** Update order_form.py (#1030)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Adds @frappe.whitelist() to order_form.get_bom_detail, which unit 119 added without it, so its frappe.call failed.
- **Reason:** Master's get_bom_detail already has @frappe.whitelist(). The hunk is not textually absorbed only because the function sits at a different position in master.

### kggk:123 — 01-08-2026 cross company added and resignation json file (#1053)

- **SHA:** `40bbae8d832be7dec3c931bbdfcdfe4af37bf900` (PR #1053), 2 commit(s): `42f2b468d8`, `40bbae8d83`
- **Message:** 01-08-2026 cross company added and resignation json file (#1053)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Adds the submittable Cross Company Employee Transfer doctype and its Cross Employee Transfer Details child.
- **Reason:** Every path this unit touched has the same blob on the kggk and master heads, except cross_employee_transfer_details.json. That file differs only because master's copy has duplicated 'modified'/'modified_by' keys from a merge; its fields are identical. The unit's own early code (hardcoded UAT URL, fixed holiday list) was rewritten by units 150/152, and master already has those versions.
- **Superseded by:** 150, 152

### kggk:127 — Shubham gke v16 (#1072)

- **SHA:** `1e3ff5808e2915c505a4ce8e991cee60219251dd` (PR #1072), 5 commit(s): `a741c79cf3`, `e74dd7f7ff`, `e9db578e21`, `9cc2f68570`, `1e3ff5808e`
- **Message:** Shubham gke v16 (#1072)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Product Return Order Form changes.
- **Reason:** Every hunk that survives at kggk head is already in master: d_hunk shows .py 8/8, _api.py 5/5 and .js 4/4 absorbed. The JSON fields is_sale, ref_company and old_product_return_order_form, editable metal_purity and the naming rule are present in master. The one non-absorbed hunk, the product_return_order.py controller disable, was undone by unit 144 (2ea8770, #1119).
- **Superseded by:** 144
- **Master equivalent:** 6a2ccb2cda c97b25f8a5

### kggk:128 — 07-08 update in gke_hrms and gke_survey module (#1074)

- **SHA:** `bba46393b9d031d884f928dda4accee5e4b0352d` (PR #1074), 2 commit(s): `1006e44f5d`, `bba46393b9`
- **Message:** 07-08 update in gke_hrms and gke_survey module (#1074)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** HR and Survey changes.
- **Reason:** Everything from this unit that survives on GK live is already in master. The 39 'same' paths are identical blobs on the kggk and master heads. The survey runner and response JSON at the kggk head equal this unit's version, and master holds a superset. The unit's get_list regressions in attendance.py, attendance_api.py, monthly_in_out_log.py, manual_punch_entry.py and ot_allowance_entry.py were reverted by units 130 and 138. pf_challan_report.py was rewritten by units 131, 138 and 139. holiday_punch.py at the kggk head is still this unit's rewrite, but GK live replaced it through gkp2 (#1358) with master's version.
- **Superseded by:** 130, 131, 138, 139, 145, 164

### kggk:130 — 08-08-2026 update in gke_hrms api file (#1077)

- **SHA:** `415319242623ec1f00dbe3e7b67f7cb217b7bb68` (PR #1077), 2 commit(s): `eee0bd2d27`, `4153192426`
- **Message:** 08-08-2026 update in gke_hrms api file (#1077)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Replaces frappe.get_list calls that used SQL-function field strings ('date(time) as login_date' + group_by) for Outdoor Duty checkins, and the Holiday child-table get_list, with parametrized frappe.db.sql.
- **Reason:** Master already has the same code. attendance.py, attendance_api.py and monthly_summery.py are byte-identical at master and kggk heads. monthly_in_out_log.py has the same two SQL blocks on master, differing only in tab vs space indentation (d_hunk 2/2). Master got these through its own commits 178a333 (2026-09-03), 55cff56 (2026-09-12) and 5dd0c13 (2026-09-29). leftover_d was flagged only because the unit's interim broken attendance_api.py hunk and the whitespace differences do not apply cleanly to master.
- **Superseded by:** 133

### kggk:132 — Sb aerele l (#1081)

- **SHA:** `36993724921163ab421cbd8a0d984bbb1e0f2946` (PR #1081), 3 commit(s): `2e08a17730`, `1daa5875a8`, `3699372492`
- **Message:** Sb aerele l (#1081)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Order edit-item dialog: set_edit_order_form_detail now receives order_form_data and refills that same array in place, keeping the grid's data reference, instead of reassigning df.data.
- **Reason:** absorbed=true. Master dfb9be0 ('Update set_edit_order_form_detail In Order', same author, 2026-08-11) contains the identical function.

### kggk:133 — 10-08-2026 update in attendance_api py file (#1082)

- **SHA:** `2299e0f89f2d6a2d0b4113b0343386863abc2431` (PR #1082), 2 commit(s): `5dcf69aea2`, `2299e0f89f`
- **Message:** 10-08-2026 update in attendance_api py file (#1082)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Fixes the SyntaxError that unit 130 introduced in gke_hrms/api/attendance_api.py (the wo = ...
- **Reason:** absorbed=true. attendance_api.py is identical at master and kggk heads, and master has the corrected form.

### kggk:135 — Update Order  (#1086)

- **SHA:** `e26a0251f6c4d88635887dcceba17564672a6168` (PR #1086), 2 commit(s): `4c488f6520`, `e26a0251f6`
- **Message:** Update Order  (#1086)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Order edit-item dialog loads the attribute table from the Order's design_id after dialog.show(), instead of from the dialog's item field before showing.
- **Reason:** absorbed=true. Master dfb9be0 contains the identical hunk.

### kggk:138 — 12-08-2026 update gke_hrms file (#1093)

- **SHA:** `1ac7132715d32dda31b3e91386cdedf443eb6af5` (PR #1093), 2 commit(s): `0cd5bad72a`, `1ac7132715`
- **Message:** 12-08-2026 update gke_hrms file (#1093)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** v16 query fixes across HR.
- **Reason:** All of this unit's changes are on master. monthly_summery.py and employee_advance.py are byte-identical at both heads. manual_punch_entry.py differs only by two commented lines. ot_allowance_entry.get_emp_list is identical on master (the remaining divergence is other OT logic from units 166/174). Master's pf_challan_report.js has the same console.log. The pf_challan_report.py eps rule was superseded by unit 139, whose result master has. Master commits: 9d35b28 (2026-08-12) and 5dd0c13 (2026-09-29).
- **Superseded by:** 139, 145

### kggk:139 — 13-08-2026 added new doctype of asset in gke_order_forms (#1101)

- **SHA:** `367bb9dd2c7cf7ea292108c4a74c4facc41916a4` (PR #1101), 2 commit(s): `4fdaf64895`, `367bb9dd2c`
- **Message:** 13-08-2026 added new doctype of asset in gke_order_forms (#1101)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Adds the Asset Item Master doctype (company/branch/warehouse/department plus a consumable items table) with autoname {abbr}-{branch}-ASM-#####.
- **Reason:** absorbed=true. The asset_item_master files are identical on master (added there as 56368d5, 2026-07-22; path class 'same'). Master has the pf_challan_report.py eps_wage_total block (e3d0134).

### kggk:145 — 20-08-2026 update in employee_advance py file (#1129)

- **SHA:** `ba4549b284350991b3cd520ec7337097517a3cce` (PR #1129), 2 commit(s): `4b7dab253d`, `ba4549b284`
- **Message:** 20-08-2026 update in employee_advance py file (#1129)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Rewrites the Employee Advance validation (calculate_working_days doc_event).
- **Reason:** absorbed=true. employee_advance.py is byte-identical at master and kggk heads; master has it via 9d35b28 / 787f63b.

### kggk:146 — Add frappe dependency to pyproject.toml (#1158)

- **SHA:** `83ee74422b3545c117a8730beb8ff65c4019fc50` (PR #1158), 2 commit(s): `4ffb05006c`, `83ee74422b`
- **Message:** Add frappe dependency to pyproject.toml (#1158)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Adds [tool.bench.frappe-dependencies] frappe = '>=15.0.0,<17.0.0' to pyproject.toml.
- **Reason:** absorbed=true. Master pyproject.toml already has the identical block (84f6e7a, range updated in 0ad0794).

### kggk:148 — 31-08-2026 added new tow report of Department wise present and attend… (#1172)

- **SHA:** `7d75d56425be00238b17a6166cd6b06ac4c768d0` (PR #1172), 3 commit(s): `a33dc4ae78`, `72b86cb42d`, `7d75d56425`
- **Message:** 31-08-2026 added new tow report of Department wise present and attend… (#1172)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Adds the Department Wise Daily Attendance and Department Wise Daily Present reports with scheduled manager mails, plus the salary register comparison API.
- **Reason:** Default PORT overridden. Master already carries this feature through its own twin commits by the same author (569811b salary register API, 60fb6dd reports + hooks, b243ade). salary_register_api.py and both report JSON/__init__ files are blob-identical to master. The report .js/.py versions added here were brought by later kggk units (152/164/173/174) to blobs identical to master at kggk head (path class 'same'). The only diverged path is hooks.py: the 0 10 / 0 8 crons added here were changed by unit 152 to 30 10 / 30 8, which are exactly master's entries. Skipping loses no GK-live behaviour.
- **Superseded by:** 152, 164, 173, 174

### kggk:150 — 31-08-2026 update in cross company doctype (#1175)

- **SHA:** `440dc086d6702280f1314e433b51719d010bc531` (PR #1175), 2 commit(s): `95b60c55eb`, `440dc086d6`
- **Message:** 31-08-2026 update in cross company doctype (#1175)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Cross Company Employee Transfer update: target_site-driven REST calls, holiday list as a transferable property, reports_to taken from new_value, and attendance_device_id carried over.
- **Reason:** Default PORT overridden. Master's twin commits (ab927ef / 7ad1a83 #1174, then 0cf5e27) give the same result. cross_company_employee_transfer .js/.json are blob-identical to master, and .py at kggk head (after unit 152) equals master. cross_employee_transfer_details.json differs only in metadata: master's copy carries duplicated 'modified'/'modified_by' keys (a merge artifact); the fields are identical. No GK-live behaviour is lost.
- **Superseded by:** 152

### kggk:152 — 01-09-2026 01-09-2026 update in auto mail report js and py file and  hooks file  (#1182)

- **SHA:** `624b695fff677b369dd861579bb26d370724516c` (PR #1182), 2 commit(s): `289f1317d9`, `624b695fff`
- **Message:** 01-09-2026 01-09-2026 update in auto mail report js and py file and  hooks file  (#1182)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Moves the department report mail crons to 08:30/10:30, adds a manager guard and hardcoded CC lists to the mailers, and tweaks the report JS.
- **Reason:** Default PORT overridden. cross_company_employee_transfer.py, both report .js files and item_request.json are blob-identical to master. The report .py files at kggk head equal master (this unit's CC lines were later replaced by units 164/173/174 on both lines). The hooks.py cron change (0 10->30 10, 0 8->30 8) matches master's scheduler_events exactly (hunks 2/2 absorbed). Master twin commit is 0cf5e27 (same author, same day). No GK-live behaviour is lost.
- **Superseded by:** 164, 173, 174

### kggk:164 — 11-09-2026 update in attendance api and hr report (#1240)

- **SHA:** `d55b2445ba6cd6f2252a796bbfd764e7426448ad` (PR #1240), 2 commit(s): `2e8a01fab1`, `d55b2445ba`
- **Message:** 11-09-2026 update in attendance api and hr report (#1240)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Brings the attendance API (gke_hrms/api/attendance.py), the loan_application doc event and the ESIC challan and PF contribution reports in line.
- **Reason:** All six paths are identical between master and kggk_prod head (path class 'same'). attendance.py, loan_application.py, esic_challan_report.py and pf_contribution_report.py in master equal the unit's result byte for byte. For the two daily reports, master's commit 317e06b (same date) carries exactly the same +/- lines, and master's file already includes the later edits that kggk got in units 173/174. leftover_d appears only because master moved further ahead.

### kggk:166 — 16-09-2026 update in ot_allowance_entry py file (#1272)

- **SHA:** `92071f775cf689778c257d2bce2ca23e4ffbaa10` (PR #1272), 3 commit(s): `f279000c36`, `f04a4927e5`, `92071f775c`
- **Message:** 16-09-2026 update in ot_allowance_entry py file (#1272)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** OT Allowance Entry adds Employee.old_employee_code to its attendance query.
- **Reason:** absorbed=true. Master's employee_additional_details.json is identical to the unit result, and master's ot_allowance_entry.py contains the old_employee_code select (master commit 820ded9), together with later code.
- **Master equivalent:** 820ded9

### kggk:172 — 21-09-2026 added new doctype employee signature (#1297)

- **SHA:** `98ec5fbcad46756dd043f27b2fa40a9251d0e2b1` (PR #1297), 2 commit(s): `d17508a147`, `98ec5fbcad`
- **Message:** 21-09-2026 added new doctype employee signature (#1297)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Adds the Employee Signature doctype (employee, branch, route, is_published, naming series EMP-SIG-) and its child table Employee Signature Doctype.
- **Reason:** absorbed=true. All 8 files are byte-identical in master (master commit 8b1b9b3, same date).
- **Master equivalent:** 8b1b9b3

### kggk:173 — 24-09-2026 update in daily present and attedance report py file (#1328)

- **SHA:** `9f631325a5411d43c4cd2fc4f7eecc38ba2deb28` (PR #1328), 2 commit(s): `c35e18de79`, `9f631325a5`
- **Message:** 24-09-2026 update in daily present and attedance report py file (#1328)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Department-wise Daily Attendance and Department-wise Daily Present report mailers: the CC list becomes one fixed HR mailbox plus the HR users configured on each Branch (User Group Member rows under Branch.custom_user_group) for every branch that has an active employee in the department, de-duplicated and excluding the To recipients; a second hardcoded CC mailbox is dropped.
- **Reason:** Leaf c35e18de is patch-identical to master commit 757b589c (same title, 2026-09-24). Both report files are byte-identical on master and kggk_prod (path class 'same'), absorbed=true, so the whole behaviour is already in master.
- **Master equivalent:** 757b589cdf

### kggk:174 — 26-09-2026 update in report py file and ot allowance entry (#1335)

- **SHA:** `cc654ee00ae302661be9d39d07cf3d6c00e4d477` (PR #1335), 2 commit(s): `01f3ea04d5`, `cc654ee00a`
- **Message:** 26-09-2026 update in report py file and ot allowance entry (#1335)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** OT Allowance Entry: fetched OT rows are sorted by old employee code then attendance date (previously by date only), grouping rows per employee.
- **Reason:** Leaf 01f3ea04 is patch-identical to master 33fd0160 (same title, 2026-09-26). absorbed=true; the sort key is present in master ot_allowance_entry.py and the site paragraph in both master report files.
- **Master equivalent:** 33fd0160fa

### kggk:175 — 29-09-2026 Logic Update in api for Ot deducation after shift end (#1350)

- **SHA:** `361835e1adad41377d53b03f8757e5822861f3e2` (PR #1350), 2 commit(s): `da2a97ce78`, `361835e1ad`
- **Message:** 29-09-2026 Logic Update in api for Ot deducation after shift end (#1350)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Personal-out deduction clamped at shift end: a new correlated pol_deduction_subquery sums Personal Out Log durations with in_time capped at shift end.
- **Reason:** Functionally identical to master af896a3c (PR #1349, merged in master as 2160feb3). monthly_in_out_log.py has 8/8 hunks absorbed, attendance_api_new.py is 'same', and personal_out_entry.py differs only by a trailing '#<-- changes' comment on master's line. absorbed=false comes solely from that comment. GK live carries the same patch as gkp1 member b94d417a (patch-id == af896a3c), so nothing production-relevant is lost by skipping.
- **Master equivalent:** 2160feb366 af896a3cb5

### gkp:2 — 30-09-2026 update in holiday punch py file (#1358)

- **SHA:** `c94f0475c5d53a4ada2e546c910dcff4dfff5a07` (PR #1358), 2 commit(s): `fde2e28044`, `c94f0475c5`
- **Message:** 30-09-2026 update in holiday punch py file (#1358)
- **Decision:** SKIP_ALREADY_IN_MASTER
- **What it did:** Holiday Punch rewrite.
- **Reason:** GK live's final holiday_punch.py equals master's apart from blank lines: master commit 70308a6 (merge bd749538, #1354, 2026-09-30 18:04) carries the same rewrite. The 0.19 survival at kggk head is irrelevant because kggk_prod never received this change. Audit note for master code: the new guard returns when no row has an existing employee_checkin, the opposite of its own comment ('skip if there is no missing employee_checkin').
- **Master equivalent:** 70308a6


## SKIP_PATCH_EQUIVALENT

_master has a patch-equivalent commit (same diff, different SHA)._

### kggk:9 — 23-03-2026 Add Monthly In-Out Log Doctype (#666)

- **SHA:** `e93df539c4a023cbad49bd4a49b11bff14d65216` (PR #666), 2 commit(s): `f0ce363961`, `e93df539c4`
- **Message:** 23-03-2026 Add Monthly In-Out Log Doctype (#666)
- **Decision:** SKIP_PATCH_EQUIVALENT
- **What it did:** Adds the Monthly In-Out Log doctype to the kggk line: a per-employee monthly attendance/punch summary filled from Attendance, shift, personal-out and OT data, with a list view and a fetch-latest-data button.
- **Reason:** This is a port of master's own feature. The six files equal master@1686de8 (same author, same day) apart from a deleted 41-line commented-out block. JSON, JS, list JS and tests are 'same' at both heads. The kggk-head vs master-head differences in monthly_in_out_log.py/.js come from later kggk units and master's own evolution, not from this unit. Skipping it removes no functionality.
- **Master equivalent:** c72c86b50a

### kggk:75 — 30-06-2026 Update in version 16 for gke hrms module (#920)

- **SHA:** `75d4195722ca687f8066c77128a16a540845b9e0` (PR #920), 2 commit(s): `ee80d8cea1`, `75d4195722`
- **Message:** 30-06-2026 Update in version 16 for gke hrms module (#920)
- **Decision:** SKIP_PATCH_EQUIVALENT
- **What it did:** v16-line copy of the HRMS developer's late-June master changes.
- **Reason:** Every substantive change is already in master. The same developer pushed it there as a3b84bb (22-06-2026: attendance.py, monthly_summery.py, employee_resignation.py, ot_allowance_entry.py, hooks.py, with identical hunk text), 9c92431 (01-06, monthly summary) and ddf4761 (26-05, night-shift detection). A line-level check shows 0 added lines missing from master in 11 of 12 paths. The only lines missing are the 12-line OT personal-out clamp, which master had (a3b84bb) and deliberately replaced on 2026-09-23 (98711a0) with checkin-pair recomputation. Paths attendance.py, attendance_api*.py, monthly_summery.py and sync_checkin.py are class 'same'. employee_resignation.py differs from master only by the EOF newline. The unit carries no behaviour master lacks.

### kggk:79 — 02-07-2026 Update in gke_hrms py file get_list to customfunction (#931)

- **SHA:** `a10114d4aeb50ad5b9d39c2afbec6945225c9c3e` (PR #931), 2 commit(s): `2a477761a8`, `a10114d4ae`
- **Message:** 02-07-2026 Update in gke_hrms py file get_list to customfunction (#931)
- **Decision:** SKIP_PATCH_EQUIVALENT
- **What it did:** v16 query fixes in gke_hrms.
- **Reason:** All functional lines are already in master: master took the same v16-safe rewrites in 29952ac (11-07-2026, OT Allowance Entry), 178a333 (03-09, attendance.py), 55cff56 (12-09, Monthly In-Out Log) and 5dd0c13 (29-09, attendance_api, monthly_summery, manual_punch_entry). A scripted check found 0 of the unit's added non-comment lines missing from master across all 6 paths. The remaining diffs are commented-out old code and indentation. The IndentationError is moot because master has correctly indented code.

### kggk:86 — 09-07-2026 added challan in gke_hrms report and utills and hooks py file (#948)

- **SHA:** `7b091932424b9699d34e546c6617b0d8ac6d0e2f` (PR #948), 2 commit(s): `d32e37847e`, `7b09193242`
- **Message:** 09-07-2026 added challan in gke_hrms report and utills and hooks py file (#948)
- **Decision:** SKIP_PATCH_EQUIVALENT
- **What it did:** Reworks the PF Challan and ESIC Challan reports (account-wise totals panel and print helper) and adds a PF Contribution Report (EPF/EPS/EDLI wages and shares from Salary Slips).
- **Reason:** Patch-equivalent to master 00def16 (30-06-2026 'Update in payroll report and holiday punch') for all six report files (identical line counts) plus 034ed9a (01-07-2026) for the utils helper. Master hooks.py has the same jinja registration. A scripted check found 0 added lines missing from master, except a handful in pf_challan_report.py and pf_contribution_report.py that are no longer live at kggk head either; both sides moved on, and master later refined employee_count in e3d0134.
- **Master equivalent:** 00def16

### kggk:103 — update quotation and order form (#996)

- **SHA:** `9e18b4af8b6370ad204f28eb0efe127e07b8a294` (PR #996), 2 commit(s): `8870386280`, `9e18b4af8b`
- **Message:** update quotation and order form (#996)
- **Decision:** SKIP_PATCH_EQUIVALENT
- **What it did:** Adds Customer Gold/Diamond/Stone/Good/Finding Yes/No selects to the Order Form.
- **Reason:** Master commit e9425d5 (2026-07-29, same author, 'update Sales Type') adds the identical Order Form fields and the identical cad_order_form -> quotation block (tab-indented). d_hunk_containment for order.py is 2/2. A field-level JSON check shows all 10 added fields identical in master. The only unabsorbed hunk is the JSON 'modified' timestamp.

### kggk:131 — 08-08-2026 update in pf challan report py file (#1079)

- **SHA:** `8b2d1c88edf23291bc939782784f8ec01322af71` (PR #1079), 2 commit(s): `8af85c16c2`, `8b2d1c88ed`
- **Message:** 08-08-2026 update in pf challan report py file (#1079)
- **Decision:** SKIP_PATCH_EQUIVALENT
- **What it did:** PF Challan report get_account_total_summary: re-indented with tabs.
- **Reason:** Master has the same patch as d1554ad (same author, same day, same title). The file after d1554ad differs from this unit's leaf only by one whitespace-only line. Master also carries the follow-ups (eps_wage_total excluding the Total row, and its own employee_count = len(employee_data)).
- **Superseded by:** 138, 139
- **Master equivalent:** d1554adb64

### kggk:137 — Update Order Form Detail . Json (#1091)

- **SHA:** `9d165999cebfe3a195b1aa126974672065508dda` (PR #1091), 3 commit(s): `a8e3e2bb23`, `d4e53db541`, `9d165999ce`
- **Message:** Update Order Form Detail . Json (#1091)
- **Decision:** SKIP_PATCH_EQUIVALENT
- **What it did:** Order Form Detail: chain_weight is read-only for 'As Per Design Type' only when the category is not Mugappu.
- **Reason:** Exact patch-id match with master 7d355dc (same author, 2026-08-12), merged via #1092 (cba7b21). The chain_weight read_only_depends_on value is identical at master and kggk heads.
- **Master equivalent:** 7d355dc8b9 cba7b21106


## SKIP_SUPERSEDED

_a later change — in production or on master — replaces it; carrying it would reintroduce old behaviour._

### kggk:8 — Fix/orderform (#653)

- **SHA:** `7de53ba167059d8e2c9f02bf3011ab0edd1ea762` (PR #653), 3 commit(s): `d8b0ecf5e7`, `e42d6d29c1`, `7de53ba167`
- **Message:** Fix/orderform (#653)
- **Decision:** SKIP_SUPERSEDED
- **What it did:** Follow-up to the #631 refactor.
- **Reason:** The unit's entire effect is gone at kggk head. Unit 70 (#908) replaced both files with the MB blob, and of this unit's novel lines only 3 generic ones (of 180) remain in order_form.py and none (of 33) in order_form.js. The debug frappe.throw in get_bom_details for finding orders already existed in MB/master and kggk head.
- **Superseded by:** 70

### kggk:10 — fix: convert report to Query Report for v16 compatibility

- **SHA:** `e7d0b7dbf985e80d552b46609cb7774040cdfe3a` (direct commit), 1 commit(s): `e7d0b7dbf9`
- **Message:** fix: convert report to Query Report for v16 compatibility
- **Decision:** SKIP_SUPERSEDED
- **What it did:** Converts the standard report 'Warehouse wise Consumable Consumption' from Script Report to Query Report.
- **Reason:** technical (consolidated port c7): production's Query Report form only returns data for Administrator on v16 (its JSON MultiSelect filter breaks validate_filters_permissions for other users) and ignores the date and warehouse filters; master's Script Report is kept, so the report shows master's detailed rows instead of production's item x department totals. Not asked at the 2026-10-02 checkpoint - listed for business confirmation

### kggk:18 — Order form (#762)

- **SHA:** `5ac322b67eba5f112233897653f48d0943eb7451` (PR #762), 2 commit(s): `8c74f2c3e4`, `5ac322b67e`
- **Message:** Order form (#762)
- **Decision:** SKIP_SUPERSEDED
- **What it did:** One-line guard in Order Form gc_export_to_excel, SET-item branch: write '' when no Customer RM Code Detail row matches instead of indexing stone_code[0].
- **Reason:** The unit changes one line and that change is gone at kggk head. Units 67, 70 and 68, 78 removed and then re-added the function body. Unit 84 (132daca, #944) then explicitly replaced the guarded SET-branch expression with the unguarded one. Unit 84 is on GK live and gurukrupa-prod's order_form.py is identical to kggk's, so the guard is not live production behaviour. The whole effect is superseded.
- **Superseded by:** 84

### kggk:40 — V16 dharm (#835)

- **SHA:** `bcb4b9c1cce6ceb82098bf6b27759630f218839e` (PR #835), 3 commit(s): `1da1aae4bd`, `f25cd4a4d6`, `bcb4b9c1cc`
- **Message:** V16 dharm (#835)
- **Decision:** SKIP_SUPERSEDED
- **What it did:** Adds the Product Return Form doctype and flow (return of sold pieces: fetch sales BOM and invoice by serial, re-rate the BOM at invoice/current/BBPM/physical-repair/consignment rates, create a return Sales Invoice, e-invoice logic, list view) plus child doctypes Product Return Form Item and Product Return Form E Invoice Item.
- **Reason:** Nothing of this unit needs to land in gk_prod: the parent doctype is gone at kggk head (deleted by unit 95, replaced by Product Return Order Form in unit 96, which master has), and the surviving child doctypes are already in master in superset form. Skipping removes no production functionality. Note for replay: units 64 and 91 later edit product_return_form and unit 95 deletes it; those path changes become no-ops when this unit is skipped.
- **Superseded by:** 95, 96

### kggk:54 — Shubham gke v16 (#873)

- **SHA:** `aebd145e48694b5a4b1dc3b582d9de7550d446ad` (PR #873), 4 commit(s): `bfe90a8179`, `f73ebc89ec`, `795ada4a84`, `aebd145e48`
- **Message:** Shubham gke v16 (#873)
- **Decision:** SKIP_SUPERSEDED
- **What it did:** Temporarily switches off KGGK replication.
- **Reason:** The entire effect is gone at kggk head: hooks are active and the functions are active again (unit 57, later unit 111). It was a temporary disable.
- **Superseded by:** 57
- **Master equivalent:** 2959ad2285 a646f7f74d c6083d123e

### kggk:55 — Update Repair Order . py (#874)

- **SHA:** `43fddcb04c7156a6f20ba7e8624de8b59c51efe1` (PR #874), 2 commit(s): `bcbd791c96`, `43fddcb04c`
- **Message:** Update Repair Order . py (#874)
- **Decision:** SKIP_SUPERSEDED
- **What it did:** Removes a trailing comma in Repair Order create_item_template_from_order, so Item.item_group is set to a string instead of a 1-tuple.
- **Reason:** The entire effect is gone at kggk head (survival 0.0). Unit 114 reintroduced the comma when it synced the file to master's content, and the bug is now identical in master and kggk. It is harmless only because the callers are commented out. If those callers are ever re-enabled, fix the commas as a new change, not as a port of this unit.
- **Superseded by:** 114

### kggk:59 — update item.py fieldname (#883)

- **SHA:** `324edbc5bd7af6e72789e7a3fd32d31df691481a` (PR #883), 2 commit(s): `80e91bfd14`, `324edbc5bd`
- **Message:** update item.py fieldname (#883)
- **Decision:** SKIP_SUPERSEDED
- **What it did:** The create_bom_kggk BOM payload reads and sends black_beed / black_beed_line instead of black_bead / black_bead_line.
- **Reason:** technical (consolidated port c3): master's black_bead/black_bead_line BOM payload keys win - master's deliberate rename (ece7b4e) is newer, black_bead is the field that holds data on the GK side, and the receiving KG site has no black_beed field, so production's keys were silently ignored

### kggk:61 — V16 dharm (#887)

- **SHA:** `3a75b2ee6860858a76bda143807e6741945633ef` (PR #887), 3 commit(s): `ba5a7bef9a`, `2c8c0dae81`, `3a75b2ee68`
- **Message:** V16 dharm (#887)
- **Decision:** SKIP_SUPERSEDED
- **What it did:** Removes the trailing comma in Repair Order create_variant_of_template_from_order, which set Item.item_group for the '- V' variant to a 1-tuple.
- **Reason:** The entire effect is gone at kggk head (survival 0.0); unit 114 reintroduced the bug when it synced repair_order.py to master's content. master == kggk for this file.
- **Superseded by:** 114

### kggk:64 — Sb aerele l (#892)

- **SHA:** `662fc2c0cbaafc2f529622d7d784159ac7fa9dc2` (PR #892), 4 commit(s): `e3c4e36bc3`, `df722cea8c`, `c67f8c9f13`, `662fc2c0cb`
- **Message:** Sb aerele l (#892)
- **Decision:** SKIP_SUPERSEDED
- **What it did:** Product Return Form (the old doctype): when building the Sales Invoice return, set company_address to an Address linked to the Company through Dynamic Link.
- **Reason:** The entire effect is gone at kggk head: the file no longer exists (survival 0.0). The leftover_d path product_return_order_form.py is the successor file and never carried this lookup.
- **Superseded by:** 95, 96

### kggk:91 — V16 dharm (#967)

- **SHA:** `35481e86612c560a187f40bb7b7f560be5dd75f2` (PR #967), 4 commit(s): `9d462cb299`, `79116e7fd3`, `d2ec18cdb9`, `35481e8661`
- **Message:** V16 dharm (#967)
- **Decision:** SKIP_SUPERSEDED
- **What it did:** Adds Product Hallmarking and Product Certification checkboxes to Product Return Form.
- **Reason:** The unit's whole effect on its own paths is gone at kggk head: product_return_form/ was deleted by unit 95 (survival 0, path class 'same'). The feature was carried into Product Return Order Form by unit 96, and master's PROF already contains all of it. If units 40/64 (which create Product Return Form) are replayed and unit 95's deletion is cherry-picked, skipping this unit may show as a modify/delete conflict on two files. Resolve it by deleting (the kggk state).
- **Superseded by:** 95, 96

### kggk:100 — Sb aerele l (#991)

- **SHA:** `5fe374c1af639533821f5f20871a8dc8ec187ffb` (PR #991), 3 commit(s): `4339a7399f`, `fa4884abe7`, `5fe374c1af`
- **Message:** Sb aerele l (#991)
- **Decision:** SKIP_SUPERSEDED
- **What it did:** Rounds Product Return Order BOM re-pricing values (metal and finding rate and amount, making amount, diamond and gemstone amounts) to 2 decimals.
- **Reason:** The unit's whole effect is gone at kggk head (survival 0). git log -S shows the rounded lines added here and removed by 582ab41 (#1005, unit 108), which refactored the e90b4ec blob produced by this unit. Master's product_return_order.py also has the unrounded build_* helpers.
- **Superseded by:** 108

### kggk:108 — Sb aerele l (#1005)

- **SHA:** `582ab418b6f9e99ed3a021c06197144e19156579` (PR #1005), 3 commit(s): `1dfec842af`, `0820e1673f`, `582ab418b6`
- **Message:** Sb aerele l (#1005)
- **Decision:** SKIP_SUPERSEDED
- **What it did:** Large rework of Product Return Order and Product Return Order Form: Jewelex tag import, BOM recalculation, Serial No creation, GST/tax-category resolution and return-invoice building.
- **Reason:** business decision 2026-10-02 (Orders: take master's; HR/Accounts: e-invoice keys on invoice_sales_type): master c97b25f's BOM/serial flow with Sale_*/Costing_Rate keys supersedes the surviving Jewelex and e-invoice hunks

### kggk:121 — Sb aerele l (#1032)

- **SHA:** `d0efb8cd0837bd010c95ccf048e74f07014ffb5b` (PR #1032), 4 commit(s): `7557d23edc`, `c9ca589d9d`, `32e22136be`, `d0efb8cd08`
- **Message:** Sb aerele l (#1032)
- **Decision:** SKIP_SUPERSEDED
- **What it did:** Adds read-only Check fields hallmarking_amounts and certification_amounts on Product Return Order, copied from the form's product_hallmarking/product_certification.
- **Reason:** The unit's whole effect is gone at kggk head: neither field nor any reference exists on the kggk or master heads. Survival of 0.667 on the JSON is a false match on generic lines such as default 0 and read_only 1.
- **Superseded by:** 127, 144

### kggk:122 — V16 dharm (#1038)

- **SHA:** `2893736db8d242658ba040e677e2dec04481901c` (PR #1038), 3 commit(s): `0625914275`, `1b0ef47a6d`, `2893736db8`
- **Message:** V16 dharm (#1038)
- **Decision:** SKIP_SUPERSEDED
- **What it did:** Passes a company code to the Jewelex credit-note API, mapped from the full company name to KGJPL or GEPL, in both the ProductReturnOrderForm class method and the whitelisted _api helper.
- **Reason:** Unit 127 rewrote every line this unit added (survival 0.0 on both files). Master already has unit 127's evolved form, and get_data_from_jwelex is identical on the kggk and master heads. The intermediate state was also broken.
- **Superseded by:** 127

### kggk:125 — Sb aerele l (#1051)

- **SHA:** `41defdf99b584f6fcaef7136a2c884c5d7784bdc` (PR #1051), 3 commit(s): `c8fd3d8db7`, `b49658cabd`, `41defdf99b`
- **Message:** Sb aerele l (#1051)
- **Decision:** SKIP_SUPERSEDED
- **What it did:** 'Added Precision': rounds the Product Return Order Form grand_total and the per-row diamond amount accumulation to 2 decimals in the manual calculation.
- **Reason:** The unit's whole effect is gone at kggk head (survival 0.0). Master also lacks it, and the K and M heads have the same unrounded lines.
- **Superseded by:** 127


## SKIP_REVERTED

_reverted later in kggk_prod (the revert pair cancels out); neither side is carried._

### kggk:56 — Update Order . py (#877)

- **SHA:** `a714c9922cd95730e288440fc4543b1f29b871e4` (PR #877), 2 commit(s): `ff6b73a113`, `a714c9922c`
- **Message:** Update Order . py (#877)
- **Decision:** SKIP_REVERTED
- **What it did:** Order.create_item_template_from_order post_process sets the new template Item's item_code to the Order name.
- **Reason:** Net-zero pair with unit 60. The pid-based revert detection missed it because the revert is a comment-out rather than a deletion.
- **Superseded by:** 60

### kggk:60 — Sb aerele l (#885)

- **SHA:** `0c191e3f668daa3bdb1a48a0a731c52bd4dd5952` (PR #885), 4 commit(s): `168c9fcfc2`, `4c3fa37ee9`, `b639931ed1`, `0c191e3f66`
- **Message:** Sb aerele l (#885)
- **Decision:** SKIP_REVERTED
- **What it did:** Comments out the 'target.item_code = source.name' line that unit 56 added to Order.create_item_template_from_order (PR body: revert changes in order).
- **Reason:** Undoes unit 56. Together they leave only a comment, so there is no behaviour to port.

### kggk:67 — Sb aerele l (#900)

- **SHA:** `099f93dadf64ef37f3daf63d7e6ef639626ecae5` (PR #900), 3 commit(s): `2bf9c5e657`, `dab91d91d8`, `099f93dadf`
- **Message:** Sb aerele l (#900)
- **Decision:** SKIP_REVERTED
- **What it did:** 'Updated V16 Code To Gkexport Code': resets order.py and order_form.js to the merge-base (v15 gkexport) content and rewrites order_form.py (+880/-3885).
- **Reason:** Exact net-zero pair with unit 68, confirmed by an empty net diff.
- **Superseded by:** 68

### kggk:68 — Revert "Sb aerele l" (#902)

- **SHA:** `d360a42f69729ca4adce9e9d45ada00a61d7f3e1` (PR #902), 2 commit(s): `9d78e91644`, `d360a42f69`
- **Message:** Revert "Sb aerele l" (#902)
- **Decision:** SKIP_REVERTED
- **What it did:** GitHub revert of unit 67 (order.py, order_form.js and order_form.py restored).
- **Reason:** Exact inverse of unit 67; the net diff across the pair is empty.

### kggk:71 — Sb aerele l (#914)

- **SHA:** `f87bdc5621c2ec542a956843d268ff1fd64006b8` (PR #914), 4 commit(s): `17fb2456a3`, `8b39978d76`, `ab1162e9c5`, `f87bdc5621`
- **Message:** Sb aerele l (#914)
- **Decision:** SKIP_REVERTED
- **What it did:** Commented out the back-link that create_cad_orders writes from the originating Pre Order Form Details row to the Order Form (order_form_id).
- **Reason:** This is a net-zero revert pair with unit 73 (reverts_units_by_pid / reverted_by_units = 73). The whole chain of units 71-74 leaves the tree byte-identical: git diff 174e9f1249 95b5b3b66b is empty. Leaf 17fb2456a3 rewrites order_form.py to exactly the mainline blob d5728a1, so it adds nothing to the first-parent diff.

### kggk:72 — Update Order files (#913)

- **SHA:** `f875de685816c3094123aa0242d310ae93980925` (PR #913), 2 commit(s): `f6cc6b1bff`, `f875de6858`
- **Message:** Update Order files (#913)
- **Decision:** SKIP_REVERTED
- **What it did:** Replaced kggk's Order controller and field layout (order.py, order.json), the Order Form JSON and the Order Form Detail JSON with the gkexport/master copies ('Updated Order Files From Gkexport').
- **Reason:** Unit 74 reverts it exactly (pid revert relation, inverse numstat on all 4 files). The 71-74 chain is byte-identical to its start (empty git diff 174e9f1249 95b5b3b66b).

### kggk:73 — Revert "Sb aerele l" (#916)

- **SHA:** `9067f1c4dd8869725e4b218dadbd86cb7bbe1d63` (PR #916), 2 commit(s): `b8c06d7127`, `9067f1c4dd`
- **Message:** Revert "Sb aerele l" (#916)
- **Decision:** SKIP_REVERTED
- **What it did:** Revert of #914 (unit 71).
- **Reason:** The default was SKIP_ALREADY_IN_MASTER only because master already has the restored line. More precisely, this is the second half of a net-zero revert pair with unit 71, and both are skipped as reverted.

### kggk:74 — Revert "Update Order files" (#917)

- **SHA:** `95b5b3b66b238562cb56a32c8db3795b1c01eea9` (PR #917), 2 commit(s): `c731e5d7a7`, `95b5b3b66b`
- **Message:** Revert "Update Order files" (#917)
- **Decision:** SKIP_REVERTED
- **What it did:** Revert of #913 (unit 72).
- **Reason:** This is the second half of a net-zero revert pair with unit 72. After it, the tree equals the state before unit 71.

### kggk:94 — Serial No Detail Report (#973)

- **SHA:** `b6335658d69edaa193cb3127a559b09392f05ce5` (PR #973), 4 commit(s): `21fea421dc`, `cb19b1ea7f`, `d3bd7fb85b`, `b6335658d6`
- **Message:** Serial No Detail Report (#973)
- **Decision:** SKIP_REVERTED
- **What it did:** Adds a correctly named Serial No Detail Report (js/json/py).
- **Reason:** Net-zero revert pair with unit 102, matched by patch-id (reverts_units_by_pid = reverted_by_units = [102]). The report is absent at kggk head and on GK live, so skipping removes nothing from production.

### kggk:102 — Delete gke_customization/gke_catalog/report/serial_no_detail_report directory

- **SHA:** `1bdd883466e3a69b9169e43b4ec5044de5f192ed` (direct commit), 1 commit(s): `1bdd883466`
- **Message:** Delete gke_customization/gke_catalog/report/serial_no_detail_report directory
- **Decision:** SKIP_REVERTED
- **What it did:** Web-UI commit that deletes the serial_no_detail_report directory that unit 94 had added.
- **Reason:** This is the exact patch-id inverse of unit 94 (reverts_units_by_pid [94], reverted_by_units [94]). All 4 paths are class 'same': absent from both master and kggk head. The dry-run conflict on batch_wise_sales_cycle.json is a rename-detection artifact of deleting files that never existed on master. Skip together with unit 94.

### kggk:168 — Revert "refactor: rename close setting and label to nova glow" (#1280)

- **SHA:** `3ec2f3376daf8c862f818fe5d71b40a95486baa9` (PR #1280), 2 commit(s): `3ca34b0203`, `3ec2f3376d`
- **Message:** Revert "refactor: rename close setting and label to nova glow" (#1280)
- **Decision:** SKIP_REVERTED
- **What it did:** Exact revert of #1278: restores 'Close' / 'Close Setting' in the CAD Report, item.py replication gates, Targets Form, Retailer Survey and Order Form tests.
- **Reason:** This is the inverse patch of 167 (same patch-id) and is itself reverted by 169. 168 and 169 form a net-zero pair (survival 0.0 for every path). plan_v2 skips it.

### kggk:169 — Revert "Revert "refactor: rename close setting and label to nova glow"" (#1283)

- **SHA:** `c1f7ed5f7bd521aff9de4a5685e71faccce817a2` (PR #1283), 2 commit(s): `bff1420f5f`, `c1f7ed5f7b`
- **Message:** Revert "Revert "refactor: rename close setting and label to nova glow"" (#1283)
- **Decision:** SKIP_REVERTED
- **What it did:** Revert of the revert: re-applies the #1278 Close -> Nova Glow rename unchanged.
- **Reason:** Same patch-id as 167. Together with 168 it is net-zero, and the kept effect is carried by unit 167, as decided in plan_v2.


## SKIP_UNRELATED

_KGGK-only functionality the business decided not to carry into GK's line._

### kggk:155 — Sandepp v16 dummy (#1203)

- **SHA:** `d090a12db456f0954d8f03142b8b186a74aa0a0c` (PR #1203), 3 commit(s): `f2b70d1641`, `3c0d78f905`, `d090a12db4`
- **Message:** Sandepp v16 dummy (#1203)
- **Decision:** SKIP_UNRELATED
- **What it did:** Rewrites the KGGK Jewelex tally data source: removes the pyodbc/SQL query and the cache file, and fetches rows from an HTTP order-tally API with 3 retries and a site-private fallback JSON.
- **Reason:** KGGK Jewelex - ERP Order Tally only; business decision 2026-10-02; replayed for ordering, removed by the exclude: commit
- **Superseded by:** 160, 161

### kggk:156 — Sandepp v16 dummy (#1205)

- **SHA:** `3c6741b515f3864501801de6ad6f3e2ee0eea1a0` (PR #1205), 3 commit(s): `d938b30b0a`, `5bc5d6e7cf`, `3c6741b515`
- **Message:** Sandepp v16 dummy (#1205)
- **Decision:** SKIP_UNRELATED
- **What it did:** In the KGGK Jewelex tally compare mode, 'ERP Order Complete' becomes an Int count of fully submitted PMOs (0 when none) instead of a sales-order list or 'Not Found'.
- **Reason:** KGGK Jewelex - ERP Order Tally only; business decision 2026-10-02; replayed for ordering, removed by the exclude: commit

### kggk:161 — Report Update (#1224)

- **SHA:** `d1c7fe32d8e3702b31005b1ee85f071362941ed2` (PR #1224), 3 commit(s): `482953b54a`, `fc7a922c51`, `d1c7fe32d8`
- **Message:** Report Update (#1224)
- **Decision:** SKIP_UNRELATED
- **What it did:** Adds Order Date from/to, Jewelex Order No and Jewelex Batch No filters to the 'KGGK Jewelex - ERP Order Tally' report.
- **Reason:** business decision 2026-10-02 (Access/KGGK): the KGGK Jewelex - ERP Order Tally family is not carried; replayed for ordering, removed by the exclude: commit
- **Master equivalent:** dce267ec30

## Partially carried units

These units are PORT, but part of their content was intentionally replaced or left out:

| Unit | PR | What was left out or changed, and why |
|---|---|---|
| kggk:6 | #650 | get_orders_for_quotation kept; the clearing of all Quotation rows (target_doc.items = []) is replaced by master's add-to-existing-rows filter (business decision 2026-10-02, Orders); the port renumbers kept rows |
| kggk:12 | #746 | master's Revise Gemstone Price List redesign replaces the old controller fields this unit added (no documents of this DocType exist on the GK copies); production's System Manager permission row is kept |
| kggk:22 | #769 | the Sales Invoice validate hook stays commented out as on master 3100eaf (business decision 2026-10-02, HR/Accounts); Batch autoname stays dropped (jewellery registers the same handler) |
| kggk:29 | #809 | fixtures curated - doctype.json keeps the 5 gke-owned DocTypes, the 46 rows jewellery already ships are dropped (see 07) |
| kggk:118 | #1025 | master's later removal of reqd on Order BOM Metal Detail metal fields is kept (business decision 2026-10-02, Orders) |
| kggk:147 | #1123 | create_bom_for_touch is split by metal type - Silver touch changes follow master (Order purity), gold and other metals keep production's touch-to-purity map (business decision 2026-10-02, Orders) |
| kggk:151 | #1176 | Production Report and Advance Bagging Summary changes kept; its KGGK Jewelex - ERP Order Tally files removed by the exclude: commit (business decision 2026-10-02) |
| kggk:154 | #1191 | Production Report changes kept; KGGK tally hunk removed by the exclude: commit (business decision 2026-10-02) |
| kggk:160 | #1217 | department report changes kept; KGGK tally hunk removed by the exclude: commit (business decision 2026-10-02) |
| kggk:170 | #1288 | the Jewelex-tag validate guard is dropped and the on_submit guard narrowed to Jewelex tags without a new BOM, so BOM-calculated Jewelex returns build a BOM and serial as on master (business decision 2026-10-02, Orders) |

Where a consolidated port replaced a production behaviour with master's newer logic, the per-file record in [06](06_cherry_pick_plan_and_conflicts.md) lists it under *dropped or changed*.

## Pending promotion (open PRs at the cut, 2026-10-02)

Not part of this reconstruction (the source branches were pinned before they merged). Each needs a decision after it lands:

| PR | Target | Title | Opened | Action for gk_prod |
|---|---|---|---|---|
| #1371 | kggk_prod | 01-10-2026 update in holiday punch py file | 2026-10-01 | forward-port to gk_prod if it merges into kggk_prod |
| #1367 | kggk_prod | Backport/salary withholding kggk prod | 2026-10-01 | forward-port to gk_prod if it merges into kggk_prod |
| #1351 | kggk_uat | fix(metal-conversion-report): derive customer metal from the conversion's Stock Entry rows | 2026-09-30 | KGGK UAT line; promote to gk_prod only if GK needs it |
| #1336 | kggk_uat | fix: attendance session pairing and monthly in-out | 2026-09-28 | KGGK UAT line; promote to gk_prod only if GK needs it |
| #1331 | kggk_uat | fix(reports): leave FG work orders out of the employee batch issue/receive reports | 2026-09-25 | KGGK UAT line; promote to gk_prod only if GK needs it |
| #1323 | kggk_uat | fix(gold rates): run the rate job at 09:00, 15:00 and 23:00, and stop false failures | 2026-09-24 | KGGK UAT line; promote to gk_prod only if GK needs it |
| #1310 | kggk_uat | fix(monthly-in-out): migrate spent hours from time to duration | 2026-09-22 | KGGK UAT line; promote to gk_prod only if GK needs it |
| #1365 | master | Bhavika gkexport | 2026-10-01 | reaches gk_prod by merging master into gk_prod after it lands |
| #1353 | master | Shruti gkexport | 2026-09-30 | reaches gk_prod by merging master into gk_prod after it lands |

Merged after the cut and **included**: #1370 (master, fix(pro-push): send absolute image URLs to the remote site) — merged into the migration branch with merge commit `0e6e3dc`.

