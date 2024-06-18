import datetime
import yaml
import string
from abgrid.ABGridNetwork import ABGridNetwork

from pathlib import Path


class ABGridData():

    def __init__(self, project_name, yaml_loader):
        self.configuration_file_path = Path(f"{project_name}.yaml")
        self.groups_file_paths = Path(
            "./").glob(f"{project_name}_gruppo_*.yaml")
        self.prefix = self.configuration_file_path.stem
        self.yaml_loader = yaml_loader

    def get_answersheets_data(self):
        # load configuration data
        yaml_data, validation_errors = self.yaml_loader.load_yaml(
            "configuration", self.configuration_file_path)
        # if configuration data was correctly loaded
        if yaml_data != None:
            # init sheet_data dict
            data = dict()
            # update sheet_data
            data["title"] = yaml_data["titolo"]
            data["groups"] = list(range(1, yaml_data["numero_gruppi"] + 1))
            data["likert"] = string.ascii_uppercase[:yaml_data["numero_partecipanti_per_gruppo"]]
            data["explanation"] = yaml_data["consegna"]
            data["ga_question"] = yaml_data["domandaA"]
            data["ga_question_hint"] = yaml_data["domandaA_scelte"]
            data["gb_question"] = yaml_data["domandaB"]
            data["gb_question_hint"] = yaml_data["domandaB_scelte"]
            # return sheet data
            return (data, None)
        # on validation errors
        else:
            # return None and validation errors
            return (None, validation_errors)

    def get_report_data(self, group_file_path):
        # try to load configuration data
        yaml_data, conf_validation_errors = self.yaml_loader.load_yaml(
            "configuration", self.configuration_file_path)
        # if configuration data was correctly loaded
        if yaml_data != None:
            # try to load group data
            group_yaml_data, group_validation_errors = self.yaml_loader.load_yaml(
                "group", group_file_path)
            # if group data was correctly loaded
            if group_yaml_data != None:
                # init networker
                ntw = ABGridNetwork(
                    (group_yaml_data["scelteA"], group_yaml_data["scelteB"]))
                # under this condition
                if not ntw.validate_nodes():
                    # return None and errors
                    return (None, "Letters are not correct")
                # compute networks
                ntw.compute_networks()
                # init report data
                report_data = dict()
                # update report data
                report_data["assessment_info"] = yaml_data["titolo"]
                report_data["group_id"] = f'gruppo {
                    group_yaml_data["IDGruppo"]}'
                report_data["ga_question"] = yaml_data["domandaA"]
                report_data["gb_question"] = yaml_data["domandaB"]
                report_data["edges_a"] = ntw.edges_a
                report_data["edges_b"] = ntw.edges_b
                report_data["year"] = datetime.datetime.now(datetime.UTC).year
                report_data["ga_info"] = ntw.Ga_info
                report_data["ga_data"] = ntw.Ga_data.to_dict("index")
                report_data["ga_graph"] = ntw.graphA
                report_data["gb_info"] = ntw.Gb_info
                report_data["gb_data"] = ntw.Gb_data.to_dict("index")
                report_data["gb_graph"] = ntw.graphB
                # return report data
                return (report_data, None)
            # on validation error of group data
            else:
                # return None and validation errors
                return (None, group_validation_errors)
        # on validation error of configuration data
        else:
            # return None and validation errors
            return (None, conf_validation_errors)

    def get_data(self, type, *args):
        # retrun sheets data of report data
        return self.get_answersheets_data() if type == "sheets" else self.get_report_data(*args)
