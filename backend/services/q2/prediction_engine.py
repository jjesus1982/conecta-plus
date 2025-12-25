"""
Conecta Plus - Q2: Motor de Previsao de Problemas
RF-05: Previsao de Problemas

Este servico analisa dados historicos e tendencias para prever
problemas antes que ocorram.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session

from ...models import (
    Previsao, TipoPrevisao, SubtipoPrevisao, StatusPrevisao, TipoEntidadePrevisao,
    Ocorrencia, StatusOcorrencia,
    Lancamento, Boleto, StatusBoleto,
    OrdemServico, StatusOS,
    RegistroAcesso,
    Morador, Unidade, Condominio
)
from ...models.decision_log import DecisionLog, ModuloSistema, TipoDecisao, NivelCriticidade

logger = logging.getLogger(__name__)


class PredictionEngine:
    """
    Motor de previsao de problemas.
    Analisa dados historicos e tendencias para antecipar problemas.
    """

    MODELO_VERSAO = "1.0.0"

    # Thresholds para previsoes
    THRESHOLD_INADIMPLENCIA = 0.6  # 60% probabilidade minima
    THRESHOLD_EQUIPAMENTO = 0.5
    THRESHOLD_CONFLITO = 0.4
    THRESHOLD_SEGURANCA = 0.5

    def __init__(self, db: Session):
        self.db = db

    async def executar_analise_completa(self, condominio_id: UUID) -> Dict[str, Any]:
        """
        Executa analise completa de previsoes para um condominio.
        Retorna resumo das previsoes geradas.
        """
        logger.info(f"Iniciando analise de previsoes para condominio {condominio_id}")

        resultados = {
            "condominio_id": str(condominio_id),
            "timestamp": datetime.utcnow().isoformat(),
            "previsoes_geradas": 0,
            "por_tipo": {},
            "detalhes": []
        }

        try:
            # 1. Previsoes Financeiras
            prev_financeiras = await self._analisar_financeiro(condominio_id)
            resultados["por_tipo"]["financeiro"] = len(prev_financeiras)
            resultados["previsoes_geradas"] += len(prev_financeiras)
            resultados["detalhes"].extend(prev_financeiras)

            # 2. Previsoes de Manutencao
            prev_manutencao = await self._analisar_manutencao(condominio_id)
            resultados["por_tipo"]["manutencao"] = len(prev_manutencao)
            resultados["previsoes_geradas"] += len(prev_manutencao)
            resultados["detalhes"].extend(prev_manutencao)

            # 3. Previsoes de Seguranca
            prev_seguranca = await self._analisar_seguranca(condominio_id)
            resultados["por_tipo"]["seguranca"] = len(prev_seguranca)
            resultados["previsoes_geradas"] += len(prev_seguranca)
            resultados["detalhes"].extend(prev_seguranca)

            # 4. Previsoes de Convivencia
            prev_convivencia = await self._analisar_convivencia(condominio_id)
            resultados["por_tipo"]["convivencia"] = len(prev_convivencia)
            resultados["previsoes_geradas"] += len(prev_convivencia)
            resultados["detalhes"].extend(prev_convivencia)

            logger.info(f"Analise concluida: {resultados['previsoes_geradas']} previsoes geradas")

        except Exception as e:
            logger.error(f"Erro na analise de previsoes: {e}")
            resultados["erro"] = str(e)

        return resultados

    # ==========================================
    # PREVISOES FINANCEIRAS
    # ==========================================

    async def _analisar_financeiro(self, condominio_id: UUID) -> List[Dict]:
        """Analisa riscos financeiros"""
        previsoes = []

        # 1. Risco de inadimplencia por morador
        riscos_inadimplencia = await self._calcular_risco_inadimplencia(condominio_id)
        for risco in riscos_inadimplencia:
            if risco["probabilidade"] >= self.THRESHOLD_INADIMPLENCIA:
                previsao = await self._criar_previsao(
                    condominio_id=condominio_id,
                    tipo=TipoPrevisao.FINANCEIRO,
                    subtipo=SubtipoPrevisao.INADIMPLENCIA_RISCO,
                    entidade_tipo=TipoEntidadePrevisao.UNIDADE,
                    entidade_id=risco["unidade_id"],
                    entidade_nome=risco["unidade_nome"],
                    probabilidade=risco["probabilidade"],
                    confianca=risco["confianca"],
                    horizonte_dias=30,
                    sinais=risco["sinais"],
                    acao_recomendada=self._gerar_acao_inadimplencia(risco),
                    impacto_estimado=f"R$ {risco.get('valor_risco', 0):.2f} em risco"
                )
                previsoes.append(previsao.to_dict())

        # 2. Alerta de fluxo de caixa
        alerta_fluxo = await self._analisar_fluxo_caixa(condominio_id)
        if alerta_fluxo and alerta_fluxo["probabilidade"] >= 0.5:
            previsao = await self._criar_previsao(
                condominio_id=condominio_id,
                tipo=TipoPrevisao.FINANCEIRO,
                subtipo=SubtipoPrevisao.FLUXO_CAIXA_ALERTA,
                entidade_tipo=TipoEntidadePrevisao.CONDOMINIO,
                entidade_id=condominio_id,
                entidade_nome="Condominio",
                probabilidade=alerta_fluxo["probabilidade"],
                confianca=alerta_fluxo["confianca"],
                horizonte_dias=alerta_fluxo["horizonte_dias"],
                sinais=alerta_fluxo["sinais"],
                acao_recomendada=alerta_fluxo["acao"],
                impacto_estimado=alerta_fluxo.get("impacto", "")
            )
            previsoes.append(previsao.to_dict())

        return previsoes

    async def _calcular_risco_inadimplencia(self, condominio_id: UUID) -> List[Dict]:
        """
        Calcula risco de inadimplencia por unidade.
        Analisa:
        - Historico de atrasos
        - Padrao de pagamento
        - Comunicacoes ignoradas
        """
        riscos = []

        # Buscar unidades com boletos
        stmt = (
            select(Unidade)
            .where(Unidade.condominio_id == condominio_id)
        )
        result = self.db.execute(stmt)
        unidades = result.scalars().all()

        for unidade in unidades:
            sinais = []
            score = 0.0
            confianca = 0.3  # Base

            # 1. Verificar historico de boletos (ultimos 12 meses)
            data_limite = datetime.utcnow() - timedelta(days=365)
            stmt_boletos = (
                select(Boleto)
                .where(
                    and_(
                        Boleto.unidade_id == unidade.id,
                        Boleto.created_at >= data_limite
                    )
                )
            )
            result_boletos = self.db.execute(stmt_boletos)
            boletos = result_boletos.scalars().all()

            if boletos:
                total_boletos = len(boletos)
                atrasados = sum(1 for b in boletos if b.status == StatusBoleto.VENCIDO.value or b.status == "vencido")
                pagos_atrasados = sum(1 for b in boletos if b.data_pagamento and b.data_vencimento and b.data_pagamento > b.data_vencimento)

                taxa_atraso = (atrasados + pagos_atrasados) / total_boletos if total_boletos > 0 else 0

                if taxa_atraso > 0.3:
                    sinais.append(f"Taxa de atraso alta: {taxa_atraso:.0%}")
                    score += 0.4
                    confianca += 0.2

                if atrasados > 2:
                    sinais.append(f"{atrasados} boletos vencidos em aberto")
                    score += 0.3

                # Padrao de pagamento no ultimo dia
                if total_boletos >= 3:
                    pagamentos_ultimo_dia = sum(
                        1 for b in boletos
                        if b.data_pagamento and b.data_vencimento and
                        (b.data_vencimento - b.data_pagamento).days <= 1
                    )
                    if pagamentos_ultimo_dia / total_boletos > 0.5:
                        sinais.append("Padrao de pagamento no ultimo dia")
                        score += 0.1
                        confianca += 0.1

            # 2. Verificar ocorrencias financeiras
            stmt_ocor = (
                select(func.count(Ocorrencia.id))
                .where(
                    and_(
                        Ocorrencia.unidade_id == unidade.id,
                        Ocorrencia.tipo.in_(["financeiro", "cobranca"]),
                        Ocorrencia.created_at >= data_limite
                    )
                )
            )
            result_ocor = self.db.execute(stmt_ocor)
            ocorrencias_financeiras = result_ocor.scalar() or 0

            if ocorrencias_financeiras > 2:
                sinais.append(f"{ocorrencias_financeiras} ocorrencias financeiras no ultimo ano")
                score += 0.2

            # Normalizar score
            probabilidade = min(score, 1.0)
            confianca = min(confianca, 1.0)

            if probabilidade > 0:
                # Calcular valor em risco
                valor_risco = sum(
                    float(b.valor) for b in boletos
                    if b.status == StatusBoleto.VENCIDO
                ) if boletos else 0

                riscos.append({
                    "unidade_id": unidade.id,
                    "unidade_nome": unidade.numero or f"Unidade {unidade.id}",
                    "probabilidade": probabilidade,
                    "confianca": confianca,
                    "sinais": sinais,
                    "valor_risco": valor_risco
                })

        return riscos

    async def _analisar_fluxo_caixa(self, condominio_id: UUID) -> Optional[Dict]:
        """Analisa tendencia de fluxo de caixa"""
        # Verificar tendencia dos ultimos 3 meses
        data_inicio = datetime.utcnow() - timedelta(days=90)

        stmt_receitas = (
            select(func.sum(Lancamento.valor))
            .where(
                and_(
                    Lancamento.condominio_id == condominio_id,
                    Lancamento.tipo == "receita",
                    Lancamento.created_at >= data_inicio
                )
            )
        )

        stmt_despesas = (
            select(func.sum(Lancamento.valor))
            .where(
                and_(
                    Lancamento.condominio_id == condominio_id,
                    Lancamento.tipo == "despesa",
                    Lancamento.created_at >= data_inicio
                )
            )
        )

        try:
            result_receitas = self.db.execute(stmt_receitas)
            result_despesas = self.db.execute(stmt_despesas)

            receitas = float(result_receitas.scalar() or 0)
            despesas = float(result_despesas.scalar() or 0)

            if receitas > 0:
                margem = (receitas - despesas) / receitas

                if margem < 0.1:  # Margem menor que 10%
                    sinais = []
                    sinais.append(f"Margem baixa: {margem:.1%}")

                    if despesas > receitas:
                        sinais.append("Despesas maiores que receitas")

                    return {
                        "probabilidade": 0.7 if margem < 0 else 0.5,
                        "confianca": 0.6,
                        "horizonte_dias": 30,
                        "sinais": sinais,
                        "acao": "Revisar despesas e verificar inadimplencia",
                        "impacto": f"Deficit de R$ {abs(receitas - despesas):.2f}" if despesas > receitas else ""
                    }

        except Exception as e:
            logger.warning(f"Erro ao analisar fluxo de caixa: {e}")

        return None

    def _gerar_acao_inadimplencia(self, risco: Dict) -> str:
        """Gera recomendacao de acao para risco de inadimplencia"""
        prob = risco["probabilidade"]

        if prob >= 0.8:
            return "Contato urgente para negociacao. Considerar parcelamento preventivo."
        elif prob >= 0.6:
            return "Enviar lembrete amigavel 5 dias antes do vencimento. Oferecer debito automatico."
        else:
            return "Monitorar pagamentos. Incluir em campanha de conscientizacao."

    # ==========================================
    # PREVISOES DE MANUTENCAO
    # ==========================================

    async def _analisar_manutencao(self, condominio_id: UUID) -> List[Dict]:
        """Analisa riscos de manutencao"""
        previsoes = []

        # 1. Equipamentos com risco de falha
        riscos_equipamento = await self._calcular_risco_equipamento(condominio_id)
        for risco in riscos_equipamento:
            if risco["probabilidade"] >= self.THRESHOLD_EQUIPAMENTO:
                previsao = await self._criar_previsao(
                    condominio_id=condominio_id,
                    tipo=TipoPrevisao.MANUTENCAO,
                    subtipo=SubtipoPrevisao.EQUIPAMENTO_RISCO,
                    entidade_tipo=TipoEntidadePrevisao.EQUIPAMENTO,
                    entidade_id=risco.get("equipamento_id"),
                    entidade_nome=risco["equipamento_nome"],
                    probabilidade=risco["probabilidade"],
                    confianca=risco["confianca"],
                    horizonte_dias=risco["horizonte_dias"],
                    sinais=risco["sinais"],
                    acao_recomendada=risco["acao"],
                    impacto_estimado=risco.get("impacto", "")
                )
                previsoes.append(previsao.to_dict())

        # 2. Areas com desgaste
        areas_desgaste = await self._analisar_areas_desgaste(condominio_id)
        for area in areas_desgaste:
            previsao = await self._criar_previsao(
                condominio_id=condominio_id,
                tipo=TipoPrevisao.MANUTENCAO,
                subtipo=SubtipoPrevisao.AREA_COMUM_DESGASTE,
                entidade_tipo=TipoEntidadePrevisao.AREA,
                entidade_id=area.get("area_id"),
                entidade_nome=area["area_nome"],
                probabilidade=area["probabilidade"],
                confianca=area["confianca"],
                horizonte_dias=90,
                sinais=area["sinais"],
                acao_recomendada=area["acao"],
                impacto_estimado=""
            )
            previsoes.append(previsao.to_dict())

        return previsoes

    async def _calcular_risco_equipamento(self, condominio_id: UUID) -> List[Dict]:
        """Calcula risco de falha de equipamentos baseado em OS"""
        riscos = []

        # Buscar OS dos ultimos 12 meses agrupadas por equipamento
        # OrdemServico nao tem condominio_id diretamente, filtramos por fornecedor
        data_limite = datetime.utcnow() - timedelta(days=365)

        stmt = (
            select(
                OrdemServico.equipamento,
                func.count(OrdemServico.id).label("total_os"),
                func.max(OrdemServico.created_at).label("ultima_os")
            )
            .where(
                and_(
                    OrdemServico.created_at >= data_limite,
                    OrdemServico.equipamento.isnot(None)
                )
            )
            .group_by(OrdemServico.equipamento)
        )

        try:
            result = self.db.execute(stmt)
            equipamentos = result.all()

            for equip in equipamentos:
                if equip.total_os >= 3:  # Pelo menos 3 OS no ano
                    sinais = []
                    score = 0.0

                    sinais.append(f"{equip.total_os} OS no ultimo ano")
                    score += min(equip.total_os * 0.1, 0.5)

                    # Verificar frequencia
                    if equip.total_os >= 6:
                        sinais.append("Alta frequencia de manutencoes")
                        score += 0.3

                    # Ultima manutencao
                    if equip.ultima_os:
                        dias_desde = (datetime.utcnow() - equip.ultima_os).days
                        if dias_desde > 180:
                            sinais.append(f"Ultima manutencao ha {dias_desde} dias")
                            score += 0.2

                    riscos.append({
                        "equipamento_nome": equip.equipamento or "Equipamento",
                        "probabilidade": min(score, 1.0),
                        "confianca": 0.5,
                        "horizonte_dias": 60,
                        "sinais": sinais,
                        "acao": f"Agendar manutencao preventiva para {equip.equipamento}"
                    })

        except Exception as e:
            logger.warning(f"Erro ao analisar equipamentos: {e}")

        return riscos

    async def _analisar_areas_desgaste(self, condominio_id: UUID) -> List[Dict]:
        """Analisa areas com potencial desgaste baseado em ocorrencias"""
        areas = []

        # Buscar ocorrencias por tipo (areas comuns identificadas pelo tipo)
        data_limite = datetime.utcnow() - timedelta(days=180)

        stmt = (
            select(
                Ocorrencia.tipo,
                func.count(Ocorrencia.id).label("total")
            )
            .where(
                and_(
                    Ocorrencia.condominio_id == condominio_id,
                    Ocorrencia.created_at >= data_limite,
                    Ocorrencia.tipo.isnot(None)
                )
            )
            .group_by(Ocorrencia.tipo)
            .having(func.count(Ocorrencia.id) >= 3)
        )

        try:
            result = self.db.execute(stmt)
            tipos = result.all()

            for tipo_oc in tipos:
                sinais = [f"{tipo_oc.total} ocorrencias do tipo '{tipo_oc.tipo}' em 6 meses"]

                areas.append({
                    "area_nome": tipo_oc.tipo or "Area comum",
                    "probabilidade": min(tipo_oc.total * 0.15, 0.9),
                    "confianca": 0.6,
                    "sinais": sinais,
                    "acao": f"Inspecionar areas relacionadas a '{tipo_oc.tipo}' e avaliar necessidade de manutencao"
                })

        except Exception as e:
            logger.warning(f"Erro ao analisar areas: {e}")

        return areas

    # ==========================================
    # PREVISOES DE SEGURANCA
    # ==========================================

    async def _analisar_seguranca(self, condominio_id: UUID) -> List[Dict]:
        """Analisa riscos de seguranca"""
        previsoes = []

        # 1. Horarios vulneraveis
        vulnerabilidades = await self._identificar_horarios_vulneraveis(condominio_id)
        for vuln in vulnerabilidades:
            previsao = await self._criar_previsao(
                condominio_id=condominio_id,
                tipo=TipoPrevisao.SEGURANCA,
                subtipo=SubtipoPrevisao.HORARIO_VULNERAVEL,
                entidade_tipo=TipoEntidadePrevisao.CONDOMINIO,
                entidade_id=condominio_id,
                entidade_nome=f"Horario {vuln['horario']}",
                probabilidade=vuln["probabilidade"],
                confianca=vuln["confianca"],
                horizonte_dias=7,
                sinais=vuln["sinais"],
                acao_recomendada=vuln["acao"],
                impacto_estimado=""
            )
            previsoes.append(previsao.to_dict())

        # 2. Padroes anomalos
        anomalias = await self._detectar_padroes_anomalos(condominio_id)
        for anomalia in anomalias:
            previsao = await self._criar_previsao(
                condominio_id=condominio_id,
                tipo=TipoPrevisao.SEGURANCA,
                subtipo=SubtipoPrevisao.PADRAO_ANOMALO,
                entidade_tipo=TipoEntidadePrevisao.UNIDADE,
                entidade_id=anomalia.get("unidade_id"),
                entidade_nome=anomalia.get("descricao", "Padrao anomalo"),
                probabilidade=anomalia["probabilidade"],
                confianca=anomalia["confianca"],
                horizonte_dias=7,
                sinais=anomalia["sinais"],
                acao_recomendada=anomalia["acao"],
                impacto_estimado=""
            )
            previsoes.append(previsao.to_dict())

        return previsoes

    async def _identificar_horarios_vulneraveis(self, condominio_id: UUID) -> List[Dict]:
        """Identifica horarios com menor cobertura de seguranca"""
        vulnerabilidades = []

        # Analisar distribuicao de acessos por horario
        # RegistroAcesso nao tem condominio_id direto, analisa todos os acessos recentes
        data_limite = datetime.utcnow() - timedelta(days=30)

        stmt = (
            select(
                func.extract('hour', RegistroAcesso.data_hora).label('hora'),
                func.count(RegistroAcesso.id).label('total')
            )
            .where(RegistroAcesso.data_hora >= data_limite)
            .group_by(func.extract('hour', RegistroAcesso.data_hora))
        )

        try:
            result = self.db.execute(stmt)
            acessos_por_hora = {int(r.hora): r.total for r in result.all()}

            # Identificar horarios com baixo movimento (potencialmente vulneraveis)
            media_acessos = sum(acessos_por_hora.values()) / 24 if acessos_por_hora else 0

            for hora in range(24):
                acessos = acessos_por_hora.get(hora, 0)
                if acessos < media_acessos * 0.2 and hora not in [0, 1, 2, 3, 4, 5]:
                    # Horarios com baixo movimento fora da madrugada
                    vulnerabilidades.append({
                        "horario": f"{hora:02d}:00",
                        "probabilidade": 0.6,
                        "confianca": 0.5,
                        "sinais": [f"Apenas {acessos} acessos registrados no horario"],
                        "acao": f"Reforcar vigilancia no horario das {hora:02d}h"
                    })

        except Exception as e:
            logger.warning(f"Erro ao analisar horarios: {e}")

        return vulnerabilidades

    async def _detectar_padroes_anomalos(self, condominio_id: UUID) -> List[Dict]:
        """Detecta padroes de acesso anomalos"""
        anomalias = []

        # Verificar acessos em horarios incomuns (madrugada)
        # RegistroAcesso usa destino_unidade_id, nao unidade_id
        data_limite = datetime.utcnow() - timedelta(days=7)

        stmt = (
            select(
                RegistroAcesso.destino_unidade_id,
                func.count(RegistroAcesso.id).label('total_madrugada')
            )
            .where(
                and_(
                    RegistroAcesso.data_hora >= data_limite,
                    RegistroAcesso.destino_unidade_id.isnot(None),
                    func.extract('hour', RegistroAcesso.data_hora).between(0, 5)
                )
            )
            .group_by(RegistroAcesso.destino_unidade_id)
            .having(func.count(RegistroAcesso.id) >= 5)
        )

        try:
            result = self.db.execute(stmt)
            unidades_anomalas = result.all()

            for unidade in unidades_anomalas:
                anomalias.append({
                    "unidade_id": unidade.destino_unidade_id,
                    "descricao": "Acessos frequentes na madrugada",
                    "probabilidade": 0.5,
                    "confianca": 0.4,
                    "sinais": [f"{unidade.total_madrugada} acessos entre 0h-5h na ultima semana"],
                    "acao": "Verificar se padrao e esperado ou requer atencao"
                })

        except Exception as e:
            logger.warning(f"Erro ao detectar anomalias: {e}")

        return anomalias

    # ==========================================
    # PREVISOES DE CONVIVENCIA
    # ==========================================

    async def _analisar_convivencia(self, condominio_id: UUID) -> List[Dict]:
        """Analisa riscos de convivencia"""
        previsoes = []

        # 1. Potenciais conflitos entre unidades
        conflitos = await self._identificar_conflitos_potenciais(condominio_id)
        for conflito in conflitos:
            if conflito["probabilidade"] >= self.THRESHOLD_CONFLITO:
                previsao = await self._criar_previsao(
                    condominio_id=condominio_id,
                    tipo=TipoPrevisao.CONVIVENCIA,
                    subtipo=SubtipoPrevisao.CONFLITO_POTENCIAL,
                    entidade_tipo=TipoEntidadePrevisao.UNIDADE,
                    entidade_id=conflito.get("unidade_id"),
                    entidade_nome=conflito["descricao"],
                    probabilidade=conflito["probabilidade"],
                    confianca=conflito["confianca"],
                    horizonte_dias=30,
                    sinais=conflito["sinais"],
                    acao_recomendada=conflito["acao"],
                    impacto_estimado=""
                )
                previsoes.append(previsao.to_dict())

        return previsoes

    async def _identificar_conflitos_potenciais(self, condominio_id: UUID) -> List[Dict]:
        """Identifica unidades com potencial de conflito"""
        conflitos = []

        # Buscar ocorrencias de barulho/convivencia nos ultimos 6 meses
        data_limite = datetime.utcnow() - timedelta(days=180)

        stmt = (
            select(
                Ocorrencia.unidade_id,
                func.count(Ocorrencia.id).label('total')
            )
            .where(
                and_(
                    Ocorrencia.condominio_id == condominio_id,
                    Ocorrencia.created_at >= data_limite,
                    or_(
                        Ocorrencia.tipo == "barulho",
                        Ocorrencia.tipo == "convivencia",
                        Ocorrencia.tipo == "reclamacao"
                    )
                )
            )
            .group_by(Ocorrencia.unidade_id)
            .having(func.count(Ocorrencia.id) >= 3)
        )

        try:
            result = self.db.execute(stmt)
            unidades_problematicas = result.all()

            for unidade in unidades_problematicas:
                if unidade.unidade_id:
                    # Buscar detalhes da unidade
                    stmt_unidade = select(Unidade).where(Unidade.id == unidade.unidade_id)
                    result_unidade = self.db.execute(stmt_unidade)
                    un = result_unidade.scalar()

                    nome_unidade = un.numero if un else f"Unidade {unidade.unidade_id}"

                    conflitos.append({
                        "unidade_id": unidade.unidade_id,
                        "descricao": f"Conflitos envolvendo {nome_unidade}",
                        "probabilidade": min(unidade.total * 0.2, 0.9),
                        "confianca": 0.6,
                        "sinais": [f"{unidade.total} ocorrencias de convivencia em 6 meses"],
                        "acao": f"Agendar conversa de mediacao com moradores da {nome_unidade}"
                    })

        except Exception as e:
            logger.warning(f"Erro ao identificar conflitos: {e}")

        return conflitos

    # ==========================================
    # UTILIDADES
    # ==========================================

    async def _criar_previsao(
        self,
        condominio_id: UUID,
        tipo: TipoPrevisao,
        subtipo: SubtipoPrevisao,
        entidade_tipo: TipoEntidadePrevisao,
        entidade_id: Optional[UUID],
        entidade_nome: str,
        probabilidade: float,
        confianca: float,
        horizonte_dias: int,
        sinais: List[str],
        acao_recomendada: str,
        impacto_estimado: str = ""
    ) -> Previsao:
        """Cria e persiste uma nova previsao"""

        previsao = Previsao(
            condominio_id=condominio_id,
            tipo=tipo,
            subtipo=subtipo,
            entidade_tipo=entidade_tipo,
            entidade_id=entidade_id,
            entidade_nome=entidade_nome,
            probabilidade=probabilidade,
            confianca=confianca,
            horizonte_dias=horizonte_dias,
            sinais=sinais,
            dados_entrada={},
            acao_recomendada=acao_recomendada,
            impacto_estimado=impacto_estimado,
            status=StatusPrevisao.PENDENTE,
            modelo_versao=self.MODELO_VERSAO,
            expires_at=datetime.utcnow() + timedelta(days=horizonte_dias)
        )

        self.db.add(previsao)
        self.db.commit()
        self.db.refresh(previsao)

        logger.info(f"Previsao criada: {tipo.value}/{subtipo.value} prob={probabilidade:.0%}")

        return previsao

    async def listar_previsoes_ativas(
        self,
        condominio_id: UUID,
        tipo: Optional[TipoPrevisao] = None,
        limit: int = 50
    ) -> List[Previsao]:
        """Lista previsoes ativas de um condominio"""

        stmt = (
            select(Previsao)
            .where(
                and_(
                    Previsao.condominio_id == condominio_id,
                    Previsao.status == StatusPrevisao.PENDENTE,
                    or_(
                        Previsao.expires_at.is_(None),
                        Previsao.expires_at > datetime.utcnow()
                    )
                )
            )
            .order_by(Previsao.probabilidade.desc(), Previsao.created_at.desc())
            .limit(limit)
        )

        if tipo:
            stmt = stmt.where(Previsao.tipo == tipo)

        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def validar_previsao(
        self,
        previsao_id: UUID,
        usuario_id: UUID,
        confirmada: bool,
        motivo: str = None
    ) -> Previsao:
        """Valida uma previsao (confirma ou marca como falso positivo)"""

        stmt = select(Previsao).where(Previsao.id == previsao_id)
        result = self.db.execute(stmt)
        previsao = result.scalar()

        if not previsao:
            raise ValueError(f"Previsao {previsao_id} nao encontrada")

        previsao.status = StatusPrevisao.CONFIRMADA if confirmada else StatusPrevisao.FALSO_POSITIVO
        previsao.validada_em = datetime.utcnow()
        previsao.validada_por = usuario_id
        previsao.motivo_validacao = motivo

        self.db.commit()
        self.db.refresh(previsao)

        logger.info(f"Previsao {previsao_id} validada: confirmada={confirmada}")

        return previsao

    async def obter_dashboard(self, condominio_id: UUID) -> Dict[str, Any]:
        """Retorna dados para dashboard de previsoes"""

        # Contagem por tipo
        stmt_por_tipo = (
            select(Previsao.tipo, func.count(Previsao.id))
            .where(
                and_(
                    Previsao.condominio_id == condominio_id,
                    Previsao.status == StatusPrevisao.PENDENTE
                )
            )
            .group_by(Previsao.tipo)
        )

        result_tipo = self.db.execute(stmt_por_tipo)
        por_tipo = {r[0].value: r[1] for r in result_tipo.all()}

        # Previsoes de alto risco
        stmt_alto_risco = (
            select(func.count(Previsao.id))
            .where(
                and_(
                    Previsao.condominio_id == condominio_id,
                    Previsao.status == StatusPrevisao.PENDENTE,
                    Previsao.probabilidade >= 0.7
                )
            )
        )

        result_alto = self.db.execute(stmt_alto_risco)
        alto_risco = result_alto.scalar() or 0

        # Precisao historica
        stmt_validadas = (
            select(
                func.count(Previsao.id).filter(Previsao.status == StatusPrevisao.CONFIRMADA),
                func.count(Previsao.id).filter(Previsao.status == StatusPrevisao.FALSO_POSITIVO)
            )
            .where(Previsao.condominio_id == condominio_id)
        )

        result_validadas = self.db.execute(stmt_validadas)
        validadas = result_validadas.first()
        confirmadas = validadas[0] or 0
        falsos = validadas[1] or 0

        precisao = confirmadas / (confirmadas + falsos) if (confirmadas + falsos) > 0 else None

        return {
            "total_pendentes": sum(por_tipo.values()),
            "por_tipo": por_tipo,
            "alto_risco": alto_risco,
            "metricas": {
                "confirmadas": confirmadas,
                "falsos_positivos": falsos,
                "precisao": precisao
            }
        }
