"""
core/services/fiscal/signer.py

Assinatura digital do XML NF-e/NFC-e com certificado A1 (PFX/P12).
Usa a API nativa da nfelib 2.3 que já encapsula o erpbrasil.assinatura.

Dependências:
    pip install nfelib==2.3.0 xsdata lxml

Uso:
    from core.services.fiscal.signer import assinar_xml
    xml_assinado = assinar_xml(invoice, xml_str)
"""

from __future__ import annotations
import os
from pathlib import Path


def _carregar_certificado(business) -> tuple[bytes, str]:
    """
    Carrega o PFX do certificado e a senha a partir do model Business.

    Business.certificate_file → FileField (upload_to='certificates/')
    Business.certificate_password → CharField

    Retorna (pfx_bytes, senha_str)
    """
    if not business.certificate_file:
        raise ValueError(
            f'Empresa "{business.name}" não possui certificado digital cadastrado. '
            'Acesse Empresa → Editar e faça o upload do arquivo .pfx'
        )

    # Lê o arquivo do storage (funciona com FileField local e S3)
    cert_file = business.certificate_file
    cert_file.seek(0)
    pfx_data = cert_file.read()

    senha = business.certificate_password or ''

    return pfx_data, senha


def assinar_xml(invoice, xml_str: str) -> str:
    """
    Assina digitalmente o XML usando o certificado A1 da empresa.

    Args:
        invoice:  instância de core.Invoice
        xml_str:  XML não assinado gerado por xml_builder.build_xml()

    Returns:
        str: XML assinado digitalmente

    Raises:
        ValueError: certificado não cadastrado ou senha inválida
        Exception:  erros de assinatura (certificado vencido, etc.)
    """
    from nfelib.nfe.bindings.v4_0 import nfe_v4_00 as nfe_schema

    business = invoice.order.business
    pfx_data, senha = _carregar_certificado(business)

    # ID da tag a ser assinada: infNFe para NF-e/NFC-e
    inf_id = f'NFe{invoice.access_key}'

    try:
        # nfelib 2.3 expõe sign_xml diretamente no módulo de bindings
        # Carrega o objeto a partir do XML string para usar o método sign_xml
        nfe_obj = nfe_schema.TNFe.from_xml(xml_str.encode())

        xml_assinado = nfe_obj.sign_xml(
            xml_str.encode(),
            pfx_data,
            senha,
            inf_id,
        )

        # Retorna como string
        if isinstance(xml_assinado, bytes):
            return xml_assinado.decode('utf-8')
        return xml_assinado

    except Exception as e:
        raise Exception(
            f'Erro ao assinar XML da NF {invoice.serie}/{invoice.number}: {str(e)}\n'
            'Verifique se o certificado está correto e não está vencido.'
        ) from e


def validar_certificado(business) -> dict:
    """
    Valida o certificado digital cadastrado na empresa.

    Returns:
        dict com: valido (bool), expiracao (date), cnpj (str), mensagem (str)
    """
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.hazmat.backends import default_backend
    from datetime import date

    try:
        pfx_data, senha = _carregar_certificado(business)
        senha_bytes = senha.encode() if isinstance(senha, str) else senha

        privkey, cert, _ = pkcs12.load_key_and_certificates(
            pfx_data, senha_bytes, backend=default_backend()
        )

        expiracao  = cert.not_valid_after.date()
        subject    = cert.subject
        cn         = subject.get_attributes_for_oid(
            __import__('cryptography.x509.oid', fromlist=['NameOID']).NameOID.COMMON_NAME
        )
        nome_cert  = cn[0].value if cn else 'N/A'
        hoje       = date.today()
        dias_restantes = (expiracao - hoje).days

        return {
            'valido':          dias_restantes > 0,
            'expiracao':       expiracao,
            'dias_restantes':  dias_restantes,
            'nome':            nome_cert,
            'mensagem': (
                f'Certificado válido até {expiracao.strftime("%d/%m/%Y")} '
                f'({dias_restantes} dias restantes)'
                if dias_restantes > 0
                else f'Certificado VENCIDO em {expiracao.strftime("%d/%m/%Y")}'
            )
        }

    except ValueError as e:
        return {'valido': False, 'mensagem': str(e)}
    except Exception as e:
        return {
            'valido':   False,
            'mensagem': f'Erro ao ler certificado: {str(e)}'
        }