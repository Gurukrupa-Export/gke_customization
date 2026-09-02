# Manufacturing Plan → KGGK testing push

This package pushes a submitted Manufacturing Plan's **subcontracting** items and their
BOMs to a **separate testing site**, so the flow can be exercised with real production data
without touching production.

## There are two syncs on this bench. This is not the other one.

| | Live Item/BOM sync | This package |
|---|---|---|
| Code | `doc_events/item.py` | `doc_events/kggk_sync/` + `doc_events/manufacturing_plan.py` |
| Trigger | `before_validate` on Item and BOM | Manufacturing Plan `on_submit`, plus a button |
| Target | `to_site` | `testing_site` |
| Credentials | `api_key` / `api_secret` | `testing_api_key` / `testing_api_secret` |
| Switch | none — always on | `enable_testing_sync`, **off by default** |

They share only the *Data Migration in KGGK* settings screen. Nothing here reads the live
sync's fields, and nothing here changes its behaviour. If you are debugging why an Item did
not reach the live KGGK site, this package is not involved.

## Turning it on

On **Data Migration in KGGK**, under *Manufacturing Plan Testing Sync*:

1. Tick **Send Manufacturing Plan Data to Testing Site**. While this is off, nothing is
   sent — not by submit, and not by the button, which is not even offered.
2. **Testing Site** — full base URL of the target, e.g. `https://kggk-test.example.com`.
3. **Testing API Key** / **Testing API Secret** — an API user *on the testing site*.

The secret is a Password field, so it lives in `__Auth` rather than in the Singles table.
It is read with `get_decrypted_password`; reading it with `frappe.db.get_value` would return
`*****` and every push would 401 in a way that looks like a mistyped key.

## What gets pushed

Rows of `manufacturing_plan_table` where `subcontracting` is ticked, contributing:

- `item_code` → Item
- `manufacturing_bom` → BOM

`manufacturing_bom`, not `row.bom`. `row.bom` is the Sales Order BOM; `manufacturing_bom` is
the one the plan makes mandatory on a subcontracting row, prices, and hands to the Purchase
Order. Items go before BOMs, across chunks as well as within one, because a BOM cannot
validate on the target without its finished-goods item.

## The guards

`get_sync_config()` refuses, with a reason, when:

- the switch is off;
- **Testing Site** or its credentials are blank;
- the testing site **is this site** — a Single travels with a database restore, so a clone
  arrives already configured to push into itself. Not bypassable;
- the testing site **is the live `to_site`** — pasting the production URL into the testing
  field would put several hundred items and BOMs into production KGGK on one submit.

## Where errors go

**One Error Log on the target site, per chunk, only when something went wrong.** A clean run
writes nothing anywhere — no news is good news. Reporting per record would mean hundreds of
POSTs, each with its own retries, at exactly the moment the target is least able to answer.

Four kinds, and they need different fixes:

| Kind | Means | Fix |
|---|---|---|
| `FIELD-MISSING` | the field does not exist on the target | add the Custom Field there |
| `LINK-MISSING` | an optional Link's target record is absent; the field was dropped | create the master there |
| `FAILED` | a required Link was absent, or the target rejected the record | read the message |
| `SCHEMA-UNKNOWN` | we could not read the target's own field list | check connectivity and the API user's permissions |
| `LINK-UNKNOWN` | the existence check itself failed; the value was sent anyway | as above |

`SCHEMA-UNKNOWN` matters more than it looks. When it appears, everything was sent and the
target was left to decide — so that run **cannot** tell you which fields are missing. It is
not the same answer as "nothing is missing".

If the Error Log POST itself fails, the report is written locally instead, clearly labelled
`FALLBACK`. That needs the API user on the target to hold **create on Error Log**; without
it every report quietly ends up in the local log where nobody is looking.

## Things that will bite

- **Ping-pong.** `frappe.flags.in_kggk_sync` does not cross HTTP. If the testing site also
  has `gke_customization` installed with a `to_site` of its own, everything posted to it
  fires *its* `before_validate` hooks and it pushes onward. Check the testing site's own
  settings before the first run.
- **Link checks, not pushes, are the volume.** Every Link field value is checked against the
  target. `run.link_cache` is per chunk, so low-cardinality links cost one GET per chunk, but
  `variant_of` is near-unique per item and does not cache usefully.
- **Nothing is recorded on the Item or BOM.** By design — this must add no fields to live
  doctypes. There is therefore no "already synced" state and no way to push "only what has
  not gone yet"; a re-push sends everything and lets the target decide create vs update.
