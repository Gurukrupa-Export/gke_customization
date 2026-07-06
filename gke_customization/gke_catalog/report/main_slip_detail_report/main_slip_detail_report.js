frappe.query_reports["Main Slip Detail Report"] = {
    "filters": [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date"
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date"
        },
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            on_change: function(report) {
                report.set_filter_value("branch", "");
                report.set_filter_value("department", "");
                report.set_filter_value("manager", "");
                report.set_filter_value("employee", "");
                report.refresh();
            }
        },
        {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "Link",
            options: "Branch",
            get_query: function() {
                let company = frappe.query_report.get_filter_value("company");
                let filters = {};
                if (company) filters.company = company;
                return { filters: filters };
            },
            on_change: function(report) {
                report.set_filter_value("department", "");
                report.set_filter_value("manager", "");
                report.set_filter_value("employee", "");
                report.refresh();
            }
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department",
            get_query: function() {
                let company = frappe.query_report.get_filter_value("company");
                let branch = frappe.query_report.get_filter_value("branch");
                let filters = {};
                if (company) filters.company = company;
                if (branch) filters.branch = branch;
                return { filters: filters };
            },
            on_change: function(report) {
                report.set_filter_value("manager", "");
                report.set_filter_value("employee", "");
                report.refresh();
            }
        },
        {
            fieldname: "manager",
            label: __("Manager"),
            fieldtype: "Link",
            options: "Employee",
            get_query: function() {
                let company = frappe.query_report.get_filter_value("company");
                let branch = frappe.query_report.get_filter_value("branch");
                let department = frappe.query_report.get_filter_value("department");

                let filters = {};
                if (company) filters.company = company;
                if (branch) filters.branch = branch;
                if (department) filters.department = department;

                return {
                    filters: filters
                };
            },
            on_change: function(report) {
                report.set_filter_value("employee", "");
                report.refresh();
            }
        },
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee",
            get_query: function() {
                let company = frappe.query_report.get_filter_value("company");
                let branch = frappe.query_report.get_filter_value("branch");
                let department = frappe.query_report.get_filter_value("department");
                let manager = frappe.query_report.get_filter_value("manager");

                let filters = {};
                if (company) filters.company = company;
                if (branch) filters.branch = branch;
                if (department) filters.department = department;
                if (manager) filters.reports_to = manager;

                return {
                    filters: filters
                };
            }
        },
        {
            fieldname: "main_slip_id",
            label: __("Main Slip No"),
            fieldtype: "Link",
            options: "Main Slip"
        },
        {
            fieldname: "manufacturer",
            label: __("Manufacturer"),
            fieldtype: "Link",
            options: "Manufacturer"
        }
    ]
};

function show_main_slip_details(main_slip_no) {
    frappe.call({
        method: "gke_customization.gke_catalog.report.main_slip_detail_report.main_slip_detail_report.get_main_slip_detail_popup",
        args: { main_slip_no: main_slip_no },
        callback: function (r) {
            if (!r.message) return;
            const data = r.message;
            const operations = data.operations_list || [];
            let ops_html = "";

            operations.forEach((op, idx) => {
                ops_html += `
                    <tr>
                        <td>${idx + 1}</td>
                        <td>${op.manufacturing_work_order || ""}</td>
                        <td>${op.manufacturing_operation || ""}</td>
                        <td>${op.model || ""}</td>
                        <td>${op.posting_date || ""}</td>
                        <td>${op.delivery_date || ""}</td>
                        <td>${op.status || ""}</td>
                        <td>${op.company || ""}</td>
                        <td>${op.branch || ""}</td>
                        <td>${op.manufacturer || ""}</td>
                        <td>${op.metal_touch || ""}</td>
                        <td>${op.gross_wt || ""}</td>
                        <td>${op.net_wt || ""}</td>
                    </tr>
                `;
            });

            const d = new frappe.ui.Dialog({
                title: __("Main Slip Details - {0}", [main_slip_no]),
                size: "extra-large",
                fields: [{ fieldtype: "HTML", fieldname: "html" }],
                primary_action_label: __("Close"),
                primary_action() { d.hide(); }
            });

            d.fields_dict.html.$wrapper.html(`
                <div style="padding:10px;">
                    <h5 style="margin: 10px 0;">Manufacturing Work Orders</h5>
                    <table class="table table-bordered">
                        <thead>
                            <tr>
                                <th>No</th>
                                <th>Manufacturing Work Order</th>
                                <th>Manufacturing Operation</th>
                                <th>Model</th>
                                <th>Posting Date</th>
                                <th>Delivery Date</th>
                                <th>Status</th>
                                <th>Company</th>
                                <th>Branch</th>
                                <th>Manufacturer</th>
                                <th>Touch</th>
                                <th>Gross Wt</th>
                                <th>Net Wt</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${ops_html || '<tr><td colspan="13" class="text-center">No Manufacturing Work Orders found</td></tr>'}
                        </tbody>
                    </table>
                </div>
            `);
            d.show();
        }
    });
}