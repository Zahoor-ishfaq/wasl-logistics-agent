# Product Requirements Document — Wasl

**Status:** Draft v1.0
**Owner:** Zahoor Ishfaq
**Last updated:** 2026-07-28

---

## 1. Problem

Logistics operations teams run on knowledge that is scattered and slow to access. Standard operating procedures, carrier contracts, customs requirements, and exception-handling rules live across PDFs, shared drives, and people's heads. When an exception occurs — a shipment stalls, a cold-chain breaks, an SLA is at risk — an operator has to manually pull the shipment's status from one system, find the relevant policy in a document, check the contract for the SLA terms, and decide what to do. This is slow, inconsistent between operators, and does not scale with volume.

The cost is concrete: delayed exception handling causes SLA breaches and penalty payments; inconsistent decisions create compliance risk; and senior staff spend time answering the same procedural questions instead of doing higher-value work.

## 2. Goal

Give operations staff a single assistant that (a) answers procedural questions from the company's own documents with traceable sources, and (b) autonomously investigates shipment exceptions by combining live shipment data with policy and contract knowledge, then proposes an action for human approval.

The system does not replace the operator. It compresses the investigation work — data lookup, policy retrieval, SLA checking, drafting — into one step and leaves the decision with a human.

## 3. Non-goals

- **Not** an autonomous system that sends external communications or modifies records without human approval. Every outbound action is drafted and held for sign-off.
- **Not** a replacement for the TMS/WMS systems of record. Wasl reads from them; it is not the source of truth.
- **Not** a general-purpose chatbot. Scope is bounded to logistics operations knowledge and the connected tools.
- **Not** a forecasting or route-optimization product. Those are separate problem domains.

## 4. Users

| User | Need | How Wasl serves it |
|---|---|---|
| Operations agent | Fast, correct answers to "what do I do when…" | RAG over SOPs and contracts, with citations |
| Operations agent | Investigate a stalled/exception shipment quickly | Agent pulls status + policy + SLA, drafts response |
| Team lead | Consistent decisions across the team | Answers grounded in one canonical document set |
| Compliance | Auditable, traceable reasoning | Every answer cites sources; every action is logged |

## 5. Scope — v1

### In scope
1. Document ingestion pipeline for the operations knowledge base (PDF, DOCX, plain text).
2. Retrieval-augmented question answering with inline source citations.
3. A multi-step agent that, given a shipment reference, retrieves its status via a tool, identifies exceptions, retrieves the governing policy and SLA, and drafts a recommended action.
4. Human-in-the-loop approval gate before any drafted action is marked as "to send."
5. REST API exposing the above.
6. A minimal web interface for querying and reviewing agent output.

### Deferred (post-v1)
- Live integration with a production TMS (v1 uses a mock shipment service with representative data).
- Multimodal document/photo intelligence (damage detection on delivery photos, field extraction from scanned notes) — designed as a pluggable module, not built in v1.
- Multi-tenant support.

## 6. Reference exception scenarios

These four scenarios are drawn from documented, recurring causes of shipment disruption in the Saudi market and are used to validate FR-3 (exception investigation) and to build the evaluation set (ADR-0006). They are illustrative test cases, not a claim to have observed them at a specific company.

**Scenario A — Customs / documentation hold.** Saudi customs clearance runs through ZATCA's FASAH platform, which requires pre-clearance digital documentation for every shipment; a mismatched HS code or an incomplete commercial invoice (missing the importer's Commercial Registration number or product description) is a common, well-documented trigger for a customs hold. The agent should identify the hold, retrieve the specific documentation requirement, and draft an internal request to the party who can supply the missing item — not a customer-facing message, since the cause is internal.

**Scenario B — Expected holiday-period closure.** Government and customs offices in Saudi Arabia and the wider Gulf slow substantially or close during religious holidays such as Eid al-Adha, and clearance, document processing, and delivery can be delayed as a direct, expected consequence. The agent must distinguish this from a genuine exception: if a delay coincides with a known closure window, the correct output is "expected delay, monitor" rather than an escalation. This scenario specifically tests whether the agent avoids false-positive escalations.

**Scenario C — Cross-border delay with unclear cause.** Land shipments crossing GCC borders can be held for extended periods — in some documented cases, several days to over a week — for reasons that are not always communicated by the border authority. Because the cause is external and not resolvable by the company, the correct agent behavior is escalation for visibility and customer communication, not an attempt to diagnose a root cause it cannot access.

**Scenario D — Upstream supplier delay.** Distinct from a carrier-side exception: a shipment is delayed because a supplier failed to deliver goods or documentation on time, not because of anything in transit. The agent must recognize this as a different category (vendor performance, not carrier performance) and route the drafted action accordingly — typically a vendor-facing follow-up rather than a customer or carrier notice.

## 7. Functional requirements

**FR-1 — Ingestion.** The system ingests documents, splits them into retrievable chunks, generates embeddings, and stores them with metadata (source filename, section, page). Re-ingesting an updated document replaces its prior chunks.

**FR-2 — Grounded answering.** Given a natural-language question, the system retrieves relevant chunks and produces an answer that cites the specific sources used. If retrieval returns nothing relevant, the system says so rather than answering from general knowledge.

**FR-3 — Exception investigation.** Given a shipment reference, the agent retrieves current status, determines whether an exception condition exists, retrieves the applicable policy and contractual SLA, and produces a structured assessment (what is wrong, what the policy requires, time to SLA breach, recommended action).

**FR-4 — Tool use.** The agent can call defined tools: shipment lookup, ETA/time calculation, and message drafting. Tool inputs and outputs are validated and logged.

**FR-5 — Human approval.** Any action with external effect (customer notice, escalation) is produced as a draft and requires explicit human approval before being marked actionable. The system never auto-sends in v1.

**FR-6 — Traceability.** Every response records which documents and tool calls produced it. This record is retrievable for audit.

## 8. Non-functional requirements

**NFR-1 — Latency.** A grounded answer returns within a few seconds under normal load. A full exception investigation (multiple tool + retrieval steps) completes within a small number of tens of seconds. These are targets for a single-user demo deployment, not production SLAs.

**NFR-2 — Cost.** The system runs within a constrained budget. LLM usage is metered and logged. Cloud infrastructure is provisioned on demand and torn down when not in use; nothing runs idle.

**NFR-3 — Security.** User-supplied input is treated as untrusted (see threat model). Secrets are never committed or hardcoded. Retrieved document content that reaches the model is treated as data, not instructions.

**NFR-4 — Evaluability.** Answer quality is measured against a fixed evaluation set with reproducible metrics, not assessed ad hoc. A change that regresses those metrics is detectable before deployment.

**NFR-5 — Reproducibility.** The full environment builds from source: application via container image, infrastructure via declarative configuration. No manual console setup is required to recreate a deployment.

## 9. Success criteria

The v1 is successful if:

1. An operator can ask a procedural question and receive a correct, cited answer without opening the source documents themselves.
2. Given a stalled shipment, the agent produces an assessment and a draft action that a human judges correct and complete on the majority of a defined test set of exception scenarios.
3. Answer quality is backed by measured evaluation scores (faithfulness, relevance, retrieval precision) committed to the repository, not by assertion.
4. The entire system can be deployed and torn down reproducibly, and the total run cost stays within budget.
5. The reasoning behind every architectural decision is documented and defensible.

## 10. Assumptions

- A representative document set is available for the knowledge base (real or realistic synthetic logistics documents).
- Shipment data can be represented by a mock service with a realistic schema; production TMS integration is a later concern.
- A single foundation-model provider is sufficient for v1; provider abstraction is desirable but not required initially.

## 11. Open questions

- Which retrieval strategy (dense-only vs. hybrid with keyword) is warranted given the document set size? To be decided empirically during Phase 1, measured against the evaluation set.
- Is a reranking step worth its latency cost at this scale? Same — decide on evidence.
- What is the right chunking granularity for procedural documents where a rule may span a section? To be tuned against retrieval-precision metrics.
