# gke_price_list/doctype/update_customer_diamond_criteria/__init__.py

def on_validate(doc, method):
    doc.update_items_in_diamond_criteria()
