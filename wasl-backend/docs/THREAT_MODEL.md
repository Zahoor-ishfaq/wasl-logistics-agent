# Threat Model — Wasl

**Status:** v1  
**Last updated:** 2026-08-03

## 1. Scope

This document describes the main security risks in Wasl and the controls currently used to reduce them.

Wasl combines authenticated APIs, a document knowledge base, retrieval-augmented generation, an LLM, and an approval-gated investigation workflow. The main security objective is therefore not only protecting infrastructure and credentials, but also protecting the integrity of the information presented to an operator.

## 2. Assets

The system protects:

- operational policy and procedure documents;
- shipment and investigation data;
- application and cloud credentials;
- authentication secrets;
- the integrity of grounded answers and recommendations;
- logs, traces, and audit information;
- model-provider spending capacity.

## 3. Trust boundaries

### User → API
Authenticated input is still untrusted. Users may submit malformed data or adversarial prompts.

### Uploaded / retrieved document → RAG context
Knowledge-base content is reference data, not executable instruction. Retrieved text may contain malicious or misleading instructions.

### Tool output → investigation workflow
Shipment and tool data must be validated before it influences a recommendation.

### Application → external model provider
Only the context required for the model request should cross this boundary. Credentials must remain server-side.

### Application → AWS services
IAM permissions, Secrets Manager values, database credentials, logs, and deployment configuration must be controlled independently of application code.

## 4. Threats and controls

| Threat | Risk | Current controls |
|---|---|---|
| Direct prompt injection | User attempts to override grounding or reveal internal instructions | deterministic injection checks, system/user separation, constrained behavior, no direct external-action capability |
| Indirect prompt injection | Retrieved document contains instructions intended to control the model | suspicious-content filtering, retrieved sources explicitly treated as untrusted reference data |
| Unsupported / hallucinated policy | Model invents a procedure that is not present in evidence | retrieval threshold, grounded prompt, citation filtering, controlled decline when evidence is insufficient |
| Policy misapplication | A valid rule is applied to the wrong incident type | facet-aware retrieval, source-applicability instructions, multi-policy separation |
| Credential exposure | API keys, JWT secrets, or database credentials leak | `.gitignore`, environment-based configuration, AWS Secrets Manager for runtime secrets, no credentials in frontend code |
| Unauthorized access | Unauthenticated user reaches operational APIs | JWT authentication, API-key fallback for controlled compatibility, endpoint validation |
| Denial of wallet / request abuse | Excessive requests consume model or cloud budget | API rate limiting, bounded agent workflow, semantic cache |
| Malicious tool data | Tool output contains malformed or adversarial content | defined tool interfaces, schema validation, tool output treated as data |
| Sensitive logging | Secrets or unnecessary sensitive payloads appear in logs | secrets remain outside application output; operational logging is separated from secret storage |
| Over-trust in AI output | Operator treats a model recommendation as authoritative | citations, explicit evidence, structured investigation output, human approval boundary |

## 5. Human-in-the-loop boundary

The investigation workflow may prepare a recommendation or draft communication, but it does not send the communication itself.

The approval boundary is a structural control:

```text
Agent reasoning
    -> proposed action
    -> human review
    -> approve / reject
```

Approval records the operator's decision. External delivery remains outside the current system.

This limits the impact of incorrect reasoning, prompt injection, or malformed retrieved content.

## 6. RAG-specific controls

Wasl applies several controls before and after the model call:

1. direct injection-style requests can be handled locally without retrieval or model invocation;
2. retrieved chunks are checked for suspicious instructions;
3. prompt instructions state that retrieved content is evidence, not commands;
4. compound questions are separated by policy applicability;
5. only sources actually used in the generated answer are returned as citations;
6. insufficient evidence produces a decline instead of an unsupported answer;
7. conversation history is bounded and is not treated as policy evidence.

These controls reduce prompt-level risk but do not eliminate it.

## 7. Infrastructure controls

Current deployment controls include:

- application containers on ECS Fargate;
- private application secrets supplied at runtime;
- PostgreSQL credentials managed through AWS secret integration;
- S3 frontend access restricted through CloudFront;
- CloudWatch application logs;
- ECS Container Insights;
- Terraform-managed infrastructure;
- CI linting, migrations, tests, and coverage checks.

## 8. Residual risk

### Prompt injection is not fully solved
Detection and prompt boundaries are defense-in-depth controls, not a guarantee. The approval gate limits operational impact if a model-level control fails.

### External model-provider trust
Grounded context is sent to an external LLM provider. A production deployment with stricter data requirements would need provider-specific governance or a different model-hosting strategy.

### Single-tenant design
The current application does not implement tenant-level data isolation.

### No external-system write integration
This reduces current risk, but adding TMS, ERP, email, or messaging write capabilities would materially expand the threat model and require new authorization and approval controls.

## 9. Security assumptions

The current threat model assumes:

- repository secrets remain excluded from source control;
- AWS IAM and account access are administered securely;
- knowledge-base upload access is restricted to trusted authenticated users;
- operators review proposed actions before acting on them;
- production integrations that can modify external systems are not enabled.

Any change to these assumptions should trigger a review of this document.
