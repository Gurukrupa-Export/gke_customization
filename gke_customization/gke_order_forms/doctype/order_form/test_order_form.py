# Copyright (c) 2023, Gurukrupa Export and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.model.workflow import apply_workflow
from frappe.utils import now, add_days


class TestOrderForm(FrappeTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.department = frappe.get_value(
            "Department", {"department_name": "Test_Department"}, "name"
        )
        cls.branch = frappe.get_value("Branch", {"branch_name": "Test Branch"}, "name")

    def test_order_created_purchase(self):
        order_form = make_order_form(
            department=self.department,
            branch=self.branch,
            order_type="Purchase",
            design_by="Purchase",
            design_type="New Design",
        )

        order = frappe.get_all(
            "Order", filters={"cad_order_form": order_form.name, "docstatus": 0}
        )
        self.assertEqual(len(order), len(order_form.order_details))

        purchase_order = frappe.get_all(
            "Purchase Order",
            filters={"custom_form_id": order_form.name, "docstatus": 0},
        )
        self.assertEqual(len(purchase_order), 1)

    def test_order_created_mod(self):
        order_form = make_order_form(
            department=self.department,
            branch=self.branch,
            order_type="Sales",
            design_by="Our Design",
            design_type="Mod - Old Stylebio & Tag No",
            design_code="RI05086-001",
        )

        order = frappe.get_all(
            "Order", filters={"cad_order_form": order_form.name, "docstatus": 0}
        )
        self.assertEqual(len(order), len(order_form.order_details))

    def test_order_created_sketch_design(self):
        order_form = make_order_form(
            department=self.department,
            branch=self.branch,
            order_type="Sales",
            design_by="Our Design",
            design_type="Sketch Design",
            design_code="EA05120-001",
        )

        order = frappe.get_all(
            "Order", filters={"cad_order_form": order_form.name, "docstatus": 0}
        )
        self.assertEqual(len(order), len(order_form.order_details))

    def test_order_created_customer_design(self):
        order_form = make_order_form(
            department=self.department,
            branch=self.branch,
            order_type="Sales",
            design_by="Customer Design",
            design_type="New Design",
        )

        order = frappe.get_all(
            "Order", filters={"cad_order_form": order_form.name, "docstatus": 0}
        )
        self.assertEqual(len(order), len(order_form.order_details))

    def tearDown(self):
        frappe.db.rollback()


def make_order_form(**args):
    args = frappe._dict(args)
    order_form = frappe.new_doc("Order Form")
    order_form.company = "Gurukrupa Export Private Limited"
    order_form.department = args.department
    order_form.branch = args.branch
    order_form.salesman_name = "Test_Sales_Person"
    order_form.customer_code = "Test_Customer_External"
    order_form.order_type = args.order_type
    order_form.flow_type = "MTO"
    order_form.due_days = 4
    order_form.diamond_quality = "EF-VVS"
    order_form.order_date = now()
    order_form.due_days = 3
    order_form.delivery_date = add_days(now(), 3)
    if order_form.order_type == "Purchase":
        order_form.flow_type = "FILLER"
        order_form.supplier = "Test_Supplier"

    if args.design_type == "Sketch Design":
        order_form.append(
            "order_details",
            {
                "delivery_date": order_form.delivery_date,
                "design_by": args.design_by,
                "design_type": args.design_type,
                "design_id": args.design_code,
                "category": "Mugappu",
                "subcategory": "Casual Mugappu",
                "setting_type": "Close",
                "sub_setting_type1": "Close Setting",
                "metal_type": "Gold",
                "metal_touch": "22KT",
                "metal_colour": "Yellow",
                "metal_target": 10,
                "diamond_target": 10,
                "product_size": 10,
                "stone_changeable": "No",
                "detachable": "No",
                "feature": "Lever Back",
                "back_side_size": 10,
                "rhodium": "None",
                "enamal": "No",
                "two_in_one": "No",
                "number_of_ant": 1,
                "distance_between_kadi_to_mugappu": 10,
                "space_between_mugappu": 10,
                "count_of_spiral_turns": 2,
                "chain_type": "Hollow Pipes",
                "customer_chain": "Customer",
                "chain_weight": 10,
                "chain_length": 10,
                "chain_thickness": 10,
                "gemstone_type": "Rose Quartz",
                "gemstone_quality": "Synthetic",
            },
        )

    elif args.design_type == "Mod - Old Stylebio & Tag No":
        order_form.append(
            "order_details",
            {
                "delivery_date": order_form.delivery_date,
                "design_by": args.design_by,
                "design_type": args.design_type,
                "design_id": args.design_code,
                "bom": "BOM-RI05086-001-001",
                "mod_reason": "Change in Metal Colour",
                "category": "Mugappu",
                "subcategory": "Casual Mugappu",
                "setting_type": "Close",
                "sub_setting_type1": "Close Setting",
                "metal_type": "Gold",
                "metal_touch": "22KT",
                "metal_colour": "Pink",
                "metal_target": 10,
                "diamond_target": 10,
                "product_size": 10,
                "stone_changeable": "No",
                "detachable": "No",
                "feature": "Lever Back",
                "back_side_size": 10,
                "rhodium": "None",
                "enamal": "No",
                "two_in_one": "No",
                "number_of_ant": 1,
                "distance_between_kadi_to_mugappu": 10,
                "space_between_mugappu": 10,
                "count_of_spiral_turns": 2,
                "chain_type": "Hollow Pipes",
                "customer_chain": "Customer",
                "chain_weight": 10,
                "chain_length": 10,
                "chain_thickness": 10,
                "gemstone_type": "Rose Quartz",
                "gemstone_quality": "Synthetic",
            },
        )

    else:
        order_form.append(
            "order_details",
            {
                "delivery_date": order_form.delivery_date,
                "design_by": args.design_by,
                "design_type": args.design_type,
                "category": "Mugappu",
                "subcategory": "Casual Mugappu",
                "setting_type": "Close",
                "sub_setting_type1": "Close Setting",
                "metal_type": "Gold",
                "metal_touch": "22KT",
                "metal_colour": "Yellow",
                "metal_target": 10,
                "diamond_target": 10,
                "product_size": 10,
                "stone_changeable": "No",
                "detachable": "No",
                "feature": "Lever Back",
                "back_side_size": 10,
                "rhodium": "None",
                "enamal": "No",
                "two_in_one": "No",
                "number_of_ant": 1,
                "distance_between_kadi_to_mugappu": 10,
                "space_between_mugappu": 10,
                "count_of_spiral_turns": 2,
                "chain_type": "Hollow Pipes",
                "customer_chain": "Customer",
                "chain_weight": 10,
                "chain_length": 10,
                "chain_thickness": 10,
                "gemstone_type": "Rose Quartz",
                "gemstone_quality": "Synthetic",
            },
        )

    order_form.save()

    apply_workflow(order_form, "Send For Approval")
    apply_workflow(order_form, "Approve")

    return order_form
