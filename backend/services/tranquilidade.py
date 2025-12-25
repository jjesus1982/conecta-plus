"""
Conecta Plus - Servico de Tranquilidade
Calcula estado de tranquilidade e recomendacoes por perfil
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID
import logging

from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from ..models.tranquilidade import (
    TranquilidadeSnapshot,
    EstadoTranquilidade,
    PerfilUsuario,
    CRITERIOS_ESTADO,
    RECOMENDACOES_PADRAO
)
from ..models.ocorrencia import Ocorrencia, StatusOcorrencia
from ..models.financeiro import Boleto
from .sla_manager import SLAManagerService

logger = logging.getLogger(__name__)


class TranquilidadeService:
    """Servico para calcular e gerenciar estado de tranquilidade."""

    def __init__(self, db: Session):
        self.db = db
        self.sla_manager = SLAManagerService(db)

    async def calcular_tranquilidade(
        self,
        perfil: str,
        usuario_id: UUID,
        condominio_id: UUID
    ) -> TranquilidadeSnapshot:
        """
        Calcula o estado de tranquilidade para um perfil/usuario.
        Retorna snapshot com estado, contadores e recomendacoes.
        """
        # Coleta metricas
        metricas = await self._coletar_metricas(condominio_id, perfil, usuario_id)

        # Calcula estado
        estado = self._calcular_estado(metricas)

        # Gera "Precisa de voce"
        precisa_de_voce = await self._gerar_precisa_de_voce(
            condominio_id, perfil, usuario_id, metricas
        )

        # Gera recomendacao
        recomendacao = self._gerar_recomendacao(metricas, estado, perfil)

        # Calcula score (0-100)
        score = self._calcular_score(metricas)

        # Mensagem principal
        mensagem = CRITERIOS_ESTADO.get(estado, {}).get("mensagem", "")

        # Cria snapshot
        snapshot = TranquilidadeSnapshot(
            perfil=perfil,
            usuario_id=usuario_id,
            condominio_id=condominio_id,
            estado=estado.value,
            score=score,
            mensagem_principal=mensagem,
            alertas_criticos=metricas["alertas_criticos"],
            alertas_medios=metricas["alertas_medios"],
            ocorrencias_abertas=metricas["ocorrencias_abertas"],
            ocorrencias_sla_proximo=metricas["ocorrencias_sla_proximo"],
            ocorrencias_sla_estourado=metricas["ocorrencias_sla_estourado"],
            cameras_offline=metricas["cameras_offline"],
            inadimplencia_percentual=metricas["inadimplencia_percentual"],
            precisa_de_voce=precisa_de_voce,
            resolvido_hoje=metricas["resolvido_hoje"],
            recomendacao=recomendacao["mensagem"],
            recomendacao_tipo=recomendacao["tipo"],
            saude_condominio=self._gerar_saude_condominio(metricas) if perfil in ["sindico", "gerente", "admin"] else {},
            proxima_tarefa=await self._gerar_proxima_tarefa(condominio_id) if perfil == "porteiro" else None,
            expires_at=datetime.utcnow() + timedelta(minutes=5)  # Cache 5 min
        )

        # Salva no banco
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)

        return snapshot

    async def _coletar_metricas(
        self,
        condominio_id: UUID,
        perfil: str,
        usuario_id: UUID
    ) -> Dict[str, Any]:
        """Coleta todas as metricas necessarias para calculo."""
        agora = datetime.utcnow()
        inicio_dia = agora.replace(hour=0, minute=0, second=0, microsecond=0)

        # Alertas de seguranca
        alertas_criticos = 0
        alertas_medios = 0

        # Ocorrencias
        ocorrencias_abertas = self.db.query(func.count(Ocorrencia.id)).filter(
            and_(
                Ocorrencia.condominio_id == condominio_id,
                Ocorrencia.status.in_([
                    StatusOcorrencia.ABERTA.value,
                    StatusOcorrencia.EM_ANALISE.value,
                    StatusOcorrencia.EM_ANDAMENTO.value,
                    StatusOcorrencia.AGUARDANDO.value
                ])
            )
        ).scalar() or 0

        # Ocorrencias com SLA critico
        ocorrencias_sla = await self.sla_manager.get_ocorrencias_sla_critico(condominio_id)
        ocorrencias_sla_proximo = sum(1 for o in ocorrencias_sla if o["sla_status"]["status"] == "amarelo")
        ocorrencias_sla_estourado = sum(1 for o in ocorrencias_sla if o["sla_status"]["status"] in ["vermelho", "estourado"])

        # Resolvidas hoje
        resolvido_hoje = self.db.query(func.count(Ocorrencia.id)).filter(
            and_(
                Ocorrencia.condominio_id == condominio_id,
                Ocorrencia.status == StatusOcorrencia.RESOLVIDA.value,
                Ocorrencia.resolvido_at >= inicio_dia
            )
        ).scalar() or 0

        # Cameras offline (a ser implementado com integração CFTV)
        cameras_offline = 0

        # Inadimplencia
        total_boletos = self.db.query(func.count(Boleto.id)).filter(
            Boleto.condominio_id == condominio_id
        ).scalar() or 1

        boletos_vencidos = self.db.query(func.count(Boleto.id)).filter(
            and_(
                Boleto.condominio_id == condominio_id,
                Boleto.status == "VENCIDO"
            )
        ).scalar() or 0

        inadimplencia_percentual = (boletos_vencidos / total_boletos) * 100 if total_boletos > 0 else 0

        return {
            "alertas_criticos": alertas_criticos,
            "alertas_medios": alertas_medios,
            "ocorrencias_abertas": ocorrencias_abertas,
            "ocorrencias_sla_proximo": ocorrencias_sla_proximo,
            "ocorrencias_sla_estourado": ocorrencias_sla_estourado,
            "cameras_offline": cameras_offline,
            "inadimplencia_percentual": round(inadimplencia_percentual, 1),
            "resolvido_hoje": resolvido_hoje
        }

    def _calcular_estado(self, metricas: Dict[str, Any]) -> EstadoTranquilidade:
        """Calcula estado baseado nas metricas."""
        # Criterios para VERMELHO (qualquer um)
        if (
            metricas["alertas_criticos"] > 0 or
            metricas["ocorrencias_sla_estourado"] > 0 or
            metricas["inadimplencia_percentual"] > 20 or
            metricas["cameras_offline"] > 3
        ):
            return EstadoTranquilidade.VERMELHO

        # Criterios para AMARELO
        criterios_amarelo = CRITERIOS_ESTADO[EstadoTranquilidade.AMARELO]
        if (
            metricas["alertas_medios"] > 2 or
            metricas["ocorrencias_sla_proximo"] > 0 or
            metricas["inadimplencia_percentual"] > 10 or
            metricas["cameras_offline"] > 1
        ):
            return EstadoTranquilidade.AMARELO

        return EstadoTranquilidade.VERDE

    def _calcular_score(self, metricas: Dict[str, Any]) -> float:
        """Calcula score de 0-100 (maior = melhor)."""
        score = 100.0

        # Penalidades
        score -= metricas["alertas_criticos"] * 20
        score -= metricas["alertas_medios"] * 5
        score -= metricas["ocorrencias_sla_estourado"] * 15
        score -= metricas["ocorrencias_sla_proximo"] * 5
        score -= metricas["cameras_offline"] * 10
        score -= metricas["inadimplencia_percentual"] * 0.5

        # Bonus
        score += min(metricas["resolvido_hoje"] * 2, 10)  # Max 10 pontos

        return max(0, min(100, score))

    async def _gerar_precisa_de_voce(
        self,
        condominio_id: UUID,
        perfil: str,
        usuario_id: UUID,
        metricas: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Gera lista de itens que precisam de atencao (max 3)."""
        itens = []

        # Alertas criticos (placeholder - sistema de alertas a ser implementado)
        if metricas["alertas_criticos"] > 0:
            itens.append({
                "titulo": f"{metricas['alertas_criticos']} alerta(s) critico(s)",
                "descricao": "Requerem atencao imediata",
                "urgencia": "critica",
                "link": "/alertas?severity=critical",
                "tipo": "alerta"
            })

        # SLA estourado
        if metricas["ocorrencias_sla_estourado"] > 0:
            itens.append({
                "titulo": f"{metricas['ocorrencias_sla_estourado']} SLA(s) estourado(s)",
                "descricao": "Prazo de atendimento ultrapassado",
                "urgencia": "alta",
                "link": "/ocorrencias?sla=estourado",
                "tipo": "ocorrencia"
            })

        # Inadimplencia alta (apenas para sindico/gerente)
        if perfil in ["sindico", "gerente"] and metricas["inadimplencia_percentual"] > 15:
            itens.append({
                "titulo": f"Inadimplencia em {metricas['inadimplencia_percentual']:.1f}%",
                "descricao": "Acima do ideal, verificar cobranças",
                "urgencia": "media",
                "link": "/financeiro/inadimplencia",
                "tipo": "financeiro"
            })

        # SLA proximo
        if metricas["ocorrencias_sla_proximo"] > 0 and len(itens) < 3:
            itens.append({
                "titulo": f"{metricas['ocorrencias_sla_proximo']} prazo(s) proximo(s)",
                "descricao": "Ocorrências próximas do vencimento",
                "urgencia": "media",
                "link": "/ocorrencias?sla=proximo",
                "tipo": "ocorrencia"
            })

        return itens[:3]  # Maximo 3 itens

    def _gerar_recomendacao(
        self,
        metricas: Dict[str, Any],
        estado: EstadoTranquilidade,
        perfil: str
    ) -> Dict[str, Any]:
        """Gera recomendacao principal baseada no contexto."""
        if estado == EstadoTranquilidade.VERDE:
            return {
                "tipo": "parabens",
                "mensagem": "Nenhuma acao necessaria agora. Tudo sob controle!",
                "icone": "check-circle"
            }

        if metricas["alertas_criticos"] > 0:
            return {
                "tipo": "alerta",
                "mensagem": f"Atencao: {metricas['alertas_criticos']} alerta(s) critico(s) aguardando tratamento.",
                "icone": "alert-triangle"
            }

        if metricas["ocorrencias_sla_estourado"] > 0:
            return {
                "tipo": "acao",
                "mensagem": f"Priorize: {metricas['ocorrencias_sla_estourado']} ocorrencia(s) com prazo estourado.",
                "icone": "clock"
            }

        if metricas["inadimplencia_percentual"] > 15 and perfil in ["sindico", "gerente"]:
            return {
                "tipo": "informativo",
                "mensagem": f"Inadimplencia em {metricas['inadimplencia_percentual']:.1f}%. Considere acoes de cobranca.",
                "icone": "dollar-sign"
            }

        return {
            "tipo": "informativo",
            "mensagem": "Alguns itens requerem sua atencao. Verifique a lista acima.",
            "icone": "info"
        }

    def _gerar_saude_condominio(self, metricas: Dict[str, Any]) -> Dict[str, Any]:
        """Gera indicadores de saude do condominio para sindico/gerente."""
        return {
            "inadimplencia": {
                "valor": metricas["inadimplencia_percentual"],
                "tendencia": "estavel",  # TODO: calcular tendencia real
                "meta": 10,
                "status": "ok" if metricas["inadimplencia_percentual"] <= 10 else "atencao"
            },
            "ocorrencias": {
                "abertas": metricas["ocorrencias_abertas"],
                "resolvidas_hoje": metricas["resolvido_hoje"],
                "sla_ok": metricas["ocorrencias_abertas"] - metricas["ocorrencias_sla_proximo"] - metricas["ocorrencias_sla_estourado"]
            },
            "seguranca": {
                "alertas_ativos": metricas["alertas_criticos"] + metricas["alertas_medios"],
                "cameras_offline": metricas["cameras_offline"],
                "status": "ok" if metricas["alertas_criticos"] == 0 else "atencao"
            }
        }

    async def _gerar_proxima_tarefa(self, condominio_id: UUID) -> Optional[Dict[str, Any]]:
        """Gera proxima tarefa para perfil porteiro."""
        # Busca visitantes aguardando
        # TODO: implementar busca real

        return {
            "titulo": "Nenhuma tarefa pendente",
            "procedimento": ["Monitore as entradas", "Verifique alertas periodicamente"],
            "urgencia": "baixa"
        }

    async def get_ou_calcular(
        self,
        perfil: str,
        usuario_id: UUID,
        condominio_id: UUID,
        forcar_recalculo: bool = False
    ) -> TranquilidadeSnapshot:
        """
        Retorna snapshot do cache ou calcula novo se expirado.
        """
        if not forcar_recalculo:
            # Busca snapshot valido no cache
            snapshot = self.db.query(TranquilidadeSnapshot).filter(
                and_(
                    TranquilidadeSnapshot.perfil == perfil,
                    TranquilidadeSnapshot.usuario_id == usuario_id,
                    TranquilidadeSnapshot.condominio_id == condominio_id,
                    TranquilidadeSnapshot.expires_at > datetime.utcnow()
                )
            ).order_by(TranquilidadeSnapshot.calculated_at.desc()).first()

            if snapshot:
                return snapshot

        # Calcula novo
        return await self.calcular_tranquilidade(perfil, usuario_id, condominio_id)
