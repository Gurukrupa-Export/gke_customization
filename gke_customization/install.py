"""
gke_customization install lifecycle.

THE PROBLEM, MEASURED
----------------------
A fresh `bench new-site` + `bench install-app gke_customization` + `bench migrate`
does not apply this app's own schema. The fields this app defines live in two
places that Frappe's own install flow does not reliably wire together on a
brand-new site:

1. `gke_customization/fixtures/custom_field.json` -- a standard Frappe fixture.
   It is only ever synced by `sync_fixtures()`, which Frappe's installer runs
   AFTER `after_install`, and `frappe.utils.fixtures.import_fixtures` wraps the
   ENTIRE FILE in one try/except that only catches ImportError/DoesNotExistError.
   The first record in the file whose Link/Table target doctype does not exist
   yet silently discards every record after it in that file.

2. `gke_customization/gke_customization/custom_fields/*.json` -- a split of the
   same fixture, one file per DocType, consumed explicitly by `provision_schema()`
   below via `create_custom_fields(..., update=False)`. This directory is not
   touched by Frappe's fixture sync at all; nothing calls into it unless this
   module's `after_install` hook does.

3. Patches are MARKED, not RUN, on a fresh install -- `set_all_patches_as_completed()`
   inserts a `Patch Log` row per `patches.txt` entry without importing the module.
   Any patch that creates schema (custom fields) therefore never runs on a new
   site unless explicitly invoked here.

PRESERVATION, NOT CONVERGENCE
------------------------------
`provision_schema()` always calls `create_custom_fields(..., update=False)`:
create-only, never overwrite. If a field already exists (e.g. restored from a
backup, or customized on-site), we leave it alone. Use `report_field_drift()`
to see what an `update=True` run would have changed, without changing anything.

ORDERING (load-bearing)
------------------------
`after_install` runs before `sync_fixtures` in frappe/installer.py, so
`provision_schema()` here creates the custom fields and runs schema-creating
patches with a clean field set. `after_sync` runs after fixtures/customizations/
dashboards are synced, so `after_sync()` here repairs any records that the
fixture importer's per-file try/except dropped out of
`fixtures/custom_field.json`.
"""

import json
import os

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "gke_customization", "custom_fields"
)

FIXTURE_CUSTOM_FIELD_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "fixtures", "custom_field.json"
)

_DOCTYPE_LINK_TYPES = ("Link", "Table", "Table MultiSelect")


def before_install():
    pass


def after_install():
    provision_schema()
    _run_schema_patches()


def after_sync():
    reconcile_own_fixtures()


# ---------------------------------------------------------------------------
# Schema provisioning
# ---------------------------------------------------------------------------


def provision_schema(verbose=True):
    """Create every custom field this app defines, skipping only fields whose
    Link/Table target doesn't exist yet, or whose dt/fieldname is claimed by
    another app's fixture under an incompatible `name`. Never overwrites an
    existing field.
    """
    applied, skipped, drift, deferred = 0, 0, {}, []

    if not os.path.isdir(CUSTOM_FIELDS_DIR):
        if verbose:
            print(
                f"gke_customization: no custom_fields dir at {CUSTOM_FIELDS_DIR}, skipping"
            )
        return applied, skipped, drift, deferred

    claimed = _pairs_a_fixture_claims_under_another_name()

    for fname in sorted(os.listdir(CUSTOM_FIELDS_DIR)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(CUSTOM_FIELDS_DIR, fname)
        try:
            with open(path) as f:
                spec = json.load(f)
        except (OSError, ValueError) as e:
            if verbose:
                print(f"gke_customization: could not read {path}: {e}")
            continue

        spec = _drop_fields_with_missing_targets(spec)
        usable, dropped = _drop_fields_claimed_by_a_fixture(spec, claimed)
        skipped += len(dropped)
        deferred.extend(dropped)

        if not any(usable.values()):
            continue

        drift.update(report_field_drift(usable))

        try:
            create_custom_fields(usable, ignore_validate=True, update=False)
            applied += sum(len(v) for v in usable.values())
        except Exception as e:
            frappe.log_error(
                title="gke_customization.provision_schema",
                message=f"Failed applying {fname}: {e}",
            )
            if verbose:
                print(f"gke_customization: failed applying {fname}: {e}")

    if verbose:
        print(
            f"gke_customization.provision_schema: applied={applied} skipped={skipped} "
            f"drift_fields={len(drift)} deferred={len(deferred)}"
        )

    return applied, skipped, drift, deferred


def report_field_drift(spec):
    """Read-only: report which keys differ between `spec` and what already
    exists on site, for fields that already exist. Writes nothing.
    """
    existing = get_existing_custom_fields(spec)
    drift = {}
    for dt, fields in spec.items():
        for df in fields:
            key = (dt, df.get("fieldname"))
            current = existing.get(key)
            if not current:
                continue
            diffs = {
                k: (current.get(k), v)
                for k, v in df.items()
                if k not in ("dt", "fieldname") and current.get(k) != v
            }
            if diffs:
                drift[key] = diffs
    return drift


def get_existing_custom_fields(spec):
    existing = {}
    for dt, fields in spec.items():
        fieldnames = [df.get("fieldname") for df in fields]
        if not fieldnames:
            continue
        rows = frappe.get_all(
            "Custom Field",
            filters={"dt": dt, "fieldname": ["in", fieldnames]},
            fields=["fieldname"]
            + list({k for df in fields for k in df.keys() if k not in ("dt",)}),
        )
        for row in rows:
            existing[(dt, row["fieldname"])] = row
    return existing


def _drop_fields_with_missing_targets(spec):
    """Drop fields whose Link/Table/Table MultiSelect `options` target
    doctype belongs to an app that isn't installed. A doctype with no
    schema file anywhere is assumed fixture-only and kept.
    """
    cleaned = {}
    for dt, fields in spec.items():
        if _target_belongs_to_an_uninstalled_app(dt):
            continue
        keep = []
        for df in fields:
            if df.get("fieldtype") in _DOCTYPE_LINK_TYPES:
                target = df.get("options")
                if target and _target_belongs_to_an_uninstalled_app(target):
                    continue
            keep.append(df)
        if keep:
            cleaned[dt] = keep
    return cleaned


def _target_belongs_to_an_uninstalled_app(doctype):
    installed = set(frappe.get_installed_apps())
    scrubbed = frappe.scrub(doctype)
    apps_dir = (
        frappe.get_app_path("frappe")
        .rsplit(os.sep + "frappe", 1)[0]
        .rsplit(os.sep, 1)[0]
    )
    try:
        bench_apps = os.listdir(apps_dir)
    except OSError:
        return False

    for app in bench_apps:
        if app in installed:
            continue
        schema_path = os.path.join(
            apps_dir, app, app, scrubbed, scrubbed, scrubbed + ".json"
        )
        folder_path = os.path.join(apps_dir, app, app, scrubbed)
        if os.path.isfile(schema_path) or os.path.isdir(folder_path):
            return True
    return False


def _pairs_a_fixture_claims_under_another_name():
    """Scan every installed-or-on-disk app's fixtures/*.json for Custom Field
    records whose `name` differs from f"{dt}-{fieldname}" (CustomField.autoname
    would rename them on insert, risking a collision with our own record).
    Returns a set of (dt, fieldname) pairs to withhold from provisioning.
    """
    claimed = set()
    apps_dir = (
        frappe.get_app_path("frappe")
        .rsplit(os.sep + "frappe", 1)[0]
        .rsplit(os.sep, 1)[0]
    )
    try:
        apps = os.listdir(apps_dir)
    except OSError as e:
        print(f"gke_customization: could not list {apps_dir}: {e}")
        return claimed

    for app in apps:
        fixtures_dir = os.path.join(apps_dir, app, app, "fixtures")
        if not os.path.isdir(fixtures_dir):
            continue
        for fname in os.listdir(fixtures_dir):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(fixtures_dir, fname)) as f:
                    data = json.load(f)
            except (OSError, ValueError):
                continue
            records = data if isinstance(data, list) else [data]
            for record in records:
                if record.get("doctype") != "Custom Field":
                    continue
                dt, fieldname = record.get("dt"), record.get("fieldname")
                if not dt or not fieldname:
                    continue
                expected_name = f"{dt}-{fieldname}"
                if record.get("name") and record.get("name") != expected_name:
                    claimed.add((dt, fieldname))
    return claimed


def _drop_fields_claimed_by_a_fixture(spec, claimed):
    usable, dropped = {}, []
    for dt, fields in spec.items():
        keep = []
        for df in fields:
            if (dt, df.get("fieldname")) in claimed:
                dropped.append((dt, df.get("fieldname")))
            else:
                keep.append(df)
        if keep:
            usable[dt] = keep
    return usable, dropped


# ---------------------------------------------------------------------------
# Schema-creating patches
# ---------------------------------------------------------------------------


def _run_schema_patches():
    """Explicitly run only the patches.txt entries that CREATE schema (custom
    fields). This is a curated, hand-picked list -- not discovered
    programmatically -- because a data-migration or field-removal patch must
    not run against an empty site. See patches.txt for the full patch list;
    the remaining entries are either data migrations, a field-removal patch,
    a property-setter patch, or a server-script toggle, none of which belong
    here.
    """
    from gke_customization.patches import (
        punch_pairing_fields,
        salary_withholding_release_fields,
    )

    for patch in (salary_withholding_release_fields, punch_pairing_fields):
        try:
            patch.execute()
        except Exception as e:
            frappe.log_error(
                title="gke_customization._run_schema_patches",
                message=f"Failed running {patch.__name__}: {e}",
            )


# ---------------------------------------------------------------------------
# Post-fixture-sync self-reconciliation
# ---------------------------------------------------------------------------


def reconcile_own_fixtures(verbose=True):
    """`frappe.utils.fixtures.import_fixtures` wraps the ENTIRE
    fixtures/custom_field.json file in one try/except that only catches
    ImportError/DoesNotExistError -- the first record whose Link/Table target
    doesn't exist yet silently discards every record after it in that file.
    By the time `after_sync` runs, fixtures have already synced once (and any
    doctypes that were missing earlier are now installed), so re-insert
    whatever didn't make it in, one record at a time, so one bad record costs
    one record instead of the rest of the file.
    """
    if not os.path.isfile(FIXTURE_CUSTOM_FIELD_PATH):
        return 0

    try:
        with open(FIXTURE_CUSTOM_FIELD_PATH) as f:
            records = json.load(f)
    except (OSError, ValueError) as e:
        if verbose:
            print(f"gke_customization: could not read {FIXTURE_CUSTOM_FIELD_PATH}: {e}")
        return 0

    inserted = 0
    for record in records:
        dt, fieldname = record.get("dt"), record.get("fieldname")
        if not dt or not fieldname:
            continue
        if frappe.db.exists("Custom Field", {"dt": dt, "fieldname": fieldname}):
            continue
        if _unresolvable_target(record):
            continue
        try:
            doc = frappe.get_doc(record)
            doc.insert(ignore_permissions=True)
            inserted += 1
        except Exception as e:
            frappe.log_error(
                title="gke_customization.reconcile_own_fixtures",
                message=f"Failed inserting {dt}-{fieldname}: {e}",
            )

    if inserted:
        frappe.db.commit()
    if verbose:
        print(
            f"gke_customization.reconcile_own_fixtures: inserted {inserted} record(s)"
        )
    return inserted


def _unresolvable_target(record):
    """Return the doctype name that isn't installed/resolvable for this
    record, or None if everything it depends on exists.
    """
    dt = record.get("dt")
    if dt and not frappe.db.exists("DocType", dt):
        return dt
    if record.get("fieldtype") in _DOCTYPE_LINK_TYPES:
        target = record.get("options")
        if target and not frappe.db.exists("DocType", target):
            return target
    return None


# ---------------------------------------------------------------------------
# Install verification gate
# ---------------------------------------------------------------------------


def verify_site_schema(verbose=True):
    """Assert that this app's schema actually landed. Intended to be run
    manually (e.g. in CI, after `bench migrate`) -- not wired to a hook.
    """
    problems = []

    for dt, fieldname in (
        ("Salary Withholding", "custom_release_history"),
        ("Salary Withholding Cycle", "custom_released_amount"),
        ("Shift Type", "early_check_in_horizon"),
        ("Shift Type", "max_session_length"),
        ("Employee Checkin", "punch_rule"),
        ("Employee Checkin", "source"),
        ("Employee Checkin", "custom_unique_id"),
        ("Attendance", "punch_error"),
        ("Employee", "attendance_review_by"),
        ("HR Settings", "enable_session_pairing"),
        ("HR Settings", "default_attendance_review_user"),
    ):
        if not frappe.db.exists("Custom Field", {"dt": dt, "fieldname": fieldname}):
            problems.append(f"missing Custom Field {dt}-{fieldname}")

    if os.path.isfile(FIXTURE_CUSTOM_FIELD_PATH):
        with open(FIXTURE_CUSTOM_FIELD_PATH) as f:
            records = json.load(f)
        for record in records:
            dt, fieldname = record.get("dt"), record.get("fieldname")
            if not dt or not fieldname:
                continue
            if _unresolvable_target(record):
                continue
            if not frappe.db.exists("Custom Field", {"dt": dt, "fieldname": fieldname}):
                problems.append(f"missing fixture Custom Field {dt}-{fieldname}")

    if verbose:
        if problems:
            print(f"gke_customization.verify_site_schema: {len(problems)} problem(s):")
            for p in problems:
                print(f"  - {p}")
        else:
            print("gke_customization.verify_site_schema: OK")

    return problems
