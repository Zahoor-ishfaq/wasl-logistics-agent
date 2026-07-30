"""
app/agent/nodes.py

The nodes of the investigation graph. Each node is a function that
takes the current AgentState, does one step of work (usually calling
a tool), and returns the updated state.

Nodes never talk to each other directly. They only read and write
AgentState. The graph (graph.py) decides the order they run in.

The nine nodes:
    initialize              set up the run
    lookup_shipment         call shipment_lookup tool
    assess_exception        LLM decides if there's a real exception
    retrieve_policy_and_sla call policy_search + compute_eta tools
    build_assessment        LLM synthesizes the situation
    draft_action            call draft_message tool
    approval_gate           marker node — graph interrupts BEFORE it
    finalize                record the human's decision
    summarize_and_stop      no-exception path — explain and end

Design note: assess_exception and build_assessment are where the LLM
makes judgments. Every other node is deterministic tool-calling. This
is the "single agentic workflow" scoping — the graph defines the paths,
the LLM decides at two specific points.
"""

import uuid
from datetime import datetime, timezone

from app.observability.tracing import observe
from app.models.shipment import ExceptionType, Shipment, ShipmentNotFound
from app.models.state import (
    AgentState,
    ApprovalStatus,
    Assessment,
    RetrievedPolicy,
)
from app.services.llm import get_llm_service
from app.tools.compute_eta import compute_eta
from app.tools.draft_message import draft_message
from app.tools.policy_search import policy_search
from app.tools.shipment_lookup import shipment_lookup


# Maps each exception type to the recipient the drafted action should
# go to. Decided in code, not by the LLM — a deliberate control boundary.
_RECIPIENT_BY_EXCEPTION: dict[ExceptionType, tuple[str, str]] = {
    ExceptionType.customs_hold: ("internal", "Compliance / Operations Team"),
    ExceptionType.cross_border: ("customer", "Customer Service"),
    ExceptionType.supplier_delay: ("vendor", "Supplier Account Manager"),
    ExceptionType.carrier_delay: ("customer", "Customer Service"),
    ExceptionType.failed_delivery: ("customer", "Customer Service"),
}


# ---------------------------------------------------------------------------
# Node: initialize
# ---------------------------------------------------------------------------
def initialize(state: AgentState) -> AgentState:
    """Set up the investigation run: assign an id and a start time."""
    state.investigation_id = state.investigation_id or f"inv-{uuid.uuid4().hex[:12]}"
    state.started_at = datetime.now(timezone.utc)
    state.add_trace("initialize", "start", f"Investigating {state.shipment_id}")
    return state


# ---------------------------------------------------------------------------
# Node: lookup_shipment
# ---------------------------------------------------------------------------
@observe("lookup_shipment")
def lookup_shipment(state: AgentState) -> AgentState:
    """Call the shipment_lookup tool and store the result."""
    result = shipment_lookup(state.shipment_id)

    if isinstance(result, ShipmentNotFound):
        state.shipment_found = False
        state.add_trace(
            "lookup_shipment", "not_found",
            f"No shipment found for {state.shipment_id}",
        )
        return state

    state.shipment = result
    state.shipment_found = True
    state.add_trace(
        "lookup_shipment", "found",
        f"status={result.status.value}, exception={result.exception_type.value}",
    )
    return state


# ---------------------------------------------------------------------------
# Node: assess_exception  (LLM judgment)
# ---------------------------------------------------------------------------
@observe("assess_exception")
def assess_exception(state: AgentState) -> AgentState:
    """
    Decide whether this shipment has a real, actionable exception.

    The shipment record already carries an exception_type, but this node
    uses the LLM to make a judgment: is this something that needs action,
    or is it an expected situation (e.g. a holiday delay) that should be
    acknowledged and closed?

    Sets state.exception_detected and state.exception_type.
    """
    shipment = state.shipment
    if shipment is None:
        state.exception_detected = False
        return state

    # Holiday closure is the key "expected, do not escalate" case.
    # We still let the LLM confirm, but frame the decision clearly.
    system = (
        "You are a logistics operations analyst. Decide whether a "
        "shipment situation needs an operational action (escalation, "
        "customer notice, or vendor notice), or whether it is an expected "
        "situation that needs no action beyond acknowledgement.\n"
        "Answer with exactly one word: ACTION or NO_ACTION."
    )
    prompt = (
        f"Shipment {shipment.shipment_id}\n"
        f"Status: {shipment.status.value}\n"
        f"Exception type: {shipment.exception_type.value}\n"
        f"Detail: {shipment.exception_detail}\n\n"
        "A holiday closure delay that is already reflected in the delivery "
        "schedule is NO_ACTION. A customs hold, unexplained cross-border "
        "hold, supplier failure, or carrier delay that risks the SLA is "
        "ACTION.\n\n"
        "Does this need an operational action? Answer ACTION or NO_ACTION."
    )

    decision = get_llm_service().complete(prompt=prompt, system=system).strip().upper()
    needs_action = "ACTION" in decision and "NO_ACTION" not in decision

    state.exception_type = shipment.exception_type
    state.exception_detected = needs_action

    state.add_trace(
        "assess_exception", "decision",
        f"{shipment.exception_type.value} -> "
        f"{'ACTION' if needs_action else 'NO_ACTION'}",
    )
    return state


# ---------------------------------------------------------------------------
# Node: retrieve_policy_and_sla
# ---------------------------------------------------------------------------
def retrieve_policy_and_sla(state: AgentState) -> AgentState:
    """Call policy_search and compute_eta tools to gather grounding."""
    shipment = state.shipment
    if shipment is None:
        return state

    # Policy governing this exception type.
    citations = policy_search(
        exception_type=state.exception_type,
        extra_context=shipment.exception_detail[:200],
        top_k=3,
    )
    state.retrieved_policy = RetrievedPolicy(
        exception_type=state.exception_type,
        citations=citations,
        summary="",
    )
    state.add_trace(
        "retrieve_policy_and_sla", "policy",
        f"retrieved {len(citations)} policy chunk(s)",
    )

    # SLA breach status.
    state.sla_status = compute_eta(shipment)
    if state.sla_status.sla_applies:
        if state.sla_status.already_breached:
            sla_msg = "SLA already breached"
        else:
            sla_msg = f"{state.sla_status.hours_until_breach}h until breach"
    else:
        sla_msg = "no SLA"
    state.add_trace("retrieve_policy_and_sla", "sla", sla_msg)

    return state


# ---------------------------------------------------------------------------
# Node: build_assessment  (LLM synthesis)
# ---------------------------------------------------------------------------
def build_assessment(state: AgentState) -> AgentState:
    """
    Synthesize everything gathered into a structured Assessment.

    Uses the LLM to write a clear plain-language summary, then derives
    urgency and the recommended action type from the SLA status and
    exception type (derived in code, not left to the model).
    """
    shipment = state.shipment
    if shipment is None:
        return state

    policy_text = ""
    if state.retrieved_policy and state.retrieved_policy.citations:
        policy_text = "\n".join(
            f"- ({c.source}) {c.snippet[:200]}"
            for c in state.retrieved_policy.citations
        )

    sla = state.sla_status
    if sla and sla.sla_applies:
        sla_text = (
            "already breached" if sla.already_breached
            else f"{sla.hours_until_breach} hours until breach"
        )
    else:
        sla_text = "no SLA applies"

    system = (
        "You are a logistics operations analyst. Write a concise, factual "
        "assessment (3-5 sentences) of the shipment exception for an ops "
        "agent. State what happened, what the policy requires, and the SLA "
        "position. Do not invent facts. Do not recommend a specific message "
        "yet — just assess."
    )
    prompt = (
        f"Shipment: {shipment.shipment_id}\n"
        f"Exception: {shipment.exception_type.value}\n"
        f"Detail: {shipment.exception_detail}\n"
        f"Route: {shipment.origin} -> {shipment.destination}\n"
        f"SLA: {sla_text}\n\n"
        f"Relevant policy:\n{policy_text or '(none retrieved)'}\n\n"
        "Write the assessment now."
    )
    summary = get_llm_service().complete(prompt=prompt, system=system)

    # Derive urgency from SLA status (code, not LLM).
    urgency = "medium"
    if sla and sla.sla_applies:
        if sla.already_breached:
            urgency = "critical"
        elif sla.hours_until_breach is not None and sla.hours_until_breach <= 12:
            urgency = "high"
        elif sla.hours_until_breach is not None and sla.hours_until_breach <= 48:
            urgency = "medium"
        else:
            urgency = "low"

    # Derive recommended action type from exception type (code, not LLM).
    recipient_type, _ = _RECIPIENT_BY_EXCEPTION.get(
        state.exception_type, ("internal", "Operations Team")
    )
    action_type = {
        "internal": "internal_escalation",
        "customer": "customer_notice",
        "vendor": "vendor_notice",
    }[recipient_type]

    state.assessment = Assessment(
        exception_type=state.exception_type,
        summary=summary,
        urgency=urgency,
        recommended_action_type=action_type,
        sla_status=sla,
    )
    state.add_trace("build_assessment", "assessment", f"urgency={urgency}")
    return state


# ---------------------------------------------------------------------------
# Node: draft_action
# ---------------------------------------------------------------------------
def draft_action(state: AgentState) -> AgentState:
    """Call the draft_message tool to produce a proposed action."""
    shipment = state.shipment
    if shipment is None:
        return state

    recipient_type, recipient_label = _RECIPIENT_BY_EXCEPTION.get(
        state.exception_type, ("internal", "Operations Team")
    )

    policy_citations = (
        state.retrieved_policy.citations if state.retrieved_policy else []
    )

    state.drafted_action = draft_message(
        shipment=shipment,
        recipient_type=recipient_type,
        recipient_label=recipient_label,
        sla_status=state.sla_status,
        policy_citations=policy_citations,
    )
    state.approval_status = ApprovalStatus.PENDING
    state.add_trace(
        "draft_action", "drafted",
        f"{recipient_type} message to {recipient_label}",
    )
    return state


# ---------------------------------------------------------------------------
# Node: approval_gate
# ---------------------------------------------------------------------------
def approval_gate(state: AgentState) -> AgentState:
    """
    Marker node. The graph is compiled to interrupt BEFORE this node,
    so execution pauses here until a human resumes it.

    When resumed, the human's decision has already been written into
    state.drafted_action.approved (via graph.update_state), so this
    node simply records that the gate was passed.
    """
    state.add_trace("approval_gate", "resumed", "human decision received")
    return state


# ---------------------------------------------------------------------------
# Node: finalize
# ---------------------------------------------------------------------------
def finalize(state: AgentState) -> AgentState:
    """Record the human's approve/reject decision and close the run."""
    action = state.drafted_action
    if action is not None and action.approved is True:
        state.approval_status = ApprovalStatus.APPROVED
        note = "approved"
    elif action is not None and action.approved is False:
        state.approval_status = ApprovalStatus.REJECTED
        note = f"rejected: {action.rejection_reason or 'no reason given'}"
    else:
        state.approval_status = ApprovalStatus.PENDING
        note = "no decision recorded"

    state.completed_at = datetime.now(timezone.utc)
    state.add_trace("finalize", "closed", note)
    return state


# ---------------------------------------------------------------------------
# Node: summarize_and_stop  (no-exception path)
# ---------------------------------------------------------------------------
def summarize_and_stop(state: AgentState) -> AgentState:
    """
    Terminal node for the no-action path: shipment not found, or no
    actionable exception (e.g. an expected holiday delay).

    Writes a plain-language summary so the ops agent understands why no
    action was taken. No draft is produced.
    """
    if not state.shipment_found:
        state.summary = (
            f"No shipment was found with reference {state.shipment_id}. "
            "Please check the reference and try again."
        )
    elif state.shipment is not None:
        shipment = state.shipment
        if shipment.exception_type == ExceptionType.holiday_closure:
            state.summary = (
                f"Shipment {shipment.shipment_id} is delayed due to a Saudi "
                f"public holiday closure. This is expected and already "
                f"reflected in the delivery schedule. No action is required "
                f"— the delay does not count as an SLA breach."
            )
        else:
            state.summary = (
                f"Shipment {shipment.shipment_id} (status: "
                f"{shipment.status.value}) shows no exception requiring "
                f"action. No escalation or notice is needed at this time."
            )

    state.completed_at = datetime.now(timezone.utc)
    state.add_trace("summarize_and_stop", "summary", "no action required")
    return state