# 00 — Branch baseline

Pinned at the start of the reconstruction (2026-10-01, 14:03 IST) and re-checked before every stage and again before the push. Full SHAs are kept as `refs/recon/base/*` in the working clone (never pushed).

## Branch heads

| Branch | SHA | Last commit date | Author | Subject |
|---|---|---|---|---|
| `master` | `c867d348cd6b48974608acdf5d0c8f53f948f18e` | 2026-10-01 12:28 +0530 | Dhinesh | update order.py (#1363) |
| `kggk_prod` | `3d6c61ac921c74714c89e6619ab93a22ecbc25b2` | 2026-10-01 00:25 +0530 | Devendra Pandey | Sandepp v16 dummy (#1360) |
| `gurukrupa-prod` | `c94f0475c5d53a4ada2e546c910dcff4dfff5a07` | 2026-09-30 21:34 +0530 | Devendra Pandey | 30-09-2026 update in holiday punch py file (#1358) |
| `gk_prod` (created from master) | `c867d348cd6b48974608acdf5d0c8f53f948f18e` | same commit as master | | |

master gained three commits between planning and execution (the #1362 sync and #1363 `order.py`); `gk_prod` was cut from that newer head and pushed as an exact copy of it.

## Merge bases

| Pair | Merge base | Date |
|---|---|---|
| master ↔ kggk_prod | `b387f829248ef06cfd363d7eb5f4328f71420f40` | 2026-02-03 18:25 +0530 |
| master ↔ gurukrupa-prod | `b387f829248ef06cfd363d7eb5f4328f71420f40` | same commit |
| kggk_prod ↔ gurukrupa-prod | `cc654ee00ae302661be9d39d07cf3d6c00e4d477` | 2026-09-27 22:07 +0530 |

## Ahead / behind (at the pinned heads)

| Comparison | Ahead | Behind |
|---|---:|---:|
| kggk_prod vs master | 501 | 614 |
| gurukrupa-prod vs master | 500 | 614 |
| gurukrupa-prod vs kggk_prod | 6 | 7 |

The brief's figures (501/611, 500/611, 6/7) were confirmed at planning time; "behind" grew to 614 after master's three new commits.

## Shape of the divergence

- kggk_prod's 501 unique commits form **177 first-parent units** (170 PR merges + 7 direct commits); the remaining commits are the PRs' own branch commits. gurukrupa-prod adds **2 units** (6 commits) of its own. Every one of the **507** source commits belongs to exactly one unit.
- 127 of the PRs targeted `v16_develop_aerele`, 34 targeted `kggk_prod` and 9 targeted `develop_aerele`: kggk_prod is the Frappe/ERPNext v16 line.
- master is GK's v15 development line (its first-parent PRs come from `*-gkexport` developer branches). gk_prod therefore received a v16 compatibility audit of master-only code (see 07 and 08).
- No PR number is shared between the two sides; the same work often landed as separate PRs on each.

## Files, three-way (base = merge base)

| Class | Meaning | Files |
|---|---|---:|
| same | master and kggk_prod ended identical | 1301 |
| kggk-only | changed only on kggk_prod: replayed from production history | 346 |
| master-only | changed only on master: kept as master has them | 301 |
| both | changed on both sides: settled in consolidated three-way port commits | 54 |

## Replay

189 dry-run records over the 179 units (leaf picks 58, PR net changes `-m 1` 44, direct commits 6, skipped units 81): 71 produced commits, 37 were empty (their change was already in master, or lived only on paths master also changed and was carried by a consolidated port). Zero conflicts outside the held-back paths; every replayed commit's tree matched the simulation, and on every path master never touched the result is byte-identical to kggk_prod.
