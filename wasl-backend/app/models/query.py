"""
app/models/query.py

Pydantic schema for incoming user questions to the RAG answer endpoint.
"""

from pydantic import BaseModel, Field


class Question(BaseModel):
    """
    Represents a question submitted by an ops agent to the /answer endpoint.

    Example:
        {
            "text": "What documents are required to import goods into Saudi Arabia?",
            "top_k": 5
        }
    """

    text: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="The question text. Must be at least 3 characters.",
        examples=["What is the re-delivery policy after a failed delivery attempt?"],
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of document chunks to retrieve. Defaults to 5.",
    )