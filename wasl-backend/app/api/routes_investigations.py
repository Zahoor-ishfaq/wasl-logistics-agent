"""
app/api/routes_investigations.py

The investigation endpoints — the agent, exposed over HTTP.

    POST /investigations              start an investigation (runs to the
                                      approval gate, or to a no-action stop)
    POST /investigations/{id}/approve approve or reject the drafted action

The two-call shape mirrors the human-in-the-loop design: the first call
runs the agent up to the point where a human must decide; the second
call delivers that decision and resumes the graph to completion.

State persists between the two calls via the graph's checkpointer,
keyed by the investigation's thread_id.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.agent.graph import investigation_graph
from app.api.deps import limiter, require_api_key
from app.models.state import AgentState

router = APIRouter(prefix="/investigations", tags=["investigations"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------
class StartInvestigation(BaseModel):
    """Body for starting an investigation."""

    shipment_id: str = Field(
        ...,
        min_length=3,
        max_length=50,
        examples=["WSL-20260310-0042"],
    )


class ApprovalDecision(BaseModel):
    """Body for approving or rejecting a drafted action."""

    approved: bool = Field(..., description="True to approve, False to reject.")
    reason: str = Field(
        default="",
        max_length=500,
        description="Optional reason, recorded on rejection.",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _config_for(investigation_id: str) -> dict:
    """The graph config that ties a call to a persisted investigation."""
    return {"configurable": {"thread_id": investigation_id}}


def _state_response(values: dict) -> dict:
    """
    Shape a graph state dict into a clean API response.

    We return the fields a UI needs, not the entire internal state.
    """
    assessment = values.get("assessment")
    draft = values.get("drafted_action")
    sla = values.get("sla_status")

    return {
        "investigation_id": values.get("investigation_id", ""),
        "shipment_id": values.get("shipment_id", ""),
        "shipment_found": values.get("shipment_found", False),
        "exception_detected": values.get("exception_detected", False),
        "exception_type": values.get("exception_type", "none"),
        "approval_status": values.get("approval_status", "pending"),
        "summary": values.get("summary", ""),
        "assessment": None
        if assessment is None
        else {
            "urgency": assessment.urgency,
            "recommended_action_type": assessment.recommended_action_type,
            "summary": assessment.summary,
        },
        "sla_status": None
        if sla is None or not sla.sla_applies
        else {
            "already_breached": sla.already_breached,
            "hours_until_breach": sla.hours_until_breach,
            "penalty_if_breached_sar": sla.penalty_if_breached_sar,
        },
        "drafted_action": None
        if draft is None
        else {
            "recipient_type": draft.recipient_type,
            "recipient_label": draft.recipient_label,
            "subject": draft.subject,
            "body": draft.body,
            "approved": draft.approved,
        },
        "trace": [
            {"node": e.node, "event": e.event, "detail": e.detail}
            for e in values.get("trace", [])
        ],
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post(
    "",
    dependencies=[Depends(require_api_key)],
    summary="Start an investigation",
)
@limiter.limit("15/minute")
async def start_investigation(request: Request, body: StartInvestigation) -> dict:
    """
    Start investigating a shipment.

    Runs the agent up to either:
      - the approval gate (an action was drafted, awaiting your decision), or
      - a no-action stop (not found, or an expected/holiday delay).

    The response includes the investigation_id needed to approve later,
    plus the assessment, drafted action (if any), and full trace.
    """
    # Use the shipment id as a stable thread id for this demo. In a
    # real system you'd generate a unique id per investigation run.
    investigation_id = f"inv-{body.shipment_id}"
    config = _config_for(investigation_id)

    initial = AgentState(
        shipment_id=body.shipment_id,
        investigation_id=investigation_id,
    )
    investigation_graph.invoke(initial, config)

    snapshot = investigation_graph.get_state(config)
    return _state_response(snapshot.values)


@router.post(
    "/{investigation_id}/approve",
    dependencies=[Depends(require_api_key)],
    summary="Approve or reject the drafted action",
)
@limiter.limit("15/minute")
async def approve_investigation(
    request: Request,
    investigation_id: str,
    decision: ApprovalDecision,
) -> dict:
    """
    Deliver the human's approve/reject decision and resume the agent.

    Only valid for an investigation paused at the approval gate. Returns
    the finalized state.
    """
    config = _config_for(investigation_id)

    snapshot = investigation_graph.get_state(config)
    if not snapshot.values:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No investigation found with that id.",
        )

    draft = snapshot.values.get("drafted_action")
    if draft is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This investigation has no drafted action to approve.",
        )

    # Write the decision into the paused state, then resume the graph.
    draft.approved = decision.approved
    draft.rejection_reason = decision.reason
    investigation_graph.update_state(config, {"drafted_action": draft})

    final = investigation_graph.invoke(None, config)  # None = resume
    return _state_response(final)
