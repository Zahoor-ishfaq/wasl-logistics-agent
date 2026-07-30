"""
app/rag/service.py

The RAG answer service. This is the heart of the question-answering
feature — it ties together the retriever, the prompt, and the LLM.

The critical rule it enforces (FR-2 grounding):

    If retrieval finds no relevant chunks, the LLM is NEVER called.
    The service returns a decline immediately.

This is what prevents hallucination. The model cannot invent an answer
from general knowledge because, with no context, it never gets asked.

Flow:
    answer(question)
      → retrieve citations
      → if none: return Answer(answered=False, ...)   [LLM NOT called]
      → else:    build prompt, call LLM, return Answer(answered=True, citations=...)
"""

from app.models.answer import Answer
from app.models.query import Question
from app.rag.prompt import SYSTEM_PROMPT, build_user_prompt
from app.rag.retriever import get_retriever
from app.services.llm import get_llm_service

# The message returned when the knowledge base has no relevant content.
_DECLINE_MESSAGE = (
    "I don't have information about that in the knowledge base. "
    "I can only answer questions covered by the logistics documents "
    "I have access to."
)


class RAGService:
    """Answers questions using retrieval-augmented generation."""

    def answer(self, question: Question) -> Answer:
        """
        Answer a question from the knowledge base.

        Args:
            question: The validated Question (text + top_k).

        Returns:
            Answer. Either:
              - answered=True  with text and citations, or
              - answered=False with a decline message and no citations.

        The LLM is only called when relevant context exists.
        """
        retriever = get_retriever()

        # 1. Retrieve relevant chunks as citations.
        citations = retriever.retrieve_as_citations(
            query=question.text,
            top_k=question.top_k,
        )

        # 2. No relevant context → decline WITHOUT calling the LLM.
        if not citations:
            return Answer(
                answered=False,
                text=_DECLINE_MESSAGE,
                citations=[],
            )

        # 3. Build the grounded prompt and call the LLM.
        user_prompt = build_user_prompt(question.text, citations)
        response_text = get_llm_service().complete(
            prompt=user_prompt,
            system=SYSTEM_PROMPT,
        )

        # 4. Return the grounded answer with its supporting citations.
        return Answer(
            answered=True,
            text=response_text,
            citations=citations,
        )

    def answer_text(self, text: str, top_k: int | None = None) -> Answer:
        """
        Convenience wrapper to answer from a plain string.

        Builds a Question for you — handy in scripts and tests.
        """
        q = Question(text=text, top_k=top_k or 5)
        return self.answer(q)


_rag_service: RAGService | None = None


def get_rag_service() -> RAGService:
    """Return the shared RAGService instance."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
