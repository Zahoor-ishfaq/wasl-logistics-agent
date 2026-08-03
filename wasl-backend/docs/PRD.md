# Product Requirements Document — Wasl

**Status:** v1 implemented  
**Owner:** Zahoor Ishfaq  
**Last updated:** 2026-08-03

## 1. Purpose

Wasl is an AI-assisted logistics control tower for two recurring operational tasks:

1. answering policy and procedure questions from internal documents with source citations;
2. investigating shipment exceptions and preparing an operational recommendation for human approval.

The system is intentionally bounded. It supports operators with retrieval, reasoning, and drafting, but it does not send external communications or execute operational changes autonomously.

## 2. Problem

Shipment exceptions are often investigated across separate sources: shipment records, SOPs, customs procedures, SLA policies, and escalation rules. Operators must find the relevant information, determine which policy applies, and decide what action is required.

This creates three practical problems:

- slow exception handling;
- inconsistent decisions between operators;
- weak traceability between a recommendation and the policy that supports it.

Wasl brings those steps into one workflow.

## 3. Users

| User | Primary need |
|---|---|
| Operations user | Find the correct procedure quickly |
| Operations user | Investigate an exception and understand the next action |
| Team lead | Apply escalation rules consistently |
| Reviewer / compliance user | See the evidence behind an answer or recommendation |

## 4. v1 capabilities

### Grounded knowledge assistant

Wasl can:

- ingest `.pdf`, `.md`, and `.txt` documents;
- extract and chunk document text with metadata;
- create local sentence-transformer embeddings;
- store and retrieve vectors with PostgreSQL + pgvector;
- answer questions using retrieved evidence;
- return only model-used source citations;
- decline when the knowledge base does not provide sufficient support;
- retain bounded conversation context for follow-up questions.

### Shipment investigation

Given a shipment exception, Wasl can:

- retrieve shipment data;
- classify and assess the exception;
- evaluate ETA / SLA conditions;
- retrieve applicable policy;
- prepare a recommended action;
- draft a proposed communication;
- stop at an approval gate for a human decision.

The workflow can also determine that no action is required.

### Knowledge-base management

Authorized users can upload and remove supported documents through the application. Production document embeddings persist in PostgreSQL + pgvector.

### Security and operational controls

v1 includes:

- JWT authentication;
- API-key fallback;
- request rate limiting;
- prompt-injection checks;
- filtering of suspicious retrieved instructions;
- untrusted-content boundaries in the RAG prompt;
- human approval before consequential actions;
- application logging and AWS monitoring.

## 5. Reference exception scenarios

The project uses realistic synthetic logistics scenarios to validate behavior:

| Scenario | Expected behavior |
|---|---|
| Customs hold | Retrieve customs procedure and apply the correct escalation clock |
| High-value shipment | Apply high-value controls without transferring unrelated thresholds |
| Carrier SLA risk | Evaluate SLA policy only when applicable to the cause |
| Supplier delay | Route escalation to the appropriate origin / supplier workflow |
| Holiday or port closure | Recognize an expected delay and avoid unnecessary escalation |
| Cross-border hold | Report confirmed facts and avoid inventing an unknown cause |

## 6. Functional requirements

| ID | Requirement |
|---|---|
| FR-1 | Ingest supported operational documents and persist searchable chunks with source metadata |
| FR-2 | Produce grounded answers with citations and decline unsupported questions |
| FR-3 | Investigate shipment exceptions using shipment data, policy retrieval, and operational rules |
| FR-4 | Restrict agent actions to defined and validated tools |
| FR-5 | Require human approval before a proposed action becomes actionable |
| FR-6 | Preserve sufficient source, tool, and decision information for review |
| FR-7 | Support authenticated document upload and deletion |
| FR-8 | Expose application capabilities through REST APIs and a web interface |

## 7. Non-functional requirements

### Reliability
Unsupported questions must fail safely. A missing policy is preferable to an invented policy.

### Performance
Normal APIs should respond quickly. RAG and investigation requests may take longer because they include retrieval and external model inference. Latency is monitored through AWS metrics.

### Security
Secrets must not be committed to source control. User input, retrieved documents, and tool outputs are treated as untrusted data.

### Reproducibility
Application services are containerized. Database changes are managed with Alembic and AWS infrastructure is defined with Terraform.

### Evaluability
RAG, agent, route, security, and pgvector behavior must be covered by automated tests and regression checks.

## 8. Production architecture

The current deployment uses:

- React + Vite frontend;
- Amazon S3 + CloudFront;
- FastAPI on ECS Fargate behind an Application Load Balancer;
- Amazon RDS PostgreSQL with pgvector;
- Redis semantic cache;
- Anthropic Claude for grounded reasoning and drafting;
- CloudWatch and ECS Container Insights for operational monitoring;
- Terraform for infrastructure management;
- GitHub Actions for CI.

## 9. Out of scope

The current version does not provide:

- autonomous sending of email, SMS, or customer notifications;
- autonomous modification of external TMS / ERP systems;
- route optimization or demand forecasting;
- OCR for scanned documents;
- multi-tenant isolation;
- a production integration with a third-party transportation-management platform.

## 10. Success criteria

v1 is considered successful when:

1. supported procedural questions return useful, cited answers;
2. unsupported questions decline without fabricated policy;
3. shipment scenarios route to the correct operational workflow;
4. multi-policy questions preserve policy applicability boundaries;
5. consequential actions remain behind human approval;
6. the application can be deployed reproducibly from source;
7. automated tests and monitoring provide evidence of system behavior.

## 11. Current verification

The latest verified backend test run contains:

- **120 passing tests**
- **76% total coverage**
- **98% coverage for the RAG service**

The repository also contains a golden-set evaluation harness for RAG and agent regression testing.
