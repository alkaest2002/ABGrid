import datetime
import string

from pathlib import Path
from abgrid.ABGridNetwork import ABGridNetwork

class ABGridData(object):

    def __init__(self, project, yaml_loader):
      self.project = project
      self.project_filepath = Path(f"{project}.yaml")
      self.groups_filepaths = list(Path(
          "./").glob(f"{project}_gruppo_*.yaml"))
      self.yaml_loader = yaml_loader

    def get_answersheets_data(self):
      # load project data
      yaml_data, validation_errors = self.yaml_loader.load_yaml(
          "project", self.project_filepath)
      # if project data was correctly loaded
      if yaml_data != None:
          # init sheet data dict
          data = dict()
          # update sheet data
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

    def get_report_data(self, group_filepath):
        # try to load project data
        yaml_data, project_validation_errors = self.yaml_loader.load_yaml(
            "project", self.project_filepath)
        # if project data was correctly loaded
        if yaml_data != None:
          # try to load group data
          group_yaml_data, group_validation_errors = self.yaml_loader.load_yaml(
              "group", group_filepath)
          # if group data was correctly loaded
          if group_yaml_data != None:
            # init ABGridNetwork class
            ntw = ABGridNetwork(
                (group_yaml_data["scelteA"], group_yaml_data["scelteB"]))
            # in case of nodes mismatch
            if not ntw.validate_nodes():
                # return None and errors
                return (None, f"Choices within group {group_yaml_data['IDGruppo']} file are not correct.")
            # compute networks
            ntw.compute_networks()
            # init report data
            report_data = dict()
            # update report data
            report_data["assessment_info"] = yaml_data["titolo"]
            report_data["group_id"] = group_yaml_data["IDGruppo"]
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
            return (None, project_validation_errors)
