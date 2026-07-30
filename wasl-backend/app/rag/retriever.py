"""
app/rag/retriever.py

The retriever finds the document chunks most relevant to a question.

It's a thin layer over the vector store. Why have it at all, rather
than calling the vector store directly from the RAG service?

  - It's the single place retrieval behavior lives. If we later add
    re-ranking, query expansion, or hybrid search, it changes here
    and nowhere else.
  - It converts vector-store RetrievedChunk objects into Citation
    objects (the shape the rest of the app and the API speak in).

The retriever does NOT call the LLM. It only fetches context.
"""

from app.config import settings
from app.models.answer import Citation
from app.services.vector_store import RetrievedChunk, get_vector_store


class Retriever:
    """Finds and returns the most relevant chunks for a query."""

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        min_score: float | None = None,
        source_filter: str | None = None,
    ) -> list[RetrievedChunk]:
        """
        Return the raw retrieved chunks for a query.

        Args:
            query:         The question or search text.
            top_k:         How many chunks to return. Defaults to settings.
            min_score:     Drop chunks below this similarity. Defaults to settings.
            source_filter: Restrict search to a single source file
                           (used by the policy_search tool).

        Returns:
            A list of RetrievedChunk, highest similarity first,
            already filtered by min_score.
        """
        store = get_vector_store()
        return store.search(
            query=query,
            top_k=top_k or settings.retrieval_top_k,
            min_score=min_score,
            source_filter=source_filter,
        )

    def retrieve_as_citations(
        self,
        query: str,
        top_k: int | None = None,
        min_score: float | None = None,
    ) -> list[Citation]:
        """
        Retrieve chunks and convert them to Citation objects.

        Citations are the shape used in Answer responses and the API,
        so this is what the RAG service consumes.

        The snippet is truncated to 500 characters to match the
        Citation schema's max_length.
        """
        chunks = self.retrieve(query, top_k=top_k, min_score=min_score)
        return [
            Citation(
                source=chunk.source,
                section=chunk.section,
                snippet=chunk.text[:500],
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