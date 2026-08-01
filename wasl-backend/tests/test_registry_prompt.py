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

    assert "[1] (source: customs_procedure.md — Required documentation)" in context
    assert "A SASO certificate is required." in context
    assert "[2] (source: delayed_shipments_policy.md — Category A)" in context
    assert "Customs holds must be reported within one hour." in context


def test_build_user_prompt_contains_question_and_sources(fake_citations):
    prompt = build_user_prompt(
        "What document is required?",
        fake_citations,
    )

    assert "<sources>" in prompt
    assert "</sources>" in prompt
    assert "<question>" in prompt
    assert "What document is required?" in prompt
    assert "customs_procedure.md" in prompt
    assert "A SASO certificate is required." in prompt


def test_prompt_constants_are_defined():
    assert PROMPT_VERSION == "v1"
    assert "ONLY" in SYSTEM_PROMPT
    assert "<sources>" in SYSTEM_PROMPT
