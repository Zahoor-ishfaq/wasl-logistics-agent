"""
tests/test_compute_eta.py

Unit tests for compute_eta — the one piece of real business logic.
Pure Python, no LLM, so these are fast, deterministic, and exact.
The holiday-exclusion behavior is the most important thing to pin down.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.shipment import SLATerms
from app.tools.compute_eta import compute_eta, _count_holiday_days_between

from tests.conftest import make_shipment


def _with_deadline(deadline: datetime):
    """A shipment whose SLA promises delivery at `deadline`."""
    return make_shipment(sla=SLATerms(
        promised_delivery=deadline,
        penalty_per_day_sar=500.0,
        max_liability_sar=60000.0,
    ))


class TestBasicSLA:
    def test_not_breached_when_deadline_ahead(self):
        now = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)
        s = _with_deadline(now + timedelta(hours=30))
        r = compute_eta(s, now=now)
        assert r.sla_applies is True
        assert r.already_breached is False
        assert r.hours_until_breach == pytest.approx(30.0, abs=0.1)

    def test_breached_when_deadline_passed(self):
        now = datetime(2026, 4, 10, 0, 0, tzinfo=timezone.utc)
        s = _with_deadline(datetime(2026, 4, 8, 0, 0, tzinfo=timezone.utc))
        r = compute_eta(s, now=now)
        assert r.already_breached is True
        assert r.hours_until_breach is None
        assert r.penalty_if_breached_sar > 0

    def test_penalty_capped_at_max_liability(self):
        now = datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc)
        s = _with_deadline(datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc))
        r = compute_eta(s, now=now)
        assert r.penalty_if_breached_sar <= 60000.0

    def test_no_sla_returns_not_applicable(self):
        s = make_shipment(sla=None)
        r = compute_eta(s, now=datetime(2026, 4, 1, tzinfo=timezone.utc))
        assert r.sla_applies is False
        assert r.already_breached is False


class TestHolidayLogic:
    """The behavior that makes the Eid scenario work correctly."""

    def test_counts_eid_al_fitr_days(self):
        start = datetime(2026, 3, 18, 16, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 24, 18, 0, tzinfo=timezone.utc)
        assert _count_holiday_days_between(start, end) == 4

    def test_no_holidays_in_ordinary_window(self):
        start = datetime(2026, 4, 1, tzinfo=timezone.utc)
        end = datetime(2026, 4, 5, tzinfo=timezone.utc)
        assert _count_holiday_days_between(start, end) == 0

    def test_holiday_delay_not_flagged_as_urgent(self):
        now = datetime(2026, 3, 18, 16, 0, tzinfo=timezone.utc)
        deadline = datetime(2026, 3, 24, 18, 0, tzinfo=timezone.utc)
        s = _with_deadline(deadline)
        r = compute_eta(s, now=now)
        assert r.already_breached is False
        assert r.hours_until_breach == pytest.approx(50.0, abs=1.0)


class TestDeterminism:
    def test_same_inputs_same_output(self):
        now = datetime(2026, 4, 1, 9, 0, tzinfo=timezone.utc)
        s = _with_deadline(now + timedelta(hours=10))
        r1 = compute_eta(s, now=now)
        r2 = compute_eta(s, now=now)
        assert r1.hours_until_breach == r2.hours_until_breach
        assert r1.already_breached == r2.already_breached