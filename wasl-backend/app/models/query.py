"""
app/models/query.py

Pydantic schema for incoming user questions to the RAG answer endpoint.
"""

from pydantic import BaseModel, Field


class ConversationTurn(BaseModel):
    """
    A small amount of recent conversation context.

    This is session-only context supplied by the frontend.
    It is not stored permanently by this model.
    """

    role: str = Field(
        ...,
        pattern="^(user|assistant)$",
        description="Conversation role: user or assistant.",
    )

    text: str = Field(
        ...,
        min_length=1,
        max_length=1200,
        description="Text from a recent conversation turn.",
    )


class Question(BaseModel):
    """
    Represents a question submitted by an ops agent to the /answer endpoint.

    Example:
        {
            "text": "What documents are required to import goods into Saudi Arabia?",
            "top_k": 5,
            "history": [
                {
                    "role": "user",
                    "text": "A shipment has been held at customs for 26 hours."
                },
                {
                    "role": "assistant",
                    "text": "The internal SOP requires Operations Manager review after 24 hours."
                }
            ]
        }
    """

    text: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The current user question.",
        examples=["What should we do next?"],
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of document chunks to retrieve. Defaults to 5.",
    )

    history: list[ConversationTurn] = Field(
        default_factory=list,
        max_length=4,
        description=(
            "Up to 4 recent conversation turns used only for current-session "
            "follow-up context."
        ),
    )