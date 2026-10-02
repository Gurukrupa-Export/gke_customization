# gk_prod migration

`gk_prod` is GK's new production line: **current `master` plus the production behaviour that until now lived only on `kggk_prod` and `gurukrupa-prod` (GK live)**, rebuilt as a reviewable branch instead of merging eight months of divergence. This folder is the audit trail: every source commit, every decision, every conflict and every test.

## Read in this order

| File | What it answers |
|---|---|
| [00_branch_baseline.md](00_branch_baseline.md) | Which SHAs were used, how far the branches had diverged, how the history is shaped |
| [01_commit_inventory.md](01_commit_inventory.md) + [csv](01_commit_inventory.csv) | All 507 unique production commits, the unit (PR) each belongs to, its status and where it landed |
| [02_gurukrupa_prod_delta.md](02_gurukrupa_prod_delta.md) | The 6 GK-live-only and 7 kggk_prod-only commits, each answered against the brief's questions |
| [03_feature_parity_matrix.md](03_feature_parity_matrix.md) | Feature by feature: master / kggk_prod / GK live / gk_prod |
| [04_commit_promotion_matrix.md](04_commit_promotion_matrix.md) | Per logical change: original PR and SHAs, master equivalent, port method, new SHA |
| [05_rejected_commits.md](05_rejected_commits.md) | Everything not carried, with the reason; partially carried units |
| [06_cherry_pick_plan_and_conflicts.md](06_cherry_pick_plan_and_conflicts.md) | Order of work, replay checkpoints, every consolidated port with its per-file resolution and open points |
| [07_schema_fixtures_patches.md](07_schema_fixtures_patches.md) | Files/DocTypes/reports added and removed, fixture curation, patches, hooks differences |
| [08_test_evidence.md](08_test_evidence.md) | Exact commands, sites, SHAs and results of every check |

## Outcome at a glance

- **507 source commits in 179 units, each accounted for exactly once** (trailer-checked):
  ported 284 (92 units) · already in master 140 (57) · superseded 44 (15) · reverted 30 (12) · excluded as KGGK-only 9 (3).
- **90 commits on the migration branch**: 71 replayed production commits (original authors and dates, `cherry-pick -x` provenance), 7 consolidated three-way ports for the files both sides changed, 3 fixture commits (curation, row order, GK's current values), 3 business-decision commits, 4 v16-compatibility fix groups for master-only code, 1 security fix and this documentation.
- **The final tree equals an independently assembled oracle** (replay simulation + recorded decisions), so nothing outside the recorded decisions changed.
- **No master file is lost**: the only 9 deletions are two intentional moves (see 07).

## Business decisions (checkpoint 2026-10-02)

| Area | Decision |
|---|---|
| HR / Accounts | take master's newer logic: OT allowance uses master's check-in-pair recompute; the Sales Invoice company-specific validate stays disabled; Product Return e-invoice tax matching keys on `invoice_sales_type` |
| Orders / returns | take master's: no hard-coded customer shipping-address override in Sales Order; fetching Orders into a Quotation adds to existing rows; BOM-calculated Jewelex returns build a BOM and serial using the `Sale_*`/`Costing_Rate` keys; Silver touch-change BOMs use the Order's purity; metal fields not mandatory in repair flows |
| Access / KGGK | restore the GK roles on the 25 reports #1057 rewrote (alongside the current roles); **do not** carry the KGGK Jewelex - ERP Order Tally report family; keep the Order form's design-id `console.log` as GK live has it; keep the Product Return Order → KGGK sync gated to Jewelex-tag and KGGK-serial returns |
| Nova Glow | ship master's rename patch; deploy in a joint KG + GK window with a backup |

## Decided by default — please confirm in review

- **Warehouse wise Consumable Consumption** returns to master's Script Report (detailed rows per item/warehouse/date/entry type with a summary) instead of GK live's item × department totals, which on v16 only work for Administrator. Not asked at the checkpoint.
- **create_bom_for_touch** is split by metal type: Silver follows master (Order purity), gold and other metals keep production's touch-to-purity map.
- **OT Allowance Entry** also restores `old_employee_code` as the week-off sort key (lost in a master refactor).
- **Product Return Order Form** keeps production's naming (`prompt`) over master's series format.
- **Revise Gemstone Price List** keeps production's System Manager permission row (master's JSON had none, which would remove standard access on sync).

## Before deploying (not done by this PR)

1. Take a full backup of the GK site. Deploy in a window agreed with KG (Nova Glow, see 07).
2. Run on the same hrms version GK live runs today: gke's Salary Slip and Salary Structure Assignment overrides import `COMPONENT_EVAL_GLOBALS`, which this bench's hrms 16.5.4 lacks (identical on GK live's current code).
3. Confirm `Item.custom_silver_image` and `Item.custom_catalogue_image` exist on GK live (catalogue endpoints select them; no app ships them).
4. `pyodbc` is now imported lazily; install it (with unixODBC) only if the PD-to-production and CSAT endpoints are used.
5. Leave **Data Migration in KGGK** unconfigured until KG is ready; Product Return Order mirroring and the KGGK serial push are inert until `prf_to_site` is set.
6. After deploy: `bench --site <site> migrate`, then `clear-cache`; read the migrate output for `Deleting entity Report KGGK Jewelex - ERP Order Tally` (expected) and nothing else deleted.

## Pre-existing issues found (recorded, not changed here)

- Credentials committed to this public repository's history (API key pairs in old `item.py` comments, master commit 4f5c313, the KGGK tally `jewelex_db_config.py`, and the hard-coded keys in master's `encryption_response.py`). Rotate them; move secrets to site config.
- Undefined names that raise at runtime when reached: `product_return_order_form.py` (`_`, `update_making_charges`, `_calculate_diamond_amount`), `gold_rates.py` (`action`), `holiday_punch.py` overnight branch (`add_days`).
- Gold-rate scheduler: three cron entries for one method collapse to a single job (23:00) — as on GK live.
- Secured and Unsecured Loan links to a Payment Entry field no app ships; dead hooks (Solitaire Calculator `calculate_rate`, a Payment Entry JS path); Monthly In-Out Log compares times without dates for overnight shifts.
- `make_delivery_note` override predates ERPNext v16's version (no already-mapped quantity check).
