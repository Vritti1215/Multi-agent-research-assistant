import networkx as nx
from pyvis.network import Network


def build_paper_graph(papers: list[dict], output_path: str = "outputs/knowledge_graph.html"):
    """Builds a paper<->author bipartite graph and writes an interactive HTML view."""
    G = nx.Graph()
    for p in papers:
        G.add_node(p["title"], type="paper", title=p["title"])
        for a in p["authors"]:
            G.add_node(a, type="author")
            G.add_edge(a, p["title"])

    net = Network(height="600px", width="100%", bgcolor="#1e1e1e", font_color="white")
    net.from_nx(G)
    net.write_html(output_path)
    return output_path
