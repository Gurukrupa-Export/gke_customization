// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Code Creation Tool", {
// 	refresh(frm) {
//         frm.disable_save();

// 		frm.get_field("file_to_upload").df.options = {
// 			restrictions: {
// 				allowed_file_types: [".csv"],
// 			},
// 		};
//         if (!frm.doc.file_to_upload) {
// 			frm.get_field("code_creation_log").$wrapper.html("");
// 		}
//         frm.page.set_primary_action(__("Update"), function () {
// 			frm.get_field("code_creation_log").$wrapper.html("<p>Updating...</p>");
			
// 			frappe.call({
// 				method: "gke_customization.gke_order_forms.doctype.code_creation_tool.code_creation_tool.upload",
// 				args: {
// 					select_doctype: frm.doc.select_doctype,
// 				},
// 				callback: function (r) {
// 					if (r.message) {
// 						let data = r.message;

// 						if (Array.isArray(data) && data.length > 0) {
// 							let html = "<table class='table table-bordered'>";
// 							html += "<thead><tr>";

// 							let headers = data[0];
// 							headers.forEach(header => {
// 								html += `<th>${header}</th>`;
// 							});
// 							html += "</tr></thead><tbody>";

// 							for (let i = 1; i < data.length; i++) {
// 								html += "<tr>";
// 								data[i].forEach(value => {
// 									html += `<td>${value || ""}</td>`; 
// 								});
// 								html += "</tr>";
// 							}
// 							html += "</tbody></table>";

// 							frm.get_field("code_creation_log").$wrapper.html(html);
// 						} else {
// 							frm.get_field("code_creation_log").$wrapper.html("<p>No data available.</p>");
// 						}
// 					} else {
// 						frm.get_field("code_creation_log").$wrapper.html("<p>Error occurred while fetching data.</p>");
// 					}
// 				},
// 			});
// 		});
// 	},
// }); 

frappe.ui.form.on("Code Creation Tool", {
    refresh(frm) {
        frm.disable_save();

        frm.get_field("file_to_upload").df.options = {
            restrictions: {
                allowed_file_types: [".csv"],
            },
        }; 

        if (!frm.doc.file_to_upload) {
            frm.get_field("code_creation_log").$wrapper.html("");
        }

        frm.page.set_primary_action(__("Update"), function () {
            frm.get_field("code_creation_log").$wrapper.html("<p>Updating...</p>");

            frappe.call({
                method: "gke_customization.gke_order_forms.doctype.code_creation_tool.code_creation_tool.upload",
                args: {
                    select_doctype: frm.doc.select_doctype,
                },
                callback: function (r) {
                    if (r.message) {
                        let data = r.message;

                        if (Array.isArray(data) && data.length > 0) {
                            let html = "<table class='table table-bordered'>";
                            html += "<thead><tr>";

                            let headers = data[0];
                            headers.forEach(header => {
                                html += `<th>${header}</th>`;
                            });
                            html += "</tr></thead><tbody>";

                            for (let i = 1; i < data.length; i++) {
                                html += "<tr>";
                                data[i].forEach(value => {
                                    html += `<td>${value || ""}</td>`;
                                });
                                html += "</tr>";
                            }
                            html += "</tbody></table>";

                            frm.get_field("code_creation_log").$wrapper.html(html);
                        } else {
                            frm.get_field("code_creation_log").$wrapper.html("<p>No data available.</p>");
                        }
                    } else {
                        frm.get_field("code_creation_log").$wrapper.html("<p>Error occurred while fetching data.</p>");
                    }
                },
            });
        });

		
    },

    onload(frm) {
        // Clear file attachment when the form is loaded
        frappe.model.set_value(frm.doctype, frm.docname, "file_to_upload", "");
    },
    download_template(frm){
        window.location.href = repl(
			frappe.request.url + "?cmd=%(cmd)s&doctype=%(select_doctype)s",
			{
				cmd: "gke_customization.gke_order_forms.doctype.code_creation_tool.code_creation_tool.get_template",
				doctype: frm.doc.select_doctype
			},
		);
    }
});
