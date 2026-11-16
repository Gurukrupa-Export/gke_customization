# Copyright (c) 2026, Gurukrupa Export and Contributors
# See license.txt

"""Pins that one gold-rate dealer failing cannot cost the others their rates.

No network: ``requests`` is patched in the module. No DB writes: the document is built in
memory and only ``validate`` runs.
"""

from unittest.mock import MagicMock, patch

import frappe
import requests
from frappe.tests import UnitTestCase

from gke_customization.gke_price_list.doctype.gold_rates import gold_rates

MOD = "gke_customization.gke_price_list.doctype.gold_rates.gold_rates"

ROW = {
    dealer: i
    for i, dealer in enumerate(
        [
            "Jain Jewels",
            "J K Sons",
            "Arihant",
            "Mohanlal",
            "Ambica",
            "Shiv Sahai",
            "SLN Bullion",
        ]
    )
}


def _doc():
    doc = frappe.new_doc("Gold Rates")
    doc.add_default_rows()
    return doc


class TestProviderIsolation(UnitTestCase):
    def setUp(self):
        patcher = patch(f"{MOD}.frappe.log_error")
        self.log_error = patcher.start()
        self.addCleanup(patcher.stop)

    def _validate_with(self, failing):
        """Run validate with every fetch method stubbed: those in ``failing`` raise, the
        others write 1000 + row index to their own row."""
        doc = _doc()

        def stub(dealer):
            def fetch():
                if dealer in failing:
                    raise requests.exceptions.SSLError("certificate has expired")
                doc.table_djrm[ROW[dealer]].live_rate = 1000 + ROW[dealer]

            return fetch

        for dealer, method in gold_rates.PROVIDERS:
            setattr(doc, method, stub(dealer))
        doc.validate()
        return doc

    def test_every_dealer_is_fetched_once_in_order(self):
        self.assertEqual(
            [dealer for dealer, _m in gold_rates.PROVIDERS],
            [
                "Jain Jewels",
                "J K Sons",
                "Arihant",
                "Mohanlal",
                "Shiv Sahai",
                "SLN Bullion",
            ],
        )

    def test_an_unguarded_dealer_failing_keeps_the_others(self):
        for failing in ("J K Sons", "Shiv Sahai"):
            self.log_error.reset_mock()
            doc = self._validate_with({failing})

            for dealer, row in ROW.items():
                if dealer in (failing, "Ambica"):
                    self.assertFalse(doc.table_djrm[row].live_rate, dealer)
                else:
                    self.assertEqual(doc.table_djrm[row].live_rate, 1000 + row, dealer)
            self.log_error.assert_called_once()
            self.assertEqual(
                self.log_error.call_args.kwargs["title"],
                f"Gold Rate Fetch Error: {failing}",
            )

    def test_all_failing_still_validates(self):
        doc = self._validate_with({dealer for dealer, _m in gold_rates.PROVIDERS})

        self.assertEqual(self.log_error.call_count, len(gold_rates.PROVIDERS))
        self.assertFalse(any(row.live_rate for row in doc.table_djrm))


class TestRealFetchersOffline(UnitTestCase):
    """The real fetch methods, with the network replaced."""

    def setUp(self):
        patcher = patch(f"{MOD}.frappe.log_error")
        self.log_error = patcher.start()
        self.addCleanup(patcher.stop)

    def test_jk_sons_http_error_no_longer_escapes_validate(self):
        bad = MagicMock()
        bad.raise_for_status.side_effect = requests.exceptions.HTTPError("503")
        with patch(f"{MOD}.requests.get", return_value=bad), patch(
            f"{MOD}.requests.post",
            side_effect=requests.exceptions.ConnectTimeout("down"),
        ):
            _doc().validate()

        titles = [c.kwargs["title"] for c in self.log_error.call_args_list]
        self.assertIn("Gold Rate Fetch Error: J K Sons", titles)
        self.assertIn("Gold Rate Fetch Error: Shiv Sahai", titles)

    def test_expired_certificate_on_arihant_is_logged_under_its_name(self):
        def get(url, timeout):
            if "arihant" in url:
                raise requests.exceptions.SSLError("certificate has expired")
            ok = MagicMock()
            ok.text = ""
            return ok

        ok_post = MagicMock()
        ok_post.text = ""
        with patch(f"{MOD}.requests.get", side_effect=get), patch(
            f"{MOD}.requests.post", return_value=ok_post
        ):
            _doc().validate()

        titles = [c.kwargs["title"] for c in self.log_error.call_args_list]
        self.assertEqual(titles, ["Gold Rate Fetch Error: Arihant"])
