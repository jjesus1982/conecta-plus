"""
Conecta Plus - Q2: Motor de Sugestoes Automaticas
RF-06: Sugestoes Automaticas

Este servico recomenda acoes baseadas em padroes e contexto.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session

from ...models import (
    Sugestao, TipoSugestao, CodigoSugestao, StatusSugestao, PerfilDestino,
    Previsao, StatusPrevisao, TipoPrevisao,
    Ocorrencia, StatusOcorrencia,
    OrdemServico, StatusOS,
    Reserva, AreaComum,
    Lancamento, Boleto, StatusBoleto,
    Comunicado,
    Unidade, Morador, Usuario
)

logger = logging.getLogger(__name__)


class SuggestionEngine:
    """
    Motor de sugestoes automaticas.
    Gera recomendacoes baseadas em padroes e contexto.
    """

    MODELO_VERSAO = "1.0.0"

    def __init__(self, db: Session):
        self.db = db

    async def gerar_sugestoes(self, condominio_id: UUID) -> Dict[str, Any]:
        """
        Gera sugestoes automaticas para um condominio.
        Analisa dados e gera recomendacoes acionaveis.
        """
        logger.info(f"Gerando sugestoes para condominio {condominio_id}")

        resultados = {
            "condominio_id": str(condominio_id),
            "timestamp": datetime.utcnow().isoformat(),
            "sugestoes_geradas": 0,
            "por_tipo": {},
            "detalhes": []
        }

        try:
            # 1. Sugestoes Operacionais
            sug_operacionais = await self._gerar_sugestoes_operacionais(condominio_id)
            resultados["por_tipo"]["operacional"] = len(sug_operacionais)
            resultados["sugestoes_geradas"] += len(sug_operacionais)
            resultados["detalhes"].extend(sug_operacionais)

            # 2. Sugestoes Financeiras
            sug_financeiras = await self._gerar_sugestoes_financeiras(condominio_id)
            resultados["por_tipo"]["financeira"] = len(sug_financeiras)
            resultados["sugestoes_geradas"] += len(sug_financeiras)
            resultados["detalhes"].extend(sug_financeiras)

            # 3. Sugestoes de Convivencia
            sug_convivencia = await self._gerar_sugestoes_convivencia(condominio_id)
            resultados["por_tipo"]["convivencia"] = len(sug_convivencia)
            resultados["sugestoes_geradas"] += len(sug_convivencia)
            resultados["detalhes"].extend(sug_convivencia)

            # 4. Sugestoes baseadas em Previsoes
            sug_previsoes = await self._gerar_sugestoes_de_previsoes(condominio_id)
            resultados["sugestoes_geradas"] += len(sug_previsoes)
            resultados["detalhes"].extend(sug_previsoes)

            logger.info(f"Sugestoes geradas: {resultados['sugestoes_geradas']}")

        except Exception as e:
            logger.error(f"Erro ao gerar sugestoes: {e}")
            resultados["erro"] = str(e)

        return resultados

    # ==========================================
    # SUGESTOES OPERACIONAIS
    # ==========================================

    async def _gerar_sugestoes_operacionais(self, condominio_id: UUID) -> List[Dict]:
        """Gera sugestoes operacionais"""
        sugestoes = []

        # 1. Reagendar manutencao se conflitar com reservas
        conflitos = await self._verificar_conflitos_manutencao_reserva(condominio_id)
        for conflito in conflitos:
            sugestao = await self._criar_sugestao(
                condominio_id=condominio_id,
                tipo=TipoSugestao.OPERACIONAL,
                codigo=CodigoSugestao.REAGENDAR_MANUTENCAO,
                titulo="Reagendar manutencao",
                descricao=conflito["descricao"],
                contexto=conflito["contexto"],
                beneficio_estimado="Evitar transtornos aos moradores",
                perfil_destino=PerfilDestino.SINDICO,
                prioridade=70,
                dados_entrada=conflito["dados"]
            )
            sugestoes.append(sugestao.to_dict())

        # 2. Consolidar comunicados
        consolidacao = await self._verificar_consolidacao_comunicados(condominio_id)
        if consolidacao:
            sugestao = await self._criar_sugestao(
                condominio_id=condominio_id,
                tipo=TipoSugestao.OPERACIONAL,
                codigo=CodigoSugestao.CONSOLIDAR_COMUNICADOS,
                titulo="Consolidar comunicados",
                descricao=consolidacao["descricao"],
                contexto=consolidacao["contexto"],
                beneficio_estimado="Reduzir fadiga de notificacoes",
                perfil_destino=PerfilDestino.SINDICO,
                prioridade=40,
                dados_entrada=consolidacao["dados"]
            )
            sugestoes.append(sugestao.to_dict())

        # 3. Otimizar rondas de seguranca
        otimizacao_ronda = await self._analisar_otimizacao_rondas(condominio_id)
        if otimizacao_ronda:
            sugestao = await self._criar_sugestao(
                condominio_id=condominio_id,
                tipo=TipoSugestao.SEGURANCA,
                codigo=CodigoSugestao.OTIMIZAR_RONDA,
                titulo="Otimizar rondas de seguranca",
                descricao=otimizacao_ronda["descricao"],
                contexto=otimizacao_ronda["contexto"],
                beneficio_estimado="Melhorar cobertura de seguranca",
                perfil_destino=PerfilDestino.SINDICO,
                prioridade=60,
                dados_entrada=otimizacao_ronda["dados"]
            )
            sugestoes.append(sugestao.to_dict())

        return sugestoes

    async def _verificar_conflitos_manutencao_reserva(self, condominio_id: UUID) -> List[Dict]:
        """Verifica conflitos entre manutencoes agendadas e reservas"""
        conflitos = []

        # Buscar OS com previsao para os proximos 7 dias
        # OrdemServico nao tem condominio_id diretamente
        data_limite = datetime.utcnow() + timedelta(days=7)

        stmt_os = (
            select(OrdemServico)
            .where(
                and_(
                    OrdemServico.status == StatusOS.ABERTA,
                    OrdemServico.data_previsao.isnot(None),
                    OrdemServico.data_previsao <= data_limite,
                    OrdemServico.data_previsao >= datetime.utcnow()
                )
            )
        )

        try:
            result_os = self.db.execute(stmt_os)
            ordens = result_os.scalars().all()

            for os_item in ordens:
                if os_item.data_previsao and os_item.local:
                    # Verificar reservas no mesmo local/data
                    stmt_reserva = (
                        select(Reserva)
                        .join(AreaComum)
                        .where(
                            and_(
                                AreaComum.condominio_id == condominio_id,
                                func.date(Reserva.data_inicio) == func.date(os_item.data_previsao),
                                AreaComum.nome.ilike(f"%{os_item.local}%")
                            )
                        )
                    )

                    result_reserva = self.db.execute(stmt_reserva)
                    reservas = result_reserva.scalars().all()

                    if reservas:
                        conflitos.append({
                            "descricao": f"Manutencao em {os_item.local} conflita com {len(reservas)} reserva(s)",
                            "contexto": f"OS #{os_item.id} prevista para {os_item.data_previsao.strftime('%d/%m')} no mesmo local de reservas",
                            "dados": {
                                "os_id": str(os_item.id),
                                "data_previsao": os_item.data_previsao.isoformat(),
                                "local": os_item.local,
                                "reservas": len(reservas)
                            }
                        })

        except Exception as e:
            logger.warning(f"Erro ao verificar conflitos: {e}")

        return conflitos

    async def _verificar_consolidacao_comunicados(self, condominio_id: UUID) -> Optional[Dict]:
        """Verifica se muitos comunicados foram enviados recentemente"""

        # Contar comunicados dos ultimos 7 dias
        data_limite = datetime.utcnow() - timedelta(days=7)

        stmt = (
            select(func.count(Comunicado.id))
            .where(
                and_(
                    Comunicado.condominio_id == condominio_id,
                    Comunicado.created_at >= data_limite
                )
            )
        )

        try:
            result = self.db.execute(stmt)
            total = result.scalar() or 0

            if total >= 5:
                return {
                    "descricao": f"{total} comunicados enviados na ultima semana",
                    "contexto": "Muitos comunicados podem causar fadiga. Considere agrupar em boletim semanal.",
                    "dados": {
                        "total_comunicados": total,
                        "periodo_dias": 7
                    }
                }

        except Exception as e:
            logger.warning(f"Erro ao verificar comunicados: {e}")

        return None

    async def _analisar_otimizacao_rondas(self, condominio_id: UUID) -> Optional[Dict]:
        """Analisa se rondas podem ser otimizadas"""

        # Buscar ocorrencias de seguranca dos ultimos 30 dias
        data_limite = datetime.utcnow() - timedelta(days=30)

        stmt = (
            select(
                func.extract('hour', Ocorrencia.created_at).label('hora'),
                func.count(Ocorrencia.id).label('total')
            )
            .where(
                and_(
                    Ocorrencia.condominio_id == condominio_id,
                    Ocorrencia.created_at >= data_limite,
                    Ocorrencia.tipo.in_(["seguranca", "invasao", "vandalismo", "furto"])
                )
            )
            .group_by(func.extract('hour', Ocorrencia.created_at))
        )

        try:
            result = self.db.execute(stmt)
            por_hora = {int(r.hora): r.total for r in result.all()}

            if por_hora:
                # Encontrar horario de pico
                hora_pico = max(por_hora, key=por_hora.get)
                total_pico = por_hora[hora_pico]

                if total_pico >= 3:
                    return {
                        "descricao": f"Concentrar rondas no horario das {hora_pico:02d}h",
                        "contexto": f"{total_pico} ocorrencias de seguranca neste horario no ultimo mes",
                        "dados": {
                            "hora_pico": hora_pico,
                            "ocorrencias": total_pico,
                            "distribuicao": por_hora
                        }
                    }

        except Exception as e:
            logger.warning(f"Erro ao analisar rondas: {e}")

        return None

    # ==========================================
    # SUGESTOES FINANCEIRAS
    # ==========================================

    async def _gerar_sugestoes_financeiras(self, condominio_id: UUID) -> List[Dict]:
        """Gera sugestoes financeiras"""
        sugestoes = []

        # 1. Antecipar cobranca para inadimplentes
        antecipacao = await self._verificar_antecipacao_cobranca(condominio_id)
        for ant in antecipacao:
            sugestao = await self._criar_sugestao(
                condominio_id=condominio_id,
                tipo=TipoSugestao.FINANCEIRA,
                codigo=CodigoSugestao.ANTECIPAR_COBRANCA,
                titulo="Antecipar lembrete de cobranca",
                descricao=ant["descricao"],
                contexto=ant["contexto"],
                beneficio_estimado="Reduzir inadimplencia",
                perfil_destino=PerfilDestino.ADMIN,
                prioridade=60,
                dados_entrada=ant["dados"]
            )
            sugestoes.append(sugestao.to_dict())

        # 2. Revisar fundo de reserva
        fundo = await self._verificar_fundo_reserva(condominio_id)
        if fundo:
            sugestao = await self._criar_sugestao(
                condominio_id=condominio_id,
                tipo=TipoSugestao.FINANCEIRA,
                codigo=CodigoSugestao.RESERVA_EMERGENCIA,
                titulo="Revisar fundo de reserva",
                descricao=fundo["descricao"],
                contexto=fundo["contexto"],
                beneficio_estimado=fundo.get("beneficio", "Seguranca financeira"),
                perfil_destino=PerfilDestino.SINDICO,
                prioridade=50,
                dados_entrada=fundo["dados"]
            )
            sugestoes.append(sugestao.to_dict())

        # 3. Renegociar contratos
        contratos = await self._verificar_renegociacao_contratos(condominio_id)
        for contrato in contratos:
            sugestao = await self._criar_sugestao(
                condominio_id=condominio_id,
                tipo=TipoSugestao.FINANCEIRA,
                codigo=CodigoSugestao.RENEGOCIAR_CONTRATO,
                titulo="Renegociar contrato",
                descricao=contrato["descricao"],
                contexto=contrato["contexto"],
                beneficio_estimado=contrato.get("economia", "Reducao de custos"),
                perfil_destino=PerfilDestino.SINDICO,
                prioridade=40,
                dados_entrada=contrato["dados"]
            )
            sugestoes.append(sugestao.to_dict())

        return sugestoes

    async def _verificar_antecipacao_cobranca(self, condominio_id: UUID) -> List[Dict]:
        """Identifica unidades que devem receber lembrete antecipado"""
        antecipacoes = []

        # Buscar unidades com historico de atraso
        data_limite = datetime.utcnow() - timedelta(days=180)

        stmt = (
            select(
                Boleto.unidade_id,
                func.count(Boleto.id).label('total_atrasados')
            )
            .where(
                and_(
                    Boleto.condominio_id == condominio_id,
                    Boleto.created_at >= data_limite,
                    or_(
                        Boleto.status == StatusBoleto.VENCIDO.value,
                        and_(
                            Boleto.data_pagamento.isnot(None),
                            Boleto.data_vencimento.isnot(None),
                            Boleto.data_pagamento > Boleto.data_vencimento
                        )
                    )
                )
            )
            .group_by(Boleto.unidade_id)
            .having(func.count(Boleto.id) >= 2)
        )

        try:
            result = self.db.execute(stmt)
            unidades = result.all()

            for unidade in unidades:
                # Verificar se tem boleto a vencer nos proximos 10 dias
                stmt_proximo = (
                    select(Boleto)
                    .where(
                        and_(
                            Boleto.unidade_id == unidade.unidade_id,
                            Boleto.status == StatusBoleto.ABERTO.value,
                            Boleto.data_vencimento >= datetime.utcnow().date(),
                            Boleto.data_vencimento <= (datetime.utcnow() + timedelta(days=10)).date()
                        )
                    )
                )

                result_proximo = self.db.execute(stmt_proximo)
                boleto_proximo = result_proximo.scalar()

                if boleto_proximo:
                    # Buscar nome da unidade
                    stmt_unidade = select(Unidade).where(Unidade.id == unidade.unidade_id)
                    result_unidade = self.db.execute(stmt_unidade)
                    un = result_unidade.scalar()
                    nome = un.numero if un else f"Unidade {unidade.unidade_id}"

                    antecipacoes.append({
                        "descricao": f"Enviar lembrete antecipado para {nome}",
                        "contexto": f"Unidade tem {unidade.total_atrasados} atrasos nos ultimos 6 meses",
                        "dados": {
                            "unidade_id": str(unidade.unidade_id),
                            "total_atrasados": unidade.total_atrasados,
                            "vencimento_proximo": boleto_proximo.data_vencimento.isoformat() if boleto_proximo.data_vencimento else None
                        }
                    })

        except Exception as e:
            logger.warning(f"Erro ao verificar antecipacao: {e}")

        return antecipacoes

    async def _verificar_fundo_reserva(self, condominio_id: UUID) -> Optional[Dict]:
        """Verifica situacao financeira geral (receitas vs despesas)"""

        # Calcular totais (Lancamento nao tem campo categoria direto)
        data_limite = datetime.utcnow() - timedelta(days=365)

        stmt_receitas = (
            select(func.sum(Lancamento.valor))
            .where(
                and_(
                    Lancamento.condominio_id == condominio_id,
                    Lancamento.tipo == "receita",
                    Lancamento.created_at >= data_limite
                )
            )
        )

        stmt_despesas = (
            select(func.sum(Lancamento.valor))
            .where(
                and_(
                    Lancamento.condominio_id == condominio_id,
                    Lancamento.tipo == "despesa",
                    Lancamento.created_at >= data_limite
                )
            )
        )

        try:
            result_receitas = self.db.execute(stmt_receitas)
            result_despesas = self.db.execute(stmt_despesas)

            receitas = float(result_receitas.scalar() or 0)
            despesas = float(result_despesas.scalar() or 0)
            saldo = receitas - despesas

            # Calcular despesas medias mensais (ultimos 6 meses)
            data_limite = datetime.utcnow() - timedelta(days=180)
            stmt_media = (
                select(func.avg(Lancamento.valor))
                .where(
                    and_(
                        Lancamento.condominio_id == condominio_id,
                        Lancamento.tipo == "despesa",
                        Lancamento.created_at >= data_limite
                    )
                )
            )

            result_media = self.db.execute(stmt_media)
            despesa_media = float(result_media.scalar() or 0)

            # Recomendacao: fundo deve cobrir 3 meses de despesas
            minimo_recomendado = despesa_media * 3

            if saldo < minimo_recomendado and minimo_recomendado > 0:
                diferenca = minimo_recomendado - saldo
                return {
                    "descricao": "Reserva financeira abaixo do recomendado",
                    "contexto": f"Saldo atual: R$ {saldo:.2f}. Recomendado: R$ {minimo_recomendado:.2f}",
                    "beneficio": f"Necessario acumular mais R$ {diferenca:.2f}",
                    "dados": {
                        "saldo_atual": saldo,
                        "minimo_recomendado": minimo_recomendado,
                        "diferenca": diferenca
                    }
                }

        except Exception as e:
            logger.warning(f"Erro ao verificar fundo de reserva: {e}")

        return None

    async def _verificar_renegociacao_contratos(self, condominio_id: UUID) -> List[Dict]:
        """Verifica contratos que podem ser renegociados"""
        contratos = []

        # Buscar despesas recorrentes altas
        data_limite = datetime.utcnow() - timedelta(days=180)

        stmt = (
            select(
                Lancamento.descricao,
                func.sum(Lancamento.valor).label('total'),
                func.count(Lancamento.id).label('quantidade')
            )
            .where(
                and_(
                    Lancamento.condominio_id == condominio_id,
                    Lancamento.tipo == "despesa",
                    Lancamento.created_at >= data_limite
                )
            )
            .group_by(Lancamento.descricao)
            .having(func.count(Lancamento.id) >= 3)
            .order_by(func.sum(Lancamento.valor).desc())
            .limit(5)
        )

        try:
            result = self.db.execute(stmt)
            despesas_recorrentes = result.all()

            for despesa in despesas_recorrentes:
                if despesa.total > 5000:  # Apenas despesas significativas
                    contratos.append({
                        "descricao": f"Revisar contrato: {despesa.descricao}",
                        "contexto": f"R$ {float(despesa.total):.2f} gastos em {despesa.quantidade} pagamentos",
                        "economia": "Potencial economia de 10-20%",
                        "dados": {
                            "categoria": despesa.descricao,
                            "total_gasto": float(despesa.total),
                            "quantidade": despesa.quantidade
                        }
                    })

        except Exception as e:
            logger.warning(f"Erro ao verificar contratos: {e}")

        return contratos

    # ==========================================
    # SUGESTOES DE CONVIVENCIA
    # ==========================================

    async def _gerar_sugestoes_convivencia(self, condominio_id: UUID) -> List[Dict]:
        """Gera sugestoes de convivencia"""
        sugestoes = []

        # 1. Mediar conflitos
        conflitos = await self._identificar_conflitos_para_mediacao(condominio_id)
        for conflito in conflitos:
            sugestao = await self._criar_sugestao(
                condominio_id=condominio_id,
                tipo=TipoSugestao.CONVIVENCIA,
                codigo=CodigoSugestao.MEDIAR_CONFLITO,
                titulo="Mediar conflito entre moradores",
                descricao=conflito["descricao"],
                contexto=conflito["contexto"],
                beneficio_estimado="Melhorar convivencia",
                perfil_destino=PerfilDestino.SINDICO,
                prioridade=70,
                dados_entrada=conflito["dados"]
            )
            sugestoes.append(sugestao.to_dict())

        # 2. Reconhecer colaboradores
        colaboradores = await self._identificar_colaboradores(condominio_id)
        for colab in colaboradores:
            sugestao = await self._criar_sugestao(
                condominio_id=condominio_id,
                tipo=TipoSugestao.CONVIVENCIA,
                codigo=CodigoSugestao.RECONHECER_COLABORADOR,
                titulo="Reconhecer morador colaborativo",
                descricao=colab["descricao"],
                contexto=colab["contexto"],
                beneficio_estimado="Incentivar participacao",
                perfil_destino=PerfilDestino.SINDICO,
                prioridade=30,
                dados_entrada=colab["dados"]
            )
            sugestoes.append(sugestao.to_dict())

        return sugestoes

    async def _identificar_conflitos_para_mediacao(self, condominio_id: UUID) -> List[Dict]:
        """Identifica conflitos que precisam de mediacao"""
        conflitos = []

        # Buscar ocorrencias de conflito recentes
        data_limite = datetime.utcnow() - timedelta(days=60)

        stmt = (
            select(
                Ocorrencia.unidade_id,
                func.count(Ocorrencia.id).label('total')
            )
            .where(
                and_(
                    Ocorrencia.condominio_id == condominio_id,
                    Ocorrencia.created_at >= data_limite,
                    Ocorrencia.tipo.in_(["barulho", "reclamacao", "conflito"])
                )
            )
            .group_by(Ocorrencia.unidade_id)
            .having(func.count(Ocorrencia.id) >= 2)
        )

        try:
            result = self.db.execute(stmt)
            unidades = result.all()

            for unidade in unidades:
                if unidade.unidade_id:
                    stmt_un = select(Unidade).where(Unidade.id == unidade.unidade_id)
                    result_un = self.db.execute(stmt_un)
                    un = result_un.scalar()
                    nome = un.numero if un else f"Unidade {unidade.unidade_id}"

                    conflitos.append({
                        "descricao": f"Agendar conversa com moradores da {nome}",
                        "contexto": f"{unidade.total} ocorrencias de conflito nos ultimos 2 meses",
                        "dados": {
                            "unidade_id": str(unidade.unidade_id),
                            "total_ocorrencias": unidade.total
                        }
                    })

        except Exception as e:
            logger.warning(f"Erro ao identificar conflitos: {e}")

        return conflitos

    async def _identificar_colaboradores(self, condominio_id: UUID) -> List[Dict]:
        """Identifica moradores que merecem reconhecimento"""
        colaboradores = []

        # Simplificado: buscar moradores que reportaram problemas/sugestoes
        data_limite = datetime.utcnow() - timedelta(days=90)

        stmt = (
            select(
                Ocorrencia.reportado_por,
                func.count(Ocorrencia.id).label('total')
            )
            .where(
                and_(
                    Ocorrencia.condominio_id == condominio_id,
                    Ocorrencia.created_at >= data_limite,
                    Ocorrencia.tipo.in_(["sugestao", "melhoria", "elogio"])
                )
            )
            .group_by(Ocorrencia.reportado_por)
            .having(func.count(Ocorrencia.id) >= 2)
        )

        try:
            result = self.db.execute(stmt)
            usuarios = result.all()

            for usuario in usuarios:
                if usuario.reportado_por:
                    stmt_user = select(Usuario).where(Usuario.id == usuario.reportado_por)
                    result_user = self.db.execute(stmt_user)
                    user = result_user.scalar()
                    nome = user.nome if user else "Morador"

                    colaboradores.append({
                        "descricao": f"Agradecer {nome} pela participacao",
                        "contexto": f"{usuario.total} contribuicoes nos ultimos 3 meses",
                        "dados": {
                            "usuario_id": str(usuario.reportado_por),
                            "total_contribuicoes": usuario.total
                        }
                    })

        except Exception as e:
            logger.warning(f"Erro ao identificar colaboradores: {e}")

        return colaboradores

    # ==========================================
    # SUGESTOES BASEADAS EM PREVISOES
    # ==========================================

    async def _gerar_sugestoes_de_previsoes(self, condominio_id: UUID) -> List[Dict]:
        """Gera sugestoes baseadas em previsoes ativas"""
        sugestoes_geradas = []

        # Buscar previsoes pendentes de alta probabilidade
        stmt = (
            select(Previsao)
            .where(
                and_(
                    Previsao.condominio_id == condominio_id,
                    Previsao.status == StatusPrevisao.PENDENTE,
                    Previsao.probabilidade >= 0.6,
                    Previsao.acao_tomada == False
                )
            )
            .order_by(Previsao.probabilidade.desc())
            .limit(10)
        )

        try:
            result = self.db.execute(stmt)
            previsoes = result.scalars().all()

            for previsao in previsoes:
                # Verificar se ja existe sugestao para esta previsao
                stmt_existe = (
                    select(func.count(Sugestao.id))
                    .where(
                        and_(
                            Sugestao.previsao_id == previsao.id,
                            Sugestao.status.in_([StatusSugestao.PENDENTE, StatusSugestao.ACEITA])
                        )
                    )
                )

                result_existe = self.db.execute(stmt_existe)
                if result_existe.scalar() > 0:
                    continue

                # Criar sugestao baseada na previsao
                tipo_sugestao = self._mapear_tipo_previsao_para_sugestao(previsao.tipo)
                codigo_sugestao = self._mapear_codigo_previsao_para_sugestao(previsao.subtipo)

                if tipo_sugestao and codigo_sugestao:
                    sugestao = await self._criar_sugestao(
                        condominio_id=condominio_id,
                        tipo=tipo_sugestao,
                        codigo=codigo_sugestao,
                        titulo=f"Acao preventiva: {previsao.entidade_nome}",
                        descricao=previsao.acao_recomendada,
                        contexto=f"Previsao com {previsao.probabilidade:.0%} de probabilidade",
                        beneficio_estimado=previsao.impacto_estimado or "Evitar problema previsto",
                        perfil_destino=PerfilDestino.SINDICO,
                        prioridade=int(previsao.probabilidade * 100),
                        dados_entrada={"previsao_id": str(previsao.id)},
                        previsao_id=previsao.id
                    )
                    sugestoes_geradas.append(sugestao.to_dict())

        except Exception as e:
            logger.warning(f"Erro ao gerar sugestoes de previsoes: {e}")

        return sugestoes_geradas

    def _mapear_tipo_previsao_para_sugestao(self, tipo: TipoPrevisao) -> Optional[TipoSugestao]:
        """Mapeia tipo de previsao para tipo de sugestao"""
        mapa = {
            TipoPrevisao.FINANCEIRO: TipoSugestao.FINANCEIRA,
            TipoPrevisao.MANUTENCAO: TipoSugestao.MANUTENCAO,
            TipoPrevisao.SEGURANCA: TipoSugestao.SEGURANCA,
            TipoPrevisao.CONVIVENCIA: TipoSugestao.CONVIVENCIA,
        }
        return mapa.get(tipo)

    def _mapear_codigo_previsao_para_sugestao(self, subtipo) -> Optional[CodigoSugestao]:
        """Mapeia subtipo de previsao para codigo de sugestao"""
        from ...models.previsao import SubtipoPrevisao
        mapa = {
            SubtipoPrevisao.INADIMPLENCIA_RISCO: CodigoSugestao.ANTECIPAR_COBRANCA,
            SubtipoPrevisao.EQUIPAMENTO_RISCO: CodigoSugestao.PREVENTIVA_URGENTE,
            SubtipoPrevisao.CONFLITO_POTENCIAL: CodigoSugestao.MEDIAR_CONFLITO,
            SubtipoPrevisao.HORARIO_VULNERAVEL: CodigoSugestao.REFORCAR_HORARIO,
        }
        return mapa.get(subtipo, CodigoSugestao.REDUZIR_CUSTOS)

    # ==========================================
    # UTILIDADES
    # ==========================================

    async def _criar_sugestao(
        self,
        condominio_id: UUID,
        tipo: TipoSugestao,
        codigo: CodigoSugestao,
        titulo: str,
        descricao: str,
        contexto: str,
        beneficio_estimado: str,
        perfil_destino: PerfilDestino,
        prioridade: int,
        dados_entrada: Dict = None,
        previsao_id: UUID = None
    ) -> Sugestao:
        """Cria e persiste uma nova sugestao"""

        sugestao = Sugestao(
            condominio_id=condominio_id,
            tipo=tipo,
            codigo=codigo,
            titulo=titulo,
            descricao=descricao,
            contexto=contexto,
            beneficio_estimado=beneficio_estimado,
            perfil_destino=perfil_destino,
            prioridade=prioridade,
            dados_entrada=dados_entrada or {},
            previsao_id=previsao_id,
            status=StatusSugestao.PENDENTE,
            modelo_versao=self.MODELO_VERSAO,
            expires_at=datetime.utcnow() + timedelta(days=30)
        )

        self.db.add(sugestao)
        self.db.commit()
        self.db.refresh(sugestao)

        logger.info(f"Sugestao criada: {tipo.value}/{codigo.value}")

        return sugestao

    async def listar_sugestoes_pendentes(
        self,
        condominio_id: UUID,
        perfil: Optional[PerfilDestino] = None,
        limit: int = 20
    ) -> List[Sugestao]:
        """Lista sugestoes pendentes para um condominio"""

        stmt = (
            select(Sugestao)
            .where(
                and_(
                    Sugestao.condominio_id == condominio_id,
                    Sugestao.status == StatusSugestao.PENDENTE,
                    or_(
                        Sugestao.expires_at.is_(None),
                        Sugestao.expires_at > datetime.utcnow()
                    )
                )
            )
            .order_by(Sugestao.prioridade.desc(), Sugestao.created_at.desc())
            .limit(limit)
        )

        if perfil:
            stmt = stmt.where(Sugestao.perfil_destino == perfil)

        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def aceitar_sugestao(self, sugestao_id: UUID, usuario_id: UUID) -> Sugestao:
        """Aceita uma sugestao"""

        stmt = select(Sugestao).where(Sugestao.id == sugestao_id)
        result = self.db.execute(stmt)
        sugestao = result.scalar()

        if not sugestao:
            raise ValueError(f"Sugestao {sugestao_id} nao encontrada")

        sugestao.aceitar(usuario_id)

        self.db.commit()
        self.db.refresh(sugestao)

        logger.info(f"Sugestao {sugestao_id} aceita por {usuario_id}")

        return sugestao

    async def rejeitar_sugestao(
        self,
        sugestao_id: UUID,
        usuario_id: UUID,
        motivo: str = None
    ) -> Sugestao:
        """Rejeita uma sugestao"""

        stmt = select(Sugestao).where(Sugestao.id == sugestao_id)
        result = self.db.execute(stmt)
        sugestao = result.scalar()

        if not sugestao:
            raise ValueError(f"Sugestao {sugestao_id} nao encontrada")

        sugestao.rejeitar(usuario_id, motivo)

        self.db.commit()
        self.db.refresh(sugestao)

        logger.info(f"Sugestao {sugestao_id} rejeitada por {usuario_id}")

        return sugestao

    async def registrar_feedback(
        self,
        sugestao_id: UUID,
        util: bool,
        texto: str = None,
        avaliacao: int = None
    ) -> Sugestao:
        """Registra feedback sobre uma sugestao"""

        stmt = select(Sugestao).where(Sugestao.id == sugestao_id)
        result = self.db.execute(stmt)
        sugestao = result.scalar()

        if not sugestao:
            raise ValueError(f"Sugestao {sugestao_id} nao encontrada")

        sugestao.registrar_feedback(util, texto, avaliacao)

        self.db.commit()
        self.db.refresh(sugestao)

        return sugestao
