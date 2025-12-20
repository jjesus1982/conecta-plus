"""
Agente Rede - Gestão de infraestrutura de rede
Conecta Plus
"""

from typing import List, Dict
from agents.base.agent import BaseAgent


class AgenteRede(BaseAgent):
    """Agente especializado em infraestrutura de rede"""

    def __init__(self):
        super().__init__(
            name="rede",
            description="Agente de gestão de rede e conectividade",
            model="claude-3-5-sonnet-20241022",
            temperature=0.3,
        )

    @property
    def system_prompt(self) -> str:
        return """Você é o Agente de Rede do Conecta Plus, especializado em:

1. MONITORAMENTO:
   - Status de equipamentos (MikroTik, Ubiquiti, Furukawa)
   - Consumo de banda
   - Latência e perda de pacotes
   - Clientes conectados

2. WIFI:
   - Gerenciar SSIDs
   - Autorizar/bloquear dispositivos
   - Configurar hotspot para visitantes
   - Verificar força de sinal

3. ROTEAMENTO:
   - Regras de firewall
   - NAT e redirecionamentos
   - VPN para acesso remoto
   - Balanceamento de links

4. FIBRA ÓPTICA (GPON):
   - Status de ONUs
   - Níveis de sinal óptico
   - Provisionamento de novos clientes

5. TROUBLESHOOTING:
   - Diagnóstico de problemas
   - Testes de conectividade
   - Análise de tráfego

Mantenha a rede estável e segura para todos os serviços."""

    def get_tools(self) -> List[Dict]:
        return [
            {"name": "get_network_status", "description": "Status geral da rede"},
            {"name": "list_clients", "description": "Lista clientes conectados"},
            {"name": "get_bandwidth", "description": "Consumo de banda"},
            {"name": "block_client", "description": "Bloqueia cliente"},
            {"name": "unblock_client", "description": "Desbloqueia cliente"},
            {"name": "authorize_guest", "description": "Autoriza acesso visitante"},
            {"name": "add_firewall_rule", "description": "Adiciona regra firewall"},
            {"name": "get_onu_signal", "description": "Sinal de ONU GPON"},
            {"name": "restart_device", "description": "Reinicia equipamento"},
            {"name": "run_diagnostic", "description": "Executa diagnóstico"},
        ]

    def get_mcps(self) -> List[str]:
        return [
            "mcp-mikrotik",
            "mcp-ubiquiti",
            "mcp-furukawa",
        ]


agente_rede = AgenteRede()
