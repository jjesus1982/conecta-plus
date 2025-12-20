"""
Conecta Plus - Agente Portaria Virtual ULTRA
Sistema inteligente de portaria, rondas, NCs e atendimento omnichannel
"""

from .agent_v2 import (
    # Agente Principal
    AgentePortariaVirtual,
    create_virtual_doorman_agent,

    # Enums de Atendimento
    TipoAtendimento,
    StatusAtendimento,
    TipoValidacao,

    # Enums de Ronda
    StatusRonda,
    TipoCheckpoint,
    PrioridadeCheckpoint,

    # Enums de NC
    CategoriaNaoConformidade,
    SeveridadeNC,
    StatusNC,

    # Enums de Segurança Porteiro
    TipoAlertaPorteiro,
    StatusPorteiro,

    # Enums de Atendimento Omnichannel
    CanalAtendimento,
    StatusConversacao,

    # Dataclasses
    Atendimento,
    ChamadaInterfone,
    Checkpoint,
    RotaRonda,
    RondaExecucao,
    CheckpointVisita,
    NaoConformidade,
    DocumentacaoVisual,
    AlertaPorteiro,
    Conversacao,
    PorteiroStatus,
)

__all__ = [
    # Agente
    "AgentePortariaVirtual",
    "create_virtual_doorman_agent",

    # Atendimento
    "TipoAtendimento",
    "StatusAtendimento",
    "TipoValidacao",
    "Atendimento",
    "ChamadaInterfone",

    # Ronda
    "StatusRonda",
    "TipoCheckpoint",
    "PrioridadeCheckpoint",
    "Checkpoint",
    "RotaRonda",
    "RondaExecucao",
    "CheckpointVisita",

    # NC
    "CategoriaNaoConformidade",
    "SeveridadeNC",
    "StatusNC",
    "NaoConformidade",

    # Documentação
    "DocumentacaoVisual",

    # Segurança Porteiro
    "TipoAlertaPorteiro",
    "StatusPorteiro",
    "AlertaPorteiro",
    "PorteiroStatus",

    # Omnichannel
    "CanalAtendimento",
    "StatusConversacao",
    "Conversacao",
]
