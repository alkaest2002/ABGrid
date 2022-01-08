#!/usr/bin/env python
# coding: utf-8

# ## IMPORTS AND UTILITY FNS

# Author: Dr. Pierpaolo Calanna, Phd

# In[1]:
import sys
if len(sys.argv) != 3:
	print("Parametri insufficienti")
	sys.exit()


# define constants
import os
import io
import re
import json
import yaml
import datetime
from pathlib import Path
from base64 import b64encode
import numpy as np
import pandas as pd
import networkx as nx
import networkx.algorithms.connectivity as nxcon
from networkx.readwrite import json_graph
import matplotlib
import matplotlib.pyplot as plt
import jinja2 as jn
from weasyprint import HTML

TEMPLATES_PATH = Path("./templates/")
DATA_PATH = Path("./data/")
REPORTS_PATH = Path("./out/reports/")

CONF_FILE = DATA_PATH / sys.argv[1]
DATA_FILE = DATA_PATH / sys.argv[2]

# customize matplotlib
font = {'size' : 8}
matplotlib.rc('font', **font)

# init jinja environment
e = jn.Environment(loader=jn.FileSystemLoader(TEMPLATES_PATH))


# In[10]:


# function to unpack edges
def unpack(data):
    unpacked_edges = [];
    for row in data:
        for node, edges in row.items():
            for edge in edges.split(","):
                unpacked_edges.append((node, edge))
    return unpacked_edges


# ## DATA

# In[4]:


# read conf data
with open(CONF_FILE, 'r') as file:
    conf_yaml_data = yaml.safe_load(file)
    
# read group data
with open(DATA_FILE, 'r') as file:
    group_yaml_data = yaml.safe_load(file)
    group_id = "non definito"
    if match := re.search(f"^.+[{os.path.sep}](.+)\..+$", file.name, re.IGNORECASE):
        group_id = match.group(1)
    group_yaml_data["gruppo"] = group_id
    group_yaml_data["scelteA"] = unpack(group_yaml_data["scelteA"])
    group_yaml_data["scelteB"] = unpack(group_yaml_data["scelteB"])

# merge data
yaml_data = conf_yaml_data | group_yaml_data


# ## REPORT

# In[6]:


# init report data
report_data = dict()

# update report data
report_data["assessment_info"] = yaml_data["titolo"]
report_data["group_id"] = yaml_data["gruppo"]
report_data["ga_question"] = yaml_data["domandaA"]
report_data["gb_question"] = yaml_data["domandaB"]
report_data["edges_a"] = yaml_data["scelteA"]
report_data["edges_b"] = yaml_data["scelteB"]


# In[7]:


def get_graph_data_uri(buffer):
    # encode svg
    svg = b64encode(buffer.getvalue()).decode()
    # return svg data uri
    return f"data:image/svg+xml;base64,{svg}"    


# In[8]:


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
    # return svg data uri (from buffer)
    return get_graph_data_uri(buffer)

def get_network_diameter(G):
    # convert network to undirected
    Gu = G.to_undirected()
    # if network is connected
    if nx.is_connected(Gu):
        # return network diameter
        return nx.diameter(Gu)
    # otherwise
    else:
        # get largest connected component
        Gcc_max = sorted(nx.connected_components(Gu), key=len, reverse=True)[0]
        # get largest connected component subgraph
        Gcc_max_graph = Gu.subgraph(Gcc_max)
        # return diameter of largest connected component
        return nx.diamter(Gcc_max_graph)

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
    # get nodes' neighbors
    for node in G.nodes():
        no_indegree[node]="x" if G.in_degree(node) == 0 else ""
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
    # add name to tats dataframe index
    df.index.name = "letter"
    # sort index
    df = df.sort_index()
    # return stats tuple
    return (
        dict(
            nodes=G.number_of_nodes(), 
            edges=G.number_of_edges(),
            degree_centralization=get_degree_centralization(G),
            clustering_coefficient=nx.average_clustering(G),
            reciprocity=nx.reciprocity(G)
        ),
        df
    )


# In[9]:


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
report_data["year"] = datetime.datetime.utcnow().year

# get report template
tpl = e.get_template("ABGrid_report.html")

# render report
rendered_tpl = tpl.render(report_data);

# save report as pdf
HTML(string=rendered_tpl).write_pdf( REPORTS_PATH / f"ABGrid_report_{report_data['group_id']}.pdf")


