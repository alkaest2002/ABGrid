import yaml
import re
import string
import jinja2
import json

from pathlib import Path
from weasyprint import HTML
from abgrid.ABGridErrors import ValidationError

# init jinja environment
jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(["./abgrid/templates", "./templates"]))


class ABGridDocuments(object):

    def __init__(self, abgrid_data):
        self.abgrid_data = abgrid_data

    # decorator to add print messages
    def notify_decorator(argument):
        def decorator(function):
            def wrapper(*args, **kwargs):
                print(f"Generating {argument} file(s).")
                try:
                    result = function(*args, **kwargs)
                    print(f"{argument} file(s) generated.")
                    return result
                except Exception as error:
                    print(f"Error while generating {
                          argument} file(s).", "\n", error)
            return wrapper
        return decorator

    @staticmethod
    @notify_decorator("project")
    def generate_project_file(project_name, n_groups, n_members_per_group):
        # open project file template
        with open(Path("./abgrid/templates/project.yaml"), 'r') as fin:
            # load yaml data
            yaml_data = yaml.safe_load(fin)
        # update yaml data
        yaml_data["titolo"] = project_name
        yaml_data["numero_gruppi"] = n_groups
        yaml_data["numero_partecipanti_per_gruppo"] = n_members_per_group
        # write yaml data to file
        with open(f"{project_name}.yaml", 'w') as fout:
            yaml.dump(yaml_data, fout, sort_keys=False)

    @staticmethod
    @notify_decorator("group")
    def generate_group_inputs(project_name, n_groups, n_members_per_group):
        # build letter list for members (i.e., 5 --> A,B,C,D,E)
        members_per_group = string.ascii_uppercase[:n_members_per_group]
        # get group template
        tpl = jinja_env.get_template("group.html")
        # loop thorugh groups
        for group_id in range(1, n_groups+1):
            # set template data
            tpl_data = dict(groupId=group_id, members=members_per_group)
            # render current group template
            rendered_tpl = tpl.render(tpl_data)
            # remove blank lines from rendered template
            rendered_tpl = "\n".join(
                [line for line in rendered_tpl.split("\n") if len(line) > 0])
            # write rendered template to disk
            with open(Path(f"{project_name}_gruppo_{group_id}.yaml"), "w") as file:
                file.write(rendered_tpl)

    @staticmethod
    def init_files(*args):
        # generate project file
        ABGridDocuments.generate_project_file(*args)
        # generate group files
        ABGridDocuments.generate_group_inputs(*args)

    def render_pdf(self, doc_type, doc_data, doc_suffix):
        # set template
        doc_template = f"{doc_type}.html"
        # get template
        tpl = jinja_env.get_template(doc_template)
        # render template
        rendered_tpl = tpl.render(doc_data)
        # build file name
        filename = re.sub("^_|_$", "", f"{self.abgrid_data.project}_{
                          doc_type}_{doc_suffix}")
        # save rendered template as pdf
        HTML(string=rendered_tpl).write_pdf(f"{filename}.pdf")
        # -----------------------------------------------------------------------------------
        # FOR DEBUGGING PURPOSES
        # -----------------------------------------------------------------------------------
        # with open(f"{filename}.html"", "w") as file: file.write(rendered_tpl)
        # -----------------------------------------------------------------------------------

    @notify_decorator("sheet")
    def generate_answer_sheets(self):
        # load sheet(s) data
        sheets_data, sheets_errors = self.abgrid_data.get_answersheets_data()
        # on error
        if sheets_errors:
            raise ValidationError(sheets_errors)
        # render sheets
        self.render_pdf("sheet", sheets_data, "")

    @notify_decorator("report")
    def generate_reports(self):
        # init report data object
        all_data = {}
        # check if group file(s) are present, otherwise raise error
        if len(self.abgrid_data.groups_filepaths) == 0:
            raise ValidationError(f"Group file(s) for {
                                  self.abgrid_data.project} are missing")
        # loop through groups
        for group_file in self.abgrid_data.groups_filepaths:
            # load report data for current group
            report_data, report_errors = self.abgrid_data.get_report_data(
                group_file)
            # on errors
            if report_errors:
                raise ValidationError(report_errors)
            # add current group data
            all_data[f"{self.abgrid_data.project}_gruppo_{
                report_data['group_id']}"] = report_data
            # render report
            self.render_pdf("report", report_data, f"gruppo_{
                            report_data['group_id']}")
        # save all data
        with open(Path(f"./{self.abgrid_data.project}_data.json"), "w") as fout:
            fout.write(json.dumps(all_data))
