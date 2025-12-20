"""
Conecta Plus - Funções Auxiliares
"""

import uuid
from datetime import datetime
from typing import Optional


def generate_protocol(prefix: str = "PROT") -> str:
    """Gera um protocolo único."""
    timestamp = datetime.now().strftime("%Y%m%d")
    unique = uuid.uuid4().hex[:6].upper()
    return f"{prefix}-{timestamp}-{unique}"


def format_currency(value: float) -> str:
    """Formata valor monetário para Real brasileiro."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_phone(phone: str) -> str:
    """Formata número de telefone brasileiro."""
    digits = "".join(filter(str.isdigit, phone))
    if len(digits) == 11:
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    elif len(digits) == 10:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    return phone


def format_cpf(cpf: str) -> str:
    """Formata CPF."""
    digits = "".join(filter(str.isdigit, cpf))
    if len(digits) == 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    return cpf


def format_cnpj(cnpj: str) -> str:
    """Formata CNPJ."""
    digits = "".join(filter(str.isdigit, cnpj))
    if len(digits) == 14:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
    return cnpj


def validate_cpf(cpf: str) -> bool:
    """Valida CPF."""
    digits = "".join(filter(str.isdigit, cpf))
    if len(digits) != 11:
        return False
    if digits == digits[0] * 11:
        return False

    # Primeiro dígito verificador
    soma = sum(int(digits[i]) * (10 - i) for i in range(9))
    resto = soma % 11
    d1 = 0 if resto < 2 else 11 - resto

    # Segundo dígito verificador
    soma = sum(int(digits[i]) * (11 - i) for i in range(10))
    resto = soma % 11
    d2 = 0 if resto < 2 else 11 - resto

    return digits[9:] == f"{d1}{d2}"


def generate_slug(text: str) -> str:
    """Gera slug a partir de texto."""
    import re
    import unicodedata

    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[-\s]+", "-", text)
    return text


def paginate(items: list, page: int = 1, per_page: int = 20) -> dict:
    """Pagina uma lista de itens."""
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page

    return {
        "items": items[start:end],
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": (total + per_page - 1) // per_page
    }
