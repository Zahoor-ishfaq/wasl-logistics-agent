import re

import pytest

from app.services import vector_store


def normalize_sql(statement) -> str:
    """Collapse SQL whitespace so tests do not depend on formatting."""
    return re.sub(
        r"\s+",
        " ",
        str(statement),
    ).strip()


class FakeResult:
    def __init__(
        self,
        rows=None,
        scalar=None,
    ):
        self._rows = rows or []
        self._scalar = scalar

    def mappings(self):
        return self

    def all(self):
        return self._rows

    def scalar_one(self):
        return self._scalar

    def scalars(self):
        return self


class FakeConnection:
    def __init__(self):
        self.calls = []

    def execute(
        self,
        statement,
        params=None,
    ):
        self.calls.append(
            (statement, params)
        )

        sql = normalize_sql(
            statement
        )

        if "SELECT COUNT(*)" in sql:
            return FakeResult(
                scalar=3
            )

        if (
            "SELECT DISTINCT source"
            in sql
        ):
            return FakeResult(
                rows=[
                    "customs.pdf",
                    "policy.pdf",
                ]
            )

        if (
            "FROM document_chunks"
            in sql
            and "ORDER BY embedding"
            in sql
        ):
            return FakeResult(
                rows=[
                    {
                        "chunk_text":
                            "Customs clearance requires documents.",
                        "source":
                            "customs.pdf",
                        "section":
                            "Clearance",
                        "page": 2,
                        "distance":
                            0.1,
                    },
                    {
                        "chunk_text":
                            "Low relevance text.",
                        "source":
                            "other.pdf",
                        "section":
                            "",
                        "page": 1,
                        "distance":
                            0.8,
                    },
                ]
            )

        return FakeResult()

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ):
        return False


class FakeEngine:
    def __init__(self):
        self.connection = (
            FakeConnection()
        )

    def begin(self):
        return self.connection

    def connect(self):
        return self.connection


class FakeEmbeddingService:
    def embed_texts(
        self,
        texts,
    ):
        return [
            [0.01] * 384
            for _ in texts
        ]

    def embed_query(
        self,
        query,
    ):
        return [0.02] * 384


@pytest.fixture
def pg_store(
    monkeypatch,
):
    monkeypatch.setattr(
        vector_store.settings,
        "db_host",
        "rds.example.internal",
    )

    fake_engine = (
        FakeEngine()
    )

    monkeypatch.setattr(
        vector_store,
        "engine",
        fake_engine,
    )

    monkeypatch.setattr(
        vector_store,
        "get_embedding_service",
        lambda:
            FakeEmbeddingService(),
    )

    return (
        vector_store.VectorStore(),
        fake_engine,
    )


def test_vector_literal_validates_dimension():
    values = [0.1] * 384

    literal = (
        vector_store
        .VectorStore
        ._vector_literal(
            values
        )
    )

    assert literal.startswith(
        "["
    )

    assert literal.endswith(
        "]"
    )

    assert (
        literal.count(",")
        == 383
    )

    with pytest.raises(
        ValueError
    ):
        (
            vector_store
            .VectorStore
            ._vector_literal(
                [0.1, 0.2]
            )
        )


def test_pgvector_add(
    pg_store,
):
    store, fake_engine = (
        pg_store
    )

    store.add(
        ids=[
            "policy.pdf::chunk_0"
        ],
        texts=[
            "Important policy text"
        ],
        metadatas=[
            {
                "source":
                    "policy.pdf",
                "section":
                    "SLA",
                "page": 4,
            }
        ],
    )

    assert (
        len(
            fake_engine
            .connection
            .calls
        )
        == 1
    )

    _, params = (
        fake_engine
        .connection
        .calls[0]
    )

    assert (
        params[0]["id"]
        == "policy.pdf::chunk_0"
    )

    assert (
        params[0]["source"]
        == "policy.pdf"
    )

    assert (
        params[0]["section"]
        == "SLA"
    )

    assert (
        params[0]["page"]
        == 4
    )

    assert (
        params[0][
            "chunk_text"
        ]
        == "Important policy text"
    )

    assert (
        params[0][
            "embedding"
        ].startswith("[")
    )


def test_pgvector_add_rejects_mismatched_lists(
    pg_store,
):
    store, _ = pg_store

    with pytest.raises(
        ValueError
    ):
        store.add(
            ids=["one"],
            texts=["text"],
            metadatas=[],
        )


def test_pgvector_search_filters_by_score_and_source(
    pg_store,
):
    store, fake_engine = (
        pg_store
    )

    chunks = store.search(
        query=
            "customs documents",
        top_k=5,
        min_score=0.5,
        source_filter=
            "customs.pdf",
    )

    assert len(chunks) == 1

    assert (
        chunks[0].source
        == "customs.pdf"
    )

    assert (
        chunks[0].section
        == "Clearance"
    )

    assert (
        chunks[0].page
        == 2
    )

    assert (
        chunks[0]
        .similarity_score
        == pytest.approx(0.9)
    )

    _, params = (
        fake_engine
        .connection
        .calls[-1]
    )

    assert (
        params[
            "source_filter"
        ]
        == "customs.pdf"
    )

    assert (
        params["top_k"]
        == 5
    )


def test_pgvector_delete_count_list_and_reset(
    pg_store,
):
    store, fake_engine = (
        pg_store
    )

    store.delete_by_source(
        "policy.pdf"
    )

    assert store.count() == 3

    assert (
        store.list_sources()
        == [
            "customs.pdf",
            "policy.pdf",
        ]
    )

    store.reset()

    sql_calls = [
        normalize_sql(
            statement
        )
        for (
            statement,
            _,
        ) in (
            fake_engine
            .connection
            .calls
        )
    ]

    assert any(
        (
            "DELETE FROM "
            "document_chunks "
            "WHERE source"
        )
        in sql
        for sql in sql_calls
    )

    assert any(
        "SELECT COUNT(*)"
        in sql
        for sql in sql_calls
    )

    assert any(
        (
            "SELECT DISTINCT "
            "source"
        )
        in sql
        for sql in sql_calls
    )

    assert any(
        (
            sql.startswith(
                "DELETE FROM "
                "document_chunks"
            )
            and "WHERE source"
            not in sql
        )
        for sql in sql_calls
    )