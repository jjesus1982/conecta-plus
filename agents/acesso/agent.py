"""
Agente Acesso - Controle de acesso físico
Conecta Plus
"""

from typing import List, Dict
from agents.base.agent import BaseAgent


class AgenteAcesso(BaseAgent):
    """Agente especializado em controle de acesso"""

    def __init__(self):
        super().__init__(
            name="acesso",
            description="Agente de controle de acesso físico e biometria",
            model="claude-3-5-sonnet-20241022",
            temperature=0.3,
        )

    @property
    def system_prompt(self) -> str:
        return """Você é o Agente de Acesso do Conecta Plus, especializado em:

1. CONTROLE DE ACESSO:
   - Gerenciar controladoras (Control iD, Intelbras SS/CT)
   - Cadastrar/remover usuários
   - Definir permissões de acesso
   - Gerenciar credenciais (cartão, biometria, facial, senha)

2. CADASTRO BIOMÉTRICO:
   - Cadastrar digitais
   - Cadastrar reconhecimento facial
   - Sincronizar cadastros entre dispositivos

3. REGRAS DE ACESSO:
   - Configurar horários permitidos
   - Definir zonas de acesso
   - Criar regras por perfil de usuário
   - Gerenciar visitantes temporários

4. MONITORAMENTO:
   - Logs de acesso em tempo real
   - Tentativas de acesso negadas
   - Porta aberta por tempo excessivo
   - Acesso em horário não autorizado

5. INTEGRAÇÃO:
   - Sincronizar com cadastro de moradores
   - Integrar com portaria virtual
   - Notificar síndico sobre eventos críticos

Priorize segurança, mas mantenha a praticidade para os usuários."""

    def get_tools(self) -> List[Dict]:
        return [
            {"name": "add_user", "description": "Cadastra usuário no sistema de acesso"},
            {"name": "remove_user", "description": "Remove usuário"},
            {"name": "add_credential", "description": "Adiciona credencial (cartão, digital, face)"},
            {"name": "set_access_rule", "description": "Define regra de acesso"},
            {"name": "open_door", "description": "Abre porta remotamente"},
            {"name": "get_access_logs", "description": "Consulta logs de acesso"},
            {"name": "sync_devices", "description": "Sincroniza cadastros entre dispositivos"},
            {"name": "add_visitor", "description": "Cadastra visitante temporário"},
            {"name": "list_controllers", "description": "Lista controladoras"},
            {"name": "get_controller_status", "description": "Status de controladora"},
        ]

    def get_mcps(self) -> List[str]:
        return [
            "mcp-control-id",
            "mcp-intelbras-acesso",
            "mcp-vision-ai",  # Para facial
        ]


agente_acesso = AgenteAcesso()
