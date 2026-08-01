from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, Float, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ShipmentRecord(Base):
    __tablename__ = "shipments"

    shipment_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    exception_type: Mapped[str] = mapped_column(String(50), nullable=False)
    exception_detail: Mapped[str] = mapped_column(Text, default="")

    origin: Mapped[str] = mapped_column(String(255), nullable=False)
    destination: Mapped[str] = mapped_column(String(255), nullable=False)
    current_location: Mapped[dict] = mapped_column(JSON, nullable=False)

    carrier: Mapped[str] = mapped_column(String(255), nullable=False)
    vendor_cr: Mapped[str] = mapped_column(String(50), default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    promised_delivery: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    shipment_value_sar: Mapped[Decimal] = mapped_column(
    Numeric(14, 2),
    nullable=False,
    default=0,
    )
    penalty_per_day_sar: Mapped[float] = mapped_column(Float, default=0.0)
    max_liability_sar: Mapped[float] = mapped_column(Float, default=50000.0)

    customer_name: Mapped[str] = mapped_column(String(255), default="")
    customer_contact: Mapped[str] = mapped_column(String(255), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
