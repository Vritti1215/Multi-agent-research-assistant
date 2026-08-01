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
from fastapi.staticfiles import StaticFiles
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

# In-memory session store: session_id -> {...}. Resets on server restart —
# fine for a portfolio demo. Swap for Redis/DB if you ever need this to
# survive restarts or scale beyond one process.
SESSIONS: dict[str, dict] = {}


class ResearchRequest(BaseModel):
    query: str
    deep_mode: bool = False


@app.post("/research")
def run_research(req: ResearchRequest):
    if not req.query.strip():
        raise HTTPException(400, "Query cannot be empty")

    session_id = str(uuid.uuid4())[:8]

    try:
        graph = build_graph(session_id)
        final_state = graph.invoke(initial_state(req.query, deep_mode=req.deep_mode))

        papers = final_state.get("papers", [])
        SESSIONS[session_id] = {
            "papers": papers,
            "query": req.query,
            "analysis": final_state.get("analysis", ""),
            "gaps": final_state.get("gaps", []),
            "contradictions": final_state.get("contradictions", []),
            "domain": final_state.get("domain", "General"),
            "report": final_state.get("final_report", ""),
            "sub_questions": final_state.get("sub_questions", []),
            "deep_mode": req.deep_mode,
            "confidence_score": final_state.get("confidence_score", 0),
            "confidence_breakdown": final_state.get("confidence_breakdown", {}),
            "validated_claims": final_state.get("validated_claims", []),
            "critique_verdict": final_state.get("critique_verdict", ""),
            "critique_feedback": final_state.get("critique_feedback", ""),
            "revision_count": final_state.get("revision_iteration", 0),
        }

        return {
            "session_id": session_id,
            "report": final_state.get("final_report", "No report was generated."),
            "papers": papers,
            "papers_found": len(papers),
            "validated_claims": final_state.get("validated_claims", []),
            "contradictions": final_state.get("contradictions", []),
            "gaps": final_state.get("gaps", []),
            "confidence_score": final_state.get("confidence_score", 0),
            "confidence_breakdown": final_state.get("confidence_breakdown", {}),
            "domain": final_state.get("domain", "General"),
            "critique_verdict": final_state.get("critique_verdict", ""),
            "critique_feedback": final_state.get("critique_feedback", ""),
            "revision_count": final_state.get("revision_iteration", 0),
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Research pipeline failed: {e}")


@app.get("/session/{session_id}")
def get_session(session_id: str):
    """Read-only fetch of an existing session's full results — powers the
    'Share with a teammate' link. Anyone with the URL (and access to this
    running backend, e.g. same machine or local network) can view the
    same results without re-running the pipeline. Note: this only works
    while the backend process is still running and hasn't restarted —
    sessions are in-memory, not a database."""
    if session_id not in SESSIONS:
        raise HTTPException(404, "Session not found — it may have expired if the server restarted.")

    s = SESSIONS[session_id]
    return {
        "session_id": session_id,
        "query": s.get("query", ""),
        "report": s.get("report", ""),
        "papers": s.get("papers", []),
        "papers_found": len(s.get("papers", [])),
        "validated_claims": s.get("validated_claims", []),
        "contradictions": s.get("contradictions", []),
        "gaps": s.get("gaps", []),
        "confidence_score": s.get("confidence_score", 0),
        "confidence_breakdown": s.get("confidence_breakdown", {}),
        "domain": s.get("domain", "General"),
        "critique_verdict": s.get("critique_verdict", ""),
        "critique_feedback": s.get("critique_feedback", ""),
        "revision_count": s.get("revision_count", 0),
    }


class KGRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


@app.post("/knowledge-graph")
def knowledge_graph(req: KGRequest):
    """Reuses papers already found in a prior /research call when
    session_id is provided (no wasted API calls); otherwise runs a fresh
    search for standalone use."""
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Knowledge graph generation failed: {e}")

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

    # HTML files (the knowledge graph) need to render INSIDE the iframe,
    # not force a browser download. FileResponse sets Content-Disposition:
    # attachment automatically whenever `filename` is passed.
    if path.endswith(".html"):
        return FileResponse(path, media_type="text/html")

    return FileResponse(path, filename=os.path.basename(path))


class ChatRequest(BaseModel):
    session_id: str
    message: str
    paper_title: Optional[str] = None  # if set, scopes the answer to just this one paper


@app.post("/chat")
def chat(req: ChatRequest):
    """Interactive follow-up Q&A. If paper_title is given, answers using
    ONLY that paper's abstract ('chat with this paper'); otherwise
    retrieves across everything indexed for the session."""
    try:
        from tools.llm_client import call_llm

        if req.session_id not in SESSIONS:
            raise HTTPException(404, "Unknown session — run a research query first.")

        if req.paper_title:
            session = SESSIONS[req.session_id]
            paper = next((p for p in session.get("papers", []) if p["title"] == req.paper_title), None)
            if not paper:
                return {"answer": "I couldn't find that paper in this session anymore."}
            context = f"[{paper['title']}]: {paper.get('abstract', 'No abstract available.')}"
            scope_note = f"You are answering questions about ONLY this one paper: \"{paper['title']}\". "
        else:
            from tools.vector_store import retrieve
            chunks = retrieve(req.session_id, req.message, k=6)
            if not chunks:
                return {"answer": "I don't have any relevant indexed papers for that question yet."}
            context = "\n\n".join(f"[{c['title']}]: {c['text'][:500]}" for c in chunks)
            scope_note = ""

        prompt = f"""{scope_note}Answer the question using ONLY the sources
below. Cite paper titles inline like [Title]. If the sources don't cover
it, say so plainly rather than guessing.

QUESTION: {req.message}

SOURCES:
{context}"""
        answer = call_llm(prompt, max_tokens=800)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Chat failed: {e}")

    return {"answer": answer}


class CompareRequest(BaseModel):
    session_id: str
    paper_titles: list[str]


@app.post("/compare-papers")
def compare_papers(req: CompareRequest):
    """On-demand, single LLM call comparing 2+ selected papers."""
    if req.session_id not in SESSIONS:
        raise HTTPException(404, "Unknown session — run a research query first.")
    if len(req.paper_titles) < 2:
        raise HTTPException(400, "Select at least 2 papers to compare.")

    try:
        from agents.paper_comparison_agent import generate_paper_comparison

        session = SESSIONS[req.session_id]
        selected = [p for p in session.get("papers", []) if p["title"] in req.paper_titles]
        if len(selected) < 2:
            raise HTTPException(400, "Couldn't find enough of the selected papers in this session.")
        comparison = generate_paper_comparison(selected)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Comparison failed: {e}")

    return {"comparison": comparison}


class ProposalRequest(BaseModel):
    session_id: str


@app.post("/research-proposal")
def research_proposal(req: ProposalRequest):
    if req.session_id not in SESSIONS:
        raise HTTPException(404, "Unknown session — run a research query first.")

    try:
        from agents.proposal_agent import generate_proposal
        session = SESSIONS[req.session_id]
        proposal = generate_proposal(
            session["query"], session.get("analysis", ""), session.get("gaps", [])
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Proposal generation failed: {e}")

    return {"proposal": proposal}


class RoadmapRequest(BaseModel):
    session_id: str


@app.post("/research-roadmap")
def research_roadmap(req: RoadmapRequest):
    if req.session_id not in SESSIONS:
        raise HTTPException(404, "Unknown session — run a research query first.")

    try:
        from agents.roadmap_agent import generate_roadmap
        session = SESSIONS[req.session_id]
        roadmap = generate_roadmap(session["query"], session.get("analysis", ""))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Roadmap generation failed: {e}")

    return {"roadmap": roadmap}


class ExperimentRequest(BaseModel):
    session_id: str


@app.post("/experiment-design")
def experiment_design(req: ExperimentRequest):
    if req.session_id not in SESSIONS:
        raise HTTPException(404, "Unknown session — run a research query first.")

    try:
        from agents.experiment_agent import generate_experiment_design
        session = SESSIONS[req.session_id]
        design = generate_experiment_design(session["query"], session.get("analysis", ""))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Experiment design generation failed: {e}")

    return {"experiment_design": design}


class PeerReviewRequest(BaseModel):
    session_id: str


@app.post("/peer-review")
def peer_review(req: PeerReviewRequest):
    if req.session_id not in SESSIONS:
        raise HTTPException(404, "Unknown session — run a research query first.")

    try:
        from agents.peer_reviewer_agent import generate_peer_review
        session = SESSIONS[req.session_id]
        review = generate_peer_review(
            session["query"], session.get("report", ""), session.get("confidence_breakdown", {})
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Peer review generation failed: {e}")

    return {"review": review}


@app.post("/reproducibility-check")
def reproducibility_check(req: PeerReviewRequest):
    if req.session_id not in SESSIONS:
        raise HTTPException(404, "Unknown session — run a research query first.")

    try:
        from agents.reproducibility_agent import generate_reproducibility_check
        session = SESSIONS[req.session_id]
        check = generate_reproducibility_check(
            session["query"], session.get("analysis", ""), session.get("papers", [])
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Reproducibility check failed: {e}")

    return {"reproducibility_check": check}


@app.post("/check-new-papers")
def check_new_papers(req: PeerReviewRequest):
    """Honest 'live monitoring' — no background scheduler (this app has
    no persistent DB or cron), but re-runs the SAME sub-questions against
    all four sources right now and diffs against what was already found."""
    if req.session_id not in SESSIONS:
        raise HTTPException(404, "Unknown session — run a research query first.")

    try:
        from agents.search_agent import search_node
        session = SESSIONS[req.session_id]
        known_titles = {p["title"].lower() for p in session.get("papers", [])}

        temp_state = {
            "sub_questions": session.get("sub_questions", [session["query"]]),
            "deep_mode": session.get("deep_mode", False),
            "papers": [],
            "iteration": 0,
        }
        result = search_node(temp_state)
        fresh_papers = result.get("papers", [])
        new_papers = [p for p in fresh_papers if p["title"].lower() not in known_titles]
        session["papers"] = session.get("papers", []) + new_papers
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Search failed: {e}")

    return {"new_papers": new_papers, "new_count": len(new_papers)}


@app.get("/health")
def health():
    return {"status": "ok"}


# Serves frontend/index.html at "/" and any other static assets in that
# folder. Mounted LAST, after every @app.get/@app.post route above — FastAPI
# matches explicit routes first, so this only catches what nothing else
# handled, meaning it can't accidentally shadow /research, /chat, etc.
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
