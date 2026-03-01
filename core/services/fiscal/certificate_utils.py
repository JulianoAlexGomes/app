"""
core/services/fiscal/certificate_utils.py

Utilitários para:
  - Ler o certificado PFX de forma robusta (FileField, base64, path, bytes)
  - Criptografar/descriptografar a senha no banco com Fernet (AES-128-CBC)
  - Diagnosticar problemas no certificado
  - Migrar senhas já gravadas em texto puro

Dependências:
    pip install cryptography  (já instalada)

Configuração obrigatória em settings.py:
    CERTIFICATE_ENCRYPTION_KEY = Fernet.generate_key().decode()
    # Gere uma vez com: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # Guarde em variável de ambiente, nunca no código!

Uso:
    from core.services.fiscal.certificate_utils import (
        ler_pfx, encrypt_password, decrypt_password, diagnosticar_certificado
    )
"""

from __future__ import annotations
import base64
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# CHAVE DE CRIPTOGRAFIA
# ─────────────────────────────────────────────────────────────────────────────

def _get_fernet():
    """Retorna instância Fernet usando CERTIFICATE_ENCRYPTION_KEY do settings."""
    from django.conf import settings
    from cryptography.fernet import Fernet

    key = getattr(settings, 'CERTIFICATE_ENCRYPTION_KEY', None)
    if not key:
        raise RuntimeError(
            'settings.CERTIFICATE_ENCRYPTION_KEY não configurada.\n'
            'Gere com: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


# ─────────────────────────────────────────────────────────────────────────────
# CRIPTOGRAFIA DE SENHA
# ─────────────────────────────────────────────────────────────────────────────

def encrypt_password(plain_password: str) -> str:
    """
    Criptografa a senha do certificado com Fernet (AES-128-CBC + HMAC).
    O resultado é uma string base64url segura para gravar em CharField.

    Uso:
        business.certificate_password = encrypt_password(senha_digitada)
        business.save()
    """
    if not plain_password:
        return ''
    f = _get_fernet()
    return f.encrypt(plain_password.encode('utf-8')).decode('utf-8')


def decrypt_password(encrypted_password: str) -> str:
    """
    Descriptografa a senha do certificado.
    Retorna a senha em texto puro para uso na assinatura.

    Compatível com senhas ainda em texto puro (antes da migração):
    tenta descriptografar; se falhar, assume que ainda é texto puro.
    """
    if not encrypted_password:
        return ''
    try:
        f = _get_fernet()
        return f.decrypt(encrypted_password.encode('utf-8')).decode('utf-8')
    except Exception:
        # Senha ainda em texto puro (período de migração)
        return encrypted_password


def is_password_encrypted(password: str) -> bool:
    """Verifica se uma senha já está criptografada com Fernet."""
    if not password:
        return False
    try:
        _get_fernet().decrypt(password.encode('utf-8'))
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# LEITURA ROBUSTA DO PFX
# ─────────────────────────────────────────────────────────────────────────────

def ler_pfx(business) -> tuple[bytes, str]:
    """
    Lê o arquivo PFX e a senha de forma robusta.

    Trata todos os casos possíveis:
      - FileField (FieldFile / InMemoryUploadedFile / S3Boto3StorageFile)
      - Senha criptografada com Fernet ou ainda em texto puro
      - Arquivo armazenado em base64
      - Arquivo armazenado como texto (raro, mas acontece)

    Returns:
        (pfx_bytes, senha_plain)

    Raises:
        ValueError: certificado não cadastrado
        RuntimeError: não foi possível ler os bytes do PFX
    """
    if not business.certificate_file:
        raise ValueError(
            f'Empresa "{business.name}" não possui certificado digital cadastrado. '
            'Acesse Empresa → Editar e faça o upload do arquivo .pfx'
        )

    # ── Lê os bytes do arquivo ────────────────────────────────────────────
    raw: bytes = _read_file_bytes(business.certificate_file)

    # ── Detecta e decodifica base64 (caso o arquivo tenha sido salvo em b64) ──
    pfx_bytes = _normalizar_pfx_bytes(raw)

    # ── Descriptografa a senha ────────────────────────────────────────────
    senha = decrypt_password(business.certificate_password or '')

    return pfx_bytes, senha


def _read_file_bytes(field) -> bytes:
    """Lê bytes de um FileField/FieldFile/InMemoryUploadedFile/S3."""
    # Caso 1: já é bytes
    if isinstance(field, (bytes, bytearray)):
        return bytes(field)

    # Caso 2: é string (path ou conteúdo texto — raro)
    if isinstance(field, str):
        import os
        if os.path.exists(field):
            with open(field, 'rb') as f:
                return f.read()
        # Pode ser conteúdo em base64
        try:
            return base64.b64decode(field)
        except Exception:
            raise RuntimeError(f'certificate_file é uma string mas não é um path válido nem base64: {field[:50]}')

    # Caso 3: FileField / FieldFile / InMemoryUploadedFile / S3
    try:
        # Sempre volta ao início antes de ler
        if hasattr(field, 'seek'):
            try:
                field.seek(0)
            except Exception:
                pass  # Alguns storages não suportam seek mas tudo bem

        if hasattr(field, 'read'):
            data = field.read()
            if isinstance(data, str):
                # Storage abriu em modo texto — tenta reabrir em binário
                try:
                    field.seek(0)
                    with field.open('rb') as f:
                        return f.read()
                except Exception:
                    raise RuntimeError('FileField retornou string em vez de bytes. '
                                       'Verifique o storage backend.')
            return data

        # Caso 4: tem .path (FieldFile local)
        if hasattr(field, 'path'):
            with open(field.path, 'rb') as f:
                return f.read()

    except (AttributeError, TypeError):
        pass

    raise RuntimeError(
        f'Não foi possível ler bytes do certificate_file. '
        f'Tipo recebido: {type(field).__name__}'
    )


def _normalizar_pfx_bytes(raw: bytes) -> bytes:
    """
    PKCS#12 começa com 0x30 (tag DER SEQUENCE).
    Se o arquivo foi salvo em base64, decodifica.
    """
    if not raw:
        raise RuntimeError('Arquivo de certificado está vazio.')

    # Se começa com 0x30 → é DER direto
    if raw[0] == 0x30:
        return raw

    # Tenta decodificar como base64
    try:
        decoded = base64.b64decode(raw)
        if decoded[0] == 0x30:
            return decoded
    except Exception:
        pass

    # Tenta remover whitespace e decodificar
    try:
        decoded = base64.b64decode(raw.strip())
        if decoded[0] == 0x30:
            return decoded
    except Exception:
        pass

    # Retorna como está e deixa o pkcs12 reclamar com mensagem melhor
    return raw


# ─────────────────────────────────────────────────────────────────────────────
# CARREGAR PKCS12 COM TENTATIVAS DE SENHA
# ─────────────────────────────────────────────────────────────────────────────

def carregar_pkcs12(pfx_bytes: bytes, senha: str):
    """
    Carrega o PKCS12 tentando variações de senha para maximizar compatibilidade.

    Tenta em ordem:
      1. Senha como UTF-8
      2. Senha como Latin-1 (ISO-8859-1) — certificados mais antigos
      3. Senha como bytes raw (sem encoding)
      4. Sem senha (None) — certificados sem proteção

    Returns:
        (private_key, cert, chain)

    Raises:
        ValueError com mensagem detalhada se todas as tentativas falharem
    """
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.hazmat.backends import default_backend

    tentativas = []

    # Prepara variações de encoding da senha
    if senha:
        tentativas.append(('UTF-8',    senha.encode('utf-8')))
        tentativas.append(('Latin-1',  senha.encode('latin-1')))
        tentativas.append(('bytes raw', senha.encode('utf-8').decode('latin-1').encode('latin-1')))
    tentativas.append(('sem senha', None))
    tentativas.append(('vazia',     b''))

    erros = []
    for descricao, senha_bytes in tentativas:
        try:
            privkey, cert, chain = pkcs12.load_key_and_certificates(
                pfx_bytes, senha_bytes, backend=default_backend()
            )
            return privkey, cert, chain
        except Exception as e:
            erros.append(f'  [{descricao}]: {e}')

    raise ValueError(
        'Não foi possível abrir o certificado com nenhuma variação de senha.\n'
        'Erros por tentativa:\n' + '\n'.join(erros) + '\n\n'
        'Verifique: (1) se a senha está correta, (2) se o arquivo .pfx não está corrompido, '
        '(3) se o certificado não usa algoritmos legados (RC2/3DES — use openssl para converter).'
    )


# ─────────────────────────────────────────────────────────────────────────────
# DIAGNÓSTICO COMPLETO
# ─────────────────────────────────────────────────────────────────────────────

def diagnosticar_certificado(business) -> dict:
    """
    Diagnóstico completo do certificado digital.
    Útil para exibir na tela de configuração da empresa.

    Returns:
        dict com: valido, expiracao, dias_restantes, nome, cnpj_cert,
                  algoritmo, tamanho_bits, mensagem, erros[]
    """
    from cryptography.hazmat.primitives.serialization import Encoding
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives.asymmetric import rsa, ec
    from datetime import date

    erros = []
    resultado = {
        'valido':          False,
        'expiracao':       None,
        'dias_restantes':  None,
        'nome':            None,
        'cnpj_cert':       None,
        'algoritmo':       None,
        'tamanho_bits':    None,
        'senha_criptografada': False,
        'arquivo_ok':      False,
        'mensagem':        '',
        'erros':           erros,
    }

    # 1. Lê arquivo
    try:
        pfx_bytes, senha = ler_pfx(business)
        resultado['arquivo_ok'] = True
        resultado['tamanho_arquivo'] = len(pfx_bytes)
        resultado['primeiro_byte'] = hex(pfx_bytes[0]) if pfx_bytes else 'vazio'
    except Exception as e:
        erros.append(f'Erro ao ler arquivo: {e}')
        resultado['mensagem'] = str(e)
        return resultado

    # 2. Verifica se senha está criptografada
    resultado['senha_criptografada'] = is_password_encrypted(business.certificate_password or '')

    # 3. Carrega PKCS12
    try:
        privkey, cert, chain = carregar_pkcs12(pfx_bytes, senha)
    except ValueError as e:
        erros.append(str(e))
        resultado['mensagem'] = 'Falha ao abrir o PKCS12. Verifique senha e arquivo.'
        return resultado

    # 4. Extrai informações do certificado
    try:
        expiracao      = cert.not_valid_after.date()
        hoje           = date.today()
        dias_restantes = (expiracao - hoje).days

        # Nome (CN)
        cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        nome = cn[0].value if cn else 'N/A'

        # CNPJ (serialNumber ou CN pode conter)
        serial_attrs = cert.subject.get_attributes_for_oid(NameOID.SERIAL_NUMBER)
        cnpj_cert = serial_attrs[0].value if serial_attrs else None
        if not cnpj_cert:
            # Tenta extrair do CN (formato "NOME:CNPJ")
            if ':' in nome:
                cnpj_cert = nome.split(':')[-1].strip()

        # Algoritmo da chave
        if isinstance(privkey, rsa.RSAPrivateKey):
            algoritmo   = 'RSA'
            tamanho_bits = privkey.key_size
        elif isinstance(privkey, ec.EllipticCurvePrivateKey):
            algoritmo   = 'EC'
            tamanho_bits = privkey.key_size
        else:
            algoritmo    = type(privkey).__name__
            tamanho_bits = None

        resultado.update({
            'valido':         dias_restantes > 0,
            'expiracao':      expiracao,
            'dias_restantes': dias_restantes,
            'nome':           nome,
            'cnpj_cert':      cnpj_cert,
            'algoritmo':      algoritmo,
            'tamanho_bits':   tamanho_bits,
            'mensagem': (
                f'Certificado válido até {expiracao.strftime("%d/%m/%Y")} '
                f'({dias_restantes} dias restantes)'
                if dias_restantes > 0
                else f'⚠️ Certificado VENCIDO em {expiracao.strftime("%d/%m/%Y")}'
            ),
        })

        if dias_restantes <= 30:
            erros.append(f'Certificado vence em {dias_restantes} dias — providencie a renovação.')

    except Exception as e:
        erros.append(f'Erro ao extrair informações do certificado: {e}')
        resultado['mensagem'] = str(e)

    return resultado


# ─────────────────────────────────────────────────────────────────────────────
# MIGRAÇÃO: criptografar senhas já gravadas em texto puro
# ─────────────────────────────────────────────────────────────────────────────

def migrar_senhas_para_criptografadas():
    """
    Utilitário de management command: criptografa todas as senhas de certificado
    que ainda estão em texto puro no banco.

    Chame via:
        from core.services.fiscal.certificate_utils import migrar_senhas_para_criptografadas
        migrar_senhas_para_criptografadas()

    Ou crie um management command:
        python manage.py migrar_certificados
    """
    from core.models import Business  # ajuste para o seu model

    migradas = 0
    erros    = 0

    for business in Business.objects.exclude(certificate_password='').exclude(certificate_password=None):
        senha = business.certificate_password
        if not is_password_encrypted(senha):
            try:
                business.certificate_password = encrypt_password(senha)
                business.save(update_fields=['certificate_password'])
                migradas += 1
                print(f'✅ {business.name}: senha criptografada')
            except Exception as e:
                erros += 1
                print(f'❌ {business.name}: erro ao criptografar — {e}')

    print(f'\nMigração concluída: {migradas} senhas criptografadas, {erros} erros.')
    return migradas, erros