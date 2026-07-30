# Wasl — Agentic Logistics Control Tower

> **وصل** (*wasl*) — Arabic for "connection / delivery."

An AI system for logistics operations that does two things:

1. **Answers procedural questions** from company documents, with citations, and declines when the answer isn't in the knowledge base (grounded RAG).
2. **Investigates shipment exceptions autonomously** — looks up the shipment, assesses the exception against policy, calculates the SLA position, drafts a corrective action, and **holds it for human approval.** It never sends anything on its own.

<!-- Replace with your demo GIF: record a customs-hold investigation, then the Eid no-action case -->
![Wasl demo](docs/demo.gif)

---

## Why this exists

Commercial "control tower" platforms — project44, FourKites, Blue Yonder — dominate logistics visibility and planning. The newest frontier is the **agentic execution layer**: systems that don't just show a late shipment but investigate it and propose the fix. FourKites' Intelligent Control Tower and Locus are building exactly this.

**Wasl is a focused, open demonstration of that agentic-execution layer**, scoped to Saudi import/customs logistics. It's not trying to replace an enterprise platform; it's a working demonstration of the reasoning-and-human-approval loop that defines the category's leading edge — built end to end, from retrieval to agent to API to UI.

---

## What it does — the two flows

### Ask (grounded RAG)
Ask a logistics question; get an answer drawn **only** from the knowledge base, with the source documents cited. If nothing relevant is retrieved, the LLM is never called and the system declines — so it can't hallucinate a policy that doesn't exist.

### Investigate (the agent)
Point it at a shipment exception. The agent runs a multi-step investigation and either drafts an action for approval or correctly stands down:

| Scenario | Agent behavior |
|---|---|
| Customs hold (missing SASO cert) | Escalates internally to Compliance — drafts action, awaits approval |
| Cross-border hold (unknown cause) | Drafts customer notice, honest that cause is unconfirmed |
| Supplier delay | Drafts vendor notice demanding a revised dispatch date |
| **Holiday closure (Eid)** | **Takes NO action** — recognizes an expected delay that doesn't breach SLA |

That last row is the point: an agent that escalates *everything* is useless. Wasl knows when **not** to act.

---

## Architecture

![Architecture](docs/architecture.svg)

```
React UI (Vite)  ──HTTP──▶  FastAPI  ──▶  RAG service  ──▶  Chroma (vector store)
                              │                              ▲
                              │                              │ sentence-transformers
                              ▼                              │ (local, free)
                        LangGraph agent  ──▶  Tools ─────────┘
                              │              (lookup, compute_eta,
                              │               policy_search, draft_message)
                              ▼
                        Claude (Anthropic)
```

**The agent is a LangGraph state machine** with a conditional branch (is there an actionable exception?) and a human-in-the-loop interrupt before the approval gate. The graph defines the possible paths; the LLM makes judgment calls at two nodes. It's deliberately a *single agentic workflow*, not a multi-agent system — scoped to the problem, not over-engineered.

---

## Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| LLM | Claude (via `langchain-anthropic`) |
| Agent | LangGraph (tools + conditional branching + human-in-the-loop) |
| Retrieval | LangChain + Chroma + sentence-transformers (`all-MiniLM-L6-v2`, local) |
| API | FastAPI + slowapi (rate limiting) |
| Frontend | React + Vite |
| Evaluation | RAGAS + a custom golden-set harness |

Embeddings run locally (free); only the Claude calls cost money — cents per investigation.

---

## Evaluation

Quality is measured, not assumed. A 26-case golden set covers RAG answers, out-of-scope declines, and agent routing, scored by a runner with a regression gate that fails CI if quality drops more than 5%.

| Suite | Result |
|---|---|
| Agent routing (all 4 scenarios + not-found + no-exception) | **6/6 (100%)** |
| Out-of-scope declines | 2/3 |
| RAG answers | 12/17 |
| **Overall** | **20/26 (77%)** |

*The agent — the hard part — routes every scenario correctly. The RAG suite uses a deliberately strict keyword matcher; several "misses" are correct answers phrased differently, and RAGAS scoring (faithfulness / answer relevancy / context precision) is being wired in as the primary signal.*

```bash
python eval/run_eval.py       # run all cases, write results
python eval/compare.py        # compare to baseline; non-zero exit on regression
```

---

## Running locally

### Prerequisites
- Python 3.11+
- Node.js 20+
- An Anthropic API key

### Backend

```bash
cd wasl
python -m venv .venv
.venv\Scripts\activate            # Windows;  source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt

copy .env.example .env            # then edit: set ANTHROPIC_API_KEY and API_KEY

python scripts/ingest.py          # build the knowledge base (~69 chunks)
uvicorn app.main:app --reload     # API on http://localhost:8000  (docs at /docs)
```

### Frontend

```bash
cd wasl-ui
npm install
copy .env.example .env            # set VITE_API_KEY to the SAME value as backend API_KEY
npm run dev                       # UI on http://localhost:5173
```

Open **http://localhost:5173**, pick a shipment, and watch the agent investigate.

---

## Project layout

```
wasl/                     backend
  app/
    config.py             settings (Pydantic, from .env)
    models/               Pydantic schemas (shipment, state, answer, ...)
    rag/                  retriever, prompt, grounded answer service
    tools/                agent tools (lookup, compute_eta, policy_search, draft_message)
    agent/                LangGraph nodes + graph
    api/                  FastAPI routes, auth, middleware
  data/documents/         the knowledge base (6 markdown policies)
  scripts/                ingest, try_rag, try_agent
  eval/                   golden set, runner, regression gate
wasl-ui/                  React + Vite frontend
```

---

## Design decisions

A few choices worth calling out (full write-up in [`docs/decisions.md`](docs/decisions.md)):

- **Single agentic workflow, not multi-agent.** The problem is one investigation with branching, not several collaborating agents. Scoping honestly beats over-engineering.
- **Human-in-the-loop by construction.** The `draft_message` tool has no send capability, and the graph physically interrupts before the approval gate. Safety is structural, not a policy note.
- **Grounding guarantee.** No retrieved context → the LLM is never invoked → the system declines. Hallucination is prevented by control flow, not by asking the model nicely.
- **Local embeddings.** `all-MiniLM-L6-v2` runs on CPU for free, keeping the whole thing near-zero-cost to operate.

---

## Status & roadmap

Built and working: knowledge base, RAG, agent (all scenarios verified), API, React UI, evaluation harness.

Planned: observability (Langfuse), a semantic answer cache, a pytest suite, Docker + CI/CD, and Terraform for an AWS deployment.

---