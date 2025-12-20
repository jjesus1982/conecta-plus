"""
Conecta Plus - ML Engine
Motor de Machine Learning para previsões e análises avançadas
"""

import os
import json
import hashlib
import pickle
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import math

# ML Libraries (graceful fallback se não disponíveis)
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

try:
    from sklearn.ensemble import IsolationForest, RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


# ==================== CONFIGURAÇÃO ====================

class ModeloTipo(str, Enum):
    """Tipos de modelo disponíveis"""
    INADIMPLENCIA = "inadimplencia"
    FLUXO_CAIXA = "fluxo_caixa"
    ANOMALIA = "anomalia"
    SEGMENTACAO = "segmentacao"
    PRIORIDADE = "prioridade"


@dataclass
class PrevisaoInadimplencia:
    """Resultado de previsão de inadimplência"""
    unidade_id: str
    probabilidade: float
    classificacao: str  # baixo, medio, alto, critico
    score: int  # 0-1000
    fatores_risco: List[Dict[str, Any]]
    recomendacao: str
    confianca: float
    modelo_versao: str


@dataclass
class PrevisaoFluxoCaixa:
    """Resultado de previsão de fluxo de caixa"""
    data: str
    receita_prevista: float
    despesa_prevista: float
    saldo_previsto: float
    intervalo_inferior: float
    intervalo_superior: float
    confianca: float
    sazonalidade: str  # alta, normal, baixa
    tendencia: str  # crescente, estavel, decrescente


@dataclass
class AlertaProativo:
    """Alerta gerado proativamente pelo sistema"""
    tipo: str
    severidade: str  # info, warning, critical
    titulo: str
    mensagem: str
    entidade_tipo: str
    entidade_id: str
    data_prevista: Optional[str]
    acao_recomendada: str
    probabilidade: float
    criado_em: str


@dataclass
class SegmentoCliente:
    """Segmento de cliente identificado"""
    segmento_id: int
    nome: str
    descricao: str
    caracteristicas: Dict[str, Any]
    tamanho: int
    estrategia_recomendada: str


# ==================== FEATURE ENGINEERING ====================

class FeatureEngineering:
    """
    Engenharia de features avançada para modelos de ML
    """

    @staticmethod
    def calcular_features_pagador(
        historico_boletos: List[Dict],
        historico_pagamentos: List[Dict],
        acordos: List[Dict],
        dados_unidade: Dict
    ) -> Dict[str, float]:
        """
        Calcula features avançadas do pagador

        Returns:
            Dict com 40+ features para o modelo
        """
        features = {}

        # ============ FEATURES BÁSICAS ============
        total_boletos = len(historico_boletos)
        features['total_boletos'] = total_boletos

        if total_boletos == 0:
            # Retorna features zeradas para novos clientes
            return FeatureEngineering._features_novo_cliente()

        # Status dos boletos
        pagos = [b for b in historico_boletos if b.get('status') == 'pago']
        vencidos = [b for b in historico_boletos if b.get('status') == 'vencido']
        pendentes = [b for b in historico_boletos if b.get('status') == 'pendente']

        features['boletos_pagos'] = len(pagos)
        features['boletos_vencidos'] = len(vencidos)
        features['boletos_pendentes'] = len(pendentes)
        features['taxa_adimplencia'] = len(pagos) / total_boletos if total_boletos > 0 else 0

        # ============ FEATURES DE VALOR ============
        valores = [b.get('valor', 0) for b in historico_boletos]
        features['valor_medio_boleto'] = sum(valores) / len(valores) if valores else 0
        features['valor_total_historico'] = sum(valores)
        features['valor_max_boleto'] = max(valores) if valores else 0
        features['valor_min_boleto'] = min(valores) if valores else 0

        # Valor em aberto
        valor_vencido = sum(b.get('valor', 0) for b in vencidos)
        valor_pendente = sum(b.get('valor', 0) for b in pendentes)
        features['valor_em_aberto'] = valor_vencido + valor_pendente
        features['valor_vencido'] = valor_vencido

        # ============ FEATURES TEMPORAIS ============
        # Dias de atraso
        atrasos = []
        for boleto in historico_boletos:
            if boleto.get('status') == 'pago' and boleto.get('data_pagamento') and boleto.get('vencimento'):
                try:
                    venc = datetime.strptime(str(boleto['vencimento'])[:10], '%Y-%m-%d').date()
                    pag = datetime.strptime(str(boleto['data_pagamento'])[:10], '%Y-%m-%d').date()
                    atraso = (pag - venc).days
                    if atraso > 0:
                        atrasos.append(atraso)
                except:
                    pass

        features['media_dias_atraso'] = sum(atrasos) / len(atrasos) if atrasos else 0
        features['max_dias_atraso'] = max(atrasos) if atrasos else 0
        features['frequencia_atraso'] = len(atrasos) / len(pagos) if pagos else 0

        # Variabilidade de atraso (desvio padrão)
        if len(atrasos) > 1 and HAS_NUMPY:
            features['volatilidade_atraso'] = float(np.std(atrasos))
        else:
            features['volatilidade_atraso'] = 0

        # ============ FEATURES DE TENDÊNCIA ============
        # Últimos 6 meses vs período anterior
        hoje = date.today()
        seis_meses_atras = hoje - timedelta(days=180)

        boletos_recentes = [b for b in historico_boletos
                          if FeatureEngineering._parse_date(b.get('vencimento'))
                          and FeatureEngineering._parse_date(b.get('vencimento')) >= seis_meses_atras]
        boletos_antigos = [b for b in historico_boletos
                         if FeatureEngineering._parse_date(b.get('vencimento'))
                         and FeatureEngineering._parse_date(b.get('vencimento')) < seis_meses_atras]

        taxa_recente = len([b for b in boletos_recentes if b.get('status') == 'pago']) / len(boletos_recentes) if boletos_recentes else 0
        taxa_antiga = len([b for b in boletos_antigos if b.get('status') == 'pago']) / len(boletos_antigos) if boletos_antigos else 0

        features['tendencia_pagamento'] = taxa_recente - taxa_antiga  # positivo = melhorando
        features['aceleracao_atraso'] = FeatureEngineering._calcular_aceleracao(atrasos)

        # ============ FEATURES DE COMPORTAMENTO ============
        # Padrão de dia do mês de pagamento
        dias_pagamento = []
        for pag in historico_pagamentos:
            try:
                data = datetime.strptime(str(pag.get('data_pagamento'))[:10], '%Y-%m-%d')
                dias_pagamento.append(data.day)
            except:
                pass

        features['dia_medio_pagamento'] = sum(dias_pagamento) / len(dias_pagamento) if dias_pagamento else 15
        features['consistencia_dia_pagamento'] = 1 - (FeatureEngineering._std(dias_pagamento) / 15) if dias_pagamento else 0

        # Padrão de forma de pagamento
        formas = [p.get('forma_pagamento', 'unknown') for p in historico_pagamentos]
        features['usa_pix'] = 1 if 'pix' in formas else 0
        features['usa_boleto'] = 1 if 'boleto' in formas else 0
        features['diversidade_pagamento'] = len(set(formas)) / len(formas) if formas else 0

        # ============ FEATURES DE ACORDOS ============
        features['total_acordos'] = len(acordos)
        acordos_cumpridos = len([a for a in acordos if a.get('status') == 'quitado'])
        acordos_quebrados = len([a for a in acordos if a.get('status') == 'quebrado'])
        features['acordos_cumpridos'] = acordos_cumpridos
        features['acordos_quebrados'] = acordos_quebrados
        features['taxa_cumprimento_acordo'] = acordos_cumpridos / len(acordos) if acordos else 1.0

        # ============ FEATURES SAZONAIS ============
        mes_atual = hoje.month
        features['mes_atual'] = mes_atual
        features['trimestre'] = (mes_atual - 1) // 3 + 1
        features['fim_de_ano'] = 1 if mes_atual in [11, 12, 1] else 0  # maior inadimplência
        features['inicio_ano'] = 1 if mes_atual in [1, 2, 3] else 0  # IPTU, material escolar

        # ============ FEATURES DE UNIDADE ============
        features['bloco_numerico'] = ord(dados_unidade.get('bloco', 'A')[0]) - ord('A') + 1
        features['andar'] = int(dados_unidade.get('numero', '101')[:1]) if dados_unidade.get('numero') else 1

        # ============ FEATURES CALCULADAS ============
        # Score de risco composto
        features['score_risco_composto'] = (
            features['taxa_adimplencia'] * 0.3 +
            (1 - min(features['media_dias_atraso'] / 30, 1)) * 0.2 +
            features['taxa_cumprimento_acordo'] * 0.2 +
            (1 - min(features['valor_vencido'] / 10000, 1)) * 0.15 +
            features['consistencia_dia_pagamento'] * 0.15
        )

        # Índice de estabilidade
        features['indice_estabilidade'] = (
            features['consistencia_dia_pagamento'] * 0.4 +
            (1 - features['volatilidade_atraso'] / 30 if features['volatilidade_atraso'] < 30 else 0) * 0.3 +
            (1 - features['diversidade_pagamento']) * 0.3
        )

        return features

    @staticmethod
    def _features_novo_cliente() -> Dict[str, float]:
        """Features padrão para cliente sem histórico"""
        return {
            'total_boletos': 0,
            'boletos_pagos': 0,
            'boletos_vencidos': 0,
            'boletos_pendentes': 0,
            'taxa_adimplencia': 0.5,  # neutro
            'valor_medio_boleto': 0,
            'valor_total_historico': 0,
            'valor_max_boleto': 0,
            'valor_min_boleto': 0,
            'valor_em_aberto': 0,
            'valor_vencido': 0,
            'media_dias_atraso': 0,
            'max_dias_atraso': 0,
            'frequencia_atraso': 0,
            'volatilidade_atraso': 0,
            'tendencia_pagamento': 0,
            'aceleracao_atraso': 0,
            'dia_medio_pagamento': 15,
            'consistencia_dia_pagamento': 0.5,
            'usa_pix': 0,
            'usa_boleto': 0,
            'diversidade_pagamento': 0,
            'total_acordos': 0,
            'acordos_cumpridos': 0,
            'acordos_quebrados': 0,
            'taxa_cumprimento_acordo': 1.0,
            'mes_atual': date.today().month,
            'trimestre': (date.today().month - 1) // 3 + 1,
            'fim_de_ano': 1 if date.today().month in [11, 12, 1] else 0,
            'inicio_ano': 1 if date.today().month in [1, 2, 3] else 0,
            'bloco_numerico': 1,
            'andar': 1,
            'score_risco_composto': 0.5,
            'indice_estabilidade': 0.5
        }

    @staticmethod
    def _parse_date(date_str: Any) -> Optional[date]:
        """Parse de data seguro"""
        if not date_str:
            return None
        try:
            return datetime.strptime(str(date_str)[:10], '%Y-%m-%d').date()
        except:
            return None

    @staticmethod
    def _std(values: List[float]) -> float:
        """Desvio padrão sem numpy"""
        if len(values) < 2:
            return 0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return math.sqrt(variance)

    @staticmethod
    def _calcular_aceleracao(atrasos: List[int]) -> float:
        """Calcula aceleração do atraso (tendência de piora)"""
        if len(atrasos) < 3:
            return 0

        # Divide em primeira e segunda metade
        meio = len(atrasos) // 2
        primeira_metade = sum(atrasos[:meio]) / meio if meio > 0 else 0
        segunda_metade = sum(atrasos[meio:]) / (len(atrasos) - meio) if len(atrasos) - meio > 0 else 0

        # Aceleração = diferença normalizada
        if primeira_metade > 0:
            return (segunda_metade - primeira_metade) / primeira_metade
        return 0


# ==================== MODELO DE INADIMPLÊNCIA ====================

class ModeloInadimplenciaML:
    """
    Modelo de ML para previsão de inadimplência

    Usa ensemble de regras + scoring para ambientes sem sklearn,
    ou RandomForest/XGBoost quando disponível.
    """

    VERSAO = "2.0.0"

    def __init__(self):
        self.feature_engineering = FeatureEngineering()
        self.modelo = None
        self.scaler = None

        if HAS_SKLEARN:
            self._init_sklearn_model()

    def _init_sklearn_model(self):
        """Inicializa modelo sklearn se disponível"""
        self.scaler = StandardScaler()
        self.modelo = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42
        )

    def prever(
        self,
        historico_boletos: List[Dict],
        historico_pagamentos: List[Dict],
        acordos: List[Dict],
        dados_unidade: Dict
    ) -> PrevisaoInadimplencia:
        """
        Prevê probabilidade de inadimplência

        Returns:
            PrevisaoInadimplencia com detalhes
        """
        # Calcula features
        features = self.feature_engineering.calcular_features_pagador(
            historico_boletos, historico_pagamentos, acordos, dados_unidade
        )

        # Calcula probabilidade usando ensemble de regras
        prob, fatores = self._calcular_probabilidade(features)

        # Classifica
        if prob < 0.15:
            classificacao = "baixo"
        elif prob < 0.35:
            classificacao = "medio"
        elif prob < 0.60:
            classificacao = "alto"
        else:
            classificacao = "critico"

        # Score 0-1000
        score = int((1 - prob) * 1000)

        # Recomendação baseada na classificação
        recomendacao = self._gerar_recomendacao(classificacao, fatores, features)

        return PrevisaoInadimplencia(
            unidade_id=dados_unidade.get('id', 'unknown'),
            probabilidade=round(prob, 4),
            classificacao=classificacao,
            score=score,
            fatores_risco=fatores,
            recomendacao=recomendacao,
            confianca=self._calcular_confianca(features),
            modelo_versao=self.VERSAO
        )

    def _calcular_probabilidade(self, features: Dict[str, float]) -> Tuple[float, List[Dict]]:
        """
        Calcula probabilidade usando ensemble de regras ponderadas
        """
        fatores = []
        prob_total = 0.0
        peso_total = 0.0

        # Regra 1: Taxa de adimplência histórica (peso 25%)
        taxa_adimpl = features.get('taxa_adimplencia', 0.5)
        prob_r1 = 1 - taxa_adimpl
        peso_r1 = 0.25
        prob_total += prob_r1 * peso_r1
        peso_total += peso_r1
        if prob_r1 > 0.3:
            fatores.append({
                'fator': 'historico_pagamento',
                'impacto': round(prob_r1, 2),
                'descricao': f'Taxa de adimplência de {taxa_adimpl:.1%}'
            })

        # Regra 2: Média de dias de atraso (peso 20%)
        media_atraso = features.get('media_dias_atraso', 0)
        prob_r2 = min(media_atraso / 60, 1.0)  # normaliza para 60 dias
        peso_r2 = 0.20
        prob_total += prob_r2 * peso_r2
        peso_total += peso_r2
        if media_atraso > 10:
            fatores.append({
                'fator': 'media_atraso',
                'impacto': round(prob_r2, 2),
                'descricao': f'Média de {media_atraso:.0f} dias de atraso'
            })

        # Regra 3: Valor em aberto (peso 15%)
        valor_aberto = features.get('valor_em_aberto', 0)
        prob_r3 = min(valor_aberto / 10000, 1.0)  # normaliza para R$ 10.000
        peso_r3 = 0.15
        prob_total += prob_r3 * peso_r3
        peso_total += peso_r3
        if valor_aberto > 1000:
            fatores.append({
                'fator': 'valor_em_aberto',
                'impacto': round(prob_r3, 2),
                'descricao': f'R$ {valor_aberto:,.2f} em aberto'
            })

        # Regra 4: Tendência de pagamento (peso 15%)
        tendencia = features.get('tendencia_pagamento', 0)
        prob_r4 = max(0, -tendencia)  # negativo = piorando
        peso_r4 = 0.15
        prob_total += prob_r4 * peso_r4
        peso_total += peso_r4
        if tendencia < -0.1:
            fatores.append({
                'fator': 'tendencia_piora',
                'impacto': round(prob_r4, 2),
                'descricao': 'Comportamento piorando nos últimos meses'
            })

        # Regra 5: Acordos quebrados (peso 10%)
        acordos_quebrados = features.get('acordos_quebrados', 0)
        total_acordos = features.get('total_acordos', 0)
        prob_r5 = acordos_quebrados / max(total_acordos, 1)
        peso_r5 = 0.10
        prob_total += prob_r5 * peso_r5
        peso_total += peso_r5
        if acordos_quebrados > 0:
            fatores.append({
                'fator': 'acordos_quebrados',
                'impacto': round(prob_r5, 2),
                'descricao': f'{acordos_quebrados} acordo(s) não cumprido(s)'
            })

        # Regra 6: Sazonalidade (peso 10%)
        fim_ano = features.get('fim_de_ano', 0)
        inicio_ano = features.get('inicio_ano', 0)
        prob_r6 = 0.3 if fim_ano else (0.2 if inicio_ano else 0)
        peso_r6 = 0.10
        prob_total += prob_r6 * peso_r6
        peso_total += peso_r6
        if fim_ano or inicio_ano:
            fatores.append({
                'fator': 'sazonalidade',
                'impacto': round(prob_r6, 2),
                'descricao': 'Período de maior inadimplência histórica'
            })

        # Regra 7: Volatilidade (peso 5%)
        volatilidade = features.get('volatilidade_atraso', 0)
        prob_r7 = min(volatilidade / 20, 1.0)
        peso_r7 = 0.05
        prob_total += prob_r7 * peso_r7
        peso_total += peso_r7
        if volatilidade > 10:
            fatores.append({
                'fator': 'comportamento_irregular',
                'impacto': round(prob_r7, 2),
                'descricao': 'Padrão de pagamento imprevisível'
            })

        # Normaliza probabilidade final
        prob_final = prob_total / peso_total if peso_total > 0 else 0.5

        # Aplica ajuste para novos clientes (mais conservador)
        if features.get('total_boletos', 0) < 3:
            prob_final = prob_final * 0.7 + 0.15  # puxa para 15% (incerteza)

        return min(max(prob_final, 0.01), 0.99), fatores

    def _gerar_recomendacao(
        self,
        classificacao: str,
        fatores: List[Dict],
        features: Dict[str, float]
    ) -> str:
        """Gera recomendação personalizada"""

        if classificacao == "baixo":
            return "Cliente com excelente histórico. Manter comunicação positiva e oferecer benefícios de fidelidade."

        elif classificacao == "medio":
            # Identifica principal fator
            if features.get('tendencia_pagamento', 0) < -0.1:
                return "Comportamento piorando. Contato preventivo recomendado para entender situação."
            elif features.get('media_dias_atraso', 0) > 15:
                return "Atrasos frequentes mas pagamentos realizados. Considerar débito automático ou desconto para antecipação."
            else:
                return "Risco moderado. Monitorar de perto e enviar lembretes antes do vencimento."

        elif classificacao == "alto":
            if features.get('acordos_quebrados', 0) > 0:
                return "Histórico de acordos não cumpridos. Exigir entrada maior ou garantias adicionais em nova negociação."
            elif features.get('valor_em_aberto', 0) > 3000:
                return "Dívida acumulada significativa. Priorizar contato pessoal para negociação. Considerar cobrança extrajudicial."
            else:
                return "Alto risco de inadimplência. Intensificar cobrança e preparar ação judicial se necessário."

        else:  # crítico
            if features.get('valor_em_aberto', 0) > 5000:
                return "AÇÃO URGENTE: Dívida crítica. Iniciar processo de cobrança judicial. Considerar negativação."
            else:
                return "AÇÃO URGENTE: Risco de perda iminente. Última tentativa de acordo com condições especiais ou encaminhar para jurídico."

    def _calcular_confianca(self, features: Dict[str, float]) -> float:
        """Calcula confiança da previsão baseado na quantidade de dados"""
        total_boletos = features.get('total_boletos', 0)

        if total_boletos == 0:
            return 0.3  # baixa confiança para novos
        elif total_boletos < 3:
            return 0.5
        elif total_boletos < 6:
            return 0.7
        elif total_boletos < 12:
            return 0.85
        else:
            return 0.95


# ==================== PREVISÃO DE FLUXO DE CAIXA ====================

class PrevisaoFluxoCaixaML:
    """
    Modelo para previsão de fluxo de caixa usando decomposição temporal
    """

    VERSAO = "2.0.0"

    def __init__(self):
        self.historico_cache = {}

    def prever(
        self,
        historico_receitas: List[Dict],
        historico_despesas: List[Dict],
        boletos_pendentes: List[Dict],
        dias_previsao: int = 90
    ) -> List[PrevisaoFluxoCaixa]:
        """
        Prevê fluxo de caixa para os próximos N dias

        Returns:
            Lista de PrevisaoFluxoCaixa por período
        """
        previsoes = []
        hoje = date.today()

        # Calcula médias e tendências históricas
        stats = self._calcular_estatisticas(historico_receitas, historico_despesas)

        # Agrupa boletos pendentes por data
        boletos_por_data = {}
        for boleto in boletos_pendentes:
            venc = boleto.get('vencimento', str(hoje))[:10]
            if venc not in boletos_por_data:
                boletos_por_data[venc] = []
            boletos_por_data[venc].append(boleto)

        # Gera previsão para cada semana
        for semana in range(dias_previsao // 7 + 1):
            data_inicio = hoje + timedelta(days=semana * 7)
            data_fim = data_inicio + timedelta(days=6)

            # Calcula receita prevista
            receita = self._prever_receita_periodo(
                data_inicio, data_fim, stats, boletos_por_data
            )

            # Calcula despesa prevista
            despesa = self._prever_despesa_periodo(
                data_inicio, data_fim, stats
            )

            # Intervalo de confiança (±15%)
            margem = 0.15

            previsao = PrevisaoFluxoCaixa(
                data=data_inicio.isoformat(),
                receita_prevista=round(receita, 2),
                despesa_prevista=round(despesa, 2),
                saldo_previsto=round(receita - despesa, 2),
                intervalo_inferior=round((receita - despesa) * (1 - margem), 2),
                intervalo_superior=round((receita - despesa) * (1 + margem), 2),
                confianca=self._calcular_confianca_periodo(semana),
                sazonalidade=self._identificar_sazonalidade(data_inicio.month),
                tendencia=self._identificar_tendencia(stats)
            )
            previsoes.append(previsao)

        return previsoes

    def _calcular_estatisticas(
        self,
        receitas: List[Dict],
        despesas: List[Dict]
    ) -> Dict[str, Any]:
        """Calcula estatísticas históricas"""

        # Receitas por mês
        receitas_por_mes = {}
        for r in receitas:
            try:
                data = datetime.strptime(str(r.get('data', ''))[:10], '%Y-%m-%d')
                mes = data.strftime('%Y-%m')
                if mes not in receitas_por_mes:
                    receitas_por_mes[mes] = 0
                receitas_por_mes[mes] += r.get('valor', 0)
            except:
                pass

        # Despesas por mês
        despesas_por_mes = {}
        for d in despesas:
            try:
                data = datetime.strptime(str(d.get('data', ''))[:10], '%Y-%m-%d')
                mes = data.strftime('%Y-%m')
                if mes not in despesas_por_mes:
                    despesas_por_mes[mes] = 0
                despesas_por_mes[mes] += d.get('valor', 0)
            except:
                pass

        # Médias
        media_receita = sum(receitas_por_mes.values()) / len(receitas_por_mes) if receitas_por_mes else 50000
        media_despesa = sum(despesas_por_mes.values()) / len(despesas_por_mes) if despesas_por_mes else 40000

        # Tendência (últimos 3 meses vs 3 anteriores)
        meses_ordenados = sorted(receitas_por_mes.keys())
        if len(meses_ordenados) >= 6:
            recentes = sum(receitas_por_mes[m] for m in meses_ordenados[-3:]) / 3
            antigos = sum(receitas_por_mes[m] for m in meses_ordenados[-6:-3]) / 3
            tendencia_receita = (recentes - antigos) / antigos if antigos > 0 else 0
        else:
            tendencia_receita = 0

        return {
            'media_receita_mensal': media_receita,
            'media_despesa_mensal': media_despesa,
            'tendencia_receita': tendencia_receita,
            'receitas_por_mes': receitas_por_mes,
            'despesas_por_mes': despesas_por_mes
        }

    def _prever_receita_periodo(
        self,
        data_inicio: date,
        data_fim: date,
        stats: Dict,
        boletos_por_data: Dict
    ) -> float:
        """Prevê receita para um período específico"""

        # Base: média semanal
        media_semanal = stats['media_receita_mensal'] / 4

        # Ajuste por boletos pendentes no período
        receita_boletos = 0
        for data_str, boletos in boletos_por_data.items():
            try:
                data_boleto = datetime.strptime(data_str, '%Y-%m-%d').date()
                if data_inicio <= data_boleto <= data_fim:
                    for boleto in boletos:
                        # Aplica taxa de conversão esperada (baseado em status)
                        valor = boleto.get('valor', 0)
                        if boleto.get('status') == 'pendente':
                            receita_boletos += valor * 0.85  # 85% de conversão esperada
                        elif boleto.get('status') == 'vencido':
                            receita_boletos += valor * 0.40  # 40% de conversão para vencidos
            except:
                pass

        # Se tem boletos no período, usa esse valor; senão usa média
        if receita_boletos > 0:
            return receita_boletos
        else:
            return media_semanal

    def _prever_despesa_periodo(
        self,
        data_inicio: date,
        data_fim: date,
        stats: Dict
    ) -> float:
        """Prevê despesa para um período específico"""

        # Base: média semanal
        media_semanal = stats['media_despesa_mensal'] / 4

        # Ajuste sazonal
        mes = data_inicio.month
        if mes in [12, 1]:  # 13º, férias
            media_semanal *= 1.20
        elif mes in [7]:  # manutenção de férias
            media_semanal *= 1.10

        return media_semanal

    def _calcular_confianca_periodo(self, semanas_futuro: int) -> float:
        """Confiança diminui com o tempo"""
        return max(0.5, 0.95 - (semanas_futuro * 0.03))

    def _identificar_sazonalidade(self, mes: int) -> str:
        """Identifica sazonalidade do período"""
        if mes in [12, 1, 7]:
            return "alta"
        elif mes in [2, 3, 11]:
            return "normal"
        else:
            return "baixa"

    def _identificar_tendencia(self, stats: Dict) -> str:
        """Identifica tendência geral"""
        tendencia = stats.get('tendencia_receita', 0)
        if tendencia > 0.05:
            return "crescente"
        elif tendencia < -0.05:
            return "decrescente"
        else:
            return "estavel"


# ==================== SISTEMA DE ALERTAS PROATIVOS ====================

class SistemaAlertasProativos:
    """
    Gera alertas proativos baseado em análise preditiva
    """

    def __init__(self):
        self.modelo_inadimplencia = ModeloInadimplenciaML()
        self.modelo_fluxo = PrevisaoFluxoCaixaML()

    def gerar_alertas(
        self,
        unidades: List[Dict],
        boletos: List[Dict],
        pagamentos: List[Dict],
        acordos: List[Dict],
        lancamentos: List[Dict],
        saldo_atual: float = 0
    ) -> List[AlertaProativo]:
        """
        Analisa dados e gera alertas proativos

        Returns:
            Lista de AlertaProativo ordenada por severidade
        """
        alertas = []

        # 1. Alertas de inadimplência iminente
        alertas.extend(self._alertas_inadimplencia(unidades, boletos, pagamentos, acordos))

        # 2. Alertas de fluxo de caixa
        alertas.extend(self._alertas_fluxo_caixa(lancamentos, boletos, saldo_atual))

        # 3. Alertas de vencimentos próximos
        alertas.extend(self._alertas_vencimentos(boletos))

        # 4. Alertas de anomalias
        alertas.extend(self._alertas_anomalias(lancamentos))

        # Ordena por severidade
        severidade_ordem = {'critical': 0, 'warning': 1, 'info': 2}
        alertas.sort(key=lambda x: severidade_ordem.get(x.severidade, 3))

        return alertas

    def _alertas_inadimplencia(
        self,
        unidades: List[Dict],
        boletos: List[Dict],
        pagamentos: List[Dict],
        acordos: List[Dict]
    ) -> List[AlertaProativo]:
        """Gera alertas de inadimplência prevista"""
        alertas = []

        for unidade in unidades:
            # Filtra dados da unidade
            boletos_unidade = [b for b in boletos if b.get('unidade_id') == unidade.get('id')]
            pagamentos_unidade = [p for p in pagamentos if p.get('unidade_id') == unidade.get('id')]
            acordos_unidade = [a for a in acordos if a.get('unidade_id') == unidade.get('id')]

            # Calcula previsão
            previsao = self.modelo_inadimplencia.prever(
                boletos_unidade, pagamentos_unidade, acordos_unidade, unidade
            )

            # Gera alerta se risco alto
            if previsao.classificacao in ['alto', 'critico']:
                severidade = 'critical' if previsao.classificacao == 'critico' else 'warning'

                alertas.append(AlertaProativo(
                    tipo='inadimplencia_prevista',
                    severidade=severidade,
                    titulo=f"Risco de inadimplência: Unidade {unidade.get('numero', 'N/A')}",
                    mensagem=f"Probabilidade de {previsao.probabilidade:.1%} de inadimplência. "
                             f"Score: {previsao.score}/1000.",
                    entidade_tipo='unidade',
                    entidade_id=unidade.get('id', ''),
                    data_prevista=None,
                    acao_recomendada=previsao.recomendacao,
                    probabilidade=previsao.probabilidade,
                    criado_em=datetime.now().isoformat()
                ))

        return alertas

    def _alertas_fluxo_caixa(
        self,
        lancamentos: List[Dict],
        boletos: List[Dict],
        saldo_atual: float
    ) -> List[AlertaProativo]:
        """Gera alertas de fluxo de caixa crítico"""
        alertas = []

        # Separa receitas e despesas
        receitas = [l for l in lancamentos if l.get('tipo') == 'receita']
        despesas = [l for l in lancamentos if l.get('tipo') == 'despesa']

        # Previsão de fluxo
        previsoes = self.modelo_fluxo.prever(receitas, despesas, boletos, 30)

        # Verifica se saldo ficará negativo
        saldo_acumulado = saldo_atual
        for prev in previsoes:
            saldo_acumulado += prev.saldo_previsto

            if saldo_acumulado < 0:
                alertas.append(AlertaProativo(
                    tipo='fluxo_caixa_critico',
                    severidade='critical',
                    titulo='Fluxo de caixa crítico previsto',
                    mensagem=f"Saldo previsto de R$ {saldo_acumulado:,.2f} em {prev.data}. "
                             f"Ação imediata necessária.",
                    entidade_tipo='financeiro',
                    entidade_id='fluxo_caixa',
                    data_prevista=prev.data,
                    acao_recomendada='Antecipar recebimentos ou postergar despesas não essenciais.',
                    probabilidade=prev.confianca,
                    criado_em=datetime.now().isoformat()
                ))
                break

            elif saldo_acumulado < saldo_atual * 0.2:  # Abaixo de 20% do saldo atual
                alertas.append(AlertaProativo(
                    tipo='fluxo_caixa_baixo',
                    severidade='warning',
                    titulo='Saldo em caixa baixando',
                    mensagem=f"Saldo previsto de R$ {saldo_acumulado:,.2f} em {prev.data} "
                             f"(redução de {((saldo_atual - saldo_acumulado) / saldo_atual * 100):.0f}%).",
                    entidade_tipo='financeiro',
                    entidade_id='fluxo_caixa',
                    data_prevista=prev.data,
                    acao_recomendada='Monitorar recebimentos e intensificar cobrança.',
                    probabilidade=prev.confianca,
                    criado_em=datetime.now().isoformat()
                ))

        return alertas

    def _alertas_vencimentos(self, boletos: List[Dict]) -> List[AlertaProativo]:
        """Gera alertas de vencimentos próximos"""
        alertas = []
        hoje = date.today()

        # Boletos vencendo em 3 dias
        for boleto in boletos:
            if boleto.get('status') != 'pendente':
                continue

            try:
                vencimento = datetime.strptime(str(boleto.get('vencimento'))[:10], '%Y-%m-%d').date()
                dias_para_vencer = (vencimento - hoje).days

                if 0 < dias_para_vencer <= 3:
                    alertas.append(AlertaProativo(
                        tipo='vencimento_proximo',
                        severidade='info',
                        titulo=f"Boleto vence em {dias_para_vencer} dia(s)",
                        mensagem=f"Boleto de R$ {boleto.get('valor', 0):,.2f} da unidade "
                                 f"{boleto.get('unidade_id', 'N/A')} vence em {vencimento}.",
                        entidade_tipo='boleto',
                        entidade_id=boleto.get('id', ''),
                        data_prevista=vencimento.isoformat(),
                        acao_recomendada='Enviar lembrete ao morador.',
                        probabilidade=1.0,
                        criado_em=datetime.now().isoformat()
                    ))
            except:
                pass

        return alertas

    def _alertas_anomalias(self, lancamentos: List[Dict]) -> List[AlertaProativo]:
        """Detecta anomalias em lançamentos"""
        alertas = []

        if not lancamentos:
            return alertas

        # Calcula média e desvio padrão por categoria
        valores_por_categoria = {}
        for lanc in lancamentos:
            cat = lanc.get('categoria', 'geral')
            if cat not in valores_por_categoria:
                valores_por_categoria[cat] = []
            valores_por_categoria[cat].append(lanc.get('valor', 0))

        # Verifica lançamentos recentes
        hoje = date.today()
        for lanc in lancamentos:
            try:
                data_lanc = datetime.strptime(str(lanc.get('data', ''))[:10], '%Y-%m-%d').date()
                if (hoje - data_lanc).days > 7:
                    continue

                cat = lanc.get('categoria', 'geral')
                valores = valores_por_categoria.get(cat, [])

                if len(valores) >= 3:
                    media = sum(valores) / len(valores)
                    valor_lanc = lanc.get('valor', 0)

                    # Anomalia se > 2x a média
                    if valor_lanc > media * 2:
                        alertas.append(AlertaProativo(
                            tipo='anomalia_lancamento',
                            severidade='warning',
                            titulo=f"Lançamento atípico detectado",
                            mensagem=f"Valor de R$ {valor_lanc:,.2f} é {valor_lanc/media:.1f}x "
                                     f"a média da categoria ({cat}).",
                            entidade_tipo='lancamento',
                            entidade_id=lanc.get('id', ''),
                            data_prevista=None,
                            acao_recomendada='Verificar se o lançamento está correto.',
                            probabilidade=0.85,
                            criado_em=datetime.now().isoformat()
                        ))
            except:
                pass

        return alertas


# ==================== PRIORIZAÇÃO INTELIGENTE ====================

class PriorizadorCobranca:
    """
    Prioriza cobranças baseado em múltiplos fatores
    """

    def __init__(self):
        self.modelo_inadimplencia = ModeloInadimplenciaML()

    def priorizar(
        self,
        boletos_vencidos: List[Dict],
        unidades: Dict[str, Dict],
        historico_boletos: Dict[str, List[Dict]],
        historico_pagamentos: Dict[str, List[Dict]],
        acordos: Dict[str, List[Dict]]
    ) -> List[Dict]:
        """
        Retorna lista de boletos priorizados para cobrança

        Critérios:
        - Probabilidade de pagamento (quem tem mais chance de pagar)
        - Valor (ROI potencial)
        - Dias de atraso (urgência)
        - Histórico de respostas

        Returns:
            Lista ordenada por score de prioridade
        """
        priorizados = []

        for boleto in boletos_vencidos:
            unidade_id = boleto.get('unidade_id', '')
            unidade = unidades.get(unidade_id, {})

            # Calcula previsão de inadimplência
            previsao = self.modelo_inadimplencia.prever(
                historico_boletos.get(unidade_id, []),
                historico_pagamentos.get(unidade_id, []),
                acordos.get(unidade_id, []),
                unidade
            )

            # Calcula dias de atraso
            try:
                vencimento = datetime.strptime(str(boleto.get('vencimento'))[:10], '%Y-%m-%d').date()
                dias_atraso = (date.today() - vencimento).days
            except:
                dias_atraso = 0

            # Score de prioridade (0-100)
            valor = boleto.get('valor', 0)

            # Componentes do score
            score_conversao = (1 - previsao.probabilidade) * 30  # Quem tem mais chance de pagar
            score_valor = min(valor / 5000, 1) * 25  # Normalizado para R$ 5.000
            score_urgencia = min(dias_atraso / 90, 1) * 25  # Normalizado para 90 dias
            score_historico = previsao.confianca * 20  # Confiança no histórico

            score_total = score_conversao + score_valor + score_urgencia + score_historico

            # Estratégia recomendada
            if previsao.classificacao == 'baixo' and dias_atraso < 15:
                estrategia = "Lembrete amigável - alta chance de pagamento espontâneo"
            elif previsao.classificacao == 'medio':
                estrategia = "Contato direto com proposta de regularização"
            elif previsao.classificacao == 'alto':
                estrategia = "Cobrança intensiva - múltiplos canais"
            else:
                estrategia = "Última tentativa antes de medidas judiciais"

            priorizados.append({
                'boleto': boleto,
                'unidade': unidade,
                'score_prioridade': round(score_total, 1),
                'probabilidade_pagamento': round(1 - previsao.probabilidade, 3),
                'dias_atraso': dias_atraso,
                'classificacao_risco': previsao.classificacao,
                'estrategia_recomendada': estrategia,
                'fatores_risco': previsao.fatores_risco,
                'componentes_score': {
                    'conversao': round(score_conversao, 1),
                    'valor': round(score_valor, 1),
                    'urgencia': round(score_urgencia, 1),
                    'historico': round(score_historico, 1)
                }
            })

        # Ordena por score (maior primeiro)
        priorizados.sort(key=lambda x: x['score_prioridade'], reverse=True)

        return priorizados


# ==================== INSTÂNCIAS GLOBAIS ====================

ml_inadimplencia = ModeloInadimplenciaML()
ml_fluxo_caixa = PrevisaoFluxoCaixaML()
sistema_alertas = SistemaAlertasProativos()
priorizador_cobranca = PriorizadorCobranca()
