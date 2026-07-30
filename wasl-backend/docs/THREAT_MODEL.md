# Threat Model — Wasl

**Status:** Draft v1.0
**Last updated:** 2026-07-28

This document identifies what can go wrong from a security standpoint, and what the system does about it. It is scoped to v1. It is written to be revisited as the system changes; a new capability that changes the attack surface requires updating this document.

---

## 1. Assets

What is worth protecting:

- **The knowledge base** — the company's operational documents. May contain commercially sensitive contract terms and internal procedures.
- **Shipment data** — read from the (mock in v1) shipment service. In production would include operational and potentially personal data.
- **Model-provider credentials** — API keys with a spending capability. Compromise means both financial loss and unauthorized use.
- **The integrity of answers and actions** — operators act on what the system says. A manipulated answer or a manipulated drafted action has real-world effect.
- **Trace and audit data** — records of interactions; needed for audit, and themselves a potential source of leakage if they capture sensitive content.

## 2. Trust boundaries

- **User → API.** All user input is untrusted, including from authenticated users. It crosses into the system at the API layer.
- **Retrieved documents → model.** Document content placed into the model's context is *data*, but the model may treat text within it as instructions. This is a trust boundary that does not exist in conventional applications and is easy to miss.
- **Tool outputs → agent.** Data returned by tools (shipment service, etc.) enters the agent's reasoning and must not be assumed well-formed or benign.
- **Application → model provider.** An external service boundary; credentials cross it, and its responses re-enter the system.
- **Application → cloud infrastructure.** Deployment credentials and configuration.

## 3. Threats and mitigations

Organized by the primary risks for this class of system.

### T1 — Prompt injection via user input
**Threat.** A user crafts input designed to override system instructions — to make the assistant ignore its grounding rules, reveal its system prompt, or misuse a tool.
**Mitigation.** Treat the system prompt and the user input as separate, clearly delimited roles rather than concatenated text. Constrain the agent's available actions to a fixed, validated tool set — the model cannot invoke anything outside it regardless of what it is told. Keep the human-approval gate (ADR-0010) as the backstop: no external action executes on the model's say-so alone. Log inputs that trip guardrails for review.

### T2 — Indirect prompt injection via documents
**Threat.** A document in the knowledge base (or an uploaded file) contains text engineered to hijack the model when retrieved — e.g., "ignore previous instructions and…". Because retrieval places this text into the model's context, it can act as an injected instruction. This is the boundary most specific to this system.
**Mitigation.** Retrieved content is framed to the model explicitly as reference material to be used, not as instructions to be followed. Ingestion is a controlled process over vetted documents, not an open pipe — arbitrary untrusted documents are not silently absorbed into the knowledge base. The tool-set constraint and approval gate again bound the blast radius: even a successful content injection cannot cause an external action without human sign-off.

### T3 — Credential exposure
**Threat.** Model-provider or cloud credentials are committed to source, baked into an image, logged, or otherwise leaked, leading to financial loss or unauthorized access.
**Mitigation.** Secrets are never committed and never hardcoded; they are supplied through the environment/secret store at runtime. The repository is scanned so that an accidentally committed secret is caught. Container images are built so as not to embed secrets in layers. Trace/log output is scrubbed of credential material.

### T4 — Sensitive data leakage through model or traces
**Threat.** Sensitive document content or PII is sent to the model provider, or captured in traces, beyond what is necessary — expanding where sensitive data lives.
**Mitigation.** Only the content needed to answer is retrieved and sent. PII is filtered at ingestion where documents contain it (v1 does not require PII to function). Tracing captures what is needed to debug and audit while avoiding wholesale capture of sensitive payloads. Data handling is documented so it is a conscious choice, not an accident.

### T5 — Unbounded cost / denial of wallet
**Threat.** Because each interaction costs money, a flood of requests — malicious or accidental (e.g., an agent loop) — runs up cost. Under a fixed budget this is both a financial and an availability threat.
**Mitigation.** Rate limiting at the API. Explicit termination guards on agent loops so a run cannot recurse indefinitely (a real failure mode of agentic systems, noted in ADR-0001). Per-interaction cost is traced and visible (ADR-0005), so anomalies are detectable. Infrastructure is torn down when idle (ADR-0008), removing standing exposure.

### T6 — Unauthorized access
**Threat.** An unauthenticated or improperly authorized party reaches the API and queries the knowledge base or triggers investigations.
**Mitigation.** Authentication at the API layer; no unauthenticated path to the model, the documents, or the tools. Input validation on every endpoint. For v1's scope this is single-tenant; multi-tenant isolation is explicitly deferred and noted as a future requirement, not silently assumed solved.

### T7 — Malicious or malformed tool input/output
**Threat.** A tool receives crafted input, or returns malformed/malicious data that the agent then reasons over or that flows into a drafted action.
**Mitigation.** Tool inputs and outputs are validated against defined schemas. Tool outputs are treated as untrusted data (trust boundary in §2), not as trusted fact or instruction. Drafted actions derived from tool data still pass through the approval gate.

### T8 — Over-trust in system output (operational, not purely technical)
**Threat.** Operators treat the assistant's answers or assessments as authoritative and stop verifying, so a wrong-but-confident answer causes a wrong action.
**Mitigation.** Every answer carries its sources (FR-2, FR-6), so a human can check the basis rather than trust the assertion. The decline-when-no-context rule prevents confident answers with no grounding. The approval gate keeps a human in the decision. This threat is partly cultural and is called out so it is designed for, not assumed away.

## 4. Residual risk (accepted for v1)

- **Model-provider trust.** Data sent to the provider is governed by that provider's terms; v1 accepts this in exchange for not self-hosting (ADR-0004). Revisitable behind the model interface if requirements tighten.
- **Prompt-injection is mitigated, not solved.** No current technique fully eliminates injection. The design's stance is defense in depth — constrained tools plus the human-approval gate — so that injection cannot translate into unauthorized external action even if a prompt-level defense is bypassed.
- **Single-tenant scope.** v1 does not implement multi-tenant isolation; it is out of scope, not handled.

## 5. Non-threats for v1

- Autonomous external action abuse — not applicable, because the system takes no external action without human approval (ADR-0010).
- Model-training-data exfiltration — not applicable, because the system does not train or fine-tune a model in v1 (ADR-0004).
