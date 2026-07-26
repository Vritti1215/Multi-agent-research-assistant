import networkx as nx
from pyvis.network import Network


def build_paper_graph(papers: list[dict], output_path: str = "outputs/knowledge_graph.html"):
    """Builds a paper<->author bipartite graph. Tuned specifically to avoid
    the tangled, jittery default pyvis look: stronger damping and a longer
    spring length let it settle into a readable layout instead of nodes
    flying around indefinitely, and node/edge colors match the app's
    brand palette instead of pyvis defaults.
    """
    G = nx.Graph()
    for p in papers:
        short_title = p["title"] if len(p["title"]) <= 40 else p["title"][:37] + "..."
        G.add_node(
            p["title"],
            type="paper",
            label=short_title,
            title=f"{p['title']}\n\n{p.get('abstract', '')[:280]}...",  # hover tooltip
            color="#4F46E5",
            size=22,
            shape="dot",
        )
        for a in p["authors"]:
            G.add_node(a, type="author", label=a, title=a, color="#06B6D4", size=13, shape="dot")
            G.add_edge(a, p["title"])

    net = Network(
        height="600px",
        width="100%",
        bgcolor="#FFFFFF",
        font_color="#111827",
        notebook=False,
        cdn_resources="in_line",
    )
    net.from_nx(G)

    # Calmer physics: higher damping + longer spring length = settles into
    # a clean layout instead of the default jittery tangle. stabilization
    # runs before display so it's not visibly bouncing when opened.
    net.set_options("""
    {
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -6000,
          "centralGravity": 0.25,
          "springLength": 160,
          "springConstant": 0.03,
          "damping": 0.45
        },
        "minVelocity": 0.9,
        "stabilization": { "enabled": true, "iterations": 250, "fit": true }
      },
      "edges": {
        "color": { "color": "#E5E7EB", "highlight": "#4F46E5" },
        "smooth": { "type": "continuous" },
        "width": 1.2
      },
      "nodes": {
        "borderWidth": 2,
        "borderWidthSelected": 3,
        "font": { "face": "Inter, sans-serif", "size": 13, "color": "#111827" }
      },
      "interaction": { "hover": true, "tooltipDelay": 120 }
    }
    """)

    html = net.generate_html(notebook=False)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
