"""
app/rag/retriever.py

Retrieval layer for Wasl RAG.

This module retrieves the most relevant knowledge-base chunks and
converts them into Citation objects used by the RAG service.

The retriever does not call the LLM.
"""

from app.config import settings
from app.models.answer import Citation
from app.services.vector_store import RetrievedChunk, get_vector_store


class Retriever:
    """Find the document chunks most relevant to a query."""

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        min_score: float | None = None,
        source_filter: str | None = None,
    ) -> list[RetrievedChunk]:
        """
        Retrieve relevant raw chunks.

        Args:
            query:
                Search query.

            top_k:
                Maximum number of chunks to return.

            min_score:
                Minimum similarity score.

            source_filter:
                Optionally restrict retrieval to one source document.
        """

        store = get_vector_store()

        return store.search(
            query=query,
            top_k=top_k or settings.retrieval_top_k,
            min_score=(
                settings.retrieval_min_score
                if min_score is None
                else min_score
            ),
            source_filter=source_filter,
        )

    def retrieve_as_citations(
        self,
        query: str,
        top_k: int | None = None,
        min_score: float | None = None,
    ) -> list[Citation]:
        """
        Retrieve relevant chunks and preserve their full text.

        Previously this method used:

            chunk.text[:500]

        That could remove important instructions located later in a
        retrieved chunk before the LLM ever received them.
        """

        chunks = self.retrieve(
            query=query,
            top_k=top_k,
            min_score=min_score,
        )

        return [
            Citation(
                source=chunk.source,
                section=chunk.section,
                snippet=chunk.text,
                similarity_score=chunk.similarity_score,
            )
            for chunk in chunks
        ]


_retriever: Retriever | None = None


def get_retriever() -> Retriever:
    """Return the shared Retriever instance."""

    global _retriever

    if _retriever is None:
        _retriever = Retriever()

    return _retriever