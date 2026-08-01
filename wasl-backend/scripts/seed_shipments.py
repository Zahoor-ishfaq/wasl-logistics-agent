import json
from datetime import datetime
from pathlib import Path

from app.database import SessionLocal
from app.db_models import ShipmentRecord

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "mock_shipments.json"


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main() -> None:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    shipments = data["shipments"]

    with SessionLocal() as db:
        for item in shipments:
            sla = item.get("sla") or {}

            db.merge(
                ShipmentRecord(
                    shipment_id=item["shipment_id"],
                    status=item["status"],
                    exception_type=item["exception_type"],
                    exception_detail=item.get("exception_detail", ""),
                    origin=item["origin"],
                    destination=item["destination"],
                    current_location=item["current_location"],
                    carrier=item["carrier"],
                    vendor_cr=item.get("vendor_cr", ""),
                    created_at=parse_datetime(item["created_at"]),
                    last_updated=parse_datetime(item["last_updated"]),
                    promised_delivery=parse_datetime(
                        sla.get("promised_delivery")
                    ),
                    penalty_per_day_sar=sla.get(
                        "penalty_per_day_sar", 0.0
                    ),
                    max_liability_sar=sla.get(
                        "max_liability_sar", 50000.0
                    ),
                    shipment_value_sar=item.get("shipment_value_sar", 0),
                    customer_name=item.get("customer_name", ""),
                    customer_contact=item.get("customer_contact", ""),
                    notes=item.get("notes", ""),
                )
            )

        db.commit()

    print(f"Seeded {len(shipments)} shipments.")


if __name__ == "__main__":
    main()
