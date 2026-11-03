"""KGGK Item/BOM sync: hook timing, gates, request timeout and error propagation.

The remote site and the Data Migration in KGGK settings are mocked; no request leaves
the process.
"""

import unittest
from unittest.mock import Mock, patch

import frappe

from gke_customization import hooks
from gke_customization.gke_order_forms.doc_events import item as item_events

PREFIX = "gke_customization.gke_order_forms.doc_events.item."


class FakeDoc:
    """Any field the sync payload reads is None unless set; tables are empty."""

    tables = ("attributes", "metal_detail", "diamond_detail", "gemstone_detail", "finding_detail", "other_detail", "items")

    def __init__(self, **values):
        for table in self.tables:
            setattr(self, table, [])
        self.__dict__.update(values)

    def __getattr__(self, name):
        return None

    def get(self, name, default=None):
        return getattr(self, name, default)


def response(status):
    return Mock(status_code=status, text="{}", url="https://kggk.invalid/api/resource")


class TestKggkSyncHooks(unittest.TestCase):
    def test_sync_runs_before_save_after_validation(self):
        # before_save follows validate (so only a valid document is sent) and precedes
        # the write and ERPNext's variant propagation (so a template syncs before its variants).
        self.assertEqual(hooks.doc_events["Item"], {"before_save": PREFIX + "create_item_kggk"})
        self.assertEqual(hooks.doc_events["BOM"], {"before_save": PREFIX + "create_bom_kggk"})


class TestKggkSyncRequests(unittest.TestCase):
    def setUp(self):
        self.settings = {
            "from_site": "https://source.invalid",
            "to_site": "https://kggk.invalid",
            "api_key": "key",
            "api_secret": "secret",
        }
        db = Mock(get_single_value=lambda doctype, field: self.settings.get(field))
        self.put = Mock(return_value=response(200))
        self.post = Mock(return_value=response(200))
        for patcher in (
            patch.object(item_events.frappe, "db", db),
            patch.object(item_events.frappe, "get_all", Mock(return_value=[])),
            patch.object(item_events.frappe, "log_error", Mock()),
            patch.object(item_events.frappe, "logger", Mock()),
            patch.object(item_events.requests, "put", self.put),
            patch.object(item_events.requests, "post", self.post),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def item(self, **values):
        return FakeDoc(**{"name": "ITEM-1", "setting_type": "Nova Glow", **values})

    def bom(self, **values):
        # The BOM payload sends float(diamond_target), so a real BOM always carries it.
        return FakeDoc(**{"name": "BOM-1", "setting_type": "Nova Glow", "bom_type": "Template", "diamond_target": 0, **values})

    def test_every_request_uses_connect_and_read_timeouts(self):
        self.assertEqual(item_events.SYNC_TIMEOUT, (5, 15))
        self.put.return_value = response(404)
        item_events.create_item_kggk(self.item())
        item_events.create_bom_kggk(self.bom())
        calls = self.put.call_args_list + self.post.call_args_list
        self.assertEqual(len(calls), 4)
        self.assertTrue(all(call.kwargs["timeout"] == (5, 15) for call in calls))

    def test_put_updates_and_404_falls_back_to_post(self):
        item_events.create_item_kggk(self.item())
        self.put.assert_called_once()
        self.post.assert_not_called()
        self.assertEqual(self.put.call_args.args[0], "https://kggk.invalid/api/resource/Item/ITEM-1")

        self.put.reset_mock()
        self.put.return_value = response(404)
        item_events.create_bom_kggk(self.bom())
        self.assertEqual(self.post.call_args.args[0], "https://kggk.invalid/api/resource/BOM")

    def test_gates_send_nothing(self):
        cases = [
            (item_events.create_item_kggk, self.item(setting_type="Other")),
            (item_events.create_bom_kggk, self.bom(bom_type="Quotation")),
            (item_events.create_bom_kggk, self.bom(setting_type=None)),
        ]
        for function, doc in cases:
            with self.subTest(function=function.__name__):
                function(doc)
        self.settings["to_site"] = None
        item_events.create_item_kggk(self.item())
        self.put.assert_not_called()
        self.post.assert_not_called()

    def test_remote_error_blocks_the_save(self):
        self.put.return_value = response(500)
        for function, doc in ((item_events.create_item_kggk, self.item()), (item_events.create_bom_kggk, self.bom())):
            with self.subTest(function=function.__name__):
                with self.assertRaises(frappe.ValidationError):
                    function(doc)
        self.post.assert_not_called()
