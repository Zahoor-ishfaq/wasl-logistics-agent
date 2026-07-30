"""
app/api/routes_answer.py

The /answer endpoint — grounded question answering (RAG).

Wraps the RAG service. Takes a Question, returns an Answer with
citations, or a decline if the knowledge base has nothing relevant.
"""

from fastapi import APIRouter, Depends, Request

from app.api.deps import limiter, require_api_key
from app.models.answer import Answer
from app.models.query import Question
from app.rag.service import get_rag_service

router = APIRouter(tags=["answer"])


@router.post(
    "/answer",
    response_model=Answer,
    dependencies=[Depends(require_api_key)],
    summary="Ask a grounded question",
)
@limiter.limit("30/minute")
async def answer(request: Request, question: Question) -> Answer:
    """
    Answer a question using only the knowledge base, with citations.

    Returns an Answer where:
      - answered=True  → text plus the citations it drew from
      - answered=False → a decline message, no citations (nothing relevant found)

    The `request: Request` parameter is required by the rate limiter.
    """
    return get_rag_service().answer(question)