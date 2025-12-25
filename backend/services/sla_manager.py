"""
Conecta Plus - Servico de Gerenciamento de SLA
Calcula prazos, monitora vencimentos e dispara escalacoes
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID
import logging

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..models.sla_config import SLAConfig, SLA_DEFAULTS
from ..models.ocorrencia import Ocorrencia, StatusOcorrencia

logger = logging.getLogger(__name__)


class SLAManagerService:
    """Gerencia SLAs e prazos do sistema."""

    def __init__(self, db: Session):
        self.db = db

    async def get_sla_config(
        self,
        tipo_entidade: str,
        subtipo: str,
        prioridade: str,
        condominio_id: Optional[UUID] = None
    ) -> Optional[SLAConfig]:
        """
        Busca configuracao de SLA aplicavel.
        Prioridade: condominio especifico > global > default
        """
        # Busca config especifica do condominio
        if condominio_id:
            config = self.db.query(SLAConfig).filter(
                and_(
                    SLAConfig.tipo_entidade == tipo_entidade,
                    SLAConfig.subtipo == subtipo,
                    SLAConfig.prioridade == prioridade,
                    SLAConfig.condominio_id == condominio_id,
                    SLAConfig.ativo == True
                )
            ).first()
            if config:
                return config

        # Busca config global
        config = self.db.query(SLAConfig).filter(
            and_(
                SLAConfig.tipo_entidade == tipo_entidade,
                SLAConfig.subtipo == subtipo,
                SLAConfig.prioridade == prioridade,
                SLAConfig.condominio_id == None,
                SLAConfig.ativo == True
            )
        ).first()

        return config

    def get_prazo_minutos(
        self,
        tipo_entidade: str,
        subtipo: str,
        prioridade: str
    ) -> int:
        """
        Retorna prazo em minutos usando defaults se nao houver config.
        """
        defaults = SLA_DEFAULTS.get(tipo_entidade, {})
        subtipo_config = defaults.get(subtipo, defaults.get("default", {}))
        return subtipo_config.get(prioridade, 1440)  # Default 24h

    async def calcular_prazo_estimado(
        self,
        tipo_entidade: str,
        subtipo: str,
        prioridade: str,
        data_abertura: datetime,
        condominio_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Calcula prazo estimado para resolucao.
        Retorna datetime do prazo e informacoes de SLA.
        """
        # Tenta buscar config do banco
        config = await self.get_sla_config(tipo_entidade, subtipo, prioridade, condominio_id)

        if config:
            prazo_minutos = config.prazo_resolucao
            origem = "sla_config"
        else:
            prazo_minutos = self.get_prazo_minutos(tipo_entidade, subtipo, prioridade)
            origem = "sla_default"

        prazo_estimado = data_abertura + timedelta(minutes=prazo_minutos)

        return {
            "prazo_estimado": prazo_estimado,
            "prazo_minutos": prazo_minutos,
            "prazo_formatado": self._formatar_prazo(prazo_minutos),
            "origem": origem,
            "config_id": str(config.id) if config else None
        }

    def _formatar_prazo(self, minutos: int) -> str:
        """Formata prazo em minutos para texto legivel."""
        if minutos < 60:
            return f"{minutos} minutos"
        elif minutos < 1440:
            horas = minutos / 60
            return f"{horas:.0f}h" if horas == int(horas) else f"{horas:.1f}h"
        else:
            dias = minutos / 1440
            return f"{dias:.0f} dia(s)" if dias == int(dias) else f"{dias:.1f} dia(s)"

    async def verificar_status_sla(
        self,
        prazo_estimado: datetime,
        prazo_alerta_amarelo: Optional[int] = None,
        prazo_alerta_vermelho: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Verifica status atual do SLA.
        Retorna: status (verde/amarelo/vermelho/estourado), tempo restante, percentual
        """
        agora = datetime.utcnow()

        if agora >= prazo_estimado:
            tempo_estourado = agora - prazo_estimado
            return {
                "status": "estourado",
                "cor": "vermelho",
                "tempo_restante": None,
                "tempo_estourado": tempo_estourado,
                "tempo_estourado_minutos": int(tempo_estourado.total_seconds() / 60),
                "percentual": 100,
                "mensagem": f"SLA estourado ha {self._formatar_tempo(tempo_estourado)}"
            }

        tempo_restante = prazo_estimado - agora
        tempo_restante_minutos = int(tempo_restante.total_seconds() / 60)

        # Calcula percentual
        # Assumindo que queremos alerta amarelo em 25% restante e vermelho em 10%
        if prazo_alerta_amarelo:
            limiar_amarelo = prazo_alerta_amarelo
        else:
            limiar_amarelo = tempo_restante_minutos * 0.25

        if prazo_alerta_vermelho:
            limiar_vermelho = prazo_alerta_vermelho
        else:
            limiar_vermelho = tempo_restante_minutos * 0.10

        if tempo_restante_minutos <= limiar_vermelho:
            status = "vermelho"
            cor = "vermelho"
            mensagem = f"URGENTE: Apenas {self._formatar_prazo(tempo_restante_minutos)} restantes!"
        elif tempo_restante_minutos <= limiar_amarelo:
            status = "amarelo"
            cor = "amarelo"
            mensagem = f"Atencao: {self._formatar_prazo(tempo_restante_minutos)} restantes"
        else:
            status = "verde"
            cor = "verde"
            mensagem = f"Prazo: {self._formatar_prazo(tempo_restante_minutos)} restantes"

        return {
            "status": status,
            "cor": cor,
            "tempo_restante": tempo_restante,
            "tempo_restante_minutos": tempo_restante_minutos,
            "tempo_restante_formatado": self._formatar_prazo(tempo_restante_minutos),
            "percentual": max(0, min(100, 100 - (tempo_restante_minutos / 1440 * 100))),
            "mensagem": mensagem
        }

    def _formatar_tempo(self, delta: timedelta) -> str:
        """Formata timedelta para texto legivel."""
        total_minutos = int(delta.total_seconds() / 60)
        return self._formatar_prazo(total_minutos)

    async def get_ocorrencias_sla_critico(
        self,
        condominio_id: UUID,
        limite: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retorna ocorrencias com SLA proximo de estourar ou ja estourado.
        """
        agora = datetime.utcnow()

        ocorrencias = self.db.query(Ocorrencia).filter(
            and_(
                Ocorrencia.condominio_id == condominio_id,
                Ocorrencia.status.in_([
                    StatusOcorrencia.ABERTA.value,
                    StatusOcorrencia.EM_ANALISE.value,
                    StatusOcorrencia.EM_ANDAMENTO.value,
                    StatusOcorrencia.AGUARDANDO.value
                ])
            )
        ).order_by(Ocorrencia.created_at).limit(limite).all()

        resultado = []
        for oc in ocorrencias:
            # Calcula prazo
            info_prazo = await self.calcular_prazo_estimado(
                "ocorrencia",
                oc.tipo or "default",
                oc.prioridade or "media",
                oc.created_at,
                condominio_id
            )

            status_sla = await self.verificar_status_sla(info_prazo["prazo_estimado"])

            if status_sla["status"] in ["amarelo", "vermelho", "estourado"]:
                resultado.append({
                    "id": str(oc.id),
                    "titulo": oc.titulo,
                    "tipo": oc.tipo,
                    "prioridade": oc.prioridade,
                    "status": oc.status,
                    "created_at": oc.created_at.isoformat(),
                    "prazo_estimado": info_prazo["prazo_estimado"].isoformat(),
                    "sla_status": status_sla
                })

        # Ordena por criticidade
        resultado.sort(key=lambda x: (
            0 if x["sla_status"]["status"] == "estourado" else
            1 if x["sla_status"]["status"] == "vermelho" else 2
        ))

        return resultado

    async def escalar_ocorrencias_vencidas(self, condominio_id: UUID) -> int:
        """
        Escala automaticamente ocorrencias com SLA estourado.
        Retorna quantidade de ocorrencias escaladas.
        """
        ocorrencias_criticas = await self.get_ocorrencias_sla_critico(condominio_id, limite=100)

        escaladas = 0
        for oc in ocorrencias_criticas:
            if oc["sla_status"]["status"] == "estourado":
                # Aqui faria a logica de escalacao
                # Por enquanto apenas loga
                logger.warning(
                    "ocorrencia_sla_estourado",
                    ocorrencia_id=oc["id"],
                    titulo=oc["titulo"],
                    tempo_estourado=oc["sla_status"].get("tempo_estourado_minutos")
                )
                escaladas += 1

        return escaladas
