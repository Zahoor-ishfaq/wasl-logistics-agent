"""
app/api/routes_documents.py

Knowledge-base endpoints.

    GET    /documents
    POST   /documents/upload
    DELETE /documents/{filename}

Supported uploads:
    .md
    .txt
    .pdf

PDF text is extracted page-by-page so page numbers are retained in
vector metadata.

Scanned/image-only PDFs require OCR and are rejected with a clear
message for now.
"""

from io import BytesIO
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    UploadFile,
    status,
)

from app.api.deps import limiter, require_api_key
from app.config import settings
from app.services.vector_store import get_vector_store

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)

_ALLOWED_SUFFIXES = {
    ".md",
    ".txt",
    ".pdf",
}

_MAX_UPLOAD_BYTES = (
    20
    * 1024
    * 1024
)


@router.get(
    "",
    dependencies=[
        Depends(require_api_key)
    ],
    summary="List knowledge-base documents",
)
@limiter.limit("30/minute")
async def list_documents(
    request: Request,
) -> dict:
    """
    Return documents currently stored in the vector store.

    Includes:
    - document filenames
    - per-document chunk counts
    - total document count
    - total vector chunk count
    """

    store = get_vector_store()

    sources = store.list_sources()
    source_counts = store.source_counts()

    document_details = [
        {
            "name": source,
            "chunks": source_counts.get(
                source,
                0,
            ),
        }
        for source in sources
    ]

    return {
        # Kept for compatibility with existing frontend/code.
        "documents": sources,

        # New richer document information.
        "document_details": document_details,

        "count": len(sources),

        "total_chunks": store.count(),
    }


@router.post(
    "/upload",
    dependencies=[
        Depends(require_api_key)
    ],
    summary="Upload and ingest a document",
)
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    file: UploadFile,
) -> dict:
    """
    Upload a .md, .txt or text-based .pdf
    and make it searchable.
    """

    filename = Path(
        file.filename
        or ""
    ).name

    if not filename:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail="Filename is required.",
        )

    suffix = Path(
        filename
    ).suffix.lower()

    if suffix not in _ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                f"Unsupported file type "
                f"'{suffix}'. "
                "Allowed: .md, .txt, .pdf"
            ),
        )

    raw = await file.read()

    if len(raw) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            ),
            detail=(
                "File is larger than "
                "the 20 MB upload limit."
            ),
        )

    if not raw:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail="File is empty.",
        )

    # Imported here to keep API module lightweight.
    from scripts.ingest import chunk_document

    ids: list[str] = []
    texts: list[str] = []
    metadatas: list[dict] = []

    # --------------------------------------------------------------
    # PDF
    # --------------------------------------------------------------

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(
                BytesIO(raw)
            )

        except Exception as exc:
            raise HTTPException(
                status_code=(
                    status.HTTP_400_BAD_REQUEST
                ),
                detail="PDF could not be read.",
            ) from exc

        for page_number, page in enumerate(
            reader.pages,
            start=1,
        ):
            try:
                page_text = (
                    page.extract_text()
                    or ""
                )

            except Exception:
                page_text = ""

            if not page_text.strip():
                continue

            page_chunks = chunk_document(
                page_text
            )

            for (
                chunk_index,
                chunk,
            ) in enumerate(
                page_chunks
            ):
                ids.append(

                        f"{filename}"
                        f"::page_{page_number}"
                        f"::chunk_{chunk_index}"

                )

                texts.append(
                    chunk["text"]
                )

                metadatas.append(
                    {
                        "source": filename,
                        "section": chunk.get(
                            "section",
                            "",
                        ),
                        "page": page_number,
                    }
                )

        if not texts:
            raise HTTPException(
                status_code=(
                    status.HTTP_400_BAD_REQUEST
                ),
                detail=(
                    "PDF has no extractable text. "
                    "Scanned/image-only PDFs "
                    "need OCR before ingestion."
                ),
            )

    # --------------------------------------------------------------
    # TXT / Markdown
    # --------------------------------------------------------------

    else:
        try:
            document_text = raw.decode(
                "utf-8"
            )

        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=(
                    status.HTTP_400_BAD_REQUEST
                ),
                detail=(
                    "Text file must be "
                    "UTF-8 encoded."
                ),
            ) from exc

        if not document_text.strip():
            raise HTTPException(
                status_code=(
                    status.HTTP_400_BAD_REQUEST
                ),
                detail="File is empty.",
            )

        chunks = chunk_document(
            document_text
        )

        for (
            chunk_index,
            chunk,
        ) in enumerate(
            chunks
        ):
            ids.append(

                    f"{filename}"
                    f"::chunk_{chunk_index}"

            )

            texts.append(
                chunk["text"]
            )

            metadatas.append(
                {
                    "source": filename,
                    "section": chunk.get(
                        "section",
                        "",
                    ),
                    "page": 0,
                }
            )

    if not texts:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "No ingestible content "
                "found in the file."
            ),
        )

    # --------------------------------------------------------------
    # Save local copy
    # --------------------------------------------------------------

    docs_dir = Path(
        settings.documents_directory
    )

    docs_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path = (
        docs_dir
        / filename
    )

    file_path.write_bytes(
        raw
    )

    # --------------------------------------------------------------
    # Vector ingestion
    # --------------------------------------------------------------

    store = get_vector_store()

    # Re-uploading the same file should replace old chunks.
    store.delete_by_source(
        filename
    )

    store.add(
        ids=ids,
        texts=texts,
        metadatas=metadatas,
    )

    return {
        "filename": filename,
        "chunks_added": len(texts),
        "total_chunks": store.count(),
        "message": (
            "Document ingested and searchable."
        ),
    }


@router.delete(
    "/{filename}",
    dependencies=[
        Depends(require_api_key)
    ],
    summary="Delete a knowledge-base document",
)
@limiter.limit("20/minute")
async def delete_document(
    request: Request,
    filename: str,
) -> dict:
    """
    Delete a document from the knowledge base.

    Removes:
    - vector chunks for the source
    - local uploaded copy if it still exists

    Production vector data is removed from pgvector.
    """

    safe_filename = Path(
        filename
    ).name

    if not safe_filename:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail="Filename is required.",
        )

    # Prevent path traversal.
    if safe_filename != filename:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail="Invalid filename.",
        )

    store = get_vector_store()

    sources = store.list_sources()

    if safe_filename not in sources:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "Document not found "
                "in the knowledge base."
            ),
        )

    # --------------------------------------------------------------
    # Delete vector chunks
    # --------------------------------------------------------------

    store.delete_by_source(
        safe_filename
    )

    # --------------------------------------------------------------
    # Delete local copy if present
    # --------------------------------------------------------------

    docs_dir = Path(
        settings.documents_directory
    )

    local_file = (
        docs_dir
        / safe_filename
    )

    local_file_deleted = False

    try:
        if (
            local_file.exists()
            and local_file.is_file()
        ):
            local_file.unlink()
            local_file_deleted = True

    except OSError:
        # Vector deletion succeeded already.
        # Local ECS disk is ephemeral anyway.
        local_file_deleted = False

    return {
        "filename": safe_filename,
        "deleted": True,
        "local_file_deleted": (
            local_file_deleted
        ),
        "total_chunks": store.count(),
        "message": (
            "Document deleted from "
            "the knowledge base."
        ),
    }
