"""
core/services/fiscal/xml_builder.py

nfelib 2.3 + xsdata 24.12

Tipos auxiliares corretos:
  enderEmit  → leiaute_nfe_v4_00.TenderEmi
  enderDest  → leiaute_nfe_v4_00.Tendereco
  ICMSTot    → Tnfe.InfNfe.Total.Icmstot
  ICMS/PIS/COFINS → Tnfe.InfNfe.Det.Imposto.Icms / .Pis / .Cofins
"""

from __future__ import annotations
import random
import string
from decimal import Decimal
from datetime import datetime

from nfelib.nfe.bindings.v4_0.nfe_v4_00 import Tnfe
from nfelib.nfe.bindings.v4_0.leiaute_nfe_v4_00 import TenderEmi, Tendereco
from xsdata.formats.dataclass.serializers import XmlSerializer
from xsdata.formats.dataclass.context import XmlContext


# ─── helpers ─────────────────────────────────────────────────────────────────

def _fmt(valor, casas: int = 2) -> str:
    if valor is None:
        return '0.' + '0' * casas
    return f'{Decimal(str(valor)):.{casas}f}'


def _dt(dt: datetime) -> str:
    if not dt:
        dt = datetime.now()
    from django.utils import timezone as tz
    if tz.is_naive(dt):
        dt = tz.make_aware(dt)
    return dt.strftime('%Y-%m-%dT%H:%M:%S') + dt.strftime('%z')[:3] + ':' + dt.strftime('%z')[3:]


def _cUF(uf: str) -> str:
    return {
        'AC':'12','AL':'27','AP':'16','AM':'13','BA':'29','CE':'23','DF':'53',
        'ES':'32','GO':'52','MA':'21','MT':'51','MS':'50','MG':'31','PA':'15',
        'PB':'25','PR':'41','PE':'26','PI':'22','RJ':'33','RN':'24','RS':'43',
        'RO':'11','RR':'14','SC':'42','SP':'35','SE':'28','TO':'17',
    }.get(uf.upper(), '35')


def _calcular_chave(invoice) -> tuple[str, int]:
    aamm    = invoice.issue_date.strftime('%y%m')
    cnpj    = ''.join(filter(str.isdigit, invoice.emit_cnpj)).zfill(14)
    cnf     = (invoice.code_nf or '').zfill(8)
    chave   = (f'{_cUF(invoice.emit_state)}{aamm}{cnpj}{invoice.model}'
               f'{str(invoice.serie).zfill(3)}{str(invoice.number).zfill(9)}'
               f'{invoice.emission_type}{cnf}')
    soma, peso = 0, 2
    for d in reversed(chave):
        soma += int(d) * peso
        peso = peso + 1 if peso < 9 else 2
    r  = soma % 11
    dv = 0 if r < 2 else 11 - r
    return chave + str(dv), dv


# ─── ICMS ────────────────────────────────────────────────────────────────────

def _build_icms(item):
    Icms = Tnfe.InfNfe.Det.Imposto.Icms

    if item.icms_csosn:
        csosn = item.icms_csosn
        if csosn in ('102', '300', '400', '500'):
            return Icms(ICMSSN102=Icms.Icmssn102(orig=item.origin, CSOSN=csosn))
        if csosn == '101':
            return Icms(ICMSSN101=Icms.Icmssn101(
                orig=item.origin, CSOSN='101',
                pCredSN=_fmt(item.sn_credit_rate, 4),
                vCredICMSSN=_fmt(item.sn_credit_value),
            ))
        if csosn == '900':
            return Icms(ICMSSN900=Icms.Icmssn900(
                orig=item.origin, CSOSN='900', modBC='3',
                vBC=_fmt(item.icms_bc), pICMS=_fmt(item.icms_rate, 4),
                vICMS=_fmt(item.icms_value),
                pCredSN=_fmt(item.sn_credit_rate, 4),
                vCredICMSSN=_fmt(item.sn_credit_value),
            ))
        return Icms(ICMSSN500=Icms.Icmssn500(orig=item.origin, CSOSN=csosn))

    cst = item.icms_cst or '40'
    if cst == '00':
        return Icms(ICMS00=Icms.Icms00(
            orig=item.origin, CST='00', modBC='3',
            vBC=_fmt(item.icms_bc), pICMS=_fmt(item.icms_rate, 4),
            vICMS=_fmt(item.icms_value),
        ))
    if cst == '10':
        return Icms(ICMS10=Icms.Icms10(
            orig=item.origin, CST='10', modBC='3',
            vBC=_fmt(item.icms_bc), pICMS=_fmt(item.icms_rate, 4),
            vICMS=_fmt(item.icms_value), modBCST='4',
            pMVAST=_fmt(item.icms_st_bc), vBCST=_fmt(item.icms_st_bc),
            pICMSST=_fmt(item.icms_st_rate, 4), vICMSST=_fmt(item.icms_st_value),
        ))
    if cst == '20':
        return Icms(ICMS20=Icms.Icms20(
            orig=item.origin, CST='20', modBC='3', pRedBC=_fmt(0, 4),
            vBC=_fmt(item.icms_bc), pICMS=_fmt(item.icms_rate, 4),
            vICMS=_fmt(item.icms_value),
        ))
    if cst == '60':
        return Icms(ICMS60=Icms.Icms60(
            orig=item.origin, CST='60',
            vBCSTRet=_fmt(item.icms_st_bc),
            pST=_fmt(item.icms_st_rate, 4),
            vICMSSTRet=_fmt(item.icms_st_value),
        ))
    return Icms(ICMS40=Icms.Icms40(
        orig=item.origin,
        CST=cst if cst in ('40', '41', '50') else '40',
    ))


# ─── PIS ─────────────────────────────────────────────────────────────────────

def _build_pis(item):
    Pis = Tnfe.InfNfe.Det.Imposto.Pis
    cst = item.pis_cst or '07'
    if cst in ('01', '02'):
        return Pis(PISAliq=Pis.Pisaliq(
            CST=cst, vBC=_fmt(item.pis_bc),
            pPIS=_fmt(item.pis_rate, 4), vPIS=_fmt(item.pis_value),
        ))
    if cst in ('49', '50', '99'):
        return Pis(PISOutr=Pis.Pisoutr(
            CST=cst, vBC=_fmt(item.pis_bc),
            pPIS=_fmt(item.pis_rate, 4), vPIS=_fmt(item.pis_value),
        ))
    return Pis(PISNT=Pis.Pisnt(CST=cst))


# ─── COFINS ──────────────────────────────────────────────────────────────────

def _build_cofins(item):
    Cofins = Tnfe.InfNfe.Det.Imposto.Cofins
    cst = item.cofins_cst or '07'
    if cst in ('01', '02'):
        return Cofins(COFINSAliq=Cofins.Cofinsaliq(
            CST=cst, vBC=_fmt(item.cofins_bc),
            pCOFINS=_fmt(item.cofins_rate, 4), vCOFINS=_fmt(item.cofins_value),
        ))
    if cst in ('49', '50', '99'):
        return Cofins(COFINSOutr=Cofins.Cofinsoutr(
            CST=cst, vBC=_fmt(item.cofins_bc),
            pCOFINS=_fmt(item.cofins_rate, 4), vCOFINS=_fmt(item.cofins_value),
        ))
    return Cofins(COFINSNT=Cofins.Cofinsnt(CST=cst))


# ─── XML principal ────────────────────────────────────────────────────────────

def build_xml(invoice) -> str:
    if not invoice.code_nf:
        invoice.code_nf = ''.join(random.choices(string.digits, k=8))

    chave, dv = _calcular_chave(invoice)
    invoice.access_key = chave
    invoice.dv         = dv
    invoice.save(update_fields=['access_key', 'dv', 'code_nf'])

    # ── Emitente ──────────────────────────────────────────────────────────
    emit = Tnfe.InfNfe.Emit(
        CNPJ      = ''.join(filter(str.isdigit, invoice.emit_cnpj)),
        xNome     = invoice.emit_name[:60],
        xFant     = invoice.emit_fantasy[:60] if invoice.emit_fantasy else None,
        enderEmit = TenderEmi(
            xLgr    = invoice.emit_street[:60],
            nro     = invoice.emit_number[:60],
            xCpl    = invoice.emit_complement[:60] if invoice.emit_complement else None,
            xBairro = invoice.emit_district[:60],
            cMun    = invoice.emit_city_code,
            xMun    = invoice.emit_city[:60],
            UF      = invoice.emit_state,
            CEP     = ''.join(filter(str.isdigit, invoice.emit_zip_code)),
            cPais   = invoice.emit_country_code or '1058',
            xPais   = 'Brasil',
            fone    = invoice.emit_phone or None,
        ),
        IE  = invoice.emit_ie or None,
        IM  = invoice.emit_im or None,
        CRT = str(invoice.emit_tax_regime),
    )

    # ── Destinatário ──────────────────────────────────────────────────────
    dest = None
    if not (invoice.model == '65' and not invoice.dest_cnpj and not invoice.dest_cpf):
        ender_dest = None
        if invoice.dest_street:
            ender_dest = Tendereco(
                xLgr    = invoice.dest_street[:60],
                nro     = (invoice.dest_number or 'SN')[:60],
                xCpl    = invoice.dest_complement[:60] if invoice.dest_complement else None,
                xBairro = (invoice.dest_neighborhood or 'N/A')[:60],
                cMun    = invoice.dest_city_code or '9999999',
                xMun    = (invoice.dest_city or 'N/A')[:60],
                UF      = invoice.dest_state or 'SP',
                CEP     = ''.join(filter(str.isdigit, invoice.dest_zip_code)) if invoice.dest_zip_code else None,
                cPais   = invoice.dest_country_code or '1058',
                xPais   = invoice.dest_country or 'Brasil',
                fone    = invoice.dest_phone or None,
            )
        dest = Tnfe.InfNfe.Dest(
            CNPJ      = invoice.dest_cnpj or None,
            CPF       = invoice.dest_cpf or None,
            xNome     = invoice.dest_name[:60],
            enderDest = ender_dest,
            indIEDest = invoice.dest_taxpayer_type,
            IE        = invoice.dest_ie or None,
            email     = invoice.dest_email or None,
        )

    # ── Itens ─────────────────────────────────────────────────────────────
    det_list = []
    for item in invoice.items.all().order_by('item_number'):
        prod = Tnfe.InfNfe.Det.Prod(
            cProd    = item.product_code[:60],
            cEAN     = item.ean or 'SEM GTIN',
            xProd    = item.description[:120],
            NCM      = item.ncm,
            CEST     = item.cest if item.cest else None,
            CFOP     = item.cfop,
            uCom     = item.unit,
            qCom     = _fmt(item.quantity, 4),
            vUnCom   = _fmt(item.unit_price, 10),
            vProd    = _fmt(item.gross_total),
            cEANTrib = item.ean or 'SEM GTIN',
            uTrib    = item.unit,
            qTrib    = _fmt(item.quantity, 4),
            vUnTrib  = _fmt(item.unit_price, 10),
            vFrete   = _fmt(item.freight)   if item.freight   else None,
            vSeg     = _fmt(item.insurance) if item.insurance else None,
            vDesc    = _fmt(item.discount)  if item.discount  else None,
            vOutro   = _fmt(item.other)     if item.other     else None,
            indTot   = '1',
        )
        imposto = Tnfe.InfNfe.Det.Imposto(
            ICMS   = _build_icms(item),
            PIS    = _build_pis(item),
            COFINS = _build_cofins(item),
        )
        det_list.append(Tnfe.InfNfe.Det(
            nItem     = str(item.item_number),
            prod      = prod,
            imposto   = imposto,
            infAdProd = item.item_info or None,
        ))

    # ── Totais ────────────────────────────────────────────────────────────
    icm_tot = Tnfe.InfNfe.Total.Icmstot(
        vBC        = _fmt(invoice.total_bc_icms),
        vICMS      = _fmt(invoice.total_icms),
        vICMSDeson = '0.00',
        vFCPST     = '0.00',
        vBCST      = _fmt(invoice.total_bc_st),
        vST        = _fmt(invoice.total_icms_st),
        vFCP       = '0.00',
        vProd      = _fmt(invoice.total_products),
        vFrete     = _fmt(invoice.total_freight),
        vSeg       = _fmt(invoice.total_insurance),
        vDesc      = _fmt(invoice.total_discount),
        vII        = '0.00',
        vIPI       = '0.00',
        vIPIDevol  = '0.00',
        vPIS       = _fmt(invoice.total_pis),
        vCOFINS    = _fmt(invoice.total_cofins),
        vOutro     = _fmt(invoice.total_other),
        vNF        = _fmt(invoice.total_nf),
    )
    total = Tnfe.InfNfe.Total(ICMSTot=icm_tot)

    # ── IDE ───────────────────────────────────────────────────────────────
    ide = Tnfe.InfNfe.Ide(
        cUF      = _cUF(invoice.emit_state),
        cNF      = invoice.code_nf.zfill(8),
        natOp    = invoice.nature_operation[:60],
        mod      = invoice.model,
        serie    = str(invoice.serie).zfill(3),
        nNF      = str(invoice.number).zfill(9),
        dhEmi    = _dt(invoice.issue_date),
        dhSaiEnt = _dt(invoice.exit_date) if invoice.exit_date else None,
        tpNF     = invoice.operation_type,
        idDest   = '1',
        cMunFG   = invoice.emit_city_code,
        tpImp    = '4' if invoice.model == '65' else '1',
        tpEmis   = invoice.emission_type,
        cDV      = str(dv),
        tpAmb    = invoice.environment,
        finNFe   = invoice.finality,
        indFinal = '1' if invoice.model == '65' else '0',
        indPres  = invoice.presence_indicator,
        procEmi  = '0',
        verProc  = '1.0',
    )

    # ── Transporte ────────────────────────────────────────────────────────
    try:
        t      = invoice.transport
        transp = Tnfe.InfNfe.Transp(modFrete=t.freight_mode or '9')
        if t.carrier_name:
            transp.transporta = Tnfe.InfNfe.Transp.Transporta(
                xNome  = t.carrier_name,
                CNPJ   = t.carrier_cnpj    or None,
                CPF    = t.carrier_cpf     or None,
                IE     = t.carrier_ie      or None,
                xEnder = t.carrier_address or None,
                xMun   = t.carrier_city    or None,
                UF     = t.carrier_state   or None,
            )
        if t.volume_qty:
            transp.vol = [Tnfe.InfNfe.Transp.Vol(
                qVol  = _fmt(t.volume_qty, 4),
                esp   = t.volume_species    or None,
                marca = t.volume_brand      or None,
                nVol  = t.volume_numbering  or None,
                pesoL = _fmt(t.net_weight, 3)   if t.net_weight   else None,
                pesoB = _fmt(t.gross_weight, 3) if t.gross_weight else None,
            )]
    except Exception:
        transp = Tnfe.InfNfe.Transp(modFrete='9')

    # ── Pagamentos ────────────────────────────────────────────────────────
    det_pag_list = []
    for pag in invoice.payments.all():
        det_pag_list.append(Tnfe.InfNfe.Pag.DetPag(
            tPag = pag.payment_code,
            vPag = _fmt(pag.value),
        ))
    if not det_pag_list:
        det_pag_list.append(Tnfe.InfNfe.Pag.DetPag(
            tPag='90', vPag=_fmt(invoice.total_nf)
        ))
    pag = Tnfe.InfNfe.Pag(detPag=det_pag_list)

    # ── Info adicional ────────────────────────────────────────────────────
    inf_adic = None
    if invoice.additional_info or invoice.fiscal_info:
        inf_adic = Tnfe.InfNfe.InfAdic(
            infCpl   = invoice.additional_info[:5000] if invoice.additional_info else None,
            infFisco = invoice.fiscal_info[:500]      if invoice.fiscal_info     else None,
        )

    # ── Monta NF-e ────────────────────────────────────────────────────────
    inf_nfe = Tnfe.InfNfe(
        Id      = f'NFe{chave}',
        versao  = '4.00',
        ide     = ide,
        emit    = emit,
        dest    = dest,
        det     = det_list,
        total   = total,
        transp  = transp,
        pag     = pag,
        infAdic = inf_adic,
    )
    nfe_obj = Tnfe(infNFe=inf_nfe)

    # ── QR Code NFC-e ─────────────────────────────────────────────────────
    if invoice.model == '65':
        import hashlib
        business  = invoice.order.business
        ambiente  = invoice.environment
        uf        = invoice.emit_state
        env_key   = 'prod' if ambiente == '1' else 'homolog'
        _urls = {
            'prod':    {'RS': 'https://www.sefaz.rs.gov.br/NFCE/NFCE-COM.aspx'},
            'homolog': {'RS': 'https://homologacao.sefaz.rs.gov.br/NFCE/NFCE-COM.aspx'},
        }
        url_base  = _urls[env_key].get(uf, list(_urls[env_key].values())[0])
        csc_id    = str(business.nfce_csc_id or '').zfill(6)
        csc_token = business.nfce_csc or ''
        dh_hex    = invoice.issue_date.strftime('%Y-%m-%dT%H:%M:%S-03:00').encode().hex().upper()
        v_nf      = _fmt(invoice.total_nf)
        v_icms    = _fmt(invoice.total_icms)
        qr_str    = f'{chave}|2|{ambiente}|{dh_hex}|{v_nf}|{v_icms}|{csc_id}{csc_token}'
        c_hash    = hashlib.sha1(qr_str.encode()).hexdigest().upper()
        nfe_obj.infNFeSupl = Tnfe.InfNfeSupl(
            qrCode   = (f'{url_base}?chNFe={chave}&nVersao=2&tpAmb={ambiente}'
                        f'&dhEmi={dh_hex}&vNF={v_nf}&vICMS={v_icms}'
                        f'&digVal=&cIdToken={csc_id}&cHashQRCode={c_hash}'),
            urlChave = f'{url_base}?chNFe={chave}&tpAmb={ambiente}',
        )

    # ── Serializa ─────────────────────────────────────────────────────────
    return XmlSerializer(context=XmlContext()).render(nfe_obj)