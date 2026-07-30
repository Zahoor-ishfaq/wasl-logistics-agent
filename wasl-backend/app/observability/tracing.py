"""
app/observability/tracing.py

Observability via Langfuse (ADR-0005). Wraps LLM calls and agent nodes
so every investigation produces a full timeline in the Langfuse
dashboard: per-step latency, token counts, cost, and the exact prompt
and response for each generation.

Design principles:
  - Degrade gracefully. If Langfuse keys aren't configured, tracing is
    a no-op and the app runs exactly as before. Observability must
    never be a hard dependency for the system to function.
  - Scrub secrets before they leave the process (threat T4). Known
    patterns — API keys, emails, phone numbers, long digit runs — are
    redacted from anything sent to Langfuse.

Public surface:
  - is_enabled()            -> bool
  - observe                 -> decorator to trace a function as a span
  - trace_generation(...)   -> record one LLM call (prompt/response/usage)
  - scrub(text)             -> redact secret patterns from a string
  - update_trace(**kw)      -> attach ids/metadata to the current trace
  - flush()                 -> force-send buffered events (short scripts)
"""

from __future__ import annotations

import functools
import re
from typing import Any, Callable

from app.config import settings


# ---------------------------------------------------------------------------
# Client bootstrap (lazy, optional)
# ---------------------------------------------------------------------------
_client = None
_initialized = False


def _get_client():
    """Return a Langfuse client, or None if not configured/available."""
    global _client, _initialized
    if _initialized:
        return _client
    _initialized = True

    pub = getattr(settings, "langfuse_public_key", "") or ""
    sec = getattr(settings, "langfuse_secret_key", "") or ""
    if not pub or not sec:
        _client = None
        return None

    try:
        from langfuse import get_client
        # The SDK reads keys from env vars; ensure they're present.
        import os
        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", pub)
        os.environ.setdefault("LANGFUSE_SECRET_KEY", sec)
        os.environ.setdefault(
            "LANGFUSE_HOST",
            getattr(settings, "langfuse_host", "https://cloud.langfuse.com"),
        )
        _client = get_client()
    except Exception as exc:  # noqa: BLE001
        print(f"[tracing] Langfuse unavailable, tracing disabled: {exc}")
        _client = None
    return _client


def is_enabled() -> bool:
    """True if Langfuse is configured and the client initialized."""
    return _get_client() is not None


def flush() -> None:
    """Force-send buffered events. Call at the end of short-lived scripts."""
    client = _get_client()
    if client is not None:
        try:
            client.flush()
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# Secret scrubber (threat T4)
# ---------------------------------------------------------------------------
_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"sk-ant-[A-Za-z0-9\-_]{10,}"), "[REDACTED_ANTHROPIC_KEY]"),
    (re.compile(r"sk-lf-[A-Za-z0-9\-_]{6,}"), "[REDACTED_LANGFUSE_KEY]"),
    (re.compile(r"pk-lf-[A-Za-z0-9\-_]{6,}"), "[REDACTED_LANGFUSE_KEY]"),
    (re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"), "[REDACTED_EMAIL]"),
    # Phone numbers: +country and 9+ digit runs (covers Saudi +9665XXXXXXXX)
    (re.compile(r"\+\d[\d\s\-]{8,}\d"), "[REDACTED_PHONE]"),
    (re.compile(r"\b\d{9,}\b"), "[REDACTED_NUMBER]"),
]


def scrub(text: Any) -> Any:
    """
    Redact known secret patterns from a string. Non-strings pass through
    unchanged (callers may hand us dicts/objects). Best-effort: this
    reduces accidental leakage, it is not a guarantee against all PII.
    """
    if not isinstance(text, str):
        return text
    out = text
    for pattern, replacement in _PATTERNS:
        out = pattern.sub(replacement, out)
    return out


# ---------------------------------------------------------------------------
# Span decorator
# ---------------------------------------------------------------------------
def observe(name: str | None = None) -> Callable:
    """
    Decorator that traces a function as a Langfuse span (nested inside
    any active trace). If Langfuse isn't enabled, returns the function
    unchanged — zero overhead, zero behavior change.

    Usage:
        @observe("lookup_shipment")
        def lookup_shipment(state): ...
    """
    def decorator(func: Callable) -> Callable:
        if not is_enabled():
            return func

        try:
            from langfuse import observe as lf_observe
        except Exception:  # noqa: BLE001
            return func

        # Delegate to Langfuse's own decorator, naming the span.
        span_name = name or func.__name__
        wrapped = lf_observe(name=span_name)(func)

        @functools.wraps(func)
        def inner(*args, **kwargs):
            return wrapped(*args, **kwargs)

        return inner

    return decorator


# ---------------------------------------------------------------------------
# Generation recording (one LLM call)
# ---------------------------------------------------------------------------
def trace_generation(
    *,
    name: str,
    model: str,
    prompt: str,
    response: str,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    metadata: dict | None = None,
) -> None:
    """
    Record a single LLM call as a Langfuse generation, so it shows up
    with prompt, response, token usage and computed cost. Prompt and
    response are scrubbed of secrets before sending.

    No-op if Langfuse isn't enabled.
    """
    client = _get_client()
    if client is None:
        return

    try:
        usage = None
        if input_tokens is not None or output_tokens is not None:
            usage = {
                "input": input_tokens or 0,
                "output": output_tokens or 0,
                "unit": "TOKENS",
            }
        client.start_observation(
            as_type="generation",
            name=name,
            model=model,
            input=scrub(prompt),
            output=scrub(response),
            usage_details=usage,
            metadata=metadata or {},
        ).end()
    except Exception as exc:  # noqa: BLE001
        # Never let tracing break the request path.
        print(f"[tracing] generation record failed: {exc}")


def update_trace(**kwargs) -> None:
    """Attach metadata (e.g. shipment_id, trace_id) to the current trace."""
    client = _get_client()
    if client is None:
        return
    try:
        client.update_current_trace(**kwargs)
    except Exception:  # noqa: BLE001
        pass