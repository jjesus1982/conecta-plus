"""
Conecta Plus - Q2: Motor de Aprendizado Continuo
RF-08: Aprendizado Continuo

Este servico gerencia feedback loops e metricas dos modelos.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session

from ...models import (
    FeedbackModelo, MetricaModelo, HistoricoTreinamento,
    TipoOrigem, TipoFeedback, ValorFeedback,
    Previsao, StatusPrevisao,
    Sugestao, StatusSugestao,
    HistoricoComunicacao
)

logger = logging.getLogger(__name__)


class LearningEngine:
    """
    Motor de aprendizado continuo.
    Coleta feedback, calcula metricas e monitora performance dos modelos.
    """

    # Versao atual dos modelos
    VERSAO_MODELO_PREVISAO = "1.0.0"
    VERSAO_MODELO_SUGESTAO = "1.0.0"
    VERSAO_MODELO_COMUNICACAO = "1.0.0"

    def __init__(self, db: Session):
        self.db = db

    # ==========================================
    # COLETA DE FEEDBACK
    # ==========================================

    async def registrar_feedback(
        self,
        condominio_id: UUID,
        tipo_origem: TipoOrigem,
        origem_id: UUID,
        valor: ValorFeedback,
        usuario_id: UUID = None,
        perfil_usuario: str = None,
        comentario: str = None,
        avaliacao: int = None,
        contexto: Dict = None
    ) -> FeedbackModelo:
        """
        Registra feedback explicito do usuario.
        """
        feedback = FeedbackModelo(
            condominio_id=condominio_id,
            tipo_origem=tipo_origem,
            origem_id=origem_id,
            tipo_feedback=TipoFeedback.EXPLICITO,
            valor=valor,
            usuario_id=usuario_id,
            perfil_usuario=perfil_usuario,
            comentario=comentario,
            avaliacao=avaliacao,
            contexto=contexto or {}
        )

        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)

        logger.info(f"Feedback registrado: {tipo_origem.value}/{valor.value}")

        return feedback

    async def registrar_feedback_implicito(
        self,
        condominio_id: UUID,
        tipo_origem: TipoOrigem,
        origem_id: UUID,
        valor: ValorFeedback,
        contexto: Dict = None
    ) -> FeedbackModelo:
        """
        Registra feedback implicito (inferido do comportamento).
        """
        feedback = FeedbackModelo(
            condominio_id=condominio_id,
            tipo_origem=tipo_origem,
            origem_id=origem_id,
            tipo_feedback=TipoFeedback.IMPLICITO,
            valor=valor,
            contexto=contexto or {},
            peso=0.5  # Feedback implicito tem peso menor
        )

        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)

        return feedback

    async def coletar_feedback_automatico(self, condominio_id: UUID) -> Dict[str, int]:
        """
        Coleta feedback automatico de eventos do sistema.
        Analisa acoes do usuario e infere feedback.
        """
        stats = {
            "previsoes_analisadas": 0,
            "sugestoes_analisadas": 0,
            "comunicacoes_analisadas": 0,
            "feedbacks_criados": 0
        }

        # 1. Analisar previsoes confirmadas/falsas
        await self._coletar_feedback_previsoes(condominio_id, stats)

        # 2. Analisar sugestoes aceitas/rejeitadas
        await self._coletar_feedback_sugestoes(condominio_id, stats)

        # 3. Analisar engajamento de comunicacoes
        await self._coletar_feedback_comunicacoes(condominio_id, stats)

        logger.info(f"Feedback automatico coletado: {stats}")

        return stats

    async def _coletar_feedback_previsoes(
        self,
        condominio_id: UUID,
        stats: Dict
    ) -> None:
        """Coleta feedback de previsoes validadas"""

        # Buscar previsoes validadas sem feedback
        stmt = (
            select(Previsao)
            .where(
                and_(
                    Previsao.condominio_id == condominio_id,
                    Previsao.status.in_([
                        StatusPrevisao.CONFIRMADA,
                        StatusPrevisao.FALSO_POSITIVO,
                        StatusPrevisao.EVITADA
                    ]),
                    ~Previsao.id.in_(
                        select(FeedbackModelo.origem_id)
                        .where(FeedbackModelo.tipo_origem == TipoOrigem.PREVISAO)
                    )
                )
            )
        )

        result = self.db.execute(stmt)
        previsoes = result.scalars().all()

        for previsao in previsoes:
            stats["previsoes_analisadas"] += 1

            # Mapear status para valor de feedback
            if previsao.status == StatusPrevisao.CONFIRMADA:
                valor = ValorFeedback.CONFIRMADO
            elif previsao.status == StatusPrevisao.EVITADA:
                valor = ValorFeedback.UTIL
            else:
                valor = ValorFeedback.FALSO_POSITIVO

            await self.registrar_feedback_implicito(
                condominio_id=condominio_id,
                tipo_origem=TipoOrigem.PREVISAO,
                origem_id=previsao.id,
                valor=valor,
                contexto={
                    "tipo": previsao.tipo.value,
                    "subtipo": previsao.subtipo.value,
                    "probabilidade": previsao.probabilidade,
                    "modelo_versao": previsao.modelo_versao
                }
            )
            stats["feedbacks_criados"] += 1

    async def _coletar_feedback_sugestoes(
        self,
        condominio_id: UUID,
        stats: Dict
    ) -> None:
        """Coleta feedback de sugestoes respondidas"""

        stmt = (
            select(Sugestao)
            .where(
                and_(
                    Sugestao.condominio_id == condominio_id,
                    Sugestao.status.in_([
                        StatusSugestao.ACEITA,
                        StatusSugestao.REJEITADA,
                        StatusSugestao.CONCLUIDA
                    ]),
                    ~Sugestao.id.in_(
                        select(FeedbackModelo.origem_id)
                        .where(FeedbackModelo.tipo_origem == TipoOrigem.SUGESTAO)
                    )
                )
            )
        )

        result = self.db.execute(stmt)
        sugestoes = result.scalars().all()

        for sugestao in sugestoes:
            stats["sugestoes_analisadas"] += 1

            if sugestao.status == StatusSugestao.ACEITA:
                valor = ValorFeedback.ACEITO
            elif sugestao.status == StatusSugestao.REJEITADA:
                valor = ValorFeedback.REJEITADO
            elif sugestao.status == StatusSugestao.CONCLUIDA:
                valor = ValorFeedback.UTIL if sugestao.foi_util else ValorFeedback.NAO_UTIL
            else:
                continue

            await self.registrar_feedback_implicito(
                condominio_id=condominio_id,
                tipo_origem=TipoOrigem.SUGESTAO,
                origem_id=sugestao.id,
                valor=valor,
                contexto={
                    "tipo": sugestao.tipo.value,
                    "codigo": sugestao.codigo.value,
                    "prioridade": sugestao.prioridade,
                    "modelo_versao": sugestao.modelo_versao
                }
            )
            stats["feedbacks_criados"] += 1

    async def _coletar_feedback_comunicacoes(
        self,
        condominio_id: UUID,
        stats: Dict
    ) -> None:
        """Coleta feedback de comunicacoes"""

        # Comunicacoes com mais de 24h
        data_limite = datetime.utcnow() - timedelta(hours=24)

        stmt = (
            select(HistoricoComunicacao)
            .where(
                and_(
                    HistoricoComunicacao.condominio_id == condominio_id,
                    HistoricoComunicacao.enviado_em < data_limite,
                    ~HistoricoComunicacao.id.in_(
                        select(FeedbackModelo.origem_id)
                        .where(FeedbackModelo.tipo_origem == TipoOrigem.COMUNICACAO)
                    )
                )
            )
        )

        result = self.db.execute(stmt)
        comunicacoes = result.scalars().all()

        for com in comunicacoes:
            stats["comunicacoes_analisadas"] += 1

            # Determinar valor baseado no engajamento
            if com.marcou_spam:
                valor = ValorFeedback.SPAM
            elif com.respondeu or com.clicou:
                valor = ValorFeedback.UTIL
            elif com.aberto:
                valor = ValorFeedback.ACEITO  # Abriu mas nao interagiu
            else:
                valor = ValorFeedback.IGNORADO

            await self.registrar_feedback_implicito(
                condominio_id=condominio_id,
                tipo_origem=TipoOrigem.COMUNICACAO,
                origem_id=com.id,
                valor=valor,
                contexto={
                    "tipo": com.tipo.value,
                    "canal": com.canal.value,
                    "horario_otimizado": com.horario_otimizado,
                    "tempo_abertura": com.tempo_ate_abertura_segundos
                }
            )
            stats["feedbacks_criados"] += 1

    # ==========================================
    # CALCULO DE METRICAS
    # ==========================================

    async def calcular_metricas_periodo(
        self,
        modelo: str,
        periodo_inicio: datetime,
        periodo_fim: datetime,
        condominio_id: UUID = None
    ) -> MetricaModelo:
        """
        Calcula metricas de um modelo para um periodo.
        """
        logger.info(f"Calculando metricas para {modelo} de {periodo_inicio} a {periodo_fim}")

        # Buscar feedback do periodo
        stmt = (
            select(FeedbackModelo)
            .where(
                and_(
                    FeedbackModelo.created_at >= periodo_inicio,
                    FeedbackModelo.created_at <= periodo_fim
                )
            )
        )

        if condominio_id:
            stmt = stmt.where(FeedbackModelo.condominio_id == condominio_id)

        # Filtrar por tipo de origem baseado no modelo
        if modelo.startswith("previsao"):
            stmt = stmt.where(FeedbackModelo.tipo_origem == TipoOrigem.PREVISAO)
        elif modelo.startswith("sugestao"):
            stmt = stmt.where(FeedbackModelo.tipo_origem == TipoOrigem.SUGESTAO)
        elif modelo.startswith("comunicacao"):
            stmt = stmt.where(FeedbackModelo.tipo_origem == TipoOrigem.COMUNICACAO)

        result = self.db.execute(stmt)
        feedbacks = result.scalars().all()

        # Calcular metricas
        total = len(feedbacks)
        vp = sum(1 for f in feedbacks if f.valor in [ValorFeedback.CONFIRMADO, ValorFeedback.UTIL, ValorFeedback.ACEITO])
        fp = sum(1 for f in feedbacks if f.valor == ValorFeedback.FALSO_POSITIVO)
        fn = sum(1 for f in feedbacks if f.valor == ValorFeedback.REJEITADO)
        vn = sum(1 for f in feedbacks if f.valor in [ValorFeedback.IGNORADO, ValorFeedback.NAO_UTIL])

        # Criar registro de metricas
        metricas = MetricaModelo(
            modelo=modelo,
            versao=self._obter_versao_modelo(modelo),
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            condominio_id=condominio_id,
            total_predicoes=total,
            verdadeiros_positivos=vp,
            falsos_positivos=fp,
            verdadeiros_negativos=vn,
            falsos_negativos=fn
        )

        # Calcular precision, recall, f1
        metricas.calcular_metricas()

        # Calcular metricas de negocio
        if total > 0:
            metricas.taxa_aceitacao = vp / total
            metricas.taxa_utilidade = sum(1 for f in feedbacks if f.valor == ValorFeedback.UTIL) / total

        self.db.add(metricas)
        self.db.commit()
        self.db.refresh(metricas)

        logger.info(f"Metricas calculadas: precision={metricas.precision_val}, recall={metricas.recall_val}")

        return metricas

    async def obter_metricas_modelo(
        self,
        modelo: str,
        limite: int = 10
    ) -> List[MetricaModelo]:
        """Retorna historico de metricas de um modelo"""

        stmt = (
            select(MetricaModelo)
            .where(MetricaModelo.modelo == modelo)
            .order_by(MetricaModelo.created_at.desc())
            .limit(limite)
        )

        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def comparar_versoes(
        self,
        modelo: str,
        versao_a: str,
        versao_b: str
    ) -> Dict[str, Any]:
        """Compara metricas entre duas versoes de um modelo"""

        stmt_a = (
            select(MetricaModelo)
            .where(
                and_(
                    MetricaModelo.modelo == modelo,
                    MetricaModelo.versao == versao_a
                )
            )
            .order_by(MetricaModelo.created_at.desc())
            .limit(1)
        )

        stmt_b = (
            select(MetricaModelo)
            .where(
                and_(
                    MetricaModelo.modelo == modelo,
                    MetricaModelo.versao == versao_b
                )
            )
            .order_by(MetricaModelo.created_at.desc())
            .limit(1)
        )

        result_a = self.db.execute(stmt_a)
        result_b = self.db.execute(stmt_b)

        metrica_a = result_a.scalar()
        metrica_b = result_b.scalar()

        if not metrica_a or not metrica_b:
            return {"erro": "Versoes nao encontradas"}

        return {
            "modelo": modelo,
            "versao_a": {
                "versao": versao_a,
                "precision": metrica_a.precision_val,
                "recall": metrica_a.recall_val,
                "f1_score": metrica_a.f1_score,
                "taxa_aceitacao": metrica_a.taxa_aceitacao
            },
            "versao_b": {
                "versao": versao_b,
                "precision": metrica_b.precision_val,
                "recall": metrica_b.recall_val,
                "f1_score": metrica_b.f1_score,
                "taxa_aceitacao": metrica_b.taxa_aceitacao
            },
            "delta": {
                "precision": (metrica_b.precision_val or 0) - (metrica_a.precision_val or 0),
                "recall": (metrica_b.recall_val or 0) - (metrica_a.recall_val or 0),
                "f1_score": (metrica_b.f1_score or 0) - (metrica_a.f1_score or 0),
            },
            "melhor_versao": versao_b if (metrica_b.f1_score or 0) > (metrica_a.f1_score or 0) else versao_a
        }

    # ==========================================
    # DASHBOARD E RELATORIOS
    # ==========================================

    async def obter_dashboard(self, condominio_id: UUID = None) -> Dict[str, Any]:
        """Retorna dashboard de aprendizado"""

        # Feedbacks recentes
        stmt_feedback = (
            select(
                FeedbackModelo.tipo_origem,
                FeedbackModelo.valor,
                func.count(FeedbackModelo.id)
            )
            .where(FeedbackModelo.created_at >= datetime.utcnow() - timedelta(days=30))
            .group_by(FeedbackModelo.tipo_origem, FeedbackModelo.valor)
        )

        if condominio_id:
            stmt_feedback = stmt_feedback.where(FeedbackModelo.condominio_id == condominio_id)

        result_feedback = self.db.execute(stmt_feedback)
        feedback_por_tipo = {}
        for row in result_feedback.all():
            tipo = row[0].value
            valor = row[1].value
            count = row[2]
            if tipo not in feedback_por_tipo:
                feedback_por_tipo[tipo] = {}
            feedback_por_tipo[tipo][valor] = count

        # Metricas mais recentes por modelo
        modelos = ["previsao", "sugestao", "comunicacao"]
        metricas_atuais = {}

        for modelo in modelos:
            stmt_metrica = (
                select(MetricaModelo)
                .where(MetricaModelo.modelo.like(f"{modelo}%"))
                .order_by(MetricaModelo.created_at.desc())
                .limit(1)
            )
            result_metrica = self.db.execute(stmt_metrica)
            metrica = result_metrica.scalar()

            if metrica:
                metricas_atuais[modelo] = {
                    "versao": metrica.versao,
                    "precision": metrica.precision_val,
                    "recall": metrica.recall_val,
                    "f1_score": metrica.f1_score,
                    "taxa_aceitacao": metrica.taxa_aceitacao,
                    "calculado_em": metrica.created_at.isoformat() if metrica.created_at else None
                }

        # Total de feedback
        stmt_total = select(func.count(FeedbackModelo.id))
        if condominio_id:
            stmt_total = stmt_total.where(FeedbackModelo.condominio_id == condominio_id)

        result_total = self.db.execute(stmt_total)
        total_feedback = result_total.scalar() or 0

        return {
            "total_feedback": total_feedback,
            "feedback_ultimos_30_dias": feedback_por_tipo,
            "metricas_atuais": metricas_atuais,
            "recomendacoes": await self._gerar_recomendacoes(metricas_atuais)
        }

    async def _gerar_recomendacoes(self, metricas: Dict) -> List[str]:
        """Gera recomendacoes baseadas nas metricas"""
        recomendacoes = []

        for modelo, dados in metricas.items():
            if not dados:
                continue

            f1 = dados.get("f1_score")
            precision = dados.get("precision")
            taxa = dados.get("taxa_aceitacao")

            if f1 and f1 < 0.5:
                recomendacoes.append(
                    f"Modelo de {modelo} com F1 baixo ({f1:.2f}). Considere retreinamento."
                )

            if precision and precision < 0.6:
                recomendacoes.append(
                    f"Modelo de {modelo} com muitos falsos positivos. Ajustar thresholds."
                )

            if taxa and taxa < 0.3:
                recomendacoes.append(
                    f"Taxa de aceitacao de {modelo} baixa ({taxa:.0%}). Revisar relevancia."
                )

        if not recomendacoes:
            recomendacoes.append("Modelos operando dentro dos parametros esperados.")

        return recomendacoes

    # ==========================================
    # TREINAMENTO (SIMULADO)
    # ==========================================

    async def iniciar_treinamento(
        self,
        modelo: str,
        parametros: Dict = None
    ) -> HistoricoTreinamento:
        """
        Inicia processo de treinamento de modelo.
        Em producao, isso seria uma chamada a um servico de ML.
        """
        logger.info(f"Iniciando treinamento de {modelo}")

        versao_atual = self._obter_versao_modelo(modelo)
        versao_nova = self._incrementar_versao(versao_atual)

        # Contar amostras de treinamento
        stmt = (
            select(func.count(FeedbackModelo.id))
            .where(
                and_(
                    FeedbackModelo.usado_treinamento == False,
                    FeedbackModelo.tipo_origem == self._tipo_origem_para_modelo(modelo)
                )
            )
        )

        result = self.db.execute(stmt)
        total_amostras = result.scalar() or 0

        if total_amostras < 50:
            raise ValueError(f"Amostras insuficientes para treinamento: {total_amostras}")

        # Criar registro de treinamento
        treinamento = HistoricoTreinamento(
            modelo=modelo,
            versao_anterior=versao_atual,
            versao_nova=versao_nova,
            total_amostras=total_amostras,
            parametros=parametros or {},
            metricas_validacao={},  # Seria preenchido apos treinamento real
            duracao_segundos=0,
            executado_por="sistema"
        )

        self.db.add(treinamento)

        # Marcar amostras como usadas
        stmt_update = (
            update(FeedbackModelo)
            .where(
                and_(
                    FeedbackModelo.usado_treinamento == False,
                    FeedbackModelo.tipo_origem == self._tipo_origem_para_modelo(modelo)
                )
            )
            .values(
                usado_treinamento=True,
                data_treinamento=datetime.utcnow(),
                versao_modelo=versao_nova
            )
        )

        self.db.execute(stmt_update)
        self.db.commit()
        self.db.refresh(treinamento)

        logger.info(f"Treinamento registrado: {modelo} v{versao_nova}")

        return treinamento

    async def deploy_modelo(self, treinamento_id: UUID) -> HistoricoTreinamento:
        """Marca um treinamento como deployed"""

        stmt = select(HistoricoTreinamento).where(HistoricoTreinamento.id == treinamento_id)
        result = self.db.execute(stmt)
        treinamento = result.scalar()

        if not treinamento:
            raise ValueError(f"Treinamento {treinamento_id} nao encontrado")

        treinamento.deployed = True
        treinamento.deployed_em = datetime.utcnow()

        self.db.commit()
        self.db.refresh(treinamento)

        logger.info(f"Modelo {treinamento.modelo} v{treinamento.versao_nova} deployed")

        return treinamento

    # ==========================================
    # UTILITARIOS
    # ==========================================

    def _obter_versao_modelo(self, modelo: str) -> str:
        """Retorna versao atual do modelo"""
        if modelo.startswith("previsao"):
            return self.VERSAO_MODELO_PREVISAO
        elif modelo.startswith("sugestao"):
            return self.VERSAO_MODELO_SUGESTAO
        elif modelo.startswith("comunicacao"):
            return self.VERSAO_MODELO_COMUNICACAO
        return "1.0.0"

    def _incrementar_versao(self, versao: str) -> str:
        """Incrementa versao (patch)"""
        partes = versao.split(".")
        partes[-1] = str(int(partes[-1]) + 1)
        return ".".join(partes)

    def _tipo_origem_para_modelo(self, modelo: str) -> TipoOrigem:
        """Mapeia nome do modelo para tipo de origem"""
        if modelo.startswith("previsao"):
            return TipoOrigem.PREVISAO
        elif modelo.startswith("sugestao"):
            return TipoOrigem.SUGESTAO
        elif modelo.startswith("comunicacao"):
            return TipoOrigem.COMUNICACAO
        return TipoOrigem.GERAL
