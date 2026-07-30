# Architecture — Wasl

**Status:** Draft v1.0
**Last updated:** 2026-07-28

This document describes the system structure and the data/control flow. Rationale for specific technology choices lives in the ADRs (`docs/adr/`); this document states *what* the system is, and references the ADR for *why*.

---

## 1. Overview

Wasl is a retrieval-augmented, agentic assistant for logistics operations. It has two primary paths through the same core:

- **Answer path** — a question is answered from the document knowledge base with citations.
- **Investigation path** — a shipment reference triggers a multi-step agent that combines live shipment data (via tools) with knowledge-base retrieval to assess an exception and draft an action.

Both paths share the retrieval layer, the model layer, and the observability/evaluation instrumentation. The investigation path adds orchestration, tools, and a human-approval gate.

## 2. Component diagram

```
                          ┌──────────────────────────────┐
                          │  Web UI (chat + review panel) │
                          └───────────────┬──────────────┘
                                          │ HTTPS / REST
                          ┌───────────────▼──────────────┐
                          │        API layer (FastAPI)     │
                          │  auth · validation · routing   │
                          └───────┬───────────────┬───────┘
                                  │               │
                     answer path  │               │  investigation path
                          ┌───────▼──────┐  ┌──────▼─────────────────────┐
                          │  RAG service │  │  Agent orchestrator         │
                          │              │  │  (LangGraph state machine)  │
                          │  retrieve →  │  │                             │
                          │  ground →    │  │  ┌───────────────────────┐  │
                          │  answer      │  │  │ Retrieval node (RAG)  │  │
                          └───────┬──────┘  │  ├───────────────────────┤  │
                                  │         │  │ Tool node:            │  │
                                  │         │  │  shipment_lookup      │  │
                                  │         │  │  compute_eta          │  │
                                  │         │  │  draft_message        │  │
                                  │         │  ├───────────────────────┤  │
                                  │         │  │ Assessment node       │  │
                                  │         │  ├───────────────────────┤  │
                                  │         │  │ Approval gate (HITL)  │  │
                                  │         │  └───────────────────────┘  │
                                  │         └──────┬──────────────────────┘
                                  │                │
                    ┌─────────────▼────────────────▼─────────────┐
                    │              Shared services                 │
                    │                                              │
                    │  Embedding + Vector store (Chroma/pgvector)  │
                    │  Foundation model client (LLM API)           │
                    │  Mock shipment service (stands in for TMS)   │
                    │  Observability (tracing) · Eval harness      │
                    └──────────────────────────────────────────────┘
```

## 3. Components

### 3.1 API layer (FastAPI)
Single entry point. Responsibilities: request validation, authentication, input sanitization (see threat model), routing to the answer or investigation path, and response shaping. Holds no business logic beyond routing; keeps the model/agent layers testable in isolation.

### 3.2 Ingestion pipeline
Offline/triggered process, not on the request path. Loads source documents, splits them into chunks with source metadata, embeds them, and writes to the vector store. Idempotent per document: re-ingesting replaces prior chunks for that source. Chunking strategy and granularity are tuned against retrieval metrics (ADR-0003).

### 3.3 RAG service (answer path)
Given a question: embed the query, retrieve top-k chunks, assemble a grounded prompt, call the model, and return the answer with the citations of the chunks actually used. Enforces the "no relevant context → decline" rule (FR-2) rather than allowing unсited answers.

### 3.4 Agent orchestrator (investigation path)
A state machine (LangGraph, ADR-0002) coordinating discrete nodes:

- **Retrieval node** — pulls relevant policy/contract chunks (reuses the RAG service).
- **Tool node** — calls defined tools (`shipment_lookup`, `compute_eta`, `draft_message`). Tool schemas and outputs are validated.
- **Assessment node** — reasons over the gathered status + policy + SLA to produce a structured assessment.
- **Approval gate** — a human-in-the-loop interrupt. Any action with external effect stops here for explicit approval before it is marked actionable.

State (what has been gathered, which steps have run) is explicit and inspectable. Routing between nodes is conditional (e.g., exception present → draft action; no exception → summarize and stop).

### 3.5 Shared services

- **Vector store** — Chroma locally, pgvector when a Postgres instance is present (ADR-0003). Same interface either way.
- **Foundation model client** — thin wrapper over the LLM API, isolating provider specifics behind one interface so the provider can change without touching agent logic (ADR-0004).
- **Mock shipment service** — an in-repo service exposing a realistic shipment schema and representative data, standing in for a production TMS. Deliberately behind the same interface a real integration would use, so it can be swapped later without changing the agent.
- **Observability** — request and agent-step tracing (ADR-0005), capturing tool calls, retrieved sources, latency, and token/cost per interaction.
- **Evaluation harness** — offline; runs the answer path against a fixed question/ground-truth set and reports faithfulness, answer relevance, and context precision (ADR-0006).

## 4. Control flow — answer path

1. Request arrives at the API, is validated and authenticated.
2. Query is embedded; top-k relevant chunks are retrieved.
3. If nothing relevant is retrieved, return a decline response.
4. Otherwise assemble the grounded prompt and call the model.
5. Return the answer with citations; emit a trace with sources, latency, and cost.

## 5. Control flow — investigation path

1. Request with a shipment reference arrives; validated and authenticated.
2. Orchestrator initializes state.
3. Tool node calls `shipment_lookup`; status is written to state.
4. Assessment logic determines whether an exception condition holds.
5. If an exception holds: retrieval node pulls the governing policy and SLA; `compute_eta` establishes time-to-breach; assessment node produces the structured assessment; `draft_message` produces the proposed action.
6. Control reaches the approval gate and **stops**. The draft is surfaced to a human.
7. On human approval, the action is marked actionable. On rejection, it is discarded with the reason logged.
8. The full path — every tool call, every retrieved source — is traced.

## 6. Deployment view

- Application is packaged as a container image (ADR-0007).
- Infrastructure is declared as code and provisioned on demand; the deployment is torn down when idle to control cost (ADR-0008, and NFR-2).
- Build, test, and image publication run through a CI pipeline (ADR-0009).

Target footprint is deliberately small: a single small compute target for the API/agent, the vector store either co-located or on a small managed instance, and object storage for documents. The design does not assume a cluster; it can run on one modest instance and scale later if warranted.

## 7. Data

- **Documents** — source of the knowledge base; stored in object storage, chunked into the vector store.
- **Shipment data** — read-only from the (mock) shipment service; never persisted as source of truth.
- **Traces / eval results** — operational data; retained for audit and quality tracking.

No customer PII is required for v1. If real documents contain PII, it is filtered at ingestion (see threat model).

## 8. Explicitly out of the v1 architecture

- No fine-tuned models. v1 uses foundation models via API; fine-tuning is a later, evidence-driven decision (it is not required to meet the success criteria).
- No GPU-dependent components on the request path.
- No live TMS integration.
- The multimodal (vision) module is designed as a pluggable tool behind the same tool interface, but is not part of the v1 build.
