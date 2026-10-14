"""Rename DocType "Revise Diamond Price  List" (two spaces) to "Revise Diamond Price List".

kggk_prod renamed this doctype in #825 by moving its folder from
revise_diamond_price__list/ to revise_diamond_price_list/, without a patch. On a site that
still has the old DocType (for example one that ran GK's v15 master line), the first
migrate on the renamed code would create an empty "Revise Diamond Price List" and then
delete the old DocType record as an orphan (frappe.model.sync.remove_orphan_doctypes).
Its documents would stay behind in the old table, its child rows under the old
parenttype and its Custom DocPerm rows on the old name.

Renaming before model sync carries all of that over instead: the table is renamed, and
child-table parenttype values, Link options and values (amended_from, Custom Field.dt,
Property Setter.doc_type, Client Script.dt, Workflow.document_type, ...) and Custom
DocPerm rows follow the new name. This patch must therefore be listed under
[pre_model_sync]; once model sync has created the new DocType it can only refuse.

frappe.rename_doc changes link values, never code. A Client Script of the old DocType
registers its handlers by name (frappe.ui.form.on("Revise Diamond Price  List", ...)), so
after the rename it would load for the new form but never attach. The old name is
therefore replaced by the new one in the script text of the Client Scripts that belonged
to the old DocType, as Frappe itself does for JS controllers when it renames a DocType.
Other code that still mentions the old name (Server Scripts, Client Scripts of other
DocTypes, Report queries and scripts, Print Formats, Notifications) is not changed, only
listed for manual review.

Safe to run on every site:
- old DocType absent (fresh installs, and sites that already migrated #825, such as GK
  live): nothing to do.
- new DocType or its table already present as well: raises before changing anything, so
  bench migrate stops before model sync and this patch stays pending. Returning would
  record it as done, and the same migrate would then delete the old DocType record as an
  orphan, leaving its documents without a DocType and the rename impossible (bench
  migrate --skip-failing has that effect too). The error lists both tables with their
  row counts. Reconcile them by hand and migrate again: once the new DocType and its
  table are gone this patch renames, and once the old DocType record is gone it does
  nothing.
"""

import frappe

OLD_DOCTYPE = "Revise Diamond Price  List"  # two spaces
NEW_DOCTYPE = "Revise Diamond Price List"

# Text fields that can hold code or queries naming a DocType. After a rename, rows that
# still mention the old name are reported for manual review and left unchanged.
REVIEW_FIELDS = (
    ("Client Script", ("script",)),
    ("Server Script", ("script",)),
    ("Report", ("query", "report_script", "javascript", "json")),
    ("Print Format", ("html", "format_data")),
    ("Notification", ("subject", "message", "condition")),
)

# Appended to the error raised when the new DocType or its table already exists.
RECONCILE_HELP = (
    "The new DocType or its table already exists, so the two have to be reconciled by "
    "hand. Either remove the new side: move any documents you need into the old table, "
    "then delete the new DocType record (with developer_mode off, or Frappe deletes "
    "its code too), its customizations and its table; this patch then renames the old "
    "DocType with its documents. Or remove the old side: move its documents and "
    "customizations to the new DocType, then delete the old DocType record; this patch "
    "then does nothing. Run bench migrate again afterwards.\n"
    "Do not use --skip-failing: the same migrate would then delete the old DocType "
    "record as an orphan, and the rename could not run afterwards."
)


def execute():
    if not frappe.db.exists("DocType", OLD_DOCTYPE):
        return

    if frappe.db.exists("DocType", NEW_DOCTYPE) or frappe.db.table_exists(
        NEW_DOCTYPE, cached=False
    ):
        # Refuse rather than skip: a patch that returns is logged as done, and later in
        # this migrate remove_orphan_doctypes would delete the old DocType record.
        frappe.throw(conflict_message(), title="DocType rename conflict")

    # Read before the rename moves their dt to the new name.
    client_scripts = frappe.get_all(
        "Client Script", filters={"dt": OLD_DOCTYPE}, pluck="name"
    )

    frappe.rename_doc(
        "DocType",
        OLD_DOCTYPE,
        NEW_DOCTYPE,
        force=True,
        show_alert=False,
        rebuild_search=False,
    )

    rekey_workflow_state_field()
    rename_in_client_scripts(client_scripts)
    report_remaining_references()


def conflict_message():
    lines = [f"Cannot rename DocType {OLD_DOCTYPE!r} to {NEW_DOCTYPE!r}."]
    for doctype in (OLD_DOCTYPE, NEW_DOCTYPE):
        record = "present" if frappe.db.exists("DocType", doctype) else "absent"
        if frappe.db.table_exists(doctype, cached=False):
            table = f"table `tab{doctype}` with {frappe.db.count(doctype)} rows"
        else:
            table = f"no table `tab{doctype}`"
        lines.append(f"- {doctype!r}: DocType record {record}, {table}.")
    lines.append(RECONCILE_HELP)
    return "\n".join(lines)


def rekey_workflow_state_field():
    # The rename moved the workflow_state custom field to the new dt but kept its
    # "{dt}-{fieldname}" name. Re-key it so a Workflow or fixture that writes
    # "Revise Diamond Price List-workflow_state" updates this row instead of
    # colliding with it.
    old_field = f"{OLD_DOCTYPE}-workflow_state"
    new_field = f"{NEW_DOCTYPE}-workflow_state"
    if frappe.db.exists(
        "Custom Field", {"name": old_field, "dt": NEW_DOCTYPE}
    ) and not frappe.db.exists("Custom Field", new_field):
        frappe.rename_doc(
            "Custom Field",
            old_field,
            new_field,
            force=True,
            show_alert=False,
            rebuild_search=False,
        )


def rename_in_client_scripts(names):
    changed = False
    for name in names:
        row = frappe.db.get_value("Client Script", name, ["dt", "script"], as_dict=True)
        if not row or row.dt != NEW_DOCTYPE or OLD_DOCTYPE not in (row.script or ""):
            continue

        frappe.db.set_value(
            "Client Script",
            name,
            "script",
            row.script.replace(OLD_DOCTYPE, NEW_DOCTYPE),
            update_modified=False,
        )
        print(f"Client Script {name!r}: replaced {OLD_DOCTYPE!r} with {NEW_DOCTYPE!r}.")
        changed = True

    if changed:
        # Client Script.on_update would do this; set_value bypasses the controller.
        frappe.clear_cache(doctype=NEW_DOCTYPE)


def report_remaining_references():
    for doctype, fields in REVIEW_FIELDS:
        if not frappe.db.table_exists(doctype):
            continue

        for field in fields:
            if not frappe.db.has_column(doctype, field):
                continue

            for name in frappe.get_all(
                doctype, filters={field: ("like", f"%{OLD_DOCTYPE}%")}, pluck="name"
            ):
                warn(
                    f"{doctype} {name!r} still mentions {OLD_DOCTYPE!r} in {field}. "
                    f"Update it to {NEW_DOCTYPE!r} by hand."
                )


def warn(message):
    print(message)
    frappe.logger().warning(message)
