# Autonomous Multi-Agent Framework Using Agentic RAG
### Iterative Knowledge Synthesis and Report Generation

> **Capstone Project** | Prabhav Srivastava (22BIT0266) | VIT, Dept. of Information Technology  
> Guide: Dr. Sweta Bhattacharya | BITE498J – Project II

---

## Overview

A production-ready autonomous research system that overcomes the limitations of traditional single-pass RAG by deploying four specialized AI agents in an iterative refinement loop.

```
User Query
    │
    ▼
┌─────────────┐    subtasks    ┌──────────────────┐
│   PLANNER   │──────────────▶│   RESEARCHER      │
│   Agent     │◀──────────────│   Agent           │
│ Task Decomp │   gap queries │ Semantic Retrieval │
└─────────────┘               └────────┬─────────┘
       ▲                               │ evidence
       │                               ▼
       │                      ┌──────────────────┐
       │    critique +         │   ANALYST        │
       │    new queries        │   Agent          │
       └───────────────────────│ Gap Detection &  │
                               │ Self-Critique    │
                               └────────┬─────────┘
                                        │ validated evidence
                                        ▼
                               ┌──────────────────┐
                               │   WRITER         │
                               │   Agent          │
                               │ Report Synthesis │
                               └────────┬─────────┘
                                        │
                                        ▼
                               ┌──────────────────┐
                               │  RESEARCH REPORT │
                               │  PDF/HTML/MD     │
                               │  with Citations  │
                               └──────────────────┘
```

**Iterative loop** continues until:
- Coverage score ≥ 75% (configurable)
- Analyst confidence ≥ 85%
- OR max iteration count reached

---

## Architecture

### Backend (Python + FastAPI)

```
backend/
├── main.py                  # FastAPI app, all REST endpoints
├── config.py                # Settings via pydantic-settings + .env
├── agents/
│   ├── base_agent.py        # Abstract base: LLM invocation, retry, logging
│   ├── planner.py           # PlannerAgent: query → subtasks + roadmap
│   ├── researcher.py        # ResearcherAgent: query expansion + retrieval
│   ├── analyst.py           # AnalystAgent: coverage scoring + gap detection
│   └── writer.py            # WriterAgent: structured report + citations
├── core/
│   ├── vector_store.py      # ChromaDB / FAISS abstraction
│   ├── document_processor.py# PDF/TXT/HTML/MD/DOCX ingestion pipeline
│   └── orchestrator.py      # Multi-agent coordination + SSE streaming
└── models/
    └── schemas.py           # All Pydantic models (request/response/session)
```

### Frontend (React + TypeScript + TailwindCSS)

```
frontend/src/
├── pages/
│   ├── ResearchPage.tsx     # Query input + agent pipeline diagram
│   ├── DocumentsPage.tsx    # Drag & drop upload + knowledge base manager
│   ├── MonitorPage.tsx      # Real-time SSE agent activity log + report viewer
│   ├── SessionsPage.tsx     # All research sessions list
│   └── EvaluatePage.tsx     # Quality metrics + comparison vs. baseline RAG
├── components/
│   ├── Sidebar.tsx          # Navigation
│   ├── ReportViewer.tsx     # Sectioned report with citations + quality rings
│   └── ui.tsx               # AgentBadge, StatusBadge, ProgressBar, ScoreRing
├── api/
│   └── index.ts             # Axios API client + SSE helper
└── types/
    └── index.ts             # All TypeScript interfaces
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, Uvicorn |
| LLM Orchestration | LangChain, with Anthropic / OpenAI / Ollama |
| Multi-Agent | Custom orchestrator (inspired by AutoGen / CrewAI patterns) |
| Vector Database | ChromaDB (default) or FAISS |
| Embeddings | Sentence Transformers (`all-MiniLM-L6-v2`) or OpenAI |
| Document Processing | PyPDF, BeautifulSoup4, python-docx |
| Frontend | React 18, TypeScript, Vite, TailwindCSS |
| Streaming | Server-Sent Events (SSE) via `sse-starlette` |
| Containerization | Docker + Docker Compose |

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- A free API key from **Groq** or **Cerebras** (or Ollama for fully local)

### Free LLM Providers

| Provider | Free Tier | Sign-Up | Best Models |
|----------|-----------|---------|-------------|
| **Groq** ⭐ | ✅ No credit card | [console.groq.com](https://console.groq.com) | `llama-3.3-70b-versatile`, `llama-3.1-8b-instant` |
| **Cerebras** ⭐ | ✅ No credit card | [cloud.cerebras.ai](https://cloud.cerebras.ai) | `llama3.1-70b`, `llama3.1-8b` |
| **Ollama** | ✅ Fully local | [ollama.ai](https://ollama.ai) | `llama3.1`, `mistral` |
| Anthropic | ❌ Paid | — | claude-3-5-sonnet |
| OpenAI | ❌ Paid | — | gpt-4o-mini |

### 1. Clone & configure

```bash
git clone https://github.com/yourusername/agentic-rag.git
cd agentic-rag

cp backend/.env.example backend/.env
# Minimum config for free Groq:
#   LLM_PROVIDER=groq
#   GROQ_API_KEY=gsk_...   ← from https://console.groq.com (free, no CC)
#
# Or for free Cerebras:
#   LLM_PROVIDER=cerebras
#   CEREBRAS_API_KEY=csk_... ← from https://cloud.cerebras.ai (free)
```

### 2. Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Backend runs at: http://localhost:8000  
API docs: http://localhost:8000/docs

### 3. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: http://localhost:5173

### 4. Docker Compose (full stack)

```bash
# Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

docker compose up --build
```

- Frontend: http://localhost:5173  
- Backend API: http://localhost:8000

---

## Configuration

All settings in `backend/.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `anthropic` | `anthropic` \| `openai` \| `ollama` |
| `ANTHROPIC_API_KEY` | — | Claude API key |
| `OPENAI_API_KEY` | — | GPT API key |
| `VECTOR_DB` | `chromadb` | `chromadb` \| `faiss` |
| `EMBEDDING_PROVIDER` | `sentence_transformers` | Local or OpenAI embeddings |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | HuggingFace model name |
| `CHUNK_SIZE` | `500` | Tokens per document chunk |
| `CHUNK_OVERLAP` | `50` | Overlap between chunks |
| `MAX_ITERATIONS` | `5` | Maximum refinement cycles |
| `COVERAGE_THRESHOLD` | `0.75` | Minimum coverage to stop |
| `ANALYST_CONFIDENCE_THRESHOLD` | `0.85` | Minimum confidence to stop |
| `TOP_K_RETRIEVAL` | `8` | Top-k documents per query |

---

## API Reference

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/documents/upload` | Upload document (multipart/form-data) |
| `GET` | `/api/documents` | List all documents |
| `GET` | `/api/documents/{id}` | Get document status |
| `DELETE` | `/api/documents/{id}` | Remove document + chunks |

### Research

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/research/start` | Start research session |
| `GET` | `/api/research/{id}/status` | Poll session status |
| `GET` | `/api/research/{id}/stream` | SSE real-time stream |
| `GET` | `/api/research/{id}/report` | Get full report JSON |
| `GET` | `/api/research/{id}/report/markdown` | Download Markdown report |
| `GET` | `/api/research/{id}/evaluate` | Get evaluation metrics |
| `GET` | `/api/research` | List all sessions |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/system/stats` | System statistics |

---

## Agent Design Details

### Planner Agent
- **Model**: `claude-3-5-haiku` (fast + cheap for planning)
- **Input**: Raw user research query
- **Output**: `ResearchPlan` with 4–7 subtasks, each with targeted search queries
- **Gap Filling**: When Analyst detects gaps, Planner generates new subtasks

### Researcher Agent
- **Model**: `claude-3-5-haiku`
- **Query Expansion**: Reformulates each subtask into 6–8 diverse queries
- **Multi-hop Retrieval**: Runs all expanded queries against vector DB
- **Evidence Scoring**: LLM scores each chunk by relevance (0–1)
- **Deduplication**: Removes duplicate chunk IDs across queries

### Analyst Agent  
- **Model**: `claude-3-5-sonnet` (deeper reasoning for critique)
- **Coverage Scoring**: 0–1 score across all subtasks + sections
- **Gap Detection**: Identifies specific missing information
- **Contradiction Detection**: Flags conflicting claims across sources
- **Stopping Decision**: Returns `sufficient=True` when thresholds met
- **Inspired by**: Self-RAG, CRITIC frameworks

### Writer Agent
- **Model**: `claude-3-5-sonnet`
- **Citation Registry**: Builds deduplicated `[N]` citation map
- **Section Generation**: One LLM call per report section
- **Quality Scoring**: Composite of coverage, citation density, section completeness
- **Report Structure**: Abstract → Introduction → Literature Review → Methodology → Findings → Analysis → Conclusion → References

---

## Iterative Refinement Loop

```
iteration = 1
while iteration <= max_iterations:

    evidence = researcher.retrieve(pending_subtasks)

    analysis = analyst.evaluate(evidence)
    # Returns: coverage_score, confidence_score, gaps[], additional_queries[]

    if coverage >= 0.75 AND confidence >= 0.85:
        break   # Quality threshold met

    if iteration < max_iterations:
        new_subtasks = planner.refine_plan(gaps)
        # Adds gap-filling subtasks to session

    iteration += 1

report = writer.synthesize(evidence, citations)
```

---

## Evaluation Metrics

Run via `GET /api/research/{id}/evaluate`:

| Metric | Description |
|--------|-------------|
| `factual_accuracy` | Analyst's confidence score (0–1) |
| `coverage_score` | Topic coverage across all subtasks (0–1) |
| `citation_correctness` | % of sections with ≥1 citation |
| `hallucination_rate` | `1 - confidence_score` |
| `response_completeness` | Word count relative to 2000-word baseline |
| `overall_score` | Weighted composite of all metrics |

---

## Project Structure

```
agentic-rag/
├── backend/
│   ├── agents/              # Four specialized AI agents
│   ├── core/                # Vector store, doc processor, orchestrator
│   ├── models/              # Pydantic schemas
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/           # React pages
│   │   ├── components/      # Reusable components
│   │   ├── api/             # API client
│   │   └── types/           # TypeScript interfaces
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## References

1. Asai et al., "Self-RAG: Learning to Retrieve, Generate, and Critique," ICLR 2024
2. Gou et al., "CRITIC: Large Language Models Can Self-Correct," ICLR 2024
3. Wu et al., "AutoGen: Enabling Next-Gen LLM Applications," arXiv 2023
4. Hong et al., "MetaGPT: Meta Programming for Multi-Agent Framework," ICLR 2024
5. Yao et al., "ReAct: Synergizing Reasoning and Acting," ICLR 2023
6. Lewis et al., "Retrieval-Augmented Generation for NLP Tasks," NeurIPS 2020
7. Wei et al., "Chain-of-Thought Prompting," NeurIPS 2022
