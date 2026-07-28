# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime, timedelta
from frappe.utils import get_datetime, get_datetime_str, getdate, get_time, add_to_date, today
from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift_timings
from gke_customization.gke_hrms.utils import get_employees_by_shift


class HolidayPunch(Document):

	def on_submit(self):
		"""
		For large datasets (100+ rows), offload to a background job to avoid
		request timeouts. For small datasets, process inline as before.
		"""
		# ROW_THRESHOLD = 100

		# if len(self.details) >= ROW_THRESHOLD:
		# 	# Enqueue a background job — returns immediately to the browser
		# 	frappe.enqueue(
		# 		method=process_holiday_punch_bg,
		# 		queue="long",          # use the 'long' queue for heavy jobs
		# 		timeout=1800,          # 30 minutes max
		# 		job_id=f"holiday_punch_{self.name}",  # deduplicate re-submits
		# 		is_async=True,
		# 		now=True,
		# 		docname=self.name,
		# 	)
		# 	frappe.msgprint(
		# 		"Processing in background. You will be notified once attendance is updated.",
		# 		alert=True,
		# 	)
		# else:
		# 	# Small batch — process synchronously as before
		# 	try:
		# 		self._process_all()
		# 		frappe.msgprint("Attendance Updated")
		# 	except Exception as e:
		# 		frappe.db.rollback()
		# 		frappe.throw(str(e))

	def _process_all(self):

		try:
			self.update_emp_checkin()

			emp_map = {}

			for row in self.details:

				if not row.employee:
					continue

				emp_map.setdefault(row.employee, []).append(row)

			for emp, rows in emp_map.items():

				process_attendance_from_rows(
					rows,
					emp,
					self.shift_name,
					self.date,
				)

			frappe.msgprint("Attendance Updated")

		except Exception as e:
			frappe.db.rollback()
			frappe.throw(str(e))

	@frappe.whitelist()
	def validate_punch(self):

		shift_datetime = get_datetime(
			f"{getdate(self.date)} {get_time(self.start_time)}"
		)

		shift_det = get_employee_shift_timings(
			self.employee,
			shift_datetime,
			True,
		)[1]

		if not (
			get_datetime(self.new_punch) > shift_det.actual_start
			and get_datetime(self.new_punch) < shift_det.actual_end
		):

			frappe.throw(f"Punch must be between {shift_det.actual_start} and {shift_det.actual_end}")

	def update_emp_checkin(self):
		for punch in self.details:
			if punch.employee_checkin:
				doc = frappe.get_doc("Employee Checkin", punch.employee_checkin)
			else:
				doc = frappe.new_doc("Employee Checkin")
				doc.time = punch.time
				doc.employee = punch.employee
			doc.skip_auto_attendance = 0
			doc.log_type = punch.type
			doc.source = punch.source
			doc.save()

	@frappe.whitelist()
	def search_checkin(self):
		self.details = []
		shift_datetime = get_datetime(f"{getdate(self.date)} {get_time(self.start_time)}")

		employees = [emp.get("employee") for emp in self.employees if emp.get("employee")]

		return self.get_checkins(shift_datetime, employees)


	def get_checkins(self, shift_datetime, employee_lst=[]):
		# employee_list = frappe.db.get_list('Employee',filters={'company': self.company,'default_shift':self.shift_name},fields=['name','employee_name'])
		employee_list = get_employees_by_shift(self.shift_name, getdate(shift_datetime)) or []

		
		filters = {}
		if self.get("department"):
			filters["department"] = self.department
			filters["name"] = ["in", employee_list]
		if employee_lst:
			filter_emp = [emp for emp in employee_list if emp in employee_lst]
			filters["name"] = ["in", filter_emp]

		if filters:
			employee_list = frappe.get_all("Employee", filters, pluck="name")

		data_list = []
		for employee in employee_list:
			shift_timings = get_employee_shift_timings(employee, get_datetime(shift_datetime), True)[1] 	#for current shift
			or_filter = {
					"time":["between",[get_datetime_str(shift_timings.actual_start), get_datetime_str(shift_timings.actual_end)]]
			}
			fields = ["date(time) as date", "log_type as type", "time", "source", "name as employee_checkin", "employee", "employee_name as custom_employee_name"]
			attendance = frappe.db.get_value("Attendance", {"employee": employee, "attendance_date": getdate(shift_datetime), "docstatus":1})
			if attendance:
				or_filter["attendance"] = attendance

			data = frappe.get_all("Employee Checkin", filters= {"employee": employee}, or_filters = or_filter, fields=fields, order_by='time')
			
			if data:
				data_list.append(data)
			
		return data_list


def process_attendance_from_rows(rows, employee, shift_type, date):

	date = getdate(date)

	# if row doest have checkins then skip it
	if not any(row.get("employee_checkin") is None for row in rows):
		# frappe.msgprint(f"Employee {employee} Skipped..........")
		return

	# -------------------------
	# cancel old attendance
	# -------------------------

	if att := frappe.db.exists(
		"Attendance",
		{
			"employee": employee,
			"attendance_date": date,
			"docstatus": 1,
		},
	):
		doc = frappe.get_doc("Attendance", att)
		doc.cancel()

	# -------------------------
	# collect punches
	# -------------------------

	punches = []

	rows.sort(key=lambda x: x.time)

	for r in rows:

		if not r.time:
			continue

		dt = get_datetime(r.time)

		punches.append(dt)

	if not punches:
		return

	# -------------------------
	# first IN last OUT
	# -------------------------

	in_time = punches[0]
	out_time = punches[-1]

	if out_time <= in_time:
		return

	working_hours = (out_time - in_time).total_seconds() / 3600

	# -------------------------
	# create attendance
	# -------------------------

	att = frappe.new_doc("Attendance")

	att.employee = employee
	att.attendance_date = date
	att.shift = shift_type
	att.in_time = in_time
	att.out_time = out_time
	att.working_hours = working_hours

	if working_hours > 0:
		att.status = "Present"
	else:
		att.status = "Absent"

	att.insert()
	att.submit()

	# link checkin record with attendance
	all_checkins = frappe.get_all("Employee Checkin", {"employee": employee, "time": ["between", [in_time, out_time]]}, "name")
	for checkin in all_checkins:
		frappe.db.set_value("Employee Checkin", checkin.name, "attendance", att.name)

@frappe.whitelist()
def add_checkins(details, date, shift_name):

	if isinstance(details, str):
		details = frappe.json.loads(details)

	date = getdate(date)
	employee_details = {}

	# group by employee
	for entry in details:
		emp = entry["employee"]
		employee_details.setdefault(emp, []).append(entry)

	merged_data = []

	for emp, emp_rows in employee_details.items():

		one_data = check_employee_punch(
			emp_rows,
			date,
			shift_name
		)

		merged_data.extend(one_data)

	# fix idx
	for i, row in enumerate(merged_data, start=1):
		row["idx"] = i

	return merged_data


def check_employee_punch(employee_details, shift_date, shift_name):

	if not employee_details:
		return employee_details

	shift_doc = frappe.get_doc("Shift Type", shift_name)

	start_time_obj = get_time(shift_doc.start_time)
	end_time_obj = get_time(shift_doc.end_time)

	is_night_shift = start_time_obj > end_time_obj

	employee_details.sort(key=lambda x: x["time"])

	shift_start_dt = get_datetime(f"{shift_date} {start_time_obj}")
	actual_start_dt = shift_start_dt - timedelta(minutes=shift_doc.get("begin_check_in_before_shift_start_time", 0))


	if is_night_shift:
		shift_end_date = add_to_date(shift_date, days=1)
	else:
		shift_end_date = shift_date

	shift_end_dt = get_datetime(f"{shift_end_date} {end_time_obj}")

	# -------------------------
	# check if any punch after shift end
	# -------------------------

	for d in employee_details:
		dt = get_datetime(d["time"])

		if dt >= shift_end_dt:
			return employee_details  # shift already completed

	# -------------------------
	# punches inside shift
	# -------------------------

	punches = []

	# emp = ''
	for d in employee_details:
		dt = get_datetime(d["time"])
		# emp = d.get("employee")

		if actual_start_dt <= dt <= shift_end_dt:
			punches.append(dt)

	if not punches:
		return employee_details

	last_dt = punches[-1]

	count = len(punches)

	# -------------------------
	# odd → need OUT
	# even → need IN + OUT
	# -------------------------

	if count % 2 == 1:

		employee_details.append(
			make_row(employee_details, "OUT", shift_end_dt)
		)

	else:

		employee_details.append(
			make_row(employee_details, "IN", add_to_date(last_dt))
			# make_row(employee_details, "IN", add_to_date(last_dt, minutes=1))
		)

		employee_details.append(
			make_row(employee_details, "OUT", shift_end_dt)
		)

	return employee_details


def make_row(employee_details, punch_type, dt):

	last = employee_details[-1]

	return {
		"date": str(dt.date()),
		"type": punch_type,
		"employee": last.get("employee"),
		"custom_employee_name": last.get("custom_employee_name"),
		"time": dt,
		"source": "Employee Checkin",
		"idx": "",
	}


def process_holiday_punch_bg(docname):
    """Called by the Frappe background worker."""		
    try:
        doc = frappe.get_doc("Holiday Punch", docname)
        doc._process_all()
        frappe.db.commit()

        # Notify the submitter
        frappe.msgprint(
            msg=f"Holiday Punch {docname} — Attendance Updated",
            alert=True,
            indicator="green"
        )
    except Exception:
        frappe.db.rollback()
        frappe.log_error(message=frappe.get_traceback(), title=f"Holiday Punch BG Error: {docname}")
        frappe.msgprint(
            msg=f"Holiday Punch {docname} — Error",
            alert=True,
            indicator="red",
        )


# new method
# method="gke_customization.gke_hrms.doctype.holiday_punch.holiday_punch.process_checkins"
def process_checkins(docname):
    try:
        doc = frappe.get_doc("Holiday Punch", docname)

        # Step 1: Cancel old attendance
        for row in doc.details:
            if row.employee:
                att = frappe.db.get_value(
                    "Attendance",
                    {
                        "employee": row.employee,
                        "attendance_date": doc.date,
                        "docstatus": 1
                    }
                )
                if att:
                    frappe.db.set_value("Attendance", att, "docstatus", 2)

        # Step 2: Create / Update checkins
        doc.update_emp_checkin()

        # Step 3: Update workflow state
        frappe.db.set_value(doc.doctype, doc.name, "workflow_state", "Checkin Created")

        frappe.db.commit()

    except Exception:
        frappe.db.rollback()
        error = frappe.get_traceback()
        # Error log create
        log = frappe.log_error(
            title=f"Holiday Punch: {doc.name}",
            message=error
        )

        # Update document
        doc.db_set("workflow_state", "Failed")
        doc.db_set(
            "error_details",
            f"""
                Process failed.

                Check Error Log: {log.name}

                {str(error)}
                """
                        )

        frappe.db.commit()
    

# method="gke_customization.gke_hrms.doctype.holiday_punch.holiday_punch.process_attendance"
def process_attendance(docname):
    try:
        doc = frappe.get_doc("Holiday Punch", docname)

        emp_map = {}

        # Group by employee
        for row in doc.details:
            if not row.employee:
                continue
            emp_map.setdefault(row.employee, []).append(row)

        # Process attendance
        for emp, rows in emp_map.items():
            process_attendance_from_rows(
                rows,
                emp,
                doc.shift_name,
                doc.date
            )

        # Update workflow state
        frappe.db.set_value(doc.doctype, doc.name, "workflow_state", "Attendance Created")

        frappe.db.commit()

    except Exception:
        frappe.db.rollback()
        error = frappe.get_traceback()
        # Error log create
        log = frappe.log_error(
            title=f"Holiday Punch: {doc.name}",
            message=error
        )

        # Update document
        doc.db_set("workflow_state", "Failed")
        doc.db_set(
            "error_details",
            f"""
                Process failed.

                Check Error Log: {log.name}

                {str(error)}
                """
                        )

        frappe.db.commit()
        
        
@frappe.whitelist()
def enqueue_modify_checkin(docname):

    job = frappe.enqueue(
        method="gke_customization.gke_hrms.doctype.holiday_punch.holiday_punch.process_checkins",
        queue="long",
        timeout=10000,
        job_name=f"Modify Checkin {docname}",
        now=False,
        docname=docname,
    )

    frappe.msgprint(f"Job Enqueued: {job.id}")
    return job.id


@frappe.whitelist()
def enqueue_modify_attendance(docname):

    job = frappe.enqueue(
        method="gke_customization.gke_hrms.doctype.holiday_punch.holiday_punch.process_attendance",
        queue="long",
        timeout=10000,
        job_name=f"Modify Attendance {docname}",
        now=False,
        docname=docname
    )

    frappe.msgprint(f"Job Enqueued: {job.id}")
    return job.id



@frappe.whitelist()
def get_employees(doc):

    doc = frappe._dict(frappe.parse_json(doc))
    
    # store combined employee + shift assignment data
    merge_data = []
    
    # =====================================================
    # Employee Filters
    # =====================================================
    employee_filters = {
        "company": doc.company,
        "default_shift": doc.shift_name,
        "status": "Active"
    }

    # add department filter dynamically
    if doc.department:
        employee_filters["department"] = doc.department

    # =====================================================
    # Fetch employees whose default shift
    # matches selected shift
    # =====================================================
    employee_data = frappe.get_all(
        "Employee",
        filters=employee_filters,
        fields=[
            "name",
            "employee_name",
            "default_shift"
        ]
    )
    merge_data.extend(employee_data)
    
    # =====================================================
    # Fetch employees having valid shift assignment
    # for selected date and shift
    # =====================================================
    shift_assignments = get_shift(
        doc.company,
        doc.shift_name,
        doc.date
    )

    # merge shift assignment records
    merge_data.extend(shift_assignments)
        
    # =====================================================
    # Remove duplicate employees  Duplicate check based on employee ID (name)
    # =====================================================
    employee_data = []
    seen = set()

    for row in merge_data:

        if row["name"] not in seen:

            employee_data.append(row)
            seen.add(row["name"])
    
    # =====================================================
    # Cross verify actual shift of employee # Shift Assignment takes priority over default shift
    # =====================================================
    data = []
    for row in employee_data:
        final_data = get_employee_shift(row["name"], doc.date)
                
        if final_data:
            for f in final_data:
                if f.get("default_shift") == doc.shift_name:
                    data.append(f)

    return data

# get shift  with name, employee_name, default_shift
@frappe.whitelist()
def get_shift(company, shift_type, for_date=None):
    if not for_date:
        for_date = today()

    for_date = getdate(for_date)

	# =====================================================
    # Fetch valid shift assignments
    #
    # Conditions:
    # 1. start_date <= selected date
    # 2. end_date is blank (open assignment)
    #    OR
    # 3. end_date >= selected date
    # =====================================================
    shift_data = frappe.get_all(
        "Shift Assignment",
        filters={
            "company": company,
            "shift_type": shift_type,
            "docstatus": 1,
            "status": "Active"
        },
        or_filters=[
            {"start_date": ("<=", for_date)},
            {"start_date": (">=", for_date)},
            {"end_date": ("is", "not set")},
            {"end_date": (">=", for_date)}
        ],
        fields=[
            "employee as name",
            "employee_name",
            "shift_type as default_shift"
        ]
    )

    return shift_data

# Get employee final shift for selected date
@frappe.whitelist()
def get_employee_shift(employee, for_date=None):
    if not for_date:
        for_date = today()

    for_date = getdate(for_date)

    # =====================================================
    # Fetch active shift assignment
    #
    # Conditions:
    # 1. start_date <= selected date
    # 2. end_date is blank
    #    OR
    # 3. end_date exists
    # =====================================================
    shift = frappe.db.get_all(
        "Shift Assignment",
        filters={
            "employee": employee,
            "docstatus": 1,
            "status": "Active"
        },
        or_filters=[
            {"start_date": ("<=", for_date)},
            {"start_date": (">=", for_date)},
            {"end_date": ("is", "not set")}, 
            {"end_date": ("is", "set")}
        ],
        fields=["shift_type as default_shift","employee as name"]
    )               

    # =====================================================
    # If valid shift assignment exists,
    # return assigned shift
    # =====================================================
    if shift:
        return shift

    # =====================================================
    # Fallback to Employee default shift
    # when no Shift Assignment exists
    # =====================================================
    return frappe.db.get_all(
        "Employee",
        filters={
            "name": employee
        },
        fields=["default_shift","name"]
    )