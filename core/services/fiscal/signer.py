"""
core/services/fiscal/signer.py

Assinatura digital XMLDSig para NF-e/NFC-e com certificado A1 (PFX/P12).
Implementada com lxml + cryptography puras — sem erpbrasil, sem signxml.

Dependências:
    pip install lxml cryptography

Uso:
    from core.services.fiscal.signer import assinar_xml, assinar_xml_evento
    xml_assinado    = assinar_xml(invoice, xml_str)
    evento_assinado = assinar_xml_evento(pfx_bytes, senha, evento_xml, id_evento)
"""

from __future__ import annotations
from lxml import etree

_NS_DS   = 'http://www.w3.org/2000/09/xmldsig#'
_NS_C14N = 'http://www.w3.org/TR/2001/REC-xml-c14n-20010315'


def _assinar(xml_bytes: bytes, pfx_bytes: bytes, senha: str, ref_id: str) -> str:
    """
    Assina um XML NF-e/NFC-e ou Evento seguindo o padrão XMLDSig exigido pela SEFAZ.

    Algoritmos:
      Canonicalização : C14N  (http://www.w3.org/TR/2001/REC-xml-c14n-20010315)
      Transformações  : Enveloped-Signature + C14N
      Digest          : SHA-1  (exigido pelo leiaute NF-e 4.00)
      Assinatura      : RSA-SHA1
    """
    import base64
    import hashlib
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.serialization import Encoding
    from core.services.fiscal.certificate_utils import carregar_pkcs12

    privkey, cert, _chain = carregar_pkcs12(pfx_bytes, senha)
    cert_der = cert.public_bytes(Encoding.DER)

    root = etree.fromstring(xml_bytes)

    # Localiza a tag com Id=ref_id
    tag_ref = None
    for el in root.iter():
        if el.get('Id') == ref_id:
            tag_ref = el
            break
    if tag_ref is None:
        raise ValueError(f'Tag com Id="{ref_id}" não encontrada no XML.')

    # C14N da tag referenciada → DigestValue (SHA-1)
    c14n_bytes = etree.tostring(tag_ref, method='c14n', exclusive=False, with_comments=False)
    digest_b64 = base64.b64encode(hashlib.sha1(c14n_bytes).digest()).decode()

    # Monta <SignedInfo>
    signed_info_xml = (
        f'<SignedInfo xmlns="{_NS_DS}">'
        f'<CanonicalizationMethod Algorithm="{_NS_C14N}"/>'
        f'<SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>'
        f'<Reference URI="#{ref_id}">'
        f'<Transforms>'
        f'<Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>'
        f'<Transform Algorithm="{_NS_C14N}"/>'
        f'</Transforms>'
        f'<DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>'
        f'<DigestValue>{digest_b64}</DigestValue>'
        f'</Reference>'
        f'</SignedInfo>'
    )
    signed_info_el = etree.fromstring(signed_info_xml.encode())

    # C14N do <SignedInfo> → assina RSA-SHA1
    si_c14n = etree.tostring(signed_info_el, method='c14n', exclusive=False, with_comments=False)
    sig_b64 = base64.b64encode(
        privkey.sign(si_c14n, padding.PKCS1v15(), hashes.SHA1())
    ).decode()

    # Injeta <Signature> na tag referenciada
    cert_b64 = base64.b64encode(cert_der).decode()
    tag_ref.append(etree.fromstring((
        f'<Signature xmlns="{_NS_DS}">'
        + signed_info_xml
        + f'<SignatureValue>{sig_b64}</SignatureValue>'
        f'<KeyInfo><X509Data>'
        f'<X509Certificate>{cert_b64}</X509Certificate>'
        f'</X509Data></KeyInfo>'
        f'</Signature>'
    ).encode()))

    return etree.tostring(root, encoding='unicode', xml_declaration=False)


def assinar_xml(invoice, xml_str: str) -> str:
    """Assina digitalmente o XML de uma NF-e ou NFC-e."""
    from core.services.fiscal.certificate_utils import ler_pfx

    pfx_bytes, senha = ler_pfx(invoice.order.business)
    inf_id = f'NFe{invoice.access_key}'

    try:
        return _assinar(
            xml_str.encode() if isinstance(xml_str, str) else xml_str,
            pfx_bytes, senha, inf_id,
        )
    except Exception as e:
        raise Exception(
            f'Erro ao assinar XML da NF {invoice.serie}/{invoice.number}: {str(e)}\n'
            'Verifique se o certificado está correto e não está vencido.'
        ) from e


def assinar_xml_evento(pfx_bytes: bytes, senha: str, evento_xml: str, id_evento: str) -> str:
    """Assina digitalmente o XML de um evento (cancelamento, CCe, etc.)."""
    try:
        return _assinar(
            evento_xml.encode() if isinstance(evento_xml, str) else evento_xml,
            pfx_bytes, senha, id_evento,
        )
    except Exception as e:
        raise Exception(f'Erro ao assinar evento {id_evento}: {str(e)}') from e


def validar_certificado(business) -> dict:
    """Valida o certificado. Delega ao diagnosticar_certificado."""
    from core.services.fiscal.certificate_utils import diagnosticar_certificado
    return diagnosticar_certificado(business)