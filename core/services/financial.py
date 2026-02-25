from models import FinancialMovementParcel
from datetime import timedelta
from decimal import Decimal

def generate_parcels(movement, total, start_date, parcels, interval_days):
    value = (Decimal(total) / parcels).quantize(Decimal("0.01"))

    for i in range(parcels):
        FinancialMovementParcel.objects.create(
            movement=movement,
            parcel=i + 1,
            value=value,
            deadline=start_date + timedelta(days=i * interval_days)
        )
