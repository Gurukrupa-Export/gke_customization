// Copyright (c) 2024, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.ui.form.on("Old BOM", {
	// old_stylebio(frm) {
    //     if (frm.doc.old_stylebio){
    //         frm.set_value('old_bom_metal_details', []);
    //         frm.refresh_field('old_bom_metal_details');
    //         frappe.call({
    //             method: 'gke_customization.gke_order_forms.doctype.old_bom.old_bom.get_details',
    //             args: {
    //                 'old_stylebio': frm.doc.old_stylebio,
    //             },
    //             callback: function(r) {
    //                 if (!r.exc) {
    //                     for (var i = 0; i < r.message[0].length; i++) {
    //                         console.log(r.message[0])
    //                         let row = frm.add_child('old_bom_metal_details', {
    //                             old_stylebio: r.message[0][i]['stylebio'],
    //                             tag_no: r.message[0][i]['tagno'],
    
    //                             // metal details
    //                             metal_touch: r.message[0][i]['metal_touch'],
    //                             metal_purity: r.message[0][i]['metal_purity'].toFixed(1),
    //                             metal_colour: r.message[0][i]['metal_colour'],
    //                             metal_weight: r.message[0][i]['metal_weight'],
    //                         });
    //                         frm.refresh_field('old_bom_metal_details');
                           
    //                     };
    //                     for (var i = 0; i < r.message[1].length; i++) {
    //                         let row = frm.add_child('old_bom_diamond_details', {
    
    //                             old_stylebio: r.message[1][i]['stylebio'],
    //                             tag_no: r.message[1][i]['tagno'],
    
    //                             // diamond details
    //                             diamond_shape: r.message[1][i]['diamond_shape'],
    //                             diamond_sieve_size: r.message[1][i]['diamond_sieve_size'],
    //                             diamond_pcs: r.message[1][i]['diamond_pcs'],
    //                             diamond_weight: r.message[1][i]['diamond_weight'],
    
    //                         });
    //                         frm.refresh_field('old_bom_diamond_details');
                           
    //                     };
    //                     for (var i = 0; i < r.message[2].length; i++) {
    //                         let row = frm.add_child('old_bom_gemstone_details', {
    
    //                             old_stylebio: r.message[2][i]['stylebio'],
    //                             tag_no: r.message[2][i]['tagno'],
    
    //                             // gemstone details
    //                             gemstone_type: r.message[2][i]['gemstone_type'],
    //                             cut_or_cab: r.message[2][i]['cut_or_cab'],
    //                             gemstone_shape: r.message[2][i]['gemstone_shape'],
    
    //                             gemstone_quality: r.message[2][i]['gemstone_quality'],
    //                             gemstone_grade: r.message[2][i]['gemstone_grade'],
    //                             total_gemstone_rate: r.message[2][i]['total_gemstone_rate'],
    
    //                             gemstone_size: r.message[2][i]['gemstone_size'],
    //                             gemstone_pcs: r.message[2][i]['gemstone_pcs'],
    //                             gemstone_weight: r.message[2][i]['gemstone_weight'],
    //                             per_pcs_per_carat: r.message[2][i]['per_pcs_per_carat'],
    
    //                         });
    //                         frm.refresh_field('old_bom_gemstone_details');
                           
    //                     }
    //                     // frm.save();

    //                 }
    //             }
    //         });
    //     }
    //     else{
    //         frm.set_value('old_bom_metal_details', []);
    //         frm.refresh_field('old_bom_metal_details');

    //         frm.set_value('old_bom_diamond_details', []);
    //         frm.refresh_field('old_bom_diamond_details');

    //         frm.set_value('old_bom_gemstone_details', []);
    //         frm.refresh_field('old_bom_gemstone_details');
    //     }
	// },
});



    
