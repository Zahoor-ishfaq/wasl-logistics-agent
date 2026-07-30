"""
app/services/shipment_service.py

A mock Transport Management System (TMS).

In a real deployment this service would call a live TMS API (SAP TM,
Oracle OTM, or an in-house system). In v1 it reads from a static JSON
file — data/mock_shipments.json — but exposes exactly the interface a
real TMS wrapper would.

Because the interface is defined here and the rest of the app only
depends on this interface (never on the JSON file directly), swapping
to a real TMS later means rewriting only this one file. The agent,
tools, and API don't change.

Public methods:
    get_shipment(shipment_id) -> Shipment | ShipmentNotFound
    list_shipments()          -> list[Shipment]
    list_shipment_ids()       -> list[str]   (used by the UI dropdown)
"""

import json
from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError

from app.config import settings
from app.models.shipment import Shipment, ShipmentNotFound


class ShipmentService:
    """
    Reads shipment records from a JSON file and returns them as
    validated Shipment models.

    The file is loaded once and cached in memory. In v1 the data is
    static, so there is no need to re-read on every call. (A real TMS
    wrapper would make a network call per lookup instead.)
    """

    def __init__(self) -> None:
        self._shipments: dict[str, Shipment] = {}
        self._loaded = False

    def _load(self) -> None:
        """
        Load and validate all shipments from the JSON file on first use.

        Each record is validated against the Shipment schema. If a record
        is malformed, it is skipped with a clear message rather than
        crashing the whole service — one bad record shouldn't take down
        every lookup.
        """
        if self._loaded:
            return

        path = Path(settings.mock_shipments_file)
        if not path.exists():
            raise FileNotFoundError(
                f"Mock shipment file not found at '{path}'. "
                f"Expected it at settings.mock_shipments_file. "
                f"Did you create data/mock_shipments.json?"
            )

        raw = json.loads(path.read_text(encoding="utf-8"))

        # Accept either a top-level list or {"shipments": [...]}.
        records = raw.get("shipments", raw) if isinstance(raw, dict) else raw

        for record in records:
            try:
                shipment = Shipment(**record)
            except ValidationError as exc:
                # Skip the bad record, keep the rest working.
                bad_id = record.get("shipment_id", "<unknown>")
                print(f"[shipment_service] Skipping invalid record '{bad_id}': {exc}")
                continue
            self._shipments[shipment.shipment_id] = shipment

        self._loaded = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_shipment(self, shipment_id: str) -> Shipment | ShipmentNotFound:
        """
        Look up one shipment by its reference.

        Returns:
            Shipment          if found
            ShipmentNotFound  if no shipment matches the id

        Returning a typed not-found result (rather than None or raising)
        lets the agent handle the missing case explicitly and cleanly.
        """
        self._load()
        shipment = self._shipments.get(shipment_id.strip())
        if shipment is None:
            return ShipmentNotFound(shipment_id=shipment_id)
        return shipment

    def list_shipments(self) -> list[Shipment]:
        """Return every shipment. Used for tests and bulk views."""
        self._load()
        return list(self._shipments.values())

    def list_shipment_ids(self) -> list[str]:
        """
        Return all shipment ids, sorted.
        Used to populate the shipment dropdown in the Streamlit UI.
        """
        self._load()
        return sorted(self._shipments.keys())


@lru_cache
def get_shipment_service() -> ShipmentService:
    """Return the shared ShipmentService singleton."""
    return ShipmentService()