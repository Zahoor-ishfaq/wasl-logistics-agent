from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import limiter, require_api_key
from app.models.shipment import Shipment, ShipmentNotFound
from app.services.shipment_service import get_shipment_service
from app.tools.compute_eta import compute_eta

router = APIRouter(prefix="/shipments", tags=["shipments"])


def _shipment_response(shipment: Shipment) -> dict:
    reference_time = (
    shipment.last_updated
    if shipment.status.value == "delivered"
    else None
)

    sla = compute_eta(shipment, now=reference_time)

    return {
        **shipment.model_dump(mode="json"),
        "sla_status": (
            "breached"
            if sla.already_breached
            else "at_risk"
            if sla.hours_until_breach is not None
            and sla.hours_until_breach <= 24
            else "ok"
        ),
        "sla_hours_remaining": sla.hours_until_breach,
        "sla_breached": sla.already_breached,
        "penalty_if_breached_sar": sla.penalty_if_breached_sar,
    }


@router.get(
    "",
    dependencies=[Depends(require_api_key)],
)
@limiter.limit("30/minute")
async def list_shipments(request: Request) -> list[dict]:
    shipments = get_shipment_service().list_shipments()
    return [_shipment_response(shipment) for shipment in shipments]


@router.get(
    "/{shipment_id}",
    dependencies=[Depends(require_api_key)],
)
@limiter.limit("30/minute")
async def get_shipment(request: Request, shipment_id: str) -> dict:
    result = get_shipment_service().get_shipment(shipment_id)

    if isinstance(result, ShipmentNotFound):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.message,
        )

    return _shipment_response(result)
