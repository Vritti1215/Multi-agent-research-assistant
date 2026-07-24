from tools.vector_store import index_papers, retrieve


def retrieval_node(state: dict, session_id: str) -> dict:
    """Indexes newly found papers into Chroma, then retrieves the most
    relevant chunks for every sub-question."""
    index_papers(session_id, state["papers"])

    k = 12 if state.get("deep_mode") else 8

    all_chunks = []
    seen = set()
    for sq in state["sub_questions"]:
        for c in retrieve(session_id, sq, k=k):
            key = (c["title"], c["text"][:50])
            if key not in seen:
                seen.add(key)
                all_chunks.append(c)

    return {"retrieved_chunks": all_chunks}
