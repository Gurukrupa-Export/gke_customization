// frappe.listview_settings['Parent Manufacturing Order'] = {
//     onload: function (listview) {
//         listview.page.add_menu_item('Generate PDFs', () => {
//             frappe.call({
//                 method: "frappe.client.get_list",
//                 args: {
//                     doctype: "Print Format",
//                     fields: ["name"],
//                     filters: { doc_type: "Parent Manufacturing Order" }
//                 },
//                 callback: function (response) {
//                     const print_formats = response.message.map(format => ({
//                         label: format.name,
//                         value: format.name
//                     }));

//                     new frappe.ui.Dialog({
//                         title: 'Generate PDFs',
//                         fields: [
//                             {
//                                 fieldname: 'print_format',
//                                 label: 'Print Format',
//                                 fieldtype: 'Select',
//                                 options: print_formats,
//                                 reqd: 1
//                             }
//                         ],
//                         primary_action_label: 'Generate',
//                         primary_action: (values) => {
//                             const selected_docs = listview.get_checked_items();
//                             if (selected_docs.length === 0) {
//                                 frappe.msgprint(__('Please select at least one document.'));
//                                 return;
//                             }

//                             const docnames = selected_docs.map(doc => doc.name);

//                             frappe.call({
//                                 method: 'jewellery_erpnext.jewellery_erpnext.doctype.parent_manufacturing_order.parent_manufacturing_order.generate_pdfs',
//                                 args: {
//                                     docnames: docnames,
//                                     print_format: values.print_format
//                                 },
//                                 callback: function (response) {
//                                     // After generating the PDFs, open them in a new tab for printing
//                                     if (response.message && response.message.length > 0) {
//                                         frappe.msgprint('PDF generation completed. PDFs are now open for viewing.');
//                                     } else {
//                                         frappe.msgprint('No PDFs were generated.');
//                                     }
//                                 },
//                             });
//                         },
//                     }).show();
//                 }
//             });
//         });
//     },
// };

// frappe.listview_settings['Parent Manufacturing Order'] = {
//     onload: function (listview) {
//         listview.page.add_menu_item('Generate PDFs', () => {
//             frappe.call({
//                 method: "frappe.client.get_list",
//                 args: {
//                     doctype: "Print Format",
//                     fields: ["name"],
//                     filters: { doc_type: "Parent Manufacturing Order" }
//                 },
//                 callback: function (response) {
//                     const print_formats = response.message.map(format => ({
//                         label: format.name,
//                         value: format.name
//                     }));

//                     new frappe.ui.Dialog({
//                         title: 'Generate PDFs',
//                         fields: [
//                             {
//                                 fieldname: 'print_format',
//                                 label: 'Print Format',
//                                 fieldtype: 'Select',
//                                 options: print_formats,
//                                 reqd: 1
//                             }
//                         ],
//                         primary_action_label: 'Generate',
//                         primary_action: (values) => {
//                             const selected_docs = listview.get_checked_items();
//                             if (selected_docs.length === 0) {
//                                 frappe.msgprint(__('Please select at least one document.'));
//                                 return;
//                             }

//                             const docnames = selected_docs.map(doc => doc.name);

//                             frappe.call({
//                                 method: 'jewellery_erpnext.jewellery_erpnext.doctype.parent_manufacturing_order.parent_manufacturing_order.generate_pdfs',
//                                 args: {
//                                     docnames: docnames,
//                                     print_format: values.print_format
//                                 },
//                                 callback: function (response) {
//                                     if (response.message) {
//                                         // Assuming response.message is the URL or base64 data of the PDF file(s)
//                                         response.message.forEach(pdf_url => {
//                                             const link = document.createElement('a');
//                                             link.href = pdf_url; // This should be the direct link to the generated PDF
//                                             link.download = pdf_url.split('/').pop(); // Extract file name from URL
//                                             document.body.appendChild(link);
//                                             link.click();
//                                             document.body.removeChild(link);
//                                         });

//                                         frappe.msgprint('PDF generation completed. Files have been downloaded.');
//                                     } else {
//                                         frappe.msgprint('No PDFs were generated.');
//                                     }
//                                 },
//                             });
//                         },
//                     }).show();
//                 }
//             });
//         });
//     },
// };




