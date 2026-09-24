frappe.pages['cad-order-dashboard'].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'CAD Dashboard',
		single_column: true,
	});

	new CadDashboard(page);
};

class CadDashboard {
	constructor(page) {
		this.page = page;
		this.method =
			'gke_customization.gke_catalog.report.cad_dashboard_script.cad_dashboard_script.get_dashboard_data';
		this.segment_method =
			'gke_customization.gke_catalog.report.cad_dashboard_script.cad_dashboard_script.get_segment_orders';
		this.get_my_tab_access_method =
			'gke_customization.gke_catalog.report.cad_dashboard_script.cad_dashboard_script.get_my_tab_access';
		this.get_my_matrix_view_access_method =
			'gke_customization.gke_catalog.report.cad_dashboard_script.cad_dashboard_script.get_my_matrix_view_access';

		this.BUCKET_ACCENTS = {
			pending: 'var(--cad-blue)',
			assigned: 'var(--cad-orange)',
			assigned_on_hold: 'var(--cad-cyan)',
			designing: 'var(--cad-purple)',
			designing_on_hold: 'var(--cad-cyan)',
			rework: 'var(--cad-amber)',
			qc: 'var(--cad-pink)',
			approved: 'var(--cad-green)',
			rejected: 'var(--cad-red)',
			bom_stage: 'var(--cad-cyan)',
		};

		this.due_soon_days = 2;
		this.setting_type = '';
		this.sub_setting_type1 = '';
		this.status_filter = '';
		this.matrix_filter = '';
		this.matrix_view = 'designer';

		this.has_tab_access = false;

		this.render_shell();
		Promise.all([this.init_tab_access(), this.init_matrix_view_access()]).then(() => {
			this.setup_page_controls();
			this.apply_matrix_view_access_ui(this.matrix_view_flags || {});
			if (!this.company_field.get_value()) {
				this.refresh();
			}
		});
	}

	// Tab and matrix-view access is decided entirely server-side
	// (get_my_tab_access / get_my_matrix_view_access in cad_dashboard_script.py).

	init_tab_access() {
		return frappe.call({ method: this.get_my_tab_access_method }).then((r) => {
			this.apply_tab_access_ui(r.message || {});
		});
	}

	init_matrix_view_access() {
		return frappe.call({ method: this.get_my_matrix_view_access_method }).then((r) => {
			this.matrix_view_flags = r.message || {};
		});
	}

	// ---- restrict the matrix view dropdown for non-management sessions ----
	//
	// `get_dashboard_data` already returns designer/customer matrices scoped
	// to the session's own data (see cad_dashboard_script.py), so there is
	// no leak in the data itself. This is a UI-level restriction on top of
	// that: a plain Designer-role user should only ever be offered the
	// Status x Category view, never be able to switch into the
	// Designer/Customer-keyed views at all - even though those would only
	// ever show their own row.

	apply_matrix_view_access_ui(flags) {
		if (!flags.restrict_to_status) return; // management: leave every view option available

		const $select = this.page.main.find('[data-field="matrix-view-select"]');
		$select.find('option').each((_, opt) => {
			if ($(opt).val() !== 'status') $(opt).remove();
		});
		$select.val('status').prop('disabled', true);

		this.matrix_view = 'status';
		this.$matrix_title.text(this.matrix_view_title());
	}

	apply_tab_access_ui(flags) {
		this.tab_flags = flags;
		const tabs = [
			{ selector: '[data-filter-field=""][data-filter-value=""]', flag: 'allow_all', setting_type: '', sub_setting_type1: '' },
			{ selector: '[data-filter-field="setting_type"][data-filter-value="Open"]', flag: 'allow_open_setting', setting_type: 'Open', sub_setting_type1: '' },
			{ selector: '[data-filter-field="setting_type"][data-filter-value="Nova Glow"]', flag: 'allow_nova_glow', setting_type: 'Nova Glow', sub_setting_type1: '' },
			{ selector: '[data-filter-field="sub_setting_type1"][data-filter-value="Close-Open Setting"]', flag: 'allow_close_open_setting', setting_type: '', sub_setting_type1: 'Close-Open Setting' },
		];

		let first_allowed = null;
		tabs.forEach((tab) => {
			const $btn = this.page.main.find(`[data-field="setting-type-tabs"] .caddash__tab${tab.selector}`);
			const allowed = !!flags[tab.flag];
			$btn.toggle(allowed).removeClass('is-active');
			if (allowed && !first_allowed) first_allowed = tab;
		});

		this.has_tab_access = !!first_allowed;
		this.setting_type = first_allowed ? first_allowed.setting_type : '';
		this.sub_setting_type1 = first_allowed ? first_allowed.sub_setting_type1 : '';
		if (first_allowed) {
			this.page.main.find(`[data-field="setting-type-tabs"] .caddash__tab${first_allowed.selector}`).addClass('is-active');
		}
	}

	setup_page_controls() {
		const page = this.page;

		page.set_secondary_action(__('Refresh'), () => this.refresh(), 'refresh');

		this.page.main.find('[data-field="clear-filters"]').on('click', () => this.clear_filters());

		this.page.main.find('[data-field="setting-type-tabs"] .caddash__tab').on('click', (e) => {
			const $tab = $(e.currentTarget);
			const field = $tab.attr('data-filter-field') || '';
			const value = $tab.attr('data-filter-value') || '';
			this.setting_type = field === 'setting_type' ? value : '';
			this.sub_setting_type1 = field === 'sub_setting_type1' ? value : '';
			$tab.addClass('is-active').siblings().removeClass('is-active');
			this.refresh();
		});

		this.company_field = frappe.ui.form.make_control({
			df: {
				fieldname: 'company',
				fieldtype: 'Link',
				options: 'Company',
				placeholder: __('Select Company'),
				onchange: () => this.refresh(),
			},
			parent: this.page.main.find('[data-field="company-field"]'),
			render_input: true,
		});
		this.company_field.refresh();

		this.company_field.set_value('Gurukrupa Export Private Limited');

		this.designer_field = frappe.ui.form.make_control({
			df: {
				fieldname: 'designer',
				fieldtype: 'Link',
				options: 'Employee',
				placeholder: __('All Designers'),
				onchange: () => this.refresh(),
			},
			parent: this.page.main.find('[data-field="designer-field"]'),
			render_input: true,
		});
		this.designer_field.refresh();

		this.category_field = frappe.ui.form.make_control({
			df: {
				fieldname: 'category',
				fieldtype: 'Link',
				options: 'Attribute Value',
				placeholder: __('All Categories'),
				get_query: () => ({
					query: 'jewellery_erpnext.query.item_attribute_query',
					filters: { item_attribute: 'Item Category' },
				}),
				onchange: () => this.refresh(),
			},
			parent: this.page.main.find('[data-field="category-field"]'),
			render_input: true,
		});
		this.category_field.refresh();

		this.customer_field = frappe.ui.form.make_control({
			df: {
				fieldname: 'customer',
				fieldtype: 'Link',
				options: 'Customer',
				placeholder: __('All Customers'),
				onchange: () => this.refresh(),
			},
			parent: this.page.main.find('[data-field="customer-field"]'),
			render_input: true,
		});
		this.customer_field.refresh();

		this.branch_field = frappe.ui.form.make_control({
			df: {
				fieldname: 'branch',
				fieldtype: 'Link',
				options: 'Branch',
				placeholder: __('All Branches'),
				onchange: () => this.refresh(),
			},
			parent: this.page.main.find('[data-field="branch-field"]'),
			render_input: true,
		});
		this.branch_field.refresh();

		this.department_field = frappe.ui.form.make_control({
			df: {
				fieldname: 'department',
				fieldtype: 'Link',
				options: 'Department',
				placeholder: __('All Departments'),
				onchange: () => this.refresh(),
			},
			parent: this.page.main.find('[data-field="department-field"]'),
			render_input: true,
		});
		this.department_field.refresh();

		this.assigned_to_field = frappe.ui.form.make_control({
			df: {
				fieldname: 'assigned_to',
				fieldtype: 'Link',
				options: 'User',
				placeholder: __('Assigned To'),
				onchange: () => this.refresh(),
			},
			parent: this.page.main.find('[data-field="assigned-to-field"]'),
			render_input: true,
		});
		this.assigned_to_field.refresh();

		this.daterange_field = frappe.ui.form.make_control({
			df: {
				fieldname: 'order_date_range',
				fieldtype: 'DateRange',
				placeholder: __('All Dates'),
				onchange: () => this.refresh(),
			},
			parent: this.page.main.find('[data-field="daterange-field"]'),
			render_input: true,
		});
		this.daterange_field.refresh();

		this.page.main.find('[data-field="period-select"]').on('change', (e) => {
			this.apply_period(e.target.value);
		});

		this.page.main.find('[data-field="matrix-filter"]').on('change', (e) => {
			this.matrix_filter = e.target.value;
			this.refresh();
		});

		this.page.main.find('[data-field="matrix-status-filter"]').on('change', (e) => {
			this.status_filter = e.target.value;
			this.refresh();
		});

		this.page.main.find('[data-field="matrix-view-select"]').on('change', (e) => {
			this.matrix_view = e.target.value;
			this.$matrix_title.text(this.matrix_view_title());
			if (this.data) {
				this.render_matrix(this.active_matrix());
			}
		});

		this.page.main.find('[data-field="matrix-export"]').on('click', () => this.export_matrix_csv());

		this.page.main.find('[data-field="designer-search"]').on('input', () => this.filter_designer_list());

		this.page.main.find('[data-field="period-select"]').val('today');
		this.apply_period('today');
	}

	active_matrix() {
		if (this.matrix_view === 'status') return this.data.status_category_matrix;
		if (this.matrix_view === 'designer_status') return this.data.designer_status_matrix;
		if (this.matrix_view === 'customer') return this.data.customer_category_matrix;
		if (this.matrix_view === 'customer_status') return this.data.customer_status_matrix;
		return this.data.designer_category_matrix;
	}

	matrix_view_title() {
		if (this.matrix_view === 'status') return __('Status × Category (Qty)');
		if (this.matrix_view === 'designer_status') return __('Designer × Status (Qty)');
		if (this.matrix_view === 'customer') return __('Customer × Category (Qty)');
		if (this.matrix_view === 'customer_status') return __('Customer × Status (Qty)');
		return __('Designer × Category (Qty)');
	}

	matrix_row_label() {
		if (this.matrix_view === 'status') return __('Status');
		if (this.matrix_view === 'customer' || this.matrix_view === 'customer_status') return __('Customer');
		return __('Designer');
	}

	apply_period(period) {
		if (!period) {
			this.daterange_field.set_value('');
			return;
		}
		let from, to;
		if (period === 'today') {
			from = moment();
			to = moment();
		} else if (period === 'current_week') {
			from = moment().startOf('week');
			to = moment().endOf('week');
		} else if (period === 'last_week') {
			from = moment().subtract(1, 'weeks').startOf('week');
			to = moment().subtract(1, 'weeks').endOf('week');
		} else if (period === 'this_month') {
			from = moment().startOf('month');
			to = moment().endOf('month');
		} else if (period === 'last_month') {
			from = moment().subtract(1, 'months').startOf('month');
			to = moment().subtract(1, 'months').endOf('month');
		} else {
			return;
		}
		this.daterange_field.set_value([from.format('YYYY-MM-DD'), to.format('YYYY-MM-DD')]);
	}

	get_date_range() {
		const value = this.daterange_field.get_value();
		if (!value || !value[0] || !value[1]) return [null, null];
		return [value[0], value[1]];
	}

	clear_filters() {
		this.designer_field.set_value('');
		this.category_field.set_value('');
		this.customer_field.set_value('');
		this.branch_field.set_value('');
		this.department_field.set_value('');
		this.assigned_to_field.set_value('');
		this.daterange_field.set_value('');
		this.page.main.find('[data-field="period-select"]').val('');
		this.page.main.find('[data-field="matrix-filter"]').val('');
		this.page.main.find('[data-field="matrix-status-filter"]').val('');
		this.matrix_filter = '';
		this.status_filter = '';
		this.apply_tab_access_ui(this.tab_flags || {});
		this.refresh();
	}

	render_shell() {
		this.page.main.html(frappe.render_template('cad_order_dashboard', {}));
		this.$kpi_row = this.page.main.find('[data-field="kpi-row"]');
		this.$matrix = this.page.main.find('[data-field="designer-category-matrix"]');
		this.$matrix_title = this.page.main.find('[data-field="matrix-title"]');
		this.$designer_list = this.page.main.find('[data-field="designer-list"]');
		this.$alerts = this.page.main.find('[data-field="alerts-board"]');
		this.$design_types = this.page.main.find('[data-field="design-type-board"]');
		this.$generated_at = this.page.main.find('[data-field="generated-at"]');

		this.$kpi_row.on('click', '[data-segment]', (e) => this.open_segment(e.currentTarget));
		this.$designer_list.on('click', '[data-segment]', (e) => this.open_segment(e.currentTarget));
		this.$alerts.on('click', '[data-segment]', (e) => this.open_segment(e.currentTarget));
		this.$design_types.on('click', '[data-segment]', (e) => this.open_segment(e.currentTarget));
		this.$matrix.on('click', 'td[data-segment]', (e) => this.open_segment(e.currentTarget, { thumbnails: true }));
	}

	// ---- click-through to Order list / thumbnail popup ----
	//
	// No order names are kept in `this.data` - every number only carries a
	// small `data-segment` descriptor (e.g. {type:'status_bucket', bucket:
	// 'pending'}), and the actual order list is resolved on demand from the
	// server, scoped to exactly that one segment, when it's clicked.

	open_segment(el, opts = {}) {
		const segment = JSON.parse($(el).attr('data-segment'));
		if (segment.type === 'designer' && segment.metric === 'in_progress') {
			this.show_designer_status_breakdown(segment);
			return;
		}
		const args = this.build_call_args();
		args.segment = segment;
		frappe.call({
			method: this.segment_method,
			args,
			freeze: true,
			callback: (r) => {
				const names = r.message || [];
				if (opts.thumbnails) {
					this.show_order_thumbnails(names);
				} else {
					this.open_orders(names);
				}
			},
		});
	}

	open_orders(names) {
		if (!names || !names.length) {
			frappe.show_alert({ message: __('No orders in this segment'), indicator: 'orange' });
			return;
		}
		frappe.route_options = { name: ['in', names] };
		frappe.set_route('List', 'Order');
	}

	// ---- designer "in progress" status breakdown popup ----

	show_designer_status_breakdown(segment) {
		const args = this.build_call_args();
		args.designer_key = segment.designer_key;

		const dialog = new frappe.ui.Dialog({
			title: __('In Progress — Status Breakdown'),
			size: 'small',
		});
		dialog.$body.html(`<div class="caddash__loading">${__('Loading…')}</div>`);
		dialog.show();

		frappe.call({
			method:
				'gke_customization.gke_catalog.report.cad_dashboard_script.cad_dashboard_script.get_designer_status_breakdown',
			args,
			callback: (r) => {
				const rows = r.message || [];
				if (!rows.length) {
					dialog.$body.html(`<div class="caddash__empty">${__('No in-progress orders.')}</div>`);
					return;
				}

				const esc = frappe.utils.escape_html;
				const html =
					`<div class="cad-status-breakdown">` +
					rows
						.map(
							(row) => `
						<div class="cad-status-breakdown__row" data-bucket="${esc(row.bucket)}">
							<span class="cad-status-breakdown__label">${esc(row.label)}</span>
							<span class="cad-status-breakdown__count">${this.fmt_count(row.count)}</span>
						</div>`
						)
						.join('') +
					`</div>`;
				dialog.$body.html(html);

				dialog.$body.find('.cad-status-breakdown__row').on('click', (e) => {
					const bucket = $(e.currentTarget).attr('data-bucket');
					const seg_args = this.build_call_args();
					seg_args.segment = {
						type: 'designer_status',
						designer_key: segment.designer_key,
						bucket,
					};
					frappe.call({
						method: this.segment_method,
						args: seg_args,
						freeze: true,
						callback: (r2) => {
							dialog.hide();
							this.open_orders(r2.message || []);
						},
					});
				});
			},
		});
	}

	// ---- matrix cell: image popup ----

	show_order_thumbnails(names) {
		if (!names || !names.length) {
			frappe.show_alert({ message: __('No orders in this segment'), indicator: 'orange' });
			return;
		}

		const THUMB_LIMIT = 60;
		const shown = names.slice(0, THUMB_LIMIT);
		const remaining = names.length - shown.length;

		const dialog = new frappe.ui.Dialog({
			title: __('Orders ({0})', [names.length]),
			size: 'large',
		});
		dialog.$body.html(`<div class="caddash__loading">${__('Loading…')}</div>`);
		dialog.show();

		frappe.call({
			method:
				'gke_customization.gke_catalog.report.cad_dashboard_script.cad_dashboard_script.get_order_thumbnails',
			args: { order_names: shown },
			callback: (r) => {
				const order_rows = r.message || [];
				const go_to_order = (order_name) => {
					dialog.hide();
					frappe.set_route('Form', 'Order', order_name);
				};

				const thumbs = order_rows
					.map((row) => {
						const img = row.design_image_1
							? `<img src="${frappe.utils.escape_html(row.design_image_1)}">`
							: `<div class="cad-thumb__placeholder">${__('No Image')}</div>`;
						return `
							<div class="cad-thumb" data-order="${frappe.utils.escape_html(row.name)}">
								<div class="cad-thumb__img">${img}</div>
								<div class="cad-thumb__name">${frappe.utils.escape_html(row.name)}</div>
							</div>`;
					})
					.join('');

				const more_footer = remaining
					? `<div class="cad-thumb-more">
							${__('+ {0} more orders not shown here.', [remaining])}
							<button type="button" class="btn btn-xs btn-default" data-action="view-all">${__('View all in list')}</button>
						</div>`
					: '';

				dialog.$body.html(`<div class="cad-thumb-grid">${thumbs}</div>${more_footer}`);

				dialog.$body.find('.cad-thumb').on('click', (e) => {
					go_to_order($(e.currentTarget).attr('data-order'));
				});
				dialog.$body.find('[data-action="view-all"]').on('click', () => {
					dialog.hide();
					this.open_orders(names);
				});
			},
		});
	}

	build_call_args() {
		const [from_date, to_date] = this.get_date_range();
		return {
			company: this.company_field.get_value(),
			due_soon_days: this.due_soon_days,
			designer: this.designer_field.get_value() || undefined,
			category: this.category_field.get_value() || undefined,
			customer: this.customer_field.get_value() || undefined,
			branch: this.branch_field.get_value() || undefined,
			department: this.department_field.get_value() || undefined,
			assigned_to: this.assigned_to_field.get_value() || undefined,
			from_date: from_date || undefined,
			to_date: to_date || undefined,
			setting_type: this.setting_type || undefined,
			sub_setting_type1: this.sub_setting_type1 || undefined,
			matrix_filter: this.matrix_filter || undefined,
			status_filter: this.status_filter || undefined,
		};
	}

	refresh() {
		if (!this.has_tab_access) {
			this.render_prompt(__('You do not have access to any tab on this dashboard. Contact your System Manager.'));
			return;
		}

		const args = this.build_call_args();
		if (!args.company) {
			this.render_prompt(__('Select a Company above to view the dashboard.'));
			return;
		}

		this.render_loading();

		frappe.call({
			method: this.method,
			args,
			freeze: false,
			callback: (r) => {
				if (!r.message) {
					this.render_prompt(__('No data returned for this company.'));
					return;
				}
				this.data = r.message;
				this.render();
			},
			error: () => {
				this.render_prompt(__('Could not load the dashboard. Please refresh and try again.'));
			},
		});
	}

	refresh_alerts() {
		const args = this.build_call_args();
		if (!args.company) return;

		frappe.call({
			method: this.method,
			args,
			freeze: false,
			callback: (r) => {
				if (!r.message) return;
				this.data = r.message;
				this.render_alerts(this.data.alerts);
			},
		});
	}

	render_loading() {
		const loading = (text) => `<div class="caddash__loading">${frappe.utils.escape_html(text)}</div>`;
		this.$kpi_row.html(loading(__('Loading status summary…')));
		this.$matrix.html(loading(__('Loading matrix…')));
		this.$designer_list.html(loading(__('Loading designer workload…')));
		this.$alerts.html(loading(__('Loading alerts…')));
		this.$design_types.html(loading(__('Loading design types…')));
	}

	render_prompt(text) {
		const html = `<div class="caddash__empty" style="grid-column:1/-1">${frappe.utils.escape_html(text)}</div>`;
		this.$kpi_row.html(html);
		this.$matrix.html('');
		this.$designer_list.html('');
		this.$alerts.html('');
		this.$design_types.html('');
	}

	render() {
		this.render_kpis(
			this.data.status_summary,
			this.data.total_orders,
			this.data.gk_stock,
			this.data.customer_stock,
			this.data.customer_order
		);
		this.render_matrix(this.active_matrix());
		this.render_designers(this.data.designers);
		this.render_alerts(this.data.alerts);
		this.render_design_types(this.data.design_types);
		if (this.data.generated_at) {
			this.$generated_at.text('as of ' + frappe.datetime.str_to_user(this.data.generated_at));
		}
	}

	fmt_count(n) {
		return (n || 0).toLocaleString('en-IN');
	}

	// ---- KPI strip ----

	render_kpis(rows, total, gk_stock, customer_stock, customer_order) {
		const seg_attr = (segment) => frappe.utils.escape_html(JSON.stringify(segment));
		const by_key = {};
		rows.forEach((row) => {
			by_key[row.key] = row;
		});

		const bucket_tile = (key) => {
			const row = by_key[key];
			if (!row) return '';
			const pct = total ? Math.min(100, Math.round((row.count / total) * 1000) / 10) : 0;
			const accent = this.BUCKET_ACCENTS[row.key] || 'var(--cad-blue)';
			const segment = { type: 'status_bucket', bucket: key };
			return `
				<div class="cad-kpi" style="--cad-accent:${accent}">
					<div class="cad-kpi__label">${frappe.utils.escape_html(row.label)}</div>
					<div class="cad-kpi__count" data-segment="${seg_attr(segment)}">${this.fmt_count(row.count)}</div>
					<div class="cad-kpi__pct">${pct}% of total</div>
				</div>`;
		};

		const total_tile = `
			<div class="cad-kpi cad-kpi--total">
				<div class="cad-kpi__label">${__('Total CAD Orders')}</div>
				<div class="cad-kpi__count" data-segment="${seg_attr({ type: 'total' })}">${this.fmt_count(total)}</div>
			</div>`;

		const stock_tile = (label, stock, flag_cls, key) => {
			const count = stock ? stock.count : 0;
			const pct = total ? Math.min(100, Math.round((count / total) * 1000) / 10) : 0;
			const segment = { type: 'stock_split', key };
			return `
				<div class="cad-kpi ${flag_cls}">
					<div class="cad-kpi__label">${frappe.utils.escape_html(label)}</div>
					<div class="cad-kpi__count" data-segment="${seg_attr(segment)}">${this.fmt_count(count)}</div>
					<div class="cad-kpi__pct">${pct}% of total</div>
				</div>`;
		};

		// Distinct from the "Assigned" status tile above: that one is just the
		// workflow_state label, which an order can carry without ever having a
		// row in the Designer Assignment - CAD child table. This tile counts
		// orders that actually have >= 1 designer assigned, regardless of status.
		const assigned_to_designer_tile = () => {
			const stock = this.data.assigned_to_designer;
			const count = stock ? stock.count : 0;
			const pct = total ? Math.min(100, Math.round((count / total) * 1000) / 10) : 0;
			const segment = { type: 'assigned_to_designer' };
			return `
				<div class="cad-kpi" style="--cad-accent:var(--cad-amber)">
					<div class="cad-kpi__label">${frappe.utils.escape_html(__('Assigned to Designer'))}</div>
					<div class="cad-kpi__count" data-segment="${seg_attr(segment)}">${this.fmt_count(count)}</div>
					<div class="cad-kpi__pct">${pct}% of total</div>
				</div>`;
		};

		// 11 status/count tiles at 6 columns = exactly 2 rows.
		const status_tiles = [
			total_tile,
			bucket_tile('pending'),
			bucket_tile('assigned'),
			assigned_to_designer_tile(),
			bucket_tile('assigned_on_hold'),
			bucket_tile('rework'),
			bucket_tile('designing'),
			bucket_tile('designing_on_hold'),
			bucket_tile('qc'),
			bucket_tile('approved'),
			bucket_tile('rejected'),
		].join('');

		// Kept as its own row, deliberately visually distinct (Indian flag
		// palette) from the status/count tiles above.
		const flag_tiles = [
			stock_tile(__('Customer Order'), customer_order, 'cad-kpi--flag-saffron', 'customer_order'),
			stock_tile(__('Customer Stock'), customer_stock, 'cad-kpi--flag-white', 'customer_stock'),
			stock_tile(__('GK Stock'), gk_stock, 'cad-kpi--flag-green', 'gk_stock'),
		].join('');

		this.$kpi_row.html(
			`<div class="cad-kpi-row cad-kpi-row--status">${status_tiles}</div>` +
				`<div class="cad-kpi-row cad-kpi-row--flags">${flag_tiles}</div>`
		);
	}

	// ---- designer x category qty matrix ----

	render_matrix(matrix) {
		if (!matrix || !matrix.rows || !matrix.rows.length) {
			this.$matrix.html('<div class="caddash__empty">No CAD orders for this selection.</div>');
			return;
		}

		const categories = matrix.categories;
		const category_labels = matrix.category_labels || {};
		const esc = (s) => frappe.utils.escape_html(s);
		const zero_cls = (metric) => (metric.qty ? '' : ' cad-matrix__zero');
		const seg_attr = (segment) => esc(JSON.stringify(segment));
		const view = this.matrix_view;
		const row_label = this.matrix_row_label();
		const risk_dot = (metric) => {
			if (metric.overdue) return `<span class="cad-matrix__risk cad-matrix__risk--overdue" title="${__('Contains overdue orders')}"></span>`;
			if (metric.due_soon) return `<span class="cad-matrix__risk cad-matrix__risk--due-soon" title="${__('Contains orders due soon')}"></span>`;
			return '';
		};
		const empty_metric = { qty: 0, overdue: 0, due_soon: 0 };

		const header =
			`<th>${row_label}</th>` +
			categories.map((c) => `<th>${esc(category_labels[c] || c)}</th>`).join('') +
			`<th class="cad-matrix__total">${__('Total')}</th>`;

		const body = matrix.rows
			.map((row) => {
				const cells = categories
					.map((c) => {
						const metric = row.cells[c] || empty_metric;
						const segment = { type: 'matrix_cell', view, row_key: row.key, category: c };
						return `<td class="${zero_cls(metric)}" data-segment="${seg_attr(segment)}">${risk_dot(metric)}${this.fmt_count(metric.qty)}</td>`;
					})
					.join('');
				const row_total_segment = { type: 'matrix_cell', view, row_key: row.key, category: null };
				return `<tr>
					<td>${esc(row.name)}</td>
					${cells}
					<td class="cad-matrix__total" data-segment="${seg_attr(row_total_segment)}">${risk_dot(row.total)}${this.fmt_count(row.total.qty)}</td>
				</tr>`;
			})
			.join('');

		const footer_cells = categories
			.map((c) => {
				const metric = matrix.category_totals[c] || empty_metric;
				const segment = { type: 'matrix_cell', view, row_key: null, category: c };
				return `<td class="cad-matrix__total" data-segment="${seg_attr(segment)}">${risk_dot(metric)}${this.fmt_count(metric.qty)}</td>`;
			})
			.join('');

		const grand_segment = { type: 'matrix_cell', view, row_key: null, category: null };

		const html = `<table>
			<thead><tr>${header}</tr></thead>
			<tbody>${body}</tbody>
			<tfoot><tr>
				<td>${__('Total')}</td>
				${footer_cells}
				<td class="cad-matrix__total" data-segment="${seg_attr(grand_segment)}">${risk_dot(matrix.grand_total)}${this.fmt_count(matrix.grand_total.qty)}</td>
			</tr></tfoot>
		</table>`;

		this.$matrix.html(html);
	}

	export_matrix_csv() {
		const matrix = this.active_matrix();
		if (!matrix || !matrix.rows || !matrix.rows.length) {
			frappe.show_alert({ message: __('Nothing to export'), indicator: 'orange' });
			return;
		}

		const categories = matrix.categories;
		const category_labels = matrix.category_labels || {};
		const row_label = this.matrix_row_label();
		const qty_of = (metric) => (metric && metric.qty) || 0;

		const csv_rows = [[row_label, ...categories.map((c) => category_labels[c] || c), __('Total')]];
		matrix.rows.forEach((row) => {
			csv_rows.push([row.name, ...categories.map((c) => qty_of(row.cells[c])), qty_of(row.total)]);
		});
		csv_rows.push([
			__('Total'),
			...categories.map((c) => qty_of(matrix.category_totals[c])),
			qty_of(matrix.grand_total),
		]);

		const csv_text = csv_rows
			.map((cells) => cells.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(','))
			.join('\n');

		const blob = new Blob([csv_text], { type: 'text/csv;charset=utf-8;' });
		const url = URL.createObjectURL(blob);
		const $link = $('<a></a>').attr({
			href: url,
			download: `cad_matrix_${this.matrix_view}_${frappe.datetime.get_today()}.csv`,
		});
		$link.appendTo(document.body)[0].click();
		$link.remove();
		URL.revokeObjectURL(url);
	}

	// ---- designer workload ----

	render_designers(designers) {
		if (!designers || !designers.length) {
			this.$designer_list.html('<div class="caddash__empty">No CAD orders for this selection.</div>');
			return;
		}

		const max_count = Math.max(...designers.map((d) => d.count));
		const seg_attr = (segment) => frappe.utils.escape_html(JSON.stringify(segment));

		const html = designers
			.map((d) => {
				const pct = max_count ? Math.round((d.count / max_count) * 100) : 0;
				const designer_key = d.designer || '__unassigned__';
				const seg = (metric) => seg_attr({ type: 'designer', designer_key, metric });
				return `
					<div class="cad-designer">
						<div class="cad-designer__name">${frappe.utils.escape_html(d.name)}</div>
						<div class="cad-designer__bar"><span style="width:${pct}%"></span></div>
						<div class="cad-designer__stats">
							<span class="cad-designer__count" data-segment="${seg('total')}">${this.fmt_count(d.count)} total</span>
							<span class="cad-designer__inprogress" data-segment="${seg('in_progress')}">${this.fmt_count(d.in_progress)} in progress</span>
							<span class="cad-designer__completed" data-segment="${seg('completed')}">${this.fmt_count(d.completed)} approved</span>
						</div>
					</div>`;
			})
			.join('');

		this.$designer_list.html(html);
		this.filter_designer_list();
	}

	filter_designer_list() {
		const query = (this.page.main.find('[data-field="designer-search"]').val() || '').trim().toLowerCase();
		this.$designer_list.find('.cad-designer').each((_, el) => {
			const name = $(el).find('.cad-designer__name').text().toLowerCase();
			$(el).toggle(!query || name.includes(query));
		});
	}

	// ---- due-date alerts ----

	render_alerts(alerts) {
		if (!alerts) {
			this.$alerts.html('<div class="caddash__empty">No alert data.</div>');
			return;
		}

		const due_soon = alerts.due_soon || { count: 0 };
		const overdue = alerts.overdue || { count: 0 };
		if (due_soon.days !== undefined && due_soon.days !== null) {
			this.due_soon_days = due_soon.days;
		}

		const seg_attr = (segment) => frappe.utils.escape_html(JSON.stringify(segment));

		const lamp = (label_html, count, color, active, which) => `
			<div class="cad-lamp ${active ? 'cad-lamp--active' : ''}" style="--cad-lamp-color:${color}">
				<div class="cad-lamp__bulb"></div>
				<div>
					<div class="cad-lamp__label">${label_html}</div>
					<div class="cad-lamp__count" data-segment="${seg_attr({ type: 'alert', which })}">${this.fmt_count(count)}<span>orders</span></div>
				</div>
			</div>`;

		const due_soon_label = `Due Soon (within
			<input type="number" class="cad-lamp__days-input" data-field="due-soon-days"
				min="0" max="365" step="1" value="${this.due_soon_days}" /> days)`;

		const html =
			lamp(due_soon_label, due_soon.count, 'var(--cad-orange)', due_soon.count > 0, 'due_soon') +
			lamp('Overdue', overdue.count, 'var(--cad-red)', overdue.count > 0, 'overdue');

		this.$alerts.html(html);

		this.$alerts.find('[data-field="due-soon-days"]').on('change', (e) => {
			let value = parseInt(e.target.value, 10);
			if (isNaN(value) || value < 0) value = 0;
			e.target.value = value;
			this.due_soon_days = value;
			this.refresh_alerts();
		});
	}

	// ---- design type breakdown ----

	render_design_types(design_types) {
		if (!design_types || !design_types.length) {
			this.$design_types.html('<div class="caddash__empty">No design type data.</div>');
			return;
		}

		const seg_attr = (segment) => frappe.utils.escape_html(JSON.stringify(segment));
		const colors = [
			'var(--cad-blue)',
			'var(--cad-purple)',
			'var(--cad-pink)',
			'var(--cad-teal)',
			'var(--cad-amber)',
			'var(--cad-cyan)',
		];

		const html = design_types
			.map((d, i) => {
				const segment = { type: 'design_type', design_type: d.design_type };
				const color = colors[i % colors.length];
				return `
					<div class="cad-lamp ${d.count > 0 ? 'cad-lamp--active' : ''}" style="--cad-lamp-color:${color}">
						<div class="cad-lamp__bulb"></div>
						<div>
							<div class="cad-lamp__label">${frappe.utils.escape_html(d.label)}</div>
							<div class="cad-lamp__count" data-segment="${seg_attr(segment)}">${this.fmt_count(d.count)}<span>orders</span></div>
						</div>
					</div>`;
			})
			.join('');

		this.$design_types.html(html);
	}
}