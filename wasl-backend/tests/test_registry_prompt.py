import pytest

from app.rag.prompt import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_context,
    build_user_prompt,
)
from app.tools.registry import TOOL_SPECS, TOOLS, get_tool, list_tools


def test_registry_lists_all_tools():
    assert list_tools() == sorted(TOOLS.keys())
    assert {item["name"] for item in TOOL_SPECS} == set(TOOLS.keys())


@pytest.mark.parametrize("name", list(TOOLS.keys()))
def test_get_tool_returns_registered_callable(name):
    assert get_tool(name) is TOOLS[name]
    assert callable(get_tool(name))


def test_get_tool_rejects_unknown_name():
    with pytest.raises(KeyError) as error:
        get_tool("missing_tool")

    message = str(error.value)

    assert "Unknown tool 'missing_tool'" in message
    assert "compute_eta" in message
    assert "draft_message" in message
    assert "policy_search" in message
    assert "shipment_lookup" in message


def test_build_context_without_citations():
    assert build_context([]) == "(no sources found)"


def test_build_context_formats_citations(fake_citations):
    context = build_context(fake_citations)

    assert "[SOURCE 1]" in context
    assert "Document: customs_procedure.md" in context
    assert "Section: Required documentation" in context
    assert "A SASO certificate is required." in context

    assert "[SOURCE 2]" in context
    assert "Document: delayed_shipments_policy.md" in context
    assert "Section: Category A" in context
    assert "Customs holds must be reported within one hour." in context


def test_build_user_prompt_contains_question_and_sources(fake_citations):
    prompt = build_user_prompt(
        "What document is required?",
        fake_citations,
    )

    assert "<conversation_context>" in prompt
    assert "</conversation_context>" in prompt

    assert "<sources>" in prompt
    assert "</sources>" in prompt

    assert "<question>" in prompt
    assert "</question>" in prompt

    assert "What document is required?" in prompt
    assert "customs_procedure.md" in prompt
    assert "A SASO certificate is required." in prompt


def test_build_user_prompt_without_history(fake_citations):
    prompt = build_user_prompt(
        "What document is required?",
        fake_citations,
        history=None,
    )

    assert "(no previous conversation)" in prompt


def test_prompt_constants_are_defined():
    assert PROMPT_VERSION == "v3"

    assert "ONLY" in SYSTEM_PROMPT
    assert "<sources>" in SYSTEM_PROMPT

    # v3 source-applicability protections.
    assert "SOURCE APPLICABILITY" in SYSTEM_PROMPT
    assert "DO NOT TRANSFER RULES BETWEEN INCIDENT TYPES" in SYSTEM_PROMPT
    assert "NO UNSUPPORTED INFERENCE" in SYSTEM_PROMPT
    assert "Conversation context is NOT evidence" in SYSTEM_PROMPT or (
        "CONVERSATION IS NOT EVIDENCE" in SYSTEM_PROMPT
    )