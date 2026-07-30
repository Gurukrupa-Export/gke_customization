let page;
let template_field;

frappe.pages["questionnaire-runner"].on_page_load = function(wrapper) {

    page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Questionnaire Runner",
        single_column: true
    });

    template_field = page.add_field({
        label: "Questionnaire Template",
        fieldname: "questionnaire",
        fieldtype: "Link",
        options: "Questionnaire Template"
    });

    page.set_primary_action("Load Questionnaire", load_questionnaire);

    $(page.body).append(`
        <div id="questionnaire-container" class="mt-4"></div>
    `);
};

function load_questionnaire() {

    let questionnaire = template_field.get_value();

    if (!questionnaire) {
        frappe.msgprint("Please select Questionnaire");
        return;
    }

    frappe.call({
        method: "gke_customization.gke_survey.page.questionnaire_runner.questionnaire_runner.get_questionnaire",
        args: {
            template: questionnaire
        },
        callback: function(r) {

            render_questionnaire(r.message);

            // Change button after loading
            page.set_primary_action("Submit", submit_questionnaire);

        }
    });

}

function submit_questionnaire() {

    let answers = [];

    Object.values(questionnaire_controls).forEach(item => {

        answers.push({
            question: item.question.name,
            answer: item.control.get_value()
        });

    });

    frappe.call({
        method: "gke_customization.gke_survey.page.questionnaire_runner.questionnaire_runner.save_response",
        args: {
            questionnaire: template_field.get_value(),
            answers: answers
        },
        callback: function(r) {

            frappe.msgprint("Questionnaire Saved Successfully");

            console.log(r.message);

        }
    });

}


function render_questionnaire(data) {

    $("#questionnaire-container").empty();

    // Store controls globally for save later
    window.questionnaire_controls = {};

    data.sections.forEach(section => {

        let section_wrapper = $(`
            <div class="questionnaire-section mb-5">
                <h4>${section.section_name}</h4>
                <hr>
                <div class="row questions-row"></div>
            </div>
        `);

        $("#questionnaire-container").append(section_wrapper);

        let questions = data.questions.filter(q => {
            return q.section === section.name;
        });

        questions.forEach(question => {

            let col_size = question.width || 4; // default 3 columns

            let field_wrapper = $(`
                <div class="col-md-${col_size} mb-3">
                </div>
            `);

            section_wrapper.find(".questions-row").append(field_wrapper);

            let df = {
                label: question.question,
                fieldname: question.fieldname || frappe.scrub(question.question),
                fieldtype: question.field_type || "Data",
                reqd: question.mandatory || 0
            };

            // Select field
            if (question.field_type === "Select") {
                df.options = question.options;
            }

            // Link field
            if (question.field_type === "Link") {
                df.options = question.options;
            }

            // Check field
            if (question.field_type === "Check") {
                df.default = 0;
            }

            let control = frappe.ui.form.make_control({
                parent: field_wrapper,
                df: df,
                render_input: true
            });

            // Save reference for submit later
            window.questionnaire_controls[df.fieldname] = {
                control: control,
                question: question
            };
        });

    });
}