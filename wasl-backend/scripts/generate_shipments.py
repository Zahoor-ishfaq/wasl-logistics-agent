from __future__ import annotations

import argparse
import random
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.database import SessionLocal
from app.db_models import ShipmentRecord

ORIGINS = [
    "Shenzhen, China",
    "Shanghai, China",
    "Dubai, UAE",
    "Mumbai, India",
    "Istanbul, Türkiye",
    "Hamburg, Germany",
    "Singapore",
    "Karachi, Pakistan",
]

DESTINATIONS = [
    ("Riyadh, KSA", "Riyadh", "Riyadh Distribution Hub"),
    ("Jeddah, KSA", "Jeddah", "Jeddah Logistics Hub"),
    ("Dammam, KSA", "Dammam", "Dammam Distribution Hub"),
    ("Yanbu, KSA", "Yanbu", "Yanbu Industrial Hub"),
    ("Medina, KSA", "Medina", "Medina Distribution Center"),
    ("Jubail, KSA", "Jubail", "Jubail Industrial Hub"),
]

CUSTOMERS = [
    "Riyadh Electronics Trading Co.",
    "Jeddah Industrial Supplies",
    "Eastern Province Medical Trading",
    "Yanbu Engineering Services",
    "Saudi Retail Distribution",
    "Gulf Food Imports",
    "Arabian Auto Parts",
    "Najd Construction Materials",
]

CARRIERS = [
    "Al-Wasl Freight Solutions",
    "Gulf Transit Logistics",
    "Red Sea Cargo Services",
    "Arabian Route Transport",
]

STATUSES = [
    "in_transit",
    "held",
    "at_customs",
    "pending",
    "out_for_delivery",
    "delivered",
    "failed_delivery",
    "returned",
]

STATUS_WEIGHTS = [24, 8, 10, 10, 14, 24, 6, 4]


def email_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())[:24] or "customer"


def make_unique_id(db, created_at: datetime, rng: random.Random) -> str:
    while True:
        shipment_id = f"WSL-{created_at:%Y%m%d}-{rng.randint(1000, 9999)}"
        if db.get(ShipmentRecord, shipment_id) is None:
            return shipment_id


def exception_for_status(status: str, rng: random.Random) -> tuple[str, str]:
    if status == "delivered":
        return "none", "Shipment delivered and closed."

    if status in {"held", "at_customs"}:
        exception_type = rng.choice(["customs_hold", "cross_border"])
        detail = (
            "Shipment is waiting for customs document verification."
            if exception_type == "customs_hold"
            else "Cross-border clearance is pending carrier confirmation."
        )
        return exception_type, detail

    if status == "pending":
        exception_type = rng.choice(
            ["supplier_delay", "holiday_closure", "none"]
        )
        details = {
            "supplier_delay": "Supplier has not completed cargo handover.",
            "holiday_closure": "Processing is delayed because the facility is closed.",
            "none": "Shipment is queued for processing.",
        }
        return exception_type, details[exception_type]

    if status == "failed_delivery":
        return (
            "failed_delivery",
            "Delivery attempt failed because the consignee was unavailable.",
        )

    if status == "returned":
        return (
            "failed_delivery",
            "Shipment is returning after repeated delivery failure.",
        )

    exception_type = rng.choices(
        ["none", "carrier_delay"],
        weights=[75, 25],
        k=1,
    )[0]
    detail = (
        "Shipment is moving normally."
        if exception_type == "none"
        else "Carrier reported a delay in the current movement."
    )
    return exception_type, detail


def build_record(db, rng: random.Random, now: datetime) -> ShipmentRecord:
    status = rng.choices(STATUSES, weights=STATUS_WEIGHTS, k=1)[0]

    created_at = now - timedelta(
        days=rng.randint(1, 20),
        hours=rng.randint(0, 23),
        minutes=rng.randint(0, 59),
    )

    if status == "delivered":
        promised_delivery = created_at + timedelta(
            days=rng.randint(2, 7),
            hours=rng.randint(0, 12),
        )

        delivered_on_time = rng.random() < 0.75

        if delivered_on_time:
            last_updated = promised_delivery - timedelta(
                hours=rng.randint(1, 30)
            )
        else:
            last_updated = promised_delivery + timedelta(
                hours=rng.randint(1, 48)
            )

        last_updated = min(last_updated, now)
    else:
        elapsed_hours = max(
            5,
            int((now - created_at).total_seconds() // 3600),
        )

        last_updated = min(
            now,
            created_at + timedelta(hours=rng.randint(4, elapsed_hours)),
        )

        sla_state = rng.choices(
            ["breached", "at_risk", "ok"],
            weights=[30, 30, 40],
            k=1,
        )[0]

        if sla_state == "breached":
            promised_delivery = now - timedelta(
                hours=rng.randint(1, 72)
            )
        elif sla_state == "at_risk":
            promised_delivery = now + timedelta(
                hours=rng.randint(1, 24)
            )
        else:
            promised_delivery = now + timedelta(
                hours=rng.randint(25, 120)
            )

    destination, city, facility = rng.choice(DESTINATIONS)
    customer_name = rng.choice(CUSTOMERS)
    exception_type, exception_detail = exception_for_status(status, rng)

    shipment_value = Decimal(
        rng.randrange(25_000, 900_001, 500)
    ).quantize(Decimal("0.01"))

    penalty_per_day = Decimal(
        str(rng.choice([250, 500, 750, 1000, 1500]))
    )

    max_liability = min(
        Decimal("50000.00"),
        (shipment_value * Decimal("0.20")).quantize(Decimal("0.01")),
    )

    return ShipmentRecord(
        shipment_id=make_unique_id(db, created_at, rng),
        status=status,
        exception_type=exception_type,
        exception_detail=exception_detail,
        origin=rng.choice(ORIGINS),
        destination=destination,
        current_location={
            "city": city,
            "country": "Saudi Arabia",
            "facility": facility,
        },
        carrier=rng.choice(CARRIERS),
        vendor_cr=str(rng.randint(1000000000, 1099999999)),
        created_at=created_at,
        last_updated=last_updated,
        promised_delivery=promised_delivery,
        penalty_per_day_sar=penalty_per_day,
        max_liability_sar=max_liability,
        shipment_value_sar=shipment_value,
        customer_name=customer_name,
        customer_contact=f"ops@{email_slug(customer_name)}.sa",
        notes="Generated demo shipment stored directly in PostgreSQL.",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate realistic shipments and insert them into PostgreSQL."
    )
    parser.add_argument(
        "--count",
        type=int,
        default=25,
        help="Number of shipments to insert. Default: 25",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for repeatable data.",
    )
    args = parser.parse_args()

    if args.count < 1 or args.count > 500:
        raise SystemExit("--count must be between 1 and 500.")

    rng = random.Random(args.seed)
    now = datetime.now(UTC)

    with SessionLocal() as db:
        records = [
            build_record(db, rng, now)
            for _ in range(args.count)
        ]

        db.add_all(records)
        db.commit()

        print(f"Inserted {len(records)} new shipments into PostgreSQL.")

        for record in records[:5]:
            print(
                f"{record.shipment_id} | "
                f"{record.status} | "
                f"SAR {record.shipment_value_sar}"
            )

        if len(records) > 5:
            print(f"...and {len(records) - 5} more.")


if __name__ == "__main__":
    main()
