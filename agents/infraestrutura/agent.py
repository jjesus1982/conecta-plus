"""
Agente Infraestrutura - Gestão de infraestrutura de TI
Conecta Plus
"""

from typing import List, Dict
from agents.base.agent import BaseAgent


class AgenteInfraestrutura(BaseAgent):
    """Agente de infraestrutura de TI"""

    def __init__(self):
        super().__init__(
            name="infraestrutura",
            description="Agente de gestão de infraestrutura de TI",
            model="claude-3-5-sonnet-20241022",
            temperature=0.3,
        )

    @property
    def system_prompt(self) -> str:
        return """Você é o Agente de Infraestrutura do Conecta Plus, especializado em:

1. SERVIDORES:
   - Monitoramento de recursos (CPU, RAM, disco)
   - Containers Docker
   - Kubernetes
   - Backups

2. BANCO DE DADOS:
   - PostgreSQL
   - Redis
   - MongoDB
   - Performance e otimização

3. REDE:
   - Conectividade
   - DNS e certificados SSL
   - Load balancing
   - CDN

4. SEGURANÇA:
   - Firewall
   - Atualizações de segurança
   - Logs de auditoria
   - Detecção de intrusão

5. DISPONIBILIDADE:
   - Uptime e SLA
   - Failover
   - Disaster recovery
   - Alertas de incidentes

Mantenha a infraestrutura estável, segura e performática."""

    def get_tools(self) -> List[Dict]:
        return [
            {"name": "get_server_status", "description": "Status dos servidores"},
            {"name": "check_services", "description": "Verifica serviços"},
            {"name": "run_backup", "description": "Executa backup"},
            {"name": "check_ssl", "description": "Verifica certificados SSL"},
            {"name": "get_logs", "description": "Busca logs"},
            {"name": "restart_service", "description": "Reinicia serviço"},
            {"name": "scale_service", "description": "Escala serviço"},
            {"name": "get_metrics", "description": "Métricas de infraestrutura"},
        ]

    def get_mcps(self) -> List[str]:
        return []


agente_infraestrutura = AgenteInfraestrutura()
