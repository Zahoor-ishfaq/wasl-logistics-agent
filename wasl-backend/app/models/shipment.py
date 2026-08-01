"""
app/models/shipment.py

Pydantic schema for a shipment record returned by the shipment service.

This schema deliberately mirrors what a real TMS (Transport Management
System) API would return. In v1 the shipment service reads from
data/mock_shipments.json — but because the schema is defined here
independently, swapping to a real TMS later only requires changing
the service, not the agent or any other code that uses this model.

The four exception types map directly to the four Saudi exception
scenarios defined in PRD Section 6:
  - customs_hold     → Scenario A
  - holiday_closure  → Scenario B (identified by the agent, not ZATCA)
  - cross_border     → Scenario C
  - supplier_delay   → Scenario D
  - none             → no exception, route to summarize_and_stop
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ShipmentStatus(str, Enum):
    """Current state of the shipment in the logistics pipeline."""

    pending = "pending"  # accepted, not yet dispatched
    in_transit = "in_transit"  # moving toward destination
    at_customs = "at_customs"  # at a Saudi port awaiting clearance
    held = "held"  # stopped — exception in progress
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    failed_delivery = "failed_delivery"  # attempt made, consignee not reached
    returned = "returned"  # sent back to origin



class ExceptionType(str, Enum):
    """
    The category of exception affecting this shipment.

    Drives the agent's conditional routing — each type maps to a
    different investigation path and a different draft action type.
    """

    none = "none"  # no exception
    customs_hold = "customs_hold"  # Scenario A — ZATCA documentation issue
    holiday_closure = "holiday_closure"  # Scenario B — expected, not escalated
    cross_border = "cross_border"  # Scenario C — GCC border, unclear cause
    supplier_delay = "supplier_delay"  # Scenario D — upstream vendor failure
    carrier_delay = "carrier_delay"  # operational delay, carrier fault
    failed_delivery = "failed_delivery"  # consignee not available


class ShipmentLocation(BaseModel):
    """Physical location of the shipment at the last known point."""

    city: str = Field(..., examples=["Jeddah"])
    country: str = Field(default="Saudi Arabia")
    facility: str = Field(
        default="",
        description="Port, warehouse, or border crossing name if applicable.",
        examples=["King Abdulaziz Port", "Saudi-UAE Border — Ghuwaifat"],
    )


class SLATerms(BaseModel):
    """
    The contractual SLA terms governing this shipment.

    Populated from the vendor contract. Used by the ETA calculator
    to determine time-to-breach and whether a penalty applies.
    """

    promised_delivery: datetime = Field(
        ...,
        description="The contractually committed delivery date and time.",
    )
    penalty_per_day_sar: float = Field(
        default=0.0,
        ge=0.0,
        description="Penalty in SAR for each day beyond the promised delivery date.",
    )
    max_liability_sar: float = Field(
        default=50000.0,
        ge=0.0,
        description="Maximum total penalty cap per the vendor contract.",
    )


class Shipment(BaseModel):
    """
    A single shipment record as returned by the shipment service.

    This is the primary input to the agent's investigation workflow.
    The agent calls shipment_lookup(shipment_id) and receives one
    of these objects — or a not-found result.

    Example:
        {
            "shipment_id": "WSL-20240315-0042",
            "status": "held",
            "exception_type": "customs_hold",
            "exception_detail": "Missing certificate of origin. HS code 8471.30 requires SASO conformity certificate.",
            "origin": "Dubai, UAE",
            "destination": "Riyadh, KSA",
            "current_location": {
                "city": "Jeddah",
                "country": "Saudi Arabia",
                "facility": "King Abdulaziz Port"
            },
            "carrier": "Al-Wasl Freight Solutions",
            "vendor_cr": "1010456789",
            "created_at": "2024-03-13T08:00:00Z",
            "last_updated": "2024-03-15T14:30:00Z",
            "sla": {
                "promised_delivery": "2024-03-16T18:00:00Z",
                "penalty_per_day_sar": 500.0,
                "max_liability_sar": 50000.0,
                "shipment_value_sar": Decimal("0")
            },
            "customer_name": "Riyadh Electronics Trading Co.",
            "customer_contact": "ops@riyadhelectronics.sa",
            "notes": "Third attempted customs submission. Client notified."
        }
    """

    shipment_id: str = Field(
        ...,
        description="Unique shipment reference. Format: WSL-YYYYMMDD-XXXX",
        examples=["WSL-20240315-0042"],
    )

    status: ShipmentStatus = Field(
        ...,
        description="Current state of the shipment.",
    )

    exception_type: ExceptionType = Field(
        default=ExceptionType.none,
        description="The type of exception affecting this shipment, if any.",
    )

    exception_detail: str = Field(
        default="",
        description=(
            "Human-readable description of the exception. "
            "For customs holds: includes the specific missing document and HS code. "
            "For cross-border holds: includes border name and hours held. "
            "Empty when exception_type is none."
        ),
        examples=[
            "Missing certificate of origin. HS code 8471.30 requires SASO conformity certificate.",
            "Held at Ghuwaifat border crossing for 52 hours. No reason communicated by UAE/KSA border authority.",
            "Supplier failed to dispatch goods on the agreed date. New dispatch date not yet confirmed.",
        ],
    )

    origin: str = Field(
        ...,
        description="Origin city and country.",
        examples=["Dubai, UAE"],
    )

    destination: str = Field(
        ...,
        description="Destination city and country.",
        examples=["Riyadh, KSA"],
    )

    current_location: ShipmentLocation = Field(
        ...,
        description="Last known physical location of the shipment.",
    )

    carrier: str = Field(
        ...,
        description="Name of the carrier or logistics provider.",
        examples=["Al-Wasl Freight Solutions"],
    )

    vendor_cr: str = Field(
        default="",
        description="Vendor Commercial Registration number — used to look up contract terms.",
        examples=["1010456789"],
    )

    created_at: datetime = Field(
        ...,
        description="When the shipment was created in the system.",
    )

    last_updated: datetime = Field(
        ...,
        description="When the shipment record was last updated.",
    )

    sla: SLATerms | None = Field(
        default=None,
        description=(
            "SLA terms from the vendor contract. "
            "None if no SLA applies to this shipment "
            "(e.g. spot shipments without a contract)."
        ),
    )

    customer_name: str = Field(
        default="",
        description="Name of the end customer or consignee.",
    )

    customer_contact: str = Field(
        default="",
        description="Email or phone for the customer contact.",
    )

    notes: str = Field(
        default="",
        description="Free-text operational notes added by the ops team.",
    )


class ShipmentNotFound(BaseModel):
    """
    Returned by the shipment service when no shipment matches the given ID.

    The agent checks for this before proceeding with investigation —
    if the shipment does not exist, it cannot investigate and should
    return a clear message to the user.
    """

    shipment_id: str
    found: bool = False
    message: str = "No shipment found with this reference number."
