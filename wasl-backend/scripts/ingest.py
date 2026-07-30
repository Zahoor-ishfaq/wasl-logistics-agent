"""
scripts/ingest.py

Ingestion pipeline: reads the knowledge-base documents, splits them
into chunks, embeds them, and stores them in the Chroma vector store.

Run this once after placing documents in data/documents/, and again
whenever those documents change.

    python scripts/ingest.py

What it does, per file:
  1. Read the markdown text
  2. Split by markdown headers  → captures the section name as metadata
  3. Split large sections into ~chunk_size pieces with overlap
  4. Delete any existing chunks for this file (idempotent re-ingest)
  5. Embed all chunks and store them in Chroma with metadata

Idempotent: re-running replaces a file's chunks instead of duplicating.
"""

import sys
from pathlib import Path

# Make the project root importable when running this file directly
# (so `from app...` works whether run as `python scripts/ingest.py`
# from the project root, which is the intended usage).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from langchain_text_splitters import (  # noqa: E402
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from app.config import settings  # noqa: E402
from app.services.vector_store import get_vector_store  # noqa: E402


# Markdown headers we split on. The section name is stored in metadata
# so citations can tell the user which section an answer came from.
HEADERS_TO_SPLIT_ON = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
]


def chunk_document(text: str) -> list[dict]:
    """
    Split one document's text into chunks with section metadata.

    Returns a list of dicts: {"text": str, "section": str}

    Two-stage split:
      1. MarkdownHeaderTextSplitter — break at headers, tagging each
         piece with its section heading(s).
      2. RecursiveCharacterTextSplitter — break any piece that is still
         larger than chunk_size into overlapping sub-chunks.
    """
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS_TO_SPLIT_ON,
        strip_headers=False,  # keep headers in the text for context
    )
    header_sections = header_splitter.split_text(text)

    size_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[dict] = []
    for section in header_sections:
        # Pick the most specific heading available for this section.
        meta = section.metadata
        section_name = meta.get("h3") or meta.get("h2") or meta.get("h1") or ""

        # Break the section further if it's too large.
        for piece in size_splitter.split_text(section.page_content):
            piece = piece.strip()
            if piece:
                chunks.append({"text": piece, "section": section_name})

    return chunks


def ingest_file(path: Path, store) -> int:
    """
    Ingest a single document file into the vector store.

    Returns the number of chunks stored.
    """
    text = path.read_text(encoding="utf-8")
    source = path.name

    chunks = chunk_document(text)
    if not chunks:
        print(f"  ! {source}: no content found, skipped")
        return 0

    # Idempotent: remove old chunks for this source before adding new ones.
    store.delete_by_source(source)

    ids = [f"{source}::chunk_{i}" for i in range(len(chunks))]
    texts = [c["text"] for c in chunks]
    metadatas = [
        {"source": source, "section": c["section"], "page": 0}
        for c in chunks
    ]

    store.add(ids=ids, texts=texts, metadatas=metadatas)
    return len(chunks)


def main() -> None:
    docs_dir = Path(settings.documents_directory)

    if not docs_dir.exists():
        print(f"ERROR: documents directory not found: {docs_dir}")
        print("Create it and add your .md documents, then run again.")
        sys.exit(1)

    # Support both .md and .txt documents.
    files = sorted(
        [p for p in docs_dir.iterdir() if p.suffix.lower() in {".md", ".txt"}]
    )

    if not files:
        print(f"ERROR: no .md or .txt files found in {docs_dir}")
        sys.exit(1)

    print(f"Ingesting {len(files)} document(s) from {docs_dir}\n")

    store = get_vector_store()
    total_chunks = 0

    for path in files:
        count = ingest_file(path, store)
        total_chunks += count
        print(f"  \u2713 {path.name} \u2192 {count} chunks")

    print(f"\nDone. {total_chunks} chunks stored across {len(files)} documents.")
    print(f"Vector store total: {store.count()} chunks.")
    print(f"Persisted to: {settings.chroma_persist_directory}/")


if __name__ == "__main__":
    main()