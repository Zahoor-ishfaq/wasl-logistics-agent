"""
app/config.py

Central settings object for Wasl. Reads from environment variables
(loaded from .env in development by python-dotenv).

Usage anywhere in the codebase:
    from app.config import settings
    print(settings.anthropic_api_key)
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All configuration for the application.

    Values are read from environment variables. In local development,
    variables are loaded from a .env file in the project root.
    In production, they come from the real environment.

    If a required variable is missing, the app fails immediately on
    startup with a clear error — rather than crashing later when
    the variable is first used.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # silently ignore unknown env vars
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    app_name: str = "Wasl"
    app_version: str = "0.1.0"
    debug: bool = False

    # ------------------------------------------------------------------
    # LLM provider (Anthropic Claude)
    # ------------------------------------------------------------------
    anthropic_api_key: str = Field(..., description="Anthropic API key — required")
    anthropic_model: str = "claude-sonnet-4-6"
    llm_temperature: float = 0.0  # deterministic for RAG and agent reasoning
    llm_max_tokens: int = 2048

    # Daily cost cap in USD. Requests are rejected once this is exceeded.
    # Set to 0.0 to disable the cap (not recommended in production).
    llm_daily_cost_cap_usd: float = Field(
        default=5.0,
        description="Maximum LLM spend per day in USD. Protects budget.",
    )

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------
    # sentence-transformers model — runs locally, no API key needed.
    # all-MiniLM-L6-v2 is small (~80MB), fast on CPU, good quality.
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384  # must match the model above

    # ------------------------------------------------------------------
    # Vector store (Chroma)
    # ------------------------------------------------------------------
    chroma_persist_directory: str = "chroma_db"
    chroma_collection_name: str = "wasl_knowledge_base"

    # Number of chunks to retrieve per query
    retrieval_top_k: int = 5

    # Minimum similarity score — chunks below this are considered irrelevant.
    # Range: 0.0 (keep everything) to 1.0 (keep only exact matches).
    # 0.3 is a reasonable starting point; tune against eval scores.
    retrieval_min_score: float = 0.3

    # ------------------------------------------------------------------
    # Document ingestion
    # ------------------------------------------------------------------
    documents_directory: str = "data/documents"

    # Chunk size in tokens (approximate — splitter uses characters).
    # 500 tokens ≈ 2000 characters for English prose.
    chunk_size: int = 2000
    chunk_overlap: int = 200  # ~50 tokens overlap between chunks

    # ------------------------------------------------------------------
    # Mock shipment data
    # ------------------------------------------------------------------
    mock_shipments_file: str = "data/mock_shipments.json"

    # ------------------------------------------------------------------
    # API security
    # ------------------------------------------------------------------
    # The API key clients must send in the X-API-Key header.
    # Use a strong random string in production.
    api_key: str = Field(
        ..., description="API key for authenticating clients — required"
    )

    # Rate limiting: max requests per minute per IP address
    rate_limit_per_minute: int = 30

    # ------------------------------------------------------------------
    # Observability (Langfuse)
    # ------------------------------------------------------------------
    # Set to False to disable tracing entirely (e.g. in CI tests)
    tracing_enabled: bool = True
    langfuse_public_key: str = Field(default="", description="Langfuse public key")
    langfuse_secret_key: str = Field(default="", description="Langfuse secret key")
    langfuse_host: str = "https://cloud.langfuse.com"

    # ------------------------------------------------------------------
    # CORS (for the API)
    # ------------------------------------------------------------------
    # Comma-separated list of allowed origins.
    # Use "*" only in development; never in production.
    cors_origins: str = "http://localhost:3000,http://localhost:8501"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse the comma-separated CORS origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """
    Return the Settings singleton.

    lru_cache means this is only instantiated once — the same object
    is returned on every subsequent call. This is the pattern FastAPI
    recommends for settings with Depends().

    Example in a FastAPI route:
        from app.config import get_settings
        from fastapi import Depends

        @app.get("/health")
        def health(settings: Settings = Depends(get_settings)):
            return {"app": settings.app_name}
    """
    return Settings()


# Module-level convenience alias.
# Import this anywhere you need settings without going through Depends():
#   from app.config import settings
settings: Settings = get_settings()
