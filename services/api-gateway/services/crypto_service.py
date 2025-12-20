"""
Conecta Plus - Serviço de Criptografia
Criptografia de dados sensíveis para conformidade LGPD
"""

import os
import base64
import hashlib
import secrets
from typing import Optional, Tuple, Union
from dataclasses import dataclass
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend


@dataclass
class DadosCriptografados:
    """Estrutura de dados criptografados"""
    dados_encrypted: bytes
    salt: bytes
    hash_verificacao: str


class CryptoService:
    """
    Serviço de Criptografia

    Usa AES-256 via Fernet para criptografia simétrica
    Chave derivada de master key + salt único por registro
    """

    def __init__(self, master_key: Optional[str] = None):
        """
        Inicializa serviço de criptografia

        Args:
            master_key: Chave mestra (32 bytes em base64)
                       Se não fornecida, usa variável de ambiente
        """
        self._master_key = master_key or os.getenv('CRYPTO_MASTER_KEY')

        if not self._master_key:
            # Em desenvolvimento, gera uma chave
            # EM PRODUÇÃO: DEVE SER CONFIGURADA VIA VARIÁVEL DE AMBIENTE
            self._master_key = Fernet.generate_key().decode()
            print("[CRYPTO] ATENÇÃO: Usando chave gerada automaticamente. Configure CRYPTO_MASTER_KEY em produção!")

        # Cache de Fernet instances por salt
        self._fernet_cache = {}

    def _derive_key(self, salt: bytes) -> bytes:
        """Deriva chave de criptografia a partir da master key e salt"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(self._master_key.encode())
        return base64.urlsafe_b64encode(key)

    def _get_fernet(self, salt: bytes) -> Fernet:
        """Obtém instância Fernet para o salt (com cache)"""
        salt_hex = salt.hex()
        if salt_hex not in self._fernet_cache:
            key = self._derive_key(salt)
            self._fernet_cache[salt_hex] = Fernet(key)
        return self._fernet_cache[salt_hex]

    def criptografar(self, dados: str) -> Tuple[bytes, bytes]:
        """
        Criptografa dados

        Args:
            dados: String a ser criptografada

        Returns:
            Tupla (dados_criptografados, salt)
        """
        if not dados:
            return b'', b''

        # Gera salt único
        salt = secrets.token_bytes(16)

        # Obtém Fernet
        fernet = self._get_fernet(salt)

        # Criptografa
        dados_encrypted = fernet.encrypt(dados.encode('utf-8'))

        return dados_encrypted, salt

    def descriptografar(self, dados_encrypted: bytes, salt: bytes) -> Optional[str]:
        """
        Descriptografa dados

        Args:
            dados_encrypted: Dados criptografados
            salt: Salt usado na criptografia

        Returns:
            String original ou None se falhar
        """
        if not dados_encrypted or not salt:
            return None

        try:
            fernet = self._get_fernet(salt)
            dados = fernet.decrypt(dados_encrypted)
            return dados.decode('utf-8')
        except InvalidToken:
            return None
        except Exception:
            return None

    def hash_documento(self, documento: str) -> str:
        """
        Gera hash de documento para busca

        Usa SHA-256 com salt fixo para permitir busca
        O salt é derivado da master key (não do documento)

        Args:
            documento: CPF/CNPJ

        Returns:
            Hash hexadecimal
        """
        # Remove formatação
        doc_limpo = ''.join(filter(str.isdigit, documento))

        # Usa parte da master key como salt fixo
        salt = hashlib.sha256(self._master_key.encode()).digest()[:16]

        # Hash com salt
        hash_obj = hashlib.sha256(salt + doc_limpo.encode())
        return hash_obj.hexdigest()

    def criptografar_campo(self, valor: str) -> dict:
        """
        Criptografa um campo e retorna dict com dados e salt

        Args:
            valor: Valor a criptografar

        Returns:
            Dict com 'encrypted' e 'salt' em base64
        """
        if not valor:
            return {'encrypted': None, 'salt': None}

        dados_enc, salt = self.criptografar(valor)

        return {
            'encrypted': base64.b64encode(dados_enc).decode('ascii'),
            'salt': base64.b64encode(salt).decode('ascii')
        }

    def descriptografar_campo(self, campo_dict: dict) -> Optional[str]:
        """
        Descriptografa um campo de dict

        Args:
            campo_dict: Dict com 'encrypted' e 'salt' em base64

        Returns:
            Valor original ou None
        """
        if not campo_dict:
            return None

        encrypted = campo_dict.get('encrypted')
        salt = campo_dict.get('salt')

        if not encrypted or not salt:
            return None

        try:
            dados_enc = base64.b64decode(encrypted)
            salt_bytes = base64.b64decode(salt)
            return self.descriptografar(dados_enc, salt_bytes)
        except Exception:
            return None


class FieldEncryptor:
    """
    Classe auxiliar para criptografia de campos específicos

    Uso:
        encryptor = FieldEncryptor(crypto_service)
        dados_seguros = encryptor.encrypt_boleto_fields(dados_boleto)
    """

    # Campos que devem ser criptografados por entidade
    CAMPOS_SENSIVEIS = {
        'boleto': [
            'pagador_documento',
            'pagador_endereco',
            'pagador_email',
            'pagador_telefone'
        ],
        'morador': [
            'cpf',
            'rg',
            'email',
            'telefone',
            'endereco'
        ],
        'banco': [
            'conta',
            'agencia',
            'chave_pix',
            'api_key',
            'api_secret'
        ]
    }

    def __init__(self, crypto_service: CryptoService):
        self.crypto = crypto_service

    def encrypt_fields(self, dados: dict, tipo_entidade: str) -> dict:
        """
        Criptografa campos sensíveis de uma entidade

        Args:
            dados: Dicionário com dados
            tipo_entidade: Tipo da entidade (boleto, morador, banco)

        Returns:
            Dicionário com campos sensíveis criptografados
        """
        campos_sensiveis = self.CAMPOS_SENSIVEIS.get(tipo_entidade, [])
        resultado = dados.copy()

        for campo in campos_sensiveis:
            if campo in resultado and resultado[campo]:
                valor = resultado[campo]

                # Criptografa
                encrypted, salt = self.crypto.criptografar(str(valor))

                # Substitui por versão criptografada
                resultado[f'{campo}_encrypted'] = encrypted
                resultado[f'{campo}_salt'] = salt

                # Gera hash para busca (apenas para documentos)
                if 'documento' in campo or campo in ['cpf', 'cnpj']:
                    resultado[f'{campo}_hash'] = self.crypto.hash_documento(str(valor))

                # Remove valor original
                del resultado[campo]

        return resultado

    def decrypt_fields(self, dados: dict, tipo_entidade: str) -> dict:
        """
        Descriptografa campos sensíveis de uma entidade

        Args:
            dados: Dicionário com dados criptografados
            tipo_entidade: Tipo da entidade

        Returns:
            Dicionário com campos descriptografados
        """
        campos_sensiveis = self.CAMPOS_SENSIVEIS.get(tipo_entidade, [])
        resultado = dados.copy()

        for campo in campos_sensiveis:
            encrypted_field = f'{campo}_encrypted'
            salt_field = f'{campo}_salt'

            if encrypted_field in resultado and salt_field in resultado:
                encrypted = resultado.get(encrypted_field)
                salt = resultado.get(salt_field)

                if encrypted and salt:
                    valor = self.crypto.descriptografar(encrypted, salt)
                    resultado[campo] = valor

                # Remove campos criptografados
                resultado.pop(encrypted_field, None)
                resultado.pop(salt_field, None)

        return resultado


# Instâncias globais
crypto_service = CryptoService()
field_encryptor = FieldEncryptor(crypto_service)


# ==================== FUNÇÕES DE CONVENIÊNCIA ====================

def criptografar_documento(documento: str) -> Tuple[bytes, bytes, str]:
    """
    Criptografa documento e retorna hash para busca

    Returns:
        Tupla (dados_criptografados, salt, hash_para_busca)
    """
    encrypted, salt = crypto_service.criptografar(documento)
    hash_doc = crypto_service.hash_documento(documento)
    return encrypted, salt, hash_doc


def descriptografar_documento(encrypted: bytes, salt: bytes) -> Optional[str]:
    """Descriptografa documento"""
    return crypto_service.descriptografar(encrypted, salt)


def hash_para_busca(documento: str) -> str:
    """Gera hash de documento para busca no banco"""
    return crypto_service.hash_documento(documento)
