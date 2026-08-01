"""
app/services/shipment_service.py

A PostgreSQL-backed Transport Management System (TMS) service.

In a real deployment this service could call a live TMS API such as SAP TM,
Oracle OTM, or an in-house system. For the current Wasl deployment, shipment
records are stored in PostgreSQL.

Because the interface is defined here and the rest of the app only depends
on this interface, replacing PostgreSQL with a real TMS integration later
requires changing only this service. The agent, tools, and API do not change.

Public methods:
    get_shipment(shipment_id) -> Shipment | ShipmentNotFound
    list_shipments()          -> list[Shipment]
    list_shipment_ids()       -> list[str]
"""

from functools import lru_cache

from sqlalchemy import select

from app.database import SessionLocal
from app.db_models import ShipmentRecord
from app.models.shipment import (
    Shipment,
    ShipmentLocation,
    ShipmentNotFound,
    SLATerms,
)


class ShipmentService:
    """
    Reads shipment records from PostgreSQL and returns them as validated
    Shipment models.

    Database records are converted into the existing Pydantic Shipment
    schema so the agent, tools, API routes, and tests continue using the
    same interface.
    """

    def _record_to_shipment(self, record: ShipmentRecord) -> Shipment:
        """
        Convert a SQLAlchemy ShipmentRecord into the existing Pydantic
        Shipment model.
        """

        sla: SLATerms | None = None

        if record.promised_delivery is not None:
            sla = SLATerms(
                promised_delivery=record.promised_delivery,
                penalty_per_day_sar=record.penalty_per_day_sar,
                max_liability_sar=record.max_liability_sar,
            )

        return Shipment(
            shipment_id=record.shipment_id,
            status=record.status,
            exception_type=record.exception_type,
            exception_detail=record.exception_detail,
            shipment_value_sar=record.shipment_value_sar,
            origin=record.origin,
            destination=record.destination,
            current_location=ShipmentLocation(**record.current_location),
            carrier=record.carrier,
            vendor_cr=record.vendor_cr,
            created_at=record.created_at,
            last_updated=record.last_updated,
            sla=sla,
            customer_name=record.customer_name,
            customer_contact=record.customer_contact,
            notes=record.notes,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_shipment(self, shipment_id: str) -> Shipment | ShipmentNotFound:
        """
        Look up one shipment by its reference.

        Returns:
            Shipment          if found
            ShipmentNotFound  if no shipment matches the ID

        Returning a typed not-found result rather than None or raising
        lets the agent handle the missing case explicitly and cleanly.
        """

        cleaned_id = shipment_id.strip()

        with SessionLocal() as db:
            record = db.get(ShipmentRecord, cleaned_id)

            if record is None:
                return ShipmentNotFound(shipment_id=cleaned_id)

            return self._record_to_shipment(record)

    def list_shipments(self) -> list[Shipment]:
        """
        Return every shipment from PostgreSQL.

        Used by tests, API routes, and bulk shipment views.
        """

        with SessionLocal() as db:
            statement = select(ShipmentRecord).order_by(
                ShipmentRecord.shipment_id
            )

            records = db.scalars(statement).all()

            return [
                self._record_to_shipment(record)
                for record in records
            ]

    def list_shipment_ids(self) -> list[str]:
        """
        Return all shipment IDs sorted alphabetically.

        Used to populate shipment selectors in the frontend.
        """

        with SessionLocal() as db:
            statement = select(
                ShipmentRecord.shipment_id
            ).order_by(
                ShipmentRecord.shipment_id
            )

            return list(db.scalars(statement).all())


@lru_cache
def get_shipment_service() -> ShipmentService:
    """
    Return the shared ShipmentService singleton.

    The service itself does not retain database sessions. Every method opens
    and closes its own session safely.
    """

    return ShipmentService()
