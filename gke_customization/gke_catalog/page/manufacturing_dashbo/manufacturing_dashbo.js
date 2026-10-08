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

		const api = 'gke_customization.gke_catalog.report.mfg_dashboard_script.mfg_dashboard_script.';
		this.stage_method = api + 'get_stage_details';
		this.detail_method = api + 'get_order_details';
		this.STATUS_COLORS = {
			'In Progress': 'var(--mfg-steel)',
			Completed: 'var(--mfg-emerald)',
			Pending: 'var(--mfg-amber)',
			'On Hold': 'var(--mfg-red)',
		};
		// Drill-down state (sections 4-6): the operation tag picked in section 3, the status row
		// picked in the stage summary (null = all), the order-list page and the order opened.
		this.selection = null;
		this.drill = { status: null, page: 1, order: null };
		this.page_size = 10;

		this.render_shell();
		this.setup_page_controls();
		if (!this.company_field.get_value()) {
			this.refresh();
		}
	}

	// The filter controls are rendered inside our own template (not via page.add_field's
	// toolbar row) so they are always visible regardless of desk theme/version - some Frappe
	// versions tuck page-toolbar fields behind a collapsed filter affordance that's easy to miss.
	setup_page_controls() {
		const page = this.page;

		page.set_secondary_action(__('Refresh'), () => this.refresh(), 'refresh');

		this.page.main.find('[data-field="clear-filters"]').on('click', () => this.clear_filters());

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
	}

	get_date_range() {
		const value = this.daterange_field.get_value();
		if (!value || !value[0] || !value[1]) return [null, null];
		return [value[0], value[1]];
	}

	clear_filters() {
		this.company_field.set_value('');
		this.customer_field.set_value('');
		this.daterange_field.set_value('');
		this.refresh();
	}

	render_shell() {
		this.page.main.html(frappe.render_template('manufacturing_dashbo', {}));
		this.$kpi_row = this.page.main.find('[data-field="kpi-row"]');
		this.$dept_line = this.page.main.find('[data-field="dept-line"]');
		this.$andon = this.page.main.find('[data-field="andon-board"]');
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
		return {
			company: this.company_field.get_value(),
			due_soon_days: this.due_soon_days,
			customer: this.customer_field.get_value() || undefined,
			from_date: from_date || undefined,
			to_date: to_date || undefined,
		};
	}

	refresh() {
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

	render_loading() {
		const cyclone = `
			<div class="mfg-cyclone">
				<span class="mfg-cyclone__ring"></span>
				<span class="mfg-cyclone__ring"></span>
				<span class="mfg-cyclone__ring"></span>
				<span class="mfg-cyclone__core"></span>
			</div>`;
		const loading = (text) => `
			<div class="mfgdash__loading">
				${cyclone}
				<div class="mfgdash__loading-text">${frappe.utils.escape_html(text)}</div>
			</div>`;
		this.$kpi_row.html(loading(__('Loading order summary…')));
		this.$dept_line.html(loading(__('Loading department flow…')));
		this.$andon.html(loading(__('Loading alerts…')));
		this.$ops.html(loading(__('Loading operations…')));
	}

	render_prompt(text) {
		const html = `<div class="mfgdash__empty" style="grid-column:1/-1">${frappe.utils.escape_html(text)}</div>`;
		this.$kpi_row.html(html);
		this.$dept_line.html('');
		this.$andon.html('');
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
				return `
					<div class="mfg-kpi" style="--mfg-accent:${accent};--mfg-delay:${i * 60}ms" data-key="${row.key}">
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
					</div>`;
			})
			.join('');

		this.$kpi_row.html(html);

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

		const html = shown
			.map((dept, i) => {
				const total = dept.count || 0;
				const pendingPct = total ? (dept.pending / total) * 100 : 0;
				const progressPct = total ? (dept.in_progress / total) * 100 : 0;
				const p1 = pendingPct;
				const p2 = pendingPct + progressPct;
				const ring = total
					? `conic-gradient(var(--mfg-amber) 0 ${p1}%, var(--mfg-steel) ${p1}% ${p2}%, var(--mfg-emerald) ${p2}% 100%)`
					: 'var(--mfg-track)';

				return `
					<div class="mfg-node" data-field="node" data-index="${i}" style="--mfg-delay:${i * 70}ms">
						<div class="mfg-node__ring" style="background:${ring}">
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
							dept.not_weighed
								? `<div class="mfg-node__stats mfg-node__stats--warn">
									<span title="Pieces past casting whose current operation has no recorded weight - not included in the weights above">⚠ Not weighed <b>${this.fmt_count(dept.not_weighed)}</b></span>
								</div>`
								: ''
						}
						${
							dept.not_started
								? `<div class="mfg-node__stats mfg-node__stats--caution">
									<span title="In Progress pieces received/issued to this department but work not started yet">⏸ Not started <b>${this.fmt_count(dept.not_started)}</b></span>
								</div>`
								: ''
						}
						<div class="mfg-node__legend">
							<span><i style="background:var(--mfg-amber)"></i>${this.fmt_count(dept.pending)}</span>
							<span><i style="background:var(--mfg-steel)"></i>${this.fmt_count(dept.in_progress)}</span>
							<span><i style="background:var(--mfg-emerald)"></i>${this.fmt_count(dept.completed)}</span>
						</div>
						${
							dept.department_id
								? `<button type="button" class="mfg-node__detail" data-field="view-detail" data-department="${frappe.utils.escape_html(dept.department_id)}">View Detail →</button>`
								: ''
						}
					</div>`;
			})
			.join('');

		this.$dept_line.html(html);
		this.bind_node_tooltips(shown);
		this.bind_view_detail_buttons();
	}

	// Jumps to the standard Manufacturing Work Order report view, pre-filtered to the exact
	// same pieces this department's card is summarizing - so "View Detail" is a drill-down,
	// not a separate ad-hoc filter the user has to rebuild themselves.
	bind_view_detail_buttons() {
		this.$dept_line.find('[data-field="view-detail"]').on('click', (e) => {
			e.stopPropagation();
			const department = e.currentTarget.dataset.department;
			const company = this.company_field.get_value();

			frappe.route_options = {
				company: company,
				department: department,
				for_fg: 0,
				is_finding_mwo: 0,
			};
			frappe.set_route('List', 'Manufacturing Work Order', 'Report');
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
				const lines = dept.operations.map((op) => line(dept, op.operation, op.label, op));
				if (dept.awaiting_operation.count) {
					lines.push(
						line(dept, '__awaiting__', __('Awaiting Operation'), dept.awaiting_operation, 'mfg-opline--awaiting')
					);
				}
				return `
					<div class="mfg-opdept" style="--mfg-delay:${i * 60}ms">
						<div class="mfg-opdept__title">${frappe.utils.escape_html(dept.name)}</div>
						<div class="mfg-opdept__lines">${lines.join('')}</div>
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
			this.drill = { status: null, page: 1, order: null };
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
			this.drill = { status: null, page: 1, order: null };
			this.render_drill_hints();
			return;
		}
		this.drill.page = 1;
		this.load_stage();
		if (this.drill.order) this.load_order(this.drill.order);
	}

	load_stage() {
		const sel = this.selection;
		if (!sel) return;
		const args = this.build_call_args();
		const token = (this.stage_token = (this.stage_token || 0) + 1);

		const crumb = `— ${sel.department_name} · ${sel.label}`;
		this.$stage_title.text(crumb);
		this.$orders_title.text(`— ${sel.label} · ${this.drill.status || __('All')}`);
		this.$orders.addClass('is-busy');

		frappe.call({
			method: this.stage_method,
			args: {
				company: args.company,
				department: sel.department,
				operation: sel.operation,
				status: this.drill.status || undefined,
				page: this.drill.page,
				page_size: this.page_size,
				customer: args.customer,
				from_date: args.from_date,
				to_date: args.to_date,
			},
			freeze: false,
			callback: (r) => {
				if (token !== this.stage_token || !r.message) return;
				this.$orders.removeClass('is-busy');
				this.render_stage(r.message);
				this.render_orders(r.message);
			},
			error: () => {
				this.$orders.removeClass('is-busy');
				this.$stage.html(`<div class="mfgdash__empty mfgdash__empty--compact">${__('Could not load stages.')}</div>`);
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

		const rows = data.stages.map((s) => row(s.status, __(s.status), s, this.STATUS_COLORS[s.status]));

		this.$stage.html(`
			<table class="mfg-table mfg-stage">
				<thead><tr><th>${__('Status')}</th><th>${__('Pcs')}</th><th>${__('Metal (g)')}</th><th>${__('Dia (ct)')}</th></tr></thead>
				<tbody>${rows.join('')}</tbody>
				<tfoot>${row(null, __('Total'), data.total, 'var(--mfg-brass)')}</tfoot>
			</table>`);

		this.$stage.find('[data-field="stage-row"]').on('click', (e) => {
			const status = e.currentTarget.dataset.status || null;
			this.drill.status = status;
			this.drill.page = 1;
			this.load_stage();
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
					<td class="mfg-orders__no">
						<i class="mfg-dot" style="background:${this.STATUS_COLORS[o.stage_status] || 'var(--mfg-border)'}"
							title="${frappe.utils.escape_html(o.stage_status)}"></i>${esc(o.order_no)}
					</td>
					<td>${esc(o.design_no)}</td>
					<td>${esc(o.item_category)}</td>
					<td class="is-num">${this.fmt_wt(o.gold_wt, '').trim()}</td>
					<td class="is-num">${this.fmt_wt(o.diamond_wt, '').trim()}</td>
					<td>${date(o.issue_date)}</td>
					<td>${date(o.due_date)}</td>
					<td>${esc(o.employee_name || o.employee)}</td>
				</tr>`
			)
			.join('');

		const pages = Math.max(1, Math.ceil((data.order_count || 0) / data.page_size));
		this.$orders.html(`
			<div class="mfg-orders__scroll">
				<table class="mfg-table mfg-orders">
					<thead><tr>
						<th>${__('Order No')}</th><th>${__('Design No')}</th><th>${__('Item')}</th>
						<th class="is-num">${__('Metal (g)')}</th><th class="is-num">${__('Dia (ct)')}</th>
						<th>${__('Issue Date')}</th><th>${__('Due Date')}</th><th>${__('Employee')}</th>
					</tr></thead>
					<tbody>${rows}</tbody>
				</table>
			</div>
			<div class="mfg-pager">
				<span>${__('Total Records')}: <b>${this.fmt_count(data.order_count)}</b></span>
				<span class="mfg-pager__nav">
					<button type="button" data-field="page-prev" ${data.page <= 1 ? 'disabled' : ''}>‹</button>
					<span>${__('Page {0} of {1}', [data.page, pages])}</span>
					<button type="button" data-field="page-next" ${data.page >= pages ? 'disabled' : ''}>›</button>
				</span>
			</div>`);

		this.$orders.find('[data-field="page-prev"]').on('click', () => {
			this.drill.page = Math.max(1, data.page - 1);
			this.load_stage();
		});
		this.$orders.find('[data-field="page-next"]').on('click', () => {
			this.drill.page = Math.min(pages, data.page + 1);
			this.load_stage();
		});
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
		this.$detail.html(`<div class="mfgdash__empty mfgdash__empty--compact">${__('Loading order…')}</div>`);

		frappe.call({
			method: this.detail_method,
			args: { company: this.company_field.get_value(), order_no },
			freeze: false,
			callback: (r) => {
				if (token !== this.detail_token || !r.message) return;
				this.render_order_detail(r.message);
			},
			error: () => {
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
					${field(__('Issue Date'), date(d.issue_date))}
					${field(__('Work Order'), esc(d.work_order))}
				</dl>
				<div class="mfg-detail__materials">
					<div class="mfg-detail__heading">${__('Materials & Weight')}</div>
					<dl class="mfg-detail__list">
						${field(__('Metal Touch'), esc(d.metal_touch))}
						${field(__('Metal Colour'), esc(d.metal_colour))}
						${field(__('Metal Wt'), this.fmt_wt(d.metal_wt, 'g'))}
						${field(__('Gross Wt'), actual(d.gross_wt, 'g'))}
						${field(__('Diamond Wt'), this.fmt_wt(d.diamond_wt, 'ct'))}
						${field(__('Diamond Pcs'), this.fmt_count(Math.round(d.diamond_pcs || 0)))}
						${field(__('Gemstone Wt'), this.fmt_wt(d.gemstone_wt, 'ct'))}
					</dl>
				</div>
			</div>`);
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
			<div class="mfg-tooltip__row pending"><span>Pending</span><b>${this.fmt_count(dept.pending)} (${pct(dept.pending)}%)</b></div>
			<div class="mfg-tooltip__row progress"><span>In Progress</span><b>${this.fmt_count(dept.in_progress)} (${pct(dept.in_progress)}%)</b></div>
			<div class="mfg-tooltip__row"><span>&nbsp;&nbsp;of which not started</span><b>${this.fmt_count(dept.not_started)}</b></div>
			<div class="mfg-tooltip__row completed"><span>Completed</span><b>${this.fmt_count(dept.completed)} (${pct(dept.completed)}%)</b></div>
			<div class="mfg-tooltip__divider"></div>
			<div class="mfg-tooltip__row"><span>Metal wt</span><b>${this.fmt_wt(dept.gold_wt, 'g')}</b></div>
			<div class="mfg-tooltip__row"><span>Diamond wt</span><b>${this.fmt_wt(dept.diamond_wt, 'ct')}</b></div>
			<div class="mfg-tooltip__row"><span>Diamond pcs</span><b>${this.fmt_count(Math.round(dept.diamond_pcs || 0))}</b></div>
			<div class="mfg-tooltip__row"><span>Not weighed</span><b>${this.fmt_count(dept.not_weighed)}</b></div>`;
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

		const lamp = (label_html, data, color) => {
			const active = data.count > 0;
			return `
				<div class="mfg-lamp ${active ? 'mfg-lamp--active' : ''}" style="--mfg-lamp-color:${color}">
					<div class="mfg-lamp__bulb"></div>
					<div>
						<div class="mfg-lamp__label">${label_html}</div>
						<div class="mfg-lamp__count">${this.fmt_count(data.count)}<span>orders</span></div>
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

		const html = lamp(due_soon_label, due_soon, 'var(--mfg-amber)') + lamp('Overdue', overdue, 'var(--mfg-red)');

		this.$andon.html(html);

		this.$andon.find('[data-field="due-soon-days"]').on('change', (e) => {
			let value = parseInt(e.target.value, 10);
			if (isNaN(value) || value < 0) value = 0;
			e.target.value = value;
			this.due_soon_days = value;
			this.refresh_alerts();
		});
	}
};
