// Copyright (c) 2025, Gurukrupa Export and contributors
// For license information, please see license.txt

frappe.query_reports["PF Challan Report"] = {
	"filters": [
		{
            "label": __("Month"),
            "fieldtype": "Select",
            "fieldname": "month",
            "reqd": 1,
            "options": [
                "January","February","March","April",
                "May","June","July","August",
                "September","October","November","December"
            ],
            "default": new Date().toLocaleString('en-US', { month: 'long' }),
            "on_change": function() {
                set_dates();
            }
        },
        {
            "label": __("Year"),
            "fieldtype": "Select",
            "fieldname": "year",
            "reqd": 1,
            "options": (() => {
                let years = [];
                let currentYear = new Date().getFullYear();
                for (let i = currentYear - 5; i <= currentYear + 5; i++) {
                    years.push(String(i));
                }
                return years;
            })(),
            "default": String(new Date().getFullYear()),
            "on_change": function() {
                set_dates();
            }
        },
		{
			"label": __("From Date"),
			"fieldtype": "Date",
			"fieldname": "from_date",
			"read_only": 1,
			"default": frappe.datetime.month_start(frappe.datetime.get_today()),
			"on_change": function(query_report) {
				var from_date = query_report.get_values().from_date;
				if (!from_date) {
					return;
				}
				let date = new moment(from_date)
				var to_date = date.endOf('month').format()
				query_report.set_filter_value({
					"to_date": to_date
				});
			}
		},
		{
			"label": __("To Date"),
			"fieldtype": "Date",
			"fieldname": "to_date",
			"reqd": 1,
			"read_only": 1,
			"default": frappe.datetime.month_end(frappe.datetime.get_today())
		},
		{
			"label": __("Company"),
			"fieldtype": "Link",
			"fieldname": "company",
			"options": "Company",
			"reqd": 1,
		},
		{
			"label": __("Branch"),
			"fieldtype": "Link",
			"fieldname": "branch",
			"options": "Branch" 
		}, 
	],
	onload: (report) => {
		set_dates();
		report.page.add_button("Clear Filters", function() {
			window.open("/app/query-report/PF%20Challan%20Report", "_self")
		}).addClass("btn-info")	
		report.page.add_inner_button(__("PF File"), function () {
			frappe.call({
				method: "gke_customization.gke_hrms.report.pf_challan_report.pf_challan_report.export_txt", 
				args: {
					filters: report.get_values()
				},
				callback: function (r) {
				if (r.message) {
					// 🔽 Auto download
					const link = document.createElement("a");
					link.href = r.message;
					link.download = "pf_export.txt";
					document.body.appendChild(link);
					link.click();
					document.body.removeChild(link);
				}
			}
			});
		}).addClass("btn-secondary");
		report.page.add_inner_button(__("PF Contribution Report"), function () {
			var filters = report.get_values();
			frappe.set_route("query-report", "PF Contribution Report", { month: filters.month, year: filters.year, company: filters.company });
		}); 
	},
	"after_datatable_render": function (datatable_obj) {
		const report = frappe.query_report;
		ensure_panel_inserted(report);
		fetch_and_render_account_total_panel(report);
	},
 
	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		return value;
	},
};
 
function ensure_panel_inserted(report) {
	if (report.pf_panel && report.pf_panel.length && report.pf_panel.closest("body").length) {
		return;
	}
 
	const $panel = $('<div class="pf-account-total-panel"></div>');
 
	let $mount = report.page.main.find(".report-wrapper");
	if (!$mount.length) {
		$mount = report.page.main.find(".dt-scrollable, .datatable");
	}
	if (!$mount.length) {
		$mount = report.page.main;
	}
 
	$mount.first().prepend($panel);
	report.pf_panel = $panel;
}
 
function fetch_and_render_account_total_panel(report) {
	const filters = report.get_values();
	if (!filters || !filters.company) return;
 
	frappe.call({
		method: "gke_customization.gke_hrms.report.pf_challan_report.pf_challan_report.get_account_total_summary",
		args: { filters: filters },
		callback: function (r) {
			if (r.message) {
				render_account_total_panel(report, r.message, filters);
			}
		},
	});
}
 
function render_account_total_panel(report, summary, filters) {
	const fmt = (n) => {
		const num = Number(n) || 0;
		return num.toLocaleString("en-IN");
	};
 
	const ac1 = summary.ac1 || {};
	const ac10 = summary.ac10 || {};
	const ac21 = summary.ac21 || {};
	const c = summary.contribution || {};
 
	const month = filters.month || ""; 
	const html = `
	<div style="padding: 1rem 0;">
		<div style="background: var(--bg-color); border-radius: var(--border-radius-lg); border: 0.5px solid var(--border-color); overflow: hidden;">
 
			<div style="padding: 0.875rem 1.25rem; border-bottom: 0.5px solid var(--border-color); display: flex; align-items: center; justify-content: space-between;">
				<span style="font-size: 16px; font-weight: 500;">Account total</span>
				<span style="font-size: 13px; color: var(--text-muted);">${frappe.utils.escape_html(month)}</span>
			</div>
 
			<div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border-bottom: 0.5px solid var(--border-color);">
 
				<div style="padding: 1rem 1.25rem; border-right: 0.5px solid var(--border-color);">
					<div style="display: inline-block; font-size: 13px; font-weight: 500; padding: 4px 14px; border-radius: 999px; background: #17a2b8; color: var(--primary); margin-bottom: 14px;">A/C 1</div>
					<div style="display: flex; align-items: baseline; gap: 10px; margin-bottom: 6px;">
						<span style="font-size: 13px; color: var(--text-muted); min-width: 78px;">Employee</span>
						<span style="font-size: 17px; font-weight: 500;">${fmt(ac1.subscribers)}</span>
					</div>
					<div style="display: flex; align-items: baseline; gap: 10px;">
						<span style="font-size: 13px; color: var(--text-muted); min-width: 78px;">Total Wages</span>
						<span style="font-size: 17px; font-weight: 500;">${fmt(ac1.wages)}</span>
					</div>
				</div>
 
				<div style="padding: 1rem 1.25rem; border-right: 0.5px solid var(--border-color);">
					<div style="display: inline-block; font-size: 13px; font-weight: 500; padding: 4px 14px; border-radius: 999px; background: #17a2b8; color: var(--primary); margin-bottom: 14px;">A/C 10</div>
					<div style="display: flex; align-items: baseline; gap: 10px; margin-bottom: 6px;">
						<span style="font-size: 13px; color: var(--text-muted); min-width: 78px;">Employee</span>
						<span style="font-size: 17px; font-weight: 500;">${fmt(ac10.subscribers)}</span>
					</div>
					<div style="display: flex; align-items: baseline; gap: 10px;">
						<span style="font-size: 13px; color: var(--text-muted); min-width: 78px;">Total Wages</span>
						<span style="font-size: 17px; font-weight: 500;">${fmt(ac10.wages)}</span>
					</div>
				</div>
 
				<div style="padding: 1rem 1.25rem;">
					<div style="display: inline-block; font-size: 13px; font-weight: 500; padding: 4px 14px; border-radius: 999px; background: #17a2b8; color: var(--primary); margin-bottom: 14px;">A/C 21</div>
					<div style="display: flex; align-items: baseline; gap: 10px; margin-bottom: 6px;">
						<span style="font-size: 13px; color: var(--text-muted); min-width: 78px;">Employee</span>
						<span style="font-size: 17px; font-weight: 500;">${fmt(ac21.subscribers)}</span>
					</div>
					<div style="display: flex; align-items: baseline; gap: 10px;">
						<span style="font-size: 13px; color: var(--text-muted); min-width: 78px;">Total Wages</span>
						<span style="font-size: 17px; font-weight: 500;">${fmt(ac21.wages)}</span>
					</div>
				</div>
 
			</div>
 
			<div style="display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); border-bottom: 0.5px solid var(--border-color);">
 
				<div style="padding: 0.875rem 1rem; border-right: 0.5px solid var(--border-color);">
					<p style="font-size: 12px; color: var(--text-muted); margin: 0 0 4px; line-height: 1.3;">A/C No.1 Employee</p>
					<p style="font-size: 15px; font-weight: 500; margin: 0;">${fmt(c.ac_no_1_employee)}</p>
				</div>
				<div style="padding: 0.875rem 1rem; border-right: 0.5px solid var(--border-color);">
					<p style="font-size: 12px; color: var(--text-muted); margin: 0 0 4px; line-height: 1.3;">A/C No.1 Employer</p>
					<p style="font-size: 15px; font-weight: 500; margin: 0;">${fmt(c.ac_no_1_employer)}</p>
				</div>
				<div style="padding: 0.875rem 1rem; border-right: 0.5px solid var(--border-color);">
					<p style="font-size: 12px; color: var(--text-muted); margin: 0 0 4px;">A/C No.2</p>
					<p style="font-size: 15px; font-weight: 500; margin: 0;">${fmt(c.ac_no_2)}</p>
				</div>
				<div style="padding: 0.875rem 1rem; border-right: 0.5px solid var(--border-color);">
					<p style="font-size: 12px; color: var(--text-muted); margin: 0 0 4px;">A/C No.10</p>
					<p style="font-size: 15px; font-weight: 500; margin: 0;">${fmt(c.ac_no_10)}</p>
				</div>
				<div style="padding: 0.875rem 1rem; border-right: 0.5px solid var(--border-color);">
					<p style="font-size: 12px; color: var(--text-muted); margin: 0 0 4px;">A/C No.21</p>
					<p style="font-size: 15px; font-weight: 500; margin: 0;">${fmt(c.ac_no_21)}</p>
				</div>
				<div style="padding: 0.875rem 1rem; border-right: 0.5px solid var(--border-color);">
					<p style="font-size: 12px; color: var(--text-muted); margin: 0 0 4px;">A/C No.22</p>
					<p style="font-size: 15px; font-weight: 500; margin: 0;">${fmt(c.ac_no_22)}</p>
				</div>
				<div style="padding: 0.875rem 1rem;">
					<p style="font-size: 12px; color: var(--text-muted); margin: 0 0 4px;">Total</p>
					<p style="font-size: 15px; font-weight: 500; margin: 0;">${fmt(summary.grand_total)}</p>
				</div>
			</div>
 
			<div style="padding: 0.875rem 1.25rem; display: flex; align-items: center; gap: 28px; flex-wrap: wrap;">
				<div style="display: flex; align-items: baseline; gap: 8px;">
					<span style="font-size: 15px; font-weight: 500; color: var(--text-muted);">Total employees</span>
					<span style="font-size: 14px;">${fmt(summary.employee_count)}</span>
				</div>
				<div style="display: flex; align-items: baseline; gap: 8px;">
					<span style="font-size: 15px; font-weight: 500; color: var(--text-muted);">Gross pay</span>
					<span style="font-size: 14px;">${fmt(summary.gross_pay)}</span>
				</div>
				<div style="display: flex; align-items: baseline; gap: 8px;">
					<span style="font-size: 15px; font-weight: 500; color: var(--text-muted);">PF amount</span>
					<span style="font-size: 14px;">${fmt(summary.pf_amount)}</span>
				</div>
				
				
			</div>
 
		</div>
	</div>
	`;
	// <div style="display: flex; align-items: baseline; gap: 8px; margin-left: auto;">
	// 				<span style="font-size: 14px; font-weight: 500;">Total</span>
	// 				<span style="font-size: 19px; font-weight: 500;">${fmt(summary.grand_total)}</span>
	// 			</div>
	
	if (report.pf_panel) {
		report.pf_panel.html(html);
	}
}
 

function fetch_month_list() {
	frappe.call({
		method: "gurukrupa_customizations.gurukrupa_customizations.report.monthly_in_out.monthly_in_out.get_month_range",
		freeze: false,
		callback: function(r) {
			var month = frappe.query_report.get_filter('month');
				month.df.options.push(...r.message);
				month.refresh();
		}
	})
}

function set_dates() {
    let report = frappe.query_report;
    if (!report) return;

    let monthName = report.get_filter_value("month");
    let year = parseInt(report.get_filter_value("year"));

    if (!monthName || !year) return;

    const monthIndex = [
        "January","February","March","April",
        "May","June","July","August",
        "September","October","November","December"
    ].indexOf(monthName);

    let from_date = new Date(year, monthIndex, 1);
    let to_date = new Date(year, monthIndex + 1, 0);

    report.set_filter_value({
        from_date: frappe.datetime.obj_to_str(from_date),
        to_date: frappe.datetime.obj_to_str(to_date)
    });
}