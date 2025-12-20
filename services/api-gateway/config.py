"""
Configurações centralizadas do Conecta Plus API Gateway.

Carrega variáveis de ambiente e valida configurações obrigatórias.
"""

import os
import sys
from typing import List, Optional
from dataclasses import dataclass, field
from pathlib import Path

# Tenta carregar python-dotenv se disponível
try:
    from dotenv import load_dotenv
    # Carrega .env do diretório atual
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv não instalado, usa apenas env vars do sistema


def get_env(key: str, default: str = None, required: bool = False) -> Optional[str]:
    """Obtém variável de ambiente com validação."""
    value = os.getenv(key, default)
    if required and not value:
        raise EnvironmentError(f"Variável de ambiente obrigatória não definida: {key}")
    return value


def get_env_bool(key: str, default: bool = False) -> bool:
    """Obtém variável de ambiente como boolean."""
    value = os.getenv(key, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')


def get_env_int(key: str, default: int = 0) -> int:
    """Obtém variável de ambiente como inteiro."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def get_env_list(key: str, default: str = "") -> List[str]:
    """Obtém variável de ambiente como lista (separada por vírgula)."""
    value = os.getenv(key, default)
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass
class SecurityConfig:
    """Configurações de segurança."""
    secret_key: str = field(default_factory=lambda: get_env("SECRET_KEY", "dev-secret-key-change-in-production"))
    jwt_algorithm: str = field(default_factory=lambda: get_env("JWT_ALGORITHM", "HS256"))
    jwt_expiration: int = field(default_factory=lambda: get_env_int("JWT_EXPIRATION", 3600))

    def validate(self, environment: str) -> List[str]:
        """Valida configurações de segurança."""
        warnings = []
        errors = []

        if self.secret_key == "dev-secret-key-change-in-production":
            if environment == "production":
                errors.append("SECRET_KEY deve ser definida em produção")
            else:
                warnings.append("SECRET_KEY usando valor padrão (OK para desenvolvimento)")

        if len(self.secret_key) < 32:
            warnings.append("SECRET_KEY deveria ter pelo menos 32 caracteres")

        return warnings, errors


@dataclass
class DatabaseConfig:
    """Configurações do banco de dados."""
    host: str = field(default_factory=lambda: get_env("DB_HOST", "localhost"))
    port: int = field(default_factory=lambda: get_env_int("DB_PORT", 5432))
    user: str = field(default_factory=lambda: get_env("DB_USER", "conecta"))
    password: str = field(default_factory=lambda: get_env("DB_PASSWORD", ""))
    database: str = field(default_factory=lambda: get_env("DB_NAME", "conecta_plus"))
    pool_min: int = field(default_factory=lambda: get_env_int("DB_POOL_MIN", 5))
    pool_max: int = field(default_factory=lambda: get_env_int("DB_POOL_MAX", 50))

    @property
    def dsn(self) -> str:
        """Retorna a string de conexão."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    def validate(self, environment: str) -> List[str]:
        """Valida configurações do banco."""
        warnings = []
        errors = []

        if not self.password:
            if environment == "production":
                errors.append("DB_PASSWORD deve ser definida em produção")
            else:
                warnings.append("DB_PASSWORD não definida (OK para desenvolvimento local)")

        if self.pool_max < 10 and environment == "production":
            warnings.append(f"DB_POOL_MAX={self.pool_max} pode ser insuficiente para produção")

        return warnings, errors


@dataclass
class RedisConfig:
    """Configurações do Redis."""
    url: str = field(default_factory=lambda: get_env("REDIS_URL", "redis://localhost:6379"))
    password: str = field(default_factory=lambda: get_env("REDIS_PASSWORD", ""))

    def validate(self, environment: str) -> List[str]:
        """Valida configurações do Redis."""
        warnings = []
        errors = []

        if "localhost" in self.url and environment == "production":
            warnings.append("REDIS_URL aponta para localhost em produção")

        return warnings, errors


@dataclass
class SMTPConfig:
    """Configurações de email."""
    host: str = field(default_factory=lambda: get_env("SMTP_HOST", "smtp.gmail.com"))
    port: int = field(default_factory=lambda: get_env_int("SMTP_PORT", 587))
    user: str = field(default_factory=lambda: get_env("SMTP_USER", ""))
    password: str = field(default_factory=lambda: get_env("SMTP_PASSWORD", ""))
    from_email: str = field(default_factory=lambda: get_env("SMTP_FROM", "noreply@conectaplus.com.br"))
    use_tls: bool = field(default_factory=lambda: get_env_bool("SMTP_TLS", True))

    def validate(self, environment: str) -> List[str]:
        """Valida configurações de SMTP."""
        warnings = []
        errors = []

        if not self.user or not self.password:
            warnings.append("SMTP não configurado - envio de emails desabilitado")

        return warnings, errors


@dataclass
class CORSConfig:
    """Configurações de CORS."""
    origins: List[str] = field(default_factory=lambda: get_env_list("CORS_ORIGINS", "http://localhost:3000"))
    allow_credentials: bool = True
    allow_methods: List[str] = field(default_factory=lambda: ["*"])
    allow_headers: List[str] = field(default_factory=lambda: ["*"])

    def validate(self, environment: str) -> List[str]:
        """Valida configurações de CORS."""
        warnings = []
        errors = []

        if "*" in self.origins:
            if environment == "production":
                errors.append("CORS_ORIGINS não pode ser '*' em produção")
            else:
                warnings.append("CORS_ORIGINS='*' - aceita qualquer origem")

        if not self.origins:
            self.origins = ["http://localhost:3000"]
            warnings.append("CORS_ORIGINS vazio, usando localhost:3000")

        return warnings, errors


@dataclass
class RateLimitConfig:
    """Configurações de rate limiting."""
    requests: int = field(default_factory=lambda: get_env_int("RATE_LIMIT_REQUESTS", 100))
    period: int = field(default_factory=lambda: get_env_int("RATE_LIMIT_PERIOD", 60))
    webhook_limit: int = field(default_factory=lambda: get_env_int("RATE_LIMIT_WEBHOOK", 10))

    def validate(self, environment: str) -> List[str]:
        """Valida configurações de rate limiting."""
        warnings = []
        errors = []

        if self.requests > 1000:
            warnings.append(f"RATE_LIMIT_REQUESTS={self.requests} muito alto")

        return warnings, errors


@dataclass
class PIXConfig:
    """Configurações de PIX/Boletos."""
    chave: str = field(default_factory=lambda: get_env("PIX_CHAVE", ""))
    banco_codigo: str = field(default_factory=lambda: get_env("BANCO_CODIGO", "077"))
    banco_agencia: str = field(default_factory=lambda: get_env("BANCO_AGENCIA", ""))
    banco_conta: str = field(default_factory=lambda: get_env("BANCO_CONTA", ""))
    beneficiario_nome: str = field(default_factory=lambda: get_env("BENEFICIARIO_NOME", ""))
    beneficiario_cnpj: str = field(default_factory=lambda: get_env("BENEFICIARIO_CNPJ", ""))

    def validate(self, environment: str) -> List[str]:
        """Valida configurações de PIX."""
        warnings = []
        errors = []

        if not self.chave:
            warnings.append("PIX_CHAVE não configurada - geração de QR Code desabilitada")

        return warnings, errors


@dataclass
class Settings:
    """Configurações globais da aplicação."""

    # Ambiente
    environment: str = field(default_factory=lambda: get_env("ENVIRONMENT", "development"))
    debug: bool = field(default_factory=lambda: get_env_bool("DEBUG", True))
    log_level: str = field(default_factory=lambda: get_env("LOG_LEVEL", "INFO"))

    # Sub-configurações
    security: SecurityConfig = field(default_factory=SecurityConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    smtp: SMTPConfig = field(default_factory=SMTPConfig)
    cors: CORSConfig = field(default_factory=CORSConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    pix: PIXConfig = field(default_factory=PIXConfig)

    # Monitoramento
    sentry_dsn: str = field(default_factory=lambda: get_env("SENTRY_DSN", ""))
    prometheus_enabled: bool = field(default_factory=lambda: get_env_bool("PROMETHEUS_ENABLED", False))

    @property
    def is_production(self) -> bool:
        """Verifica se está em produção."""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Verifica se está em desenvolvimento."""
        return self.environment.lower() in ("development", "dev", "local")

    def validate(self) -> bool:
        """
        Valida todas as configurações.

        Em produção, erros críticos causam falha na inicialização.
        Em desenvolvimento, apenas warnings são exibidos.
        """
        all_warnings = []
        all_errors = []

        # Valida cada seção
        for config_name in ['security', 'database', 'redis', 'smtp', 'cors', 'rate_limit', 'pix']:
            config = getattr(self, config_name)
            if hasattr(config, 'validate'):
                warnings, errors = config.validate(self.environment)
                all_warnings.extend(warnings)
                all_errors.extend(errors)

        # Exibe warnings
        if all_warnings:
            print("\n⚠️  AVISOS DE CONFIGURAÇÃO:")
            for warning in all_warnings:
                print(f"   - {warning}")

        # Exibe erros
        if all_errors:
            print("\n❌ ERROS DE CONFIGURAÇÃO:")
            for error in all_errors:
                print(f"   - {error}")

        # Em produção, erros são fatais
        if all_errors and self.is_production:
            print("\n🛑 Inicialização abortada devido a erros de configuração em produção.")
            print("   Verifique o arquivo .env e as variáveis de ambiente.")
            sys.exit(1)

        if not all_warnings and not all_errors:
            print("✅ Configurações validadas com sucesso")

        return len(all_errors) == 0

    def __post_init__(self):
        """Validação automática após inicialização."""
        # Ajusta log level baseado no ambiente
        if self.is_development and self.log_level == "INFO":
            self.log_level = "DEBUG"


# Instância global de configurações
settings = Settings()


def get_settings() -> Settings:
    """Retorna a instância de configurações (para dependency injection)."""
    return settings


# Validação na importação (opcional - pode ser chamado manualmente)
def validate_on_startup():
    """Valida configurações na inicialização."""
    print(f"\n🔧 Ambiente: {settings.environment.upper()}")
    print(f"   Debug: {'Ativado' if settings.debug else 'Desativado'}")
    print(f"   Log Level: {settings.log_level}")
    settings.validate()
    print("")


if __name__ == "__main__":
    # Teste de configurações
    validate_on_startup()
    print("\nConfigurações carregadas:")
    print(f"  Database: {settings.database.host}:{settings.database.port}/{settings.database.database}")
    print(f"  Redis: {settings.redis.url}")
    print(f"  CORS Origins: {settings.cors.origins}")
    print(f"  Rate Limit: {settings.rate_limit.requests} req/{settings.rate_limit.period}s")
