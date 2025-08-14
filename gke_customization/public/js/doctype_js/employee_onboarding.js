
frappe.ui.form.on("Employee Onboarding", {
    refresh: function (frm) {
        if (!frm.doc.employee && frm.doc.docstatus === 1) {
            setTimeout(()=>{
                frm.remove_custom_button("Employee", "Create")
                frm.add_custom_button(
                    __("Employee Update"),
                    function () {
                        frappe.model.open_mapped_doc({
                            method: "gke_customization.gke_hrms.doc_events.employee_onboarding.employee_update",
                            frm: frm,
                        });
                    },
                    __("Create")
                );
                frm.page.set_inner_btn_group_as_primary(__("Create"));
            }, 100)
            
            
        }
    },
});