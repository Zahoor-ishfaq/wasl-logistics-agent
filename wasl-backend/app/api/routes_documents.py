"""
app/api/routes_documents.py

Knowledge-base endpoints.

    GET  /documents          list ingested documents
    POST /documents/upload   upload a document, ingest it, add to the store

The upload endpoint is what makes the UI's "Add documents" affordance
real: it receives a file, saves it into the documents directory, runs
the same chunk-embed-store pipeline the ingest script uses, and the
document becomes immediately searchable.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status

from app.api.deps import limiter, require_api_key
from app.config import settings
from app.services.vector_store import get_vector_store

router = APIRouter(prefix="/documents", tags=["documents"])

# Allowed upload types — text formats the ingest pipeline can read.
_ALLOWED_SUFFIXES = {".md", ".txt"}


@router.get(
    "",
    dependencies=[Depends(require_api_key)],
    summary="List knowledge-base documents",
)
@limiter.limit("30/minute")
async def list_documents(request: Request) -> dict:
    """Return the distinct source documents currently in the vector store."""
    store = get_vector_store()
    sources = store.list_sources()
    return {
        "documents": sources,
        "count": len(sources),
        "total_chunks": store.count(),
    }


@router.post(
    "/upload",
    dependencies=[Depends(require_api_key)],
    summary="Upload and ingest a document",
)
@limiter.limit("10/minute")
async def upload_document(request: Request, file: UploadFile) -> dict:
    """
    Upload a .md or .txt document, ingest it, and add it to the store.

    The document is saved to the documents directory and processed with
    the same chunk-embed-store pipeline as the ingest script, so it is
    immediately searchable afterwards.
    """
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()

    if suffix not in _ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{suffix}'. Allowed: .md, .txt",
        )

    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be UTF-8 encoded text.",
        )

    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty.",
        )

    # Save into the documents directory (so a later full re-ingest sees it too).
    docs_dir = Path(settings.documents_directory)
    docs_dir.mkdir(parents=True, exist_ok=True)
    dest = docs_dir / filename
    dest.write_text(text, encoding="utf-8")

    # Ingest just this file using the shared chunking logic.
    # Imported here to avoid a heavy import at module load.
    from scripts.ingest import chunk_document

    chunks = chunk_document(text)
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No ingestible content found in the file.",
        )

    store = get_vector_store()
    store.delete_by_source(filename)  # idempotent
    ids = [f"{filename}::chunk_{i}" for i in range(len(chunks))]
    texts = [c["text"] for c in chunks]
    metadatas = [
        {"source": filename, "section": c["section"], "page": 0}
        for c in chunks
    ]
    store.add(ids=ids, texts=texts, metadatas=metadatas)

    return {
        "filename": filename,
        "chunks_added": len(chunks),
        "total_chunks": store.count(),
        "message": "Document ingested and searchable.",
    }