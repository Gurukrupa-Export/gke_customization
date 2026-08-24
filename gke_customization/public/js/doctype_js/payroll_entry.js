// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

/*
 * GKE customization: selective and partial release of withheld salaries.
 *
 * Intercepts the stock "Release Withheld Salaries" button on Payroll Entry and
 * opens a dialog that lists every withheld employee with their pending amount.
 * - Individual release: check only the employees whose salary should be released.
 * - Partial release: lower an employee's "Release Amount" below the pending amount.
 *
 * Server counterpart: gke_customization.overrides.payroll_entry.CustomPayrollEntry
 * (make_bank_entry / get_withheld_salaries).
 */

frappe.ui.form.on("Payroll Entry", {
	setup(frm) {
		// runs before refresh, hence before hrms adds the stock button (inside the
		// async has_bank_entries callback); replace just its click handler
		const stock_add_custom_button = frm.add_custom_button.bind(frm);
		frm.add_custom_button = (label, fn, ...rest) => {
			if (label === "Release Withheld Salaries") {
				fn = () => gke_release_withheld_salaries(frm);
			}
			return stock_add_custom_button(label, fn, ...rest);
		};
	},
});

function gke_release_withheld_salaries(frm) {
	if (!frm.doc.payment_account) {
		frappe.msgprint(__("Payment Account is mandatory"));
		frm.scroll_to_field("payment_account");
		return;
	}

	frm.call("get_withheld_salaries").then((r) => {
		const withheld_salaries = r.message || [];

		if (!withheld_salaries.length) {
			frappe.msgprint({
				title: __("No Withheld Salaries"),
				message: __("There are no withheld salaries pending release for this Payroll Entry."),
				indicator: "orange",
			});
			return;
		}

		gke_show_release_dialog(frm, withheld_salaries);
	});
}

function gke_show_release_dialog(frm, withheld_salaries) {
	// default each row to a full release; a lower value releases partially
	withheld_salaries.forEach((row) => {
		row.release_amount = row.amount;
	});

	const dialog = new frappe.ui.Dialog({
		title: __("Release Withheld Salaries"),
		size: "large",
		fields: [
			{
				fieldname: "employees",
				fieldtype: "Table",
				label: __("Employees"),
				cannot_add_rows: true,
				in_place_edit: true,
				data: withheld_salaries,
				get_data: () => withheld_salaries,
				fields: [
					{
						fieldname: "employee",
						fieldtype: "Link",
						options: "Employee",
						label: __("Employee"),
						in_list_view: 1,
						read_only: 1,
						columns: 2,
					},
					{
						fieldname: "employee_name",
						fieldtype: "Data",
						label: __("Employee Name"),
						in_list_view: 1,
						read_only: 1,
						columns: 3,
					},
					{
						fieldname: "amount",
						fieldtype: "Currency",
						label: __("Pending Amount"),
						in_list_view: 1,
						read_only: 1,
						columns: 2,
					},
					{
						fieldname: "release_amount",
						fieldtype: "Currency",
						label: __("Release Amount"),
						in_list_view: 1,
						columns: 2,
					},
				],
			},
		],
		primary_action_label: __("Release"),
		primary_action() {
			const selected = dialog.fields_dict.employees.grid.get_selected_children();

			if (!selected.length) {
				frappe.msgprint(__("Please select at least one employee to release the salary for"));
				return;
			}

			const employees = [];
			const release_amounts = {};
			for (const row of selected) {
				const amount = flt(row.release_amount);

				if (amount <= 0) {
					frappe.msgprint(
						__("Release Amount must be greater than zero for employee {0}", [
							row.employee,
						]),
					);
					return;
				}
				if (amount > flt(row.amount)) {
					frappe.msgprint(
						__("Release Amount for employee {0} cannot exceed the pending amount {1}", [
							row.employee,
							row.amount,
						]),
					);
					return;
				}

				employees.push(row.employee);
				release_amounts[row.employee] = amount;
			}

			dialog.hide();
			gke_make_release_bank_entry(frm, employees, release_amounts);
		},
	});

	dialog.show();
}

function gke_make_release_bank_entry(frm, employees, release_amounts) {
	frappe.call({
		method: "run_doc_method",
		args: {
			method: "make_bank_entry",
			dt: "Payroll Entry",
			dn: frm.doc.name,
			args: {
				for_withheld_salaries: 1,
				employees: employees,
				release_amounts: release_amounts,
			},
		},
		freeze: true,
		freeze_message: __("Creating Release Journal Entry..."),
		callback() {
			frappe.set_route("List", "Journal Entry", {
				"Journal Entry Account.reference_name": frm.doc.name,
			});
		},
	});
}
