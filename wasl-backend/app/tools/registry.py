"""
app/tools/registry.py

Central registry of all agent tools.

This is the one place that lists every tool the agent can use. The
graph imports from here rather than importing each tool individually,
so adding a new tool is a one-line change in this file.

Two things are exposed:

  TOOLS
      A simple name -> function mapping. Useful for tests, for a tool
      catalogue in the UI, and for any code that needs to look a tool
      up by name.

  TOOL_SPECS
      Lightweight metadata about each tool (name + one-line purpose).
      Handy for logging, documentation, and showing "what can this
      agent do" without importing the functions.

Note on binding to the LLM:
  In this project the agent nodes call these tools directly in code
  (deterministic control flow via LangGraph), rather than letting the
  LLM free-form choose tools via function-calling. That's a deliberate
  scoping decision — the graph defines the possible paths; the LLM
  makes the judgment calls at specific nodes. This registry therefore
  exists for organization and discoverability, not for LLM tool-binding.
  If you later switch to LLM-driven tool selection, this is where you'd
  build the bind_tools() list.
"""

from collections.abc import Callable

from app.tools.compute_eta import compute_eta
from app.tools.draft_message import draft_message
from app.tools.policy_search import policy_search
from app.tools.shipment_lookup import shipment_lookup


# name -> callable
TOOLS: dict[str, Callable] = {
    "shipment_lookup": shipment_lookup,
    "compute_eta": compute_eta,
    "policy_search": policy_search,
    "draft_message": draft_message,
}


# Lightweight, importable metadata about each tool.
TOOL_SPECS: list[dict[str, str]] = [
    {
        "name": "shipment_lookup",
        "purpose": "Look up a shipment by its reference ID.",
    },
    {
        "name": "compute_eta",
        "purpose": "Calculate SLA breach status, excluding holiday closure days.",
    },
    {
        "name": "policy_search",
        "purpose": "Retrieve the policy that governs a given exception type.",
    },
    {
        "name": "draft_message",
        "purpose": "Draft a message for human approval (never sends).",
    },
]


def get_tool(name: str) -> Callable:
    """
    Return a tool callable by name.

    Raises KeyError with a helpful message if the name is unknown.
    """
    if name not in TOOLS:
        available = ", ".join(sorted(TOOLS))
        raise KeyError(f"Unknown tool '{name}'. Available tools: {available}")
    return TOOLS[name]


def list_tools() -> list[str]:
    """Return the names of all registered tools."""
    return sorted(TOOLS.keys())