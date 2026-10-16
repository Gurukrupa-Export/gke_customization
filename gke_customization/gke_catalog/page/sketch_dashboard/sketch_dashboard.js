// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt
//
// Sketch Dashboard (page) - Version 1.1

frappe.pages["sketch-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Sketch Dashboard"),
		single_column: true,
	});
	wrapper.sketch_dashboard = new SketchDashboard(page);
};

const SD_METHOD = "gke_customization.gke_catalog.page.sketch_dashboard.sketch_dashboard.";

// Stage group decides the colour of each pipeline step
const SD_STAGE_GROUP = {
	draft: "waiting",
	on_hold: "waiting",
	assigned: "designer",
	rough_hod: "designer",
	final_hod: "designer",
	customer_approval: "after",
	item_update: "after",
	approved: "done",
	cancelled: "stopped",
	old_workflow: "stopped",
	other: "stopped",
};

// Plain-language meaning of each stage (shown on hover)
const SD_STAGE_HELP = {
	draft: __("Order created, not yet assigned to a designer."),
	assigned: __("Designer is making the rough sketch."),
	rough_hod: __("Rough sketch is waiting for HOD approval."),
	final_hod: __("Final sketch is waiting for HOD approval."),
	customer_approval: __("Final sketch is waiting for the customer's approval."),
	item_update: __("Sketch is approved; QC / BOM team is creating the design item."),
	approved: __("Sketch work is complete."),
	on_hold: __("Order is paused at one of the stages."),
	cancelled: __("Order is cancelled, including orders cancelled after submit."),
	old_workflow: __("Order is stuck in a stage from an older workflow and needs clean-up."),
	other: __("Order is in a state that is not part of the current workflow."),
};

// Rows with fewer sketches than this are shown faded in Designer performance
const SD_LOW_VOLUME = 5;

class SketchDashboard {
	constructor(page) {
		this.page = page;
		this.tab = "all";
		this.due_soon_days = 2;
		this.data = null;
		this.sort = {
			workload: { key: "in_progress", dir: -1 },
			performance: { key: "volume", dir: -1 },
		};
		this.search = { workload: "", performance: "" };
		this.refresh = frappe.utils.debounce(() => this.load(), 350);

		this.add_styles();
		this.make_filters();
		this.make_body();
		this.bind_events();
		this.refresh();
	}

	// ------------------------------------------------------------------
	// Filters
	// ------------------------------------------------------------------
	make_filters() {
		const on_change = () => this.refresh();
		const add = (df) => this.page.add_field(Object.assign({ change: on_change }, df));

		add({
			fieldname: "period",
			label: __("Period"),
			fieldtype: "Select",
			options: ["", "Today", "This Week", "This Month", "Last 3 Months", "This Quarter", "This Year"].join("\n"),
			change: () => this.apply_period(),
		});
		add({ fieldname: "from_date", label: __("From Date"), fieldtype: "Date" });
		add({ fieldname: "to_date", label: __("To Date"), fieldtype: "Date" });
		add({ fieldname: "branch", label: __("Branch"), fieldtype: "Link", options: "Branch" });
		add({
			fieldname: "sketch_no",
			label: __("Sketch No"),
			fieldtype: "Link",
			options: "Sketch Order",
		});
		add({ fieldname: "customer", label: __("Customer"), fieldtype: "Link", options: "Customer" });
		add({ fieldname: "sales_person", label: __("Sales Person"), fieldtype: "Link", options: "Sales Person" });
		add({
			fieldname: "designer",
			label: __("Designer"),
			fieldtype: "Link",
			options: "Employee",
			get_query: () => ({ filters: { status: "Active" } }),
		});
		add({ fieldname: "category", label: __("Category"), fieldtype: "Select", options: "" });
		add({
			fieldname: "order_type",
			label: __("Order Type"),
			fieldtype: "Select",
			options: ["", "Sales", "Stock Order", "Repair", "Purchase"].join("\n"),
		});

		this.page.set_primary_action(__("Refresh"), () => this.load(), "refresh");
		this.page.set_secondary_action(__("Clear filters"), () => this.clear_filters());
	}

	apply_period() {
		const period = this.page.fields_dict.period.get_value();
		const today = moment();
		let from = null;
		if (period === "Today") from = today.clone();
		else if (period === "This Week") from = today.clone().startOf("isoWeek");
		else if (period === "This Month") from = today.clone().startOf("month");
		else if (period === "Last 3 Months") from = today.clone().subtract(3, "months").add(1, "days");
		else if (period === "This Quarter") from = today.clone().startOf("quarter");
		else if (period === "This Year") from = today.clone().startOf("year");

		this.page.fields_dict.from_date.set_value(from ? from.format("YYYY-MM-DD") : "");
		this.page.fields_dict.to_date.set_value(from ? today.format("YYYY-MM-DD") : "");
		this.refresh();
	}

	clear_filters() {
		[
			"period",
			"from_date",
			"to_date",
			"branch",
			"sketch_no",
			"customer",
			"sales_person",
			"designer",
			"category",
			"order_type",
		].forEach((f) => this.page.fields_dict[f].set_value(""));
		this.tab = "all";
		this.refresh();
	}

	get_filters() {
		const v = (f) => this.page.fields_dict[f].get_value() || null;
		return {
			from_date: v("from_date"),
			to_date: v("to_date"),
			branch: v("branch"),
			sketch_no: v("sketch_no"),
			customer: v("customer"),
			sales_person: v("sales_person"),
			designer: v("designer"),
			category: v("category"),
			order_type: v("order_type"),
			tab: this.tab,
		};
	}

	set_category_options(categories) {
		const field = this.page.fields_dict.category;
		const current = field.get_value();
		field.df.options = [""].concat(categories || []).join("\n");
		field.refresh();
		if (current) field.set_input(current);
	}

	// ------------------------------------------------------------------
	// Events
	// ------------------------------------------------------------------
	make_body() {
		this.$body = $(`<div class="sd"></div>`).appendTo(this.page.main);
	}

	bind_events() {
		this.$body.on("click", "[data-seg]", (e) => {
			const seg = JSON.parse(decodeURIComponent($(e.currentTarget).attr("data-seg")));
			const title = $(e.currentTarget).attr("data-title") || __("Sketch Orders");
			this.drill(seg, title);
		});
		this.$body.on("keydown", "[data-seg], [data-sort]", (e) => {
			if (e.key === "Enter") $(e.currentTarget).trigger("click");
		});
		this.$body.on("click", "[data-tab]", (e) => {
			this.tab = $(e.currentTarget).attr("data-tab");
			this.refresh();
		});
		this.$body.on("change", ".sd-due-days", (e) => {
			this.due_soon_days = Math.max(parseInt($(e.currentTarget).val(), 10) || 0, 0);
			this.refresh();
		});
		// Tooltips inside scrolling tables: float the box above the table so it is not clipped
		this.$body.on("mouseenter", ".sd-scrollbox .sd-tip", (e) => {
			const tip = e.currentTarget;
			const box = tip.querySelector(".sd-tip-box");
			if (!box) return;
			const r = tip.getBoundingClientRect();
			const width = 300;
			const left = Math.max(8, Math.min(r.right - width, window.innerWidth - width - 8));
			box.style.position = "fixed";
			box.style.left = left + "px";
			box.style.right = "auto";
			box.style.top = r.bottom + 6 + "px";
			box.style.display = "block";
			const bh = box.getBoundingClientRect().height;
			if (r.bottom + 6 + bh > window.innerHeight) box.style.top = Math.max(8, r.top - bh - 6) + "px";
		});
		this.$body.on("mouseleave", ".sd-scrollbox .sd-tip", (e) => {
			const box = e.currentTarget.querySelector(".sd-tip-box");
			if (box) box.removeAttribute("style");
		});
		this.$body.on("input", ".sd-search", (e) => {
			const table = $(e.currentTarget).attr("data-table");
			this.search[table] = ($(e.currentTarget).val() || "").toLowerCase();
			this.apply_search(table);
		});
		this.$body.on("click", "[data-sort]", (e) => {
			const [table, key] = $(e.currentTarget).attr("data-sort").split(":");
			const s = this.sort[table];
			s.dir = s.key === key ? -s.dir : key === "name" ? 1 : -1;
			s.key = key;
			this.render();
		});
	}

	apply_search(table) {
		const q = this.search[table];
		this.$body.find(`.sd-${table} tbody tr`).each(function () {
			$(this).toggle(!q || ($(this).attr("data-name") || "").includes(q));
		});
	}

	load() {
		const filters = this.get_filters();
		this.$body.addClass("sd-loading");
		frappe
			.call({
				method: SD_METHOD + "get_dashboard_data",
				args: { filters: JSON.stringify(filters), due_soon_days: this.due_soon_days },
			})
			.then((r) => {
				this.data = r.message;
				this.set_category_options(this.data.categories);
				this.render();
			})
			.always(() => this.$body.removeClass("sd-loading"));
	}

	// ------------------------------------------------------------------
	// Rendering helpers
	// ------------------------------------------------------------------
	esc(v) {
		return frappe.utils.escape_html(v == null ? "" : String(v));
	}

	num(v) {
		return (v || 0).toLocaleString("en-IN");
	}

	seg(obj, title) {
		return `data-seg="${encodeURIComponent(JSON.stringify(obj))}" data-title="${this.esc(title)}" tabindex="0" role="button"`;
	}

	link_num(value, seg, title) {
		if (!value) return `<span class="sd-zero">0</span>`;
		return `<a class="sd-link" ${this.seg(seg, title)}>${this.num(value)}</a>`;
	}

	section(title, body, note, extra_class) {
		return `
			<section class="sd-section ${extra_class || ""}">
				<div class="sd-section-head">
					<h4>${this.esc(title)}</h4>
					${note ? `<span class="sd-note">${note}</span>` : ""}
				</div>
				${body}
			</section>`;
	}

	sort_th(table, key, label, numeric) {
		const s = this.sort[table];
		const arrow = s.key === key ? (s.dir === 1 ? " ▲" : " ▼") : "";
		return `<th class="sd-sortable ${numeric ? "sd-n" : ""}" data-sort="${table}:${key}" tabindex="0" title="${__("Sort")}">${label}${arrow}</th>`;
	}

	sorted(list, table, value_fn) {
		const s = this.sort[table];
		const val = value_fn || ((row, key) => row[key]);
		return [...list].sort((a, b) => {
			const x = val(a, s.key);
			const y = val(b, s.key);
			if (typeof x === "string" || typeof y === "string") {
				return s.dir * String(x || "").localeCompare(String(y || ""));
			}
			return s.dir * ((x || 0) - (y || 0));
		});
	}

	// ------------------------------------------------------------------
	// Render
	// ------------------------------------------------------------------
	render() {
		const d = this.data;
		if (!d) return;
		this.$body.html(`
			<div class="sd-snapshot"><strong>${__("Sketch snapshot")}</strong> ${__("as of")} ${frappe.datetime.str_to_user(d.generated_at)}</div>
			<div class="sd-info">
				${__("Stages below follow the Sketch Order workflow. \"Draft\" here means the order is not yet assigned to a designer. This is different from \"Draft\" in the Sketch Order list, which means the document is not yet submitted.")}
			</div>
			<div class="sd-topbar">
				${this.render_tabs()}
				<span class="sd-hint">${__("Click any underlined number to see the Sketch Orders behind it.")}</span>
			</div>
			${this.render_pipeline(d)}
			<div class="sd-row sd-row-3">
				${this.render_made_by(d)}
				${this.render_order_types(d)}
				${this.render_alerts(d)}
			</div>
			${this.render_workload(d)}
			${this.render_performance(d)}
			${this.section(
				__("Approval rate by month"),
				`<div class="sd-chart"></div>`,
				__("Last 12 months, by the date the approval was recorded. Months with no approvals are not shown.")
			)}
			${this.render_matrix(d)}
			<div class="sd-row sd-row-2">
				${this.render_breakdown(__("Design type"), d.design_types, "design_type")}
				${this.render_breakdown(__("Flow type"), d.flow_types, "flow_type")}
			</div>
			<div class="sd-row sd-row-2">
				${this.render_breakdown(__("Top suppliers"), d.top_suppliers, "supplier")}
				${this.render_breakdown(__("Top customers"), d.top_customers, "customer")}
			</div>
			${this.render_health(d)}
		`);
		this.render_chart(d.trend);
		this.apply_search("workload");
		this.apply_search("performance");
		this.$body.find(".sd-search").each((_, el) => {
			$(el).val(this.search[$(el).attr("data-table")] || "");
		});
	}

	render_tabs() {
		const tabs = [
			["all", __("All")],
			["open_setting", __("Open setting")],
			["nova_glow", __("Nova Glow")],
			["close_open_setting", __("Close-open setting")],
		];
		return `<div class="sd-tabs">${tabs
			.map(
				([key, label]) =>
					`<button class="sd-tab ${this.tab === key ? "active" : ""}" data-tab="${key}">${label}</button>`
			)
			.join("")}</div>`;
	}

	render_pipeline(d) {
		const steps = d.status_summary
			.map((s) => {
				const group = SD_STAGE_GROUP[s.key] || "stopped";
				const tip = `${s.label}: ${SD_STAGE_HELP[s.key] || ""}\n${__("Workflow states")}: ${(s.states || []).join(", ")}`;
				const inner = `
					<span class="sd-step-label">${this.esc(s.label)}</span>
					<span class="sd-step-count">${this.num(s.orders)}</span>
					<span class="sd-step-meta">${s.pct}% · ${this.num(s.designs)} ${__("designs")}</span>`;
				return s.orders
					? `<a class="sd-step sd-${group}" title="${this.esc(tip)}" ${this.seg({ type: "bucket", key: s.key }, s.label)}>${inner}</a>`
					: `<div class="sd-step sd-${group} sd-step-empty" title="${this.esc(tip)}">${inner}</div>`;
			})
			.join("");

		return `
			<section class="sd-section sd-hero">
				<div class="sd-total">
					<a class="sd-total-num" ${this.seg({ type: "total" }, __("All Sketch Orders"))}>${this.num(d.total_orders)}</a>
					<span class="sd-total-label">${__("sketch orders")}</span>
					<span class="sd-total-sub">${this.num(d.total_designs)} ${__("designs")}</span>
				</div>
				<div class="sd-pipeline">${steps}</div>
				<div class="sd-legend">
					<span class="sd-key sd-waiting">${__("Waiting")}</span>
					<span class="sd-key sd-designer">${__("With designer / HOD")}</span>
					<span class="sd-key sd-after">${__("QC and item creation")}</span>
					<span class="sd-key sd-done">${__("Approved")}</span>
					<span class="sd-key sd-stopped">${__("Stopped")}</span>
					<span class="sd-legend-tip">${__("Hover a stage to see which workflow states it includes.")}</span>
				</div>
			</section>`;
	}

	simple_table(rows_html) {
		return `<table class="sd-table"><thead><tr><th></th><th class="sd-n">${__("Orders")}</th><th class="sd-n">${__("Designs")}</th></tr></thead><tbody>${rows_html}</tbody></table>`;
	}

	purchase_tip(d, label) {
		const ps = d.purchase_split;
		const supplier = (d.made_by || []).find((m) => m.key === "supplier") || { orders: 0 };
		const purchase = (d.order_types || []).find((o) => o.key === "Purchase") || { orders: 0 };
		// No tip when the two numbers match, or when the server did not send the split
		if (!ps || supplier.orders === purchase.orders) return null;

		const lines = [];
		if (ps.not_assigned) {
			lines.push(`<b>${this.num(ps.not_assigned)}</b> ${__("Purchase orders are not given to any supplier yet.")}`);
		}
		if (ps.designer) {
			lines.push(`<b>${this.num(ps.designer)}</b> ${__("Purchase orders were made by our own designers, not a supplier.")}`);
		}
		const otherSupplier = supplier.orders - ps.supplier;
		if (otherSupplier > 0) {
			lines.push(`<b>${this.num(otherSupplier)}</b> ${__("supplier orders are not of type Purchase.")}`);
		}
		return `
			<span class="sd-tip">
				${this.esc(label)} <span class="sd-tip-icon">ⓘ</span>
				<span class="sd-tip-box">
					<b>${__("Supplier")} ${this.num(supplier.orders)} ${__("vs")} ${__("Purchase")} ${this.num(purchase.orders)}</b><br>
					${__("Supplier = sketches made by a supplier.")}<br>
					${__("Purchase = orders of type Purchase.")}
					<span class="sd-tip-list"><b>${__("Why the difference")}:</b><br>${lines.join("<br>")}</span>
				</span>
			</span>`;
	}

	render_made_by(d) {
		const na = d.not_assigned_breakdown || { waiting: 0, cancelled: 0, to_check: 0 };
		const naTip = `
			<span class="sd-tip">
				${__("Not assigned")} <span class="sd-tip-icon">ⓘ</span>
				<span class="sd-tip-box">
					<b>${__("Not assigned")}</b>: ${__("the Sketch Order has no designer assigned and no supplier set.")}<br>
					${__("This usually means the order is still waiting to be given to a designer or supplier.")}
					<span class="sd-tip-list">
						${__("Waiting for assignment (Draft / On hold)")}: <b>${this.num(na.waiting)}</b><br>
						${__("Cancelled before assignment")}: <b>${this.num(na.cancelled)}</b><br>
						${__("Moved ahead without designer or supplier (to check)")}: <b>${this.num(na.to_check)}</b>
					</span>
				</span>
			</span>`;
		const rows = d.made_by
			// Hide "Not assigned" when there is nothing in it
			.filter((m) => !(m.key === "not_assigned" && !m.orders))
			.map(
				(m) => `
				<tr>
					<td>${
						m.key === "not_assigned"
							? naTip
							: m.key === "supplier"
							? this.purchase_tip(d, m.label) || this.esc(m.label)
							: this.esc(m.label)
					}</td>
					<td class="sd-n">${this.link_num(m.orders, { type: "made_by", key: m.key }, m.label)}</td>
					<td class="sd-n">${this.num(m.designs)}</td>
				</tr>`
			)
			.join("");
		return this.section(__("Sketch made by"), this.simple_table(rows));
	}

	render_order_types(d) {
		const rows = d.order_types
			.map(
				(o) => `
				<tr>
					<td>${o.key === "Purchase" ? this.purchase_tip(d, o.label) || this.esc(o.label) : this.esc(o.label)}</td>
					<td class="sd-n">${this.link_num(o.orders, { type: "order_type", key: o.key }, o.label)}</td>
					<td class="sd-n">${this.num(o.designs)}</td>
				</tr>`
			)
			.join("");
		return this.section(__("Order type"), this.simple_table(rows));
	}

	render_alerts(d) {
		const a = d.alerts;
		const age = (key, label) => `
			<div class="sd-age-row">
				<span>${label}</span>
				<span class="sd-n">${this.link_num(a[key], { type: "alert", key }, `${__("Overdue")}: ${label}`)}</span>
			</div>`;
		return this.section(
			__("Delivery alerts"),
			`
			<div class="sd-alert sd-alert-over">
				<span>${__("Overdue")}</span>
				<strong>${this.link_num(a.overdue, { type: "alert", key: "overdue" }, __("Overdue orders"))}</strong>
			</div>
			<div class="sd-age">
				${age("overdue_7", __("1–7 days late"))}
				${age("overdue_30", __("8–30 days late"))}
				${age("overdue_old", __("More than 30 days late"))}
			</div>
			<div class="sd-alert sd-alert-soon">
				<span>${__("Due within")}
					<input type="number" min="0" class="sd-due-days" value="${a.due_soon_days}" aria-label="${__("Days")}"> ${__("days")}</span>
				<strong>${this.link_num(a.due_soon, { type: "alert", key: "due_soon" }, __("Orders due soon"))}</strong>
			</div>`,
			__("Orders still with the designer or HOD, by delivery date")
		);
	}

	render_workload(d) {
		if (!d.designer_workload.length) {
			return this.section(
				__("Designer workload"),
				`<div class="sd-empty">${__("No designer assignments for these filters.")}</div>`
			);
		}
		const list = this.sorted(d.designer_workload, "workload");
		const total = { orders: 0, designs: 0, in_progress: 0, stuck: 0, completed: 0, cancelled: 0 };
		const rows = list
			.map((w) => {
				Object.keys(total).forEach((k) => (total[k] += w[k] || 0));
				const s = (metric) => ({ type: "designer", key: w.key, metric });
				const t = (label) => `${w.name}: ${label}`;
				return `
				<tr data-name="${this.esc((w.name || "").toLowerCase())}">
					<td>${this.esc(w.name)}</td>
					<td class="sd-n">${this.link_num(w.orders, s("orders"), t(__("all orders")))}</td>
					<td class="sd-n">${this.num(w.designs)}</td>
					<td class="sd-n">${this.link_num(w.in_progress, s("in_progress"), t(__("in progress")))}</td>
					<td class="sd-n sd-warn-col">${this.link_num(w.stuck, s("stuck"), t(__("more than 30 days late")))}</td>
					<td class="sd-n">${this.link_num(w.completed, s("completed"), t(__("completed")))}</td>
					<td class="sd-n">${this.link_num(w.cancelled, s("cancelled"), t(__("cancelled")))}</td>
				</tr>`;
			})
			.join("");
		return this.section(
			__("Designer workload"),
			`
			<input type="text" class="sd-search form-control" data-table="workload" placeholder="${__("Search designer")}">
			<div class="sd-scrollbox">
				<table class="sd-table sd-workload">
					<thead><tr>
						${this.sort_th("workload", "name", __("Designer"))}
						${this.sort_th("workload", "orders", __("Orders"), true)}
						${this.sort_th("workload", "designs", __("Designs"), true)}
						${this.sort_th("workload", "in_progress", __("In progress"), true)}
						${this.sort_th("workload", "stuck", __("Late 30+ days"), true)}
						${this.sort_th("workload", "completed", __("Completed"), true)}
						${this.sort_th("workload", "cancelled", __("Cancelled"), true)}
					</tr></thead>
					<tbody>${rows}</tbody>
					<tfoot><tr>
						<td>${__("Total")}</td>
						<td class="sd-n">${this.num(total.orders)}</td>
						<td class="sd-n">${this.num(total.designs)}</td>
						<td class="sd-n">${this.num(total.in_progress)}</td>
						<td class="sd-n">${this.num(total.stuck)}</td>
						<td class="sd-n">${this.num(total.completed)}</td>
						<td class="sd-n">${this.num(total.cancelled)}</td>
					</tr></tfoot>
				</table>
			</div>`,
			__("In-house designers only. Completed = passed final sketch approval (HOD). Late 30+ days = still in progress, delivery date passed over 30 days ago. Total counts an order once per designer."),
			"sd-tall"
		);
	}

	rate_cell(approved, total, rate) {
		if (!total) return `<span class="sd-zero">–</span>`;
		const cls = rate >= 80 ? "sd-good" : rate >= 60 ? "sd-mid" : "sd-low";
		return `${this.num(approved)}/${this.num(total)} <span class="sd-rate ${cls}">${rate}%</span>`;
	}

	final_gap_tip(p, cell) {
		// Explain why final sketches reviewed differ from rough sketches passed
		const waiting = p.gap_waiting || 0;
		const cancelled = p.gap_cancelled || 0;
		const notTaken = p.gap_not_taken || 0;
		if (!waiting && !cancelled && !notTaken) return cell;
		const lines = [];
		if (waiting) lines.push(`<b>${this.num(waiting)}</b> ${__("are waiting for the HOD final check (order still in progress).")}`);
		if (cancelled) lines.push(`<b>${this.num(cancelled)}</b> ${__("were in orders that got cancelled.")}`);
		if (notTaken) lines.push(`<b>${this.num(notTaken)}</b> ${__("were not taken to a final sketch (order moved ahead with fewer designs).")}`);
		return `
			<span class="sd-tip sd-tip-right">
				${cell} <span class="sd-tip-icon">ⓘ</span>
				<span class="sd-tip-box">
					<b>${__("Rough passed")} ${this.num(p.rough_approved)} ${__("vs")} ${__("Final checked")} ${this.num(p.final_total)}</b><br>
					${__("Rough and final are two separate HOD checks. Not every rough sketch has reached the final check yet.")}
					<span class="sd-tip-list"><b>${__("Why {0} have not reached the final check yet", [this.num(waiting + cancelled + notTaken)])}:</b><br>${lines.join("<br>")}</span>
				</span>
			</span>`;
	}

	render_performance(d) {
		const f = this.get_filters();
		const period =
			f.from_date || f.to_date
				? `${f.from_date ? frappe.datetime.str_to_user(f.from_date) : "…"} – ${f.to_date ? frappe.datetime.str_to_user(f.to_date) : "…"}`
				: __("all time");
		const t = d.performance_totals;
		if (!d.performance.length) {
			return this.section(
				__("Designer performance"),
				`<div class="sd-empty">${__("No approvals recorded for this period.")}</div>`,
				`${__("Approvals recorded")}: ${period}`
			);
		}
		const value = (row, key) => (key === "volume" ? row.rough_total + row.final_total : row[key]);
		const rows = this.sorted(d.performance, "performance", value)
			.map((p) => {
				const low = p.rough_total + p.final_total < SD_LOW_VOLUME;
				const flag = p.unusual
					? ` <span class="sd-flag" title="${__("Has an unusual approval entry. See Data health.")}">⚠</span>`
					: "";
				return `
				<tr class="${low ? "sd-low-volume" : ""}" data-name="${this.esc((p.name || "").toLowerCase())}">
					<td>${this.esc(p.name)}${flag}</td>
					<td class="sd-n">${this.rate_cell(p.rough_approved, p.rough_total, p.rough_rate)}</td>
					<td class="sd-n">${this.num(p.rough_rejected)}</td>
					<td class="sd-n">${this.final_gap_tip(p, this.rate_cell(p.final_approved, p.final_total, p.final_rate))}</td>
					<td class="sd-n">${this.num(p.final_rejected)}</td>
					<td class="sd-n">${this.num(p.final_hold)}</td>
					<td class="sd-n">${this.num(p.cmo_approved)}</td>
				</tr>`;
			})
			.join("");
		return this.section(
			__("Designer performance"),
			`
			<input type="text" class="sd-search form-control" data-table="performance" placeholder="${__("Search designer")}">
			<div class="sd-scrollbox">
				<table class="sd-table sd-performance">
					<thead><tr>
						${this.sort_th("performance", "name", __("Designer"))}
						${this.sort_th("performance", "rough_rate", __("Rough sketch approved"), true)}
						${this.sort_th("performance", "rough_rejected", __("Rough rejected"), true)}
						${this.sort_th("performance", "final_rate", __("Final sketch approved"), true)}
						${this.sort_th("performance", "final_rejected", __("Final rejected"), true)}
						${this.sort_th("performance", "final_hold", __("Final on hold"), true)}
						${this.sort_th("performance", "cmo_approved", __("CMO approved"), true)}
					</tr></thead>
					<tbody>${rows}</tbody>
					<tfoot><tr>
						<td>${__("Total")}</td>
						<td class="sd-n">${this.rate_cell(t.rough_approved, t.rough_total, t.rough_rate)}</td>
						<td class="sd-n">${this.num(t.rough_rejected)}</td>
						<td class="sd-n">${this.final_gap_tip(t, this.rate_cell(t.final_approved, t.final_total, t.final_rate))}</td>
						<td class="sd-n">${this.num(t.final_rejected)}</td>
						<td class="sd-n">${this.num(t.final_hold)}</td>
						<td class="sd-n">${this.num(t.cmo_approved)}</td>
					</tr></tfoot>
				</table>
			</div>`,
			`${__("Approvals recorded")}: ${period}. ${__("Faded rows have fewer than {0} sketches.", [SD_LOW_VOLUME])}`,
			"sd-tall"
		);
	}

	render_chart(trend) {
		const el = this.$body.find(".sd-chart").get(0);
		if (!el || !trend || !frappe.Chart) return;
		const idx = trend.labels.map((_, i) => i).filter((i) => trend.rough_total[i] || trend.final_total[i]);
		if (!idx.length) {
			$(el).html(`<div class="sd-empty">${__("No approvals in the last 12 months.")}</div>`);
			return;
		}
		const pick = (arr) => idx.map((i) => arr[i]);
		const labels = idx.map((i) => `${trend.labels[i]} (${trend.rough_total[i] + trend.final_total[i]})`);
		new frappe.Chart(el, {
			type: "line",
			height: 230,
			data: {
				labels: labels,
				datasets: [
					{ name: __("Rough sketch %"), values: pick(trend.rough_rate) },
					{ name: __("Final sketch %"), values: pick(trend.final_rate) },
				],
			},
			axisOptions: { xIsSeries: 1 },
			lineOptions: { dotSize: 4, regionFill: 0 },
			tooltipOptions: { formatTooltipY: (v) => `${v}%` },
			colors: ["#2f6db5", "#2e8b57"],
		});
		$(el).append(
			`<div class="sd-note sd-chart-note">${__("Number in brackets = sketches reviewed that month (rough + final).")}</div>`
		);
	}

	render_matrix(d) {
		const m = Object.assign({}, d.category_status_matrix);
		if (!m.rows.length) return "";
		// Approved goes last, just before Total
		m.columns = m.columns.filter((c) => c.key !== "approved").concat(m.columns.filter((c) => c.key === "approved"));
		const pctCell = (approved, total) => {
			if (!total) return `<td class="sd-n"><span class="sd-zero">–</span></td>`;
			const pct = Math.round((approved * 1000) / total) / 10;
			// up to 50% red, above 50% to 80% golden, above 80% green
			const cls = pct > 80 ? "sd-good" : pct > 50 ? "sd-mid" : "sd-low";
			return `<td class="sd-n"><span class="sd-rate ${cls}">${pct}%</span></td>`;
		};
		const col_max = {};
		m.columns.forEach((c) => {
			col_max[c.key] = Math.max(1, ...m.rows.map((r) => r.cells[c.key] || 0));
		});
		const head = m.columns.map((c) => `<th class="sd-n">${this.esc(c.label)}</th>`).join("");
		const rows = m.rows
			.map((r) => {
				const cells = m.columns
					.map((c) => {
						const v = r.cells[c.key] || 0;
						const alpha = v ? (0.08 + (0.42 * v) / col_max[c.key]).toFixed(2) : 0;
						const group = SD_STAGE_GROUP[c.key] || "stopped";
						const style = v ? `style="--sd-heat:${alpha}"` : "";
						return `<td class="sd-n sd-heat sd-${group}" ${style}>${this.link_num(
							v,
							{ type: "matrix", category: r.category, bucket: c.key },
							`${r.category}: ${c.label}`
						)}</td>`;
					})
					.join("");
				return `<tr>
					<td>${this.esc(r.category)}</td>
					${cells}
					<td class="sd-n sd-strong">${this.link_num(r.total, { type: "matrix", category: r.category }, r.category)}</td>
					${pctCell(r.cells.approved || 0, r.total)}
				</tr>`;
			})
			.join("");
		const foot = m.columns
			.map((c) => `<td class="sd-n">${this.link_num(m.column_totals[c.key], { type: "bucket", key: c.key }, c.label)}</td>`)
			.join("");
		return this.section(
			__("Orders by category and stage"),
			`<div class="sd-scroll"><table class="sd-table sd-matrix">
				<thead><tr><th>${__("Category")}</th>${head}<th class="sd-n">${__("Total")}</th><th class="sd-n" title="${__("Approved ÷ Total orders of the category")}">${__("Approval %")}</th></tr></thead>
				<tbody>${rows}</tbody>
				<tfoot><tr><td>${__("Total")}</td>${foot}<td class="sd-n">${this.link_num(m.grand_total, { type: "total" }, __("All Sketch Orders"))}</td>${pctCell((m.column_totals || {}).approved || 0, m.grand_total)}</tr></tfoot>
			</table></div>`,
			__("Darker cell = more orders compared with the rest of that column. Approval % = Approved ÷ Total.")
		);
	}

	render_breakdown(title, items, seg_type) {
		if (!items || !items.length) {
			return this.section(title, `<div class="sd-empty">${__("No data for these filters.")}</div>`);
		}
		const max = Math.max(...items.map((i) => i.orders), 1);
		const rows = items
			.map((i) => {
				let tag = i.own ? `<span class="sd-tag" title="${__("Company's own customer account (stock)")}">${__("Own company")}</span>` : "";
				if (i.warn) {
					tag += `<span class="sd-tag sd-tag-warn" title="${__("This supplier is not in a design supplier group. See Data health.")}">⚠ ${__("Check supplier")}</span>`;
				}
				return `
				<div class="sd-bar-row">
					<span class="sd-bar-label" title="${this.esc(i.label)}">${tag}${this.esc(i.label)}</span>
					<span class="sd-bar"><span style="width:${Math.round((i.orders * 100) / max)}%"></span></span>
					<span class="sd-n">${this.link_num(i.orders, { type: seg_type, key: i.key }, `${title}: ${i.label}`)}</span>
					<span class="sd-n sd-muted">${this.num(i.designs)}</span>
				</div>`;
			})
			.join("");
		return this.section(
			title,
			`<div class="sd-bars">
				<div class="sd-bar-row sd-bar-head"><span></span><span></span><span class="sd-n">${__("Orders")}</span><span class="sd-n">${__("Designs")}</span></div>
				${rows}
			</div>`
		);
	}

	render_health(d) {
		const h = d.data_health;
		const items = [
			{
				label: __("Workflow says Cancelled, but the document is still submitted"),
				value: h.cancelled_not_closed,
				seg: { type: "health", key: "cancelled_not_closed" },
			},
			{
				label: __("Workflow says Approved, but the document is cancelled"),
				value: h.approved_but_cancelled,
				seg: { type: "health", key: "approved_but_cancelled" },
			},
			{
				label:
					__("Supplier is not a design supplier") +
					(h.wrong_supplier_groups && h.wrong_supplier_groups.length
						? ` (${__("group")}: ${h.wrong_supplier_groups.join(", ")})`
						: ""),
				value: h.wrong_supplier,
				seg: { type: "health", key: "wrong_supplier" },
			},
			{
				label: __("Orders stuck in the old workflow (Attach Image / Image QC)"),
				value: h.old_workflow,
				seg: { type: "health", key: "old_workflow" },
			},
			{
				label: __("Orders past draft with no designer and no supplier"),
				value: h.no_maker,
				seg: { type: "health", key: "no_maker" },
			},
			{
				label: __("Orders in a state outside the workflow"),
				value: h.other_state,
				seg: { type: "health", key: "other_state" },
			},
		];
		const list = items
			.map(
				(i) =>
					`<div class="sd-health-row"><span>${i.label}</span><strong>${this.link_num(i.value, i.seg, i.label)}</strong></div>`
			)
			.join("");
		const unusual = h.unusual_approvals.length
			? `<div class="sd-health-sub">${__("Approval entries with 100 or more sketches in a single row. These may be genuine bulk entries; please verify.")}</div>
				<div class="sd-scroll"><table class="sd-table">
					<thead><tr>
						<th>${__("Sketch Order")}</th><th>${__("Stage")}</th><th>${__("Designer")}</th>
						<th class="sd-n">${__("Approved")}</th><th class="sd-n">${__("Rejected")}</th><th class="sd-n">${__("On hold")}</th>
						<th>${__("Recorded on")}</th>
					</tr></thead>
					<tbody>${h.unusual_approvals
						.map(
							(u) => `<tr>
							<td><a href="/app/sketch-order/${encodeURIComponent(u.sketch_order)}" target="_blank">${this.esc(u.sketch_order)}</a></td>
							<td>${this.esc(u.stage)}</td>
							<td>${this.esc(u.designer_name)}</td>
							<td class="sd-n">${this.num(u.approved)}</td>
							<td class="sd-n">${this.num(u.reject)}</td>
							<td class="sd-n">${this.num(u.hold)}</td>
							<td>${frappe.datetime.str_to_user(u.recorded_on)}</td>
						</tr>`
						)
						.join("")}</tbody>
				</table></div>`
			: "";
		return this.section(__("Data health"), list + unusual, __("Records to review and clean up"));
	}

	// ------------------------------------------------------------------
	// Drill-down
	// ------------------------------------------------------------------
	drill(seg, title) {
		const dialog = new frappe.ui.Dialog({
			title: title,
			size: "extra-large",
			fields: [{ fieldtype: "HTML", fieldname: "list" }],
		});
		const $list = dialog.fields_dict.list.$wrapper;
		$list.html(`<div class="sd-empty">${__("Loading…")}</div>`);
		dialog.show();

		frappe
			.call({
				method: SD_METHOD + "get_segment_orders",
				args: {
					filters: JSON.stringify(this.get_filters()),
					segment: JSON.stringify(seg),
					due_soon_days: this.due_soon_days,
				},
			})
			.then((r) => {
				const res = r.message || { total: 0, orders: [] };
				if (!res.orders.length) {
					$list.html(`<div class="sd-empty">${__("No Sketch Orders found.")}</div>`);
					return;
				}
				const rows = res.orders
					.map(
						(o) => `<tr>
						<td><a href="/app/sketch-order/${encodeURIComponent(o.name)}" target="_blank">${this.esc(o.name)}</a></td>
						<td>${this.esc(o.status)}</td>
						<td>${this.esc(o.customer)}</td>
						<td>${this.esc(o.category)}</td>
						<td class="sd-n">${this.num(o.designs)}</td>
						<td>${this.esc(o.made_by)}</td>
						<td>${o.due_date ? frappe.datetime.str_to_user(o.due_date) : ""}</td>
					</tr>`
					)
					.join("");
				const names = res.orders.map((o) => o.name);
				dialog.set_primary_action(__("Open in list view"), () => {
					dialog.hide();
					frappe.route_options = { name: ["in", names] };
					frappe.set_route("List", "Sketch Order");
				});
				const count =
					res.total > res.orders.length
						? __("Showing first {0} of {1}. List view will open these {0}.", [res.orders.length, res.total])
						: __("{0} orders", [res.total]);
				$list.html(`
					<div class="sd">
						<div class="sd-note">${count}</div>
						<div class="sd-scroll sd-drill">
							<table class="sd-table">
								<thead><tr>
									<th>${__("Sketch Order")}</th><th>${__("Status")}</th><th>${__("Customer")}</th>
									<th>${__("Category")}</th><th class="sd-n">${__("Designs")}</th>
									<th>${__("Designer / supplier")}</th><th>${__("Delivery date")}</th>
								</tr></thead>
								<tbody>${rows}</tbody>
							</table>
						</div>
					</div>`);
			});
	}

	// ------------------------------------------------------------------
	// Styles
	// ------------------------------------------------------------------
	add_styles() {
		$("#sd-styles").remove();
		const css = `
		.sd { --sd-waiting: #8a94a6; --sd-designer: #2f6db5; --sd-after: #c27c0e; --sd-done: #2e8b57; --sd-stopped: #b5473a;
			display: flex; flex-direction: column; gap: 14px; padding-bottom: 24px; }
		.sd-loading { opacity: .55; pointer-events: none; }
		.sd-section { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 10px; padding: 14px 16px; min-width: 0; }
		.sd-section-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 10px; flex-wrap: wrap; }
		.sd-section-head h4 { margin: 0; font-size: 15px; font-weight: 600; color: var(--heading-color, var(--text-color)); }
		.sd-note { font-size: 12px; color: var(--text-muted); max-width: 70ch; }
		.sd-row { display: grid; gap: 14px; }
		.sd-row-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
		.sd-row-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
		@media (max-width: 991px) { .sd-row-3, .sd-row-2 { grid-template-columns: minmax(0, 1fr); } }

		.sd-snapshot { font-size: 13px; color: var(--text-muted); }
		.sd-info { font-size: 12.5px; color: var(--text-muted); background: var(--subtle-fg, var(--bg-color)); border-radius: 8px; padding: 8px 12px; max-width: 110ch; }
		.sd-snapshot strong { color: var(--text-color); font-weight: 600; margin-right: 4px; }
		.sd-topbar { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
		.sd-hint { font-size: 12px; color: var(--text-muted); }
		.sd-tabs { display: flex; gap: 6px; flex-wrap: wrap; }
		.sd-tab { border: 1px solid var(--border-color); background: var(--card-bg); color: var(--text-color);
			border-radius: 999px; padding: 4px 14px; font-size: 13px; }
		.sd-tab.active { background: var(--text-color); color: var(--card-bg); border-color: var(--text-color); }

		.sd-hero { display: grid; grid-template-columns: 170px minmax(0, 1fr); gap: 18px; align-items: stretch; }
		@media (max-width: 767px) { .sd-hero { grid-template-columns: minmax(0, 1fr); } }
		.sd-total { display: flex; flex-direction: column; justify-content: center; border-right: 1px solid var(--border-color); padding-right: 16px; }
		@media (max-width: 767px) { .sd-total { border-right: 0; padding-right: 0; } }
		.sd-total-num { font-size: 40px; font-weight: 700; line-height: 1; color: var(--text-color); cursor: pointer; }
		.sd-total-label { font-size: 13px; color: var(--text-muted); margin-top: 4px; }
		.sd-total-sub { font-size: 13px; margin-top: 10px; color: var(--text-color); }
		.sd-pipeline { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 6px 4px; }
		@media (max-width: 1199px) { .sd-pipeline { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
		@media (max-width: 575px) { .sd-pipeline { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
		.sd-step { position: relative; display: flex; flex-direction: column; gap: 2px; min-width: 0;
			padding: 9px 14px 9px 18px; background: var(--subtle-fg, var(--bg-color)); color: var(--text-color);
			clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 50%, calc(100% - 10px) 100%, 0 100%, 10px 50%);
			border-top: 3px solid var(--sd-stage); text-decoration: none !important; }
		a.sd-step:hover, a.sd-step:focus-visible { background: var(--fg-hover-color, var(--control-bg)); outline: none; }
		.sd-step-empty { opacity: .5; }
		.sd-step-label { font-size: 12px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
		.sd-step-count { font-size: 22px; font-weight: 700; color: var(--sd-stage); line-height: 1.2; }
		.sd-step-meta { font-size: 11px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
		.sd-waiting { --sd-stage: var(--sd-waiting); }
		.sd-designer { --sd-stage: var(--sd-designer); }
		.sd-after { --sd-stage: var(--sd-after); }
		.sd-done { --sd-stage: var(--sd-done); }
		.sd-stopped { --sd-stage: var(--sd-stopped); }
		.sd-legend { grid-column: 1 / -1; display: flex; gap: 14px; flex-wrap: wrap; font-size: 12px; color: var(--text-muted); }
		.sd-legend-tip { margin-left: auto; }
		.sd-key::before { content: ""; display: inline-block; width: 10px; height: 3px; margin-right: 6px; vertical-align: middle; background: var(--sd-stage); }

		.sd-table { width: 100%; font-size: 13px; border-collapse: separate; border-spacing: 0; }
		.sd-table th { font-weight: 500; color: var(--text-muted); font-size: 12px; padding: 6px 8px; border-bottom: 1px solid var(--border-color); white-space: nowrap; background: var(--card-bg); }
		.sd-table td { padding: 6px 8px; border-bottom: 1px solid var(--border-color); color: var(--text-color); }
		.sd-table tfoot td { font-weight: 600; border-top: 1px solid var(--border-color); border-bottom: 0; background: var(--card-bg); }
		.sd-n { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
		.sd-strong { font-weight: 600; }
		.sd-scroll { overflow-x: auto; max-width: 100%; }
		.sd-scrollbox { overflow: auto; max-height: 440px; border: 1px solid var(--border-color); border-radius: 8px; }
		.sd-scrollbox thead th { position: sticky; top: 0; z-index: 2; }
		.sd-scrollbox tfoot td { position: sticky; bottom: 0; z-index: 2; }
		.sd-sortable { cursor: pointer; user-select: none; }
		.sd-sortable:hover, .sd-sortable:focus-visible { color: var(--text-color); outline: none; }
		.sd-search { max-width: 260px; margin-bottom: 8px; }
		.sd-link { color: var(--text-color); font-weight: 600; cursor: pointer; text-decoration: underline; text-decoration-color: var(--border-color); text-underline-offset: 3px; }
		.sd-link:hover, .sd-link:focus-visible { text-decoration-color: currentColor; outline: none; }
		.sd-zero, .sd-muted { color: var(--text-muted); }
		.sd-warn-col .sd-link { color: var(--sd-stopped); }
		.sd-rate { font-size: 11px; font-weight: 600; padding: 1px 6px; border-radius: 4px; margin-left: 4px; }
		.sd-good { color: var(--sd-done); background: rgba(46, 139, 87, .12); }
		.sd-mid { color: var(--sd-after); background: rgba(194, 124, 14, .12); }
		.sd-low { color: var(--sd-stopped); background: rgba(181, 71, 58, .12); }
		.sd-low-volume td { opacity: .5; }
		.sd-flag { color: var(--sd-after); cursor: help; }

		.sd-alert { display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; border-radius: 8px; margin-bottom: 8px; font-size: 13px; border-left: 3px solid; }
		.sd-alert strong { font-size: 20px; }
		.sd-alert-over { border-color: var(--sd-stopped); background: rgba(181, 71, 58, .07); margin-bottom: 4px; }
		.sd-alert-soon { border-color: var(--sd-after); background: rgba(194, 124, 14, .07); }
		.sd-age { padding: 2px 12px 8px 15px; margin-bottom: 6px; }
		.sd-age-row { display: flex; justify-content: space-between; font-size: 12.5px; padding: 3px 0; color: var(--text-muted); }
		.sd-due-days { width: 46px; margin: 0 4px; padding: 1px 4px; border: 1px solid var(--border-color); border-radius: 4px; background: var(--control-bg); color: var(--text-color); }

		.sd-heat { background: color-mix(in srgb, var(--sd-stage) calc(var(--sd-heat, 0) * 100%), transparent); }

		.sd-bars { display: flex; flex-direction: column; gap: 6px; }
		.sd-bar-row { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(0, 1.6fr) 56px 56px; gap: 10px; align-items: center; font-size: 13px; }
		.sd-bar-head { font-size: 12px; color: var(--text-muted); }
		.sd-bar-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
		.sd-bar { height: 8px; background: var(--subtle-fg, var(--bg-color)); border-radius: 4px; overflow: hidden; }
		.sd-bar span { display: block; height: 100%; background: var(--sd-designer); border-radius: 4px; }
		.sd-tag { display: inline-block; font-size: 10.5px; font-weight: 600; color: var(--sd-after); background: rgba(194, 124, 14, .12); border-radius: 4px; padding: 0 5px; margin-right: 6px; }

		.sd-tip { position: relative; cursor: help; }
		.sd-tip-icon { color: var(--text-muted); font-size: 12px; }
		.sd-tip-box { display: none; position: absolute; left: 0; top: 120%; z-index: 20; width: 300px;
			padding: 10px 12px; border-radius: 8px; border: 1px solid var(--border-color);
			background: var(--card-bg); color: var(--text-color); font-size: 12.5px; line-height: 1.45;
			box-shadow: 0 6px 20px rgba(0, 0, 0, .15); white-space: normal; }
		.sd-tip-right .sd-tip-box { left: auto; right: 0; text-align: left; }
		.sd-tip:hover .sd-tip-box, .sd-tip:focus-within .sd-tip-box { display: block; }
		.sd-tip-list { display: block; margin-top: 6px; padding-top: 6px; border-top: 1px solid var(--border-color); color: var(--text-muted); }
		.sd-tag-warn { color: var(--sd-stopped); background: rgba(181, 71, 58, .12); }
		.sd-health-row { display: flex; justify-content: space-between; gap: 12px; padding: 6px 0; border-bottom: 1px solid var(--border-color); font-size: 13px; }
		.sd-health-sub { margin: 12px 0 6px; font-size: 12px; color: var(--text-muted); }
		.sd-empty { padding: 18px; text-align: center; color: var(--text-muted); font-size: 13px; }
		.sd-footer { font-size: 12px; color: var(--text-muted); text-align: right; }
		.sd-drill { max-height: 60vh; overflow-y: auto; margin-top: 6px; }
		.sd-chart-note { margin-top: 4px; }
		`;
		$(`<style id="sd-styles">${css}</style>`).appendTo("head");
	}
}