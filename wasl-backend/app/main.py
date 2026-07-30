"""
app/main.py

FastAPI application entry point for Wasl.

Wires together:
  - CORS (so the React UI can call the API from its dev server)
  - the rate limiter (slowapi) and its 429 handler
  - the three route groups: answer, investigations, documents
  - a health check
  - a startup hook that warms the vector store

Run locally:
    uvicorn app.main:app --reload

Interactive docs are then at http://localhost:8000/docs
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.deps import limiter
from app.api.routes_answer import router as answer_router
from app.api.routes_documents import router as documents_router
from app.api.routes_investigations import router as investigations_router
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup/shutdown lifecycle.

    On startup we warm the vector store so the first real request isn't
    slowed by lazy initialization. If the store is empty, we log a hint
    rather than failing — the app can still start; answers will just
    decline until documents are ingested.
    """
    from app.services.vector_store import get_vector_store

    try:
        count = get_vector_store().count()
        print(f"[startup] Vector store ready: {count} chunks.")
        if count == 0:
            print("[startup] Knowledge base is empty — run scripts/ingest.py.")
    except Exception as exc:  # noqa: BLE001
        print(f"[startup] Warning: could not reach vector store: {exc}")

    yield
    # (nothing to clean up on shutdown for v1)


app = FastAPI(
    title="Wasl — Operations Intelligence API",
    description="Agentic RAG platform for logistics exception investigation.",
    version=settings.app_version,
    lifespan=lifespan,
)

# --- Rate limiting ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- CORS (allow the React UI origin) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---
app.include_router(answer_router)
app.include_router(investigations_router)
app.include_router(documents_router)


@app.get("/health", tags=["health"])
async def health() -> dict:
    """
    Unauthenticated health check.

    Returns basic liveness and the current knowledge-base size, so a
    load balancer or uptime monitor can confirm the app is up.
    """
    from app.services.vector_store import get_vector_store

    try:
        chunks = get_vector_store().count()
        kb_ok = True
    except Exception:  # noqa: BLE001
        chunks = 0
        kb_ok = False

    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "knowledge_base_chunks": chunks,
        "knowledge_base_ready": kb_ok,
    }


@app.get("/", tags=["health"])
async def root() -> dict:
    """Friendly root pointing at the docs."""
    return {
        "app": settings.app_name,
        "docs": "/docs",
        "health": "/health",
    }
