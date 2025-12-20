"""
Conecta Plus - Serviço de LDAP/Active Directory
Suporta autenticação via LDAP e Active Directory
"""

import json
import ssl
from typing import Optional, List, Tuple
from dataclasses import dataclass

try:
    import ldap3
    from ldap3 import Server, Connection, ALL, NTLM, SIMPLE, SUBTREE
    from ldap3.core.exceptions import LDAPException, LDAPBindError
    LDAP_AVAILABLE = True
except ImportError:
    LDAP_AVAILABLE = False

from ..config import settings
from ..schemas.auth import LDAPUserInfo


@dataclass
class LDAPConfig:
    """Configuração do servidor LDAP"""
    server: str
    base_dn: str
    bind_dn: Optional[str] = None
    bind_password: Optional[str] = None
    user_search_base: str = "ou=users"
    user_search_filter: str = "(sAMAccountName={username})"
    group_search_base: str = "ou=groups"
    use_ssl: bool = False
    timeout: int = 10


class LDAPService:
    """Serviço para autenticação LDAP/Active Directory"""

    def __init__(self, config: LDAPConfig = None):
        if not LDAP_AVAILABLE:
            raise ImportError("ldap3 library não instalada. Execute: pip install ldap3")

        self.config = config or self._load_config_from_settings()
        self._server = None

    def _load_config_from_settings(self) -> LDAPConfig:
        """Carrega configuração do settings"""
        return LDAPConfig(
            server=settings.LDAP_SERVER,
            base_dn=settings.LDAP_BASE_DN,
            bind_dn=settings.LDAP_BIND_DN,
            bind_password=settings.LDAP_BIND_PASSWORD,
            user_search_base=settings.LDAP_USER_SEARCH_BASE,
            user_search_filter=settings.LDAP_USER_SEARCH_FILTER,
            group_search_base=settings.LDAP_GROUP_SEARCH_BASE,
            use_ssl=settings.LDAP_USE_SSL,
            timeout=settings.LDAP_TIMEOUT
        )

    def _get_server(self) -> 'ldap3.Server':
        """Obtém ou cria conexão com servidor LDAP"""
        if self._server is None:
            tls = None
            if self.config.use_ssl:
                tls = ldap3.Tls(validate=ssl.CERT_NONE)

            self._server = Server(
                self.config.server,
                get_info=ALL,
                use_ssl=self.config.use_ssl,
                tls=tls,
                connect_timeout=self.config.timeout
            )
        return self._server

    def _get_user_dn(self, username: str, domain: str = None) -> str:
        """Constrói o DN do usuário"""
        if domain:
            # Para Active Directory com domínio
            return f"{domain}\\{username}"
        elif "@" in username:
            # UPN format (user@domain.com)
            return username
        else:
            # DN format
            search_base = f"{self.config.user_search_base},{self.config.base_dn}"
            return f"cn={username},{search_base}"

    def authenticate(self, username: str, password: str, domain: str = None) -> Tuple[bool, Optional[LDAPUserInfo]]:
        """
        Autentica usuário via LDAP/AD
        Retorna (sucesso, informações do usuário)
        """
        if not LDAP_AVAILABLE:
            raise ImportError("ldap3 library não disponível")

        server = self._get_server()
        user_dn = self._get_user_dn(username, domain)

        try:
            # Determinar método de autenticação
            if domain:
                # NTLM para Active Directory
                conn = Connection(
                    server,
                    user=user_dn,
                    password=password,
                    authentication=NTLM,
                    auto_bind=True
                )
            else:
                # Simple bind para LDAP genérico
                conn = Connection(
                    server,
                    user=user_dn,
                    password=password,
                    authentication=SIMPLE,
                    auto_bind=True
                )

            if conn.bound:
                # Buscar informações do usuário
                user_info = self._get_user_info(conn, username)
                conn.unbind()
                return True, user_info

            return False, None

        except LDAPBindError as e:
            # Credenciais inválidas
            return False, None
        except LDAPException as e:
            # Erro de conexão/servidor
            raise ConnectionError(f"Erro LDAP: {str(e)}")

    def _get_user_info(self, conn: 'ldap3.Connection', username: str) -> Optional[LDAPUserInfo]:
        """Busca informações detalhadas do usuário"""
        search_base = f"{self.config.user_search_base},{self.config.base_dn}"
        search_filter = self.config.user_search_filter.format(username=username)

        # Atributos a buscar
        attributes = [
            'cn', 'displayName', 'mail', 'email',
            'memberOf', 'department', 'title',
            'sAMAccountName', 'userPrincipalName', 'distinguishedName'
        ]

        conn.search(
            search_base=search_base,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=attributes
        )

        if not conn.entries:
            return None

        entry = conn.entries[0]
        attrs = entry.entry_attributes_as_dict

        # Extrair grupos
        groups = []
        if 'memberOf' in attrs:
            for group_dn in attrs['memberOf']:
                # Extrair CN do grupo
                cn = self._extract_cn(group_dn)
                if cn:
                    groups.append(cn)

        # Extrair email
        email = None
        if 'mail' in attrs and attrs['mail']:
            email = attrs['mail'][0]
        elif 'email' in attrs and attrs['email']:
            email = attrs['email'][0]
        elif 'userPrincipalName' in attrs and attrs['userPrincipalName']:
            email = attrs['userPrincipalName'][0]

        # Extrair nome
        display_name = username
        if 'displayName' in attrs and attrs['displayName']:
            display_name = attrs['displayName'][0]
        elif 'cn' in attrs and attrs['cn']:
            display_name = attrs['cn'][0]

        return LDAPUserInfo(
            dn=str(entry.entry_dn),
            username=username,
            email=email,
            display_name=display_name,
            groups=groups,
            department=attrs.get('department', [None])[0] if attrs.get('department') else None,
            title=attrs.get('title', [None])[0] if attrs.get('title') else None
        )

    def _extract_cn(self, dn: str) -> Optional[str]:
        """Extrai CN de um DN"""
        try:
            parts = dn.split(',')
            for part in parts:
                if part.strip().upper().startswith('CN='):
                    return part.strip()[3:]
        except Exception:
            pass
        return None

    def get_user_groups(self, conn: 'ldap3.Connection', user_dn: str) -> List[str]:
        """Obtém todos os grupos do usuário (incluindo nested groups)"""
        groups = []

        search_filter = f"(member:1.2.840.113556.1.4.1941:={user_dn})"

        conn.search(
            search_base=self.config.base_dn,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=['cn', 'distinguishedName']
        )

        for entry in conn.entries:
            attrs = entry.entry_attributes_as_dict
            if 'cn' in attrs and attrs['cn']:
                groups.append(attrs['cn'][0])

        return groups

    def test_connection(self) -> Tuple[bool, str]:
        """
        Testa conexão com servidor LDAP
        Retorna (sucesso, mensagem)
        """
        if not LDAP_AVAILABLE:
            return False, "ldap3 library não instalada"

        try:
            server = self._get_server()

            # Tentar bind anônimo ou com credenciais de serviço
            if self.config.bind_dn and self.config.bind_password:
                conn = Connection(
                    server,
                    user=self.config.bind_dn,
                    password=self.config.bind_password,
                    authentication=SIMPLE,
                    auto_bind=True
                )
            else:
                conn = Connection(server, auto_bind=True)

            if conn.bound:
                server_info = {
                    "vendor": str(server.info.vendor_name) if server.info else "Unknown",
                    "version": str(server.info.vendor_version) if server.info else "Unknown"
                }
                conn.unbind()
                return True, f"Conectado: {json.dumps(server_info)}"

            return False, "Falha no bind"

        except LDAPException as e:
            return False, f"Erro: {str(e)}"
        except Exception as e:
            return False, f"Erro inesperado: {str(e)}"

    def search_users(self, query: str, limit: int = 10) -> List[LDAPUserInfo]:
        """
        Busca usuários no LDAP
        """
        if not LDAP_AVAILABLE:
            return []

        if not self.config.bind_dn or not self.config.bind_password:
            raise ValueError("Credenciais de bind necessárias para busca")

        server = self._get_server()
        conn = Connection(
            server,
            user=self.config.bind_dn,
            password=self.config.bind_password,
            authentication=SIMPLE,
            auto_bind=True
        )

        search_base = f"{self.config.user_search_base},{self.config.base_dn}"
        search_filter = f"(&(objectClass=user)(|(cn=*{query}*)(mail=*{query}*)(sAMAccountName=*{query}*)))"

        conn.search(
            search_base=search_base,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=['cn', 'displayName', 'mail', 'sAMAccountName', 'distinguishedName'],
            size_limit=limit
        )

        users = []
        for entry in conn.entries:
            attrs = entry.entry_attributes_as_dict
            users.append(LDAPUserInfo(
                dn=str(entry.entry_dn),
                username=attrs.get('sAMAccountName', [attrs.get('cn', [''])[0]])[0],
                email=attrs.get('mail', [None])[0],
                display_name=attrs.get('displayName', [attrs.get('cn', [''])[0]])[0],
                groups=[]
            ))

        conn.unbind()
        return users


def map_ldap_groups_to_role(groups: List[str]) -> str:
    """
    Mapeia grupos LDAP para roles do sistema
    Personalize conforme a estrutura do seu AD
    """
    # Mapeamento de grupos para roles (case insensitive)
    group_role_map = {
        "conecta-admins": "admin",
        "conecta-sindicos": "sindico",
        "conecta-gerentes": "gerente",
        "conecta-porteiros": "porteiro",
        "domain admins": "admin",
        "administrators": "admin",
    }

    groups_lower = [g.lower() for g in groups]

    for group, role in group_role_map.items():
        if group.lower() in groups_lower:
            return role

    return settings.SSO_DEFAULT_ROLE


# Instância global (só inicializa se LDAP estiver habilitado)
ldap_service = None

def get_ldap_service() -> Optional[LDAPService]:
    """Obtém serviço LDAP se habilitado"""
    global ldap_service

    if not settings.LDAP_ENABLED:
        return None

    if ldap_service is None and LDAP_AVAILABLE:
        ldap_service = LDAPService()

    return ldap_service
