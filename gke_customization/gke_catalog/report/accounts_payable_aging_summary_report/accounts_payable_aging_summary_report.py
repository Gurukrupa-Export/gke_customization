# Copyright (c) 2026
# Accounts Payable Aging Summary - Script Report (Purchase Invoice)
# Report page par Excel jaisa layout (HTML) + "Download PDF" button

from urllib.parse import urlencode

import frappe
from frappe.utils import date_diff, flt, formatdate, get_url, getdate, nowdate
from frappe.utils.pdf import get_pdf

DEFAULT_COMPANY = "Sadguru Diamond"

# Supplier Type filter: "All Suppliers" (default) ya "Diamonds"
# Diamonds = supplier ke NAAM me "Diamond" word aaye (Diamond / Diamonds dono pakde jaate hain)
DIAMOND_KEYWORD = "Diamond"
MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


# ------------------------------------------------------------------ entry
def execute(filters=None):
    filters = frappe._dict(filters or {})
    company = DEFAULT_COMPANY
    as_on = getdate(nowdate())
    supplier_type = get_supplier_type(filters.get("supplier_type"))

    summary = build_summary(get_invoices(company, supplier_type), as_on)
    link = "/api/method/{0}.download_pdf?{1}".format(
        __name__, urlencode({"supplier_type": supplier_type}))

    # Frappe ko ek column + ek row chahiye; asli report neeche message (HTML) me hai
    columns = [{"label": " ", "fieldname": "x", "fieldtype": "Data", "width": 10}]
    data = [{"x": ""}]
    return columns, data, build_html(summary, company, as_on, link, supplier_type)


# ------------------------------------------------------------------- data
def get_supplier_type(value):
    return "Diamonds" if value == "Diamonds" else "All Suppliers"


def get_invoices(company, supplier_type="All Suppliers"):
    conditions = ""
    values = {"company": company}
    if supplier_type == "Diamonds":
        conditions = " and supplier_name like %(sname)s"
        values["sname"] = "%" + DIAMOND_KEYWORD + "%"

    return frappe.db.sql(
        """
        select name, supplier, supplier_name, posting_date, status, currency,
            grand_total, outstanding_amount,
            coalesce(due_date, posting_date) as due_date
        from `tabPurchase Invoice`
        where docstatus = 1
            and outstanding_amount > 0
            and company = %(company)s
        """ + conditions + """
        order by coalesce(due_date, posting_date), name
        """,
        values,
        as_dict=True,
    )


def od_index(days):
    """overdue bucket: 0 = 1-30, 1 = 31-60, 2 = 61-90, 3 = 91-120, 4 = 120+"""
    return 0 if days <= 30 else 1 if days <= 60 else 2 if days <= 90 else 3 if days <= 120 else 4


def up_index(ahead):
    """upcoming bucket: 0 = Due Today, 1 = 1-30, 2 = 31-60, 3 = 61-90, 4 = 91+"""
    return 0 if ahead == 0 else 1 if ahead <= 30 else 2 if ahead <= 60 else 3 if ahead <= 90 else 4


def bucket_keys(inv, as_on):
    """Ek invoice kin-kin cells me count hota hai (drill-down keys)."""
    due = getdate(inv.due_date)
    days = date_diff(as_on, due)
    keys = ["all", "m-%d-%02d" % (due.year, due.month)]
    if days <= 0:
        keys += ["open", "up%d" % up_index(-days)]
    else:
        keys += ["od_all", "od%d" % od_index(days)]
    return keys


def build_summary(invoices, as_on):
    # buckets: 0 = 1-30, 1 = 31-60, 2 = 61-90, 3 = 91-120, 4 = 120+
    cnt = [0, 0, 0, 0, 0]
    amt = [0.0, 0.0, 0.0, 0.0, 0.0]
    # upcoming buckets: 0 = Due Today, 1 = due in 1-30, 2 = 31-60, 3 = 61-90, 4 = 91+
    up_cnt = [0, 0, 0, 0, 0]
    up_amt = [0.0, 0.0, 0.0, 0.0, 0.0]
    open_cnt, open_amt = 0, 0.0
    total_cnt, total_amt = 0, 0.0
    months = {}

    for inv in invoices:
        a = flt(inv.outstanding_amount)
        total_cnt += 1
        total_amt += a

        due = getdate(inv.due_date)
        key = (due.year, due.month)
        c, s = months.get(key, (0, 0.0))
        months[key] = (c + 1, s + a)

        days = date_diff(as_on, due)  # > 0 => overdue
        if days <= 0:
            open_cnt += 1
            open_amt += a
            ahead = -days  # kitne din baad due hai
            uidx = up_index(ahead)
            up_cnt[uidx] += 1
            up_amt[uidx] += a
            continue
        idx = od_index(days)
        cnt[idx] += 1
        amt[idx] += a

    multi_year = len({k[0] for k in months}) > 1
    month_rows = []
    for (year, month) in sorted(months):
        c, a = months[(year, month)]
        label = MONTH_NAMES[month - 1] + (" %s" % year if multi_year else "")
        month_rows.append((label, c, a, year, month))

    return frappe._dict(
        cnt=cnt, amt=amt, up_cnt=up_cnt, up_amt=up_amt,
        open_cnt=open_cnt, open_amt=open_amt,
        total_cnt=total_cnt, total_amt=total_amt, month_rows=month_rows,
    )


def inr(x, dec=2):
    """Indian digit grouping: 1,78,05,86,124.97"""
    neg = x < 0
    x = abs(x)
    s = ("%." + str(dec) + "f") % x
    ip, _, fp = s.partition(".")
    if len(ip) > 3:
        last3, rest, groups = ip[-3:], ip[:-3], []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        ip = ",".join(groups) + "," + last3
    out = ip + ("." + fp if fp else "")
    return "-" + out if neg else out


# ------------------------------------------------------------- HTML layout
HEAD1 = [
    "Metric", "Total<br>Payable", "1 - 30 Days<br>Overdue", "31 - 60 Days<br>Overdue",
    "61 - 90 Days<br>Overdue", "91 - 120 Days<br>Overdue", "120+ Days<br>Overdue", "Total<br>Overdue",
    "Open<br>(Not Yet Due)",
]

HEAD2 = [
    "Metric", "Total<br>Upcoming", "Due<br>Today", "Due in 1 - 30<br>Days",
    "Due in 31 - 60<br>Days", "Due in 61 - 90<br>Days", "Due in 91+<br>Days",
]

# ---- colour palette: light blue tones (yahin se badal sakte hain)
PRIMARY = "#C2DCF2"     # header background (light blue)
PRIMARY2 = "#DAEAF8"    # title gradient end
TOTAL_BG = "#A8CBE9"    # Total Payable row
INK = "#000000"         # header / label text (black)
RED_BG = "#F5D0D4"      # Total Overdue header
RED_INK = "#8E2433"
RED = "#A32F3E"         # Total Overdue numbers
GREEN_BG = "#CFEBD6"    # Open header
GREEN_INK = "#1E6B38"
GREEN = "#1E7A3C"       # Open numbers
TINT = "#E2EEF9"        # label cells
ZEBRA = "#F2F8FD"       # alternate rows
TINT_RED = "#FDF1F2"
TINT_GREEN = "#EEF8EF"
LINE = "#C3D6E8"        # cell borders
CARD_LINE = "#9BBBD7"   # outer border
TEXT = "#000000"

FONT = ("font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif;"
        "font-size:14px;font-variant-numeric:tabular-nums;")
CELL = "border:1px solid %s;padding:10px 14px;white-space:nowrap;%s" % (LINE, FONT)


def hdr(bg=PRIMARY, align="center", ink=INK):
    return (CELL + "background:%s;color:%s;font-weight:700;text-align:%s;"
            "border-color:%s;line-height:1.35;" % (bg, ink, align, CARD_LINE))


def card(inner, extra=""):
    return (
        '<div class="ap-card" style="display:inline-block;vertical-align:top;overflow:hidden;'
        'border:1px solid %s;box-shadow:0 2px 10px rgba(0,0,0,.12);%s">%s</div>'
        % (CARD_LINE, extra, inner)
    )


# ------------------------------------------------------------- drill-down links
def inv_url(key, as_on, supplier_type="All Suppliers"):
    return get_url("/api/method/{0}.invoice_list?{1}".format(
        __name__, urlencode({"key": key, "as_on": str(as_on), "supplier_type": supplier_type})))


def linked(text, url, value):
    if not url or not value:            # 0 wale cell clickable nahi
        return text
    return (
        '<a href="%s" target="_blank" title="Invoices dekhein" '
        'style="color:inherit;text-decoration:none;border-bottom:1px dotted currentColor;">%s</a>'
        % (frappe.utils.escape_html(url), text)
    )


def build_tables(s, company, as_on, supplier_type="All Suppliers"):
    # table 1: Total Payable, 1-30, 31-60, 61-90, 91-120, 120+, Total Overdue, Open
    urls1 = [inv_url(k, as_on, supplier_type) for k in ["all", "od0", "od1", "od2", "od3", "od4", "od_all", "open"]]
    # upcoming: Total Upcoming, Due Today, 1-30, 31-60, 61-90, 91+
    urls_u = [inv_url(k, as_on, supplier_type) for k in ["open", "up0", "up1", "up2", "up3", "up4"]]

    # ---------- table 1
    t1 = ['<table style="border-collapse:collapse;table-layout:fixed;width:1330px;">']
    t1.append('<colgroup><col style="width:190px">' + '<col style="width:155px">' * 8 + "</colgroup>")
    t1.append(
        '<tr><td colspan="9" style="padding:16px;text-align:center;color:%s;font-weight:700;'
        'font-size:20px;letter-spacing:1.5px;%s background:%s;background:linear-gradient(90deg,%s,%s);">'
        "ACCOUNTS PAYABLE AGING SUMMARY"
        '<span style="font-size:14px;font-weight:600;letter-spacing:0.5px;margin-left:18px;">'
        "(Aging as on %s &nbsp;|&nbsp; Supplier: %s)</span></td></tr>"
        % (INK, FONT, TOTAL_BG, TOTAL_BG, PRIMARY2, formatdate(as_on), supplier_type)
    )

    head_bg = [(PRIMARY, INK)] * 7 + [(RED_BG, RED_INK), (GREEN_BG, GREEN_INK)]
    t1.append("<tr>" + "".join(
        '<td style="%s">%s</td>' % (hdr(head_bg[i][0], "left" if i == 0 else "center", head_bg[i][1]), h)
        for i, h in enumerate(HEAD1)) + "</tr>")

    def data_row(label, vals, dec, bg, urls):
        cells = '<td style="%sbackground:%s;color:%s;font-weight:700;text-align:left;">%s</td>' % (
            CELL, TINT, INK, label)
        for i, v in enumerate(vals):
            style = CELL + "background:%s;color:%s;text-align:right;font-weight:400;" % (bg, TEXT)
            if i == 0:                      # Total Payable
                style += "font-weight:700;color:%s;" % INK
            elif i == 5:                    # 120+ days
                style += "color:%s;font-weight:600;" % TEXT
            elif i == 6:                    # Total Overdue
                style += "background:%s;color:%s;font-weight:700;" % (TINT_RED, RED)
            elif i == 7:                    # Open
                style += "background:%s;color:%s;font-weight:700;" % (TINT_GREEN, GREEN)
            cells += '<td style="%s">%s</td>' % (style, linked(inr(v, dec), urls[i], v))
        return "<tr>" + cells + "</tr>"

    t1.append(data_row("Headcount (Invoices)",
                       [s.total_cnt] + s.cnt + [sum(s.cnt), s.open_cnt], 0, "#FFFFFF", urls1))
    t1.append(data_row("Total Amount",
                       [s.total_amt] + s.amt + [sum(s.amt), s.open_amt], 0, ZEBRA, [None] * 8))  # amount clickable nahi
    t1.append("</table>")

    # ---------- upcoming table (not yet due)
    tu = ['<table style="border-collapse:collapse;table-layout:fixed;width:1120px;">']
    tu.append('<colgroup><col style="width:190px">' + '<col style="width:155px">' * 6 + "</colgroup>")
    tu.append(
        '<tr><td colspan="7" style="padding:16px;text-align:center;color:%s;font-weight:700;'
        'font-size:20px;letter-spacing:1.5px;%s background:%s;background:linear-gradient(90deg,%s,%s);">'
        "UPCOMING DUE SUMMARY (NOT YET DUE)</td></tr>" % (INK, FONT, TOTAL_BG, TOTAL_BG, PRIMARY2)
    )
    head_bg_u = [(PRIMARY, INK), (GREEN_BG, GREEN_INK)] + [(PRIMARY, INK)] * 5
    tu.append("<tr>" + "".join(
        '<td style="%s">%s</td>' % (hdr(head_bg_u[i][0], "left" if i == 0 else "center", head_bg_u[i][1]), h)
        for i, h in enumerate(HEAD2)) + "</tr>")

    def up_row(label, vals, dec, bg, urls):
        cells = '<td style="%sbackground:%s;color:%s;font-weight:700;text-align:left;">%s</td>' % (
            CELL, TINT, INK, label)
        for i, v in enumerate(vals):
            style = CELL + "background:%s;color:%s;text-align:right;font-weight:400;" % (bg, TEXT)
            if i == 0:                      # Total Upcoming
                style += "background:%s;color:%s;font-weight:700;" % (TINT_GREEN, GREEN)
            cells += '<td style="%s">%s</td>' % (style, linked(inr(v, dec), urls[i], v))
        return "<tr>" + cells + "</tr>"

    tu.append(up_row("Headcount (Invoices)", [s.open_cnt] + s.up_cnt, 0, "#FFFFFF", urls_u))
    tu.append(up_row("Total Amount", [s.open_amt] + s.up_amt, 0, ZEBRA, [None] * 6))  # amount clickable nahi
    tu.append("</table>")

    # ---------- table 2 (month-wise)
    t2 = ['<table style="border-collapse:collapse;table-layout:fixed;width:595px;">']
    t2.append('<colgroup><col style="width:190px"><col style="width:195px"><col style="width:210px"></colgroup>')
    t2.append(
        "<tr>"
        '<td style="%s">Metric</td>'
        '<td style="%s">Headcount (Invoices)</td>'
        '<td style="%s">Total Amount Payable</td></tr>'
        % (hdr(PRIMARY, "left"), hdr(PRIMARY, "right"), hdr(PRIMARY, "right"))
    )
    m_cnt, m_amt = 0, 0.0
    for n, (label, c, a, yr, mo) in enumerate(s.month_rows):
        m_url = inv_url("m-%d-%02d" % (yr, mo), as_on, supplier_type)
        m_cnt += c
        m_amt += a
        bg = "#FFFFFF" if n % 2 == 0 else ZEBRA
        t2.append(
            '<tr><td style="%sbackground:%s;color:%s;font-weight:700;text-align:left;">%s</td>'
            '<td style="%sbackground:%s;color:%s;text-align:right;">%s</td>'
            '<td style="%sbackground:%s;color:%s;font-weight:700;text-align:right;">%s</td></tr>'
            % (CELL, TINT, INK, label,
               CELL, bg, TEXT, linked(inr(c, 0), m_url, c),
               CELL, bg, TEXT, inr(a, 2))
        )
    tot = CELL + "background:%s;color:%s;font-weight:700;border-color:%s;" % (TOTAL_BG, INK, CARD_LINE)
    t2.append(
        '<tr><td style="%stext-align:left;">Total Payable</td>'
        '<td style="%stext-align:right;">%s</td>'
        '<td style="%stext-align:right;">%s</td></tr>'
        % (tot, tot, linked(inr(m_cnt, 0), inv_url("all", as_on, supplier_type), m_cnt),
           tot, inr(m_amt, 2))
    )
    t2.append("</table>")

    gap = '<div style="height:32px"></div>'
    return card("".join(t1)) + gap + card("".join(tu)) + gap + card("".join(t2))


def build_html(s, company, as_on, link, supplier_type="All Suppliers"):
    btn = (
        '<a href="%s" target="_blank" style="display:inline-block;background:#B3261E;color:#fff;font-weight:700;'
        "%spadding:8px 18px;text-decoration:none;margin-bottom:10px;"
        'box-shadow:0 1px 3px rgba(0,0,0,.2);">&#11015;&nbsp; Download PDF</a>' % (link, FONT)
    )
    css = (
        "<style>"
        ".report-wrapper:has(.ap-aging-excel) .datatable,"
        ".report-wrapper:has(.ap-aging-excel) .report-summary,"
        ".report-wrapper:has(.ap-aging-excel) .chart-wrapper{display:none !important;}"
        "</style>"
    )
    return (
        css + '<div class="ap-aging-excel" style="overflow-x:auto;padding:8px 4px 24px;">'
        + btn + build_tables(s, company, as_on, supplier_type) + "</div>"
    )


# ------------------------------------------------------------- PDF download
@frappe.whitelist()
def download_pdf(supplier_type=None):
    frappe.has_permission("Purchase Invoice", "read", throw=True)

    company = DEFAULT_COMPANY
    as_on = getdate(nowdate())
    supplier_type = get_supplier_type(supplier_type)
    s = build_summary(get_invoices(company, supplier_type), as_on)

    html = (
        '<!DOCTYPE html><html><head><meta charset="utf-8"><style>'
        "*{-webkit-print-color-adjust:exact;print-color-adjust:exact;}"
        "body{margin:0;background:#fff;}"
        ".ap-card{page-break-inside:avoid;}"
        "</style></head><body>"
        + build_tables(s, company, as_on, supplier_type)
        + "</body></html>"
    )
    pdf = get_pdf(html, {
        "orientation": "Landscape",
        "page-size": "A4",
        "zoom": "0.75",          # 1330px wali table A4 landscape me fit karne ke liye
        "margin-top": "10mm",
        "margin-bottom": "10mm",
        "margin-left": "8mm",
        "margin-right": "8mm",
    })

    suffix = "_Diamonds" if supplier_type == "Diamonds" else ""
    frappe.response["filename"] = "AP_Aging_Summary{0}_{1}.pdf".format(suffix, str(as_on))
    frappe.response["filecontent"] = pdf
    frappe.response["type"] = "download"


# --------------------------------------------------------- drill-down page
BUCKET_LABELS = {
    "all": "Total Payable",
    "od_all": "Total Overdue",
    "od0": "1 - 30 Days Overdue",
    "od1": "31 - 60 Days Overdue",
    "od2": "61 - 90 Days Overdue",
    "od3": "91 - 120 Days Overdue",
    "od4": "120+ Days Overdue",
    "open": "Open (Not Yet Due)",
    "up0": "Due Today",
    "up1": "Due in 1 - 30 Days",
    "up2": "Due in 31 - 60 Days",
    "up3": "Due in 61 - 90 Days",
    "up4": "Due in 91+ Days",
}


@frappe.whitelist()
def invoice_list(key, as_on=None, supplier_type=None):
    """Report ke kisi bhi cell pe click -> us cell ke SAARE invoices (no pagination)."""
    frappe.has_permission("Purchase Invoice", "read", throw=True)

    company = DEFAULT_COMPANY
    as_on = getdate(as_on or nowdate())
    supplier_type = get_supplier_type(supplier_type)

    if key in BUCKET_LABELS:
        label = BUCKET_LABELS[key]
    elif key.startswith("m-") and len(key) == 9:
        y, m = int(key[2:6]), int(key[7:9])
        label = "Due in %s %s" % (MONTH_NAMES[m - 1], y)
    else:
        frappe.throw("Invalid bucket")

    rows = [inv for inv in get_invoices(company, supplier_type) if key in bucket_keys(inv, as_on)]

    th = ("border:1px solid %s;padding:8px 10px;background:%s;color:%s;font-weight:700;"
          "white-space:nowrap;text-align:%%s;" % (CARD_LINE, PRIMARY, INK))
    td = "border:1px solid %s;padding:7px 10px;white-space:nowrap;text-align:%%s;" % LINE
    heads = [("#", "right"), ("Invoice", "left"), ("Supplier", "left"),
             ("Posting Date", "left"), ("Due Date", "left"), ("Days", "right"),
             ("Status", "left"), ("Currency", "left"), ("Grand Total", "right"),
             ("Outstanding", "right")]

    out = ['<table style="border-collapse:collapse;width:100%%;%s">' % FONT]
    out.append("<tr>" + "".join('<th style="%s">%s</th>' % (th % a, h) for h, a in heads) + "</tr>")

    total = 0.0
    for n, inv in enumerate(rows, 1):
        days = date_diff(as_on, getdate(inv.due_date))
        total += flt(inv.outstanding_amount)
        bg = "#FFFFFF" if n % 2 else ZEBRA
        inv_link = '<a href="/app/purchase-invoice/%s" target="_blank">%s</a>' % (
            frappe.utils.escape_html(inv.name), frappe.utils.escape_html(inv.name))
        cells = [
            (str(n), "right"),
            (inv_link, "left"),
            (frappe.utils.escape_html(inv.supplier_name or inv.supplier or ""), "left"),
            (formatdate(inv.posting_date), "left"),
            (formatdate(inv.due_date), "left"),
            (("%d overdue" % days) if days > 0 else ("in %d" % -days) if days < 0 else "today", "right"),
            (frappe.utils.escape_html(inv.status or ""), "left"),
            (frappe.utils.escape_html(inv.currency or ""), "left"),
            (inr(flt(inv.grand_total)), "right"),
            (inr(flt(inv.outstanding_amount)), "right"),
        ]
        out.append('<tr style="background:%s">' % bg
                   + "".join('<td style="%s">%s</td>' % (td % a, v) for v, a in cells) + "</tr>")

    out.append(
        '<tr style="background:%s;font-weight:700;"><td colspan="9" style="%s">Total (%d invoices)</td>'
        '<td style="%s">%s</td></tr>' % (TOTAL_BG, td % "right", len(rows), td % "right", inr(total))
    )
    out.append("</table>")

    head = (
        '<div style="%s margin-bottom:12px;"><b>%s</b> &nbsp;|&nbsp; Supplier: <b>%s</b> &nbsp;|&nbsp; %s '
        "&nbsp;|&nbsp; as on <b>%s</b>"
        " &nbsp;|&nbsp; <b>%d</b> invoices &nbsp;|&nbsp; Outstanding <b>%s</b></div>"
        % (FONT, frappe.utils.escape_html(company), supplier_type, label, formatdate(as_on),
           len(rows), inr(total))
    )
    frappe.respond_as_web_page(
        "AP Aging - " + label,
        head + '<div style="overflow-x:auto;">' + "".join(out) + "</div>",
        primary_action=None,
        width=1300,
    )