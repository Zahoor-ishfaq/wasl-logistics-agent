"""
app/models/state.py

AgentState is the single object that flows through every node of the
LangGraph investigation graph.

Think of it as the agent's working memory for one investigation:
- It starts with just a shipment_id
- Each node reads from it and writes back to it
- By the time the graph reaches the approval gate, it contains
  everything gathered: the shipment, the policy, the assessment,
  the drafted action, and a full trace of what happened

LangGraph requires state to be a TypedDict or a Pydantic model.
We use Pydantic so we get validation and type safety automatically.

One AgentState instance = one complete investigation run.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.answer import Citation
from app.models.shipment import ExceptionType, Shipment


# ---------------------------------------------------------------------------
# Supporting models
# ---------------------------------------------------------------------------

class TraceEvent(BaseModel):
    """
    A single event recorded during an investigation.

    Every meaningful action the agent takes — tool call, retrieval,
    decision — is appended to AgentState.trace as a TraceEvent.
    This gives us a full audit trail of exactly what happened
    and in what order, without needing to read Langfuse.

    Example:
        {
            "timestamp": "2024-03-15T14:32:01Z",
            "node": "lookup_shipment",
            "event": "tool_call",
            "detail": "shipment_lookup(WSL-20240315-0042) → status: held"
        }
    """

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    node: str = Field(..., description="The graph node that emitted this event.")
    event: str = Field(..., description="Short event type label.")
    detail: str = Field(default="", description="Human-readable detail.")


class SLAStatus(BaseModel):
    """
    The result of the ETA / SLA breach calculation.

    Produced by the compute_eta tool and written into AgentState.
    Used by the build_assessment node to determine urgency.

    Example:
        {
            "sla_applies": true,
            "hours_until_breach": 6.5,
            "already_breached": false,
            "breach_time": "2024-03-15T20:00:00Z",
            "penalty_if_breached_sar": 500.0
        }
    """

    sla_applies: bool = Field(
        ...,
        description="False if no SLA contract covers this shipment.",
    )
    hours_until_breach: float | None = Field(
        default=None,
        description="Hours remaining until SLA deadline. None if already breached or no SLA.",
    )
    already_breached: bool = Field(
        default=False,
        description="True if the SLA deadline has already passed.",
    )
    breach_time: datetime | None = Field(
        default=None,
        description="The exact datetime of the SLA deadline.",
    )
    penalty_if_breached_sar: float = Field(
        default=0.0,
        description="Estimated penalty in SAR based on contract terms.",
    )


class RetrievedPolicy(BaseModel):
    """
    Policy and contract information retrieved from the knowledge base.

    Produced by the retrieve_policy_and_sla node. Contains the
    chunks most relevant to the specific exception type detected.
    """

    exception_type: ExceptionType = Field(
        ...,
        description="The exception type this policy was retrieved for.",
    )
    citations: list[Citation] = Field(
        default_factory=list,
        description="The document chunks retrieved for this exception type.",
    )
    summary: str = Field(
        default="",
        description=(
            "A brief LLM-generated summary of the relevant policy, "
            "produced by the retrieve_policy_and_sla node."
        ),
    )


class Assessment(BaseModel):
    """
    The structured assessment produced by the build_assessment node.

    This is what the ops agent reads when they review the investigation.
    It synthesizes everything the agent gathered into a clear, actionable
    summary — what happened, what the policy requires, how urgent it is,
    and what the agent recommends doing.

    Example:
        {
            "exception_type": "customs_hold",
            "summary": "Shipment WSL-20240315-0042 is held at King Abdulaziz Port
                        due to a missing certificate of origin for HS code 8471.30.
                        Per the customs procedure, a SASO conformity certificate is
                        required. The SLA deadline is in 6.5 hours. An internal
                        escalation to the compliance team is recommended.",
            "urgency": "high",
            "recommended_action_type": "internal_escalation",
            "sla_status": { ... }
        }
    """

    exception_type: ExceptionType = Field(...)

    summary: str = Field(
        ...,
        description=(
            "Plain-language synthesis of the situation: what happened, "
            "what the policy says, and what is recommended. "
            "Written for an ops agent, not a technical audience."
        ),
    )

    urgency: str = Field(
        ...,
        description="One of: low | medium | high | critical",
        examples=["high"],
    )

    recommended_action_type: str = Field(
        ...,
        description=(
            "The type of action the agent recommends. "
            "One of: internal_escalation | customer_notice | vendor_notice | monitor | none"
        ),
        examples=["internal_escalation"],
    )

    sla_status: SLAStatus | None = Field(
        default=None,
        description="SLA breach calculation if applicable.",
    )


class DraftedAction(BaseModel):
    """
    The message or action drafted by the draft_action node.

    This is what the human must approve before it becomes actionable.
    Nothing in this object is sent anywhere — it is a proposed action,
    held at the approval gate.

    Example:
        {
            "recipient_type": "internal",
            "recipient_label": "Compliance Team",
            "subject": "URGENT: Customs hold — WSL-20240315-0042 — SLA breach in 6.5 hrs",
            "body": "Shipment WSL-20240315-0042 is currently held at King Abdulaziz Port...",
            "requires_approval": true,
            "approved": null
        }
    """

    recipient_type: str = Field(
        ...,
        description="One of: customer | vendor | internal",
        examples=["internal"],
    )

    recipient_label: str = Field(
        ...,
        description="Human-readable recipient description.",
        examples=["Compliance Team", "Al-Wasl Freight Solutions", "Customer Service"],
    )

    subject: str = Field(
        ...,
        description="Subject line for the drafted message.",
    )

    body: str = Field(
        ...,
        description="Full body of the drafted message.",
    )

    requires_approval: bool = Field(
        default=True,
        description=(
            "Always True in v1 — every action requires human approval. "
            "This field exists so the architecture supports optional "
            "auto-approval for low-risk action types in a future version."
        ),
    )

    approved: bool | None = Field(
        default=None,
        description=(
            "None = awaiting decision. "
            "True = human approved. "
            "False = human rejected."
        ),
    )

    rejection_reason: str = Field(
        default="",
        description="Reason provided by the human when rejecting the draft.",
    )


class ApprovalStatus(str):
    """Possible states of the human approval gate."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# The main state object
# ---------------------------------------------------------------------------

class AgentState(BaseModel):
    """
    The complete working memory of one investigation run.

    Flows through the LangGraph graph from start to finish.
    Each node receives the current state, does its job, and
    returns an updated copy.

    Lifecycle:
        initialize          → shipment_id is set
        lookup_shipment     → shipment is populated
        assess_exception    → exception_detected and exception_type are set
        retrieve_policy_and_sla → retrieved_policy and sla_status are set
        build_assessment    → assessment is set
        draft_action        → drafted_action is set
        approval_gate       → STOPS HERE — approval_status = "pending"
        (human approves or rejects)
        finalize            → approval_status = "approved" or "rejected"

    If assess_exception finds no exception:
        summarize_and_stop  → summary set, graph ends without a draft
    """

    # ------------------------------------------------------------------
    # Input — set at initialization
    # ------------------------------------------------------------------
    shipment_id: str = Field(
        ...,
        description="The shipment reference to investigate.",
        examples=["WSL-20240315-0042"],
    )

    investigation_id: str = Field(
        default="",
        description=(
            "Unique ID for this investigation run. "
            "Generated by the initialize node. "
            "Used to resume the graph after the approval gate interrupt."
        ),
    )

    started_at: datetime | None = Field(
        default=None,
        description="When the investigation was started.",
    )

    # ------------------------------------------------------------------
    # Populated by lookup_shipment node
    # ------------------------------------------------------------------
    shipment: Shipment | None = Field(
        default=None,
        description="The shipment record retrieved from the shipment service.",
    )

    shipment_found: bool = Field(
        default=False,
        description="False if no shipment matched the shipment_id.",
    )

    # ------------------------------------------------------------------
    # Populated by assess_exception node
    # ------------------------------------------------------------------
    exception_detected: bool = Field(
        default=False,
        description=(
            "True if the LLM determined an actionable exception exists. "
            "False routes the graph to summarize_and_stop."
        ),
    )

    exception_type: ExceptionType = Field(
        default=ExceptionType.none,
        description="The specific exception type identified by the LLM.",
    )

    # ------------------------------------------------------------------
    # Populated by retrieve_policy_and_sla node
    # ------------------------------------------------------------------
    retrieved_policy: RetrievedPolicy | None = Field(
        default=None,
        description="Policy chunks relevant to the exception type.",
    )

    sla_status: SLAStatus | None = Field(
        default=None,
        description="SLA breach calculation for this shipment.",
    )

    # ------------------------------------------------------------------
    # Populated by build_assessment node
    # ------------------------------------------------------------------
    assessment: Assessment | None = Field(
        default=None,
        description="The structured assessment of the situation.",
    )

    # ------------------------------------------------------------------
    # Populated by draft_action node
    # ------------------------------------------------------------------
    drafted_action: DraftedAction | None = Field(
        default=None,
        description="The proposed action awaiting human approval.",
    )

    # ------------------------------------------------------------------
    # Populated by summarize_and_stop node (no-exception path)
    # ------------------------------------------------------------------
    summary: str = Field(
        default="",
        description=(
            "Plain-language summary used when no exception is detected. "
            "Tells the ops agent the shipment status and that no action is needed."
        ),
    )

    # ------------------------------------------------------------------
    # Updated by approval_gate and finalize nodes
    # ------------------------------------------------------------------
    approval_status: str = Field(
        default=ApprovalStatus.PENDING,
        description=(
            "pending   → graph is paused at the approval gate \n"
            "approved  → human approved the drafted action \n"
            "rejected  → human rejected the drafted action"
        ),
    )

    completed_at: datetime | None = Field(
        default=None,
        description="When the investigation was fully completed.",
    )

    # ------------------------------------------------------------------
    # Audit trail — appended to by every node
    # ------------------------------------------------------------------
    trace: list[TraceEvent] = Field(
        default_factory=list,
        description=(
            "Ordered list of events that occurred during this investigation. "
            "Every node appends at least one event. "
            "Used for debugging, audit, and observability."
        ),
    )

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------
    error: str = Field(
        default="",
        description=(
            "Set if any node encountered an unrecoverable error. "
            "Non-empty means the investigation did not complete normally."
        ),
    )

    # ------------------------------------------------------------------
    # LangGraph compatibility
    # ------------------------------------------------------------------
    class Config:
        # Allow arbitrary types so LangGraph can handle this model.
        arbitrary_types_allowed = True

    def add_trace(self, node: str, event: str, detail: str = "") -> "AgentState":
        """
        Convenience method to append a trace event and return self.

        Usage inside a node:
            state = state.add_trace("lookup_shipment", "tool_call",
                                    f"shipment_lookup({state.shipment_id})")
        """
        self.trace.append(TraceEvent(node=node, event=event, detail=detail))
        return self

    def to_summary_dict(self) -> dict[str, Any]:
        """
        Returns a compact summary of the investigation state —
        useful for API responses and logging without dumping the full object.
        """
        return {
            "investigation_id": self.investigation_id,
            "shipment_id": self.shipment_id,
            "shipment_found": self.shipment_found,
            "exception_detected": self.exception_detected,
            "exception_type": self.exception_type,
            "approval_status": self.approval_status,
            "has_assessment": self.assessment is not None,
            "has_draft": self.drafted_action is not None,
            "trace_events": len(self.trace),
            "error": self.error,
        }