import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api import routes_shipments
from app.models.shipment import ShipmentNotFound, ShipmentStatus


def run_async(function, *args):
    """Call the route function without starting FastAPI."""
    original = getattr(function, "__wrapped__", function)
    return asyncio.run(original(*args))


def test_shipment_response_uses_delivery_time(sample_shipment, monkeypatch):
    delivered = sample_shipment.model_copy(
        update={"status": ShipmentStatus.delivered}
    )
    captured = {}

    def fake_compute_eta(shipment, now=None):
        captured["now"] = now
        return SimpleNamespace(
            already_breached=False,
            hours_until_breach=None,
            penalty_if_breached_sar=0,
        )

    monkeypatch.setattr(routes_shipments, "compute_eta", fake_compute_eta)

    response = routes_shipments._shipment_response(delivered)

    assert captured["now"] == delivered.last_updated
    assert response["sla_status"] == "ok"
    assert response["sla_breached"] is False


def test_shipment_response_marks_at_risk(sample_shipment, monkeypatch):
    def fake_compute_eta(shipment, now=None):
        return SimpleNamespace(
            already_breached=False,
            hours_until_breach=12,
            penalty_if_breached_sar=0,
        )

    monkeypatch.setattr(routes_shipments, "compute_eta", fake_compute_eta)

    response = routes_shipments._shipment_response(sample_shipment)

    assert response["sla_status"] == "at_risk"
    assert response["sla_hours_remaining"] == 12


def test_list_shipments_returns_service_records(sample_shipment, monkeypatch):
    service = SimpleNamespace(list_shipments=lambda: [sample_shipment])

    monkeypatch.setattr(
        routes_shipments,
        "get_shipment_service",
        lambda: service,
    )
    monkeypatch.setattr(
        routes_shipments,
        "_shipment_response",
        lambda shipment: {"shipment_id": shipment.shipment_id},
    )

    response = run_async(routes_shipments.list_shipments, None)

    assert response == [{"shipment_id": sample_shipment.shipment_id}]


def test_get_shipment_returns_record(sample_shipment, monkeypatch):
    service = SimpleNamespace(
        get_shipment=lambda shipment_id: sample_shipment
    )

    monkeypatch.setattr(
        routes_shipments,
        "get_shipment_service",
        lambda: service,
    )
    monkeypatch.setattr(
        routes_shipments,
        "_shipment_response",
        lambda shipment: {"shipment_id": shipment.shipment_id},
    )

    response = run_async(
        routes_shipments.get_shipment,
        None,
        sample_shipment.shipment_id,
    )

    assert response["shipment_id"] == sample_shipment.shipment_id


def test_get_shipment_returns_404(monkeypatch):
    missing = ShipmentNotFound.model_construct(
        shipment_id="WSL-MISSING",
        message="Shipment not found",
    )
    service = SimpleNamespace(get_shipment=lambda shipment_id: missing)

    monkeypatch.setattr(
        routes_shipments,
        "get_shipment_service",
        lambda: service,
    )

    with pytest.raises(HTTPException) as error:
        run_async(
            routes_shipments.get_shipment,
            None,
            "WSL-MISSING",
        )

    assert error.value.status_code == 404
    assert error.value.detail == "Shipment not found"
