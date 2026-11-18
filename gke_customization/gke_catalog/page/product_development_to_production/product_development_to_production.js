frappe.pages['product_development_to_production'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Product Development To Production',
		single_column: true,
	});
	new PdtpDashboard(page);
};

const PDTP_API = 'gke_customization.gke_catalog.page.product_development_to_production.product_development_to_production.';

const PDTP_DATE_STORAGE_KEY = 'pdtp_dashboard_date_filters';

function pdtp_load_stored_dates() {
	try {
		const raw = localStorage.getItem(PDTP_DATE_STORAGE_KEY);
		if (!raw) return null;
		const parsed = JSON.parse(raw);
		if (parsed && parsed.from_date && parsed.to_date) return parsed;
	} catch (e) {
		// ignore malformed/unavailable storage - fall back to the default range
	}
	return null;
}

function pdtp_save_stored_dates(from_date, to_date) {
	try {
		localStorage.setItem(PDTP_DATE_STORAGE_KEY, JSON.stringify({ from_date, to_date }));
	} catch (e) {
		// storage unavailable (e.g. private browsing) - silently skip persistence
	}
}

const PDTP_EXTRA_FILTER_FIELDS = {
	item_code: 'filter-item-code',
	sketch_order_no: 'filter-sketch-order-no',
	cad_order_no: 'filter-cad-order-no',
	stylebio: 'filter-stylebio',
	tag: 'filter-tag',
	setting_type: 'filter-setting-type',
};

const PDTP_STAGE_COLORS = {
	sketch_approved: 'var(--pdtp-blue)',
	cad_raised: 'var(--pdtp-purple)',
	has_stylebio: 'var(--pdtp-amber)',
	tagged: 'var(--pdtp-teal)',
	sold: 'var(--pdtp-green)',
};

const PDTP_SUMMARY_ICONS = {
	total_sketch_orders:
		'<path d="M5 3h8l4 4v12a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z"/><path d="M13 3v4h4"/><path d="M7.5 12h7M7.5 15.5h7M7.5 8.5h3"/>',
	total_designs:
		'<path d="m12 3 8 4.5-8 4.5-8-4.5L12 3Z"/><path d="m4 12 8 4.5 8-4.5"/><path d="m4 16.5 8 4.5 8-4.5"/>',
	total_cad_orders:
		'<path d="M12 3 4.5 7v10L12 21l7.5-4V7L12 3Z"/><path d="M4.5 7 12 11l7.5-4"/><path d="M12 11v10"/>',
	total_stylebio:
		'<path d="M10.5 3h-5A1.5 1.5 0 0 0 4 4.5v5c0 .4.16.78.44 1.06l9 9a1.5 1.5 0 0 0 2.12 0l5-5a1.5 1.5 0 0 0 0-2.12l-9-9A1.5 1.5 0 0 0 10.5 3Z"/><circle cx="8.25" cy="8.25" r="1.25"/>',
	total_tags:
		'<path d="M3 11.5 11.5 3H18a3 3 0 0 1 3 3v6.5L12.5 21 3 11.5Z"/><circle cx="15" cy="9" r="1.4"/>',
	total_pcs_sold:
		'<path d="M6 8V6a6 6 0 0 1 12 0v2"/><path d="M4.5 8h15l-1 12.5a1.5 1.5 0 0 1-1.5 1.4H7a1.5 1.5 0 0 1-1.5-1.4L4.5 8Z"/>',
};

function pdtp_icon(key) {
	const path = PDTP_SUMMARY_ICONS[key];
	if (!path) return '';
	return `<svg class="pdtp-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${path}</svg>`;
}

class PdtpDashboard {
	constructor(page) {
		this.page = page;
		// Remember the last date range used on this browser so the page
		// doesn't quietly snap back to "last 1 month" on every visit -
		// only a brand new session (nothing stored yet) gets that default.
		const stored_dates = pdtp_load_stored_dates();
		this.filters = stored_dates || {
			from_date: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			to_date: frappe.datetime.get_today(),
		};
		this.req = 0; // request token - lets a stale in-flight response be discarded

		this.$ = (sel) => this.page.main.find(sel);
		this.render_shell();
		this.setup_controls();
		this.load_setting_type_options();
		this.load();
	}

	call(method, args = {}) {
		return frappe
			.call({ method: PDTP_API + method, args })
			.then((r) => r.message);
	}

	render_shell() {
		this.page.main.html(frappe.render_template('product_development_to_production', {}));

		this.$from_date = this.$('[data-field="from-date"]');
		this.$to_date = this.$('[data-field="to-date"]');
		this.$load = this.$('[data-field="load-btn"]');
		this.$refresh = this.$('[data-field="refresh-btn"]');
		this.$generated_at = this.$('[data-field="generated-at"]');
		this.$stage = this.$('[data-field="stage"]');
		this.$overlay_text = this.$('[data-field="overlay-text"]');
		this.$summary = this.$('[data-field="summary-row"]');
		this.$funnel = this.$('[data-field="funnel-row"]');
		this.$blockers = this.$('[data-field="blockers-row"]');
		this.$ratio = this.$('[data-field="ratio-row"]');
		this.$leadtime = this.$('[data-field="leadtime-row"]');
		this.$monthly = this.$('[data-field="monthly-row"]');
		this.$category = this.$('[data-field="category-table"]');
		this.$customer = this.$('[data-field="customer-list"]');
		this.$clear_filters = this.$('[data-field="clear-filters-btn"]');

		this.$extra_filters = {};
		Object.keys(PDTP_EXTRA_FILTER_FIELDS).forEach((key) => {
			this.$extra_filters[key] = this.$(`[data-field="${PDTP_EXTRA_FILTER_FIELDS[key]}"]`);
		});

		this.$from_date.val(this.filters.from_date);
		this.$to_date.val(this.filters.to_date);
	}

	setup_controls() {
		// Date/text filter changes only stage the value - nothing reloads
		// until "Load" is clicked (or Ctrl/Cmd+Enter in a filter box), so
		// picking just the From date (before To is set) never fires a
		// request with a half-picked, mismatched filter combination. Plain
		// Enter is left alone in the bulk filter boxes so it inserts a
		// newline instead of submitting - that's how multiple pasted/typed
		// values get separated.
		this.$load.on('click', () => this.load());
		this.$refresh.on('click', () => this.load());

		Object.keys(this.$extra_filters).forEach((key) => {
			if (key === 'setting_type') return;
			this.$extra_filters[key].on('keydown', (e) => {
				if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) this.load();
			});
		});

		// A dropdown pick is already a complete, deliberate choice (unlike a
		// half-typed text filter), so it can reload immediately on change.
		this.$extra_filters.setting_type.on('change', () => this.load());

		this.$clear_filters.on('click', () => {
			Object.values(this.$extra_filters).forEach(($el) => $el.val(''));
			this.load();
		});

		const click = (e) => this.open_segment({ stage: $(e.currentTarget).attr('data-stage') });
		this.$summary.on('click', '[data-stage]', click);
		this.$funnel.on('click', '[data-stage]', click);
		this.$blockers.on('click', '[data-stage]', click);
		this.$ratio.on('click', '[data-stage]', click);

		this.$category.on('click', '[data-stage][data-category]', (e) =>
			this.open_segment({
				stage: $(e.currentTarget).attr('data-stage'),
				category: $(e.currentTarget).attr('data-category'),
			})
		);
		this.$customer.on('click', '[data-customer]', (e) =>
			this.open_segment({ stage: 'sketch_approved', customer: $(e.currentTarget).attr('data-customer') })
		);
	}

	load_setting_type_options() {
		this.call('get_setting_type_options').then((options) => {
			if (!options || !options.length) return;
			const $select = this.$extra_filters.setting_type;
			const current = $select.val();
			options.forEach((value) => {
				$select.append(
					`<option value="${frappe.utils.escape_html(value)}">${frappe.utils.escape_html(value)}</option>`
				);
			});
			if (current) $select.val(current);
		});
	}

	load() {
		const req = ++this.req;

		// Always read every filter fresh at the moment Load/Refresh is
		// clicked - never trust a change-event snapshot that could be
		// half-updated (e.g. From changed but To not touched yet).
		this.filters = {
			from_date: this.$from_date.val(),
			to_date: this.$to_date.val(),
		};
		Object.keys(this.$extra_filters).forEach((key) => {
			const value = this.$extra_filters[key].val().trim();
			if (value) this.filters[key] = value;
		});

		if (!this.filters.from_date || !this.filters.to_date) {
			frappe.msgprint(__('Please pick both a From Date and a To Date.'));
			return;
		}

		pdtp_save_stored_dates(this.filters.from_date, this.filters.to_date);

		// Gate the whole dashboard behind one overlay until the single
		// combined payload call resolves - no section renders ahead of
		// the others, and a filter change never blends with stale content.
		this.$stage.addClass('is-loading').removeClass('is-error');
		this.$overlay_text.text(__('Loading dashboard…'));
		this.$from_date.prop('disabled', true);
		this.$to_date.prop('disabled', true);
		this.$load.prop('disabled', true);
		this.$refresh.prop('disabled', true);
		Object.values(this.$extra_filters).forEach(($el) => $el.prop('disabled', true));

		this.call('get_dashboard_payload', { filters: this.filters })
			.then((data) => {
				if (req !== this.req) return; // a newer filter change superseded this request
				if (!data) {
					this.show_load_error();
					return;
				}

				this.$generated_at.text(`Generated ${frappe.datetime.str_to_user(data.generated_at)}`);
				this.render_summary(data.summary_kpis);
				this.render_funnel(data.funnel);
				this.render_blockers(data.blockers);
				this.render_ratio(data.stylebio_tag_ratio);
				this.render_leadtime(data.lead_times);
				this.render_monthly(data.monthly_completed);
				this.render_category(data.category_breakdown);
				this.render_customer(data.customer_breakdown);

				this.$stage.removeClass('is-loading');
			})
			.catch(() => {
				if (req !== this.req) return;
				this.show_load_error();
			})
			.always(() => {
				if (req !== this.req) return;
				this.$from_date.prop('disabled', false);
				this.$to_date.prop('disabled', false);
				this.$load.prop('disabled', false);
				this.$refresh.prop('disabled', false);
				Object.values(this.$extra_filters).forEach(($el) => $el.prop('disabled', false));
			});
	}

	show_load_error() {
		this.$stage.removeClass('is-loading').addClass('is-error');
		this.$overlay_text.text(__('Could not load the dashboard. Please try Refresh.'));
	}

	// ---------- summary ----------

	render_summary(summary) {
		if (!summary || !summary.length) {
			this.$summary.html('<div class="pdtp__empty">No data.</div>');
			return;
		}

		const html = summary
			.map(
				(s) => `
					<div class="pdtp-summary__cell" data-stage="${s.stage}">
						<div class="pdtp-summary__icon">${pdtp_icon(s.key)}</div>
						<div class="pdtp-summary__text">
							<div class="pdtp-summary__value">${this.fmt_count(s.count)}</div>
							<div class="pdtp-summary__label">${frappe.utils.escape_html(s.label)}</div>
						</div>
					</div>`
			)
			.join('');

		this.$summary.html(html);
	}

	// ---------- funnel ----------

	render_funnel(funnel) {
		if (!funnel || !funnel.length) {
			this.$funnel.html('<div class="pdtp__empty">No data.</div>');
			return;
		}

		const max = Math.max(...funnel.map((f) => f.count), 1);
		const base = funnel[0].count || 1;
		const last = funnel.length - 1;

		const html = funnel
			.map((f, i) => {
				const pct = Math.max(Math.round((f.count / max) * 100), 16);
				const conv = base ? Math.round((f.count / base) * 100) : 0;
				const color = PDTP_STAGE_COLORS[f.stage] || 'var(--pdtp-blue)';
				const connector =
					i < last
						? `<div class="pdtp-funnel__connector"><span class="pdtp-funnel__chevron"></span></div>`
						: '';
				return `
					<div class="pdtp-funnel__stage" data-stage="${f.stage}">
						<div class="pdtp-funnel__shape" style="width:${pct}%; --shape-color:${color}">
							<span class="pdtp-funnel__shape-value">${this.fmt_count(f.count)}</span>
							<span class="pdtp-funnel__shape-label">${frappe.utils.escape_html(f.label)}</span>
						</div>
						<span class="pdtp-funnel__conv">${conv}% of total</span>
					</div>
					${connector}`;
			})
			.join('');

		this.$funnel.html(html);
	}

	// ---------- blockers ----------

	render_blockers(blockers) {
		if (!blockers || !blockers.length) {
			this.$blockers.html('<div class="pdtp__empty">No blockers.</div>');
			return;
		}

		const html = blockers
			.map(
				(b) => `
					<div class="pdtp-blockers__card" data-stage="${b.stage}">
						<div class="pdtp-blockers__count">${this.fmt_count(b.count)}</div>
						<div class="pdtp-blockers__label">${frappe.utils.escape_html(b.label)}</div>
					</div>`
			)
			.join('');

		this.$blockers.html(html);
	}

	// ---------- stylebio / tag ratio ----------

	render_ratio(ratio) {
		if (!ratio) {
			this.$ratio.html('<div class="pdtp__empty">No data.</div>');
			return;
		}

		const tiles = [
			{
				stage: 'has_stylebio',
				pct: ratio.stylebio_coverage_pct,
				color: 'var(--pdtp-amber)',
				label: `StyleBio Found (${ratio.with_stylebio}/${ratio.total_designs})`,
			},
			{
				stage: 'tagged',
				pct: ratio.tag_ratio_pct,
				color: 'var(--pdtp-teal)',
				label: `All Designs to Tag Ratio (${ratio.tagged}/${ratio.total_designs})`,
			},
			{
				stage: 'tagged',
				pct: ratio.tag_vs_stylebio_pct,
				color: 'var(--pdtp-green)',
				label: `StyleBio to Tag Ratio (${ratio.tagged}/${ratio.with_stylebio})`,
			},
		];

		const html = tiles
			.map(
				(t) => `
					<div class="pdtp-ratio__card" data-stage="${t.stage}">
						<div class="pdtp-ratio__ring" style="--pct:${t.pct}; --ring-color:${t.color}">
							<div class="pdtp-ratio__ring-hole">
								<span class="pdtp-ratio__ring-value">${t.pct}%</span>
							</div>
						</div>
						<div class="pdtp-ratio__label">${t.label}</div>
					</div>`
			)
			.join('');

		this.$ratio.html(html);
	}

	// ---------- lead time ----------

	render_leadtime(lead_times) {
		if (!lead_times) {
			this.$leadtime.html('<div class="pdtp__empty">No data.</div>');
			return;
		}

		const fmt = (val) => (val !== null && val !== undefined ? `${val}d` : '--');
		const nodes = ['Sketch Order', 'CAD Order', 'First Tag'];
		const edges = [fmt(lead_times.sketch_to_cad), fmt(lead_times.cad_to_tag)];

		const html = `
			<div class="pdtp-leadtime__timeline">
				${nodes
					.map(
						(label, i) => `
							<div class="pdtp-leadtime__node">
								<span class="pdtp-leadtime__dot"></span>
								<span class="pdtp-leadtime__node-label">${label}</span>
							</div>
							${
								i < edges.length
									? `<div class="pdtp-leadtime__edge"><span>${edges[i]}</span></div>`
									: ''
							}`
					)
					.join('')}
			</div>
			<div class="pdtp-leadtime__total">
				<span class="pdtp-leadtime__total-label">Sketch &rarr; First Tag (overall)</span>
				<span class="pdtp-leadtime__total-value">${fmt(lead_times.sketch_to_tag)}</span>
			</div>
		`;

		this.$leadtime.html(html);
	}

	// ---------- monthly pieces completed ----------

	render_monthly(rows) {
		if (!rows || !rows.length) {
			this.$monthly.html('<div class="pdtp__empty">No completions in range.</div>');
			return;
		}

		const max = Math.max(...rows.map((r) => r.completed_count), 1);

		const bars = rows
			.map((r) => {
				const pct = Math.max(Math.round((r.completed_count / max) * 100), 3);
				return `
					<div class="pdtp-monthly__col" title="${__('{0} designs completed in {1}', [r.completed_count, r.month_label])}">
						<div class="pdtp-monthly__bar-wrap">
							<div class="pdtp-monthly__bar" style="height:${pct}%"></div>
						</div>
						<div class="pdtp-monthly__value">${r.completed_count}</div>
						<div class="pdtp-monthly__month">${r.month_label}</div>
					</div>`;
			})
			.join('');

		this.$monthly.html(`<div class="pdtp-monthly__chart">${bars}</div>`);
	}

	// ---------- category breakdown ----------

	render_category(rows) {
		if (!rows || !rows.length) {
			this.$category.html('<div class="pdtp__empty">No category data.</div>');
			return;
		}

		const seg = (stage, category) =>
			`data-stage="${stage}" data-category="${frappe.utils.escape_html(category)}"`;

		const body = rows
			.map(
				(r) => `
					<tr>
						<td>${frappe.utils.escape_html(r.category)}</td>
						<td ${seg('sketch_approved', r.category)}>${this.fmt_count(r.total)}</td>
						<td ${seg('has_stylebio', r.category)}>${this.fmt_count(r.stylebio)}</td>
						<td ${seg('tagged', r.category)}>${this.fmt_count(r.tagged)}</td>
						<td>${this.fmt_count(r.sold_qty)}</td>
					</tr>`
			)
			.join('');

		const totals = rows.reduce(
			(acc, r) => {
				acc.total += r.total || 0;
				acc.stylebio += r.stylebio || 0;
				acc.tagged += r.tagged || 0;
				acc.sold_qty += r.sold_qty || 0;
				return acc;
			},
			{ total: 0, stylebio: 0, tagged: 0, sold_qty: 0 }
		);

		this.$category.html(`
			<table>
				<thead>
					<tr>
						<th>Category</th>
						<th>Total</th>
						<th>StyleBio</th>
						<th>Tagged</th>
						<th>Sold Qty</th>
					</tr>
				</thead>
				<tbody>${body}</tbody>
				<tfoot>
					<tr>
						<td>Total</td>
						<td>${this.fmt_count(totals.total)}</td>
						<td>${this.fmt_count(totals.stylebio)}</td>
						<td>${this.fmt_count(totals.tagged)}</td>
						<td>${this.fmt_count(totals.sold_qty)}</td>
					</tr>
				</tfoot>
			</table>
		`);
	}

	// ---------- customer workload ----------

	render_customer(rows) {
		if (!rows || !rows.length) {
			this.$customer.html('<div class="pdtp__empty">No customer data.</div>');
			return;
		}

		const max = Math.max(...rows.map((r) => r.total), 1);

		const html = rows
			.map((r) => {
				const pct = Math.max(Math.round((r.total / max) * 100), 2);
				return `
					<div class="pdtp-customer__row" data-customer="${frappe.utils.escape_html(r.customer)}">
						<div class="pdtp-customer__name">${frappe.utils.escape_html(r.customer)}</div>
						<div class="pdtp-customer__bar"><span style="width:${pct}%"></span></div>
						<div class="pdtp-customer__stats">
							<span>${r.total} total</span>
							<span class="pdtp-customer__tagged">${r.tagged} tagged</span>
							<span class="pdtp-customer__sold">${r.sold_qty} sold</span>
						</div>
					</div>`;
			})
			.join('');

		const totals = rows.reduce(
			(acc, r) => {
				acc.total += r.total || 0;
				acc.tagged += r.tagged || 0;
				acc.sold_qty += r.sold_qty || 0;
				return acc;
			},
			{ total: 0, tagged: 0, sold_qty: 0 }
		);

		this.$customer.html(`
			<div class="pdtp-customer__list">${html}</div>
			<div class="pdtp-customer__row pdtp-customer__row--total">
				<div class="pdtp-customer__name">Total</div>
				<div class="pdtp-customer__bar"></div>
				<div class="pdtp-customer__stats">
					<span>${totals.total} total</span>
					<span class="pdtp-customer__tagged">${totals.tagged} tagged</span>
					<span class="pdtp-customer__sold">${totals.sold_qty} sold</span>
				</div>
			</div>
		`);
	}

	// ---------- segment drill-down ----------

	open_segment({ stage, category, customer }) {
		const dialog = new frappe.ui.Dialog({
			title: __('Orders'),
			size: 'extra-large',
		});
		dialog.show();
		dialog.$body.html(`<div class="pdtp__loading">${__('Loading…')}</div>`);

		this.call('get_segment_rows', { filters: this.filters, stage, category, customer }).then((rows) => {
			if (!rows || !rows.length) {
				dialog.$body.html(`<div class="pdtp__empty">${__('No matching orders.')}</div>`);
				return;
			}

			const thumb = (r) =>
				r.image
					? `<div class="pdtp-category__thumb" data-image="${frappe.utils.escape_html(r.image)}" data-category="${frappe.utils.escape_html(r.item_code || '')}"><img src="${r.image}" loading="lazy" /></div>`
					: `<div class="pdtp-category__thumb pdtp-category__thumb--empty"></div>`;

			const body = rows
				.map(
					(r) => `
						<tr>
							<td>${thumb(r)}</td>
							<td>${frappe.utils.escape_html(r.sketch_order_no || '')}</td>
							<td>${frappe.utils.escape_html(r.cad_order_no || '')}</td>
							<td>${frappe.utils.escape_html(r.cad_workflow_state || '')}</td>
							<td>${frappe.utils.escape_html(r.item_code || '')}</td>
							<td title="${frappe.utils.escape_html(r.stylebio || '')}">${frappe.utils.escape_html(this.truncate(r.stylebio, 14))}</td>
							<td>${frappe.utils.escape_html(r.customer || '')}</td>
							<td>${frappe.utils.escape_html(r.category_name || '')}</td>
							<td>${frappe.datetime.str_to_user(r.sketch_order_date) || ''}</td>
							<td>${frappe.datetime.str_to_user(r.cad_order_date) || ''}</td>
							<td>${frappe.datetime.str_to_user(r.entry_date) || ''}</td>
							<td>${frappe.datetime.str_to_user(r.first_tag_date) || ''}</td>
							<td title="${frappe.utils.escape_html(r.tag_nos || '')}">${frappe.utils.escape_html(this.truncate(r.tag_nos, 20))}</td>
							<td>${r.total_sold || 0}</td>
						</tr>`
				)
				.join('');

			dialog.add_custom_action(__('Export'), () => this.export_segment_rows(rows), 'btn-default');

			dialog.$body.html(`
				<div class="pdtp-dialog-table">
					<table>
						<thead>
							<tr>
								<th></th>
								<th>Sketch Order</th>
								<th>CAD Order</th>
								<th>CAD Status</th>
								<th>Item</th>
								<th>StyleBio</th>
								<th>Customer</th>
								<th>Category</th>
								<th>Sketch Date</th>
								<th>CAD Date</th>
								<th>Catalog Date</th>
								<th>First Tag</th>
								<th>Tag No</th>
								<th>Sold</th>
							</tr>
						</thead>
						<tbody>${body}</tbody>
					</table>
				</div>
			`);

			dialog.$body.on('click', '.pdtp-category__thumb[data-image]', (e) => {
				this.open_image_preview(
					$(e.currentTarget).attr('data-image'),
					$(e.currentTarget).attr('data-category')
				);
			});
		});
	}

	fmt_count(n) {
		return frappe.format(n || 0, { fieldtype: 'Int' });
	}

	open_image_preview(src, title) {
		const dialog = new frappe.ui.Dialog({ title: title || __('Preview') });
		dialog.$body.html(`<img src="${src}" style="max-width:100%; display:block; margin:0 auto;" />`);
		dialog.show();
	}

	truncate(text, max_len) {
		text = text || '';
		return text.length > max_len ? `${text.slice(0, max_len)}…` : text;
	}

	export_segment_rows(rows) {
		const headers = [
			'Sketch Order',
			'CAD Order',
			'CAD Status',
			'Item',
			'StyleBio',
			'Customer',
			'Category',
			'Sketch Date',
			'CAD Date',
			'Catalog Date',
			'First Tag',
			'Tag No',
			'Sold',
		];

		const data = [headers].concat(
			rows.map((r) => [
				r.sketch_order_no || '',
				r.cad_order_no || '',
				r.cad_workflow_state || '',
				r.item_code || '',
				r.stylebio || '',
				r.customer || '',
				r.category_name || '',
				frappe.datetime.str_to_user(r.sketch_order_date) || '',
				frappe.datetime.str_to_user(r.cad_order_date) || '',
				frappe.datetime.str_to_user(r.entry_date) || '',
				frappe.datetime.str_to_user(r.first_tag_date) || '',
				r.tag_nos || '',
				r.total_sold || 0,
			])
		);

		frappe.tools.downloadify(data, null, 'Product Development To Production');
	}
}
