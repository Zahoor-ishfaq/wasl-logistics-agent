"""
app/rag/service.py

The RAG answer service. This is the heart of the question-answering
feature — it ties together the retriever, the prompt, and the LLM.

The critical rule it enforces (FR-2 grounding):

    If retrieval finds no relevant chunks, the LLM is NEVER called.
    The service returns a decline immediately.

This is what prevents hallucination. The model cannot invent an answer
from general knowledge because, with no context, it never gets asked.

Semantic cache (added):
    Before retrieving, we embed the question and check the semantic
    cache. If a previously-answered question is similar enough, we
    return the cached answer instantly — no retrieval, no LLM call.
    On a miss, we answer normally and store the result. Declines are
    never cached. The cache is safe against stale policy: it stores
    generated answers with citations, and is invalidated when documents
    are re-ingested. If Redis is down, the cache is a no-op.

Flow:
    answer(question)
      -> embed question
      -> cache lookup -> HIT: return cached answer
      -> retrieve citations
      -> if none: return decline               [LLM NOT called]
      -> else: build prompt, call LLM
      -> store in cache, return grounded answer
"""

from app.models.answer import Answer
from app.models.query import Question
from app.rag.prompt import SYSTEM_PROMPT, build_user_prompt
from app.rag.retriever import get_retriever
from app.services.cache import get_cache
from app.services.embeddings import get_embedding_service
from app.services.llm import get_llm_service

_DECLINE_MESSAGE = (
    "I don't have information about that in the knowledge base. "
    "I can only answer questions covered by the logistics documents "
    "I have access to."
)


class RAGService:
    """Answers questions using retrieval-augmented generation, with caching."""

    def answer(self, question: Question) -> Answer:
        """
        Answer a question from the knowledge base.

        Returns an Answer that is either grounded (answered=True, with
        citations) or a decline (answered=False). The LLM is only called
        when relevant context exists and no cached answer is found.
        """
        # 1. Embed the question once — reused for both cache and retrieval.
        query_embedding = get_embedding_service().embed_query(question.text)

        # 2. Semantic cache lookup.
        cache = get_cache()
        cached = cache.lookup(question.text, query_embedding)
        if cached is not None:
            return Answer(
                answered=cached.get("answered", True),
                text=cached.get("text", ""),
                citations=cached.get("citations", []),
            )

        # 3. Retrieve relevant chunks as citations.
        citations = get_retriever().retrieve_as_citations(
            query=question.text,
            top_k=question.top_k,
        )

        # 4. No relevant context -> decline WITHOUT calling the LLM. Not cached.
        if not citations:
            return Answer(answered=False, text=_DECLINE_MESSAGE, citations=[])

        # 5. Build the grounded prompt and call the LLM.
        user_prompt = build_user_prompt(question.text, citations)
        response_text = get_llm_service().complete(
            prompt=user_prompt,
            system=SYSTEM_PROMPT,
        )

        answer = Answer(answered=True, text=response_text, citations=citations)

        # 6. Store in the cache for future similar questions.
        cache.store(question.text, query_embedding, answer.model_dump())

        return answer

    def answer_text(self, text: str, top_k: int | None = None) -> Answer:
        """Convenience wrapper to answer from a plain string."""
        q = Question(text=text, top_k=top_k or 5)
        return self.answer(q)


_rag_service: RAGService | None = None


def get_rag_service() -> RAGService:
    """Return the shared RAGService instance."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
