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


def should_search_again(state: dict) -> str:
    """Loop back to search if too few claims got validated. Deep mode
    allows one extra retry since it's meant to dig further before settling."""
    cap = 3 if state.get("deep_mode") else 2
    if len(state.get("validated_claims", [])) < 2 and state["iteration"] < cap:
        return "search_again"
    return "proceed"


def build_graph(session_id: str):
    graph = StateGraph(ResearchState)

    graph.add_node("planner", planner_node)
    graph.add_node("search", search_node)
    graph.add_node("retrieval", partial(retrieval_node, session_id=session_id))
    graph.add_node("analysis", analysis_node)
    graph.add_node("citation", citation_node)
    graph.add_node("gap_analysis", gap_contradiction_node)
    graph.add_node("report", report_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "search")
    graph.add_edge("search", "retrieval")
    graph.add_edge("retrieval", "analysis")
    graph.add_edge("analysis", "citation")

    # gap_analysis only runs once, on the final pass — NOT inside the
    # search-retry loop — so it doesn't add extra LLM calls on every retry.
    graph.add_conditional_edges(
        "citation",
        should_search_again,
        {"search_again": "search", "proceed": "gap_analysis"},
    )
    graph.add_edge("gap_analysis", "report")
    graph.add_edge("report", END)

    return graph.compile()


def initial_state(query: str, deep_mode: bool = False) -> dict:
    return {
        "query": query,
        "deep_mode": deep_mode,
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
