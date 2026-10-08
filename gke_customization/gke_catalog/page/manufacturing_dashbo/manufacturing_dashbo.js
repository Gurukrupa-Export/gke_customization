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
	}

	render_prompt(text) {
		const html = `<div class="mfgdash__empty" style="grid-column:1/-1">${frappe.utils.escape_html(text)}</div>`;
		this.$kpi_row.html(html);
		this.$dept_line.html('');
		this.$andon.html('');
	}

	render() {
		this.render_kpis(this.data.order_summary);
		this.render_departments(this.data.departments);
		this.render_andon(this.data.alerts);
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
			<div class="mfg-tooltip__row completed"><span>Completed</span><b>${this.fmt_count(dept.completed)} (${pct(dept.completed)}%)</b></div>
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
