from django.core.management.base import BaseCommand
from core.models import ProductVariant
import random


class Command(BaseCommand):
    help = "Gera SKU e EAN13 para variantes existentes"

    def handle(self, *args, **kwargs):

        variants = ProductVariant.objects.filter(
            ean13__isnull=True
        ) | ProductVariant.objects.filter(
            ean13=''
        )

        total = 0

        for variant in variants.distinct():

            # 🔹 SKU inteligente
            variant.sku = f"{variant.product.business.id}-{variant.product.id}-{variant.size_id or 0}-{variant.color_id or 0}"

            # 🔹 EAN Brasil (prefixo 789)
            base = "789" + str(random.randint(100000000, 999999999))
            variant.ean13 = self.generate_ean13(base[:12])

            variant.save()
            total += 1

        self.stdout.write(self.style.SUCCESS(f"{total} variantes atualizadas!"))


    def generate_ean13(self, base):
        soma = 0
        for i, digit in enumerate(base):
            digit = int(digit)
            soma += digit if i % 2 == 0 else digit * 3

        resto = soma % 10
        dv = 0 if resto == 0 else 10 - resto

        return base + str(dv)
