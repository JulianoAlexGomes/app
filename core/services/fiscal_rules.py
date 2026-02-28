"""
services/fiscal.py

Serviço de resolução de regras fiscais para itens de pedido.

Fluxo:
  1. Recebe um OrderItem (já com variant/quantity/price)
  2. Identifica o NCM do produto
  3. Localiza a FiscalOperation correta (modelo NF + NCM no grupo)
  4. Busca a alíquota ICMS pela tabela ICMSOriginDestination
  5. Calcula bases e valores de ICMS, PIS e COFINS
  6. Grava tudo no OrderItem
  7. Atualiza nature_operation e cfop no cabeçalho Orders
"""

from decimal import Decimal, ROUND_HALF_UP
from core.models import (
    FiscalOperation,
    NCMGroupItem,
    ICMSOriginDestination,
    OrderItem,
    Orders,
)


# ─────────────────────────────────────────────────────────────────────────────
# EXCEÇÕES
# ─────────────────────────────────────────────────────────────────────────────

class FiscalRuleNotFound(Exception):
    """Lançada quando não há FiscalOperation compatível com o item."""
    pass


class ICMSRateNotFound(Exception):
    """Lançada quando não há alíquota ICMS para o par origem/destino."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÃO PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def apply_fiscal_rules(order_item: OrderItem, raise_on_missing: bool = False) -> bool:
    """
    Resolve a regra fiscal do item e grava os campos fiscais.

    Parâmetros
    ----------
    order_item      : instância de OrderItem (com variant e order já vinculados)
    raise_on_missing: se True lança exceção quando não encontrar regra;
                      se False apenas limpa os campos e retorna False

    Retorna
    -------
    True  → regra encontrada e campos gravados
    False → regra não encontrada (campos fiscais zerados/limpos)
    """

    order: Orders = order_item.order
    business = order.business
    product = order_item.variant.product

    # ── 1. NCM do produto ────────────────────────────────────────────────────
    ncm = product.ncm
    if not ncm:
        _clear_fiscal_fields(order_item)
        if raise_on_missing:
            raise FiscalRuleNotFound(
                f'Produto "{product.name}" não possui NCM cadastrado.'
            )
        return False

    # ── 2. Modelo do documento (55 = NF-e, 65 = NFC-e) ──────────────────────
    doc_model = order.document_model  # '55' ou '65' (pode ser None)

    # ── 3. Localiza FiscalOperation ──────────────────────────────────────────
    operation = _find_operation(business, ncm, doc_model)

    if not operation:
        _clear_fiscal_fields(order_item)
        if raise_on_missing:
            raise FiscalRuleNotFound(
                f'Nenhuma operação fiscal encontrada para NCM {ncm.code} '
                f'no modelo {doc_model or "qualquer"}.'
            )
        return False

    # ── 4. Base de cálculo = subtotal do item ────────────────────────────────
    base_value = _calc_base(order_item)

    # ── 5. ICMS ──────────────────────────────────────────────────────────────
    icms_rate, icms_base, icms_value = _calc_icms(
        operation, business, order, product, base_value
    )

    # ── 6. PIS ───────────────────────────────────────────────────────────────
    pis_value = _calc_tax(base_value, operation.pis_rate)

    # ── 7. COFINS ────────────────────────────────────────────────────────────
    cofins_value = _calc_tax(base_value, operation.cofins_rate)

    # ── 8. Grava no OrderItem ────────────────────────────────────────────────
    order_item.cfop       = operation.cfop
    order_item.ncm        = ncm.code

    # ICMS
    order_item.icms_cst   = operation.icms_cst
    order_item.icms_csosn = operation.icms_csosn
    order_item.icms_rate  = icms_rate
    order_item.icms_base  = icms_base
    order_item.icms_value = icms_value

    # PIS
    order_item.pis_cst    = operation.pis_cst
    order_item.pis_rate   = operation.pis_rate
    order_item.pis_value  = pis_value

    # COFINS
    order_item.cofins_cst   = operation.cofins_cst
    order_item.cofins_rate  = operation.cofins_rate
    order_item.cofins_value = cofins_value

    # ── 9. Atualiza cabeçalho do pedido ──────────────────────────────────────
    _update_order_header(order, operation)

    return True


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS INTERNOS
# ─────────────────────────────────────────────────────────────────────────────

def _find_operation(business, ncm, doc_model):
    """
    Retorna a primeira FiscalOperation ativa do business cujo NCMGroup
    contém o NCM do produto.

    Prioridade:
      1. Operação com model == doc_model (ex: '55' ou '65')
      2. Qualquer operação ativa (fallback)
    """

    # NCMs dos grupos que contêm este NCM para este business
    group_ids = NCMGroupItem.objects.filter(
        ncm=ncm,
        group__business=business
    ).values_list('group_id', flat=True)

    if not group_ids:
        return None

    qs = FiscalOperation.objects.filter(
        business=business,
        ncm_group_id__in=group_ids,
        active=True
    )

    # Tenta encontrar com o modelo exato primeiro
    if doc_model:
        exact = qs.filter(model=doc_model).first()
        if exact:
            return exact

    # Fallback: qualquer operação ativa para o NCM
    return qs.first()


def _calc_base(order_item: OrderItem) -> Decimal:
    """Retorna a base de cálculo (subtotal do item)."""
    qty   = Decimal(str(order_item.quantity))
    price = Decimal(str(order_item.price))
    disc  = Decimal(str(order_item.discount or 0))
    add   = Decimal(str(order_item.addition or 0))
    return (qty * price) - disc + add


def _calc_icms(operation, business, order, product, base_value):
    """
    Calcula alíquota, base e valor do ICMS.

    - Se operation.calculate_icms == False → retorna zeros
    - Se operation.use_origin_destination_table == True → busca em ICMSOriginDestination
    - Caso contrário → usa 0% (operação não tributada ou regime Simples)
    """

    zero = (Decimal('0.00'), Decimal('0.00'), Decimal('0.00'))

    if not operation.calculate_icms:
        return zero

    rate = Decimal('0.00')

    if operation.use_origin_destination_table:
        origin_state      = business.state
        destination_state = _get_destination_state(order)
        is_imported       = product.origin not in ('0', '3', '4', '5')

        try:
            icms_rule = ICMSOriginDestination.objects.get(
                origin_state=origin_state,
                destination_state=destination_state,
                imported=is_imported
            )
            # Para operações internas usa alíquota interna;
            # para interestaduais usa a interestadual
            if origin_state == destination_state:
                rate = icms_rule.internal_rate
            else:
                rate = icms_rule.interstate_rate

        except ICMSOriginDestination.DoesNotExist:
            # Se não encontrou na tabela, retorna zero sem quebrar
            rate = Decimal('0.00')

    icms_base  = base_value
    icms_value = _calc_tax(icms_base, rate)

    return rate, icms_base, icms_value


def _get_destination_state(order: Orders) -> str:
    """Retorna a UF do destinatário (cliente ou emitente se NFC-e)."""
    # NFC-e (consumidor final, operação interna) → mesmo estado da empresa
    if order.document_model == '65':
        return order.business.state

    # NF-e → estado do cliente
    if order.client and order.client.state:
        return order.client.state

    # Fallback: mesmo estado da empresa (venda interna)
    return order.business.state


def _calc_tax(base: Decimal, rate: Decimal) -> Decimal:
    """Calcula valor do tributo: base × (rate / 100), arredondado em 2 casas."""
    if not rate:
        return Decimal('0.00')
    value = base * (Decimal(str(rate)) / Decimal('100'))
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _clear_fiscal_fields(order_item: OrderItem):
    """Zera todos os campos fiscais quando não há regra aplicável."""
    order_item.cfop         = None
    order_item.ncm          = None

    order_item.icms_cst     = None
    order_item.icms_csosn   = None
    order_item.icms_rate    = Decimal('0.00')
    order_item.icms_base    = Decimal('0.00')
    order_item.icms_value   = Decimal('0.00')

    order_item.pis_cst      = None
    order_item.pis_rate     = Decimal('0.00')
    order_item.pis_value    = Decimal('0.00')

    order_item.cofins_cst   = None
    order_item.cofins_rate  = Decimal('0.00')
    order_item.cofins_value = Decimal('0.00')


def _update_order_header(order: Orders, operation: FiscalOperation):
    """
    Atualiza nature_operation e cfop no cabeçalho do pedido
    apenas se ainda não estiverem preenchidos.
    """
    changed = False

    if not order.nature_operation:
        order.nature_operation = operation.name
        changed = True

    if not order.cfop:
        order.cfop = operation.cfop
        changed = True

    if not order.document_model:
        order.document_model = operation.model
        changed = True

    if changed:
        order.save(update_fields=[
            f for f in ['nature_operation', 'cfop', 'document_model']
            if changed
        ])