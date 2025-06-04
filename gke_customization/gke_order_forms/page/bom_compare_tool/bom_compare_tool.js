frappe.pages["bom-compare-tool"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("BOM Compare Tool"),
		single_column: true,
	});

	new erpnext.BOMCompareTool(page);
};

erpnext.BOMCompareTool = class BOMCompareTool {
	constructor(page) {
		this.page = page;
		this.make_form();
	}

	make_form() {
		this.form = new frappe.ui.FieldGroup({
			fields: [
				{
					label: __("Template BOM"),
					fieldname: "name1",
					fieldtype: "Link",
					options: "BOM",
					change: () => this.fetch_and_render(),
					get_query: () => {
						return {
							filters: {
								// name: ["not in", [this.form.get_value("name2") || ""]],
								"bom_type":"Template",
							},
						};
					},
				},
				{
					fieldtype: "Column Break",
				},
				{
					label: __("Finish Goods BOM"),
					fieldname: "name2",
					fieldtype: "Link",
					options: "BOM",
					change: () => this.fetch_and_render(),
					get_query: () => {
						return {
							filters: {
								// name: ["not in", [this.form.get_value("name1") || ""]],
								"bom_type":"Finish Goods",
							},
						};
					},
				},
				{
					fieldtype: "Section Break",
				},
				{
					fieldtype: "HTML",
					fieldname: "preview",
				},
			],
			body: this.page.body,
		});
		this.form.make();
	}

	fetch_and_render() {
		let { name1, name2 } = this.form.get_values();
		if (!(name1 && name2)) {
			this.form.get_field("preview").html("");
			return;
		}

		this.form.get_field("preview").html(`
			<div class="text-muted margin-top">
				${__("Fetching...")}
			</div>
		`);

		frappe
			.call("gke_customization.gke_order_forms.doc_events.bom_compare.get_bom_diff", {
				bom1: name1,
				bom2: name2,
			})
			.then((r) => {
				let diff = r.message;
				console.log(diff);

				frappe.model.with_doctype("BOM", () => {
					this.render(name1, name2, diff);
				});
			});
	}

	render(name1, name2, diff) {
		let { all_values } = diff;

		let parent_html = `
			<h4 class="margin-top">${__("Parent Fields")}</h4>
			<table class="table table-bordered">
				<tr>
					<th>${__("Field")}</th>
					<th>${name1}</th>
					<th>${name2}</th>
				</tr>
				${Object.keys(all_values)
					.filter((key) => typeof all_values[key] === "object" && "bom1" in all_values[key])
					.map(
						(field) => `
					<tr>
						<td>${frappe.meta.get_label("BOM", field)}</td>
						<td>${all_values[field].bom1}</td>
						<td>${all_values[field].bom2}</td>
					</tr>
				`
					)
					.join("")}
			</table>
		`;

		let child_tables_html = Object.keys(all_values)
			.filter((key) => Array.isArray(all_values[key]))
			.map((table) => {
				let rows = all_values[table]
					.map((row) => {
						return Object.keys(row.values)
							.map((field) => `
							<tr>
								<td>${__(field.replace(/_/g, " ").replace(/^./, char => char.toUpperCase()))}</td>
								<td>${row.values[field].bom1 || ""}</td>
								<td>${row.values[field].bom2 || ""}</td>
							</tr>
							`)
						.join("");
					})
					.join("");

				return `
				<h4 class="margin-top">${__(table.replace(/_/g, " ").toUpperCase())}</h4>
				<table class="table table-bordered">
					<tr>
						<th>${__("Field Name")}</th>
						<th>${name1}</th>
						<th>${name2}</th>
					</tr>
					${rows}
				</table>
			`;
			})
			.join("");

		let final_html = `${parent_html} ${child_tables_html}`;
		this.form.get_field("preview").html(final_html);
	}
};
