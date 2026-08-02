"""
app/services/vector_store.py

Vector-store abstraction used by Wasl.

Production (AWS):
  PostgreSQL RDS + pgvector when DB_HOST is configured.

Local development/tests:
  Existing persistent Chroma backend when DB_HOST is not configured.

This keeps the public VectorStore API unchanged, so the retriever,
RAG service, tools, and agent do not need to change.
"""

from functools import lru_cache

from pydantic import BaseModel, Field
from sqlalchemy import text as sql_text

from app.config import settings
from app.database import engine
from app.services.embeddings import get_embedding_service

_EMBEDDING_DIMENSION = 384


class RetrievedChunk(BaseModel):
    """One chunk returned from a similarity search."""

    text: str = Field(..., description="The chunk text.")
    source: str = Field(..., description="Source filename.")
    section: str = Field(default="", description="Section heading if available.")
    page: int = Field(default=0, description="Page number if available.")
    similarity_score: float = Field(..., ge=0.0, le=1.0)


class VectorStore:
    """
    Wasl vector store.

    AWS production uses pgvector because DB_HOST is set in the ECS task.
    Local development keeps the existing Chroma behavior because local
    .env uses DATABASE_URL and normally leaves DB_HOST empty.
    """

    def __init__(self) -> None:
        self._client = None
        self._collection = None
        self._use_pgvector = bool(settings.db_host)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _vector_literal(values: list[float]) -> str:
        """Convert an embedding to PostgreSQL vector input syntax."""
        if len(values) != _EMBEDDING_DIMENSION:
            raise ValueError(
                f"Expected {_EMBEDDING_DIMENSION}-dimensional embedding, "
                f"got {len(values)}."
            )

        return "[" + ",".join(
            f"{float(value):.10g}"
            for value in values
        ) + "]"

    def _get_collection(self):
        """Lazily initialize the local Chroma collection."""
        if self._collection is None:
            import chromadb

            self._client = chromadb.PersistentClient(
                path=settings.chroma_persist_directory,
            )

            self._collection = self._client.get_or_create_collection(
                name=settings.chroma_collection_name,
                metadata={"hnsw:space": "cosine"},
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
        """Embed and store chunks."""
        if not ids:
            return

        if not (
            len(ids)
            == len(texts)
            == len(metadatas)
        ):
            raise ValueError(
                "ids, texts and metadatas must have equal lengths."
            )

        embeddings = get_embedding_service().embed_texts(texts)

        if not self._use_pgvector:
            self._get_collection().add(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            return

        statement = sql_text(
            """
            INSERT INTO document_chunks
                (
                    id,
                    source,
                    section,
                    page,
                    chunk_text,
                    embedding
                )
            VALUES
                (
                    :id,
                    :source,
                    :section,
                    :page,
                    :chunk_text,
                    CAST(:embedding AS vector)
                )
            ON CONFLICT (id) DO UPDATE SET
                source = EXCLUDED.source,
                section = EXCLUDED.section,
                page = EXCLUDED.page,
                chunk_text = EXCLUDED.chunk_text,
                embedding = EXCLUDED.embedding,
                updated_at = NOW()
            """
        )

        rows = []

        for (
            chunk_id,
            chunk_text,
            metadata,
            embedding,
        ) in zip(
            ids,
            texts,
            metadatas,
            embeddings,
        ):
            metadata = metadata or {}

            rows.append(
                {
                    "id": chunk_id,
                    "source": str(
                        metadata.get("source", "unknown")
                    ),
                    "section": str(
                        metadata.get("section", "")
                    ),
                    "page": int(
                        metadata.get("page", 0) or 0
                    ),
                    "chunk_text": chunk_text,
                    "embedding": self._vector_literal(
                        embedding
                    ),
                }
            )

        with engine.begin() as connection:
            connection.execute(
                statement,
                rows,
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
        """Return the most similar chunks to a query."""

        top_k = (
            top_k
            or settings.retrieval_top_k
        )

        min_score = (
            settings.retrieval_min_score
            if min_score is None
            else min_score
        )

        query_vector = (
            get_embedding_service()
            .embed_query(query)
        )

        # Local Chroma
        if not self._use_pgvector:
            where = (
                {"source": source_filter}
                if source_filter
                else None
            )

            results = self._get_collection().query(
                query_embeddings=[query_vector],
                n_results=top_k,
                where=where,
            )

            return self._to_chunks(
                results,
                min_score,
            )

        # Production pgvector
        params = {
            "query_vector": self._vector_literal(
                query_vector
            ),
            "top_k": int(top_k),
        }

        source_clause = ""

        if source_filter:
            source_clause = (
                "WHERE source = :source_filter"
            )
            params["source_filter"] = source_filter

        statement = sql_text(
            f"""
            SELECT
                chunk_text,
                source,
                section,
                page,
                embedding
                    <=> CAST(:query_vector AS vector)
                    AS distance
            FROM document_chunks
            {source_clause}
            ORDER BY
                embedding
                    <=> CAST(:query_vector AS vector)
            LIMIT :top_k
            """
        )

        with engine.connect() as connection:
            rows = (
                connection.execute(
                    statement,
                    params,
                )
                .mappings()
                .all()
            )

        chunks: list[RetrievedChunk] = []

        for row in rows:
            similarity = (
                1.0
                - float(row["distance"])
            )

            similarity = max(
                0.0,
                min(1.0, similarity),
            )

            if similarity < min_score:
                continue

            chunks.append(
                RetrievedChunk(
                    text=row["chunk_text"],
                    source=row["source"],
                    section=(
                        row["section"]
                        or ""
                    ),
                    page=int(
                        row["page"]
                        or 0
                    ),
                    similarity_score=similarity,
                )
            )

        return chunks

    @staticmethod
    def _to_chunks(
        results: dict,
        min_score: float,
    ) -> list[RetrievedChunk]:
        """Convert Chroma's response into RetrievedChunk objects."""

        docs = (
            results.get("documents")
            or [[]]
        )[0]

        metas = (
            results.get("metadatas")
            or [[]]
        )[0]

        distances = (
            results.get("distances")
            or [[]]
        )[0]

        chunks: list[RetrievedChunk] = []

        for (
            chunk_text,
            metadata,
            distance,
        ) in zip(
            docs,
            metas,
            distances,
        ):
            similarity = (
                1.0
                - float(distance)
            )

            if similarity < min_score:
                continue

            metadata = metadata or {}

            chunks.append(
                RetrievedChunk(
                    text=chunk_text,
                    source=metadata.get(
                        "source",
                        "unknown",
                    ),
                    section=metadata.get(
                        "section",
                        "",
                    ),
                    page=int(
                        metadata.get(
                            "page",
                            0,
                        )
                        or 0
                    ),
                    similarity_score=max(
                        0.0,
                        min(
                            1.0,
                            similarity,
                        ),
                    ),
                )
            )

        return chunks

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_by_source(
        self,
        source: str,
    ) -> None:
        """Delete every chunk belonging to one source file."""

        if not self._use_pgvector:
            self._get_collection().delete(
                where={"source": source}
            )
            return

        with engine.begin() as connection:
            connection.execute(
                sql_text(
                    """
                    DELETE FROM document_chunks
                    WHERE source = :source
                    """
                ),
                {
                    "source": source,
                },
            )

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def count(self) -> int:
        """Return the total number of stored chunks."""

        if not self._use_pgvector:
            return (
                self._get_collection()
                .count()
            )

        with engine.connect() as connection:
            return int(
                connection.execute(
                    sql_text(
                        """
                        SELECT COUNT(*)
                        FROM document_chunks
                        """
                    )
                ).scalar_one()
            )

    def list_sources(self) -> list[str]:
        """Return distinct source filenames."""

        if not self._use_pgvector:
            data = (
                self._get_collection()
                .get(
                    include=["metadatas"]
                )
            )

            metas = (
                data.get("metadatas")
                or []
            )

            sources = {
                metadata.get(
                    "source",
                    "unknown",
                )
                for metadata in metas
                if metadata
            }

            return sorted(sources)

        with engine.connect() as connection:
            rows = (
                connection.execute(
                    sql_text(
                        """
                        SELECT DISTINCT source
                        FROM document_chunks
                        ORDER BY source
                        """
                    )
                )
                .scalars()
                .all()
            )

        return list(rows)

    def source_counts(self) -> dict[str, int]:
        """
        Return the number of chunks stored for each source document.

        Example:
            {
                "policy.pdf": 14,
                "customs.txt": 8
            }
        """

        # Local Chroma
        if not self._use_pgvector:
            data = (
                self._get_collection()
                .get(
                    include=["metadatas"]
                )
            )

            metas = (
                data.get("metadatas")
                or []
            )

            counts: dict[str, int] = {}

            for metadata in metas:
                if not metadata:
                    continue

                source = str(
                    metadata.get(
                        "source",
                        "unknown",
                    )
                )

                counts[source] = (
                    counts.get(
                        source,
                        0,
                    )
                    + 1
                )

            return dict(
                sorted(
                    counts.items()
                )
            )

        # Production pgvector
        with engine.connect() as connection:
            rows = (
                connection.execute(
                    sql_text(
                        """
                        SELECT
                            source,
                            COUNT(*) AS chunk_count
                        FROM document_chunks
                        GROUP BY source
                        ORDER BY source
                        """
                    )
                )
                .mappings()
                .all()
            )

        return {
            str(row["source"]): int(
                row["chunk_count"]
            )
            for row in rows
        }

    def reset(self) -> None:
        """Clear vector store. Intended for tests/admin maintenance."""

        if self._use_pgvector:
            with engine.begin() as connection:
                connection.execute(
                    sql_text(
                        """
                        DELETE FROM document_chunks
                        """
                    )
                )

            return

        if self._client is None:
            self._get_collection()

        self._client.delete_collection(
            settings.chroma_collection_name
        )

        self._collection = None

        self._get_collection()


@lru_cache
def get_vector_store() -> VectorStore:
    """Return the shared VectorStore singleton."""

    return VectorStore()