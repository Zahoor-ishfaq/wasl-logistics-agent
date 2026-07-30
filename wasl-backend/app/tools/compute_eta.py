"""
app/tools/compute_eta.py

Agent tool: calculate how close a shipment is to breaching its SLA.

Pure Python. No LLM. No network. Deterministic — the same shipment
and the same "now" always produce the same result. That makes this
tool trivially unit-testable and cheap to call.

The one genuinely tricky rule (from the delayed_shipments_policy and
holiday_schedule documents):

    Officially declared Saudi public holidays do NOT count as breach
    time. If the SLA deadline sits on the far side of an Eid closure,
    the closed days are subtracted before deciding whether the shipment
    is "breached" or how many hours remain.

This is why Scenario B (holiday closure) must NOT be treated as an
urgent breach — the calculator removes the holiday days first.
"""

from datetime import UTC, date, datetime, timedelta

from pydantic import BaseModel, Field

from app.models.shipment import Shipment
from app.models.state import SLAStatus

# ---------------------------------------------------------------------------
# Saudi public holidays 2026 (from holiday_schedule.md).
# Each entry is an inclusive (start, end) date range of full closure.
# Kept here as a constant so the calculator is self-contained and
# deterministic. In a production system this would come from a
# calendar service or the holiday document itself.
# ---------------------------------------------------------------------------
SAUDI_HOLIDAYS_2026: list[tuple[date, date]] = [
    (date(2026, 2, 22), date(2026, 2, 22)),  # Founding Day
    (date(2026, 3, 19), date(2026, 3, 22)),  # Eid al-Fitr
    (date(2026, 5, 26), date(2026, 5, 30)),  # Day of Arafat + Eid al-Adha
    (date(2026, 9, 23), date(2026, 9, 23)),  # National Day
]


class ComputeEtaInput(BaseModel):
    """Validated input for the ETA / SLA breach calculator."""

    shipment: Shipment = Field(
        ...,
        description="The shipment to assess. Must include SLA terms to compute a breach.",
    )


def _count_holiday_days_between(start: datetime, end: datetime) -> int:
    """
    Count how many full holiday days fall between two datetimes.

    Used to subtract closure days from the time-to-deadline so that a
    holiday-driven delay is not mistaken for an SLA breach.

    Args:
        start: The earlier datetime (usually "now").
        end:   The later datetime (usually the SLA deadline).

    Returns:
        The number of calendar days in that window that are Saudi
        public holidays.
    """
    if end <= start:
        return 0

    start_day = start.date()
    end_day = end.date()

    holiday_days = 0
    for holiday_start, holiday_end in SAUDI_HOLIDAYS_2026:
        # Walk each day of this holiday range and count it if it falls
        # within the [start_day, end_day] window.
        day = holiday_start
        while day <= holiday_end:
            if start_day <= day <= end_day:
                holiday_days += 1
            day += timedelta(days=1)

    return holiday_days


def compute_eta(shipment: Shipment, now: datetime | None = None) -> SLAStatus:
    """
    Calculate the SLA breach status for a shipment.

    Use this tool to determine how urgent a shipment exception is:
    whether the SLA deadline has already passed, how many hours remain
    until it does, and what the penalty would be. Holiday closure days
    are excluded from the calculation so that expected holiday delays
    are not reported as urgent breaches.

    Args:
        shipment: The shipment to assess.
        now:      The reference time. Defaults to the current UTC time.
                  Passing it explicitly makes the function deterministic
                  for tests.

    Returns:
        SLAStatus with:
          - sla_applies: False if the shipment has no SLA terms
          - already_breached: True if the (holiday-adjusted) deadline passed
          - hours_until_breach: hours remaining, or None if breached / no SLA
          - breach_time: the SLA deadline datetime
          - penalty_if_breached_sar: estimated penalty from contract terms
    """
    # Validate input shape.
    ComputeEtaInput(shipment=shipment)

    now = now or datetime.now(UTC)

    # No SLA terms → nothing to compute.
    if shipment.sla is None:
        return SLAStatus(
            sla_applies=False,
            hours_until_breach=None,
            already_breached=False,
            breach_time=None,
            penalty_if_breached_sar=0.0,
        )

    deadline = shipment.sla.promised_delivery

    # Normalize both datetimes to timezone-aware UTC so subtraction is safe.
    now = _as_utc(now)
    deadline = _as_utc(deadline)

    # Raw time until the deadline.
    raw_delta = deadline - now

    # Subtract holiday closure days sitting between now and the deadline.
    # Those days shouldn't count against the SLA, so we effectively push
    # the "usable" deadline earlier by the number of holiday days when
    # deciding remaining working time.
    holiday_days = _count_holiday_days_between(now, deadline)
    adjusted_delta = raw_delta - timedelta(days=holiday_days)

    adjusted_hours = adjusted_delta.total_seconds() / 3600.0

    if adjusted_hours <= 0:
        # Deadline has passed even after removing holiday days → real breach.
        days_over = abs(adjusted_delta.days) + 1
        penalty = min(
            shipment.sla.penalty_per_day_sar * days_over,
            shipment.sla.max_liability_sar,
        )
        return SLAStatus(
            sla_applies=True,
            hours_until_breach=None,
            already_breached=True,
            breach_time=deadline,
            penalty_if_breached_sar=round(penalty, 2),
        )

    # Deadline still ahead (after removing holiday days) → not breached.
    return SLAStatus(
        sla_applies=True,
        hours_until_breach=round(adjusted_hours, 1),
        already_breached=False,
        breach_time=deadline,
        penalty_if_breached_sar=round(shipment.sla.penalty_per_day_sar, 2),
    )


def _as_utc(dt: datetime) -> datetime:
    """
    Return a timezone-aware datetime in UTC.

    If the input is naive (no tzinfo), assume it is already UTC.
    This avoids 'can't subtract offset-naive and offset-aware' errors
    when mixing datetimes from JSON (which may be naive) and now().
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)
