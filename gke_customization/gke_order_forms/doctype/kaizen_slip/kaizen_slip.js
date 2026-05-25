frappe.ui.form.on("Kaizen Slip", {
    refresh(frm) {
        if (frm.is_new()) return;

        frm.add_custom_button(__("Print Kaizen Slips"), function () {
            const count = parseInt(frm.doc.no_of_page || 0, 10);

            if (count <= 0) {
                frappe.throw(__("Please enter No of Page"));
            }

            const names = JSON.stringify([frm.doc.name]);
            const options = JSON.stringify({
                "page-size": "A4"
            });

            const url = frappe.urllib.get_full_url(
                "/api/method/frappe.utils.print_format.download_multi_pdf"
                + "?doctype=" + encodeURIComponent("Kaizen Slip")
                + "&name=" + encodeURIComponent(names)
                + "&format=" + encodeURIComponent("Kaizen Slip Print")
                + "&no_letterhead=0"
                + "&letterhead=" + encodeURIComponent("Sadguru Diamond")
                + "&options=" + encodeURIComponent(options)
            );

            window.open(url, "_blank");
        }, __("Actions"));
    }
});