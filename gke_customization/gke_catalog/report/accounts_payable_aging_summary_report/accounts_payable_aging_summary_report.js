// Accounts Payable Aging Summary Report
// Summary tables are built from the report rows (Python does the AP logic + bucketing).

const AP_AGING_REPORT = "Accounts Payable Aging Summary Report";
const AP_OVERDUE = ["1-30", "31-60", "61-90", "91-120", "120+"];
const AP_UPCOMING = ["Due Today", "1-30", "31-60", "61-90", "91+"];

frappe.query_reports[AP_AGING_REPORT] = {
	filters: [
		{
			fieldname: "supplier_type",
			label: __("Supplier"),
			fieldtype: "Select",
			options: "All Suppliers\nDiamond",
			default: "All Suppliers",
			reqd: 1,
		},
	],

	onload(report) {
		// query-report page is shared by all reports: remove our summary when leaving
		frappe.router.on("change", () => {
			const route = frappe.get_route() || [];
			if (route[0] !== "query-report" || route[1] !== AP_AGING_REPORT) {
				$(".ap-aging-sd").remove();
			}
		});
	},

	after_datatable_render() {
		ap_aging_render_summary();
	},
};

const AP_TYPES = [
	"Purchase Invoices",
	"Debit Notes / Returns",
	"Advance Payments (Not Adjusted)",
	"Journal Entries",
	"Others",
];

function ap_aging_entry_type(d) {
	const amt = flt(d.outstanding);
	if (d.voucher_type === "Purchase Invoice") {
		return amt >= 0 ? "Purchase Invoices" : "Debit Notes / Returns";
	}
	if (d.voucher_type === "Payment Entry") return "Advance Payments (Not Adjusted)";
	if (d.voucher_type === "Journal Entry") return "Journal Entries";
	return "Others";
}

function ap_aging_fmt(value, decimals) {
	return format_number(value || 0, null, decimals);
}

function ap_aging_compute(data) {
	const s = {
		total: { count: 0, amount: 0 },
		overdue_total: { count: 0, amount: 0 },
		upcoming_total: { count: 0, amount: 0 },
		overdue: {},
		upcoming: {},
		months: {},
		types: {},
		adv: {},
	};
	AP_TYPES.forEach((t) => (s.types[t] = { count: 0, amount: 0 }));
	AP_OVERDUE.forEach((b) => (s.overdue[b] = { count: 0, amount: 0 }));
	AP_UPCOMING.forEach((b) => (s.upcoming[b] = { count: 0, amount: 0 }));

	(data || []).forEach((d) => {
		if (!d || !d.voucher_no) return;
		const amt = flt(d.outstanding);
		const add = (o) => {
			o.count += 1;
			o.amount += amt;
		};

		add(s.total);
		const etype = ap_aging_entry_type(d);
		add(s.types[etype]);
		if (etype === "Advance Payments (Not Adjusted)") {
			if (!s.adv[d.supplier]) {
				s.adv[d.supplier] = { name: d.supplier_name || "", count: 0, amount: 0 };
			}
			add(s.adv[d.supplier]);
		}
		if (d.status === "Overdue") {
			add(s.overdue_total);
			add(s.overdue[d.bucket]);
		} else {
			add(s.upcoming_total);
			add(s.upcoming[d.bucket]);
		}

		if (!s.months[d.due_month_key]) {
			s.months[d.due_month_key] = { label: d.due_month, count: 0, amount: 0 };
		}
		add(s.months[d.due_month_key]);
	});
	return s;
}

function ap_aging_style() {
	return `<style>
		.ap-aging-sd { padding: 10px 15px 20px; }
		.ap-aging-sd table { border-collapse: collapse; margin-bottom: 24px; font-size: 13px; }
		.ap-aging-sd th, .ap-aging-sd td { border: 1px solid #9fc3e0; padding: 10px 16px; }
		.ap-aging-sd .ap-title { background: #b9d6ee; text-align: center; font-weight: 700;
			letter-spacing: 1px; font-size: 14px; padding: 16px; }
		.ap-aging-sd .ap-title span { font-weight: 600; letter-spacing: 0; }
		.ap-aging-sd th { background: #c9e0f3; text-align: center; font-weight: 700; }
		.ap-aging-sd td { text-align: right; }
		.ap-aging-sd td.ap-label { text-align: left; font-weight: 700; background: #e3eff9; }
		.ap-aging-sd .ap-red { background: #f8dde2; color: #a3182e; font-weight: 700; }
		.ap-aging-sd .ap-green { background: #e2f3e0; color: #1d6b1d; font-weight: 700; }
		.ap-aging-sd .ap-bold { font-weight: 700; }
		.ap-aging-sd tr.ap-total td { background: #b9d6ee; font-weight: 700; }
		.ap-aging-sd .ap-actions { margin-bottom: 12px; }
		.ap-aging-sd .ap-actions .btn { margin-right: 8px; }
		.ap-aging-sd .ap-breakdown-link { color: inherit; cursor: pointer;
			text-decoration: underline dotted; text-underline-offset: 3px; }
		/* detail datatable hidden unless "Show Details" is on */
		.ap-aging-sd:not(.ap-show-details) ~ .ap-detail-table { display: none !important; }
	</style>`;
}

function ap_aging_html(s, filters) {
	const asOn = frappe.datetime.str_to_user(frappe.datetime.get_today());
	const supp = filters.supplier_type || "All Suppliers";
	const company = (frappe.query_report.data || []).find((d) => d && d.company);
	filters = Object.assign({}, filters, { company: company ? company.company : "" });
	const amt0 = (v) => ap_aging_fmt(v, 0);
	const amt2 = (v) => ap_aging_fmt(v, 2);

	// 1. Aging summary
	let h1 = "", c1 = "", a1 = "";
	AP_OVERDUE.forEach((b) => {
		h1 += `<th>${b === "120+" ? "120+ Days" : b + " Days"}<br>Overdue</th>`;
		c1 += `<td>${s.overdue[b].count}</td>`;
		a1 += `<td>${amt0(s.overdue[b].amount)}</td>`;
	});
	const aging = `
		<table>
			<tr><td class="ap-title" colspan="9">ACCOUNTS PAYABLE AGING SUMMARY
				<span>&nbsp;(Aging as on ${asOn} | Supplier: ${supp} | ${frappe.utils.escape_html(filters.company || "")})</span></td></tr>
			<tr><th>Metric</th><th>Total<br>Payable</th>${h1}
				<th class="ap-red">Total<br>Overdue</th><th class="ap-green">Open<br>(Not Yet Due)</th></tr>
			<tr><td class="ap-label">Headcount (Invoices)</td><td class="ap-bold">${s.total.count}</td>${c1}
				<td class="ap-red">${s.overdue_total.count}</td><td class="ap-green">${s.upcoming_total.count}</td></tr>
			<tr><td class="ap-label">Total Amount</td><td class="ap-bold"><a class="ap-breakdown-link" title="Click to see breakdown">${amt0(s.total.amount)}</a></td>${a1}
				<td class="ap-red">${amt0(s.overdue_total.amount)}</td><td class="ap-green">${amt0(s.upcoming_total.amount)}</td></tr>
		</table>`;

	// 2. Upcoming due summary
	let h2 = "", c2 = "", a2 = "";
	AP_UPCOMING.forEach((b) => {
		h2 += `<th>${b === "Due Today" ? "Due<br>Today" : "Due in " + b + "<br>Days"}</th>`;
		c2 += `<td>${s.upcoming[b].count}</td>`;
		a2 += `<td>${amt0(s.upcoming[b].amount)}</td>`;
	});
	const upcoming = `
		<table>
			<tr><td class="ap-title" colspan="7">UPCOMING DUE SUMMARY (NOT YET DUE)</td></tr>
			<tr><th>Metric</th><th class="ap-green">Total<br>Upcoming</th>${h2}</tr>
			<tr><td class="ap-label">Headcount (Invoices)</td><td class="ap-green">${s.upcoming_total.count}</td>${c2}</tr>
			<tr><td class="ap-label">Total Amount</td><td class="ap-green">${amt0(s.upcoming_total.amount)}</td>${a2}</tr>
		</table>`;

	// 3. Month-wise (by due date)
	let mrows = "";
	Object.keys(s.months)
		.sort()
		.forEach((k) => {
			const m = s.months[k];
			mrows += `<tr><td class="ap-label">${m.label}</td><td>${m.count}</td><td class="ap-bold">${amt2(m.amount)}</td></tr>`;
		});
	const monthly = `
		<table>
			<tr><th>Metric</th><th>Headcount (Invoices)</th><th>Total Amount Payable</th></tr>
			${mrows}
			<tr class="ap-total"><td class="ap-label" style="background:#b9d6ee">Total Payable</td>
				<td>${s.total.count}</td><td>${amt2(s.total.amount)}</td></tr>
		</table>`;

	return aging + upcoming + monthly;
}

const AP_TYPE_REASON = {
	"Purchase Invoices": "Supplier bills whose payment is still pending. Adds to payable (+).",
	"Debit Notes / Returns": "Goods returned to supplier. Reduces payable (−).",
	"Advance Payments (Not Adjusted)":
		"Money paid to supplier before / without linking to a bill (incl. payments booked in a separate advance account). Reduces payable (−) until adjusted against an invoice.",
	"Journal Entries": "Manual entries in supplier account (e.g. expense bills, opening balance). Can be + or −.",
	"Others": "Any other voucher type in supplier account.",
};

// Popup content: what makes up Total Payable, with reasons
function ap_aging_breakdown_html(s) {
	const amt2 = (v) => ap_aging_fmt(v, 2);
	const esc = (v) => frappe.utils.escape_html(v || "");

	let trows = "";
	AP_TYPES.forEach((t) => {
		if (!s.types[t].count) return;
		trows += `<tr><td class="ap-label">${t}</td><td>${s.types[t].count}</td>
			<td class="ap-bold">${amt2(s.types[t].amount)}</td>
			<td style="text-align:left;font-size:12px">${AP_TYPE_REASON[t]}</td></tr>`;
	});

	let html = `<div class="ap-aging-sd">${ap_aging_style()}
		<table style="width:100%">
			<tr><td class="ap-title" colspan="4">TOTAL PAYABLE BREAKDOWN</td></tr>
			<tr><th>Entry Type</th><th>Headcount</th><th>Outstanding Amount</th><th>Reason</th></tr>
			${trows}
			<tr class="ap-total"><td class="ap-label" style="background:#b9d6ee">Total Payable</td>
				<td>${s.total.count}</td><td>${amt2(s.total.amount)}</td><td></td></tr>
		</table>`;

	// Why this differs from Purchase Invoice list outstanding
	const pi_amt = s.types["Purchase Invoices"].amount + s.types["Debit Notes / Returns"].amount;
	const other_amt = s.total.amount - pi_amt;
	html += `<table style="width:100%">
		<tr><td class="ap-title" colspan="2">WHY IS THIS DIFFERENT FROM PURCHASE INVOICE OUTSTANDING?</td></tr>
		<tr><td class="ap-label">Purchase Invoice Outstanding (Invoices + Debit Notes)</td><td class="ap-bold">${amt2(pi_amt)}</td></tr>
		<tr><td class="ap-label">+ Advances &amp; Journal Entries (not in Purchase Invoice list)</td><td class="ap-bold">${amt2(other_amt)}</td></tr>
		<tr class="ap-total"><td class="ap-label" style="background:#b9d6ee">= Total Payable (this report)</td><td>${amt2(s.total.amount)}</td></tr>
		<tr><td colspan="2" style="text-align:left;font-size:12px;line-height:1.6">
			1. Purchase Invoice list shows only bills. This report also includes advance payments and journal entries,
			because they change how much we actually owe the supplier.<br>
			2. This report uses the supplier's <b>current</b> Supplier Group (from Supplier master). The Purchase Invoice list
			filters on the group saved on each invoice, so if a supplier's group was changed later, its older invoices
			can be missing there.<br>
			3. Advances booked in a separate advance account are counted here, but not in a plain Creditors / Payable ledger total.
		</td></tr>
	</table>`;

	const advKeys = Object.keys(s.adv).sort((a, b) => s.adv[a].amount - s.adv[b].amount);
	if (advKeys.length) {
		let arows = "";
		advKeys.forEach((k) => {
			const a = s.adv[k];
			arows += `<tr><td style="text-align:left">${esc(k)}</td><td style="text-align:left">${esc(a.name)}</td>
				<td>${a.count}</td><td class="ap-bold">${amt2(a.amount)}</td></tr>`;
		});
		html += `<table style="width:100%">
			<tr><td class="ap-title" colspan="4">SUPPLIER-WISE ADVANCES (NOT ADJUSTED)</td></tr>
			<tr><th>Supplier</th><th>Supplier Name</th><th>Payments</th><th>Advance Amount</th></tr>
			${arows}
		</table>`;
	}
	return html + "</div>";
}

function ap_aging_render_summary() {
	const qr = frappe.query_report;
	if (!qr || qr.report_name !== AP_AGING_REPORT) return;

	let $wrap = qr.page.main.find(".ap-aging-sd");
	if (!$wrap.length) {
		$wrap = $('<div class="ap-aging-sd"></div>');
		qr.$report.before($wrap);
	}
	qr.$report.addClass("ap-detail-table");
	const showing = $wrap.hasClass("ap-show-details");

	const filters = qr.get_filter_values();
	const s = ap_aging_compute(qr.data);
	const tables = ap_aging_html(s, filters);

	$wrap.html(`${ap_aging_style()}
		<div class="ap-actions"><button class="btn btn-danger btn-sm ap-pdf">
			${frappe.utils.icon("down-arrow", "xs")} Download PDF</button>
			<button class="btn btn-default btn-sm ap-toggle">${showing ? "Hide Details" : "Show Details"}</button></div>
		<div class="ap-tables">${tables}</div>`);

	$wrap.find(".ap-breakdown-link").on("click", () => {
		const d = new frappe.ui.Dialog({
			title: __("Total Payable Breakdown"),
			size: "extra-large",
			fields: [{ fieldtype: "HTML", fieldname: "breakdown" }],
		});
		d.fields_dict.breakdown.$wrapper.html(ap_aging_breakdown_html(s));
		d.show();
	});

	$wrap.find(".ap-toggle").on("click", (e) => {
		$wrap.toggleClass("ap-show-details");
		const on = $wrap.hasClass("ap-show-details");
		$(e.currentTarget).text(on ? "Hide Details" : "Show Details");
	});

	$wrap.find(".ap-pdf").on("click", () => {
		const html = `${ap_aging_style()}<div class="ap-aging-sd">${tables}</div>`;
		if (typeof frappe.render_pdf === "function") {
			frappe.render_pdf(html, { orientation: "Landscape" });
		} else {
			const w = window.open("");
			w.document.write(`<html><head><title>${AP_AGING_REPORT}</title></head><body>${html}</body></html>`);
			w.document.close();
			w.print();
		}
	});
}