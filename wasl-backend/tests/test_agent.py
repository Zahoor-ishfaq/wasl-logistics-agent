"""
tests/test_agent.py

Tests the agent graph's routing with the LLM MOCKED, so they're fast,
free, and deterministic. We check the three critical paths:
  - an actionable exception -> pauses at the approval gate with a draft
  - a holiday closure -> no action (stands down)
  - a not-found shipment -> clean stop
"""

from unittest.mock import patch

import app.agent.nodes as nodes
import app.tools.draft_message as dm
from app.agent.graph import build_graph
from app.models.answer import Citation
from app.models.state import AgentState


class _FakeLLM:
    """Returns ACTION/NO_ACTION for the assess node, prose otherwise."""

    def __init__(self, decision="ACTION"):
        self.decision = decision

    def complete(self, prompt, system=None):
        if "ACTION or NO_ACTION" in prompt:
            return self.decision
        return "Drafted message body for test."


_FAKE_CITES = [
    Citation(
        source="delayed_shipments_policy.md",
        section="Cat A",
        snippet="...",
        similarity_score=0.7,
    )
]


def _run(shipment_id, decision):
    graph = build_graph()
    llm = _FakeLLM(decision)
    with (
        patch.object(nodes, "get_llm_service", lambda: llm),
        patch.object(dm, "get_llm_service", lambda: llm),
        patch.object(nodes, "policy_search", lambda **k: _FAKE_CITES),
    ):
        cfg = {"configurable": {"thread_id": f"test-{shipment_id}-{decision}"}}
        graph.invoke(AgentState(shipment_id=shipment_id), cfg)
        return graph, cfg


class TestAgentRouting:
    def test_actionable_exception_pauses_with_draft(self):
        graph, cfg = _run("WSL-20260310-0042", "ACTION")
        snap = graph.get_state(cfg)
        assert snap.values["drafted_action"] is not None
        assert snap.values["drafted_action"].recipient_type == "internal"
        # paused before the approval gate
        assert snap.next == ("approval_gate",)

    def test_holiday_closure_takes_no_action(self):
        graph, cfg = _run("WSL-20260318-0088", "NO_ACTION")
        snap = graph.get_state(cfg)
        assert snap.values.get("drafted_action") is None
        assert snap.values["summary"]
        assert snap.next == ()  # reached END

    def test_not_found_stops_cleanly(self):
        graph, cfg = _run("WSL-NOPE-9999", "ACTION")
        snap = graph.get_state(cfg)
        assert snap.values["shipment_found"] is False
        assert snap.values.get("drafted_action") is None
        assert snap.next == ()

    def test_approve_resumes_and_finalizes(self):
        graph, cfg = _run("WSL-20260310-0042", "ACTION")
        snap = graph.get_state(cfg)
        draft = snap.values["drafted_action"]
        draft.approved = True
        graph.update_state(cfg, {"drafted_action": draft})
        final = graph.invoke(None, cfg)
        assert final["approval_status"] == "approved"
        assert final["completed_at"] is not None
