import frappe
import json
from frappe.model.workflow import apply_workflow


# /home/frappe/frappe-bench/apps/gke_customization/gke_customization/gke_survey/page/questionnaire_runner/questionnaire_runner.py.get_questionnaire
@frappe.whitelist(allow_guest=True)
def get_questionnaire(template):
    template_doc = frappe.get_doc("Questionnaire Template", template)

    sections = frappe.get_all(
        "Questionnaire Section",
        filters={
            "questionnaire": template
        },
        fields=[
            "name",
            "section_name",
            "sequence",
            "tab",
            "depends_on",
            "sub_section"
        ],
        order_by="sequence asc"
    )

    questions = frappe.get_all(
        "Questionnaire Question",
        filters={
            "questionnaire": template
        },
        fields=[
            "name",
            "question",
            "section",
            "field_type",
            "options",
            "required",
            "sequence","require_rating","require_remark","amount","attach_img"
        ],
        order_by="section asc, sequence asc"
    )

    return {
        "template": template_doc,
        "sections": sections,
        "questions": questions
    }
DT = "Questionnaire Response"

@frappe.whitelist()
def get_my_response(questionnaire, audit_month):
    return frappe.db.get_value(
        DT,
        {"owner": frappe.session.user, "questionnaire": questionnaire, "audit_month": audit_month},
        "name",
        order_by="creation desc",
    )
    
@frappe.whitelist(allow_guest=True)
def save_response(questionnaire, answers, response=None, submit=0, branch=None,
    auditor_name=None,
    audit_month=None,
    audit_dates=None,
    unit_audited=None,
    gstin_of_unit=None,
    nature_of_operations=None,
    persons_met_during_audit=None,
    previous_audit_pending_points=None,
    serious_irregularities_found=None,
    fraud_suspected=None,
    matter_requiring_immediate_attention=None,
    employee_id=None,
    employee_name=None,
    department=None, designation=None, language=None):

    if isinstance(answers, str):
        answers = json.loads(answers)
    if not response:
        response = frappe.db.get_value(
            "Questionnaire Response",
            {"owner": frappe.session.user, "questionnaire": questionnaire, "audit_month": audit_month},
            "name",
            order_by="creation desc",
        )

    if response:
        doc = frappe.get_doc("Questionnaire Response", response)
        if doc.owner != frappe.session.user:
            frappe.throw("Not permitted")
        if doc.workflow_state != "Draft":
            frappe.throw("This response is already submitted")
        doc.set("questionnaire_answer", [])
        doc.set("questionnaire_table_response", [])
    else:
        doc = frappe.new_doc("Questionnaire Response")
        doc.submitted_by = frappe.session.user
    # doc = frappe.new_doc("Questionnaire Response")

    doc.questionnaire = questionnaire
    doc.branch = branch
    doc.auditor_name = auditor_name
    doc.audit_month = audit_month
    doc.audit_dates = audit_dates
    doc.unit_audited = unit_audited
    doc.gstin_of_unit = gstin_of_unit
    doc.nature_of_operations = nature_of_operations
    doc.persons_met_during_audit = persons_met_during_audit
    doc.previous_audit_pending_points = previous_audit_pending_points
    doc.serious_irregularities_found = serious_irregularities_found
    doc.fraud_suspected = fraud_suspected
    doc.matter_requiring_immediate_attention = matter_requiring_immediate_attention
    doc.submitted_by = frappe.session.user
    doc.employee_id = employee_id
    doc.employee_name = employee_name
    doc.department = department
    doc.designation = designation
    doc.language = language

    for row in answers:
        if row.get("field_type") == "Table":

            for idx, table_row in enumerate(row.get("table", []), start=1):

                doc.append("questionnaire_table_response",{
                    "question": row["question"],
                    "row_no": idx,
                    "row_data": json.dumps(table_row)
                })

        else:
            doc.append("questionnaire_answer", {
                "question": row["question"],
                "answer": row["answer"],
                "rating": row.get("rating") or 0,
                "remark": row.get("remark"),
                "amount": row.get("amount") or 0,
                "attach_img": row.get("attach_img")
            })

        # frappe.throw(f"answers: {row}") 
    if doc.is_new():
        doc.insert(ignore_permissions=True)  
    else:
        doc.save(ignore_permissions=True)
    if doc.workflow_state == "Draft":
            doc = apply_workflow(doc, "Update")

    if int(submit or 0):
        doc = apply_workflow(doc, "Submit")
        
    frappe.db.commit()

    return doc.name

@frappe.whitelist(allow_guest=True)
def get_child_table_fields(doctype):

    meta = frappe.get_meta(doctype)

    fields = []

    for df in meta.fields:

        if df.fieldtype in (
            "Data",
            "Int",
            "Float",
            "Currency",
            "Date",
            "Select",
            "Check",
            "Link",
            "Small Text"
        ):

            fields.append({
                "label": df.label,
                "fieldname": df.fieldname,
                "fieldtype": df.fieldtype,
                "options": df.options
            })

    return fields


@frappe.whitelist(allow_guest=True)
def get_questionnaires():
    return frappe.get_all("Questionnaire Template", fields=["name"], order_by="name" )


@frappe.whitelist(allow_guest=True)
def get_responses(questionnaire):
    return frappe.get_all("Questionnaire Response",
        filters={
            "questionnaire": questionnaire
        },
        fields=[
            "name",
            "auditor_name",
            "branch",
            "audit_dates",
            "audit_month",
            "employee_name","designation"
        ],
        order_by="creation desc"
    )

import frappe
import json

@frappe.whitelist(allow_guest=True)
def get_response(response):

    response_doc = frappe.get_doc("Questionnaire Response", response)

    template = frappe.get_doc(
        "Questionnaire Template",
        response_doc.questionnaire
    )

    sections = frappe.get_all(
        "Questionnaire Section",
        filters={
            "questionnaire": template.name
        },
        fields=[
            "name",
            "section_name",
            "sequence",
            "tab",
            "depends_on",
            "sub_section"
        ],
        order_by="sequence"
    )

    questions = frappe.get_all(
        "Questionnaire Question",
        filters={
            "questionnaire": template.name
        },
        fields=[
            "*"
        ],
        order_by="sequence"
    )

    answers = {}

    for d in response_doc.questionnaire_answer:
        answers[d.question] = {
            "answer": d.answer,
            "remark": d.remark,
            "rating": d.rating,"amount": d.amount,"attach_img": d.attach_img
        }

    tables = {}

    for d in response_doc.questionnaire_table_response:

        if d.question not in tables:
            tables[d.question] = []

        tables[d.question].append(json.loads(d.row_data))

    return {

        "response": response_doc,
        "sections": sections,
        "questions": questions,
        "answers": answers,
        "tables": tables

    }