// Path: apps/gke_customization/gke_customization/gke_catalog/page/employee_analysis/employee_analysis.js

frappe.pages['employee_analysis'].on_page_load = function (wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Employee Profile'),
        single_column: true
    });

    let main_body = $(wrapper).find('.layout-main-section');
    
    const isDarkMode = () => window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    const getThemeColors = () => isDarkMode() ? {
        cardBg: '#111315',
        cardBorder: '#1e2227',
        innerBg: '#16191c',
        innerBorder: '#22252a',
        textWhite: '#ffffff',
        textMuted: '#9aa1a9',
        donutText: '#ffffff'
    } : {
        cardBg: '#ffffff',
        cardBorder: '#dee2e6',
        innerBg: '#f8f9fa',
        innerBorder: '#e9ecef',
        textWhite: '#212529',
        textMuted: '#495057',
        donutText: '#212529'
    };
        // 2. Apply theme values dynamically to the DOM containers
    const applyDynamicTheme = () => {
        const colors = getThemeColors();
        const card = $('#employee-snapshot-card');
        
        if (!card.length) return;

        // Update main container card panels
        card.find('.theme-card-panel').css({
            'background': colors.cardBg,
            'border-color': colors.cardBorder,
            'box-shadow': colors.panelShadow
        });

        // Update inner subsection layout frames
        card.find('.theme-inner-panel').css({
            'background': colors.innerBg,
            'border-color': colors.innerBorder
        });

        // Update typography colors dynamically
        card.find('.theme-text-main').css('color', colors.textWhite);
        card.find('.theme-text-muted').css('color', colors.textMuted);
        
        // Re-trigger layout elements if active employee is selected
        let selected_employee = employee_filter.get_value();
        if (selected_employee) {
            // Re-render chart components to properly recalculate text contrasts
            let last_stored_data = card.data('raw-response');
            if (last_stored_data) {
                render_salary_split_chart($('#lbl_comp_ctc').data('raw-ctc'), $('#lbl_comp_grade').data('raw-variable'));
                render_increment_trend_chart(last_stored_data.compensation || []);
                render_performance_section(last_stored_data.performance_overview || []);
                render_attendance_and_leave_section(last_stored_data);
            }
        }
    };
    let details_container = $(`
        <div id="employee-snapshot-card" style="margin-top: 25px; display: none; width: 100%; flex-direction: column; gap: 20px;">
            
              <div class="theme-card-panel" style="border: 1px solid #1e2227; border-radius: 16px; padding: 24px; display: flex; align-items: center; gap: 20px;">
                <div class="theme-inner-panel" style="width: 64px; height: 64px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; border: 2px solid;">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.5 20.118a7.5 7.5 0 0 1 15 0H4.5Z" />
                    </svg>
                </div>
                <div>
                    <h2 id="lbl_name" class="theme-text-main" style="margin: 0 0 4px 0; font-size: 20px; font-weight: 700;"></h2>
                    <p id="lbl_subtitle" class="theme-text-muted" style="margin: 0 0 10px 0; font-size: 13px; font-weight: 500;"></p>
                    <span id="badge_status" style="padding: 4px 10px; font-size: 10px; font-weight: 700; border-radius: 6px; letter-spacing: 0.05em; text-transform: uppercase; display: none;"></span>
                </div>
            </div>

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; width: 100%;">
                
                <div class="theme-card-panel" style="border: 1px solid #1e2227; border-radius: 16px; padding: 24px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);">
                    <h4 style="margin-top: 0; margin-bottom: 20px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #1e2227; padding-bottom: 10px;">
                        ${__('Timeline & Geography')}
                    </h4>
                    <div style="display: flex; flex-direction: column; gap: 14px;">
                        <div style="display: flex; justify-content: space-between; font-size: 13px; align-items: center;">
                            <span>${__('Date of Joining')}</span>
                            <strong id="lbl_doj" style="font-weight: 600;"></strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 13px; align-items: center;">
                            <span>${__('Tenure')}</span>
                            <strong id="lbl_tenure" style="font-weight: 600;"></strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 13px; align-items: center;">
                            <span>${__('Location')}</span>
                            <strong id="lbl_location" style="font-weight: 600;"></strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 13px; align-items: center;">
                            <span>${__('Languages Known')}</span>
                            <strong id="lbl_language" style="font-weight: 600;"></strong>
                        </div>
                    </div>
                </div>

                <!-- Right Details Box: Organizational Lineage -->
                <div class="theme-card-panel" style="border: 1px solid #1e2227; border-radius: 16px; padding: 24px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);">
                    <h4 style="margin-top: 0; margin-bottom: 20px; font-size: 12px; font-weight: 700;text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #1e2227; padding-bottom: 10px;">
                        ${__('Organizational Lineage')}
                    </h4>
                    <div style="display: flex; flex-direction: column; gap: 14px;">
                        <div style="display: flex; justify-content: space-between; font-size: 13px; align-items: center;">
                            <span>${__('Reporting Manager')}</span>
                            <strong id="lbl_manager" style="font-weight: 600;"></strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 13px; align-items: center;">
                            <span>${__('Cost Center')}</span>
                            <strong id="lbl_cost_center" style="font-weight: 600;"></strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 13px; align-items: center;">
                            <span>${__('Branch')}</span>
                            <strong id="lbl_business_unit" style="font-weight: 600;"></strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 13px; align-items: center;">
                            <span>${__('Employee ID')}</span>
                            <strong id="lbl_emp_id" style="font-weight: 600;"></strong>
                        </div>
                    </div>
                </div>

            </div>

            <!-- TIMELINE SECTION: Visual Corporate Career Progression -->
            <div class="theme-card-panel" style="border: 1px solid #1e2227; border-radius: 16px; padding: 24px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3); width: 100%;">
                <h4 style="margin-top: 0; margin-bottom: 24px; font-size: 12px; font-weight: 700;text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #1e2227; padding-bottom: 10px;">
                    ${__('Career Timeline Chart')}
                </h4>
                <!-- Left-hand vertical line matching dark tracker layouts -->
                <div id="timeline-container-target" class="timeline-dot" style="position: relative; padding-left: 30px; display: flex; flex-direction: column; gap: 24px; border-left: 2px solid; margin-left: 10px;">
                    <!-- Timeline event elements append dynamically -->
                </div>
            </div>

			
			<!-- SECTION 4: COMPENSATION & GRADE SUMMARY BOARD -->
                <h4 style="margin-top: 20px; margin-bottom: 20px; font-size: 13px; font-weight: 700;text-transform: uppercase; border-bottom: 1px solid #1e2227; padding-bottom: 10px; letter-spacing: 0.03em;">
                    ${__('Compensation & Grade Summary')}
                </h4>
                
                <!-- Textual Financial KPI Metric Cards Grid -->
                <div class="theme-card-panel" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 28px;">
                    <div style="padding: 16px; border-radius: 12px; border: 1px solid #1e2227; box-shadow: 0 4px 6px rgba(0,0,0,0.15);">
                        <span style="display:block; font-size:11px;text-transform:uppercase; font-weight:600; margin-bottom:4px;">${__('Current Grade')}</span>
                        <strong id="lbl_comp_grade" style="font-size:16px;"></strong>
                    </div>
                    <div style="padding: 16px; border-radius: 12px; border: 1px solid #1e2227; box-shadow: 0 4px 6px rgba(0,0,0,0.15);">
                        <span style="display:block; font-size:11px;text-transform:uppercase; font-weight:600; margin-bottom:4px;">${__('Current CTC (Annual)')}</span>
                        <strong id="lbl_comp_ctc" style="font-size:16px;"></strong>
                    </div>
                    <div style="padding: 16px; border-radius: 12px; border: 1px solid #1e2227; box-shadow: 0 4px 6px rgba(0,0,0,0.15);">
                        <span style="display:block; font-size:11px;text-transform:uppercase; font-weight:600; margin-bottom:4px;">${__('Last Increment Amount')}</span>
                        <strong id="lbl_comp_increment" style="font-size:16px;"></strong>
                    </div>
                    <div style="padding: 16px; border-radius: 12px; border: 1px solid #1e2227; box-shadow: 0 4px 6px rgba(0,0,0,0.15);">
                        <span style="display:block; font-size:11px;text-transform:uppercase; font-weight:600; margin-bottom:4px;">${__('Last Revision Date')}</span>
                        <strong id="lbl_comp_revision_date" style="font-size:16px;"></strong>
                    </div>
                </div>

                <!-- CHARTS PRESENTATION DUAL COLUMNS GRID PANEL -->
                <div class="theme-card-panel" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 24px; width: 100%;">
                    <div style="border: 1px solid #1e2227; padding: 20px; border-radius: 16px;box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);">
                        <h5 style="font-size:11px; font-weight:700;text-transform:uppercase; margin-top:0; margin-bottom:16px; letter-spacing:0.02em;">${__('Salary Split (Fixed Component vs Variable Component)')}</h5>
                        <div id="chart_salary_donut" style="min-height: 220px;"></div>
                    </div>
                    <div style="border: 1px solid #1e2227; padding: 20px; border-radius: 16px;box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);">
                        <h5 style="font-size:11px; font-weight:700;text-transform:uppercase; margin-top:0; margin-bottom:16px; letter-spacing:0.02em;">${__('Increment History Trend Steps')}</h5>
                        <div id="chart_increment_bar" style="min-height: 220px;"></div>
                    </div>
                </div>

                     <!-- SECTION 5: PERFORMANCE OVERVIEW BOARD -->
            <div class="theme-card-panel" style="border: 1px solid #1e2227; border-radius: 16px; padding: 24px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3); width: 100%;">
                <h4 style="margin-top: 0; margin-bottom: 20px; font-size: 13px; font-weight: 700;text-transform: uppercase; border-bottom: 1px solid #1e2227; padding-bottom: 10px; letter-spacing: 0.03em;">
                    ${__('Performance Overview')}
                </h4>
                
                <!-- Layout Split Grid Wrapper Opening Node -->
                <div class="theme-card-panel" style="display: grid; grid-template-columns: 2fr 1fr; gap: 24px; align-items: start; margin-bottom: 24px;">
                    <!-- Line Chart Node -->
                    <div style="padding: 16px; border-radius: 12px; border: 1px solid #22252a;">
                        <div id="performance-chart-target" style="width: 100%; height: 260px;"></div>
                    </div>
                    
                    <!-- HiPo Badge and Overview Scorecard Widget -->
                    <div class="theme-card-panel" style="display: flex; flex-direction: column; gap: 16px;">
                        <div id="hipo-status-box" style="padding: 20px; border-radius: 12px; border: 2px dashed #22252a; text-align: center;">
                            <span style="font-size: 11px;font-weight: 600; text-transform: uppercase; display: block; margin-bottom: 6px;">Talent Pool Designation</span>
                            <div id="lbl_hipo_badge" style="font-size: 15px; font-weight: 700;">No History Matrix Found</div>
                        </div>
                        <div style="padding: 16px; border-radius: 12px; border: 1px solid #22252a;">
                            <span style="font-size: 11px;font-weight: 600; text-transform: uppercase; display: block; margin-bottom: 4px;">Latest Evaluation Score</span>
                            <strong id="lbl_latest_perf_score" style="font-size: 24px;">-</strong><span style="font-size: 12px;"> / 100</span>
                        </div>
                    </div>
                </div>

                <!-- Scorecard Tabular Log Document Target -->
                <div class="theme-card-panel" style="overflow-x: auto; width: 100%;">
                    <table class="table" style="width: 100%; margin: 0; font-size: 13px; border-collapse: collapse;">
                        <thead>
                            <tr style="font-weight: 600; text-align: left;">
                                <th style="padding: 12px 16px; border-bottom: 1px solid #22252a;">Evaluation Period</th>
                                <th style="padding: 12px 16px; border-bottom: 1px solid #22252a;">Appraisal ID</th>
                                <th style="padding: 12px 16px; border-bottom: 1px solid #22252a; text-align: center;">Rating (Stars)</th>
                                <th style="padding: 12px 16px; border-bottom: 1px solid #22252a; text-align: center;">Total Score</th>
                                <th style="padding: 12px 16px; border-bottom: 1px solid #22252a;">Manager Remarks / Feedback</th>
                            </tr>
                        </thead>
                        <tbody id="performance-scorecard-tbody">
                            <tr>
                                <td colspan="5" style="text-align: center;padding: 20px;">No historical appraisal cards compiled.</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- SECTION 6: ATTENDANCE & LEAVE ANALYSIS BOARD -->
            <div class="theme-card-panel" style="border: 1px solid #1e2227; border-radius: 16px; padding: 24px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3); width: 100%;">
                <h4 style="margin-top: 0; margin-bottom: 20px; font-size: 13px; font-weight: 700;text-transform: uppercase; border-bottom: 1px solid #1e2227; padding-bottom: 10px; letter-spacing: 0.03em;">
                    ${__('Attendance & Leave Analysis (Past 3 Years)')}
                </h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 24px;">
                    <div style="padding: 16px; border-radius: 12px; border: 1px solid #22252a; box-shadow: 0 4px 6px rgba(0,0,0,0.15);">
                        <span style="font-size: 11px;font-weight: 600; text-transform: uppercase; display: block; margin-bottom: 4px;">Overall Absenteeism Rate</span>
                        <strong id="lbl_absenteeism_rate" style="font-size: 24px; color: #ef4444;">0.00%</strong>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 24px; width: 100%;">
                    <div style="border: 1px solid #1e2227; padding: 20px; border-radius: 16px;box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);">
                        <h5 style="font-size:11px; font-weight:700;text-transform:uppercase; margin-top:0; margin-bottom:16px; letter-spacing:0.02em;">${__('Monthly Absenteeism Rate Trend (%)')}</h5>
                        <div id="chart_attendance_bars" style="min-height: 220px;"></div>
                    </div>
                    <div style="border: 1px solid #1e2227; padding: 20px; border-radius: 16px;box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);">
                        <h5 style="font-size:11px; font-weight:700;text-transform:uppercase; margin-top:0; margin-bottom:16px; letter-spacing:0.02em;">${__('Leave Type Breakdown')}</h5>
                        <div id="chart_leave_donut" style="min-height: 220px;"></div>
                    </div>
                </div>
            </div>



            <div class="theme-card-panel" style="border: 1px solid #1e2227; border-radius: 16px; padding: 24px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3); width: 100%;">
                <h4 style="margin-top: 0; margin-bottom: 20px; font-size: 13px; font-weight: 700;text-transform: uppercase; border-bottom: 1px solid #1e2227; padding-bottom: 10px; letter-spacing: 0.03em;">
                    ${__('Exit Information')}
                </h4>
                <div style="overflow-x: auto; width: 100%;">
                    <table class="table" style="width: 100%; margin: 0; font-size: 13px; border-collapse: collapse;">
                        <thead>
                            <tr style="font-weight: 600; text-align: left;">
                                <th style="padding: 12px 16px; border-bottom: 1px solid #22252a;">Resignation Date</th>
                                <th style="padding: 12px 16px; border-bottom: 1px solid #22252a;">Reason for Resignation</th>
                                <th style="padding: 12px 16px; border-bottom: 1px solid #22252a; text-align: center;">Status</th>
                            </tr>
                        </thead>
                        <tbody id="exit-information-tbody">
                            <tr>
                                <td colspan="3" style="text-align: center;padding: 20px;">No exit or resignation records logged.</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>


        </div> 
       
    `).appendTo(main_body);


    let employee_filter = page.add_field({
        fieldname: 'employee',
        label: __('Select Employee ID'),
        fieldtype: 'Link',
        options: 'Employee',
        change: function () {
            let selected_employee = employee_filter.get_value();
            if (selected_employee) {
                load_employee_data(selected_employee, details_container);
            } else {
                details_container.css('display', 'none').removeData('raw-response');
                $("#lbl_name, #lbl_subtitle, #lbl_doj, #lbl_tenure, #lbl_location, #lbl_language,#lbl_manager, #lbl_cost_center, #lbl_business_unit, #lbl_emp_id").empty();
                $("#badge_status").empty().hide();
                $("#timeline-container-target").empty();
            }
        }
    });
};

employee_filter.on_change = function() {
    let selected_employee = employee_filter.get_value(); 
    if (selected_employee) { 
        let last_stored_data = card.data('raw-response'); 
        if (last_stored_data) { 
            render_salary_split_chart($('#lbl_comp_ctc').data('raw-ctc'), $('#lbl_comp_grade').data('raw-variable')); 
            render_increment_trend_chart(last_stored_data.compensation || []); 
            render_performance_section(last_stored_data.performance_overview || []); 
            render_attendance_and_leave_section(last_stored_data); 
        } 
    }
};

/**
 * Handles ajax query execution pathways and triggers timeline tracking generation loops safely.
 */

function load_employee_data(employee, container) {
    frappe.call({
        method: "gke_customization.gke_catalog.page.employee_analysis.employee_analysis.get_employee_details",
        args: { employee: employee },
        freeze: true,
        freeze_message: __('Building career tracker views...'),
        callback: function (r) {
            if (r.message) {
                let response = r.message;
                let profile = response.profile || response;
                let timeline = response.timeline || [];
                let compensation = response.compensation || [];
                let performance = response.performance_overview || []; // Fixed: Extracted missing performance variable

                $("#lbl_name").text(profile.employee_name || '');

                let subtitle = [];
                if (profile.designation) subtitle.push(profile.designation);
                if (profile.department) subtitle.push(profile.department);
                $("#lbl_subtitle").text(subtitle.join(' • '));

                $("#lbl_doj").text(profile.date_of_joining ? frappe.datetime.str_to_user(profile.date_of_joining) : '');
                $("#lbl_tenure").text(profile.tenure || '');
                $("#lbl_location").text(profile.location || '');
                $("#lbl_language").text(profile.language || '-');

                $("#lbl_manager").text(profile.reporting_employee_name_ || profile.reports_to || '');
                $("#lbl_cost_center").text(profile.payroll_cost_center || '');
                $("#lbl_business_unit").text(profile.branch || '');
                $("#lbl_emp_id").text(profile.name || '');

                let status_str = (profile.status || '').trim();
                if (status_str) {
                    $("#badge_status").text(status_str).show();
                    if (status_str === "Active") {
                        $("#badge_status").css({ "background-color": "rgba(21, 128, 61, 0.15)", "color": "#15803d" });
                    } else {
                        $("#badge_status").css({ "background-color": "rgba(153, 27, 27, 0.15)", "color": "#991b1b" });
                    }
                } else {
                    $("#badge_status").hide();
                }

                // --- BUILD VISUAL CAREER TRACKING TIMELINE NODES ---
               let timeline_target = $("#timeline-container-target").empty();

                if (timeline && timeline.length > 0) {
                    timeline.forEach(function (ev) {
                        let color_map = {
                            "Hired / Profile Setup": "#1b86e6",
                            "Promotion": "#22c55e",
                            "Company Transfer": "#e43b90",
                            "Department Transfer": "#eab308",
                            "Branch Transfer": "#aa3333b2"
                        };

                        // Calming, low-saturation translucent background fills (reduces glare)
                        let bg_color_map = {
                            "Hired / Profile Setup": "rgba(92, 163, 230, 0.05)",
                            "Promotion": "rgba(92, 184, 126, 0.05)",
                            "Company Transfer": "rgba(214, 98, 155, 0.05)",
                            "Branch Transfer": "rgba(224, 158, 83, 0.05)",
                            "Department Transfer": "rgba(217, 180, 82, 0.04)"
                        };

                        // Gentle container border limits to seamlessly frame each record block
                        let border_color_map = {
                            "Hired / Profile Setup": "rgba(92, 163, 230, 0.15)",
                            "Promotion": "rgba(92, 184, 126, 0.15)",
                            "Company Transfer": "rgba(214, 98, 155, 0.15)",
                            "Branch Transfer": "rgba(224, 158, 83, 0.15)",
                            "Department Transfer": "rgba(217, 180, 82, 0.12)"
                        };


                        let active_color = color_map[ev.event_type] || "#64748b";
                        let format_date = ev.event_date ? frappe.datetime.str_to_user(ev.event_date) : '';

                        let salary_txt = ev.salary ? ` • <span style="font-weight:600;">CTC:</span> <span style="font-weight:600;">${Math.round(ev.salary)} INR</span>` : '';

                        let role_txt = ev.designation ? ` • <span style="font-weight:600;">Designation:</span> ${ev.designation}` : '';

                        let event_html = $(`
                            <div class="timeline-event-item" style="position: relative; width: 100%;">
                                <!-- Updated ring alignment with a dark border background mask -->
                                <div style="position: absolute; left: -37px; top: 14px; width: 12px; height: 12px; border-radius: 50%; background: ${active_color}; border: 3px solid #111315; box-shadow: 0 0 0 4px ${active_color}20; z-index: 2;"></div>
                                <div style="border: 1px solid #22252a; border-radius: 12px; padding: 14px 18px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.15);">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; flex-wrap: wrap; gap: 5px;">
                                        <span style="font-size: 13px; font-weight: 700; color: ${active_color}; text-transform: uppercase; letter-spacing: 0.03em;">${__(ev.event_type)}</span>
                                        <span style="font-size: 12px; font-weight: 500;">${format_date}</span>
                                    </div>
                                    <div style="font-size: 13px;line-height: 1.5;">
                                        <span style="font-weight:600;">Company :</span> ${ev.company || ''}
                                        • <span style="font-weight:600;">Department :</span> ${ev.department || ''}
                                        • <span style="font-weight:600;">Branch :</span> ${ev.branch || ''}
                                         ${role_txt}${salary_txt}
                                    </div>
                                </div>
                            </div>
                        `);

                        timeline_target.append(event_html);
                    });
                } else {
                    timeline_target.html(`<p style="font-size: 13px; margin: 0;">${__('No historical career progression data mapped.')}</p>`);
                }

                // --- PART 1: EXTRACT LATEST AUDIT EVENTS FROM UNIONS DATASET ---
                let latest_event = compensation.length > 0 ? compensation[compensation.length - 1] : {};
                let base_event = compensation.find(e => e.event_type === "Hired / Profile Setup") || {};

                // --- PART 2: POPULATE METRIC VALUES ---
                $("#lbl_comp_grade").text(profile.grade || base_event.grade || __('Unspecified'));

                let ctc_val = Math.round(profile.ctc || latest_event.salary || 0.00);
                $("#lbl_comp_ctc").text(`${ctc_val} INR`);

                let increments = compensation.filter(e => e.increment_amount > 0);
                let last_inc_val = increments.length > 0 ? Math.round(increments[increments.length - 1].increment_amount) : 0;
                $("#lbl_comp_increment").text(`${last_inc_val} INR`);

                $("#lbl_comp_revision_date").text(latest_event.revision_date ? frappe.datetime.str_to_user(latest_event.revision_date) : '-');

                // --- PART 3: DRAW NATIVE HIGH-PERFORMANCE VISUAL PLOTS ---
                render_salary_split_chart(profile.ctc, base_event.variable_pay);
                render_increment_trend_chart(compensation);

                container.css('display', 'flex');

                setTimeout(() => {
                    render_performance_section(performance);
                    render_attendance_and_leave_section(response);
                    render_exit_information_section(response.exit_information || []);
                }, 50);

            } else {
                container.css('display', 'none');
                $("#exit-information-tbody").empty();
            }
        }
    });
}
// Dynamically inject CSS styles to target both the text label and numeric value text fields
const style = document.createElement('style');
style.innerHTML = `
    /* Targets the primary text labels ("Fixed" / "Variable") */
    #chart_salary_donut .frappe-chart text.legend-dataset-text {
        font-weight: 700 !important;
        font-size: 11px !important;
    }
    
    /* Targets the numbers/values sitting right underneath the text labels */
    #chart_salary_donut .frappe-chart text {
        font-weight: 700 !important;
    }
`;
document.head.appendChild(style);


function render_salary_split_chart(total_ctc, variable_pay_config) {
    let variable = parseFloat(variable_pay_config) || 0.00;
    let fixed = Math.max((parseFloat(total_ctc) || 0.00) - variable, 0.00);
    let target = document.getElementById('chart_salary_donut');
    if (!target) return;
    target.innerHTML = '';

    new frappe.Chart(target, {
        type: 'donut',
        data: {
            labels: [__('Fixed'), __('Variable')],
            datasets: [{ values: [fixed, variable] }]
        },
        colors: ['#22c55e', '#f472b6'], 
        height: 220
    });
}

function render_increment_trend_chart(compensation) {
    let trend_events = compensation.filter(e => e.event_type === "Promotion" || e.event_type === "Hired / Profile Setup");

    // 🛠️ FIX: Safely extract the date string before parsing to prevent format crashes
    let labels = trend_events.map(e => {
        if (!e.event_date) return '-';
        let clean_date_string = String(e.event_date).split(' ')[0]; // Extracts only "YYYY-MM-DD"
        return frappe.datetime.str_to_user(clean_date_string);
    });

    let values = trend_events.map(e => parseFloat(e.increment_amount) || 0.00);

    let target = document.getElementById('chart_increment_bar');
    if (!target) return;
    target.innerHTML = '';

    // Draw the chart canvas panel safely
    new frappe.Chart(target, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{ name: __('Increment Added'), values: values }]
        },
        colors: ['#22c55e'],
        height: 220
    });
}

function render_employee_dashboard(employee) {
    frappe.call({
        method: 'apps.gke_customization.gke_customization.gke_catalog.page.employee_analysis.employee_analysis.get_employee_details',
        args: { employee: employee },
        callback: function (r) {
            if (r.message) {
                let profile = r.message.profile;
                let timeline = r.message.timeline;

                let performance = r.message.performance_overview || r.message.performance || [];

                $('#lbl_name').text(profile.employee_name || '-');
                $('#lbl_subtitle').text(`${profile.designation || '-'} • ${profile.department || '-'}`);
                $('#lbl_doj').text(profile.date_of_joining || '-');
                $('#lbl_tenure').text(profile.tenure || '-');
                $('#lbl_location').text(profile.location || '-');
                $('#lbl_language').text(profile.language || '-');
                $('#lbl_manager').text(profile.reporting_employee_name_ || profile.reports_to || '-');
                $('#lbl_cost_center').text(profile.payroll_cost_center || '-');
                $('#lbl_business_unit').text(profile.branch || '-');
                $('#lbl_emp_id').text(profile.name || '-');
                $('#lbl_comp_grade').text(profile.grade || '-');
                $('#lbl_comp_ctc').text(profile.ctc ? format_currency(profile.ctc) : '-');

                $('#employee-snapshot-card').css('display', 'flex');

                render_performance_section(performance);

                if (typeof render_increment_trend_chart === "function" && timeline) {
                    render_increment_trend_chart(timeline);
                }
                render_attendance_and_leave_section(r.message);
            }
        }
    });
}

function render_performance_section(performance_data) {
    let tbody = $('#performance-scorecard-tbody').empty();
    let chart_target = document.getElementById('performance-chart-target');

    if (!performance_data || performance_data.length === 0) {
        tbody.append(`<tr><td colspan="5" style="text-align: center;">No historical appraisal cards compiled.</td></tr>`);
        $('#lbl_latest_perf_score').text('-');
        $('#lbl_hipo_badge').text('No History Matrix Found').css({ 'border-color': '#e2e8f0' });
        if (chart_target) chart_target.innerHTML = '<div style="padding:20px;text-align:center;">No graph parameters collected.</div>';
        return;
    }

    let labels = [];
    let scores = [];
    let is_hipo_active = false;

    performance_data.forEach(row => {
        // Safe Date Parsing: Strip timestamps out to avoid rendering breaks
        let raw_date = row.evaluation_date ? String(row.evaluation_date).split(' ')[0] : null;
        let formatted_date = raw_date ? frappe.datetime.str_to_user(raw_date) : 'N/A';

        labels.push(formatted_date);
        scores.push(parseFloat(row.performance_score) || 0);

        if (parseInt(row.high_potential_indicator) === 1) {
            is_hipo_active = true;
        }

        tbody.append(`
            <tr style="border-bottom: 1px solid #1e2227;">
                <td style="padding: 12px 16px; font-weight: 500;">${formatted_date}</td>
                <td style="padding: 12px 16px;"><a href="/app/appraisal/${row.appraisal_id}" target="_blank" style="font-weight:600;">${row.appraisal_id}</a></td>
                <td style="padding: 12px 16px; text-align: center;"><span style="color: #eab308; padding: 2px 8px; border-radius: 4px; font-weight: 600;">★ ${row.performance_rating || '0'}</span></td>
                <td style="padding: 12px 16px; text-align: center; font-weight: 700;">${row.performance_score || '0'}</td>
                <td style="padding: 12px 16px;font-style: italic;">${row.feedback || 'No remarks provided.'}</td>
            </tr>
        `);

    });

    let latest_entry = performance_data[performance_data.length - 1];
    $('#lbl_latest_perf_score').text(latest_entry.performance_score || '0');

    if (is_hipo_active) {
        $('#lbl_hipo_badge').text('High Potential (HiPo)').css({
            'border': '1px solid #14532d', 'padding': '6px 12px', 'border-radius': '20px'
        });
    } else {
        $('#lbl_hipo_badge').text('Core Talent Asset').css({
            'border': '1px solid #2b3037', 'padding': '6px 12px', 'border-radius': '20px'
        });
    }


    if (chart_target) {
        chart_target.innerHTML = '';
        new frappe.Chart(chart_target, {
            title: __("Historical Score Trajectory"),
            data: {
                labels: labels,
                datasets: [{ name: __("Score"), values: scores }]
            },
            type: 'line',
            height: 240,
            colors: ['#1b86e6'],
            lineOptions: { hideDots: 0, regionFill: 1 },
            axisOptions: { xIsSeries: 1 }
        });
    }
}
function render_attendance_and_leave_section(data) {
    // 1. Render Absenteeism KPI value labels
    let rate = data.absenteeism_percentage || 0.00;
    $('#lbl_absenteeism_rate').text(`${rate}%`).css('color', rate > 8.00 ? '#ef4444' : '#22c55e');

    // 2. Build Yearly Split Line Charts for Attendance
    let line_target = document.getElementById('chart_attendance_bars');
    if (line_target && data.attendance_trends && data.attendance_trends.length > 0) {
        line_target.innerHTML = '';

        // Define fixed X-axis monthly coordinates 
        let months_labels = [__('Jan'), __('Feb'), __('Mar'), __('Apr'), __('May'), __('Jun'), __('Jul'), __('Aug'), __('Sep'), __('Oct'), __('Nov'), __('Dec')];

        // Group trends datasets by unique years dynamically
        let datasets_by_year = {};
        data.attendance_trends.forEach(row => {
            let year = row.att_year;
            if (!datasets_by_year[year]) {
                datasets_by_year[year] = new Array(12).fill(0);
            }
            // Calculate absenteeism rate for that month specifically
            let present = parseInt(row.total_present) || 0;
            let absent = parseInt(row.total_absent) || 0;
            let total = present + absent;
            let month_absent_pct = total > 0 ? ((absent / total) * 100).toFixed(2) : 0;

            datasets_by_year[year][row.att_month_num - 1] = parseFloat(month_absent_pct);
        });

        let chart_datasets = Object.keys(datasets_by_year).map(year => {
            return {
                name: String(year),
                values: datasets_by_year[year]
            };
        });

        new frappe.Chart(line_target, {
            type: 'line',
            height: 220,
            data: {
                labels: months_labels,
                datasets: chart_datasets
            },
            colors: ['#3b82f6', '#10b981', '#f59e0b'] // Custom line path indicator tones
        });
    } else if (line_target) {
        line_target.innerHTML = `<div style="padding:40px; text-align:center;">${__('No recent attendance logging captured.')}</div>`;
    }

    // 3. Build Leave Utilization Donut Charts (Fixed verification logic mapping)
    let donut_target = document.getElementById('chart_leave_donut');
    if (donut_target && data.leave_summary && data.leave_summary.length > 0) {
        // Clear target and create dedicated wrappers to prevent layout/visual overlapping
        donut_target.innerHTML = `
        <div class="frappe-chart-canvas-wrapper"></div>
        <div class="custom-legend-wrapper"></div>
    `;

        const chartWrapper = donut_target.querySelector('.frappe-chart-canvas-wrapper');
        const legendWrapper = donut_target.querySelector('.custom-legend-wrapper');

        let leave_labels = data.leave_summary.map(l => String(l.leave_type));
        let leave_values = data.leave_summary.map(l => parseFloat(l.total_utilized) || 0);

        // Inject CSS to completely hide native overlapping SVG text labels inside the chart
        const styleId = 'hide-frappe-overlapping-labels';
        if (!document.getElementById(styleId)) {
            const style = document.createElement('style');
            style.id = styleId;
            style.innerHTML = `
                .frappe-chart-canvas-wrapper .legend-dataset-text,
                .frappe-chart-canvas-wrapper .chart-label,
                .frappe-chart-canvas-wrapper .graph-stats-container,
                .frappe-chart-canvas-wrapper .chart-legend {
                    display: none !important;
                }
            `;
            document.head.appendChild(style);
        }

        new frappe.Chart(chartWrapper, {
            type: 'donut',
            height: 220,
            data: {
                labels: leave_labels,
                datasets: [{ values: leave_values }],
                lineOptions: { hideDots: 1 }
            },
            colors: ['#1b86e6', '#f59e0b', '#8b5cf6', '#ec4899', '#14b8a6']
        });

        requestAnimationFrame(() => {
            const colors = ['#1b86e6', '#f59e0b', '#8b5cf6', '#ec4899', '#14b8a6'];
            const legend = document.createElement('div');
            legend.className = 'custom-leave-legend';

            Object.assign(legend.style, {
                display: 'grid',
                gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
                gap: '11px 22px',
                marginTop: '10px',
                width: '100%',
                boxSizing: 'border-box'
            });

            leave_labels.forEach((label, i) => {
                const item = document.createElement('div');
                Object.assign(item.style, {
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '5px',
                    minWidth: '0',
                    color: '#9aa1a9',
                    fontSize: '12px',
                    lineHeight: '1.5',
                    overflowWrap: 'anywhere'
                });

                const dot = document.createElement('span');
                Object.assign(dot.style, {
                    width: '9px',
                    height: '9px',
                    minWidth: '9px',
                    borderRadius: '50%',
                    backgroundColor: colors[i % colors.length],
                    marginTop: '4px'
                });

                const text = document.createElement('span');
                text.textContent = `${label} (${leave_values[i]})`;

                item.append(dot, text);
                legend.appendChild(item);
            });

            legendWrapper.appendChild(legend);
        });
    } else if (donut_target) {
        donut_target.innerHTML = `<div style="padding:40px; text-align:center;">${__('No approved leave history tracked.')}</div>`;
    }

}
function render_exit_information_section(exit_data) {
    let tbody = $('#exit-information-tbody').empty();

    if (!exit_data || exit_data.length === 0) {
        tbody.append(`<tr><td colspan="3" style="text-align: center;padding: 20px;">No exit or resignation records logged.</td></tr>`);
        return; navigation;
    }

    exit_data.forEach(row => {
        let raw_date = row.date_resignation ? String(row.date_resignation).split(' ')[0] : null;
        let formatted_date = raw_date ? frappe.datetime.str_to_user(raw_date) : 'N/A';

        let status_color = row.status === 'Approved' ? '#22c55e' : '#f59e0b';

        tbody.append(`
            <tr style="border-bottom: 1px solid #1e2227;">
                <td style="padding: 12px 16px; font-weight: 500;">${formatted_date}</td>
                <td style="padding: 12px 16px;">${row.reason_for_resignation || 'No reason provided.'}</td>
                <td style="padding: 12px 16px; text-align: center;">
                    <span style="background: ${status_color}15; color: ${status_color}; padding: 3px 10px; font-size: 11px; font-weight: 600; border-radius: 4px;">
                        ${row.status || 'Draft'}
                    </span>
                </td>
            </tr>
        `);

    });
}
