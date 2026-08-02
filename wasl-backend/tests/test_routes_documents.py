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
        list_sources=lambda: [
            "policy.md",
            "customs.txt",
        ],
        source_counts=lambda: {
            "policy.md": 4,
            "customs.txt": 3,
        },
        count=lambda: 7,
    )

    monkeypatch.setattr(
        routes_documents,
        "get_vector_store",
        lambda: store,
    )

    response = run_async(
        routes_documents.list_documents,
        None,
    )

    assert response == {
        "documents": [
            "policy.md",
            "customs.txt",
        ],
        "document_details": [
            {
                "name": "policy.md",
                "chunks": 4,
            },
            {
                "name": "customs.txt",
                "chunks": 3,
            },
        ],
        "count": 2,
        "total_chunks": 7,
    }


def test_upload_rejects_missing_filename():
    file = make_upload(
        "",
        b"content",
    )

    with pytest.raises(HTTPException) as error:
        run_async(
            routes_documents.upload_document,
            None,
            file,
        )

    assert error.value.status_code == 400
    assert error.value.detail == "Filename is required."


def test_upload_rejects_unsupported_file():
    file = make_upload(
        "policy.docx",
        b"content",
    )

    with pytest.raises(HTTPException) as error:
        run_async(
            routes_documents.upload_document,
            None,
            file,
        )

    assert error.value.status_code == 400
    assert "Unsupported file type" in error.value.detail


def test_upload_rejects_invalid_utf8():
    file = make_upload(
        "policy.txt",
        b"\xff\xfe",
    )

    with pytest.raises(HTTPException) as error:
        run_async(
            routes_documents.upload_document,
            None,
            file,
        )

    assert error.value.status_code == 400
    assert error.value.detail == "Text file must be UTF-8 encoded."


def test_upload_rejects_empty_file():
    file = make_upload(
        "policy.md",
        b"",
    )

    with pytest.raises(HTTPException) as error:
        run_async(
            routes_documents.upload_document,
            None,
            file,
        )

    assert error.value.status_code == 400
    assert error.value.detail == "File is empty."


def test_upload_rejects_oversized_file(monkeypatch):
    monkeypatch.setattr(
        routes_documents,
        "_MAX_UPLOAD_BYTES",
        3,
    )

    file = make_upload(
        "policy.txt",
        b"1234",
    )

    with pytest.raises(HTTPException) as error:
        run_async(
            routes_documents.upload_document,
            None,
            file,
        )

    assert error.value.status_code == 413
    assert (
        error.value.detail
        == "File is larger than the 20 MB upload limit."
    )


def test_upload_rejects_file_without_chunks(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        routes_documents.settings,
        "documents_directory",
        str(tmp_path),
    )

    monkeypatch.setattr(
        ingest,
        "chunk_document",
        lambda text: [],
    )

    file = make_upload(
        "policy.md",
        b"Valid text",
    )

    with pytest.raises(HTTPException) as error:
        run_async(
            routes_documents.upload_document,
            None,
            file,
        )

    assert error.value.status_code == 400
    assert (
        error.value.detail
        == "No ingestible content found in the file."
    )


def test_upload_ingests_document(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        routes_documents.settings,
        "documents_directory",
        str(tmp_path),
    )

    monkeypatch.setattr(
        ingest,
        "chunk_document",
        lambda text: [
            {
                "text": "First section",
                "section": "Introduction",
            },
            {
                "text": "Second section",
                "section": "Requirements",
            },
        ],
    )

    calls = {}

    class FakeStore:
        def delete_by_source(self, source):
            calls["deleted"] = source

        def add(
            self,
            ids,
            texts,
            metadatas,
        ):
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

    file = make_upload(
        "policy.md",
        b"# Policy\nUseful content",
    )

    response = run_async(
        routes_documents.upload_document,
        None,
        file,
    )

    assert (
        tmp_path / "policy.md"
    ).read_text(
        encoding="utf-8"
    ) == "# Policy\nUseful content"

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


def test_upload_rejects_unreadable_pdf(monkeypatch):
    import pypdf

    def broken_reader(_):
        raise ValueError("bad pdf")

    monkeypatch.setattr(
        pypdf,
        "PdfReader",
        broken_reader,
    )

    file = make_upload(
        "broken.pdf",
        b"%PDF-broken",
    )

    with pytest.raises(HTTPException) as error:
        run_async(
            routes_documents.upload_document,
            None,
            file,
        )

    assert error.value.status_code == 400
    assert error.value.detail == "PDF could not be read."


def test_upload_rejects_pdf_without_extractable_text(
    monkeypatch,
):
    import pypdf

    class FakePage:
        def extract_text(self):
            return ""

    class FakeReader:
        def __init__(self, _):
            self.pages = [
                FakePage()
            ]

    monkeypatch.setattr(
        pypdf,
        "PdfReader",
        FakeReader,
    )

    file = make_upload(
        "scan.pdf",
        b"%PDF-scan",
    )

    with pytest.raises(HTTPException) as error:
        run_async(
            routes_documents.upload_document,
            None,
            file,
        )

    assert error.value.status_code == 400
    assert "no extractable text" in error.value.detail


def test_upload_ingests_pdf_pages(
    tmp_path,
    monkeypatch,
):
    import pypdf

    monkeypatch.setattr(
        routes_documents.settings,
        "documents_directory",
        str(tmp_path),
    )

    class FakePage:
        def __init__(self, text):
            self._text = text

        def extract_text(self):
            return self._text

    class FakeReader:
        def __init__(self, _):
            self.pages = [
                FakePage(
                    "Page one policy text"
                ),
                FakePage(
                    "Page two customs text"
                ),
            ]

    monkeypatch.setattr(
        pypdf,
        "PdfReader",
        FakeReader,
    )

    monkeypatch.setattr(
        ingest,
        "chunk_document",
        lambda text: [
            {
                "text": text,
                "section": "PDF Section",
            }
        ],
    )

    calls = {}

    class FakeStore:
        def delete_by_source(self, source):
            calls["deleted"] = source

        def add(
            self,
            ids,
            texts,
            metadatas,
        ):
            calls["ids"] = ids
            calls["texts"] = texts
            calls["metadatas"] = metadatas

        def count(self):
            return 20

    monkeypatch.setattr(
        routes_documents,
        "get_vector_store",
        lambda: FakeStore(),
    )

    raw_pdf = b"%PDF-demo"

    file = make_upload(
        "customs.pdf",
        raw_pdf,
    )

    response = run_async(
        routes_documents.upload_document,
        None,
        file,
    )

    assert (
        tmp_path / "customs.pdf"
    ).read_bytes() == raw_pdf

    assert calls["deleted"] == "customs.pdf"

    assert calls["ids"] == [
        "customs.pdf::page_1::chunk_0",
        "customs.pdf::page_2::chunk_0",
    ]

    assert calls["texts"] == [
        "Page one policy text",
        "Page two customs text",
    ]

    assert calls["metadatas"] == [
        {
            "source": "customs.pdf",
            "section": "PDF Section",
            "page": 1,
        },
        {
            "source": "customs.pdf",
            "section": "PDF Section",
            "page": 2,
        },
    ]

    assert response == {
        "filename": "customs.pdf",
        "chunks_added": 2,
        "total_chunks": 20,
        "message": "Document ingested and searchable.",
    }
