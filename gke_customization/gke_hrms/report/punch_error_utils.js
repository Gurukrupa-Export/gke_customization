// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

function get_selected_punch_error_row(report) {
	let checked_box = document.querySelector('.dt-cell input[type="checkbox"]:checked');
	if (!checked_box) {
		frappe.msgprint(__("Please select at least one row."));
		return null;
	}

	let selected_cell = checked_box.closest(".dt-cell");
	if (!selected_cell) {
		frappe.msgprint(__("Unable to identify the selected row."));
		return null;
	}

	let row_index = selected_cell.getAttribute("data-row-index");
	if (row_index === null) {
		frappe.msgprint(__("Could not fetch the selected row's index."));
		return null;
	}

	let row = report.data[row_index];
	if (!row) {
		frappe.msgprint(__("Unable to fetch data for the selected row."));
		return null;
	}
	return row;
}

function add_mark_attendance_button(report) {
	report.page
		.add_inner_button(__("Mark as Attendance"), function () {
			let row = get_selected_punch_error_row(report);
			if (!row) {
				return;
			}
			frappe.new_doc("Manual Punch Entry", {
				date: row.attendance_date,
				error_date: row.attendance_date,
				employee: row.employee,
			});
		})
		.addClass("btn-second");
}

function enable_single_row_selection() {
	document.addEventListener("change", function (event) {
		if (!event.target.matches('.dt-cell input[type="checkbox"]')) {
			return;
		}
		document.querySelectorAll('.dt-cell input[type="checkbox"]').forEach((checkbox) => {
			if (checkbox !== event.target) {
				checkbox.checked = false;
			}
		});
	});
}

function get_punch_error_datatable_options(options) {
	return Object.assign(options, {
		checkboxColumn: true,
	});
}
