"""
app/api/security.py

Input-safety guards for user-supplied text (RAG questions, uploads).

What this defends against:
  - Prompt injection: user text trying to override the system prompt
    ("ignore previous instructions", "you are now...", etc.). We don't
    rely on detection alone — the RAG prompt already isolates user text
    with role markers — but flagging the most blatant patterns lets us
    reject obvious attacks early and log them.
  - Oversized input: a very long question is either abuse or a mistake;
    cap it before it reaches the model.
  - Empty / whitespace-only input.

This is defense-in-depth, not a silver bullet. The real guarantee is
structural (grounded prompt + no tool can send anything without human
approval). These checks reduce noise and stop the obvious cases.
"""

from __future__ import annotations

import re

from fastapi import HTTPException, status

# Blatant prompt-injection phrases. Case-insensitive substring match.
# Kept deliberately short — high-precision patterns, not a keyword dragnet.
_INJECTION_PATTERNS = [
    r"ignore (all |your |the )?(previous|prior|above) (instructions|prompts?)",
    r"disregard (all |your |the )?(previous|prior|above)",
    r"you are now (a|an|the)\b",
    r"forget (everything|all|your instructions)",
    r"system prompt",
    r"reveal (your |the )?(system )?(prompt|instructions)",
    r"</?(system|assistant|user)>",   # fake role tags
]

_MAX_QUESTION_CHARS = 2000


def sanitize_question(text: str) -> str:
    """
    Validate and lightly clean a user question.

    Raises HTTPException(400) on empty or oversized input, or when a
    blatant prompt-injection pattern is detected. Returns the trimmed
    text on success.
    """
    cleaned = (text or "").strip()

    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question must not be empty.",
        )

    if len(cleaned) > _MAX_QUESTION_CHARS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Question too long (max {_MAX_QUESTION_CHARS} characters).",
        )

    lowered = cleaned.lower()
    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Input rejected: it looks like an attempt to manipulate the assistant.",
            )

    return cleaned