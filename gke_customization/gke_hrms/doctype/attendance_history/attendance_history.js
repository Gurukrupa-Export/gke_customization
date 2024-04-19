// Copyright (c) 2024, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("Attendance History", {
	employee(frm) {
        var employee = cur_frm.doc.employee;
        frappe.db.get_value('Employee',{'name': employee},['date_of_joining','name','scheduled_confirmation_date'],(r) => {
            if(r){
                // console.log(r);
                frm.clear_table('attendance_history');
                    let from_date = frappe.datetime.str_to_obj(r.date_of_joining);
                    let current_date = frappe.datetime.now_date();
                    
                    let temp_date = new Date(from_date);
                    let currentDate = new Date(current_date);
                    for (temp_date; temp_date <= currentDate; temp_date.setFullYear(temp_date.getFullYear() + 1)) {
                        // add one to from_date year 
                        let next_year = temp_date.getFullYear() + 1;

                        // get date from from_date
                        let next_date = new Date(temp_date);
                        next_date.setFullYear(next_year);

                        // subtract date from from_date's date
                        next_date.setDate(next_date.getDate() - 1);

                        let tempDate = frappe.datetime.obj_to_str(temp_date);
                        let nextDate = frappe.datetime.obj_to_str(next_date);
                        // console.log('tempDate', tempDate,'nextDate', nextDate);

                        let row = frm.add_child('attendance_history', {
                            from_date: tempDate,
                            to_date: nextDate,
                        });
                    }

                    // get cuurent date in last row of table
                    frm.doc.attendance_history[frm.doc.attendance_history.length - 1].to_date = frappe.datetime.now_date();

                    frm.refresh_field('attendance_history');
                    calculate_total(frm);
            }                
        });
	},
});

function calculate_total(frm){
	if(frm.doc.attendance_history){
		frm.doc.attendance_history.forEach(function(d){
            let from_date = frappe.datetime.str_to_obj(d.from_date);
            let to_date = frappe.datetime.str_to_obj(d.to_date);
            
            let diffDays = frappe.datetime.get_day_diff(to_date, from_date)    
            diffDays += 1;
            // console.log(diffDays);

            frappe.model.set_value(d.doctype, d.name, 'total_working_days', diffDays);
		})
	}
	
}