from typing import TypedDict, List, Optional
from pydantic import BaseModel


class Paper(BaseModel):
    title: str
    authors: List[str]
    abstract: str
    url: str
    year: Optional[int] = None
    source: str  # "arxiv" or "semantic_scholar"
    citation_count: Optional[int] = None


class Claim(BaseModel):
    text: str
    source_paper_url: str
    confidence: float  # grounding confidence, 0-1


class ResearchState(TypedDict):
    query: str
    sub_questions: List[str]
    papers: List[dict]          # serialized Paper objects
    retrieved_chunks: List[dict]
    analysis: str
    claims: List[dict]          # serialized Claim objects
    validated_claims: List[dict]
    final_report: str
    report_path: Optional[str]
    iteration: int               # for retry/loop tracking
    needs_more_search: bool
