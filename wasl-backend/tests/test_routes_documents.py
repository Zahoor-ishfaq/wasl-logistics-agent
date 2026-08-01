import asyncio
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile

from app.api import routes_documents
from scripts import ingest


def run_async(function, *args):
    original = getattr(function, "__wrapped__", function)
    return asyncio.run(original(*args))


def make_upload(filename: str, data: bytes) -> UploadFile:
    return UploadFile(filename=filename, file=BytesIO(data))


def test_list_documents(monkeypatch):
    store = SimpleNamespace(
        list_sources=lambda: ["policy.md", "customs.txt"],
        count=lambda: 7,
    )
    monkeypatch.setattr(
        routes_documents,
        "get_vector_store",
        lambda: store,
    )

    response = run_async(routes_documents.list_documents, None)

    assert response == {
        "documents": ["policy.md", "customs.txt"],
        "count": 2,
        "total_chunks": 7,
    }


def test_upload_rejects_unsupported_file():
    file = make_upload("policy.pdf", b"content")

    with pytest.raises(HTTPException) as error:
        run_async(routes_documents.upload_document, None, file)

    assert error.value.status_code == 400
    assert "Unsupported file type" in error.value.detail


def test_upload_rejects_invalid_utf8():
    file = make_upload("policy.txt", b"\xff\xfe")

    with pytest.raises(HTTPException) as error:
        run_async(routes_documents.upload_document, None, file)

    assert error.value.status_code == 400
    assert error.value.detail == "File must be UTF-8 encoded text."


def test_upload_rejects_empty_file():
    file = make_upload("policy.md", b"   \n")

    with pytest.raises(HTTPException) as error:
        run_async(routes_documents.upload_document, None, file)

    assert error.value.status_code == 400
    assert error.value.detail == "File is empty."


def test_upload_rejects_file_without_chunks(tmp_path, monkeypatch):
    monkeypatch.setattr(
        routes_documents.settings,
        "documents_directory",
        str(tmp_path),
    )
    monkeypatch.setattr(ingest, "chunk_document", lambda text: [])

    file = make_upload("policy.md", b"Valid text")

    with pytest.raises(HTTPException) as error:
        run_async(routes_documents.upload_document, None, file)

    assert error.value.status_code == 400
    assert error.value.detail == "No ingestible content found in the file."


def test_upload_ingests_document(tmp_path, monkeypatch):
    monkeypatch.setattr(
        routes_documents.settings,
        "documents_directory",
        str(tmp_path),
    )
    monkeypatch.setattr(
        ingest,
        "chunk_document",
        lambda text: [
            {"text": "First section", "section": "Introduction"},
            {"text": "Second section", "section": "Requirements"},
        ],
    )

    calls = {}

    class FakeStore:
        def delete_by_source(self, source):
            calls["deleted"] = source

        def add(self, ids, texts, metadatas):
            calls["ids"] = ids
            calls["texts"] = texts
            calls["metadatas"] = metadatas

        def count(self):
            return 12

    monkeypatch.setattr(
        routes_documents,
        "get_vector_store",
        lambda: FakeStore(),
    )

    file = make_upload("policy.md", b"# Policy\nUseful content")
    response = run_async(routes_documents.upload_document, None, file)

    assert (tmp_path / "policy.md").read_text(encoding="utf-8") == (
        "# Policy\nUseful content"
    )
    assert calls["deleted"] == "policy.md"
    assert calls["ids"] == [
        "policy.md::chunk_0",
        "policy.md::chunk_1",
    ]
    assert calls["texts"] == [
        "First section",
        "Second section",
    ]
    assert calls["metadatas"] == [
        {
            "source": "policy.md",
            "section": "Introduction",
            "page": 0,
        },
        {
            "source": "policy.md",
            "section": "Requirements",
            "page": 0,
        },
    ]
    assert response == {
        "filename": "policy.md",
        "chunks_added": 2,
        "total_chunks": 12,
        "message": "Document ingested and searchable.",
    }
