"""
app/services/vector_store.py

A thin wrapper around a persistent Chroma vector store.

Responsibilities:
  - add()     : store document chunks with their embeddings + metadata
  - search()  : find the most similar chunks to a query
  - delete_by_source() : remove all chunks from one source file (idempotent re-ingest)
  - count()   : how many chunks are stored
  - reset()   : wipe the collection (used in tests)

Why a wrapper?
  Chroma's client API is low-level and its return shape is awkward
  (parallel lists). This wrapper hides that and returns clean
  RetrievedChunk objects. If we ever switch to pgvector (see ADR-0003),
  only this file changes.

Embeddings are computed by the EmbeddingService, NOT by Chroma's
built-in embedding function — this keeps the embedding model under
our control and consistent between ingestion and retrieval.
"""

from functools import lru_cache

from pydantic import BaseModel, Field

from app.config import settings
from app.services.embeddings import get_embedding_service


class RetrievedChunk(BaseModel):
    """
    One chunk returned from a similarity search.

    similarity_score is normalized to 0..1 where 1.0 means identical.
    Chroma returns a distance (lower = closer); we convert it to a
    similarity so the rest of the app reasons in one consistent way.
    """

    text: str = Field(..., description="The chunk text.")
    source: str = Field(..., description="Source filename.")
    section: str = Field(default="", description="Section heading if available.")
    page: int = Field(default=0, description="Page number if available.")
    similarity_score: float = Field(..., ge=0.0, le=1.0)


class VectorStore:
    """
    Persistent Chroma collection wrapper.

    The collection is stored on disk at settings.chroma_persist_directory,
    so ingested data survives across restarts. Embeddings are supplied
    by us (via EmbeddingService), not computed by Chroma.
    """

    def __init__(self) -> None:
        self._client = None
        self._collection = None

    def _get_collection(self):
        """
        Lazily create the Chroma client and collection on first use.

        Imported inside the method because importing chromadb is
        relatively heavy; deferring keeps module import cheap.
        """
        if self._collection is None:
            import chromadb

            self._client = chromadb.PersistentClient(
                path=settings.chroma_persist_directory,
            )
            # get_or_create so first run creates it, later runs reuse it.
            # We pass no embedding_function — we always supply our own vectors.
            self._collection = self._client.get_or_create_collection(
                name=settings.chroma_collection_name,
                metadata={"hnsw:space": "cosine"},  # cosine distance
            )
        return self._collection

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def add(
        self,
        ids: list[str],
        texts: list[str],
        metadatas: list[dict],
    ) -> None:
        """
        Add chunks to the store.

        Args:
            ids:       Unique id per chunk (e.g. "customs_procedure.md::chunk_3").
            texts:     The chunk texts.
            metadatas: One dict per chunk. Expected keys: source, section, page.

        Embeddings are computed here via the EmbeddingService so callers
        never deal with vectors directly.
        """
        if not ids:
            return
        embeddings = get_embedding_service().embed_texts(texts)
        collection = self._get_collection()
        collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------
    def search(
        self,
        query: str,
        top_k: int | None = None,
        min_score: float | None = None,
        source_filter: str | None = None,
    ) -> list[RetrievedChunk]:
        """
        Return the most similar chunks to a query.

        Args:
            query:        The text to search for.
            top_k:        How many chunks to return. Defaults to settings.retrieval_top_k.
            min_score:    Drop chunks below this similarity. Defaults to settings.retrieval_min_score.
            source_filter: If set, only search within this source filename
                           (used by the policy_search tool to bias toward policy docs).

        Returns:
            A list of RetrievedChunk, highest similarity first, already
            filtered by min_score.
        """
        top_k = top_k or settings.retrieval_top_k
        min_score = settings.retrieval_min_score if min_score is None else min_score

        query_vector = get_embedding_service().embed_query(query)
        collection = self._get_collection()

        where = {"source": source_filter} if source_filter else None

        results = collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=where,
        )

        return self._to_chunks(results, min_score)

    @staticmethod
    def _to_chunks(results: dict, min_score: float) -> list[RetrievedChunk]:
        """
        Convert Chroma's parallel-list response into RetrievedChunk objects.

        Chroma returns dicts of lists-of-lists (one inner list per query).
        We only ever send one query, so we read index [0] of each.
        Distances are converted to similarity: similarity = 1 - distance
        (valid for cosine distance, which we configured on the collection).
        """
        docs = (results.get("documents") or [[]])[0]
        metas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]

        chunks: list[RetrievedChunk] = []
        for text, meta, distance in zip(docs, metas, distances):
            similarity = 1.0 - float(distance)
            if similarity < min_score:
                continue
            meta = meta or {}
            chunks.append(
                RetrievedChunk(
                    text=text,
                    source=meta.get("source", "unknown"),
                    section=meta.get("section", ""),
                    page=int(meta.get("page", 0)),
                    similarity_score=max(0.0, min(1.0, similarity)),
                )
            )
        return chunks

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------
    def delete_by_source(self, source: str) -> None:
        """
        Delete all chunks belonging to one source file.

        Called by the ingestion pipeline before re-adding a file, so
        re-ingesting a document replaces its chunks instead of
        duplicating them (idempotent ingestion).
        """
        collection = self._get_collection()
        collection.delete(where={"source": source})

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def count(self) -> int:
        """Return the total number of chunks stored."""
        return self._get_collection().count()

    def list_sources(self) -> list[str]:
        """
        Return the distinct source filenames currently in the store.
        Used by the Documents view in the UI.
        """
        collection = self._get_collection()
        # get() with no ids returns everything; we only need metadatas.
        data = collection.get(include=["metadatas"])
        metas = data.get("metadatas") or []
        sources = {m.get("source", "unknown") for m in metas if m}
        return sorted(sources)

    def reset(self) -> None:
        """
        Delete the entire collection and recreate it empty.
        Used by tests to guarantee a clean slate. Do not call in prod.
        """
        if self._client is None:
            self._get_collection()
        self._client.delete_collection(settings.chroma_collection_name)
        self._collection = None
        self._get_collection()


@lru_cache
def get_vector_store() -> VectorStore:
    """Return the shared VectorStore singleton."""
    return VectorStore()
