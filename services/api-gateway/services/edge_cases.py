"""
Conecta Plus - Edge Cases Handler

Utilitários para tratamento robusto de dados inválidos, nulos e edge cases.
"""

from typing import Any, Dict, List, Optional, Callable, TypeVar, Union, Tuple
from functools import wraps
from datetime import datetime, date
import math

from services.logger import create_logger

logger = create_logger("conecta-plus.edge_cases")

T = TypeVar('T')


class SafeValue:
    """Classe para acesso seguro a valores com fallback."""

    @staticmethod
    def get(data: Any, key: str, default: Any = None, type_cast: type = None) -> Any:
        """
        Obtém valor de forma segura com conversão de tipo opcional.

        Args:
            data: Dicionário ou objeto
            key: Chave a buscar
            default: Valor padrão se não encontrado ou inválido
            type_cast: Tipo para conversão (int, float, str, etc.)
        """
        try:
            if data is None:
                return default

            if isinstance(data, dict):
                value = data.get(key, default)
            elif hasattr(data, key):
                value = getattr(data, key, default)
            else:
                return default

            if value is None:
                return default

            if type_cast is not None:
                try:
                    return type_cast(value)
                except (ValueError, TypeError):
                    return default

            return value
        except Exception:
            return default

    @staticmethod
    def get_float(data: Any, key: str, default: float = 0.0) -> float:
        """Obtém valor float de forma segura."""
        value = SafeValue.get(data, key, default)
        try:
            result = float(value)
            if math.isnan(result) or math.isinf(result):
                return default
            return result
        except (ValueError, TypeError):
            return default

    @staticmethod
    def get_int(data: Any, key: str, default: int = 0) -> int:
        """Obtém valor int de forma segura."""
        value = SafeValue.get(data, key, default)
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def get_str(data: Any, key: str, default: str = "") -> str:
        """Obtém valor string de forma segura."""
        value = SafeValue.get(data, key, default)
        if value is None:
            return default
        return str(value).strip()

    @staticmethod
    def get_list(data: Any, key: str, default: List = None) -> List:
        """Obtém lista de forma segura."""
        if default is None:
            default = []
        value = SafeValue.get(data, key, default)
        if not isinstance(value, list):
            return default
        return value

    @staticmethod
    def get_date(data: Any, key: str, default: date = None) -> Optional[date]:
        """Obtém data de forma segura."""
        value = SafeValue.get(data, key)
        if value is None:
            return default

        if isinstance(value, date):
            return value

        if isinstance(value, datetime):
            return value.date()

        try:
            # Tenta vários formatos
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                try:
                    return datetime.strptime(str(value)[:10], fmt[:len(str(value)[:10])]).date()
                except ValueError:
                    continue
            return default
        except Exception:
            return default


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Divisão segura que evita divisão por zero."""
    try:
        if denominator == 0 or denominator is None:
            return default
        result = numerator / denominator
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except Exception:
        return default


def safe_percentage(part: float, total: float, default: float = 0.0) -> float:
    """Calcula percentagem de forma segura."""
    return safe_divide(part * 100, total, default)


def safe_mean(values: List[float], default: float = 0.0) -> float:
    """Calcula média de forma segura."""
    if not values:
        return default
    try:
        clean_values = [v for v in values if v is not None and not math.isnan(v)]
        if not clean_values:
            return default
        return sum(clean_values) / len(clean_values)
    except Exception:
        return default


def safe_std(values: List[float], default: float = 0.0) -> float:
    """Calcula desvio padrão de forma segura."""
    if len(values) < 2:
        return default
    try:
        clean_values = [v for v in values if v is not None and not math.isnan(v)]
        if len(clean_values) < 2:
            return default
        mean = sum(clean_values) / len(clean_values)
        variance = sum((x - mean) ** 2 for x in clean_values) / len(clean_values)
        return math.sqrt(variance)
    except Exception:
        return default


def safe_max(values: List[float], default: float = 0.0) -> float:
    """Encontra máximo de forma segura."""
    if not values:
        return default
    try:
        clean_values = [v for v in values if v is not None and not math.isnan(v)]
        if not clean_values:
            return default
        return max(clean_values)
    except Exception:
        return default


def safe_min(values: List[float], default: float = 0.0) -> float:
    """Encontra mínimo de forma segura."""
    if not values:
        return default
    try:
        clean_values = [v for v in values if v is not None and not math.isnan(v)]
        if not clean_values:
            return default
        return min(clean_values)
    except Exception:
        return default


def validate_input(
    required_fields: List[str] = None,
    optional_defaults: Dict[str, Any] = None
) -> Callable:
    """
    Decorator para validar inputs de funções.

    Args:
        required_fields: Lista de campos obrigatórios
        optional_defaults: Dict de campos opcionais com valores padrão
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Valida campos obrigatórios
            if required_fields:
                for field in required_fields:
                    if field not in kwargs or kwargs[field] is None:
                        logger.warning(
                            f"Campo obrigatório ausente: {field}",
                            function=func.__name__,
                            field=field
                        )
                        return {
                            "error": f"Campo obrigatório ausente: {field}",
                            "field": field,
                            "success": False
                        }

            # Aplica defaults para campos opcionais
            if optional_defaults:
                for field, default in optional_defaults.items():
                    if field not in kwargs or kwargs[field] is None:
                        kwargs[field] = default

            return func(*args, **kwargs)
        return wrapper
    return decorator


def handle_empty_data(default_response: Any = None) -> Callable:
    """
    Decorator para lidar com dados vazios.

    Args:
        default_response: Resposta padrão quando dados estão vazios
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Verifica se algum argumento importante está vazio
            for arg in args:
                if isinstance(arg, (list, dict)) and not arg:
                    logger.debug(
                        f"Dados vazios recebidos em {func.__name__}",
                        function=func.__name__
                    )
                    if default_response is not None:
                        return default_response

            return func(*args, **kwargs)
        return wrapper
    return decorator


def safe_execution(default_on_error: Any = None, log_errors: bool = True) -> Callable:
    """
    Decorator para execução segura com tratamento de exceções.

    Args:
        default_on_error: Valor retornado em caso de erro
        log_errors: Se deve logar erros
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(
                        f"Erro em {func.__name__}: {str(e)}",
                        function=func.__name__,
                        error_type=type(e).__name__,
                        error_message=str(e)
                    )
                if default_on_error is not None:
                    if callable(default_on_error):
                        return default_on_error()
                    return default_on_error
                raise
        return wrapper
    return decorator


def sanitize_text(text: str, max_length: int = 10000) -> str:
    """
    Sanitiza texto para processamento seguro.

    Args:
        text: Texto a sanitizar
        max_length: Comprimento máximo permitido
    """
    if not text:
        return ""

    if not isinstance(text, str):
        text = str(text)

    # Remove caracteres de controle (exceto newline e tab)
    text = ''.join(char for char in text if char == '\n' or char == '\t' or (ord(char) >= 32 and ord(char) < 127) or ord(char) >= 160)

    # Limita tamanho
    if len(text) > max_length:
        text = text[:max_length]
        logger.warning(f"Texto truncado para {max_length} caracteres")

    return text.strip()


def validate_numeric_range(
    value: float,
    min_value: float = None,
    max_value: float = None,
    default: float = 0.0
) -> float:
    """
    Valida se valor está dentro do range permitido.

    Args:
        value: Valor a validar
        min_value: Valor mínimo (opcional)
        max_value: Valor máximo (opcional)
        default: Valor padrão se fora do range
    """
    try:
        if value is None or math.isnan(value) or math.isinf(value):
            return default

        if min_value is not None and value < min_value:
            return min_value

        if max_value is not None and value > max_value:
            return max_value

        return value
    except Exception:
        return default


def coalesce(*values, default: Any = None) -> Any:
    """
    Retorna o primeiro valor não-nulo.

    Similar ao COALESCE do SQL.
    """
    for value in values:
        if value is not None:
            return value
    return default


class DataValidator:
    """Validador de dados estruturados."""

    @staticmethod
    def validate_boleto(boleto: Dict) -> Tuple[bool, List[str]]:
        """Valida estrutura de um boleto."""
        errors = []

        if not boleto:
            return False, ["Boleto vazio ou nulo"]

        required = ['id', 'valor', 'vencimento']
        for field in required:
            if field not in boleto or boleto[field] is None:
                errors.append(f"Campo obrigatório ausente: {field}")

        if 'valor' in boleto:
            valor = SafeValue.get_float(boleto, 'valor', -1)
            if valor <= 0:
                errors.append(f"Valor inválido: {boleto.get('valor')}")

        return len(errors) == 0, errors

    @staticmethod
    def validate_unidade(unidade: Dict) -> Tuple[bool, List[str]]:
        """Valida estrutura de uma unidade."""
        errors = []

        if not unidade:
            return False, ["Unidade vazia ou nula"]

        if 'id' not in unidade:
            errors.append("Campo 'id' obrigatório")

        return len(errors) == 0, errors

    @staticmethod
    def clean_list(items: List[Dict], validator: Callable) -> List[Dict]:
        """Remove itens inválidos de uma lista."""
        if not items:
            return []

        clean = []
        for item in items:
            is_valid, errors = validator(item)
            if is_valid:
                clean.append(item)
            else:
                logger.debug(f"Item removido por validação: {errors}")

        return clean


# Instância global para uso fácil
safe = SafeValue()
validator = DataValidator()
