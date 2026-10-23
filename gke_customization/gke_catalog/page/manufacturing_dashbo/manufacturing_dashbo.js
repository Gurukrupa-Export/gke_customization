frappe.pages['manufacturing-dashbo'].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Manufacturing Dashboard',
		single_column: true,
	});

	new ManufacturingDashboard(page);
};

class ManufacturingDashboard {
	constructor(page) {
		this.page = page;
		this.method =
			'gke_customization.gke_catalog.report.mfg_dashboard_script.mfg_dashboard_script.get_dashboard_data';

		this.ACCENTS = {
			total: 'var(--mfg-steel)',
			generated: 'var(--mfg-emerald)',
			pending: 'var(--mfg-amber)',
			in_progress: 'var(--mfg-copper)',
			on_hold: 'var(--mfg-red)',
		};

		this.ICONS = {
			total: '📦',
			generated: '⚙️',
			pending: '⏳',
			in_progress: '🔧',
			on_hold: '⛔',
		};

		this.due_soon_days = 2;
		this.production_days = 7;

		// KPI cards that open an order list on click, keyed by order_summary key
		this.KPI_LISTS = {
			total: __('Total Orders'),
			generated: __('Generated Orders'),
			pending: __('Pending to Generate'),
			in_progress: __('In Progress Orders'),
			on_hold: __('On Hold / Cancelled Orders'),
		};

		const api = 'gke_customization.gke_catalog.report.mfg_dashboard_script.mfg_dashboard_script.';
		this.stage_method = api + 'get_stage_details';
		this.detail_method = api + 'get_order_details';
		this.alert_method = api + 'get_alert_orders';
		this.export_method = api + 'export_order_list';
		this.department_pieces_method = api + 'get_department_pieces';
		this.summary_orders_method = api + 'get_summary_orders';
		this.production_method = api + 'get_production_summary';
		this.production_pieces_method = api + 'get_production_pieces';
		this.image_method = api + 'get_catalogue_image';
		// a piece's ERP status, in the same flow order as the server's STAGE_STATUSES
		this.STATUS_COLORS = {
			Draft: 'var(--mfg-ink-faint)',
			'In-Transit': 'var(--mfg-amber)',
			'Not Started': 'var(--mfg-copper)',
			WIP: 'var(--mfg-steel)',
			'QC Pending': 'var(--mfg-await)',
			'QC Completed': 'var(--mfg-brass)',
			'On Hold': 'var(--mfg-red)',
			Revert: 'var(--mfg-ink-dim)',
			Finished: 'var(--mfg-emerald)',
		};
		// Drill-down state (sections 4-6): the operation tag picked in section 3, the status row
		// picked in the stage summary (null = all) and the order opened.
		this.selection = null;
		this.drill = { status: null, order: null };

		this.render_shell();
		this.setup_page_controls();
		if (!this.company_field.get_value()) {
			this.refresh();
		}
		this.start_auto_refresh();
	}

	// Reloads the whole dashboard every 10 minutes with the current filters (the open operation /
	// order drill-down is kept). Skipped while the user is on another desk page or the browser tab
	// is hidden, so a dashboard left open in the background doesn't keep hitting the server.
	start_auto_refresh() {
		const AUTO_REFRESH_MS = 10 * 60 * 1000;
		setInterval(() => {
			if (document.hidden) return;
			if (frappe.get_route()[0] !== 'manufacturing-dashbo') return;
			this.refresh();
		}, AUTO_REFRESH_MS);
	}

	// The filter controls are rendered inside our own template (not via page.add_field's
	// toolbar row) so they are always visible regardless of desk theme/version - some Frappe
	// versions tuck page-toolbar fields behind a collapsed filter affordance that's easy to miss.
	setup_page_controls() {
		const page = this.page;

		page.set_secondary_action(__('Refresh'), () => this.refresh(), 'refresh');

		this.page.main.find('[data-field="clear-filters"]').on('click', () => this.clear_filters());

		// unticked by default: completed (tagged / sold) pieces are left out of every number.
		// Set up before the Company default below, which can trigger the first refresh.
		this.$include_completed = this.page.main.find('[data-field="include-completed"]');
		this.$include_completed.on('change', () => this.refresh());

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

		const default_company = frappe.defaults.get_user_default('Company');
		if (default_company) {
			this.company_field.set_value(default_company);
		}

		// Customer and Order Date are optional refinements on top of Company - left blank
		// they don't filter anything; picking either re-scopes every number on the dashboard.
		// multi-select; refresh is debounced so ticking several customers reloads once, not per tick
		const refresh_for_customers = frappe.utils.debounce(() => this.refresh(), 700);
		this.customer_field = frappe.ui.form.make_control({
			df: {
				fieldname: 'customer',
				fieldtype: 'MultiSelectList',
				placeholder: __('All Customers'),
				get_data: (txt) => frappe.db.get_link_options('Customer', txt),
				onchange: refresh_for_customers,
			},
			parent: this.page.main.find('[data-field="customer-field"]'),
			render_input: true,
		});
		this.customer_field.refresh();

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

		// matched on the order's Updated Delivery Date, falling back to its Delivery Date
		this.delivery_range_field = frappe.ui.form.make_control({
			df: {
				fieldname: 'delivery_date_range',
				fieldtype: 'DateRange',
				placeholder: __('All Dates'),
				onchange: () => this.refresh(),
			},
			parent: this.page.main.find('[data-field="delivery-range-field"]'),
			render_input: true,
		});
		this.delivery_range_field.refresh();
	}

	get_date_range(field = this.daterange_field) {
		const value = field.get_value();
		if (!value || !value[0] || !value[1]) return [null, null];
		return [value[0], value[1]];
	}

	clear_filters() {
		this.company_field.set_value('');
		this.customer_field.set_value([]);
		this.daterange_field.set_value('');
		this.delivery_range_field.set_value('');
		this.$include_completed.prop('checked', false);
		this.refresh();
	}

	render_shell() {
		this.page.main.html(frappe.render_template('manufacturing_dashbo', {}));
		this.$kpi_row = this.page.main.find('[data-field="kpi-row"]');
		this.$dept_line = this.page.main.find('[data-field="dept-line"]');
		this.$status_legend = this.page.main.find('[data-field="status-legend"]');
		this.$andon = this.page.main.find('[data-field="andon-board"]');
		this.$production = this.page.main.find('[data-field="production-board"]');
		this.$generated_at = this.page.main.find('[data-field="generated-at"]');
		this.$ops = this.page.main.find('[data-field="ops-board"]');
		this.$stage = this.page.main.find('[data-field="stage-board"]');
		this.$stage_title = this.page.main.find('[data-field="stage-title"]');
		this.$orders = this.page.main.find('[data-field="orders-board"]');
		this.$orders_title = this.page.main.find('[data-field="orders-title"]');
		this.$detail = this.page.main.find('[data-field="detail-board"]');
		this.$detail_title = this.page.main.find('[data-field="detail-title"]');
		this.render_drill_hints();

		// The department rail only scrolls horizontally, so let a plain vertical mouse-wheel
		// drive it too - otherwise a wheel over this section does nothing (page has no vertical
		// scroll here) and the only way to scroll is dragging the thin scrollbar directly.
		// Bound once here since $dept_line itself is never replaced, only its contents.
		this.$dept_line.on('wheel', (e) => {
			const el = e.currentTarget;
			if (el.scrollWidth <= el.clientWidth) return;
			if (e.originalEvent.deltaY === 0) return;
			el.scrollLeft += e.originalEvent.deltaY;
			e.preventDefault();
		});
	}

	build_call_args() {
		const [from_date, to_date] = this.get_date_range();
		const [delivery_from, delivery_to] = this.get_date_range(this.delivery_range_field);
		return {
			company: this.company_field.get_value(),
			due_soon_days: this.due_soon_days,
			customer: (this.customer_field.get_value() || []).length ? this.customer_field.get_value() : undefined,
			from_date: from_date || undefined,
			to_date: to_date || undefined,
			delivery_from: delivery_from || undefined,
			delivery_to: delivery_to || undefined,
			include_completed: this.$include_completed.prop('checked') ? 1 : 0,
		};
	}

	refresh() {
		const args = this.build_call_args();
		if (!args.company) {
			this.render_prompt(__('Select a Company above to view the dashboard.'));
			return;
		}

		this.render_loading();
		this.refresh_production();

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

	// Re-fetches everything (the backend computes it in one pass anyway) but only re-renders
	// the andon board, so tweaking the "due soon" day count doesn't flash/reset the KPI strip
	// and department rail above it.
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
				this.render_andon(this.data.alerts);
			},
		});
	}

	// compact = the smaller variant used inside the drill-down panels
	loading_html(text, compact = false) {
		return `
			<div class="mfgdash__loading ${compact ? 'mfgdash__loading--compact' : ''}">
				<div class="mfg-cyclone">
					<span class="mfg-cyclone__ring"></span>
					<span class="mfg-cyclone__ring"></span>
					<span class="mfg-cyclone__ring"></span>
					<span class="mfg-cyclone__core"></span>
				</div>
				<div class="mfgdash__loading-text">${frappe.utils.escape_html(text)}</div>
			</div>`;
	}

	render_loading() {
		const loading = (text) => this.loading_html(text);
		this.$kpi_row.html(loading(__('Loading order summary…')));
		this.$dept_line.html(loading(__('Loading department flow…')));
		this.$andon.html(loading(__('Loading alerts…')));
		this.$production.html(loading(__('Loading production…')));
		this.$ops.html(loading(__('Loading operations…')));
	}

	render_prompt(text) {
		const html = `<div class="mfgdash__empty" style="grid-column:1/-1">${frappe.utils.escape_html(text)}</div>`;
		this.$kpi_row.html(html);
		this.$dept_line.html('');
		this.$andon.html('');
		this.$production.html('');
		this.$ops.html('');
		this.render_drill_hints();
	}

	render() {
		this.render_kpis(this.data.order_summary);
		this.render_departments(this.data.departments);
		this.render_andon(this.data.alerts);
		this.render_operations(this.data.operations);
		this.refresh_drilldown();
		if (this.data.generated_at) {
			this.$generated_at.text('as of ' + frappe.datetime.str_to_user(this.data.generated_at));
		}
	}

	// ---- formatting helpers ----

	fmt_count(n) {
		return (n || 0).toLocaleString('en-IN');
	}

	fmt_wt(v, suffix) {
		if (v === null || v === undefined) return '—';
		return Number(v).toLocaleString('en-IN', { maximumFractionDigits: 2, minimumFractionDigits: 2 }) + ' ' + suffix;
	}

	// ---- KPI strip ----

	render_kpis(rows) {
		const total = (rows.find((r) => r.key === 'total') || {}).count || 0;

		const html = rows
			.map((row, i) => {
				const pct = total ? Math.min(100, Math.round((row.count / total) * 1000) / 10) : 0;
				const accent = this.ACCENTS[row.key] || 'var(--mfg-brass)';
				const icon = this.ICONS[row.key] || '📊';
				const clickable = row.key in this.KPI_LISTS;
				// On Hold / Cancelled also splits into the two under the weights, one line each:
				// count - metal - dia
				const part = (label, count, gold_wt, diamond_wt) => `
					<div class="mfg-kpi__readout mfg-kpi__readout--sub mfg-kpi__readout--split">
						<span>${label} <b>${this.fmt_count(count)}</b></span>
						<span>Metal <b>${this.fmt_wt(gold_wt, 'g')}</b></span>
						<span>Dia <b>${this.fmt_wt(diamond_wt, 'ct')}</b></span>
					</div>`;
				const split =
					row.key === 'on_hold'
						? part(__('On Hold'), row.on_hold, row.on_hold_gold_wt, row.on_hold_diamond_wt) +
						  part(__('Cancelled'), row.cancelled, row.cancelled_gold_wt, row.cancelled_diamond_wt)
						: '';
				return `
					<div class="mfg-kpi" style="--mfg-accent:${accent};--mfg-delay:${i * 60}ms" data-key="${row.key}"
						${clickable ? `title="${__('Click to view orders')}"` : ''}>
						<div class="mfg-kpi__label">${frappe.utils.escape_html(row.label)}</div>
						<div class="mfg-kpi__body">
							<div class="mfg-kpi__ring" data-field="ring" data-pct="${pct}" style="--pct:0">
								<span class="mfg-kpi__ring-pct">${pct}%</span>
							</div>
							<div class="mfg-kpi__count">${this.fmt_count(row.count)}</div>
							<div class="mfg-kpi__icon">${icon}</div>
						</div>
						<div class="mfg-kpi__readout">
							<span>Metal <b>${this.fmt_wt(row.gold_wt, 'g')}</b></span>
							<span>Dia <b>${this.fmt_wt(row.diamond_wt, 'ct')}</b></span>
						</div>
						${split}
					</div>`;
			})
			.join('');

		this.$kpi_row.html(html);

		this.$kpi_row.find('.mfg-kpi').on('click', (e) => {
			const key = e.currentTarget.dataset.key;
			if (key in this.KPI_LISTS) this.show_summary_orders(key);
		});

		// two-step so the browser paints --pct:0 first, then transitions to the real value
		// (a CSS transition never fires if the target value is already there on first paint).
		const $rings = this.$kpi_row.find('[data-field="ring"]');
		requestAnimationFrame(() => {
			$rings.each((_, el) => {
				el.style.setProperty('--pct', el.dataset.pct);
			});
		});

		this.bind_kpi_tilt();
	}

	// Mouse-tracked 3D tilt: the card rotates towards the cursor (perspective(700px)
	// rotateX/rotateY in the CSS `transform`, driven by these two custom properties) instead of
	// just lifting flat on hover - a small effect but it's what actually reads as "3D" rather
	// than merely "raised", which the box-shadow/bevel treatment alone doesn't achieve.
	bind_kpi_tilt() {
		const MAX_TILT = 10;

		this.$kpi_row.find('.mfg-kpi').on('mousemove', (e) => {
			const rect = e.currentTarget.getBoundingClientRect();
			const px = (e.clientX - rect.left) / rect.width - 0.5;
			const py = (e.clientY - rect.top) / rect.height - 0.5;
			e.currentTarget.style.setProperty('--tilt-x', (-py * MAX_TILT * 2).toFixed(2) + 'deg');
			e.currentTarget.style.setProperty('--tilt-y', (px * MAX_TILT * 2).toFixed(2) + 'deg');
		});

		this.$kpi_row.find('.mfg-kpi').on('mouseleave', (e) => {
			e.currentTarget.style.setProperty('--tilt-x', '0deg');
			e.currentTarget.style.setProperty('--tilt-y', '0deg');
		});
	}

	// ---- department production rail ----

	render_departments(departments) {
		const shown = departments.filter((d) => d.count > 0);

		if (!shown.length) {
			this.$dept_line.html('<div class="mfgdash__empty">No active manufacturing pieces for this company.</div>');
			return;
		}

		// legend: only the statuses some department card actually has
		const used = Object.keys(this.STATUS_COLORS).filter((s) => shown.some((d) => (d.statuses || {})[s]));
		this.$status_legend.html(
			used
				.map((s) => `<span><i style="background:${this.STATUS_COLORS[s]}"></i>${frappe.utils.escape_html(__(s))}</span>`)
				.join('')
		);

		const html = shown
			.map((dept, i) => {
				const total = dept.count || 0;
				// one ring segment per status, in flow order
				let from = 0;
				const segments = Object.keys(this.STATUS_COLORS)
					.filter((s) => (dept.statuses || {})[s])
					.map((s) => {
						const to = from + (dept.statuses[s] / total) * 100;
						const seg = `${this.STATUS_COLORS[s]} ${from}% ${to}%`;
						from = to;
						return seg;
					});
				const ring = total && segments.length ? `conic-gradient(${segments.join(', ')})` : 'var(--mfg-track)';

				return `
					<div class="mfg-node" data-field="node" data-index="${i}" style="--mfg-delay:${i * 70}ms">
						<div class="mfg-node__ring mfg-node__ring--link" style="background:${ring}"
							data-field="piece-list" data-kind="all" title="Click to view the list">

							<div class="mfg-node__ring-glow"></div>
							<div class="mfg-node__count">
								<b>${this.fmt_count(total)}</b>
								<small>PIECES</small>
							</div>
						</div>
						<div class="mfg-node__name">${frappe.utils.escape_html(dept.name)}</div>
						<div class="mfg-node__stats">
							<span title="Metal weight">Metal <b>${this.fmt_wt(dept.gold_wt, 'g')}</b></span>
						</div>
						<div class="mfg-node__stats">
							<span title="Diamond weight">Dia <b>${this.fmt_wt(dept.diamond_wt, 'ct')}</b></span>
						</div>
						<div class="mfg-node__stats">
							<span title="Diamond pieces">Dia Pcs <b>${this.fmt_count(Math.round(dept.diamond_pcs || 0))}</b></span>
						</div>
						${
							dept.not_started
								? `<div class="mfg-node__stats mfg-node__stats--caution mfg-node__stats--link"
										data-field="piece-list" data-kind="not_started">
									<span title="Pieces received in this department with the operation still Not Started. Click to view the list">⏸ Not started <b>${this.fmt_count(dept.not_started)}</b></span>
								</div>`
								: ''
						}
					</div>`;
			})
			.join('');

		this.$dept_line.html(html);
		this.bind_node_tooltips(shown);

		// the pieces ring opens the department's full piece list, "Not started" just those pieces
		this.$dept_line.find('[data-field="piece-list"]').on('click', (e) => {
			e.stopPropagation();
			const dept = shown[Number($(e.currentTarget).closest('[data-field="node"]').data('index'))];
			// the "Other" card groups several departments, so it has no single department name to send
			const department = dept.name === __('Other') && !dept.department_id ? '__other__' : dept.name;
			this.show_department_pieces(department, dept.name, e.currentTarget.dataset.kind);
		});
	}

	// ---- operation-wise summary (section 3) ----

	render_operations(departments) {
		if (!departments || !departments.length) {
			this.$ops.html('<div class="mfgdash__empty mfgdash__empty--compact">No operation data.</div>');
			return;
		}

		const line = (dept, key, label, row, modifier) => `
			<div class="mfg-opline ${modifier || ''} ${row.count ? '' : 'mfg-opline--empty'}"
				data-field="opline" data-department="${frappe.utils.escape_html(dept.department_id)}"
				data-department-name="${frappe.utils.escape_html(dept.name)}"
				data-operation="${frappe.utils.escape_html(key)}" data-label="${frappe.utils.escape_html(label)}"
				title="${__('Click to view stage-wise summary and orders')}">
				<div class="mfg-opline__name">${frappe.utils.escape_html(label)}</div>
				<div class="mfg-opline__vals">
					<span><small>Pcs</small><b>${this.fmt_count(row.count)}</b></span>
					<span><small>Metal</small><b>${this.fmt_wt(row.gold_wt, '').trim()}<em>g</em></b></span>
					<span><small>Dia</small><b>${this.fmt_wt(row.diamond_wt, '').trim()}<em>ct</em></b></span>
				</div>
			</div>`;

		const html = departments
			.map((dept, i) => {
				// operations with no pieces on them are left out entirely
				const lines = dept.operations
					.filter((op) => op.count > 0)
					.map((op) => line(dept, op.operation, op.label, op));
				if (dept.awaiting_operation.count) {
					lines.push(
						line(dept, '__awaiting__', __('Awaiting Operation'), dept.awaiting_operation, 'mfg-opline--awaiting')
					);
				}
				return `
					<div class="mfg-opdept" style="--mfg-delay:${i * 60}ms">
						<div class="mfg-opdept__title">${frappe.utils.escape_html(dept.name)}</div>
						<div class="mfg-opdept__lines">${
							lines.join('') ||
							`<div class="mfgdash__empty mfgdash__empty--compact">${__('No orders in this department.')}</div>`
						}</div>
						${line(dept, '__all__', __('Total'), dept.total, 'mfg-opline--total')}
					</div>`;
			})
			.join('');

		this.$ops.html(html);
		this.limit_visible_operations(3);
		this.mark_selected_operation();

		this.$ops.find('[data-field="opline"]').on('click', (e) => {
			const d = e.currentTarget.dataset;
			this.selection = {
				department: d.department,
				department_name: d.departmentName,
				operation: d.operation,
				label: d.label,
			};
			this.drill = { status: null, order: null };
			this.mark_selected_operation();
			this.load_stage();
			this.render_detail_hint();
		});
	}

	mark_selected_operation() {
		const sel = this.selection;
		this.$ops.find('[data-field="opline"]').each((_, el) => {
			const on = !!sel && el.dataset.department === sel.department && el.dataset.operation === sel.operation;
			el.classList.toggle('is-selected', on);
		});
	}

	// Each department box shows `count` operation cards; the rest scroll inside the box (Total
	// stays pinned below). Measured rather than a fixed CSS height because long operation names
	// wrap to two lines, which makes cards different heights.
	limit_visible_operations(count) {
		this.$ops.find('.mfg-opdept__lines').each((_, el) => {
			if (el.children.length <= count) return;
			const last = el.children[count - 1];
			// max-height is border-box here, so add the tray's bottom padding + the tag's own gap
			const height =
				last.offsetTop +
				last.offsetHeight +
				parseFloat(getComputedStyle(last).marginBottom || 0) +
				parseFloat(getComputedStyle(el).paddingBottom || 0);
			if (height > 0) el.style.maxHeight = height + 'px';
			el.classList.add('is-scrollable');
		});
	}

	// ---- drill-down: stage-wise summary / order list / order details (sections 4-6) ----

	render_drill_hints() {
		const hint = (text) => `<div class="mfgdash__empty mfgdash__empty--compact">${text}</div>`;
		this.$stage_title.text('');
		this.$orders_title.text('');
		this.$stage.html(hint(__('Click an operation in the Operation-wise Summary above.')));
		this.$orders.html(hint(__('Orders of the selected operation will be listed here.')));
		this.render_detail_hint();
	}

	render_detail_hint() {
		this.$detail_title.text('');
		this.$detail.html(
			`<div class="mfgdash__empty mfgdash__empty--compact">${__('Click an order in the list to see its details.')}</div>`
		);
	}

	// After a dashboard refresh / filter change: keep the drill-down on the same operation (if its
	// department is still in the operation summary), otherwise clear it.
	refresh_drilldown() {
		const sel = this.selection;
		const still_there =
			sel && (this.data.operations || []).some((d) => d.department_id === sel.department);
		if (!still_there) {
			this.selection = null;
			this.drill = { status: null, order: null };
			this.render_drill_hints();
			return;
		}
		this.load_stage();
		if (this.drill.order) this.load_order(this.drill.order);
	}

	// keep_stage: only the status filter changed, so the stage table stays on screen (dimmed)
	// instead of being swapped for a spinner
	load_stage({ keep_stage = false } = {}) {
		const sel = this.selection;
		if (!sel) return;
		const args = this.build_call_args();
		const token = (this.stage_token = (this.stage_token || 0) + 1);

		const crumb = `— ${sel.department_name} · ${sel.label}`;
		this.$stage_title.text(crumb);
		this.$orders_title.text(`— ${sel.label} · ${this.drill.status || __('All')}`);
		if (keep_stage) {
			this.$stage.addClass('is-busy');
		} else {
			this.$stage.html(this.loading_html(__('Loading stages…'), true));
		}
		this.$orders.html(this.loading_html(__('Loading orders…'), true));

		frappe.call({
			method: this.stage_method,
			args: {
				company: args.company,
				department: sel.department,
				operation: sel.operation,
				status: this.drill.status || undefined,
				customer: args.customer,
				from_date: args.from_date,
				to_date: args.to_date,
				delivery_from: args.delivery_from,
				delivery_to: args.delivery_to,
				include_completed: args.include_completed,
			},
			freeze: false,
			callback: (r) => {
				if (token !== this.stage_token || !r.message) return;
				this.$stage.removeClass('is-busy');
				this.render_stage(r.message);
				this.render_orders(r.message);
			},
			error: () => {
				if (token !== this.stage_token) return;
				this.$stage.removeClass('is-busy');
				this.$stage.html(`<div class="mfgdash__empty mfgdash__empty--compact">${__('Could not load stages.')}</div>`);
				this.$orders.html(`<div class="mfgdash__empty mfgdash__empty--compact">${__('Could not load orders.')}</div>`);
			},
		});
	}

	render_stage(data) {
		const row = (key, label, s, color) => `
			<tr class="mfg-stage__row ${this.drill.status === key ? 'is-selected' : ''} ${s.count ? '' : 'is-empty'}"
				data-field="stage-row" data-status="${key || ''}">
				<td><i class="mfg-dot" style="background:${color}"></i>${frappe.utils.escape_html(label)}</td>
				<td>${this.fmt_count(s.count)}</td>
				<td>${this.fmt_wt(s.gold_wt, '').trim()}</td>
				<td>${this.fmt_wt(s.diamond_wt, '').trim()}</td>
			</tr>`;

		// only the statuses this operation has (plus the one being filtered on, so it can be cleared)
		const rows = data.stages
			.filter((s) => s.count || s.status === this.drill.status)
			.map((s) => row(s.status, __(s.status), s, this.STATUS_COLORS[s.status]));

		this.$stage.html(`
			<table class="mfg-table mfg-stage">
				<thead><tr><th>${__('Status')}</th><th>${__('Pcs')}</th><th>${__('Metal (g)')}</th><th>${__('Dia (ct)')}</th></tr></thead>
				<tbody>${rows.join('')}</tbody>
				<tfoot>${row(null, __('Total'), data.total, 'var(--mfg-brass)')}</tfoot>
			</table>`);

		this.$stage.find('[data-field="stage-row"]').on('click', (e) => {
			const status = e.currentTarget.dataset.status || null;
			this.drill.status = status;
			this.load_stage({ keep_stage: true });
		});
	}

	render_orders(data) {
		const orders = data.orders || [];
		if (!orders.length) {
			this.$orders.html(`<div class="mfgdash__empty mfgdash__empty--compact">${__('No orders.')}</div>`);
			return;
		}

		const date = (v) => (v ? frappe.datetime.str_to_user(String(v).split(' ')[0]) : '—');
		const esc = (v) => frappe.utils.escape_html(v || '—');
		const rows = orders
			.map(
				(o) => `
				<tr class="mfg-orders__row ${this.drill.order === o.order_no ? 'is-selected' : ''}"
					data-field="order-row" data-order="${frappe.utils.escape_html(o.order_no)}">
					<td>${this.mwo_link_html(o.mwo)}</td>
					<td>${esc(o.employee_name || o.employee)}</td>
					<td>${esc(o.design_no)}</td>
					<td>${esc(o.item_category)}</td>
					<td class="is-num">${this.fmt_wt(o.gold_wt, '').trim()}</td>
					<td class="is-num">${this.fmt_wt(o.diamond_wt, '').trim()}</td>
					<td class="is-num">${this.fmt_count(Math.round(o.diamond_pcs || 0))}</td>
					<td>${date(o.issue_date)}</td>
					<td>${date(o.due_date)}</td>
					<td class="mfg-orders__no">
						<i class="mfg-dot" style="background:${this.STATUS_COLORS[o.stage_status] || 'var(--mfg-border)'}"
							title="${frappe.utils.escape_html(o.stage_status)}"></i>${esc(o.order_no)}
					</td>
				</tr>`
			)
			.join('');

		// columns after MWO (the first column, which holds the "Total" label), as far as the Total row is concerned
		const total_columns = [
			{ value: () => '' },
			{ value: () => '' },
			{ value: () => '' },
			{ num: true, sum: 'gold_wt', value: (o) => this.fmt_wt(o.gold_wt, '').trim() },
			{ num: true, sum: 'diamond_wt', value: (o) => this.fmt_wt(o.diamond_wt, '').trim() },
			{ num: true, sum: 'diamond_pcs', value: (o) => this.fmt_count(Math.round(o.diamond_pcs || 0)) },
			{ value: () => '' },
			{ value: () => '' },
			{ value: () => '' },
		];

		// every order is loaded; the table scrolls inside the fixed-height panel (header stays pinned)
		this.$orders.html(`
			<div class="mfg-orders__scroll">
				<table class="mfg-table mfg-orders">
					<thead>
						<tr>
							<th>${__('MWO')}</th><th>${__('Employee')}</th><th>${__('Design No')}</th><th>${__('Item')}</th>
							<th class="is-num">${__('Metal (g)')}</th><th class="is-num">${__('Dia (ct)')}</th>
							<th class="is-num">${__('Dia Pcs')}</th>
							<th>${__('Operation Start Date')}</th><th>${__('Due Date')}</th><th>${__('Order No')}</th>
						</tr>
						${this.search_row_html(total_columns.length + 1)}
					</thead>
					<tbody>${rows}</tbody>
					<tfoot>${this.order_totals_row(total_columns, orders)}</tfoot>
				</table>
			</div>
			<div class="mfg-pager">
				<span>${__('Total Records')}: <b data-field="shown">${this.fmt_count(data.order_count)}</b></span>
				<button type="button" class="mfg-pager__export" data-field="export-orders">${__('Export Excel')}</button>
			</div>`);

		// rows left on screen after the column searches - what the Total row and the export cover
		let shown = orders;
		this.bind_column_search(this.$orders, orders, (rows, searching) => {
			shown = rows;
			this.$orders.find('tfoot').html(this.order_totals_row(total_columns, shown));
			this.$orders.find('[data-field="shown"]').text(
				searching
					? __('{0} of {1}', [this.fmt_count(shown.length), this.fmt_count(data.order_count)])
					: this.fmt_count(data.order_count)
			);
		});

		// same Excel export as the order-list dialogs: the rows on screen, plus the Total row
		this.$orders.find('[data-field="export-orders"]').on('click', () => {
			const sum = (field) => flt(shown.reduce((acc, o) => acc + (Number(o[field]) || 0), 0), 3);
			const day = (v) => (v ? frappe.datetime.str_to_user(String(v).split(' ')[0]) : '');
			const sel = this.selection;
			open_url_post(frappe.request.url, {
				cmd: this.export_method,
				title: `${__('Order List')} ${sel ? sel.label : ''} ${this.drill.status || __('All')}`,
				rows: JSON.stringify([
					[__('MWO'), __('Employee'), __('Design No'), __('Item'), __('Metal (g)'), __('Dia (ct)'), __('Dia Pcs'), __('Operation Start Date'), __('Due Date'), __('Order No')],
					...shown.map((o) => [
						o.mwo || '',
						o.employee_name || o.employee || '',
						o.design_no || '',
						o.item_category || '',
						flt(o.gold_wt, 3),
						flt(o.diamond_wt, 3),
						Math.round(o.diamond_pcs || 0),
						day(o.issue_date),
						day(o.due_date),
						o.order_no || '',
					]),
					[__('Total'), '', '', '', sum('gold_wt'), sum('diamond_wt'), Math.round(sum('diamond_pcs')), '', '', ''],
				]),
			});
		});

		// the MWO link opens in a new tab without also selecting the row
		this.$orders.find('[data-field="order-row"] a').on('click', (e) => e.stopPropagation());

		this.$orders.find('[data-field="order-row"]').on('click', (e) => {
			this.drill.order = e.currentTarget.dataset.order;
			this.$orders.find('[data-field="order-row"]').removeClass('is-selected');
			e.currentTarget.classList.add('is-selected');
			this.load_order(this.drill.order);
		});
	}

	load_order(order_no) {
		const token = (this.detail_token = (this.detail_token || 0) + 1);
		this.$detail_title.text('— ' + order_no);
		this.$detail.html(this.loading_html(__('Loading order…'), true));

		frappe.call({
			method: this.detail_method,
			args: { company: this.company_field.get_value(), order_no },
			freeze: false,
			callback: (r) => {
				if (token !== this.detail_token || !r.message) return;
				this.render_order_detail(r.message);
			},
			error: () => {
				if (token !== this.detail_token) return;
				this.$detail.html(`<div class="mfgdash__empty mfgdash__empty--compact">${__('Could not load order.')}</div>`);
			},
		});
	}

	render_order_detail(d) {
		const esc = (v) => frappe.utils.escape_html(v === null || v === undefined || v === '' ? '—' : String(v));
		const date = (v) => (v ? frappe.datetime.str_to_user(String(v).split(' ')[0]) : '—');
		// gross/net are the operation's actual weighings - 0 means not weighed yet, not 0 g
		const actual = (v, unit) => (v ? this.fmt_wt(v, unit) : '—');
		const field = (label, value_html) => `<dt>${label}</dt><dd>${value_html}</dd>`;

		const order_link = `<a href="/app/parent-manufacturing-order/${encodeURIComponent(d.order_no)}"
			target="_blank" rel="noopener">${esc(d.order_no)}</a>`;
		const status = `<span class="mfg-chip" style="--chip:${this.STATUS_COLORS[d.status] || 'var(--mfg-border)'}">${esc(d.status)}</span>`;

		this.$detail.html(`
			<div class="mfg-detail">
				<dl class="mfg-detail__list">
					${field(__('Order No'), order_link)}
					${field(__('Sales Order'), esc(d.sales_order))}
					${field(__('Order Date'), date(d.order_date))}
					${field(__('Customer'), esc(d.customer_name || d.customer))}
					${field(__('Design No'), esc(d.design_no))}
					${field(__('Item'), esc(d.item_category))}
					${field(__('Sub Category'), esc(d.item_sub_category))}
					${field(__('Qty'), esc(d.qty))}
					${field(__('Due Date'), date(d.due_date))}
					${field(__('Department'), esc(d.department))}
					${field(__('Operation'), esc(d.operation))}
					${field(__('Status'), status)}
					${field(__('Employee'), esc(d.employee_name || d.employee))}
					${field(__('Operation Start Date'), date(d.issue_date))}
					${field(__('Work Order'), this.mwo_link_html(d.work_order))}
				</dl>
				<div class="mfg-detail__materials">
					<div class="mfg-detail__heading">${__('Materials & Weight')}</div>
					<div class="mfg-detail__materials-body">
						<dl class="mfg-detail__list">
							${field(__('Metal Touch'), esc(d.metal_touch))}
							${field(__('Metal Colour'), esc(d.metal_colour))}
							${field(__('Metal Wt'), this.fmt_wt(d.metal_wt, 'g'))}
							${field(__('Gross Wt'), actual(d.gross_wt, 'g'))}
							${field(__('Diamond Wt'), this.fmt_wt(d.diamond_wt, 'ct'))}
							${field(__('Diamond Pcs'), this.fmt_count(Math.round(d.diamond_pcs || 0)))}
							${field(__('Gemstone Wt'), this.fmt_wt(d.gemstone_wt, 'ct'))}
						</dl>
						${this.catalogue_image_html(d)}
					</div>
				</div>
			</div>`);

		if (d.has_catalogue_image) this.load_catalogue_image(d.order_no, d.design_no);
	}

	// Item's Catalogue Image (custom_catalogue_image) only - no fallback to the other item images.
	// Only a placeholder here; load_catalogue_image fills it in.
	catalogue_image_html(d) {
		if (!d.has_catalogue_image) {
			return `<div class="mfg-detail__image mfg-detail__image--empty">${__('No catalogue image')}</div>`;
		}
		return `
			<button type="button" class="mfg-detail__image is-loading" data-field="catalogue-image"
				title="${__('Click to view full size')}" disabled>
				<span class="mfg-detail__image-msg">${__('Loading…')}</span>
			</button>`;
	}

	// The image is streamed through a permission-checked server method and shown from an in-memory
	// blob: URL, so the stored image path / S3 link is never in the page, the DOM or the network log.
	load_catalogue_image(order_no, design_no) {
		const token = this.detail_token;
		if (this.catalogue_blob_url) {
			URL.revokeObjectURL(this.catalogue_blob_url);
			this.catalogue_blob_url = null;
		}
		const $box = this.$detail.find('[data-field="catalogue-image"]');
		const url = `/api/method/${this.image_method}?order_no=${encodeURIComponent(order_no)}`;

		fetch(url, { credentials: 'same-origin', headers: { 'X-Frappe-CSRF-Token': frappe.csrf_token } })
			.then((res) => {
				if (!res.ok) throw new Error(res.status);
				return res.blob();
			})
			.then((blob) => {
				if (token !== this.detail_token) return;
				this.catalogue_blob_url = URL.createObjectURL(blob);
				const img = document.createElement('img');
				img.src = this.catalogue_blob_url;
				img.alt = design_no || '';
				this.protect_image(img);
				$box.removeClass('is-loading').prop('disabled', false).empty().append(img);
				$box.on('click', () => this.show_image_full(this.catalogue_blob_url, design_no));
			})
			.catch(() => {
				if (token !== this.detail_token) return;
				$box.replaceWith(
					`<div class="mfg-detail__image mfg-detail__image--empty">${__('Image not available')}</div>`
				);
			});
	}

	// no right-click "Save / Copy image address", no drag-out to the desktop
	protect_image(img) {
		img.draggable = false;
		img.addEventListener('contextmenu', (e) => e.preventDefault());
		img.addEventListener('dragstart', (e) => e.preventDefault());
	}

	// Full-size lightbox: click anywhere or press Esc to close.
	show_image_full(src, caption) {
		const $overlay = $(`
			<div class="mfg-lightbox">
				<img src="${src}" alt="" />
				${caption ? `<div class="mfg-lightbox__caption">${frappe.utils.escape_html(caption)}</div>` : ''}
				<button type="button" class="mfg-lightbox__close" aria-label="${__('Close')}">&times;</button>
			</div>`).appendTo(document.body);
		$overlay.on('contextmenu', (e) => e.preventDefault());
		this.protect_image($overlay.find('img')[0]);

		const close = () => {
			$overlay.remove();
			$(document).off('keydown.mfg-lightbox');
		};
		$overlay.on('click', close);
		$(document).on('keydown.mfg-lightbox', (e) => {
			if (e.key === 'Escape') close();
		});
	}

	// ---- department node tooltip ----

	get_tooltip() {
		// appended inside .mfgdash (not document.body) so it inherits the theme's CSS custom
		// properties via the DOM tree; position:fixed still lets it escape the scrollable rail.
		if (!this.$tooltip) {
			this.$tooltip = $('<div class="mfg-tooltip"></div>').appendTo(this.page.main.find('.mfgdash'));
		}
		return this.$tooltip;
	}

	bind_node_tooltips(departments) {
		const $tooltip = this.get_tooltip();

		this.$dept_line.find('[data-field="node"]').each((i, el) => {
			const dept = departments[i];
			if (!dept) return;
			const $node = $(el);

			$node.on('mouseenter', () => {
				$tooltip.html(this.tooltip_html(dept));
				this.position_tooltip($tooltip, el);
				$tooltip.addClass('is-visible');
			});
			$node.on('mouseleave', () => {
				$tooltip.removeClass('is-visible');
			});
		});
	}

	tooltip_html(dept) {
		const total = dept.count || 0;
		const pct = (n) => (total ? Math.round((n / total) * 100) : 0);
		return `
			<div class="mfg-tooltip__title">${frappe.utils.escape_html(dept.name)}</div>
			<div class="mfg-tooltip__row"><span>Total pieces</span><b>${this.fmt_count(total)}</b></div>
			${Object.keys(this.STATUS_COLORS)
				.filter((s) => (dept.statuses || {})[s])
				.map(
					(s) => `<div class="mfg-tooltip__row"><i class="mfg-dot" style="background:${this.STATUS_COLORS[s]}"></i>
						<span>${frappe.utils.escape_html(__(s))}</span><b>${this.fmt_count(dept.statuses[s])} (${pct(dept.statuses[s])}%)</b></div>`
				)
				.join('')}
			<div class="mfg-tooltip__divider"></div>
			<div class="mfg-tooltip__row"><span>Metal wt</span><b>${this.fmt_wt(dept.gold_wt, 'g')}</b></div>
			<div class="mfg-tooltip__row"><span>Diamond wt</span><b>${this.fmt_wt(dept.diamond_wt, 'ct')}</b></div>
			<div class="mfg-tooltip__row"><span>Diamond pcs</span><b>${this.fmt_count(Math.round(dept.diamond_pcs || 0))}</b></div>`;
	}

	position_tooltip($tooltip, node_el) {
		const rect = node_el.getBoundingClientRect();
		const tw = $tooltip.outerWidth();
		let left = rect.left + rect.width / 2 - tw / 2;
		left = Math.max(8, Math.min(left, window.innerWidth - tw - 8));
		const top = rect.top - $tooltip.outerHeight() - 10;
		$tooltip.css({ left: left + 'px', top: Math.max(8, top) + 'px' });
	}

	// ---- andon alert board ----

	render_andon(alerts) {
		if (!alerts) {
			this.$andon.html('<div class="mfgdash__empty">No alert data.</div>');
			return;
		}

		const due_soon = alerts.due_soon || { count: 0 };
		const overdue = alerts.overdue || { count: 0 };
		if (due_soon.days !== undefined && due_soon.days !== null) {
			this.due_soon_days = due_soon.days;
		}

		const lamp = (key, label_html, data, color) => {
			const active = data.count > 0;
			return `
				<div class="mfg-lamp ${active ? 'mfg-lamp--active' : ''}" style="--mfg-lamp-color:${color}">
					<div class="mfg-lamp__bulb"></div>
					<div>
						<div class="mfg-lamp__label">${label_html}</div>
						<div class="mfg-lamp__count ${active ? 'is-clickable' : ''}" data-field="alert-count"
							data-alert="${key}" ${active ? `title="${__('Click to view orders')}"` : ''}>
							${this.fmt_count(data.count)}<span>orders</span>
						</div>
					</div>
					<div class="mfg-lamp__wts">
						<div class="mfg-lamp__wt-label">Metal</div>
						<div class="mfg-lamp__wt-value">${this.fmt_wt(data.gold_wt, 'g')}</div>
						<div class="mfg-lamp__wt-label">Dia</div>
						<div class="mfg-lamp__wt-value">${this.fmt_wt(data.diamond_wt, 'ct')}</div>
					</div>
				</div>`;
		};

		const due_soon_label = `Due Soon (within
			<input type="number" class="mfg-lamp__days-input" data-field="due-soon-days"
				min="0" max="365" step="1" value="${this.due_soon_days}" /> days)`;

		const html =
			lamp('due_soon', due_soon_label, due_soon, 'var(--mfg-amber)') +
			lamp('overdue', 'Overdue', overdue, 'var(--mfg-red)');

		this.$andon.html(html);

		this.$andon.find('[data-field="alert-count"].is-clickable').on('click', (e) => {
			this.show_alert_orders(e.currentTarget.dataset.alert);
		});

		this.$andon.find('[data-field="due-soon-days"]').on('change', (e) => {
			let value = parseInt(e.target.value, 10);
			if (isNaN(value) || value < 0) value = 0;
			e.target.value = value;
			this.due_soon_days = value;
			this.refresh_alerts();
		});
	}

	// ---- production (tagged pieces) ----

	// Its own light call, so changing the day count doesn't reload the rest of the dashboard.
	refresh_production() {
		const args = this.build_call_args();
		if (!args.company) return;
		const token = (this.production_token = (this.production_token || 0) + 1);

		frappe.call({
			method: this.production_method,
			args: {
				company: args.company,
				days: this.production_days,
				customer: args.customer,
				from_date: args.from_date,
				to_date: args.to_date,
				delivery_from: args.delivery_from,
				delivery_to: args.delivery_to,
			},
			freeze: false,
			callback: (r) => {
				if (token !== this.production_token || !r.message) return;
				this.render_production(r.message);
			},
			error: () => {
				this.$production.html(`<div class="mfgdash__empty">${__('Could not load production.')}</div>`);
			},
		});
	}

	render_production(data) {
		const active = data.count > 0;
		const label = `Production (last
			<input type="number" class="mfg-lamp__days-input" data-field="production-days"
				min="1" max="365" step="1" value="${this.production_days}" /> days)`;
		this.$production.html(`
			<div class="mfg-lamp ${active ? 'mfg-lamp--active' : ''}" style="--mfg-lamp-color:var(--mfg-emerald)">
				<div class="mfg-lamp__bulb"></div>
				<div>
					<div class="mfg-lamp__label">${label}</div>
					<div class="mfg-lamp__count ${active ? 'is-clickable' : ''}" data-field="production-count"
						${active ? `title="${__('Click to view pieces')}"` : ''}>
						${this.fmt_count(data.count)}<span>pcs</span>
					</div>
				</div>
				<div class="mfg-lamp__wts">
					<div class="mfg-lamp__wt-label">Gold</div>
					<div class="mfg-lamp__wt-value">${this.fmt_wt(data.gold_wt, 'g')}</div>
					<div class="mfg-lamp__wt-label">Dia</div>
					<div class="mfg-lamp__wt-value">${this.fmt_wt(data.diamond_wt, 'ct')}</div>
				</div>
			</div>`);

		this.$production.find('[data-field="production-count"].is-clickable').on('click', () => this.show_production_pieces());

		this.$production.find('[data-field="production-days"]').on('change', (e) => {
			let value = parseInt(e.target.value, 10);
			if (isNaN(value) || value < 1) value = 1;
			e.target.value = value;
			this.production_days = value;
			this.refresh_production();
		});
	}

	show_production_pieces() {
		const wt = (field) => ({ num: true, sum: field, value: (o) => this.fmt_wt(o[field], '').trim() });
		const days_title = __('Production - Last {0} Days', [this.production_days]);
		this.show_order_list({
			title: days_title,
			method: this.production_pieces_method,
			args: { days: this.production_days },
			// Serial No Date range inside the list: when both ends are picked it overrides the
			// lamp's "last N days"; cleared, the list goes back to the days count
			filter_bar: ($bar, reload) => {
				$bar.addClass('mfgdash__filter mfg-list-filter').html(
					`<label>${__('Serial No Date')}</label><div data-field="list-range"></div>`
				);
				const range = frappe.ui.form.make_control({
					df: {
						fieldname: 'serial_no_date',
						fieldtype: 'DateRange',
						placeholder: __('Last {0} days', [this.production_days]),
						onchange: () => {
							const value = range.get_value();
							const [from, to] = value && value[0] && value[1] ? value : [null, null];
							reload(
								{ production_from: from || undefined, production_to: to || undefined },
								from
									? __('Production - {0} to {1}', [
											frappe.datetime.str_to_user(from),
											frappe.datetime.str_to_user(to),
									  ])
									: days_title
							);
						},
					},
					parent: $bar.find('[data-field="list-range"]'),
					render_input: true,
				});
				range.refresh();
			},
			link: { label: __('Serial No'), route: 'serial-no', field: 'serial_no' },
			columns: [
				{ label: __('Serial No Date'), value: (o, esc, date) => date(o.serial_date) },
				{
					label: __('PMO'),
					value: (o, esc) =>
						o.pmo
							? `<a href="/app/parent-manufacturing-order/${encodeURIComponent(o.pmo)}" target="_blank"
								rel="noopener">${esc(o.pmo)}</a>`
							: '—',
				},
				{ label: __('Net Wt (g)'), ...wt('net_wt') },
				{ label: __('Finding Wt (g)'), ...wt('finding_wt') },
				{ label: __('Dia Wt (ct)'), ...wt('diamond_wt') },
				{ label: __('Gold Wt (g)'), ...wt('gold_wt') },
				// serial no date - first Casting operation start date (blank if never cast)
				{
					label: __('Production Days'),
					num: true,
					value: (o) => (o.production_days === null || o.production_days === undefined ? '—' : o.production_days),
				},
			],
		});
	}

	// Order list behind a Due Soon / Overdue lamp, in a dialog so the drill-down panels below
	// keep whatever operation the user had open.
	show_alert_orders(alert) {
		const days = (n) => {
			if (n < 0) return `<span class="mfg-alert-orders__late">${__('{0} days late', [-n])}</span>`;
			if (n === 0) return `<span class="mfg-alert-orders__soon">${__('Today')}</span>`;
			return `<span class="mfg-alert-orders__soon">${__('{0} days left', [n])}</span>`;
		};

		this.show_order_list({
			title:
				alert === 'overdue'
					? __('Overdue Orders')
					: __('Orders Due Within {0} Days', [this.due_soon_days]),
			method: this.alert_method,
			args: { alert },
			columns: [
				{ label: __('Customer'), value: (o, esc) => esc(o.customer) },
				{ label: __('Design No'), value: (o, esc) => esc(o.design_no) },
				{ label: __('Item'), value: (o, esc) => esc(o.item_category) },
				{ label: __('Department'), value: (o, esc) => esc(o.department) },
				{ label: __('Metal (g)'), num: true, sum: 'gold_wt', value: (o) => this.fmt_wt(o.gold_wt, '').trim() },
				{ label: __('Dia (ct)'), num: true, sum: 'diamond_wt', value: (o) => this.fmt_wt(o.diamond_wt, '').trim() },
				{ label: __('Dia Pcs'), num: true, sum: 'diamond_pcs', value: (o) => this.fmt_count(Math.round(o.diamond_pcs || 0)) },
				{ label: __('Due Date'), value: (o, esc, date) => date(o.due_date) },
				{ label: __('Due'), value: (o) => days(o.days_left) },
			],
		});
	}

	// Pieces behind a department card's total or "Not started" count.
	show_department_pieces(department, name, kind) {
		this.show_order_list({
			title: kind === 'all' ? __('{0} - All Pieces', [name]) : __('{0} - Not Started', [name]),
			method: this.department_pieces_method,
			args: { department, kind },
			columns: [
				{ label: __('Customer'), value: (o, esc) => esc(o.customer) },
				{ label: __('Design No'), value: (o, esc) => esc(o.design_no) },
				{ label: __('Item'), value: (o, esc) => esc(o.item_category) },
				// the "Other" card groups several departments, so show which one each piece is in
				...(department === '__other__'
					? [{ label: __('Department'), value: (o, esc) => esc(o.department) }]
					: []),
				{ label: __('Operation'), value: (o, esc) => esc(o.operation) },
				{ label: __('Metal (g)'), num: true, sum: 'gold_wt', value: (o) => this.fmt_wt(o.gold_wt, '').trim() },
				{ label: __('Dia (ct)'), num: true, sum: 'diamond_wt', value: (o) => this.fmt_wt(o.diamond_wt, '').trim() },
				{ label: __('Dia Pcs'), num: true, sum: 'diamond_pcs', value: (o) => this.fmt_count(Math.round(o.diamond_pcs || 0)) },
				{ label: __('Dept Issue Date'), value: (o, esc, date) => date(o.issue_date) },
				{ label: __('Due Date'), value: (o, esc, date) => date(o.due_date) },
				{ label: __('Employee'), value: (o, esc) => esc(o.employee_name || o.employee) },
			],
		});
	}

	// Rows behind the KPI cards. Total, Pending and On Hold/Cancelled are Sales Order Items,
	// Generated and In Progress are pieces.
	show_summary_orders(kind) {
		const title = this.KPI_LISTS[kind];
		const common = [
			{ label: __('Customer'), value: (o, esc) => esc(o.customer) },
			{ label: __('Design No'), value: (o, esc) => esc(o.design_no) },
			{ label: __('Item'), value: (o, esc) => esc(o.item_category) },
		];

		if (kind === 'total') {
			this.show_order_list({
				title,
				method: this.summary_orders_method,
				args: { kind },
				link: { label: __('Sales Order'), route: 'sales-order', field: 'sales_order' },
				columns: [
					...common,
					{ label: __('Qty'), num: true, sum: 'qty', value: (o) => this.fmt_count(o.qty) },
					{ label: __('Generated'), num: true, sum: 'generated', value: (o) => this.fmt_count(o.generated) },
					{ label: __('Pending'), num: true, sum: 'pending', value: (o) => this.fmt_count(o.pending) },
					{ label: __('Metal (g)'), num: true, sum: 'gold_wt', value: (o) => this.fmt_wt(o.gold_wt, '').trim() },
					{ label: __('Dia (ct)'), num: true, sum: 'diamond_wt', value: (o) => this.fmt_wt(o.diamond_wt, '').trim() },
					{ label: __('Dia Pcs'), num: true, sum: 'diamond_pcs', value: (o) => this.fmt_count(Math.round(o.diamond_pcs || 0)) },
					{ label: __('Order Date'), value: (o, esc, date) => date(o.order_date) },
					{ label: __('Delivery Date'), value: (o, esc, date) => date(o.due_date) },
				],
			});
			return;
		}

		if (kind === 'in_progress' || kind === 'generated') {
			this.show_order_list({
				title,
				method: this.summary_orders_method,
				args: { kind },
				columns: [
					...common,
					{ label: __('Department'), value: (o, esc) => esc(o.department) },
					{ label: __('Operation'), value: (o, esc) => esc(o.operation) },
					{ label: __('Metal (g)'), num: true, sum: 'gold_wt', value: (o) => this.fmt_wt(o.gold_wt, '').trim() },
					{ label: __('Dia (ct)'), num: true, sum: 'diamond_wt', value: (o) => this.fmt_wt(o.diamond_wt, '').trim() },
					{ label: __('Dia Pcs'), num: true, sum: 'diamond_pcs', value: (o) => this.fmt_count(Math.round(o.diamond_pcs || 0)) },
					{ label: __('Due Date'), value: (o, esc, date) => date(o.due_date) },
				],
			});
			return;
		}

		this.show_order_list({
			title,
			method: this.summary_orders_method,
			args: { kind },
			link: { label: __('Sales Order'), route: 'sales-order', field: 'sales_order' },
			columns: [
				...common,
				{ label: __('Qty'), num: true, sum: 'qty', value: (o) => this.fmt_count(o.qty) },
				{ label: __('Metal (g)'), num: true, sum: 'gold_wt', value: (o) => this.fmt_wt(o.gold_wt, '').trim() },
				{ label: __('Dia (ct)'), num: true, sum: 'diamond_wt', value: (o) => this.fmt_wt(o.diamond_wt, '').trim() },
				{ label: __('Dia Pcs'), num: true, sum: 'diamond_pcs', value: (o) => this.fmt_count(Math.round(o.diamond_pcs || 0)) },
				{ label: __('Order Date'), value: (o, esc, date) => date(o.order_date) },
				{ label: __('Delivery Date'), value: (o, esc, date) => date(o.due_date) },
				...(kind === 'on_hold' ? [{ label: __('Status'), value: (o, esc) => esc(o.so_status) }] : []),
			],
		});
	}

	// Shared order-list dialog: the whole list in one scrollable table with a search box under
	// every column header. The first column is the Order No linked to its Parent Manufacturing
	// Order, unless `link` names another doctype field. Export Excel downloads the table as it is
	// on screen (rows left after any column search, plus the Total row). `filter_bar($bar, reload)`
	// can put controls above the list; reload(extra_args, new_title) re-fetches it with them.
	show_order_list({ title, method, args, columns, link, filter_bar }) {
		// undefined filters are dropped so they aren't sent as the string "undefined"
		args = { ...this.build_call_args(), ...args };
		Object.keys(args).forEach((k) => args[k] === undefined && delete args[k]);

		const dialog = new frappe.ui.Dialog({
			title,
			size: 'extra-large',
			primary_action_label: __('Export Excel'),
			primary_action: () => {
				const export_rows = $body.data('export_rows');
				if (!export_rows) {
					frappe.show_alert({ message: __('Nothing to export'), indicator: 'orange' });
					return;
				}
				open_url_post(frappe.request.url, {
					cmd: this.export_method,
					title,
					rows: JSON.stringify(export_rows()),
				});
			},
		});
		// wrapped in .mfgdash so the dialog (appended to <body>) picks up the dashboard's theme tokens
		const $wrap = $('<div class="mfgdash mfgdash--dialog"><div class="mfg-alert-orders"></div></div>').appendTo(
			dialog.$body
		);
		const $body = $wrap.find('.mfg-alert-orders');
		dialog.show();

		let token = 0;
		const load = (call_args) => {
			const my_token = ++token;
			$body.removeData('export_rows');
			$body.html(`<div class="mfgdash__empty mfgdash__empty--compact">${__('Loading orders…')}</div>`);
			frappe.call({
				method,
				args: call_args,
				freeze: false,
				callback: (r) => {
					if (my_token === token && r.message) this.render_order_list($body, r.message, columns, link);
				},
				error: () => {
					if (my_token !== token) return;
					$body.html(`<div class="mfgdash__empty mfgdash__empty--compact">${__('Could not load orders.')}</div>`);
				},
			});
		};

		if (filter_bar) {
			filter_bar($('<div>').prependTo($wrap), (extra, new_title) => {
				const call_args = { ...args, ...extra };
				Object.keys(call_args).forEach((k) => call_args[k] === undefined && delete call_args[k]);
				if (new_title) {
					title = new_title;
					dialog.set_title(title);
				}
				load(call_args);
			});
		}
		load(args);
	}

	mwo_link_html(mwo) {
		if (!mwo) return '—';
		return `<a href="/app/manufacturing-work-order/${encodeURIComponent(mwo)}" target="_blank"
			rel="noopener">${frappe.utils.escape_html(mwo)}</a>`;
	}

	// "Total" footer row for an order table: every column with a `sum` field is added up over
	// `orders` and shown through the column's own formatter; the rest stay blank.
	order_totals_row(columns, orders) {
		const cells = columns.map((c) => {
			if (!c.sum) return '<td></td>';
			const total = orders.reduce((acc, o) => acc + (Number(o[c.sum]) || 0), 0);
			return `<td${c.num ? ' class="is-num"' : ''}>${c.value({ [c.sum]: total })}</td>`;
		});
		return `<tr class="mfg-orders__total"><td>${__('Total')}</td>${cells.join('')}</tr>`;
	}

	render_order_list($body, data, columns, link) {
		const orders = data.orders || [];
		if (!orders.length) {
			$body.html(`<div class="mfgdash__empty mfgdash__empty--compact">${__('No orders.')}</div>`);
			return;
		}

		const date = (v) => (v ? frappe.datetime.str_to_user(String(v).split(' ')[0]) : '—');
		const esc = (v) => frappe.utils.escape_html(v || '—');
		// lists keyed on the Parent Manufacturing Order also show its main MWO next to it
		if (!link) {
			link = { label: __('Order No'), route: 'parent-manufacturing-order', field: 'order_no' };
			columns = [{ label: __('MWO'), value: (o) => this.mwo_link_html(o.mwo) }, ...columns];
		}

		const rows = orders
			.map(
				(o) => `
				<tr data-order="${frappe.utils.escape_html(o[link.field])}">
					<td class="mfg-orders__no">
						${
							o.stage_status
								? `<i class="mfg-dot" style="background:${this.STATUS_COLORS[o.stage_status] || 'var(--mfg-border)'}"
									title="${frappe.utils.escape_html(o.stage_status)}"></i>`
								: ''
						}<a href="/app/${link.route}/${encodeURIComponent(o[link.field])}"
							target="_blank" rel="noopener">${esc(o[link.field])}</a>
					</td>
					${columns.map((c) => `<td${c.num ? ' class="is-num"' : ''}>${c.value(o, esc, date)}</td>`).join('')}
				</tr>`
			)
			.join('');

		const headers = [{ label: link.label }, ...columns]
			.map((c) => `<th${c.num ? ' class="is-num"' : ''}>${c.label}</th>`)
			.join('');
		// whole list in one table; it scrolls inside the dialog with the header pinned
		$body.html(`
			<div class="mfg-orders__scroll">
				<table class="mfg-table mfg-orders">
					<thead>
						<tr>${headers}</tr>
						${this.search_row_html(columns.length + 1)}
					</thead>
					<tbody>${rows}</tbody>
					<tfoot>${this.order_totals_row(columns, orders)}</tfoot>
				</table>
			</div>
			<div class="mfg-pager">
				<span>${__('Total Records')}: <b data-field="shown">${this.fmt_count(data.order_count)}</b></span>
			</div>`);

		// rows left on screen after the column searches - what the Total row and the export cover
		let shown = orders;

		// Excel rows: same columns and text as the table; summed columns go out as plain numbers
		// (3 decimals) so they stay numeric in Excel
		const strip = (html) => {
			const text = $('<div>').html(html).text().trim();
			return text === '—' ? '' : text;
		};
		$body.data('export_rows', () => [
			[link.label, ...columns.map((c) => c.label)],
			...shown.map((o) => [
				o[link.field] || '',
				...columns.map((c) => (c.sum ? flt(o[c.sum], 3) : strip(c.value(o, esc, date)))),
			]),
			[
				__('Total'),
				...columns.map((c) => (c.sum ? flt(shown.reduce((acc, o) => acc + (Number(o[c.sum]) || 0), 0), 3) : '')),
			],
		]);

		this.bind_column_search($body, orders, (rows, searching) => {
			shown = rows;
			// the Total row always adds up just the rows left on screen
			$body.find('tfoot').html(this.order_totals_row(columns, shown));
			$body.find('[data-field="shown"]').text(
				searching
					? __('{0} of {1}', [this.fmt_count(shown.length), this.fmt_count(data.order_count)])
					: this.fmt_count(data.order_count)
			);
		});
	}

	// a search box under every column header of an order table
	search_row_html(count) {
		const cells = Array.from(
			{ length: count },
			(_, i) => `<th><input type="search" class="mfg-orders__search" data-col="${i}"
				placeholder="${__('Search')}" autocomplete="off"></th>`
		).join('');
		return `<tr class="mfg-orders__search-row">${cells}</tr>`;
	}

	// Filters the table's body rows as the search boxes are typed in: rows are matched on the text
	// shown in each cell (case-insensitive, all searches must match). `orders` is in row order;
	// on_filter gets the orders left on screen and whether any search is active.
	bind_column_search($scope, orders, on_filter) {
		const $rows = $scope.find('tbody tr');
		const cell_text = $rows.toArray().map((tr) => Array.from(tr.cells, (td) => td.textContent.trim().toLowerCase()));
		const $inputs = $scope.find('.mfg-orders__search');

		$inputs.on('input', frappe.utils.debounce(() => {
			const terms = $inputs.toArray().map((el) => [Number(el.dataset.col), el.value.trim().toLowerCase()]).filter(([, t]) => t);
			const shown = [];
			$rows.each((i, tr) => {
				const match = terms.every(([col, t]) => cell_text[i][col].includes(t));
				tr.style.display = match ? '' : 'none';
				if (match) shown.push(orders[i]);
			});
			on_filter(shown, terms.length > 0);
		}, 200));
	}
};
