import networkx as nx
from pyvis.network import Network


def build_paper_graph(papers: list[dict], output_path: str = "outputs/knowledge_graph.html"):
    """Builds a paper<->author bipartite graph and writes a SELF-CONTAINED
    interactive HTML view.

    Two Windows-specific gotchas handled here:
    - cdn_resources="in_line": without it, pyvis links to a local lib/
      folder that doesn't exist when the HTML is read as a raw string and
      embedded in Streamlit's iframe, so the graph renders blank.
    - Explicit UTF-8 write: pyvis's own write_html() opens the file with
      the OS default encoding, which is cp1252 on Windows. Paper titles/
      author names with accented or special characters then raise
      UnicodeEncodeError. Generating the HTML string ourselves and writing
      it out with encoding="utf-8" avoids that entirely.
    """
    G = nx.Graph()
    for p in papers:
        G.add_node(p["title"], type="paper", title=p["title"], color="#4f8bf9", size=20)
        for a in p["authors"]:
            G.add_node(a, type="author", color="#f9a94f", size=12)
            G.add_edge(a, p["title"])

    net = Network(
        height="600px",
        width="100%",
        bgcolor="#1e1e1e",
        font_color="white",
        notebook=False,
        cdn_resources="in_line",
    )
    net.from_nx(G)

    html = net.generate_html(notebook=False)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
