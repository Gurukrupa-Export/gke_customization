# 07 — Schema, fixtures, patches and hooks

## Files (gk_prod tree vs master)

Code and configuration only; this documentation folder (11 files) comes on top.

| Added | Modified | Deleted |
|---:|---:|---:|
| 299 | 109 | 9 |

Every deleted path is one half of an intentional move (git's own rename detection pairs identical empty `__init__.py` files arbitrarily, so the moves are listed here explicitly):

| Old path | New path | Why |
|---|---|---|
| `gke_price_list/doctype/revise_diamond_price__list/` (5 files) | `gke_price_list/doctype/revise_diamond_price_list/` | production renamed the DocType (two spaces to one); the pre_model_sync patch `rename_revise_diamond_price_list_doctype` carries existing documents |
| `gke_catalog/report/employee_mediclaim_detailed_reports/` (4 files) | `gke_hrms/report/employee_mediclaim_detailed_reports/` | the report declares module GKE HRMS, so Frappe looked for its code under gke_hrms and could not load it; files unchanged |

Deleted paths: `gke_catalog/report/employee_mediclaim_detailed_reports/__init__.py`, `gke_catalog/report/employee_mediclaim_detailed_reports/employee_mediclaim_detailed_reports.js`, `gke_catalog/report/employee_mediclaim_detailed_reports/employee_mediclaim_detailed_reports.json`, `gke_catalog/report/employee_mediclaim_detailed_reports/employee_mediclaim_detailed_reports.py`, `gke_price_list/doctype/revise_diamond_price__list/__init__.py`, `gke_price_list/doctype/revise_diamond_price__list/revise_diamond_price__list.js`, `gke_price_list/doctype/revise_diamond_price__list/revise_diamond_price__list.json`, `gke_price_list/doctype/revise_diamond_price__list/revise_diamond_price__list.py`, `gke_price_list/doctype/revise_diamond_price__list/test_revise_diamond_price__list.py`

No other master file is deleted.

### Paths GK live (gurukrupa-prod) has that gk_prod does not

10 files, two groups, both intended:

| Path | Why |
|---|---|
| `gke_catalog/doctype/customer_order_form/` (5 files) | stale 2023 duplicate of the Customer Order Form DocType, which is defined in `gke_order_forms` (module GKE Order Forms, the definition the database uses). master deleted the duplicate in 90eebe6; the production lines never did. The active DocType is unchanged; the preflight found no orphan. |
| `gke_catalog/report/kggk_jewelex___erp_order_tally/` (5 files, incl. `jewelex_db_config.py` with a plaintext database credential) | business decision 2026-10-02: KGGK-only report family not carried; migrate deletes its standard Report record |

## DocTypes

| | vs master | vs gurukrupa-prod (GK live) |
|---|---|---|
| added in gk_prod | 19: adjustment_details, attendance_adjustment_tool, cad_designer_pricing, complexity_category, customer_diamond_shape_detail, customer_diamond_size_details, customer_gemstone_detail, customer_price_list_approval, customer_price_list_approval_details, customer_rm_code, customer_rm_code_detail, customer_setting_detail, gold_rates, gold_rates_branchs, metal_ratio, revise_cad_designing_pricing, revise_cad_designing_pricing_item, revise_diamond_price_list, salary_withholding_release | 29: add_to_cart_portal_item, audit_analytical_review_detail, audit_customer_gold_reconciliation_details, audit_high_risk_observation_detail, audit_high_risk_return_summary, audit_management_response_tracker, audit_status_of_previous_audit_points, batch_pdd_change_reason, bulk_order_detail, cataloge_item_details, cataloge_master, catalogue_collection_details, csat_feedback, csat_questionnaire, csat_questionnaire_for_po, employee_mediclaim_table, employee_multiselect, gold_rate_cut, internal_catalog_master, kaizen_slip, kaizen_tracker, order_tracking, portal_order, portal_order_item, revise_gemstone_pricelist_detail, secured_and_unsecured_loan, secured_and_unsecured_loan_repayment_schedule, size_wise_purchase, user_item_details |
| not in gk_prod | 1: revise_diamond_price__list | 0: — |

## Reports

| | vs master | vs gurukrupa-prod (GK live) |
|---|---|---|
| added in gk_prod | 52: assortment_report, batch_dashboard, broken_diamond_ir_report, chain_issue_receive_report, consumables_stocks, department_sample_issue_receive_report, department_stock_detailed_report, department_stock_issue_report, department_wise_diamond_stock, diamond_&_gemstone_conversion_detail, diamond_broken_lost_report, diamond_rate_report, diamond_stock_receive_report, diamond_stock_recevice_report, employee_batch_issue_receive, employee_batch_issue_receive_report, employee_issue_receive_reports, employee_material_stock_in_hand, everyday_work_report, fg_history, finish_good_item_details, finish_good_stylebio_detail_report, finish_tag_detail_label_report, finished_good_detail, item_code_serial_no_detail, main_slip_detail_report, main_slip_details, manufacturing_batch_stock_register, manufacturing_operations_summary, manufacturing_work_order_&_stock_register, melting_item_details, metal_convert_to_pure_report, mfg_dashboard_script, mould_report, open_day_work_order, product_certificate_ir, product_lifecycle, purchase_material_details, repair_serial_weight_difference, repair_tag_weight_difference_report, sales_invoice_detail_report, sales_invoice_summary_report, sales_material_details, serial_no_barcode_print, serial_no_search_detail, serial_no_search_summary, serial_no_stock_board, slip_wise_diamond_detail_report, stone_assortment_report, tag_search_detail, today's_absent_employees, worker_wise_performance_report | 25: 24q_report, 26q_report, accounts_payable___sd, accounts_payable_summary___sd, accounts_receivable___sd, accounts_receivable_summary___sd, available_batch_report___gkb, batch_wise_purchase_cycle, batch_wise_sales_cycle, batch_wise_sales_cycle___sam, batch_wise_stock_balance, cad_dashboard_script, consumable_stock_balance, consumable_stock_report, dummy_monthly_report, employee_mediclaim_detailed_reports, everyday_work_report, gross_profit_si_and_batch_wise, item_with_tax, ot_report, pd_to_prod, product_lifecycle, purchase_cycle, purchase_report, purchase_return_report |
| not in gk_prod | 0: — | 1: kggk_jewelex___erp_order_tally |

## Pages

| | vs master | vs gurukrupa-prod (GK live) |
|---|---|---|
| added in gk_prod | 1: manufacturing_dashbo | 1: cad_order_dashboard |
| not in gk_prod | 0: — | 0: — |

## Web Forms

| | vs master | vs gurukrupa-prod (GK live) |
|---|---|---|
| added in gk_prod | 0: — | 0: — |
| not in gk_prod | 0: — | 0: — |

## Print Formats

| | vs master | vs gurukrupa-prod (GK live) |
|---|---|---|
| added in gk_prod | 0: — | 0: — |
| not in gk_prod | 0: — | 0: — |

Everything GK live has and gk_prod lacks is accounted for: the renamed `revise_diamond_price__list`, the moved report folder, and the KGGK Jewelex - ERP Order Tally report (business decision; Frappe deletes its orphaned standard Report record on migrate — observed in the rehearsal).

## Custom fields (fixtures/custom_field.json)

master ships 5 rows, kggk_prod/GK live ship 2083 (largely a site export). gk_prod ships **1970** curated rows. Every kggk_prod row was checked by script (name format, owning app, overlap with jewellery's fixtures and code, standard-field clash, DocType existence, Link/Table targets, insert_after, references in code, live drift, row size, renamed DocTypes) and every non-trivial decision was reviewed by agents and adversarially verified.

| Decision | Rows |
|---|---:|
| KEEP | 1938 |
| DROP_DUP_PROVIDER | 89 |
| RENAME_CANONICAL | 29 |
| DROP_STALE | 24 |
| MODIFY | 3 |

- **Renamed to the canonical `{dt}-{fieldname}` name**: 29 rows. The pre_model_sync patch `canonicalise_custom_field_names` renames any existing site document to the shipped name first (Custom Field row + Version/Comment/File/… references), so the import neither fails on a duplicate fieldname nor silently deletes a different field. On the rehearsal copy it found nothing to rename.
- **Modified**: 3 rows during curation, plus 32 rows set to the values the GK site already has (`ecd9b53`): the rows came from the KG site's export, and a before/after comparison on the GK copy showed the full import would otherwise re-lay out the Customer form, swap which customer code shows in its list view, make Purchase Order Item `custom_copy_bom` editable and add a literal `''` option to Stock Entry `customer_voucher_type`. After the final migrate, the GK copy's Custom Fields differ from before the upgrade only by module tags and two intended fixes (Sales Invoice `custom_product_return_form_ref` now links to Product Return Order Form; Supplier MSME type gains the correctly spelt *Micro Enterprise*).
- **Order**: Frappe stops a fixture file at the first row whose DocType is missing and keeps what it already inserted, so rows are grouped by the app that owns their DocType in GK's install order (frappe, erpnext, india_compliance, payments, hrms, gke, jewellery, gurukrupa), then the three rows on jewellery's fixture-created `SI Item` DocType, then the optional apps (lending, helpdesk) last; within a DocType every `insert_after` target and Dynamic Link type field comes first. A site without an optional app therefore only skips that app's rows. (The first fresh-install run, with export order, stopped at the helpdesk row and left a half-made BOM Dynamic Link that broke the next migrate; `de33ad3` fixed the order.)
- **Effect on GK live**: today GK live's import stops at row 151 (`Skipping fixture syncing ... DocType Update Diamond Price  List not found`), so ~1,900 rows are never re-applied. With gk_prod the whole file imports (rehearsal: 1,970/1,970 rows present with matching type and options; no column missing).
- Nothing is deleted on existing sites: fixtures never delete rows, so dropped rows keep their existing definition and data (they are owned by jewellery_erpnext or are stale).

Dropped rows (name — decision — reason):

- `Purchase Invoice-export_type` — DROP_DUP_PROVIDER — P3: jewellery custom/purchase_invoice.json (sync_on_migrate=1) ships the identical row and overwrites gke's every migrate
- `Purchase Invoice-invoice_copy` — DROP_DUP_PROVIDER — P3: identical row in jewellery custom/purchase_invoice.json (sync_on_migrate=1)
- `Purchase Invoice-reverse_charge` — DROP_DUP_PROVIDER — P3: identical row in jewellery custom/purchase_invoice.json (sync_on_migrate=1)
- `Purchase Invoice-ecommerce_gstin` — DROP_DUP_PROVIDER — Duplicate of jewellery purchase_invoice.json (sync_on_migrate: 1), which re-asserts it after fixtures on every migrate.
- `Purchase Invoice-gst_col_break` — DROP_DUP_PROVIDER — Duplicate of jewellery purchase_invoice.json (sync_on_migrate: 1), which re-asserts it after fixtures on every migrate.
- `Purchase Invoice-reason_for_issuing_document` — DROP_DUP_PROVIDER — P3: identical row in jewellery custom/purchase_invoice.json (sync_on_migrate=1)
- `Purchase Invoice-eligibility_for_itc` — DROP_DUP_PROVIDER — P3: identical row in jewellery custom/purchase_invoice.json (sync_on_migrate=1)
- `Purchase Invoice-itc_integrated_tax` — DROP_DUP_PROVIDER — Duplicate of jewellery purchase_invoice.json (sync_on_migrate: 1), which re-asserts it after fixtures on every migrate.
- `Purchase Invoice-itc_central_tax` — DROP_DUP_PROVIDER — Duplicate of jewellery purchase_invoice.json (sync_on_migrate: 1), which re-asserts it after fixtures on every migrate.
- `Purchase Invoice-itc_state_tax` — DROP_DUP_PROVIDER — Duplicate of jewellery purchase_invoice.json (sync_on_migrate: 1), which re-asserts it after fixtures on every migrate.
- `Purchase Invoice-itc_cess_amount` — DROP_DUP_PROVIDER — Duplicate of jewellery purchase_invoice.json (sync_on_migrate: 1), which re-asserts it after fixtures on every migrate.
- `Supplier-export_type` — DROP_DUP_PROVIDER — P3: identical row in jewellery custom/supplier.json (sync_on_migrate=1)
- `Update Diamond Price  List-workflow_state` — DROP_STALE — dt 'Update Diamond Price  List' exists in no app and no fixture of the gk_prod stack.
- `Revise Diamond Price  List-workflow_state` — DROP_STALE — its dt 'Revise Diamond Price  List' is renamed away in gk_prod; on GK live the old DocType is already gone, so this row aborts the rest of the file today
- `Policy Change Request-workflow_state` — DROP_STALE — dt 'Policy Change Request' exists in no app and no fixture of the gk_prod stack.
- `Bonus-workflow_state` — DROP_STALE — dt 'Bonus' exists in no app and no fixture of the gk_prod stack.
- `Holiday Punch Entry-workflow_state` — DROP_STALE — dt 'Holiday Punch Entry' exists in no app and no fixture of the gk_prod stack.
- `Update Making Charge Price Item Subcategory-custom_category` — DROP_STALE — dt 'Update Making Charge Price Item Subcategory' exists in no app and no fixture of the gk_prod stack.
- `Sketch Order Form-workflow_state` — DROP_DUP_PROVIDER — Identical row shipped by the jewellery gurukrupa-prod fixture, which loads on every migrate.
- `Item Request-workflow_state` — DROP_STALE — workflow_state is a standard field of gke's own Item Request DocType.
- `Purchase Invoice Item-from_sales_invoice` — DROP_DUP_PROVIDER — Duplicate of jewellery purchase_invoice_item.json (sync_on_migrate: 1), which re-asserts it after fixtures on every migrate.
- `Accounts Settings-enable_audit_trail` — DROP_DUP_PROVIDER — india_compliance owns and provisions this field; gke row duplicates it (deviation note: install-time provider, not migrate-time).
- `Sketch Order-workflow_state` — DROP_DUP_PROVIDER — Identical row shipped by the jewellery gurukrupa-prod fixture, which loads on every migrate.
- `Sketch Order-custom_sketch_workflow_state` — DROP_DUP_PROVIDER — P3: identical row in jewellery fixtures/custom_field.json
- `Test-custom_first_name` — DROP_STALE — dt 'Test' exists in no app and no fixture of the gk_prod stack.
- `Supplier-operations` — DROP_DUP_PROVIDER — Duplicate of jewellery supplier.json (sync_on_migrate: 1), which re-asserts it after fixtures on every migrate.
- `Update Gemstone Price List-custom_handling_charges_for_outrightoutwork` — DROP_STALE — dt 'Update Gemstone Price List' exists in no app and no fixture of the gk_prod stack.
- `Sketch Order-custom_sketch_order_customer_approval_flow` — DROP_DUP_PROVIDER — Identical row shipped by the jewellery gurukrupa-prod fixture, which loads on every migrate.
- `Update Gemstone Price List-custom_handling_charges_` — DROP_STALE — dt 'Update Gemstone Price List' exists in no app and no fixture of the gk_prod stack.
- `Interview Round-custom_priority` — DROP_STALE — dt no longer exists in hrms v16.
- `Test-custom_last_name` — DROP_STALE — dt 'Test' exists in no app and no fixture of the gk_prod stack.
- `Update Gemstone Price List-custom_handling_charges_rate` — DROP_STALE — dt 'Update Gemstone Price List' exists in no app and no fixture of the gk_prod stack.
- `Sketch Order-manufacturer` — DROP_DUP_PROVIDER — Identical row shipped by the jewellery gurukrupa-prod fixture, which loads on every migrate. Also one of master's 5 fixture rows (identical): drop master's copy from gk_prod too.
- `Supplier-custom_territory` — DROP_DUP_PROVIDER — Duplicate of jewellery supplier.json (sync_on_migrate: 1), which re-asserts it after fixtures on every migrate.
- `Update Making Charge Price Item Subcategory-custom_description` — DROP_STALE — dt 'Update Making Charge Price Item Subcategory' exists in no app and no fixture of the gk_prod stack.
- `Supplier-custom_territory_code` — DROP_DUP_PROVIDER — Duplicate of jewellery supplier.json (sync_on_migrate: 1), which re-asserts it after fixtures on every migrate.
- `Purchase Invoice-si_reference_field` — DROP_DUP_PROVIDER — Duplicate of jewellery purchase_invoice.json (sync_on_migrate: 1), which re-asserts it after fixtures on every migrate.
- `Purchase Invoice-from_sales_invoice` — DROP_DUP_PROVIDER — Duplicate of jewellery purchase_invoice.json (sync_on_migrate: 1), which re-asserts it after fixtures on every migrate.
- `Update Making Charge Price Item Subcategory-custom_subcontracting_rate` — DROP_STALE — dt 'Update Making Charge Price Item Subcategory' exists in no app and no fixture of the gk_prod stack.
- `Print Settings-compact_item_print` — DROP_DUP_PROVIDER — erpnext owns and creates this Print Settings field; gke row is an identical copy (deviation note: install-time provider, not migrate-time).
- `Job Requisition-custom_vacancy_type` — DROP_DUP_PROVIDER — P3: gurukrupa_customizations fixture ships the identical row and loads after gke
- `Print Settings-print_uom_after_quantity` — DROP_DUP_PROVIDER — erpnext owns and creates this Print Settings field; gke row is an identical copy (deviation note: install-time provider, not migrate-time).
- `Update Making Charge Price Item Subcategory-custom_making_charges_code` — DROP_STALE — dt 'Update Making Charge Price Item Subcategory' exists in no app and no fixture of the gk_prod stack.
- `Serial and Batch Entry-inventory_dimension` — DROP_DUP_PROVIDER — Duplicate of jewellery serial_and_batch_entry.json (sync_on_migrate: 1), which re-asserts it after fixtures on every migrate.
- `Update Making Charge Price Item Subcategory-custom_subcontracting_wastage` — DROP_STALE — dt 'Update Making Charge Price Item Subcategory' exists in no app and no fixture of the gk_prod stack.
- `Supplier-section_break_hnpah` — DROP_DUP_PROVIDER — Duplicate of jewellery supplier.json (sync_on_migrate: 1), which re-asserts it after fixtures on every migrate.
- `Serial and Batch Entry-inventory_type` — DROP_DUP_PROVIDER — Duplicate of jewellery serial_and_batch_entry.json (sync_on_migrate: 1), which re-asserts it after fixtures on every migrate.
- `Job Requisition-custom_vacancy_priority` — DROP_DUP_PROVIDER — P3: gurukrupa_customizations fixture ships the identical row and loads after gke
- `Employee Referral-custom_reference_type` — DROP_DUP_PROVIDER — P3: gurukrupa_customizations fixture ships the identical row and loads after gke
- `Print Settings-print_taxes_with_zero_amount` — DROP_DUP_PROVIDER — erpnext owns and creates this Print Settings field; gke row is an identical copy (deviation note: install-time provider, not migrate-time).
- `Customer-custom_vendor_code` — DROP_DUP_PROVIDER — same pattern as 1636: jewellery custom/customer.json ships it canonically; dropping changes nothing on existing sites
- `Journal Entry-custom_bonus_reference` — DROP_STALE — Link to a DocType ('Bonus') that exists nowhere on the gk_prod stack (deviation: P2 lists Table targets; this is a Link, but frappe itself rejects it outside fixture import).
- `Asset-custom_asset_warranty_details` — DROP_STALE — Table target 'Asset Warranty Details' is missing from the stack.
- `Item-tag_no` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate (FACTS' 'none overlap' is wrong).
- `Attendance-overtime_hrs` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate (FACTS' 'none overlap' is wrong).
- `Item-custom_master_serial_no_table` — DROP_STALE — Table target 'Master Serial No Table' is missing from the stack.
- `Sketch Order-custom_item` — DROP_DUP_PROVIDER — Identical row shipped by the jewellery gurukrupa-prod fixture, which loads on every migrate. Also one of master's 5 fixture rows (identical): drop master's copy from gk_prod too.
- `Supplier-is_msme` — DROP_DUP_PROVIDER — Duplicate of jewellery supplier.json (sync_on_migrate: 1), which re-asserts it after fixtures on every migrate.
- `Sales Order Item-project` — DROP_STALE — project is a standard field of erpnext v16 Sales Order Item.
- `Material Request-custom_material_request_department_transfer` — DROP_STALE — Table target 'Material Request Department Transfer' is missing from the stack.
- `Item-section_break_13` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate (FACTS' 'none overlap' is wrong).
- `Item-item_category_code` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate (FACTS' 'none overlap' is wrong).
- `Sketch Order-custom_nakshi_from` — DROP_DUP_PROVIDER — Identical row shipped by the jewellery gurukrupa-prod fixture, which loads on every migrate.
- `Item-approx_gold` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate (FACTS' 'none overlap' is wrong).
- `Purchase Invoice Item-inventory_dimension` — DROP_DUP_PROVIDER — Duplicate of jewellery purchase_invoice_item.json (sync_on_migrate: 1), which re-asserts it after fixtures on every migrate.
- `Item-sequence` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate (FACTS' 'none overlap' is wrong).
- `Purchase Invoice Item-stock_entry` — DROP_DUP_PROVIDER — Duplicate of jewellery purchase_invoice_item.json (sync_on_migrate: 1), which re-asserts it after fixtures on every migrate.
- `Purchase Invoice Item-inventory_type` — DROP_DUP_PROVIDER — Duplicate of jewellery purchase_invoice_item.json (sync_on_migrate: 1), which re-asserts it after fixtures on every migrate.
- `Item-column_break_41` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate (FACTS' 'none overlap' is wrong).
- `Item-manufacturing_type` — DROP_DUP_PROVIDER — P3: gurukrupa_customizations fixture ships the identical row (including default Casted) and loads after gke
- `Item-productivity` — DROP_DUP_PROVIDER — P3: gurukrupa_customizations fixture ships the identical row (including default Studded) and loads after gke
- `Item-order_form_type` — DROP_DUP_PROVIDER — P3: gurukrupa_customizations ships the same name+pair with options '\nOrder\nSketch Order' and wins every migrate. No live gk_prod code needs gke's extra 'Repair Order'
- `Item-column_break_qujga` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate (FACTS' 'none overlap' is wrong).
- `Item-order_form_id` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate (FACTS' 'none overlap' is wrong).
- `Supplier-purchase_type` — DROP_DUP_PROVIDER — Duplicate of jewellery supplier.json (sync_on_migrate: 1), which re-asserts it after fixtures on every migrate.
- `Item-custom_cad_order_form_id` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate (FACTS' 'none overlap' is wrong).
- `Supplier-custom_msme_number` — DROP_DUP_PROVIDER — Duplicate of jewellery supplier.json (sync_on_migrate: 1), which re-asserts it after fixtures on every migrate.
- `Supplier-column_break_csgpp` — DROP_DUP_PROVIDER — Duplicate of jewellery supplier.json (sync_on_migrate: 1), which re-asserts it after fixtures on every migrate.
- `Purchase Invoice Item-inventory_dimension_col_break` — DROP_DUP_PROVIDER — Actually-loading provider jewellery custom/purchase_invoice_item.json ships the same pair and overwrites gke's row on every migrate.
- `Sketch Order-inventory_dimension` — DROP_DUP_PROVIDER — Identical row shipped by the jewellery gurukrupa-prod fixture, which loads on every migrate.
- `Sketch Order-inventory_type` — DROP_DUP_PROVIDER — Identical row shipped by the jewellery gurukrupa-prod fixture, which loads on every migrate.
- `Employee-custom_accident_insurance_provider` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations after_migrate re-applies this Employee field on every migrate (not listed in FACTS).
- `Customer-custom_metal_criteria` — DROP_DUP_PROVIDER — verify:needs-review and verify:misc: jewellery custom/customer.json ships it (canonical name, install-time); sites keep their row
- `Customer-custom_customer_diamond_grade` — DROP_DUP_PROVIDER — same pattern as 1636: jewellery custom/customer.json ships it canonically; dropping changes nothing on existing sites
- `Employee-additional_info` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations after_migrate re-applies this Employee field on every migrate (not listed in FACTS).
- `Employee-column_break_9oy5o` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations after_migrate re-applies this Employee field on every migrate (not listed in FACTS).
- `Employee-employee_cast` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations after_migrate re-applies this Employee field on every migrate (not listed in FACTS).
- `Item-product_supplier` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate (FACTS' 'none overlap' is wrong).
- `Employee-column_break_t3xn9` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations after_migrate re-applies this Employee field on every migrate (not listed in FACTS).
- `Employee-reference_contact` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations after_migrate re-applies this Employee field on every migrate (not listed in FACTS).
- `Employee-driving_licence_details` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations after_migrate re-applies this Employee field on every migrate (not listed in FACTS).
- `Customer-custom_customer_finding` — DROP_STALE — Table target missing on the gk_prod stack (P2).
- `Item-is_system_item` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate (FACTS' 'none overlap' is wrong).
- `Employee-handicap_certificate_date` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations after_migrate re-applies this Employee field on every migrate (not listed in FACTS).
- `Employee-is_physical_handicap` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations after_migrate re-applies this Employee field on every migrate (not listed in FACTS).
- `Employee-uan_number` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations after_migrate re-applies this Employee field on every migrate (not listed in FACTS).
- `Item-custom_age_group` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate.
- `Item-custom_alphabetnumber` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate.
- `Item-custom_animalbirds` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate.
- `Item-custom_collection` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate.
- `Item-custom_design_style` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate.
- `Item-custom_gender` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate.
- `Item-custom_lines__rows` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate.
- `Item-custom_language` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate.
- `Item-custom_occasion` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate.
- `Item-custom_rhodium` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate.
- `Item-custom_religious` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate.
- `Item-custom_shapes` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate.
- `Item-custom_zodiac` — DROP_DUP_PROVIDER — Actually-loading provider gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate.
- `Item-design_attribute` — DROP_DUP_PROVIDER — gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate.
- `Item-usa_states` — DROP_DUP_PROVIDER — P3: gurukrupa_customizations fixture ships a fully identical row (module included) and loads after gke
- `Item-mould_details` — DROP_DUP_PROVIDER — gurukrupa_customizations fixtures ships the same pair and wins after gke on every migrate.
- `BOM-bom_scrap_item` — DROP_STALE — Table target 'BOM Scrap Item' was removed in erpnext v16 (replaced by BOM Secondary Item).

## DocType fixtures (fixtures/doctype.json)

kggk_prod ships 51 DocType rows, 46 of which duplicate jewellery_erpnext's own fixtures (and one, Demo Work, lists `amended_from` twice, which makes a fresh install fail). gk_prod ships the 5 gke-owned custom DocTypes: Rename BOM, Order Missing Value, Order Missing Value Table, Data Update, Deposit Item Details.

## Property setters

gke_customization ships no Property Setter fixtures on any branch; none were added.

## Patches

```
[pre_model_sync]
gke_customization.patches.rename_revise_diamond_price_list_doctype
gke_customization.patches.canonicalise_custom_field_names

[post_model_sync]

gke_customization.patches.gc_ration_master
gke_customization.patches.salary_withholding_release_fields
gke_customization.patches.v1_0.v15_rename_close_setting_to_nova_glow
```

| Patch | Section | What | Idempotent / fresh install | Rehearsal |
|---|---|---|---|---|
| `rename_revise_diamond_price_list_doctype` | pre_model_sync | renames the DocType `Revise Diamond Price  List` (two spaces) to `Revise Diamond Price List` before sync so documents are kept | no-op when the old DocType is absent; fresh install marks it done | ran, no-op (GK copy has no old DocType) |
| `canonicalise_custom_field_names` | pre_model_sync | aligns existing Custom Field document names with the shipped canonical names; refuses (and leaves Patch Log unset) on conflicts it cannot resolve | idempotent; fresh install marks it done | ran, nothing to rename |
| `gc_ration_master` | post_model_sync | production patch (2026-02) normalising GC Ratio rows | already applied on GK live (line text unchanged) | not pending |
| `salary_withholding_release_fields` | post_model_sync | production patch (2026-08) adding hrms Salary Withholding fields | already applied on GK live | not pending |
| `v1_0.v15_rename_close_setting_to_nova_glow` | post_model_sync | master's one-way rename of the *Close* setting master data to *Nova Glow* across ~60 DocTypes | guarded by the `close_setting_to_nova_glow_v2` sentinel it shares with jewellery_erpnext's `v16_0_rename_close_setting_to_nova_glow`; jewellery runs first in installed-app order | ran as a no-op: jewellery's patch had already renamed (abbreviation NGS) |

### Nova Glow deploy note

- On GK live the rename is done by jewellery_erpnext's v16 patch if it has run there (it is in jewellery gurukrupa-prod's patches.txt); gke's patch then records itself as done without changing data.
- If a site reaches gke's patch first (jewellery's patch absent), gke renames with abbreviation `NG` where jewellery uses `NGS`. KG and GK sites call each other's pricing with the setting value, so both must switch in the same window. Take a database backup before the deploy; the patch docstring carries the rollback SQL.

## Hooks

### doc_events

| Entry | master | GK live | gk_prod |
|---|:-:|:-:|:-:|
| `Batch → autoname → jewellery_erpnext.jewellery_erpnext.customization.batch.batch.autoname` | ✅ | ❌ | ❌ |
| `Journal Entry → on_cancel → gke_customization.gke_hrms.doc_events.journal_entry.update_withholding_release_status` | ❌ | ✅ | ✅ |
| `Journal Entry → on_submit → gke_customization.gke_hrms.doc_events.journal_entry.update_withholding_release_status` | ❌ | ✅ | ✅ |
| `Journal Entry → on_trash → gke_customization.gke_hrms.doc_events.journal_entry.cancel_withholding_releases_on_trash` | ❌ | ✅ | ✅ |
| `Salary Slip → before_validate → gke_customization.overrides.salary_slip.seed_slip_only_formula_fields` | ❌ | ✅ | ✅ |
| `Sales Invoice → validate → gke_customization.gke_customization.doc_events.sales_invoice.validate` | ❌ | ✅ | ❌ |

### scheduler_events

| Entry | master | GK live | gk_prod |
|---|:-:|:-:|:-:|
| `cron → 0 15 * * * → gke_customization.gke_price_list.doctype.gold_rates.gold_rates.run_gold_rate_scheduler` | ❌ | ✅ | ✅ |
| `cron → 0 23 * * * → gke_customization.gke_price_list.doctype.gold_rates.gold_rates.run_gold_rate_scheduler` | ❌ | ✅ | ✅ |
| `cron → 0 9 * * * → gke_customization.gke_price_list.doctype.gold_rates.gold_rates.run_gold_rate_scheduler` | ❌ | ✅ | ✅ |

### override_doctype_class

| Entry | master | GK live | gk_prod |
|---|:-:|:-:|:-:|
| `Payroll Entry → gke_customization.overrides.payroll_entry.CustomPayrollEntry` | ❌ | ✅ | ✅ |
| `Salary Structure Assignment → gke_customization.overrides.salary_structure_assignment.CustomSalaryStructureAssignment` | ❌ | ✅ | ✅ |

### doctype_js

| Entry | master | GK live | gk_prod |
|---|:-:|:-:|:-:|
| `Payroll Entry → public/js/doctype_js/payroll_entry.js` | ❌ | ✅ | ✅ |

Only entries that differ between the three branches are listed.

