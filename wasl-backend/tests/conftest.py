"""
tests/conftest.py

Shared pytest fixtures. The key idea: tests run fast and free.
Unit tests exercise pure logic directly; anything that would call the
LLM or the embedding model is mocked, so the suite needs no API key and
makes no network calls. That's what lets it run in CI on every push.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Make the project importable.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def fixed_now():
    """A fixed 'now' so time-dependent logic is deterministic."""
    return datetime(2026, 3, 10, 12, 0, tzinfo=UTC)


def make_shipment(**overrides):
    """
    Factory for a valid Shipment. Pass overrides to change fields.
    Centralizes the required fields so tests stay short.
    """
    from app.models.shipment import (
        ExceptionType,
        Shipment,
        ShipmentLocation,
        ShipmentStatus,
    )

    base = dict(
        shipment_id="WSL-20260310-0042",
        status=ShipmentStatus.held,
        exception_type=ExceptionType.customs_hold,
        exception_detail="Missing SASO certificate for HS 8471.30",
        origin="Shenzhen, China",
        destination="Riyadh, KSA",
        current_location=ShipmentLocation(
            city="Jeddah", facility="King Abdulaziz Port"
        ),
        carrier="Al-Wasl Freight",
        created_at=datetime(2026, 3, 8, 8, 0, tzinfo=UTC),
        last_updated=datetime(2026, 3, 10, 14, 30, tzinfo=UTC),
        customer_name="Riyadh Electronics Trading",
    )
    base.update(overrides)
    return Shipment(**base)


@pytest.fixture
def sample_shipment():
    """A minimal valid shipment (customs hold, no SLA set)."""
    return make_shipment()


@pytest.fixture
def fake_llm():
    """A stand-in LLM service; `.complete()` returns a canned string."""
    llm = MagicMock()
    llm.complete.return_value = "Deterministic test response."
    return llm


@pytest.fixture
def fake_citations():
    """A couple of fake citations for tests that need retrieval output."""
    from app.models.answer import Citation

    return [
        Citation(
            source="customs_procedure.md",
            section="Required documentation",
            snippet="A SASO certificate is required.",
            similarity_score=0.72,
        ),
        Citation(
            source="delayed_shipments_policy.md",
            section="Category A",
            snippet="Customs holds must be reported within one hour.",
            similarity_score=0.61,
        ),
    ]
