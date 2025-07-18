
frappe.query_reports["Sketch Order Form Workflow"] = {
    formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);

    let workflow_states = {
        "draft": "Draft",
        "on_hold": "On Hold",
        "send_for_approval": "Send For Approval",
        "approved": "Approved"
    };

    if (workflow_states[column.fieldname]) {
        let branches = frappe.query_report.get_filter_value("branch") || [];
        if (typeof branches === "string") branches = [branches];

        let branch_param = branches.length > 0 ? `&branch=${encodeURIComponent(JSON.stringify(["in", branches]))}` : "";
        let workflow_state_param = `&workflow_state=${encodeURIComponent(workflow_states[column.fieldname])}`;

        let clean_date = data.date ? data.date.split(" ")[0] : "";
        let date_param = "";
        if (clean_date) {
            date_param = `&modified=${encodeURIComponent(JSON.stringify(["Between", [clean_date, clean_date]]))}`;
        }

        let url = `/app/sketch-order-form?view=list${branch_param}${workflow_state_param}${date_param}`;

        return `<a href="${url}" target="_blank">${value}</a>`;
    }

    return value;
}

};


