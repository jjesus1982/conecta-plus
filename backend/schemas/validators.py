"""
Conecta Plus - Validadores Customizados
Validacoes robustas para dados de entrada
"""

import re
from typing import Any
from pydantic import field_validator, model_validator
from pydantic_core import PydanticCustomError


class PasswordValidator:
    """
    Validador de senhas seguindo melhores praticas.

    Requisitos:
    - Minimo 8 caracteres
    - Pelo menos 1 letra maiuscula
    - Pelo menos 1 letra minuscula
    - Pelo menos 1 numero
    - Pelo menos 1 caractere especial
    - Nao pode conter espacos
    - Nao pode ser senha comum
    """

    COMMON_PASSWORDS = {
        "password", "123456", "12345678", "qwerty", "abc123",
        "password1", "123456789", "12345", "1234567", "password123",
        "admin", "admin123", "root", "master", "letmein",
        "welcome", "monkey", "dragon", "iloveyou", "trustno1",
        "senha123", "mudar123", "conecta123", "condominio"
    }

    MIN_LENGTH = 8
    MAX_LENGTH = 128

    @classmethod
    def validate(cls, password: str) -> str:
        """Valida senha e retorna se valida."""
        if not password:
            raise PydanticCustomError(
                "password_required",
                "Senha e obrigatoria"
            )

        if len(password) < cls.MIN_LENGTH:
            raise PydanticCustomError(
                "password_too_short",
                f"Senha deve ter pelo menos {cls.MIN_LENGTH} caracteres"
            )

        if len(password) > cls.MAX_LENGTH:
            raise PydanticCustomError(
                "password_too_long",
                f"Senha deve ter no maximo {cls.MAX_LENGTH} caracteres"
            )

        if " " in password:
            raise PydanticCustomError(
                "password_has_spaces",
                "Senha nao pode conter espacos"
            )

        if password.lower() in cls.COMMON_PASSWORDS:
            raise PydanticCustomError(
                "password_common",
                "Esta senha e muito comum. Escolha uma senha mais segura"
            )

        if not re.search(r"[A-Z]", password):
            raise PydanticCustomError(
                "password_no_uppercase",
                "Senha deve conter pelo menos uma letra maiuscula"
            )

        if not re.search(r"[a-z]", password):
            raise PydanticCustomError(
                "password_no_lowercase",
                "Senha deve conter pelo menos uma letra minuscula"
            )

        if not re.search(r"\d", password):
            raise PydanticCustomError(
                "password_no_digit",
                "Senha deve conter pelo menos um numero"
            )

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\;'/~`]", password):
            raise PydanticCustomError(
                "password_no_special",
                "Senha deve conter pelo menos um caractere especial (!@#$%^&* etc)"
            )

        return password


class CPFValidator:
    """Validador de CPF brasileiro."""

    @classmethod
    def validate(cls, cpf: str) -> str:
        """Valida CPF e retorna formatado."""
        # Remover caracteres nao numericos
        cpf_clean = re.sub(r"\D", "", cpf)

        if len(cpf_clean) != 11:
            raise PydanticCustomError(
                "cpf_invalid_length",
                "CPF deve ter 11 digitos"
            )

        # Verificar se todos os digitos sao iguais
        if cpf_clean == cpf_clean[0] * 11:
            raise PydanticCustomError(
                "cpf_invalid",
                "CPF invalido"
            )

        # Calcular primeiro digito verificador
        soma = sum(int(cpf_clean[i]) * (10 - i) for i in range(9))
        resto = soma % 11
        digito1 = 0 if resto < 2 else 11 - resto

        if int(cpf_clean[9]) != digito1:
            raise PydanticCustomError(
                "cpf_invalid",
                "CPF invalido"
            )

        # Calcular segundo digito verificador
        soma = sum(int(cpf_clean[i]) * (11 - i) for i in range(10))
        resto = soma % 11
        digito2 = 0 if resto < 2 else 11 - resto

        if int(cpf_clean[10]) != digito2:
            raise PydanticCustomError(
                "cpf_invalid",
                "CPF invalido"
            )

        return cpf_clean


class CNPJValidator:
    """Validador de CNPJ brasileiro."""

    @classmethod
    def validate(cls, cnpj: str) -> str:
        """Valida CNPJ e retorna formatado."""
        # Remover caracteres nao numericos
        cnpj_clean = re.sub(r"\D", "", cnpj)

        if len(cnpj_clean) != 14:
            raise PydanticCustomError(
                "cnpj_invalid_length",
                "CNPJ deve ter 14 digitos"
            )

        # Verificar se todos os digitos sao iguais
        if cnpj_clean == cnpj_clean[0] * 14:
            raise PydanticCustomError(
                "cnpj_invalid",
                "CNPJ invalido"
            )

        # Calcular primeiro digito verificador
        pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(int(cnpj_clean[i]) * pesos1[i] for i in range(12))
        resto = soma % 11
        digito1 = 0 if resto < 2 else 11 - resto

        if int(cnpj_clean[12]) != digito1:
            raise PydanticCustomError(
                "cnpj_invalid",
                "CNPJ invalido"
            )

        # Calcular segundo digito verificador
        pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(int(cnpj_clean[i]) * pesos2[i] for i in range(13))
        resto = soma % 11
        digito2 = 0 if resto < 2 else 11 - resto

        if int(cnpj_clean[13]) != digito2:
            raise PydanticCustomError(
                "cnpj_invalid",
                "CNPJ invalido"
            )

        return cnpj_clean


class PhoneValidator:
    """Validador de telefone brasileiro."""

    @classmethod
    def validate(cls, phone: str) -> str:
        """Valida telefone e retorna formatado."""
        # Remover caracteres nao numericos
        phone_clean = re.sub(r"\D", "", phone)

        # Aceitar com ou sem codigo de pais
        if phone_clean.startswith("55"):
            phone_clean = phone_clean[2:]

        if len(phone_clean) < 10 or len(phone_clean) > 11:
            raise PydanticCustomError(
                "phone_invalid",
                "Telefone deve ter 10 ou 11 digitos (com DDD)"
            )

        # Verificar DDD valido (11-99)
        ddd = int(phone_clean[:2])
        if ddd < 11 or ddd > 99:
            raise PydanticCustomError(
                "phone_invalid_ddd",
                "DDD invalido"
            )

        return phone_clean


class PlacaVeiculoValidator:
    """Validador de placa de veiculo (formato antigo e Mercosul)."""

    # Formato antigo: ABC-1234
    PATTERN_OLD = r"^[A-Z]{3}-?\d{4}$"

    # Formato Mercosul: ABC1D23
    PATTERN_MERCOSUL = r"^[A-Z]{3}\d[A-Z]\d{2}$"

    @classmethod
    def validate(cls, placa: str) -> str:
        """Valida placa e retorna formatada (maiusculas, sem hifen)."""
        placa_clean = placa.upper().replace("-", "").replace(" ", "")

        if re.match(cls.PATTERN_OLD.replace("-?", ""), placa_clean):
            return placa_clean

        if re.match(cls.PATTERN_MERCOSUL, placa_clean):
            return placa_clean

        raise PydanticCustomError(
            "placa_invalid",
            "Placa invalida. Use formato ABC1234 ou ABC1D23"
        )


class SanitizeString:
    """Sanitizador de strings para prevenir XSS e injection."""

    # Caracteres perigosos para remover
    DANGEROUS_CHARS = ["<", ">", "&", '"', "'", "\\", "\x00"]

    # Padroes de SQL injection
    SQL_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\b)",
        r"(--)|(;)",
        r"(\/\*|\*\/)",
    ]

    @classmethod
    def sanitize(cls, value: str, max_length: int = None) -> str:
        """Remove caracteres perigosos e limita tamanho."""
        if not value:
            return value

        # Remover caracteres perigosos
        for char in cls.DANGEROUS_CHARS:
            value = value.replace(char, "")

        # Remover padroes de SQL injection
        for pattern in cls.SQL_PATTERNS:
            value = re.sub(pattern, "", value, flags=re.IGNORECASE)

        # Remover espacos extras
        value = " ".join(value.split())

        # Limitar tamanho
        if max_length and len(value) > max_length:
            value = value[:max_length]

        return value.strip()


class EmailValidator:
    """Validador de email com verificacoes adicionais."""

    # Dominios de email temporario/descartavel
    DISPOSABLE_DOMAINS = {
        "tempmail.com", "10minutemail.com", "guerrillamail.com",
        "mailinator.com", "throwaway.email", "temp-mail.org",
        "fakeinbox.com", "sharklasers.com", "yopmail.com",
    }

    @classmethod
    def validate(cls, email: str) -> str:
        """Valida email e verifica se nao e descartavel."""
        email = email.lower().strip()

        # Extrair dominio
        domain = email.split("@")[-1]

        if domain in cls.DISPOSABLE_DOMAINS:
            raise PydanticCustomError(
                "email_disposable",
                "Emails temporarios nao sao permitidos"
            )

        return email
