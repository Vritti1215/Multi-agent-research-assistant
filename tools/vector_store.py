import chromadb
from chromadb.utils import embedding_functions

client = chromadb.PersistentClient(path="./data/chroma_db")

# Runs on CPU by default; will use CUDA automatically if a GPU + matching
# torch build is available (no code change needed).
embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)


def get_collection(session_id: str):
    return client.get_or_create_collection(
        name=f"research_{session_id}",
        embedding_function=embed_fn,
    )


def index_papers(session_id: str, papers: list[dict]):
    collection = get_collection(session_id)
    docs, ids, metadatas = [], [], []
    for i, p in enumerate(papers):
        chunk_text = f"{p['title']}\n\n{p['abstract']}"
        docs.append(chunk_text)
        ids.append(f"{session_id}_{i}_{hash(p['url']) % 100000}")
        metadatas.append({"title": p["title"], "url": p["url"], "source": p["source"]})
    if docs:
        collection.upsert(documents=docs, ids=ids, metadatas=metadatas)


def retrieve(session_id: str, query: str, k: int = 6) -> list[dict]:
    collection = get_collection(session_id)

    # Querying a completely empty collection can raise rather than return
    # an empty result — this happens when every search source failed for
    # this run (rate limits, network issues, etc.). Fail soft here so the
    # rest of the pipeline can still produce a report explaining that no
    # sources were found, instead of the whole request crashing with a 500.
    count = collection.count()
    if count == 0:
        return []

    results = collection.query(query_texts=[query], n_results=min(k, count))
    chunks = []
    if not results["documents"]:
        return chunks
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        chunks.append({"text": doc, "title": meta["title"], "url": meta["url"]})
    return chunks
