// Copyright (c) 2023, 8848 Digital LLP and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Dummy Monthly Report"] = {
  filters: [
    {
      label: __("Month"),
      fieldtype: "Select",
      fieldname: "month",
      reqd: 1,
      options: [],
      default: () => {
        const dateObject = new Date(); // create a new date object with the current date
        const options = { month: "short", year: "numeric" };
        const dateString = dateObject.toLocaleDateString("en-US", options);
        return dateString;
      },
      on_change: function (query_report) {
        var _month = query_report.get_filter_value("month");
        if (!_month) return;
        let firstDayOfMonth = moment(_month, "MMM YYYY").toDate();
        firstDayOfMonth = frappe.datetime.obj_to_str(firstDayOfMonth);
        let lastDayOfMonth = frappe.datetime.month_end(firstDayOfMonth);
        query_report.set_filter_value({
          from_date: firstDayOfMonth,
          to_date: lastDayOfMonth,
          employee: null,
        });
      },
    },
    {
      label: __("From Date"),
      fieldtype: "Date",
      fieldname: "from_date",
      read_only: 1,
      default: frappe.datetime.month_start(frappe.datetime.get_today()),
      on_change: function (query_report) {
        var from_date = query_report.get_values().from_date;
        if (!from_date) {
          return;
        }
        let date = new moment(from_date);
        var to_date = date.endOf("month").format();
        query_report.set_filter_value({
          to_date: to_date,
        });
      },
    },
    {
      label: __("To Date"),
      fieldtype: "Date",
      fieldname: "to_date",
      reqd: 1,
      read_only: 1,
      default: frappe.datetime.month_end(frappe.datetime.get_today()),
    },
    {
      label: __("Company"),
      fieldtype: "Link",
      fieldname: "company",
      options: "Company",
      on_change: fetch_employees,
    },
    {
      label: __("Department"),
      fieldtype: "MultiSelectList",
      fieldname: "department",
      get_data: function (txt) {
        var company = frappe.query_report.get_filter_value("company");
        var filters = {};
        if (company) filters["company"] = company;
        return frappe.db.get_link_options("Department", txt, filters);
      },
      on_change: fetch_employees,
      // on_change: function (query_report) {
      // 	// 🔥 clear selected employees
      // 	query_report.set_filter_value("employees", []);

      // 	query_report.emp_count = 0;
      // 	query_report.current_emp = 0;

      // 	fetch_employees(query_report);
      // }
    },
    {
      label: __("Employees"),
      fieldname: "employees",
      fieldtype: "MultiSelectList",
      get_data: function (txt) {
        var filters = get_filter_dict(frappe.query_report);
        if (!filters) filters = {};

        if (filters.company || filters.department) {
          filters.status = ["not in", ["Inactive", "Left"]];
        }
        console.log("filters", filters, txt);

        var options = frappe.db.get_link_options("Employee", txt, filters);
        console.log("options", options);

        return options;
      },
      on_change: function (query_report) {
        var emp_list = query_report.get_filter_value("employees");
        console.log(query_report.emp_count, "emp_list", emp_list);

        query_report.current_emp = 0;
        query_report.emp_count = emp_list.length;
        set_employee(query_report, query_report.current_emp);
      },
    },
    {
      label: __("Selected Employee"),
      fieldtype: "Link",
      fieldname: "cur_employee",
      options: "Employee",
      reqd: 1,
      get_query: function () {
        var emp_list = frappe.query_report.get_filter_value("employees");
        return {
          doctype: "Employee",
          filters: { employee: ["in", emp_list] },
        };
      },
      on_change: function (query_report) {
        let emp = frappe.query_report.get_filter_value("cur_employee");
        let employees = query_report.get_filter_value("employees");
        var idx = employees.indexOf(emp);
        if (idx > 0) {
          query_report.current_emp = idx;
        }
        set_employee_details(query_report);
      },
    },
    {
      label: __("Employee"),
      fieldtype: "Link",
      fieldname: "employee",
      options: "Employee",
      reqd: 1,
      hidden: 1,
      get_query: function () {
        var filters = get_filter_dict(frappe.query_report);
        if (!filters) return;
        return {
          doctype: "Employee",
          filters: filters,
        };
      },
    },
    {
      label: "Employee Name",
      fieldtype: "Data",
      fieldname: "emp_name",
      read_only: 1,
    },
    {
      label: "Employee Designation",
      fieldtype: "Data",
      fieldname: "designation",
      read_only: 1,
    },
    {
      label: "Department Name",
      fieldtype: "Data",
      fieldname: "emp_department",
      read_only: 1,
    },
    {
      label: "Punch ID",
      fieldtype: "Data",
      fieldname: "punch_id",
      read_only: 1,
    },
    {
      label: "Shift Hours",
      fieldtype: "Float",
      fieldname: "shift_hrs",
      read_only: 1,
    },
    {
      label: __("Prev"),
      fieldtype: "Button",
      fieldname: "prev",
      depends_on:
        "eval:(frappe.query_report.emp_count>1 && frappe.query_report.current_emp != 0)",
      onclick: function () {
        var prev_emp = frappe.query_report.current_emp - 1;
        set_employee(frappe.query_report, prev_emp, true);
        if (prev_emp < 0) prev_emp = 0;
        frappe.query_report.current_emp = prev_emp;
      },
    },
    {
      label: __("Next"),
      fieldtype: "Button",
      fieldname: "next",
      width: "80",
      depends_on:
        "eval:(frappe.query_report.emp_count>1 && frappe.query_report.emp_count - 1 > frappe.query_report.current_emp)",
      onclick: function () {
        var next_emp = frappe.query_report.current_emp + 1;
        set_employee(frappe.query_report, next_emp, true);
        if (next_emp > frappe.query_report.emp_count)
          next_emp = frappe.query_report.emp_count - 1;
        frappe.query_report.current_emp = next_emp;
      },
    },
  ],
  formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);
    var time_columns = [
      "in_time",
      "out_time",
      "spent_hours",
      "late_hrs",
      "early_hrs",
      "p_out_hrs",
      "net_wrk_hrs",
      "ot_hours",
      "total_pay_hrs",
    ];
    if (data && !data.login_date) {
      value = $(`<span>${value}</span>`);
      var $value = $(value).css("font-weight", "bold");
      value = $value.wrap("<p></p>").parent().html();
    } else if (time_columns.includes(column.id) && data.attendance_date) {
      value = frappe.datetime.str_to_user(value, true);
      if (data.late_entry && ["in_time", "out_time"].includes(column.id)) {
        value = $(`<span>${value}</span>`);
        var $value = $(value).css("color", "red");
        value = $value.wrap("<p></p>").parent().html();
      }
      if (column.id == "ot_hours") {
        value = $(`<span>${value}</span>`);
        var $value = $(value).css("color", "green");
        value = $value.wrap("<p></p>").parent().html();
      }
    }
    if (
      ["ot_hours", "total_pay_hrs"].includes(column.id) &&
      ["Net Hrs w/o OT", "Net Days w/o OT"].includes(data.ot_hours)
    ) {
      value = $(`<span>${value}</span>`);
      var $value = $(value).css("color", "blue");
      value = $value.wrap("<p></p>").parent().html();
    }
    if (column.id == "late_entry" && data.attendance_date) {
      if (data.late_entry) {
        value = $(
          `<input type="checkbox" disabled="" class="disabled-selected">`,
        );
        var $value = $(value);
        value = $value.wrap("<p></p>").parent().html();
      } else {
        value = $(
          `<input type="checkbox" disabled="" class="disabled-deselected">`,
        );
        var $value = $(value);
        value = $value.wrap("<p></p>").parent().html();
      }
    }
    return value;
  },
  onload: (report) => {
    fetch_month_list();
    report.page
      .add_button("Clear Filters", function () {
        window.open("/app/query-report/Monthly%20In-Out", "_self");
      })
      .addClass("btn-info");
    report.page
      .add_button("Generate", function () {
        var emp = frappe.query_report.get_filter_value("cur_employee");
        if (!emp) {
          frappe.msgprint(__("No Employee Selected"));
        } else {
          frappe.query_report.set_filter_value({
            employee: emp,
          });
        }
        console.log(emp);
      })
      .addClass("btn-primary");
    fetch_employees(report);
  },
};

function set_employee(query_report, index, preset = false) {
  var employees = query_report.get_filter_value("employees");
  query_report.set_filter_value({
    cur_employee: employees[index] || null,
    employee: preset ? employees[index] : null,
  });
}

function set_employee_details(query_report) {
  var employee = query_report.get_filter_value("cur_employee");
  frappe.db.get_value(
    "Employee",
    employee,
    [
      "employee_name",
      "department",
      "designation",
      "attendance_device_id",
      "default_shift",
    ],
    (r) => {
      query_report.set_filter_value({
        emp_name: r.employee_name,
        designation: r.designation,
        emp_department: r.department,
        punch_id: r.attendance_device_id,
      });
      frappe.db.get_value(
        "Shift Type",
        r.default_shift,
        "shift_hours",
        (shift) => {
          query_report.set_filter_value({
            shift_hrs: shift.shift_hours,
          });
        },
      );
    },
  );
}

function fetch_employees(query_report) {
  var filters = get_filter_dict(query_report);
  if (filters) {
    frappe.db
      .get_list("Employee", {
        filters: {
          ...filters, // existing dynamic filters (if any)
          status: ["not in", ["Inactive", "Left"]],
        },
        pluck: "name",
        order_by: "name",
        limit: 30,
      })
      .then((r) => {
        console.log(r);
        query_report.set_filter_value("employees", r);

        if (r.length) {
          query_report.current_emp = 0;
          query_report.emp_count = r.length;
          set_employee(query_report, query_report.current_emp);
        } else {
          query_report.set_filter_value("employee", null);
        }
      });
  } else {
    query_report.emp_count = 0;
    query_report.set_filter_value({
      employee: null,
      employees: [],
      cur_employee: null,
      emp_name: null,
      designation: null,
      emp_department: null,
      punch_id: null,
      shift_hrs: 0,
    });
  }
}

function get_filter_dict(query_report) {
  var company = query_report.get_filter_value("company");
  var department = query_report.get_filter_value("department");

  var filters = {};
  if (company && department.length > 0) {
    filters["company"] = company;
    filters["department"] = ["in", department];
  } else if (company) {
    filters["company"] = company;
  } else if (department.length > 0) {
    filters["department"] = ["in", department];
  } else {
    return null;
  }
  return filters;
}

function fetch_month_list() {
  frappe.call({
    method:
      "gurukrupa_customizations.gurukrupa_customizations.report.monthly_in_out.monthly_in_out.get_month_range",
    freeze: false,
    callback: function (r) {
      var month = frappe.query_report.get_filter("month");
      month.df.options.push(...r.message);
      month.refresh();
    },
  });
}
