"""Rename "Close" → "Nova Glow" and "Close Setting" → "Nova Glow Setting" in-place.

This renames the existing Attribute Values AND updates every doctype record that
references the old string values. The doctype columns store strings directly, not FKs
(most are varchar(140) Link→Attribute Value, but the stored value is the plain name).

Hierarchy:
  Attribute Value "Close" (is_setting_type=1)
    └── Attribute Value "Close Setting" (is_sub_setting_type=1, parent_attribute_value="Close")

After rename:
  Attribute Value "Nova Glow" (is_setting_type=1)
    └── Attribute Value "Nova Glow Setting" (is_sub_setting_type=1, parent_attribute_value="Nova Glow", abbreviation="NGS")

Plus: every doctype record whose setting/sub-setting string column holds the old value.

Column contract — every setting column is updated with BOTH exact replacements:
  * "Close"        → "Nova Glow"        (parent setting columns: setting_type, *_setting_type, bom_setting_type, item_setting_type, gk_setting_type)
  * "Close Setting" → "Nova Glow Setting" (sub-setting columns: sub_setting_type*, custom_sub_setting_type, custom_old_sub_setting_type, gk_sub_setting_type)
Exact equality means "Close-Open Setting" (a sibling sub-setting under "Open") is never matched.

v1 → v2: version 1 missed several tables/columns that carry these fields (notably
Quotation Item.setting_type, Sales Order Item.setting_type, plus Customer Order Form
Detail, Metal Labour Price, Order Target Detail, Pre Order Form Details (3 cols),
Reliance Cost Sheet, Sketch Order Form Setting Type, Sketch Order Form Category.setting_type,
Item.custom_old_sub_setting_type, Customer Setting Detail.gk_setting_type, Customer Order
Form.setting_type_2). The full list below was derived from information_schema, so it is
exhaustive and forward-correct. v2 re-runs on sites that already ran v1 (the v1 sentinel
is ignored); the Attribute Value rename and Item Attribute migration are idempotent.

Idempotency: guarded by a `tabDefaultValue` sentinel (`close_setting_to_nova_glow_v2`).
Re-running is a no-op. Pre-flight checks that the new Attribute Values don't already exist.

ROLLBACK (code revert plus):
    UPDATE `tabAttribute Value` SET `name`='Close', `attribute_value`='Close', `abbreviation`=NULL WHERE `attribute_value`='Nova Glow';
    UPDATE `tabAttribute Value` SET `name`='Close Setting', `attribute_value`='Close Setting', `parent_attribute_value`='Close' WHERE `attribute_value`='Nova Glow Setting';
    -- and for EVERY (doctype, column) in DOCTYPE_COLUMNS below:
    --   UPDATE `tab<doctype>` SET `<col>`='Close'          WHERE `<col>`='Nova Glow';
    --   UPDATE `tab<doctype>` SET `<col>`='Close Setting'  WHERE `<col>`='Nova Glow Setting';
    then `delete from tabDefaultValue where defkey = 'close_setting_to_nova_glow_v2'`
    and `frappe.clear_cache()`
"""

import frappe
from frappe.utils import cint

SENTINEL = "close_setting_to_nova_glow_v2"

OLD_SETTING_TYPE = "Close"
NEW_SETTING_TYPE = "Nova Glow"
OLD_SUB_SETTING = "Close Setting"
NEW_SUB_SETTING = "Nova Glow Setting"
NEW_SUB_ABBR = "NGS"

# Exhaustive map: every doctype that carries a setting string column, and all the
# columns on it. Parent ("Close") and sub ("Close Setting") columns are both listed;
# _apply_column_replacements runs both exact replacements on every column regardless.
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
    "Final Sketch Approval - Hold": ["setting_type"],
    "Final Sketch Approval CMO - Rejected": ["setting_type"],
    "Old Style Bio Data": ["setting_type"],
    "Titan Order Form Details": ["setting_type"],
    # Tables missed by v1 — these hold real 'Close' data in production:
    "Quotation Item": ["setting_type"],
    "Sales Order Item": ["setting_type"],
    # Tables missed by v1 — present but empty of 'Close'/'Close Setting' today:
    "Customer Order Form Detail": ["setting_type"],
    "Metal Labour Price": ["setting_type"],
    "Order Target Detail": ["setting_type"],
    "Reliance Cost Sheet": ["setting_type"],
    "Sketch Order Form Setting Type": ["setting_type"],

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
    frappe.cache.delete_value("__default")


def _preflight_check() -> bool:
    """Return True if safe to proceed.

    Only blocks on a genuine collision: the old master value still exists AND the new one
    already does — renaming would create a duplicate Attribute Value. On a site where v1
    already renamed the masters ('Close' is gone, 'Nova Glow' present), we must NOT block:
    v2 exists precisely to finish the data-column migration v1 missed. No sentinel is set
    on failure, so a real conflict keeps surfacing until it is resolved.
    """
    if frappe.db.exists("Attribute Value", {"attribute_value": OLD_SETTING_TYPE}) and frappe.db.exists(
        "Attribute Value", {"attribute_value": NEW_SETTING_TYPE}
    ):
        frappe.logger().error(f"{SENTINEL}: both '{OLD_SETTING_TYPE}' and '{NEW_SETTING_TYPE}' exist")
        return False
    if frappe.db.exists(
        "Attribute Value", {"attribute_value": OLD_SUB_SETTING}
    ) and frappe.db.exists("Attribute Value", {"attribute_value": NEW_SUB_SETTING}):
        frappe.logger().error(f"{SENTINEL}: both '{OLD_SUB_SETTING}' and '{NEW_SUB_SETTING}' exist")
        return False
    return True


def execute():
    if _sentinel_is_set():
        frappe.logger().info(f"{SENTINEL}: sentinel set, already applied — skipping")
        return

    if not _preflight_check():
        return

    _apply_rename_and_migrate()

    _set_sentinel()
    frappe.clear_cache(doctype="Attribute Value")
    for dt in DOCTYPE_COLUMNS:
        frappe.clear_cache(doctype=dt)

    frappe.logger().info(
        f"{SENTINEL}: renamed '{OLD_SETTING_TYPE}'→'{NEW_SETTING_TYPE}' and "
        f"'{OLD_SUB_SETTING}'→'{NEW_SUB_SETTING}' + migrated doctype records "
        f"across {len(DOCTYPE_COLUMNS)} doctypes"
    )


def _apply_rename_and_migrate():
    # ========== STEP 1: Rename Attribute Values (master data) ==========
    # NOTE: Attribute Value uses autoname: field:attribute_value, so we must update BOTH name and attribute_value

    # 1a. Rename parent setting_type "Close" → "Nova Glow" (update both name and attribute_value)
    frappe.db.sql(
        "UPDATE `tabAttribute Value` SET `name` = %s, `attribute_value` = %s "
        "WHERE `attribute_value` = %s AND `is_setting_type` = 1",
        (NEW_SETTING_TYPE, NEW_SETTING_TYPE, OLD_SETTING_TYPE),
    )

    # 1b. Update child's parent_attribute_value to point to new parent name
    frappe.db.sql(
        "UPDATE `tabAttribute Value` SET `parent_attribute_value` = %s "
        "WHERE `attribute_value` = %s AND `is_sub_setting_type` = 1",
        (NEW_SETTING_TYPE, OLD_SUB_SETTING),
    )

    # 1c. Rename sub_setting_type "Close Setting" → "Nova Glow Setting" and set abbreviation
    frappe.db.sql(
        "UPDATE `tabAttribute Value` SET `name` = %s, `attribute_value` = %s, `abbreviation` = %s "
        "WHERE `attribute_value` = %s AND `is_sub_setting_type` = 1",
        (NEW_SUB_SETTING, NEW_SUB_SETTING, NEW_SUB_ABBR, OLD_SUB_SETTING),
    )

    # ========== STEP 1b: Migrate Item Attribute option lists ==========
    _migrate_item_attribute_values()

    # ========== STEP 2: Migrate doctype records (data) ==========
    for doctype, columns in DOCTYPE_COLUMNS.items():
        for col in columns:
            _apply_column_replacements(doctype, col)

    # Single commit at the end — no mid-patch commit to avoid partial-failure deadlock
    frappe.db.commit()


def _apply_column_replacements(doctype, col):
    """Run both exact replacements on a single column, if it exists on this site."""
    if not frappe.db.has_column(doctype, col):
        frappe.logger().debug(f"{SENTINEL}: skipping {doctype}.{col} (no such column)")
        return

    # Parent setting: "Close" → "Nova Glow"
    n = frappe.db.sql(
        f"UPDATE `tab{doctype}` SET `{col}` = %s WHERE `{col}` = %s",
        (NEW_SETTING_TYPE, OLD_SETTING_TYPE),
    )
    if n:
        frappe.logger().debug(f"{SENTINEL}: {doctype}.{col} 'Close'→'Nova Glow' ({n} rows)")

    # Sub setting: "Close Setting" → "Nova Glow Setting"
    m = frappe.db.sql(
        f"UPDATE `tab{doctype}` SET `{col}` = %s WHERE `{col}` = %s",
        (NEW_SUB_SETTING, OLD_SUB_SETTING),
    )
    if m:
        frappe.logger().debug(
            f"{SENTINEL}: {doctype}.{col} 'Close Setting'→'Nova Glow Setting' ({m} rows)"
        )


def _migrate_item_attribute_values():
    """Migrate Item Attribute option lists for all setting-related attributes."""
    attr_names = frappe.get_all(
        "Item Attribute",
        filters={
            "attribute_name": [
                "in",
                [
                    "Setting Type",
                    "Sub Setting Type",
                    "Sub Setting Type1",
                    "Sub Setting Type2",
                ],
            ]
        },
        pluck="name",
    )

    for attr_name in attr_names:
        if attr_name == "Setting Type":
            frappe.db.sql(
                """
                UPDATE `tabItem Attribute Value`
                SET `attribute_value` = %s, `abbr` = %s
                WHERE `parent` = %s AND `attribute_value` = %s
                """,
                (NEW_SETTING_TYPE, "NG", attr_name, OLD_SETTING_TYPE),
            )
        else:
            frappe.db.sql(
                """
                UPDATE `tabItem Attribute Value`
                SET `attribute_value` = %s, `abbr` = %s
                WHERE `parent` = %s AND `attribute_value` = %s
                """,
                (NEW_SUB_SETTING, NEW_SUB_ABBR, attr_name, OLD_SUB_SETTING),
            )
