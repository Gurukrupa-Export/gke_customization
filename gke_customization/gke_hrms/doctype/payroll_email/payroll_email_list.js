frappe.listview_settings["Payroll Email"] = {
  fields: ["status",],
  get_indicator: function (doc) {
    if (doc.status === "Draft") {
      return [__("Draft"), "red", "status,=,Draft"];
    }

    if (doc.status === "Sending") {
      return [__("Sending"), "blue", "status,=,Sending"];
    }

    if (doc.status === "Sent") {
      return [__("Sent"), "green", "status,=,Sent"];
    }

    if (doc.status === "Partial Failed") {
      return [__("Partial Failed"), "yellow", "status,=,Partial Failed"];
    }

    if (doc.status === "Failed") {
      return [__("Failed"), "red", "status,=,Failed"];
    }
  },
};
