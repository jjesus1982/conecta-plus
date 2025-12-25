"""
Conecta Plus - Q2: Otimizador de Comunicacao
RF-07: Comunicacao Inteligente

Este servico otimiza timing, canal e conteudo das comunicacoes.
"""

import logging
from datetime import datetime, timedelta, time
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.orm import Session

from ...models import (
    PreferenciaComunicacao, HistoricoComunicacao, FilaComunicacao,
    CanalComunicacao, TipoComunicacao, UrgenciaComunicacao,
    Usuario, Morador
)

logger = logging.getLogger(__name__)


class CommunicationOptimizer:
    """
    Otimizador de comunicacao.
    Aprende preferencias e otimiza timing/canal das mensagens.
    """

    # Horarios padrao se nao houver dados suficientes
    HORARIO_PADRAO_INICIO = time(8, 0)
    HORARIO_PADRAO_FIM = time(21, 0)

    # Minimo de historico para confiar nas metricas
    MINIMO_HISTORICO = 10

    def __init__(self, db: Session):
        self.db = db

    # ==========================================
    # OTIMIZACAO DE ENVIO
    # ==========================================

    async def determinar_melhor_momento(
        self,
        usuario_id: UUID,
        urgencia: UrgenciaComunicacao = UrgenciaComunicacao.MEDIA
    ) -> Dict[str, Any]:
        """
        Determina o melhor momento para enviar comunicacao ao usuario.
        Retorna horario sugerido e se pode enviar agora.
        """
        preferencias = await self._obter_ou_criar_preferencias(usuario_id)

        agora = datetime.now()
        hora_atual = agora.time()

        # Para urgencia critica, sempre pode enviar (exceto modo nao perturbe)
        if urgencia == UrgenciaComunicacao.CRITICA:
            pode_agora = True
            if preferencias.nao_perturbe_ativo and not preferencias.nao_perturbe_exceto_emergencias:
                pode_agora = self._fora_horario_nao_perturbe(hora_atual, preferencias)

            return {
                "pode_enviar_agora": pode_agora,
                "urgencia": urgencia.value,
                "motivo": "Urgencia critica - envio imediato"
            }

        # Verificar se esta no horario preferido
        pode_agora = preferencias.pode_notificar_agora(urgencia)

        if pode_agora:
            return {
                "pode_enviar_agora": True,
                "horario_otimo": hora_atual.isoformat(),
                "canal_recomendado": preferencias.canal_primario.value,
                "motivo": "Dentro do horario preferido"
            }

        # Calcular proximo horario disponivel
        proximo_horario = await self._calcular_proximo_horario(preferencias, agora)

        return {
            "pode_enviar_agora": False,
            "agendar_para": proximo_horario.isoformat(),
            "canal_recomendado": preferencias.canal_primario.value,
            "motivo": "Fora do horario preferido - agendado"
        }

    async def determinar_melhor_canal(
        self,
        usuario_id: UUID,
        tipo_mensagem: TipoComunicacao,
        urgencia: UrgenciaComunicacao = UrgenciaComunicacao.MEDIA
    ) -> CanalComunicacao:
        """
        Determina o melhor canal para enviar a mensagem.
        Considera preferencias do usuario e historico de engajamento.
        """
        preferencias = await self._obter_ou_criar_preferencias(usuario_id)

        # Para emergencias, usar canal de emergencia
        if urgencia == UrgenciaComunicacao.CRITICA:
            return preferencias.canal_emergencia or CanalComunicacao.SMS

        # Verificar se usuario tem historico suficiente
        stmt = (
            select(func.count(HistoricoComunicacao.id))
            .where(HistoricoComunicacao.usuario_id == usuario_id)
        )
        result = self.db.execute(stmt)
        total_historico = result.scalar() or 0

        if total_historico < self.MINIMO_HISTORICO:
            # Usar canal primario configurado
            return preferencias.canal_primario

        # Analisar taxas de abertura por canal
        taxas = await self._calcular_taxas_por_canal(usuario_id)

        # Escolher canal com melhor taxa de abertura
        melhor_canal = preferencias.canal_primario
        melhor_taxa = 0.0

        for canal, taxa in taxas.items():
            if taxa > melhor_taxa:
                melhor_taxa = taxa
                melhor_canal = CanalComunicacao(canal)

        return melhor_canal

    async def agendar_comunicacao(
        self,
        usuario_id: UUID,
        condominio_id: UUID,
        tipo: TipoComunicacao,
        titulo: str,
        conteudo: str,
        urgencia: UrgenciaComunicacao = UrgenciaComunicacao.MEDIA,
        origem_id: UUID = None,
        origem_tipo: str = None,
        categoria: str = None
    ) -> FilaComunicacao:
        """
        Agenda uma comunicacao com otimizacao de timing e canal.
        """
        # Determinar melhor momento
        momento = await self.determinar_melhor_momento(usuario_id, urgencia)

        # Determinar melhor canal
        canal = await self.determinar_melhor_canal(usuario_id, tipo, urgencia)

        # Criar item na fila
        fila_item = FilaComunicacao(
            usuario_id=usuario_id,
            condominio_id=condominio_id,
            tipo=tipo,
            titulo=titulo,
            conteudo=conteudo,
            urgencia=urgencia,
            canal=canal,
            agendar_para=datetime.fromisoformat(momento["agendar_para"]) if "agendar_para" in momento else None,
            prioridade=self._calcular_prioridade(urgencia),
            pode_agrupar=urgencia in [UrgenciaComunicacao.BAIXA, UrgenciaComunicacao.MEDIA],
            origem_id=origem_id,
            origem_tipo=origem_tipo,
            categoria=categoria
        )

        self.db.add(fila_item)
        self.db.commit()
        self.db.refresh(fila_item)

        logger.info(f"Comunicacao agendada para {usuario_id} via {canal.value}")

        return fila_item

    async def processar_fila(self, limit: int = 50) -> Dict[str, Any]:
        """
        Processa itens pendentes na fila de comunicacao.
        Retorna estatisticas do processamento.
        """
        agora = datetime.utcnow()

        # Buscar itens prontos para envio
        stmt = (
            select(FilaComunicacao)
            .where(
                and_(
                    FilaComunicacao.processado == False,
                    or_(
                        FilaComunicacao.agendar_para.is_(None),
                        FilaComunicacao.agendar_para <= agora
                    )
                )
            )
            .order_by(FilaComunicacao.prioridade.desc(), FilaComunicacao.created_at)
            .limit(limit)
        )

        result = self.db.execute(stmt)
        itens = result.scalars().all()

        stats = {
            "processados": 0,
            "enviados": 0,
            "agrupados": 0,
            "erros": 0
        }

        # Agrupar por usuario se possivel
        por_usuario: Dict[UUID, List[FilaComunicacao]] = {}
        for item in itens:
            if item.usuario_id not in por_usuario:
                por_usuario[item.usuario_id] = []
            por_usuario[item.usuario_id].append(item)

        for usuario_id, itens_usuario in por_usuario.items():
            try:
                # Verificar se pode agrupar
                agrupaveis = [i for i in itens_usuario if i.pode_agrupar]

                if len(agrupaveis) > 1:
                    # Agrupar mensagens
                    historico = await self._enviar_agrupado(usuario_id, agrupaveis)
                    stats["agrupados"] += len(agrupaveis)
                    stats["enviados"] += 1
                else:
                    # Enviar individualmente
                    for item in itens_usuario:
                        historico = await self._enviar_individual(item)
                        stats["enviados"] += 1

                stats["processados"] += len(itens_usuario)

            except Exception as e:
                logger.error(f"Erro ao processar fila para {usuario_id}: {e}")
                stats["erros"] += len(itens_usuario)

        return stats

    # ==========================================
    # ENVIO DE COMUNICACOES
    # ==========================================

    async def _enviar_individual(self, item: FilaComunicacao) -> HistoricoComunicacao:
        """Envia uma comunicacao individual"""

        # Criar registro no historico
        historico = HistoricoComunicacao(
            usuario_id=item.usuario_id,
            condominio_id=item.condominio_id,
            tipo=item.tipo,
            titulo=item.titulo,
            conteudo_resumo=item.conteudo[:500] if item.conteudo else None,
            conteudo_completo=item.conteudo,
            urgencia=item.urgencia,
            canal=item.canal,
            horario_otimizado=item.agendar_para is not None,
            canal_otimizado=True,
            origem_id=item.origem_id,
            origem_tipo=item.origem_tipo,
            categoria=item.categoria
        )

        self.db.add(historico)

        # Marcar item como processado
        item.processado = True
        item.processado_em = datetime.utcnow()
        item.historico_id = historico.id

        # Aqui seria a integracao com servicos de envio reais
        # (Firebase, SendGrid, Twilio, etc.)
        await self._simular_envio(historico)

        self.db.commit()

        return historico

    async def _enviar_agrupado(
        self,
        usuario_id: UUID,
        itens: List[FilaComunicacao]
    ) -> HistoricoComunicacao:
        """Envia comunicacoes agrupadas (boletim)"""

        # Construir conteudo agrupado
        titulos = [item.titulo for item in itens]
        conteudo_resumo = f"Boletim com {len(itens)} atualizacoes"
        conteudo_completo = "\n\n---\n\n".join([
            f"**{item.titulo}**\n{item.conteudo}"
            for item in itens
        ])

        # Usar canal do primeiro item (todos devem ser do mesmo usuario)
        canal = itens[0].canal
        condominio_id = itens[0].condominio_id

        historico = HistoricoComunicacao(
            usuario_id=usuario_id,
            condominio_id=condominio_id,
            tipo=TipoComunicacao.BOLETIM,
            titulo=f"Boletim: {len(itens)} atualizacoes",
            conteudo_resumo=conteudo_resumo,
            conteudo_completo=conteudo_completo,
            urgencia=UrgenciaComunicacao.BAIXA,
            canal=canal,
            horario_otimizado=True,
            canal_otimizado=True
        )

        self.db.add(historico)

        # Marcar itens como processados
        for item in itens:
            item.processado = True
            item.processado_em = datetime.utcnow()
            item.historico_id = historico.id
            item.grupo_id = historico.id

        await self._simular_envio(historico)

        self.db.commit()

        return historico

    async def _simular_envio(self, historico: HistoricoComunicacao) -> None:
        """
        Simula envio da mensagem.
        Em producao, aqui seria a integracao real.
        """
        # Simular entrega bem-sucedida
        historico.entregue = True
        historico.entregue_em = datetime.utcnow()

        logger.info(f"[SIMULADO] Enviado {historico.tipo.value} via {historico.canal.value}")

    # ==========================================
    # TRACKING DE ENGAJAMENTO
    # ==========================================

    async def registrar_abertura(self, historico_id: UUID) -> None:
        """Registra que o usuario abriu a mensagem"""

        stmt = select(HistoricoComunicacao).where(HistoricoComunicacao.id == historico_id)
        result = self.db.execute(stmt)
        historico = result.scalar()

        if historico and not historico.aberto:
            historico.registrar_abertura()

            # Atualizar metricas do usuario
            await self._atualizar_metricas_usuario(
                historico.usuario_id,
                historico.canal,
                "abertura",
                historico.tempo_ate_abertura_segundos
            )

            self.db.commit()

    async def registrar_clique(self, historico_id: UUID) -> None:
        """Registra que o usuario clicou na mensagem"""

        stmt = select(HistoricoComunicacao).where(HistoricoComunicacao.id == historico_id)
        result = self.db.execute(stmt)
        historico = result.scalar()

        if historico and not historico.clicou:
            historico.registrar_clique()

            await self._atualizar_metricas_usuario(
                historico.usuario_id,
                historico.canal,
                "clique",
                historico.tempo_ate_clique_segundos
            )

            self.db.commit()

    async def registrar_resposta(self, historico_id: UUID) -> None:
        """Registra que o usuario respondeu a mensagem"""

        stmt = select(HistoricoComunicacao).where(HistoricoComunicacao.id == historico_id)
        result = self.db.execute(stmt)
        historico = result.scalar()

        if historico and not historico.respondeu:
            historico.registrar_resposta()
            self.db.commit()

    async def registrar_feedback(
        self,
        historico_id: UUID,
        util: bool,
        marcou_spam: bool = False
    ) -> None:
        """Registra feedback do usuario sobre a mensagem"""

        stmt = select(HistoricoComunicacao).where(HistoricoComunicacao.id == historico_id)
        result = self.db.execute(stmt)
        historico = result.scalar()

        if historico:
            historico.foi_util = util
            historico.marcou_spam = marcou_spam

            if marcou_spam:
                # Reduzir frequencia para este usuario/tipo
                await self._ajustar_preferencias_spam(historico)

            self.db.commit()

    # ==========================================
    # APRENDIZADO E METRICAS
    # ==========================================

    async def _atualizar_metricas_usuario(
        self,
        usuario_id: UUID,
        canal: CanalComunicacao,
        tipo_evento: str,
        tempo_segundos: int = None
    ) -> None:
        """Atualiza metricas de engajamento do usuario"""

        preferencias = await self._obter_ou_criar_preferencias(usuario_id)

        # Incrementar contadores
        preferencias.total_enviadas = (preferencias.total_enviadas or 0) + 1

        if tipo_evento == "abertura":
            preferencias.total_abertas = (preferencias.total_abertas or 0) + 1

            # Calcular nova taxa de abertura por canal
            taxa = (preferencias.total_abertas / preferencias.total_enviadas) if preferencias.total_enviadas > 0 else 0

            if canal == CanalComunicacao.PUSH:
                preferencias.taxa_abertura_push = taxa
            elif canal == CanalComunicacao.EMAIL:
                preferencias.taxa_abertura_email = taxa
            elif canal == CanalComunicacao.WHATSAPP:
                preferencias.taxa_abertura_whatsapp = taxa

            # Atualizar tempo medio de resposta
            if tempo_segundos:
                tempo_atual = preferencias.tempo_medio_resposta_segundos or 0
                # Media movel simples
                preferencias.tempo_medio_resposta_segundos = int((tempo_atual + tempo_segundos) / 2)

            # Aprender melhor horario
            agora = datetime.now()
            if not preferencias.horario_mais_engajado or tempo_segundos and tempo_segundos < 300:
                # Se respondeu em menos de 5 minutos, este e um bom horario
                preferencias.horario_mais_engajado = agora.time()
                preferencias.dia_mais_engajado = agora.weekday() + 1

        elif tipo_evento == "clique":
            preferencias.total_clicadas = (preferencias.total_clicadas or 0) + 1

        self.db.commit()

    async def _calcular_taxas_por_canal(self, usuario_id: UUID) -> Dict[str, float]:
        """Calcula taxas de abertura por canal para um usuario"""

        stmt = (
            select(
                HistoricoComunicacao.canal,
                func.count(HistoricoComunicacao.id).label('total'),
                func.sum(func.cast(HistoricoComunicacao.aberto, Integer)).label('abertos')
            )
            .where(HistoricoComunicacao.usuario_id == usuario_id)
            .group_by(HistoricoComunicacao.canal)
        )

        from sqlalchemy import Integer

        result = self.db.execute(stmt)
        taxas = {}

        for row in result.all():
            total = row.total or 0
            abertos = row.abertos or 0
            if total > 0:
                taxas[row.canal.value] = abertos / total

        return taxas

    async def _ajustar_preferencias_spam(self, historico: HistoricoComunicacao) -> None:
        """Ajusta preferencias quando usuario marca como spam"""

        preferencias = await self._obter_ou_criar_preferencias(historico.usuario_id)

        # Se marcou spam, desativar categoria correspondente
        if historico.categoria == "financeiro":
            preferencias.receber_financeiro = False
        elif historico.categoria == "manutencao":
            preferencias.receber_manutencao = False
        elif historico.categoria == "comunicados":
            preferencias.receber_comunicados = False

        # Reduzir max de notificacoes
        if preferencias.max_notificacoes_dia > 1:
            preferencias.max_notificacoes_dia -= 1

        logger.warning(f"Usuario {historico.usuario_id} marcou {historico.tipo.value} como spam")

    # ==========================================
    # PREFERENCIAS
    # ==========================================

    async def _obter_ou_criar_preferencias(self, usuario_id: UUID) -> PreferenciaComunicacao:
        """Obtem ou cria preferencias de comunicacao para usuario"""

        stmt = select(PreferenciaComunicacao).where(
            PreferenciaComunicacao.usuario_id == usuario_id
        )
        result = self.db.execute(stmt)
        preferencias = result.scalar()

        if not preferencias:
            # Criar preferencias padrao
            preferencias = PreferenciaComunicacao(
                usuario_id=usuario_id,
                horario_preferido_inicio=self.HORARIO_PADRAO_INICIO,
                horario_preferido_fim=self.HORARIO_PADRAO_FIM,
                canal_primario=CanalComunicacao.PUSH,
                canal_secundario=CanalComunicacao.EMAIL,
                canal_emergencia=CanalComunicacao.SMS
            )
            self.db.add(preferencias)
            self.db.commit()
            self.db.refresh(preferencias)

        return preferencias

    async def obter_preferencias(self, usuario_id: UUID) -> Dict[str, Any]:
        """Retorna preferencias de comunicacao do usuario"""
        preferencias = await self._obter_ou_criar_preferencias(usuario_id)
        return preferencias.to_dict()

    async def atualizar_preferencias(
        self,
        usuario_id: UUID,
        dados: Dict[str, Any]
    ) -> PreferenciaComunicacao:
        """Atualiza preferencias de comunicacao do usuario"""

        preferencias = await self._obter_ou_criar_preferencias(usuario_id)

        # Atualizar campos permitidos
        campos_permitidos = [
            'horario_preferido_inicio', 'horario_preferido_fim',
            'dias_preferidos', 'canal_primario', 'canal_secundario',
            'max_notificacoes_dia', 'agrupar_similares',
            'receber_financeiro', 'receber_manutencao', 'receber_seguranca',
            'receber_comunicados', 'receber_assembleias', 'receber_reservas',
            'receber_sugestoes', 'receber_marketing',
            'nao_perturbe_ativo', 'nao_perturbe_inicio', 'nao_perturbe_fim'
        ]

        for campo in campos_permitidos:
            if campo in dados:
                valor = dados[campo]

                # Converter strings de enum
                if campo in ['canal_primario', 'canal_secundario', 'canal_emergencia']:
                    valor = CanalComunicacao(valor) if valor else None
                elif campo in ['horario_preferido_inicio', 'horario_preferido_fim',
                              'nao_perturbe_inicio', 'nao_perturbe_fim']:
                    if isinstance(valor, str):
                        valor = time.fromisoformat(valor)

                setattr(preferencias, campo, valor)

        preferencias.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(preferencias)

        return preferencias

    # ==========================================
    # UTILITARIOS
    # ==========================================

    def _fora_horario_nao_perturbe(
        self,
        hora: time,
        preferencias: PreferenciaComunicacao
    ) -> bool:
        """Verifica se esta fora do horario de nao perturbe"""
        inicio = preferencias.nao_perturbe_inicio
        fim = preferencias.nao_perturbe_fim

        if inicio and fim:
            if inicio > fim:
                # Horario atravessa meia-noite (ex: 22h - 7h)
                return fim <= hora < inicio
            else:
                # Horario normal
                return hora < inicio or hora >= fim

        return True

    async def _calcular_proximo_horario(
        self,
        preferencias: PreferenciaComunicacao,
        agora: datetime
    ) -> datetime:
        """Calcula proximo horario disponivel para envio"""

        hora_inicio = preferencias.horario_preferido_inicio or self.HORARIO_PADRAO_INICIO

        # Se ja passou do horario hoje, agendar para amanha
        if agora.time() >= hora_inicio:
            proximo = agora + timedelta(days=1)
        else:
            proximo = agora

        return proximo.replace(
            hour=hora_inicio.hour,
            minute=hora_inicio.minute,
            second=0,
            microsecond=0
        )

    def _calcular_prioridade(self, urgencia: UrgenciaComunicacao) -> int:
        """Calcula prioridade baseada na urgencia"""
        mapa = {
            UrgenciaComunicacao.CRITICA: 100,
            UrgenciaComunicacao.ALTA: 80,
            UrgenciaComunicacao.MEDIA: 50,
            UrgenciaComunicacao.BAIXA: 20
        }
        return mapa.get(urgencia, 50)

    async def obter_historico(
        self,
        usuario_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[HistoricoComunicacao]:
        """Retorna historico de comunicacoes do usuario"""

        stmt = (
            select(HistoricoComunicacao)
            .where(HistoricoComunicacao.usuario_id == usuario_id)
            .order_by(HistoricoComunicacao.enviado_em.desc())
            .limit(limit)
            .offset(offset)
        )

        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def obter_metricas(self, condominio_id: UUID) -> Dict[str, Any]:
        """Retorna metricas de comunicacao do condominio"""

        # Total enviadas
        stmt_total = (
            select(func.count(HistoricoComunicacao.id))
            .where(HistoricoComunicacao.condominio_id == condominio_id)
        )

        # Taxa de abertura
        stmt_abertas = (
            select(func.count(HistoricoComunicacao.id))
            .where(
                and_(
                    HistoricoComunicacao.condominio_id == condominio_id,
                    HistoricoComunicacao.aberto == True
                )
            )
        )

        # Taxa de clique
        stmt_cliques = (
            select(func.count(HistoricoComunicacao.id))
            .where(
                and_(
                    HistoricoComunicacao.condominio_id == condominio_id,
                    HistoricoComunicacao.clicou == True
                )
            )
        )

        # Por canal
        stmt_por_canal = (
            select(
                HistoricoComunicacao.canal,
                func.count(HistoricoComunicacao.id)
            )
            .where(HistoricoComunicacao.condominio_id == condominio_id)
            .group_by(HistoricoComunicacao.canal)
        )

        try:
            result_total = self.db.execute(stmt_total)
            result_abertas = self.db.execute(stmt_abertas)
            result_cliques = self.db.execute(stmt_cliques)
            result_canal = self.db.execute(stmt_por_canal)

            total = result_total.scalar() or 0
            abertas = result_abertas.scalar() or 0
            cliques = result_cliques.scalar() or 0

            por_canal = {r[0].value: r[1] for r in result_canal.all()}

            return {
                "total_enviadas": total,
                "total_abertas": abertas,
                "total_cliques": cliques,
                "taxa_abertura": abertas / total if total > 0 else 0,
                "taxa_clique": cliques / total if total > 0 else 0,
                "por_canal": por_canal
            }

        except Exception as e:
            logger.error(f"Erro ao obter metricas: {e}")
            return {}
