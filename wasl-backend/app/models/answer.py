"""
app/models/answer.py

Pydantic schemas for the RAG answer response.

Every answer the system returns must either:
  - Cite the exact document chunks it drew from, OR
  - Explicitly decline when no relevant context was found.

This enforces Wasl's grounding rule: answers must be based on
retrieved knowledge-base context.
"""

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """
    A single source chunk that contributed to an answer.

    The full retrieved chunk is preserved so the RAG layer can reason
    over all relevant text instead of only the first 500 characters.
    """

    source: str = Field(
        ...,
        description="Filename of the source document.",
        examples=["customs_procedure.md"],
    )

    section: str = Field(
        default="",
        description="Section heading within the document, if available.",
        examples=["Required documentation for importing goods"],
    )

    snippet: str = Field(
        ...,
        max_length=2500,
        description="The retrieved text chunk used to ground the answer.",
    )

    similarity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Similarity between the chunk and query. 1.0 = identical.",
    )


class Answer(BaseModel):
    """
    Grounded RAG response.

    answered=True:
        A grounded answer was produced and citations contain the
        knowledge-base sources used.

    answered=False:
        The knowledge base did not provide enough applicable evidence.
    """

    answered: bool = Field(
        ...,
        description=(
            "True when a grounded answer was generated. "
            "False when the system declined."
        ),
    )

    text: str = Field(
        ...,
        description="Grounded answer text or decline message.",
    )

    citations: list[Citation] = Field(
        default_factory=list,
        description=(
            "Knowledge-base chunks used to ground the answer. "
            "Empty when answered is False."
        ),
    )