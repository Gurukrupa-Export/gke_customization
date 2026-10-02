# 06 — Cherry-pick plan, port resolutions and conflicts

## Order and why

1. **Chronological replay of production history** (units in their original first-parent order). Diff replay is only safe in the order the changes were written: later production commits edit what earlier ones added. The brief's layer grouping is therefore applied to the *port* commits instead. Every pick: `cherry-pick -n [-m 1] -x -X no-renames`, then the paths master also changed are held back, then commit with the original author/date/message and provenance trailers, then the tree is asserted equal to the dry-run simulation.
2. **Consolidated three-way port commits** for the 51 held-back paths (files master and production both changed), in layer order: hooks + patches + packaging → order family DocTypes/services → pricing endpoints and sales hooks → product return family → revise price lists → HR → catalogue/survey.
3. **Fixture curation** (custom_field.json, doctype.json) and the patch that aligns existing Custom Field names before fixtures import.
4. **Business decisions** from the 2026-10-02 checkpoint (report roles, Product Return Order KGGK sync gate, KGGK tally exclusion).
5. **v16 compatibility fixes** for master-only code (master is the v15 line).

## Replay groups (checkpoints)

| Group | Units | Dates | Main features | Branch commits |
|---|---|---|---|---|
| 01 | kggk:1 – kggk:17 (17) | 2026-02-04 – 2026-05-05 | Order (6), Order Form (3), Patches (2) | `be91292`..`47465ae` (5) |
| 02 | kggk:18 – kggk:36 (19) | 2026-05-05 – 2026-06-03 | Order Form (6), Gold Rates (3), Fixtures (2) | `81de021`..`60b7449` (7) |
| 03 | kggk:37 – kggk:49 (13) | 2026-06-04 – 2026-06-19 | Manufacturing reports (3), Product Return Order (2), Making charges (2) | `5ff3d31`..`965a95d` (14) |
| 04 | kggk:50 – kggk:70 (21) | 2026-06-21 – 2026-06-25 | Item and BOM creation and KGGK replication (8), Repair Order (6), Order Form (3) | none (all skipped or empty) |
| 05 | kggk:71 – kggk:86 (16) | 2026-06-27 – 2026-07-09 | Manufacturing reports (5), Order Form (4), HR attendance and punches (3) | `fc51b2f`..`8834d48` (7) |
| 06 | kggk:87 – kggk:100 (14) | 2026-07-09 – 2026-07-23 | Product Return Order (5), Order Form (2), Manufacturing reports (2) | `4f95b9a`..`7b3cbb3` (7) |
| 07 | kggk:101 – kggk:115 (15) | 2026-07-23 – 2026-07-27 | Manufacturing reports (6), Product Return Order (4), Stock and inventory reports (2) | `5c488a9`..`8a94523` (7) |
| 08 | kggk:116 – kggk:128 (13) | 2026-07-27 – 2026-08-07 | Product Return Order (5), Manufacturing reports (3), Repair Order (3) | `b82a01d`..`a1371f4` (3) |
| 09 | kggk:129 – kggk:146 (18) | 2026-08-08 – 2026-08-28 | Manufacturing reports (5), HR attendance and punches (3), Order (3) | `e0643de`..`f7aa06d` (5) |
| 10 | kggk:147 – kggk:156 (10) | 2026-08-28 – 2026-09-06 | Manufacturing reports (5), Sales and HR reports (2), Order Form + Product Return Order + HR payroll and salary withholding + Manufacturing reports (1) | `7f39ed4`..`5533247` (6) |
| 11 | kggk:157 – kggk:172 (16) | 2026-09-07 – 2026-09-21 | Manufacturing reports (4), Nova Glow rename (3), HR attendance and punches (2) | `e168048`..`8b4e46d` (9) |
| 12 | kggk:173 – gkp:2 (7) | 2026-09-26 – 2026-09-30 | HR attendance and punches (3), Sales and HR reports (1), HR overtime (1) | `c9c77f4`..`c9c77f4` (1) |

After the replay (`c9c77f4`), the remaining commits in order:

| Commit | Subject |
|---|---|
| `083c594` | port(hooks-patches-pyproject): combine master and production changes to the hooks, patches and packaging |
| `48639f4` | port(order-family): combine master and production changes to the Order, Order Form and Repair Order |
| `ed24d61` | port(pricing-sales-hooks): combine master and production changes to the pricing endpoints, Sales Order hooks and KGGK replication |
| `87d5e26` | port(product-return): combine master and production changes to the Product Return Order family |
| `6934d29` | port(revise-price-lists): combine master and production changes to the Revise price lists |
| `be0c216` | port(hrms): combine master and production changes to the HR attendance, punches, overtime and payroll |
| `dd838b8` | port(catalogue-survey): combine master and production changes to the catalogue reports, catalogue API and survey |
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

…followed by the documentation commit that adds this folder.

Review tip: the PR has fewer than 250 commits, so GitHub lists all of them; `git log --first-parent gk_prod..migration/gk-prod-reconstruction` gives the same sequence. **Merge with “Create a merge commit”** — squash or rebase would discard the `-x` provenance and the original authors.

## Consolidated port resolutions

Each port is a three-way merge (base = the master/kggk_prod merge base, ours = master, theirs = kggk_prod, with gurukrupa-prod's later edits applied first), reviewed by two independent verifiers: one checking that every master behaviour is kept, one checking that every required production behaviour is kept and v16-safe. Decisions: *merged* (both sides combined), *take_master*, *take_prod*, *deleted* (renamed away).

### c1-hooks-patches-pyproject — `083c594`

I ported the three paths into /home/dhinesh/bench/v16/wt/evidence/gkprod/work/ports/c1-hooks-patches-pyproject/files/. G equals K for all three, so PROD(p) = kggk_prod. hooks.py is prod's v16/ruff-formatted file plus master's one remaining change (Sales Invoice validate commented out). An AST check shows it equals the union of master and prod minus exactly two base-era entries, each removed by one side: the Batch autoname handler dropped by prod as a duplicate of the GK-live jewellery registration, and the Sales Invoice validate disabled by master. I fixed a silent auto-merge defect, a duplicated 'hourly' key. Every dotted path exists at master or kggk_prod, and the gold-rate cron dedupe is flagged, not changed. patches.txt keeps all three lines byte-identical in [post_model_sync]: prod's gc_ration_master and salary_withholding_release_fields first, master's nova-glow patch last. Frappe v16's own parser and importlib both pass. pyproject.toml is the dependency union with one v16 fix: prod's requests~=2.32.0 is relaxed to >=2.32.0 because it cannot be satisfied alongside frappe v16's requests~=2.33.0. No extra paths need non-default content. Main open questions: the Sales Invoice disable vs live, the first-ever nova-glow data rename on GK live, the gold-rate single-run dedupe, the requests relaxation, and the two fixture entries.

| File | Decision | Conflicts resolved |
|---|---|---:|
| `hooks.py` | merged | 4 |
| `patches.txt` | merged | 1 |
| `pyproject.toml` | merged | 1 |

**hooks.py** — dropped or changed: (1) doc_events Batch.autoname -> jewellery_erpnext...batch.batch.autoname stays DROPPED, as prod did in 5709d9c 'Develop aerele (#769)'. Master only carried the base line. GK-live jewellery_erpnext hooks.py (Batch block, lines 360-364 in /home/dhinesh/bench/v16/wt/jew-gurukrupa-prod) registers the same handler, and v16 frappe.append_hook extends lists without de-duplicating. Keeping the line would run Batch autoname twice per insert (the second run regenerates the random suffix). (2) doc_events Sales Invoice.validate is COMMENTED OUT, taking master's 3100eaf. Prod never changed this entry (only the ruff reformat in 5709d9c), the commit is not in K's history, and the handler file is byte-identical on MB/M/K, so three-way semantics apply master's change. (3) Master's stale commented-out legacy '# "Item": before_validate item.before_validate' block is not carried; prod removed it in c72dab2 when it activated create_item_kggk (comment only). (4) The header 'from . import __version__ as app_version' + 'import gke_customization.overrides' is replaced by prod's 'from . import __version__'. This changes no behaviour: v16 get_versions() reads <app>.__version__, gke_customization/overrides has no __init__.py on any ref (an empty namespace package, no side effects), and _load_app_hooks skips modules and underscore names. (5) git merge-file silently produced a DUPLICATE 'hourly' key, because both sides added the identical block. The final file has one.

**patches.txt** — dropped or changed: Nothing dropped. Order: prod's two patches first (introduced 2026-02-11 and 2026-08-21, already applied on GK live), then master's nova-glow patch last (2026-09-18), following the newest-last convention. The three patches have no inter-dependencies: GC Ratio rows; custom fields on hrms Salary Withholding/Cycle; Attribute Value plus setting string columns. On GK live only the nova-glow patch is new, and Patch Log is keyed on line text, so order is irrelevant for already-run lines. The only byte-level change is a trailing newline at EOF (both sources had none). Line texts are unchanged, and Frappe's configparser-based parser is unaffected.

**pyproject.toml** — dropped or changed: requests specifier changed from prod's '~=2.32.0' to '>=2.32.0'. Prod's pin means ==2.32.*, which cannot be satisfied together with the target v16 frappe's own 'requests~=2.33.0' (frappe commit 2cbe48a1a3 'fix: update requests', in v16.10.4 dated 2026-04-07; the local frappe is 16.33.0). packaging finds no version satisfying both, and the bench env already has requests 2.33.1. A bench requirements sweep would otherwise downgrade requests below frappe's floor or fail to resolve. '>=2.32.0' keeps prod's lower bound and leaves the cap to frappe. No other change.

Open points recorded for review:

- Sales Invoice validate hook: gk_prod takes master's 3100eaf (2026-04-01) and leaves it commented out. GK live (K line) still runs it today: a company-specific check, for one group company, that makes batch no and diamond grade mandatory on non-return invoices. Should GK confirm they want it off in gk_prod? If live must keep enforcing it, un-comment the 3-line block in hooks.py. On v16 Sales Invoice Item.batch_no is often empty when batches live in the Serial and Batch Bundle, so re-enabling it could block invoices.
- requests pin: pyproject relaxes prod's 'requests~=2.32.0' to 'requests>=2.32.0' because the target v16 frappe pins 'requests~=2.33.0' and the two cannot both be met. Revert to the verbatim pin only if gk_prod will run on a frappe older than v16.10.4.
- Gold-rate scheduler: run_gold_rate_scheduler is registered under '0 9 * * *', '0 15 * * *' and '0 23 * * *'. Frappe v16 keeps one Scheduled Job Type per method, so only the last cron processed ('0 23 * * *') takes effect. That matches GK live today. If three daily runs are intended, the business owner should pick a fix (e.g. one cron '0 9,15,23 * * *' or distinct wrapper methods). Cron times were not changed here.
- Nova-glow data patch (gke_customization.patches.v1_0.v15_rename_close_setting_to_nova_glow) has never run on GK live. The first gk_prod 'bench migrate' there will rename the setting master data and rewrite setting columns across about 60 doctypes, one-way and sentinel-guarded. Do GK sign-off, timing and a backup before deploy need confirming?
- Fixture entry 1 (kept, identical on MB/M/K): {"dt": "Custom Field", "filters": [["module", "in", ["GKE Order Forms", "GKE Catalog"]]]}, backed by gke_customization/fixtures/custom_field.json on all refs. Left for the fixture-curation track to decide.
- Fixture entry 2 (kept, identical on MB/M/K): {"dt": "DocType", "filters": [["module", "in", ["GKE Order Forms", "GKE Catalog"]], ["custom", "=", 1]]}, backed by gke_customization/fixtures/doctype.json on all refs. Left for the fixture-curation track to decide.
- Pre-existing dead hook references, kept unchanged because they are identical on MB, master and kggk_prod. Should they be cleaned up in a follow-up? (a) doc_events key 'SolitaireCalculator' never fires (the DocType is 'Solitaire Calculator'), and calculate_rate is not defined in that module. (b) doctype_js 'Payment Entry' points to public/js/doctype_js/payment_entry.js, which exists on no ref. (c) The override_whitelisted_methods key 'erpnext.selling.doctype.delivery_note.delivery_note.make_sales_invoice' is not a real ERPNext path (Delivery Note is under erpnext.stock), so that override never triggers for the standard desk action. (d) app_include_js is assigned eight times with Python dotted strings; the last value renders as a 404 <script> tag on every desk load.
- pyodbc>=5.0.1 is declared by both sides but is not installed in the v16 bench env (Python 3.14). Does the deploy target have a cp314 wheel or system unixODBC so the master-side pd_to_prod_api / csat endpoints can import it?

### c6-hrms — `be0c216`

All 12 cluster-c6 paths are written under files/; none deleted, all pass validation. Eight are byte-identical to master. On these, master and production converged (HR developer double-pushes); GK live already runs master's holiday_punch/manual_punch_entry/personal_out_entry. attendance_tool.py and the cross_employee_transfer_details JSON take the production version. The JSON drops master's duplicate modified keys from a bad merge and uses the newer modified, 2026-08-20. Two files are real merges. monthly_in_out_log.py = master (per-date shift resolution, deduction subquery) + production's 2026-09-30 guard that ignores personal outs starting after shift end. ot_allowance_entry.py = master's newer checkin-pair OT recompute, which replaces production's SQL personal-out clamp, plus Employee.old_employee_code restored in get_emp_list. pf_challan_report.py keeps master's newer employee_count fix, which excludes the Total row. Checks: py_compile on bench Python 3.14, node --check, json.load with as_json round-trip, no conflict markers, ruff F821 with no new findings. The attendance_tool override signature matches HRMS v16. Pre-existing bugs found but not fixed: holiday_punch add_days NameError, attendance_tool unbound working_hours.

| File | Decision | Conflicts resolved |
|---|---|---:|
| `gke_hrms/api/attendance_tool.py` | take_prod | 1 |
| `gke_hrms/doctype/cross_employee_transfer_details/cross_employee_transfer_details.json` | take_prod | 1 |
| `gke_hrms/doctype/employee_resignation/employee_resignation.py` | take_master | 0 |
| `gke_hrms/doctype/holiday_punch/holiday_punch.py` | take_master | 5 |
| `gke_hrms/doctype/manual_punch_entry/manual_punch_entry.py` | take_master | 0 |
| `gke_hrms/doctype/monthly_in_out_log/monthly_in_out_log.py` | merged | 3 |
| `gke_hrms/doctype/ot_allowance_entry/ot_allowance_entry.py` | merged | 6 |
| `gke_hrms/doctype/personal_out_entry/personal_out_entry.py` | take_master | 1 |
| `gke_hrms/doctype/user_permission_request/user_permission_request.py` | take_master | 0 |
| `gke_hrms/report/pf_challan_report/pf_challan_report.js` | take_master | 1 |
| `gke_hrms/report/pf_challan_report/pf_challan_report.py` | take_master | 1 |
| `gke_hrms/utils.py` | take_master | 4 |

**attendance_tool.py** — dropped or changed: Only master's trailing blank line at EOF (W391). No logic change.

**cross_employee_transfer_details.json** — dropped or changed: Dropped master's duplicated "modified"/"modified_by" keys, an artifact of merge 119b44b. With json last-wins they would have resolved to the OLDER 2026-08-17 value. Final modified = 2026-08-20 13:29:49.274262 (the newer one), with its own modified_by.

**employee_resignation.py** — dropped or changed: Nothing. Final is master's bytes, which add only the EOF newline that kggk_prod lacks.

**holiday_punch.py** — dropped or changed: Only GK live's removal of 10 blank lines. The 5 MB-base conflict hunks were whitespace-only; a re-merge against the shared blob 343455e confirms master == prod ignoring blank lines.

**monthly_in_out_log.py** — dropped or changed: Merged against the shared ancestor blob a60f206 (master df0fe91 == kggk_prod 1006e44), because MB lacks the file (add/add). Hunk 1 (pol_deduction_subquery) took prod: newer and a superset of master's. Hunks 2-3 (od/holiday SQL) took master: the SQL is identical and only whitespace inside the string differs; master's 2026-09-12 is newer than prod's 2026-08-08. Prod's frappe.get_all for ot_for_wo is replaced by master's equivalent raw SQL.

**ot_allowance_entry.py** — dropped or changed: (1) The 6 MB-base conflicts were re-merged against the true common content f677645 (master a3b84bb == kggk_prod ee80d8c/#920 except the EOF newline). That merge is clean and equals master. (2) Production's 2026-06-22/30 SQL personal-out clamp subtraction (sub_query_personal_out_log) is replaced by master's newer checkin-pair recompute. Both enforce the same rule (no OT for personal-out time after shift end); master had the clamp too and replaced it, so newest-by-date applies. (3) Resolution edit: added Employee.old_employee_code to get_emp_list's qb select. Master's 5dd0c13 copied kggk_prod's qb get_emp_list and dropped the field 98711a0 had added, leaving weekoff rows with a None sort key.

**personal_out_entry.py** — dropped or changed: Nothing. Final is master's bytes = gurukrupa-prod + EOF newline; kggk_prod differs only by the trailing comment.

**user_permission_request.py** — dropped or changed: Nothing; only the EOF newline differs.

**pf_challan_report.js** — dropped or changed: Nothing functional.

**pf_challan_report.py** — dropped or changed: kggk_prod's employee_count = len(data) is replaced by master's later fix. GK live's PF challan panel will stop counting the Total row.

**utils.py** — dropped or changed: Unused 'import calendar' (master removed it in 034ed9a; nothing uses it). The other 3 conflict hunks were whitespace-only.

Open points recorded for review:

- ot_allowance_entry.py: GK live switches from production's SQL personal-out clamp to master's 2026-09-23 checkin-pair OT recompute. It also skips attendances with null in/out times or odd checkin counts. I chose this by the newest-by-date rule, but kggk_prod's 2026-09-26 sync (#1335) took only the sort change, not this logic. Please confirm production should adopt it.
- ot_allowance_entry.py: I added Employee.old_employee_code to get_emp_list's qb select. This restores master 98711a0's weekoff sort key, which 5dd0c13 dropped. Please confirm.
- holiday_punch.py (pre-existing, not fixed): add_days is used in the overnight-shift branch (line 265) but never imported, in both master and GK live, so night-shift holiday punches raise NameError. The one-line fix is to add add_days to the frappe.utils import. Recommend doing it in a separate commit.
- attendance_tool.py (pre-existing, not fixed): working_hours and shift_start_datetime are only set when a valid Shift Type is passed. Marking Present/WFH/Half Day with no shift raises an unbound-variable error on both lines.
- Fixtures cluster: the custom field Attendance-custom_is_employee_attendance_tool exists only in kggk_prod's fixtures/custom_field.json. Keep it: attendance_tool.py writes it and monthly_checkin_report reads it.
- monthly_in_out_log.py: master's 55cff56 computes row_shift_hours but never uses it (leave rows still use the employee-level shift_hours). I kept it as master has it; please confirm the intent.

### c2-order-family — `48639f4`

Fix round for c2-order-family. I checked all five reviewer findings against git, and all are real. Only order.py changed (three edits). The other 9 files are unchanged and were re-validated. Finals are under /home/dhinesh/bench/v16/wt/evidence/gkprod/work/ports/c2-order-family/files/. Fix-round evidence is in work/fix1/: pre-fix snapshot, fix1.diff, the two behaviour harnesses and their outputs.  (1) MAJOR, fixed. create_bom_for_touch had taken master's 6c56b34 body on a 'newest wins' basis. That premise was wrong. The touch-to-purity map is MB behaviour; prod's 7b07d3f only added 20KT and the finding loop, and 6c56b34 is a Silver commit. For gold, Order.metal_purity holds the source design's purity or is blank. Master's body therefore gave the wrong purity, or failed at BOM insert, and rescaled natural stones 1.7x. The function now splits by metal type: - Silver follows master: Order purity, ratio zeroing, and 1.7x rescaling for non-AD stones. - Every other metal follows production: touch map, copied purity for unmapped touches, no stone rescaling. - Purities are now strings. Production assigns floats to the BOM.metal_purity Link field, and v16's link-type assertion rejects them. So production's own gold 22KT/18KT path fails on v16 today; this port fixes it.  (2) Minor, fixed. make_quotation_batch now keeps master's rows (Repair Order rows and earlier rows) and prod #650's duplicate guard: a re-fetched Order replaces its own row. Kept rows are renumbered so their idx values 

| File | Decision | Conflicts resolved |
|---|---|---:|
| `gke_order_forms/doctype/order/order.py` | merged | 10 |
| `gke_order_forms/doctype/order/order.js` | merged | 0 |
| `gke_order_forms/doctype/order/order.json` | merged | 2 |
| `gke_order_forms/doctype/order_form/order_form.py` | merged | 2 |
| `gke_order_forms/doctype/order_form/order_form.js` | merged | 1 |
| `gke_order_forms/doctype/order_form/order_form.json` | take_prod | 1 |
| `gke_order_forms/doctype/order_form_detail/order_form_detail.json` | take_prod | 1 |
| `gke_order_forms/doctype/order_bom_diamond_detail/order_bom_diamond_detail.json` | take_prod | 1 |
| `gke_order_forms/doctype/order_bom_metal_detail/order_bom_metal_detail.json` | take_master | 1 |
| `gke_order_forms/doctype/repair_order/repair_order.js` | take_prod | 1 |

**order.py** — dropped or changed: Fix round: (a) create_bom_for_touch. The previous port took master's 6c56b34 body wholesale and called prod's touch map 'an intermediate stage of the Silver work'. Verified wrong: the map is in MB, and 6c56b34 is titled 'Updated Order Files For Metal Type Silver'. For gold, Order.metal_purity is the source design's purity: order_form.js fills it from get_bom_details, and the Order Form Detail field is visible only for Silver. It can also be blank. So master's body gave a gold touch-change BOM the old purity, or failed at insert because jewellery's BOM Metal/Finding Detail metal_purity is reqd. It also rescaled natural stones 1.7x. Now combined by metal type. Dropped from master: Order.metal_purity and the 1.7x stone rescaling on non-Silver touch changes. Dropped from production: the touch map on Silver touch changes, replaced by master's later Silver revision from the same author. (b) make_quotation_batch now filters with `row.item_code and not (order_form_type == 'Order' and order_form_id in order_names)`. Dropped from production: #650's wipe of unrelated rows; other Orders' rows and Repair Order rows now survive, as master intends. Added: kept rows are renumbered 1..n before the append. frappe's set() keeps old idx values and append gives a new row idx = len(table), so master's own filter could produce duplicate idx after dropping a leading blank row (reproduced in the harness). (c) Order.on_cancel: filters={"order", self.name}, a set literal identical in MB, master and prod, becomes {"order": self.name}. This is outside strict porting scope; see v16_notes. Not taken from master (unchanged): its tab-indented copies of functions prod refactored, its still-buggy tuple in create_item_template_from_order, and its commented-out legacy create_bom/create_bom_for_touch.

**order.js** — dropped or changed: Nothing; the final is prod plus a newline at end of file. Unchanged in the fix round.

**order.json** — dropped or changed: repair_order moves out of prod's trailing unlabeled tab. tab_break_y79z is kept in the union but is now empty, and v16 hides empty tabs. Master's removal of the design_image_2 fetch is not taken, for the reason above; both reviewers agreed. Unchanged in the fix round; only the #913/#917 dating in this record was corrected.

**order_form.py** — dropped or changed: Nothing beyond deduplication. Unchanged in the fix round.

**order_form.js** — dropped or changed: The conflict was resolved by keeping prod's `}` (base's commented `// }` turned into the real close of the GC-format if-block), followed by master's button block. Unchanged in the fix round.

**order_form.json** — dropped or changed: Nothing semantic. The semantic merge equals prod except for where sales_type sits in the fields list (field_order is identical), so prod's bytes were taken. Unchanged in the fix round.

**order_form_detail.json** — dropped or changed: Nothing; the semantic 3-way merge is byte-identical to prod. Unchanged in the fix round. metal_purity's Silver-only visibility is why create_bom_for_touch now uses Order purity only for Silver.

**order_bom_diamond_detail.json** — dropped or changed: Nothing; the semantic merge equals prod. The line-level conflict came only from the base's reformatting. Unchanged in the fix round.

**order_bom_metal_detail.json** — dropped or changed: Fix-round finding 3 verified, no change. MB and prod both have reqd:1 on the three fields; only master removed it. That makes this a clean one-sided master change. It is also the same author's later revision: git diff 35c390c b86ee8f removes exactly those three flags and bumps modified. Recorded as a production behaviour change. Incomplete metal rows on Order, Repair Order and Customer Design Information Sheet can now be saved. For Orders, the error moves to BOM creation, where jewellery's BOM Metal Detail requires those fields. Restoring the flags is JSON-only if the owner does not want the relaxation.

**repair_order.js** — dropped or changed: The only conflict was end-of-file whitespace; prod's bytes were taken. Unchanged in the fix round.

Open points recorded for review:

- order.py create_bom_for_touch, split by metal type: please confirm with the GK team. Silver touch changes follow master: Order purity, ratio zeroing, and 1.7x rescaling for non-AD stones. Gold and other metals follow production: the touch-to-purity map and no stone rescaling. Separately, create_bom (identical on master and prod, live today) rescales non-AD stones 1.7x on every other Duplicate BOM, gold included. That may deserve its own review.
- order.py create_bom_for_touch, Silver with blank Order purity: such an order now fails at BOM insert, because BOM Metal Detail purity is reqd in jewellery_erpnext. This is master's behaviour; production would have applied the touch map. Orders drafted before this deploy carry no metal_purity, since the field arrived 2026-08-28 on prod and 2026-08-31 on master. For Silver the field is pre-filled from the source design's purity, so users must correct it.
- Two v16 paths that fail in production today will start working after deploy. First, gold 22KT/18KT 'Change in Metal Touch' BOMs: production's float header purity hits v16's link-type assertion. Second, cancelling a submitted Order that has linked Timesheets: the set-literal filter raises ValueError. After the on_cancel fix, the existing code sets those Timesheets to docstatus 2 and cancels the Order. Confirm both are wanted.
- order.py make_quotation_batch: fetching a different set of Orders now adds to the rows already on the Quotation (master). Production's #650 replaced the whole table. Only the re-fetched Orders' own rows are replaced. Confirm with the GK team.
- order_bom_metal_detail.json: master's repair-flow relaxation (metal_type, metal_purity and metal_colour no longer mandatory) also relaxes metal-row validation on Order and on Customer Design Information Sheet in production. For Orders, the error now surfaces at BOM creation.
- Existing production inconsistency, left unchanged: Order Form offers 'Repair' for order_type and flow_type, but Order fetches both into Select fields whose options lack 'Repair'. v16's _validate_selects does not skip read-only fields, so creating Orders from such an Order Form would throw.
- order.json: repair_order now sits at master's position (after salesman_name), and prod's tab_break_y79z is kept but empty (v16 hides it). The team may want to delete that tab.
- order_form.json flow_type: the final follows prod's deliberate removal of PROTO/STT/PCPM (#749; a re-add in #913 was reverted in #917). Existing records holding those values fail Select validation if re-saved.
- order.js keeps prod's debug console.log of the design id. order_form.js's new 'Get Jewelex Order Detail' button is unconditional, as on master, so it also shows on unsaved drafts. Both are cosmetic follow-ups.
- Deploy owner (cross-app, no change in this cluster): Order-based Quotations will start stamping custom_flow_type/custom_design_type (46ea145, matching jewellery's e27fb76). jewellery's Manufacturing Plan.set_order_dimensions throws when one plan's Sales Orders disagree, and blank counts as a value. Plans that mix older blank Sales Orders with newly stamped ones, or mix design types, will start failing. If multi-design plans must keep working, relax design_type on the jewellery side (the v15 lineage's SOFT_ORDER_DIMENSIONS).

### c3-pricing-sales-hooks — `ed24d61`

All five paths are written under files/ and validated: Python passes py_compile and ruff (no F821), both JS files pass node --check, and the JSON loads. PROD equals kggk_prod for every path, because gurukrupa-prod matches kggk_prod on all five.  - **item.py:** master's text is the base, adding the six whitelisted pricing endpoints jewellery calls cross-site. They come from production verbatim; names, decorators and parameters were checked against the jewellery call sites. Production's finding_size `or 0` fallback is also kept.   - Master's create_item_kggk is kept: has_variants, the six-image sync, and excluding attributes from the update payload.   - For the BOM black-bead keys I kept master's black_bead. The evidence is that production's black_beed column is unpopulated on the GK copy and absent on the KG target.   - custom_catalogue_image is read with .get(), because that field is missing on the GK-side copies.   - I removed comment lines and K's legacy drafts that embedded literal API tokens, plus K's redundant mid-file imports. - **sales_order.py:** a clean three-way merge. It keeps master's removal of a customer-specific shipping override and production's bom field mapping. The make_delivery_note signature matches ERPNext v16. - **quotation.js:** both sides made the identical "Repair" change. The final file is byte-identical to master. - **Doctype JS:** master's version; K's was the stub that master started from. - **Doctype JSON:** master's superset of 34 fields, which

| File | Decision | Conflicts resolved |
|---|---|---:|
| `gke_order_forms/doc_events/item.py` | merged | 1 |
| `doc_events/sales_order.py` | merged | 0 |
| `public/js/doctype_js/quotation.js` | merged | 0 |
| `gke_order_forms/doctype/data_migration_in_kggk/data_migration_in_kggk.js` | take_master | 1 |
| `gke_order_forms/doctype/data_migration_in_kggk/data_migration_in_kggk.json` | merged | 1 |

**item.py** — dropped or changed: (1) BOM payload: production's keys black_beed/black_beed_line are replaced by master's black_bead/black_bead_line. Same logical change, two fieldnames. Master's is newer: the deliberate rename was made when it ported K's 2026-07-27 code in ece7b4e on 2026-07-28, and K never touched those lines again. It is also the field that holds data. On the GK-side copy (gk), hundreds of BOMs populate black_bead and none populate black_beed. On the receiving KG-side copy (kg-gk), BOM has only black_bead/black_bead_line, so production's black_beed keys were silently ignored by the target. gke's own fixture also ships fieldname black_bead. This is not a v16-compat fix: jewellery defines black_beed on every line. (2) Master's `doc.custom_catalogue_image` became `doc.get("custom_catalogue_image")`. No app ships that field (it exists only in site databases), and it is absent on the GK-side copies (gk, gkprod-rehearsal.test). A v16 Document only carries attributes for meta columns, so a bare read would raise AttributeError on every Nova Glow Item save once from_site and to_site are set. Where the field exists the result is identical. (3) Removed three comment lines that embedded a literal API key:secret pair, and dropped K's two commented-out legacy drafts of create_item_kggk/create_bom_kggk, which carried hard-coded base URLs and another literal token. None of this is behaviour. (4) Dropped K's redundant mid-file `import frappe` (twice) and `from frappe.utils import flt, cint` (cint was unused). Master's top-level imports already provide frappe, requests, hashlib and flt. (5) Added a 4-line comment above the endpoints saying they are called cross-site, so they do not look dead. Master's port had omitted them.

**sales_order.py** — dropped or changed: Nothing beyond the clean three-way merge (git merge-file rc=0). Note that standard three-way semantics apply master's deliberate removal of the customer-specific shipping-address override, which production still executes. Flagged as an open question.

**quotation.js** — dropped or changed: Only one byte differs from prod: the final newline that prod's #1288 removed is kept. The final file is byte-identical to master.

**data_migration_in_kggk.json** — dropped or changed: No field dropped. modified is 2026-09-02 19:35:00.000000, the newer of master's value and K's 2026-07-15 15:37:22.702470. Four lines that master's hand-edits (081ec08, 57aea16) left mis-indented are re-indented to frappe.as_json style, and a trailing newline is added as Frappe's exporter writes it.

Open points recorded for review:

- sales_order.py validate(): gk_prod adopts master's 2026-04-20 commenting-out of a hard-coded customer-specific shipping-address override that GK live still executes. Confirm GK live no longer needs that override.
- item.py create_item_kggk: master's image sync reads Item.custom_catalogue_image. No app ships that field and it is absent on the GK-side local copies (gk, gkprod-rehearsal.test). I changed it to doc.get(), which is inert if the field exists. Confirm whether GK live has the field.
- item.py: master's image sync makes up to six synchronous GET+POST requests (15s/30s timeouts) inside Item before_validate on every Nova Glow item save, and a failed upload sends null for that image on update. This is untested on GK live; on the gk copy the sync is inactive because to_site is empty.
- Literal API key:secret pairs remain in git history on both lines, in comments in item.py. I removed them from the final file; rotate those keys if they are still valid.
- quotation.js: production PR #1288 (2026-09-20) silently reverted PR #650's custom order query get_orders_for_quotation, which also hid orders whose Item is disabled. Both current sides use plain filters, so gk_prod does too. Should #650 be restored? If not, order.get_orders_for_quotation (c2 cluster) has no caller.
- make_delivery_note override (both sides): its body predates ERPNext v16's version. It has no get_qty_already_mapped, so a second Sales Order mapped via map_docs into an existing Delivery Note can double-map quantities. It also lacks unit-price rows, filtered_children, until_delivery_date and the use_serial_batch_fields gate. Its reserved-stock path maps diamond_grade to custom_diamond_grade, which is not a Delivery Note Item fieldname, and does not map bom. All of this pre-exists on every ref and is not changed here.
- BOM sync black-bead keys: I chose master's black_bead/black_bead_line. Production's black_beed keys read an unpopulated GK column and were ignored by the KG target, whose BOM has only black_bead on the kg-gk copy. This relies on GK live's BOM having black_bead, as on the GK copies; gke's fixture ships it under the mismatched name BOM-black_beed, which is the fixtures cluster's concern.

### c4-product-return — `87d5e26`

Fix round for c4-product-return. I checked all 7 findings against git, the v16 frappe source and read-only queries on the gk and kg-gk copies. Only 2 of the 14 files changed; the other 12 are byte-identical to the previous round and were re-validated.  (1) MAJOR, confirmed and fixed (product_return_order.py). K 68884d3's Jewelex-tag guards merge cleanly against base K 7557d23, so dropping both was a manual choice and broke a real path. The stored 'Product Return Order' workflow (same on gk and kg-gk) lets Jewelex orders go Draft -> Create Item -> Send For Approval -> Approved without visiting 'BOM Calculated', so new_bom stays empty. In v16, frappe.get_doc('BOM', None) raises DoesNotExistError (load_from_db -> get_values(filters=None) -> None -> throw). Fix: master's validate is kept, so Jewelex orders still get a fresh BOM at BOM Calculated. On_submit gets a narrowed version of production's guard, 'if self.is_jewelex_tag and not self.new_bom: return'.  (2) MAJOR, confirmed and fixed (product_return_order.py). Master's on_update called get_doc('Item', variant_of) with no check. Non-variant Jewelex items exist on kg-gk. Fix: the template is pushed only when variant_of is set; the item itself is always pushed.  (3) MAJOR, confirmed and fixed (product_return_order_form.py). 'Jewelex to ERP Gemstone Mapping' is not defined in any branch, app or cluster, nor on the gk, kg-gk or alfarsi sites. git log --all -S finds it only in 081ec08. Fix: the gemstone-type lookup is skipped when 

| File | Decision | Conflicts resolved |
|---|---|---:|
| `gke_price_list/doctype/credit_note_subtype/credit_note_subtype.json` | take_master | 0 |
| `gke_price_list/doctype/credit_note_type/credit_note_type.json` | merged | 2 |
| `gke_price_list/doctype/product_return_form_e_invoice_item/product_return_form_e_invoice_item.json` | take_master | 0 |
| `gke_price_list/doctype/product_return_form_item/product_return_form_item.json` | take_master | 0 |
| `gke_price_list/doctype/product_return_order/product_return_order.json` | merged | 1 |
| `gke_price_list/doctype/product_return_order/product_return_order.py` | merged | 5 |
| `gke_price_list/doctype/product_return_order_diamond_detail/product_return_order_diamond_detail.json` | take_prod | 1 |
| `gke_price_list/doctype/product_return_order_form/e_invoice_logic.py` | take_master | 0 |
| `gke_price_list/doctype/product_return_order_form/product_return_order_form.js` | take_master | 0 |
| `gke_price_list/doctype/product_return_order_form/product_return_order_form.json` | merged | 1 |
| `gke_price_list/doctype/product_return_order_form/product_return_order_form.py` | merged | 1 |
| `gke_price_list/doctype/product_return_order_form/product_return_order_form_api.py` | take_master | 0 |
| `gke_price_list/doctype/product_return_order_gemstone_detail/product_return_order_gemstone_detail.json` | merged | 1 |
| `gke_price_list/doctype/product_return_order_metal_detail/product_return_order_metal_detail.json` | take_prod | 1 |

**credit_note_subtype.json** — dropped or changed: Only metadata changes: creation, owner and modified_by come from master's re-export. Unchanged in the fix round.

**credit_note_type.json** — dropped or changed: K's single layout-only Section Break 'section_break_dbhr' became master's equivalent 'section_break_1itk'. Neither has a DB column or a code/fixture reference. Unchanged in the fix round.

**product_return_form_e_invoice_item.json** — dropped or changed: Only metadata and fields-array order. Unchanged in the fix round.

**product_return_form_item.json** — dropped or changed: Nothing. Unchanged in the fix round.

**product_return_order.json** — dropped or changed: Nothing; the only conflict was 'modified'. Unchanged in the fix round.

**product_return_order.py** — dropped or changed: - DROPPED K 68884d3's validate guard ('if self.is_jewelex_tag: return'). Same author, newer master design: 081ec08 (09-20) added the Jewelex-only serial push, which needs the BOM; c97b25f (09-29) refined it. On GK live, Jewelex orders that go through 'BOM Calculated' now get a BOM, a serial and a remote POST at approval. - NARROWED K's on_submit guard from 'is_jewelex_tag' to 'is_jewelex_tag and not new_bom'. - FIX-ROUND additions (on neither tip): 'if item_templat:' around the template push, so a non-variant item no longer raises 'Item None not found' on every save, transition and PROF submit. The after-commit hook is registered only when frappe.get_single('Data Migration in KGGK').get('prf_to_site') is truthy; otherwise an unconfigured site saves the transition and then shows a server error. - Dropped K's stray '    # pass' line and duplicate 'errors = []'. Kept master's commented debug block. Kept the shared literal '.1244' series suffix (flagged). Whitespace-only blank lines in the edited region were normalised.

**product_return_order_diamond_detail.json** — dropped or changed: Nothing; only 'modified' conflicted. Unchanged in the fix round.

**e_invoice_logic.py** — dropped or changed: No code change in the fix round (finding 6 accepted). After deploy, the PROF 'Return Invoice Item' (credit_note_invoice_item) table starts to fill with Outright/Outwork/Hybrid lines and their tax rates. Production keyed on sales_type (Data, default 'Finished Goods Return', fallback 'Finished Goods'). Read-only checks: no E Invoice Item sales-type row on gk or kg-gk uses either value (only Outright/Outwork/Hybrid/Branch Sales/Certification), and no PROF on either copy has credit_note_invoice_item rows, so production's table is effectively empty today. In repo code this table does not feed the return Sales Invoice, which is built from PROF items and taxes. FINANCE SIGN-OFF REQUIRED before deploy.

**product_return_order_form.js** — dropped or changed: No code change in the fix round (finding 7 accepted as master's design). For ref_company 'KG' forms, entering serial_no no longer auto-fills BOM or invoice data; KG rows go through kggk_serial_no. On submit, KG forms are first pushed to the remote (see product_return_order_form.py). On GK live the impact is limited: ref_company defaults to 'GK', and every PROF on the gk copy is 'GK'. Kept the pre-existing JS 'in' bug on both tips (see open questions).

**product_return_order_form.json** — dropped or changed: Master's unchanged-from-base autoname 'format:{ref_company}-PRF-{YYYY}-{#####}' gave way to production's 'prompt', the 3-way result (only K changed it); flagged as an open question. Unchanged in the fix round.

**product_return_order_form.py** — dropped or changed: FIX ROUND, two edits on top of master. (1) In append_gemstone_detail_from_jwelex, 'if not frappe.db.exists("DocType", "Jewelex to ERP Gemstone Mapping"): continue' runs before the two lookups. v16 get_value re-raises missing-table/DocType errors when ignore is False, the default. (2) In append_diamond_detail_from_jwelex, the two debug frappe.log_error calls ('Diamond Grade', 'Diamond Grade Debug'; two Error Log rows per diamond row, holding the full Diamond Grade list) became frappe.logger().info with the same text, the app's own convention. The default ERROR log level drops them. NOW CALLED OUT: master's newer key mapping changes production's Jewelex valuation. Production read Rate/Amount and, for diamond se_rate, Costing_Amt. If the external Jewelex API omits Sale_*, rates become None and build_metal_detail's 'quantity * rate' raises TypeError at BOM Calculated. Kept as master wrote them: the one-per-document success log_error entries, and the remote calls with no request timeout. A client timeout could roll the local form back after the remote form was created and submitted, inviting duplicates on retry.

**product_return_order_form_api.py** — dropped or changed: Only the trailing newline (master). Unchanged in the fix round.

**product_return_order_gemstone_detail.json** — dropped or changed: Nothing. Unchanged in the fix round.

**product_return_order_metal_detail.json** — dropped or changed: Nothing. Unchanged in the fix round.

Open points recorded for review:

- Deploy prerequisites for master's KGGK integration on gk_prod: configure Data Migration in KGGK first: prf_to_site, api_key and api_secret; for the KGGK serial lookup also serial_no_from_site, from_site_api_key and from_site_api_secret. The remote must expose the API Server Script 'serial_product_return_order'. Until prf_to_site is set, PRO workflow mirroring is off; that is a fix-round gate, so transitions stay local as on production. Two actions fail in-transaction with a clear error and roll back: approving a Jewelex PRO that has a BOM (serial push to an empty URL) and submitting a KG-ref PROF (remote push).
- Business sign-off: master c97b25f (09-29) removed its own Jewelex/KGGK-serial gate, so once prf_to_site is set EVERY PRO workflow change is mirrored to the remote. The remote PRO gets a hard-coded counterparty customer and company, including GK-only returns. Confirm this is wanted for GK. The sync runs after commit, so a remote error appears after the local transition is saved. PROs already in flight at deploy have no remote copy, so their next transition fails the remote-state check (the sync creates the remote PRO at its default state) and keeps erroring after commit. Consider enabling mirroring only for PROs created after go-live.
- Jewelex PROs on GK live: the final keeps master's newer flow for orders that pass 'BOM Calculated': build a BOM, create a serial at Approve and POST it to the remote. Production 68884d3 skipped both. Create-Item-path orders (no BOM) keep production's skip through the narrowed guard. Confirm GK wants serials for BOM-calculated Jewelex returns. Pre-existing on both tips and now reachable for Jewelex orders: genrate_serial_no reads diamond_detail[0] whenever metal_detail is non-empty, so a metal-only Jewelex BOM raises IndexError at Approve. Even with a diamond row, the '.1244' literal suffix makes serials with the same prefix identical, so the second insert collides.
- Jewelex valuation: master's newer mapping reads Sale_Rate, Sale_Amt and Costing_Rate from the external Jewelex credit-note API; production read Rate, Amount and, for diamond se_rate, Costing_Amt. Confirm the API returns the Sale_* and Costing_Rate keys for every row type. If not, rates become None and BOM Calculated fails with TypeError in build_metal_detail.
- e-invoice (Finance sign-off): e_invoice_logic.py now keys E Invoice Item tax matching on invoice_sales_type (fallback 'Outright') and folds Hybrid making into labour. Production's sales_type key matched no E Invoice Item sales type on the local copies, and the PROF 'Return Invoice Item' table is empty there. After deploy that table fills with Outright/Outwork/Hybrid lines and their tax rates. Repo code builds credit notes from PROF items and taxes, not from this table. Check that no DB print format, Server Script or manual filing process relies on it.
- PROF naming: the final keeps production's autoname 'prompt' (K dc1c204) over master's 'format:{ref_company}-PRF-{YYYY}-{#####}'. If gk_prod, the sync source, should generate names automatically, restore master's format, but first check GK live for user-typed names that would collide with the series counter.
- No request timeout was added to sync_product_return_form_to_remote (reviewer finding 7 suggested considering one). A client timeout could roll the local PROF back after the remote PROF was created and submitted, inviting duplicates on retry. A safe fix needs an idempotent remote create (look up by name first). Recommended as a separate change.
- Error Log noise still present: master's one-per-document success entries ('Serial No Synced Successfully', 'Remote Product Return Form Created/State/Submitted') were kept as master's audit trail. Only the per-diamond-row debug entries moved to frappe.logger. Decide whether to move these as well.
- Security: master commit 4f5c313 (2026-08-23) committed a literal API key:secret pair and a hard-coded remote URL in product_return_order.py. 081ec08 removed it, but it stays in the public repository history; recommend rotating that key. The value is not reproduced here and is absent from all final files.
- Pre-existing on both tips and kept: product_return_order_form.js tests 'frm.doc.return_subtype in [...]', which in JS checks array indices, so the amount-copy block for three return subtypes never runs. K's fix 3c23349 was reverted by dc1c204, and re-applying it would change credit-note amounts, so a business decision is needed. Also pre-existing: '_' undefined in _set_hybrid_gst_details; update_making_charges and _calculate_diamond_amount undefined in the uncalled update_bom_details; and in product_return_order_form_api.py, 'Product Return  Order Form' (double space) and the unshipped DocType 'Credit Note Order'.
- Optional cleanup: master-only stray nested copy doctype/customer_scorecard/product_return_form_e_invoice_item/ (added by 6c9838c). v16 sync does not import it; consider deleting it.

### c7-catalogue-survey — `dd838b8`

Fix round for c7-catalogue-survey. Both findings were checked against git and the v16 source.\n\nFinding 1 (major, report JSON) is real and is fixed in /home/dhinesh/bench/v16/wt/evidence/gkprod/work/ports/c7-catalogue-survey/files/gke_customization/gke_catalog/report/warehouse_wise_consumable_consumption/warehouse_wise_consumable_consumption.json.\n- The file is now production's file with exactly two lines changed: report_type is 'Script Report' and filters is [] (both master/base values).\n- Kept from both sides: report_script removed. Kept from production: letter_head and letterhead removed, modified/modified_by absent (so every migrate re-imports the file and replaces GK live's broken row), and the unused query text.\n- Production's 'v16 compatibility' conversion is not needed by v16 and is what breaks the report there. The kg-gk Error Log also holds a real 2026-09-16 run that failed with the same SQL error.\n- A read-only check on gk (v16, frappe 16.33.0) used an in-memory doc and the same server path as query_report._run. The fixed JSON returns rows for a non-Administrator System Manager and for Administrator with no group, one group, two groups and group plus warehouse. The default open over about 252k Stock Entries takes about 6 s. Production's JSON fails in every case except Administrator with one group.\n- The output now matches master's detailed rows instead of production's item x warehouse totals; this is recorded as an open question for GK.\n\nFinding 2 (minor, c

| File | Decision | Conflicts resolved |
|---|---|---:|
| `gke_catalog/report/warehouse_wise_consumable_consumption/warehouse_wise_consumable_consumption.json` | merged | 1 |
| `gke_catalog/api/catalogue_api.py` | take_prod | 0 |
| `gke_catalog/report/item_wise_stock_dashboard/item_wise_stock_dashboard.js` | take_prod | 1 |
| `gke_catalog/report/item_wise_stock_dashboard/item_wise_stock_dashboard.py` | take_prod | 1 |
| `gke_survey/doctype/questionnaire_response/questionnaire_response.json` | take_master | 0 |
| `gke_survey/page/questionnaire_runner/questionnaire_runner.py` | take_master | 0 |

**warehouse_wise_consumable_consumption.json** — dropped or changed: Fix round: production's Query Report form is replaced. The 3-way merge applied production's JSON Link filter cleanly (only production changed filters) and left one hunk on report_type. Round 1 took production for both. Now report_type is 'Script Report' (master/base value) and filters is [] (master/base value, overriding the clean auto-merge). The final file is production's file with exactly these two lines changed. Why production's 'v16 compatibility' commit does not win: it is not a v16 requirement, and it breaks the report on v16. On v16, a standard Script Report runs its .py through Report.execute_module (report.py:202-228). get_script loads the folder .js for every report type. The .js defines its own filters, so the JSON filter never reaches the UI (query_report.js:444). That filter is still checked by validate_filters_permissions (query_report.py:1157-1186), which passes the MultiSelectList value (always a list) to has_permission. For a non-Administrator with any group picked, that crashes in get_doc_permissions (permissions.py:232). Output change to record: production's intended item x warehouse totals (Item Code, Item Name, Item Group, Department, Qty, Cost) are replaced by master's detailed rows per item, warehouse, date, entry type, company and branch, plus a summary. On v16, production's form only ever returned data for Administrator with exactly one group, and it ignored the date and warehouse filters.

**catalogue_api.py** — dropped or changed: PROD(p) = gurukrupa-prod, because kggk_prod and mb_kg lack the path. The base is the master revision that gurukrupa-prod copied: master tip 9e0673f, which differs by only the 4 hunks. Base equals master, so the merge exits 0 and gives gurukrupa-prod's file. Nothing is dropped. No other code in the repo reads the catalogue_image key. Fix round: no code change (see cross_app_notes).

**item_wise_stock_dashboard.js** — dropped or changed: Add/add case (MB has no file). Master added the report on 2026-04-22 (7ce51ce) and never edited it again. kggk_prod added it on 2026-07-15 (#961, 6278f90/e1fa082). The two share the same report JSON (9a3e077e), and kggk's code is a clear evolution of master's. With master's file as the inferred base, the three-way merge gives production's file, which also follows the newest-by-commit-date rule. Dropped: the company-based warehouse get_query (see master_behaviours_kept).

**item_wise_stock_dashboard.py** — dropped or changed: Add/add case, resolved as for the .js: master's never-edited April copy is the inferred base, so production's July edits apply cleanly. The company filter value is ignored (production behaviour); company is still a required filter in the JS.

**questionnaire_response.json** — dropped or changed: Add/add with MB missing. The base is master@b7ccbd1, which equals production, so the three-way merge exits 0 and gives master's file. Nothing is dropped.

**questionnaire_runner.py** — dropped or changed: Add/add with MB missing. The base is master@b8c5a23, which equals production, so the three-way merge exits 0 and gives master's file. Nothing is dropped.

Open points recorded for review:

- catalogue_api.py deploy prerequisite. Confirm that Item.custom_silver_image exists on GK live. catalogue_data22 selects it directly, and catalogue_data2 selects it through get_is_filter. No repo ships the column, and kg-gk, gk and the gkprod-rehearsal.test copy all lack it, so both endpoints fail there with 'Unknown column'. gk and the rehearsal copy also lack custom_catalogue_image, which master's code already selects. If GK live lacks the column, two options: (1) ship it as a Custom Field with module 'GKE Catalog' or 'GKE Order Forms', so the hooks fixture filter exports it (fixtures/custom_field.json belongs to the fixture-curation track); or (2) add an idempotent patch. Either way, the field definition (type, label, insert_after) must come from GK.
- warehouse_wise_consumable_consumption: tell GK that this report goes back to master's Script Report output. That output is detailed rows per item, warehouse, date, entry type, company and branch, plus a summary. It replaces production's item x warehouse totals, which on v16 only ever worked for Administrator with exactly one group. If GK wants a totals view, add it to the .py (for example a group-by option) rather than converting to a Query Report again.
- item_wise_stock_dashboard: production ignores the Company filter, which is still required, and lists all allowed consumable warehouses across companies. Master's April copy scoped results by company. Production's version was kept as the newer one that GK live runs; master's company-scoped code survives as the master-only 'Consumable Stock Balance' report. Confirm GK wants cross-company results here.

### c5-revise-price-lists — `6934d29`

Fix round. I checked all four review findings against git, the frappe v16 source and read-only queries on the gk and kg-gk copies.  (1) MAJOR, confirmed and fixed. The rename patch was never registered: c1's patches.txt has an empty [pre_model_sync] section. In v16, SiteMigration runs pre_model_sync patches, then sync_all, then post_model_sync patches. Fixtures sync and remove_orphan_doctypes come after that, and remove_orphan_doctypes deletes only the DocType record. Without the line, a site still on the two-space DocType would get an empty new DocType and orphaned data. The diamond DocType has "permissions": [] on every ref, so access depends on Custom DocPerm. New cluster file files/gke_customization/patches.txt is c1's file plus one line, gke_customization.patches.rename_revise_diamond_price_list_doctype, directly under [pre_model_sync]. Every existing line is byte-identical, and v16 parse_as_configfile gives pre=[rename] and post=[the same 3 lines]. The file is recorded in extra_paths with its exact content and supersedes c1's copy.  (2) MINOR, confirmed and fixed. frappe.rename_doc moves Client Script.dt (a Link) but never script text. v16 loads Client Scripts by dt, and they register handlers by name. The patch now reads the old DocType's Client Scripts before the rename, then replaces the old name with the new one in their text (set_value with update_modified=False, then clear_cache for the doctype). This is what Frappe's own DocType.rename_inside_controller does for 

| File | Decision | Conflicts resolved |
|---|---|---:|
| `gke_price_list/doctype/revise_diamond_price__list/revise_diamond_price__list.json` | deleted | 0 |
| `gke_price_list/doctype/revise_diamond_price__list/revise_diamond_price__list.py` | deleted | 0 |
| `gke_price_list/doctype/revise_diamond_price_list/revise_diamond_price_list.json` | merged | 0 |
| `gke_price_list/doctype/revise_diamond_price_list/revise_diamond_price_list.py` | merged | 1 |
| `gke_price_list/doctype/revise_gemstone_price_list/revise_gemstone_price_list.json` | merged | 20 |
| `gke_price_list/doctype/revise_making_charge_price/revise_making_charge_price.json` | take_master | 2 |
| `gke_price_list/doctype/revise_making_charge_price/revise_making_charge_price.py` | take_master | 4 |

**revise_diamond_price__list.json** — dropped or changed: Only the old path goes; its content moves to the renamed file. On sites that still have the old DocType, the data is carried over by the pre_model_sync rename patch. This fix round registers that patch in gke_customization/patches.txt under [pre_model_sync] (see extra_paths). Without the registration, sync_all would create an empty new DocType and remove_orphan_doctypes would orphan the old table.

**revise_diamond_price__list.py** — dropped or changed: Old path only; nothing behavioural is lost. Documents on sites that still have the old DocType move with the now-registered pre_model_sync rename patch.

**revise_diamond_price_list.json** — dropped or changed: Nothing. The three-way merge (base MB old path, master old path, K new path) was clean. Unchanged in this fix round.

**revise_diamond_price_list.py** — dropped or changed: The one conflict (the crate_price_list stone_code hunk) resolves to master's side, which already contains K's edit. One compatibility helper was added: diamond_price_list_has_sales_type(). When the field is missing, it drops the sales_type key from the before_save filters, the on_submit set_value dict and the for_weight_in_cts filters. When the field exists, master's behaviour is unchanged. K's write of the row's supplier_fg_purchase_rate is replaced by master's newer new_outwork_rate flow. Reviewer finding 4 (minor) confirmed this guard and asked for no change, so the file is unchanged this round. Trade-off: on v16 sites without the field, revisions do not split Diamond Price List rows into Outright and Outwork (see open questions).

**revise_gemstone_price_list.json** — dropped or changed: Dropped the K/MB-only fields of the old controller that master's redesign replaced. These are date, customer_name, stone_type/quality/size, the handling-charge checkboxes and rate fields, the old details section, the parent rate_per_carat/revised_rate/difference/gemstone_price_list, and K's "Multiplier" depends_on breaks. Nothing else reads them, and gk and kg-gk hold no documents of this doctype (re-checked this round). Deliberate deviation from master (reviewer finding 3, minor, confirmed): master's "permissions": [] is replaced by production's System Manager row. It is the only difference from master's JSON (verified by diff). In v16, sync replaces DocPerm rows from the JSON, so master's empty list would remove System Manager access on GK live. gk and kg-gk have only that standard row and no Custom DocPerm (re-checked). Where Custom DocPerm exists it overrides the row. Left as is pending GK confirmation (open question).

**revise_making_charge_price.json** — dropped or changed: Two conflicts. K's mis-indented making_components field_order line gives way to master's correctly formatted line, and modified takes master's newer value (K: 2026-02-10). Unchanged this round.

**revise_making_charge_price.py** — dropped or changed: Four conflicts, all resolved to master: - two are K's extra whitespace-only lines - one is K's line "making_charge_price_doc.metal_type = self.metal_touch", which overwrote metal_type; master's correction (5f71bf6, 2026-06-13, later than K's 4c50778) sets metal_touch and the gold rates instead - the last takes master's superset, which adds the finding-subcategory creation loop Unchanged this round.

Open points recorded for review:

- Assembly: gke_customization/patches.txt belongs to cluster c1, but it must carry this cluster's [pre_model_sync] line. c5's files/gke_customization/patches.txt is c1's file plus that one line, and the extra_paths entry gives its exact content. Take c5's copy, or add the line to c1's copy under [pre_model_sync] and not post. Otherwise the rename patch never runs.
- Fixtures track: K/G fixtures/custom_field.json still contains "Revise Diamond Price  List-workflow_state" with dt set to the old two-space name. It is entry 207 of 2083 in G's file. With data_import=True, v16 runs Custom Field.validate, and its get_meta on the missing old DocType raises DoesNotExistError. import_fixtures then skips the remaining ~1876 rows of custom_field.json. That happens on GK live today, and after the rename it will also happen on master-line sites. The rename patch's re-key stops this row from deleting the renamed doctype's live workflow_state field, but the row itself must still be dropped or re-targeted (name "Revise Diamond Price List-workflow_state", dt "Revise Diamond Price List").
- Deploy runbook: on any site where the rename patch actually renames (a site still on the two-space DocType), read the migrate output for lines containing "still mentions 'Revise Diamond Price  List'". Fix those Server Scripts, Reports, Print Formats, Notifications or other DocTypes' Client Scripts by hand. The patch rewrites only the renamed doctype's own Client Scripts.
- Pre-rename data on GK live: #825 shipped without a patch. The local gk copy shows the result: an orphaned `tabRevise Diamond Price  List` table holding documents from before the rename, detail rows still under the old parenttype, an orphaned old-name Client Script, and Custom DocPerm rows on the old name. One role's access on the old name was never re-granted on the new one. GK live probably looks the same. The patch deliberately does nothing there, because the old DocType record is gone. Decide whether to recover those documents (no name clash with the new table) or leave them archived.
- Diamond Price List sales_type: master's Revise Diamond Price List matches and writes Diamond Price List.sales_type. No jewellery_erpnext line here defines that field, and neither local database has the column. The port uses it only when the field exists (reviewer finding 4 accepted this). If GK wants Outright/Outwork-specific diamond prices on v16, add the field (in jewellery_erpnext or as a custom field) and fill it on existing rows; master's filter then excludes rows that have no value.
- Diamond on_submit (master's logic, kept): supplier_fg_purchase_rate is written from each row's new_outwork_rate. Sieve Size Range and Size (in mm) rows never pre-fill that field, and it is hidden unless Sales Type = Outwork, so submitting an Outright revision of those types clears the outwork rate. Worth a follow-up with GK.
- Gemstone (master's code, kept): the final controller's non-Fixed (Diamond Range) branch still sets and reads the parent fields rate_per_carat, revised_rate and gemstone_price_list, which master's JSON dropped. Submitting a non-Fixed Revise Gemstone Price List would therefore raise AttributeError. The multiplier tables also have no submit logic. GK should finish or confirm that path.
- Gemstone permissions (deliberate deviation from master, review finding 3): master's JSON set "permissions": []. The port keeps production's System Manager row, because v16 sync would otherwise strip standard access on GK live, where gk and kg-gk show no Custom DocPerm for this doctype. Ask GK to confirm whether removing standard access was intended. If it was, restore [] and grant access through Custom DocPerm before deploy.
- Unchanged on both sides: the diamond controller reads Diamond Price List.handling_rate, which the v16 jewellery doctype does not define. It works only where a leftover column exists (present on the gk copy, absent on kg-gk).

