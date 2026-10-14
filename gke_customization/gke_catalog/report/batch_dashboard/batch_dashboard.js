// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt


frappe.query_reports["Batch dashboard"] = {
    filters: [
        {
            fieldname: "sales_order",
            label: __("Sales Order"),
            fieldtype: "Link",
            options: "Sales Order",
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
                "Draft",
                "Not Started",
                "In Process",
                "Completed",
                "Stopped",
                "Closed",
                "Cancelled",
            ].join("\n"),
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
            const $btn = $(this);
            if ($btn.hasClass("disabled")) return;
            $btn.addClass("disabled");
            show_batch_detail_dialog($btn.data("batch"), () => $btn.removeClass("disabled"));
        });

        report.page.main.on("click", ".batch-history-icon", function () {
            const $btn = $(this);
            if ($btn.hasClass("disabled")) return;
            $btn.addClass("disabled");
            show_batch_history_dialog($btn.data("batch"), () => $btn.removeClass("disabled"));
        });
    },
};

function show_batch_detail_dialog(batch_no, on_close) {
    function to_float(v) {
        return typeof flt === "function" ? flt(v) : parseFloat(v) || 0;
    }

    frappe.call({
        method: "gke_customization.gke_catalog.report.batch_dashboard.batch_dashboard.get_batch_detail",
        args: {
            batch_no: batch_no,
        },
        callback: function (r) {
            const rows = r.message || [];
            const total_qty = rows.reduce((sum, d) => sum + (to_float(d.qty) || 0), 0);
            const total_amount = rows.reduce((sum, d) => sum + (to_float(d.amount) || 0), 0);

            let html = `
                <table class="table table-bordered">
                    <thead><tr>
                        <th>${__("Stock Entry")}</th><th>${__("Item Code")}</th><th>${__("Item Name")}</th>
                        <th>${__("Source Warehouse")}</th><th>${__("Target Warehouse")}</th>
                        <th>${__("Batch No")}</th>
                        <th>${__("Qty")}</th><th>${__("UOM")}</th>
                        <th>${__("Rate")}</th><th>${__("Amount")}</th>
                    </tr></thead>
                    <tbody>`;

            if (!rows.length) {
                html += `
                    <tr>
                        <td colspan="10" class="text-center text-muted">${__("No stock entry found")}</td>
                    </tr>
                `;
            } else {
                rows.forEach((d) => {
                    html += `<tr>
                        <td>${d.stock_entry || ""}</td><td>${d.item_code || ""}</td><td>${d.item_name || ""}</td>
                        <td>${d.s_warehouse || ""}</td><td>${d.t_warehouse || ""}</td>
                        <td>${d.batch_no || ""}</td>
                        <td class="text-right">${to_float(d.qty).toFixed(3)}</td><td>${d.uom || ""}</td>
                        <td class="text-right">${to_float(d.basic_rate).toFixed(2)}</td>
                        <td class="text-right">${to_float(d.amount).toFixed(2)}</td>
                    </tr>`;
                });
            }

            html += `</tbody>
                <tfoot><tr>
                    <th colspan="6" class="text-right">${__("Total")}</th>
                    <th class="text-right">${total_qty.toFixed(3)}</th>
                    <th></th><th></th>
                    <th class="text-right">${total_amount.toFixed(2)}</th>
                </tr></tfoot>
                </table>`;

            new frappe.ui.Dialog({
                title: __("Batch Detail") + " - " + batch_no,
                size: "large",
                fields: [{ fieldtype: "HTML", options: html }],
                onhide: on_close,
            }).show();
        },
        error: function () {
            on_close && on_close();
        },
    });
}

function show_batch_history_dialog(batch_no, on_close) {
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
                            <th>${__("Operation")}</th>
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
                onhide: on_close,
            }).show();
        },
        error: function () {
            on_close && on_close();
        },
    });
}