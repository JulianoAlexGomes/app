"""
fiscal/services/nf_generator.py

Lógica para gerar Invoice + InvoiceItem + InvoicePayment + InvoiceTransport
a partir de um Orders (pedido) já faturado (status=FATURADO).

Uso na view:
    from fiscal.services.nf_generator import gerar_nota_fiscal
    nf = gerar_nota_fiscal(order=order, usuario=request.user)

O modelo (NF-e 55 / NFC-e 65) já está gravado em Orders.document_model.
"""

import random
import string
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from core.models import (
    Invoice, InvoiceItem, InvoicePayment, InvoiceTransport,
    InvoiceLog, InvoiceStatus,
)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _gerar_codigo_nf() -> str:
    """cNF: 8 dígitos numéricos aleatórios (campo obrigatório no XML)."""
    return ''.join(random.choices(string.digits, k=8))


def _proximo_numero(business, modelo) -> int:
    """
    Incrementa atomicamente o último número emitido em Business.
    nfe_last_number / nfce_last_number — já existem no model Business.
    O número da NF é last_number + 1.
    """
    from core.models import Business
    # select_for_update garante sem duplicidade em ambiente concorrente
    biz = Business.objects.select_for_update().get(pk=business.pk)

    if modelo == '55':
        numero = biz.nfe_last_number + 1
        biz.nfe_last_number = numero
        biz.save(update_fields=['nfe_last_number'])
    else:
        numero = biz.nfce_last_number + 1
        biz.nfce_last_number = numero
        biz.save(update_fields=['nfce_last_number'])

    return numero


def _serie(business, modelo: str) -> str:
    """Retorna a série correta conforme o modelo."""
    return business.nfe_series if modelo == '55' else business.nfce_series


def _strip(valor: str) -> str:
    """Remove qualquer caractere não-dígito (para CNPJ, CPF, CEP, fone)."""
    return ''.join(filter(str.isdigit, valor or ''))


def _tax_regime_str(regime_int: int) -> str:
    """Converte Business.tax_regime (int) para string do XML (1, 2 ou 3)."""
    return str(regime_int)


# ─────────────────────────────────────────────────────────────────────────────
# SNAPSHOT DO EMITENTE (Business → Invoice emit_*)
# ─────────────────────────────────────────────────────────────────────────────

def _snapshot_emitente(business) -> dict:
    return dict(
        emit_name         = business.name,
        emit_fantasy      = business.fantasy_name or '',
        emit_cnpj         = _strip(business.document),
        emit_ie           = business.state_registration or '',
        emit_im           = business.municipal_registration or '',
        emit_tax_regime   = _tax_regime_str(business.tax_regime),
        emit_street       = business.street,
        emit_number       = str(business.number),
        emit_complement   = business.complement or '',
        emit_district     = business.district,
        emit_city         = business.city,
        emit_city_code    = str(business.city_code),
        emit_state        = business.state,
        emit_zip_code     = _strip(business.zip_code),
        emit_country_code = business.country_code or '1058',
        emit_phone        = _strip(business.phone or ''),
    )


# ─────────────────────────────────────────────────────────────────────────────
# SNAPSHOT DO DESTINATÁRIO (Client → Invoice dest_*)
# ─────────────────────────────────────────────────────────────────────────────

def _snapshot_destinatario(order) -> dict:
    client = order.client

    if not client:
        # NFC-e sem identificação de consumidor — campos em branco
        return dict(dest_name='CONSUMIDOR NAO IDENTIFICADO')

    doc = _strip(client.document or '')
    # Define CPF ou CNPJ pelo tamanho do documento
    dest_cnpj = doc if len(doc) == 14 else ''
    dest_cpf  = doc if len(doc) == 11 else ''

    # Indicador IE → Client.taxpayer_type (já tem os mesmos valores: 1, 2, 9)
    if client.is_exempt:
        ind_ie = '2'
    else:
        ind_ie = client.taxpayer_type or '9'

    return dict(
        dest_name          = client.name,
        dest_cnpj          = dest_cnpj,
        dest_cpf           = dest_cpf,
        dest_ie            = client.state_registration or '',
        dest_taxpayer_type = ind_ie,
        dest_email         = client.email or '',
        dest_phone         = _strip(client.phone or ''),
        dest_street        = client.street or '',
        dest_number        = client.number or '',
        dest_complement    = client.complement or '',
        dest_neighborhood  = client.neighborhood or '',
        dest_city          = client.city or '',
        dest_city_code     = client.city_ibge or '',   # Client.city_ibge
        dest_state         = client.state or '',
        dest_zip_code      = _strip(client.zip_code or ''),
        dest_country_code  = client.country_ibge or '1058',
        dest_country       = client.country or 'Brasil',
    )


# ─────────────────────────────────────────────────────────────────────────────
# GERAÇÃO DOS ITENS (OrderItem → InvoiceItem)
# ─────────────────────────────────────────────────────────────────────────────

def _gerar_itens(invoice: Invoice, order):
    """
    Converte cada OrderItem em InvoiceItem.
    Os campos fiscais (icms_cst, icms_csosn, icms_rate, etc.) já estão
    preenchidos pelo apply_fiscal_rules quando o pedido foi salvo.
    """
    for idx, item in enumerate(order.items.select_related(
        'variant', 'variant__product', 'variant__product__ncm'
    ).order_by('id'), start=1):

        variant = item.variant
        product = variant.product if variant else None
        ncm_obj = product.ncm if product else None

        qtd        = Decimal(str(item.quantity))
        preco      = Decimal(str(item.price))
        desconto   = Decimal(str(item.discount or 0))
        acrescimo  = Decimal(str(item.addition or 0))
        total_bruto = (qtd * preco).quantize(Decimal('0.01'))

        InvoiceItem.objects.create(
            invoice      = invoice,
            order_item   = item,
            item_number  = idx,

            # Produto
            product_code = variant.sku if variant else str(item.pk),
            ean          = (variant.ean13 or 'SEM GTIN') if variant else 'SEM GTIN',
            description  = product.name if product else f'Item {idx}',
            ncm          = item.ncm or (ncm_obj.code if ncm_obj else '00000000'),
            cest         = (ncm_obj.cest or '') if ncm_obj else '',
            cfop         = item.cfop or '',
            unit         = 'UN',
            origin       = product.origin if product else '0',

            # Valores
            quantity     = qtd,
            unit_price   = preco,
            gross_total  = total_bruto,
            discount     = desconto,
            addition     = acrescimo,

            # ICMS — dados já calculados pelo apply_fiscal_rules
            icms_cst     = item.icms_cst or '',
            icms_csosn   = item.icms_csosn or '',
            icms_bc      = Decimal(str(item.icms_base or 0)),
            icms_rate    = Decimal(str(item.icms_rate or 0)),
            icms_value   = Decimal(str(item.icms_value or 0)),

            # PIS
            pis_cst      = item.pis_cst or '',
            pis_bc       = Decimal(str(item.subtotal)),
            pis_rate     = Decimal(str(item.pis_rate or 0)),
            pis_value    = Decimal(str(item.pis_value or 0)),

            # COFINS
            cofins_cst   = item.cofins_cst or '',
            cofins_bc    = Decimal(str(item.subtotal)),
            cofins_rate  = Decimal(str(item.cofins_rate or 0)),
            cofins_value = Decimal(str(item.cofins_value or 0)),
        )


# ─────────────────────────────────────────────────────────────────────────────
# GERAÇÃO DOS PAGAMENTOS (OrderPayment → InvoicePayment)
# ─────────────────────────────────────────────────────────────────────────────

def _gerar_pagamentos(invoice: Invoice, order):
    """
    Converte cada OrderPayment em InvoicePayment.
    PaymentMethod.payment_type já tem os códigos numéricos inteiros
    que mapeiam direto para os códigos de 2 dígitos do XML SEFAZ.
    """
    # Mapeamento PaymentMethod.payment_type (int) → código SEFAZ (str 2 dígitos)
    type_map = {
        1: '01', 2: '02', 3: '03', 4: '04', 5: '05',
        10: '10', 11: '11', 12: '12', 13: '13', 14: '14',
        15: '15', 16: '16', 17: '17', 90: '90', 99: '99',
    }

    pagamentos = order.payments.select_related('payment_method').all()

    if not pagamentos.exists():
        # Fallback: pagamento "Outros" com valor total
        InvoicePayment.objects.create(
            invoice      = invoice,
            payment_code = '99',
            value        = invoice.total_nf,
        )
        return

    for pag in pagamentos:
        payment_type = pag.payment_method.payment_type if pag.payment_method else 99
        codigo = type_map.get(payment_type, '99')

        InvoicePayment.objects.create(
            invoice       = invoice,
            order_payment = pag,
            payment_code  = codigo,
            value         = Decimal(str(pag.total_value)),
        )


# ─────────────────────────────────────────────────────────────────────────────
# GERAÇÃO DO FRETE (Orders.freight_mode → InvoiceTransport)
# ─────────────────────────────────────────────────────────────────────────────

def _gerar_transporte(invoice: Invoice, order):
    """
    Orders.freight_mode já usa os mesmos códigos do XML (0-4, 9).
    """
    InvoiceTransport.objects.create(
        invoice      = invoice,
        freight_mode = order.freight_mode or '9',
    )


# ─────────────────────────────────────────────────────────────────────────────
# CÁLCULO DOS TOTAIS
# ─────────────────────────────────────────────────────────────────────────────

def _calcular_totais(invoice: Invoice):
    """Soma os itens e atualiza os totais do cabeçalho da Invoice."""
    from django.db.models import Sum

    itens = invoice.items.all()

    def soma(campo):
        return itens.aggregate(t=Sum(campo))['t'] or Decimal('0')

    total_produtos = soma('gross_total') - soma('discount') + soma('addition')
    total_icms     = soma('icms_value')
    total_bc_icms  = soma('icms_bc')
    total_st       = soma('icms_st_value')
    total_bc_st    = soma('icms_st_bc')
    total_pis      = soma('pis_value')
    total_cofins   = soma('cofins_value')
    total_frete    = soma('freight')
    total_seguro   = soma('insurance')
    total_outros   = soma('other')
    total_desconto = soma('discount')

    total_nf = total_produtos + total_frete + total_seguro + total_outros + total_st

    invoice.total_products = total_produtos
    invoice.total_discount = total_desconto
    invoice.total_freight  = total_frete
    invoice.total_insurance = total_seguro
    invoice.total_other    = total_outros
    invoice.total_bc_icms  = total_bc_icms
    invoice.total_icms     = total_icms
    invoice.total_bc_st    = total_bc_st
    invoice.total_icms_st  = total_st
    invoice.total_pis      = total_pis
    invoice.total_cofins   = total_cofins
    invoice.total_nf       = total_nf

    invoice.save(update_fields=[
        'total_products', 'total_discount', 'total_freight', 'total_insurance',
        'total_other', 'total_bc_icms', 'total_icms', 'total_bc_st',
        'total_icms_st', 'total_pis', 'total_cofins', 'total_nf',
    ])


# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÃO PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

@transaction.atomic
def gerar_nota_fiscal(order, usuario=None) -> Invoice:
    """
    Gera todos os registros de NF a partir de um Orders faturado.

    Args:
        order:   instância de core.Orders com status=FATURADO
        usuario: request.user para auditoria

    Returns:
        Invoice criada com status=RASCUNHO, pronta para visualização/edição

    Raises:
        ValueError: pedido não faturado ou sem modelo de documento
        ValueError: NF ativa já existe para este pedido
    """
    from core.models import Orders

    # ── Validações ────────────────────────────────────────────────────────
    if order.status != Orders.STATUS_FATURADO:
        raise ValueError('O pedido precisa estar com status FATURADO para gerar NF.')

    if not order.document_model:
        raise ValueError('O pedido não possui modelo de documento (NF-e/NFC-e) definido.')

    nf_existente = Invoice.objects.filter(
        order=order,
        model=order.document_model,
        status__in=[InvoiceStatus.RASCUNHO, InvoiceStatus.PENDENTE, InvoiceStatus.AUTORIZADA]
    ).first()

    if nf_existente:
        raise ValueError(
            f'Já existe uma {nf_existente.get_model_display()} '
            f'({nf_existente.get_status_display()}) para este pedido. '
            f'NF {nf_existente.serie}/{nf_existente.number}'
        )

    if not order.items.exists():
        raise ValueError('O pedido não possui itens.')

    business = order.business
    modelo   = order.document_model

    # Injeta o modelo no business para o helper _proximo_numero saber qual usar
    # business._nfe_model = modelo

    serie  = _serie(business, modelo)
    numero = _proximo_numero(business, modelo)

    # ── Snapshot emitente + destinatário ──────────────────────────────────
    emit = _snapshot_emitente(business)
    dest = _snapshot_destinatario(order)

    # ── Cria o cabeçalho da Invoice ───────────────────────────────────────
    invoice = Invoice.objects.create(
        order              = order,
        model              = modelo,
        serie              = serie,
        number             = numero,
        code_nf            = _gerar_codigo_nf(),
        environment        = str(business.nfe_environment),
        issue_date         = timezone.now(),
        exit_date          = order.issue_datetime or timezone.now(),
        nature_operation   = order.nature_operation or 'VENDA DE MERCADORIA',
        finality           = order.finality or '1',
        presence_indicator = order.presence_indicator or '0',
        status             = InvoiceStatus.RASCUNHO,
        created_by         = usuario,
        **emit,
        **dest,
    )

    # ── Gera os filhos ────────────────────────────────────────────────────
    _gerar_itens(invoice, order)
    _calcular_totais(invoice)
    _gerar_transporte(invoice, order)
    _gerar_pagamentos(invoice, order)

    # ── Log de geração ────────────────────────────────────────────────────
    InvoiceLog.objects.create(
        invoice    = invoice,
        action     = InvoiceLog.Action.GENERATE,
        result     = InvoiceLog.Result.SUCCESS,
        message    = (
            f'{invoice.get_model_display()} {serie}/{numero} gerada com sucesso '
            f'a partir do Pedido #{order.pk}.'
        ),
        created_by = usuario,
    )

    return invoice


# ─────────────────────────────────────────────────────────────────────────────
# RECALCULO MANUAL — chamado após edição dos itens na tela de NF
# ─────────────────────────────────────────────────────────────────────────────

def recalcular_totais(invoice: Invoice):
    """Permite recalcular totais após edição manual dos itens da NF."""
    _calcular_totais(invoice)