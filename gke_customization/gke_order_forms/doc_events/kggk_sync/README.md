# KGGK Sync

One-way push of **Item** and **BOM** records from the GK site to the KGGK site.

Everything is configured on the **Data Migration in KGGK** screen. There is no log doctype
— status, counters and the migration log are fields on that same Single.

## How it hangs together

```
                      ┌──────────────────────────────────────────┐
  Item.on_update ─────┤                                          │
  BOM.on_update  ─────┤  enqueue_sync()  →  background job       │
  Manufacturing Plan ─┤                     sync_records()       │
    .on_submit        │                       ├─ push_item()     │
  "Sync Now" button ──┤                       └─ push_bom()      │
  "Retry Failed"    ──┤                                          │
  "Re-sync Since"   ──┘                                          │
                      └──────────────────────────────────────────┘
```

| Module | Responsibility |
|---|---|
| `config.py` | Settings, URL normalisation, **the site-identity guard** |
| `client.py` | Authenticated GET/PUT/POST against To Site, retry policy |
| `payload.py` | Schema-driven payload, target-field pre-flight |
| `files.py` | Uploads attachment binaries to the target |
| `selectors.py` | What counts as unsynced (including *stale*) |
| `push.py` | The pipeline; chunking and continuation |
| `log.py` | Run state, counters, the migration log |

## Installation

```bash
bench --site <site> migrate
```

Creates `custom_is_sync`, `custom_last_synced_on` and `custom_sync_error` on Item and BOM,
and carries the old Is Migrate flag across from the deprecated *Item Migration in KGGK*.

**Is Migrate ships off.** Turning the sync on is a deliberate act.

## Turning it on

1. Set **From Site** to this site's URL and **To Site** to the KGGK URL.
2. Set **API Key** / **API Secret** for a KGGK user with write access to Item, BOM and File.
3. Submit one small Manufacturing Plan, or press **Sync Now** with a limit of 5.
4. Read the **Migration Log**. Confirm the records look right on KGGK.
5. Only then tick **Is Migrate** for real traffic.

## The guards

Two separate checks, and they are not equally strict.

**Same-site — never bypassable.** The push is refused when `From Site` and `To Site`
resolve to the same host, *or* when `To Site` is this site. This is the defect that made a
GK site push into itself: the old code only checked that both fields were non-empty, never
that they differed, and a Single doctype travels with a database restore — so a clone
arrives already configured to push.

**Wrong-site — bypassable via `Ignore Site Identity Check`.** Refused when this site is not
`From Site`. Only tick the bypass when `host_name` is unset on the bench and the check
misfires. It has no effect on the same-site guard.

## Reading the log

```
2026-08-20 16:03:46 | OK       | Item | MU02403     | created
2026-08-20 16:03:46 | MISMATCH | Item | MU02403-001 | master_bom: BOM 'BOM-…-001' does not exist on target, field dropped
2026-08-20 16:03:46 | FAILED   | BOM  | BOM-…-003   | required master(s) missing on target - item: Item '…' does not exist
```

| Level | Meaning |
|---|---|
| `OK` | Created or updated on the target |
| `MISMATCH` | One field could not be sent; **the record still synced** |
| `FAILED` | The record did not sync. It stays unsynced and lands in Retry Failed |
| `SKIP` | The push was refused before it started — the reason is on the line |

A `MISMATCH` is informational. A `FAILED` needs action, usually creating a missing master
on the target and pressing **Retry Failed**.

## Behaviour worth knowing

**Optional links are dropped, mandatory ones block.** If `item_category` is missing on the
target, that one field is dropped and logged so the rest of the record still syncs. If
`BOM.item` is missing, the record is failed instead — a BOM without its item is not a
lesser BOM, it is a broken one.

**Templates go before variants.** A variant whose template is absent on the target triggers
the template's push first.

**Attachments are uploaded, not referenced.** An Attach field holds `/files/x.png`; the
bytes only exist here. Files over 25 MB are skipped and logged. Public files are uploaded
once per run and reused; private files are uploaded per document, because the target serves
them only to users with permission on the attached document.

**Large batches are chunked.** A real Manufacturing Plan on this data selects ~490 items and
~490 BOMs. Work runs `CHUNK_SIZE` records at a time and re-queues the remainder, so a
timeout costs one chunk rather than the whole run. Items always precede BOMs, across chunks
as well as within one.

**Updates propagate, including for records the hook scope would not have caught.**
A save reaches the target when the record is in the hook scope (`setting_type = Close`,
and for BOM `bom_type = Template`) **or** when it has been pushed before by any route.
That second clause matters: a Manufacturing Plan ignores the hook scope entirely — every
plan BOM is `bom_type = Manufacturing Process` (8,359 of them on current data) and plans
carry items of any setting type. Scope alone would push those once and let them drift on
the target forever, which is worse than never sending them: KGGK would show stale data
that looks current. BOM is submittable, so `on_update_after_submit` is wired to the same
handler — otherwise every post-submit edit would be missed.

**A record edited after syncing counts as unsynced again.** `selectors.is_synced` compares
`custom_last_synced_on` against `modified`, so a marker-only check cannot strand an edited
record.

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| Log says `SKIPPED: from_site equals to_site` | Same-site config | Correct To Site |
| Log says `not the configured From Site` | Restored clone, or `host_name` unset | Fix From Site, or tick Ignore Site Identity Check |
| `Is Migrate is off` | Master switch | Tick Is Migrate |
| Many `FAILED … required master(s) missing` | Masters absent on the target | Create them on KGGK, then Retry Failed |
| Status stuck on `Running` | Worker died mid-chunk | Check the RQ queue; press Sync Now to resume |
| Nothing queues on plan submit | No `subcontracting` rows, or all already synced | Use **Re-sync All Rows** on the plan |
| An edit on GK never reaches KGGK | Record out of hook scope and never pushed | Push it once (plan submit, or **Sync Now**); updates track from then on |
| A deletion or rename on GK is not mirrored | Not implemented — see below | Fix on the target by hand |

## Scope

The Item/BOM hooks push only `setting_type = "Close"` (and, for BOM, `bom_type = "Template"`)
— unchanged from the original implementation. The Manufacturing Plan path deliberately has
no such filter: it pushes whatever the subcontracting rows reference.

## Tests

```bash
bench --site <site> run-tests --doctype "Data Migration in KGGK"
```

45 tests, HTTP stubbed throughout. The guard tests are the regression net for the same-site
defect; `TestUpdatePropagation` is the net for plan-pushed records going stale.

## Dry run

```bash
bench --site <site> execute gke_customization.gke_order_forms.doc_events.kggk_sync.dry_run.run
bench --site <site> execute ...dry_run.run --kwargs "{'plan': 'MP-GEPL-2025-00405', 'limit': 5}"
```

Stands up a mock target in-process, pushes a few real records at it and prints what crossed
the wire, then rolls everything back — no markers set, settings restored. Use it to check
payload shape, ordering and the guards before touching the real KGGK site.

It is **not** a substitute for one real run: the mock accepts what real KGGK may reject.

## Not yet done

- **Never run against the real KGGK site.** All verification to date is against a stubbed
  target. Confirm item naming, field presence and `upload_file` permissions there first.
- `custom_catalogue_image` exists on the live site only — it is in no fixture and not on
  this bench. Confirm it exists on **both** sites or that image will be logged as a mismatch.
- The nightly drain `add_item_bom_to_kggk_by_schedule` is implemented but **not registered**
  in `scheduler_events`. Wire it only after a successful manual run.
- **Deletes and renames do not propagate.** Cancelling or deleting an Item or BOM on GK
  leaves it in place on KGGK, and renaming creates a second record there rather than
  renaming the first. Both are deliberate omissions — a sync that deletes on a remote
  production site needs its own decision — but they are real gaps to be aware of.
