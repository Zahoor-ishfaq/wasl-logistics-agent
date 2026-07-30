"""
app/agent/graph.py

Wires the investigation nodes into a LangGraph state machine and
compiles it with a human-in-the-loop interrupt at the approval gate.

The shape (see nodes.py for what each node does):

    START
      -> initialize
      -> lookup_shipment
      -> [found?]  no  -> summarize_and_stop -> END
                   yes -> assess_exception
      -> [exception?] no  -> summarize_and_stop -> END
                      yes -> retrieve_policy_and_sla
                          -> build_assessment
                          -> draft_action
                          -> (INTERRUPT — wait for human)
                          -> approval_gate
                          -> finalize -> END

Two conditional branches (found? / exception?) and one interrupt
(before approval_gate). Persistence via a checkpointer is REQUIRED
for the interrupt to work — the graph saves state, stops, and resumes
exactly where it left off when the human decides.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agent.nodes import (
    approval_gate,
    assess_exception,
    build_assessment,
    draft_action,
    finalize,
    initialize,
    lookup_shipment,
    retrieve_policy_and_sla,
    summarize_and_stop,
)
from app.models.state import AgentState


# ---------------------------------------------------------------------------
# Conditional routing functions
# ---------------------------------------------------------------------------
def _route_after_lookup(state: AgentState) -> str:
    """After lookup: proceed if the shipment was found, else stop."""
    return "assess_exception" if state.shipment_found else "summarize_and_stop"


def _route_after_assess(state: AgentState) -> str:
    """After assessment: investigate if an exception needs action, else stop."""
    return (
        "retrieve_policy_and_sla" if state.exception_detected else "summarize_and_stop"
    )


# ---------------------------------------------------------------------------
# Build and compile the graph
# ---------------------------------------------------------------------------
def build_graph():
    """
    Construct the investigation StateGraph and compile it.

    Returns the compiled graph. The graph interrupts before
    'approval_gate', so invoking it runs up to the draft and then
    pauses; you resume it after the human decision.
    """
    builder = StateGraph(AgentState)

    # Register nodes.
    builder.add_node("initialize", initialize)
    builder.add_node("lookup_shipment", lookup_shipment)
    builder.add_node("assess_exception", assess_exception)
    builder.add_node("retrieve_policy_and_sla", retrieve_policy_and_sla)
    builder.add_node("build_assessment", build_assessment)
    builder.add_node("draft_action", draft_action)
    builder.add_node("approval_gate", approval_gate)
    builder.add_node("finalize", finalize)
    builder.add_node("summarize_and_stop", summarize_and_stop)

    # Linear start.
    builder.add_edge(START, "initialize")
    builder.add_edge("initialize", "lookup_shipment")

    # Branch 1: shipment found?
    builder.add_conditional_edges(
        "lookup_shipment",
        _route_after_lookup,
        {
            "assess_exception": "assess_exception",
            "summarize_and_stop": "summarize_and_stop",
        },
    )

    # Branch 2: exception needs action?
    builder.add_conditional_edges(
        "assess_exception",
        _route_after_assess,
        {
            "retrieve_policy_and_sla": "retrieve_policy_and_sla",
            "summarize_and_stop": "summarize_and_stop",
        },
    )

    # Investigation path.
    builder.add_edge("retrieve_policy_and_sla", "build_assessment")
    builder.add_edge("build_assessment", "draft_action")
    builder.add_edge("draft_action", "approval_gate")
    builder.add_edge("approval_gate", "finalize")

    # Terminal edges.
    builder.add_edge("finalize", END)
    builder.add_edge("summarize_and_stop", END)

    # Compile with a checkpointer (required for interrupts) and an
    # interrupt BEFORE the approval gate — this is the human-in-the-loop
    # pause. Execution stops after draft_action, before approval_gate.
    checkpointer = MemorySaver()
    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["approval_gate"],
    )


# Module-level singleton. Import this to run investigations.
investigation_graph = build_graph()
