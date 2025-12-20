"""
Conecta Plus - Cliente Ubiquiti UniFi Controller API
Permite gerenciamento de redes UniFi via API do Controller

Dependências:
    pip install requests

Uso:
    from unifi_client import UniFiClient

    # Conectar ao controller
    client = UniFiClient('192.168.1.1', 'admin', 'senha')
    client.login()

    # Listar clientes
    clients = client.get_clients()

    # Listar APs
    aps = client.get_access_points()
"""

import logging
import requests
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import urllib3

# Desabilitar warnings de SSL (controller geralmente usa certificado auto-assinado)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class UniFiClient:
    """Cliente conectado à rede"""
    mac: str
    hostname: str
    ip: str
    ap_mac: str
    network: str
    signal: int
    rx_bytes: int
    tx_bytes: int
    uptime: int
    is_wired: bool
    is_guest: bool


@dataclass
class AccessPoint:
    """Access Point UniFi"""
    mac: str
    name: str
    model: str
    ip: str
    state: int
    version: str
    uptime: int
    num_clients: int
    channel: int
    tx_power: int


@dataclass
class UniFiNetwork:
    """Rede configurada"""
    id: str
    name: str
    purpose: str
    vlan: int
    subnet: str
    enabled: bool


class UniFiController:
    """
    Cliente para API do UniFi Controller

    Funcionalidades:
    - Gerenciamento de clientes
    - Controle de Access Points
    - Configuração de redes
    - Estatísticas de uso
    - Controle de guests
    - Alertas e eventos
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 8443,
        site: str = "default",
        ssl_verify: bool = False
    ):
        """
        Inicializa o cliente UniFi

        Args:
            host: IP ou hostname do controller
            username: Usuário para autenticação
            password: Senha para autenticação
            port: Porta do controller (padrão: 8443)
            site: Site a gerenciar (padrão: "default")
            ssl_verify: Verificar certificado SSL
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.site = site
        self.ssl_verify = ssl_verify

        self.base_url = f"https://{host}:{port}"
        self._session = requests.Session()
        self._session.verify = ssl_verify
        self._logged_in = False

    @property
    def is_logged_in(self) -> bool:
        """Verifica se está logado"""
        return self._logged_in

    def login(self) -> bool:
        """
        Faz login no controller

        Returns:
            True se logou com sucesso

        Raises:
            ConnectionError: Se não conseguir conectar
        """
        logger.info(f"Conectando ao UniFi Controller {self.host}:{self.port}...")

        try:
            # Endpoint de login
            login_url = f"{self.base_url}/api/login"

            response = self._session.post(
                login_url,
                json={
                    "username": self.username,
                    "password": self.password
                }
            )

            if response.status_code == 200:
                self._logged_in = True
                logger.info(f"Conectado ao UniFi Controller {self.host}")
                return True
            else:
                logger.error(f"Falha no login: {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de conexão: {e}")
            raise ConnectionError(f"Não foi possível conectar: {e}")

    def logout(self):
        """Faz logout do controller"""
        if self._logged_in:
            try:
                self._session.post(f"{self.base_url}/api/logout")
            except Exception:
                pass
        self._logged_in = False
        logger.info("Desconectado do UniFi Controller")

    def _api_call(
        self,
        endpoint: str,
        method: str = "GET",
        data: Dict = None
    ) -> Dict:
        """
        Faz chamada à API

        Args:
            endpoint: Endpoint da API
            method: Método HTTP
            data: Dados para POST/PUT

        Returns:
            Resposta da API
        """
        if not self._logged_in:
            raise RuntimeError("Não logado. Execute login() primeiro")

        url = f"{self.base_url}/api/s/{self.site}/{endpoint}"

        try:
            if method == "GET":
                response = self._session.get(url)
            elif method == "POST":
                response = self._session.post(url, json=data)
            elif method == "PUT":
                response = self._session.put(url, json=data)
            elif method == "DELETE":
                response = self._session.delete(url)
            else:
                raise ValueError(f"Método HTTP inválido: {method}")

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erro na API ({endpoint}): {response.status_code}")
                return {"meta": {"rc": "error"}, "data": []}

        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição: {e}")
            return {"meta": {"rc": "error"}, "data": []}

    def get_clients(self, only_active: bool = True) -> List[Dict]:
        """
        Lista clientes conectados

        Args:
            only_active: Apenas clientes ativos

        Returns:
            Lista de clientes
        """
        endpoint = "stat/sta" if only_active else "rest/user"
        response = self._api_call(endpoint)

        return response.get("data", [])

    def get_client_by_mac(self, mac: str) -> Optional[Dict]:
        """
        Busca cliente por MAC address

        Args:
            mac: MAC address do cliente

        Returns:
            Dados do cliente ou None
        """
        mac = mac.lower().replace("-", ":").replace(".", ":")
        clients = self.get_clients(only_active=False)

        for client in clients:
            if client.get("mac", "").lower() == mac:
                return client

        return None

    def get_access_points(self) -> List[Dict]:
        """
        Lista Access Points

        Returns:
            Lista de APs
        """
        response = self._api_call("stat/device")
        return response.get("data", [])

    def get_ap_by_mac(self, mac: str) -> Optional[Dict]:
        """
        Busca AP por MAC address

        Args:
            mac: MAC address do AP

        Returns:
            Dados do AP ou None
        """
        mac = mac.lower().replace("-", ":").replace(".", ":")
        aps = self.get_access_points()

        for ap in aps:
            if ap.get("mac", "").lower() == mac:
                return ap

        return None

    def get_networks(self) -> List[Dict]:
        """
        Lista redes configuradas

        Returns:
            Lista de redes
        """
        response = self._api_call("rest/networkconf")
        return response.get("data", [])

    def get_wlans(self) -> List[Dict]:
        """
        Lista WLANs (redes WiFi)

        Returns:
            Lista de WLANs
        """
        response = self._api_call("rest/wlanconf")
        return response.get("data", [])

    def get_site_stats(self) -> Dict:
        """
        Obtém estatísticas do site

        Returns:
            Estatísticas gerais
        """
        response = self._api_call("stat/sysinfo")
        data = response.get("data", [])
        return data[0] if data else {}

    def get_health(self) -> List[Dict]:
        """
        Obtém status de saúde do sistema

        Returns:
            Lista de status por subsistema
        """
        response = self._api_call("stat/health")
        return response.get("data", [])

    def get_events(self, limit: int = 100) -> List[Dict]:
        """
        Lista eventos recentes

        Args:
            limit: Número máximo de eventos

        Returns:
            Lista de eventos
        """
        response = self._api_call(f"stat/event?_limit={limit}")
        return response.get("data", [])

    def get_alarms(self) -> List[Dict]:
        """
        Lista alarmes ativos

        Returns:
            Lista de alarmes
        """
        response = self._api_call("stat/alarm")
        return response.get("data", [])

    def block_client(self, mac: str) -> bool:
        """
        Bloqueia um cliente

        Args:
            mac: MAC address do cliente

        Returns:
            True se bloqueado com sucesso
        """
        response = self._api_call(
            "cmd/stamgr",
            method="POST",
            data={"cmd": "block-sta", "mac": mac.lower()}
        )

        if response.get("meta", {}).get("rc") == "ok":
            logger.info(f"Cliente {mac} bloqueado")
            return True
        return False

    def unblock_client(self, mac: str) -> bool:
        """
        Desbloqueia um cliente

        Args:
            mac: MAC address do cliente

        Returns:
            True se desbloqueado com sucesso
        """
        response = self._api_call(
            "cmd/stamgr",
            method="POST",
            data={"cmd": "unblock-sta", "mac": mac.lower()}
        )

        if response.get("meta", {}).get("rc") == "ok":
            logger.info(f"Cliente {mac} desbloqueado")
            return True
        return False

    def reconnect_client(self, mac: str) -> bool:
        """
        Força reconexão de um cliente

        Args:
            mac: MAC address do cliente

        Returns:
            True se comando enviado
        """
        response = self._api_call(
            "cmd/stamgr",
            method="POST",
            data={"cmd": "kick-sta", "mac": mac.lower()}
        )

        if response.get("meta", {}).get("rc") == "ok":
            logger.info(f"Cliente {mac} reconectado")
            return True
        return False

    def restart_ap(self, mac: str) -> bool:
        """
        Reinicia um Access Point

        Args:
            mac: MAC address do AP

        Returns:
            True se comando enviado
        """
        response = self._api_call(
            "cmd/devmgr",
            method="POST",
            data={"cmd": "restart", "mac": mac.lower()}
        )

        if response.get("meta", {}).get("rc") == "ok":
            logger.info(f"AP {mac} reiniciando")
            return True
        return False

    def set_ap_led(self, mac: str, enabled: bool = True) -> bool:
        """
        Liga/desliga LED do AP

        Args:
            mac: MAC address do AP
            enabled: True para ligar, False para desligar

        Returns:
            True se configurado
        """
        response = self._api_call(
            "cmd/devmgr",
            method="POST",
            data={
                "cmd": "set-locate",
                "mac": mac.lower(),
                "enabled": enabled
            }
        )

        return response.get("meta", {}).get("rc") == "ok"

    def authorize_guest(
        self,
        mac: str,
        minutes: int = 60,
        up_kbps: int = None,
        down_kbps: int = None,
        quota_mb: int = None
    ) -> bool:
        """
        Autoriza acesso guest

        Args:
            mac: MAC address do cliente
            minutes: Tempo de acesso em minutos
            up_kbps: Limite de upload em kbps
            down_kbps: Limite de download em kbps
            quota_mb: Quota de dados em MB

        Returns:
            True se autorizado
        """
        data = {
            "cmd": "authorize-guest",
            "mac": mac.lower(),
            "minutes": minutes
        }

        if up_kbps:
            data["up"] = up_kbps
        if down_kbps:
            data["down"] = down_kbps
        if quota_mb:
            data["bytes"] = quota_mb * 1024 * 1024

        response = self._api_call("cmd/stamgr", method="POST", data=data)

        if response.get("meta", {}).get("rc") == "ok":
            logger.info(f"Guest {mac} autorizado por {minutes} minutos")
            return True
        return False

    def unauthorize_guest(self, mac: str) -> bool:
        """
        Remove autorização de guest

        Args:
            mac: MAC address do cliente

        Returns:
            True se removido
        """
        response = self._api_call(
            "cmd/stamgr",
            method="POST",
            data={"cmd": "unauthorize-guest", "mac": mac.lower()}
        )

        if response.get("meta", {}).get("rc") == "ok":
            logger.info(f"Guest {mac} desautorizado")
            return True
        return False

    def get_dpi_stats(self) -> List[Dict]:
        """
        Obtém estatísticas de DPI (Deep Packet Inspection)

        Returns:
            Estatísticas por aplicação
        """
        response = self._api_call("stat/stadpi")
        return response.get("data", [])

    def get_hourly_stats(self, mac: str = None) -> List[Dict]:
        """
        Obtém estatísticas por hora

        Args:
            mac: MAC para filtrar (opcional)

        Returns:
            Estatísticas horárias
        """
        endpoint = "stat/report/hourly.site"
        if mac:
            endpoint = f"stat/report/hourly.user?mac={mac.lower()}"

        response = self._api_call(endpoint)
        return response.get("data", [])


# Exemplo de uso
if __name__ == "__main__":
    print("Cliente UniFi Controller")
    print("Uso:")
    print("  client = UniFiController('192.168.1.1', 'admin', 'senha')")
    print("  client.login()")
    print("  clients = client.get_clients()")
    print("  print(clients)")
