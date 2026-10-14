# 02 — gurukrupa-prod delta

`gurukrupa-prod` (GK live, `c94f0475c5d5`) and `kggk_prod` (`3d6c61ac921c`) split at `cc654ee00ae3` on 2026-09-27. Since then gurukrupa-prod has **6** commits kggk_prod lacks and kggk_prod has **7** commits gurukrupa-prod lacks. All 13 were analysed; none was omitted.

## Commits only on gurukrupa-prod

| Commit | Date | Author | Subject | Unit | Final status | New commit |
|---|---|---|---|---|---|---|
| `b94d417a9a` | 2026-09-30T19:09 | Devendra Pandey | 29-09-2026 Logic Update in api for Ot deducation after shift end (#1349) | gkp:1 (#1356) | PORT | `be0c216` `dd838b8` |
| `1284254966` | 2026-09-30T19:58 | bhavika-gkexport | 30-09-2026 update in monthly in_out log py file | gkp:1 (#1356) | PORT | `be0c216` `dd838b8` |
| `cc51163723` | 2026-09-30T21:15 | bhavika-gkexport | 30-09-2026 update in gke_catalogue api file | gkp:1 (#1356) | PORT | `be0c216` `dd838b8` |
| `20d3c28c8c` | 2026-09-30T21:16 | Devendra Pandey | Bhavika gk v16 (#1356) | gkp:1 (#1356) | PORT | `be0c216` `dd838b8` |
| `fde2e28044` | 2026-09-30T21:34 | bhavika-gkexport | 30-09-2026 update in holiday punch py file | gkp:2 (#1358) | SKIP_ALREADY_IN_MASTER | — |
| `c94f0475c5` | 2026-09-30T21:34 | Devendra Pandey | 30-09-2026 update in holiday punch py file (#1358) | gkp:2 (#1358) | SKIP_ALREADY_IN_MASTER | — |

## Commits only on kggk_prod

| Commit | Date | Author | Subject | Unit | Final status | New commit |
|---|---|---|---|---|---|---|
| `da2a97ce78` | 2026-09-29T18:46 | bhavika-gkexport | 29-09-2026 Logic Update in api for Ot deducation after shift end | kggk:175 (#1350) | SKIP_ALREADY_IN_MASTER | — |
| `361835e1ad` | 2026-09-30T19:21 | Devendra Pandey | 29-09-2026 Logic Update in api for Ot deducation after shift end (#1350) | kggk:175 (#1350) | SKIP_ALREADY_IN_MASTER | — |
| `5497c7f9f7` | 2026-09-30T21:23 | bhavika-gkexport | 30-09-2026 update in monthly in-out log py file | kggk:176 (#1357) | PORT | `be0c216` |
| `e7f8cf3fcb` | 2026-09-30T21:24 | Devendra Pandey | 30-09-2026 update in monthly in-out log py file (#1357) | kggk:176 (#1357) | PORT | `be0c216` |
| `259e83605b` | 2026-09-30T23:24 | sandeep-m-gk | Kggk prod (#1359) | kggk:177 (#1360) | PORT | `c9c77f4` |
| `03c43d9df7` | 2026-09-30T23:30 | sandeep-m-gk | reports update | kggk:177 (#1360) | PORT | `c9c77f4` |
| `3d6c61ac92` | 2026-10-01T00:25 | Devendra Pandey | Sandepp v16 dummy (#1360) | kggk:177 (#1360) | PORT | `c9c77f4` |

## The questions, per change

### gkp:1 — #1356 Bhavika gk v16 (#1356)

GK-live PR into gurukrupa-prod with three parts. (a) b94d417a is master's #1349 personal-out deduction (patch-identical). (b) 12842549 is the out_time-past-shift-end clamp (patch-identical to unit 176). (c) cc511637 copies 28 gke_catalog/api modules from master; 27 are byte-identical to master head, including item_catalog.py. Its catalogue_api.py also selects item.custom_silver_image in get_is_filter and catalogue_data22, and renames the response key catalogue_image to custom_catalogue_image in get_similar_item and get_set_by_itemcode.

- **What does it do?** Since 2026-09-30 GK live serves master's catalogue and portal API modules (portal_api, portal_orders_api, login, issues, dashboards, wishlist download, internal catalogue, encryption_response, and others). Catalogue listing endpoints return a silver image column, and the similar-item and set endpoints return custom_catalogue_image. HR personal-out deduction is as in units 175/176.
- **Why is it on one branch only?** Merged straight into gurukrupa-prod (GK live) on 2026-09-30 as PR #1356 from bhavika_gk_v16; kggk_prod received the HR part separately (#1350, #1357) and never the catalogue part.
- **Intentional?** Yes — a deliberate GK-live PR.
- **Hotfix?** Partly: the shift-end clamp is a same-day HR fix; the catalogue part is a feature sync from master.
- **Newer?** Yes — newer than kggk_prod's head for the catalogue API.
- **Reverted?** No.
- **Live-required?** Yes — GK live runs it.
- **Belongs in gk_prod?** Yes. The personal-out deduction (b94d417a) is patch-identical to master #1349 and needs nothing; the shift-end clamp (12842549, same as kggk #1357) and the catalogue-API delta (cc511637: `custom_silver_image` in listings, `custom_catalogue_image` key in similar-item/set responses) are carried by the consolidated ports `be0c216` (hrms) and `dd838b8` (catalogue).

### gkp:2 — #1358 30-09-2026 update in holiday punch py file (#1358)

Holiday Punch rewrite. process_attendance_from_rows computes late_entry (shift late grace) and early_exit (before shift end, overnight-aware), db_sets both after submit, sorts a copy of the rows, and changes the skip guard. check_employee_punch fills missing time with synthetic IN/OUT rows before the first punch (from shift start) and after the last punch (to shift end), replacing the odd/even punch logic.

- **What does it do?** On GK live, holiday-punch attendance carries late and early flags and full-shift gap fill. This is identical to master's #1354.
- **Why is it on one branch only?** Merged into gurukrupa-prod as PR #1358; master got the same rewrite as #1354, kggk_prod never did.
- **Intentional?** Yes.
- **Hotfix?** Yes — a holiday-punch attendance fix (late/early flags, full-shift gap fill).
- **Newer?** Same age as master's #1354 (2026-09-30).
- **Reverted?** No.
- **Live-required?** Yes — GK live runs it.
- **Belongs in gk_prod?** Yes, and gk_prod already has it: GK live's holiday_punch.py equals master's apart from blank lines, so it is retained from master (SKIP_ALREADY_IN_MASTER).

### kggk:175 — #1350 29-09-2026 Logic Update in api for Ot deducation after shift end (#1350)

Personal-out deduction clamped at shift end: a new correlated pol_deduction_subquery sums Personal Out Log durations with in_time capped at shift end. It is exposed as p_out_deduction_hrs (also by attendance_api_new) and drives net working hours for late or personal-out days and the monthly P-Out total. Personal Out Entry now also counts checkouts exactly at shift end (>=).

- **What does it do?** Employees are not penalised for personal-out time beyond shift end in Monthly In-Out Log, the attendance API and their consumers (attendance request, leave application, monthly checkin report).
- **Why is it on one branch only?** Merged into kggk_prod on 2026-09-30 (#1350) after gurukrupa-prod was cut from it; GK live carries the same patch inside #1356 (b94d417a).
- **Intentional?** Yes.
- **Hotfix?** Yes — personal-out deduction clamped at shift end.
- **Newer?** Same change as master #1349 (af896a3c).
- **Reverted?** No.
- **Live-required?** Yes — on GK live through #1356.
- **Belongs in gk_prod?** Yes, and gk_prod already has it from master (patch-identical; SKIP_ALREADY_IN_MASTER).

### kggk:176 — #1357 30-09-2026 update in monthly in-out log py file (#1357)

In Monthly In-Out Log's personal-out deduction subquery, a Personal Out Log whose out_time is already past shift end now contributes 0. Before this, it produced a negative clamped TIMEDIFF that reduced the deduction and inflated net working hours.

- **What does it do?** Personal-outs taken after shift end no longer distort net working hours or total P-Out in Monthly In-Out Log and everything built on get_attendance_details_by_date (attendance API, attendance request, leave application, monthly checkin report). The same change is live on GK through gkp1 member 12842549 (patch-identical).
- **Why is it on one branch only?** Merged into kggk_prod on 2026-09-30 (#1357); GK live has the identical change inside #1356 (12842549).
- **Intentional?** Yes.
- **Hotfix?** Yes — a personal-out after shift end no longer reduces the deduction.
- **Newer?** Newer than master (master lacks it).
- **Reverted?** No.
- **Live-required?** Yes — on GK live through #1356.
- **Belongs in gk_prod?** Yes — carried by the hrms consolidated port `be0c216` (master changed the same file).

### kggk:177 — #1360 Sandepp v16 dummy (#1360)

Four gke_catalog report changes. (1) Branch Stock Summary: WIP weight is counted once per MWO (only the furthest-progressed open operation, via a ROW_NUMBER window subquery); Work Order/Employee/Supplier WIP and Finished Goods only appear when new checkboxes are ticked; Finished Goods are valued by BOM weight (Serial No.custom_bom_no) instead of a serial count; new Manufacturing-warehouse bucket; per-department N+1 queries replaced by bulk queries; empty departments and rows hidden; company filter made visible; new 'Summary' dialog backed by a whitelisted get_summary_comparison that reconciles the total against ERPNext Stock Balance. (2) Employee Batch Issue Receive: debug Error Log writes and date filters removed; the latest Issue/Receive per (MOP, employee) is kept; only issued-but-not-received rows are shown. (3) New Everyday Work Report: Employee IR x MWO x PMO worker listing. (4) New Product Lifecycle: custom-HTML report tracing an item or tag across Sketch Order, CAD Order Form/Order, Repair Order, Serial No weights, Purchase Receipt, Stock Entry, Serial Number Creator, Product Certification and Refining.

- **What does it do?** On kggk_prod (merged 2026-10-01, not yet on GK live): manufacturing stock and WIP reports change their defaults and semantics as described; two new reports are available.
- **Why is it on one branch only?** Merged into kggk_prod on 2026-10-01 (#1360, with the #1359 sync); gurukrupa-prod was not updated after 2026-09-30.
- **Intentional?** Yes.
- **Hotfix?** No — report features (Branch Stock Summary rework, Employee Batch Issue Receive, new Product Lifecycle and Everyday Work reports).
- **Newer?** Yes — the newest production change on either line.
- **Reverted?** No.
- **Live-required?** Not yet on GK live; it is kggk_prod head behaviour and its reports serve both GK (GE roles) and KGJPL.
- **Belongs in gk_prod?** Yes — replayed as `c9c77f4` (PR net change, `-m 1`). Master has no equivalent.

## Verification points carried to deploy

- `Item.custom_silver_image` is selected by the catalogue listing endpoints (from #1356) but no fixture or app defines it; it must exist on the target site (it does on GK live, where #1356 runs). Listed in 07 as a follow-up.
- The external catalogue portal frontend must expect `custom_catalogue_image` from `get_similar_item` / `get_set_by_itemcode` (GK live already returns it).
- The shift-end clamp compares `TIME()` values only; for overnight shifts the result is still not correct (pre-existing, recorded in 05 as a follow-up).
