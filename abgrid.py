#!/usr/bin/env python
# coding: utf-8

# # GENERATE AB-GRID REPORT

# Author: Dr. Pierpaolo Calanna, Phd

# ## 1. IMPORTS

# In[9]:


# imports
import sys
import os
import io
import re
import argparse
import json
import datetime
import yaml
import cerberus
import numpy as np
import pandas as pd
import networkx as nx
import networkx.algorithms.connectivity as nxcon
import matplotlib
import matplotlib.pyplot as plt
import jinja2 as jn

from pathlib import Path
from base64 import b64encode
from cerberus import Validator
from weasyprint import HTML

# customize matplotlib
font = {'size' : 8}
matplotlib.rc('font', **font)
matplotlib.use("Agg")


# ## 2. CONSTANTS

# In[10]:


# folder path constants
TEMPLATES_PATH = Path("./templates/")
DATA_PATH = Path("./data/")
REPORTS_PATH = Path("./out/reports/")
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

# group yaml validator schema
GROUP_YAML_SCHEMA = {
    "IDGruppo": {
        "type": "integer",
        "min": 1,
        "max": 20
    },
    "scelteA": {
        "type": "list",
        "schema":{
            "type": "dict",
            "keysrules": {"type": "string", "regex": "^[A-Z]{1,1}$"},
            "valuesrules": {"type": "string", "regex": "^[A-Z,]*,[A-Z]$"}
        }
    },
    "scelteB": {
        "type": "list",
        "schema":{
            "type": "dict",
            "keysrules": {"type": "string", "regex": "^[A-Z]{1,1}$"},
            "valuesrules": {"type": "string", "regex": "^[A-Z,]*,[A-Z]$"}
        }
    }
}


# ## 3. FUNCTIONS

# ### 3.1 Function related to DATA

# In[11]:


def load_yaml_file(yaml_file, yaml_schema, validator):
    # try to load data
    try:
        # open yaml file
        with open(yaml_file, 'r') as file:
            # parse yaml data
            yaml_data = yaml.safe_load(file)
        # if yaml data validates
        if validator.validate(yaml_data, yaml_schema):
            # return yaml data and None as errors
            return (yaml_data, None)
        # on validation error
        else:
            # return None as data and errors
            return (None, validator.errors)
    # catch exceptions
    except FileNotFoundError:
        return(None,"Cannot locate files")
    except yaml.YAMLError as e:
        return (None, "Yaml files could not be parsed")
    except cerberus.DocumentError as e:
        return (None, "Document was loaded but cannot be evaluated")
    except cerberus.SchemaError as e:
        return (None, "Invalid yaml validation schema")
    
def get_sheets_data(conf_file, conf_yaml_schema):
    # init validator
    validator = Validator(required_all=True)
    # load sheet data
    sheets_yaml_data, validation_errors = load_yaml_file(DATA_PATH / conf_file, conf_yaml_schema, validator)
    # if configuration data was correctly loaded
    if sheets_yaml_data != None:
        # init dict
        sheets_data = dict()
        # compute likert
        likert = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[:sheets_yaml_data["numero_partecipanti_per_gruppo"]]
        # update sheet_data
        sheets_data["title"] = sheets_yaml_data["titolo"]
        sheets_data["groups"] = list(range(1, sheets_yaml_data["numero_gruppi"] +1))
        sheets_data["likert"] = likert
        sheets_data["explanation"] = sheets_yaml_data["consegna"]
        sheets_data["ga_question"] = sheets_yaml_data["domandaA"]
        sheets_data["ga_question_hint"] = sheets_yaml_data["domandaA_scelte"]
        sheets_data["gb_question"] = sheets_yaml_data["domandaB"]
        sheets_data["gb_question_hint"] = sheets_yaml_data["domandaB_scelte"]
        # return sheet data
        return (sheets_data, None)
    # on validation errors
    else:
        # return None and validation errors
        return (None, validation_errors)

def unpack_edges(data):
    # init edges list
    unpacked_edges = [];
    # loop through rows in data
    for row in data:
        # loop through nodes and edges
        for node, edges in row.items():
            # split edges
            for edge in edges.split(","):
                # append edge to edges list
                unpacked_edges.append((node, edge))
    # return edges list
    return unpacked_edges


def get_reports_data(conf_file, conf_yaml_schema, group_file, group_yaml_schema):
    # init validator
    validator = Validator(required_all=True)
    # try to load configuration yaml file
    conf_yaml_data, validation_errors = load_yaml_file(DATA_PATH / conf_file, conf_yaml_schema, validator)
    # if configuration data was correctly loaded
    if conf_yaml_data != None:
        # try to load group data
        group_yaml_data, validation_errors =            load_yaml_file(DATA_PATH / group_file, group_yaml_schema, validator)
        # if group data was correctly loaded
        if group_yaml_data != None:
            group_yaml_data["gruppo"] = group_yaml_data["IDGruppo"]
            group_yaml_data["scelteA"] = unpack_edges(group_yaml_data["scelteA"])
            group_yaml_data["scelteB"] = unpack_edges(group_yaml_data["scelteB"])
            # merge data
            report_yaml_data =  conf_yaml_data | group_yaml_data
            # init report data
            reports_data = dict()
            # update report data
            reports_data["assessment_info"] = report_yaml_data["titolo"]
            reports_data["group_id"] = report_yaml_data["gruppo"]
            reports_data["ga_question"] = report_yaml_data["domandaA"]
            reports_data["gb_question"] = report_yaml_data["domandaB"]
            reports_data["edges_a"] = report_yaml_data["scelteA"]
            reports_data["edges_b"] = report_yaml_data["scelteB"]
            reports_data["year"] = datetime.datetime.utcnow().year
            # return report data
            return (reports_data, None)
        # on validation error of group data
        else:
            # return None and validation errors
            return (None, validation_errors)
    # on validation error of configuration data
    else:
        # return None and validation errors
        return (None, validation_errors)
    
    
def get_graph_data_uri(buffer):
    # encode svg
    svg = b64encode(buffer.getvalue()).decode()
    # return svg data uri
    return f"data:image/svg+xml;base64,{svg}"


# ### 3.2 Functions related to Social Network Analysis

# In[12]:


def get_network_graph(G, graphType = "A"):
    # set conversion inch -> cm
    cm = 1/2.54
    # define type of graph color
    color = "#0000FF" if graphType == "A" else "#FF0000"
    # init buffer
    buffer = io.BytesIO()
    # init figure
    fig, ax = plt.subplots(constrained_layout=True, figsize=(9*cm,9*cm))
    # hide axis
    ax.axis('off')
    #-------------------------------------------------------------------------------------------
    # draw network
    # ------------------------------------------------------------------------------------------
    # compute locations
    loc = nx.spring_layout(G, k=0.3, seed=42)
    # draw nodes
    nx.draw_networkx_nodes(G.nodes(), loc, node_color=color, edgecolors=color, ax=ax)
    # set mutual preferences
    mutual_prefs = [ e for e in G.edges() if (e[1],e[0]) in G.edges ]
    # set non mutual preferences
    non_mutual_prefs = [ e for e in G.edges if e not in mutual_prefs ]
    # draw mutual preferences
    nx.draw_networkx_edges(G, loc, edgelist=mutual_prefs, edge_color=color, 
                           arrowstyle='-', width=3, ax=ax)
    # draw non mutual preferences
    nx.draw_networkx_edges(G, loc, edgelist=non_mutual_prefs, edge_color=color, style="--", 
                           arrowstyle='-|>', arrowsize=15, ax=ax)
     # draw labels
    nx.draw_networkx_labels(G, loc, font_color="#FFF", font_weight=True, font_size=14, ax=ax)
    # ------------------------------------------------------------------------------------------
    # save figure to buffer
    fig.savefig(buffer, format="svg", bbox_inches='tight', transparent=True, pad_inches=0.05)
    # close figure
    plt.close(fig)
    # return svg data uri (from buffer)
    return get_graph_data_uri(buffer)

def get_degree_centralization(G):
    # to undirected
    Gu = G.to_undirected()
    # determine n
    n = Gu.order()
    # store centrality values
    centrality_values = dict(Gu.degree()).values()
    # determine max degree
    c_max = max(centrality_values)
    # return network centrality
    return sum([ c_max - value for value in centrality_values ]) / ((n-1)*(n-2))
    
def get_network_stats(G):
    # init links dict
    links = dict()
    # init no indegree dict
    no_indegree = dict()
    # loop through nodes
    for node in G.nodes():
        # add x to nodes that do not have indegree, otherwise empty string
        no_indegree[node]="x" if G.in_degree(node) == 0 else ""
        # add joined neighbors
        links[node]=(", ".join(G.neighbors(node)))
    # build stats dataframe
    df = pd.concat([
        pd.Series(links, name="lns"),
        pd.Series(nx.in_degree_centrality(G), name="ic").rank(method="dense", ascending=False),
        pd.Series(nx.pagerank(G), name="pr").rank(method="dense", ascending=False),
        pd.Series(nx.betweenness_centrality(G), name="bc").rank(method="dense", ascending=False),
        pd.Series(nx.closeness_centrality(G), name="cc").rank(method="dense", ascending=False),
        pd.Series(
            { n: len(x)/len(G.nodes()) for n,x in dict(nx.all_pairs_shortest_path_length(G)).items()}
            , name="or"
        ),
        pd.Series(no_indegree, name="ni")
    ], axis=1)
    # add name to stats dataframe index
    df.index.name = "letter"
    # sort index
    df = df.sort_index()
    # return stats tuple
    return (
        # macro-level stats
        dict(
            nodes=G.number_of_nodes(), 
            edges=G.number_of_edges(),
            degree_centralization=get_degree_centralization(G),
            clustering_coefficient=nx.average_clustering(G),
            reciprocity=nx.reciprocity(G)
        ),
        # micro-level stats
        df
    )


# ### 3.3 Functions to generate docs

# In[13]:


def generate_sheets(sheets_data, prefix):
    # try to load template
    try:
        # get report template
        tpl = e.get_template("ABGrid_sheet.html")
        # render report
        rendered_tpl = tpl.render(sheets_data);
        # save report as pdf
        HTML(string=rendered_tpl).write_pdf(SHEETS_PATH / f"{prefix}_sheets.pdf")
    # catch exceptions
    except FileNotFoundError:
        return(None,"Cannot locate template files")
    
def generate_reports(reports_data, prefix):
    # try to load template
    try:
        # create DiGraph A
        Ga = nx.DiGraph()
        Ga.add_edges_from(reports_data["edges_a"])
        Ga_info, Ga_data = get_network_stats(Ga)
        reports_data["ga_info"] = Ga_info
        reports_data["ga_data"] = Ga_data.to_dict("index")
        reports_data["ga_graph"] = get_network_graph(Ga, "A")
        # create DiGraph B
        Gb = nx.DiGraph()
        Gb.add_edges_from(reports_data["edges_b"])
        Gb_info, Gb_data = get_network_stats(Gb)
        reports_data["gb_info"] = Gb_info
        reports_data["gb_data"] = Gb_data.to_dict("index")
        reports_data["gb_graph"] = get_network_graph(Gb, "B")
        # get report template
        tpl = e.get_template("ABGrid_report.html")
        # render report
        rendered_tpl = tpl.render(reports_data);
        # save report as pdf
        HTML(string=rendered_tpl).write_pdf(REPORTS_PATH / f"{prefix}_report_{reports_data['group_id']}.pdf")
    # catch exceptions
    except FileNotFoundError:
        return(None,"Cannot locate template files")


# ## 4. OPERATE

# In[14]:


# init jinja environment
e = jn.Environment(loader=jn.FileSystemLoader(TEMPLATES_PATH))


# In[15]:


# init list
files = []
prefix = ""
# from cli
if __name__ == '__main__' and "get_ipython" not in dir():
    # init arg parser
    my_parser = argparse.ArgumentParser(description="generate ABGrid sheets and/or reports")
    # add first argument
    my_parser.add_argument('conf', metavar='conf', type=str, help='the configuration file name')
    # add second argument (optional)
    my_parser.add_argument('-group', metavar='group', type=str, help='the group file name')
    # add third argument (optional)
    my_parser.add_argument('-prefix', metavar='prefix', type=str, help='prefix to add to group file name')
    # parse arguments
    args = my_parser.parse_args()
    # set files
    files = (args.conf, [args.group])
    # set prefix
    prefix = args.prefix
# from jupyter
else:
    # export jupyter notebook to python code
    get_ipython().system('jupyter nbconvert abgrid.ipynb --to python --output "abgrid.py"')
    # set files
    files = (
        "conf.yaml",
        [ f"gruppo{g}.yaml" for g in [2,3,6,8] ]
    );
    # set prefix
    prefix = "mlli_interni_21"


# In[16]:


# notify user
print("1. Starting...")
# unpack files
configuration_file, group_files = files
# generate sheets
if group_files == [None]:
    # notify user
    print(f"2. Loading data file ({configuration_file})...")
    # load data
    sheets_data, sheets_errors = get_sheets_data(configuration_file, CONF_YAML_SCHEMA)
    # if data was correctly loaded
    if (sheets_data != None):
        # notify user
        print("3. Generating sheet(s)...")
        # generate report
        generate_sheets(sheets_data, prefix)
        # notify user
        print("4. Sheet(s) generated.")
    else:
        # notify user
        print(sheets_errors)
# generate reports
else:
    # loop through groups
    for group_file in group_files:
        # notify user
        print(f"2. Loading data files ({group_file})...")
        # load data
        reports_data, reports_errors = get_reports_data(
            configuration_file, CONF_YAML_SCHEMA, 
            group_file, GROUP_YAML_SCHEMA
        )
        # if data was correctly loaded
        if (reports_data != None):
            # notify user
            print("3. Generating report(s)...")
            # generate reports
            generate_reports(reports_data, prefix)
            # notify user
            print("4. Report(s) generated.")
        else:
            # notify user
            print(reports_errors)

