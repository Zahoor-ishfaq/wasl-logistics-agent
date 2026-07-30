"""
app/models/answer.py

Pydantic schemas for the RAG answer response.

Every answer the system returns must either:
  - Cite the exact document chunks it drew from, OR
  - Explicitly decline (when no relevant context was found)

This enforces the grounding rule from FR-2: the LLM never answers
from general knowledge without retrieved context.
"""

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """
    A single source chunk that contributed to an answer.

    Each Citation tells the reader exactly where the answer came from —
    which document, which section, and the exact text that was used.
    This makes answers verifiable: the ops agent can open the source
    document and check the claim themselves.

    Example:
        {
            "source": "customs_procedure.md",
            "section": "Required documentation for importing goods",
            "snippet": "The customs declaration must be submitted electronically
                        no later than 24 hours before the goods arrive...",
            "similarity_score": 0.87
        }
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
        max_length=500,
        description="The relevant text from the chunk. Truncated to 500 chars.",
    )

    similarity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="How similar this chunk was to the query. 1.0 = identical.",
    )


class Answer(BaseModel):
    """
    The full response returned by the /answer endpoint.

    Two possible states:
      1. Grounded answer  — text contains the answer, citations is non-empty
      2. Decline          — answered is False, text explains why, citations is empty

    The LLM is never called when answered is False — no context means no answer.

    Example (grounded):
        {
            "answered": true,
            "text": "The customs declaration must be submitted at least 24 hours
                     before the goods arrive at the port, per ZATCA rules.",
            "citations": [
                {
                    "source": "customs_procedure.md",
                    "section": "Pre-clearance",
                    "snippet": "...submitted electronically no later than 24 hours...",
                    "similarity_score": 0.91
                }
            ]
        }

    Example (decline):
        {
            "answered": false,
            "text": "I don't have information about that in the knowledge base.",
            "citations": []
        }
    """

    answered: bool = Field(
        ...,
        description=(
            "True if the system found relevant context and generated an answer. "
            "False if no relevant chunks were found and the question was declined."
        ),
    )

    text: str = Field(
        ...,
        description="The answer text, or a decline message if answered is False.",
    )

    citations: list[Citation] = Field(
        default_factory=list,
        description=(
            "The document chunks used to generate this answer. "
            "Empty when answered is False."
        ),
    )
