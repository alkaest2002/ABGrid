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
import requests
import argparse
import json
import datetime
import yaml
import string
import random
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib
import matplotlib.pyplot as plt
import jinja2 as jn


from pathlib import Path
from base64 import b64encode
from cerberus import Validator
from weasyprint import HTML

# customize matplotlib
matplotlib.rc('font', **{'size' : 8})
matplotlib.use("Agg")


# ## 2. CONSTANTS

# In[10]:


# folder paths
TEMPLATES_PATH = Path("./templates/")
DATA_PATH = Path("./data/")
REPORTS_PATH = Path("./out/reports/")
SHEETS_PATH = Path("./out/sheets/")

# templates
SHEET_TPL = "sheet.html"
REPORT_TPL = "report.html"
GROUP_TPL = "group.html"

# configuration yaml validator schema
CONF_YAML_SCHEMA = {
    "titolo": { "type": "string" },
    "numero_gruppi": { "type": "integer", "min": 1, "max": 20 },
    "numero_partecipanti_per_gruppo": { "type": "integer", "min": 3, "max": 12 },
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
            "valuesrules": {"type": "string", "regex": "^([A-Z]{1,1},)*[A-Z]$"}
        }
    },
    "scelteB": {
        "type": "list",
        "schema":{
            "type": "dict",
            "keysrules": {"type": "string", "regex": "^[A-Z]{1,1}$"},
            "valuesrules": {"type": "string", "regex": "^([A-Z]{1,1},)*[A-Z]$"}
        }
    }
}


# ## 3. FUNCTIONS

# ### 3.1 Utility functions

# In[11]:


def get_graph_data_uri(buffer):
    # encode buffer to base64
    data = b64encode(buffer.getvalue()).decode()
    # return data as svg uri
    return f"data:image/svg+xml;base64,{data}"

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


# ### 3.2 Functions related to DOCUMENTS and DATA

# In[12]:


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
        # return None as data and errors
        return(None,"Cannot locate files")
    except yaml.YAMLError as e:
        # return None as data and errors
        return (None, "Yaml files could not be parsed")
    except cerberus.DocumentError as e:
        # return None as data and errors
        return (None, "Document was loaded but cannot be evaluated")
    except cerberus.SchemaError as e:
        # return None as data and errors
        return (None, "Invalid yaml validation schema")
    
def get_sheet_data(conf_file, conf_yaml_schema):
    # init validator
    validator = Validator(required_all=True)
    # load configuration data
    yaml_data, validation_errors = load_yaml_file(DATA_PATH / conf_file, conf_yaml_schema, validator)
    # if configuration data was correctly loaded
    if yaml_data != None:
        # init sheet_data dict
        sheet_data = dict()
        # update sheet_data
        sheet_data["title"] = yaml_data["titolo"]
        sheet_data["groups"] = list(range(1, yaml_data["numero_gruppi"] +1))
        sheet_data["likert"] = string.ascii_uppercase[:yaml_data["numero_partecipanti_per_gruppo"]]
        sheet_data["explanation"] = yaml_data["consegna"]
        sheet_data["ga_question"] = yaml_data["domandaA"]
        sheet_data["ga_question_hint"] = yaml_data["domandaA_scelte"]
        sheet_data["gb_question"] = yaml_data["domandaB"]
        sheet_data["gb_question_hint"] = yaml_data["domandaB_scelte"]
        # return sheet data
        return (sheet_data, None)
    # on validation errors
    else:
        # return None and validation errors
        return (None, validation_errors)
    

def get_report_data(conf_file, conf_yaml_schema, group_file, group_yaml_schema, anonymize_nodes=False):
    # init validator
    validator = Validator(required_all=True)
    # try to load configuration data
    conf_yaml_data, validation_errors = load_yaml_file(DATA_PATH / conf_file, conf_yaml_schema, validator)
    # if configuration data was correctly loaded
    if conf_yaml_data != None:
        # try to load group data
        group_yaml_data, validation_errors =\
            load_yaml_file(DATA_PATH / group_file, group_yaml_schema, validator)
        # if group data was correctly loaded
        if group_yaml_data != None:  
            # init report data
            report_data = dict()
            # update report data
            report_data["assessment_info"] = conf_yaml_data["titolo"]
            report_data["group_id"] = f'gruppo {group_yaml_data["IDGruppo"]}'
            report_data["ga_question"] = conf_yaml_data["domandaA"]
            report_data["gb_question"] = conf_yaml_data["domandaB"]
            report_data["edges_a"] = unpack_edges(group_yaml_data["scelteA"])
            report_data["edges_b"] = unpack_edges(group_yaml_data["scelteB"])
            report_data["year"] = datetime.datetime.utcnow().year
            # get nodes identifiers
            nodes_A = set(sum(map(list, report_data["edges_a"]), []))
            nodes_B = set(sum(map(list, report_data["edges_b"]), []))
            # under this condition
            if len(nodes_A.symmetric_difference(nodes_B)) > 0:
                # return None and errors
                return (None, "Letters are not correct")
            # create networks A & B
            (Ga, loca), (Gb, locb) = get_networks((report_data["edges_a"], report_data["edges_b"]), False)
            # add network A related data to report data
            Ga_info, Ga_data = get_network_stats(Ga)
            report_data["ga_info"] = Ga_info
            report_data["ga_data"] = Ga_data.to_dict("index")
            report_data["ga_graph"] = get_network_graph(Ga, loca, "A")
            # add network B related data to report data
            Gb_info, Gb_data = get_network_stats(Gb)
            report_data["gb_info"] = Gb_info
            report_data["gb_data"] = Gb_data.to_dict("index")
            report_data["gb_graph"] = get_network_graph(Gb, locb, "B")
            # return report data
            return (report_data, None)
        # on validation error of group data
        else:
            # return None and validation errors
            return (None, validation_errors)
    # on validation error of configuration data
    else:
        # return None and validation errors
        return (None, validation_errors)

def generate_doc_from_template(doc_type, doc_template, doc_data, path, prefix, suffix):
    # try to load sheet template
    try:
        # get doc template
        tpl = e.get_template(doc_template)
        # render doc
        rendered_tpl = tpl.render(doc_data);
        # build file name
        filename_html = re.sub("^_|_$", "", f"{prefix}_{doc_type}_{suffix}.html")
        filename_pdf = re.sub("^_|_$", "", f"{prefix}_{doc_type}_{suffix}.pdf")
        # save doc as pdf
        HTML(string=rendered_tpl).write_pdf(path / filename_pdf)
        # save doc as html
        # with open(path / filename_html, "w") as file: file.write(rendered_tpl)
    # catch exceptions
    except FileNotFoundError:
        return(None, f"Cannot locate {doc_type} template file")
    
def generate_yaml_group_inputs(doc_data, prefix):
    # try to load sheet template
    try:
        # get doc template
        tpl = e.get_template(GROUP_TPL)
        # loop thorugh groups
        for g in doc_data["groups"]:
            # render doc
            rendered_tpl = re.sub("^\s*\n$ ","",tpl.render(doc_data | { "groupId": g}));
            # remove blank lones
            rendered_tpl ="\n".join([ line for line in rendered_tpl.split("\n") if len(line)>0])
            # save doc as yaml
            with open(DATA_PATH / f"{prefix}_gruppo_{g}.yaml", "w") as file:
                file.write(rendered_tpl)
    # catch exceptions
    except FileNotFoundError:
        return(None, f"Cannot locate {doc_type} template file")


# ### 3.3 Functions related to Social Network Analysis

# In[13]:


def get_networks(edges, anonymize_nodes):
    # unpack edges
    edges_A, edges_B = edges
    # if nodes are to be anonymized
    if anonymize_nodes:
        # get list of uppercase letters
        alphabet = [ letter for letter in string.ascii_uppercase ]
        # get list of nodes ids (i.e., upper case letters)
        original_letters = sorted(list(set(sum(map(list, edges_A), []) + sum(map(list, edges_B), []))))
        # get unused letters
        unused_letters = [ letter for letter in alphabet if letter not in original_letters ]
        # shuffle unused letters
        random.shuffle(unused_letters)
        # define translation mapping
        mapping = str.maketrans(dict(zip(original_letters, unused_letters)))
        # obfuscate nodes ids in edges_A
        edges_A = list(map(lambda x: (x[0].translate(mapping), x[1].translate(mapping)), edges_A))
        # obfuscate nodes ids in edges_B
        edges_B = list(map(lambda x: (x[0].translate(mapping), x[1].translate(mapping)), edges_B))
    # create netowrk A & netowrk B
    Ga, Gb = nx.DiGraph(edges_A), nx.DiGraph(edges_B)
    # create locations A & locations B
    loca, locb = nx.spring_layout(Ga, k=.5, seed=42), nx.spring_layout(Gb, k=.3, seed=42)
    # return networks and locations
    return ((Ga, loca), (Gb, locb))

def get_network_graph(G, loc, graphType = "A"):
    # set conversion inch -> cm
    cm = 1/2.54
    # define color based of type of network (either A or B)
    color = "#0000FF" if graphType == "A" else "#FF0000"
    # init file buffer
    buffer = io.BytesIO()
    # init plt figure and ax
    fig, ax = plt.subplots(constrained_layout=True, figsize=(9*cm,9*cm))
    # hide axis
    ax.axis('off')
    #-------------------------------------------------------------------------------------------
    # draw network
    # ------------------------------------------------------------------------------------------
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
        pd.Series(nx.pagerank(G, max_iter=1000), name="pr").rank(method="dense", ascending=False),
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
            transitivity=nx.transitivity(G),
            reciprocity=nx.reciprocity(G)
        ),
        # micro-level stats
        df
    )


# ## 4. GENERATE

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
    my_parser.add_argument('-conf', required=True, type=str, help='the configuration file')
    # add second argument (optional)
    my_parser.add_argument('-group', type=str, help='the group file')
    # add third argument (optional)
    my_parser.add_argument('-prefix', type=str, help='prefix to add to group file')
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
        "2022_periti.yaml",
       ["periti2022_gruppo_1.yaml"]
    );
    # set prefix
    prefix = "periti2022"


# In[18]:


# notify user
print("1. Starting...")
# unpack files
configuration_file, group_files = files
# generate sheet(s)
if group_files == []:
    # notify user
    print(f"2. Loading file ({configuration_file})...")
    # load sheet(s) data
    sheet_data, sheet_errors = get_sheet_data(configuration_file, CONF_YAML_SCHEMA)
    print(sheet_data)
    # if sheet(s) data was correctly loaded
    if (sheet_data != None):
        # notify user
        print("3. Generating doc(s)...")
        # generate sheet(s)
        generate_doc_from_template("sheet", SHEET_TPL, sheet_data, SHEETS_PATH, prefix, "")
        # generate group input doc(s)
        generate_yaml_group_inputs(sheet_data, prefix)
        # notify user
        print("4. Doc(s) generated.")
    else:
        # notify user
        print(sheet_errors)
# generate report
else:
    # loop through groups
    for group_file in group_files:
        # notify user
        print(f"2. Loading file ({group_file})...")
        # load report(s) data
        report_data, report_errors = get_report_data(
            configuration_file, CONF_YAML_SCHEMA, 
            group_file, GROUP_YAML_SCHEMA
        )
        # if report(s) data was correctly loaded
        if (report_data != None):
            # notify user
            print("3. Generating report(s)...")
            # generate report(s)
            generate_doc_from_template("report", REPORT_TPL, report_data, REPORTS_PATH, "", group_file)
            # notify user
            print("4. Report(s) generated.")
        else:
            # notify user
            print(report_errors)


# In[ ]:





# In[ ]:




