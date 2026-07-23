import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Research Assistant", layout="wide")
st.title("🔬 Multi-Agent Research Assistant")
st.caption("Agentic RAG over ArXiv + Semantic Scholar with citation-grounded reports")

query = st.text_area(
    "Research question",
    placeholder="e.g. What are recent approaches to reducing hallucination in RAG systems?",
    height=100,
)

col1, col2 = st.columns([1, 4])
with col1:
    run = st.button("Run Research", type="primary")

if run and query.strip():
    with st.spinner("Agents are planning, searching, and analyzing... this can take 1-3 minutes."):
        try:
            resp = requests.post(f"{API_URL}/research", json={"query": query}, timeout=240)
            resp.raise_for_status()
            data = resp.json()

            st.success(
                f"Done — {data['papers_found']} papers considered, "
                f"{len(data['validated_claims'])} claims grounded."
            )

            tab1, tab2 = st.tabs(["📄 Report", "✅ Validated Claims"])
            with tab1:
                st.markdown(data["report"])
                st.download_button(
                    "Download report (.md)",
                    data["report"],
                    file_name="research_report.md",
                )
            with tab2:
                if data["validated_claims"]:
                    for c in data["validated_claims"]:
                        st.markdown(
                            f"- **{c['text']}**  \n"
                            f"  ↳ [source]({c['source_paper_url']}) · confidence: {c['confidence']:.2f}"
                        )
                else:
                    st.info("No claims passed the grounding threshold for this query.")

        except requests.exceptions.ConnectionError:
            st.error("Couldn't reach the backend. Is FastAPI running on port 8000?")
        except Exception as e:
            st.error(f"Something went wrong: {e}")

elif run:
    st.warning("Enter a research question first.")

st.divider()
with st.expander("🕸️ Optional: generate a paper/author knowledge graph"):
    if st.button("Build knowledge graph"):
        with st.spinner("Fetching papers..."):
            try:
                resp = requests.post(f"{API_URL}/knowledge-graph", json={"query": query}, timeout=60)
                resp.raise_for_status()
                data = resp.json()
                st.success(f"Graph built from {data['papers_found']} papers.")
                with open(data["graph_path"], "r", encoding="utf-8") as f:
                    st.components.v1.html(f.read(), height=650)
            except Exception as e:
                st.error(f"Something went wrong: {e}")
