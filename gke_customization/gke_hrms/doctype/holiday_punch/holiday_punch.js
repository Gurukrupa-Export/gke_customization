frappe.ui.form.on("Holiday Punch", {
	shift_name(frm){
		frappe.db.get_value("Shift Type",frm.doc.shift_name, ["start_time","end_time"], (r) => {
            frm.set_value("start_time",r.start_time)
            frm.set_value("end_time",r.end_time)
        })
	},
    search: function(frm) {
		frm.call({
			method: "search_checkin",
			doc: frm.doc,
			callback: function(r) {
                for (let i = 0; i < r.message.length; i++) {
                    var checkins = r.message[i]
                    $.each(checkins || [], function(i,d) {
                        if (!d.source) {
                            d.source = "Employee Checkin"
                        }
                        d.type = i%2==0 ? "IN":"OUT"
                        frm.add_child("details", d)
                    })
                  }
				frm.refresh_field("details")
			}
		})
	},
    add_new_punch(frm) {
		frappe.call({
			method: 'gke_customization.gke_hrms.doctype.holiday_punch.holiday_punch.add_checkins',
			args: {
				'details': frm.doc.details,
				'date': frm.doc.date,
				'start_time':frm.doc.start_time,
				'end_time':frm.doc.end_time,
			},
			callback: function(r) {
				if (!r.exc) {
					frm.clear_table('details');
					var arrayLength = r.message.length;
					for (var i = 0; i < arrayLength; i++) {
						let row = frm.add_child('details', {
							date: r.message[i]['date'],
							type:r.message[i]['type'],
							employee: r.message[i]['employee'],
							time:r.message[i]['time'],
							employee_checkin: r.message[i]['employee_checkin'],
							source: r.message[i]['source'],
						});
					}
					frm.refresh_field('details');
				}
			}
		});
			// frappe.run_serially([
			// 	// ()=>frm.call("validate_punch"),
			// 	()=>add_punch(frm),
			// 	()=>frm.refresh_field("details")
			// ])
            // console.log('IF')
		// frm.refresh_field("details")
	},
});


// function add_punch(frm) {
// 	const dateField = frm.doc.date;
// 	const timeField = frm.doc.end_time;
// 	const [year, month, day] = dateField.split('-');
// 	const [hour, minute, second] = timeField.split(':');
// 	const dateTime = new Date(year, month - 1, day, hour, minute, second);
// 	const addLeadingZero = num => num < 10 ? '0' + num : num;
// 	const formattedDateTime = `${addLeadingZero(dateTime.getFullYear())}-${addLeadingZero(dateTime.getMonth() + 1)}-${addLeadingZero(dateTime.getDate())} ${addLeadingZero(dateTime.getHours())}:${addLeadingZero(dateTime.getMinutes())}:${addLeadingZero(dateTime.getSeconds())}`;

// 	let new_punches = [];

// 	if (frm.doc.details.length % 2 == 0) {
// 		new_punches.push({
// 			"date": frm.doc.date,
// 			"time": cur_frm.doc.details[1].time,
// 			"source": frm.doc.for_od ? "Outdoor Duty" : "Manual Punch"
// 		});
// 		new_punches.push({
// 			"date": frm.doc.date,
// 			"time": formattedDateTime,
// 			"source": frm.doc.for_od ? "Outdoor Duty" : "Manual Punch"
// 		});
// 	} else {
// 		new_punches.push({
// 			"date": frm.doc.date,
// 			"time": formattedDateTime,
// 			"source": frm.doc.for_od ? "Outdoor Duty" : "Manual Punch"
// 		});
// 	}
	
// 	// new_punches.push({
// 	// 	"date": frm.doc.date,
// 	// 	"time": time,
// 	// 	"source": frm.doc.for_od ? "Outdoor Duty" : "Manual Punch"
// 	// });

// 	var checkins = frm.doc.details || [];
// 	new_punches.forEach(punch => {
// 		checkins.push(punch);
// 	});
// 	checkins.sort((a, b) => moment(a.time).diff(b.time, 'second'));

// 	frm.doc.details = [];
// 	$.each(checkins || [], function(i, d) {
// 		d.type = i % 2 == 0 ? "IN" : "OUT";
// 		frm.add_child("details", d);
// 	});

// }