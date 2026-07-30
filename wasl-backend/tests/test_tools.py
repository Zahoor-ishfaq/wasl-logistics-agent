"""
tests/test_tools.py

Tests that tool inputs are validated (Pydantic rejects bad input) and
that shipment_lookup returns the right type. No LLM calls.
"""

import pytest
from pydantic import ValidationError

from app.models.shipment import ExceptionType, Shipment, ShipmentNotFound
from app.tools.policy_search import PolicySearchInput
from app.tools.shipment_lookup import shipment_lookup


class TestInputValidation:
    def test_policy_search_rejects_bad_exception_type(self):
        with pytest.raises(ValidationError):
            PolicySearchInput(exception_type="not_a_real_type")

    def test_policy_search_rejects_top_k_too_high(self):
        with pytest.raises(ValidationError):
            PolicySearchInput(exception_type=ExceptionType.customs_hold, top_k=999)

    def test_policy_search_accepts_valid_input(self):
        inp = PolicySearchInput(exception_type=ExceptionType.customs_hold, top_k=3)
        assert inp.top_k == 3


class TestShipmentLookup:
    def test_known_shipment_returns_shipment(self):
        result = shipment_lookup("WSL-20260310-0042")
        assert isinstance(result, Shipment)
        assert result.shipment_id == "WSL-20260310-0042"

    def test_unknown_shipment_returns_not_found(self):
        result = shipment_lookup("WSL-NOPE-9999")
        assert isinstance(result, ShipmentNotFound)

    def test_too_short_id_rejected(self):
        with pytest.raises(ValidationError):
            shipment_lookup("x")
