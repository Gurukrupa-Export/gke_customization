// Copyright (c) 2026, Your Company and contributors
// For license information, please see license.txt


// Selected values of a (multi-select) filter, always as an array
function ewr_selected(fieldname) {
    const v = frappe.query_report.get_filter_value(fieldname);
    if (Array.isArray(v)) return v;
    return v ? [v] : [];
}


frappe.query_reports["Everyday Work Report"] = {

    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                return frappe.db.get_link_options("Department", txt);
            },
            // Department badalne par neeche ke dependent filters reset ho jaate hain
            on_change: function(report) {
                const cleared = {};
                ["operation", "employee", "manufacturing_work_order"].forEach(function(fn) {
                    const v = report.get_filter_value(fn);
                    if (Array.isArray(v) && v.length) {
                        cleared[fn] = [];
                    }
                });
                if (Object.keys(cleared).length) {
                    report.set_filter_value(cleared);   // sab saath set hote hain, refresh ek baar
                } else {
                    report.refresh();
                }
            }
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                return ["WIP", "Not Issued", "Received"]
                    .filter(s => !txt || s.toLowerCase().includes(txt.toLowerCase()))
                    .map(s => ({ value: s, description: "" }));
            }
        },
        {
            // Sirf selected department(s) ke operations
            fieldname: "operation",
            label: __("Operation"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                const depts = ewr_selected("department");
                const f = [
                    ["Employee IR", "operation", "is", "set"],
                    ["Employee IR", "docstatus", "=", 1],
                ];
                if (depts.length) f.push(["Employee IR", "department", "in", depts]);
                if (txt) f.push(["Employee IR", "operation", "like", `%${txt}%`]);

                return frappe.db.get_list("Employee IR", {
                    fields: ["operation"],
                    filters: f,
                    group_by: "operation",
                    order_by: "operation",
                    limit: 0
                }).then(r => {
                    return r
                        .filter(d => d.operation)
                        .map(d => ({
                            value: d.operation,
                            description: ""
                        }));
                });
            }
        },
        {
            // Sirf selected department(s) me jinko issue hua hai
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                const depts = ewr_selected("department");
                if (!depts.length) {
                    return frappe.db.get_link_options("Employee", txt);
                }

                const f = [
                    ["Employee IR", "employee", "is", "set"],
                    ["Employee IR", "docstatus", "=", 1],
                    ["Employee IR", "department", "in", depts],
                ];
                return frappe.db.get_list("Employee IR", {
                    fields: ["employee"],
                    filters: f,
                    group_by: "employee",
                    limit: 0
                }).then(rows => {
                    const ids = rows.map(r => r.employee).filter(Boolean);
                    if (!ids.length) return [];
                    return frappe.db.get_list("Employee", {
                        fields: ["name", "employee_name"],
                        filters: [["Employee", "name", "in", ids]],
                        limit: 0
                    }).then(emps => {
                        const t = (txt || "").toLowerCase();
                        return emps
                            .filter(e => !t
                                || e.name.toLowerCase().includes(t)
                                || (e.employee_name || "").toLowerCase().includes(t))
                            .map(e => ({ value: e.name, description: e.employee_name || "" }));
                    });
                });
            }
        },
        {
            // Sirf selected department(s) ke MWO (date range ke andar)
            fieldname: "manufacturing_work_order",
            label: __("Manufacturing Work Order"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                const depts = ewr_selected("department");
                if (!depts.length) {
                    return frappe.db.get_link_options(
                        "Manufacturing Work Order",
                        txt
                    );
                }

                const M = "Manufacturing Work Order";
                const f = [
                    [M, "department", "in", depts],
                    [M, "docstatus", "<", 2],
                ];
                const from_date = frappe.query_report.get_filter_value("from_date");
                const to_date = frappe.query_report.get_filter_value("to_date");
                if (from_date) f.push([M, "posting_date", ">=", from_date]);
                if (to_date) f.push([M, "posting_date", "<=", to_date]);
                if (txt) f.push([M, "name", "like", `%${txt}%`]);

                return frappe.db.get_list(M, {
                    fields: ["name"],
                    filters: f,
                    order_by: "creation desc",
                    limit: 50
                }).then(r => r.map(d => ({ value: d.name, description: "" })));
            }
        }
    ],


    formatter: function(value, row, column, data, default_formatter) {

        // Grand Total row: plain bold text
        if (data && data.is_total_row) {
            if (["gold_wt", "diamond_wt"].includes(column.fieldname)) {
                return `<b>${flt(data[column.fieldname]).toFixed(3)}</b>`;
            }
            if (column.fieldname === "diamond_pcs") {
                return `<b>${cint(data[column.fieldname])}</b>`;
            }
            return (value !== null && value !== undefined && value !== "")
                ? `<b>${value}</b>`
                : "";
        }

        value = default_formatter(value, row, column, data);

        // Status colours
        if (column.fieldname === "status" && data) {
            const colors = {
                "WIP": "#e67e22",
                "Not Issued": "#c0392b",
                "Received": "#27ae60",
            };
            const color = colors[data.status];
            if (color) {
                return `<b style="color:${color}">${data.status}</b>`;
            }
        }

        // MWO hover: always attach hover; image may be empty (blank box)
        if (column.fieldname === "batch_no" && data) {
            const img = frappe.utils.escape_html(data.item_image || "");
            return `<span class="mwo-image-hover" data-image="${img}">${value}</span>`;
        }

        return value;
    },


    onload: function(report) {

        report.page.add_inner_button(
            __("Clear Filter"),
            function() {
                // set all filters together so the report refreshes only once
                let values = {};
                report.filters.forEach(function(f) {
                    values[f.df.fieldname] =
                        f.df.fieldtype === "MultiSelectList"
                            ? []
                            : (f.df.default || "");
                });
                report.set_filter_value(values);
            }
        );


        // ---- Hover image preview (blank box when image is missing) ----
        $("#mwo-image-preview").remove();
        $(document).off(".mwoimg");

        const $preview = $(`
            <div id="mwo-image-preview" style="
                display:none;
                position:fixed;
                z-index:100000;
                pointer-events:none;
                background:#fff;
                padding:4px;
                border:1px solid #d1d8dd;
                border-radius:6px;
                box-shadow:0 4px 16px rgba(0,0,0,0.25);">
                <img style="display:block;max-width:250px;max-height:250px;">
            </div>
        `).appendTo("body");

        const $img = $preview.find("img");

        function showBlank() {
            $img.hide();
            $preview.css({ width: "200px", height: "200px" });
        }

        function showImage() {
            $img.show();
            $preview.css({ width: "", height: "" });
        }

        $img.on("error", showBlank);
        $img.on("load", showImage);

        function place(e) {
            const w = $preview.outerWidth() || 260;
            const h = $preview.outerHeight() || 260;
            let x = e.clientX + 18;
            let y = e.clientY + 18;
            if (x + w > window.innerWidth) x = e.clientX - w - 18;
            if (y + h > window.innerHeight) y = window.innerHeight - h - 10;
            $preview.css({ left: Math.max(x, 5) + "px", top: Math.max(y, 5) + "px" });
        }

        $(document).on("mouseenter.mwoimg", ".mwo-image-hover", function(e) {
            const image = $(this).attr("data-image");
            if (image) {
                showImage();
                $img.attr("src", image);
            } else {
                $img.removeAttr("src");
                showBlank();
            }
            $preview.show();
            place(e);
        });

        $(document).on("mousemove.mwoimg", ".mwo-image-hover", place);

        $(document).on("mouseleave.mwoimg", ".mwo-image-hover", function() {
            $preview.hide();
            $img.removeAttr("src");
        });
    }
};