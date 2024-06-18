import yaml
import re
import string
from pathlib import Path
from weasyprint import HTML


class ABGridDocuments():

    def __init__(self, abgrid_data, jinja_env):
        self.jinja_env = jinja_env
        self.abgrid_data = abgrid_data

    def printer_decorator(argument):
        def decorator(function):
            def wrapper(*args, **kwargs):
                print(f"generating {argument}")
                result = function(*args, **kwargs)
                print(f"{argument} generated!")
                return result
            return wrapper
        return decorator

    @staticmethod
    @printer_decorator("configuration file")
    def generate_configuration_file(project_name, n_groups, n_members_per_group, jinja_env):
        try:
            with open(Path("./abgrid/templates/") / "configuration_file.yaml", 'r') as file:
                conf_file = yaml.safe_load(file)
            conf_file["titolo"] = project_name
            conf_file["numero_gruppi"] = n_groups
            conf_file["numero_partecipanti_per_gruppo"] = n_members_per_group
            with open(f"{project_name}.yaml", 'w') as file:
                yaml.dump(conf_file, file, sort_keys=False)
        except yaml.YAMLError:
            print("Error while writing configuration file")
        except FileNotFoundError:
            print("Cannot locate configuration file template file")

    @staticmethod
    @printer_decorator("groups")
    def generate_group_inputs(project_name, number_of_groups, number_of_members_per_group, jinja_env):
        # init group files list
        groups_files = []
        # build letter list for members
        members_per_group = string.ascii_uppercase[:number_of_members_per_group]
        # get doc template
        tpl = jinja_env.get_template("group.html")
        # loop thorugh groups
        for group_id in range(1, number_of_groups+1):
            # render current group doc
            rendered_tpl = tpl.render(
                dict(groupId=group_id, members=members_per_group))
            # remove blank lines from rendered template
            rendered_tpl = "\n".join(
                [line for line in rendered_tpl.split("\n") if len(line) > 0])
            # save current group  doc as yaml
            group_file = Path(f"{project_name}_gruppo_{group_id}.yaml")
            groups_files.append(group_file)
            with open(group_file, "w") as file:
                file.write(rendered_tpl)

    @staticmethod
    def init_files(*args):
        ABGridDocuments.generate_configuration_file(*args)
        ABGridDocuments.generate_group_inputs(*args)

    def render_pdf(self, doc_type, doc_data, doc_template, doc_prefix, doc_suffix):
        # try to load sheet template
        try:
            # get doc template
            tpl = self.jinja_env.get_template(doc_template)
            # render doc
            rendered_tpl = tpl.render(doc_data)
            # build file name
            filename = re.sub("^_|_$", "", f"{doc_prefix}_{doc_type}_{doc_suffix}")
            # save doc as pdf
            HTML(string=rendered_tpl).write_pdf(f"{filename}.pdf")
            # FOR DEBUGGING
            # -----------------------------------------------------------------------------------
            # with open(f"{filename}.html"", "w") as file: file.write(rendered_tpl)
            # -----------------------------------------------------------------------------------
        # catch exceptions
        except FileNotFoundError:
            return (None, f"Cannot locate {doc_type} template file")

    @printer_decorator("sheets")
    def generate_answer_sheets(self):
        sheets_data, sheets_errors = self.abgrid_data .get_data("sheets")
        if sheets_data:
            self.render_pdf("sheet", sheets_data, "sheet.html",
                            self.abgrid_data.prefix, "")
        else:
            print(sheets_errors)

    @printer_decorator("reports")
    def generate_reports(self):
        # loop through groups
        for group_file in self.abgrid_data.groups_file_paths:
            # load report(s) data
            report_data, report_errors = self.abgrid_data.get_data(
                "reports", group_file)
            # if report(s) data was correctly loaded
            if (report_data != None):
                # generate report(s)
                self.render_pdf("report", report_data,
                                "report.html", self.abgrid_data.prefix, f"gruppo_{report_data['group_id']}")
            else:
                # notify user
                print(report_errors)
