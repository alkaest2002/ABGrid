import yaml

from pathlib import Path
from cerberus import Validator, DocumentError, SchemaError


class ABGridYAML(object):

    def __init__(self):
        self.validator = Validator(required_all=True)
        self.project_schema = {
            "titolo": {"type": "string"},
            "numero_gruppi": {"type": "integer", "min": 1, "max": 20},
            "numero_partecipanti_per_gruppo": {"type": "integer", "min": 3, "max": 15},
            "consegna": {"type": "string"},
            "domandaA": {"type": "string"},
            "domandaA_scelte": {"type": "string"},
            "domandaB": {"type": "string"},
            "domandaB_scelte": {"type": "string"},
        }
        self.group_schema = {
            "IDGruppo": {
                "type": "integer",
                "min": 1,
                "max": 20
            },
            "scelteA": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "keysrules": {"type": "string", "regex": "^[A-Z]{1,1}$"},
                    "valuesrules": {"type": "string", "regex": "^([A-Z]{1,1},)*[A-Z]$"}
                }
            },
            "scelteB": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "keysrules": {"type": "string", "regex": "^[A-Z]{1,1}$"},
                    "valuesrules": {"type": "string", "regex": "^([A-Z]{1,1},)*[A-Z]$"}
                }
            }
        }

    def validate(self, yaml_type, yaml_data):
        # choose type of validation schema
        yaml_schema = self.project_schema if yaml_type == "project" else self.group_schema
        try:
            # validate data
            self.validator.validate(yaml_data, yaml_schema)
            # return validation errors dict (if validation is paddes dict is empty)
            return self.validator.errors
        # catch exceptions
        except DocumentError as e:
            # return error message
            return "Document was loaded but cannot be evaluated."
        except SchemaError as e:
            # return error message
            return "Invalid yaml validation schema."

    def load_yaml(self, yaml_type, yaml_file_path):
        try:
            # open yaml file
            with open(yaml_file_path, 'r') as file:
                # parse yaml data
                yaml_data = yaml.safe_load(file)
            # validate yaml data
            validation_errors = self.validate(yaml_type, yaml_data)
            # if validation is ok
            if not validation_errors:
                # return yaml data and None as errors
                return (yaml_data, None)
            # on validation error
            else:
                # return None as data and errors
                return (None, validation_errors)
        # catch exceptions
        except FileNotFoundError:
            # return None as data and errors
            return (None, "Cannot locate Yaml file.")
        except yaml.YAMLError as e:
            # return None as data and errors
            return (None, "Yaml file could not be parsed.")
