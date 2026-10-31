frappe.pages["sadguru_dashboard"].on_page_load = function (wrapper) {
	new SadguruDashboard(wrapper);
};

class SadguruDashboard {
	constructor(wrapper) {
		this.company = "Sadguru Diamond";
		this.active_tab = "purchase";
		this.purchase_sort = { by: "amount", order: "desc" };
		this.sales_sort = { by: "amount", order: "desc" };
		this.sales_grade_sort = { by: "amount", order: "desc" };
		this.matrix_mode = "amount";
		this.matrix_month = "";

		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: "Sadguru Dashboard",
			single_column: true,
		});

		$(frappe.render_template("sadguru_dashboard", {})).appendTo(this.page.body);

		this.setup_filters();
		this.setup_tabs();
		this.setup_matrix_controls();
		this.refresh_all();
	}

	setup_tabs() {
		this.page.body.find(".sadguru-tab").on("click", (e) => {
			const tab = $(e.currentTarget).data("tab");
			this.active_tab = tab;
			this.page.body.find(".sadguru-tab").removeClass("active");
			$(e.currentTarget).addClass("active");
			this.page.body
				.find(".sadguru-tab-pane")
				.hide()
				.filter(`[data-tab-pane="${tab}"]`)
				.show();
			this.supplier_field.$wrapper.toggle(tab === "purchase");
			this.customer_field.$wrapper.toggle(tab === "sales");
			this.grade_field.$wrapper.toggle(tab === "sales");
			this.page.body
				.find(".sadguru-chart-title")
				.text(tab === "sales" ? "Sales — Month wise" : "Purchase — Month wise");
			this.page.body
				.find(".sadguru-qty-chart-title")
				.text(tab === "sales" ? "Sales — Ct Wt Month wise" : "Purchase — Ct Wt Month wise");
			this.load_kpis();
			this.load_chart();
		});
	}

	setup_filters() {
		const today = frappe.datetime.get_today();
		const month_start = frappe.datetime.month_start();

		this.period_type_field = this.page.add_field({
			fieldname: "period_type",
			label: "Period",
			fieldtype: "Select",
			options: ["Custom", "Month", "Quarter", "Financial Year"],
			default: "Custom",
			change: () => {
				const type = this.period_type_field.get_value();
				this.period_value_field.$wrapper.toggle(type !== "Custom");
				if (type !== "Custom") this.populate_period_values(type);
			},
		});

		this.period_value_field = this.page.add_field({
			fieldname: "period_value",
			label: "Select Period",
			fieldtype: "Select",
			options: [],
			change: () => this.apply_period_value(),
		});
		this.period_value_field.$wrapper.hide();

		this.from_date_field = this.page.add_field({
			fieldname: "from_date",
			label: "From Date",
			fieldtype: "Date",
			default: month_start,
			change: () => this.refresh_all(),
		});

		this.to_date_field = this.page.add_field({
			fieldname: "to_date",
			label: "To Date",
			fieldtype: "Date",
			default: today,
			change: () => this.refresh_all(),
		});

		this.supplier_field = this.page.add_field({
			fieldname: "supplier",
			label: "Supplier",
			fieldtype: "Link",
			options: "Supplier",
			change: () => {
				this.load_purchase();
				this.load_kpis();
				this.load_chart();
				this.load_trend_table();
			},
		});

		this.customer_field = this.page.add_field({
			fieldname: "customer",
			label: "Customer",
			fieldtype: "Link",
			options: "Customer",
			change: () => {
				this.load_sales();
				this.load_sales_grade();
				this.load_kpis();
				this.load_chart();
				this.load_matrix();
				this.load_trend_table();
			},
		});
		this.customer_field.$wrapper.hide();

		this.grade_field = this.page.add_field({
			fieldname: "grade",
			label: "Diamond Grade",
			fieldtype: "Link",
			options: "Attribute Value",
			get_query: () => ({ filters: { is_diamond_grade: 1 } }),
			change: () => {
				this.load_sales();
				this.load_kpis();
				this.load_chart();
				this.load_trend_table();
			},
		});
		this.grade_field.$wrapper.hide();
	}

	populate_period_values(type) {
		let values = [];
		let formatter = (v) => v;

		if (type === "Month") {
			values = sadguru_generate_month_options();
			formatter = sadguru_format_month;
		} else if (type === "Quarter") {
			values = sadguru_generate_quarter_options();
			formatter = sadguru_format_quarter;
		} else if (type === "Financial Year") {
			values = sadguru_generate_fy_options();
			formatter = sadguru_format_fy;
		}

		this.period_value_field.df.options = values.map((v) => ({ value: v, label: formatter(v) }));
		this.period_value_field.set_options();
		if (values.length) {
			this.period_value_field.set_value(values[0]);
		}
	}

	apply_period_value() {
		const type = this.period_type_field.get_value();
		const value = this.period_value_field.get_value();
		if (!value) return;

		const range = sadguru_period_to_range(type, value);
		if (!range) return;

		this.from_date_field.set_value(range.from).then(() => this.to_date_field.set_value(range.to));
	}

	get_dates() {
		return {
			from_date: this.from_date_field.get_value(),
			to_date: this.to_date_field.get_value(),
			company: this.company,
		};
	}

	refresh_all() {
		this.load_kpis();
		this.load_purchase();
		this.load_sales();
		this.load_sales_grade();
		this.load_chart();
		this.load_trend_table();
		this.update_matrix_months();
		this.load_matrix();
	}

	load_kpis() {
		if (this.active_tab === "sales") {
			frappe.call({
				method:
					"gke_customization.gke_catalog.page.sadguru_dashboard.sadguru_dashboard.get_sales_kpis",
				args: {
					...this.get_dates(),
					customer: this.customer_field.get_value(),
					grade: this.grade_field.get_value(),
				},
				callback: (r) => this.render_sales_kpis(r.message || {}),
			});
		} else {
			frappe.call({
				method:
					"gke_customization.gke_catalog.page.sadguru_dashboard.sadguru_dashboard.get_purchase_kpis",
				args: { ...this.get_dates(), supplier: this.supplier_field.get_value() },
				callback: (r) => this.render_purchase_kpis(r.message || {}),
			});
		}
	}

	render_purchase_kpis(d) {
		this.render_kpi_tiles([
			{ icon: SADGURU_ICONS.stack, label: "Total Purchase", value: sadguru_format_currency(d.total_purchase) },
			{ icon: SADGURU_ICONS.scale, label: "Total Qty Purchased (Ct Wt)", value: sadguru_format_number(d.total_qty_purchased) },
			{
				icon: SADGURU_ICONS.building,
				label: "Avg Per Supplier",
				value: sadguru_format_currency(d.avg_per_supplier),
				back_label: "Avg Per Supplier (Ct Wt)",
				back_value: `${sadguru_format_number(d.avg_per_supplier_qty)}`,
			},
			{
				icon: SADGURU_ICONS.calendar,
				label: "Avg Monthly Purchase",
				value: sadguru_format_currency(d.avg_monthly_purchase),
				back_label: "Avg Monthly Purchase (Ct Wt)",
				back_value: `${sadguru_format_number(d.avg_monthly_purchase_qty)}`,
			},
		]);
	}

	render_sales_kpis(d) {
		this.render_kpi_tiles([
			{ icon: SADGURU_ICONS.stack, label: "Total Sales", value: sadguru_format_currency(d.total_sales) },
			{ icon: SADGURU_ICONS.scale, label: "Total Qty Sold (Ct Wt)", value: sadguru_format_number(d.total_qty_sold) },
			{
				icon: SADGURU_ICONS.user,
				label: "Avg Per Customer",
				value: sadguru_format_currency(d.avg_per_customer),
				back_label: "Avg Per Customer (Ct Wt)",
				back_value: `${sadguru_format_number(d.avg_per_customer_qty)}`,
			},
			{
				icon: SADGURU_ICONS.gem,
				label: "Avg Per Grade",
				value: sadguru_format_currency(d.avg_per_grade),
				back_label: "Avg Per Grade (Ct Wt)",
				back_value: `${sadguru_format_number(d.avg_per_grade_qty)}`,
			},
			{
				icon: SADGURU_ICONS.calendar,
				label: "Avg Monthly Sales",
				value: sadguru_format_currency(d.avg_monthly_sales),
				back_label: "Avg Monthly Sales (Ct Wt)",
				back_value: `${sadguru_format_number(d.avg_monthly_sales_qty)}`,
			},
		]);
	}

	render_kpi_tiles(tiles) {
		const $kpis = this.page.body.find(".sadguru-kpi-grid").empty();
		tiles.forEach((tile) => {
			if (tile.back_value) {
				const $card = $(`
					<div class="sadguru-kpi-card sadguru-kpi-flip">
						<div class="sadguru-kpi-flip-inner">
							<div class="sadguru-kpi-face sadguru-kpi-front">
								<div class="sadguru-kpi-icon">${tile.icon}</div>
								<div class="sadguru-kpi-value">${tile.value}</div>
								<div class="sadguru-kpi-label">${tile.label}</div>
							</div>
							<div class="sadguru-kpi-face sadguru-kpi-back">
								<div class="sadguru-kpi-icon">${SADGURU_ICONS.scale}</div>
								<div class="sadguru-kpi-value">${tile.back_value}</div>
								<div class="sadguru-kpi-label">${tile.back_label}</div>
							</div>
						</div>
					</div>
				`);
				$card.on("click", () => $card.toggleClass("flipped"));
				$kpis.append($card);
			} else {
				$kpis.append(`
					<div class="sadguru-kpi-card">
						<div class="sadguru-kpi-icon">${tile.icon}</div>
						<div class="sadguru-kpi-value">${tile.value}</div>
						<div class="sadguru-kpi-label">${tile.label}</div>
					</div>
				`);
			}
		});
	}

	load_purchase() {
		frappe.call({
			method:
				"gke_customization.gke_catalog.page.sadguru_dashboard.sadguru_dashboard.get_purchase_breakdown",
			args: {
				...this.get_dates(),
				supplier: this.supplier_field.get_value(),
				sort_by: this.purchase_sort.by,
				sort_order: this.purchase_sort.order,
			},
			callback: (r) => this.render_purchase(r.message || []),
		});
	}

	render_purchase(rows) {
		const $table = this.page.body.find(".sadguru-purchase-table");
		this.render_sortable_table($table, rows, "supplier_name", "Supplier", this.purchase_sort, () => {
			this.load_purchase();
		});
	}

	load_sales() {
		frappe.call({
			method:
				"gke_customization.gke_catalog.page.sadguru_dashboard.sadguru_dashboard.get_sales_breakdown",
			args: {
				...this.get_dates(),
				customer: this.customer_field.get_value(),
				grade: this.grade_field.get_value(),
				sort_by: this.sales_sort.by,
				sort_order: this.sales_sort.order,
			},
			callback: (r) => this.render_sales(r.message || []),
		});
	}

	render_sales(rows) {
		const $table = this.page.body.find(".sadguru-sales-table");
		this.render_sortable_table($table, rows, "label", "Customer", this.sales_sort, () => {
			this.load_sales();
		});
	}

	load_sales_grade() {
		frappe.call({
			method:
				"gke_customization.gke_catalog.page.sadguru_dashboard.sadguru_dashboard.get_sales_grade_breakdown",
			args: {
				...this.get_dates(),
				customer: this.customer_field.get_value(),
				sort_by: this.sales_grade_sort.by,
				sort_order: this.sales_grade_sort.order,
			},
			callback: (r) => this.render_sales_grade(r.message || []),
		});
	}

	render_sales_grade(rows) {
		const $table = this.page.body.find(".sadguru-sales-grade-table");
		this.render_sortable_table($table, rows, "label", "Grade", this.sales_grade_sort, () => {
			this.load_sales_grade();
		});
	}

	setup_matrix_controls() {
		this.page.body.find(".sadguru-matrix-toggle").on("click", (e) => {
			this.matrix_mode = this.matrix_mode === "amount" ? "qty" : "amount";
			$(e.currentTarget).attr("data-mode", this.matrix_mode);
			this.render_matrix(this.matrix_data || { grades: [], rows: [] });
		});

		this.page.body.find(".sadguru-matrix-month").on("change", (e) => {
			this.matrix_month = $(e.currentTarget).val();
			this.load_matrix();
		});
	}

	update_matrix_months() {
		const from_date = this.from_date_field.get_value();
		const to_date = this.to_date_field.get_value();
		const $select = this.page.body.find(".sadguru-matrix-month");
		const current = this.matrix_month;

		const months = sadguru_months_in_range(from_date, to_date);
		let options = `<option value="">All Months</option>`;
		options += months.map((m) => `<option value="${m}">${sadguru_format_month(m)}</option>`).join("");
		$select.html(options);

		this.matrix_month = months.includes(current) ? current : "";
		$select.val(this.matrix_month);
	}

	load_matrix() {
		frappe.call({
			method:
				"gke_customization.gke_catalog.page.sadguru_dashboard.sadguru_dashboard.get_sales_matrix",
			args: {
				...this.get_dates(),
				customer: this.customer_field.get_value(),
				month: this.matrix_month,
			},
			callback: (r) => {
				this.matrix_data = r.message || { grades: [], rows: [] };
				this.render_matrix(this.matrix_data);
			},
		});
	}

	render_matrix(data) {
		const { grades, rows } = data;
		const $table = this.page.body.find(".sadguru-matrix-table");
		const $thead = $table.find("thead");
		const $tbody = $table.find("tbody").empty();
		const $tfoot = $table.find("tfoot").empty();

		$thead.html(`
			<tr>
				<th>Customer</th>
				${grades.map((g) => `<th>${frappe.utils.escape_html(g)}</th>`).join("")}
				<th>Total</th>
			</tr>
		`);

		if (!rows.length) {
			$tbody.append(
				`<tr><td colspan="${grades.length + 2}" class="text-muted">No data for this period.</td></tr>`
			);
			return;
		}

		const format_cell = (cell) => {
			if (!cell) return "—";
			return this.matrix_mode === "qty" ? sadguru_format_number(cell.qty) : sadguru_format_currency(cell.amount);
		};

		rows.forEach((row) => {
			const cells = grades
				.map((g) => `<td>${format_cell(row.cells[g])}</td>`)
				.join("");
			const total =
				this.matrix_mode === "qty"
					? sadguru_format_number(row.total_qty)
					: sadguru_format_currency(row.total_amount);
			$tbody.append(`
				<tr>
					<td>${frappe.utils.escape_html(row.customer)}</td>
					${cells}
					<td class="sadguru-matrix-total">${total}</td>
				</tr>
			`);
		});

		const format_grade_total = (g) => {
			const qty = rows.reduce((sum, row) => sum + (row.cells[g]?.qty || 0), 0);
			const amount = rows.reduce((sum, row) => sum + (row.cells[g]?.amount || 0), 0);
			return this.matrix_mode === "qty" ? sadguru_format_number(qty) : sadguru_format_currency(amount);
		};
		const grand_total =
			this.matrix_mode === "qty"
				? sadguru_format_number(rows.reduce((sum, row) => sum + (row.total_qty || 0), 0))
				: sadguru_format_currency(rows.reduce((sum, row) => sum + (row.total_amount || 0), 0));
		$tfoot.append(`
			<tr class="sadguru-table-total">
				<td>Total</td>
				${grades.map((g) => `<td>${format_grade_total(g)}</td>`).join("")}
				<td class="sadguru-matrix-total">${grand_total}</td>
			</tr>
		`);
	}

	render_sortable_table($table, rows, label_field, label_header, sort_state, on_sort) {
		const sort_arrow = (field) => {
			if (sort_state.by !== field) return "";
			return sort_state.order === "desc" ? " ▼" : " ▲";
		};
		const active_class = (field) => (sort_state.by === field ? "active-sort" : "");

		const $thead = $table.find("thead");
		$thead.html(`
			<tr>
				<th>${label_header}</th>
				<th class="sadguru-sortable ${active_class("qty")}" data-field="qty">Qty${sort_arrow("qty")}</th>
				<th class="sadguru-sortable ${active_class("rate")}" data-field="rate">Rate${sort_arrow("rate")}</th>
				<th class="sadguru-sortable ${active_class("amount")}" data-field="amount">Amount${sort_arrow("amount")}</th>
			</tr>
		`);

		$thead.find(".sadguru-sortable").on("click", (e) => {
			const field = $(e.currentTarget).data("field");
			if (sort_state.by === field) {
				sort_state.order = sort_state.order === "desc" ? "asc" : "desc";
			} else {
				sort_state.by = field;
				sort_state.order = "desc";
			}
			on_sort();
		});

		const $tbody = $table.find("tbody").empty();
		const $tfoot = $table.find("tfoot").empty();
		if (!rows.length) {
			$tbody.append(`<tr><td colspan="4" class="text-muted">No data for this period.</td></tr>`);
			return;
		}
		const max_amount = Math.max(...rows.map((row) => row.amount || 0), 1);
		rows.forEach((row) => {
			const bar_width = ((row.amount || 0) / max_amount) * 100;
			$tbody.append(`
				<tr>
					<td>${frappe.utils.escape_html(row[label_field] || "Not Set")}</td>
					<td>${sadguru_format_number(row.qty)}</td>
					<td>${sadguru_format_currency(row.rate)}</td>
					<td class="sadguru-amount-cell">
						<div class="sadguru-bar" style="width: ${bar_width}%"></div>
						<span class="sadguru-amount-text">${sadguru_format_currency(row.amount)}</span>
					</td>
				</tr>
			`);
		});

		const total_qty = rows.reduce((sum, row) => sum + (row.qty || 0), 0);
		const total_amount = rows.reduce((sum, row) => sum + (row.amount || 0), 0);
		const total_rate = total_qty ? total_amount / total_qty : 0;
		$tfoot.append(`
			<tr class="sadguru-table-total">
				<td>Total</td>
				<td>${sadguru_format_number(total_qty)}</td>
				<td>${sadguru_format_currency(total_rate)}</td>
				<td>${sadguru_format_currency(total_amount)}</td>
			</tr>
		`);
	}

	load_chart() {
		if (this.active_tab === "sales") {
			frappe.call({
				method:
					"gke_customization.gke_catalog.page.sadguru_dashboard.sadguru_dashboard.get_sales_monthly",
				args: {
					...this.get_dates(),
					customer: this.customer_field.get_value(),
					grade: this.grade_field.get_value(),
				},
				callback: (r) => {
					const rows = r.message || [];
					this.render_chart(rows, "Sales");
					this.render_qty_chart(rows, "Sales");
				},
			});
		} else {
			frappe.call({
				method:
					"gke_customization.gke_catalog.page.sadguru_dashboard.sadguru_dashboard.get_purchase_monthly",
				args: { ...this.get_dates(), supplier: this.supplier_field.get_value() },
				callback: (r) => {
					const rows = r.message || [];
					this.render_chart(rows, "Purchase");
					this.render_qty_chart(rows, "Purchase");
				},
			});
		}
	}

	render_chart(rows, series_name) {
		const $chart_wrapper = this.page.body.find(".sadguru-month-chart").empty();
		if (!rows.length) {
			$chart_wrapper.append(`<div class="text-muted">No data for this period.</div>`);
			return;
		}
		const to_crore = (v) => v / 10000000;
		new frappe.Chart($chart_wrapper[0], {
			data: {
				labels: rows.map((r) => sadguru_format_month(r.month)),
				datasets: [{ name: series_name, values: rows.map((r) => to_crore(r.amount)) }],
			},
			type: "bar",
			height: 260,
			colors: ["#b8860b"],
			barOptions: { spaceRatio: 0.65 },
			axisOptions: { xAxisMode: "tick", yAxisMode: "tick" },
			tooltipOptions: {
				formatTooltipY: (value) => sadguru_format_currency(value * 10000000),
			},
		});
	}

	render_qty_chart(rows, series_name) {
		const $chart_wrapper = this.page.body.find(".sadguru-qty-month-chart").empty();
		if (!rows.length) {
			$chart_wrapper.append(`<div class="text-muted">No data for this period.</div>`);
			return;
		}
		new frappe.Chart($chart_wrapper[0], {
			data: {
				labels: rows.map((r) => sadguru_format_month(r.month)),
				datasets: [{ name: series_name, values: rows.map((r) => r.qty || 0) }],
			},
			type: "bar",
			height: 260,
			colors: ["#b8860b"],
			barOptions: { spaceRatio: 0.65 },
			axisOptions: { xAxisMode: "tick", yAxisMode: "tick" },
			tooltipOptions: {
				formatTooltipY: (value) => sadguru_format_number(value),
			},
		});
	}

	load_trend_table() {
		frappe.call({
			method:
				"gke_customization.gke_catalog.page.sadguru_dashboard.sadguru_dashboard.get_monthly_trend",
			args: {
				...this.get_dates(),
				supplier: this.supplier_field.get_value(),
				customer: this.customer_field.get_value(),
				grade: this.grade_field.get_value(),
			},
			callback: (r) => this.render_trend_table(r.message || []),
		});
	}

	render_trend_table(rows) {
		const $tbody = this.page.body.find(".sadguru-trend-table tbody").empty();
		const $tfoot = this.page.body.find(".sadguru-trend-table tfoot").empty();
		if (!rows.length) {
			$tbody.append(`<tr><td colspan="7" class="text-muted">No data for this period.</td></tr>`);
			return;
		}
		rows.forEach((row) => {
			$tbody.append(`
				<tr>
					<td>${sadguru_format_month(row.month)}</td>
					<td>${sadguru_format_number(row.purchase_qty)}</td>
					<td>${sadguru_format_currency(row.purchase_rate)}</td>
					<td>${sadguru_format_currency(row.purchase_amount)}</td>
					<td>${sadguru_format_number(row.sales_qty)}</td>
					<td>${sadguru_format_currency(row.sales_rate)}</td>
					<td>${sadguru_format_currency(row.sales_amount)}</td>
				</tr>
			`);
		});

		const sum = (field) => rows.reduce((total, row) => total + (row[field] || 0), 0);
		const total_purchase_qty = sum("purchase_qty");
		const total_purchase_amount = sum("purchase_amount");
		const total_sales_qty = sum("sales_qty");
		const total_sales_amount = sum("sales_amount");
		$tfoot.append(`
			<tr class="sadguru-table-total">
				<td>Total</td>
				<td>${sadguru_format_number(total_purchase_qty)}</td>
				<td>${sadguru_format_currency(total_purchase_qty ? total_purchase_amount / total_purchase_qty : 0)}</td>
				<td>${sadguru_format_currency(total_purchase_amount)}</td>
				<td>${sadguru_format_number(total_sales_qty)}</td>
				<td>${sadguru_format_currency(total_sales_qty ? total_sales_amount / total_sales_qty : 0)}</td>
				<td>${sadguru_format_currency(total_sales_amount)}</td>
			</tr>
		`);
	}
}

function sadguru_format_number(v, precision = 2) {
	return frappe.format(v || 0, { fieldtype: "Float", precision });
}

function sadguru_format_currency(v, precision) {
	const options = { fieldtype: "Currency" };
	if (precision !== undefined) options.precision = precision;
	return frappe.format(v || 0, options);
}

const SADGURU_MONTH_NAMES = [
	"Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function sadguru_format_month(ym) {
	const [year, month] = (ym || "").split("-");
	if (!year || !month) return ym;
	return `${SADGURU_MONTH_NAMES[parseInt(month, 10) - 1]}'${year.slice(2)}`;
}

function sadguru_months_in_range(from_date, to_date) {
	if (!from_date || !to_date) return [];
	const [from_year, from_month] = from_date.split("-").map(Number);
	const [to_year, to_month] = to_date.split("-").map(Number);
	const months = [];
	let year = from_year;
	let month = from_month;
	while (year < to_year || (year === to_year && month <= to_month)) {
		months.push(`${year}-${String(month).padStart(2, "0")}`);
		month += 1;
		if (month > 12) {
			month = 1;
			year += 1;
		}
	}
	return months;
}

function sadguru_pad(n) {
	return String(n).padStart(2, "0");
}

function sadguru_last_day_of_month(year, month) {
	return new Date(year, month, 0).getDate();
}

function sadguru_fy_start_year(date) {
	const year = date.getFullYear();
	const month = date.getMonth() + 1;
	return month >= 4 ? year : year - 1;
}

function sadguru_quarter_of(date) {
	const month = date.getMonth() + 1;
	if (month >= 4 && month <= 6) return 1;
	if (month >= 7 && month <= 9) return 2;
	if (month >= 10 && month <= 12) return 3;
	return 4;
}

function sadguru_generate_month_options(count = 18) {
	const now = new Date();
	const options = [];
	for (let i = 0; i < count; i++) {
		const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
		options.push(`${d.getFullYear()}-${sadguru_pad(d.getMonth() + 1)}`);
	}
	return options;
}

function sadguru_generate_quarter_options(count = 8) {
	const now = new Date();
	let fy = sadguru_fy_start_year(now);
	let q = sadguru_quarter_of(now);
	const options = [];
	for (let i = 0; i < count; i++) {
		options.push(`${fy}-Q${q}`);
		q -= 1;
		if (q < 1) {
			q = 4;
			fy -= 1;
		}
	}
	return options;
}

function sadguru_generate_fy_options(count = 5) {
	const now = new Date();
	const fy = sadguru_fy_start_year(now);
	const options = [];
	for (let i = 0; i < count; i++) {
		options.push(String(fy - i));
	}
	return options;
}

function sadguru_format_quarter(value) {
	const [fy, q] = value.split("-Q");
	const fy_num = Number(fy);
	return `Q${q} FY${String(fy_num).slice(2)}-${String(fy_num + 1).slice(2)}`;
}

function sadguru_format_fy(value) {
	const fy_num = Number(value);
	return `FY ${fy_num}-${String(fy_num + 1).slice(2)}`;
}

function sadguru_period_to_range(type, value) {
	if (type === "Month") {
		const [year, month] = value.split("-").map(Number);
		return {
			from: `${year}-${sadguru_pad(month)}-01`,
			to: `${year}-${sadguru_pad(month)}-${sadguru_pad(sadguru_last_day_of_month(year, month))}`,
		};
	}

	if (type === "Quarter") {
		const [fy, q] = value.split("-Q").map(Number);
		const QUARTER_MONTHS = { 1: [4, 6], 2: [7, 9], 3: [10, 12], 4: [1, 3] };
		const [start_month, end_month] = QUARTER_MONTHS[q];
		const year = q === 4 ? fy + 1 : fy;
		return {
			from: `${year}-${sadguru_pad(start_month)}-01`,
			to: `${year}-${sadguru_pad(end_month)}-${sadguru_pad(sadguru_last_day_of_month(year, end_month))}`,
		};
	}

	if (type === "Financial Year") {
		const fy = Number(value);
		return { from: `${fy}-04-01`, to: `${fy + 1}-03-31` };
	}

	return null;
}

const SADGURU_ICONS = {
	stack: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 3 8l9 5 9-5-9-5Z"/><path d="m3 13 9 5 9-5"/></svg>`,
	scale: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v18"/><path d="M5 7h14"/><path d="M5 7 2 13a3 3 0 0 0 6 0L5 7Z"/><path d="M19 7l-3 6a3 3 0 0 0 6 0l-3-6Z"/></svg>`,
	building: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 21V7l8-4 8 4v14"/><path d="M4 21h16"/><path d="M9 9h1M9 13h1M14 9h1M14 13h1M9 21v-4h6v4"/></svg>`,
	calendar: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>`,
	user: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 4-6 8-6s8 2 8 6"/></svg>`,
	gem: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12l3 5-9 13L3 8l3-5Z"/><path d="M3 8h18M9 3l3 5 3-5M12 8l-3 13M12 8l3 13"/></svg>`,
};
