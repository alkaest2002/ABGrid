#!/usr/bin/env python
# coding: utf-8

# # GENERATE AB-GRID REPORT

# Author: Dr. Pierpaolo Calanna, Phd

# ## 1. IMPORTS

# In[1]:


# imports
import sys
import os
import io
import re
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

# In[2]:


# folder path constants
TEMPLATES_PATH = Path("./templates/")
DATA_PATH = Path("./data/")
REPORTS_PATH = Path("./out/reports/")

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

# ### 3.1 Functions related to IO

# In[3]:


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


def load_data(conf_file, conf_yaml_schema, group_file, group_yaml_schema):
    # init validator
    validator = Validator(required_all=True)
    # try to load data
    try:
        # read conf data
        with open(DATA_PATH / conf_file, 'r') as file:
            conf_yaml_data = yaml.safe_load(file)
        # validate conf data
        if validator.validate(conf_yaml_data, conf_yaml_schema):
            # read group data
            with open(DATA_PATH / group_file, 'r') as file:
                group_yaml_data = yaml.safe_load(file)
            # validate data
            if validator.validate(group_yaml_data, group_yaml_schema):
                # update group data
                group_id = "non definito"
                if match := re.search(f"^.+[{os.path.sep}](.+)\..+$", file.name, re.IGNORECASE):
                    group_id = match.group(1)
                group_yaml_data["gruppo"] = group_id
                group_yaml_data["scelteA"] = unpack_edges(group_yaml_data["scelteA"])
                group_yaml_data["scelteB"] = unpack_edges(group_yaml_data["scelteB"])
                # merge data
                report_yaml_data =  conf_yaml_data | group_yaml_data
                # init report data
                report_data = dict()
                # update report data
                report_data["assessment_info"] = report_yaml_data["titolo"]
                report_data["group_id"] = report_yaml_data["gruppo"]
                report_data["ga_question"] = report_yaml_data["domandaA"]
                report_data["gb_question"] = report_yaml_data["domandaB"]
                report_data["edges_a"] = report_yaml_data["scelteA"]
                report_data["edges_b"] = report_yaml_data["scelteB"]
                report_data["year"] = datetime.datetime.utcnow().year
                # report data
                return (report_data, None)
            else:
                return (None, validator.errors)
        else:
            return (None, validator.errors)
    # catch eroors
    except FileNotFoundError:
        return(None,"Cannot locate files")
    except yaml.YAMLError as e:
        return (None, "Yaml files could not be parsed")
    except cerberus.DocumentError as e:
        return (None, "Document was loaded but cannot be evaluated")
    except cerberus.SchemaError as e:
        return (None, "Invalid yaml validation schema")


def generate_report(report_data):
    # create DiGraph A
    Ga = nx.DiGraph()
    Ga.add_edges_from(report_data["edges_a"])
    Ga_info, Ga_data = get_network_stats(Ga)
    report_data["ga_info"] = Ga_info
    report_data["ga_data"] = Ga_data.to_dict("index")
    report_data["ga_graph"] = get_network_graph(Ga, "A")
    # create DiGraph B
    Gb = nx.DiGraph()
    Gb.add_edges_from(report_data["edges_b"])
    Gb_info, Gb_data = get_network_stats(Gb)
    report_data["gb_info"] = Gb_info
    report_data["gb_data"] = Gb_data.to_dict("index")
    report_data["gb_graph"] = get_network_graph(Gb, "B")
    # get report template
    tpl = e.get_template("ABGrid_report.html")
    # render report
    rendered_tpl = tpl.render(report_data);
    # save report as pdf
    HTML(string=rendered_tpl).write_pdf(REPORTS_PATH / f"ABGrid_report_{report_data['group_id']}.pdf")


# ### 3.2 Functions related to Social Network Analysis

# In[4]:


def get_graph_data_uri(buffer):
    # encode svg
    svg = b64encode(buffer.getvalue()).decode()
    # return svg data uri
    return f"data:image/svg+xml;base64,{svg}"    

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


# ## 4. REPORT

# In[5]:


# init jinja environment
e = jn.Environment(loader=jn.FileSystemLoader(TEMPLATES_PATH))


# In[6]:


# init list
files = []
# from cli
if __name__ == '__main__' and "get_ipython" not in dir():
    if len(sys.argv) != 3:
        print("Parametri insufficienti")
        sys.exit()
    files = (
        sys.argv[1], 
        [sys.argv[2]]
    )
# from jupyter
else:
    files = (
        "conf.yaml",
        [ f"gruppo{g}.yaml" for g in [2,3,6,8]]
    )

# notify user
print("1. Starting...")
# unpack files
conf, groups = files
# loop through groups
for group in groups:
    # notify user
    print("2. Loading data files...")
    # load data
    report_data, errors = load_data(conf, CONF_YAML_SCHEMA, group, GROUP_YAML_SCHEMA)
    # if data was correctly loaded
    if (report_data != None):
        # notify user
        print("3. Generating report(s)...")
        # generate report
        generate_report(report_data)
        # notify user
        print("4. Report(s) generated.")
    else:
        # notify user
        print(errors)

