// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt


frappe.query_reports["Batch dashboard"] = {
    filters: [
        {
            fieldname: "order_no",
            label: __("Order No"),
            fieldtype: "Data",
        },
        {
            fieldname: "to_department",
            label: __("To Department"),
            fieldtype: "Link",
            options: "Department",
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: [
                "",
                "Department Stock",
                "Department Issue",
                "Employee Issue",
                "Customer Issue",
            ].join("\n"),
        },
        {
            fieldname: "priority",
            label: __("Priority"),
            fieldtype: "Select",
            options: ["", "NORMAL", "PRIORITY:1"].join("\n"),
        },
        {
            fieldname: "from_due_date",
            label: __("Due Date From"),
            fieldtype: "Date",
        },
        {
            fieldname: "to_due_date",
            label: __("Due Date To"),
            fieldtype: "Date",
        },
    ],

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "batch_no" && data && data.batch_no) {
            value = `
                <a href="#" onclick="return false;" class="batch-detail-icon" data-batch="${data.batch_no}" title="${__("Batch Detail")}">
                    <i class="fa fa-search-plus" style="margin-right:6px;"></i>
                </a>
                <a href="#" onclick="return false;" class="batch-history-icon" data-batch="${data.batch_no}" title="${__("Batch History")}">
                    <i class="fa fa-history" style="margin-right:6px;"></i>
                </a>
                ${value}
            `;
        }

        return value;
    },

    onload: function (report) {
        report.page.main.on("click", ".batch-detail-icon", function () {
            show_batch_detail_dialog($(this).data("batch"));
        });

        report.page.main.on("click", ".batch-history-icon", function () {
            show_batch_history_dialog($(this).data("batch"));
        });
    },
};

function show_batch_detail_dialog(batch_no) {
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Batch Detail",
            filters: { parent: batch_no },
            fields: ["type", "shape", "purity", "size", "code", "weight", "pcs"],
            parent: "Batch",
            limit_page_length: 0,
        },
        callback: function (r) {
            const rows = r.message || [];
            const total_weight = rows.reduce((sum, d) => sum + (flt(d.weight) || 0), 0);
            const total_pcs = rows.reduce((sum, d) => sum + (flt(d.pcs) || 0), 0);

            let html = `
                <table class="table table-bordered">
                    <thead><tr>
                        <th>${__("Type")}</th><th>${__("Shape")}</th><th>${__("Purity")}</th>
                        <th>${__("Size")}</th><th>${__("Code")}</th>
                        <th>${__("Weight")}</th><th>${__("Pcs")}</th>
                    </tr></thead>
                    <tbody>`;

            rows.forEach((d) => {
                html += `<tr>
                    <td>${d.type || ""}</td><td>${d.shape || ""}</td><td>${d.purity || ""}</td>
                    <td>${d.size || ""}</td><td>${d.code || ""}</td>
                    <td class="text-right">${flt(d.weight).toFixed(3)}</td>
                    <td class="text-right">${d.pcs || 0}</td>
                </tr>`;
            });

            html += `</tbody>
                <tfoot><tr>
                    <th colspan="5" class="text-right">${__("Total")}</th>
                    <th class="text-right">${total_weight.toFixed(3)}</th>
                    <th class="text-right">${total_pcs}</th>
                </tr></tfoot>
                </table>`;

            new frappe.ui.Dialog({
                title: __("Batch Detail") + " - " + batch_no,
                size: "large",
                fields: [{ fieldtype: "HTML", options: html }],
            }).show();
        },
    });

    function flt(v) {
        return frappe.utils ? frappe.utils.flt(v) : parseFloat(v) || 0;
    }
}

function show_batch_history_dialog(batch_no) {
    frappe.call({
        method: "gke_customization.gke_catalog.report.batch_dashboard.batch_dashboard.get_batch_history",
        args: {
            batch_no: batch_no,
        },
        callback: function (r) {
            const rows = r.message || [];
            let html = `
                <table class="table table-bordered">
                    <thead>
                        <tr>
                            <th>${__("Batch No")}</th>
                            <th>${__("From Department")}</th>
                            <th>${__("To Department")}</th>
                            <th>${__("Receive Date")}</th>
                            <th>${__("Receive Time")}</th>
                            <th>${__("Employee Name")}</th>
                            <th>${__("Current Operation")}</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            if (!rows.length) {
                html += `
                    <tr>
                        <td colspan="7" class="text-center text-muted">${__("No history found")}</td>
                    </tr>
                `;
            } else {
                rows.forEach((d) => {
                    html += `
                        <tr>
                            <td>${d.batch_no || ""}</td>
                            <td>${d.from_department || ""}</td>
                            <td>${d.to_department || ""}</td>
                            <td>${d.receive_date || ""}</td>
                            <td>${d.receive_time || ""}</td>
                            <td>${d.employee_name || ""}</td>
                            <td>${d.current_operation || ""}</td>
                        </tr>
                    `;
                });
            }

            html += `</tbody></table>`;

            new frappe.ui.Dialog({
                title: __("Batch History") + " - " + batch_no,
                size: "extra-large",
                fields: [{ fieldtype: "HTML", options: html }],
            }).show();
        },
    });
}