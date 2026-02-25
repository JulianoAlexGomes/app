from django.db import transaction
from django.core.exceptions import ValidationError
from core.models import OrderItem, StockEntry
from django.core.exceptions import ValidationError
from django.db import transaction
from core.models import StockEntry, ProductVariant, colorchart
from django.db.models import Sum
from core.models import generate_sku, generate_ean13 
from django.core.exceptions import ValidationError
from core.models import StockEntry, ProductVariant
from django.db.models import Sum


def reserve_stock(order):
    for item in order.items.select_related('variant', 'variant__product'):
        if item.reserved:
            continue

        available = item.variant.stock_available

        if available < item.quantity:
            raise ValidationError(
                f'Estoque insuficiente para {item.variant}. '
                f'Disponível: {available}'
            )

        StockEntry.objects.create(
            variant=item.variant,  # ✅ agora é variant
            order_item=item,
            entry_type=None,
            movement_type=StockEntry.MovementType.RESERVE,
            quantity=item.quantity
        )

        item.reserved = True
        item.save(update_fields=['reserved'])


def release_stock(order):
    for item in order.items.select_related('variant', 'variant__product'):
        if not item.reserved:
            continue

        StockEntry.objects.create(
            variant=item.variant,
            order_item=item,
            entry_type=None,
            movement_type=StockEntry.MovementType.RELEASE,
            quantity=item.quantity
        )

        item.reserved = False
        item.save(update_fields=['reserved'])


def finalize_stock(order):
    for item in order.items.select_related('variant', 'variant__product'):

        # 🔹 Se estava reservado, libera logicamente
        if item.reserved:
            StockEntry.objects.create(
                variant=item.variant,
                order_item=item,
                entry_type=None,
                movement_type=StockEntry.MovementType.RELEASE,
                quantity=item.quantity
            )

            item.reserved = False
            item.save(update_fields=['reserved'])

        # 🔥 Saída física real
        StockEntry.objects.create(
            variant=item.variant,
            order_item=item,
            entry_type='out',
            movement_type=StockEntry.MovementType.SALE,
            quantity=item.quantity
        )

def create_variants(product):

    if not product.color:
        return

    sizes = product.size.sizes.all() if product.size else [None]

    for size in sizes:

        variant, created = ProductVariant.objects.get_or_create(
            product=product,
            size=size,
            color=product.color
        )

        # 🔹 Se acabou de criar, gera SKU e EAN
        if created:

            # Primeiro salva para garantir ID
            variant.save()

            # Gera SKU
            variant.sku = generate_sku(variant)
            variant.save()

            # Gera EAN13 (precisa do ID da variante)
            variant.ean13 = generate_ean13(variant)
            variant.save()
