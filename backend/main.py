import os
import sys
import uuid

# allow `python backend/main.py` to find sibling packages (agents/, tools/, graph/)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from graph.orchestrator import build_graph, initial_state  # uses Groq via tools/llm_client.py
from tools.knowledge_graph import build_paper_graph

app = FastAPI(title="Multi-Agent Research Assistant")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store: session_id -> {"papers": [...], "query": str}
# Resets on server restart — fine for a portfolio demo. Swap for Redis/DB
# if you ever need this to survive restarts.
SESSIONS: dict[str, dict] = {}


class ResearchRequest(BaseModel):
    query: str
    deep_mode: bool = False


@app.post("/research")
def run_research(req: ResearchRequest):
    if not req.query.strip():
        raise HTTPException(400, "Query cannot be empty")

    session_id = str(uuid.uuid4())[:8]
    graph = build_graph(session_id)

    try:
        final_state = graph.invoke(initial_state(req.query, deep_mode=req.deep_mode))
    except Exception as e:
        raise HTTPException(500, f"Research pipeline failed: {e}")

    SESSIONS[session_id] = {"papers": final_state["papers"], "query": req.query}

    return {
        "session_id": session_id,
        "report": final_state["final_report"],
        "papers": final_state["papers"],  # for the paper-comparison table
        "papers_found": len(final_state["papers"]),
        "validated_claims": final_state["validated_claims"],
    }


class KGRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


@app.post("/knowledge-graph")
def knowledge_graph(req: KGRequest):
    """Reuses papers already found in a prior /research call when
    session_id is provided (no wasted API calls); otherwise runs a fresh
    search for standalone use."""
    if req.session_id and req.session_id in SESSIONS:
        papers = SESSIONS[req.session_id]["papers"]
    else:
        from agents.search_agent import search_node
        from agents.planner import planner_node

        state = initial_state(req.query)
        state.update(planner_node(state))
        state.update(search_node(state))
        papers = state["papers"]

    os.makedirs("outputs", exist_ok=True)
    path = f"outputs/kg_{uuid.uuid4().hex[:8]}.html"
    build_paper_graph(papers, path)
    return {"graph_path": path, "papers_found": len(papers)}


class ExportRequest(BaseModel):
    report: str
    query: str
    format: str  # "pdf" | "pptx" | "docx"


@app.post("/export")
def export_report(req: ExportRequest):
    os.makedirs("outputs", exist_ok=True)
    fname = f"outputs/report_{uuid.uuid4().hex[:8]}"
    title = (req.query[:70] or "Research Report")

    try:
        if req.format == "pdf":
            from tools.export_tool import export_pdf
            path = export_pdf(req.report, fname + ".pdf", title=title)
        elif req.format == "pptx":
            from tools.export_tool import export_pptx
            path = export_pptx(req.report, fname + ".pptx", title=title)
        elif req.format == "docx":
            from tools.export_tool import export_docx
            path = export_docx(req.report, fname + ".docx", title=title)
        else:
            raise HTTPException(400, "format must be pdf, pptx, or docx")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"{req.format.upper()} export failed: {e}")

    return {"path": path}


@app.get("/download")
def download(path: str):
    if not path.startswith("outputs") or not os.path.exists(path):
        raise HTTPException(404, "File not found")
    return FileResponse(path, filename=os.path.basename(path))


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.post("/chat")
def chat(req: ChatRequest):
    """Interactive follow-up Q&A grounded in the papers already indexed
    for this session — lets the user dig into the research without
    re-running the whole pipeline."""
    from tools.vector_store import retrieve
    from tools.llm_client import call_llm

    if req.session_id not in SESSIONS:
        raise HTTPException(404, "Unknown session — run a research query first.")

    chunks = retrieve(req.session_id, req.message, k=6)
    if not chunks:
        return {"answer": "I don't have any relevant indexed papers for that question yet."}

    context = "\n\n".join(f"[{c['title']}]: {c['text'][:500]}" for c in chunks)
    prompt = f"""Answer the question using ONLY the sources below. Cite
paper titles inline like [Title]. If the sources don't cover it, say so
plainly rather than guessing.

QUESTION: {req.message}

SOURCES:
{context}"""
    answer = call_llm(prompt, max_tokens=800)
    return {"answer": answer}


@app.get("/health")
def health():
    return {"status": "ok"}
