frappe.pages['bom-dashboard'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'BOM Dashboard',
		single_column: true,
	});
	new BomDashboard(page);
};

const BOM_API = 'gke_customization.gke_catalog.page.bom_dashboard.bom_dashboard.';

class BomDashboard {
	constructor(page) {
		this.page = page;
		this.state = {
			setting_type: '',
			sub_setting_type1: '',
			matrix_view: 'assignee',
			matrix_stock_filter: '',
			matrix_status_filter: '',
			due_soon_days: 2,
		};
		this.f = {}; // filter controls
		this.ready = false;
		this.req = 0; // request token: ignore stale responses
		this.refresh = frappe.utils.debounce(() => this.load(), 250);

		this.$ = (sel) => this.page.main.find(sel);
		this.render_shell();

		this.setup_controls();
		this.ready = true;
		this.load();
	}

	call(method, args = {}, opts = {}) {
		return frappe.call({ method: BOM_API + method, args, ...opts }).then((r) => r.message);
	}

	// ---------- setup ----------

	render_shell() {
		this.page.main.html(frappe.render_template('bom_dashboard', {}));
		this.$kpi = this.$('[data-field="kpi-row"]');
		this.$matrix = this.$('[data-field="matrix"]');
		this.$matrix_title = this.$('[data-field="matrix-title"]');
		this.$workload = this.$('[data-field="workload-list"]');
		this.$alerts = this.$('[data-field="alerts-board"]');
		this.$bom_docs = this.$('[data-field="bom-doc-board"]');
		this.$generated_at = this.$('[data-field="generated-at"]');

		const click = (e) => this.open_segment(e.currentTarget);
		[this.$kpi, this.$workload, this.$alerts, this.$bom_docs].forEach(($el) =>
			$el.on('click', '[data-segment]', click)
		);
		this.$matrix.on('click', 'td[data-segment]', click);
	}

	reset_tabs() {
		this.state.setting_type = '';
		this.state.sub_setting_type1 = '';
		this.$('[data-field="setting-type-tabs"] .bomdash__tab').removeClass('is-active').first().addClass('is-active');
	}

	make_link(fieldname, options, placeholder, extra = {}) {
		const control = frappe.ui.form.make_control({
			df: { fieldname, fieldtype: 'Link', options, placeholder, onchange: () => this.refresh(), ...extra },
			parent: this.$(`[data-field="${fieldname.replace(/_/g, '-')}-field"]`),
			render_input: true,
		});
		control.refresh();
		this.f[fieldname] = control;
	}

	setup_controls() {
		this.page.set_secondary_action(__('Refresh'), () => this.load(), 'refresh');
		this.$('[data-field="clear-filters"]').on('click', () => this.clear_filters());

		this.$('[data-field="setting-type-tabs"] .bomdash__tab').on('click', (e) => {
			const $t = $(e.currentTarget);
			const field = $t.attr('data-filter-field') || '';
			const value = $t.attr('data-filter-value') || '';
			this.state.setting_type = field === 'setting_type' ? value : '';
			this.state.sub_setting_type1 = field === 'sub_setting_type1' ? value : '';
			$t.addClass('is-active').siblings().removeClass('is-active');
			this.refresh();
		});

		this.make_link('category', 'Attribute Value', __('All Categories'), {
			get_query: () => ({
				query: 'jewellery_erpnext.query.item_attribute_query',
				filters: { item_attribute: 'Item Category' },
			}),
		});
		this.make_link('customer', 'Customer', __('All Customers'));
		this.make_link('branch', 'Branch', __('All Branches'));
		this.make_link('assigned_to', 'User', __('Assigned To'));

		this.f.daterange = frappe.ui.form.make_control({
			df: { fieldname: 'order_date_range', fieldtype: 'DateRange', placeholder: __('All Dates'), onchange: () => this.refresh() },
			parent: this.$('[data-field="daterange-field"]'),
			render_input: true,
		});
		this.f.daterange.refresh();

		this.$('[data-field="period-select"]').on('change', (e) => this.apply_period(e.target.value));
		this.$('[data-field="matrix-view-select"]').on('change', (e) => {
			this.state.matrix_view = e.target.value;
			this.$matrix_title.text(this.matrix_title());
			this.refresh();
		});
		this.$('[data-field="matrix-filter"]').on('change', (e) => {
			this.state.matrix_stock_filter = e.target.value;
			this.refresh();
		});
		this.$('[data-field="matrix-status-filter"]').on('change', (e) => {
			this.state.matrix_status_filter = e.target.value;
			this.refresh();
		});
		this.$('[data-field="assignee-search"]').on('input', () => this.filter_workload());

		// default view: today's orders
		this.$('[data-field="period-select"]').val('today');
		this.apply_period('today');
	}

	apply_period(period) {
		const m = moment;
		const ranges = {
			today: [m(), m()],
			current_week: [m().startOf('week'), m().endOf('week')],
			last_week: [m().subtract(1, 'weeks').startOf('week'), m().subtract(1, 'weeks').endOf('week')],
			this_month: [m().startOf('month'), m().endOf('month')],
			last_month: [m().subtract(1, 'months').startOf('month'), m().subtract(1, 'months').endOf('month')],
		};
		const r = ranges[period];
		this.f.daterange.set_value(r ? r.map((d) => d.format('YYYY-MM-DD')) : '');
	}

	clear_filters() {
		['category', 'customer', 'branch', 'assigned_to'].forEach((k) => this.f[k].set_value(''));
		this.f.daterange.set_value('');
		this.$('[data-field="period-select"]').val('');
		this.$('[data-field="matrix-filter"]').val('');
		this.$('[data-field="matrix-status-filter"]').val('');
		this.state.matrix_stock_filter = '';
		this.state.matrix_status_filter = '';
		this.reset_tabs();
		this.refresh();
	}

	matrix_title() {
		return {
			status: __('Status × Category (Orders)'),
			customer: __('Customer × Category (Orders)'),
		}[this.state.matrix_view] || __('Assignee × Category (Orders)');
	}

	matrix_row_label() {
		return { status: __('Status'), customer: __('Customer') }[this.state.matrix_view] || __('Assignee');
	}

	args() {
		const v = (k) => this.f[k].get_value() || undefined;
		const range = this.f.daterange.get_value();
		return {
			category: v('category'),
			customer: v('customer'),
			branch: v('branch'),
			assigned_to: v('assigned_to'),
			from_date: range && range[0] ? range[0] : undefined,
			to_date: range && range[1] ? range[1] : undefined,
			setting_type: this.state.setting_type || undefined,
			sub_setting_type1: this.state.sub_setting_type1 || undefined,
			due_soon_days: this.state.due_soon_days,
			matrix_view: this.state.matrix_view,
			matrix_stock_filter: this.state.matrix_stock_filter || undefined,
			matrix_status_filter: this.state.matrix_status_filter || undefined,
		};
	}

	// ---------- load / render ----------

	load() {
		if (!this.ready) return;
		const args = this.args();

		const token = ++this.req;
		const loading = (t) => `<div class="bomdash__loading">${frappe.utils.escape_html(t)}</div>`;
		this.$kpi.html(loading(__('Loading status summary…')));
		this.$matrix.html(loading(__('Loading matrix…')));
		this.$workload.html(loading(__('Loading workload…')));
		this.$alerts.html(loading(__('Loading alerts…')));
		this.$bom_docs.html(loading(__('Loading BOM documents…')));

		this.call('get_dashboard_data', args, { freeze: false })
			.then((data) => {
				if (token !== this.req) return;
				if (!data) return this.prompt(__('No data returned.'));
				this.data = data;
				this.render();
			})
			.catch(() => token === this.req && this.prompt(__('Could not load the dashboard. Please refresh and try again.')));
	}

	prompt(text) {
		this.$kpi.html(`<div class="bomdash__empty">${frappe.utils.escape_html(text)}</div>`);
		[this.$matrix, this.$workload, this.$alerts, this.$bom_docs].forEach(($el) => $el.html(''));
	}

	render() {
		const d = this.data;
		this.render_kpis(d);
		this.render_matrix(d.matrix);
		this.render_workload(d.workload);
		this.render_alerts(d.alerts);
		this.render_bom_docs(d.bom_docs);
		if (d.generated_at) this.$generated_at.text('as of ' + frappe.datetime.str_to_user(d.generated_at));
	}

	fmt(n) {
		return (n || 0).toLocaleString('en-IN');
	}

	seg(o) {
		return frappe.utils.escape_html(JSON.stringify(o));
	}

	render_kpis(d) {
		const esc = frappe.utils.escape_html;
		const total = d.total_orders;
		const pct = (n) => (total ? Math.min(100, Math.round((n / total) * 1000) / 10) : 0);
		const ACCENT = {
			pending: 'blue', on_hold: 'yellow', update_item: 'orange', update_bom: 'purple',
			creating_bom: 'cyan', designing: 'indigo', bom_qc: 'pink', customer_approval: 'amber',
			approved: 'green', rejected: 'red', other: 'gray',
		};

		const tile = (label, count, segment, accent, cls = '') => `
			<div class="bom-kpi ${cls}" ${accent ? `style="--bom-accent:var(--bom-${accent})"` : ''}>
				<div class="bom-kpi__label">${esc(label)}</div>
				<div class="bom-kpi__count" data-segment="${this.seg(segment)}">${this.fmt(count)}</div>
				${cls.includes('total') ? '' : `<div class="bom-kpi__pct">${pct(count)}% of total</div>`}
			</div>`;

		const status = [tile(__('Total BOM Orders'), total, { type: 'total' }, '', 'bom-kpi--total')]
			.concat(d.status_summary.map((r) => tile(r.label, r.count, { type: 'status_bucket', bucket: r.key }, ACCENT[r.key])))
			.join('');

		const stock = [
			[__('Customer Order'), 'customer_order'],
			[__('Customer Stock'), 'customer_stock'],
			[__('GK Stock'), 'gk_stock'],
			[__('GK Order'), 'gk_order'],
			[__('No Order Type'), 'blank_order_type'],
			[__('GK, No Order Type'), 'gk_blank'],
		]
			.map(([label, key]) => tile(label, d.stock[key], { type: 'stock_split', key }, ''))
			.join('');

		this.$kpi.html(
			`<div class="bom-kpi-row bom-kpi-row--status">${status}</div>` +
				`<div class="bom-kpi-row bom-kpi-row--flags">${stock}</div>`
		);
	}

	render_matrix(m) {
		if (!m || !m.rows.length) {
			this.$matrix.html('<div class="bomdash__empty">No BOM orders for this selection.</div>');
			return;
		}
		const esc = frappe.utils.escape_html;
		const view = this.state.matrix_view;
		const empty = { qty: 0, overdue: 0, due_soon: 0 };
		const dot = (x) =>
			x.overdue
				? `<span class="bom-matrix__risk bom-matrix__risk--overdue" title="${__('Contains overdue orders')}"></span>`
				: x.due_soon
				? `<span class="bom-matrix__risk bom-matrix__risk--due-soon" title="${__('Contains orders due soon')}"></span>`
				: '';
		const cell = (x, row_key, category, cls = '') =>
			`<td class="${cls}${x.qty ? '' : ' bom-matrix__zero'}" data-segment="${this.seg({ type: 'matrix_cell', view, row_key, category })}">${dot(x)}${this.fmt(x.qty)}</td>`;

		const head =
			`<th>${this.matrix_row_label()}</th>` +
			m.categories.map((c) => `<th>${esc(c)}</th>`).join('') +
			`<th class="bom-matrix__total">${__('Total')}</th>`;
		const body = m.rows
			.map(
				(r) =>
					`<tr><td>${esc(r.name)}</td>` +
					m.categories.map((c) => cell(r.cells[c] || empty, r.key, c)).join('') +
					cell(r.total, r.key, null, 'bom-matrix__total') +
					'</tr>'
			)
			.join('');
		const foot =
			`<td>${__('Total')}</td>` +
			m.categories.map((c) => cell(m.category_totals[c] || empty, null, c, 'bom-matrix__total')).join('') +
			cell(m.grand_total, null, null, 'bom-matrix__total');

		this.$matrix.html(`<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody><tfoot><tr>${foot}</tr></tfoot></table>`);
	}

	render_workload(list) {
		if (!list || !list.length) {
			this.$workload.html('<div class="bomdash__empty">No BOM orders for this selection.</div>');
			return;
		}
		const max = Math.max(...list.map((w) => w.count));
		this.$workload.html(
			list
				.map((w) => {
					const s = (metric) => this.seg({ type: 'assignee', key: w.key, metric });
					return `
					<div class="bom-designer">
						<div class="bom-designer__name">${frappe.utils.escape_html(w.name)}</div>
						<div class="bom-designer__bar"><span style="width:${max ? Math.round((w.count / max) * 100) : 0}%"></span></div>
						<div class="bom-designer__stats">
							<span class="bom-designer__count" data-segment="${s('total')}">${this.fmt(w.count)} total</span>
							<span class="bom-designer__inprogress" data-segment="${s('in_progress')}">${this.fmt(w.in_progress)} in progress</span>
							<span class="bom-designer__completed" data-segment="${s('completed')}">${this.fmt(w.completed)} approved</span>
						</div>
					</div>`;
				})
				.join('')
		);
		this.filter_workload();
	}

	filter_workload() {
		const q = (this.$('[data-field="assignee-search"]').val() || '').trim().toLowerCase();
		this.$workload.find('.bom-designer').each((_, el) => {
			$(el).toggle(!q || $(el).find('.bom-designer__name').text().toLowerCase().includes(q));
		});
	}

	lamp(label_html, count, color, segment, unit = 'orders') {
		return `
			<div class="bom-lamp ${count > 0 ? 'bom-lamp--active' : ''}" style="--bom-lamp-color:${color}">
				<div class="bom-lamp__bulb"></div>
				<div>
					<div class="bom-lamp__label">${label_html}</div>
					<div class="bom-lamp__count" ${segment ? `data-segment="${this.seg(segment)}"` : ''}>${count}<span>${unit}</span></div>
				</div>
			</div>`;
	}

	render_alerts(a) {
		if (!a) return this.$alerts.html('<div class="bomdash__empty">No alert data.</div>');
		if (a.due_soon.days != null) this.state.due_soon_days = a.due_soon.days;
		const label = `Due Soon (within <input type="number" class="bom-lamp__days-input" data-field="due-soon-days" min="0" max="365" step="1" value="${this.state.due_soon_days}" /> days)`;
		this.$alerts.html(
			this.lamp(label, this.fmt(a.due_soon.count), 'var(--bom-orange)', { type: 'alert', which: 'due_soon' }) +
				this.lamp('Overdue', this.fmt(a.overdue.count), 'var(--bom-red)', { type: 'alert', which: 'overdue' })
		);
		this.$alerts.find('[data-field="due-soon-days"]').on('change', (e) => {
			let v = parseInt(e.target.value, 10);
			if (isNaN(v) || v < 0) v = 0;
			e.target.value = v;
			this.state.due_soon_days = v;
			this.refresh();
		});
	}

	render_bom_docs(b) {
		if (!b) return this.$bom_docs.html('<div class="bomdash__empty">No BOM data.</div>');
		const doc = (label, which, color) => this.lamp(label, this.fmt(b[which]), color, { type: 'bom_doc', which }, 'BOMs');
		this.$bom_docs.html(
			doc('Draft BOMs', 'draft', 'var(--bom-blue)') +
				doc('Active BOMs', 'active', 'var(--bom-green)') +
				doc('Inactive BOMs', 'inactive', 'var(--bom-gray)') +
				this.lamp('Orders without BOM', this.fmt(b.no_bom), 'var(--bom-amber)', { type: 'no_bom' }) +
				this.lamp('Total BOM Amount', this.fmt(Math.round(b.total_amount)), 'var(--bom-teal)', null, '')
		);
	}

	// ---------- click-through ----------

	open_segment(el) {
		const segment = JSON.parse($(el).attr('data-segment'));
		this.call('get_segment_orders', { ...this.args(), segment }, { freeze: true }).then((r) => {
			const names = (r && r.names) || [];
			if (!names.length) {
				frappe.show_alert({ message: __('No records in this segment'), indicator: 'orange' });
				return;
			}
			frappe.route_options = { name: ['in', names] };
			frappe.set_route('List', r.doctype);
		});
	}
}