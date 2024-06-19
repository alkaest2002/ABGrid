import yaml
import re
import string
import json
from pathlib import Path
from weasyprint import HTML


class ABGridDocuments():

    def __init__(self, abgrid_data, jinja_env):
        self.jinja_env = jinja_env
        self.abgrid_data = abgrid_data

    # decorator to add print messages
    def notify_decorator(argument):
        def decorator(function):
            def wrapper(*args, **kwargs):
                print(f"Generating {argument} file(s).")
                try:
                    return function(*args, **kwargs)
                except Exception as error:
                    print(f"Error while generating {argument} file(s).", "\n", error)
            return wrapper
        return decorator

    @staticmethod
    @notify_decorator("project")
    def generate_configuration_file(project_name, n_groups, n_members_per_group, jinja_env):
        # open configuration file template
        with open(Path("./abgrid/templates/") / "configuration_file.yaml", 'r') as fin:
            # load yaml data
            yaml_data = yaml.safe_load(fin)
        # update yaml data
        yaml_data["titolo"] = project_name
        yaml_data["numero_gruppi"] = n_groups
        yaml_data["numero_partecipanti_per_gruppo"] = n_members_per_group
        # write yaml data to file
        with open(f"{project_name}.yaml", 'w') as fout:
            yaml.dump(yaml_data, fout, sort_keys=False)
        # notify
        print("Project file generated.")

    @staticmethod
    @notify_decorator("group")
    def generate_group_inputs(project_name, number_of_groups, number_of_members_per_group, jinja_env):
        # init group files list
        groups_files = []
        # build letter list for members (i.e., 5 --> A,B,C,D,E)
        members_per_group = string.ascii_uppercase[:number_of_members_per_group]
        # get group template
        tpl = jinja_env.get_template("group.html")
        # loop thorugh groups
        for group_id in range(1, number_of_groups+1):
            # render current group template
            rendered_tpl = tpl.render(
                dict(groupId=group_id, members=members_per_group))
            # remove blank lines from rendered template
            rendered_tpl = "\n".join(
                [line for line in rendered_tpl.split("\n") if len(line) > 0])
            # save current rendered to file
            group_file = Path(f"{project_name}_gruppo_{group_id}.yaml")
            groups_files.append(group_file)
            with open(group_file, "w") as file:
                file.write(rendered_tpl)
        # notify
        print("Group file(s) generated.")

    @staticmethod
    def init_files(*args):
        # generate configuration file and group files
        ABGridDocuments.generate_configuration_file(*args)
        ABGridDocuments.generate_group_inputs(*args)

    def render_pdf(self, doc_type, doc_data, doc_template, doc_prefix, doc_suffix):
        # get template
        tpl = self.jinja_env.get_template(doc_template)
        # render template
        rendered_tpl = tpl.render(doc_data)
        # build file name
        filename = re.sub("^_|_$", "", f"{doc_prefix}_{doc_type}_{doc_suffix}")
        # save rendered template as pdf
        HTML(string=rendered_tpl).write_pdf(f"{filename}.pdf")
        # -----------------------------------------------------------------------------------
        # FOR DEBUGGING PURPOSES
        # -----------------------------------------------------------------------------------
        # with open(f"{filename}.html"", "w") as file: file.write(rendered_tpl)
        # -----------------------------------------------------------------------------------

    @notify_decorator("sheet")
    def generate_answer_sheets(self):
        # get sheets data
        sheets_data, sheets_errors = self.abgrid_data.get_data("sheets")
        # on error
        if sheets_errors:
            raise Exception(sheets_errors)
        # generate sheets
        self.render_pdf("sheet", sheets_data, "sheet.html",
                        self.abgrid_data.prefix, "")
        # notify
        print("Sheet file(s) generated.")

    @notify_decorator("report")
    def generate_reports(self):
        # loop through groups
        for group_file in self.abgrid_data.groups_file_paths:
            # load report(s) data
            report_data, report_errors = self.abgrid_data.get_data(
                "reports", group_file)
            # on error
            if report_errors:
                raise Exception(report_errors)
            # generate report(s)
            self.render_pdf("report", report_data,
                            "report.html", self.abgrid_data.prefix, f"gruppo_{report_data['group_id']}")
        # notify
        print("Report file(s) generated.")
