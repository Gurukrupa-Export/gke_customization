# 01 — Commit inventory

Every commit unique to `kggk_prod` (501) or to `gurukrupa-prod` (6) is listed in [`01_commit_inventory.csv`](01_commit_inventory.csv) — one row per commit, with its unit, PR, author, date, subject, classifier status, final status, how it was carried and the new commit on the migration branch.

Commits were analysed per **unit** (one first-parent PR merge or direct commit together with the commits it brought in), because the PR, not the SHA, is the logical change. Each unit got one status; `final_status` records the outcome after the 2026-10-02 business checkpoint.

## Totals

| Final status | Units | Commits |
|---|---:|---:|
| PORT | 92 | 284 |
| SKIP_ALREADY_IN_MASTER | 50 | 125 |
| SKIP_PATCH_EQUIVALENT | 7 | 15 |
| SKIP_SUPERSEDED | 15 | 44 |
| SKIP_REVERTED | 12 | 30 |
| SKIP_UNRELATED | 3 | 9 |
| **total** | **179** | **507** |

No unit is left at `NEEDS_BUSINESS_REVIEW` or `NEEDS_TECHNICAL_REVIEW`: the six that were are resolved in `final_status` with the decision that settled them (see 05 and 06).

## How the PORT units were carried

| Port method | Units |
|---|---:|
| retained-from-master | 61 |
| manual-logical-port | 28 |
| squashed-port | 26 |
| direct-cherry-pick | 19 |
| superseded | 15 |
| reverted | 12 |
| direct-cherry-pick + manual-logical-port | 9 |
| squashed-port + manual-logical-port | 6 |
| not-required | 3 |

- **direct-cherry-pick**: the developer's own commits replayed with `cherry-pick -x`, author and date kept, `Part-of: #PR` trailer.
- **squashed-port**: the PR's net change replayed with `cherry-pick -m 1 -x` (PRs with internal merges or whose leaves do not reproduce the PR), main author kept, other authors as `Co-authored-by`, `Includes-commits:` trailer.
- **manual-logical-port**: the part of the change on files master also changed, landed in one of the seven consolidated three-way port commits (`Ported-from:` trailers).
- **retained-from-master**: master already has the same change; nothing to carry.

## Units

| Unit | PR | Merge / commit | Date | Feature | Final status | How it landed | New commit(s) |
|---|---|---|---|---|---|---|---|
| kggk:1 | #634 | `d0816eb1ab` | 2026-02-04 | Tests | PORT | leaf x1 | `be91292` |
| kggk:2 | #631 | `398707865a` | 2026-02-04 | Order | PORT | leaf x1 (1 empty); held-back paths -> c2-order-family | `48639f4` |
| kggk:3 | #644 | `2f041b5969` | 2026-02-11 | Order | PORT | leaf x1; held-back paths -> c2-order-family | `71f72ef` `48639f4` |
| kggk:4 | #645 | `a01ead8785` | 2026-02-11 | Patches | PORT | leaf x1 (1 empty); held-back paths -> c1-hooks-patches-pyproject | `083c594` |
| kggk:5 | #646 | `c003e91b41` | 2026-02-11 | Order | PORT | leaf x1 | `86232cd` |
| kggk:6 | #650 | `549b99bf40` | 2026-02-13 | Order | PORT | leaf x1 (1 empty); held-back paths -> c2-order-family, c3-pricing-sales-hooks | `48639f4` `ed24d61` |
| kggk:7 | #651 | `b297393035` | 2026-02-13 | Patches | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:8 | #653 | `7de53ba167` | 2026-02-17 | Order Form | SKIP_SUPERSEDED | skip | — |
| kggk:9 | #666 | `e93df539c4` | 2026-02-23 | HR attendance and punches | SKIP_PATCH_EQUIVALENT | skip | — |
| kggk:10 | — | `e7d0b7dbf9` | 2026-04-27 | Stock and inventory reports | SKIP_SUPERSEDED | direct (empty); held-back paths -> c7-catalogue-survey | `dd838b8` |
| kggk:11 | #749 | `9f3433b271` | 2026-04-29 | Order Form | PORT | PR net change (-m 1); held-back paths -> c1-hooks-patches-pyproject, c2-order-family | `e673fd9` `083c594` `48639f4` |
| kggk:12 | #746 | `f946dc8b4e` | 2026-04-30 | Price List and Revise Price | PORT | leaf x1; held-back paths -> c5-revise-price-lists | `47465ae` `6934d29` |
| kggk:13 | #750 | `2bb0e3ccb1` | 2026-05-02 | Item and BOM creation and KGGK replication | PORT | leaf x1 (1 empty); held-back paths -> c2-order-family | `48639f4` |
| kggk:14 | #752 | `254f25877f` | 2026-05-02 | Item and BOM creation and KGGK replication | PORT | leaf x1 (1 empty); held-back paths -> c2-order-family | `48639f4` |
| kggk:15 | #758 | `3aa12e00e1` | 2026-05-04 | Order | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:16 | #759 | `49a4c3da9c` | 2026-05-05 | Order Form | PORT | leaf x1 (1 empty); held-back paths -> c2-order-family | `48639f4` |
| kggk:17 | #760 | `0868e53bf7` | 2026-05-05 | Order | PORT | leaf x1 (1 empty); held-back paths -> c2-order-family | `48639f4` |
| kggk:18 | #762 | `5ac322b67e` | 2026-05-05 | Order Form | SKIP_SUPERSEDED | skip | — |
| kggk:19 | #763 | `8effcc39a3` | 2026-05-06 | Order Form | PORT | leaf x1; held-back paths -> c2-order-family | `81de021` `48639f4` |
| kggk:20 | #764 | `e6973785dd` | 2026-05-06 | Gold Rates | PORT | leaf x1; held-back paths -> c2-order-family | `64f15cf` `48639f4` |
| kggk:21 | #770 | `19f1882756` | 2026-05-07 | Order Form | PORT | leaf x1 (1 empty); held-back paths -> c2-order-family | `48639f4` |
| kggk:22 | #769 | `5709d9cfde` | 2026-05-07 | Packaging and config | PORT | direct (empty); held-back paths -> c1-hooks-patches-pyproject | `083c594` |
| kggk:23 | #772 | `5cf65cd5ac` | 2026-05-08 | Order Form | PORT | leaf x1 (1 empty); held-back paths -> c2-order-family | `48639f4` |
| kggk:24 | #774 | `faa55e2c8b` | 2026-05-08 | Order Form | PORT | leaf x1 (1 empty); held-back paths -> c2-order-family | `48639f4` |
| kggk:25 | #789 | `421656ee9e` | 2026-05-18 | HR attendance and punches | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:26 | #792 | `3be028bdc8` | 2026-05-19 | Order Form | PORT | leaf x1; held-back paths -> c2-order-family | `c3ab935` `48639f4` |
| kggk:27 | #799 | `4734bd2f40` | 2026-05-26 | Gold Rates | PORT | leaf x1 | `117e4db` |
| kggk:28 | #808 | `f74d9a1610` | 2026-05-28 | Gold Rates | PORT | leaf x1 | `3991b28` |
| kggk:29 | #809 | `c6b22dadd7` | 2026-05-29 | Fixtures | PORT | leaf x1 (1 empty) | `26bfda3` |
| kggk:30 | — | `d5878c4f98` | 2026-05-29 | Fixtures | PORT | direct (empty) | `26bfda3` |
| kggk:31 | #810 | `fa7ea703a5` | 2026-05-29 | Diamond and Gemstone pricing | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:32 | #818 | `310eb6a215` | 2026-06-02 | Tests | PORT | leaf x1 | `6545610` |
| kggk:33 | #817 | `b0b2aeec21` | 2026-06-02 | Making charges | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:34 | #819 | `d25f9f1688` | 2026-06-02 | Diamond and Gemstone pricing | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:35 | #820 | `a7163c1489` | 2026-06-03 | Price List and Revise Price | PORT | leaf x1 | `60b7449` |
| kggk:36 | #822 | `93da164324` | 2026-06-03 | Making charges | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:37 | #823 | `10f0cfa68e` | 2026-06-04 | Sales and HR reports | PORT | leaf x8 | `5ff3d31` `be7e82f` `20e246a` `14793d7` `7ae741e` `8ae4219` `8eff717` `ade6ff3` |
| kggk:38 | #825 | `d5541c6535` | 2026-06-04 | Price List and Revise Price | PORT | PR net change (-m 1); held-back paths -> c5-revise-price-lists | `687a7dc` `6934d29` |
| kggk:39 | #833 | `5c19380b01` | 2026-06-09 | Manufacturing reports | PORT | PR net change (-m 1) | `f36d428` |
| kggk:40 | #835 | `bcb4b9c1cc` | 2026-06-09 | Product Return Order | SKIP_SUPERSEDED | skip | — |
| kggk:41 | #840 | `c673ca33ff` | 2026-06-10 | Manufacturing reports | PORT | leaf x2 | `0fbc6c7` `0ed99a0` |
| kggk:42 | #841 | `efd81fa2d1` | 2026-06-13 | Manufacturing reports | PORT | leaf x1 | `68a971d` |
| kggk:43 | #850 | `c24d209016` | 2026-06-13 | Product Return Order | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:44 | — | `c6fdce26f2` | 2026-06-14 | Sales Order, Delivery Note and Invoice hooks | PORT | direct; held-back paths -> c3-pricing-sales-hooks | `965a95d` `ed24d61` |
| kggk:45 | #856 | `020d9624e0` | 2026-06-17 | Making charges | PORT | leaf x1 (1 empty); held-back paths -> c3-pricing-sales-hooks | `ed24d61` |
| kggk:46 | #858 | `057fbac944` | 2026-06-18 | Making charges | PORT | leaf x1 (1 empty); held-back paths -> c3-pricing-sales-hooks | `ed24d61` |
| kggk:47 | #861 | `b140da522c` | 2026-06-18 | Diamond and Gemstone pricing | PORT | leaf x1 (1 empty); held-back paths -> c3-pricing-sales-hooks | `ed24d61` |
| kggk:48 | #862 | `a887b4c45e` | 2026-06-18 | Diamond and Gemstone pricing | PORT | leaf x1 (1 empty); held-back paths -> c3-pricing-sales-hooks | `ed24d61` |
| kggk:49 | #864 | `4c231fda6b` | 2026-06-19 | Repair Order | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:50 | #867 | `c72dab2608` | 2026-06-21 | Item and BOM creation and KGGK replication | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:51 | #869 | `0ccb08995b` | 2026-06-22 | Repair Order | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:52 | #871 | `1d04e98ba8` | 2026-06-22 | Item and BOM creation and KGGK replication | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:53 | #872 | `7a1ea3d7b8` | 2026-06-22 | Repair Order | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:54 | #873 | `aebd145e48` | 2026-06-22 | Item and BOM creation and KGGK replication | SKIP_SUPERSEDED | skip | — |
| kggk:55 | #874 | `43fddcb04c` | 2026-06-22 | Repair Order | SKIP_SUPERSEDED | skip | — |
| kggk:56 | #877 | `a714c9922c` | 2026-06-22 | Order | SKIP_REVERTED | skip | — |
| kggk:57 | #879 | `a0e1050676` | 2026-06-22 | Item and BOM creation and KGGK replication | PORT | leaf x1 (1 empty); held-back paths -> c1-hooks-patches-pyproject, c3-pricing-sales-hooks | `083c594` `ed24d61` |
| kggk:58 | #882 | `41179f265d` | 2026-06-22 | Item and BOM creation and KGGK replication | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:59 | #883 | `324edbc5bd` | 2026-06-23 | Item and BOM creation and KGGK replication | SKIP_SUPERSEDED | leaf x1 (1 empty); held-back paths -> c3-pricing-sales-hooks | `ed24d61` |
| kggk:60 | #885 | `0c191e3f66` | 2026-06-23 | Order | SKIP_REVERTED | skip | — |
| kggk:61 | #887 | `3a75b2ee68` | 2026-06-23 | Repair Order | SKIP_SUPERSEDED | skip | — |
| kggk:62 | #888 | `31a2af21e9` | 2026-06-23 | Repair Order | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:63 | #890 | `a2df7b513a` | 2026-06-23 | Repair Order | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:64 | #892 | `662fc2c0cb` | 2026-06-23 | Product Return Order | SKIP_SUPERSEDED | skip | — |
| kggk:65 | #895 | `2f68217c73` | 2026-06-23 | Item and BOM creation and KGGK replication | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:66 | #901 | `947cf74b68` | 2026-06-24 | Item and BOM creation and KGGK replication | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:67 | #900 | `099f93dadf` | 2026-06-24 | Order Form | SKIP_REVERTED | skip | — |
| kggk:68 | #902 | `d360a42f69` | 2026-06-24 | Order Form | SKIP_REVERTED | skip | — |
| kggk:69 | #911 | `24f9193fe9` | 2026-06-25 | Data Migration in KGGK | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:70 | #908 | `174e9f1249` | 2026-06-25 | Order Form | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:71 | #914 | `f87bdc5621` | 2026-06-27 | Order Form | SKIP_REVERTED | skip | — |
| kggk:72 | #913 | `f875de6858` | 2026-06-27 | Order | SKIP_REVERTED | skip | — |
| kggk:73 | #916 | `9067f1c4dd` | 2026-06-27 | Order Form | SKIP_REVERTED | skip | — |
| kggk:74 | #917 | `95b5b3b66b` | 2026-06-27 | Order | SKIP_REVERTED | skip | — |
| kggk:75 | #920 | `75d4195722` | 2026-06-30 | HR attendance and punches | SKIP_PATCH_EQUIVALENT | skip | — |
| kggk:76 | #926 | `777eae6618` | 2026-07-02 | Manufacturing reports | PORT | leaf x1 | `fc51b2f` |
| kggk:77 | #930 | `f374adb9bc` | 2026-07-02 | Manufacturing reports | PORT | PR net change (-m 1) | `c7c46e4` |
| kggk:78 | #928 | `a8d94cd038` | 2026-07-02 | Order Form | PORT | PR net change (-m 1) (empty); held-back paths -> c2-order-family | `48639f4` |
| kggk:79 | #931 | `a10114d4ae` | 2026-07-02 | HR attendance and punches | SKIP_PATCH_EQUIVALENT | skip | — |
| kggk:80 | #933 | `abf79b4a37` | 2026-07-02 | HR attendance and punches | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:81 | #935 | `c480b15015` | 2026-07-03 | Manufacturing reports | PORT | PR net change (-m 1) | `7d1eea5` |
| kggk:82 | #938 | `737198076c` | 2026-07-03 | HR overtime | PORT | leaf x1 | `a01fe9b` |
| kggk:83 | #943 | `cdc4ecc02d` | 2026-07-06 | Manufacturing reports | PORT | PR net change (-m 1) | `967e312` |
| kggk:84 | #944 | `132daca436` | 2026-07-06 | Order Form | PORT | PR net change (-m 1); held-back paths -> c2-order-family | `d5c030e` `48639f4` |
| kggk:85 | #947 | `9727741f1a` | 2026-07-08 | Manufacturing reports | PORT | leaf x1 | `8834d48` |
| kggk:86 | #948 | `7b09193242` | 2026-07-09 | HR payroll and salary withholding | SKIP_PATCH_EQUIVALENT | skip | — |
| kggk:87 | #949 | `81ef3e9c30` | 2026-07-09 | Order Form | PORT | leaf x1; held-back paths -> c2-order-family | `4f95b9a` `48639f4` |
| kggk:88 | #961 | `6278f9019d` | 2026-07-15 | Manufacturing reports | PORT | PR net change (-m 1); held-back paths -> c7-catalogue-survey | `bc5198d` `dd838b8` |
| kggk:89 | #963 | `5ad362ebaa` | 2026-07-15 | Manufacturing reports | PORT | PR net change (-m 1) | `450c974` |
| kggk:90 | #965 | `cb9acada3f` | 2026-07-15 | HR overtime | PORT | PR net change (-m 1) | `544ca41` |
| kggk:91 | #967 | `35481e8661` | 2026-07-16 | Product Return Order | SKIP_SUPERSEDED | skip | — |
| kggk:92 | #968 | `8a3afd4d05` | 2026-07-17 | HR employee lifecycle | PORT | leaf x1 | `9faadcb` |
| kggk:93 | — | `ca7004c4a9` | 2026-07-20 | Stock and inventory reports | PORT | direct | `7d4c4fa` |
| kggk:94 | #973 | `b6335658d6` | 2026-07-20 | Stock and inventory reports | SKIP_REVERTED | skip | — |
| kggk:95 | — | `05d0bbb1a6` | 2026-07-21 | Product Return Order | PORT | direct (empty); held-back paths -> c4-product-return; 2 path(s) converged with master | `87d5e26` |
| kggk:96 | #977 | `c32d0cad7f` | 2026-07-21 | Product Return Order | PORT | PR net change (-m 1) (empty); held-back paths -> c4-product-return | `87d5e26` |
| kggk:97 | #979 | `cccbb2c097` | 2026-07-22 | Product Return Order | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:98 | #981 | `1d0f40b5db` | 2026-07-22 | HR attendance and punches | PORT | PR net change (-m 1) | `7b3cbb3` |
| kggk:99 | #988 | `5142bd4ca5` | 2026-07-22 | Order Form | PORT | leaf x1 (1 empty); held-back paths -> c2-order-family, c5-revise-price-lists; 1 path(s) converged with master | `48639f4` `6934d29` |
| kggk:100 | #991 | `5fe374c1af` | 2026-07-23 | Product Return Order | SKIP_SUPERSEDED | skip | — |
| kggk:101 | #995 | `52797c9e2e` | 2026-07-23 | Stock and inventory reports | PORT | PR net change (-m 1) | `5c488a9` |
| kggk:102 | — | `1bdd883466` | 2026-07-24 | Stock and inventory reports | SKIP_REVERTED | skip | — |
| kggk:103 | #996 | `9e18b4af8b` | 2026-07-24 | Order Form | SKIP_PATCH_EQUIVALENT | skip | — |
| kggk:104 | #998 | `e050850422` | 2026-07-25 | Manufacturing reports | PORT | PR net change (-m 1) | `895cf9a` |
| kggk:105 | #999 | `31cbd4dc28` | 2026-07-25 | Manufacturing reports | PORT | leaf x1 | `5561eaf` |
| kggk:106 | #1001 | `f86ab07a96` | 2026-07-25 | Manufacturing reports | PORT | PR net change (-m 1) | `cd21123` |
| kggk:107 | #1003 | `a3dfe421cf` | 2026-07-25 | Manufacturing reports | PORT | PR net change (-m 1) | `bb117c1` |
| kggk:108 | #1005 | `582ab418b6` | 2026-07-25 | Product Return Order | SKIP_SUPERSEDED | PR net change (-m 1) (empty); held-back paths -> c4-product-return | `87d5e26` |
| kggk:109 | #1007 | `16fec73930` | 2026-07-26 | Product Return Order | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:110 | #1010 | `40b04bc125` | 2026-07-27 | Product Return Order | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:111 | #1011 | `7fbb3e841e` | 2026-07-27 | Item and BOM creation and KGGK replication | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:112 | #1014 | `37499e78c5` | 2026-07-27 | Product Return Order | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:113 | #1016 | `46b754fa3a` | 2026-07-27 | Manufacturing reports | PORT | PR net change (-m 1) | `1122c5a` |
| kggk:114 | #1019 | `7b4922f857` | 2026-07-27 | Repair Order | PORT | PR net change (-m 1) (empty); held-back paths -> c2-order-family; 5 path(s) converged with master | `48639f4` |
| kggk:115 | #1018 | `d34dbe92ae` | 2026-07-27 | Manufacturing reports | PORT | leaf x1 | `8a94523` |
| kggk:116 | #1020 | `046589febe` | 2026-07-27 | Product Return Order | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:117 | #1021 | `a50376d183` | 2026-07-27 | Manufacturing reports | PORT | leaf x1 | `b82a01d` |
| kggk:118 | #1025 | `33bdbd1d0a` | 2026-07-28 | Repair Order | PORT | leaf x1 (1 empty); held-back paths -> c2-order-family; 6 path(s) converged with master | `48639f4` |
| kggk:119 | #1029 | `fb172765bf` | 2026-07-29 | Repair Order | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:120 | #1030 | `b2e1f1327f` | 2026-07-29 | Repair Order | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:121 | #1032 | `d0efb8cd08` | 2026-07-30 | Product Return Order | SKIP_SUPERSEDED | skip | — |
| kggk:122 | #1038 | `2893736db8` | 2026-07-31 | Product Return Order | SKIP_SUPERSEDED | skip | — |
| kggk:123 | #1053 | `40bbae8d83` | 2026-08-01 | HR employee lifecycle | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:124 | #1057 | `939d28bccd` | 2026-08-03 | Manufacturing reports | PORT | PR net change (-m 1) | `5f1177c` `485f6f6` |
| kggk:125 | #1051 | `41defdf99b` | 2026-08-03 | Product Return Order | SKIP_SUPERSEDED | skip | — |
| kggk:126 | #1060 | `205aea60e8` | 2026-08-03 | Manufacturing reports | PORT | PR net change (-m 1) | `a1371f4` |
| kggk:127 | #1072 | `1e3ff5808e` | 2026-08-06 | Product Return Order | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:128 | #1074 | `bba46393b9` | 2026-08-07 | HR attendance and punches | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:129 | #1076 | `638f440e5b` | 2026-08-08 | Manufacturing reports | PORT | PR net change (-m 1) | `e0643de` |
| kggk:130 | #1077 | `4153192426` | 2026-08-08 | HR attendance and punches | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:131 | #1079 | `8b2d1c88ed` | 2026-08-08 | HR payroll and salary withholding | SKIP_PATCH_EQUIVALENT | skip | — |
| kggk:132 | #1081 | `3699372492` | 2026-08-10 | Order | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:133 | #1082 | `2299e0f89f` | 2026-08-10 | HR attendance and punches | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:134 | #1084 | `e0c8c29de9` | 2026-08-10 | Order | PORT | PR net change (-m 1) (empty); held-back paths -> c2-order-family | `48639f4` |
| kggk:135 | #1086 | `e26a0251f6` | 2026-08-11 | Order | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:136 | #1088 | `5679b355dc` | 2026-08-11 | Manufacturing reports | PORT | PR net change (-m 1) | `964ac3e` |
| kggk:137 | #1091 | `9d165999ce` | 2026-08-12 | Order Form | SKIP_PATCH_EQUIVALENT | skip | — |
| kggk:138 | #1093 | `1ac7132715` | 2026-08-12 | HR attendance and punches | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:139 | #1101 | `367bb9dd2c` | 2026-08-13 | Asset Item Master | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:140 | #1099 | `0b806e5de1` | 2026-08-13 | Item and BOM creation and KGGK replication | PORT | PR net change (-m 1) (empty); held-back paths -> c3-pricing-sales-hooks | `ed24d61` |
| kggk:141 | #1103 | `a26b426d3c` | 2026-08-13 | Manufacturing reports | PORT | PR net change (-m 1) | `f19a00f` |
| kggk:142 | #1108 | `37606c2710` | 2026-08-15 | Manufacturing reports | PORT | PR net change (-m 1) | `d21fc64` |
| kggk:143 | #1110 | `a67674c412` | 2026-08-16 | Manufacturing reports | PORT | PR net change (-m 1) | `f7aa06d` |
| kggk:144 | #1119 | `2ea8770fa2` | 2026-08-18 | Product Return Order | PORT | PR net change (-m 1) (empty); held-back paths -> c4-product-return | `87d5e26` |
| kggk:145 | #1129 | `ba4549b284` | 2026-08-20 | HR payroll and salary withholding | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:146 | #1158 | `83ee74422b` | 2026-08-28 | Packaging and config | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:147 | #1123 | `ed9c4d3bbb` | 2026-08-28 | Order Form + Product Return Order + HR payroll and salary withholding + Manufacturing reports | PORT | PR net change (-m 1); held-back paths -> c1-hooks-patches-pyproject, c2-order-family, c4-product-return | `7f39ed4` `083c594` `48639f4` `87d5e26` |
| kggk:148 | #1172 | `7d75d56425` | 2026-08-31 | Sales and HR reports | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:149 | #1170 | `63b1bbcd8c` | 2026-08-31 | Fixtures | PORT | PR net change (-m 1) (empty) | `26bfda3` |
| kggk:150 | #1175 | `440dc086d6` | 2026-08-31 | HR employee lifecycle | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:151 | #1176 | `e699b95344` | 2026-08-31 | Manufacturing reports | PORT | PR net change (-m 1) | `fc388a1` `fe31a17` |
| kggk:152 | #1182 | `624b695fff` | 2026-09-01 | Sales and HR reports | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:153 | #1185 | `177ca4bdd1` | 2026-09-02 | Manufacturing reports | PORT | PR net change (-m 1); held-back paths -> c1-hooks-patches-pyproject | `a03131d` `083c594` |
| kggk:154 | #1191 | `dd4aa34012` | 2026-09-05 | Manufacturing reports | PORT | PR net change (-m 1) | `00d6da5` `fe31a17` |
| kggk:155 | #1203 | `d090a12db4` | 2026-09-06 | Manufacturing reports | SKIP_UNRELATED | PR net change (-m 1) | `3a509ec` `fe31a17` |
| kggk:156 | #1205 | `3c6741b515` | 2026-09-06 | Manufacturing reports | SKIP_UNRELATED | PR net change (-m 1) | `5533247` `fe31a17` |
| kggk:157 | #1209 | `ed98efe701` | 2026-09-07 | HR attendance and punches | PORT | leaf x1 | `e168048` |
| kggk:158 | #1208 | `50145bd6f9` | 2026-09-07 | HR payroll and salary withholding | PORT | leaf x1; held-back paths -> c1-hooks-patches-pyproject | `bcbe1c3` `083c594` |
| kggk:159 | #1194 | `3629b4c6bc` | 2026-09-07 | Material Request transfer to department | PORT | leaf x1 (1 empty) | `26bfda3` |
| kggk:160 | #1217 | `e2b103762d` | 2026-09-08 | Manufacturing reports | PORT | PR net change (-m 1) | `6f32e00` `fe31a17` |
| kggk:161 | #1224 | `d1c7fe32d8` | 2026-09-09 | Manufacturing reports | SKIP_UNRELATED | PR net change (-m 1) | `a850c8f` `fe31a17` |
| kggk:162 | #1229 | `35e21d2eba` | 2026-09-10 | Stock and inventory reports | PORT | PR net change (-m 1) | `2f531e0` |
| kggk:163 | #1235 | `fc4caf290e` | 2026-09-11 | Manufacturing Operation naming | PORT | leaf x1 | `8c59e22` |
| kggk:164 | #1240 | `d55b2445ba` | 2026-09-11 | HR attendance and punches | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:165 | #1255 | `e986264cdb` | 2026-09-14 | Manufacturing reports | PORT | PR net change (-m 1) | `13559f5` |
| kggk:166 | #1272 | `92071f775c` | 2026-09-16 | HR overtime | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:167 | #1278 | `3d05870fd3` | 2026-09-18 | Nova Glow rename | PORT | leaf x1; held-back paths -> c3-pricing-sales-hooks | `e0e6adb` `ed24d61` |
| kggk:168 | #1280 | `3ec2f3376d` | 2026-09-18 | Nova Glow rename | SKIP_REVERTED | skip | — |
| kggk:169 | #1283 | `c1f7ed5f7b` | 2026-09-18 | Nova Glow rename | SKIP_REVERTED | skip | — |
| kggk:170 | #1288 | `e0b01c1f35` | 2026-09-20 | Product Return Order | PORT | PR net change (-m 1) (empty); held-back paths -> c2-order-family, c3-pricing-sales-hooks, c4-product-return | `48639f4` `ed24d61` `87d5e26` |
| kggk:171 | #1293 | `a264410c5b` | 2026-09-21 | Manufacturing reports | PORT | PR net change (-m 1) | `8b4e46d` |
| kggk:172 | #1297 | `98ec5fbcad` | 2026-09-21 | HR misc | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:173 | #1328 | `9f631325a5` | 2026-09-26 | Sales and HR reports | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:174 | #1335 | `cc654ee00a` | 2026-09-27 | HR overtime | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:175 | #1350 | `361835e1ad` | 2026-09-30 | HR attendance and punches | SKIP_ALREADY_IN_MASTER | skip | — |
| kggk:176 | #1357 | `e7f8cf3fcb` | 2026-09-30 | HR attendance and punches | PORT | leaf x1 (1 empty); held-back paths -> c6-hrms | `be0c216` |
| kggk:177 | #1360 | `3d6c61ac92` | 2026-10-01 | Manufacturing reports | PORT | PR net change (-m 1) | `c9c77f4` |
| gkp:1 | #1356 | `20d3c28c8c` | 2026-09-30 | Catalogue portal and APIs | PORT | leaf x3 (3 empty); held-back paths -> c6-hrms, c7-catalogue-survey | `be0c216` `dd838b8` |
| gkp:2 | #1358 | `c94f0475c5` | 2026-09-30 | HR attendance and punches | SKIP_ALREADY_IN_MASTER | skip | — |
