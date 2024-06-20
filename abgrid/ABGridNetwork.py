# imports
import io
import pandas as pd
import networkx as nx
import matplotlib
import matplotlib.pyplot as plt

from base64 import b64encode

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
        # init edges list
        unpacked_edges = []
        # loop through rows in data
        for row in packed_edges:
            # loop through nodes and edges
            for node, edges in row.items():
                # split edges
                for edge in edges.split(","):
                    # append edge to edges list
                    unpacked_edges.append((node, edge))
        # return edges list
        return unpacked_edges

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

    def get_degree_centralization(self, G):
        # to undirected
        Gu = G.to_undirected()
        # determine n
        n = Gu.order()
        # store centrality values
        centrality_values = dict(Gu.degree()).values()
        # determine max degree
        c_max = max(centrality_values)
        # return network centrality
        return sum([c_max - value for value in centrality_values]) / ((n-1)*(n-2))

    def get_network_stats(self, G):
        # compute networks params
        df = pd.concat([
            # store edges for each node
            pd.Series(nx.to_pandas_adjacency(G).apply(
                lambda x: ", ".join(x[x > 0].index.values), axis=1), name="lns"),
            # store in_degree_centrality
            pd.Series(nx.in_degree_centrality(G), name="ic").round(3),
            # store pagerank_centrality
            pd.Series(nx.pagerank(G, max_iter=1000), name="pr").round(3),
            # store betweenness_centrality centrality
            pd.Series(nx.betweenness_centrality(G), name="bc").round(3),
            # store closeness_centrality centrality
            pd.Series(nx.closeness_centrality(G), name="cc").round(3),
            # store other nodes reachability for each node
            pd.Series(
                {n: len(x) for n, x in dict(nx.all_pairs_shortest_path_length(G)).items()}, name="or"
            ).div(len(G.nodes())).round(3),
        ], axis=1)
        # add identification of nodes with no indegree
        df = df.assign(ni=(lambda x: (x['ic'] == 0).astype(int)))
        # compute ranks of networks params
        ranks = (df.iloc[:, 1:-1]
                 .apply(lambda x: x.rank(method="dense", ascending=False))
                 .rename(columns={"ic": "ic_r", "pr": "pr_r", "bc": "bc_r", "cc": "cc_r", "or": "or_r"})
                 )
        # finalize dataframe
        df = pd.concat([df, ranks], axis=1)
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
                degree_centralization=round(
                    self.get_degree_centralization(G), 3),
                transitivity=round(nx.transitivity(G), 3),
                reciprocity=round(nx.reciprocity(G), 3)
            ),
            # micro-level stats
            df
        )
