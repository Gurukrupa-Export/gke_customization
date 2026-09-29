# Copyright (c) 2026, Gurukrupa Export and Contributors
# See license.txt

"""Metal Conversion Report: whose metal each conversion consumed.

The Metal Conversions header stopped recording an owner on 2026-07-30 (jewellery b59fec28
dropped ``is_customer_metal``), and FIFO may draw one conversion from several owners. Each
row of the conversion's "Repack-Metal Conversion" Stock Entry carries its own lane's
``inventory_type`` / ``customer``, so that is where the report reads the owner.

The helpers are looked up inside each test, so a checkout without them fails test by test
rather than as one import error for the whole module.

The integration cases insert bare rows with ``db_insert`` (no validation, no stock), name
them ``_T-D3-``, date them 2099, patch ``frappe.db.commit`` out and roll back after every
test. They skip unless the site sets ``customer_gold_disposable_site``.
"""

import os
import unittest
from unittest.mock import patch

import frappe
from frappe.utils import flt

import gke_customization
from gke_customization.gke_catalog.report.metal_conversion_report import (
    metal_conversion_report as report,
)

DISPOSABLE_FLAG = "customer_gold_disposable_site"
#: No real conversion is dated this far out, so the date filter sees only this module's.
RUN_DATE = "2099-01-01"
CONVERSION_SE_TYPE = "Repack-Metal Conversion"
G24 = "M-G-24KT-99.9-Y"
G22 = "M-G-22KT-91.75-Y"
ALLOY = "M-Genia-221"
CUSTOMER = "GJCU0009"
OTHER_CUSTOMER = "GJCU0010"
WAREHOUSE = "Waxing RM - KGJPL"

#: Saved before any test patches it. A fake answers only the doctypes it owns and hands
#: every other read to the real one: ``flt(x, precision)`` looks the rounding method up
#: through System Settings, and a fake that swallowed that read would zero every quantity.
_REAL_GET_ALL = frappe.get_all


def setUpModule():
    """Refuse to test any checkout but the one ``PYTHONPATH`` names.

    Run against a worktree, ``PYTHONPATH`` must win over the bench's own
    ``apps/gke_customization``. With the path order wrong the bench copy is imported, and a
    red or green run proves nothing about the worktree.
    """
    for entry in filter(None, os.environ.get("PYTHONPATH", "").split(os.pathsep)):
        expected = os.path.join(entry, "gke_customization")
        if os.path.isdir(expected):
            actual = os.path.dirname(gke_customization.__file__)
            if os.path.realpath(actual) != os.path.realpath(expected):
                raise AssertionError(
                    f"gke_customization was imported from {actual}, not {expected}"
                )
            return


def _owning(doctypes, fake, real):
    """A side_effect that routes ``doctypes`` to ``fake`` and everything else to ``real``."""

    def side_effect(doctype, *args, **kwargs):
        if doctype in doctypes:
            return fake(doctype, *args, **kwargs)
        return real(doctype, *args, **kwargs)

    return side_effect


def _consumed(item_code, qty, inventory_type="Regular Stock", customer=None):
    """A Stock Entry Detail row that draws ``qty`` of ``item_code`` from the warehouse."""
    return frappe._dict(
        item_code=item_code,
        s_warehouse=WAREHOUSE,
        t_warehouse=None,
        transfer_qty=qty,
        inventory_type=inventory_type,
        customer=customer,
    )


def _produced(item_code, qty, inventory_type="Regular Stock", customer=None):
    """A Stock Entry Detail row that makes ``qty`` of ``item_code`` into the warehouse."""
    row = _consumed(item_code, qty, inventory_type, customer)
    row.update(s_warehouse=None, t_warehouse=WAREHOUSE)
    return row


def _mcon00333_rows():
    """MAT-STE-19749 as booked for MCON00333: GJCU0009's 24K from two batches, 1.798 g of
    company alloy, and the 22K made into the customer's lane."""
    return [
        _consumed(G24, 1.327, "Customer Goods", CUSTOMER),
        _consumed(G24, 18.673, "Customer Goods", CUSTOMER),
        _consumed(ALLOY, 1.798),
        _produced(G22, 21.798, "Customer Goods", CUSTOMER),
    ]


def _mcon00331_rows():
    """MCON00331's shape: FIFO drew 9.523 g of GJCU0009's 24K and 0.477 g of company 24K,
    and each lane made its own 22K."""
    return [
        _consumed(G24, 9.523, "Customer Goods", CUSTOMER),
        _consumed(G24, 0.477),
        _consumed(ALLOY, 0.899),
        _produced(G22, 10.379, "Customer Goods", CUSTOMER),
        _produced(G22, 0.520),
    ]


def _company_rows():
    """A conversion of company metal only."""
    return [_consumed(G24, 10), _consumed(ALLOY, 0.899), _produced(G22, 10.899)]


class TestOwnershipSummary(unittest.TestCase):
    """``summarise_ownership``: only the rows that consume the source item decide."""

    def test_customer_conversion_with_company_alloy_is_customer_metal(self):
        """MCON00333 read "No" on production. Its company alloy must not make it Mixed,
        and the 21.798 g of 22K it made is not customer metal consumed."""
        summary = report.summarise_ownership(G24, _mcon00333_rows())
        self.assertEqual(
            summary,
            {"is_customer_metal": "Yes", "customer": CUSTOMER, "customer_qty": 20.0},
        )

    def test_customer_and_company_draw_is_mixed(self):
        """The customer's share is kept to 3 places: 9.523, not the site's 2-place 9.52."""
        summary = report.summarise_ownership(G24, _mcon00331_rows())
        self.assertEqual(
            summary,
            {"is_customer_metal": "Mixed", "customer": CUSTOMER, "customer_qty": 9.523},
        )

    def test_owner_edge_cases(self):
        summarise = report.summarise_ownership
        cases = {
            # Untyped rows are company metal, as in jewellery's get_batch_lane_map.
            "untyped and Regular Stock": (
                [_consumed(G24, 4, None), _consumed(G24, 6)],
                ("No", "", 0.0),
            ),
            "Customer Stock": (
                [_consumed(G24, 10, "Customer Stock", CUSTOMER)],
                ("Yes", CUSTOMER, 10.0),
            ),
            # Customers are listed in the order they were drawn, not sorted.
            "two customers": (
                [
                    _consumed(G24, 4, "Customer Goods", OTHER_CUSTOMER),
                    _consumed(G24, 6, "Customer Goods", CUSTOMER),
                ],
                ("Yes", f"{OTHER_CUSTOMER}, {CUSTOMER}", 10.0),
            ),
            # Shown as booked: legacy rows carry a customer type with no customer.
            "customer type without a customer": (
                [_consumed(G24, 10, "Customer Goods")],
                ("Yes", "", 10.0),
            ),
            # Nothing consumed says whose metal it was: unknown, not "No".
            "only produced rows": (
                [_produced(G22, 10.899, "Customer Goods", CUSTOMER)],
                ("", "", 0.0),
            ),
            "no rows": ([], ("", "", 0.0)),
        }
        for case, (rows, (flag, customer, qty)) in cases.items():
            with self.subTest(case):
                self.assertEqual(
                    summarise(G24, rows),
                    {
                        "is_customer_metal": flag,
                        "customer": customer,
                        "customer_qty": qty,
                    },
                )


class TestColumns(unittest.TestCase):
    def test_customer_columns_follow_the_flag(self):
        """The existing columns keep their fieldnames and order."""
        columns = report.get_columns()
        self.assertEqual(
            [column["fieldname"] for column in columns],
            [
                "metal_conversion_id",
                "stock_entry",
                "creation_datetime",
                "manufacturer",
                "user_name",
                "department",
                "source_item",
                "source_qty",
                "source_alloy",
                "source_alloy_qty",
                "target_item",
                "target_qty",
                "is_customer_metal",
                "customer",
                "customer_qty",
            ],
        )
        self.assertEqual(columns[-1]["precision"], 3)


class TestHeaderQuery(unittest.TestCase):
    """The header row carries no owner; the conversion's Stock Entry rows decide it."""

    def test_header_sql_no_longer_reads_the_dropped_flag(self):
        """A migrated site keeps ``is_customer_metal`` at its default 0, so every conversion
        read "No"; a site installed since has no such column, and the report failed with
        error 1054. Even a header row still carrying the flag is overruled by the rows."""
        real_sql = frappe.db.sql
        headers = []

        def sql(query, *args, **kwargs):
            if "`tabMetal Conversions`" not in str(query):
                return real_sql(query, *args, **kwargs)
            headers.append(str(query))
            return [
                frappe._dict(
                    metal_conversion_id="_T-D3-MCON-H",
                    source_item=G24,
                    is_customer_metal="Yes",
                )
            ]

        found = {
            "Stock Entry": [
                frappe._dict(
                    name="_T-D3-SE-H", custom_metal_conversion_reference="_T-D3-MCON-H"
                )
            ],
            "Stock Entry Detail": [
                frappe._dict(row, parent="_T-D3-SE-H") for row in _company_rows()
            ],
        }
        with patch.object(frappe.db, "sql", side_effect=sql), patch.object(
            frappe,
            "get_all",
            side_effect=_owning(
                set(found), lambda dt, *a, **k: found[dt], _REAL_GET_ALL
            ),
        ):
            _, data = report.execute(frappe._dict())

        self.assertEqual(len(headers), 1)
        self.assertNotIn("is_customer_metal", headers[0])
        self.assertNotIn("tabStock Entry", headers[0])
        self.assertEqual([row.is_customer_metal for row in data], ["No"])


def _insert_conversion(name, source_qty, alloy_qty, target_qty, minute=0):
    """A submitted Metal Conversions header, with only what the report selects."""
    creation = f"{RUN_DATE} 10:{minute:02d}:00"
    frappe.get_doc(
        {
            "doctype": "Metal Conversions",
            "name": name,
            "docstatus": 1,
            "creation": creation,
            "modified": creation,
            "owner": frappe.session.user,
            "modified_by": frappe.session.user,
            "source_item": G24,
            "source_qty": source_qty,
            "source_alloy": ALLOY,
            "source_alloy_qty": alloy_qty,
            "target_item": G22,
            "target_qty": target_qty,
        }
    ).db_insert()


def _insert_entry(
    name, conversion, rows, stock_entry_type=CONVERSION_SE_TYPE, docstatus=1
):
    """A Stock Entry that points back at ``conversion``, with ``rows`` as its items."""
    frappe.get_doc(
        {
            "doctype": "Stock Entry",
            "name": name,
            "docstatus": docstatus,
            "stock_entry_type": stock_entry_type,
            "purpose": "Repack",
            "custom_metal_conversion_reference": conversion,
        }
    ).db_insert()
    for idx, row in enumerate(rows, 1):
        frappe.get_doc(
            {
                "doctype": "Stock Entry Detail",
                "parent": name,
                "parenttype": "Stock Entry",
                "parentfield": "items",
                "idx": idx,
                "docstatus": docstatus,
                **row,
            }
        ).db_insert()


class TestMetalConversionReport(unittest.TestCase):
    """The report against real tables. Every row is inserted bare and rolled back."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not frappe.conf.get(DISPOSABLE_FLAG):
            raise unittest.SkipTest(
                f"needs {DISPOSABLE_FLAG!r} in site_config.json -- it inserts (and rolls "
                "back) Metal Conversions and Stock Entries"
            )

    def setUp(self):
        self.addCleanup(frappe.db.rollback)
        commit = patch.object(frappe.db, "commit")
        commit.start()
        self.addCleanup(commit.stop)

    def run_report(self, **filters):
        """This module's rows of the report for ``RUN_DATE``, in report order."""
        filters = frappe._dict(from_date=RUN_DATE, to_date=RUN_DATE, **filters)
        _, data = report.execute(filters)
        return [row for row in data if row.metal_conversion_id.startswith("_T-D3-")]

    def names(self, **filters):
        return [row.metal_conversion_id for row in self.run_report(**filters)]

    def insert_customer_conversion(self, minute=0):
        """The MCON00333 replica: 20 g of GJCU0009's 24K made into 21.798 g of 22K."""
        _insert_conversion("_T-D3-MCON-1", 20, "1.798", 21.798365123, minute)
        _insert_entry("_T-D3-SE-1", "_T-D3-MCON-1", _mcon00333_rows())

    def insert_mixed_and_company_conversions(self):
        _insert_conversion("_T-D3-MCON-2", 10, "0.899", 10.899, minute=2)
        _insert_entry("_T-D3-SE-2", "_T-D3-MCON-2", _mcon00331_rows())
        _insert_conversion("_T-D3-MCON-3", 10, "0.899", 10.899, minute=3)
        _insert_entry("_T-D3-SE-3", "_T-D3-MCON-3", _company_rows())

    def test_mcon00333_replica_reports_customer_metal(self):
        """MCON00333 showed "No" beside MAT-STE-19749, whose metal was all GJCU0009's."""
        self.insert_customer_conversion()

        (row,) = self.run_report()
        self.assertEqual(row.metal_conversion_id, "_T-D3-MCON-1")
        self.assertEqual(row.is_customer_metal, "Yes")
        self.assertEqual(row.stock_entry, "_T-D3-SE-1")
        self.assertAlmostEqual(flt(row.source_qty), 20, places=3)
        self.assertAlmostEqual(flt(row.target_qty), 21.798, places=3)
        self.assertEqual(row.customer, CUSTOMER)
        self.assertAlmostEqual(flt(row.customer_qty), 20, places=3)

    def test_yes_and_no_filters_split_customer_mixed_and_company(self):
        """On production "Yes" listed none of the 17 conversions that drew GJCU0009's
        gold. "Yes" keeps Mixed ones too, so no conversion of customer metal is hidden."""
        self.insert_customer_conversion(minute=1)
        self.insert_mixed_and_company_conversions()

        rows = {row.metal_conversion_id: row for row in self.run_report()}
        self.assertEqual(
            {name: row.is_customer_metal for name, row in rows.items()},
            {"_T-D3-MCON-1": "Yes", "_T-D3-MCON-2": "Mixed", "_T-D3-MCON-3": "No"},
        )
        self.assertEqual(rows["_T-D3-MCON-2"].customer, CUSTOMER)
        self.assertAlmostEqual(flt(rows["_T-D3-MCON-2"].customer_qty), 9.523, places=3)
        self.assertEqual(
            self.names(is_customer_metal="Yes"), ["_T-D3-MCON-2", "_T-D3-MCON-1"]
        )
        self.assertEqual(self.names(is_customer_metal="No"), ["_T-D3-MCON-3"])

    def test_conversion_with_only_a_cancelled_entry_has_no_owner(self):
        """gk's MCON00602-604: the only conversion entry was cancelled. The old join showed
        it and said "No". With no submitted entry there is no owner, in either filter."""
        _insert_conversion("_T-D3-MCON-C", 10, "0.899", 10.899)
        _insert_entry("_T-D3-SE-C", "_T-D3-MCON-C", _company_rows(), docstatus=2)

        (row,) = self.run_report()
        self.assertEqual(row.metal_conversion_id, "_T-D3-MCON-C")
        self.assertFalse(row.stock_entry)
        self.assertEqual(row.is_customer_metal, "")
        self.assertEqual(row.customer, "")
        self.assertEqual(row.customer_qty, 0)
        self.assertEqual(self.names(is_customer_metal="Yes"), [])
        self.assertEqual(self.names(is_customer_metal="No"), [])

    def test_process_loss_entry_does_not_duplicate_the_row(self):
        """A melting loss books a "Process Loss" entry against the same conversion. The old
        join (purpose "Repack" only) listed the conversion once per entry and doubled its
        totals. Its rows hold both owners' metal, so taking them in would also show."""
        self.insert_customer_conversion()
        _insert_entry(
            "_T-D3-SE-PL",
            "_T-D3-MCON-1",
            [_consumed(G24, 0.1, "Customer Goods", CUSTOMER), _consumed(G24, 0.05)],
            stock_entry_type="Process Loss",
        )

        (row,) = self.run_report()
        self.assertEqual(row.stock_entry, "_T-D3-SE-1")
        self.assertEqual(row.is_customer_metal, "Yes")
        self.assertAlmostEqual(flt(row.customer_qty), 20, places=3)

    def test_ownership_lookup_query_count_is_constant(self):
        """One header query and two batched lookups, however many conversions are listed."""
        self.insert_customer_conversion(minute=1)
        self.run_report()  # warm the meta and settings caches
        one = self.queries()
        self.insert_mixed_and_company_conversions()
        three = self.queries()

        self.assertEqual(len(self.run_report()), 3)
        self.assertEqual(len(three), len(one), three)
        self.assertEqual(
            len([query for query in three if "`tabStock Entry Detail`" in query]), 1
        )

    def queries(self):
        """Every SQL statement one run of the report sends."""
        with patch.object(frappe.db, "sql", wraps=frappe.db.sql) as sql:
            self.run_report()
        return [str(call.args[0]) for call in sql.call_args_list]
