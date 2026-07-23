import os
import sys
import uuid

# allow `python backend/main.py` to find sibling packages (agents/, tools/, graph/)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from graph.orchestrator import build_graph, initial_state  # uses Groq via tools/llm_client.py
from tools.knowledge_graph import build_paper_graph

app = FastAPI(title="Multi-Agent Research Assistant")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ResearchRequest(BaseModel):
    query: str


@app.post("/research")
def run_research(req: ResearchRequest):
    if not req.query.strip():
        raise HTTPException(400, "Query cannot be empty")

    session_id = str(uuid.uuid4())[:8]
    graph = build_graph(session_id)

    try:
        final_state = graph.invoke(initial_state(req.query))
    except Exception as e:
        raise HTTPException(500, f"Research pipeline failed: {e}")

    return {
        "session_id": session_id,
        "report": final_state["final_report"],
        "papers_found": len(final_state["papers"]),
        "validated_claims": final_state["validated_claims"],
    }


@app.post("/knowledge-graph")
def knowledge_graph(req: ResearchRequest):
    """Re-runs search only (no LLM analysis) to build a quick paper/author graph."""
    from agents.search_agent import search_node
    from agents.planner import planner_node

    state = initial_state(req.query)
    state.update(planner_node(state))
    state.update(search_node(state))

    path = f"outputs/kg_{uuid.uuid4().hex[:8]}.html"
    os.makedirs("outputs", exist_ok=True)
    build_paper_graph(state["papers"], path)
    return {"graph_path": path, "papers_found": len(state["papers"])}


@app.get("/health")
def health():
    return {"status": "ok"}
