"""
app/config.py

Central settings object for Wasl. Reads from environment variables
(loaded from .env in development by python-dotenv).

Usage anywhere in the codebase:
    from app.config import settings
    print(settings.anthropic_api_key)
"""

from functools import lru_cache
from urllib.parse import quote

from pydantic import Field, model_validator
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
        extra="ignore",
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
    anthropic_api_key: str = Field(
        ...,
        description="Anthropic API key — required",
    )
    anthropic_model: str = "claude-sonnet-4-6"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 2048

    llm_daily_cost_cap_usd: float = Field(
        default=5.0,
        description="Maximum LLM spend per day in USD. Protects budget.",
    )

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # ------------------------------------------------------------------
    # Vector store (Chroma)
    # ------------------------------------------------------------------
    chroma_persist_directory: str = "chroma_db"
    chroma_collection_name: str = "wasl_knowledge_base"

    retrieval_top_k: int = 5
    retrieval_min_score: float = 0.3

    # ------------------------------------------------------------------
    # Semantic cache (Redis)
    # ------------------------------------------------------------------
    cache_enabled: bool = True
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    cache_similarity_threshold: float = 0.95
    cache_ttl_seconds: int = 86400

    # ------------------------------------------------------------------
    # Document ingestion
    # ------------------------------------------------------------------
    documents_directory: str = "data/documents"

    chunk_size: int = 2000
    chunk_overlap: int = 200

    # ------------------------------------------------------------------
    # JWT authentication
    # ------------------------------------------------------------------
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    auth_username: str = "admin"
    auth_password_hash: str = ""

    # ------------------------------------------------------------------
    # PostgreSQL database
    # ------------------------------------------------------------------
    #
    # Local development:
    #   DATABASE_URL=postgresql+psycopg2://...
    #
    # Production / ECS:
    #   DB_HOST
    #   DB_PORT
    #   DB_NAME
    #   DB_USER
    #   DB_PASSWORD
    #
    # DB_PASSWORD can be injected directly from AWS Secrets Manager.
    # ------------------------------------------------------------------

    database_url: str = ""

    db_host: str = ""
    db_port: int = 5432
    db_name: str = "wasl"
    db_user: str = ""
    db_password: str = ""
    db_sslmode: str = "require"

    @model_validator(mode="after")
    def configure_database_url(self) -> "Settings":
        """
        Use DATABASE_URL when supplied, which keeps local development
        unchanged.

        In production, build DATABASE_URL from individual environment
        variables so credentials can be injected securely by ECS and
        AWS Secrets Manager.
        """

        if self.database_url:
            return self

        if self.db_host and self.db_user and self.db_password:
            username = quote(self.db_user, safe="")
            password = quote(self.db_password, safe="")
            database = quote(self.db_name, safe="")

            self.database_url = (
                f"postgresql+psycopg2://"
                f"{username}:{password}"
                f"@{self.db_host}:{self.db_port}/{database}"
                f"?sslmode={self.db_sslmode}"
            )

            return self

        raise ValueError(
            "Database configuration missing. "
            "Set DATABASE_URL or DB_HOST, DB_USER and DB_PASSWORD."
        )

    # ------------------------------------------------------------------
    # Mock shipment data
    # ------------------------------------------------------------------
    mock_shipments_file: str = "data/mock_shipments.json"

    # ------------------------------------------------------------------
    # API security
    # ------------------------------------------------------------------
    api_key: str = Field(
        ...,
        description="API key for authenticating clients — required",
    )

    rate_limit_per_minute: int = 30

    # ------------------------------------------------------------------
    # Observability (Langfuse)
    # ------------------------------------------------------------------
    tracing_enabled: bool = True

    langfuse_public_key: str = Field(
        default="",
        description="Langfuse public key",
    )
    langfuse_secret_key: str = Field(
        default="",
        description="Langfuse secret key",
    )
    langfuse_host: str = "https://cloud.langfuse.com"

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    cors_origins: str = "http://localhost:3000,http://localhost:8501"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse the comma-separated CORS origins into a list."""
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """
    Return the Settings singleton.

    lru_cache means this is instantiated only once.
    """
    return Settings()


settings: Settings = get_settings()
