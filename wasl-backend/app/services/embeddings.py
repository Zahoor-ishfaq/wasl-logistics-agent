"""
app/services/embeddings.py

A thin wrapper around a local sentence-transformers embedding model.

Why local embeddings instead of an API?
  - Zero per-call cost — embeddings run on CPU, no API key, no billing
  - No network dependency — ingestion and retrieval work offline
  - Fast enough for our corpus size (a few hundred chunks)
  - Privacy — document text never leaves the machine to be embedded

The model (all-MiniLM-L6-v2) is small (~80MB) and produces 384-dim
vectors. It downloads once on first use and is cached locally after.

Why a wrapper?
  Same reasons as the LLM service: one place configures the model,
  one place to swap it, and tests can mock this instead of loading a
  real model (which is slow to import).

Nothing else in the app should import SentenceTransformer directly —
import get_embedding_service() from here.
"""

from functools import lru_cache

from app.config import settings


class EmbeddingService:
    """
    Wraps a sentence-transformers model and exposes two methods:

        embed_texts(list[str]) -> list[list[float]]
            Embed many texts at once (used during ingestion).

        embed_query(str) -> list[float]
            Embed a single query (used during retrieval).

    The model is loaded lazily on first use, not at construction —
    so importing this module stays cheap.
    """

    def __init__(self) -> None:
        self._model = None  # loaded on first embed call

    def _load_model(self):
        """
        Load the sentence-transformers model on first use.

        Imported inside the method (not at module top) because
        importing sentence_transformers is slow and pulls in torch.
        Deferring it keeps `import app.services.embeddings` fast for
        code paths and tests that never actually embed anything.
        """
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(settings.embedding_model)
        return self._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of texts. Used by the ingestion pipeline to embed
        all document chunks in one batch.

        Args:
            texts: The texts to embed.

        Returns:
            A list of vectors, one per input text. Each vector is a
            list of floats of length settings.embedding_dimension.
        """
        if not texts:
            return []
        model = self._load_model()
        # convert_to_numpy=True then .tolist() gives plain Python lists,
        # which Chroma expects. normalize_embeddings improves cosine
        # similarity behavior for retrieval.
        vectors = model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        """
        Embed a single query string. Used at retrieval time.

        Returns:
            One vector as a list of floats.
        """
        return self.embed_texts([text])[0]

    @property
    def dimension(self) -> int:
        """The dimension of the vectors this model produces."""
        return settings.embedding_dimension


@lru_cache
def get_embedding_service() -> EmbeddingService:
    """
    Return the shared EmbeddingService instance.

    lru_cache makes this a singleton — the model is only ever loaded
    once per process, no matter how many times this is called.
    """
    return EmbeddingService()