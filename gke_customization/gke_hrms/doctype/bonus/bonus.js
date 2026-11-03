// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bonus', {
    refresh(frm) {
        if (frm.doc.workflow_state === "On Hold") {
            frm.add_custom_button(__('Release Hold Bonus'), function() {
                show_release_dialog(frm);
            });
        }
        frm.set_query("department", function() {
            return {
                filters: { company: frm.doc.company }
            };
        });
    },
    from_date(frm){
        validate_date(frm)
        get_months(frm)
        setTimeout(() => {
            let result = get_months(frm);
            if (!result) return;
            let excluded_months = result.excluded;
            const table = frm.fields_dict['bonus_details'];
            if (!table || !table.grid) return;
            excluded_months.forEach(month => {
                let bounsfield = month.toLowerCase() + '_bonus';
                let salaryfield =  month.toLowerCase() + '_salary'
                
                table.grid.update_docfield_property(bounsfield,'hidden',1);
                table.grid.update_docfield_property(salaryfield,'hidden',1);
            });
            frm.refresh_field('bonus_details');
        }, 1000);
    },
    to_date(frm){
        validate_date(frm)
        get_months(frm)
        setTimeout(() => {
            let result = get_months(frm);
            if (!result) return;
            let excluded_months = result.excluded;
            const table = frm.fields_dict['bonus_details'];
            if (!table || !table.grid) return;
            excluded_months.forEach(month => {
                let bounsfield = month.toLowerCase() + '_bonus';
                let salaryfield =  month.toLowerCase() + '_salary'

                table.grid.update_docfield_property(bounsfield,'hidden',1);
                table.grid.update_docfield_property(salaryfield,'hidden',1);
            });
            frm.refresh_field('bonus_details');
        }, 1000);
    },
    bonus_percent(frm){
        if((frm.doc.bonus_percent > 20) || (frm.doc.bonus_percent < 8.33)){
            frappe.throw("Please Enter Bonus Percent Between 8.33% to 20%")
        }
    },
    validate(frm) {
        calculate_totals(frm);
    },
    search(frm) {
        check_overlap(frm)
        if (!frm.doc.from_date || !frm.doc.to_date) {
            frappe.msgprint("Please select From Date and To Date");
            return;
        }

        let filters = {};
        let or_filters = [
            ["Employee", "status", "=", "Active"],
            ["Employee", "relieving_date", "between", [frm.doc.from_date, frm.doc.to_date]]
        ];

        if (frm.doc.employee) {
            filters.name = frm.doc.employee;
        }
        else if (frm.doc.department) {
            filters.department = frm.doc.department;
            filters.company = frm.doc.company;
        }
        else if (frm.doc.branch) {
            filters.branch = frm.doc.branch;
            filters.company = frm.doc.company;
        }
        else if (frm.doc.company) {
            filters.company = frm.doc.company;
        }
        else {
            frappe.msgprint("Please select Employee, Department, or Company");
            return;
        }

        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Employee",
                filters: filters,
                or_filters: or_filters,
                fields: [
                    "name","branch",
                    "employee_name","department",
                    "designation","company",
                    "status","relieving_date"
                ],
                limit_page_length: 1000
            },
            callback: function (res) {
                if (!res.message || !res.message.length) {
                    frappe.msgprint("No employees found");
                    return;
                }
                frm.clear_table("bonus_details");
                res.message.forEach(emp => {
                    let row = frm.add_child("bonus_details");
                    row.employee = emp.name;
                    row.branch = emp.branch;
                    row.employee_name = emp.employee_name;
                    row.department = emp.department;
                    row.designation = emp.designation;
                    row.company = emp.company;
                    row.employee_status  = emp.status;
                    calculate_bonus(frm, row.doctype, row.name);
                });
                frm.refresh_field("bonus_details");
            }
        });
    }
})

frappe.ui.form.on('Bonus Details', {
    refresh(frm,cdt,cdn) {
    },
    employee(frm, cdt, cdn) {
        calculate_bonus(frm, cdt, cdn);
    },
    bonus_details_remove(frm) {
        calculate_totals(frm);
    }
})

function calculate_totals(frm) {
    let rows = frm.doc.bonus_details || [];
    let total_employee = 0;
    let total_bonus = 0;

    rows.forEach(row => {
        if (row.employee) total_employee += 1;
        total_bonus += flt(row.total_bonus);
    });

    frm.set_value("total_employee_count", total_employee);
    frm.set_value("totalbonus_amt", total_bonus);
}

function calculate_bonus(frm, cdt, cdn) {

    let row = locals[cdt][cdn];
    let total_salary = 0;
    let total_bonus = 0;

    frappe.call({
        method: "gke_customization.gke_hrms.doctype.bonus.bonus.employee_salary",
        args: {
            employee: row.employee,
            from_date: frm.doc.from_date,
            to_date: frm.doc.to_date,
            wage_eligibility_limit: frm.doc.wage_eligibility_limit
        },
        callback: function (r) {
            // reset fields first (important when recalculating)
            total_salary = 0;
            total_bonus = 0;

            if (r.message && r.message.length) {

                r.message.forEach(item => {
                    if (!item.start_date) return;

                    let month = get_month_from_date(item.start_date);
                    let salary_field = month.toLowerCase() + '_salary';
                    let bonus_field = month.toLowerCase() + '_bonus';

                    let salary = flt(item.amount);
                    let bonus = Math.round(salary * frm.doc.bonus_percent / 100);

                    total_salary += salary;
                    total_bonus += bonus;

                    frappe.model.set_value(cdt, cdn, salary_field, salary);
                    frappe.model.set_value(cdt, cdn, bonus_field, bonus);
                });
            }

            // set totals
            frappe.model.set_value(cdt, cdn, "total_salary", total_salary);
            frappe.model.set_value(cdt, cdn, "total_bonus", total_bonus);

            if (!total_salary || total_salary === 0) {
                // IMPORTANT: delay so frappe finishes setting values
                setTimeout(() => {
                    let table = frm.doc.bonus_details || [];
                    for (let i = table.length - 1; i >= 0; i--) {
                        if (table[i].name === cdn) {
                            table.splice(i, 1);
                            break;
                        }
                    }
                    frm.refresh_field("bonus_details");
                    calculate_totals(frm);
                }, 200);
            }
        }
    });
}

function run_overlap(frm){
    if(!frm.doc.from_date || !frm.doc.to_date || !frm.doc.bonus_details?.length)
        return;

    let emp_list = frm.doc.bonus_details.map(d => d.employee);

    frappe.call({
        method: "gke_customization.gke_hrms.doctype.bonus.bonus.check_bonus_overlap",
        args: {
            from_date: frm.doc.from_date,
            to_date: frm.doc.to_date,
            name: frm.doc.name || null,
            employees: emp_list
        },
        freeze: false,
        callback: function(r){
            if(!r.message || !r.message.length) return;

            let remove_set = new Set(r.message);
            let removed = [];

            // IMPORTANT: clone array before modifying
            let rows = [...frm.doc.bonus_details];

            rows.forEach(row => {
                if(remove_set.has(row.employee)){
                    removed.push(row.employee);
                    frappe.model.clear_doc(row.doctype, row.name);
                }
            });

            frm.refresh_field("bonus_details");
            calculate_totals(frm);

            frappe.msgprint({
                title: "Employees Removed",
                indicator: "red",
                message: `These employees already have Bonus:<br><br>${removed.join("<br>")}`
            });
        }

    });
}

function validate_date(frm){
    if(frm.doc.from_date > frm.doc.to_date){
        frappe.throw(
        "From Date  can not be Greater than To Date "
        )
    }
}

function get_month_from_date(date_str) {
    if (!date_str) return null;

    let date = frappe.datetime.str_to_obj(date_str);
    let monthNames = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ];

    return monthNames[date.getMonth()];
}

function get_months(frm) {
    if (!frm.doc.from_date || !frm.doc.to_date) return { included: [], excluded: [] };

    let start = frappe.datetime.str_to_obj(frm.doc.from_date);
    let end = frappe.datetime.str_to_obj(frm.doc.to_date);

    let included_months = [];
    let excluded_months = [];

    let monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

    let current = new Date(start.getFullYear(), start.getMonth(), 1);

    while (current <= end) {
        included_months.push(monthNames[current.getMonth()]);
        current.setMonth(current.getMonth() + 1);
    }

    monthNames.forEach(month => {
        if (!included_months.includes(month)) {
            excluded_months.push(month);
        }
    });
    return {
        included: included_months,
        excluded: excluded_months
    };
}

let overlap_timer = null;

function check_overlap(frm){
    if(overlap_timer){
        clearTimeout(overlap_timer);
    }
    overlap_timer = setTimeout(() => {
        run_overlap(frm);
    }, 1000);   // wait 600ms after last change
}

function show_release_dialog(frm) {
    let hold_rows = frm.doc.bonus_details
        .filter(row => row.hold_bonus == 1)
        .map(row => {
            return {
                employee: row.employee,
                total_bonus: row.total_bonus,
                original_name: row.name
            };
        });

    if (!hold_rows.length) {
        frappe.msgprint(__('No Hold Bonus Found'));
        return;
    }

    let dialog = new frappe.ui.Dialog({
        title: 'Release Hold Bonus',
        size: 'large',
        fields: [
            {
                fieldtype: 'Table',
                fieldname: 'hold_bonus_table',
                label: 'Hold Bonus Employees',
                cannot_add_rows: true,
                in_place_edit: false,
                data: hold_rows,
                fields: [
                    {
                        fieldtype: 'Data',
                        fieldname: 'employee',
                        label: 'Employee',
                        in_list_view: 1,
                        read_only: 1
                    },
                    {
                        fieldtype: 'Currency',
                        fieldname: 'total_bonus',
                        label: 'Total Bonus',
                        in_list_view: 1,
                        read_only: 1
                    }
                ]
            }
        ],

        primary_action_label: 'Release Selected',

        primary_action() {
            let selected_rows = dialog.fields_dict.hold_bonus_table.grid.get_selected_children();
            if (!selected_rows.length) {
                frappe.msgprint(__('Please select at least one employee'));
                return;
            }
            let row_names = selected_rows.map(row => row.original_name);
            console.log(row_names)
            frappe.call({
                method: "gke_customization.gke_hrms.doctype.bonus.bonus.release_hold_bonus",
                args: {
                    docname: frm.doc.name,
                    row_names: row_names
                },
                callback: function(r) {
                    if (!r.exc) {
                        frm.reload_doc();
                        dialog.hide();
                        frappe.msgprint(__('Selected Hold Bonuses Released Successfully'));
                    }
                }
            });
        }
    });
    dialog.show();
}
