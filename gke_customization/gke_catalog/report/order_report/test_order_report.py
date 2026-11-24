# Copyright (c) 2026, Gurukrupa Export and Contributors
# See license.txt

"""Pins that the Order Report never runs its query over the whole order history.

No DB writes and no report query: ``get_data`` is patched.
"""

from unittest.mock import patch

from frappe.tests import UnitTestCase

from gke_customization.gke_catalog.report.order_report import order_report

MOD = "gke_customization.gke_catalog.report.order_report.order_report"


class TestOrderReportNeedsAFilter(UnitTestCase):
    def test_no_filter_returns_a_message_and_skips_the_query(self):
        for filters in (None, {}, {"company": []}, {"order": [], "so": ""}):
            with patch(
                f"{MOD}.get_data", side_effect=AssertionError("query ran")
            ) as get_data:
                result = order_report.execute(filters)

            get_data.assert_not_called()
            columns, data, message = result
            self.assertTrue(columns)
            self.assertEqual(data, [])
            self.assertIn("at least one filter", message)

    def test_any_single_filter_runs_the_report(self):
        for key in order_report.FILTER_KEYS:
            with patch(f"{MOD}.get_data", return_value=[]) as get_data:
                columns, data = order_report.execute({key: ["X"]})

            get_data.assert_called_once()
            self.assertEqual(get_data.call_args.args[0][key], ["X"])

    def test_every_js_filter_is_a_filter_key(self):
        import os
        import re

        path = os.path.join(os.path.dirname(order_report.__file__), "order_report.js")
        with open(path) as f:
            source = f.read()
        active = re.sub(r"//.*", "", source)
        names = set(re.findall(r"""["']?fieldname["']?\s*:\s*["'](\w+)["']""", active))

        self.assertEqual(names, set(order_report.FILTER_KEYS))
