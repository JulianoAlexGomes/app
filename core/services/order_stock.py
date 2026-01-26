from django.db import transaction
from django.core.exceptions import ValidationError
from core.models import OrderItem, StockEntry
from django.core.exceptions import ValidationError
from django.db import transaction
from core.models import StockEntry
from django.db.models import Sum

@transaction.atomic
def reserve_stock(order):
    for item in order.items.select_related('product'):

        # 🔐 evita reserva duplicada
        if StockEntry.objects.filter(
            order_item=item,
            movement_type=StockEntry.MovementType.RESERVE
        ).exists():
            continue

        product = item.product
        qty = item.quantity

        if product.stock_available < qty:
            raise ValidationError(
                f'Estoque insuficiente para {product.name}. '
                f'Disponível: {product.stock_available}'
            )

        StockEntry.objects.create(
            product=product,
            order_item=item,
            entry_type='out',
            movement_type=StockEntry.MovementType.RESERVE,
            quantity=qty
        )

@transaction.atomic
def release_stock(order):
    for item in order.items.select_related('product'):

        reserved = StockEntry.objects.filter(
            order_item=item,
            movement_type=StockEntry.MovementType.RESERVE
        ).aggregate(total=Sum('quantity'))['total'] or 0

        released = StockEntry.objects.filter(
            order_item=item,
            movement_type=StockEntry.MovementType.RELEASE
        ).aggregate(total=Sum('quantity'))['total'] or 0

        to_release = reserved - released

        if to_release <= 0:
            continue

        StockEntry.objects.create(
            product=item.product,
            order_item=item,
            entry_type='in',
            movement_type=StockEntry.MovementType.RELEASE,
            quantity=to_release
        )


@transaction.atomic
def finalize_stock(order):
    for item in order.items.select_related('product'):

        # libera reserva pendente
        release_stock(order)

        # saída definitiva
        StockEntry.objects.create(
            product=item.product,
            order_item=item,
            entry_type='out',
            movement_type=StockEntry.MovementType.SALE,
            quantity=item.quantity
        )
