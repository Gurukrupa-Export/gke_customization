# 08 — Test evidence

Everything below was run on this machine's v16 bench against throwaway sites, with the code under test proven by path (`frappe.get_app_path` pointed at the worktree being tested). Raw logs, JSON results and dumps are kept in the local evidence tree (`wt/evidence/gkprod/`), not in the repository.

## Environment

| | |
|---|---|
| Frappe / ERPNext / HRMS / India Compliance | 16.33.0 / 16.34.1 / 16.5.4 / 16.7.0 |
| jewellery_erpnext | `gurukrupa-prod` @ `8c1357a8` (the line GK live runs) |
| gke baseline code | `gurukrupa-prod` @ `c94f0475` (GK live) |
| gke candidate code | `migration/gk-prod-reconstruction`: `670242a0` for the first rehearsal migrates, report smoke and contract checks; `ecd9b531` (the final code: adds the login fix to one HR API module and the two fixture fixes) for the final migrates, re-runs and tests; fresh install with `de33ad34` (+ third migrate with `ecd9b531`). The last commit only adds this folder. |
| Python / MariaDB | 3.14.3 / 10.11 (InnoDB buffer pool lowered to 3 GB for the duration, restored afterwards) |
| Isolation | private Redis pair (13190/11190), outbound HTTP blocked through a dead proxy, `CI` unset, code via `PYTHONPATH` worktrees |

## Sites

| Site | What it is |
|---|---|
| `gkprod-rehearsal.test` | upgrade rehearsal: a **copy of the local `gk` site** (GK-line schema and data; no backup of GK live was available, so this is a proxy — its transactional data ends in August 2026) restored with safety switches on (scheduler paused, emails muted, GST/e-invoice off, KGGK link blanked, webhooks and email accounts disabled) |
| `gkprod-fresh-base.test` | fresh install with GK live's code (fails) |
| `gkprod-fresh-cand.test` | fresh install with the candidate code |

## Static checks

| Check | Command | Result |
|---|---|---|
| compileall | `PYTHONPYCACHEPREFIX=<scratch> env/bin/python -m compileall -q gke_customization` | exit 0, 0 errors (whole app) |
| json_parse | `json.load every tracked *.json` | 0 failures |
| conflict_markers | `grep -E '^(<<<<<<<\|>>>>>>>)( \|$)\|^=======$' over the 408 changed files` | none |
| node_check | `node --check on every changed .js` | 96 files, 0 failures |
| ruff | `~/.cache/pre-commit/.../ruff check --isolated --select F821,F811,F822,F823 <198 changed .py files> (probe file confirmed the checker reports F821)` | 8 F821 (undefined name) and 32 F811 (redefinition); every F821 is byte-identical on master, kggk_prod and gurukrupa-prod (pre-existing); F811 counts per file equal the source branch they came from (no duplicate introduced) |
| oracle | `build_oracle.py decisions.json (replay simulation tree + 137 recorded decisions) vs HEAD^{tree}` | identical: tree 5cd249e5 at 670242a (137 decisions) and tree df49eeda at f482786 after the security fix (138 decisions) |
| accounting | `accounting.py` | 507 source commits in 179 units, each in exactly one unit; 71 replay commits = 71 applied dry-run records; 0 problems |
| coverage | `every path held back during replay has a port decision` | 51 held-back paths: 43 decided by the 7 ports, 8 converged (identical on master, kggk_prod, gurukrupa-prod) |

## Upgrade rehearsal (GK site copy)

| Step | Command | Result |
|---|---|---|
| restore | `bench new-site gkprod-rehearsal.test --source-sql <gk dump>` | exit 0 |
| baseline migrate (GK live code) | `bench --site gkprod-rehearsal.test migrate --skip-search-index` | exit 0; **`Skipping fixture syncing from the file custom_field.json. Reason: DocType Update Diamond Price  List not found`** (GK live's gke fixture import stops at row 151 of 2,083); 2 orphaned DocTypes removed (baseline noise) |
| snapshot S1 | `mariadb-dump --single-transaction` | taken |
| baseline report smoke | `bench execute gk_smoke.reports` (165 reports, 202 filter sets) | see below |
| back to S1 | tabReport reloaded from S1 (the only table written since: v16 auto-enables *prepared report* for runs over 15 s) | fingerprint equal to S1 |
| preflight (candidate code, read-only) | `gk_smoke.preflight` | orphan DocTypes: none; standard entities to be deleted: only *KGGK Jewelex - ERP Order Tally*; pending patches: the 3 gke ones; JSON skipped by the timestamp rule: none |
| candidate migrate 1 | `bench --site gkprod-rehearsal.test migrate --skip-search-index` | **exit 0**; the 3 gke patches ran; full fixture import; `Deleting entity Report KGGK Jewelex - ERP Order Tally`; no Traceback, no `Failed to execute patch`, no 1118, no orphaned DocType |
| candidate migrate 2 | same | **exit 0**, no patch ran; schema (columns, indexes), DocType/DocField/DocPerm/Property Setter/Report/Scheduled Job Type content unchanged; Custom Field converged once (see note) |
| fixture completeness | SQL over the shipped file | 1,970/1,970 rows present with identical fieldtype and options; the 44 without a column are 41 Image fields and 3 on Single/virtual DocTypes |
| Nova Glow | Patch Log + Attribute Value | jewellery's own rename had already run on this copy (abbreviation NGS, sentinel set); gke's patch recorded itself as done without changing data |
| hooks sweep | `gk_smoke.hooks_sweep` | 663 hook paths; the same 5 failures as GK live's code (hrms here lacks `COMPONENT_EVAL_GLOBALS`, used by two gke overrides — GK live runs a newer hrms; Solitaire Calculator `calculate_rate` does not exist; erpnext/lending `before_tests`) |
| module import | `gk_smoke.import_all gke_customization` | every gke module imports on v16 (0 failures) |
| final code: migrate 4 and 5 (`ecd9b53`: fixture order + GK values) | `bench --site gkprod-rehearsal.test migrate --skip-search-index` x2 | **exit 0** both; clean log scan; no patch ran |
| Custom Fields after the upgrade vs before (S1) | SQL diff of every property against S1's `tabCustom Field` | only 29 module tags and the 2 intended option fixes (Sales Invoice `custom_product_return_form_ref` → Product Return Order Form, Supplier MSME *Micro Enterprise*); nothing else on GK's existing fields changes |

| final code: migrate 6 | same | **exit 0**; Custom Field table identical to after migrate 5 (every column, every row) |

Idempotency: on the final code, migrate 5 → migrate 6 changed nothing in `tabCustom Field`, DocType/DocField/DocPerm, Property Setter, Report, Scheduled Job Type, columns or indexes. The only rows that change on every migrate are the Workflow child rows that jewellery's Workflow fixtures delete and re-insert with new random names. Earlier migrates showed a one-time change of Custom Field `idx` (a stored position number Frappe recomputes on import; field order comes from `insert_after`) while the fixture content was still changing.

## Report smoke (baseline vs candidate, same data, same filters)

Each report ran in a read-only transaction with a 30 s per-statement cap, Administrator, with the filter sets in the spec (empty filters, and required filters filled from the newest matching record).

| Outcome | Runs |
|---|---:|
| FAIL_BOTH_DIFFERENT | 1 |
| FIXED | 2 |
| NEW_REPORT_FAIL | 1 |
| NEW_REPORT_OK | 22 |
| NEW_REPORT_OK_WITH_FORM_FILTERS | 12 |
| OK_ROWS_DIFFER | 2 |
| PRE_EXISTING_FAIL | 42 |
| SAME_OK | 116 |
| TIMING_NEAR_CAP | 4 |

### FIXED — fails on the baseline, runs on the candidate

| Report | Filter set | Baseline | Candidate | Code changed | Detail |
|---|---:|---|---|---|---|
| Employee Batch Issue Receive Report | 0 | ERROR (None) | OK (10000) | True | GK live's code selects Manufacturing Operation.allowed_loss_percentage, which never existed; fixed by f57144d (dropped, as 2d2156d did for the sibling report) |
| Warehouse wise Consumable Consumption | 0 | ERROR (None) | OK (85) | True | GK live's Query Report form fails on v16 (`format requires a mapping`); gk_prod carries master's Script Report, which runs (decided by default, listed for confirmation) |

### OK_ROWS_DIFFER — both run; row count differs

| Report | Filter set | Baseline | Candidate | Code changed | Detail |
|---|---:|---|---|---|---|
| CAD Order Tracking Report | 0 | OK (200) | OK (201) | True | master's report update (1181bf1) appends a Total row: 200 orders + 1 total row |
| Employee Batch Issue Receive | 0 | OK (10000) | OK (181) | True | #1360 (kggk_prod, 2026-10-01, not yet on GK live) keeps only the latest issue/receive per operation and employee and shows only issued-but-not-received rows; gk_prod carries kggk_prod's version plus the restored GK roles. The 181 were only the outstanding operations among the newest 10,000; review fix e1c4db2 selects the outstanding ones before the cap: 4,183 on this copy (see Review fixes) |

### FAIL_BOTH_DIFFERENT — fails on both, with a different error

| Report | Filter set | Baseline | Candidate | Code changed | Detail |
|---|---:|---|---|---|---|
| KGGK Jewelex - ERP Order Tally | 0 | VALIDATION (None) | VALIDATION (None) | True | removed by business decision; migrate deletes its standard Report record |

### PRE_EXISTING_FAIL — fails identically with GK live's code

| Report | Filter set | Baseline | Candidate | Code changed | Detail |
|---|---:|---|---|---|---|
| Absence Report | 0 | VALIDATION (None) | VALIDATION (None) | True | From Date and To Date are required |
| Asset Additions Report | 0 | ERROR (None) | ERROR (None) | True | ModuleNotFoundError: No module named 'erpnext.assets.report.asset_additions_report' |
| Asset Additions Report | 1 | ERROR (None) | ERROR (None) | True | ModuleNotFoundError: No module named 'erpnext.assets.report.asset_additions_report' |
| Assortment Report | 0 | VALIDATION (None) | VALIDATION (None) | False | Company is mandatory |
| Attendance Detail Report | 0 | TIMEOUT (None) | TIMEOUT (None) | False | MySQLdb.OperationalError: (1969, 'Query execution was interrupted (max_statement_time exceeded)') |
| Attendance Punch Error Report | 0 | ERROR (None) | ERROR (None) | False | MySQLdb.ProgrammingError: (1064, "You have an error in your SQL syntax; check the manual that corresponds to your MariaDB server version for the right syntax to use near 'GROUP BY \n\t\t\t\tat.employe |
| Attrition and retention compliance report | 0 | ERROR (None) | ERROR (None) | True | MySQLdb.OperationalError: (1054, "Unknown column 'er.reduce_notice_days' in 'SELECT'") |
| Attrition and retention compliance report | 1 | ERROR (None) | ERROR (None) | True | MySQLdb.OperationalError: (1054, "Unknown column 'er.reduce_notice_days' in 'SELECT'") |
| Branch Stock Summary | 0 | VALIDATION (None) | VALIDATION (None) | True | Company is required |
| Branch Wise Sketch Order Form | 0 | ERROR (None) | ERROR (None) | False | MySQLdb.ProgrammingError: format requires a mapping |
| Customer Group wise Sketch Order Form | 0 | ERROR (None) | ERROR (None) | False | MySQLdb.ProgrammingError: format requires a mapping |
| Customer Order | 0 | TIMEOUT (None) | TIMEOUT (None) | False | MySQLdb.OperationalError: (1969, 'Query execution was interrupted (max_statement_time exceeded)') |
| Department Stock Issue Report | 0 | TIMEOUT (None) | TIMEOUT (None) | True | MySQLdb.OperationalError: (1969, 'Query execution was interrupted (max_statement_time exceeded)') |
| Department Wise Absent Employee | 0 | ERROR (None) | ERROR (None) | False | MySQLdb.ProgrammingError: (1064, "You have an error in your SQL syntax; check the manual that corresponds to your MariaDB server version for the right syntax to use near 'GROUP BY e.employee, e.employ |
| Department Wise Diamond Stock | 0 | VALIDATION (None) | VALIDATION (None) | True | Mandatory filters missing: <strong>Company</strong>, <strong>Department</strong> |
| Designer wise Sketch Details | 0 | ERROR (None) | ERROR (None) | False | MySQLdb.ProgrammingError: (1064, "You have an error in your SQL syntax; check the manual that corresponds to your MariaDB server version for the right syntax to use near 'GROUP BY ds.designer_name,o.c |
| Diamond & Gemstone Conversion Detail | 0 | VALIDATION (None) | VALIDATION (None) | True | Department is mandatory |
| Employee Punch Error | 0 | ERROR (None) | ERROR (None) | False | MySQLdb.ProgrammingError: (1064, "You have an error in your SQL syntax; check the manual that corresponds to your MariaDB server version for the right syntax to use near 'GROUP BY \n\t\t\t\tat.employe |
| Employee Variable Payment | 0 | ERROR (None) | ERROR (None) | False | MySQLdb.ProgrammingError: (1064, "You have an error in your SQL syntax; check the manual that corresponds to your MariaDB server version for the right syntax to use near 'and ss.status = 'Submitted'' |
| Item Code Serial No Detail | 0 | VALIDATION (None) | VALIDATION (None) | True | Error fetching data: (1969, 'Query execution was interrupted (max_statement_time exceeded)') |
| Manufacturing Work Order History Report | 0 | TIMEOUT (None) | TIMEOUT (None) | True | MySQLdb.OperationalError: (1969, 'Query execution was interrupted (max_statement_time exceeded)') |
| Mfg Dashboard Script | 0 | VALIDATION (None) | VALIDATION (None) | False | Please select a Company |
| Monthly Checkin Report | 0 | VALIDATION (None) | VALIDATION (None) | False | Please select Employee, From Date and To Date |
| Monthly Sketch Order Form for Delivery | 0 | ERROR (None) | ERROR (None) | False | MySQLdb.ProgrammingError: format requires a mapping |
| Monthly Sketch Order Form for Delivery | 1 | ERROR (None) | ERROR (None) | False | KeyError: b'branch' |
| Mould Report | 0 | VALIDATION (None) | VALIDATION (None) | False | Please select MWO |
| No. of Designs in Sketch Order | 0 | ERROR (None) | ERROR (None) | False | MySQLdb.ProgrammingError: format requires a mapping |
| Order Detail Report | 0 | TIMEOUT (None) | TIMEOUT (None) | True | MySQLdb.OperationalError: (1969, 'Query execution was interrupted (max_statement_time exceeded)') |
| Order From Detailed Count | 0 | ERROR (None) | ERROR (None) | True | MySQLdb.ProgrammingError: (1064, "You have an error in your SQL syntax; check the manual that corresponds to your MariaDB server version for the right syntax to use near 'GROUP BY ofd.name\n        OR |
| Order Report | 0 | TIMEOUT (None) | TIMEOUT (None) | True | MySQLdb.OperationalError: (1969, 'Query execution was interrupted (max_statement_time exceeded)') |
| Pre Order Form Details | 0 | ERROR (None) | ERROR (None) | True | MySQLdb.OperationalError: (1054, "Unknown column 'pofd.order_form_type' in 'SELECT'") |
| Production Report | 0 | VALIDATION (None) | VALIDATION (None) | True | Error fetching data: (1969, 'Query execution was interrupted (max_statement_time exceeded)') |
| Quotation Detailed Count | 0 | TIMEOUT (None) | TIMEOUT (None) | True | MySQLdb.OperationalError: (1969, 'Query execution was interrupted (max_statement_time exceeded)') |
| Sales Order Detailed Count | 0 | ERROR (None) | ERROR (None) | True | MySQLdb.ProgrammingError: (1064, "You have an error in your SQL syntax; check the manual that corresponds to your MariaDB server version for the right syntax to use near 'GROUP BY\n    qi.name, so.nam |
| Serial No Search Detail | 0 | TIMEOUT (None) | TIMEOUT (None) | True | MySQLdb.OperationalError: (1969, 'Query execution was interrupted (max_statement_time exceeded)') |
| Serial No Stock Board | 0 | TIMEOUT (None) | TIMEOUT (None) | False | MySQLdb.OperationalError: (1969, 'Query execution was interrupted (max_statement_time exceeded)') |
| Sketch Order Docstatus | 0 | ERROR (None) | ERROR (None) | False | MySQLdb.ProgrammingError: format requires a mapping |
| Sketch Order Form Workflow | 0 | ERROR (None) | ERROR (None) | False | MySQLdb.ProgrammingError: format requires a mapping |
| Sketch Order Workflow | 0 | ERROR (None) | ERROR (None) | False | MySQLdb.ProgrammingError: format requires a mapping |
| Standard Shift Report | 0 | VALIDATION (None) | VALIDATION (None) | False | From & To Dates are mandatory |
| Stock Ledger Detailed Report | 0 | VALIDATION (None) | VALIDATION (None) | False | Please select both From Date and To Date |
| Tag Search Detail | 0 | TIMEOUT (None) | TIMEOUT (None) | False | MySQLdb.OperationalError: (1969, 'Query execution was interrupted (max_statement_time exceeded)') |

### NEW_REPORT_FAIL — master-only report; fails on the harness's filters (mandatory filters left empty, a test fiscal year name) or hits the 30 s cap on real data

| Report | Filter set | Baseline | Candidate | Code changed | Detail |
|---|---:|---|---|---|---|
| PD to Prod | 0 | VALIDATION (None) | VALIDATION (None) | True | Failed to fetch data from Jwelex API at <external URL> |

### Re-runs on an idle database

The near-cap timeouts were re-run alone with their original filters (both code versions), and the master-only reports that failed on the harness's filters were re-run with the values their filter forms supply (company, a real fiscal year, `group_by` = Invoice, the default item).

| Code | Report | Filters | Status | Rows | Seconds |
|---|---|---|---|---:|---:|
| candidate | Diamond Stock Receive Report | `{}` | OK | 188136 | 20.66 |
| candidate | Diamond Stock Recevice Report | `{}` | OK | 188136 | 19.19 |
| candidate | Gross Profit SI and Batch Wise | `{"company": "<GK company>", "from_date": "2026-09-02", "to_date": "2026-10-02", "group_by": "Invoice"}` | OK | 1 | 0.18 |
| candidate | 24Q Report | `{"company": "<GK company>", "fiscal_year": "2025-2026"}` | OK | 0 | 0.01 |
| candidate | 26Q Report | `{"company": "<GK company>", "financial_year": "2025-2026"}` | OK | 0 | 0.02 |
| candidate | Available Batch Report - GKB | `{"company": "<GK company>", "to_date": "2026-10-02", "item_code": "D-Polished Diamonds"}` | OK | 953 | 1.19 |
| candidate | Batch Wise Stock Balance | `{"company": "<GK company>", "to_date": "2026-10-02", "item_code": "D-Polished Diamonds"}` | OK | 5 | 0.06 |
| candidate | Stock Balance User | `{}` | OK | 11756 | 24.55 |
| candidate | Stock Balance User | `{"from_date": "2026-09-02", "to_date": "2026-10-02"}` | OK | 11756 | 24.68 |
| candidate | Dummy Monthly Report | `{"month": "December", "from_date": "2024-12-01", "to_date": "2024-12-31", "company": "<GK company>", "cur_employee": "<employee>", "employee": "<employee>"}` | OK | 39 | 0.3 |
| candidate | Variant Details | `{"item": "<template item>"}` | OK | 1 | 0.22 |
| candidate | 24Q Report | `{"company": "<GK company>", "fiscal_year": "2024-2025"}` | OK | 0 | 0.01 |
| candidate | 26Q Report | `{"company": "<GK company>", "financial_year": "2024-2025"}` | OK | 743 | 0.36 |
| GK live code | Diamond Stock Receive Report | `{}` | OK | 188136 | 20.53 |
| GK live code | Diamond Stock Recevice Report | `{}` | OK | 188136 | 21.56 |
| GK live code | Stock Balance User | `{}` | TIMEOUT |  | 38.78 |
| GK live code | Stock Balance User | `{"from_date": "2026-09-02", "to_date": "2026-10-02"}` | TIMEOUT |  | 34.28 |

## Tests

`bench --site gkprod-rehearsal.test run-tests --module <module> --junit-xml-output <file>` (through the isolation wrapper). Candidate code first; every module that did not pass was re-run with GK live's gke code on the same database to tell pre-existing failures from regressions.

| Run | Module | gke SHA | Start | Expected | Ran | Failures | Errors | Skipped | Status |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| cand-T1 | `gke_customization.gke_order_forms.doctype.order.test_order` | `ecd9b531` | 14:01:25 | 7 | None | 0 | 0 | 0 | DISCOVERY_ERROR |
| cand-T1 | `gke_customization.gke_order_forms.doctype.order_form.test_order_form` | `ecd9b531` | 14:01:29 | 4 | None | 0 | 0 | 0 | DISCOVERY_ERROR |
| cand-T1 | `gke_customization.gke_order_forms.doc_events.test_kggk_sync` | `ecd9b531` | 14:01:32 | 30 | 30 | 0 | 0 | 0 | PASS |
| cand-T1 | `gke_customization.gke_catalog.report.accounts_receivable___sd.test_accounts_receivable___sd` | `ecd9b531` | 14:01:34 | 21 | None | 0 | 0 | 0 | DISCOVERY_ERROR |
| cand-T1 | `gke_customization.gke_catalog.report.accounts_receivable_summary___sd.test_accounts_receivable_summary___sd` | `ecd9b531` | 14:01:38 | 2 | None | 0 | 0 | 0 | DISCOVERY_ERROR |
| cand-T1 | `gke_customization.gke_catalog.report.accounts_payable___sd.test_accounts_payable___sd` | `ecd9b531` | 14:01:42 | 1 | None | 0 | 0 | 0 | DISCOVERY_ERROR |
| cand-T2 | `jewellery_erpnext.jewellery_erpnext.tests.test_quotation` | `ecd9b531` | 14:01:45 | 21 | 21 | 0 | 4 | 0 | FAIL |
| cand-T2 | `jewellery_erpnext.jewellery_erpnext.tests.test_sales_order` | `ecd9b531` | 14:01:48 | 12 | 12 | 0 | 1 | 0 | FAIL |
| cand-T2 | `jewellery_erpnext.jewellery_erpnext.tests.test_purchase_order` | `ecd9b531` | 14:01:51 | 37 | 37 | 0 | 0 | 0 | PASS |
| cand-T2 | `jewellery_erpnext.jewellery_erpnext.doctype.manufacturing_operation.test_manufacturing_operation` | `ecd9b531` | 14:01:54 | 9 | 9 | 0 | 6 | 0 | FAIL |
| base-rerun-T1 | `gke_customization.gke_order_forms.doctype.order.test_order` | `c94f0475` | 14:01:57 |  | None | 0 | 0 | 0 | DISCOVERY_ERROR |
| base-rerun-T1 | `gke_customization.gke_order_forms.doctype.order_form.test_order_form` | `c94f0475` | 14:02:01 |  | None | 0 | 0 | 0 | DISCOVERY_ERROR |
| base-rerun-T2 | `jewellery_erpnext.jewellery_erpnext.tests.test_quotation` | `c94f0475` | 14:02:05 |  | 21 | 0 | 4 | 0 | FAIL |
| base-rerun-T2 | `jewellery_erpnext.jewellery_erpnext.tests.test_sales_order` | `c94f0475` | 14:02:08 |  | 12 | 0 | 1 | 0 | FAIL |
| base-rerun-T2 | `jewellery_erpnext.jewellery_erpnext.doctype.manufacturing_operation.test_manufacturing_operation` | `c94f0475` | 14:02:11 |  | 9 | 0 | 6 | 0 | FAIL |

**Reading the results.** Every module was run with gk_prod's code and, where it did not pass, again with GK live's gke code on the same database. In every case the two runs give **the same result**, so none of the failures is caused by the reconstruction — but they are not passes either:

- **Passed:** `test_kggk_sync` (30 tests, the KGGK replication contract: Item/BOM payloads, image sync, the Nova Glow gate) and jewellery_erpnext's `test_purchase_order` (37 tests, including the Purchase Order → gke Nova Glow BOM push).
- **Could not start** (`test_order`, `test_order_form`, and the three Accounts Receivable/Payable SD report tests, which are master-only and had never run on v16): erpnext's test bootstrap creates `_Test Holiday List`, and on GK sites Holiday List has a mandatory `custom_company` field that the bootstrap does not fill (`MandatoryError: [Holiday List, _Test Holiday List]: custom_company`). Identical with GK live's code.
- **Errors in setup** (`test_quotation` 4/21, `test_sales_order` 1/12, `test_manufacturing_operation` 6/9 — jewellery's cross-app tests that drive gke's Order → Quotation → Sales Order flow): they expect the records jewellery's CI seeds (`Test_Company`, `Test_Customer_External`, `Order Management - T`, …), which a copy of a production site does not have (`LinkValidationError: Could not find Company: Test_Company`). Identical with GK live's code.
- **Seeding a clean site like CI** (`jewellery_erpnext.create_test_data.create_test_data` on the fresh gk_prod site) failed: first on india_compliance's HSN validation (disabled for the test site), then in erpnext's Department tree while importing jewellery's test departments. jewellery's CI builds its site from its own image with gke's fixtures moved aside, which was not reproduced here. Both attempts' results are kept in the evidence tree, not counted above.

**Gap:** the order-flow tests (Order Form → Order → Quotation → Sales Order) did not execute in this environment. Before deploy, run jewellery_erpnext's CI workflows (core, inventory, manufacturing) against gk_prod, or a UAT walkthrough of that flow.

## Fresh install

All three runs install the apps in production's order: `bench new-site … --install-app erpnext india_compliance payments hrms gke_customization jewellery_erpnext gurukrupa_customizations gurukrupa_biometric lending` (helpdesk, wiki, telephony and optimus are not installed, which also tests gke on a site without them).

| | GK live's code | gk_prod, first attempt (`f482786`, export-ordered fixture) | gk_prod final (`de33ad3` install + migrates; migrate 3 with `ecd9b53`) |
|---|---|---|---|
| install | **fails** in gke: `UniqueFieldnameError: Demo Work: Fieldname amended_from appears multiple times` | exit 0 | **exit 0** |
| fixture import during install | stops at the first lending row | stops at the first lending row | stops at the first jewellery row (jewellery installs after gke) |
| migrate 1 / 2 | — | **both exit 1**: the import stopped at the helpdesk row and left BOM's Dynamic Link `custom_creation_docname` without its type field; Frappe's icon clean-up then hit `Unknown column 'custom_creation_doctype'` → fixed by `de33ad3` | migrate1 exit 0 2026-10-02T12:36:41+05:30, migrate2 exit 0 2026-10-02T12:41:33+05:30 ; migrate3 exit 0 2026-10-02T14:06:09+05:30 |
| log scan | Skipping fixture syncing from the file custom_field.json. Reason: DocType Loan not found; Traceback; UniqueFieldnameError, (x2) | Skipping fixture syncing from the file custom_field.json. Reason: DocType HD Ticket not found; Traceback | Skipping fixture syncing from the file custom_field.json. Reason: DocType Ignore Department For MOP not found; Skipping fixture syncing from the file custom_field.json. Reason: DocType HD Ticket not found; Skipping fixture syncing from the file custom_field.json. Reason: DocType HD Ticket not found; Skipping fixture syncing from the file custom_field.json. Reason: DocType HD Ticket not found (the helpdesk row is expected: helpdesk is not installed) |
| Custom Field install → migrate 1 | — | — | {'only_first': 0, 'only_second': 1349, 'changed_rows': 414, 'by_column': {'module': 81, 'idx': 411, 'insert_after': 25, 'label': 1, 'hidden': 1, 'in_list_view': 3}} |
| Custom Field migrate 1 → 2 | — | — | {'only_first': 0, 'only_second': 0, 'changed_rows': 756, 'by_column': {'idx': 756}} |
| Custom Field migrate 2 → 3 | — | — | {'only_first': 0, 'only_second': 0, 'changed_rows': 278, 'by_column': {'insert_after': 29, 'idx': 275, 'hidden': 1, 'in_list_view': 2, 'read_only': 1, 'options': 1}} |
| hooks / import | — | — | 637 hook paths, 5 failing (same pre-existing set); import_all failures: 0 |

On a clean site the first migrate also applies gke's fixture over fields other apps create during install (module tags, layout and a few labels/flags, e.g. lending's Company loan tab label), giving them the definitions GK sites have; on the GK copy the same import changed nothing beyond module tags and the two intended fixes (see the rehearsal above).


## Cross-app contracts

Every dotted path from one app into another (Python imports, hooks, JS server calls) was resolved with the candidate code and with GK live's code; server calls must also be whitelisted (`gk_smoke.contracts`).

| Direction | References | Resolve |
|---|---:|---:|
| jewellery->gke | 8 | 8 |
| gurukrupa_customizations->gke | 1 | 1 |
| gurukrupa_biometric->gke | 4 | 4 |
| gke->gke | 223 | 208 |
| gke->jewellery | 12 | 10 |
| gke->hrms | 13 | 13 |
| gke->erpnext | 47 | 33 |
| gke->gurukrupa_customizations | 3 | 3 |

References that do not resolve with the candidate (none of them works with GK live's code either — no regression):

| Direction | Reference | Problem | Referenced from |
|---|---|---|---|
| gke->gke | `gke_customization.doctype.customer_scorecard_criteria.customer_scorecard_criteria.get_criteria_list` | ModuleNotFoundError: No module named 'gke_customization.doctype' | `gke_price_list/doctype/customer_scorecard/customer_scorecard.js:24` |
| gke->gke | `gke_customization.gke_catalog.api.attendance.attendance` | ModuleNotFoundError: No module named 'gke_customization.gke_catalog.api.attendance' | `hooks.py:257` |
| gke->gke | `gke_customization.gke_catalog.api.item_catalog.get_attribute_values` | AttributeError: module 'gke_customization.gke_catalog.api.item_catalog' has no attribute 'get_attribute_values' | `hooks.py:261` |
| gke->gke | `gke_customization.gke_catalog.api.item_catalog.update_xyz` | AttributeError: module 'gke_customization.gke_catalog.api.item_catalog' has no attribute 'update_xyz' | `hooks.py:262` |
| gke->gke | `gke_customization.gke_catalog.api.item_list.get_item_list` | AttributeError: module 'gke_customization.gke_catalog.api.item_list' has no attribute 'get_item_list' | `hooks.py:254` |
| gke->gke | `gke_customization.gke_catalog.api.reposne.get_submited_data` | ModuleNotFoundError: No module named 'gke_customization.gke_catalog.api.reposne' | `hooks.py:264` |
| gke->gke | `gke_customization.gke_custom_export.doctype.solitaire_calculator.solitaire_calculator.calculate_rate` | AttributeError: module 'gke_customization.gke_custom_export.doctype.solitaire_calculator.solitaire_calculator' has no at | `hooks.py:270` |
| gke->gke | `gke_customization.gke_hrms.doc_events.ot_and_night_shift_report.send_auto_email_alert` | ModuleNotFoundError: No module named 'gke_customization.gke_hrms.doc_events.ot_and_night_shift_report' | `gke_catalog/report/ot_and_night_shift_report/ot_and_night_shift_report.js:70` |
| gke->gke | `gke_customization.gke_hrms.doctype.holiday_punch.holiday_punch.process_attendance` | not whitelisted | `gke_hrms/doctype/holiday_punch/holiday_punch.py:668` |
| gke->gke | `gke_customization.gke_hrms.doctype.holiday_punch.holiday_punch.process_checkins` | not whitelisted | `gke_hrms/doctype/holiday_punch/holiday_punch.py:652` |
| gke->gke | `gke_customization.gke_hrms.doctype.ot_allowance_entry.ot_allowance_entry.get_ot_details` | AttributeError: module 'gke_customization.gke_hrms.doctype.ot_allowance_entry.ot_allowance_entry' has no attribute 'get_ | `gke_hrms/doctype/ot_allowance_entry/ot_allowance_entry.js:58` |
| gke->gke | `gke_customization.overrides.payroll_entry.CustomPayrollEntry` | not whitelisted | `hooks.py:125` |
| gke->gke | `gke_customization.overrides.salary_slip.seed_slip_only_formula_fields` | ImportError: cannot import name 'COMPONENT_EVAL_GLOBALS' from 'hrms.payroll.doctype.salary_structure_assignment.salary_s | `hooks.py:336` |
| gke->gke | `gke_customization.overrides.salary_structure_assignment` | AttributeError: module 'gke_customization.overrides' has no attribute 'salary_structure_assignment' | `overrides/salary_slip.py:3` |
| gke->gke | `gke_customization.overrides.salary_structure_assignment.CustomSalaryStructureAssignment` | ImportError: cannot import name 'COMPONENT_EVAL_GLOBALS' from 'hrms.payroll.doctype.salary_structure_assignment.salary_s | `hooks.py:126` |
| gke->jewellery | `jewellery_erpnext.jewellery_erpnext.doc_events.sales_invoice.get_dispatch_slip` | AttributeError: module 'jewellery_erpnext.jewellery_erpnext.doc_events.sales_invoice' has no attribute 'get_dispatch_sli | `gke_custom_export/doctype/dispatch_slip/dispatch_slip.js:66` |
| gke->jewellery | `jewellery_erpnext.jewellery_erpnext.doc_events.stock_entry.get_dispatch_slip` | AttributeError: module 'jewellery_erpnext.jewellery_erpnext.doc_events.stock_entry' has no attribute 'get_dispatch_slip' | `gke_custom_export/doctype/dispatch_slip/dispatch_slip.js:107` |
| gke->erpnext | `erpnext.BOMCompareTool` | AttributeError: module 'erpnext' has no attribute 'BOMCompareTool' | `gke_order_forms/page/bom_compare_tool/bom_compare_tool.js:8` |
| gke->erpnext | `erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice` | AttributeError: module 'erpnext.accounts.doctype.purchase_invoice' has no attribute 'test_purchase_invoice' (only in master-only code) | `gke_catalog/report/accounts_payable___sd/test_accounts_payable___sd.py:5` |
| gke->erpnext | `erpnext.accounts.doctype.sales_invoice.test_sales_invoice` | AttributeError: module 'erpnext.accounts.doctype.sales_invoice' has no attribute 'test_sales_invoice' (only in master-only code) | `gke_catalog/report/accounts_receivable___sd/test_accounts_receivable___sd.py:7` |
| gke->erpnext | `erpnext.accounts.test.accounts_mixin` | AttributeError: module 'erpnext.accounts.test' has no attribute 'accounts_mixin' (only in master-only code) | `gke_catalog/report/accounts_receivable___sd/test_accounts_receivable___sd.py:9` |
| gke->erpnext | `erpnext.get_presentation_currency_list` | AttributeError: module 'erpnext' has no attribute 'get_presentation_currency_list' | `gke_catalog/report/gst_ledger_report/gst_ledger_report.js:231` |
| gke->erpnext | `erpnext.item` | AttributeError: module 'erpnext' has no attribute 'item' | `gke_price_list/doctype/product_return_order_form/product_return_order_form.js:3` |
| gke->erpnext | `erpnext.selling.doctype.delivery_note.delivery_note.make_sales_invoice` | ModuleNotFoundError: No module named 'erpnext.selling.doctype.delivery_note' | `hooks.py:193` |
| gke->erpnext | `erpnext.selling.doctype.sales_order.test_sales_order` | AttributeError: module 'erpnext.selling.doctype.sales_order' has no attribute 'test_sales_order' (only in master-only code) | `gke_catalog/report/accounts_receivable___sd/test_accounts_receivable___sd.py:10` |
| gke->erpnext | `erpnext.utils` | AttributeError: module 'erpnext' has no attribute 'utils' (only in master-only code) | `gke_catalog/report/accounts_receivable___sd/accounts_receivable___sd.js:4` |
| gke->erpnext | `erpnext.utils.add_dimensions` | ModuleNotFoundError: No module named 'erpnext.utils' | `gke_catalog/report/accounts_payable_summary___sd/accounts_payable_summary___sd.js:141` |
| gke->erpnext | `erpnext.utils.add_inventory_dimensions` | ModuleNotFoundError: No module named 'erpnext.utils' | `gke_customization/report/stock_balance_user/stock_balance_user.js:131` |
| gke->erpnext | `erpnext.utils.get_fiscal_year` | ModuleNotFoundError: No module named 'erpnext.utils' (only in master-only code) | `gke_catalog/report/gross_profit_si_and_batch_wise/gross_profit_si_and_batch_wise.js:18` |
| gke->erpnext | `erpnext.utils.get_party_name` | ModuleNotFoundError: No module named 'erpnext.utils' | `gke_catalog/report/gst_ledger_report/gst_ledger_report.js:95` |
| gke->erpnext | `erpnext.utils.map_current_doc` | ModuleNotFoundError: No module named 'erpnext.utils' | `gke_custom_export/doctype/dispatch_slip/dispatch_slip.js:65` |

JS references such as `erpnext.utils.add_dimensions` are browser-side functions, not server paths; they appear above only because the scan is textual. The erpnext `test_*` modules exist in v16 but only import inside the test runner. `enqueue` targets and `override_doctype_class` entries do not need whitelisting.

## Static reviews (security, performance)

Every ported unit was reviewed for guest access, whitelisting, permission checks, company/customer restrictions, SQL built from user input, unbounded queries and N+1 loops (109 security and 100 performance observations, recorded per unit in the classification data). Old production code was not assumed safe.

**Fixed in this PR**

- `f482786` — three Attendance Adjustment Tool endpoints (`process_salary_adjustment`, `proceed_check_in_modify`, `update_proceed_check_in_modify`, production #1209) accepted unauthenticated calls that delete and recreate Employee Checkins and rewrite Additional Salary. They now require login and read permission on the tool document.
- Literal API key pairs in comments of `item.py` and the KGGK tally report's plaintext database credential (`jewelex_db_config.py`) are no longer in the tree (they remain in git history — rotate them).
- Per-diamond-row debug `frappe.log_error` calls in Product Return Order Form moved to the logger (they wrote two Error Log rows per row).
- `9ff3bd9` (review F-01) — Branch Stock Summary's whitelisted `get_summary_comparison` (new to GK with #1360) and `get_stock_details` (as on GK live) ran SQL built from the caller's filters for any logged-in user, and the Summary ran ERPNext Stock Balance without that report's roles. Both now repeat Desk's checks (report roles, Main Slip report permission, read or select on the chosen Company with User Permissions), the Summary also requires Stock Balance access, `execute()` checks the Company itself, and every statement in the module binds its values.
- `4c24611` (review S-4) — Product Lifecycle's whitelisted `get_finish_tag_history` and `get_serial_no_section_data` (new with #1360) now require access to the report.

**Carried unchanged (identical on GK live and/or master), recommended follow-ups**

| Area | Finding | Where |
|---|---|---|
| Guest endpoints | `allow_guest=True` on master's portal, catalogue, login, issues, survey and attendance APIs (≈80 endpoints); designed for the external portal and devices, but they need an audit of what each returns | `gke_catalog/api/*`, `gke_survey`, `gke_hrms/api/attendance*` |
| Hard-coded secrets | AES-GCM key, HMAC secret and Fernet key in `encryption_response.py` (master); remote URL + API key pair in master commit 4f5c313 and in old `item.py` revisions (history) | public repository — rotate and move to site config |
| Missing permission checks | many whitelisted report helpers return BOM, pricing, serial and customer data to any logged-in user (e.g. Serial No search, Main Slip popup, Employee Material Stock In Hand, mfg dashboard; Product Lifecycle, new with #1360, is fixed by `4c24611`); the six cross-site pricing endpoints are open by design for the KG↔GK link | `gke_catalog/report/*`, `gke_order_forms/doc_events/item.py` |
| SQL from user input | f-string SQL with filter values in Order Detail Report and Order Form `get_customer_order_form` (Branch Stock Summary, whose comparison method is new with #1360, is fixed by `9ff3bd9`) | parameterise in a follow-up |
| Outbound calls | synchronous HTTP in Item/BOM `before_validate` (KGGK replication, only when configured) and in Gold Rates `validate` (bullion feeds, some plain HTTP); no request timeout on the PROF remote push | `item.py`, `gold_rates.py`, `product_return_order_form.py` |
| Heavy reports | full-table derived tables / window functions on every run (MOP summary, Branch Stock Summary *Summary*, Production Report up to 10,000 rows with per-row lookups, Employee Material Stock In Hand); several reports take 20–270 s on the GK copy | candidates for indexes and filter push-down |
| N+1 | Order Form exports, Product Return Order Form validate/submit, Gold Rates fetchers | |
| Error Log noise | Employee Batch/Issue Receive reports write debug rows on every run (production) | |

Changing report SQL or API exposure beyond the fix above was kept out of this PR: each would change what users see or what the external portal receives, and needs the owning team's sign-off.

## Review fixes (2026-10-05)

The review of #1372 found six defects (F-01 to F-06); the fixes and four same-cause siblings are the commits listed in
[06](06_cherry_pick_plan_and_conflicts.md). Everything below ran on `gkprod-rehearsal.test` through the isolation wrapper
(gke from the fix worktree, jewellery from GK live's `gurukrupa-prod`, outbound HTTP blocked, private Redis).

**Tests** at `d430472`, all passing:

| Module | Covers | Ran | Result |
|---|---|---:|---|
| `gke_customization.gke_price_list.doctype.product_return_order.test_product_return_order` | F-02 serial push gate, F-03 diamond-free serial | 15 | PASS |
| `gke_customization.gke_price_list.doctype.product_return_order_form.test_product_return_order_form` | S-1 KG-ref form push gate | 4 | PASS |
| `gke_customization.gke_order_forms.doctype.repair_order.test_repair_order` | S-2 diamond-free serial | 3 | PASS |
| `gke_customization.patches.test_rename_revise_diamond_price_list_doctype` | F-04 refusal, patch stays pending | 5 | PASS |
| `gke_customization.patches.v1_0.test_v15_rename_close_setting_to_nova_glow` | S-3 refusal, patch stays pending | 6 | PASS |
| `gke_customization.gke_catalog.report.employee_batch_issue_receive.test_employee_batch_issue_receive` | F-05, unit and MariaDB | 14 | PASS |
| `gke_customization.gke_catalog.report.branch_stock_summary.test_branch_stock_summary` | F-01 gate and binding, F-06 netting, unit and MariaDB | 26 | PASS |
| `gke_customization.gke_catalog.report.product_lifecycle.test_product_lifecycle` | S-4 report gate | 3 | PASS |
| `gke_customization.gke_order_forms.doc_events.test_kggk_sync` | regression | 30 | PASS |

**Negative control.** The new test files were run against the unfixed code (`cebf9da`) in a throwaway worktree. Every
module failed, mostly with assertion failures:
- a blank KG site blocks approval and submit;
- a metal-only BOM raises IndexError;
- both patches return instead of refusing;
- `X' OR '1'='1` returns every company's departments;
- a user without the report's roles, or limited to another company, gets through.

The rest error on the new interfaces (the report's 3-tuple return, new signatures). Removing the Main Slip company scoping
or the summary's report gate from the fixed code also fails the tests.

**Before/after on the rehearsal copy** (read-only transaction, Administrator, the `cebf9da` module beside the fixed one):

| Employee Batch Issue Receive | Before | After | Old rule without its cap |
|---|---:|---:|---:|
| no filter | 181 | 4,183 | 4,183 |
| Waxing - GEPL | 162 | 981 | 981 |
| Model Making - GEPL | 33 | 258 | 258 |

Every row shown before is still shown. A department run takes 2-5 s, an unfiltered run about 7 s.

Branch Stock Summary returned identical output in all 222 comparisons, with no failed statement on either side. They
covered:
- 54 report runs over both companies, two GEPL branches, Metal, Diamond and Finding, both flag combinations and three
  manufacturers;
- 166 View drill-downs;
- both companies' Summary dialogs.

So binding the queries, netting per department and item (F-06) and scoping Main Slip figures to the company change no
figure on this data.

**Review of the fixes.** Six independent read-only reviews (SQL binding, authorization, the outstanding-operations rule,
PRO/PROF/Repair Order, patches, tests) found no defect in the fixed code. Two follow-ups were applied:
- `cdb7af6`: a filtered Employee Batch Issue Receive run applies its filters inside the outstanding selection. Department
  runs had become about twice as slow; the rows are identical.
- `d430472`: six test assertions were strengthened so that they fail when the fix they guard is undone.

**Site data, not code.** The GK copies carry a site Server Script, *Create Serial No* (Serial No, Before Insert). It posts
every new Serial No to a hard-coded remote with a hard-coded token and fails the save when the call fails, independent of
`prf_to_site`. Check GK live for it (README, before deploying, step 5).

## Not run

- Real external integrations: GST/e-invoice, email, SMS, COSEC/biometric devices, DeskTime, bullion rate feeds, and the KG ↔ GK REST link (outbound HTTP was blocked on purpose).
- Scheduled jobs firing at real times; concurrency and performance at production volume.
- Desk UI, built assets and translations; file attachments.
- A copy of the **live GK** database (no backup was available; the rehearsal used the local `gk` copy).
- The actual deploy and its rollback.

