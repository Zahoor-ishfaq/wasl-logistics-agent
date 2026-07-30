"""
eval/run_eval.py

Runs the golden test set and scores the system. Three kinds of case:

  rag     — ask the RAG service; score with RAGAS (faithfulness,
            answer relevancy, context precision) plus a keyword check
  decline — ask an out-of-scope question; the system MUST decline
            (answered=False). Scored as pass/fail.
  agent   — run the agent on a shipment; check it detected the right
            exception, took (or correctly withheld) action, and routed
            to the right recipient. Scored as pass/fail.

Writes results to eval/results/latest.json.

    python eval/run_eval.py

Requires ANTHROPIC_API_KEY (RAG + agent make real calls) and an
ingested knowledge base. RAGAS itself uses an LLM judge — by default
this uses the same Anthropic model via langchain, so no OpenAI key is
needed.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings  # noqa: E402
from app.rag.service import get_rag_service  # noqa: E402
from app.rag.retriever import get_retriever  # noqa: E402

GOLDEN = Path(__file__).resolve().parent / "golden_set.jsonl"
RESULTS_DIR = Path(__file__).resolve().parent / "results"


def load_cases() -> list[dict]:
    cases = []
    with open(GOLDEN, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


# ---------------------------------------------------------------------------
# Keyword coverage — a cheap, deterministic signal alongside RAGAS.
# ---------------------------------------------------------------------------
def keyword_coverage(answer_text: str, expected_points: list[str]) -> float:
    """Fraction of expected points that appear in the answer (case-insensitive)."""
    if not expected_points:
        return 1.0
    text = answer_text.lower()
    hits = sum(1 for p in expected_points if p.lower() in text)
    return hits / len(expected_points)


# ---------------------------------------------------------------------------
# RAGAS scoring (optional — degrades gracefully if not installed)
# ---------------------------------------------------------------------------
def score_with_ragas(samples: list[dict]) -> dict | None:
    """
    Score RAG samples with RAGAS. Returns average metrics, or None if
    RAGAS isn't available (so the harness still runs without it).

    Each sample: {question, answer, contexts: list[str]}
    """
    try:
        from ragas import evaluate
        from ragas.dataset_schema import EvaluationDataset, SingleTurnSample
        from ragas.metrics import Faithfulness, ResponseRelevancy, LLMContextPrecisionWithoutReference
        from ragas.llms import LangchainLLMWrapper
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from langchain_anthropic import ChatAnthropic
        from langchain_community.embeddings import HuggingFaceEmbeddings
    except ImportError as exc:
        print(f"[eval] RAGAS not available ({exc}); skipping RAGAS metrics.")
        return None

    judge = LangchainLLMWrapper(ChatAnthropic(
        model=settings.anthropic_model,
        api_key=settings.anthropic_api_key,
        temperature=0.0,
        max_tokens=1024,
    ))
    embed = LangchainEmbeddingsWrapper(
        HuggingFaceEmbeddings(model_name=settings.embedding_model)
    )

    ds = EvaluationDataset(samples=[
        SingleTurnSample(
            user_input=s["question"],
            response=s["answer"],
            retrieved_contexts=s["contexts"],
        ) for s in samples
    ])

    metrics = [
        Faithfulness(llm=judge),
        ResponseRelevancy(llm=judge, embeddings=embed),
        LLMContextPrecisionWithoutReference(llm=judge),
    ]
    result = evaluate(dataset=ds, metrics=metrics)
    df = result.to_pandas()

    def avg(col):
        return float(df[col].mean()) if col in df else None

    return {
        "faithfulness": avg("faithfulness"),
        "answer_relevancy": avg("answer_relevancy"),
        "context_precision": avg("llm_context_precision_without_reference"),
    }


# ---------------------------------------------------------------------------
# Case runners
# ---------------------------------------------------------------------------
def run_rag_case(case: dict) -> dict:
    rag = get_rag_service()
    retriever = get_retriever()
    ans = rag.answer_text(case["question"])
    contexts = [c.text for c in retriever.retrieve(case["question"])]

    coverage = keyword_coverage(ans.text, case.get("expected_points", []))
    got_sources = {c.source for c in ans.citations}
    want_sources = set(case.get("expected_sources", []))
    source_hit = bool(want_sources & got_sources) if want_sources else True

    return {
        "id": case["id"], "type": "rag", "answered": ans.answered,
        "keyword_coverage": round(coverage, 3),
        "source_hit": source_hit,
        "passed": ans.answered and coverage >= 0.5 and source_hit,
        "_ragas_sample": {"question": case["question"], "answer": ans.text, "contexts": contexts},
    }


def run_decline_case(case: dict) -> dict:
    ans = get_rag_service().answer_text(case["question"])
    # Must decline: answered == False.
    return {
        "id": case["id"], "type": "decline",
        "answered": ans.answered,
        "passed": ans.answered is False,
    }


def run_agent_case(case: dict) -> dict:
    from app.agent.graph import build_graph
    from app.models.state import AgentState

    graph = build_graph()
    cfg = {"configurable": {"thread_id": f"eval-{case['id']}"}}
    graph.invoke(AgentState(shipment_id=case["shipment_id"]), cfg)
    values = graph.get_state(cfg).values

    draft = values.get("drafted_action")
    took_action = draft is not None
    recipient = draft.recipient_type if draft else None
    exception = str(values.get("exception_type", "none"))
    if "." in exception:
        exception = exception.split(".")[-1]

    action_ok = took_action == case["expected_action"]
    recipient_ok = (recipient == case["expected_recipient"]) if case["expected_action"] else True

    return {
        "id": case["id"], "type": "agent",
        "detected_exception": exception,
        "took_action": took_action,
        "recipient": recipient,
        "action_ok": action_ok,
        "recipient_ok": recipient_ok,
        "passed": action_ok and recipient_ok,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    cases = load_cases()
    print(f"Running {len(cases)} evaluation cases...\n")

    results = []
    ragas_samples = []

    for case in cases:
        t = case["type"]
        if t == "rag":
            r = run_rag_case(case)
            ragas_samples.append(r.pop("_ragas_sample"))
        elif t == "decline":
            r = run_decline_case(case)
        elif t == "agent":
            r = run_agent_case(case)
        else:
            continue
        results.append(r)
        mark = "PASS" if r["passed"] else "FAIL"
        print(f"  [{mark}] {r['id']} ({t})")

    # RAGAS on the collected RAG samples.
    print("\nScoring RAG answers with RAGAS (LLM judge)...")
    ragas_scores = score_with_ragas(ragas_samples)

    # Aggregate.
    by_type = {}
    for t in ("rag", "decline", "agent"):
        subset = [r for r in results if r["type"] == t]
        if subset:
            by_type[t] = {
                "total": len(subset),
                "passed": sum(1 for r in subset if r["passed"]),
                "pass_rate": round(sum(1 for r in subset if r["passed"]) / len(subset), 3),
            }

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": settings.anthropic_model,
        "total_cases": len(results),
        "total_passed": sum(1 for r in results if r["passed"]),
        "overall_pass_rate": round(sum(1 for r in results if r["passed"]) / len(results), 3),
        "by_type": by_type,
        "ragas": ragas_scores,
        "cases": results,
    }

    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / "latest.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n" + "=" * 56)
    print("EVALUATION SUMMARY")
    print("=" * 56)
    print(f"Overall: {summary['total_passed']}/{summary['total_cases']} "
          f"({summary['overall_pass_rate'] * 100:.0f}%)")
    for t, s in by_type.items():
        print(f"  {t:8s}: {s['passed']}/{s['total']} ({s['pass_rate'] * 100:.0f}%)")
    if ragas_scores:
        print("\nRAGAS (RAG answers):")
        for k, v in ragas_scores.items():
            if v is not None:
                print(f"  {k:20s}: {v:.3f}")
    print(f"\nResults written to {out}")


if __name__ == "__main__":
    main()