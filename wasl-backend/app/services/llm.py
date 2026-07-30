"""
app/services/llm.py

A thin wrapper around the Claude LLM (via langchain-anthropic).

Why a wrapper instead of calling ChatAnthropic directly everywhere?

  1. Single source of truth — model, temperature, and max_tokens are
     configured once, here, from settings. No scattered magic values.

  2. Cost tracking — every call runs through one place, so we can
     enforce the daily cost cap (ADR / threat model requirement) and
     later attach Langfuse tracing in exactly one spot.

  3. Testability — tests can mock this one service instead of patching
     the Anthropic SDK across the whole codebase.

  4. Swappability — if we ever change providers or add fallback models,
     only this file changes; the RAG service, agent, and tools don't.

The rest of the app should NEVER import ChatAnthropic directly.
It should import get_llm_service() from here.
"""

from datetime import date

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from app.config import settings


class DailyCostCapExceeded(Exception):
    """
    Raised when the day's LLM spend has hit the configured cap.

    The API layer catches this and returns a 503, so a runaway loop
    or a flood of requests cannot silently drain the budget overnight.
    """


# Approximate Claude Sonnet pricing (USD per million tokens).
# These are used ONLY for the internal budget guard — not billing.
# Update if pricing changes; the guard is a safety net, not accounting.
_PRICE_PER_MTOK_INPUT = 3.0
_PRICE_PER_MTOK_OUTPUT = 15.0


class LLMService:
    """
    Wraps a single ChatAnthropic client and adds cost tracking.

    Public methods:
        complete(prompt, system=...) -> str
            One-shot: send a prompt, get text back.

        chat(messages) -> str
            Send a list of LangChain messages, get text back.

        get_chat_model() -> ChatAnthropic
            Return the underlying model — needed by LangGraph and by
            tools that use .bind_tools(). Cost tracking is bypassed
            for this path, so use complete()/chat() where possible.
    """

    def __init__(self) -> None:
        self._model = ChatAnthropic(
            model=settings.anthropic_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            api_key=settings.anthropic_api_key,
            timeout=60,
            max_retries=2,
        )

        # Simple in-memory daily cost tracker.
        # Resets automatically when the date rolls over.
        # NOTE: this is per-process. In a multi-instance deployment
        # you'd move this to Redis or a shared store — noted as a
        # known limitation, acceptable for v1 / single instance.
        self._tracked_date: date = date.today()
        self._spend_today_usd: float = 0.0

    # ------------------------------------------------------------------
    # Cost guard
    # ------------------------------------------------------------------
    def _roll_over_if_new_day(self) -> None:
        today = date.today()
        if today != self._tracked_date:
            self._tracked_date = today
            self._spend_today_usd = 0.0

    def _check_budget(self) -> None:
        """Raise if we've already exceeded today's cap. Cap of 0 disables the guard."""
        if settings.llm_daily_cost_cap_usd <= 0:
            return
        self._roll_over_if_new_day()
        if self._spend_today_usd >= settings.llm_daily_cost_cap_usd:
            raise DailyCostCapExceeded(
                f"Daily LLM cost cap of "
                f"${settings.llm_daily_cost_cap_usd:.2f} reached. "
                f"Requests are paused until tomorrow (UTC)."
            )

    def _record_usage(self, response: BaseMessage) -> None:
        """Add the cost of one response to today's running total."""
        if settings.llm_daily_cost_cap_usd <= 0:
            return
        usage = getattr(response, "usage_metadata", None) or {}
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        cost = (
            input_tokens / 1_000_000 * _PRICE_PER_MTOK_INPUT
            + output_tokens / 1_000_000 * _PRICE_PER_MTOK_OUTPUT
        )
        self._spend_today_usd += cost

    @property
    def spend_today_usd(self) -> float:
        """Current day's estimated spend — useful for a /health or debug endpoint."""
        self._roll_over_if_new_day()
        return round(self._spend_today_usd, 4)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def complete(self, prompt: str, system: str | None = None) -> str:
        """
        Send a single prompt (optionally with a system message) and
        return the model's text response.

        This is the method RAG and most tools should use.

        Args:
            prompt: The user prompt.
            system: Optional system message to steer behavior.

        Returns:
            The model's response as a plain string.

        Raises:
            DailyCostCapExceeded: if today's budget is exhausted.
        """
        self._check_budget()

        messages: list[BaseMessage] = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))

        response = self._model.invoke(messages)
        self._record_usage(response)

        text = self._text_of(response)

        # Observability: record this call as a Langfuse generation.
        # No-op if Langfuse isn't configured.
        try:
            from app.observability.tracing import trace_generation

            usage = getattr(response, "usage_metadata", None) or {}
            trace_generation(
                name="llm.complete",
                model=settings.anthropic_model,
                prompt=prompt
                if not system
                else f"[system]\n{system}\n\n[user]\n{prompt}",
                response=text,
                input_tokens=usage.get("input_tokens"),
                output_tokens=usage.get("output_tokens"),
            )
        except Exception:
            pass  # tracing must never break the request

        return text

    def chat(self, messages: list[BaseMessage]) -> str:
        """
        Send a full list of LangChain messages and return text.

        Use this when you need multi-turn context or a custom
        message sequence rather than a single prompt.
        """
        self._check_budget()
        response = self._model.invoke(messages)
        self._record_usage(response)
        return self._text_of(response)

    def get_chat_model(self) -> ChatAnthropic:
        """
        Return the underlying ChatAnthropic model.

        Needed by LangGraph nodes and by tools that call
        .bind_tools(). Note: cost tracking does NOT apply to calls
        made directly through this model, so prefer complete()/chat()
        wherever a plain text response is enough.
        """
        return self._model

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _text_of(response: BaseMessage) -> str:
        """
        Extract plain text from a LangChain response.

        Claude responses can be a string or a list of content blocks
        (text, tool calls, etc). For our text-completion use cases we
        join the text blocks and return a clean string.
        """
        content = response.content
        if isinstance(content, str):
            return content.strip()
        # content is a list of blocks
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts).strip()


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    """
    Return the shared LLMService instance.

    We build it lazily (on first use) rather than at import time so
    that importing this module never triggers a client build or
    requires the API key to be present — which keeps tests and tooling
    that don't hit the LLM fast and dependency-free.
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
