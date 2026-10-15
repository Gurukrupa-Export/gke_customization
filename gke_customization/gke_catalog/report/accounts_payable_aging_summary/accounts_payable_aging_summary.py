# Copyright (c) 2026
# Accounts Payable Aging Summary (Standard Report, Purchase Invoice)

import frappe
from frappe.utils import fmt_money, today


def execute(filters=None):
    filters = frappe._dict(filters or {})
    as_of = filters.get("as_of_date") or today()

    cond = ""
    params = {"d": as_of}
    if filters.get("company"):
        cond += " AND company = %(company)s"
        params["company"] = filters.get("company")
    if filters.get("supplier"):
        cond += " AND supplier = %(supplier)s"
        params["supplier"] = filters.get("supplier")

    # amount in company currency, due date (fallback to posting date)
    amt = "(outstanding_amount * conversion_rate)"
    dd = "IFNULL(due_date, posting_date)"
    days = "DATEDIFF(%(d)s, {0})".format(dd)

    buckets = [
        ("b1", "{0} BETWEEN 1 AND 30".format(days)),
        ("b2", "{0} BETWEEN 31 AND 60".format(days)),
        ("b3", "{0} BETWEEN 61 AND 90".format(days)),
        ("b4", "{0} BETWEEN 91 AND 120".format(days)),
        ("b5", "{0} > 120".format(days)),
        ("nd", "{0} <= 0".format(days)),
    ]

    select_parts = [
        "COUNT(*) AS tot_c",
        "IFNULL(SUM({0}),0) AS tot_a".format(amt),
    ]
    for key, c in buckets:
        select_parts.append(
            "IFNULL(SUM(CASE WHEN {0} THEN 1 ELSE 0 END),0) AS {1}_c".format(c, key)
        )
        select_parts.append(
            "IFNULL(SUM(CASE WHEN {0} THEN {1} ELSE 0 END),0) AS {2}_a".format(c, amt, key)
        )

    s = frappe.db.sql(
        """
        SELECT {sel}
        FROM `tabPurchase Invoice`
        WHERE docstatus = 1 AND is_return = 0 AND outstanding_amount > 0 {c}
        """.format(sel=", ".join(select_parts), c=cond),
        params,
        as_dict=True,
    )[0]

    def f(v):
        return fmt_money(v, precision=2)

    # Total Overdue = 1-30 + 31-60 + 61-90 + 91-120 + 120+
    over_c = s.b1_c + s.b2_c + s.b3_c + s.b4_c + s.b5_c
    over_a = s.b1_a + s.b2_a + s.b3_a + s.b4_a + s.b5_a

    message = """
    <table class="table table-bordered text-center">
      <thead style="background:#2F3E56;color:#fff">
        <tr>
          <th>Metric</th><th>Total Payable</th>
          <th>1 - 30 Days<br>Overdue</th><th>31 - 60 Days<br>Overdue</th>
          <th>61 - 90 Days<br>Overdue</th><th>91 - 120 Days<br>Overdue</th>
          <th>120+ Days<br>Overdue</th><th>Total<br>Overdue</th>
          <th>Total<br>(Not Due Yet)</th>
        </tr>
      </thead>
      <tbody>
        <tr><td>Headcount (Invoices)</td><td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td><td>{4}</td><td>{5}</td><td>{6}</td><td><b>{7}</b></td></tr>
        <tr><td>Total Amount</td><td>{8}</td><td>{9}</td><td>{10}</td><td>{11}</td><td>{12}</td><td>{13}</td><td>{14}</td><td><b>{15}</b></td></tr>
      </tbody>
    </table>""".format(
        s.tot_c, s.b1_c, s.b2_c, s.b3_c, s.b4_c, s.b5_c, over_c, s.nd_c,
        f(s.tot_a), f(s.b1_a), f(s.b2_a), f(s.b3_a), f(s.b4_a), f(s.b5_a), f(over_a), f(s.nd_a),
    )

    # ---------- Month-wise table (due date month) ----------
    columns = [
        {"label": "Month (Due)", "fieldname": "metric", "fieldtype": "Data", "width": 150},
        {"label": "Headcount (Invoices)", "fieldname": "cnt", "fieldtype": "Int", "width": 160},
        {"label": "Total Amount Payable", "fieldname": "amt", "fieldtype": "Currency", "width": 200},
    ]

    rows = frappe.db.sql(
        """
        SELECT DATE_FORMAT({dd}, '%%b %%Y') AS metric,
               DATE_FORMAT({dd}, '%%Y-%%m') AS ym,
               COUNT(*) AS cnt,
               SUM({a}) AS amt
        FROM `tabPurchase Invoice`
        WHERE docstatus = 1 AND is_return = 0 AND outstanding_amount > 0 {c}
        GROUP BY ym, metric
        ORDER BY ym
        """.format(dd=dd, a=amt, c=cond),
        params,
        as_dict=True,
    )

    total_cnt = 0
    total_amt = 0
    for r in rows:
        total_cnt += r.cnt
        total_amt += r.amt

    rows.append({"metric": "Total Payable", "cnt": total_cnt, "amt": total_amt})

    return columns, rows, message