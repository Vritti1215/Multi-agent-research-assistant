from functools import partial
from langgraph.graph import StateGraph, END

from graph.state import ResearchState
from agents.planner import planner_node
from agents.search_agent import search_node
from agents.retrieval_agent import retrieval_node
from agents.analysis_agent import analysis_node
from agents.citation_agent import citation_node
from agents.gap_contradiction_agent import gap_contradiction_node
from agents.report_agent import report_node
from agents.critique_agent import critique_node


def should_search_again(state: dict) -> str:
    """Loop back to search if too few claims got validated. Deep mode
    allows one extra retry since it's meant to dig further before settling."""
    cap = 3 if state.get("deep_mode") else 2
    if len(state.get("validated_claims", [])) < 2 and state["iteration"] < cap:
        return "search_again"
    return "proceed"


def after_critique(state: dict) -> str:
    """The Reflection routing decision: Plan -> Act -> Write -> Critique
    -> Revise, as a real loop with hard caps so it can never run forever.

    - "revise": evidence was fine, the WRITING missed the original
      question — go back to report_node in revision mode (same evidence,
      targeted rewrite), capped at 1 pass to keep this cheap.
    - "research_gap": the underlying evidence itself was too thin — loop
      back to search for more sources, sharing the same iteration budget
      as the citation-driven retry loop.
    - otherwise ("pass", or a cap was hit): deliver what we have.
    """
    verdict = state.get("critique_verdict", "pass")
    revision_cap = 1
    search_cap = 3 if state.get("deep_mode") else 2

    if verdict == "revise" and state.get("revision_iteration", 0) < revision_cap:
        return "revise"
    if verdict == "research_gap" and state.get("iteration", 0) < search_cap:
        return "research_gap"
    return "done"


def build_graph(session_id: str):
    graph = StateGraph(ResearchState)

    graph.add_node("planner", planner_node)
    graph.add_node("search", search_node)
    graph.add_node("retrieval", partial(retrieval_node, session_id=session_id))
    graph.add_node("analysis", analysis_node)
    graph.add_node("citation", citation_node)
    graph.add_node("gap_analysis", gap_contradiction_node)
    graph.add_node("report", report_node)
    graph.add_node("critique", critique_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "search")
    graph.add_edge("search", "retrieval")
    graph.add_edge("retrieval", "analysis")
    graph.add_edge("analysis", "citation")

    # gap_analysis only runs once per pass through this loop — NOT on
    # every citation retry — so it doesn't add extra LLM calls per retry.
    graph.add_conditional_edges(
        "citation",
        should_search_again,
        {"search_again": "search", "proceed": "gap_analysis"},
    )
    graph.add_edge("gap_analysis", "report")

    # The Reflection loop: critique the finished report against the
    # ORIGINAL question, then either revise the writing, re-search for
    # more evidence, or finish — never blind re-generation, always
    # feedback-driven, always capped.
    graph.add_edge("report", "critique")
    graph.add_conditional_edges(
        "critique",
        after_critique,
        {"revise": "report", "research_gap": "search", "done": END},
    )

    return graph.compile()


def initial_state(query: str, deep_mode: bool = False) -> dict:
    return {
        "query": query,
        "deep_mode": deep_mode,
        "domain": "General",
        "sub_questions": [],
        "papers": [],
        "retrieved_chunks": [],
        "analysis": "",
        "claims": [],
        "validated_claims": [],
        "contradictions": [],
        "gaps": [],
        "confidence_score": 0.0,
        "confidence_breakdown": {},
        "final_report": "",
        "report_path": None,
        "iteration": 0,
        "needs_more_search": False,
        "critique_verdict": "",
        "critique_feedback": "",
        "revision_iteration": 0,
    }


if __name__ == "__main__":
    # Manual end-to-end test, no FastAPI/Streamlit needed:
    #   conda activate research-agent
    #   python -m graph.orchestrator
    import uuid
    from dotenv import load_dotenv
    load_dotenv()

    session_id = str(uuid.uuid4())[:8]
    g = build_graph(session_id)
    result = g.invoke(initial_state("What are recent approaches to reducing hallucination in RAG systems?"))
    print(result["final_report"])
