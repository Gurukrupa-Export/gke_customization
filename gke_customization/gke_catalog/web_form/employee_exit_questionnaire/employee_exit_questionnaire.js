frappe.ready(function() {
	frappe.web_form.on('employee', (field,value) => {
		frappe.call({
			method: 'gke_customization.gke_catalog.web_form.employee_exit_questionnaire.employee_exit_questionnaire.get_context',
			args: {
				'employee':value
			},
			callback: (data) => {
				if(data.message){
					// console.log(data.message)
					frappe.web_form.set_value(['employee_name'], [data.message[0]['employee_name']])
					frappe.web_form.set_value(['department'], [data.message[0]['department']])
					frappe.web_form.set_value(['designation'], [data.message[0]['designation']])
					frappe.web_form.set_value(['date_of_joining'], [data.message[0]['date_of_joining']])
					if(data.message[0]['relieving_date'] ){
						frappe.web_form.set_value(['relieving_date'], [data.message[0]['relieving_date']]);

						let date_of_joining = moment(data.message[0]['date_of_joining']);
						let relieving_date = moment(data.message[0]['relieving_date']);
						let diff_years = relieving_date.diff(date_of_joining, 'years', true); 
						
						frappe.web_form.set_value('total_length_of_service', diff_years.toFixed(2)); 
					}
				}
			},
		});
	});
});