# Copyright (c) 2023, Gurukrupa Export and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from gke_customization.gke_order_forms.doctype.order_form.test_order_form import (
    make_order_form,
)
from frappe.model.workflow import apply_workflow


class TestOrder(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.department = frappe.get_value(
            "Department", {"department_name": "Test_Department"}, "name"
        )
        cls.branch = frappe.get_value("Branch", {"branch_name": "Test Branch"}, "name")

    def test_order_sketch_design(self):
        item = frappe.db.get_value(
            "Item", {"has_variants": 1}, "name", order_by="creation desc"
        )
        order_form = make_order_form(
            department=self.department,
            branch=self.branch,
            order_type="Sales",
            design_by="Customer Design",
            design_type="Sketch Design",
            design_code=item,
        )
        order = frappe.get_doc(
            "Order",
            frappe.get_value(
                "Order", {"cad_order_form": order_form.name, "docstatus": 0}
            ),
        )

        order.append("designer_assignment", {"designer": "GEPL - 00202"})
        order.save()
        apply_workflow(order, "Assigned")

        timesheets = frappe.get_all(
            "Timesheet", filters={"order": order.name, "docstatus": 0}
        )

        for ts in timesheets:
            timesheet = frappe.get_doc("Timesheet", ts.name)
            apply_workflow(timesheet, "Start Designing")
            apply_workflow(timesheet, "Send to QC")
            apply_workflow(timesheet, "Update Design")
            apply_workflow(timesheet, "Start Designing")
            apply_workflow(timesheet, "Send to QC")
            if timesheet.custom_required_customer_approval:
                apply_workflow(timesheet, "Send For Approval")
            apply_workflow(timesheet, "Approve")

        order.reload()
        order.capganthan = "None"
        order.save()
        apply_workflow(order, "Update")

        self.assertTrue(frappe.db.exists("Item", order.item))

        bom = frappe.new_doc("BOM")
        bom.item = order.item
        bom.append("items", {"item_code": order.item})
        bom.two_in_one = "No"
        bom.metal_target = 10
        bom.feature = "Lever Back"
        bom.save()

        frappe.db.set_value("Item", order.item, "master_bom", bom.name)
        order.reload()
        order.new_bom = bom.name
        order.save()

        apply_workflow(order, "Send to QC")

        order.cad_file = "https://www.chidambaramcovering.in/image/cache/catalog/Mogappu%20Chain/mchn510-gold-plated-jewellery-mugappu-design-without-stone-5-425x500.jpg.webp"
        order.cad_image = "https://www.chidambaramcovering.in/image/cache/catalog/Mogappu%20Chain/mchn510-gold-plated-jewellery-mugappu-design-without-stone-5-425x500.jpg.webp"
        apply_workflow(order, "Approve")

    def test_order_modification_only_variant(self):
        item = frappe.db.get_value(
            "Item", {"has_variants": 0}, "name", order_by="creation desc"
        )
        order_form = make_order_form(
            department=self.department,
            branch=self.branch,
            order_type="Sales",
            design_by="Our Design",
            design_type="Mod - Old Stylebio & Tag No",
            design_code=item,
        )
        order = frappe.get_doc(
            "Order",
            frappe.get_value(
                "Order", {"cad_order_form": order_form.name, "docstatus": 0}
            ),
        )
        order.bom_or_cad = "Check"
        order.workflow_type = "BOM"
        order.item_type = "Only Variant"
        order.bom_type = "New BOM"
        order.capganthan = "None"
        order.save()

        apply_workflow(order, "Create BOM")

        self.assertTrue(frappe.db.exists("Item", order.item))
        order.reload()

        order.append("bom_assignment", {"designer": "GEPL - 00590"})
        order.save()
        apply_workflow(order, "Create")
        self.assertTrue(frappe.db.exists("BOM", order.new_bom))

        frappe.db.set_value("Item", order.item, "master_bom", order.new_bom)
        apply_workflow(order, "Send to QC")
        order.cad_file = "https://www.chidambaramcovering.in/image/cache/catalog/Mogappu%20Chain/mchn510-gold-plated-jewellery-mugappu-design-without-stone-5-425x500.jpg.webp"
        order.cad_image = "https://www.chidambaramcovering.in/image/cache/catalog/Mogappu%20Chain/mchn510-gold-plated-jewellery-mugappu-design-without-stone-5-425x500.jpg.webp"
        apply_workflow(order, "Approve")

    def test_order_modification_no_variant(self):
        item = frappe.db.get_value(
            "Item", {"has_variants": 0}, "name", order_by="creation desc"
        )
        order_form = make_order_form(
            department=self.department,
            branch=self.branch,
            order_type="Sales",
            design_by="Our Design",
            design_type="Mod - Old Stylebio & Tag No",
            design_code=item,
        )
        order = frappe.get_doc(
            "Order",
            frappe.get_value(
                "Order", {"cad_order_form": order_form.name, "docstatus": 0}
            ),
        )
        order.bom_or_cad = "Check"
        order.workflow_type = "BOM"
        order.item_type = "No Variant No Suffix"
        order.bom_type = "New BOM"
        order.save()

        apply_workflow(order, "Create BOM")
        order.reload()
        order.new_bom = ""
        order.append("bom_assignment", {"designer": "GEPL - 00590"})
        order.save()

        apply_workflow(order, "Create")
        self.assertTrue(frappe.db.exists("BOM", order.new_bom))
        apply_workflow(order, "Send to QC")
        order.cad_file = "https://www.chidambaramcovering.in/image/cache/catalog/Mogappu%20Chain/mchn510-gold-plated-jewellery-mugappu-design-without-stone-5-425x500.jpg.webp"
        order.cad_image = "https://www.chidambaramcovering.in/image/cache/catalog/Mogappu%20Chain/mchn510-gold-plated-jewellery-mugappu-design-without-stone-5-425x500.jpg.webp"
        apply_workflow(order, "Approve")

    def test_order_modification_template_variant(self):
        item = frappe.db.get_value(
            "Item", {"has_variants": 0}, "name", order_by="creation desc"
        )
        order_form = make_order_form(
            department=self.department,
            branch=self.branch,
            order_type="Sales",
            design_by="Our Design",
            design_type="Mod - Old Stylebio & Tag No",
            design_code=item,
        )
        order = frappe.get_doc(
            "Order",
            frappe.get_value(
                "Order", {"cad_order_form": order_form.name, "docstatus": 0}
            ),
        )
        order.bom_or_cad = "Check"
        order.workflow_type = "BOM"
        order.item_type = "Template and Variant"
        order.bom_type = "New BOM"
        order.save()

        apply_workflow(order, "Create BOM")
        self.assertTrue(frappe.db.exists("Item", order.item))
        item_variant = order.item
        self.assertTrue(frappe.get_value("Item", item_variant, "variant_of"))

        order.reload()
        order.append("bom_assignment", {"designer": "GEPL - 00590"})
        order.save()

        apply_workflow(order, "Create")
        self.assertTrue(frappe.db.exists("BOM", order.new_bom))
        apply_workflow(order, "Send to QC")
        order.cad_file = "https://www.chidambaramcovering.in/image/cache/catalog/Mogappu%20Chain/mchn510-gold-plated-jewellery-mugappu-design-without-stone-5-425x500.jpg.webp"
        order.cad_image = "https://www.chidambaramcovering.in/image/cache/catalog/Mogappu%20Chain/mchn510-gold-plated-jewellery-mugappu-design-without-stone-5-425x500.jpg.webp"
        apply_workflow(order, "Approve")

    def test_order_modification_duplicate_bom(self):
        item = frappe.db.get_value(
            "Item", {"has_variants": 0}, "name", order_by="creation desc"
        )
        order_form = make_order_form(
            department=self.department,
            branch=self.branch,
            order_type="Sales",
            design_by="Our Design",
            design_type="Mod - Old Stylebio & Tag No",
            design_code=item,
        )
        order = frappe.get_doc(
            "Order",
            frappe.get_value(
                "Order", {"cad_order_form": order_form.name, "docstatus": 0}
            ),
        )
        order.bom_or_cad = "Check"
        order.workflow_type = "BOM"
        order.item_type = "Only Variant"
        order.bom_type = "Duplicate BOM"
        order.capganthan = "None"
        order.save()
        frappe.db.commit()

        apply_workflow(order, "Create BOM")

        self.assertTrue(frappe.db.exists("Item", order.item))
        self.assertTrue(frappe.db.exists("BOM", order.new_bom))
        apply_workflow(order, "Send to QC")
        order.cad_file = "https://www.chidambaramcovering.in/image/cache/catalog/Mogappu%20Chain/mchn510-gold-plated-jewellery-mugappu-design-without-stone-5-425x500.jpg.webp"
        order.cad_image = "https://www.chidambaramcovering.in/image/cache/catalog/Mogappu%20Chain/mchn510-gold-plated-jewellery-mugappu-design-without-stone-5-425x500.jpg.webp"
        apply_workflow(order, "Approve")

    def test_order_modification_cad(self):
        item = frappe.db.get_value(
            "Item", {"has_variants": 0}, "name", order_by="creation desc"
        )
        order_form = make_order_form(
            department=self.department,
            branch=self.branch,
            order_type="Sales",
            design_by="Our Design",
            design_type="Mod - Old Stylebio & Tag No",
            design_code=item,
        )
        order = frappe.get_doc(
            "Order",
            frappe.get_value(
                "Order", {"cad_order_form": order_form.name, "docstatus": 0}
            ),
        )
        order.bom_or_cad = "Check"
        order.workflow_type = "CAD"
        order.append("designer_assignment", {"designer": "GEPL - 00997"})
        order.save()

        apply_workflow(order, "Create CAD")

        timesheets = frappe.get_all(
            "Timesheet", filters={"order": order.name, "docstatus": 0}
        )
        timesheet = frappe.get_doc("Timesheet", timesheets[0].name)
        apply_workflow(timesheet, "Start Designing")
        apply_workflow(timesheet, "Send to QC")
        apply_workflow(timesheet, "Update Design")
        apply_workflow(timesheet, "Start Designing")
        apply_workflow(timesheet, "Send to QC")
        if timesheet.custom_required_customer_approval:
            apply_workflow(timesheet, "Send For Approval")
        apply_workflow(timesheet, "Approve")

        apply_workflow(order, "Update")
        order.reload()
        order.item = order.design_id
        order.append("bom_assignment", {"designer": "GEPL - 00590"})
        order.save()

        bom = frappe.new_doc("BOM")
        bom.item = order.item
        bom.append("items", {"item_code": order.item})
        bom.two_in_one = "No"
        bom.metal_target = 10
        bom.feature = "Lever Back"
        bom.save()
        apply_workflow(order, "Create")
        self.assertTrue(frappe.db.exists("BOM", order.new_bom))
        apply_workflow(order, "Send to QC")
        order.cad_file = "https://www.chidambaramcovering.in/image/cache/catalog/Mogappu%20Chain/mchn510-gold-plated-jewellery-mugappu-design-without-stone-5-425x500.jpg.webp"
        order.cad_image = "https://www.chidambaramcovering.in/image/cache/catalog/Mogappu%20Chain/mchn510-gold-plated-jewellery-mugappu-design-without-stone-5-425x500.jpg.webp"
        apply_workflow(order, "Approve")

    def test_order_sketch_design_copy_paste_item(self):
        item = frappe.db.get_value(
            "Item", {"has_variants": 0}, "name", order_by="creation desc"
        )
        order_form = make_order_form(
            department=self.department,
            branch=self.branch,
            order_type="Sales",
            design_by="Our Design",
            design_type="Sketch Design",
            design_code=item,
        )
        order = frappe.get_doc(
            "Order",
            frappe.get_value(
                "Order", {"cad_order_form": order_form.name, "docstatus": 0}
            ),
        )
        order.bom_or_cad = "Check"
        order.item_remark = "Copy Paste Item"
        order.append("designer_assignment", {"designer": "GEPL - 00997"})
        order.item = order.design_id
        order.save()
        order.reload()

        apply_workflow(order, "Create CAD")
        timesheets = frappe.get_all(
            "Timesheet", filters={"order": order.name, "docstatus": 0}
        )
        timesheet = frappe.get_doc("Timesheet", timesheets[0].name)
        apply_workflow(timesheet, "Start Designing")
        apply_workflow(timesheet, "Send to QC")
        apply_workflow(timesheet, "Update Design")
        apply_workflow(timesheet, "Start Designing")
        apply_workflow(timesheet, "Send to QC")
        if timesheet.custom_required_customer_approval:
            apply_workflow(timesheet, "Send For Approval")
        apply_workflow(timesheet, "Approve")
        order.reload()
        self.assertEquals(order.workflow_state, "Approved")

    def tearDown(self):
        frappe.db.rollback()
