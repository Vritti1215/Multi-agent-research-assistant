import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Research Assistant", layout="wide")
st.title("🔬 Multi-Agent Research Assistant")
st.caption("Agentic RAG over ArXiv + Semantic Scholar with citation-grounded reports")

# Persist state across reruns (Streamlit reruns the whole script on every interaction)
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "report" not in st.session_state:
    st.session_state.report = None
if "papers" not in st.session_state:
    st.session_state.papers = []
if "validated_claims" not in st.session_state:
    st.session_state.validated_claims = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "last_query" not in st.session_state:
    st.session_state.last_query = ""
if "exported_files" not in st.session_state:
    st.session_state.exported_files = {}  # fmt -> (filename, bytes)

query = st.text_area(
    "Research question",
    placeholder="e.g. What are recent approaches to reducing hallucination in RAG systems?",
    height=100,
)

col1, col2, col3 = st.columns([1, 2, 3])
with col1:
    run = st.button("Run Research", type="primary")
with col2:
    deep_mode = st.checkbox(
        "🔎 Deep research mode",
        help="More sub-questions, more papers per source, deeper analysis, and an extra retry pass if grounding is thin. Slower and uses more free-tier requests.",
    )

if run and query.strip():
    st.session_state.chat_history = []  # new topic, reset any old chat
    with st.spinner(
        f"Agents are planning, searching, and analyzing"
        f"{' (deep mode — this takes longer)' if deep_mode else ''}..."
    ):
        try:
            resp = requests.post(
                f"{API_URL}/research",
                json={"query": query, "deep_mode": deep_mode},
                timeout=400 if deep_mode else 240,
            )
            resp.raise_for_status()
            data = resp.json()

            st.session_state.session_id = data["session_id"]
            st.session_state.report = data["report"]
            st.session_state.papers = data["papers"]
            st.session_state.validated_claims = data["validated_claims"]
            st.session_state.last_query = query

        except requests.exceptions.ConnectionError:
            st.error("Couldn't reach the backend. Is FastAPI running on port 8000?")
        except Exception as e:
            st.error(f"Something went wrong: {e}")

elif run:
    st.warning("Enter a research question first.")

# ---- Results ----
if st.session_state.report:
    st.success(
        f"{len(st.session_state.papers)} papers considered, "
        f"{len(st.session_state.validated_claims)} claims grounded."
    )

    tab1, tab2, tab3, tab4 = st.tabs(
        ["📄 Report", "✅ Validated Claims", "📊 Paper Comparison", "🕸️ Knowledge Graph"]
    )

    with tab1:
        st.markdown(st.session_state.report)

        st.divider()
        st.caption("Export report")
        ecol1, ecol2, ecol3 = st.columns(3)
        for col, fmt, label in [
            (ecol1, "pdf", "📄 Download PDF"),
            (ecol2, "pptx", "📊 Download PPTX"),
            (ecol3, "docx", "📝 Download DOCX"),
        ]:
            with col:
                if st.button(label, key=f"export_{fmt}"):
                    with st.spinner(f"Building {fmt.upper()}..."):
                        try:
                            r = requests.post(
                                f"{API_URL}/export",
                                json={
                                    "report": st.session_state.report,
                                    "query": st.session_state.last_query,
                                    "format": fmt,
                                },
                                timeout=60,
                            )
                            r.raise_for_status()
                            file_path = r.json()["path"]
                            dl = requests.get(f"{API_URL}/download", params={"path": file_path})
                            dl.raise_for_status()
                            # Store in session_state rather than only calling
                            # st.download_button here: this whole block only
                            # runs on the render right after the click (Streamlit
                            # button state is transient), so without persisting
                            # it, the download button would vanish on the very
                            # next rerun before you could click it.
                            st.session_state.exported_files[fmt] = (
                                file_path.split("/")[-1],
                                dl.content,
                            )
                        except requests.exceptions.HTTPError as e:
                            detail = e.response.json().get("detail", str(e)) if e.response is not None else str(e)
                            st.error(f"{fmt.upper()} export failed: {detail}")
                        except Exception as e:
                            st.error(f"{fmt.upper()} export failed: {e}")

                if fmt in st.session_state.exported_files:
                    saved_name, saved_bytes = st.session_state.exported_files[fmt]
                    st.download_button(
                        f"⬇️ Save {saved_name}",
                        saved_bytes,
                        file_name=saved_name,
                        key=f"save_{fmt}",
                    )

    with tab2:
        if st.session_state.validated_claims:
            for c in st.session_state.validated_claims:
                st.markdown(
                    f"- **{c['text']}**  \n"
                    f"  ↳ [source]({c['source_paper_url']}) · confidence: {c['confidence']:.2f}"
                )
        else:
            st.info("No claims passed the grounding threshold for this query.")

    with tab3:
        if st.session_state.papers:
            table_data = [
                {
                    "Title": p["title"],
                    "Authors": ", ".join(p["authors"][:3]) + (" et al." if len(p["authors"]) > 3 else ""),
                    "Year": p.get("year", "—"),
                    "Source": p["source"],
                    "Citations": p.get("citation_count") if p.get("citation_count") is not None else "—",
                }
                for p in st.session_state.papers
            ]
            st.dataframe(table_data, use_container_width=True, hide_index=True)
        else:
            st.info("No papers to compare yet.")

    with tab4:
        if st.button("Build knowledge graph"):
            with st.spinner("Building paper/author graph..."):
                try:
                    r = requests.post(
                        f"{API_URL}/knowledge-graph",
                        json={"query": st.session_state.last_query, "session_id": st.session_state.session_id},
                        timeout=60,
                    )
                    r.raise_for_status()
                    kg_data = r.json()
                    if kg_data["papers_found"] == 0:
                        st.warning("No papers were found for this query, so there's nothing to graph.")
                    else:
                        with open(kg_data["graph_path"], "r", encoding="utf-8") as f:
                            st.components.v1.html(f.read(), height=650)
                except Exception as e:
                    st.error(f"Something went wrong: {e}")

    # ---- Interactive research chat ----
    st.divider()
    st.subheader("💬 Ask follow-up questions")
    st.caption("Grounded in the papers already retrieved for this query — no new search needed.")

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if chat_input := st.chat_input("Ask something about these papers..."):
        st.session_state.chat_history.append({"role": "user", "content": chat_input})
        with st.chat_message("user"):
            st.markdown(chat_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    r = requests.post(
                        f"{API_URL}/chat",
                        json={"session_id": st.session_state.session_id, "message": chat_input},
                        timeout=60,
                    )
                    r.raise_for_status()
                    answer = r.json()["answer"]
                except Exception as e:
                    answer = f"Something went wrong: {e}"
                st.markdown(answer)
                st.session_state.chat_history.append({"role": "assistant", "content": answer})
