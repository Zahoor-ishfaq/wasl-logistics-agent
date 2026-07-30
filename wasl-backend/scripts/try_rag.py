"""
scripts/try_rag.py

A smoke test for the RAG pipeline. Run it to confirm the whole
question-answering flow works end to end:

    retriever → prompt → LLM → grounded answer with citations

    python scripts/try_rag.py

It asks a few real logistics questions (that the knowledge base CAN
answer) and one question it CANNOT answer, so you can see both:
  - a grounded answer with citations, and
  - a clean decline with no hallucination.

Requires:
  - documents already ingested (run scripts/ingest.py first)
  - ANTHROPIC_API_KEY set in .env
"""

import sys
from pathlib import Path

# Make the project root importable when run directly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.rag.service import get_rag_service  # noqa: E402

# Questions the knowledge base SHOULD be able to answer.
ANSWERABLE = [
    "What documents are required to import goods into Saudi Arabia?",
    "How many hours before arrival must the customs declaration be submitted?",
    "What is the re-delivery policy after a failed delivery attempt?",
    "Does a delay caused by Eid count as an SLA breach?",
]

# A question the knowledge base should NOT be able to answer —
# expect a clean decline, not a made-up answer.
UNANSWERABLE = "What is the capital city of Australia?"


def print_answer(question: str, answer) -> None:
    print("=" * 70)
    print(f"Q: {question}")
    print("-" * 70)
    print(f"answered: {answer.answered}")
    print()
    print(answer.text)
    if answer.citations:
        print()
        print("Citations:")
        for c in answer.citations:
            section = f" — {c.section}" if c.section else ""
            print(f"  [{c.similarity_score:.2f}] {c.source}{section}")
    print()


def main() -> None:
    service = get_rag_service()

    print("\nTesting questions the knowledge base SHOULD answer:\n")
    for q in ANSWERABLE:
        answer = service.answer_text(q)
        print_answer(q, answer)

    print("\nTesting a question the knowledge base should DECLINE:\n")
    answer = service.answer_text(UNANSWERABLE)
    print_answer(UNANSWERABLE, answer)

    print("Done. Check that:")
    print("  - the answerable questions returned grounded answers with citations")
    print("  - the unanswerable question returned answered=False and NO citations")


if __name__ == "__main__":
    main()
