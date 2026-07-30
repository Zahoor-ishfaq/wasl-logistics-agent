"""
scripts/try_agent.py

Run a real shipment investigation end to end, interactively.

    python scripts/try_agent.py                      # uses a default shipment
    python scripts/try_agent.py WSL-20260318-0088    # investigate a specific one

What it does:
  1. Starts an investigation (runs the graph up to the approval gate)
  2. Prints the assessment and the drafted action
  3. If the graph paused for approval, asks you to approve or reject
  4. Resumes the graph and prints the final outcome
  5. Prints the full trace so you can see every step

Requires:
  - documents ingested (scripts/ingest.py)
  - ANTHROPIC_API_KEY set in .env
  - mock_shipments.json present

Good shipments to try:
  WSL-20260310-0042  customs hold      -> investigates, drafts internal escalation
  WSL-20260412-0210  cross-border      -> investigates, drafts customer notice
  WSL-20260420-0301  supplier delay    -> investigates, drafts vendor notice
  WSL-20260318-0088  holiday closure   -> NO action, explains why (expected delay)
  WSL-NOPE-9999      does not exist     -> stops cleanly
"""

import sys
from pathlib import Path

# Make the project root importable when run directly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agent.graph import build_graph  # noqa: E402
from app.models.state import AgentState  # noqa: E402


DEFAULT_SHIPMENT = "WSL-20260310-0042"


def _line(char: str = "-", n: int = 72) -> None:
    print(char * n)


def _print_assessment(values: dict) -> None:
    assessment = values.get("assessment")
    if assessment is None:
        return
    _line("=")
    print("ASSESSMENT")
    _line()
    print(f"Exception : {assessment.exception_type.value}")
    print(f"Urgency   : {assessment.urgency}")
    print(f"Recommend : {assessment.recommended_action_type}")
    if assessment.sla_status and assessment.sla_status.sla_applies:
        sla = assessment.sla_status
        if sla.already_breached:
            print(f"SLA       : BREACHED (penalty ~{sla.penalty_if_breached_sar} SAR)")
        else:
            print(f"SLA       : {sla.hours_until_breach}h until breach")
    print()
    print(assessment.summary)
    print()


def _print_draft(values: dict) -> None:
    draft = values.get("drafted_action")
    if draft is None:
        return
    _line("=")
    print("DRAFTED ACTION  (awaiting your approval — nothing is sent)")
    _line()
    print(f"To      : {draft.recipient_label} ({draft.recipient_type})")
    print(f"Subject : {draft.subject}")
    print()
    print(draft.body)
    print()


def _print_trace(values: dict) -> None:
    trace = values.get("trace", [])
    if not trace:
        return
    _line("=")
    print("INVESTIGATION TRACE")
    _line()
    for event in trace:
        print(f"  {event.node:24s} {event.event:12s} {event.detail}")
    print()


def main() -> None:
    shipment_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SHIPMENT

    graph = build_graph()
    config = {"configurable": {"thread_id": f"cli-{shipment_id}"}}

    print(f"\nStarting investigation for: {shipment_id}\n")

    # 1. Run the graph. It runs until it either finishes (no-action path)
    #    or pauses before the approval gate (action path).
    graph.invoke(AgentState(shipment_id=shipment_id), config)

    # 2. Inspect where we ended up.
    snapshot = graph.get_state(config)
    values = snapshot.values

    # No-action path (not found, or expected/holiday) — the graph reached
    # END without drafting anything. Print the summary and stop.
    if values.get("drafted_action") is None:
        _line("=")
        print("RESULT — NO ACTION REQUIRED")
        _line()
        print(values.get("summary", "(no summary)"))
        print()
        _print_trace(values)
        return

    # Action path — the graph paused at the approval gate.
    _print_assessment(values)
    _print_draft(values)

    # 3. Ask the human to approve or reject.
    _line("=")
    choice = input("Approve this action? [y]es / [n]o : ").strip().lower()
    approved = choice in {"y", "yes"}
    reason = ""
    if not approved:
        reason = input("Reason for rejection (optional): ").strip()

    # 4. Write the decision into state, then resume the graph.
    draft = values["drafted_action"]
    draft.approved = approved
    draft.rejection_reason = reason
    graph.update_state(config, {"drafted_action": draft})

    final = graph.invoke(None, config)  # None = resume from the interrupt

    # 5. Print the outcome.
    print()
    _line("=")
    print(f"RESULT — {final['approval_status'].upper()}")
    _line()
    if final["approval_status"] == "approved":
        print("The action was approved. In production this is where the")
        print("message would be sent or the ticket created.")
    else:
        print("The action was rejected. Nothing was sent.")
        if reason:
            print(f"Reason: {reason}")
    print()
    _print_trace(final)


if __name__ == "__main__":
    main()