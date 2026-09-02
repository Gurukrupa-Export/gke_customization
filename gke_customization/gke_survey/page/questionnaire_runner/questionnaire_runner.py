import frappe
import json


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
            "sequence","require_rating","require_remark"
        ],
        order_by="section asc, sequence asc"
    )

    return {
        "template": template_doc,
        "sections": sections,
        "questions": questions
    }

@frappe.whitelist(allow_guest=True)
def save_response(questionnaire,answers,branch=None,
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
    department=None):

    if isinstance(answers, str):
        answers = json.loads(answers)

    response = frappe.new_doc("Questionnaire Response")

    response.questionnaire = questionnaire
    response.branch = branch
    response.auditor_name = auditor_name
    response.audit_month = audit_month
    response.audit_dates = audit_dates
    response.unit_audited = unit_audited
    response.gstin_of_unit = gstin_of_unit
    response.nature_of_operations = nature_of_operations
    response.persons_met_during_audit = persons_met_during_audit
    response.previous_audit_pending_points = previous_audit_pending_points
    response.serious_irregularities_found = serious_irregularities_found
    response.fraud_suspected = fraud_suspected
    response.matter_requiring_immediate_attention = matter_requiring_immediate_attention
    response.submitted_by = frappe.session.user
    response.employee_id = employee_id
    response.employee_name = employee_name
    response.department = department

    for row in answers:
        if row.get("field_type") == "Table":

            for idx, table_row in enumerate(row.get("table", []), start=1):

                response.append("questionnaire_table_response",{
                    "question": row["question"],
                    "row_no": idx,
                    "row_data": json.dumps(table_row)
                })

        else:
            response.append("questionnaire_answer", {
                "question": row["question"],
                "answer": row["answer"],
                "rating": row.get("rating") or 0,
                "remark": row.get("remark")
            })

        # frappe.throw(f"answers: {row}") 
    response.insert(ignore_permissions=True)

    frappe.db.commit()

    return response.name

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
            "employee_name"
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
            "rating": d.rating
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