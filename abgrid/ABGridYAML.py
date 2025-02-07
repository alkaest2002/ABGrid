import yaml

from cerberus import Validator, DocumentError, SchemaError


class ABGridYAML(object):

    def __init__(self):
        self.validator = Validator(require_all=True) # type: ignore
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
            self.validator.validate(yaml_data, yaml_schema) # type: ignore
            # return validation errors dict (if validation is passed dict wiil be empty)
            return self.validator.errors # type: ignore
        # catch exceptions
        except DocumentError:
            # return error message
            return "Document was loaded but cannot be evaluated."
        except SchemaError:
            # return error message
            return "Invalid yaml validation schema."

    def load_yaml(self, yaml_type, yaml_file_path):
        try:
            # open yaml file
            with open(yaml_file_path, 'r') as file:
                # parse yaml data
                yaml_data = yaml.safe_load(file)
            # if validation is not ok
            if validation_errors := self.validate(yaml_type, yaml_data):
                # return None as data and errors
                return (None, validation_errors)
            # on validation error
            else:
                # return yaml data and None as errors
                return (yaml_data, None)
        # catch exceptions
        except FileNotFoundError:
            # return None as data and errors
            return (None, "Cannot locate Yaml file.")
        except yaml.YAMLError as e:
            print(e)
            # return None as data and errors
            return (None, "Yaml file could not be parsed.")
