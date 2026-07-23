# Multi-Agent Research Assistant

Agentic RAG system that plans, searches ArXiv/Semantic Scholar, retrieves
with Chroma, analyzes, validates claims against sources, and produces a
citation-grounded Markdown report — orchestrated as a LangGraph state
machine with a conditional retry loop.

## Setup (Windows / Anaconda)

```powershell
conda create -n research-agent python=3.11 -y
conda activate research-agent
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your **Groq** API key (free — get
one at https://console.groq.com/keys, no billing required):

```powershell
copy .env.example .env
```

All LLM calls go through `tools/llm_client.py`, which uses
`llama-3.3-70b-versatile` on Groq's free tier. If you hit rate limits
mid-run, switch to `llama-3.1-8b-instant` in that file — much higher
free-tier throughput, some drop in output quality for the analysis/report
steps.

## Run order

1. **Sanity check the pipeline end-to-end without any UI:**
   ```powershell
   python -m graph.orchestrator
   ```
   This runs one hardcoded query through the full graph and prints the report.
   Do this first — it's much easier to debug than through the API/UI.

2. **Start the backend:**
   ```powershell
   uvicorn backend.main:app --reload --port 8000
   ```

3. **Start the UI (separate terminal, same conda env):**
   ```powershell
   streamlit run frontend/app.py
   ```

Open the Streamlit URL it prints (usually http://localhost:8501).

## Project layout

- `agents/` — one file per LangGraph node (planner, search, retrieval, analysis, citation, report)
- `tools/` — external API wrappers (ArXiv, Semantic Scholar) and the Chroma vector store
- `graph/` — shared state schema + the compiled LangGraph orchestrator
- `backend/` — FastAPI app exposing `/research` and `/knowledge-graph`
- `frontend/` — Streamlit UI
- `eval/` — put your evaluation query set here (see guide for the LLM-judge pattern)

## Notes

- Embeddings run on CPU by default via `sentence-transformers`; if you have
  a CUDA-capable GPU with a matching torch build installed, it'll be used
  automatically — no code changes needed.
- Using Groq instead of a paid API is itself worth a line in an interview:
  it shows you can design against provider constraints (free-tier rate
  limits) rather than just calling an API. `tools/llm_client.py` is the
  single swap point if you want to try a different provider later.
- The citation agent makes one LLM call per extracted claim (batched against
  all candidate chunks at once) rather than one call per claim-per-chunk —
  keep this in mind when discussing cost tradeoffs in interviews.
- `graph.add_conditional_edges` in `graph/orchestrator.py` is the loop that
  sends the pipeline back to search if too few claims get grounded — capped
  at 2 iterations so it can't run away on a thin topic.
