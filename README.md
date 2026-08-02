# Research Engine — Multi-Agent Research Assistant

An agentic research platform that plans its own research strategy, searches five academic sources, grounds every claim against retrieved text, critiques its own report against the original question, and revises before delivering — orchestrated as a LangGraph state machine, not a single prompt-and-response chatbot.

Given only a research question, the system autonomously: **plans → searches → retrieves → analyzes → validates citations → writes → critiques → revises**, with hard iteration caps so it can never loop forever.

---

## Why this exists

Most "AI research assistant" demos are a single RAG call with a nice UI. This project is built to demonstrate the patterns that actually matter in production agentic systems:

- **Multi-agent orchestration** with explicit state, not an implicit prompt chain
- **Grounded citation validation** — claims are checked against retrieved source text before being allowed into the report, with a confidence score that explains *why* it's confident or not
- **The Reflection pattern** — the system critiques its own output against the original question and decides whether to revise the writing or go get more evidence, capped so it's bounded and cheap
- **Explainability over black-box output** — every score, claim, and contradiction traces back to something concrete you can click into

---

## Architecture

```
                              ┌─────────────┐
                    ┌────────▶│   Planner    │  decomposes query into
                    │         │ (+ domain    │  sub-questions AND classifies
                    │         │ classifier)  │  domain (Medical/Legal/.../
                    │         └──────┬───────┘  General) — one call, no
                    │                │           extra cost
                    │                ▼
                    │         ┌─────────────┐
        research_gap│         │   Search     │  ArXiv, Semantic Scholar,
        (from        │         │ (5 sources)  │  OpenAlex, CrossRef, +
        critique)    │         └──────┬───────┘  Europe PMC if Medical
                    │                │
                    │                ▼
                    │         ┌─────────────┐
                    │         │  Retrieval   │  Chroma vector store
                    │         │   (RAG)      │
                    │         └──────┬───────┘
                    │                ▼
                    │         ┌─────────────┐
                    │         │  Analysis    │  domain-expert persona,
                    │         │              │  grounded in retrieved text
                    │         └──────┬───────┘
                    │                ▼
                    │         ┌─────────────┐
              search_again    │  Citation    │  extracts claims, verifies
              (too few        │ Validation   │  each against source chunks,
              grounded)◀──────┤              │  computes confidence score
                    │         └──────┬───────┘
                    │                │ (enough grounded claims)
                    │                ▼
                    │         ┌─────────────┐
                    │         │ Gap/Contra-  │  finds disagreements between
                    │         │  diction     │  sources + concrete research
                    │         │  Detection   │  gaps (single combined call)
                    │         └──────┬───────┘
                    │                ▼
                    │         ┌─────────────┐
              revise │◀───────│   Report     │  formal lit-review structure;
              (writing        │  Generation  │  in revision mode, rewrites
              missed the      └──────┬───────┘  against specific feedback
              question)              ▼
                    │         ┌─────────────┐
                    └─────────┤  Critique    │  compares the FINISHED report
                              │ (Reflection) │  against the ORIGINAL question
                              └──────┬───────┘  → pass / revise / research_gap
                                     ▼
                                   done
```

**Two independent, hard-capped retry loops:**
- Citation-driven: if too few claims get grounded, search again (capped at 2, or 3 in deep mode)
- Critique-driven: if the report itself misses the question, revise the writing (capped at 1); if evidence is too thin, go back to search (shares the search cap above)

Neither loop can run forever — both check an iteration counter before looping.

---

## Features

### Core pipeline
- Multi-agent orchestration via **LangGraph**, explicit typed state passed between nodes
- **RAG** over a Chroma vector store, populated from live search results per session
- **Citation validation** — every claim in the report is checked against actual retrieved source text; ungrounded claims are dropped, not hallucinated around
- **Confidence scoring** — computed from data (grounding strength, claim coverage, source breadth), not a separate LLM call, with a plain-English explanation of what's driving the score
- **Contradiction & gap detection** — finds where sources disagree and what they collectively fail to cover
- **Domain-expert routing** — the planner classifies the query's domain in its existing call and the analysis agent adopts that persona (Medical/Legal/Finance/Computer Vision/NLP/Cybersecurity/General) — zero extra API cost
- **The Reflection loop** — critiques the finished report against the original question and revises or re-searches accordingly (see architecture above)

### On-demand tools (one call each, not run automatically)
- **Research Proposal** — 11-section formal proposal targeting a real identified gap
- **Learning Roadmap** — phased curriculum grounded in the actual analysis
- **Experiment Designer** — dataset, training settings, metrics, baselines, ablations, hardware requirements
- **AI Peer Reviewer** — skeptical critique of the report with a real Accept/Revise/Reject-style verdict
- **Reproducibility Checker** — heuristic assessment of code/data availability and methodology detail (explicitly labeled as heuristic, not a verified audit)
- **Paper Comparison** — synthesized methodology/findings comparison across 2+ selected papers
- **Knowledge Graph** — paper/author co-authorship graph, tuned physics for a readable (non-chaotic) layout

### Interface
- Sidebar dashboard layout — all sections in one place, Dashboard tab as the landing view with KPIs, confidence breakdown, and source mix
- Light/dark mode
- Floating chatbot — ask follow-up questions grounded in the session's papers, or scope it to a single paper
- Inline PDF reader (modal) for papers with genuine open-access PDFs — clearly distinguished from papers that only have a landing-page link
- Per-paper annotations, workspace notes — both saved locally in the browser
- Research history — past queries saved locally, restorable
- Session sharing — copy a link, a teammate on the same running backend sees the same results read-only
- PDF / PPTX / DOCX export for the report and proposal

---

## Search sources

| Source | Cost | Notes |
|---|---|---|
| ArXiv | Free, no key | Always queried |
| Semantic Scholar | Free, key required (manual approval, ~hours to days) | Always queried; degrades gracefully without a key |
| OpenAlex | Free, key required as of Feb 2026 | Always queried; skipped cleanly without a key |
| CrossRef | Free, no key | Always queried; rarely has real PDF links (mostly metadata) |
| Europe PMC | Free, no key | Only queried when the domain classifier tags the query **Medical** |

---

## Setup

```bash
conda create -n research-agent python=3.11 -y
conda activate research-agent
pip install -r requirements.txt
```

Create `.env` in the project root:

```
GROQ_API_KEY=your_key_here
SEMANTIC_SCHOLAR_API_KEY=optional_but_recommended
OPENALEX_API_KEY=required_get_free_key_at_openalex.org/settings/api
```

- **Groq** (required): free at [console.groq.com/keys](https://console.groq.com/keys)
- **OpenAlex** (required as of Feb 2026): free at [openalex.org/settings/api](https://openalex.org/settings/api)
- **Semantic Scholar** (optional): request at [semanticscholar.org/product/api](https://www.semanticscholar.org/product/api#api-key) — manual approval, the app works fine without it in the meantime

## Run

```bash
uvicorn backend.main:app --reload --port 8000
```

Open **http://localhost:8000** — the backend serves the frontend directly, no separate frontend process needed.

---

## Project structure

```
research-assistant/
│
├── agents/                          # One file per LangGraph node / on-demand agent.
│   │                                 Each exposes a single function taking (and
│   │                                 usually returning updates to) the shared state.
│   ├── planner.py                    # Decomposes query into sub-questions +
│   │                                  classifies domain, in one LLM call
│   ├── search_agent.py               # Queries all search sources, dedupes results
│   ├── retrieval_agent.py            # Indexes papers into Chroma, retrieves chunks
│   ├── analysis_agent.py             # Synthesizes retrieved chunks, domain-persona
│   ├── citation_agent.py             # Extracts + verifies claims, scores confidence
│   ├── gap_contradiction_agent.py    # Finds disagreements + research gaps (1 call)
│   ├── report_agent.py               # Writes the report; also handles revision mode
│   ├── critique_agent.py             # Reflection: critiques report vs. original query
│   ├── proposal_agent.py             # On-demand: research proposal generator
│   ├── roadmap_agent.py              # On-demand: phased learning roadmap
│   ├── experiment_agent.py           # On-demand: ML experiment designer
│   ├── peer_reviewer_agent.py        # On-demand: skeptical report critique
│   ├── reproducibility_agent.py      # On-demand: heuristic reproducibility check
│   └── paper_comparison_agent.py     # On-demand: multi-paper comparison
│
├── tools/                            # External integrations, not LangGraph nodes.
│   ├── arxiv_tool.py                  # ArXiv search (free, no key)
│   ├── semantic_scholar_tool.py       # Semantic Scholar search (free, key optional)
│   ├── openalex_tool.py               # OpenAlex search (free, key required)
│   ├── crossref_tool.py               # CrossRef search (free, no key)
│   ├── europepmc_tool.py              # Europe PMC search (free, Medical-domain only)
│   ├── vector_store.py                # Chroma wrapper — index + retrieve
│   ├── llm_client.py                  # Single entry point for all LLM calls;
│   │                                    handles the Groq model fallback chain
│   ├── knowledge_graph.py             # Builds the paper/author pyvis graph
│   └── export_tool.py                 # PDF (xhtml2pdf) / PPTX / DOCX export
│
├── graph/
│   ├── state.py                       # Typed shared state schema (ResearchState)
│   └── orchestrator.py                # Builds + compiles the LangGraph graph;
│                                        defines both retry-loop routing functions
│
├── backend/
│   └── main.py                        # FastAPI app: every endpoint, in-memory
│                                        SESSIONS store, serves frontend/ as static
│
├── frontend/                          # No build step — plain files, served by FastAPI
│   ├── index.html                      # Structure: sidebar nav + dashboard + tabs
│   ├── styles.css                      # Theme (light/dark), layout, components
│   ├── script.js                       # All client-side logic, state, API calls
│   └── app.py                          # Legacy Streamlit UI — superseded by the
│                                         HTML/CSS/JS frontend above; safe to delete
│
├── data/chroma_db/                    # Vector store (gitignored, regenerated at runtime)
├── outputs/                           # Generated exports + knowledge graphs (gitignored)
│
├── .env.example                       # Template for required/optional API keys
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Testing & validation

This was tested iteratively and manually across many runs during development, not just written once and left alone:

**Core pipeline**
- Both normal mode and deep research mode, across multiple distinct query topics (RAG/hallucination-mitigation, LLM-as-a-judge, multi-agent coordination, and biomedical queries to exercise domain routing)
- The search-retry loop (too-few-grounded-claims → search again) observed triggering and recovering correctly
- The Reflection loop specifically: **both the `revise` and `research_gap` critique paths were observed firing** in real runs, not just reasoned about — confirming the report-rewrite-on-feedback branch and the capped re-search branch both work end to end
- Domain classification confirmed routing Medical queries to the Europe PMC source and the medical-analyst persona

**On-demand features** — each generated and regenerated multiple times across different sessions: research proposal, learning roadmap, experiment design, peer review, reproducibility check, paper comparison, knowledge graph (including the pyvis rendering/physics fix and the inline-vs-download bug fix)

**Interface** — sidebar navigation, dashboard-first layout, light/dark theme persistence, floating chatbot (both global and per-paper-scoped), workspace notes and per-paper annotations (localStorage persistence), research history restore, session sharing via link, PDF/PPTX/DOCX export for both report and proposal

**Search sources** — all 5 sources confirmed returning results independently; graceful degradation confirmed when Semantic Scholar (no key yet) and OpenAlex (key required post-Feb-2026) are unavailable — the pipeline continues with whichever sources are working rather than failing outright

### On accuracy, specifically

Citation validation and confidence scoring are real, working mechanisms — every claim in a report is checked against actual retrieved source text before being included, and the confidence score is computed from that grounding data. What this project does **not** yet have is a fixed benchmark number (e.g. "grounds N% of claims correctly across a 15-query eval set") — that requires a dedicated eval script with an LLM-judge or manual scoring pass, which is the top item in Future Work below. Worth building before claiming a specific accuracy figure anywhere formal, like a resume.



Being upfront about these rather than hiding them:

- **Sessions are in-memory, not a database.** They reset on backend restart. Session sharing and the "check for new papers" delta both depend on the backend staying up.
- **No real multiplayer collaboration.** Session sharing is a read-only link against an in-memory session, not live sync between users. Real collaboration would need auth, a shared database, and likely websockets.
- **Domain routing changes the analysis persona, not the retrieval strategy** (except for Europe PMC on Medical queries specifically). It's not six fully separate specialized agents.
- **Reproducibility checks are heuristic**, based on abstracts and synthesized analysis text — not a verified audit of actual code repositories.
- **CrossRef rarely provides real PDF links** — most results link to a landing page (often paywalled), clearly labeled as such in the UI rather than presented as a PDF.
- **Free-tier rate limits apply** (Groq daily token budget, ArXiv request pacing) — heavy testing in a short window can hit these; the LLM client falls back to a smaller model automatically on rate-limit errors.
- **No automated evaluation suite yet** — citation validation and confidence scoring are real mechanisms, but there isn't yet a fixed eval set with a faithfulness benchmark score.

## What I'd build next

- A 10-15 query evaluation set with an LLM-judge faithfulness score, to turn "the pipeline validates citations" into a measured number
- Deployment (Render/Railway) so this is a live link, not just clone-and-run
- A persistent store (Redis/Postgres) so sessions survive restarts and sharing/history work reliably
- True PDF highlighting via PDF.js, beyond the current per-paper text annotations

---

## Tech stack

### Backend
| Component | Choice | Why |
|---|---|---|
| Language | Python 3.11 | |
| Web framework | FastAPI | Async, typed request/response models via Pydantic, serves the frontend as static files from the same process |
| Agent orchestration | LangGraph | Explicit typed state machine with conditional edges — not an implicit prompt chain; makes the two retry loops (search-retry, critique-revise) inspectable and independently capped |
| LLM provider | Groq | Free tier; `llama-3.3-70b-versatile` primary, automatic fallback to `llama-3.1-8b-instant` on rate limits |
| Vector store | ChromaDB | In-process, per-session collections, no external service to run |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) | Runs on CPU; automatically uses CUDA if available, no code change needed |
| Server | Uvicorn | ASGI server, `--reload` for development |

### Frontend
| Component | Choice | Why |
|---|---|---|
| Framework | None — vanilla HTML/CSS/JS | No build step, no node_modules; the whole UI is 3 static files served directly |
| Markdown rendering | marked.js (CDN) | Renders agent-generated Markdown (report, proposal, roadmap, etc.) client-side |
| State management | Plain JS object + `localStorage` | Session state in memory during use; notes, annotations, theme, and history persisted locally per-browser |

### Search & data sources
| Source | Type | Auth |
|---|---|---|
| ArXiv | Preprint repository | None |
| Semantic Scholar | Academic search API | Optional key (higher rate limit) |
| OpenAlex | Open scholarly index | Required key (as of Feb 2026) |
| CrossRef | DOI/citation metadata | None |
| Europe PMC | Biomedical literature | None (queried only for Medical-domain queries) |

### Document generation
| Format | Library |
|---|---|
| PDF | xhtml2pdf (pure Python, no OS-level GTK dependency — deliberately chosen over WeasyPrint for portability) |
| PPTX | python-pptx |
| DOCX | python-docx |
| Knowledge graph | NetworkX (graph structure) + pyvis (interactive HTML rendering) |

### Dev environment
| Tool | Purpose |
|---|---|
| Anaconda / conda | Environment + dependency isolation |
| python-dotenv | Loads `.env` for API keys |
| `requests` / `arxiv` (PyPI) | HTTP clients for the search tools |
