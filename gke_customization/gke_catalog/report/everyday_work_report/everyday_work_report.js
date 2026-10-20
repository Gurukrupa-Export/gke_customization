// Copyright (c) 2026, Your Company and contributors
// For license information, please see license.txt


const EWR_REPORT = "Everyday Work Report";

// Cascade order: har filter ke options uske pehle wale filters ke hisaab se aate hain
const EWR_ORDER = ["department", "is_finding_mwo", "status", "operation", "employee", "manufacturing_work_order"];

const ewr_cache = {};   // key -> {t, rows}  (60 sec)


// Selected values of a (multi-select) filter, always as an array
function ewr_selected(fieldname) {
    const v = frappe.query_report.get_filter_value(fieldname);
    if (Array.isArray(v)) return v;
    return v ? [v] : [];
}


// Kya "upto" list ke filters me se koi bhi selected hai?
function ewr_any_selected(upto) {
    return upto.some(fn => ewr_selected(fn).length > 0);
}


// Report ko dates + "upto" filters ke saath chalakar uski rows laata hai
function ewr_get_rows(upto) {
    const f = {};
    ["from_date", "to_date"].forEach(function(fn) {
        const v = frappe.query_report.get_filter_value(fn);
        if (v) f[fn] = v;
    });
    upto.forEach(function(fn) {
        const v = ewr_selected(fn);
        if (v.length) f[fn] = v;
    });

    const key = JSON.stringify(f);
    const hit = ewr_cache[key];
    if (hit && Date.now() - hit.t < 60000) {
        return Promise.resolve(hit.rows);
    }

    return frappe.xcall("frappe.desk.query_report.run", {
        report_name: EWR_REPORT,
        filters: f,
        ignore_prepared_report: true
    }).then(function(res) {
        const all = (res && res.result) || [];
        // sirf asli MWO rows (total row me batch_no nahi hota)
        const rows = all.filter(r => r && !Array.isArray(r) && r.batch_no);
        ewr_cache[key] = { t: Date.now(), rows: rows };
        return rows;
    });
}


// Filter badalne par uske baad wale filters clear ho jaate hain
function ewr_on_change(fieldname) {
    return function(report) {
        const idx = EWR_ORDER.indexOf(fieldname);
        const cleared = {};
        EWR_ORDER.slice(idx + 1).forEach(function(fn) {
            const v = report.get_filter_value(fn);
            if (Array.isArray(v) && v.length) {
                cleared[fn] = [];
            }
        });
        if (Object.keys(cleared).length) {
            report.set_filter_value(cleared);   // sab saath set hote hain
        } else {
            report.refresh();
        }
    };
}


function ewr_match(txt, ...parts) {
    const t = (txt || "").toLowerCase();
    if (!t) return true;
    return parts.some(p => (p || "").toLowerCase().includes(t));
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
            on_change: ewr_on_change("department")
        },
        {
            fieldname: "is_finding_mwo",
            label: __("Is Finding MWO"),
            fieldtype: "Select",
            options: ["", "Yes", "No"],
            on_change: ewr_on_change("is_finding_mwo")
        },
        {
            // Department + Is Finding MWO ke hisaab se
            fieldname: "status",
            label: __("Status"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                const order = ["WIP", "Not Issued", "Received"];
                const toOptions = list => list
                    .filter(s => ewr_match(txt, s))
                    .map(s => ({ value: s, description: "" }));

                if (!ewr_any_selected(["department", "is_finding_mwo"])) {
                    return toOptions(order);
                }
                return ewr_get_rows(["department", "is_finding_mwo"]).then(function(rows) {
                    const present = new Set(rows.map(r => r.status).filter(Boolean));
                    return toOptions(order.filter(s => present.has(s)));
                });
            },
            on_change: ewr_on_change("status")
        },
        {
            // Department + Is Finding MWO + Status ke hisaab se
            fieldname: "operation",
            label: __("Operation"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                const upto = ["department", "is_finding_mwo", "status"];

                if (!ewr_any_selected(upto)) {
                    return frappe.db.get_list("Employee IR", {
                        fields: ["operation"],
                        group_by: "operation",
                        filters: txt
                            ? { operation: ["like", `%${txt}%`] }
                            : { operation: ["is", "set"] },
                        order_by: "operation",
                        limit: 0
                    }).then(r => r
                        .filter(d => d.operation)
                        .map(d => ({ value: d.operation, description: "" })));
                }

                return ewr_get_rows(upto).then(function(rows) {
                    const ops = Array.from(
                        new Set(rows.map(r => r.current_process).filter(Boolean))
                    ).sort();
                    return ops
                        .filter(o => ewr_match(txt, o))
                        .map(o => ({ value: o, description: "" }));
                });
            },
            on_change: ewr_on_change("operation")
        },
        {
            // Department + Is Finding MWO + Status + Operation ke hisaab se
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                const upto = ["department", "is_finding_mwo", "status", "operation"];

                if (!ewr_any_selected(upto)) {
                    return frappe.db.get_link_options("Employee", txt);
                }

                return ewr_get_rows(upto).then(function(rows) {
                    const seen = {};
                    const out = [];
                    rows.forEach(function(r) {
                        if (r.worker_code && !seen[r.worker_code]) {
                            seen[r.worker_code] = 1;
                            out.push({ value: r.worker_code, description: r.worker || "" });
                        }
                    });
                    return out
                        .filter(o => ewr_match(txt, o.value, o.description))
                        .sort((a, b) => a.description.localeCompare(b.description));
                });
            },
            on_change: ewr_on_change("employee")
        },
        {
            // Department + Is Finding MWO + Status + Operation + Employee ke hisaab se
            fieldname: "manufacturing_work_order",
            label: __("Manufacturing Work Order"),
            fieldtype: "MultiSelectList",
            get_data: function(txt) {
                const upto = ["department", "is_finding_mwo", "status", "operation", "employee"];

                if (!ewr_any_selected(upto)) {
                    return frappe.db.get_link_options(
                        "Manufacturing Work Order",
                        txt
                    );
                }

                return ewr_get_rows(upto).then(function(rows) {
                    return rows
                        .filter(r => ewr_match(txt, r.batch_no))
                        .slice(0, 100)
                        .map(r => ({ value: r.batch_no, description: r.status || "" }));
                });
            }
        }
    ],


    // Frozen Grand Total row (Frappe ka built-in total row; "Add Total Row" ON hona chahiye).
    // PMO ka distinct count, aur Gold wt / Diamond pcs / Diamond Wt ka sum.
    get_datatable_options: function(options) {
        // Frozen total row hamesha dikhao, chahe report me "Add Total Row" ON ho ya OFF
        options.showTotalRow = true;

        options.hooks = Object.assign({}, options.hooks, {
            columnTotal: function(values, column, type) {
                const fn = (column.column && column.column.fieldname) || column.id;
                const vals = values || [];

                if (fn === "department") {
                    return __("Total");
                }
                if (fn === "g_order_no") {
                    return new Set(vals.filter(v => v !== null && v !== undefined && v !== "")).size;
                }
                if (fn === "gold_wt" || fn === "diamond_wt") {
                    return vals.reduce((a, v) => a + flt(v), 0).toFixed(3);
                }
                if (fn === "diamond_pcs") {
                    return vals.reduce((a, v) => a + cint(v), 0);
                }
                return "";
            }
        });
        return options;
    },


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