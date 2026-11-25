from dataclasses import field
import json
from os import name
from warnings import filters
import frappe
from frappe import _
from werkzeug.wrappers import request
from gke_customization.gke_catalog.api.portals_api.item_price import get_item_price




@frappe.whitelist()
def get_placed_orders(customer=None, user=None):

    # ── CASE 1: Customer login ──
    if customer:
        filters = {"customer": customer, "status": "Ordered"}
        orders = frappe.get_all(
            "Portal Order",
            filters=filters,
            fields=["name", "customer", "user", "order_date", "status", "total_quantity", "total_amount"],
            order_by="order_date desc",
        )

    # ── CASE 2: Rep/User login ──
    elif user:
        assigned_customers = frappe.get_all(
            "Customer Representatives",
            filters={"user_id": user},
            pluck="parent"
        )

        if not assigned_customers:
            return {"success": True, "count": 0, "orders": []}

        orders = frappe.get_all(
            "Portal Order",
            filters={
                "customer": ["in", assigned_customers],
                "status": "Ordered"
            },
            fields=["name", "customer", "user", "order_date", "status", "total_quantity", "total_amount"],
            order_by="order_date desc",
        )

    else:
        frappe.throw(_("Customer or User required"))

    if not orders:
        return {"success": True, "count": 0, "orders": []}

    result = []
    for order in orders:
        doc = frappe.get_doc("Portal Order", order["name"])
        
        
        items = _serialize_items(
            doc.items,
            status_filter="Ordered"
        ) 

        if not items:
            continue
        
        result.append({
            "name": doc.name,
            "customer": doc.customer,
            "order_by": getattr(doc, "order_by", "") or "",
            "order_date": str(doc.order_date) if doc.order_date else "",
            "status": doc.status,
            "total_quantity": doc.total_quantity,
            "total_amount": doc.total_amount,
            # "items": _serialize_items(doc.items, status_filter="Ordered"), 
            "items": items,
        })

    return {"success": True, "count": len(result), "orders": result}


def _serialize_items(items, status_filter=None):
    """
    Child table rows ko clean dict list mein convert karo.
 
    status_filter:
        - Pass karo toh sirf us status ki rows aayengi  (e.g. "Add To Cart")
        - None ho toh sab aayengi except "Cancel Order" wali rows
    """
    result = []
    for row in items:
        row_status = getattr(row, "status", "Add To Cart") or "Add To Cart"
 
        # ── Status filter ──────────────────────────────────────────────────────
        if status_filter:
            if row_status != status_filter:
                continue
        else:
            if row_status in ("Cancel Order", "Cancelled"):
                continue
            
 
        # ── Item & BOM extra data ──────────────────────────────────────────────
        item_data = frappe.db.get_value(
            "Item",
            row.item_code,
            ["image", "name", "item_group","custom_catalogue_image", "custom_silver_image","sketch_image", "front_view"],
            as_dict=True,
        ) or {}
        
        # item_image = (
        #     item_data.get("custom_catalogue_image")
        #     or
        #     item_data.get("custom_silver_image")
        # )
        
        # if not item_image:
        #     continue 
            
 
        bom_data = frappe.db.get_value(
            "BOM",
            row.bom,
            ["gross_weight", "metal_and_finding_weight", "total_diamond_weight_in_gms", "metal_touch"],
            as_dict=True,
        ) or {}
 
        result.append({
            "name"                        : row.name,
            "item_code"                   : row.item_code or "",
            "bom"                         : row.bom or "",
            "uom"                         : row.uom or "",
            "quantity"                    : row.quantity or 0,
            "rate"                        : row.rate or 0,
            "amount"                      : (row.quantity or 0) * (row.rate or 0),
            "custom_catalogue_image"      : item_data.get("custom_catalogue_image") or "",
            "custom_silver_image"         : item_data.get("custom_silver_image") or "",
            "image"                       : item_data.get("image") or "",
            "cad_image"                   : item_data.get("front_view") or "",
            "sketch_image"                : item_data.get("sketch_image") or "",
            
            # "custom_catalogue_image"      : (item_data.get("custom_catalogue_image") or item_data.get("custom_silver_image")),
            # "custom_catalogue_image"      : item_image,
            "category"                    : item_data.get("item_group") or "",
            "gross_weight"                : bom_data.get("gross_weight") or "",
            "net_weight"                  : bom_data.get("metal_and_finding_weight") or "",
            "total_diamond_weight_in_gms" : bom_data.get("total_diamond_weight_in_gms") or "",
            "metal_touch"                 : bom_data.get("metal_touch") or "",
            "user"                        : getattr(row, "user", "") or "",
            "status"                      : row_status,
            "design"                      : "Customized" if (getattr(row, "as_per_customization", 0) or 0) else "As Per Design",
            "as_per_design"               : getattr(row, "as_per_design", 0) or 0,
            "as_per_customization"        : getattr(row, "as_per_customization", 0) or 0,
            "customized_data"             : row.customized_data or "",
            "job_work"                    : getattr(row, "job_work", 0) or 0,
            "out_right"                   : getattr(row, "out_right", 0) or 0,
            "hybrid"                      : getattr(row, "hybrid", 0) or 0,
        })
    return result


@frappe.whitelist()
def cancel_order(order_name):
    """Cancel complete Portal Order"""

    doc = frappe.get_doc("Portal Order", order_name)

    if doc.status == "Cancel Order":
        frappe.throw(_("Order already cancelled"))

    doc.status = "Cancel Order"

    customer_item_array = []

    for row in doc.items:
        row.status = "Cancel Order"

        customer_item_array.append({
            "item_code": row.item_code,
            "bom": row.bom,
            "quantity": row.quantity
        })

    send_customer_order_notification(
        user=doc.customer,
        order_id=doc.name,
        customer_item_array=customer_item_array
    )

    _recalculate_totals_draft_only(doc)

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "success": True,
        "order": doc.name,
        "message": "Order cancelled successfully"
    }

# #  GET PLACED ORDERS  (Ordered)
# # ─────────────────────────────────────────────
def _recalculate_totals_draft_only(doc):
    """Only Draft items total calculate """
    total_qty = 0
    total_amt = 0
    for row in doc.items:
        # Cancelled items skip 
        if getattr(row, "status", "Draft") == "Cancel Order":
            continue
        total_qty += row.quantity or 0
        total_amt += (row.quantity or 0) * (row.rate or 0)
    doc.total_quantity = total_qty
    doc.total_amount = total_amt


@frappe.whitelist()
def send_customer_order_notification(user, order_id, customer_item_array):
    """
    Send order update mail notification to user

    user: user email/id
    order_id: order reference
    customer_item_array: list of items
    """

    items_html = ""
        
    for item in customer_item_array:
        
        items_html += build_item_row(
            item.get('item_code'),
            item.get('bom'),
            item.get('quantity')
    )


    # find representative of the customer
    
    customer = frappe.get_doc("Customer", user)
    
    representatives = customer.custom_customer_representatives
    
    customer = customer.customer_name

    users = [u.user_id for u in representatives]

    message = get_email_template(customer, order_id, items_html)
    
    frappe.sendmail(
        recipients="bhavika_p@gkexport.com",
        sender="customer_portal@gkexport.com",
        subject=f"Order Update - {order_id}",
        message=message
    )


    return {
        "status": "sent",
        "user": user,
        "order_id": order_id
    }

    
def get_email_template(customer, order_id, items_html):
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; overflow: hidden;">
      
      <!-- Header -->
      <div style="background: #1a1a2e; padding: 32px 32px 24px; text-align: center;">
        <span style="display: inline-block; background: #fee2e2; color: #b91c1c; font-size: 12px; font-weight: 600; padding: 4px 14px; border-radius: 99px; margin-bottom: 12px;">&#x2715; Order Cancelled</span>
        <h2 style="color: #ffffff; font-size: 22px; font-weight: 600; margin: 0 0 4px;">Order Update</h2>
      </div>

      <!-- Body -->
      <div style="padding: 32px;">
        <p style="font-size: 15px; color: #111827; margin: 0 0 8px;">Hello,</p>
        <p style="font-size: 14px; color: #6b7280; margin: 0 0 24px; line-height: 1.6;">
          {customer} Your order <strong style="color: #111827;">{order_id}</strong> has been 
          <strong style="color: #b91c1c;">cancelled successfully.</strong>
        </p>

        <!-- Order info strip -->
        <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 16px; display: flex; justify-content: space-between; margin-bottom: 24px;">
          <div>
            <div style="font-size: 11px; color: #9ca3af;">Order ID</div>
            <div style="font-size: 15px; font-weight: 600; color: #111827;">{order_id}</div>
          </div>
          <div style="text-align: right;">
            <div style="font-size: 11px; color: #9ca3af;">Status</div>
            <div style="font-size: 15px; font-weight: 600; color: #b91c1c;">Cancelled</div>
          </div>
        </div>

        <!-- Items heading -->
        <div style="font-size: 11px; font-weight: 600; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 10px;">Items in order</div>

        <!-- Items table -->
        # <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
        #   <thead>
        #     <tr style="border-bottom: 1px solid #e5e7eb;">
        #       <th style="font-size: 11px; color: #9ca3af; text-align: left; padding: 0 12px 10px; text-transform: uppercase; letter-spacing: 0.05em;">Item</th>
        #       <th style="font-size: 11px; color: #9ca3af; text-align: left; padding: 0 12px 10px; text-transform: uppercase; letter-spacing: 0.05em;">BOM</th>
        #       <th style="font-size: 11px; color: #9ca3af; text-align: right; padding: 0 12px 10px; text-transform: uppercase; letter-spacing: 0.05em;">Qty</th>
        #     </tr>
        #   </thead>
        #   <tbody>
        #     {items_html}
        #   </tbody>
        # </table>
      </div>

      <!-- Footer -->
      <div style="border-top: 1px solid #e5e7eb; background: #f9fafb; padding: 20px 32px; text-align: center;">
        <p style="font-size: 13px; color: #9ca3af; margin: 0;">Thank you — <strong style="color: #6b7280;">GK Export</strong></p>
      </div>

    </div>
    """

def build_item_row(item_code, bom, qty):
    return f"""
    <tr style="border-bottom: 1px solid #f3f4f6;">
      <td style="padding: 12px;">
        <span style="font-family: monospace; font-size: 12px; color: #1d4ed8; background: #eff6ff; padding: 2px 8px; border-radius: 4px;">{item_code}</span>
      </td>
      <td style="padding: 12px; font-size: 13px; color: #6b7280;">{bom}</td>
      <td style="padding: 12px; text-align: right;">
        <span style="display: inline-block; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; font-size: 13px; font-weight: 600; padding: 2px 10px; color: #111827;">{qty}</span>
      </td>
    </tr>
    """