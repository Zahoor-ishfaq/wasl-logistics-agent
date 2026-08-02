"""add pgvector document chunks

Revision ID: 9d7c3a1b6e42
Revises: 7128700a6766
Create Date: 2026-08-02
"""

from alembic import op

revision = "9d7c3a1b6e42"
down_revision = "7128700a6766"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Amazon RDS for PostgreSQL supports pgvector under extension name "vector".
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute(
        """
        CREATE TABLE document_chunks (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            section TEXT NOT NULL DEFAULT '',
            page INTEGER NOT NULL DEFAULT 0,
            chunk_text TEXT NOT NULL,
            embedding vector(384) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )

    op.execute(
        """
        CREATE INDEX ix_document_chunks_source
        ON document_chunks (source)
        """
    )

    op.execute(
        """
        CREATE INDEX ix_document_chunks_embedding_hnsw
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_source")
    op.execute("DROP TABLE IF EXISTS document_chunks")
    # Intentionally keep the vector extension installed because other
    # database objects may use it later.
