"""Revert "Nova Glow" → "Close" and "Nova Glow Setting" → "Close Setting" in-place.

This undoes the database half of commit 2696ca6a (merged as 404ac348), which was applied
by `v15_rename_close_setting_to_nova_glow.py`. The app-code half (hardcoded "Nova Glow"
literals in catalogue_api*.py, cad_report.js/py, gke_order_forms/doc_events/item.py,
targets_form.js, retailer_survey.json) is reverted in the same change.

Hierarchy restored:
  Attribute Value "Close" (is_setting_type=1)
    └── Attribute Value "Close Setting" (is_sub_setting_type=1,
                                         parent_attribute_value="Close", abbreviation="CS")

Plus every doctype record whose setting/sub-setting string column holds the new value, the
`Item Attribute Value` option lists, the `Attribute Value` child tables orphaned by the
master rename, and `Item Variant Attribute` rows written while the UI said "Nova Glow".

=============================== RAW SQL ONLY — DO NOT "SIMPLIFY" ==============================
Every write here is raw SQL on purpose. Never rewrite this to use the Document API on
`Item Attribute`:

    erpnext/stock/doctype/item_attribute/item_attribute.py  ItemAttribute.on_update()
      → erpnext/controllers/item_variant.py update_variant_item_codes_for_abbr_renames()
        → rename_variant_item_code() → frappe.rename_doc("Item", ...)  for EVERY variant

Changing `abbr` from 'NG' back to 'CL'/'CS' through `doc.save()` would mass-rename Items
inside a `bench migrate` — a multi-hour, non-atomic operation on production. Raw SQL leaves
no document diff, so the rename detection in item_variant.py never fires. That is intended.
==============================================================================================

Abbreviations: the forward patch overwrote `abbr`/`abbreviation` with 'NG' without recording
the previous values, and nothing in the repo retains them. The originals below were supplied
by the team. They are module constants so they are trivial to correct — verify against a
pre-2026-09-08 backup before running on production:

    SELECT parent, attribute_value, abbr FROM `tabItem Attribute Value`
    WHERE parent IN ('Setting Type','Sub Setting Type','Sub Setting Type1','Sub Setting Type2');
    SELECT attribute_value, abbreviation FROM `tabAttribute Value`
    WHERE is_setting_type = 1 OR is_sub_setting_type = 1;

Do NOT use the ROLLBACK recipe in the forward patch's docstring. It is wrong in both
directions: it clears `abbreviation` on the *parent* row (which the forward patch never
touched) and leaves 'NG' on the *sub* row (which it did).

Idempotency: guarded by a `tabDefaultValue` sentinel (`nova_glow_to_close_setting_revert_v1`)
in addition to Frappe's own Patch Log. Every statement is an exact-match rewrite, so
re-running is a no-op and a mid-way crash is recoverable.

The forward patch's sentinel (`close_setting_to_nova_glow_v2`) is deliberately LEFT IN PLACE.
It means "v15 has been applied once; never apply it again", which is still true and is
exactly the guard we want. Deleting it would re-arm the forward rename on any site where the
Patch Log row later goes missing (partial restores, cross-site DB copies).

Operator checklist:
  1. Take a backup.
  2. Restore a copy and run `report_leftovers()` there to size the blast radius.
  3. Confirm the abbreviations (see query above).
  4. Run in a maintenance window — most target columns are unindexed, so each UPDATE is a
     full scan holding row locks, all inside one transaction.
  5. Run `report_leftovers()` again afterwards; expect hits only in history tables.
"""

import frappe
from frappe.utils import cint

SENTINEL = "nova_glow_to_close_setting_revert_v1"

# Forward patch's sentinel. Read-only here — see the module docstring.
V15_SENTINEL = "close_setting_to_nova_glow_v2"

OLD_SETTING_TYPE = "Nova Glow"
NEW_SETTING_TYPE = "Close"
OLD_SUB_SETTING = "Nova Glow Setting"
NEW_SUB_SETTING = "Close Setting"

# Restored `tabAttribute Value`.abbreviation for the sub-setting row. The forward patch set
# this to 'NG'; it never touched the parent row's abbreviation, so neither do we.
RESTORE_SUB_ABBREVIATION = "CS"

# Restored `tabItem Attribute Value`.abbr, per Item Attribute.
ITEM_ATTR_PARENT = "Setting Type"
ITEM_ATTR_SUBS = ["Sub Setting Type", "Sub Setting Type1", "Sub Setting Type2"]
SETTING_ATTRIBUTES = [ITEM_ATTR_PARENT] + ITEM_ATTR_SUBS
RESTORE_PARENT_ABBR = "CL"
RESTORE_SUB_ABBR = "CS"

# Snapshot of DOCTYPE_COLUMNS from v15_rename_close_setting_to_nova_glow.py @ 2696ca6a,
# copied rather than imported: a patch that imports another patch breaks at import time —
# aborting every `bench migrate` — the moment the old patch is archived or renamed.
#
# Three tables are ADDED below that the forward patch missed. They carry real `setting_type`
# DocFields and were exposed to users for the whole Nova Glow window, so they can hold the
# new value even though the forward patch never wrote it there.
DOCTYPE_COLUMNS = {
    # ---- Parent + sub setting tables ----
    "Item": ["setting_type", "sub_setting_type", "custom_old_sub_setting_type"],
    "BOM": ["setting_type", "sub_setting_type1", "sub_setting_type2"],
    "Order": ["setting_type", "sub_setting_type1", "sub_setting_type2"],
    "Sketch Order": ["setting_type", "sub_setting_type1", "sub_setting_type2"],
    "Repair Order": ["setting_type", "sub_setting_type1", "sub_setting_type2"],
    "Order Form Detail": ["setting_type", "sub_setting_type1", "sub_setting_type2"],
    "CAD Order Form Detail": ["setting_type", "sub_setting_type1", "sub_setting_type2"],
    "Sketch Order Form Detail": ["setting_type", "sub_setting_type1", "sub_setting_type2"],
    "Repair Order Form Detail": ["setting_type", "sub_setting_type1", "sub_setting_type2"],
    "Parent Manufacturing Order": ["setting_type", "sub_setting_type"],
    "Manufacturing Work Order": ["setting_type", "sub_setting_type"],
    "Customer Order Form": ["setting_type", "setting_type_2"],
    "Sketch Order Form Category": ["setting_type", "sub_setting_type", "sub_setting_type2"],
    "Pre Order Form Details": ["setting_type", "bom_setting_type", "item_setting_type"],

    # ---- Parent-only setting tables ----
    "Making Charge Price": ["setting_type"],
    "Manufacturing Plan": ["setting_type"],
    "Product Return Order": ["setting_type"],
    "Serial No and Design Code Order": ["setting_type"],
    "Titan Design Information Sheet": ["setting_type"],
    "Revise Making Charge Price": ["setting_type"],
    "Serial No and Design Code Order Form Detail": ["setting_type"],
    # "Metal Ratio": ["setting_type"],  # no such doctype/table in DB
    "Product Return Form Item": ["setting_type"],
    # "Tracking Bom": ["setting_type"],  # no such doctype/table in DB
    "Exploded Product Details": ["setting_type"],
    "Final Sketch Approval CMO": ["setting_type"],
    "Customer Design Information Sheet": ["setting_type"],
    "Update Making Charge Price": ["setting_type"],
    "Old Style Bio Data": ["setting_type"],
    "Titan Order Form Details": ["setting_type"],
    "Quotation Item": ["setting_type"],
    "Sales Order Item": ["setting_type"],
    "Customer Order Form Detail": ["setting_type"],
    "Metal Labour Price": ["setting_type"],
    "Order Target Detail": ["setting_type"],
    "Reliance Cost Sheet": ["setting_type"],
    "Sketch Order Form Setting Type": ["setting_type"],
    # Missing from the forward patch entirely — real DocFields, verified in the live schema:
    "Bulk Order Detail": ["setting_type"],
    "Final Sketch Approval - Hold": ["setting_type"],
    "Final Sketch Approval CMO - Rejected": ["setting_type"],

    # ---- Sub-only setting tables ----
    "BOM Diamond Detail": ["sub_setting_type"],
    "BOM Gemstone Detail": ["sub_setting_type"],
    "Order BOM Diamond Detail": ["sub_setting_type"],
    "Order BOM Gemstone Detail": ["sub_setting_type"],
    # "Customer Setting Detail": ["gk_setting_type", "gk_sub_setting_type"],  # no such doctype/table in DB
    "MWO MOP Balance Table": ["sub_setting_type"],
    # "Stock Entry MOP Item": ["custom_sub_setting_type"],  # doctype exists, but column custom_sub_setting_type not in DB
    "SM Source Table": ["sub_setting_type"],
    "Manually Book Loss Details": ["sub_setting_type"],
    "SM Remain Balance Table": ["sub_setting_type"],
    "MOP Balance Table": ["sub_setting_type"],
    "SM Target Table": ["sub_setting_type"],
    "Employee Target Table": ["sub_setting_type"],
    "Employee Source Table": ["sub_setting_type"],
    "Department Target Table": ["sub_setting_type"],
    "Department Source Table": ["sub_setting_type"],
    "PMO Gemstone Table": ["sub_setting_type"],
    "SNC Source Table": ["sub_setting_type"],
    "SNC SFG Details": ["sub_setting_type"],
    "SNC FG Details": ["sub_setting_type"],
    "Employee Loss Details": ["sub_setting_type"],
    "Material Request Item": ["custom_sub_setting_type"],
    "Stock Entry Detail": ["custom_sub_setting_type"],
    "Product Return Order Diamond Detail": ["sub_setting_type"],
    "Product Return Order Gemstone Detail": ["sub_setting_type"],
}


def _log(message):
    """Log and print. `bench migrate` shows stdout; logger().debug is usually filtered out,
    which is why the forward patch's run left no record of what it changed."""
    print(f"{SENTINEL}: {message}")
    frappe.logger().info(f"{SENTINEL}: {message}")


def _rowcount():
    """Rows changed by the UPDATE that just ran.

    frappe.db.sql() returns () for an UPDATE — database.py bails out before fetchall() when
    the cursor has no description — so the forward patch's `if n:` logging was dead code.
    MariaDB connects without CLIENT.FOUND_ROWS, so rowcount is rows *changed*; for an
    exact-match rewrite changed == matched.
    """
    try:
        return frappe.db._cursor.rowcount or 0
    except Exception:
        return 0


def _sentinel_is_set() -> bool:
    row = frappe.db.sql(
        "select defvalue from tabDefaultValue where defkey = %s and parent = %s",
        (SENTINEL, "__default"),
    )
    return bool(row) and cint(row[0][0])


def _set_sentinel():
    frappe.db.sql(
        """
        insert into tabDefaultValue (name, parent, parenttype, defkey, defvalue)
        values (%(name)s, '__default', '__default', %(key)s, '1')
        on duplicate key update defvalue = '1'
        """,
        {"name": f"__default-{SENTINEL}", "key": SENTINEL},
    )
    # Defaults are cached at hash "defaults", field "__default". The forward patch used
    # frappe.cache.delete_value("__default"), which targets a key that does not exist.
    frappe.cache.hdel("defaults", "__default")


def _preflight_check() -> bool:
    """Return True if it is safe to proceed.

    `tabAttribute Value` has a unique key on `attribute_value` and a PK on `name`, and the
    collation is utf8mb4_unicode_ci (case- and trailing-space-insensitive). If both the old
    and new values are present, the rename raises error 1062 and rolls back the whole
    migrate, so refuse up front and say which rows collide.

    `tabItem Attribute Value` has NO unique key, so a same-parent duplicate would not error —
    it would silently create a second row that makes ItemAttribute.validate_duplication()
    throw on every later save. Check that too.

    No sentinel is set on failure, so a real conflict keeps resurfacing until it is resolved.
    """
    ok = True

    for old, new in ((NEW_SETTING_TYPE, OLD_SETTING_TYPE), (NEW_SUB_SETTING, OLD_SUB_SETTING)):
        if frappe.db.exists("Attribute Value", {"attribute_value": old}) and frappe.db.exists(
            "Attribute Value", {"attribute_value": new}
        ):
            _log(f"ABORT: both '{old}' and '{new}' exist in `tabAttribute Value` — resolve the duplicate first")
            ok = False

    dupes = frappe.db.sql(
        """
        select parent, count(distinct attribute_value) as n
        from `tabItem Attribute Value`
        where parent in %(parents)s and attribute_value in %(values)s
        group by parent
        having n > 1
        """,
        {
            "parents": tuple(SETTING_ATTRIBUTES),
            "values": (NEW_SETTING_TYPE, OLD_SETTING_TYPE, NEW_SUB_SETTING, OLD_SUB_SETTING),
        },
        as_dict=True,
    )
    for row in dupes:
        _log(
            f"ABORT: `tabItem Attribute Value` parent '{row.parent}' holds both old and new "
            f"values — reverting would create a duplicate option row"
        )
        ok = False

    return ok


def execute():
    if _sentinel_is_set():
        _log("sentinel set, already applied — skipping")
        return

    if not _preflight_check():
        return

    _revert_attribute_value_masters()
    _reparent_child_tables()
    _revert_item_attribute_values()
    _revert_item_variant_attributes()

    total = 0
    for doctype, columns in DOCTYPE_COLUMNS.items():
        for col in columns:
            total += _apply_column_replacements(doctype, col)

    _set_sentinel()

    # One call, not a 58-iteration frappe.clear_cache(doctype=...) loop: that loop cannot
    # raise on missing doctypes, but it costs ~4 queries each for no benefit.
    frappe.clear_cache()

    _log(
        f"reverted '{OLD_SETTING_TYPE}'→'{NEW_SETTING_TYPE}' and "
        f"'{OLD_SUB_SETTING}'→'{NEW_SUB_SETTING}': {total} rows across "
        f"{len(DOCTYPE_COLUMNS)} doctypes"
    )
    _report_affected_item_codes()

    # No frappe.db.commit() — patch_handler commits the data, the Patch Log row and the
    # sentinel together. Committing here would break that atomicity.


def _revert_attribute_value_masters():
    """Rename the Attribute Value master rows back.

    Order matters. Children are re-pointed FIRST, keyed off the value that is still current,
    so nothing can be missed once the parent row changes name. The two renames afterwards
    cannot collide with each other ('Close' != 'Close Setting').
    """
    # 1. Re-point every child, not just the one sub-setting row. The forward patch filtered
    #    on attribute_value='Close Setting', so any other child of the renamed parent
    #    (sibling sub-settings, subcategories) is currently dangling. This heals them.
    frappe.db.sql(
        "UPDATE `tabAttribute Value` SET `parent_attribute_value` = %s WHERE `parent_attribute_value` = %s",
        (NEW_SETTING_TYPE, OLD_SETTING_TYPE),
    )
    _log(f"re-pointed {_rowcount()} child rows to parent_attribute_value='{NEW_SETTING_TYPE}'")

    # 2. Sub-setting row: name, attribute_value and abbreviation (the forward patch set 'NG').
    #    Attribute Value autonames as field:attribute_value, so `name` must move with it.
    frappe.db.sql(
        "UPDATE `tabAttribute Value` SET `name` = %s, `attribute_value` = %s, `abbreviation` = %s "
        "WHERE `attribute_value` = %s AND `is_sub_setting_type` = 1",
        (NEW_SUB_SETTING, NEW_SUB_SETTING, RESTORE_SUB_ABBREVIATION, OLD_SUB_SETTING),
    )
    _log(f"renamed sub-setting master ({_rowcount()} rows), abbreviation={RESTORE_SUB_ABBREVIATION!r}")

    # 3. Parent row: name and attribute_value ONLY. The forward patch never touched the
    #    parent's abbreviation, so writing it here would invent data.
    frappe.db.sql(
        "UPDATE `tabAttribute Value` SET `name` = %s, `attribute_value` = %s "
        "WHERE `attribute_value` = %s AND `is_setting_type` = 1",
        (NEW_SETTING_TYPE, NEW_SETTING_TYPE, OLD_SETTING_TYPE),
    )
    _log(f"renamed parent setting master ({_rowcount()} rows)")


def _attribute_value_child_tables():
    """Child doctypes of Attribute Value, from metadata rather than a hardcoded list."""
    rows = frappe.db.sql(
        """
        select distinct parent as dt from `tabDocField`
        where fieldtype in ('Table', 'Table MultiSelect') and options = 'Attribute Value'
        union
        select distinct dt from `tabCustom Field`
        where fieldtype in ('Table', 'Table MultiSelect') and options = 'Attribute Value'
        """,
        as_dict=True,
    )
    return [r.dt for r in rows if r.dt]


def _reparent_child_tables():
    """Renaming the master's `name` orphaned every child row keyed by `parent`."""
    for child in _attribute_value_child_tables():
        if "`" in child or not frappe.db.table_exists(child):
            continue
        moved = 0
        for old, new in ((OLD_SETTING_TYPE, NEW_SETTING_TYPE), (OLD_SUB_SETTING, NEW_SUB_SETTING)):
            frappe.db.sql(
                f"UPDATE `tab{child}` SET `parent` = %s WHERE `parenttype` = 'Attribute Value' AND `parent` = %s",
                (new, old),
            )
            moved += _rowcount()
        if moved:
            _log(f"re-parented {moved} rows in `tab{child}`")


def _revert_item_attribute_values():
    """Revert the Item Attribute option lists (value + abbr) for the setting attributes."""
    attr_names = frappe.get_all(
        "Item Attribute",
        filters={"attribute_name": ["in", SETTING_ATTRIBUTES]},
        pluck="name",
    )

    for attr_name in attr_names:
        if attr_name == ITEM_ATTR_PARENT:
            old, new, abbr = OLD_SETTING_TYPE, NEW_SETTING_TYPE, RESTORE_PARENT_ABBR
        else:
            old, new, abbr = OLD_SUB_SETTING, NEW_SUB_SETTING, RESTORE_SUB_ABBR

        frappe.db.sql(
            """
            UPDATE `tabItem Attribute Value`
            SET `attribute_value` = %s, `abbr` = %s
            WHERE `parent` = %s AND `attribute_value` = %s
            """,
            (new, abbr, attr_name, old),
        )
        n = _rowcount()
        if n:
            _log(f"Item Attribute '{attr_name}': '{old}'→'{new}', abbr={abbr!r} ({n} rows)")


def _revert_item_variant_attributes():
    """Revert variant attribute rows written while the UI offered 'Nova Glow'.

    The forward patch never touched this table, so rows that predate it already say 'Close'
    and need nothing. Rows created during the Nova Glow window would fail
    validate_item_attribute_value() after the revert (Item Variant Settings has
    allow_rename_attribute_value = 0), so they must move back. Scoped to the setting
    attributes so unrelated attributes are untouched.
    """
    if not frappe.db.table_exists("Item Variant Attribute"):
        return

    for old, new in ((OLD_SETTING_TYPE, NEW_SETTING_TYPE), (OLD_SUB_SETTING, NEW_SUB_SETTING)):
        frappe.db.sql(
            """
            UPDATE `tabItem Variant Attribute`
            SET `attribute_value` = %(new)s
            WHERE `attribute` in %(attrs)s AND `attribute_value` = %(old)s
            """,
            {"new": new, "old": old, "attrs": tuple(SETTING_ATTRIBUTES)},
        )
        n = _rowcount()
        if n:
            _log(f"Item Variant Attribute: '{old}'→'{new}' ({n} rows)")


def _apply_column_replacements(doctype, col) -> int:
    """Run both exact replacements on a single column, if it exists on this site."""
    try:
        if not frappe.db.table_exists(doctype) or not frappe.db.has_column(doctype, col):
            return 0
    except Exception as e:
        frappe.logger().debug(f"{SENTINEL}: skipping {doctype}.{col} due to error {e}")
        return 0

    changed = 0
    for old, new in ((OLD_SETTING_TYPE, NEW_SETTING_TYPE), (OLD_SUB_SETTING, NEW_SUB_SETTING)):
        frappe.db.sql(f"UPDATE `tab{doctype}` SET `{col}` = %s WHERE `{col}` = %s", (new, old))
        n = _rowcount()
        if n:
            _log(f"{doctype}.{col} '{old}'→'{new}' ({n} rows)")
            changed += n

    return changed


def _report_affected_item_codes():
    """Read-only. Items whose item_code has the 'NG' abbreviation baked in.

    make_variant_item_code() returns early when item_code is already set, and nothing
    auto-renames items on save, so restoring the abbr only affects NEW variants. Items minted
    during the Nova Glow window keep '-NG' in their code permanently. Renaming them is a
    business decision — report, never rename (see the RAW SQL note at the top).
    """
    try:
        rows = frappe.db.sql(
            """
            select distinct i.name, i.item_code
            from `tabItem` i
            join `tabItem Variant Attribute` iva on iva.parent = i.name
            where iva.attribute in %(attrs)s and i.item_code like %(pattern)s
            limit 50
            """,
            {"attrs": tuple(SETTING_ATTRIBUTES), "pattern": "%-NG%"},
            as_dict=True,
        )
    except Exception as e:
        frappe.logger().debug(f"{SENTINEL}: item code report skipped: {e}")
        return

    if rows:
        _log(
            f"{len(rows)} item(s) carry the 'NG' abbreviation in their item_code and were NOT "
            f"renamed (business decision). Sample: {', '.join(r.item_code for r in rows[:10])}"
        )


# ---------------------------------------------------------------------------------------
# Standalone verification helper. NOT called by execute().
#
#   bench --site <site> console
#   >>> from gke_customization.patches.v1_0.v15_revert_nova_glow_to_close_setting import report_leftovers
#   >>> report_leftovers()
# ---------------------------------------------------------------------------------------

LEFTOVER_VALUES = (OLD_SETTING_TYPE, OLD_SUB_SETTING)

# Framework columns that can never hold a setting type.
_SKIP_COLUMNS = {
    "name", "owner", "modified_by", "parent", "parentfield", "parenttype",
    "_user_tags", "_comments", "_assign", "_liked_by", "idx",
}

# History/metadata tables. These SHOULD still say "Nova Glow" — rewriting them would be
# falsifying an audit trail, and the metadata ones are regenerated from JSON on migrate.
_HISTORY_TABLES = {
    "tabVersion", "tabPatch Log", "tabError Log", "tabActivity Log", "tabAccess Log",
    "tabView Log", "tabRoute History", "tabEmail Queue", "tabCommunication",
    "tabNotification Log", "tabScheduled Job Log", "tabPrepared Report",
    "tabDocField", "tabCustom Field", "tabProperty Setter",
}

_TEXT_TYPES = {"text", "tinytext", "mediumtext", "longtext"}


def report_leftovers(include_history=False, sample=5, verbose=True):
    """Scan the whole database for any column still holding 'Nova Glow'/'Nova Glow Setting'.

    Returns {table: {column: count}}. Scans per table rather than per column — one OR'd,
    short-circuiting probe each — so clean tables cost one scan and most cost nothing.
    """
    candidates = {}
    for row in frappe.db.sql(
        """
        select table_name as tbl, column_name as col, data_type as dt
        from information_schema.columns
        where table_schema = database()
          and data_type in ('varchar','char','text','tinytext','mediumtext','longtext')
          and (character_maximum_length is null or character_maximum_length >= %s)
        order by table_name, column_name
        """,
        (len(OLD_SUB_SETTING),),
        as_dict=True,
    ):
        if row.col in _SKIP_COLUMNS or "`" in row.tbl or "`" in row.col:
            continue
        if not include_history and row.tbl in _HISTORY_TABLES:
            continue
        candidates.setdefault(row.tbl, []).append((row.col, row.dt))

    found = {}
    total = len(candidates)
    for i, (tbl, cols) in enumerate(sorted(candidates.items()), 1):
        if verbose and i % 100 == 0:
            print(f"  scanned {i}/{total} tables...")
        try:
            # Skip empty tables. information_schema.tables.table_rows is an InnoDB estimate
            # that reads 0 for small non-empty tables, so probe directly instead.
            if not frappe.db.sql(f"select 1 from `{tbl}` limit 1"):
                continue

            clauses = []
            for col, dt in cols:
                clauses.append(f"`{col}` in %(vals)s")
                if dt in _TEXT_TYPES:
                    # Catches values embedded in stored JSON (saved filters etc.)
                    clauses.append(f"`{col}` like %(like)s")
            probe = f"select 1 from `{tbl}` where {' or '.join(clauses)} limit 1"
            if not frappe.db.sql(probe, {"vals": LEFTOVER_VALUES, "like": f"%{OLD_SETTING_TYPE}%"}):
                continue

            # Positive: pinpoint the columns in a single pass.
            sums = ", ".join(f"sum(`{col}` in %(vals)s) as `{col}`" for col, _ in cols)
            counts = frappe.db.sql(
                f"select {sums} from `{tbl}`", {"vals": LEFTOVER_VALUES}, as_dict=True
            )[0]
            hits = {col: int(n) for col, n in counts.items() if n}
            if hits:
                found[tbl] = hits
                if verbose:
                    print(f"  {tbl}: {hits}")
                    for col in hits:
                        rows = frappe.db.sql(
                            f"select `name`, `{col}` from `{tbl}` where `{col}` in %(vals)s limit %(lim)s",
                            {"vals": LEFTOVER_VALUES, "lim": sample},
                        )
                        for r in rows:
                            print(f"      {col}: {r[0]} = {r[1]!r}")
        except Exception as e:
            if verbose:
                print(f"  {tbl}: skipped ({e})")

    if verbose:
        print(f"\n{len(found)} table(s) still hold {LEFTOVER_VALUES}." if found else "\nNo leftovers found.")
    return found
