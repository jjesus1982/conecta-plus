"""
Conecta Plus - Cliente MikroTik RouterOS API
Permite gerenciamento de roteadores MikroTik via API

Dependências:
    pip install librouteros

Uso:
    from mikrotik_client import MikroTikClient

    # Conectar ao roteador
    client = MikroTikClient('192.168.88.1', 'admin', 'senha')
    client.connect()

    # Listar interfaces
    interfaces = client.get_interfaces()

    # Listar clientes PPPoE
    pppoe_clients = client.get_pppoe_active()
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RouterInfo:
    """Informações do roteador"""
    identity: str
    model: str
    serial_number: str
    firmware: str
    uptime: str
    cpu_load: int
    free_memory: int
    total_memory: int


@dataclass
class Interface:
    """Interface de rede"""
    name: str
    type: str
    mac_address: str
    running: bool
    disabled: bool
    rx_bytes: int
    tx_bytes: int


@dataclass
class PPPoEClient:
    """Cliente PPPoE ativo"""
    name: str
    service: str
    caller_id: str
    address: str
    uptime: str
    encoding: str
    rx_bytes: int
    tx_bytes: int


class MikroTikClient:
    """
    Cliente para API do MikroTik RouterOS

    Funcionalidades:
    - Gerenciamento de interfaces
    - Controle de clientes PPPoE
    - Monitoramento de tráfego
    - Configuração de firewall
    - Gerenciamento de filas (QoS)
    - Controle de hotspot
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 8728,
        use_ssl: bool = False
    ):
        """
        Inicializa o cliente MikroTik

        Args:
            host: IP ou hostname do roteador
            username: Usuário para autenticação
            password: Senha para autenticação
            port: Porta da API (8728 ou 8729 para SSL)
            use_ssl: Usar conexão SSL
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl

        self._api = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Verifica se está conectado"""
        return self._connected and self._api is not None

    def connect(self) -> bool:
        """
        Conecta ao roteador MikroTik

        Returns:
            True se conectou com sucesso

        Raises:
            ConnectionError: Se não conseguir conectar
        """
        try:
            import librouteros

            logger.info(f"Conectando ao MikroTik {self.host}:{self.port}...")

            # Método de conexão
            method = librouteros.connect

            self._api = method(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password
            )

            self._connected = True
            logger.info(f"Conectado ao MikroTik {self.host}")
            return True

        except ImportError:
            logger.error("Biblioteca librouteros não instalada. Execute: pip install librouteros")
            raise
        except Exception as e:
            logger.error(f"Erro ao conectar ao MikroTik: {e}")
            raise ConnectionError(f"Não foi possível conectar: {e}")

    def disconnect(self):
        """Desconecta do roteador"""
        if self._api:
            try:
                self._api.close()
            except Exception:
                pass
            self._api = None
        self._connected = False
        logger.info("Desconectado do MikroTik")

    def _execute(self, path: str, **kwargs) -> List[Dict]:
        """
        Executa comando na API

        Args:
            path: Caminho do comando (ex: '/interface')
            **kwargs: Parâmetros adicionais

        Returns:
            Lista de resultados
        """
        if not self.is_connected:
            raise RuntimeError("Não conectado. Execute connect() primeiro")

        try:
            result = self._api.path(path)
            return list(result)
        except Exception as e:
            logger.error(f"Erro ao executar {path}: {e}")
            raise

    def get_router_info(self) -> RouterInfo:
        """
        Obtém informações do roteador

        Returns:
            RouterInfo com dados do roteador
        """
        # Identity
        identity = self._execute('/system/identity')
        identity_name = identity[0]['name'] if identity else "Unknown"

        # Resource
        resource = self._execute('/system/resource')
        res = resource[0] if resource else {}

        # RouterBoard
        board = self._execute('/system/routerboard')
        board_info = board[0] if board else {}

        return RouterInfo(
            identity=identity_name,
            model=board_info.get('model', 'Unknown'),
            serial_number=board_info.get('serial-number', 'Unknown'),
            firmware=res.get('version', 'Unknown'),
            uptime=res.get('uptime', 'Unknown'),
            cpu_load=int(res.get('cpu-load', 0)),
            free_memory=int(res.get('free-memory', 0)),
            total_memory=int(res.get('total-memory', 0))
        )

    def get_interfaces(self, include_disabled: bool = False) -> List[Interface]:
        """
        Lista interfaces de rede

        Args:
            include_disabled: Incluir interfaces desabilitadas

        Returns:
            Lista de Interface
        """
        interfaces = self._execute('/interface')

        result = []
        for iface in interfaces:
            if not include_disabled and iface.get('disabled', False):
                continue

            result.append(Interface(
                name=iface.get('name', ''),
                type=iface.get('type', ''),
                mac_address=iface.get('mac-address', ''),
                running=iface.get('running', False),
                disabled=iface.get('disabled', False),
                rx_bytes=int(iface.get('rx-byte', 0)),
                tx_bytes=int(iface.get('tx-byte', 0))
            ))

        return result

    def get_pppoe_active(self) -> List[PPPoEClient]:
        """
        Lista clientes PPPoE ativos

        Returns:
            Lista de PPPoEClient
        """
        clients = self._execute('/ppp/active')

        result = []
        for client in clients:
            result.append(PPPoEClient(
                name=client.get('name', ''),
                service=client.get('service', ''),
                caller_id=client.get('caller-id', ''),
                address=client.get('address', ''),
                uptime=client.get('uptime', ''),
                encoding=client.get('encoding', ''),
                rx_bytes=int(client.get('rx-byte', 0)),
                tx_bytes=int(client.get('tx-byte', 0))
            ))

        return result

    def get_pppoe_secrets(self) -> List[Dict]:
        """
        Lista secrets PPPoE (usuários cadastrados)

        Returns:
            Lista de secrets
        """
        return self._execute('/ppp/secret')

    def add_pppoe_secret(
        self,
        name: str,
        password: str,
        profile: str = "default",
        service: str = "pppoe",
        remote_address: str = None,
        comment: str = None
    ) -> bool:
        """
        Adiciona um secret PPPoE

        Args:
            name: Nome do usuário
            password: Senha
            profile: Perfil de conexão
            service: Tipo de serviço
            remote_address: IP fixo (opcional)
            comment: Comentário

        Returns:
            True se adicionado com sucesso
        """
        params = {
            'name': name,
            'password': password,
            'profile': profile,
            'service': service
        }

        if remote_address:
            params['remote-address'] = remote_address
        if comment:
            params['comment'] = comment

        try:
            self._api.path('/ppp/secret').add(**params)
            logger.info(f"Secret PPPoE '{name}' adicionado")
            return True
        except Exception as e:
            logger.error(f"Erro ao adicionar secret: {e}")
            return False

    def remove_pppoe_secret(self, name: str) -> bool:
        """
        Remove um secret PPPoE

        Args:
            name: Nome do usuário

        Returns:
            True se removido com sucesso
        """
        try:
            secrets = self._execute('/ppp/secret')
            for secret in secrets:
                if secret.get('name') == name:
                    self._api.path('/ppp/secret').remove(secret['.id'])
                    logger.info(f"Secret PPPoE '{name}' removido")
                    return True
            logger.warning(f"Secret '{name}' não encontrado")
            return False
        except Exception as e:
            logger.error(f"Erro ao remover secret: {e}")
            return False

    def disconnect_pppoe_user(self, name: str) -> bool:
        """
        Desconecta um usuário PPPoE ativo

        Args:
            name: Nome do usuário

        Returns:
            True se desconectado
        """
        try:
            active = self._execute('/ppp/active')
            for client in active:
                if client.get('name') == name:
                    self._api.path('/ppp/active').remove(client['.id'])
                    logger.info(f"Usuário PPPoE '{name}' desconectado")
                    return True
            logger.warning(f"Usuário '{name}' não está ativo")
            return False
        except Exception as e:
            logger.error(f"Erro ao desconectar usuário: {e}")
            return False

    def get_queues(self) -> List[Dict]:
        """
        Lista filas de QoS (Simple Queues)

        Returns:
            Lista de filas
        """
        return self._execute('/queue/simple')

    def set_queue_limit(
        self,
        name: str,
        max_upload: str,
        max_download: str
    ) -> bool:
        """
        Define limites de velocidade na fila

        Args:
            name: Nome da fila
            max_upload: Limite de upload (ex: "10M")
            max_download: Limite de download (ex: "50M")

        Returns:
            True se configurado com sucesso
        """
        try:
            queues = self._execute('/queue/simple')
            for queue in queues:
                if queue.get('name') == name:
                    self._api.path('/queue/simple').update(
                        **{'.id': queue['.id'], 'max-limit': f"{max_upload}/{max_download}"}
                    )
                    logger.info(f"Fila '{name}' atualizada: {max_upload}/{max_download}")
                    return True
            logger.warning(f"Fila '{name}' não encontrada")
            return False
        except Exception as e:
            logger.error(f"Erro ao atualizar fila: {e}")
            return False

    def get_traffic_stats(self, interface: str) -> Dict[str, Any]:
        """
        Obtém estatísticas de tráfego de uma interface

        Args:
            interface: Nome da interface

        Returns:
            Dicionário com estatísticas
        """
        interfaces = self._execute('/interface')

        for iface in interfaces:
            if iface.get('name') == interface:
                return {
                    'name': interface,
                    'rx_bytes': int(iface.get('rx-byte', 0)),
                    'tx_bytes': int(iface.get('tx-byte', 0)),
                    'rx_packets': int(iface.get('rx-packet', 0)),
                    'tx_packets': int(iface.get('tx-packet', 0)),
                    'rx_errors': int(iface.get('rx-error', 0)),
                    'tx_errors': int(iface.get('tx-error', 0)),
                    'running': iface.get('running', False)
                }

        return {}

    def get_hotspot_active(self) -> List[Dict]:
        """
        Lista usuários hotspot ativos

        Returns:
            Lista de usuários ativos
        """
        return self._execute('/ip/hotspot/active')

    def get_dhcp_leases(self) -> List[Dict]:
        """
        Lista leases DHCP

        Returns:
            Lista de leases
        """
        return self._execute('/ip/dhcp-server/lease')

    def execute_command(self, path: str) -> List[Dict]:
        """
        Executa comando personalizado na API

        Args:
            path: Caminho do comando

        Returns:
            Resultado do comando
        """
        return self._execute(path)


# Exemplo de uso
if __name__ == "__main__":
    # Exemplo de conexão (não executar sem roteador configurado)
    print("Cliente MikroTik RouterOS")
    print("Uso:")
    print("  client = MikroTikClient('192.168.88.1', 'admin', 'senha')")
    print("  client.connect()")
    print("  info = client.get_router_info()")
    print("  print(info)")
