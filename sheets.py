#!/usr/bin/env python
# coding: utf-8

# # GENERATE AB-GRID SHEETS

# Author: Dr. Pierpaolo Calanna, Phd

# ## 1. IMPORTS

# In[1]:


# imports
import sys
import io
import json
import yaml
import jinja2 as jn
from cerberus import Validator

from pathlib import Path
from cerberus import Validator
from base64 import b64encode
from weasyprint import HTML


# ## 2. CONSTANTS

# In[2]:


TEMPLATES_PATH = Path("./templates/")
DATA_PATH = Path("./data/")
SHEETS_PATH = Path("./out/sheets/")

# conf yaml validator schema
CONF_YAML_SCHEMA = {
    "titolo": { "type": "string" },
    "numero_gruppi": { "type": "integer", "min": 1, "max": 20 },
    "numero_partecipanti_per_gruppo": { "type": "integer", "min": 3, "max": 26 },
    "consegna": { "type": "string" },
    "domandaA":{ "type": "string" },
    "domandaA_scelte": { "type": "string" },
    "domandaB": { "type": "string" },
    "domandaB_scelte": { "type": "string" },
}


# ## 3. FUNCTIONS

# In[18]:


def load_data(conf_file, conf_yaml_schema):
    # init validator
    validator = Validator(required_all=True)
    # try to load data
    try:
        # read yaml data
        with open(DATA_PATH / conf_file, 'r') as file:
            conf_yaml_data = yaml.safe_load(file)
        # validate conf data
        if validator.validate(conf_yaml_data, conf_yaml_schema):
            # return data
            return (conf_yaml_data, None)
        else:
            return (None, validator.errors)
    # catch eroors
    except FileNotFoundError:
        return(None,"Cannot locate files")
    except yaml.YAMLError as e:
        return (None, "Yaml files could not be parsed")
        

def generate_sheets(conf_data):
    # init dict
    sheet_data = dict()
    # compute vars
    letters = "ABCDEFGHILMNOPQRSTUVZ"
    likert = letters[:conf_data["numero_partecipanti_per_gruppo"]]
    # update sheet_data
    sheet_data["title"] = conf_data["titolo"]
    sheet_data["groups"] = list(range(1, conf_data["numero_gruppi"] +1))
    sheet_data["likert"] = likert
    sheet_data["explanation"] = conf_data["consegna"]
    sheet_data["ga_question"] = conf_data["domandaA"]
    sheet_data["ga_question_hint"] = conf_data["domandaA_scelte"]
    sheet_data["gb_question"] = conf_data["domandaB"]
    sheet_data["gb_question_hint"] = conf_data["domandaB_scelte"]
    # get report template
    tpl = e.get_template("ABGrid_sheet.html")
    # render report
    rendered_tpl = tpl.render(sheet_data);
    # save report as pdf
    HTML(string=rendered_tpl).write_pdf(SHEETS_PATH / "ABGrid_sheets.pdf")


# ## 3. SHEETS

# In[19]:


# init jinja environment
e = jn.Environment(loader=jn.FileSystemLoader(TEMPLATES_PATH))


# In[20]:


# from cli
if __name__ == '__main__' and "get_ipython" not in dir():
    if len(sys.argv) != 2:
        print("Numero non corretto di parametri")
        sys.exit()
    configuration_file = sys.argv[1] 
# from jupyter
else:
    # export jupyter notebook to python code
    get_ipython().system('jupyter nbconvert ABGrid_sheet.ipynb --to python --output "sheets.py"')
    # convert file
    configuration_file = "conf.yaml"

# notify user
print("1. Starting...")
# notify user
print(f"2. Loading data file ({configuration_file})...")
# load data
sheet_data, errors = load_data(configuration_file, CONF_YAML_SCHEMA)
# if data was correctly loaded
if (sheet_data != None):
    # notify user
    print("3. Generating sheet(s)...")
    # generate report
    generate_sheets(sheet_data)
    # notify user
    print("4. Sheet(s) generated.")
else:
    # notify user
    print(errors)


# In[ ]:




