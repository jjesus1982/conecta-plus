"""
Conecta Plus - Dashboard Inteligente
Geração automática de insights e análises contextualizadas
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import math


# ==================== TIPOS ====================

class TipoInsight(str, Enum):
    """Tipos de insight gerados"""
    POSITIVO = "positivo"
    NEGATIVO = "negativo"
    NEUTRO = "neutro"
    ALERTA = "alerta"
    OPORTUNIDADE = "oportunidade"
    TENDENCIA = "tendencia"


class CategoriaInsight(str, Enum):
    """Categorias de insight"""
    INADIMPLENCIA = "inadimplencia"
    RECEITA = "receita"
    DESPESA = "despesa"
    FLUXO_CAIXA = "fluxo_caixa"
    COBRANCA = "cobranca"
    ACORDO = "acordo"
    COMPARATIVO = "comparativo"
    PREVISAO = "previsao"


@dataclass
class Insight:
    """Um insight gerado pelo sistema"""
    tipo: TipoInsight
    categoria: CategoriaInsight
    titulo: str
    descricao: str
    valor_destaque: Optional[str]
    variacao: Optional[float]  # % de variação
    periodo_comparacao: Optional[str]
    acao_sugerida: Optional[str]
    prioridade: int  # 1-5 (5 = mais importante)
    dados_suporte: Dict[str, Any]


@dataclass
class DashboardCompleto:
    """Dashboard completo com dados e insights"""
    periodo: str
    resumo_financeiro: Dict[str, Any]
    indicadores_chave: List[Dict[str, Any]]
    insights: List[Insight]
    alertas_ativos: List[Dict[str, Any]]
    graficos_dados: Dict[str, List[Dict]]
    acoes_recomendadas: List[Dict[str, Any]]
    saude_financeira: Dict[str, Any]


# ==================== GERADOR DE INSIGHTS ====================

class GeradorInsights:
    """
    Gera insights automáticos baseado em análise de dados
    """

    def gerar_insights(
        self,
        dados_atuais: Dict[str, Any],
        dados_anteriores: Dict[str, Any],
        benchmarks: Optional[Dict[str, Any]] = None
    ) -> List[Insight]:
        """
        Gera lista de insights baseado em análise comparativa

        Args:
            dados_atuais: Dados do período atual
            dados_anteriores: Dados do período anterior para comparação
            benchmarks: Benchmarks de mercado (opcional)

        Returns:
            Lista de Insight ordenada por prioridade
        """
        insights = []

        # 1. Insights de inadimplência
        insights.extend(self._insights_inadimplencia(dados_atuais, dados_anteriores))

        # 2. Insights de receita
        insights.extend(self._insights_receita(dados_atuais, dados_anteriores))

        # 3. Insights de despesa
        insights.extend(self._insights_despesa(dados_atuais, dados_anteriores))

        # 4. Insights de fluxo de caixa
        insights.extend(self._insights_fluxo_caixa(dados_atuais, dados_anteriores))

        # 5. Insights de cobrança
        insights.extend(self._insights_cobranca(dados_atuais, dados_anteriores))

        # 6. Insights comparativos (benchmarks)
        if benchmarks:
            insights.extend(self._insights_benchmark(dados_atuais, benchmarks))

        # 7. Insights de tendência
        insights.extend(self._insights_tendencia(dados_atuais, dados_anteriores))

        # Ordena por prioridade (maior primeiro)
        insights.sort(key=lambda x: x.prioridade, reverse=True)

        # Limita a top 10 insights mais relevantes
        return insights[:10]

    def _insights_inadimplencia(
        self,
        atual: Dict,
        anterior: Dict
    ) -> List[Insight]:
        """Gera insights sobre inadimplência"""
        insights = []

        taxa_atual = atual.get('taxa_inadimplencia', 0)
        taxa_anterior = anterior.get('taxa_inadimplencia', 0)

        if taxa_anterior > 0:
            variacao = ((taxa_atual - taxa_anterior) / taxa_anterior) * 100
        else:
            variacao = 0

        # Insight de variação
        if variacao > 10:
            insights.append(Insight(
                tipo=TipoInsight.NEGATIVO,
                categoria=CategoriaInsight.INADIMPLENCIA,
                titulo="Inadimplência em alta",
                descricao=f"A taxa de inadimplência aumentou {variacao:.1f}% em relação ao período anterior, "
                         f"passando de {taxa_anterior:.1f}% para {taxa_atual:.1f}%.",
                valor_destaque=f"{taxa_atual:.1f}%",
                variacao=variacao,
                periodo_comparacao="mês anterior",
                acao_sugerida="Intensificar cobrança preventiva e revisar régua de comunicação.",
                prioridade=5,
                dados_suporte={
                    'taxa_atual': taxa_atual,
                    'taxa_anterior': taxa_anterior,
                    'unidades_inadimplentes': atual.get('unidades_inadimplentes', 0)
                }
            ))
        elif variacao < -10:
            insights.append(Insight(
                tipo=TipoInsight.POSITIVO,
                categoria=CategoriaInsight.INADIMPLENCIA,
                titulo="Inadimplência em queda",
                descricao=f"Excelente! A taxa de inadimplência reduziu {abs(variacao):.1f}%, "
                         f"de {taxa_anterior:.1f}% para {taxa_atual:.1f}%.",
                valor_destaque=f"{taxa_atual:.1f}%",
                variacao=variacao,
                periodo_comparacao="mês anterior",
                acao_sugerida="Manter estratégia atual de cobrança. Considerar reconhecer bons pagadores.",
                prioridade=4,
                dados_suporte={
                    'taxa_atual': taxa_atual,
                    'taxa_anterior': taxa_anterior
                }
            ))

        # Insight de valor em aberto
        valor_aberto = atual.get('valor_inadimplente', 0)
        if valor_aberto > 50000:
            insights.append(Insight(
                tipo=TipoInsight.ALERTA,
                categoria=CategoriaInsight.INADIMPLENCIA,
                titulo="Alto valor em aberto",
                descricao=f"O valor total inadimplente de R$ {valor_aberto:,.2f} representa "
                         f"risco significativo ao fluxo de caixa.",
                valor_destaque=f"R$ {valor_aberto:,.2f}",
                variacao=None,
                periodo_comparacao=None,
                acao_sugerida="Priorizar negociação com os 5 maiores devedores, que representam maior parte do valor.",
                prioridade=5,
                dados_suporte={'valor_total': valor_aberto}
            ))

        return insights

    def _insights_receita(
        self,
        atual: Dict,
        anterior: Dict
    ) -> List[Insight]:
        """Gera insights sobre receita"""
        insights = []

        receita_atual = atual.get('receita_total', 0)
        receita_anterior = anterior.get('receita_total', 0)
        receita_prevista = atual.get('receita_prevista', receita_atual)

        if receita_anterior > 0:
            variacao = ((receita_atual - receita_anterior) / receita_anterior) * 100
        else:
            variacao = 0

        # Variação de receita
        if variacao < -5:
            insights.append(Insight(
                tipo=TipoInsight.NEGATIVO,
                categoria=CategoriaInsight.RECEITA,
                titulo="Receita abaixo do esperado",
                descricao=f"A receita recebida foi {abs(variacao):.1f}% menor que o período anterior. "
                         f"Principal motivo: aumento na inadimplência.",
                valor_destaque=f"R$ {receita_atual:,.2f}",
                variacao=variacao,
                periodo_comparacao="mês anterior",
                acao_sugerida="Analisar principais devedores e acelerar cobrança.",
                prioridade=4,
                dados_suporte={
                    'receita_atual': receita_atual,
                    'receita_anterior': receita_anterior
                }
            ))
        elif variacao > 5:
            insights.append(Insight(
                tipo=TipoInsight.POSITIVO,
                categoria=CategoriaInsight.RECEITA,
                titulo="Receita acima do esperado",
                descricao=f"A receita cresceu {variacao:.1f}% em relação ao período anterior, "
                         f"totalizando R$ {receita_atual:,.2f}.",
                valor_destaque=f"+{variacao:.1f}%",
                variacao=variacao,
                periodo_comparacao="mês anterior",
                acao_sugerida="Considerar aplicação financeira do excedente.",
                prioridade=3,
                dados_suporte={
                    'receita_atual': receita_atual,
                    'receita_anterior': receita_anterior
                }
            ))

        # Atingimento da meta
        if receita_prevista > 0:
            atingimento = (receita_atual / receita_prevista) * 100
            if atingimento < 90:
                insights.append(Insight(
                    tipo=TipoInsight.ALERTA,
                    categoria=CategoriaInsight.RECEITA,
                    titulo="Meta de receita não atingida",
                    descricao=f"Atingido apenas {atingimento:.1f}% da receita prevista. "
                             f"Faltam R$ {receita_prevista - receita_atual:,.2f} para a meta.",
                    valor_destaque=f"{atingimento:.1f}%",
                    variacao=atingimento - 100,
                    periodo_comparacao="meta do período",
                    acao_sugerida="Revisar previsões e intensificar recuperação de inadimplentes.",
                    prioridade=4,
                    dados_suporte={
                        'receita_atual': receita_atual,
                        'receita_prevista': receita_prevista
                    }
                ))

        return insights

    def _insights_despesa(
        self,
        atual: Dict,
        anterior: Dict
    ) -> List[Insight]:
        """Gera insights sobre despesas"""
        insights = []

        despesa_atual = atual.get('despesa_total', 0)
        despesa_anterior = anterior.get('despesa_total', 0)
        orcamento = atual.get('despesa_orcada', despesa_atual)

        if despesa_anterior > 0:
            variacao = ((despesa_atual - despesa_anterior) / despesa_anterior) * 100
        else:
            variacao = 0

        # Variação de despesa
        if variacao > 15:
            insights.append(Insight(
                tipo=TipoInsight.NEGATIVO,
                categoria=CategoriaInsight.DESPESA,
                titulo="Despesas em alta",
                descricao=f"As despesas aumentaram {variacao:.1f}% em relação ao período anterior. "
                         f"Avaliar se são gastos necessários ou extraordinários.",
                valor_destaque=f"R$ {despesa_atual:,.2f}",
                variacao=variacao,
                periodo_comparacao="mês anterior",
                acao_sugerida="Revisar principais categorias de gasto e identificar oportunidades de redução.",
                prioridade=4,
                dados_suporte={
                    'despesa_atual': despesa_atual,
                    'despesa_anterior': despesa_anterior
                }
            ))
        elif variacao < -10:
            insights.append(Insight(
                tipo=TipoInsight.POSITIVO,
                categoria=CategoriaInsight.DESPESA,
                titulo="Economia nas despesas",
                descricao=f"Despesas {abs(variacao):.1f}% menores que o período anterior, "
                         f"gerando economia de R$ {despesa_anterior - despesa_atual:,.2f}.",
                valor_destaque=f"-{abs(variacao):.1f}%",
                variacao=variacao,
                periodo_comparacao="mês anterior",
                acao_sugerida="Manter controle rigoroso. Avaliar se cortes são sustentáveis.",
                prioridade=3,
                dados_suporte={
                    'despesa_atual': despesa_atual,
                    'despesa_anterior': despesa_anterior
                }
            ))

        # Despesa vs orçamento
        if orcamento > 0 and despesa_atual > orcamento * 1.1:
            excesso = despesa_atual - orcamento
            insights.append(Insight(
                tipo=TipoInsight.ALERTA,
                categoria=CategoriaInsight.DESPESA,
                titulo="Orçamento estourado",
                descricao=f"Despesas {((despesa_atual/orcamento)-1)*100:.1f}% acima do orçado. "
                         f"Excesso de R$ {excesso:,.2f}.",
                valor_destaque=f"+R$ {excesso:,.2f}",
                variacao=((despesa_atual/orcamento)-1)*100,
                periodo_comparacao="orçamento",
                acao_sugerida="Identificar gastos não previstos e ajustar orçamento dos próximos meses.",
                prioridade=4,
                dados_suporte={
                    'despesa_atual': despesa_atual,
                    'orcamento': orcamento
                }
            ))

        # Detecta categoria com maior aumento
        categorias_atual = atual.get('despesas_por_categoria', {})
        categorias_anterior = anterior.get('despesas_por_categoria', {})

        maior_aumento = None
        maior_variacao = 0

        for cat, valor in categorias_atual.items():
            valor_ant = categorias_anterior.get(cat, 0)
            if valor_ant > 0:
                var = ((valor - valor_ant) / valor_ant) * 100
                if var > maior_variacao:
                    maior_variacao = var
                    maior_aumento = cat

        if maior_aumento and maior_variacao > 20:
            insights.append(Insight(
                tipo=TipoInsight.NEUTRO,
                categoria=CategoriaInsight.DESPESA,
                titulo=f"Destaque: {maior_aumento}",
                descricao=f"A categoria '{maior_aumento}' teve aumento de {maior_variacao:.1f}% "
                         f"em relação ao período anterior.",
                valor_destaque=f"+{maior_variacao:.1f}%",
                variacao=maior_variacao,
                periodo_comparacao="mês anterior",
                acao_sugerida=f"Verificar se aumento em '{maior_aumento}' é pontual ou tendência.",
                prioridade=2,
                dados_suporte={'categoria': maior_aumento, 'variacao': maior_variacao}
            ))

        return insights

    def _insights_fluxo_caixa(
        self,
        atual: Dict,
        anterior: Dict
    ) -> List[Insight]:
        """Gera insights sobre fluxo de caixa"""
        insights = []

        saldo_atual = atual.get('saldo_caixa', 0)
        saldo_anterior = anterior.get('saldo_caixa', 0)
        receita = atual.get('receita_total', 0)
        despesa = atual.get('despesa_total', 0)

        # Saldo negativo ou muito baixo
        if saldo_atual < 0:
            insights.append(Insight(
                tipo=TipoInsight.ALERTA,
                categoria=CategoriaInsight.FLUXO_CAIXA,
                titulo="ATENÇÃO: Saldo negativo",
                descricao=f"O caixa está negativo em R$ {abs(saldo_atual):,.2f}. "
                         f"Situação crítica que requer ação imediata.",
                valor_destaque=f"-R$ {abs(saldo_atual):,.2f}",
                variacao=None,
                periodo_comparacao=None,
                acao_sugerida="URGENTE: Acelerar recebimentos, postergar despesas não essenciais, avaliar empréstimo de curto prazo.",
                prioridade=5,
                dados_suporte={'saldo': saldo_atual}
            ))
        elif receita > 0 and saldo_atual < receita * 0.5:
            insights.append(Insight(
                tipo=TipoInsight.ALERTA,
                categoria=CategoriaInsight.FLUXO_CAIXA,
                titulo="Reserva de caixa baixa",
                descricao=f"O saldo de R$ {saldo_atual:,.2f} representa menos de 50% da receita mensal. "
                         f"Recomenda-se manter ao menos 1-2 meses de despesas em reserva.",
                valor_destaque=f"R$ {saldo_atual:,.2f}",
                variacao=None,
                periodo_comparacao=None,
                acao_sugerida="Considerar criar fundo de reserva com parte dos recebimentos.",
                prioridade=3,
                dados_suporte={'saldo': saldo_atual, 'receita': receita}
            ))

        # Fluxo positivo/negativo
        fluxo = receita - despesa
        if fluxo > 0:
            insights.append(Insight(
                tipo=TipoInsight.POSITIVO,
                categoria=CategoriaInsight.FLUXO_CAIXA,
                titulo="Fluxo de caixa positivo",
                descricao=f"Receitas superaram despesas em R$ {fluxo:,.2f}. "
                         f"Superávit pode ser destinado a fundo de reserva ou investimentos.",
                valor_destaque=f"+R$ {fluxo:,.2f}",
                variacao=None,
                periodo_comparacao=None,
                acao_sugerida="Avaliar aplicação do excedente em fundo de reserva ou investimento de curto prazo.",
                prioridade=2,
                dados_suporte={'fluxo': fluxo, 'receita': receita, 'despesa': despesa}
            ))
        elif fluxo < 0:
            insights.append(Insight(
                tipo=TipoInsight.NEGATIVO,
                categoria=CategoriaInsight.FLUXO_CAIXA,
                titulo="Fluxo de caixa negativo",
                descricao=f"Despesas superaram receitas em R$ {abs(fluxo):,.2f}. "
                         f"Situação que não pode se repetir sem comprometer a saúde financeira.",
                valor_destaque=f"-R$ {abs(fluxo):,.2f}",
                variacao=None,
                periodo_comparacao=None,
                acao_sugerida="Revisar despesas, acelerar cobrança de inadimplentes.",
                prioridade=4,
                dados_suporte={'fluxo': fluxo, 'receita': receita, 'despesa': despesa}
            ))

        return insights

    def _insights_cobranca(
        self,
        atual: Dict,
        anterior: Dict
    ) -> List[Insight]:
        """Gera insights sobre efetividade da cobrança"""
        insights = []

        taxa_recuperacao = atual.get('taxa_recuperacao', 0)
        taxa_anterior = anterior.get('taxa_recuperacao', 0)
        acordos_realizados = atual.get('acordos_realizados', 0)
        valor_recuperado = atual.get('valor_recuperado', 0)

        # Taxa de recuperação
        if taxa_recuperacao > taxa_anterior and taxa_anterior > 0:
            variacao = ((taxa_recuperacao - taxa_anterior) / taxa_anterior) * 100
            insights.append(Insight(
                tipo=TipoInsight.POSITIVO,
                categoria=CategoriaInsight.COBRANCA,
                titulo="Cobrança mais efetiva",
                descricao=f"A taxa de recuperação aumentou {variacao:.1f}%, "
                         f"indicando melhoria na estratégia de cobrança.",
                valor_destaque=f"{taxa_recuperacao:.1f}%",
                variacao=variacao,
                periodo_comparacao="mês anterior",
                acao_sugerida="Manter estratégia atual e identificar práticas de sucesso.",
                prioridade=3,
                dados_suporte={'taxa_atual': taxa_recuperacao, 'taxa_anterior': taxa_anterior}
            ))

        # Acordos realizados
        if acordos_realizados > 0:
            insights.append(Insight(
                tipo=TipoInsight.POSITIVO,
                categoria=CategoriaInsight.ACORDO,
                titulo=f"{acordos_realizados} acordo(s) realizado(s)",
                descricao=f"Foram fechados {acordos_realizados} acordos de pagamento, "
                         f"recuperando potencialmente R$ {valor_recuperado:,.2f}.",
                valor_destaque=f"R$ {valor_recuperado:,.2f}",
                variacao=None,
                periodo_comparacao=None,
                acao_sugerida="Acompanhar cumprimento dos acordos e oferecer proativamente a inadimplentes.",
                prioridade=3,
                dados_suporte={'acordos': acordos_realizados, 'valor': valor_recuperado}
            ))

        return insights

    def _insights_benchmark(
        self,
        atual: Dict,
        benchmarks: Dict
    ) -> List[Insight]:
        """Gera insights comparativos com benchmarks de mercado"""
        insights = []

        taxa_inadimpl = atual.get('taxa_inadimplencia', 0)
        benchmark_inadimpl = benchmarks.get('taxa_inadimplencia_media', 5.0)

        if taxa_inadimpl > benchmark_inadimpl * 1.5:
            insights.append(Insight(
                tipo=TipoInsight.NEGATIVO,
                categoria=CategoriaInsight.COMPARATIVO,
                titulo="Inadimplência acima do mercado",
                descricao=f"Sua taxa de {taxa_inadimpl:.1f}% está {((taxa_inadimpl/benchmark_inadimpl)-1)*100:.0f}% "
                         f"acima da média de condomínios similares ({benchmark_inadimpl:.1f}%).",
                valor_destaque=f"{taxa_inadimpl:.1f}%",
                variacao=((taxa_inadimpl/benchmark_inadimpl)-1)*100,
                periodo_comparacao="média do mercado",
                acao_sugerida="Analisar causas específicas e considerar consultoria especializada em cobrança.",
                prioridade=4,
                dados_suporte={'seu_valor': taxa_inadimpl, 'benchmark': benchmark_inadimpl}
            ))
        elif taxa_inadimpl < benchmark_inadimpl * 0.7:
            insights.append(Insight(
                tipo=TipoInsight.POSITIVO,
                categoria=CategoriaInsight.COMPARATIVO,
                titulo="Inadimplência abaixo do mercado",
                descricao=f"Parabéns! Sua taxa de {taxa_inadimpl:.1f}% está "
                         f"{((1-taxa_inadimpl/benchmark_inadimpl))*100:.0f}% abaixo da média do mercado.",
                valor_destaque=f"{taxa_inadimpl:.1f}%",
                variacao=-((1-taxa_inadimpl/benchmark_inadimpl))*100,
                periodo_comparacao="média do mercado",
                acao_sugerida="Excelente gestão! Considerar compartilhar práticas de sucesso.",
                prioridade=2,
                dados_suporte={'seu_valor': taxa_inadimpl, 'benchmark': benchmark_inadimpl}
            ))

        return insights

    def _insights_tendencia(
        self,
        atual: Dict,
        anterior: Dict
    ) -> List[Insight]:
        """Gera insights sobre tendências"""
        insights = []

        # Tendência de inadimplência (últimos 3 meses)
        historico_inadimpl = atual.get('historico_inadimplencia', [])
        if len(historico_inadimpl) >= 3:
            tendencia = self._calcular_tendencia(historico_inadimpl[-3:])
            if tendencia > 0.5:
                insights.append(Insight(
                    tipo=TipoInsight.TENDENCIA,
                    categoria=CategoriaInsight.INADIMPLENCIA,
                    titulo="Tendência de alta na inadimplência",
                    descricao="Os últimos 3 meses mostram tendência de aumento na inadimplência. "
                             "Ação preventiva recomendada.",
                    valor_destaque="Tendência ↑",
                    variacao=None,
                    periodo_comparacao="últimos 3 meses",
                    acao_sugerida="Implementar cobrança preventiva antes do vencimento.",
                    prioridade=4,
                    dados_suporte={'historico': historico_inadimpl[-3:]}
                ))
            elif tendencia < -0.5:
                insights.append(Insight(
                    tipo=TipoInsight.TENDENCIA,
                    categoria=CategoriaInsight.INADIMPLENCIA,
                    titulo="Tendência de queda na inadimplência",
                    descricao="Os últimos 3 meses mostram melhoria consistente na inadimplência. "
                             "A estratégia está funcionando!",
                    valor_destaque="Tendência ↓",
                    variacao=None,
                    periodo_comparacao="últimos 3 meses",
                    acao_sugerida="Manter estratégia atual de gestão financeira.",
                    prioridade=2,
                    dados_suporte={'historico': historico_inadimpl[-3:]}
                ))

        return insights

    def _calcular_tendencia(self, valores: List[float]) -> float:
        """Calcula tendência usando regressão linear simplificada"""
        if len(valores) < 2:
            return 0

        n = len(valores)
        x_mean = (n - 1) / 2
        y_mean = sum(valores) / n

        numerador = sum((i - x_mean) * (valores[i] - y_mean) for i in range(n))
        denominador = sum((i - x_mean) ** 2 for i in range(n))

        if denominador == 0:
            return 0

        return numerador / denominador


# ==================== DASHBOARD BUILDER ====================

class DashboardBuilder:
    """
    Constrói dashboard completo com dados e insights
    """

    def __init__(self):
        self.gerador_insights = GeradorInsights()

    def construir(
        self,
        dados_financeiros: Dict[str, Any],
        dados_periodo_anterior: Dict[str, Any],
        alertas: List[Dict] = None,
        benchmarks: Dict[str, Any] = None
    ) -> DashboardCompleto:
        """
        Constrói dashboard completo

        Args:
            dados_financeiros: Dados do período atual
            dados_periodo_anterior: Dados do período anterior
            alertas: Lista de alertas ativos
            benchmarks: Benchmarks de comparação

        Returns:
            DashboardCompleto com todos os dados
        """
        # Gera insights
        insights = self.gerador_insights.gerar_insights(
            dados_financeiros,
            dados_periodo_anterior,
            benchmarks
        )

        # Calcula indicadores chave
        indicadores = self._calcular_indicadores(dados_financeiros, dados_periodo_anterior)

        # Prepara dados para gráficos
        graficos = self._preparar_graficos(dados_financeiros)

        # Gera ações recomendadas
        acoes = self._gerar_acoes_recomendadas(insights, dados_financeiros)

        # Calcula saúde financeira
        saude = self._calcular_saude_financeira(dados_financeiros)

        return DashboardCompleto(
            periodo=dados_financeiros.get('periodo', datetime.now().strftime('%m/%Y')),
            resumo_financeiro={
                'receita_total': dados_financeiros.get('receita_total', 0),
                'despesa_total': dados_financeiros.get('despesa_total', 0),
                'saldo': dados_financeiros.get('receita_total', 0) - dados_financeiros.get('despesa_total', 0),
                'saldo_caixa': dados_financeiros.get('saldo_caixa', 0),
                'inadimplencia': dados_financeiros.get('taxa_inadimplencia', 0)
            },
            indicadores_chave=indicadores,
            insights=[asdict(i) for i in insights],
            alertas_ativos=alertas or [],
            graficos_dados=graficos,
            acoes_recomendadas=acoes,
            saude_financeira=saude
        )

    def _calcular_indicadores(
        self,
        atual: Dict,
        anterior: Dict
    ) -> List[Dict[str, Any]]:
        """Calcula indicadores chave (KPIs)"""
        indicadores = []

        # Taxa de adimplência
        taxa_adimpl = 100 - atual.get('taxa_inadimplencia', 0)
        taxa_ant = 100 - anterior.get('taxa_inadimplencia', 0)
        indicadores.append({
            'nome': 'Taxa de Adimplência',
            'valor': f"{taxa_adimpl:.1f}%",
            'variacao': taxa_adimpl - taxa_ant,
            'status': 'positivo' if taxa_adimpl >= taxa_ant else 'negativo',
            'meta': 95,
            'icone': 'check-circle'
        })

        # Receita vs Orçado
        receita = atual.get('receita_total', 0)
        orcado = atual.get('receita_prevista', receita)
        atingimento = (receita / orcado * 100) if orcado > 0 else 100
        indicadores.append({
            'nome': 'Receita vs Meta',
            'valor': f"{atingimento:.1f}%",
            'variacao': atingimento - 100,
            'status': 'positivo' if atingimento >= 95 else ('neutro' if atingimento >= 85 else 'negativo'),
            'meta': 100,
            'icone': 'trending-up'
        })

        # Despesa vs Orçamento
        despesa = atual.get('despesa_total', 0)
        orcamento = atual.get('despesa_orcada', despesa)
        utilizacao = (despesa / orcamento * 100) if orcamento > 0 else 100
        indicadores.append({
            'nome': 'Despesa vs Orçamento',
            'valor': f"{utilizacao:.1f}%",
            'variacao': utilizacao - 100,
            'status': 'positivo' if utilizacao <= 100 else 'negativo',
            'meta': 100,
            'icone': 'dollar-sign'
        })

        # Saldo de Caixa
        saldo = atual.get('saldo_caixa', 0)
        indicadores.append({
            'nome': 'Saldo em Caixa',
            'valor': f"R$ {saldo:,.2f}",
            'variacao': saldo - anterior.get('saldo_caixa', 0),
            'status': 'positivo' if saldo > 0 else 'negativo',
            'meta': None,
            'icone': 'wallet'
        })

        return indicadores

    def _preparar_graficos(self, dados: Dict) -> Dict[str, List[Dict]]:
        """Prepara dados para gráficos"""
        return {
            'receita_mensal': dados.get('historico_receita', []),
            'despesa_mensal': dados.get('historico_despesa', []),
            'inadimplencia_mensal': dados.get('historico_inadimplencia', []),
            'despesas_por_categoria': dados.get('despesas_por_categoria', {}),
            'status_boletos': dados.get('boletos_por_status', {})
        }

    def _gerar_acoes_recomendadas(
        self,
        insights: List[Insight],
        dados: Dict
    ) -> List[Dict[str, Any]]:
        """Gera lista de ações recomendadas baseado nos insights"""
        acoes = []

        for insight in insights[:5]:  # Top 5 insights
            if insight.acao_sugerida:
                acoes.append({
                    'acao': insight.acao_sugerida,
                    'prioridade': insight.prioridade,
                    'categoria': insight.categoria.value,
                    'origem': insight.titulo
                })

        # Remove duplicatas mantendo maior prioridade
        acoes_unicas = {}
        for acao in acoes:
            key = acao['acao'][:50]
            if key not in acoes_unicas or acoes_unicas[key]['prioridade'] < acao['prioridade']:
                acoes_unicas[key] = acao

        return sorted(acoes_unicas.values(), key=lambda x: x['prioridade'], reverse=True)

    def _calcular_saude_financeira(self, dados: Dict) -> Dict[str, Any]:
        """Calcula score de saúde financeira geral"""

        # Componentes do score
        componentes = []

        # 1. Inadimplência (peso 30%)
        inadimpl = dados.get('taxa_inadimplencia', 0)
        score_inadimpl = max(0, 100 - inadimpl * 5)  # 0% = 100, 20% = 0
        componentes.append(('Inadimplência', score_inadimpl, 0.30))

        # 2. Fluxo de caixa (peso 25%)
        receita = dados.get('receita_total', 1)
        despesa = dados.get('despesa_total', 0)
        margem = ((receita - despesa) / receita * 100) if receita > 0 else 0
        score_fluxo = max(0, min(100, 50 + margem * 2))
        componentes.append(('Fluxo de Caixa', score_fluxo, 0.25))

        # 3. Reserva (peso 20%)
        saldo = dados.get('saldo_caixa', 0)
        meses_reserva = saldo / despesa if despesa > 0 else 0
        score_reserva = min(100, meses_reserva * 50)  # 2 meses = 100%
        componentes.append(('Reserva', score_reserva, 0.20))

        # 4. Atingimento de metas (peso 15%)
        receita_meta = dados.get('receita_prevista', receita)
        atingimento = (receita / receita_meta * 100) if receita_meta > 0 else 100
        score_metas = min(100, atingimento)
        componentes.append(('Metas', score_metas, 0.15))

        # 5. Tendência (peso 10%)
        historico = dados.get('historico_inadimplencia', [])
        if len(historico) >= 3:
            tendencia = (historico[-3] - historico[-1]) / historico[-3] if historico[-3] > 0 else 0
            score_tendencia = 50 + tendencia * 50
        else:
            score_tendencia = 50
        componentes.append(('Tendência', score_tendencia, 0.10))

        # Score final
        score_final = sum(score * peso for _, score, peso in componentes)

        # Classificação
        if score_final >= 80:
            classificacao = "Excelente"
            cor = "green"
        elif score_final >= 60:
            classificacao = "Boa"
            cor = "blue"
        elif score_final >= 40:
            classificacao = "Regular"
            cor = "yellow"
        else:
            classificacao = "Crítica"
            cor = "red"

        return {
            'score': round(score_final, 1),
            'classificacao': classificacao,
            'cor': cor,
            'componentes': [
                {'nome': nome, 'score': round(score, 1), 'peso': f"{peso*100:.0f}%"}
                for nome, score, peso in componentes
            ]
        }


# ==================== INSTÂNCIAS GLOBAIS ====================

gerador_insights = GeradorInsights()
dashboard_builder = DashboardBuilder()
