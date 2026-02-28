"""
core/services/fiscal/sefaz_client.py

Comunicação com os WebServices da SEFAZ via SOAP (Zeep).
Suporta NF-e (55) e NFC-e (65), produção e homologação.

Dependências:
    pip install nfelib==2.3.0 xsdata zeep requests lxml cryptography

Uso:
    from core.services.fiscal.sefaz_client import transmitir, cancelar, consultar_status

    resultado = transmitir(invoice, xml_assinado)
    resultado = cancelar(invoice, justificativa)
    resultado = consultar_status(invoice)
"""

from __future__ import annotations
import time
from datetime import datetime, timezone


# ─────────────────────────────────────────────────────────────────────────────
# URLS DOS WEBSERVICES POR UF / MODELO / AMBIENTE
# Fonte: Manual de Orientação do Contribuinte NT 2023.001
# ─────────────────────────────────────────────────────────────────────────────

# SEFAZ Virtual do RSIL (RS) atende as UFs sem servidor próprio
_SVRS_UFS = {
    'AC','AL','AP','DF','ES','PB','PI','RJ','RN','RO','RR','SC','SE','TO'
}
# SEFAZ Virtual Nacional (SVC-AN) — contingência
_SVC_AN_UFS = {
    'AC','AL','AP','CE','DF','ES','MA','PB','PE','PI','RJ','RN','RO','RR','SC','SE','TO'
}

_URLS = {
    # NF-e (55)
    '55': {
        'producao': {
            'SP': 'https://nfe.fazenda.sp.gov.br/ws',
            'MG': 'https://nfe.fazenda.mg.gov.br/nfe/services',
            'PR': 'https://nfe.fazenda.pr.gov.br/nfe/services',
            'RS': 'https://nfe.sefazrs.rs.gov.br/ws',
            'MT': 'https://nfe.sefaz.mt.gov.br/ws',
            'MS': 'https://nfe.sefaz.ms.gov.br/ws',
            'GO': 'https://nfe.sefaz.go.gov.br/nfe/services',
            'BA': 'https://nfe.sefaz.ba.gov.br/webservices',
            'AM': 'https://nfe.sefaz.am.gov.br/services/services',
            'MA': 'https://www.sefazvirtual.fazenda.gov.br/NFeAutorizacao4',
            'PE': 'https://nfe.sefaz.pe.gov.br/nfe-service',
            'CE': 'https://nfe.sefaz.ce.gov.br/nfe4/services',
            'PA': 'https://www.sefa.pa.gov.br/nfe/services',
            # SVRS para UFs sem servidor próprio
            'SVRS': 'https://nfe.svrs.rs.gov.br/ws',
        },
        'homologacao': {
            'SP': 'https://homologacao.nfe.fazenda.sp.gov.br/ws',
            'MG': 'https://hnfe.fazenda.mg.gov.br/nfe/services',
            'PR': 'https://homologacao.nfe.fazenda.pr.gov.br/nfe/services',
            'RS': 'https://nfe-homologacao.sefazrs.rs.gov.br/ws',
            'MT': 'https://homologacao.nfe.sefaz.mt.gov.br/ws',
            'MS': 'https://homologacao.nfe.sefaz.ms.gov.br/ws',
            'GO': 'https://homologacao.nfe.sefaz.go.gov.br/nfe/services',
            'BA': 'https://hnfe.sefaz.ba.gov.br/webservices',
            'AM': 'https://homnfe.sefaz.am.gov.br/services/services',
            # SVRS homologação
            'SVRS': 'https://homologacao.nfe.svrs.rs.gov.br/ws',
        },
    },
    # NFC-e (65)
    '65': {
        'producao': {
            'SP': 'https://nfce.fazenda.sp.gov.br/ws',
            'PR': 'https://nfce.fazenda.pr.gov.br/nfce/services',
            'RS': 'https://nfce.sefazrs.rs.gov.br/ws',
            'MG': 'https://nfce.fazenda.mg.gov.br/nfce/services',
            'MT': 'https://nfce.sefaz.mt.gov.br/ws',
            'MS': 'https://nfce.sefaz.ms.gov.br/ws',
            'GO': 'https://nfce.sefaz.go.gov.br/nfce/services',
            'BA': 'https://nfce.sefaz.ba.gov.br/webservices',
            'AM': 'https://nfce.sefaz.am.gov.br/services/services',
            'SVRS': 'https://nfce.svrs.rs.gov.br/ws',
        },
        'homologacao': {
            'SP': 'https://homologacao.nfce.fazenda.sp.gov.br/ws',
            'PR': 'https://homologacao.nfce.fazenda.pr.gov.br/nfce/services',
            'RS': 'https://homologacao.nfce.sefazrs.rs.gov.br/ws',
            'MG': 'https://hnfce.fazenda.mg.gov.br/nfce/services',
            'SVRS': 'https://homologacao.nfce.svrs.rs.gov.br/ws',
        },
    },
}


def _base_url(uf: str, modelo: str, ambiente: str) -> str:
    """Retorna a URL base do WS da SEFAZ para a UF/modelo/ambiente."""
    env_key = 'producao' if ambiente == '1' else 'homologacao'
    urls    = _URLS.get(modelo, _URLS['55']).get(env_key, {})
    url     = urls.get(uf)

    if not url:
        # UF sem servidor próprio → SVRS
        url = urls.get('SVRS', '')

    return url


# ─────────────────────────────────────────────────────────────────────────────
# MONTAGEM DO CONTEXTO SSL (certificado A1)
# ─────────────────────────────────────────────────────────────────────────────

def _ssl_context(business):
    """
    Cria um contexto SSL com o certificado PFX da empresa para usar no Zeep.
    Usa arquivos temporários (necessário para zeep/requests).
    """
    import ssl
    import tempfile
    from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
    from cryptography.hazmat.backends import default_backend

    cert_file = business.certificate_file
    cert_file.seek(0)
    pfx_data = cert_file.read()
    senha    = (business.certificate_password or '').encode()

    privkey, cert, chain = pkcs12.load_key_and_certificates(
        pfx_data, senha, backend=default_backend()
    )

    # Exporta para PEM
    pem_key  = privkey.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
    pem_cert = cert.public_bytes(Encoding.PEM)

    # Arquivos temporários (zeep precisa de path)
    tmp_key  = tempfile.NamedTemporaryFile(delete=False, suffix='.pem')
    tmp_cert = tempfile.NamedTemporaryFile(delete=False, suffix='.pem')

    tmp_key.write(pem_key)
    tmp_key.flush()
    tmp_cert.write(pem_cert)
    tmp_cert.flush()

    return tmp_cert.name, tmp_key.name


def _limpar_tmp(*paths):
    import os
    for p in paths:
        try:
            os.unlink(p)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# RESULTADO PADRÃO
# ─────────────────────────────────────────────────────────────────────────────

def _resultado(sucesso: bool, codigo: str, mensagem: str,
               protocolo: str = '', xml_ret: str = '') -> dict:
    return {
        'sucesso':   sucesso,
        'codigo':    codigo,
        'mensagem':  mensagem,
        'protocolo': protocolo,
        'xml_ret':   xml_ret,
    }


# ─────────────────────────────────────────────────────────────────────────────
# TRANSMISSÃO (NFeAutorizacao4 — síncrona para NFC-e, assíncrona para NF-e)
# ─────────────────────────────────────────────────────────────────────────────

def transmitir(invoice, xml_assinado: str) -> dict:
    """
    Transmite a NF-e/NFC-e para a SEFAZ.

    NFC-e (65): usa modo síncrono (indSinc=1) — resposta imediata.
    NF-e  (55): usa modo assíncrono (indSinc=0) — depois consulta o recibo.

    Atualiza invoice.status, invoice.protocol, invoice.xml_sent, invoice.xml_return.

    Returns:
        dict: {sucesso, codigo, mensagem, protocolo, xml_ret}
    """
    import requests
    from lxml import etree
    from core.models import InvoiceStatus, InvoiceLog

    business  = invoice.order.business
    uf        = invoice.emit_state
    modelo    = invoice.model
    ambiente  = invoice.environment
    base_url  = _base_url(uf, modelo, ambiente)

    if not base_url:
        return _resultado(False, '999', f'URL do WS não encontrada para UF {uf}')

    # Endpoint de autorização
    ws_url    = f'{base_url}/NFeAutorizacao4'
    wsdl_url  = f'{ws_url}?wsdl'

    cert_path, key_path = _ssl_context(business)

    inicio = time.time()

    try:
        from zeep import Client
        from zeep.transports import Transport
        from requests import Session

        session = Session()
        session.cert = (cert_path, key_path)
        session.verify = True   # Valida certificado SEFAZ (ICP-Brasil)

        transport = Transport(session=session, timeout=30)
        client    = Client(wsdl=wsdl_url, transport=transport)

        # Cabeçalho SOAP
        cabec_msg = f'<nfeCabecMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4">' \
                    f'<cUF>{_cUF_from_state(uf)}</cUF>' \
                    f'<versaoDados>4.00</versaoDados>' \
                    f'</nfeCabecMsg>'

        # Monta envio em lote
        ind_sinc = '1' if modelo == '65' else '0'
        id_lote  = datetime.now().strftime('%Y%m%d%H%M%S') + '1'

        env_xml = (
            f'<enviNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">'
            f'<idLote>{id_lote}</idLote>'
            f'<indSinc>{ind_sinc}</indSinc>'
            f'{xml_assinado}'
            f'</enviNFe>'
        )

        # Chama o WS
        resposta = client.service.nfeAutorizacaoLote(
            nfeDadosMsg=etree.fromstring(env_xml.encode()),
        )

        xml_ret  = etree.tostring(resposta, encoding='unicode')
        duracao  = int((time.time() - inicio) * 1000)

        # Parseia o retorno
        ret = _parsear_retorno_autorizacao(xml_ret)

        # ── Atualiza Invoice ──────────────────────────────────────────────
        invoice.xml_sent   = xml_assinado
        invoice.xml_return = xml_ret

        if ret['autorizado']:
            invoice.status        = InvoiceStatus.AUTORIZADA
            invoice.protocol      = ret['protocolo']
            invoice.authorized_at = datetime.now(tz=timezone.utc)
            invoice.return_code   = ret['cStat']
            invoice.return_message = ret['xMotivo']
            invoice.save(update_fields=[
                'status', 'protocol', 'authorized_at',
                'return_code', 'return_message',
                'xml_sent', 'xml_return'
            ])

            # Atualiza também Orders com a chave e protocolo
            invoice.order.access_key = invoice.access_key
            invoice.order.protocol   = ret['protocolo']
            invoice.order.xml        = xml_assinado
            invoice.order.save(update_fields=['access_key', 'protocol', 'xml'])

        elif ret['rejeitada']:
            invoice.status        = InvoiceStatus.REJEITADA
            invoice.return_code   = ret['cStat']
            invoice.return_message = ret['xMotivo']
            invoice.save(update_fields=[
                'status', 'return_code', 'return_message',
                'xml_sent', 'xml_return'
            ])

        else:
            # Em processamento (NF-e assíncrona)
            invoice.status = InvoiceStatus.PENDENTE
            invoice.save(update_fields=['status', 'xml_sent', 'xml_return'])

        # ── Log ───────────────────────────────────────────────────────────
        InvoiceLog.objects.create(
            invoice     = invoice,
            action      = InvoiceLog.Action.TRANSMIT,
            result      = InvoiceLog.Result.SUCCESS if ret['autorizado'] else InvoiceLog.Result.ERROR,
            return_code = ret['cStat'],
            message     = ret['xMotivo'],
            xml_sent    = xml_assinado[:5000],
            xml_return  = xml_ret[:5000],
            duration_ms = duracao,
        )

        return _resultado(
            sucesso   = ret['autorizado'],
            codigo    = ret['cStat'],
            mensagem  = ret['xMotivo'],
            protocolo = ret['protocolo'],
            xml_ret   = xml_ret,
        )

    except Exception as e:
        duracao = int((time.time() - inicio) * 1000)

        invoice.status        = InvoiceStatus.REJEITADA
        invoice.return_code   = '999'
        invoice.return_message = str(e)
        invoice.save(update_fields=['status', 'return_code', 'return_message'])

        InvoiceLog.objects.create(
            invoice     = invoice,
            action      = InvoiceLog.Action.TRANSMIT,
            result      = InvoiceLog.Result.ERROR,
            return_code = '999',
            message     = str(e)[:500],
            detail      = str(e),
            duration_ms = duracao,
        )

        return _resultado(False, '999', f'Erro de comunicação: {str(e)}')

    finally:
        _limpar_tmp(cert_path, key_path)


# ─────────────────────────────────────────────────────────────────────────────
# CONSULTA DE STATUS
# ─────────────────────────────────────────────────────────────────────────────

def consultar_status(invoice) -> dict:
    """
    Consulta o status de uma NF-e na SEFAZ pelo número do recibo (modo assíncrono)
    ou pela chave de acesso.

    Returns:
        dict: {sucesso, codigo, mensagem, protocolo, xml_ret}
    """
    from lxml import etree
    from zeep import Client
    from zeep.transports import Transport
    from requests import Session
    from core.models import InvoiceStatus, InvoiceLog

    business = invoice.order.business
    uf       = invoice.emit_state
    modelo   = invoice.model
    ambiente = invoice.environment
    base_url = _base_url(uf, modelo, ambiente)

    ws_url   = f'{base_url}/NFeConsultaProtocolo4'
    wsdl_url = f'{ws_url}?wsdl'

    cert_path, key_path = _ssl_context(business)
    inicio = time.time()

    try:
        session = Session()
        session.cert = (cert_path, key_path)
        session.verify = True

        transport = Transport(session=session, timeout=30)
        client    = Client(wsdl=wsdl_url, transport=transport)

        cons_xml = (
            f'<consSitNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">'
            f'<tpAmb>{ambiente}</tpAmb>'
            f'<xServ>CONSULTAR</xServ>'
            f'<chNFe>{invoice.access_key}</chNFe>'
            f'</consSitNFe>'
        )

        resposta = client.service.nfeConsultaNF(
            nfeDadosMsg=etree.fromstring(cons_xml.encode())
        )

        xml_ret = etree.tostring(resposta, encoding='unicode')
        duracao = int((time.time() - inicio) * 1000)

        ret = _parsear_retorno_consulta(xml_ret)

        if ret['autorizado']:
            invoice.status        = InvoiceStatus.AUTORIZADA
            invoice.protocol      = ret['protocolo']
            invoice.authorized_at = datetime.now(tz=timezone.utc)
            invoice.return_code   = ret['cStat']
            invoice.return_message = ret['xMotivo']
            invoice.save(update_fields=[
                'status', 'protocol', 'authorized_at',
                'return_code', 'return_message', 'xml_return'
            ])

        InvoiceLog.objects.create(
            invoice     = invoice,
            action      = InvoiceLog.Action.QUERY,
            result      = InvoiceLog.Result.SUCCESS,
            return_code = ret['cStat'],
            message     = ret['xMotivo'],
            xml_return  = xml_ret[:5000],
            duration_ms = duracao,
        )

        return _resultado(ret['autorizado'], ret['cStat'], ret['xMotivo'], ret['protocolo'], xml_ret)

    except Exception as e:
        InvoiceLog.objects.create(
            invoice = invoice,
            action  = InvoiceLog.Action.QUERY,
            result  = InvoiceLog.Result.ERROR,
            message = str(e)[:500],
            detail  = str(e),
        )
        return _resultado(False, '999', f'Erro ao consultar: {str(e)}')

    finally:
        _limpar_tmp(cert_path, key_path)


# ─────────────────────────────────────────────────────────────────────────────
# CANCELAMENTO (Evento 110111)
# ─────────────────────────────────────────────────────────────────────────────

def cancelar(invoice, justificativa: str) -> dict:
    """
    Envia evento de cancelamento para a SEFAZ.

    Args:
        invoice:        Invoice AUTORIZADA
        justificativa:  Texto com mínimo 15 e máximo 255 caracteres

    Returns:
        dict: {sucesso, codigo, mensagem, protocolo, xml_ret}
    """
    from lxml import etree
    from zeep import Client
    from zeep.transports import Transport
    from requests import Session
    from core.models import InvoiceStatus, InvoiceEvent, InvoiceLog

    if len(justificativa) < 15:
        return _resultado(False, '999', 'Justificativa deve ter no mínimo 15 caracteres.')

    if invoice.status != InvoiceStatus.AUTORIZADA:
        return _resultado(False, '999', 'Somente notas AUTORIZADAS podem ser canceladas.')

    business = invoice.order.business
    uf       = invoice.emit_state
    modelo   = invoice.model
    ambiente = invoice.environment
    base_url = _base_url(uf, modelo, ambiente)

    ws_url   = f'{base_url}/NFeRecepcaoEvento4'
    wsdl_url = f'{ws_url}?wsdl'

    cert_path, key_path = _ssl_context(business)
    inicio = time.time()

    try:
        dh_evento   = datetime.now(tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%S-03:00')
        id_evento   = f'ID110111{invoice.access_key}01'
        cuf         = _cUF_from_state(uf)
        cnpj        = invoice.emit_cnpj

        evento_xml = (
            f'<evento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00">'
            f'<infEvento Id="{id_evento}">'
            f'<cOrgao>{cuf}</cOrgao>'
            f'<tpAmb>{ambiente}</tpAmb>'
            f'<CNPJ>{cnpj}</CNPJ>'
            f'<chNFe>{invoice.access_key}</chNFe>'
            f'<dhEvento>{dh_evento}</dhEvento>'
            f'<tpEvento>110111</tpEvento>'
            f'<nSeqEvento>1</nSeqEvento>'
            f'<verEvento>1.00</verEvento>'
            f'<detEvento versao="1.00">'
            f'<descEvento>Cancelamento</descEvento>'
            f'<nProt>{invoice.protocol}</nProt>'
            f'<xJust>{justificativa[:255]}</xJust>'
            f'</detEvento>'
            f'</infEvento>'
            f'</evento>'
        )

        # Assina o XML do evento com o mesmo certificado
        from core.services.fiscal.signer import assinar_xml as _sign

        # Usa nfelib para assinar o evento
        from nfelib.nfe.bindings.v4_0 import nfe_v4_00 as nfe_schema
        pfx_data = business.certificate_file.read()
        senha    = business.certificate_password or ''
        nfe_obj  = nfe_schema.TNFe.from_xml(b'<NFe/>')   # placeholder
        evento_assinado = nfe_obj.sign_xml(
            evento_xml.encode(), pfx_data, senha, id_evento
        )

        # Monta envio de evento
        id_lote = datetime.now().strftime('%Y%m%d%H%M%S') + '1'
        env_eventos = (
            f'<envEvento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00">'
            f'<idLote>{id_lote}</idLote>'
            f'{evento_assinado if isinstance(evento_assinado, str) else evento_assinado.decode()}'
            f'</envEvento>'
        )

        session = Session()
        session.cert = (cert_path, key_path)
        session.verify = True

        transport = Transport(session=session, timeout=30)
        client    = Client(wsdl=wsdl_url, transport=transport)

        resposta  = client.service.nfeRecepcaoEvento(
            nfeDadosMsg=etree.fromstring(env_eventos.encode())
        )

        xml_ret = etree.tostring(resposta, encoding='unicode')
        duracao = int((time.time() - inicio) * 1000)

        ret = _parsear_retorno_evento(xml_ret)

        if ret['sucesso']:
            invoice.status     = InvoiceStatus.CANCELADA
            invoice.xml_cancel = xml_ret
            invoice.save(update_fields=['status', 'xml_cancel'])

            InvoiceEvent.objects.create(
                invoice        = invoice,
                event_type     = '110111',
                justification  = justificativa,
                event_protocol = ret['protocolo'],
                return_code    = ret['cStat'],
                return_message = ret['xMotivo'],
                xml_event      = evento_xml,
                xml_return     = xml_ret,
            )

        InvoiceLog.objects.create(
            invoice     = invoice,
            action      = InvoiceLog.Action.CANCEL,
            result      = InvoiceLog.Result.SUCCESS if ret['sucesso'] else InvoiceLog.Result.ERROR,
            return_code = ret['cStat'],
            message     = ret['xMotivo'],
            xml_return  = xml_ret[:5000],
            duration_ms = duracao,
        )

        return _resultado(ret['sucesso'], ret['cStat'], ret['xMotivo'], ret['protocolo'], xml_ret)

    except Exception as e:
        InvoiceLog.objects.create(
            invoice = invoice,
            action  = InvoiceLog.Action.CANCEL,
            result  = InvoiceLog.Result.ERROR,
            message = str(e)[:500],
            detail  = str(e),
        )
        return _resultado(False, '999', f'Erro ao cancelar: {str(e)}')

    finally:
        _limpar_tmp(cert_path, key_path)


# ─────────────────────────────────────────────────────────────────────────────
# PARSERS DE RETORNO XML
# ─────────────────────────────────────────────────────────────────────────────

def _parsear_retorno_autorizacao(xml_ret: str) -> dict:
    """Parseia o retorno do NFeAutorizacao4."""
    from lxml import etree
    ns = 'http://www.portalfiscal.inf.br/nfe'

    try:
        root     = etree.fromstring(xml_ret.encode())
        c_stat   = root.findtext(f'.//{{{ns}}}cStat', '000')
        x_motivo = root.findtext(f'.//{{{ns}}}xMotivo', 'Sem descrição')
        protocolo = root.findtext(f'.//{{{ns}}}nProt', '')

        # 100 = Uso Autorizado, 150 = Autorizado fora do prazo
        autorizado = c_stat in ('100', '150')
        # 2xx = Rejeições, 5xx = Denegadas
        rejeitada  = c_stat.startswith('2') or c_stat.startswith('5') or c_stat.startswith('7')

        return {
            'cStat':      c_stat,
            'xMotivo':    x_motivo,
            'protocolo':  protocolo,
            'autorizado': autorizado,
            'rejeitada':  rejeitada,
        }
    except Exception as e:
        return {'cStat': '999', 'xMotivo': str(e), 'protocolo': '',
                'autorizado': False, 'rejeitada': True}


def _parsear_retorno_consulta(xml_ret: str) -> dict:
    """Parseia o retorno do NFeConsultaProtocolo4."""
    from lxml import etree
    ns = 'http://www.portalfiscal.inf.br/nfe'

    try:
        root      = etree.fromstring(xml_ret.encode())
        c_stat    = root.findtext(f'.//{{{ns}}}cStat', '000')
        x_motivo  = root.findtext(f'.//{{{ns}}}xMotivo', '')
        protocolo = root.findtext(f'.//{{{ns}}}nProt', '')
        return {
            'cStat':      c_stat,
            'xMotivo':    x_motivo,
            'protocolo':  protocolo,
            'autorizado': c_stat in ('100', '150'),
        }
    except Exception as e:
        return {'cStat': '999', 'xMotivo': str(e), 'protocolo': '', 'autorizado': False}


def _parsear_retorno_evento(xml_ret: str) -> dict:
    """Parseia o retorno do NFeRecepcaoEvento4."""
    from lxml import etree
    ns = 'http://www.portalfiscal.inf.br/nfe'

    try:
        root      = etree.fromstring(xml_ret.encode())
        c_stat    = root.findtext(f'.//{{{ns}}}cStat', '000')
        x_motivo  = root.findtext(f'.//{{{ns}}}xMotivo', '')
        protocolo = root.findtext(f'.//{{{ns}}}nProt', '')
        # 135 = Evento Registrado e Vinculado a NF-e
        return {
            'cStat':     c_stat,
            'xMotivo':   x_motivo,
            'protocolo': protocolo,
            'sucesso':   c_stat == '135',
        }
    except Exception as e:
        return {'cStat': '999', 'xMotivo': str(e), 'protocolo': '', 'sucesso': False}


# ─────────────────────────────────────────────────────────────────────────────
# HELPER cUF
# ─────────────────────────────────────────────────────────────────────────────

def _cUF_from_state(uf: str) -> str:
    _map = {
        'AC': '12','AL': '27','AP': '16','AM': '13','BA': '29',
        'CE': '23','DF': '53','ES': '32','GO': '52','MA': '21',
        'MT': '51','MS': '50','MG': '31','PA': '15','PB': '25',
        'PR': '41','PE': '26','PI': '22','RJ': '33','RN': '24',
        'RS': '43','RO': '11','RR': '14','SC': '42','SP': '35',
        'SE': '28','TO': '17',
    }
    return _map.get(uf.upper(), '35')