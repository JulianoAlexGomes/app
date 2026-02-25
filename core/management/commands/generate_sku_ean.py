from django.core.management.base import BaseCommand
from core.models import ProductVariant
import random


class Command(BaseCommand):
    help = 'Regera SKU para todas as variantes e cria EAN13 quando não existir'

    def handle(self, *args, **kwargs):
        variants = ProductVariant.objects.select_related(
            'product',
            'product__business',
            'size',
            'color'
        )

        total = 0

        for variant in variants:

            # 🔹 GERAR SKU PADRÃO MULTI-EMPRESA
            business_id = variant.product.business.id
            product_id = variant.product.id
            size_id = variant.size.id if variant.size else 0
            color_id = variant.color.id if variant.color else 0

            variant.sku = f"B{business_id}P{product_id}S{size_id}C{color_id}"

            # 🔹 GERAR EAN13 SOMENTE SE NÃO EXISTIR
            if not variant.ean13:
                variant.ean13 = generate_unique_ean13()

            variant.save(update_fields=['sku', 'ean13'])
            total += 1

        self.stdout.write(self.style.SUCCESS(f'{total} variantes atualizadas com sucesso.'))


def generate_unique_ean13():
    """
    Gera um EAN13 único no banco
    """
    while True:
        base = str(random.randint(100000000000, 999999999999))
        ean = generate_ean13(base)

        if not ProductVariant.objects.filter(ean13=ean).exists():
            return ean


def generate_ean13(base):
    """
    Recebe 12 dígitos e calcula o dígito verificador
    """
    base = base[:12]

    soma = 0
    for i, digit in enumerate(base):
        digit = int(digit)
        if i % 2 == 0:
            soma += digit
        else:
            soma += digit * 3

    resto = soma % 10
    dv = 0 if resto == 0 else 10 - resto

    return base + str(dv)
