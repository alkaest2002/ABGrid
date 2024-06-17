from cerberus import Validator


class ABGridValidator():

  def __init__(self):
      self.validator = Validator(required_all=True)
      self.conf_file_schema = {
          "titolo": {"type": "string"},
          "numero_gruppi": {"type": "integer", "min": 1, "max": 20},
          "numero_partecipanti_per_gruppo": {"type": "integer", "min": 3, "max": 12},
          "consegna": {"type": "string"},
          "domandaA": {"type": "string"},
          "domandaA_scelte": {"type": "string"},
          "domandaB": {"type": "string"},
          "domandaB_scelte": {"type": "string"},
      }
      self.group_file_schema = {
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
                  "keysrules": {"type": "string", "regex": "^[A-Z]{1,1}$"},
                  "valuesrules": {"type": "string", "regex": "^([A-Z]{1,1},)*[A-Z]$"}
              }
          }
      }

  def validate(self, type, data):
    schema = self.conf_file_schema if type == "configuration" else self.group_file_schema
    try:
      if self.validator.validate(data, schema):
          # return True as validation check and None as errors
          return (True, None)
      # on validation error
      else:
          # return False as validation check and relevant errors messages
          return (False, validator.errors)
    except cerberus.DocumentError as e:
      # return False as validation check and relevant errors messages
      return (False, "Document was loaded but cannot be evaluated")
    except cerberus.SchemaError as e:
      # return False as validation check and relevant errors messages
      return (False, "Invalid yaml validation schema")
