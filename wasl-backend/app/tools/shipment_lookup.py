"""
app/tools/shipment_lookup.py

Agent tool: look up a shipment by its reference ID.

This is the agent's first action in almost every investigation —
before it can assess anything, it needs the shipment record.

A "tool" here is just a plain function with:
  - validated inputs  (so the agent can't call it with garbage)
  - a predictable, typed return value
  - a docstring the LLM reads to decide when to call it

It wraps the shipment service (the mock TMS). The tool layer exists
so that when the agent calls a tool, it always goes through one
consistent, validated interface — regardless of what the underlying
data source is.

This tool does NOT call the LLM. It is pure data retrieval.
"""

from pydantic import BaseModel, Field

from app.models.shipment import Shipment, ShipmentNotFound
from app.services.shipment_service import get_shipment_service


class ShipmentLookupInput(BaseModel):
    """
    Validated input for the shipment lookup tool.

    Using a Pydantic model for the input (rather than a bare string)
    means the agent's call is validated before the tool runs, and the
    schema can be handed to the LLM so it knows exactly what to pass.
    """

    shipment_id: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="The shipment reference to look up, e.g. 'WSL-20260310-0042'.",
    )


def shipment_lookup(shipment_id: str) -> Shipment | ShipmentNotFound:
    """
    Look up a single shipment by its reference ID.

    Use this tool whenever you need the current status, location,
    exception details, or SLA terms of a specific shipment. This is
    normally the first step of an investigation.

    Args:
        shipment_id: The shipment reference, e.g. "WSL-20260310-0042".

    Returns:
        Shipment          if a matching shipment is found.
        ShipmentNotFound  if no shipment matches the reference — the
                          agent should stop the investigation and report
                          that the shipment could not be found.
    """
    # Validate the input. Raises a clear error if the id is malformed,
    # which the agent node catches and records in the trace.
    validated = ShipmentLookupInput(shipment_id=shipment_id)

    service = get_shipment_service()
    return service.get_shipment(validated.shipment_id)