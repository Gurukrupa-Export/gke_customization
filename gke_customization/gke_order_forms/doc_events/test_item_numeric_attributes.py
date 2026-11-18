"""Tests for `item.set_numeric_attribute_values`, the Item before_validate hook.

ERPNext checks a variant against its template's attribute row, so a template row left at
``numeric_values = 0`` for a numeric Item Attribute refuses every value. The hook copies the
attribute's flag and range onto template rows, and must leave variants alone: a stocked
variant whose rows change cannot be saved again.
"""

import unittest
from unittest.mock import patch

import frappe

from . import item

ATTRIBUTES = {
	"Distance Between Kadi To Mugappu": frappe._dict(
		numeric_values=1, from_range=0.0, to_range=1000.0, increment=0.01
	),
	"Metal Colour": frappe._dict(numeric_values=0, from_range=0.0, to_range=0.0, increment=0.0),
}


def _row(attribute, numeric_values=0, from_range=0.0, to_range=0.0, increment=0.0):
	return frappe._dict(
		attribute=attribute,
		numeric_values=numeric_values,
		from_range=from_range,
		to_range=to_range,
		increment=increment,
	)


def _item(rows, has_variants=0, variant_of=None):
	return frappe._dict(doctype="Item", has_variants=has_variants, variant_of=variant_of, attributes=rows)


def _flags(row):
	return (row.numeric_values, row.from_range, row.to_range, row.increment)


class TestSetNumericAttributeValues(unittest.TestCase):
	def setUp(self):
		patcher = patch.object(
			frappe,
			"get_cached_value",
			side_effect=lambda doctype, name, fields, as_dict=False: ATTRIBUTES.get(name),
		)
		self.get_cached_value = patcher.start()
		self.addCleanup(patcher.stop)

	def test_a_stale_template_row_takes_the_attribute_flag_and_range(self):
		"""MU06453: the 2026-08-08 import left this row at 0 and a 0/0/0 range."""
		row = _row("Distance Between Kadi To Mugappu")

		item.set_numeric_attribute_values(_item([row], has_variants=1))

		self.assertEqual(_flags(row), (1, 0.0, 1000.0, 0.01))

	def test_a_template_row_whose_range_drifted_is_brought_back(self):
		row = _row("Distance Between Kadi To Mugappu", 1, 0.0, 50.0, 0.5)

		item.set_numeric_attribute_values(_item([row], has_variants=1))

		self.assertEqual(_flags(row), (1, 0.0, 1000.0, 0.01))

	def test_a_list_attribute_row_is_left_alone(self):
		row = _row("Metal Colour")

		item.set_numeric_attribute_values(_item([row], has_variants=1))

		self.assertEqual(_flags(row), (0, 0.0, 0.0, 0.0))

	def test_a_variant_is_never_touched(self):
		"""Its row is not what ERPNext checks, and a stocked variant's rows may not change."""
		row = _row("Distance Between Kadi To Mugappu")

		item.set_numeric_attribute_values(_item([row], variant_of="MU06453"))

		self.assertEqual(_flags(row), (0, 0.0, 0.0, 0.0))
		self.get_cached_value.assert_not_called()

	def test_an_item_without_variants_is_not_looked_at(self):
		item.set_numeric_attribute_values(_item([_row("Distance Between Kadi To Mugappu")]))

		self.get_cached_value.assert_not_called()

	def test_a_row_without_an_attribute_or_an_unknown_attribute_is_skipped(self):
		blank, unknown = _row(None), _row("No Such Attribute")

		item.set_numeric_attribute_values(_item([blank, unknown], has_variants=1))

		self.assertEqual(_flags(blank), (0, 0.0, 0.0, 0.0))
		self.assertEqual(_flags(unknown), (0, 0.0, 0.0, 0.0))


if __name__ == "__main__":
	unittest.main()
