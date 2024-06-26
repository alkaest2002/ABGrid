# imports
import io
import pandas as pd
import networkx as nx
import matplotlib
import matplotlib.pyplot as plt

from base64 import b64encode
from functools import reduce

# customize matplotlib
matplotlib.rc('font', **{'size': 8})
matplotlib.use("Agg")


class ABGridNetwork(object):

    def __init__(self, edges):
        # set conversion inch -> cm
        self.cm = 1/2.54

        self.edges = edges
        self.edges_a = self.unpack_edges(edges[0])
        self.edges_b = self.unpack_edges(edges[1])
        self.nodes_a = set(sum(map(list, edges[0]), []))
        self.nodes_b = set(sum(map(list, edges[1]), []))

        self.Ga_info = None
        self.Ga_data = None
        self.graphA = None
        self.Gb_info = None
        self.Gb_data = None
        self.graphB = None

    def unpack_edges(self, packed_edges):
        # from [{ A: B,C, B: A,C, C: A,B}] --> [(A,B), (A,C), (B,A), (B,C), (C,A), (C,B)]
        return reduce(
            lambda acc, itr: [*acc, *[(node_a, node_b) for node_a, edges in itr.items()
                                      for node_b in edges.split(",")]], packed_edges, []
        )

    def validate_nodes(self):
        # determine whether nodes are consistent with project data
        return len(self.nodes_a.symmetric_difference(self.nodes_b)) == 0

    def compute_networks(self):
        # create netowrk A & netowrk B
        Ga, Gb = nx.DiGraph(self.edges_a), nx.DiGraph(self.edges_b)
        # create locations A & locations B
        loca, locb = nx.spring_layout(
            Ga, k=.5, seed=42), nx.spring_layout(Gb, k=.3, seed=42)
        # set netoworks data
        self.Ga_info, self.Ga_data = self.get_network_stats(Ga)
        self.Gb_info, self.Gb_data = self.get_network_stats(Gb)
        self.graphA = self.get_network_graph(Ga, loca, graphType="A")
        self.graphB = self.get_network_graph(Gb, locb, graphType="B")

    def get_network_graph(self, G, loc, graphType="A"):
        # define color based of type of network (either A or B)
        color = "#0000FF" if graphType == "A" else "#FF0000"
        # init file buffer
        buffer = io.BytesIO()
        # init plt figure and ax
        fig, ax = plt.subplots(constrained_layout=True,
                               figsize=(9*self.cm, 9*self.cm))
        # hide axis
        ax.axis('off')
        # -------------------------------------------------------------------------------------------
        # draw network
        # ------------------------------------------------------------------------------------------
        # draw nodes
        nx.draw_networkx_nodes(
            G.nodes(), loc, node_color=color, edgecolors=color, ax=ax)
        # store mutual preferences
        mutual_prefs = [e for e in G.edges() if e[::-1] in G.edges]
        # store non mutual preferences
        non_mutual_prefs = [e for e in G.edges if e not in mutual_prefs]
        # draw mutual preferences
        nx.draw_networkx_edges(G, loc, edgelist=mutual_prefs,
                               edge_color=color, arrowstyle='-', width=3, ax=ax)
        # draw non mutual preferences
        nx.draw_networkx_edges(G, loc, edgelist=non_mutual_prefs, edge_color=color,
                               style="--", arrowstyle='-|>', arrowsize=15, ax=ax)
        # draw labels
        nx.draw_networkx_labels(G, loc, font_color="#FFF",
                                font_weight=True, font_size=14, ax=ax)
        # ------------------------------------------------------------------------------------------
        # save figure to buffer
        fig.savefig(buffer, format="svg", bbox_inches='tight',
                    transparent=True, pad_inches=0.05)
        # close figure
        plt.close(fig)
        # encode buffer to base64
        data = b64encode(buffer.getvalue()).decode()
        # return data as svg uri
        return f"data:image/svg+xml;base64,{data}"

    def get_network_centralization(self, G):
        # store centrality values
        centralities = pd.Series(dict(nx.degree(G.to_undirected())))
        # store number of nodes
        number_of_nodes = G.number_of_nodes()
        # compute and return network centralization value
        return (
            centralities
            .sub(centralities.max())
            .abs()
            .sum()
            / ((number_of_nodes-1)*(number_of_nodes-2))
        )

    def get_network_stats(self, G):
        # create dataframe
        df = pd.concat([
            # store edges for each node
            pd.Series(nx.to_pandas_adjacency(G).apply(
                lambda x: ", ".join(x[x > 0].index.values), axis=1), name="lns"),
            # store in_degree_centrality
            pd.Series(nx.in_degree_centrality(G), name="ic"),
            # store pagerank_centrality
            pd.Series(nx.pagerank(G, max_iter=1000), name="pr"),
            # store betweenness_centrality
            pd.Series(nx.betweenness_centrality(G), name="bc"),
            # store closeness_centrality
            pd.Series(nx.closeness_centrality(G), name="cc"),
            # store other nodes reachability for each node
            pd.Series(
                reduce(lambda acc, itr: {**acc, **{itr: nx.local_reaching_centrality(G, itr)}}, G.nodes(), {}), name="or"
            ),
        ], axis=1)
        # add identification of nodes with no in_degree to dataframe
        df = df.assign(ni=(lambda x: (x['ic'] == 0).astype(int)))
        # compute ranks of networks params
        ranks = (df.iloc[:, 1:-1]
                 .apply(lambda x: x.rank(method="dense", ascending=False))
                 .add_suffix("_r", axis=1)
                 )
        # finalize dataframe
        df = pd.concat([df, ranks], axis=1).round(3).sort_index()
        # add name to dataframe index
        df.index.name = "letter"
        # return tuple
        return (
            # macro-level statistics
            dict(
                network_nodes=G.number_of_nodes(),
                network_edges=G.number_of_edges(),
                network_centralization=round(
                    self.get_network_centralization(G), 3),
                network_transitivity=round(nx.transitivity(G), 3),
                network_reciprocity=round(nx.reciprocity(G), 3)
            ),
            # micro-level statistics as dataframe
            df
        )
