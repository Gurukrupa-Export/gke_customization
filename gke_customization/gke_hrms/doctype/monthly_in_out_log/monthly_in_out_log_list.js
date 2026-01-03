// Copyright (c) 2026, Gurukrupa Export and contributors
// For license information, please see license.txt
// Present
// Absent
// Half Day
// Privilege Leave
// Casual Leave
// Sick Leave
// Leave Without Pay
// Outdoor Duty
// Work From Home
// Maternity Leave
frappe.listview_settings["Monthly In-Out Log"] = {
    get_indicator: function (doc) {
        if (doc.status == "Present") {
            return [__("Present"), "green", "status,=,Present"];
        }
        else if (doc.status == "Absent") {
            return [__("Absent"), "red", "status,=,Absent"];
        }
        else if (doc.status == "Half Day") {
            return [__("Half Day"), "orange", "status,=,Half Day"];
        }
        else if (doc.status == "Privilege Leave") {
            return [__("Privilege Leave"), "blue", "status,=,Privilege Leave"];
        }
        else if (doc.status == "Casual Leave") {
            return [__("Casual Leave"), "blue", "status,=,Casual Leave"];
        }
        else if (doc.status == "Sick Leave") {
            return [__("Sick Leave"), "blue", "status,=,Sick Leave"];
        }
        else if (doc.status == "Leave Without Pay") {
            return [__("Leave Without Pay"), "blue", "status,=,Leave Without Pay"];
        }
        else if (doc.status == "Outdoor Duty") {
            return [__("Outdoor Duty"), "blue", "status,=,Outdoor Duty"];
        }
        else if (doc.status == "Work From Home") {
            return [__("Work From Home"), "blue", "status,=,Work From Home"];
        }
        else if (doc.status == "Maternity Leave") {
            return [__("Maternity Leave"), "blue", "status,=,Maternity Leave"];
        }
    },
};