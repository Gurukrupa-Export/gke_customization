import frappe


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


# -----------------------------------
# Columns
# -----------------------------------
def get_columns():
    return [
        {"label": "Section", "fieldname": "section", "fieldtype": "Link", "options": "Tax Withholding Category", "width": 90},
        {"label": "Supplier", "fieldname": "supplier_name", "fieldtype": "Data", "width": 180},
        {"label": "PAN", "fieldname": "pan", "fieldtype": "Data", "width": 120},
        {"label": "Invoice No", "fieldname": "invoice_no", "fieldtype": "Link", "options": "Purchase Invoice", "width": 150},
        {"label": "Invoice Date", "fieldname": "invoice_date", "fieldtype": "Date", "width": 100},
        {"label": "Invoice Amount", "fieldname": "invoice_amount", "fieldtype": "Currency", "width": 130},
        {"label": "TDS Rate (%)", "fieldname": "tds_rate", "fieldtype": "Percent", "width": 110},
        {"label": "TDS Amount", "fieldname": "tds_amount", "fieldtype": "Currency", "width": 130},
    ]


# -----------------------------------
# Quarter Logic
# -----------------------------------
def get_quarter_dates(financial_year, quarter):
    start_year = int(financial_year.split("-")[0])
    end_year = start_year + 1
    if quarter == "Q1":
        return f"{start_year}-04-01", f"{start_year}-06-30"
    elif quarter == "Q2":
        return f"{start_year}-07-01", f"{start_year}-09-30"
    elif quarter == "Q3":
        return f"{start_year}-10-01", f"{start_year}-12-31"
    elif quarter == "Q4":
        return f"{end_year}-01-01", f"{end_year}-03-31"


# -----------------------------------
# Month Logic
# -----------------------------------
def get_month_dates(financial_year, month):
    start_year = int(financial_year.split("-")[0])
    end_year = start_year + 1

    month_map = {
        "April":     (start_year, 4),
        "May":       (start_year, 5),
        "June":      (start_year, 6),
        "July":      (start_year, 7),
        "August":    (start_year, 8),
        "September": (start_year, 9),
        "October":   (start_year, 10),
        "November":  (start_year, 11),
        "December":  (start_year, 12),
        "January":   (end_year, 1),
        "February":  (end_year, 2),
        "March":     (end_year, 3),
    }

    if month not in month_map:
        return None, None

    year, mn = month_map[month]
    mn_str = str(mn) if mn >= 10 else "0" + str(mn)
    first_day = f"{year}-{mn_str}-01"
    last_day = str(frappe.utils.get_last_day(first_day))
    return first_day, last_day


# -----------------------------------
# Main Data Logic
# -----------------------------------
def get_data(filters):
    # Priority Logic:
    # 1. Month selected   → Month dates use karo
    # 2. Quarter selected → Quarter dates use karo
    # 3. Dono blank       → Pure Financial Year ka data dikhao
    if filters.get("month"):
        from_date, to_date = get_month_dates(
            filters.get("financial_year"),
            filters.get("month")
        )
    elif filters.get("quarter"):
        from_date, to_date = get_quarter_dates(
            filters.get("financial_year"),
            filters.get("quarter")
        )
    else:
        start_year = int(filters.get("financial_year").split("-")[0])
        end_year = start_year + 1
        from_date = f"{start_year}-04-01"
        to_date = f"{end_year}-03-31"

    query = """
        SELECT
            pi.tax_withholding_category AS section,
            pi.supplier_name,
            s.pan,
            pi.name AS invoice_no,
            pi.posting_date AS invoice_date,
            pi.base_net_total AS invoice_amount,
            (
            SELECT tr.tax_withholding_rate
            FROM `tabTax Withholding Rate` tr
            WHERE tr.parent = twc.name
            ORDER BY tr.from_date DESC
            LIMIT 1
            ) AS tds_rate,
            IFNULL(SUM(gle.credit), 0) AS tds_amount
        FROM `tabPurchase Invoice` pi
        LEFT JOIN `tabSupplier` s
            ON pi.supplier = s.name
        LEFT JOIN `tabTax Withholding Category` twc
            ON pi.tax_withholding_category = twc.name
        LEFT JOIN `tabGL Entry` gle
            ON gle.voucher_no = pi.name
            AND gle.account LIKE %s
            AND gle.credit > 0
        WHERE pi.docstatus = 1
            AND pi.company = %s
            AND pi.posting_date BETWEEN %s AND %s
            AND pi.tax_withholding_category IS NOT NULL
            AND twc.tds_section NOT IN ('192', '192B')
        GROUP BY pi.name
        ORDER BY pi.posting_date ASC
    """
    values = (
        "%TDS%",
        filters.get("company"),
        from_date,
        to_date,
    )
    data = frappe.db.sql(query, values, as_dict=True)
    return data